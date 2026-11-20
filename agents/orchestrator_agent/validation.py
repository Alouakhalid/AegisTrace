import os
import re
import json
import jsonschema
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

def current_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class AssessmentMode(str, Enum):
    code_only = "code_only"
    dynamic_only = "dynamic_only"
    full = "full"

class AgentName(str, Enum):
    orchestrator = "orchestrator"
    code_intelligence = "code_intelligence"
    recon = "recon"
    vulnerability_research = "vulnerability_research"
    dynamic_testing = "dynamic_testing"
    verification = "verification"
    remediation = "remediation"

class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    needs_input = "needs_input"
    cancelled = "cancelled"

class WorkflowStatus(str, Enum):
    planned = "planned"
    running = "running"
    blocked = "blocked"
    completed = "completed"
    failed = "failed"

class CredentialRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: str = Field(..., pattern=r"^cred_[a-z0-9_]+$")
    role: str = Field(..., min_length=1)

class ProjectInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    language: Literal["python"] = "python"
    framework_hint: Optional[str] = None

class RepositoryRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: Literal["github", "zip"]
    url: str = Field(..., min_length=1)
    ref: str = Field(..., min_length=1)

class TargetInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(..., min_length=1)
    environment: Literal["sandbox", "staging_approved"]

class OrchestratorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project: ProjectInfo
    target: TargetInfo
    repository: RepositoryRef
    scope_manifest_id: str = Field(..., pattern=r"^scm_[0-9a-f]{8,}$")
    assessment_mode: AssessmentMode
    credential_refs: List[CredentialRef] = Field(..., min_length=2)
    requested_operations: List[Literal["code_analysis", "recon", "dynamic_testing", "remediation"]]

class OrchestratorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    agent: Literal["orchestrator"] = "orchestrator"
    input: OrchestratorInput

class ScopeCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    passed: bool
    detail: str = Field(..., min_length=1)

class ScopeValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valid: bool
    checks: List[ScopeCheck]

class Stage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    agent: AgentName
    depends_on: List[str] = Field(default_factory=list)
    parallel_group: Optional[str] = None
    requires_approval: bool = False

class TaskAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent: AgentName
    stage: str = Field(..., min_length=1)
    depends_on: List[str] = Field(default_factory=list)

class OrchestratorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope_validation: ScopeValidation
    stages: List[Stage]
    task_assignments: List[TaskAssignment]
    workflow_status: WorkflowStatus

class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    retryable: bool
    details: Optional[Dict[str, Any]] = None

class Metrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_ms: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

class OrchestratorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(default_factory=current_utc_iso, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    status: TaskStatus
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    metrics: Metrics
    agent: Literal["orchestrator"] = "orchestrator"
    output: Optional[OrchestratorOutput] = None

    @model_validator(mode="after")
    def validate_status_output_consistency(self):
        if self.status == TaskStatus.succeeded and self.output is None:
            raise ValueError("Output is required when status is succeeded")
        if self.status in [TaskStatus.failed, TaskStatus.blocked] and self.error is None:
            raise ValueError("Error info is required when status is failed or blocked")
        return self

def load_master_schema() -> Dict[str, Any]:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    schema_path = os.path.join(
        repo_root, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_orchestrator_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[OrchestratorRequest]]:
    try:
        req = OrchestratorRequest.model_validate(data)
    except Exception as e:
        return False, f"Pydantic Validation Error: {e}", None

    try:
        master = load_master_schema()
        sub_schema = master["agents"]["orchestrator"]["request"]
        resolver_schema = dict(sub_schema)
        jsonschema.validate(instance=data, schema=resolver_schema)
    except Exception as e:
        return False, f"Master JSON Schema Validation Error: {e}", None

    return True, None, req

def validate_orchestrator_response(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[OrchestratorResponse]]:
    try:
        resp = OrchestratorResponse.model_validate(data)
    except Exception as e:
        return False, f"Pydantic Validation Error: {e}", None

    try:
        master = load_master_schema()
        sub_schema = master["agents"]["orchestrator"]["response"]
        jsonschema.validate(instance=data, schema=sub_schema)
    except Exception as e:
        return False, f"Master JSON Schema Validation Error: {e}", None

    return True, None, resp

def create_error_response(request: OrchestratorRequest, code: str, message: str, retryable: bool, details: Optional[Dict[str, Any]] = None, status: TaskStatus = TaskStatus.failed, partial_output: Optional[OrchestratorOutput] = None) -> OrchestratorResponse:
    return OrchestratorResponse(
        schema_version=request.schema_version,
        correlation_id=request.correlation_id,
        project_id=request.project_id,
        engagement_id=request.engagement_id,
        scan_id=request.scan_id,
        task_id=request.task_id,
        agent_run_id=request.agent_run_id,
        status=status,
        warnings=[],
        error=ErrorInfo(code=code, message=message, retryable=retryable, details=details),
        metrics=Metrics(duration_ms=0, llm_calls=0, input_tokens=0, output_tokens=0),
        agent="orchestrator",
        output=partial_output
    )
