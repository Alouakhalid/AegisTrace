import os
import sys
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
from crewai import Agent, Crew, Task, LLM

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

agent_dir = os.path.dirname(os.path.abspath(__file__))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from validation import (
    validate_verification_request,
    validate_verification_response,
    create_error_response,
    VerificationRequest,
    VerificationResponse,
    VerificationOutput,
    Reproducibility,
    Severity,
    SeverityLevel,
    Verdict,
    Metrics,
    TaskStatus
)
from tools.verification_tools import (
    EvidenceStore,
    EvidenceHashMismatchError,
    ReproductionEnvError,
    InsufficientEvidenceError,
    DynamicTestingReplayEngine,
    InvariantEvaluator,
    TriageValidationSkill,
    CVSSCalculatorEngine,
    ConfidenceScorer,
    VerifyEvidenceHashTool,
    ReplayDynamicScenarioTool,
    EvaluateInvariantTool,
    ComputeCVSSVectorTool
)
from tools.artifact_store import load_task_output

class VerificationAgent:
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
            VerifyEvidenceHashTool(),
            ReplayDynamicScenarioTool(),
            EvaluateInvariantTool(),
            ComputeCVSSVectorTool()
        ]
        self.crew_agent = Agent(
            role="Independent Vulnerability Verification & Exploit Arbiter",
            goal="Reproduce candidate vulnerabilities, verify evidence integrity, evaluate state diff invariants, and determine definitive findings with CVSS v3.1.",
            backstory="Senior verification engineer and exploit arbiter evaluating empirical vulnerability evidence and calculating formal CVSS vectors.",
            llm=self.llm,
            tools=self.tools,
            verbose=False
        )

    def execute(
        self,
        request_data: Dict[str, Any],
        evidence_store: Optional[EvidenceStore] = None,
        replay_engine: Optional[DynamicTestingReplayEngine] = None,
        sandbox_id: str = "sbx_0192f2f0",
        test_steps: Optional[List[Dict[str, Any]]] = None,
        state_checks: Optional[List[Dict[str, Any]]] = None,
        is_business_logic_intended: bool = False
    ) -> Dict[str, Any]:
        start_time = time.time()
        warnings: List[str] = []

        is_valid, req, err = validate_verification_request(request_data)
        if not is_valid or not req:
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="INVALID_REQUEST_PAYLOAD",
                message=err or "Schema validation failed against VerificationRequest",
                retryable=False,
                duration_ms=duration_ms
            )

        if len(req.input.evidence_ids) == 0:
            duration_ms = int((time.time() - start_time) * 1000)
            out = VerificationOutput(
                finding_id=None,
                verdict=Verdict.UNCONFIRMED,
                reproducibility=Reproducibility(runs=0, reproduced=0),
                confidence=0.0,
                severity=None,
                invariant_violated=False,
                supporting_evidence_ids=[],
                rejection_reasons=["Insufficient evidence records provided in request payload"]
            )
            return self._build_response(req, out, ["INSUFFICIENT_EVIDENCE: zero evidence IDs supplied, default verdict is unconfirmed"], duration_ms)

        store = evidence_store or EvidenceStore()
        missing_evidence: List[str] = []
        verified_evidence = 0
        for eid in req.input.evidence_ids:
            record = store.get_evidence(eid)
            if not record:
                missing_evidence.append(eid)
                continue
            is_hash_ok, hash_detail = store.verify_evidence_hash(eid)
            if not is_hash_ok:
                duration_ms = int((time.time() - start_time) * 1000)
                return create_error_response(
                    request_data=request_data,
                    code="EVIDENCE_HASH_MISMATCH",
                    message=f"Stored evidence {eid} no longer matches its SHA-256: {hash_detail}",
                    retryable=False,
                    duration_ms=duration_ms
                )
            verified_evidence += 1
        evidence_integrity_ratio = verified_evidence / max(1, len(req.input.evidence_ids))
        if missing_evidence:
            warnings.append(
                "INSUFFICIENT_EVIDENCE: evidence records not found: "
                + ", ".join(sorted(missing_evidence))
            )

        artifact = load_task_output(req.input.dynamic_result_ref) or {}
        dynamic_output = artifact.get("output") if isinstance(artifact.get("output"), dict) else artifact
        internal = artifact.get("internal") if isinstance(artifact.get("internal"), dict) else {}
        sandbox_config = internal.get("sandbox", {}) if isinstance(internal.get("sandbox"), dict) else {}
        base_url = sandbox_config.get("base_url", "")

        replay_steps: List[Dict[str, Any]] = list(test_steps or [])
        if not replay_steps:
            for item in internal.get("executed_requests", []) or []:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if not url and base_url:
                    url = base_url.rstrip("/") + str(item.get("path", "/"))
                if not url:
                    continue
                replay_steps.append({
                    "method": item.get("method", "GET"),
                    "url": url,
                    "identity_id": item.get("identity_id", "id_owner"),
                    "json_body": item.get("json_body"),
                    "credential_ref": item.get("credential_ref"),
                })
        if not replay_steps:
            for case in (dynamic_output or {}).get("executed_cases", []) or []:
                exchange = case.get("exchange", {}) if isinstance(case, dict) else {}
                if exchange.get("url"):
                    replay_steps.append({
                        "method": exchange.get("method", "GET"),
                        "url": exchange.get("url"),
                        "identity_id": case.get("identity_id", "id_owner"),
                        "json_body": None,
                    })

        state_checks = state_checks or internal.get("state_checks") or []
        if not state_checks:
            state_checks = self._state_checks_from_diffs((dynamic_output or {}).get("state_diffs", []))

        if not replay_steps:
            duration_ms = int((time.time() - start_time) * 1000)
            out = VerificationOutput(
                finding_id=None,
                verdict=Verdict.UNCONFIRMED,
                reproducibility=Reproducibility(runs=0, reproduced=0),
                confidence=0.0,
                severity=None,
                invariant_violated=False,
                supporting_evidence_ids=[],
                rejection_reasons=[
                    f"dynamic_result_ref '{req.input.dynamic_result_ref}' does not contain replayable requests"
                ]
            )
            warnings.append("INSUFFICIENT_EVIDENCE: no replayable dynamic-testing requests were found")
            return self._build_response(req, out, warnings, duration_ms)

        if not base_url:
            parsed_first = urlparse(replay_steps[0].get("url", ""))
            if parsed_first.scheme and parsed_first.netloc:
                base_url = f"{parsed_first.scheme}://{parsed_first.netloc}"
        allowed_hosts = sorted({
            urlparse(step.get("url", "")).hostname
            for step in replay_steps
            if urlparse(step.get("url", "")).hostname
        })
        allowed_methods = sorted({str(step.get("method", "GET")).upper() for step in replay_steps})

        engine = replay_engine or DynamicTestingReplayEngine()
        runs_requested = req.input.reproduction_runs_requested
        try:
            runs_attempted, runs_reproduced, state_diff, last_exchange = engine.replay_scenario(
                sandbox_id=sandbox_id,
                runs_requested=runs_requested,
                test_steps=replay_steps,
                expected_violation=True,
                state_checks=state_checks or None,
                base_url=base_url or None,
                allowed_hosts=allowed_hosts or None,
                allowed_methods=allowed_methods or None,
            )
        except ReproductionEnvError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="REPRODUCTION_ENV_FAILED",
                message=str(e),
                retryable=True,
                duration_ms=duration_ms
            )
        except ValueError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            out = VerificationOutput(
                finding_id=None,
                verdict=Verdict.UNCONFIRMED,
                reproducibility=Reproducibility(runs=0, reproduced=0),
                confidence=0.0,
                severity=None,
                invariant_violated=False,
                supporting_evidence_ids=[],
                rejection_reasons=[str(e)]
            )
            warnings.append("INSUFFICIENT_EVIDENCE: replay could not be constructed")
            return self._build_response(req, out, warnings, duration_ms)

        target_url = replay_steps[0].get("url", "") if replay_steps else ""
        mutations = state_diff.get("mutations", [])
        state_diff_detected = len(mutations) > 0
        if missing_evidence:
            runs_reproduced = 0

        triage_passed, rejection_reasons = TriageValidationSkill.evaluate_triage_gates(
            target_url=target_url,
            runs_reproduced=runs_reproduced,
            state_diff_detected=state_diff_detected,
            is_business_logic_intended=is_business_logic_intended,
            allowed_hosts=allowed_hosts or None,
        )

        if not triage_passed:
            verdict = Verdict.REJECTED
            finding_id = None
            severity = None
            invariant_violated = False
            confidence = 0.0
            supporting_ids = []
        else:
            is_violated, eval_msg = InvariantEvaluator.evaluate(
                invariant_statement=req.input.invariant_statement,
                state_diff=state_diff,
                exchange=last_exchange
            )
            if is_violated and runs_reproduced >= 1:
                verdict = Verdict.CONFIRMED
                finding_id = f"fnd_{uuid.uuid4().hex[:8]}"
                cvss_calc = CVSSCalculatorEngine.calculate(
                    category=req.input.hypothesis.category,
                    invariant_violated=True,
                    state_diff=state_diff
                )
                severity = Severity(
                    level=SeverityLevel(cvss_calc["level"]),
                    rationale=cvss_calc["rationale"],
                    cvss_vector=cvss_calc.get("cvss_vector")
                )
                confidence = ConfidenceScorer.score(
                    reproduction_rate=runs_reproduced / max(1, runs_attempted),
                    evidence_integrity_ratio=evidence_integrity_ratio,
                    has_state_diff=True
                )
                invariant_violated = True
                supporting_ids = [eid for eid in req.input.evidence_ids if store.get_evidence(eid)]
                rejection_reasons = []
            else:
                verdict = Verdict.UNCONFIRMED
                finding_id = None
                severity = None
                confidence = ConfidenceScorer.score(
                    reproduction_rate=runs_reproduced / max(1, runs_attempted),
                    evidence_integrity_ratio=evidence_integrity_ratio,
                    has_state_diff=state_diff_detected
                )
                invariant_violated = is_violated
                supporting_ids = [eid for eid in req.input.evidence_ids if store.get_evidence(eid)]
                rejection_reasons = [] if is_violated else [eval_msg]

        output = VerificationOutput(
            finding_id=finding_id,
            verdict=verdict,
            reproducibility=Reproducibility(runs=runs_attempted, reproduced=runs_reproduced),
            confidence=confidence,
            severity=severity,
            invariant_violated=invariant_violated,
            supporting_evidence_ids=supporting_ids,
            rejection_reasons=rejection_reasons
        )

        duration_ms = int((time.time() - start_time) * 1000)
        response_dict = self._build_response(req, output, warnings, duration_ms)

        if self.db:
            try:
                mem_db_path = os.path.join(workspace_root, "memory and database")
                if mem_db_path not in sys.path:
                    sys.path.insert(0, mem_db_path)
                from agent_db_connector import AgentDatabaseConnector
                connector = AgentDatabaseConnector(self.db)
                connector.sync_verification(request_data, response_dict)
            except Exception as exc:
                response_dict["warnings"].append(f"PERSISTENCE_FAILED: verification sync failed: {exc}")

        return response_dict

    @staticmethod
    def _state_checks_from_diffs(diffs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for diff in diffs or []:
            if not isinstance(diff, dict):
                continue
            table = diff.get("table")
            key = diff.get("key", {})
            if not table:
                continue
            group_key = (table, json.dumps(key, sort_keys=True))
            if group_key not in grouped:
                grouped[group_key] = {"table": table, "key": key, "columns": []}
            column = diff.get("column")
            if column and column not in grouped[group_key]["columns"]:
                grouped[group_key]["columns"].append(column)
        return [value for value in grouped.values() if value["columns"]]

    def _build_response(self, req, output: VerificationOutput, warnings: List[str], duration_ms: int) -> Dict[str, Any]:
        response_dict = {
            "schema_version": req.schema_version,
            "correlation_id": req.correlation_id,
            "project_id": req.project_id,
            "engagement_id": req.engagement_id,
            "scan_id": req.scan_id,
            "task_id": req.task_id,
            "agent_run_id": req.agent_run_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": "verification",
            "status": TaskStatus.SUCCEEDED.value,
            "warnings": warnings,
            "error": None,
            "metrics": {
                "duration_ms": max(1, duration_ms),
                "llm_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0
            },
            "output": output.model_dump()
        }
        is_resp_valid, _resp_model, resp_err = validate_verification_response(response_dict)
        if not is_resp_valid:
            return create_error_response(
                request_data=response_dict,
                code="RESPONSE_VALIDATION_FAILED",
                message=resp_err or "VerificationResponse schema validation failed",
                retryable=False,
                duration_ms=duration_ms
            )
        return response_dict

def run_verification(request_data: Dict[str, Any], db: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
    agent = VerificationAgent(db=db)
    return agent.execute(request_data, **kwargs)
