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

class RemediationStatus(str, Enum):
    PATCH_READY_FOR_REVIEW = "patch_ready_for_review"
    PATCH_FAILED_TESTS = "patch_failed_tests"
    PATCH_NOT_POSSIBLE = "patch_not_possible"

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

class SandboxConfig(Strict):
    sandbox_id: str = Field(..., pattern=r"^sbx_[0-9a-f]{8,}$")
    base_url: str
    snapshot_enabled: bool
    max_requests: int = Field(..., ge=1)

class SourceRef(Strict):
    file: str
    start_line: int
    end_line: int

class RemediationInput(Strict):
    finding_id: str = Field(..., pattern=r"^fnd_[0-9a-f]{8,}$")
    source_refs: List[SourceRef]
    verification_evidence_ids: List[str]
    test_environment: SandboxConfig
    original_test_plan_id: str
    max_attempts: int = Field(..., ge=1, le=3)

class RemediationRequest(Strict):
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    agent: Literal["remediation"] = "remediation"
    input: RemediationInput

class RootCause(Strict):
    summary: str
    files: List[str]

class PatchInfo(Strict):
    patch_id: str = Field(..., pattern=r"^pat_[0-9a-f]{8,}$")
    branch: str
    diff_ref: str
    changed_files: List[str]

class TestCounts(Strict):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_sum(self) -> "TestCounts":
        if self.passed + self.failed != self.total:
            raise ValueError(f"Sum of passed ({self.passed}) and failed ({self.failed}) must equal total ({self.total})")
        return self

class RemediationTests(Strict):
    unit: TestCounts
    integration: TestCounts
    regression: TestCounts

class ReplayResult(Strict):
    original_scenario_replayed: bool
    vulnerability_still_reproducible: bool
    evidence_id: str

class RemediationOutput(Strict):
    root_cause: RootCause
    patch: Optional[PatchInfo] = None
    tests: RemediationTests
    replay: ReplayResult
    remediation_status: RemediationStatus
    requires_human_approval: Literal[True] = True

    @model_validator(mode="after")
    def validate_remediation_invariants(self) -> "RemediationOutput":
        if self.remediation_status == RemediationStatus.PATCH_READY_FOR_REVIEW:
            if self.tests.unit.failed > 0 or self.tests.integration.failed > 0 or self.tests.regression.failed > 0:
                raise ValueError("remediation_status=patch_ready_for_review requires failed=0 in all test suites")
            if self.replay.vulnerability_still_reproducible is True:
                raise ValueError("remediation_status=patch_ready_for_review requires vulnerability_still_reproducible=false")
            if self.patch is None:
                raise ValueError("remediation_status=patch_ready_for_review requires non-null patch")
            target_branch = self.patch.branch.lower()
            if target_branch in ["main", "master", "develop", "default", "prod"] or target_branch.startswith("main"):
                raise ValueError(f"The patch never targets the default branch: '{self.patch.branch}'")
        return self

class RemediationResponse(Strict):
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(..., pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(..., pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(..., pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(..., pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(..., pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(..., pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    agent: Literal["remediation"] = "remediation"
    status: TaskStatus
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    metrics: Metrics
    output: Optional[RemediationOutput] = None

def validate_remediation_request(data: Dict[str, Any]) -> Tuple[bool, Optional[RemediationRequest], Optional[str]]:
    try:
        req = RemediationRequest.model_validate(data)
        return True, req, None
    except ValidationError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, str(e)

def validate_remediation_response(data: Dict[str, Any]) -> Tuple[bool, Optional[RemediationResponse], Optional[str]]:
    try:
        resp = RemediationResponse.model_validate(data)
        return True, resp, None
    except ValidationError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, str(e)

def create_error_response(
    request_data: Dict[str, Any],
    code: str,
    message: str,
    retryable: bool,
    details: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    duration_ms: int = 0
) -> Dict[str, Any]:
    return {
        "schema_version": request_data.get("schema_version", "1.0.0"),
        "correlation_id": request_data.get("correlation_id", f"cor_{uuid.uuid4().hex[:8]}"),
        "project_id": request_data.get("project_id", f"prj_{uuid.uuid4().hex[:8]}"),
        "engagement_id": request_data.get("engagement_id", f"eng_{uuid.uuid4().hex[:8]}"),
        "scan_id": request_data.get("scan_id", f"scn_{uuid.uuid4().hex[:8]}"),
        "task_id": request_data.get("task_id", f"tsk_{uuid.uuid4().hex[:8]}"),
        "agent_run_id": request_data.get("agent_run_id", f"run_{uuid.uuid4().hex[:8]}"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "remediation",
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
