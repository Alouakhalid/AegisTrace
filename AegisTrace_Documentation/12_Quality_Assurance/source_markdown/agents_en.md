# 1. Overview and Reading Guide

This document specifies how the seven official AegisTrace agents cooperate: responsibilities, hand-offs, control loops, failure handling, human approval checkpoints and the exact JSON contracts they exchange. The Pydantic models in Section 4 and in each agent chapter are the **single source of truth**; the JSON Schemas file `AegisTrace_Agent_JSON_Schemas.json` is exported from them, and every example JSON in this document was validated against those models.

**Build order is not runtime order.** Agents are implemented in the order given in the Implementation Roadmap, but at runtime the Orchestrator schedules them by dependency, not by implementation order.

**Scenario used in all examples.** An e-commerce API (ShopLite). Buyer A owns Order 100, buyer B owns Order 200. B sends `PATCH /api/v1/orders/100`; the API returns 403 yet the order's `shipping_address` changes. The same identifiers flow through all seven agents.

# 2. Architecture and Communication

## 2.1 Seven agents

![Seven agents](../diagrams/d02_agents.svg)

## 2.2 Communication model

Agents never call each other directly. The Orchestrator is the only router: it sends a validated request, receives a validated response, persists both in `agent_messages`, and decides what runs next. This keeps scope enforcement, retries and audit logging in one place.

![Hub and spoke communication](../diagrams/d04c_comm.svg)

Every message carries the shared envelope (ids, `schema_version`, `created_at`). The persisted form of a message is an `agent_messages` row:

```json
{
  "id": "msg_0192f450",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "correlation_id": "cor_0192f230",
  "from_agent": "orchestrator",
  "to_agent": "verification",
  "message_type": "request",
  "schema_version": "1.0.0",
  "payload": { "...": "the VerificationRequest JSON" },
  "created_at": "2026-11-17T09:32:10Z"
}
```

# 3. Workflow, Dependencies and Control Loops

## 3.1 End-to-end sequence

![Agent sequence](../diagrams/d05_sequence.svg)

## 3.2 Task dependencies

![Task dependency graph](../diagrams/d06_taskdeps.svg)

## 3.3 Parallelism and loops (exact conditions)

| Pattern | Condition | Bound |
|---|---|---|
| Parallel Recon | Scope validation passed; Recon needs only scope and API spec | Code Intelligence and Recon start together (`parallel_group=g1`) |
| Research requests code context | A hypothesis references a route, symbol or flow missing from the Repository Security Map | 2 requests per hypothesis |
| Verification returns to Dynamic Testing | verdict would be `unconfirmed` for lack of evidence and the plan allows more variants | 2 extra rounds |
| Remediation asks Code Intelligence | Root cause lies in code outside mapped files | 2 clarifications |
| Orchestrator halts | Scope invalid, sandbox unavailable, credentials missing, or `ScopeViolation` | Immediate and audit-logged |
| Patch rework | Tests fail, exploit still reproduces, or reviewer requests changes | 3 patch attempts |

## 3.4 State transitions

![Task states](../diagrams/d07_states.svg)

## 3.5 Failure and retry

![Failure and retry](../diagrams/d08_retry.svg)

## 3.6 Human approval checkpoints

| # | Checkpoint | Trigger | Who decides |
|---|---|---|---|
| 1 | Authorization attestation | Before any active test | Engagement owner (recorded in `engagements.attested_by`) |
| 2 | Test-plan approval | Only when `environment=staging_approved` | Reviewer |
| 3 | Patch approval | Remediation returned `patch_ready_for_review` | Reviewer (`approvals` table). A human performs any merge |

![Remediation and approval](../diagrams/d17_approval.svg)

## 3.7 What each agent hands to the next

| From | To | Handed over |
|---|---|---|
| Orchestrator | Code Intelligence, Recon | task, scope, repository, API spec |
| Code Intelligence | Vulnerability Research | routes, mechanisms, models, graph ref, candidate invariants |
| Recon | Vulnerability Research | endpoints, technologies, attack surface ref, intel refs (untrusted) |
| Vulnerability Research | Dynamic Testing | hypotheses, test plans with state checks |
| Dynamic Testing | Verification | executed cases, state diffs, evidence ids |
| Verification | Remediation | finding id, verdict, severity, supporting evidence |
| Remediation | Human reviewer | patch, test results, replay evidence, approval request |

# 4. Contract Conventions

## 4.1 Identifiers

`project_id` (`prj_`), `engagement_id` (`eng_`), `scan_id` (`scn_`), `task_id` (`tsk_`), `agent_run_id` (`run_`), `finding_id` (`fnd_`), `evidence_id` (`evd_`), `correlation_id` (`cor_`). Format: prefix, underscore, at least 8 hex characters (UUIDv7-derived recommended). The same strings are database primary keys.

## 4.2 Rules

- `schema_version` follows semantic versioning. Minor releases add optional fields only; a breaking change raises the major version and both versions run side by side during migration. Consumers ignore nothing silently: models use `extra="forbid"`.
- Timestamps are ISO 8601 UTC with a trailing `Z`.
- Status values are closed enums; unknown values are rejected.
- Secrets never appear in contracts; credentials are references (`cred_*`) resolved only inside the sandbox.
- A response with `status` other than `succeeded` carries an `error` object and `output` may be null.
- On a schema validation failure the agent gets one repair attempt that includes the validation message; a second failure marks the task `failed`.

## 4.3 Shared base models

**`ErrorInfo`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `code` | `str` | yes | - | Stable machine-readable error code |
| `message` | `str` | yes | - | Human-readable error message |
| `retryable` | `bool` | yes | - | Whether the Orchestrator may retry |
| `details` | `dict or null` | no | - | Optional structured error context |


**`Metrics`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `duration_ms` | `int` | yes | `ge=0` | Wall-clock time of the run |
| `llm_calls` | `int` | yes | `ge=0` | Number of model calls made |
| `input_tokens` | `int` | yes | `ge=0` | Prompt tokens consumed |
| `output_tokens` | `int` | yes | `ge=0` | Completion tokens produced |


**`Envelope`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |


**`ResponseEnvelope`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |

```python
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
```

## 4.4 Error response format

