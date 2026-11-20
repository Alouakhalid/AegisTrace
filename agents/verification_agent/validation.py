import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ConfigDict, ValidationError, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class TaskStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    RUNNING = "running"

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class Verdict(str, Enum):
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    REJECTED = "rejected"

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

class Hypothesis(Strict):
    hypothesis_id: str = Field(..., pattern=r"^hyp_[a-z0-9_]+$")
    category: Literal["broken_access_control", "idor", "authn_authz_flaw", "business_logic"]
    title: str
    rationale: str
    endpoint_id: str
    invariant_id: str
    priority: int = Field(ge=1, le=5)
    skill_refs: List[str] = Field(default_factory=list)

class VerificationInput(Strict):
    hypothesis: Hypothesis
    dynamic_result_ref: str
    evidence_ids: List[str]
    invariant_statement: str
    reproduction_runs_requested: int = Field(ge=1, le=10)

class VerificationRequest(Strict):
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    agent: Literal["verification"] = "verification"
    input: VerificationInput

class Reproducibility(Strict):
    runs: int = Field(ge=0)
    reproduced: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "Reproducibility":
        if self.reproduced > self.runs:
            raise ValueError(f"reproduced count ({self.reproduced}) cannot exceed total runs ({self.runs})")
        return self

class Severity(Strict):
    level: SeverityLevel
    rationale: str
    cvss_vector: Optional[str] = None

class Finding(Strict):
    finding_id: str = Field(..., pattern=r"^fnd_[0-9a-f]{8,}$")
    title: str
    severity: Severity
    cwe_id: str
    reproducibility: Reproducibility
    confidence: float = Field(ge=0, le=1)
    supporting_evidence_ids: List[str]

class VerificationOutput(Strict):
    finding_id: Optional[str] = Field(default=None, pattern=r"^fnd_[0-9a-f]{8,}$")
    verdict: Verdict
    reproducibility: Reproducibility
    confidence: float = Field(ge=0, le=1)
    severity: Optional[Severity] = None
    invariant_violated: bool
    supporting_evidence_ids: List[str]
    rejection_reasons: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_section_10_rules(self) -> "VerificationOutput":
        if self.verdict == Verdict.CONFIRMED:
            if not self.invariant_violated:
                raise ValueError("verdict=confirmed requires invariant_violated=True")
            if self.severity is None:
                raise ValueError("verdict=confirmed requires non-null severity")
            if self.reproducibility.reproduced < 1:
                raise ValueError("verdict=confirmed requires reproduced >= 1")
            if self.finding_id is None:
                raise ValueError("verdict=confirmed requires non-null finding_id")
        if self.verdict == Verdict.REJECTED:
            if len(self.rejection_reasons) == 0:
                raise ValueError("verdict=rejected requires non-empty rejection_reasons")
        return self

class VerificationResponse(Strict):
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    agent: Literal["verification"] = "verification"
    status: TaskStatus
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    metrics: Metrics
    output: Optional[VerificationOutput] = None

def validate_verification_request(data: Dict[str, Any]) -> Tuple[bool, Optional[VerificationRequest], Optional[str]]:
    try:
        req = VerificationRequest.model_validate(data)
        return True, req, None
    except ValidationError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, str(e)

def validate_verification_response(data: Dict[str, Any]) -> Tuple[bool, Optional[VerificationResponse], Optional[str]]:
    try:
        resp = VerificationResponse.model_validate(data)
        return True, resp, None
    except ValidationError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, str(e)

def create_error_response(request_data: Dict[str, Any], code: str, message: str, retryable: bool, details: Optional[Dict[str, Any]] = None, warnings: Optional[List[str]] = None, duration_ms: int = 0) -> Dict[str, Any]:
    return {
        "schema_version": request_data.get("schema_version", "1.0.0"),
        "correlation_id": request_data.get("correlation_id", f"cor_{uuid.uuid4().hex[:8]}"),
        "project_id": request_data.get("project_id", f"prj_{uuid.uuid4().hex[:8]}"),
        "engagement_id": request_data.get("engagement_id", f"eng_{uuid.uuid4().hex[:8]}"),
        "scan_id": request_data.get("scan_id", f"scn_{uuid.uuid4().hex[:8]}"),
        "task_id": request_data.get("task_id", f"tsk_{uuid.uuid4().hex[:8]}"),
        "agent_run_id": request_data.get("agent_run_id", f"run_{uuid.uuid4().hex[:8]}"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "verification",
        "status": TaskStatus.FAILED.value,
        "warnings": warnings or [],
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details or {}
        },
        "metrics": {
            "duration_ms": duration_ms,
            "llm_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0
        },
        "output": None
    }
