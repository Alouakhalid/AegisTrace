"""AegisTrace agent contracts, schema_version 1.0.0 (single source of truth)."""
from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

# ---------- enums ----------
class AgentName(str, Enum):
    orchestrator = "orchestrator"; code_intelligence = "code_intelligence"; recon = "recon"
    vulnerability_research = "vulnerability_research"; dynamic_testing = "dynamic_testing"
    verification = "verification"; remediation = "remediation"

class TaskStatus(str, Enum):
    queued = "queued"; running = "running"; succeeded = "succeeded"; failed = "failed"
    blocked = "blocked"; needs_input = "needs_input"; cancelled = "cancelled"

class AssessmentMode(str, Enum):
    code_only = "code_only"; dynamic_only = "dynamic_only"; full = "full"

class VulnCategory(str, Enum):
    broken_access_control = "broken_access_control"; idor = "idor"
    authn_authz_flaw = "authn_authz_flaw"; business_logic = "business_logic"

class Verdict(str, Enum):
    confirmed = "confirmed"; unconfirmed = "unconfirmed"; rejected = "rejected"

class SeverityLevel(str, Enum):
    informational = "informational"; low = "low"; medium = "medium"; high = "high"; critical = "critical"

class RemediationStatus(str, Enum):
    patch_ready_for_review = "patch_ready_for_review"; patch_failed_tests = "patch_failed_tests"
    patch_not_possible = "patch_not_possible"

# ---------- shared ----------
class ErrorInfo(Strict):
    code: str = Field(description="Stable machine-readable error code, e.g. SCOPE_VIOLATION")
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
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", description="ISO 8601 UTC")

class ResponseEnvelope(Envelope):
    status: TaskStatus
    warnings: list[str] = []
    error: Optional[ErrorInfo] = None
    metrics: Metrics

# ---------- 1 Orchestrator ----------
class ProjectInfo(Strict):
    name: str; language: Literal["python"]; framework_hint: Optional[str] = None
class TargetInfo(Strict):
    base_url: str; environment: Literal["sandbox", "staging_approved"]
class RepositoryRef(Strict):
    source_type: Literal["github", "zip"]; url: str; ref: str
class CredentialRef(Strict):
    ref: str = Field(pattern=r"^cred_[a-z0-9_]+$"); role: str
class OrchestratorInput(Strict):
    project: ProjectInfo; target: TargetInfo; repository: RepositoryRef
    scope_manifest_id: str = Field(pattern=r"^scm_[0-9a-f]{8,}$")
    assessment_mode: AssessmentMode
    credential_refs: list[CredentialRef] = Field(min_length=2)
    requested_operations: list[Literal["code_analysis", "recon", "dynamic_testing", "remediation"]]
class OrchestratorRequest(Envelope):
    agent: Literal["orchestrator"] = "orchestrator"; input: OrchestratorInput

class ScopeCheck(Strict):
    name: str; passed: bool; detail: str
class ScopeValidation(Strict):
    valid: bool; checks: list[ScopeCheck]
class Stage(Strict):
    name: str; agent: AgentName; depends_on: list[str]; parallel_group: Optional[str] = None
    requires_approval: bool = False
class TaskAssignment(Strict):
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$"); agent: AgentName; stage: str; depends_on: list[str]
class OrchestratorOutput(Strict):
    scope_validation: ScopeValidation; stages: list[Stage]
    task_assignments: list[TaskAssignment]
    workflow_status: Literal["planned", "running", "blocked", "completed", "failed"]
class OrchestratorResponse(ResponseEnvelope):
    agent: Literal["orchestrator"] = "orchestrator"; output: Optional[OrchestratorOutput] = None

# ---------- 2 Code Intelligence ----------
class RepoCheckout(Strict):
    path_ref: str; commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")
class ScanConfig(Strict):
    max_files: int = Field(gt=0); include_globs: list[str]; enable_semgrep: bool
class CodeIntelInput(Strict):
    repository: RepoCheckout; source_language: Literal["python"]
    framework_hints: list[str]; scan_config: ScanConfig
class CodeIntelRequest(Envelope):
    agent: Literal["code_intelligence"] = "code_intelligence"; input: CodeIntelInput

class RepoStructure(Strict):
    files_analyzed: int; frameworks: list[str]; entry_points: list[str]