A blocked task caused by a scope violation:

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f409",
  "created_at": "2026-11-17T09:32:07Z",
  "agent": "dynamic_testing",
  "status": "blocked",
  "warnings": [],
  "output": null,
  "error": {
    "code": "SCOPE_VIOLATION",
    "message": "Request to host other-site.example blocked by the scope gate",
    "retryable": false,
    "details": {
      "host": "other-site.example",
      "rule": "host_not_in_allowed_hosts"
    }
  },
  "metrics": {
    "duration_ms": 120,
    "llm_calls": 0,
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

## 4.5 Structured log format

One JSON object per line, always carrying the ids so a whole assessment can be traced by `correlation_id`:

```json
{"ts":"2026-11-17T09:32:05Z","level":"INFO","correlation_id":"cor_0192f230","scan_id":"scn_0192f1c9","task_id":"tsk_0192f305","agent_run_id":"run_0192f405","agent":"dynamic_testing","event":"http_request_sent","identity_id":"id_buyer_b","method":"PATCH","path":"/api/v1/orders/100","status_code":403,"duration_ms":41,"scope_gate":"allowed"}
```

# 5. Agent 1 - Orchestrator

## 5.1 Purpose

Turns a user's assessment request into a validated, dependency-ordered plan and keeps the whole workflow inside the authorized scope.

## 5.2 Responsibilities

- Validate the scope manifest and engagement attestation
- Check required inputs (repository, credentials, startup instructions)
- Build stages and task assignments with dependencies
- Track task states, retries and timeouts
- Pause for human approval at the defined checkpoints
- Collect and consolidate agent outputs
- Halt on any scope violation

## 5.3 Internal workflow

1. Receive request and assign correlation_id
2. Run the five scope checks; any failure sets workflow_status=blocked
3. Select stages from requested_operations and assessment_mode
4. Create tasks with depends_on; mark independent stages with one parallel_group
5. Dispatch ready tasks; consume responses; apply retry and loop rules
6. Emit approval requests; wait; then trigger the deterministic report service

## 5.4 Required tools

- Scope validator (deterministic code)
- Task queue and state store (PostgreSQL)
- Audit logger

## 5.5 Validation rules

- credential_refs has at least 2 identities (paired tests need them)
- environment is sandbox or staging_approved; production is rejected
- scope_manifest_id refers to a manifest with valid=true
- Every task depends_on id exists and the graph is acyclic
- Plan contains only the seven official agents

## 5.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `SCOPE_INVALID` | no | A scope check failed |
| `MISSING_INPUT` | no | Required credential or repository missing |
| `PLAN_CYCLE` | no | Dependency graph has a cycle |
| `LLM_UNAVAILABLE` | yes | Provider timeout or rate limit |

## 5.7 Retry policy

Transient errors: up to 3 attempts with exponential backoff and jitter. Deterministic scope errors are never retried.

## 5.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f301",
  "agent_run_id": "run_0192f401",
  "created_at": "2026-11-17T09:30:00Z",
  "agent": "orchestrator",
  "input": {
    "project": {
      "name": "ShopLite",
      "language": "python",
      "framework_hint": "fastapi"
    },
    "target": {
      "base_url": "http://shoplite-app:8000",
      "environment": "sandbox"
    },
    "repository": {
      "source_type": "github",
      "url": "https://github.com/example-org/shoplite-api",
      "ref": "main"
    },
    "scope_manifest_id": "scm_0192f1b9",
    "assessment_mode": "full",
    "credential_refs": [
      {
        "ref": "cred_buyer_a",
        "role": "customer"
      },
      {
        "ref": "cred_buyer_b",
        "role": "customer"
      },
      {
        "ref": "cred_admin",
        "role": "admin"
      }
    ],
    "requested_operations": [
      "code_analysis",
      "recon",
      "dynamic_testing",
      "remediation"
    ]
  }
}
```

## 5.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f301",
  "agent_run_id": "run_0192f401",
  "created_at": "2026-11-17T09:30:04Z",
  "agent": "orchestrator",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 3900,
    "llm_calls": 1,
    "input_tokens": 2100,
    "output_tokens": 640
  },
  "output": {
    "scope_validation": {
      "valid": true,
      "checks": [
        {
          "name": "manifest_well_formed",
          "passed": true,
          "detail": "scm_0192f1b9 parsed, 1 allowed host"
        },
        {
          "name": "host_in_scope",
          "passed": true,
          "detail": "shoplite-app matches allowed_hosts"
        },
        {
          "name": "no_third_party_wildcards",
          "passed": true,
          "detail": "no wildcard entries"
        },
        {
          "name": "environment_not_production",
          "passed": true,
          "detail": "environment=sandbox"
        },
        {
          "name": "authorization_attested",
          "passed": true,
          "detail": "attested by user usr_0192f19e at 2026-11-17T09:12:00Z"
        }
      ]
    },
    "stages": [
      {
        "name": "code_analysis",
        "agent": "code_intelligence",
        "depends_on": [],
        "parallel_group": "g1"
      },
      {
        "name": "recon",
        "agent": "recon",
        "depends_on": [],
        "parallel_group": "g1"
      },
      {
        "name": "research",
        "agent": "vulnerability_research",
        "depends_on": [
          "code_analysis",
          "recon"
        ]
      },
      {
        "name": "dynamic_testing",
        "agent": "dynamic_testing",
        "depends_on": [
          "research"
        ]
      },
      {
        "name": "verification",
        "agent": "verification",
        "depends_on": [
          "dynamic_testing"
        ]
      },
      {
        "name": "remediation",
        "agent": "remediation",
        "depends_on": [
          "verification"
        ],
        "requires_approval": true
      }
    ],
    "task_assignments": [
      {
        "task_id": "tsk_0192f302",
        "agent": "code_intelligence",
        "stage": "code_analysis",
        "depends_on": []
      },
      {
        "task_id": "tsk_0192f303",
        "agent": "recon",
        "stage": "recon",
        "depends_on": []
      },
      {
        "task_id": "tsk_0192f304",
        "agent": "vulnerability_research",
        "stage": "research",
        "depends_on": [
          "tsk_0192f302",
          "tsk_0192f303"
        ]
      },
      {
        "task_id": "tsk_0192f305",
        "agent": "dynamic_testing",
        "stage": "dynamic_testing",
        "depends_on": [
          "tsk_0192f304"
        ]
      },
      {
        "task_id": "tsk_0192f306",
        "agent": "verification",
        "stage": "verification",
        "depends_on": [
          "tsk_0192f305"
        ]
      },
      {
        "task_id": "tsk_0192f307",
        "agent": "remediation",
        "stage": "remediation",
        "depends_on": [
          "tsk_0192f306"
        ]
      }
    ],
    "workflow_status": "planned"
  }
}
```

## 5.10 Pydantic schema

```python
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
```

## 5.11 Field reference (every field)

**`ProjectInfo`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `language` | `enum[python]` | yes | - | Application language (python in the MVP) |
| `framework_hint` | `str or null` | no | - | Framework suggested by the user |

**`TargetInfo`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `base_url` | `str` | yes | - | Root URL of the application under test |
| `environment` | `enum[sandbox, staging_approved]` | yes | - | sandbox or staging_approved; production is rejected |

**`RepositoryRef`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `source_type` | `enum[github, zip]` | yes | - | github or zip; or the kind of intelligence source |
| `url` | `str` | yes | - | Location of the resource |
| `ref` | `str` | yes | - | Credential reference id |

**`CredentialRef`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `ref` | `str` | yes | `pattern=^cred_[a-z0-9_]+$` | Credential reference id |
| `role` | `str` | yes | - | Role of the identity or credential |

**`OrchestratorInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `project` | `ProjectInfo` | yes | - | Project information |
| `target` | `TargetInfo` | yes | - | Application under test |
| `repository` | `RepositoryRef` | yes | - | Repository reference |
| `scope_manifest_id` | `str` | yes | `pattern=^scm_[0-9a-f]{8,}$` | Validated scope manifest identifier |
| `assessment_mode` | `enum AssessmentMode` | yes | - | code_only, dynamic_only or full |
| `credential_refs` | `list[CredentialRef]` | yes | `min_length=2` | References to test credentials, at least two for paired tests |
| `requested_operations` | `list[enum[code_analysis, recon, dynamic_testing, remediation]]` | yes | - | Operations the user asked for |

**`OrchestratorRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[orchestrator]` | no | - | Official agent name (closed enum) |
| `input` | `OrchestratorInput` | yes | - | Agent-specific request payload |

**`ScopeCheck`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `passed` | `bool` | yes | - | Number of passed tests |
| `detail` | `str` | yes | - | Explanation of the check result |

**`ScopeValidation`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `valid` | `bool` | yes | - | True if all checks passed |
| `checks` | `list[ScopeCheck]` | yes | - | Individual scope validation checks |

**`Stage`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `agent` | `enum AgentName` | yes | - | Official agent name (closed enum) |
| `depends_on` | `list[str]` | yes | - | Stages or task ids that must finish first |
| `parallel_group` | `str or null` | no | - | Stages with the same group may run concurrently |
| `requires_approval` | `bool` | no | - | Stage needs a human decision |

**`TaskAssignment`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent` | `enum AgentName` | yes | - | Official agent name (closed enum) |
| `stage` | `str` | yes | - | Workflow stage name |
| `depends_on` | `list[str]` | yes | - | Stages or task ids that must finish first |

