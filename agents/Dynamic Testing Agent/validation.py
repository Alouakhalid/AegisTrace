import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ConfigDict, ValidationError

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class TaskStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    RUNNING = "running"

class ErrorInfo(Strict):
    code: str
    message: str
    retryable: bool
    details: Optional[Dict[str, Any]] = None

class Metrics(Strict):
    duration_ms: int = Field(ge=0)
    llm_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

class StateCheck(Strict):
    table: str
    key: Dict[str, Any]
    columns: List[str]

class TestPlan(Strict):
    test_plan_id: str = Field(..., pattern=r"^tpl_[a-z0-9_]+$")
    hypothesis_id: str
    method: Literal["paired_identity", "single_identity", "workflow_sequence"]
    steps: List[str]
    identities: List[str]
    expected_secure_behavior: str
    state_checks: List[StateCheck]

class Endpoint(Strict):
    endpoint_id: str = Field(..., pattern=r"^ep_[a-z0-9_]+$")
    method: str
    path: str
    path_params: List[str]
    auth_required: Optional[bool] = None
    source: Literal["openapi", "code_routes", "crawl"]

class Identity(Strict):
    identity_id: str
    role: str
    credential_ref: str = Field(..., pattern=r"^cred_[a-z0-9_]+$")
    owns: Dict[str, Any]

class SandboxConfig(Strict):
    sandbox_id: str = Field(..., pattern=r"^sbx_[0-9a-f]{8,}$")
    base_url: str
    snapshot_enabled: bool
    max_requests: int = Field(..., gt=0)

class DynamicInput(Strict):
    test_plan: TestPlan
    endpoint: Endpoint
    identities: List[Identity]
    sandbox: SandboxConfig
    invariant_id: str

class Envelope(Strict):
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class DynamicRequest(Envelope):
    agent: Literal["dynamic_testing"] = "dynamic_testing"
    input: DynamicInput

class HttpExchange(Strict):
    method: str
    url: str
    status_code: int
    response_excerpt: str
    evidence_id: str = Field(..., pattern=r"^evd_[0-9a-f]{8,}$")

class ExecutedCase(Strict):
    case_id: str
    identity_id: str
    exchange: HttpExchange

class StateDiff(Strict):
    table: str
    key: Dict[str, Any]
    column: str
    before: Any
    after: Any
    snapshot_before_id: str
    snapshot_after_id: str
    evidence_id: str

class DynamicOutput(Strict):
    executed_cases: List[ExecutedCase]
    identity_comparison: str
    state_diffs: List[StateDiff]
    execution_status: Literal["completed", "partial", "aborted"]
    log_ref: str

class DynamicResponse(Envelope):
    status: TaskStatus
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    metrics: Metrics
    agent: Literal["dynamic_testing"] = "dynamic_testing"
    output: Optional[DynamicOutput] = None

def validate_dynamic_request(data: Dict[str, Any]) -> Tuple[bool, Optional[DynamicRequest], Optional[ErrorInfo]]:
    try:
        req = DynamicRequest(**data)
        return True, req, None
    except ValidationError as e:
        err = ErrorInfo(
            code="SCHEMA_VALIDATION_FAILED",
            message=f"Dynamic testing request validation failed: {str(e)}",
            retryable=False,
            details={"errors": e.errors()}
        )
        return False, None, err
    except Exception as e:
        err = ErrorInfo(
            code="UNEXPECTED_VALIDATION_ERROR",
            message=str(e),
            retryable=False
        )
        return False, None, err

def validate_dynamic_response(data: Dict[str, Any]) -> Tuple[bool, Optional[DynamicResponse], Optional[ErrorInfo]]:
    try:
        resp = DynamicResponse(**data)
        return True, resp, None
    except ValidationError as e:
        err = ErrorInfo(
            code="SCHEMA_VALIDATION_FAILED",
            message=f"Dynamic testing response validation failed: {str(e)}",
            retryable=False,
            details={"errors": e.errors()}
        )
        return False, None, err
    except Exception as e:
        err = ErrorInfo(
            code="UNEXPECTED_VALIDATION_ERROR",
            message=str(e),
            retryable=False
        )
        return False, None, err

def create_error_response(
    request_data: Dict[str, Any],
    code: str,
    message: str,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    return {
        "schema_version": request_data.get("schema_version", "1.0.0"),
        "correlation_id": request_data.get("correlation_id", f"cor_{uuid.uuid4().hex[:10]}"),
        "project_id": request_data.get("project_id", f"prj_{uuid.uuid4().hex[:10]}"),
        "engagement_id": request_data.get("engagement_id", f"eng_{uuid.uuid4().hex[:10]}"),
        "scan_id": request_data.get("scan_id", f"scn_{uuid.uuid4().hex[:10]}"),
        "task_id": request_data.get("task_id", f"tsk_{uuid.uuid4().hex[:10]}"),
        "agent_run_id": request_data.get("agent_run_id", f"run_{uuid.uuid4().hex[:10]}"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "failed",
        "warnings": warnings or [],
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details
        },
        "metrics": {
            "duration_ms": 0,
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0
        },
        "agent": "dynamic_testing",
        "output": None
    }
