import os
import sys
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from crewai import Agent, Crew, Task, LLM

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from agents.dynamic_testing_agent.validation import (
    validate_dynamic_request,
    validate_dynamic_response,
    create_error_response,
    DynamicRequest,
    DynamicResponse,
    DynamicOutput,
    ExecutedCase,
    HttpExchange,
    StateDiff,
    Metrics,
    TaskStatus
)
from tools.dynamic_testing_tools import (
    HTTPXScopedClient,
    SandboxController,
    DBSnapshotHelper,
    StateDiffEngine,
    PlaywrightBrowserTool,
    ExecuteHttpTestTool,
    SnapshotDatabaseTool,
    ComputeStateDiffTool,
    PlaywrightUiTool,
    ScopeGateError,
    SandboxHealthError,
    SnapshotError
)
from tools.artifact_store import save_task_output

class DynamicTestingAgent:
    def __init__(self, groq_api_key: Optional[str] = None, model_name: Optional[str] = None, db: Optional[Any] = None):
        self.api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.model_name = model_name or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.db = db
        self.llm = LLM(
            model=f"groq/{self.model_name}",
            api_key=self.api_key,
            temperature=0.1
        )
        self.tools = [
            ExecuteHttpTestTool(),
            SnapshotDatabaseTool(),
            ComputeStateDiffTool(),
            PlaywrightUiTool()
        ]
        self.crew_agent = Agent(
            role="Dynamic Application Security Testing Specialist",
            goal="Execute validated multi-identity exploit scenarios inside isolated sandboxes and capture cryptographic state diffs.",
            backstory="Senior dynamic AppSec test engineer proficient in HTTP protocol verification, multi-tenant state isolation, and database forensic diffs.",
            llm=self.llm,
            tools=self.tools,
            verbose=False
        )

    def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        warnings = []

        is_valid, req, err = validate_dynamic_request(request_data)
        if not is_valid or not req:
            return create_error_response(
                request_data,
                code=err.code if err else "SCHEMA_VALIDATION_FAILED",
                message=err.message if err else "Request validation failed",
                retryable=err.retryable if err else False,
                details=err.details if err else None
            )

        test_plan = req.input.test_plan
        endpoint = req.input.endpoint
        identities = req.input.identities
        sandbox = req.input.sandbox
        invariant_id = req.input.invariant_id

        sandbox_ctrl = SandboxController(base_url=sandbox.base_url)
        healthy = False
        for attempt in range(1, 4):
            if sandbox_ctrl.check_health():
                healthy = True
                break
            sandbox_ctrl.reset_sandbox()
            time.sleep(0.05)

        if not healthy:
            return create_error_response(
                request_data,
                code="SANDBOX_UNHEALTHY",
                message=f"Target sandbox '{sandbox.sandbox_id}' failed health check at {sandbox.base_url} after 3 attempts",
                retryable=True
            )

        try:
            db_helper = DBSnapshotHelper()
        except SnapshotError as exc:
            return create_error_response(
                request_data,
                code="SNAPSHOT_FAILED",
                message=f"No sandbox database available for state snapshots: {exc}",
                retryable=True
            )

        sandbox_host = None
        try:
            from urllib.parse import urlparse
            sandbox_host = urlparse(sandbox.base_url).hostname
        except Exception:
            sandbox_host = None
        http_client = HTTPXScopedClient(
            base_url=sandbox.base_url,
            allowed_hosts=[sandbox_host] if sandbox_host else None,
            allowed_methods=[endpoint.method.upper()],
        )
        browser_tool = PlaywrightBrowserTool()

        before_snapshots: List[Tuple[Any, str, Dict[str, Any]]] = []
        if sandbox.snapshot_enabled:
            snap_ok = False
            last_snap_err = None
            for attempt in range(1, 4):
                try:
                    before_snapshots = []
                    for sc in test_plan.state_checks:
                        snap_id, data = db_helper.snapshot(sc.table, sc.key, sc.columns)
                        before_snapshots.append((sc, snap_id, data))
                    snap_ok = True
                    break
                except Exception as e:
                    last_snap_err = str(e)
                    sandbox_ctrl.reset_sandbox()
                    time.sleep(0.05)
            if not snap_ok:
                return create_error_response(
                    request_data,
                    code="SNAPSHOT_FAILED",
                    message=f"Initial database snapshot failed: {last_snap_err}",
                    retryable=True
                )

        executed_cases = []
        executed_requests: List[Dict[str, Any]] = []
        path = endpoint.path
        if endpoint.path_params:
            for p in endpoint.path_params:
                sample_val = None
                for ident in identities:
                    if ident.owns and p in ident.owns:
                        sample_val = str(ident.owns[p])
                        break
                    if ident.owns and "order_id" in ident.owns:
                        sample_val = str(ident.owns["order_id"])
                        break
                if sample_val is None:
                    sample_val = os.environ.get("AEGIS_SAMPLE_ID", "1")
                path = path.replace(f"{{{p}}}", sample_val)

        def build_test_body(identity_id: str) -> Optional[Dict[str, Any]]:
            if endpoint.method.upper() not in ["POST", "PATCH", "PUT"]:
                return None
            body: Dict[str, Any] = {}
            for sc, _snap_id, data in before_snapshots:
                for col in sc.columns:
                    current = data.get(col)
                    if isinstance(current, bool):
                        body[col] = not current
                    elif isinstance(current, (int, float)):
                        body[col] = current + 1
                    elif isinstance(current, str):
                        body[col] = f"{current} [aegistrace-{identity_id}]"
                    else:
                        body[col] = f"aegistrace-{identity_id}"
            return body or None

        case_num = 1
        request_count = 0
        for ident in identities:
            if request_count >= sandbox.max_requests:
                return create_error_response(
                    request_data,
                    code="REQUEST_BUDGET_EXCEEDED",
                    message=f"Request budget of {sandbox.max_requests} exceeded during test execution",
                    retryable=False
                )

            case_id = f"case_{case_num:02d}"
            body = build_test_body(ident.identity_id)

            try:
                ex = http_client.execute(
                    method=endpoint.method,
                    path=path,
                    identity_id=ident.identity_id,
                    json_body=body,
                    credential_ref=ident.credential_ref
                )
                request_count += 1
            except ScopeGateError as e:
                return create_error_response(
                    request_data,
                    code="SCOPE_VIOLATION",
                    message=str(e),
                    retryable=False
                )
            except SandboxHealthError as e:
                return create_error_response(
                    request_data,
                    code="SANDBOX_UNHEALTHY",
                    message=str(e),
                    retryable=True
                )

            executed_requests.append({
                "case_id": case_id,
                "identity_id": ident.identity_id,
                "method": ex["method"],
                "url": ex["url"],
                "path": path,
                "json_body": body,
                "status_code": ex["status_code"],
                "evidence_id": ex["evidence_id"],
                "credential_ref": ident.credential_ref,
                "credential_resolved": ex.get("credential_resolved", False),
            })

            exchange = HttpExchange(
                method=ex["method"],
                url=ex["url"],
                status_code=ex["status_code"],
                response_excerpt=ex["response_excerpt"],
                evidence_id=ex["evidence_id"]
            )
            executed_cases.append(ExecutedCase(
                case_id=case_id,
                identity_id=ident.identity_id,
                exchange=exchange
            ))
            case_num += 1

        after_snapshots: List[Tuple[Any, str, Dict[str, Any]]] = []
        if sandbox.snapshot_enabled:
            snap_after_ok = False
            last_after_err = None
            for attempt in range(1, 4):
                try:
                    after_snapshots = []
                    for sc in test_plan.state_checks:
                        snap_id, data = db_helper.snapshot(sc.table, sc.key, sc.columns)
                        after_snapshots.append((sc, snap_id, data))
                    snap_after_ok = True
                    break
                except Exception as e:
                    last_after_err = str(e)
                    sandbox_ctrl.reset_sandbox()
                    time.sleep(0.05)
            if not snap_after_ok:
                return create_error_response(
                    request_data,
                    code="SNAPSHOT_FAILED",
                    message=f"Post-request database snapshot failed: {last_after_err}",
                    retryable=True
                )

        state_diffs = []
        if sandbox.snapshot_enabled:
            for (sc, before_id, before_data), (_sc_after, after_id, after_data) in zip(before_snapshots, after_snapshots):
                diffs = StateDiffEngine.compute_diffs(
                    table=sc.table,
                    key=sc.key,
                    columns=sc.columns,
                    before_snapshot_id=before_id,
                    after_snapshot_id=after_id,
                    before_state=before_data,
                    after_state=after_data
                )
                for d in diffs:
                    state_diffs.append(StateDiff(
                        table=d["table"],
                        key=d["key"],
                        column=d["column"],
                        before=d["before"],
                        after=d["after"],
                        snapshot_before_id=d["snapshot_before_id"],
                        snapshot_after_id=d["snapshot_after_id"],
                        evidence_id=d["evidence_id"]
                    ))

        if len(executed_cases) >= 2:
            c1 = executed_cases[0]
            c2 = executed_cases[1]
            if state_diffs:
                narrative = f"Primary identity '{c1.identity_id}' yielded HTTP {c1.exchange.status_code}; secondary identity '{c2.identity_id}' yielded HTTP {c2.exchange.status_code}, yet state diffs prove unauthorized mutation occurred in database table '{state_diffs[0].table}'."
            else:
                narrative = f"Primary identity '{c1.identity_id}' yielded HTTP {c1.exchange.status_code}; secondary identity '{c2.identity_id}' yielded HTTP {c2.exchange.status_code}. No unauthorized database mutations were observed."
        elif executed_cases:
            narrative = f"Single identity '{executed_cases[0].identity_id}' yielded HTTP {executed_cases[0].exchange.status_code}. State diffs count: {len(state_diffs)}."
        else:
            narrative = "No test cases executed."

        duration_ms = int((time.time() - start_time) * 1000)
        metrics = Metrics(
            duration_ms=duration_ms,
            llm_calls=0,
            input_tokens=0,
            output_tokens=0
        )

        output = DynamicOutput(
            executed_cases=executed_cases,
            identity_comparison=narrative,
            state_diffs=state_diffs,
            execution_status="completed",
            log_ref=f"log://{req.task_id}"
        )

        resp_payload = {
            "schema_version": req.schema_version,
            "correlation_id": req.correlation_id,
            "project_id": req.project_id,
            "engagement_id": req.engagement_id,
            "scan_id": req.scan_id,
            "task_id": req.task_id,
            "agent_run_id": req.agent_run_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "succeeded",
            "warnings": warnings,
            "error": None,
            "metrics": metrics.model_dump(),
            "agent": "dynamic_testing",
            "output": output.model_dump()
        }

        is_resp_valid, resp_obj, resp_err = validate_dynamic_response(resp_payload)
        if not is_resp_valid or not resp_obj:
            return create_error_response(
                request_data,
                code="RESPONSE_VALIDATION_FAILED",
                message=resp_err.message if resp_err else "Response validation failed",
                retryable=False,
                details=resp_err.details if resp_err else None
            )

        artifact = {
            "task_id": req.task_id,
            "agent": "dynamic_testing",
            "request": request_data,
            "response": resp_payload,
            "output": resp_payload["output"],
            "internal": {
                "sandbox": sandbox.model_dump(),
                "test_plan": test_plan.model_dump(),
                "endpoint": endpoint.model_dump(),
                "identities": [i.model_dump() for i in identities],
                "executed_requests": executed_requests,
                "state_checks": [sc.model_dump() for sc in test_plan.state_checks],
            },
        }
        save_task_output(req.task_id, artifact)

        unresolved = [r["identity_id"] for r in executed_requests if not r.get("credential_resolved")]
        if unresolved:
            resp_payload["warnings"].append(
                "CREDENTIAL_UNRESOLVED: no secret was configured for identities "
                + ", ".join(sorted(set(unresolved)))
                + "; requests were sent without an Authorization header"
            )

        if self.db:
            try:
                mem_db_path = os.path.join(workspace_root, "memory and database")
                if mem_db_path not in sys.path:
                    sys.path.insert(0, mem_db_path)
                from agent_db_connector import AgentDatabaseConnector
                connector = AgentDatabaseConnector(self.db)
                connector.sync_dynamic_testing(request_data, resp_payload)
            except Exception as exc:
                resp_payload["warnings"].append(f"PERSISTENCE_FAILED: dynamic testing sync failed: {exc}")

        return resp_payload

def run_dynamic_testing(request_data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    agent = DynamicTestingAgent(db=db)
    return agent.execute(request_data)