**`OrchestratorOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `scope_validation` | `ScopeValidation` | yes | - | Result of validating the scope |
| `stages` | `list[Stage]` | yes | - | Planned workflow stages |
| `task_assignments` | `list[TaskAssignment]` | yes | - | Tasks assigned to agents with dependencies |
| `workflow_status` | `enum[planned, running, blocked, completed, failed]` | yes | - | Overall workflow state |

**`OrchestratorResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[orchestrator]` | no | - | Official agent name (closed enum) |
| `output` | `OrchestratorOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 5.12 How the next agent consumes this output

The Orchestrator response is the plan. Each task_assignment becomes a queued task; Code Intelligence and Recon share parallel_group g1 and start together.

# 6. Agent 2 - Code Intelligence

## 6.1 Purpose

Builds the Repository Security Map: routes, authentication and authorization, data models, code graph and candidate security invariants.

## 6.2 Responsibilities

- Identify frameworks and structure
- Parse Python with Tree-sitter, cross-checked with ast for decorators and calls
- Extract routes and controllers
- Find authentication and authorization mechanisms
- Map ORM models and database operations
- Analyze dependencies
- Build the code graph (NetworkX, persisted to code_nodes and code_edges)
- Propose candidate invariants with confidence

## 6.3 Internal workflow

1. Ingest repository at the pinned commit
2. Detect framework and entry points
3. Parse files; record unparseable files as warnings
4. Run framework route extractors (Flask, FastAPI, Django)
5. Link routes to guards (auth/authz) and to model reads/writes
6. Derive invariants, e.g. a route that loads an owned model without comparing the owner field
7. Validate output schema, store graph, return references

## 6.4 Required tools

- Tree-sitter (Python grammar)
- Python ast
- Framework route extractors
- NetworkX
- Semgrep (optional)

## 6.5 Validation rules

- commit matches the hex pattern and exists in the checkout
- Every route_id is unique within the scan
- Every applies_to_route_ids entry refers to a returned route
- confidence is within [0, 1]
- code_graph_ref resolves to a stored graph

## 6.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `REPO_UNREADABLE` | no | Checkout missing or corrupt |
| `NO_ROUTES_FOUND` | no | No supported framework detected |
| `PARSE_PARTIAL` | no | Some files unparseable (warning, not failure) |
| `LLM_UNAVAILABLE` | yes | Provider timeout or rate limit |

## 6.7 Retry policy

Parsing is deterministic and not retried. Only the LLM-assisted invariant step retries, up to 3 times.

## 6.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f302",
  "agent_run_id": "run_0192f402",
  "created_at": "2026-11-17T09:30:10Z",
  "agent": "code_intelligence",
  "input": {
    "repository": {
      "path_ref": "workspace://scn_0192f1c9/repo",
      "commit": "a1b2c3d4e5f6"
    },
    "source_language": "python",
    "framework_hints": [
      "fastapi",
      "sqlalchemy"
    ],
    "scan_config": {
      "max_files": 2000,
      "include_globs": [
        "app/**/*.py"
      ],
      "enable_semgrep": false
    }
  }
}
```

## 6.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f302",
  "agent_run_id": "run_0192f402",
  "created_at": "2026-11-17T09:31:02Z",
  "agent": "code_intelligence",
  "status": "succeeded",
  "warnings": [
    "2 files skipped: syntax errors tolerated by tree-sitter but not resolvable"
  ],
  "error": null,
  "metrics": {
    "duration_ms": 51800,
    "llm_calls": 6,
    "input_tokens": 18400,
    "output_tokens": 3100
  },
  "output": {
    "repository_structure": {
      "files_analyzed": 86,
      "frameworks": [
        "fastapi",
        "sqlalchemy"
      ],
      "entry_points": [
        "app/main.py"
      ]
    },
    "routes": [
      {
        "route_id": "rte_patch_order",
        "method": "PATCH",
        "path": "/api/v1/orders/{order_id}",
        "handler": "update_order",
        "file": "app/routes/orders.py",
        "line": 58,
        "auth_required": true,
        "authz_checks": []
      },
      {
        "route_id": "rte_get_order",
        "method": "GET",
        "path": "/api/v1/orders/{order_id}",
        "handler": "get_order",
        "file": "app/routes/orders.py",
        "line": 31,
        "auth_required": true,
        "authz_checks": [
          "order.user_id == current_user.id"
        ]
      }
    ],
    "auth_mechanisms": [
      {
        "name": "get_current_user",
        "kind": "authentication",
        "location": "app/deps.py:14",
        "description": "Decodes bearer JWT and loads the user"
      }
    ],
    "db_models": [
      {
        "name": "Order",
        "table": "orders",
        "owner_field": "user_id",
        "file": "app/models.py"
      }
    ],
    "code_graph_ref": "graph://scn_0192f1c9/code",
    "candidate_invariants": [
      {
        "invariant_id": "inv_order_owner_only",
        "statement": "An order may be read or modified only by the user referenced in orders.user_id",
        "kind": "ownership",
        "applies_to_route_ids": [
          "rte_patch_order",
          "rte_get_order"
        ],
        "source": "code",
        "confidence": 0.86
      }
    ]
  }
}
```

## 6.10 Pydantic schema

```python
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
```

## 6.11 Field reference (every field)

**`RepoCheckout`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `path_ref` | `str` | yes | - | Workspace location of the checked-out repository |
| `commit` | `str` | yes | `pattern=^[0-9a-f]{7,40}$` | Git commit being analyzed |

**`ScanConfig`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `max_files` | `int` | yes | `gt=0` | Upper bound on files parsed |
| `include_globs` | `list[str]` | yes | - | Glob patterns of files to analyze |
| `enable_semgrep` | `bool` | yes | - | Run Semgrep as an optional static pass |

**`CodeIntelInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `repository` | `RepoCheckout` | yes | - | Repository reference |
| `source_language` | `enum[python]` | yes | - | Source language (python) |
| `framework_hints` | `list[str]` | yes | - | Frameworks to prioritize when parsing |
| `scan_config` | `ScanConfig` | yes | - | Analysis limits and options |

**`CodeIntelRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[code_intelligence]` | no | - | Official agent name (closed enum) |
| `input` | `CodeIntelInput` | yes | - | Agent-specific request payload |

**`RepoStructure`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `files_analyzed` | `int` | yes | - | Count of files parsed |
| `frameworks` | `list[str]` | yes | - | Frameworks detected |
| `entry_points` | `list[str]` | yes | - | Application entry modules |

**`Route`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `route_id` | `str` | yes | `pattern=^rte_[a-z0-9_]+$` | Identifier of a route |
| `method` | `str` | yes | - | HTTP method, or the testing method for a plan |
| `path` | `str` | yes | - | URL path template |
| `handler` | `str` | yes | - | Function that serves the route |
| `file` | `str` | yes | - | Source file path |
| `line` | `int` | yes | - | Line number in the file |
| `auth_required` | `bool` | yes | - | Whether the route or endpoint demands authentication |
| `authz_checks` | `list[str]` | yes | - | Authorization checks found in the handler (empty means none) |

**`SecurityMechanism`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `kind` | `enum[authentication, authorization]` | yes | - | Category of the item (closed enum) |
| `location` | `str` | yes | - | file:line where the mechanism lives |
| `description` | `str` | yes | - | Human-readable description |

**`DbModel`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `table` | `str` | yes | - | Database table name |
| `owner_field` | `str or null` | no | - | Column that stores the owning user |
| `file` | `str` | yes | - | Source file path |

**`CandidateInvariant`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `invariant_id` | `str` | yes | `pattern=^inv_[a-z0-9_]+$` | Identifier of a security invariant |
| `statement` | `str` | yes | - | Invariant in plain language |
| `kind` | `enum[ownership, role_restriction, state_transition, authentication_required]` | yes | - | Category of the item (closed enum) |
| `applies_to_route_ids` | `list[str]` | yes | - | Routes the invariant constrains |
| `source` | `enum[code, declared_policy]` | yes | - | Where the item was discovered or derived from |
| `confidence` | `float` | yes | `ge=0, le=1` | Score from 0 to 1 |

**`CodeIntelOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `repository_structure` | `RepoStructure` | yes | - | Summary of the analyzed repository |
| `routes` | `list[Route]` | yes | - | Routes and controllers found |
| `auth_mechanisms` | `list[SecurityMechanism]` | yes | - | Authentication and authorization mechanisms found |
| `db_models` | `list[DbModel]` | yes | - | ORM models and their tables |
| `code_graph_ref` | `str` | yes | - | Reference to the stored code graph |
| `candidate_invariants` | `list[CandidateInvariant]` | yes | - | Security invariants proposed from code |

