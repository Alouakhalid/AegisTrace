import os
import sys
import json
import time
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from crewai import Agent, Crew, Task, LLM

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_dir = os.path.join(workspace_root, "memory and database")
if mem_db_dir not in sys.path:
    sys.path.insert(0, mem_db_dir)

from agent_db_connector import AgentDatabaseConnector
from agents.orchestrator_agent.validation import (
    validate_orchestrator_request,
    validate_orchestrator_response,
    create_error_response,
    OrchestratorRequest,
    OrchestratorResponse,
    OrchestratorOutput,
    ScopeValidation,
    ScopeCheck,
    Stage,
    TaskAssignment,
    ErrorInfo,
    Metrics,
    TaskStatus,
    WorkflowStatus,
    AgentName,
    current_utc_iso
)

from tools.orchestrator_tools import (
    ScopeValidator,
    WorkflowPlanner,
    TaskQueueManager,
    AuditLogger,
    WorkflowCycleError,
    ValidateScopeTool,
    PlanWorkflowStagesTool,
    AssignAgentTasksTool,
    EmitAuditLogTool
)

class OrchestratorAgent:
    def __init__(self, groq_api_key: Optional[str] = None, model_name: Optional[str] = None, db: Optional[Any] = None):
        self.api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.model_name = model_name or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.db = db
        self.llm = LLM(
            model=f"groq/{self.model_name}",
            api_key=self.api_key,
            temperature=0.1
        )
        self.scope_validator = ScopeValidator()
        self.workflow_planner = WorkflowPlanner()
        self.task_queue_manager = TaskQueueManager()
        self.audit_logger = AuditLogger(self.db)
        self.connector = AgentDatabaseConnector(self.db)

        self.tools = [
            ValidateScopeTool(validator=self.scope_validator),
            PlanWorkflowStagesTool(planner=self.workflow_planner),
            AssignAgentTasksTool(queue_manager=self.task_queue_manager),
            EmitAuditLogTool(logger=self.audit_logger)
        ]

        self.crew_agent = Agent(
            role="AegisTrace Workflow & Scope Orchestrator",
            goal="Validate customer authorization and scope boundaries, plan acyclic multi-agent assessment workflows, and assign deterministic agent tasks.",
            backstory="Lead Security Operations Orchestrator responsible for verifying that every security assessment operation stays strictly within authorized scope, rejects production environments, and provisions stage dependencies.",
            tools=self.tools,
            llm=self.llm,
            verbose=False,
            memory=False
        )

    def register_scope_manifest(self, scm_id: str, manifest_data: Dict[str, Any], valid: bool = True, attested: bool = False) -> None:
        self.scope_validator.register_manifest(scm_id, manifest_data, valid=valid, attested=attested)

    def run_orchestration(self, request_data: Dict[str, Any], raw_manifest: Optional[Dict[str, Any]] = None) -> OrchestratorResponse:
        start_time = time.time()
        target_info = request_data.get("input", {}).get("target", {})
        target_env = target_info.get("environment", "") if isinstance(target_info, dict) else ""
        if str(target_env).lower() == "production":
            scope_valid, checks_data = self.scope_validator.validate_scope(
                target_base_url=target_info.get("base_url", ""),
                environment="production",
                scope_manifest_id=request_data.get("input", {}).get("scope_manifest_id", "scm_00000000"),
                manifest_data=raw_manifest
            )
            pydantic_checks = [ScopeCheck(**c) for c in checks_data]
            failed_checks = [c.name for c in pydantic_checks if not c.passed]
            self.audit_logger.emit_log(
                actor_type="agent",
                actor_id="orchestrator",
                action="scope_validation_failed",
                allowed=False,
                scan_id=request_data.get("scan_id"),
                resource_type="scope_manifest",
                resource_id=request_data.get("input", {}).get("scope_manifest_id"),
                details={"failed_checks": failed_checks}
            )
            partial_output = OrchestratorOutput(
                scope_validation=ScopeValidation(valid=False, checks=pydantic_checks),
                stages=[],
                task_assignments=[],
                workflow_status=WorkflowStatus.blocked
            )
            return OrchestratorResponse(
                schema_version=request_data.get("schema_version", "1.0.0"),
                correlation_id=request_data.get("correlation_id", f"cor_{uuid.uuid4().hex[:10]}"),
                project_id=request_data.get("project_id", f"prj_{uuid.uuid4().hex[:10]}"),
                engagement_id=request_data.get("engagement_id", f"eng_{uuid.uuid4().hex[:10]}"),
                scan_id=request_data.get("scan_id", f"scn_{uuid.uuid4().hex[:10]}"),
                task_id=request_data.get("task_id", f"tsk_{uuid.uuid4().hex[:10]}"),
                agent_run_id=request_data.get("agent_run_id", f"run_{uuid.uuid4().hex[:10]}"),
                status=TaskStatus.blocked,
                warnings=[],
                error=ErrorInfo(
                    code="SCOPE_INVALID",
                    message="Testing on environment 'production' is strictly forbidden in MVP",
                    retryable=False,
                    details={"failed_checks": failed_checks}
                ),
                metrics=Metrics(duration_ms=int((time.time() - start_time) * 1000), llm_calls=0, input_tokens=0, output_tokens=0),
                agent="orchestrator",
                output=partial_output
            )

        valid_req, err_msg, req = validate_orchestrator_request(request_data)
        if not valid_req or not req:
            c_id = request_data.get("correlation_id", "")
            if not isinstance(c_id, str) or not re.match(r"^cor_[0-9a-f]{8,}$", c_id):
                c_id = f"cor_{uuid.uuid4().hex[:10]}"
            p_id = request_data.get("project_id", "")
            if not isinstance(p_id, str) or not re.match(r"^prj_[0-9a-f]{8,}$", p_id):
                p_id = f"prj_{uuid.uuid4().hex[:10]}"
            e_id = request_data.get("engagement_id", "")
            if not isinstance(e_id, str) or not re.match(r"^eng_[0-9a-f]{8,}$", e_id):
                e_id = f"eng_{uuid.uuid4().hex[:10]}"
            s_id = request_data.get("scan_id", "")
            if not isinstance(s_id, str) or not re.match(r"^scn_[0-9a-f]{8,}$", s_id):
                s_id = f"scn_{uuid.uuid4().hex[:10]}"
            t_id = request_data.get("task_id", "")
            if not isinstance(t_id, str) or not re.match(r"^tsk_[0-9a-f]{8,}$", t_id):
                t_id = f"tsk_{uuid.uuid4().hex[:10]}"
            r_id = request_data.get("agent_run_id", "")
            if not isinstance(r_id, str) or not re.match(r"^run_[0-9a-f]{8,}$", r_id):
                r_id = f"run_{uuid.uuid4().hex[:10]}"
            error_resp = OrchestratorResponse(
                schema_version=request_data.get("schema_version", "1.0.0"),
                correlation_id=c_id,
                project_id=p_id,
                engagement_id=e_id,
                scan_id=s_id,
                task_id=t_id,
                agent_run_id=r_id,
                status=TaskStatus.failed,
                warnings=[],
                error=ErrorInfo(
                    code="MISSING_INPUT",
                    message=f"Request contract validation failed: {err_msg}",
                    retryable=False,
                    details={"error": err_msg}
                ),
                metrics=Metrics(duration_ms=int((time.time() - start_time) * 1000), llm_calls=0, input_tokens=0, output_tokens=0),
                agent="orchestrator",
                output=None
            )
            return error_resp

        inp = req.input

        if len(inp.credential_refs) < 2:
            return create_error_response(
                request=req,
                code="MISSING_INPUT",
                message="At least 2 distinct credential references are required for horizontal privilege testing.",
                retryable=False,
                details={"credential_count": len(inp.credential_refs)},
                status=TaskStatus.failed
            )

        distinct_refs = {c.ref for c in inp.credential_refs}
        if len(distinct_refs) < 2:
            return create_error_response(
                request=req,
                code="MISSING_INPUT",
                message="At least 2 distinct credential references are required for horizontal privilege testing.",
                retryable=False,
                details={"credential_count": len(inp.credential_refs), "distinct_count": len(distinct_refs)},
                status=TaskStatus.failed
            )

        scope_valid, checks_data = self.scope_validator.validate_scope(
            target_base_url=inp.target.base_url,
            environment=inp.target.environment,
            scope_manifest_id=inp.scope_manifest_id,
            manifest_data=raw_manifest
        )

        pydantic_checks = [ScopeCheck(**c) for c in checks_data]
        scope_validation_obj = ScopeValidation(valid=scope_valid, checks=pydantic_checks)

        if not scope_valid:
            failed_checks = [c.name for c in pydantic_checks if not c.passed]
            self.audit_logger.emit_log(
                actor_type="agent",
                actor_id="orchestrator",
                action="scope_validation_failed",
                allowed=False,
                scan_id=req.scan_id,
                resource_type="scope_manifest",
                resource_id=inp.scope_manifest_id,
                details={"failed_checks": failed_checks}
            )
            partial_output = OrchestratorOutput(
                scope_validation=scope_validation_obj,
                stages=[],
                task_assignments=[],
                workflow_status=WorkflowStatus.blocked
            )
            return create_error_response(
                request=req,
                code="SCOPE_INVALID",
                message=f"Deterministic scope validation failed on checks: {', '.join(failed_checks)}",
                retryable=False,
                details={"failed_checks": failed_checks},
                status=TaskStatus.blocked,
                partial_output=partial_output
            )

        self.audit_logger.emit_log(
            actor_type="agent",
            actor_id="orchestrator",
            action="scope_validation_passed",
            allowed=True,
            scan_id=req.scan_id,
            resource_type="scope_manifest",
            resource_id=inp.scope_manifest_id,
            details={"checks": [c.name for c in pydantic_checks]}
        )

        try:
            planned_stages_data = self.workflow_planner.plan_workflow(
                assessment_mode=inp.assessment_mode.value if hasattr(inp.assessment_mode, "value") else str(inp.assessment_mode),
                requested_operations=[op for op in inp.requested_operations]
            )
        except WorkflowCycleError as e:
            return create_error_response(
                request=req,
                code="PLAN_CYCLE",
                message=str(e),
                retryable=False,
                details={"error": str(e)},
                status=TaskStatus.failed
            )

        stages_objs = [Stage(**s) for s in planned_stages_data]

        assignments_data = self.task_queue_manager.create_assignments_for_stages(planned_stages_data)
        assignments_objs = [TaskAssignment(**a) for a in assignments_data]

        if self.db:
            try:
                self.db.create_scan(
                    scn_id=req.scan_id,
                    engagement_id=req.engagement_id,
                    scope_manifest_id=inp.scope_manifest_id,
                    correlation_id=req.correlation_id,
                    requested_by="usr_00000001",
                    status="running"
                )
                for a in assignments_data:
                    self.db.create_agent_task(
                        tsk_id=a["task_id"],
                        scan_id=req.scan_id,
                        agent=a["agent"],
                        stage=a["stage"],
                        status="queued",
                        depends_on=a["depends_on"]
                    )
            except Exception:
                pass

        self.audit_logger.emit_log(
            actor_type="agent",
            actor_id="orchestrator",
            action="workflow_planned",
            allowed=True,
            scan_id=req.scan_id,
            resource_type="workflow",
            resource_id=req.scan_id,
            details={"stages": [s.name for s in stages_objs], "tasks": len(assignments_objs)}
        )

        output_obj = OrchestratorOutput(
            scope_validation=scope_validation_obj,
            stages=stages_objs,
            task_assignments=assignments_objs,
            workflow_status=WorkflowStatus.planned
        )

        duration_ms = max(1, int((time.time() - start_time) * 1000))
        resp = OrchestratorResponse(
            schema_version=req.schema_version,
            correlation_id=req.correlation_id,
            project_id=req.project_id,
            engagement_id=req.engagement_id,
            scan_id=req.scan_id,
            task_id=req.task_id,
            agent_run_id=req.agent_run_id,
            status=TaskStatus.succeeded,
            warnings=[],
            error=None,
            metrics=Metrics(duration_ms=duration_ms, llm_calls=0, input_tokens=0, output_tokens=0),
            agent="orchestrator",
            output=output_obj
        )

        if self.db:
            try:
                self.connector.sync_orchestrator(request_data, resp.model_dump(mode="json"))
            except Exception:
                pass

        return resp
