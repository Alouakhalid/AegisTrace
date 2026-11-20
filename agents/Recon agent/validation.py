import fnmatch
from typing import List, Optional, Literal, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict, ValidationError

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ErrorInfo(StrictModel):
    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error message")
    retryable: bool = Field(description="Whether the Orchestrator may retry")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured error context")

class Metrics(StrictModel):
    duration_ms: int = Field(ge=0, description="Wall-clock time of the run")
    llm_calls: int = Field(ge=0, description="Number of model calls made")
    input_tokens: int = Field(ge=0, description="Prompt tokens consumed")
    output_tokens: int = Field(ge=0, description="Completion tokens produced")

class Envelope(StrictModel):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class ResponseEnvelope(Envelope):
    status: Literal["succeeded", "failed", "blocked", "needs_input", "running", "queued", "cancelled"]
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    metrics: Metrics

class ScopeSummary(StrictModel):
    allowed_hosts: List[str]
    allowed_methods: List[str]
    forbidden_paths: List[str]

class ResearchConfig(StrictModel):
    enabled: bool
    max_queries: int = Field(ge=0)
    search_depth: Literal["basic", "advanced"]

class ReconInput(StrictModel):
    scope: ScopeSummary
    api_spec_ref: Optional[str] = None
    technology_hints: List[str] = Field(default_factory=list)
    research: ResearchConfig

class ReconRequest(Envelope):
    agent: Literal["recon"] = "recon"
    input: ReconInput

class Endpoint(StrictModel):
    endpoint_id: str = Field(pattern=r"^ep_[a-z0-9_]+$")
    method: str
    path: str
    path_params: List[str] = Field(default_factory=list)
    auth_required: Optional[bool] = None
    source: Literal["openapi", "code_routes", "crawl"]

class Technology(StrictModel):
    name: str
    version: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str

class IntelRef(StrictModel):
    ref_id: str
    title: str
    url: str
    retrieved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    source_type: Literal["vendor", "nvd", "owasp", "other"]
    relevance: float = Field(ge=0.0, le=1.0)
    trusted: Literal[False] = False

class ReconOutput(StrictModel):
    endpoints: List[Endpoint]
    technologies: List[Technology]
    attack_surface_ref: str
    intel_refs: List[IntelRef] = Field(default_factory=list)

class ReconResponse(ResponseEnvelope):
    agent: Literal["recon"] = "recon"
    output: Optional[ReconOutput] = None

def check_scope_gate(path: str, method: str, scope: ScopeSummary) -> Tuple[bool, Optional[str]]:
    upper_method = method.upper()
    allowed_methods = [m.upper() for m in scope.allowed_methods]
    if upper_method not in allowed_methods:
        return False, f"Method '{upper_method}' is not in allowed_methods {allowed_methods}"
    norm_path = path if path.startswith("/") else f"/{path}"
    for forbidden in scope.forbidden_paths:
        pattern = forbidden.rstrip("/")
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if norm_path.startswith(prefix) or fnmatch.fnmatch(norm_path, pattern):
                return False, f"Path '{norm_path}' matches forbidden pattern '{forbidden}'"
        else:
            if norm_path == pattern or norm_path.startswith(f"{pattern}/"):
                return False, f"Path '{norm_path}' matches forbidden path '{forbidden}'"
    return True, None

def validate_recon_request(data: dict) -> Tuple[bool, Optional[ReconRequest], Optional[ErrorInfo]]:
    try:
        req = ReconRequest.model_validate(data)
        return True, req, None
    except ValidationError as e:
        err = ErrorInfo(
            code="SCHEMA_VALIDATION_FAILED",
            message=str(e),
            retryable=False,
            details={"errors": e.errors()}
        )
        return False, None, err
    except Exception as ex:
        err = ErrorInfo(
            code="REQUEST_MALFORMED",
            message=str(ex),
            retryable=False,
            details=None
        )
        return False, None, err

def validate_recon_response(data: dict) -> Tuple[bool, Optional[ReconResponse], Optional[ErrorInfo]]:
    try:
        res = ReconResponse.model_validate(data)
        if res.output:
            for intel in res.output.intel_refs:
                if intel.trusted is not False:
                    return False, None, ErrorInfo(
                        code="UNTRUSTED_INTEL_RULE_VIOLATION",
                        message="intel_refs.trusted must strictly be False",
                        retryable=False
                    )
        return True, res, None
    except ValidationError as e:
        err = ErrorInfo(
            code="RESPONSE_VALIDATION_FAILED",
            message=str(e),
            retryable=False,
            details={"errors": e.errors()}
        )
        return False, None, err
    except Exception as ex:
        err = ErrorInfo(
            code="RESPONSE_MALFORMED",
            message=str(ex),
            retryable=False,
            details=None
        )
        return False, None, err

def create_error_response(req_dict: dict, code: str, message: str, retryable: bool, details: Optional[dict] = None) -> dict:
    return {
        "schema_version": req_dict.get("schema_version", "1.0.0"),
        "correlation_id": req_dict.get("correlation_id", "cor_000000000000"),
        "project_id": req_dict.get("project_id", "prj_000000000000"),
        "engagement_id": req_dict.get("engagement_id", "eng_000000000000"),
        "scan_id": req_dict.get("scan_id", "scn_000000000000"),
        "task_id": req_dict.get("task_id", "tsk_000000000000"),
        "agent_run_id": req_dict.get("agent_run_id", "run_000000000000"),
        "created_at": req_dict.get("created_at", "2026-11-17T09:30:00Z"),
        "agent": "recon",
        "status": "blocked" if code == "SCOPE_VIOLATION" else "failed",
        "warnings": [],
        "output": None,
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
        }
    }