**`CodeIntelResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[code_intelligence]` | no | - | Official agent name (closed enum) |
| `output` | `CodeIntelOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 6.12 How the next agent consumes this output

Vulnerability Research reads routes whose authz_checks is empty and matches them with candidate_invariants through applies_to_route_ids; Recon-discovered endpoints are linked to routes by method and path.

# 7. Agent 3 - Recon

## 7.1 Purpose

Discovers the authorized attack surface and enriches technology findings with external security intelligence, strictly inside scope.

## 7.2 Responsibilities

- Ingest and normalize the OpenAPI specification
- Enumerate in-scope endpoints and operations
- Fingerprint technologies from headers, docs routes and config
- Query Tavily for advisories of fingerprinted technologies (when enabled)
- Build the Attack Surface Map
- Preserve source, URL and retrieval time for every reference

## 7.3 Internal workflow

1. Load scope and API spec
2. Reject any endpoint outside allowed_hosts or inside forbidden_paths
3. Create Endpoint records (source=openapi, code_routes or crawl)
4. Fingerprint technologies with evidence strings
5. Run at most max_queries Tavily searches; deduplicate; mark trusted=false
6. Return endpoints, technologies, attack_surface_ref and intel_refs

## 7.4 Required tools

- HTTPX through the scope gate
- OpenAPI parser
- Tavily (langchain-tavily wrapper)
- Schemathesis (optional, spec validation)

## 7.5 Validation rules

- Every endpoint host is in allowed_hosts
- No endpoint path matches forbidden_paths
- intel_refs.trusted is always false
- retrieved_at is ISO 8601 UTC
- Number of searches does not exceed max_queries

## 7.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `SPEC_INVALID` | no | OpenAPI document cannot be parsed |
| `SCOPE_VIOLATION` | no | A probe targeted an out-of-scope host |
| `RESEARCH_UNAVAILABLE` | yes | Tavily timeout or rate limit; recon continues without intel |
| `LLM_UNAVAILABLE` | yes | Provider timeout or rate limit |

## 7.7 Retry policy

Tavily failures retry up to 3 times with backoff and then degrade to a warning; a missing intel reference never fails Recon.

## 7.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f303",
  "agent_run_id": "run_0192f403",
  "created_at": "2026-11-17T09:30:10Z",
  "agent": "recon",
  "input": {
    "scope": {
      "allowed_hosts": [
        "shoplite-app"
      ],
      "allowed_methods": [
        "GET",
        "POST",
        "PATCH",
        "DELETE"
      ],
      "forbidden_paths": [
        "/admin/danger/*"
      ]
    },
    "api_spec_ref": "workspace://scn_0192f1c9/openapi.json",
    "technology_hints": [
      "fastapi",
      "postgresql"
    ],
    "research": {
      "enabled": true,
      "max_queries": 3,
      "search_depth": "basic"
    }
  }
}
```

## 7.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f303",
  "agent_run_id": "run_0192f403",
  "created_at": "2026-11-17T09:30:51Z",
  "agent": "recon",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 41000,
    "llm_calls": 3,
    "input_tokens": 6200,
    "output_tokens": 1500
  },
  "output": {
    "endpoints": [
      {
        "endpoint_id": "ep_patch_order",
        "method": "PATCH",
        "path": "/api/v1/orders/{order_id}",
        "path_params": [
          "order_id"
        ],
        "auth_required": true,
        "source": "openapi"
      },
      {
        "endpoint_id": "ep_get_order",
        "method": "GET",
        "path": "/api/v1/orders/{order_id}",
        "path_params": [
          "order_id"
        ],
        "auth_required": true,
        "source": "openapi"
      }
    ],
    "technologies": [
      {
        "name": "FastAPI",
        "version": null,
        "confidence": 0.9,
        "evidence": "OpenAPI document generator metadata and /docs route"
      },
      {
        "name": "PostgreSQL",
        "version": null,
        "confidence": 0.7,
        "evidence": "docker-compose service image name"
      }
    ],
    "attack_surface_ref": "graph://scn_0192f1c9/attack_surface",
    "intel_refs": [
      {
        "ref_id": "ref_0192f2b1",
        "title": "API1:2023 Broken Object Level Authorization",
        "url": "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
        "retrieved_at": "2026-11-17T09:30:40Z",
        "source_type": "owasp",
        "relevance": 0.9,
        "trusted": false
      }
    ]
  }
}
```

## 7.10 Pydantic schema

```python
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
```

## 7.11 Field reference (every field)

**`ScopeSummary`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `allowed_hosts` | `list[str]` | yes | - | Hosts the tests may contact |
| `allowed_methods` | `list[str]` | yes | - | HTTP methods permitted by scope |
| `forbidden_paths` | `list[str]` | yes | - | Paths that must never be tested |

**`ResearchConfig`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `enabled` | `bool` | yes | - | Whether external research is allowed |
| `max_queries` | `int` | yes | `ge=0` | Upper bound on external searches |
| `search_depth` | `enum[basic, advanced]` | yes | - | Tavily depth: basic costs 1 credit, advanced 2 |

**`ReconInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `scope` | `ScopeSummary` | yes | - | Summary of the authorized scope |
| `api_spec_ref` | `str or null` | no | - | Reference to the OpenAPI document in the workspace |
| `technology_hints` | `list[str]` | yes | - | Technologies suggested by the user |
| `research` | `ResearchConfig` | yes | - | External research settings |

**`ReconRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[recon]` | no | - | Official agent name (closed enum) |
| `input` | `ReconInput` | yes | - | Agent-specific request payload |

**`Endpoint`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `endpoint_id` | `str` | yes | `pattern=^ep_[a-z0-9_]+$` | Identifier of an endpoint |
| `method` | `str` | yes | - | HTTP method, or the testing method for a plan |
| `path` | `str` | yes | - | URL path template |
| `path_params` | `list[str]` | yes | - | Names of path parameters |
| `auth_required` | `bool or null` | no | - | Whether the route or endpoint demands authentication |
| `source` | `enum[openapi, code_routes, crawl]` | yes | - | Where the item was discovered or derived from |

**`Technology`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `name` | `str` | yes | - | Name of the item |
| `version` | `str or null` | no | - | Version string, or null when unknown |
| `confidence` | `float` | yes | `ge=0, le=1` | Score from 0 to 1 |
| `evidence` | `str` | yes | - | Why this technology was inferred |

**`IntelRef`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `ref_id` | `str` | yes | - | Intelligence reference id |
| `title` | `str` | yes | - | Short title |
| `url` | `str` | yes | - | Location of the resource |
| `retrieved_at` | `str` | yes | - | When the reference was fetched |
| `source_type` | `enum[vendor, nvd, owasp, other]` | yes | - | github or zip; or the kind of intelligence source |
| `relevance` | `float` | yes | `ge=0, le=1` | Relevance score from 0 to 1 |
| `trusted` | `enum[False]` | no | - | Always false: external text is untrusted |

