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

class SkillHit(StrictModel):
    skill: str
    source_commit: str
    score: float

class ResearchInput(StrictModel):
    code_intel_ref: str
    recon_ref: str
    invariant_ids: List[str]
    skill_hits: List[SkillHit] = Field(default_factory=list)

class ResearchRequest(Envelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"
    input: ResearchInput

class StateCheck(StrictModel):
    table: str
    key: Dict[str, Any]
    columns: List[str]

class Hypothesis(StrictModel):
    hypothesis_id: str = Field(pattern=r"^hyp_[a-z0-9_]+$")
    category: Literal["broken_access_control", "idor", "authn_authz_flaw", "business_logic"]
    title: str
    rationale: str
    endpoint_id: str
    invariant_id: str
    priority: int = Field(ge=1, le=5)
    skill_refs: List[str] = Field(default_factory=list)

class TestPlan(StrictModel):
    test_plan_id: str = Field(pattern=r"^tpl_[a-z0-9_]+$")
    hypothesis_id: str
    method: Literal["paired_identity", "single_identity", "workflow_sequence"]
    steps: List[str]
    identities: List[str]
    expected_secure_behavior: str
    state_checks: List[StateCheck]

class ResearchOutput(StrictModel):
    hypotheses: List[Hypothesis]
    test_plans: List[TestPlan]

class ResearchResponse(ResponseEnvelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"
    output: Optional[ResearchOutput] = None

def validate_research_request(data: dict) -> Tuple[bool, Optional[ResearchRequest], Optional[ErrorInfo]]:
    try:
        req = ResearchRequest.model_validate(data)
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

def validate_research_response(data: dict) -> Tuple[bool, Optional[ResearchResponse], Optional[ErrorInfo]]:
    try:
        res = ResearchResponse.model_validate(data)
        if res.output:
            hyp_ids = {h.hypothesis_id for h in res.output.hypotheses}
            for plan in res.output.test_plans:
                if plan.hypothesis_id not in hyp_ids:
                    return False, None, ErrorInfo(
                        code="PLAN_ORPHANED_HYPOTHESIS",
                        message=f"Test plan '{plan.test_plan_id}' references unknown hypothesis '{plan.hypothesis_id}'",
                        retryable=False
                    )
                if plan.method == "paired_identity" and len(plan.identities) < 2:
                    return False, None, ErrorInfo(
                        code="PAIRED_IDENTITY_INSUFFICIENT",
                        message=f"Test plan '{plan.test_plan_id}' using paired_identity requires at least 2 identities",
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
        "created_at": req_dict.get("created_at", "2026-11-17T09:31:10Z"),
        "agent": "vulnerability_research",
        "status": "failed",
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
