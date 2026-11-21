from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default="")
    repository_url: Optional[str] = Field(default="")
    branch: Optional[str] = Field(default="main")
    local_path: Optional[str] = Field(default="")
    project_type: Optional[str] = Field(default="web_api")

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    repository_url: Optional[str] = None
    branch: Optional[str] = "main"
    local_path: Optional[str] = None
    project_type: str
    created_at: str
    last_scan_at: Optional[str] = None
    total_scans: int = 0
    open_findings: int = 0
    security_score: Optional[int] = None

#: The orchestrator contract only accepts these three modes. The HTTP layer
#: accepted any string, so an "unknown" mode used to pass request validation and
#: then blow up inside the pipeline at 15% progress — after the repository had
#: already been cloned. Normalising at the edge keeps every downstream stage and
#: the engagement row consistent.
ASSESSMENT_MODES = ("code_only", "dynamic_only", "full")

_ASSESSMENT_MODE_ALIASES = {
    "source": "code_only",
    "source_only": "code_only",
    "source-only": "code_only",
    "static": "code_only",
    "static_only": "code_only",
    "code": "code_only",
    "sast": "code_only",
    "dynamic": "dynamic_only",
    "dynamic-only": "dynamic_only",
    "dast": "dynamic_only",
    "runtime": "dynamic_only",
    "live": "dynamic_only",
    "complete": "full",
    "all": "full",
    "custom": "full",
    "": "full",
}


def normalize_assessment_mode(value: str) -> str:
    """Map a user-supplied mode onto the orchestrator contract enum."""
    raw = str(value or "").strip().lower()
    if raw in ASSESSMENT_MODES:
        return raw
    mapped = _ASSESSMENT_MODE_ALIASES.get(raw)
    if mapped:
        return mapped
    raise ValueError(
        f"Unsupported assessment_mode '{value}'. Use one of: {', '.join(ASSESSMENT_MODES)}."
    )


class ScanCreateRequest(BaseModel):
    project_id: Optional[str] = None
    project_name: Optional[str] = "Default Assessment"
    target_type: str = Field(default="source_and_url")
    assessment_mode: str = Field(default="full")
    source_path: Optional[str] = Field(default="")
    github_url: Optional[str] = Field(default="")
    github_branch: Optional[str] = Field(default="main")
    web_target_url: Optional[str] = Field(default="")
    openapi_spec_url: Optional[str] = Field(default="")
    allowed_hosts: List[str] = Field(default_factory=lambda: ["127.0.0.1", "localhost"])
    excluded_paths: List[str] = Field(default_factory=list)
    auth_token: Optional[str] = Field(default=None)
    test_user_roles: List[str] = Field(default_factory=lambda: ["admin", "buyer_a", "buyer_b"])
    active_testing_consented: bool = Field(default=True)

    @field_validator("assessment_mode")
    @classmethod
    def _normalize_mode(cls, v: str) -> str:
        return normalize_assessment_mode(v)

class ScanProgressEvent(BaseModel):
    scan_id: str
    stage: str
    agent_name: str
    status: str
    progress_percentage: int
    message: str
    timestamp: str

class ForensicEvidenceResponse(BaseModel):
    id: str
    finding_id: str
    title: str
    timestamp: str
    http_method: str
    http_url: str
    http_status: int
    request_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[str] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    response_body: Optional[str] = None
    identity_used: Optional[str] = None
    target_resource_owner: Optional[str] = None
    db_mutation_trapped: bool = False
    table_name: Optional[str] = None
    row_id: Optional[str] = None
    state_before: Optional[str] = None
    state_after: Optional[str] = None
    sha256_snapshot_hash: Optional[str] = None
    reproduction_attempts: int = 3
    reproduction_successes: int = 3

class FindingResponse(BaseModel):
    id: str
    scan_id: str
    title: str
    severity: str
    cvss_score: float
    cvss_vector: str
    cwe_id: str
    cwe_name: str
    status: str
    confidence: float
    endpoint: str
    http_method: str
    affected_file: Optional[str] = None
    line_number: Optional[int] = None
    root_cause: str
    reproduction_summary: str
    verification_verdict: str
    evidence: Optional[ForensicEvidenceResponse] = None
    created_at: str

class PatchResponse(BaseModel):
    id: str
    scan_id: str
    finding_id: str
    finding_title: str
    status: str
    target_file: str
    original_code_hash: str
    patched_code_hash: str
    unified_diff: str
    unit_tests_pass: bool = True
    integration_tests_pass: bool = True
    exploit_closure_verified: bool = True
    regression_tests_pass: bool = True
    approval_status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str

class ApprovalActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|defer)$")
    reviewer: str = Field(default="Security Engineer")
    notes: Optional[str] = Field(default="")
    expected_patch_hash: Optional[str] = None

class ScanStatusResponse(BaseModel):
    scan_id: str
    project_id: str
    project_name: str
    status: str
    current_stage: str
    active_agent: str
    progress_percentage: int
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    verified_findings: int = 0
    resolved_findings: int = 0
    pending_approvals: int = 0
    log_messages: List[str] = Field(default_factory=list)

class SkillResponse(BaseModel):
    id: str
    name: str
    category: str
    version: str
    description: str
    supported_cwes: List[str]
    compatible_agents: List[str]
    active: bool = True

class BenchmarkMetricResponse(BaseModel):
    agent_name: str
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    reproduction_rate: float
    patch_success_rate: float
    total_evaluations: int

class OverviewStatsResponse(BaseModel):
    total_projects: int
    total_scans: int
    total_findings: int
    confirmed_findings: int
    resolved_findings: int
    critical_findings: int
    security_score: Optional[int] = None
    pending_approvals: int
    active_skills: int
    system_status: str

class ReportResponse(BaseModel):
    scan_id: str
    report_type: str
    generated_at: str
    executive_summary: str
    findings_count: int
    resolved_count: int
    compliance_assessment: Dict[str, Any]
    content_json: Dict[str, Any]

class RepoAnalyzeRequest(BaseModel):
    repository_url: str
    auth_token: Optional[str] = None

class AssessmentCreateRequest(BaseModel):
    repository_url: str
    project_name: Optional[str] = None
    assessment_mode: str = "full"
    selected_categories: Optional[List[str]] = None
    target_dir_filter: Optional[str] = None
    instructions: Optional[str] = None
    auth_token: Optional[str] = None
    active_testing_consented: bool = True

    @field_validator("assessment_mode")
    @classmethod
    def _normalize_mode(cls, v: str) -> str:
        return normalize_assessment_mode(v)

class TavilyTestRequest(BaseModel):
    query: Optional[str] = "FastAPI security advisory"
    max_results: Optional[int] = 3