**`ReconOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `endpoints` | `list[Endpoint]` | yes | - | Discovered authorized endpoints |
| `technologies` | `list[Technology]` | yes | - | Detected technologies and fingerprints |
| `attack_surface_ref` | `str` | yes | - | Reference to the Attack Surface Map graph |
| `intel_refs` | `list[IntelRef]` | yes | - | External intelligence references (untrusted) |

**`ReconResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[recon]` | no | - | Official agent name (closed enum) |
| `output` | `ReconOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 7.12 How the next agent consumes this output

Vulnerability Research joins endpoints with routes and invariants. intel_refs are attached to hypotheses only as references, never as proof.

# 8. Agent 4 - Vulnerability Research

## 8.1 Purpose

Converts maps and invariants into prioritized, testable hypotheses and structured test plans, guided by retrieved Claude-BugHunter skills.

## 8.2 Responsibilities

- Join routes, endpoints and invariants
- Identify applicable vulnerability classes
- Generate hypotheses with an explicit rationale
- Select skills through the Skill Router (1 to 3 per hypothesis)
- Choose a testing method and state checks
- Prioritize and explain
- Request more code context when a symbol is missing

## 8.3 Internal workflow

1. Match routes with empty authz_checks to ownership invariants
2. Create one hypothesis per mismatch; category from invariant kind
3. Retrieve skills (for example hunt-idor) within the token budget
4. Write a test plan: paired_identity when an ownership rule exists
5. Define state_checks: table, key and columns to diff
6. Order by priority 1 to 5; validate and return

## 8.4 Required tools

- Skill Router and Loader
- Code graph query
- Tavily (optional, references only)

## 8.5 Validation rules

- Every hypothesis references an existing endpoint_id and invariant_id
- category is one of the four MVP classes
- Every test plan references an existing hypothesis
- paired_identity plans list at least two identities
- skill_refs are names present in the skills table

## 8.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `NO_HYPOTHESES` | no | Nothing to test (valid, empty result with warning) |
| `SKILL_NOT_FOUND` | no | Router returned an unknown skill |
| `CONTEXT_REQUEST_LIMIT` | no | More than 2 context requests for a hypothesis |
| `LLM_UNAVAILABLE` | yes | Provider timeout or rate limit |

## 8.7 Retry policy

Schema repair once, then up to 3 transient retries. Context-request loops are capped at 2 per hypothesis.

## 8.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f304",
  "agent_run_id": "run_0192f404",
  "created_at": "2026-11-17T09:31:10Z",
  "agent": "vulnerability_research",
  "input": {
    "code_intel_ref": "out://tsk_0192f302",
    "recon_ref": "out://tsk_0192f303",
    "invariant_ids": [
      "inv_order_owner_only"
    ],
    "skill_hits": [
      {
        "skill": "hunt-idor",
        "source_commit": "64410ed",
        "score": 0.91
      }
    ]
  }
}
```

## 8.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f304",
  "agent_run_id": "run_0192f404",
  "created_at": "2026-11-17T09:31:30Z",
  "agent": "vulnerability_research",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 20100,
    "llm_calls": 2,
    "input_tokens": 9100,
    "output_tokens": 1800
  },
  "output": {
    "hypotheses": [
      {
        "hypothesis_id": "hyp_idor_patch_order",
        "category": "idor",
        "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
        "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
        "endpoint_id": "ep_patch_order",
        "invariant_id": "inv_order_owner_only",
        "priority": 1,
        "skill_refs": [
          "hunt-idor"
        ]
      }
    ],
    "test_plans": [
      {
        "test_plan_id": "tpl_idor_patch_order",
        "hypothesis_id": "hyp_idor_patch_order",
        "method": "paired_identity",
        "steps": [
          "Snapshot orders.id=100",
          "As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address",
          "Snapshot orders.id=100",
          "As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address",
          "Snapshot orders.id=100 and diff"
        ],
        "identities": [
          "id_buyer_a",
          "id_buyer_b"
        ],
        "expected_secure_behavior": "Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
        "state_checks": [
          {
            "table": "orders",
            "key": {
              "id": 100
            },
            "columns": [
              "shipping_address"
            ]
          }
        ]
      }
    ]
  }
}
```

## 8.10 Pydantic schema

```python
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
```

## 8.11 Field reference (every field)

**`SkillHit`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `skill` | `str` | yes | - | Claude-BugHunter skill name |
| `source_commit` | `str` | yes | - | Commit of the skill repository used |
| `score` | `float` | yes | - | Retrieval score |

**`ResearchInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `code_intel_ref` | `str` | yes | - | Reference to the Code Intelligence output |
| `recon_ref` | `str` | yes | - | Reference to the Recon output |
| `invariant_ids` | `list[str]` | yes | - | Invariants to build hypotheses from |
| `skill_hits` | `list[SkillHit]` | yes | - | Skills retrieved for this task |

**`ResearchRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[vulnerability_research]` | no | - | Official agent name (closed enum) |
| `input` | `ResearchInput` | yes | - | Agent-specific request payload |

**`StateCheck`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `table` | `str` | yes | - | Database table name |
| `key` | `dict` | yes | - | Primary-key values identifying the row |
| `columns` | `list[str]` | yes | - | Columns to compare before and after |

**`Hypothesis`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `hypothesis_id` | `str` | yes | `pattern=^hyp_[a-z0-9_]+$` | Identifier of a hypothesis |
| `category` | `enum VulnCategory` | yes | - | Vulnerability class (closed enum of the four MVP classes) |
| `title` | `str` | yes | - | Short title |
| `rationale` | `str` | yes | - | Why the hypothesis or severity applies |
| `endpoint_id` | `str` | yes | - | Identifier of an endpoint |
| `invariant_id` | `str` | yes | - | Identifier of a security invariant |
| `priority` | `int` | yes | `ge=1, le=5` | 1 (highest) to 5 (lowest) |
| `skill_refs` | `list[str]` | yes | - | Skills that informed the hypothesis |

**`TestPlan`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `test_plan_id` | `str` | yes | `pattern=^tpl_[a-z0-9_]+$` | Identifier of a test plan |
| `hypothesis_id` | `str` | yes | - | Identifier of a hypothesis |
| `method` | `enum[paired_identity, single_identity, workflow_sequence]` | yes | - | HTTP method, or the testing method for a plan |
| `steps` | `list[str]` | yes | - | Ordered test steps |
| `identities` | `list[str]` | yes | - | Test identities involved |
| `expected_secure_behavior` | `str` | yes | - | What a correct implementation must do |
| `state_checks` | `list[StateCheck]` | yes | - | Database rows and columns to snapshot and diff |

**`ResearchOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `hypotheses` | `list[Hypothesis]` | yes | - | Testable vulnerability hypotheses |
| `test_plans` | `list[TestPlan]` | yes | - | Structured testing plans |

