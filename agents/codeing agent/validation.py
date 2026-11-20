import uuid
import datetime
from enum import Enum
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    needs_input = "needs_input"
    cancelled = "cancelled"

class ErrorInfo(Strict):
    code: str = Field(description="Machine-readable error code")
    message: str
    retryable: bool
    details: Optional[dict] = None

class Metrics(Strict):
    duration_ms: int = Field(ge=0)
    llm_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

class Envelope(Strict):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class ResponseEnvelope(Envelope):
    status: TaskStatus
    warnings: List[str] = []
    error: Optional[ErrorInfo] = None
    metrics: Metrics

class RepoCheckout(Strict):
    path_ref: str
    commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")

class ScanConfig(Strict):
    max_files: int = Field(gt=0)
    include_globs: List[str]
    enable_semgrep: bool

class CodeIntelInput(Strict):
    repository: RepoCheckout
    source_language: Literal["python"]
    framework_hints: List[str]
    scan_config: ScanConfig

class CodeIntelRequest(Envelope):
    agent: Literal["code_intelligence"] = "code_intelligence"
    input: CodeIntelInput

class RepoStructure(Strict):
    files_analyzed: int
    frameworks: List[str]
    entry_points: List[str]

class Route(Strict):
    route_id: str = Field(pattern=r"^rte_[a-z0-9_]+$")
    method: str
    path: str
    handler: str
    file: str
    line: int
    auth_required: bool
    authz_checks: List[str]

class SecurityMechanism(Strict):
    name: str
    kind: Literal["authentication", "authorization"]
    location: str
    description: str

class DbModel(Strict):
    name: str
    table: str
    owner_field: Optional[str] = None
    file: str

class CandidateInvariant(Strict):
    invariant_id: str = Field(pattern=r"^inv_[a-z0-9_]+$")
    statement: str
    kind: Literal["ownership", "role_restriction", "state_transition", "authentication_required"]
    applies_to_route_ids: List[str]
    source: Literal["code", "declared_policy"]
    confidence: float = Field(ge=0, le=1)

class CodeIntelOutput(Strict):
    repository_structure: RepoStructure
    routes: List[Route]
    auth_mechanisms: List[SecurityMechanism]
    db_models: List[DbModel]
    code_graph_ref: str
    candidate_invariants: List[CandidateInvariant]

class CodeIntelResponse(ResponseEnvelope):
    agent: Literal["code_intelligence"] = "code_intelligence"
    output: Optional[CodeIntelOutput] = None

class CodeIntelValidationError(Exception):
    def __init__(self, message: str, code: str = "SCHEMA_VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

def validate_code_intel_request(payload: Dict[str, Any]) -> CodeIntelRequest:
    try:
        return CodeIntelRequest(**payload)
    except ValidationError as e:
        raise CodeIntelValidationError(
            message=f"Request validation failed: {str(e)}",
            code="REQUEST_SCHEMA_INVALID",
            details={"errors": e.errors()}
        )

def validate_business_invariants(output_obj: CodeIntelOutput) -> List[str]:
    violations = []
    routes = output_obj.routes
    invariants = output_obj.candidate_invariants

    route_ids = [r.route_id for r in routes]
    seen_route_ids = set()
    for rid in route_ids:
        if rid in seen_route_ids:
            violations.append(f"Duplicate route_id discovered: {rid}")
        seen_route_ids.add(rid)

    valid_route_set = set(route_ids)
    for inv in invariants:
        for target_rid in inv.applies_to_route_ids:
            if target_rid not in valid_route_set:
                violations.append(
                    f"Invariant '{inv.invariant_id}' references non-existent route_id: '{target_rid}'"
                )

    if not output_obj.code_graph_ref.startswith("graph://"):
        violations.append(
            f"Invalid code_graph_ref format: '{output_obj.code_graph_ref}'. Must start with 'graph://'"
        )

    for inv in invariants:
        if not (0.0 <= inv.confidence <= 1.0):
            violations.append(
                f"Invariant '{inv.invariant_id}' confidence {inv.confidence} outside valid range [0.0, 1.0]"
            )

    return violations

def validate_code_intel_response(payload: Dict[str, Any]) -> CodeIntelResponse:
    try:
        response_obj = CodeIntelResponse(**payload)
    except ValidationError as e:
        raise CodeIntelValidationError(
            message=f"Response schema validation failed: {str(e)}",
            code="RESPONSE_SCHEMA_INVALID",
            details={"errors": e.errors()}
        )

    if response_obj.status == TaskStatus.succeeded and response_obj.output:
        violations = validate_business_invariants(response_obj.output)
        if violations:
            raise CodeIntelValidationError(
                message=f"Business invariant integrity failed: {'; '.join(violations)}",
                code="INVARIANT_INTEGRITY_VIOLATION",
                details={"violations": violations}
            )

    return response_obj

def create_error_response_payload(
    error_code: str,
    error_message: str,
    request_payload: Dict[str, Any],
    duration_ms: int = 0
) -> Dict[str, Any]:
    return {
        "schema_version": request_payload.get("schema_version", "1.0.0"),
        "correlation_id": request_payload.get("correlation_id", f"cor_{uuid.uuid4().hex[:8]}"),
        "project_id": request_payload.get("project_id", f"prj_{uuid.uuid4().hex[:8]}"),
        "engagement_id": request_payload.get("engagement_id", f"eng_{uuid.uuid4().hex[:8]}"),
        "scan_id": request_payload.get("scan_id", f"scn_{uuid.uuid4().hex[:8]}"),
        "task_id": request_payload.get("task_id", f"tsk_{uuid.uuid4().hex[:8]}"),
        "agent_run_id": f"run_{uuid.uuid4().hex[:8]}",
        "created_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "code_intelligence",
        "status": "failed",
        "warnings": [],
        "error": {
            "code": error_code,
            "message": error_message,
            "retryable": False,
            "details": None
        },
        "metrics": {
            "duration_ms": duration_ms,
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0
        },
        "output": None
    }