class Route(Strict):
    route_id: str = Field(pattern=r"^rte_[a-z0-9_]+$"); method: str; path: str; handler: str
    file: str; line: int; auth_required: bool; authz_checks: list[str]
class SecurityMechanism(Strict):
    name: str; kind: Literal["authentication", "authorization"]; location: str; description: str
class DbModel(Strict):
    name: str; table: str; owner_field: Optional[str] = None; file: str
class CandidateInvariant(Strict):
    invariant_id: str = Field(pattern=r"^inv_[a-z0-9_]+$"); statement: str
    kind: Literal["ownership", "role_restriction", "state_transition", "authentication_required"]
    applies_to_route_ids: list[str]; source: Literal["code", "declared_policy"]
    confidence: float = Field(ge=0, le=1)
class CodeIntelOutput(Strict):
    repository_structure: RepoStructure; routes: list[Route]
    auth_mechanisms: list[SecurityMechanism]; db_models: list[DbModel]
    code_graph_ref: str; candidate_invariants: list[CandidateInvariant]
class CodeIntelResponse(ResponseEnvelope):
    agent: Literal["code_intelligence"] = "code_intelligence"; output: Optional[CodeIntelOutput] = None

# ---------- 3 Recon ----------
class ScopeSummary(Strict):
    allowed_hosts: list[str]; allowed_methods: list[str]; forbidden_paths: list[str]
class ResearchConfig(Strict):
    enabled: bool; max_queries: int = Field(ge=0); search_depth: Literal["basic", "advanced"]
class ReconInput(Strict):
    scope: ScopeSummary; api_spec_ref: Optional[str] = None
    technology_hints: list[str]; research: ResearchConfig
class ReconRequest(Envelope):
    agent: Literal["recon"] = "recon"; input: ReconInput

class Endpoint(Strict):
    endpoint_id: str = Field(pattern=r"^ep_[a-z0-9_]+$"); method: str; path: str
    path_params: list[str]; auth_required: Optional[bool] = None
    source: Literal["openapi", "code_routes", "crawl"]
class Technology(Strict):
    name: str; version: Optional[str] = None; confidence: float = Field(ge=0, le=1); evidence: str
class IntelRef(Strict):
    ref_id: str; title: str; url: str; retrieved_at: str; source_type: Literal["vendor", "nvd", "owasp", "other"]
    relevance: float = Field(ge=0, le=1); trusted: Literal[False] = False
class ReconOutput(Strict):
    endpoints: list[Endpoint]; technologies: list[Technology]; attack_surface_ref: str
    intel_refs: list[IntelRef]
class ReconResponse(ResponseEnvelope):
    agent: Literal["recon"] = "recon"; output: Optional[ReconOutput] = None

# ---------- 4 Vulnerability Research ----------
class SkillHit(Strict):
    skill: str; source_commit: str; score: float
class ResearchInput(Strict):
    code_intel_ref: str; recon_ref: str; invariant_ids: list[str]; skill_hits: list[SkillHit]