**`ResearchResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[vulnerability_research]` | no | - | Official agent name (closed enum) |
| `output` | `ResearchOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 8.12 How the next agent consumes this output

Dynamic Testing receives one test plan with its endpoint and identities. state_checks tell it which rows to snapshot; expected_secure_behavior is what Verification later judges against.

# 9. Agent 5 - Dynamic Testing

## 9.1 Purpose

Executes an approved test plan inside the sandbox with multiple identities and captures requests, responses and database state changes as evidence.

## 9.2 Responsibilities

- Resolve credential references to tokens inside the sandbox only
- Execute paired-identity and workflow tests
- Snapshot database rows before and after
- Run the State-Diff Engine
- Capture redacted request/response evidence
- Stay within max_requests and the scope gate

## 9.3 Internal workflow

1. Start or attach to the sandbox sbx_*; confirm health
2. Snapshot rows named in state_checks (phase=before)
3. Run each step as the specified identity through the scoped HTTP tool
4. Snapshot again (phase=after) around the suspect request
5. Compute diffs per column; store evidence with SHA-256
6. Compare identity outcomes and return

## 9.4 Required tools

- HTTPX scoped client
- Sandbox controller (Docker)
- DB snapshot helper
- State-Diff Engine
- Playwright (deferred; UI flows only)

## 9.5 Validation rules

- Every outgoing request passes the scope gate (host, path, method, rate)
- Evidence content is redacted before storage (see evidence-hygiene)
- evidence_id exists for every exchange and diff
- Snapshot ids are present when snapshot_enabled is true
- Requests do not exceed max_requests

## 9.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `SCOPE_VIOLATION` | no | Request blocked by the scope gate; task becomes blocked |
| `SANDBOX_UNHEALTHY` | yes | Application failed health check |
| `REQUEST_BUDGET_EXCEEDED` | no | max_requests reached |
| `SNAPSHOT_FAILED` | yes | Database snapshot could not be taken |

## 9.7 Retry policy

Sandbox and snapshot failures retry up to 3 times after a sandbox reset. A single test request is never auto-retried, because replays could alter state.

## 9.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f405",
  "created_at": "2026-11-17T09:31:35Z",
  "agent": "dynamic_testing",
  "input": {
    "test_plan": {
      "test_plan_id": "tpl_idor_patch_order",
      "hypothesis_id": "hyp_idor_patch_order",
      "method": "paired_identity",
      "steps": [
        "Snapshot orders.id=100",
        "As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address",
        "Snapshot orders.id=100",
        "As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address",
        "Snapshot orders.id=100 and diff"
      ],
      "identities": [
        "id_buyer_a",
        "id_buyer_b"
      ],
      "expected_secure_behavior": "Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
      "state_checks": [
        {
          "table": "orders",
          "key": {
            "id": 100
          },
          "columns": [
            "shipping_address"
          ]
        }
      ]
    },
    "endpoint": {
      "endpoint_id": "ep_patch_order",
      "method": "PATCH",
      "path": "/api/v1/orders/{order_id}",
      "path_params": [
        "order_id"
      ],
      "auth_required": true,
      "source": "openapi"
    },
    "identities": [
      {
        "identity_id": "id_buyer_a",
        "role": "customer",
        "credential_ref": "cred_buyer_a",
        "owns": {
          "order_id": 100
        }
      },
      {
        "identity_id": "id_buyer_b",
        "role": "customer",
        "credential_ref": "cred_buyer_b",
        "owns": {
          "order_id": 200
        }
      }
    ],
    "sandbox": {
      "sandbox_id": "sbx_0192f2f0",
      "base_url": "http://shoplite-app:8000",
      "snapshot_enabled": true,
      "max_requests": 200
    },
    "invariant_id": "inv_order_owner_only"
  }
}
```

## 9.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f305",
  "agent_run_id": "run_0192f405",
  "created_at": "2026-11-17T09:32:05Z",
  "agent": "dynamic_testing",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 29800,
    "llm_calls": 0,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "output": {
    "executed_cases": [
      {
        "case_id": "case_01",
        "identity_id": "id_buyer_a",
        "exchange": {
          "method": "PATCH",
          "url": "http://shoplite-app:8000/api/v1/orders/100",
          "status_code": 200,
          "response_excerpt": "{\"id\":100,\"status\":\"updated\"}",
          "evidence_id": "evd_0192f21a"
        }
      },
      {
        "case_id": "case_02",
        "identity_id": "id_buyer_b",
        "exchange": {
          "method": "PATCH",
          "url": "http://shoplite-app:8000/api/v1/orders/100",
          "status_code": 403,
          "response_excerpt": "{\"detail\":\"Forbidden\"}",
          "evidence_id": "evd_0192f21b"
        }
      }
    ],
    "identity_comparison": "Owner received 200; non-owner received 403 (response-level control appears to hold)",
    "state_diffs": [
      {
        "table": "orders",
        "key": {
          "id": 100
        },
        "column": "shipping_address",
        "before": "12 Nile St, Alexandria",
        "after": "99 Test Ave, Cairo",
        "snapshot_before_id": "snp_0192f2c1",
        "snapshot_after_id": "snp_0192f2c2",
        "evidence_id": "evd_0192f21c"
      }
    ],
    "execution_status": "completed",
    "log_ref": "log://tsk_0192f305"
  }
}
```

## 9.10 Pydantic schema

```python
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
```

## 9.11 Field reference (every field)

**`Identity`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `identity_id` | `str` | yes | - | Test identity identifier |
| `role` | `str` | yes | - | Role of the identity or credential |
| `credential_ref` | `str` | yes | `pattern=^cred_[a-z0-9_]+$` | Opaque reference to a credential; secrets never travel in contracts |
| `owns` | `dict` | yes | - | Resources owned by the identity |

**`SandboxConfig`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `sandbox_id` | `str` | yes | `pattern=^sbx_[0-9a-f]{8,}$` | Identifier of the sandbox instance |
| `base_url` | `str` | yes | - | Root URL of the application under test |
| `snapshot_enabled` | `bool` | yes | - | Database snapshots available |
| `max_requests` | `int` | yes | `gt=0` | Request budget inside the sandbox |

**`DynamicInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `test_plan` | `TestPlan` | yes | - | Approved plan to execute |
| `endpoint` | `Endpoint` | yes | - | The endpoint under test |
| `identities` | `list[Identity]` | yes | - | Test identities involved |
| `sandbox` | `SandboxConfig` | yes | - | Isolated environment configuration |
| `invariant_id` | `str` | yes | - | Identifier of a security invariant |

**`DynamicRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[dynamic_testing]` | no | - | Official agent name (closed enum) |
| `input` | `DynamicInput` | yes | - | Agent-specific request payload |

**`HttpExchange`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `method` | `str` | yes | - | HTTP method, or the testing method for a plan |
| `url` | `str` | yes | - | Location of the resource |
| `status_code` | `int` | yes | - | HTTP status code received |
| `response_excerpt` | `str` | yes | - | Redacted excerpt of the response body |
| `evidence_id` | `str` | yes | `pattern=^evd_[0-9a-f]{8,}$` | Immutable evidence record id |

**`ExecutedCase`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `case_id` | `str` | yes | - | Identifier of one executed test case |
| `identity_id` | `str` | yes | - | Test identity identifier |
| `exchange` | `HttpExchange` | yes | - | Captured HTTP request/response summary |

**`StateDiff`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `table` | `str` | yes | - | Database table name |
| `key` | `dict` | yes | - | Primary-key values identifying the row |
| `column` | `str` | yes | - | Database column that changed |
| `before` | `object` | yes | - | Column value before the request |
| `after` | `object` | yes | - | Column value after the request |
| `snapshot_before_id` | `str` | yes | - | Snapshot taken before the request |
| `snapshot_after_id` | `str` | yes | - | Snapshot taken after the request |
| `evidence_id` | `str` | yes | - | Immutable evidence record id |

**`DynamicOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `executed_cases` | `list[ExecutedCase]` | yes | - | Test cases that were actually run |
| `identity_comparison` | `str` | yes | - | Narrative comparison of identity outcomes |
| `state_diffs` | `list[StateDiff]` | yes | - | Database differences observed |
| `execution_status` | `enum[completed, partial, aborted]` | yes | - | completed, partial or aborted |
| `log_ref` | `str` | yes | - | Reference to execution logs |

**`DynamicResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[dynamic_testing]` | no | - | Official agent name (closed enum) |
| `output` | `DynamicOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 9.12 How the next agent consumes this output

Verification re-reads evidence by id. The key insight is in state_diffs: case_02 returned 403, yet orders.id=100.shipping_address changed.

# 10. Agent 6 - Verification

## 10.1 Purpose

Decides whether a hypothesis is a real vulnerability by reproducing it, validating the evidence and checking the invariant. Search results are never evidence.

## 10.2 Responsibilities

- Re-run the scenario reproduction_runs_requested times
- Validate evidence integrity (SHA-256) and completeness
- Check that the invariant is actually violated
- Verify state changes
- Compute reproducibility and confidence
- Assign severity by the documented method
- Return confirmed, unconfirmed or rejected

## 10.3 Internal workflow

1. Load hypothesis, invariant and evidence; verify hashes
2. Apply triage gates: reproducible, in scope, real impact, not expected behavior
3. Reproduce through Dynamic Testing runs on a fresh sandbox state
4. Evaluate invariant_violated from state diff, not from the status code alone
5. Score confidence = f(reproduction rate, evidence completeness, invariant source)
6. Assign severity (impact x likelihood; optional CVSS v3.1 vector) and create the finding

## 10.4 Required tools

- Dynamic Testing replay
- Evidence store with hash check
- Skill: triage-validation, evidence-hygiene

## 10.5 Validation rules

- verdict=confirmed requires severity, invariant_violated=true and reproduced>=1
- reproduced <= runs
- rejection_reasons is non-empty when verdict=rejected
- Every supporting_evidence_id exists and its hash verifies
- Tavily results are not accepted as evidence

## 10.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `EVIDENCE_HASH_MISMATCH` | no | Stored evidence no longer matches its SHA-256 |
| `REPRODUCTION_ENV_FAILED` | yes | Sandbox could not be reset for a clean rerun |
| `INSUFFICIENT_EVIDENCE` | no | Yields verdict=unconfirmed, not a failure |
| `LLM_UNAVAILABLE` | yes | Provider timeout or rate limit |

## 10.7 Retry policy

Unconfirmed results may return to Dynamic Testing for at most 2 extra rounds; after that the verdict stays unconfirmed.

## 10.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "agent_run_id": "run_0192f406",
  "created_at": "2026-11-17T09:32:10Z",
  "agent": "verification",
  "input": {
    "hypothesis": {
      "hypothesis_id": "hyp_idor_patch_order",
      "category": "idor",
      "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
      "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
      "endpoint_id": "ep_patch_order",
      "invariant_id": "inv_order_owner_only",
      "priority": 1,
      "skill_refs": [
        "hunt-idor"
      ]
    },
    "dynamic_result_ref": "out://tsk_0192f305",
    "evidence_ids": [
      "evd_0192f21a",
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "invariant_statement": "An order may be read or modified only by the user referenced in orders.user_id",
    "reproduction_runs_requested": 3
  }
}
```

## 10.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f306",
  "agent_run_id": "run_0192f406",
  "created_at": "2026-11-17T09:32:50Z",
  "agent": "verification",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 40000,
    "llm_calls": 2,
    "input_tokens": 7400,
    "output_tokens": 1200
  },
  "output": {
    "finding_id": "fnd_0192f200",
    "verdict": "confirmed",
    "reproducibility": {
      "runs": 3,
      "reproduced": 3
    },
    "confidence": 0.97,
    "severity": {
      "level": "medium",
      "rationale": "Authenticated non-owner can alter another customer's order data (integrity impact, no confidentiality impact observed); low attack complexity",
      "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N"
    },
    "invariant_violated": true,
    "supporting_evidence_ids": [
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "rejection_reasons": []
  }
}
```

## 10.10 Pydantic schema

```python
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
```

## 10.11 Field reference (every field)

**`VerificationInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `hypothesis` | `Hypothesis` | yes | - | The hypothesis being verified |
| `dynamic_result_ref` | `str` | yes | - | Reference to the Dynamic Testing output |
| `evidence_ids` | `list[str]` | yes | - | Evidence records supporting the request |
| `invariant_statement` | `str` | yes | - | Plain-language rule being checked |
| `reproduction_runs_requested` | `int` | yes | `ge=1, le=10` | How many reproduction runs to perform (1 to 10) |

**`VerificationRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[verification]` | no | - | Official agent name (closed enum) |
| `input` | `VerificationInput` | yes | - | Agent-specific request payload |

**`Reproducibility`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `runs` | `int` | yes | - | Total reproduction runs |
| `reproduced` | `int` | yes | - | Runs in which the behavior reproduced |

**`Severity`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `level` | `enum SeverityLevel` | yes | - | Severity level |
| `rationale` | `str` | yes | - | Why the hypothesis or severity applies |
| `cvss_vector` | `str or null` | no | - | Optional CVSS v3.1 vector supporting the severity |

**`VerificationOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `finding_id` | `str or null` | no | `pattern=^fnd_[0-9a-f]{8,}$` | Verified finding identifier |
| `verdict` | `enum Verdict` | yes | - | confirmed, unconfirmed or rejected |
| `reproducibility` | `Reproducibility` | yes | - | Reproduction statistics |
| `confidence` | `float` | yes | `ge=0, le=1` | Score from 0 to 1 |
| `severity` | `Severity or null` | no | - | Severity with rationale |
| `invariant_violated` | `bool` | yes | - | True if observed behavior breaks the invariant |
| `supporting_evidence_ids` | `list[str]` | yes | - | Evidence backing the verdict |
| `rejection_reasons` | `list[str]` | no | - | Why a finding was rejected |

**`VerificationResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[verification]` | no | - | Official agent name (closed enum) |
| `output` | `VerificationOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 10.12 How the next agent consumes this output

Remediation accepts only verdict=confirmed. It reads finding_id, the supporting evidence and the original test plan id so it can replay the exact scenario on the patched build.

# 11. Agent 7 - Remediation

## 11.1 Purpose

Finds the root cause, writes a patch on an isolated branch, proves it with tests and a replay of the original exploit, and asks a human to approve.

## 11.2 Responsibilities

- Analyze the root cause from code and evidence
- Generate the smallest secure patch
- Apply it only to an isolated branch
- Run unit, integration and regression tests
- Replay the original vulnerability scenario
- Compare pre-patch and post-patch behavior
- Request human approval; never merge or deploy

## 11.3 Internal workflow

1. Read source_refs and evidence; ask Code Intelligence if context is missing (max 2)
2. Draft the fix and a new authorization regression test
3. Create branch fix/aegistrace-<finding>; apply patch there
4. Run test suites; on failure retry up to max_attempts
5. Replay original test plan; require vulnerability_still_reproducible=false
6. Return patch, test counts and replay; set requires_human_approval=true

## 11.4 Required tools

- Git (isolated branch only)
- Sandbox test runner
- Replay via Dynamic Testing
- Tavily (optional, official fix guidance only)

## 11.5 Validation rules

- finding verdict is confirmed
- The patch never targets the default branch
- requires_human_approval is always true
- remediation_status=patch_ready_for_review requires failed=0 in all suites and vulnerability_still_reproducible=false
- changed_files are inside the repository checkout

## 11.6 Error cases

| Code | Retryable | When |
|---|---|---|
| `FINDING_NOT_CONFIRMED` | no | Input finding is not confirmed |
| `PATCH_TESTS_FAILED` | no | Tests failed after max_attempts |
| `EXPLOIT_STILL_REPRODUCES` | no | Replay shows the bug remains |
| `BRANCH_PROTECTED` | no | Attempt to write outside the isolated branch |

## 11.7 Retry policy

Up to 3 patch attempts, each informed by the previous failure. Network or LLM transients get 3 backoff retries within an attempt.

## 11.8 Example request JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f307",
  "agent_run_id": "run_0192f407",
  "created_at": "2026-11-17T09:32:55Z",
  "agent": "remediation",
  "input": {
    "finding_id": "fnd_0192f200",
    "source_refs": [
      {
        "file": "app/routes/orders.py",
        "start_line": 58,
        "end_line": 79
      }
    ],
    "verification_evidence_ids": [
      "evd_0192f21b",
      "evd_0192f21c"
    ],
    "test_environment": {
      "sandbox_id": "sbx_0192f2f0",
      "base_url": "http://shoplite-app:8000",
      "snapshot_enabled": true,
      "max_requests": 200
    },
    "original_test_plan_id": "tpl_idor_patch_order",
    "max_attempts": 3
  }
}
```