class ResearchRequest(Envelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"; input: ResearchInput

class StateCheck(Strict):
    table: str; key: dict; columns: list[str]
class Hypothesis(Strict):
    hypothesis_id: str = Field(pattern=r"^hyp_[a-z0-9_]+$"); category: VulnCategory; title: str
    rationale: str; endpoint_id: str; invariant_id: str; priority: int = Field(ge=1, le=5)
    skill_refs: list[str]
class TestPlan(Strict):
    test_plan_id: str = Field(pattern=r"^tpl_[a-z0-9_]+$"); hypothesis_id: str
    method: Literal["paired_identity", "single_identity", "workflow_sequence"]
    steps: list[str]; identities: list[str]; expected_secure_behavior: str
    state_checks: list[StateCheck]
class ResearchOutput(Strict):
    hypotheses: list[Hypothesis]; test_plans: list[TestPlan]
class ResearchResponse(ResponseEnvelope):
    agent: Literal["vulnerability_research"] = "vulnerability_research"; output: Optional[ResearchOutput] = None

# ---------- 5 Dynamic Testing ----------
class Identity(Strict):
    identity_id: str; role: str; credential_ref: str = Field(pattern=r"^cred_[a-z0-9_]+$"); owns: dict
class SandboxConfig(Strict):
    sandbox_id: str = Field(pattern=r"^sbx_[0-9a-f]{8,}$"); base_url: str
    snapshot_enabled: bool; max_requests: int = Field(gt=0)
class DynamicInput(Strict):
    test_plan: TestPlan; endpoint: Endpoint; identities: list[Identity]
    sandbox: SandboxConfig; invariant_id: str
class DynamicRequest(Envelope):
    agent: Literal["dynamic_testing"] = "dynamic_testing"; input: DynamicInput

class HttpExchange(Strict):
    method: str; url: str; status_code: int; response_excerpt: str; evidence_id: str = Field(pattern=r"^evd_[0-9a-f]{8,}$")
class ExecutedCase(Strict):
    case_id: str; identity_id: str; exchange: HttpExchange
class StateDiff(Strict):
    table: str; key: dict; column: str; before: object; after: object
    snapshot_before_id: str; snapshot_after_id: str; evidence_id: str
class DynamicOutput(Strict):
    executed_cases: list[ExecutedCase]; identity_comparison: str
    state_diffs: list[StateDiff]; execution_status: Literal["completed", "partial", "aborted"]
    log_ref: str
class DynamicResponse(ResponseEnvelope):
    agent: Literal["dynamic_testing"] = "dynamic_testing"; output: Optional[DynamicOutput] = None

# ---------- 6 Verification ----------
class VerificationInput(Strict):
    hypothesis: Hypothesis; dynamic_result_ref: str; evidence_ids: list[str]
    invariant_statement: str; reproduction_runs_requested: int = Field(ge=1, le=10)
class VerificationRequest(Envelope):
    agent: Literal["verification"] = "verification"; input: VerificationInput

class Reproducibility(Strict):
    runs: int; reproduced: int
class Severity(Strict):
    level: SeverityLevel; rationale: str; cvss_vector: Optional[str] = None
class VerificationOutput(Strict):
    finding_id: Optional[str] = Field(default=None, pattern=r"^fnd_[0-9a-f]{8,}$")
    verdict: Verdict; reproducibility: Reproducibility; confidence: float = Field(ge=0, le=1)
    severity: Optional[Severity] = None; invariant_violated: bool
    supporting_evidence_ids: list[str]; rejection_reasons: list[str] = []
class VerificationResponse(ResponseEnvelope):
    agent: Literal["verification"] = "verification"; output: Optional[VerificationOutput] = None

# ---------- 7 Remediation ----------
class SourceRef(Strict):
    file: str; start_line: int; end_line: int
class RemediationInput(Strict):
    finding_id: str = Field(pattern=r"^fnd_[0-9a-f]{8,}$"); source_refs: list[SourceRef]
    verification_evidence_ids: list[str]; test_environment: SandboxConfig
    original_test_plan_id: str; max_attempts: int = Field(ge=1, le=3)
class RemediationRequest(Envelope):
    agent: Literal["remediation"] = "remediation"; input: RemediationInput

class RootCause(Strict):
    summary: str; files: list[str]
class PatchInfo(Strict):
    patch_id: str = Field(pattern=r"^pat_[0-9a-f]{8,}$"); branch: str; diff_ref: str; changed_files: list[str]
class TestCounts(Strict):
    total: int; passed: int; failed: int
class RemediationTests(Strict):
    unit: TestCounts; integration: TestCounts; regression: TestCounts
class ReplayResult(Strict):
    original_scenario_replayed: bool; vulnerability_still_reproducible: bool; evidence_id: str
class RemediationOutput(Strict):
    root_cause: RootCause; patch: Optional[PatchInfo] = None; tests: RemediationTests
    replay: ReplayResult; remediation_status: RemediationStatus
    requires_human_approval: Literal[True] = True
class RemediationResponse(ResponseEnvelope):
    agent: Literal["remediation"] = "remediation"; output: Optional[RemediationOutput] = None

PAIRS = {
 "orchestrator": (OrchestratorRequest, OrchestratorResponse),
 "code_intelligence": (CodeIntelRequest, CodeIntelResponse),
 "recon": (ReconRequest, ReconResponse),
 "vulnerability_research": (ResearchRequest, ResearchResponse),
 "dynamic_testing": (DynamicRequest, DynamicResponse),
 "verification": (VerificationRequest, VerificationResponse),
 "remediation": (RemediationRequest, RemediationResponse),
}