## 11.9 Example response JSON

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "cor_0192f230",
  "project_id": "prj_0192f1a0",
  "engagement_id": "eng_0192f1b4",
  "scan_id": "scn_0192f1c9",
  "task_id": "tsk_0192f307",
  "agent_run_id": "run_0192f407",
  "created_at": "2026-11-17T09:34:20Z",
  "agent": "remediation",
  "status": "succeeded",
  "warnings": [],
  "error": null,
  "metrics": {
    "duration_ms": 85000,
    "llm_calls": 5,
    "input_tokens": 26000,
    "output_tokens": 4200
  },
  "output": {
    "root_cause": {
      "summary": "update_order loads the order by id and applies changes without comparing order.user_id to the authenticated user; the 403 is produced by a later serialization step after the write is committed",
      "files": [
        "app/routes/orders.py"
      ]
    },
    "patch": {
      "patch_id": "pat_0192f500",
      "branch": "fix/aegistrace-fnd-0192f200",
      "diff_ref": "patches/pat_0192f500.diff",
      "changed_files": [
        "app/routes/orders.py",
        "tests/test_orders_authz.py"
      ]
    },
    "tests": {
      "unit": {
        "total": 42,
        "passed": 42,
        "failed": 0
      },
      "integration": {
        "total": 18,
        "passed": 18,
        "failed": 0
      },
      "regression": {
        "total": 120,
        "passed": 120,
        "failed": 0
      }
    },
    "replay": {
      "original_scenario_replayed": true,
      "vulnerability_still_reproducible": false,
      "evidence_id": "evd_0192f2a0"
    },
    "remediation_status": "patch_ready_for_review",
    "requires_human_approval": true
  }
}
```

## 11.10 Pydantic schema

```python
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
```

## 11.11 Field reference (every field)

**`SourceRef`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `file` | `str` | yes | - | Source file path |
| `start_line` | `int` | yes | - | First line of the referenced code |
| `end_line` | `int` | yes | - | Last line of the referenced code |

**`RemediationInput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `finding_id` | `str` | yes | `pattern=^fnd_[0-9a-f]{8,}$` | Verified finding identifier |
| `source_refs` | `list[SourceRef]` | yes | - | Code locations relevant to the finding |
| `verification_evidence_ids` | `list[str]` | yes | - | Evidence that proved the vulnerability |
| `test_environment` | `SandboxConfig` | yes | - | Sandbox used to validate the patch |
| `original_test_plan_id` | `str` | yes | - | Test plan that originally proved the bug |
| `max_attempts` | `int` | yes | `ge=1, le=3` | Maximum patch attempts (1 to 3) |

**`RemediationRequest`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `agent` | `enum[remediation]` | no | - | Official agent name (closed enum) |
| `input` | `RemediationInput` | yes | - | Agent-specific request payload |

**`RootCause`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `summary` | `str` | yes | - | Short explanation |
| `files` | `list[str]` | yes | - | Files involved in the root cause |

**`PatchInfo`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `patch_id` | `str` | yes | `pattern=^pat_[0-9a-f]{8,}$` | Patch identifier |
| `branch` | `str` | yes | - | Isolated working branch holding the patch |
| `diff_ref` | `str` | yes | - | Reference to the stored unified diff |
| `changed_files` | `list[str]` | yes | - | Files modified by the patch |

**`TestCounts`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `total` | `int` | yes | - | Total tests |
| `passed` | `int` | yes | - | Number of passed tests |
| `failed` | `int` | yes | - | Number of failed tests |

**`RemediationTests`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `unit` | `TestCounts` | yes | - | Unit test counts |
| `integration` | `TestCounts` | yes | - | Integration test counts |
| `regression` | `TestCounts` | yes | - | Regression test counts |

**`ReplayResult`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `original_scenario_replayed` | `bool` | yes | - | Original exploit scenario was replayed on the patched build |
| `vulnerability_still_reproducible` | `bool` | yes | - | True means the patch failed to fix the bug |
| `evidence_id` | `str` | yes | - | Immutable evidence record id |

**`RemediationOutput`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `root_cause` | `RootCause` | yes | - | Explanation of why the flaw exists |
| `patch` | `PatchInfo or null` | no | - | Patch metadata (null if none produced) |
| `tests` | `RemediationTests` | yes | - | Unit, integration and regression results |
| `replay` | `ReplayResult` | yes | - | Result of replaying the original exploit |
| `remediation_status` | `enum RemediationStatus` | yes | - | Outcome of the remediation attempt |
| `requires_human_approval` | `enum[True]` | no | - | Always true; no automatic merge exists |

**`RemediationResponse`**

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| `schema_version` | `str` | yes | `pattern=^\d+\.\d+\.\d+$` | Contract version, semantic versioning |
| `correlation_id` | `str` | yes | `pattern=^cor_[0-9a-f]{8,}$` | Traces one assessment across agents and logs |
| `project_id` | `str` | yes | `pattern=^prj_[0-9a-f]{8,}$` | Top-level project |
| `engagement_id` | `str` | yes | `pattern=^eng_[0-9a-f]{8,}$` | The authorized assessment and its scope |
| `scan_id` | `str` | yes | `pattern=^scn_[0-9a-f]{8,}$` | One execution of the workflow |
| `task_id` | `str` | yes | `pattern=^tsk_[0-9a-f]{8,}$` | One unit of agent work |
| `agent_run_id` | `str` | yes | `pattern=^run_[0-9a-f]{8,}$` | One agent invocation; retries get new run ids |
| `created_at` | `str` | yes | `pattern=^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` | ISO 8601 UTC timestamp |
| `status` | `enum TaskStatus` | yes | - | Task status (closed enum) |
| `warnings` | `list[str]` | no | - | Non-fatal issues found while running |
| `error` | `ErrorInfo or null` | no | - | Error object when status is not succeeded |
| `metrics` | `Metrics` | yes | - | Resource usage of the run |
| `agent` | `enum[remediation]` | no | - | Official agent name (closed enum) |
| `output` | `RemediationOutput or null` | no | - | Agent-specific result payload (null on failure) |

## 11.12 How the next agent consumes this output

The Orchestrator creates an approval record and shows the diff, test counts and replay evidence to a human reviewer. Only the reviewer's decision can move the patch forward; merging is a human action.

# 12. Complete Execution Example

The table follows the validated example payloads (all timestamps UTC, 2026-11-17).

| Time | Agent | Event |
|---|---|---|
| 09:30:00 | Orchestrator | Receives request; five scope checks pass; plan with 6 stages created |
| 09:30:10 | Code Intelligence, Recon | Start in parallel (`g1`) |
| 09:30:51 | Recon | 2 endpoints, 2 technologies, 1 OWASP reference (marked untrusted) |
| 09:31:02 | Code Intelligence | 86 files; `PATCH /orders/{order_id}` has no authorization check; invariant `inv_order_owner_only` proposed (0.86) |
| 09:31:30 | Vulnerability Research | Hypothesis `hyp_idor_patch_order` (priority 1) with a paired-identity plan; skill `hunt-idor` |
| 09:32:05 | Dynamic Testing | Owner gets 200; non-owner gets 403; **state diff shows `shipping_address` changed** |
| 09:32:50 | Verification | Reproduced 3 of 3; confidence 0.97; severity medium (integrity impact); finding `fnd_0192f200` confirmed |
| 09:34:20 | Remediation | Root cause: write committed before the 403 is produced; patch on `fix/aegistrace-fnd-0192f200`; 42/42 unit, 18/18 integration, 120/120 regression pass; exploit no longer reproduces |
| after | Human reviewer | Approves, rejects or requests changes. Only a human merges |

All durations and token figures in the examples are **illustrative sample values**, not measurements.

# 13. References

- Pydantic: https://docs.pydantic.dev/
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/schema
- CrewAI: https://docs.crewai.com/
- LangChain: https://docs.langchain.com/
- Groq: https://console.groq.com/docs
- Tavily Search API: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter
