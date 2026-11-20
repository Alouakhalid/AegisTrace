# 1. Overview and Design Principles

This document defines how AegisTrace stores, remembers and retrieves information: the memory model, the retrieval pipeline, the PostgreSQL schema and its pgvector usage, retention and security. The DDL in `AegisTrace_Database_SQL_Appendix.sql` was **executed on PostgreSQL 16 with pgvector 0.6.0** and the table reference in Section 5 is generated from that live schema, so the document cannot drift from the SQL.

| Principle | Consequence |
|---|---|
| Prefixed text identifiers equal contract identifiers | A database id and a JSON id are the same string; domains (`prj_id`, `fnd_id`...) reject wrong prefixes |
| Evidence is immutable | `evidence`, `state_snapshots` and `audit_logs` reject UPDATE and DELETE by trigger |
| Relational first | PostgreSQL is the system of record; vectors only help retrieval |
| `jsonb` only for variable payloads | Scope manifests, request bodies and task input/output; everything queried by a rule is a column |
| Secrets are never stored | Only references (`cred_*`); redaction happens before evidence is written |
| No table without a reason | 30 tables; each justified in Section 4 |

# 2. Memory Architecture

![Memory architecture](../diagrams/d10_memory.svg)

## 2.1 The five memory categories

| Category | What it holds | Stored in | Persist / expire | Plaintext secrets |
|---|---|---|---|---|
| A. Working | Current task context, agent state, temporary results | Process memory; the task row records input and output as an execution record | Discarded when the task ends | Never |
| B. Project | Repository structure, frameworks, routes, security invariants, earlier findings | `repositories_analysis`, `code_nodes`, `code_edges`, `endpoints`, `security_invariants`, `memory_items(type=project)` | Persist; items superseded when the commit changes (`superseded_by`) | Never |
| C. Engagement | Scope, scan history, test identities, findings, evidence, decisions | `scope_manifests`, `scans`, `findings`, `evidence`, `memory_items(type=engagement)` | Persist for the engagement, then the retention policy | Never; identities are `credential_ref` only |
| D. Knowledge | Methodologies, vulnerability patterns, skill metadata, reusable strategies | `skills`, `skill_metadata`, `memory_items(type=knowledge)` | Versioned by skill commit | Never |
| E. Remediation | Previous patches, root causes, successful and failed fixes, regression results | `patches`, `patch_tests`, `memory_items(type=remediation)` | Persist; failed fixes are kept as negative knowledge | Never |

## 2.2 Storage kinds compared

| Kind | Definition | Where | Mutable? | Example |
|---|---|---|---|---|
| Relational storage | Structured facts with constraints | PostgreSQL tables | Yes, by rules | `findings.severity` |
| Vector retrieval | Similarity search over embeddings | `embedding` columns, HNSW index | Rebuilt on re-index | Find skill chunks about ownership checks |
| Short-term working state | Context for one task | Process memory | Yes | Partial hypothesis list |
| Long-term project memory | Facts worth reusing across scans | `memory_items` and project tables | Superseded, not edited | "Orders are owned by `user_id`" |
| Execution logs | What ran and how | `agent_tasks`, `agent_runs`, `agent_messages`, structured logs | Append-mostly | Retry attempt 2 of run X |
| Immutable evidence | Proof for a finding | `evidence` (hashed content in the object store), `state_snapshots` | Never | HTTP exchange with SHA-256 |

## 2.3 What must never be stored as plaintext

Passwords, API keys (Groq, Tavily), session tokens, JWTs, cookies, `Authorization` headers and personal data from test responses. Credentials live in a secret manager and travel only as `cred_*` references that are resolved inside the sandbox. Evidence is redacted **before** it is written (following the Claude-BugHunter `evidence-hygiene` guidance), and memory writes pass a secret-pattern filter that rejects the write rather than storing a suspected secret.

# 3. Memory Retrieval

![Memory retrieval pipeline](../diagrams/d11_retrieval.svg)

| Stage | What happens |
|---|---|
| 1. Metadata filter | Restrict by `project_id`, `memory_type`, vulnerability category or phase, and `expires_at IS NULL OR expires_at > now()`. This is what makes retrieval project-specific and prevents cross-project leakage |
| 2a. Keyword retrieval | Full-text `tsvector` rank over keywords and headings; precise for identifiers such as `IDOR` or `hunt-idor` |
| 2b. Vector similarity | Cosine distance over embeddings; finds related wording that keywords miss |
| 3. Hybrid merge | Reciprocal Rank Fusion: `score = sum(1 / (60 + rank_i))` across the two lists, so no scale calibration between ts_rank and cosine is needed |
| 4. Deduplication | Unique `(project_id, memory_type, content_sha256)` on write; at read, drop items with `superseded_by` set |
| 5. Ranking | `final = rrf x importance x freshness` where `freshness = 0.5^(age_days / half_life)` |
| 6. Budget | Fill the token budget in rank order, stop at the budget, and attach attribution (skill name, commit, memory id) |

**Proposed defaults (to be tuned by experiment, not facts).** Half-lives: project 90 days, engagement 30, knowledge 365, remediation 180. Budget: retrieved material at most 25 percent of the model context; at most 3 skill chunks per hypothesis. Retrieved text is delimited and marked as untrusted data in every prompt.

**Skill retrieval** uses the same pipeline against `skill_metadata`, filtered by `vuln_categories` and `phases`. The example query in the SQL appendix runs against the schema; it was exercised on synthetic vectors, which proves it executes but says nothing about retrieval quality. Quality must be measured on real skills in Phase 1.

# 4. Database Architecture

## 4.1 Why 30 tables

All 29 requested entities were evaluated. All are kept because each has a distinct lifecycle or access pattern. One table was added: `finding_evidence`. Evidence must be immutable, so it cannot carry a `finding_id` that is filled in later when a finding is created; a junction table links them without ever updating an evidence row.

| Question | Decision |
|---|---|
| `agent_tasks` vs `agent_runs` | Separate: one task can have several runs (retries), and the contract carries both `task_id` and `agent_run_id` |
| `test_cases` | Stores **test plans** (contract prefix `tpl_`); the name follows the requested entity list |
| `skills` vs `skill_metadata` | Separate: one skill has many retrievable chunks with embeddings |
| `repositories_analysis` | Kept as the per-scan header that code nodes belong to |

**Deliberate denormalization.** `security_invariants.applies_to_node_ids` is an array rather than a junction table because it is read-mostly and always read with the invariant. `agent_tasks.depends_on` is an array for the same reason. `findings` duplicates `endpoint_id` and `invariant_id` from its hypothesis so the findings list needs no joins.

## 4.2 Entity relationship diagrams

Generated from the foreign keys of the live schema. The overview shows how the eight table groups depend on each other; Figures 12a to 12d show the tables inside each group. Foreign keys that cross figures are listed in each table's constraints in Section 5.

![ERD overview](../diagrams/d12_overview.svg)

![ERD a](../diagrams/d12a_erd.svg)

![ERD b](../diagrams/d12b_erd.svg)

![ERD c](../diagrams/d12c_erd.svg)

![ERD d](../diagrams/d12d_erd.svg)

# 5. Table Reference

Generated from the live database: purpose and retention are authored; columns, constraints and indexes come from PostgreSQL catalogs. Retention values are **proposed defaults**, configurable per deployment.

### `agent_messages`

**Purpose.** Validated request/response messages between Orchestrator and agents.

**Retention (proposal).** Proposal: 90 days (large, reproducible from tasks).

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `msg_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `task_id` | `tsk_id` | yes | - |
| `correlation_id` | `text` | no | - |
| `from_agent` | `text` | no | - |
| `to_agent` | `text` | no | - |
| `message_type` | `text` | no | - |
| `schema_version` | `text` | no | - |
| `payload` | `jsonb` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE SET NULL`
- `CHECK ((message_type = ANY (ARRAY['request'::text, 'response'::text, 'event'::text, 'approval_request'::text])))`

**Indexes**

- `agent_messages_correlation_id_idx ON agent_messages USING btree (correlation_id)`
- `UNIQUE agent_messages_pkey ON agent_messages USING btree (id)`
- `agent_messages_scan_id_created_at_idx ON agent_messages USING btree (scan_id, created_at)`

### `agent_runs`

**Purpose.** Each invocation of an agent for a task (retries create rows).

**Retention (proposal).** Proposal: 180 days.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `run_id` | no | - |
| `task_id` | `tsk_id` | no | - |
| `attempt` | `integer` | no | - |
| `status` | `text` | no | - |
| `prompt_version` | `text` | no | - |
| `model` | `text` | no | - |
| `llm_calls` | `integer` | no | `0` |
| `input_tokens` | `integer` | no | `0` |
| `output_tokens` | `integer` | no | `0` |
| `error` | `jsonb` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `UNIQUE (task_id, attempt)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id) ON DELETE CASCADE`
- `CHECK ((attempt >= 1))`
- `CHECK ((status = ANY (ARRAY['running'::text, 'succeeded'::text, 'failed'::text, 'cancelled'::text])))`

**Indexes**

- `UNIQUE agent_runs_pkey ON agent_runs USING btree (id)`
- `UNIQUE agent_runs_task_id_attempt_key ON agent_runs USING btree (task_id, attempt)`
- `agent_runs_task_id_idx ON agent_runs USING btree (task_id)`

### `agent_tasks`

**Purpose.** Units of agent work with dependencies, input and output.

**Retention (proposal).** Proposal: 180 days after scan end.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `tsk_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `agent` | `text` | no | - |
| `stage` | `text` | no | - |
| `status` | `text` | no | `'queued'::text` |
| `depends_on` | `tsk_id[]` | no | `'{}'::tsk_id[]` |
| `input` | `jsonb` | yes | - |
| `output` | `jsonb` | yes | - |
| `error` | `jsonb` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `UNIQUE (scan_id, stage)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((agent = ANY (ARRAY['orchestrator'::text, 'code_intelligence'::text, 'recon'::text, 'vulnerability_research'::text, 'dynamic_testing'::text, 'verification'::text, 'remediation'::text])))`
- `CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'succeeded'::text, 'failed'::text, 'blocked'::text, 'needs_input'::text, 'cancelled'::text])))`

**Indexes**

- `UNIQUE agent_tasks_pkey ON agent_tasks USING btree (id)`
- `UNIQUE agent_tasks_scan_id_stage_key ON agent_tasks USING btree (scan_id, stage)`
- `agent_tasks_scan_id_status_idx ON agent_tasks USING btree (scan_id, status)`

### `approvals`

**Purpose.** Human decisions on patches; the mandatory gate.

**Retention (proposal).** Kept for audit.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `apr_id` | no | - |
| `patch_id` | `pat_id` | no | - |
| `requested_at` | `timestamp with time zone` | no | `now()` |
| `decision` | `text` | no | `'pending'::text` |
| `decided_by` | `usr_id` | yes | - |
| `decided_at` | `timestamp with time zone` | yes | - |
| `comment` | `text` | yes | - |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (decided_by) REFERENCES users(id)`
- `FOREIGN KEY (patch_id) REFERENCES patches(id) ON DELETE CASCADE`
- `CHECK ((((decision = 'pending'::text) AND (decided_by IS NULL) AND (decided_at IS NULL)) OR ((decision <> 'pending'::text) AND (decided_by IS NOT NULL) AND (decided_at IS NOT NULL))))`
- `CHECK ((decision = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'changes_requested'::text])))`

**Indexes**

- `approvals_decision_idx ON approvals USING btree (decision) WHERE (decision = 'pending'::text)`
- `UNIQUE approvals_pkey ON approvals USING btree (id)`

### `audit_logs`

**Purpose.** Append-only log of actions, including blocked ones.

**Retention (proposal).** Proposal: 2 years; never edited.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `ts` | `timestamp with time zone` | no | `now()` |
| `actor_type` | `text` | no | - |
| `actor_id` | `text` | no | - |
| `action` | `text` | no | - |
| `scan_id` | `scn_id` | yes | - |
| `resource_type` | `text` | yes | - |
| `resource_id` | `text` | yes | - |
| `allowed` | `boolean` | no | - |
| `details` | `jsonb` | no | `'{}'::jsonb` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id)`
- `CHECK ((actor_type = ANY (ARRAY['user'::text, 'agent'::text, 'system'::text])))`

**Indexes**

- `UNIQUE audit_logs_pkey ON audit_logs USING btree (id)`
- `audit_logs_scan_id_ts_idx ON audit_logs USING btree (scan_id, ts)`
- `audit_logs_ts_idx ON audit_logs USING btree (ts) WHERE (allowed = false)`

### `code_edges`

**Purpose.** Edges of the code graph (calls, guards, reads, writes, data flow).

**Retention (proposal).** Same as code_nodes.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `analysis_id` | `ran_id` | no | - |
| `src` | `bigint` | no | - |
| `dst` | `bigint` | no | - |
| `kind` | `text` | no | - |
| `props` | `jsonb` | no | `'{}'::jsonb` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE CASCADE`
- `FOREIGN KEY (dst) REFERENCES code_nodes(id) ON DELETE CASCADE`
- `FOREIGN KEY (src) REFERENCES code_nodes(id) ON DELETE CASCADE`
- `CHECK ((kind = ANY (ARRAY['calls'::text, 'imports'::text, 'handles_route'::text, 'guards'::text, 'reads'::text, 'writes'::text, 'data_flow'::text, 'depends_on'::text])))`

**Indexes**

- `code_edges_analysis_id_dst_idx ON code_edges USING btree (analysis_id, dst)`
- `code_edges_analysis_id_src_idx ON code_edges USING btree (analysis_id, src)`
- `UNIQUE code_edges_pkey ON code_edges USING btree (id)`

### `code_nodes`

**Purpose.** Nodes of the code graph (files, functions, routes, checks, models).

**Retention (proposal).** Proposal: 90 days; re-derivable from the commit.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `analysis_id` | `ran_id` | no | - |
| `kind` | `text` | no | - |
| `name` | `text` | no | - |
| `file` | `text` | yes | - |
| `line` | `integer` | yes | - |
| `props` | `jsonb` | no | `'{}'::jsonb` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE CASCADE`
- `CHECK ((kind = ANY (ARRAY['file'::text, 'module'::text, 'function'::text, 'class'::text, 'route'::text, 'auth_check'::text, 'authz_check'::text, 'db_model'::text, 'db_operation'::text, 'dependency'::text])))`

**Indexes**

- `code_nodes_analysis_id_file_idx ON code_nodes USING btree (analysis_id, file)`
- `code_nodes_analysis_id_kind_idx ON code_nodes USING btree (analysis_id, kind)`
- `UNIQUE code_nodes_pkey ON code_nodes USING btree (id)`

### `endpoints`

**Purpose.** Discovered authorized endpoints, linked to code nodes.

**Retention (proposal).** With the scan.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `ep_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `method` | `text` | no | - |
| `path` | `text` | no | - |
| `path_params` | `text[]` | no | `'{}'::text[]` |
| `auth_required` | `boolean` | yes | - |
| `source` | `text` | no | - |
| `code_node_id` | `bigint` | yes | - |

**Constraints**

- `UNIQUE (scan_id, method, path)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (code_node_id) REFERENCES code_nodes(id) ON DELETE SET NULL`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((source = ANY (ARRAY['openapi'::text, 'code_routes'::text, 'crawl'::text])))`

**Indexes**

- `UNIQUE endpoints_pkey ON endpoints USING btree (id)`
- `endpoints_scan_id_idx ON endpoints USING btree (scan_id)`
- `UNIQUE endpoints_scan_id_method_path_key ON endpoints USING btree (scan_id, method, path)`

### `engagements`

**Purpose.** One authorized assessment with attestation, mode and environment.

**Retention (proposal).** Kept for audit for the audit period.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `eng_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `name` | `text` | no | - |
| `assessment_mode` | `text` | no | - |
| `environment` | `text` | no | - |
| `status` | `text` | no | `'draft'::text` |
| `attested_by` | `usr_id` | yes | - |
| `attested_at` | `timestamp with time zone` | yes | - |
| `starts_at` | `timestamp with time zone` | yes | - |
| `ends_at` | `timestamp with time zone` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (attested_by) REFERENCES users(id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `CHECK ((assessment_mode = ANY (ARRAY['code_only'::text, 'dynamic_only'::text, 'full'::text])))`
- `CHECK (((status = 'draft'::text) OR ((attested_by IS NOT NULL) AND (attested_at IS NOT NULL))))`
- `CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at > starts_at)))`
- `CHECK ((environment = ANY (ARRAY['sandbox'::text, 'staging_approved'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'closed'::text])))`

**Indexes**

- `UNIQUE engagements_pkey ON engagements USING btree (id)`
- `engagements_project_id_idx ON engagements USING btree (project_id)`

### `evidence`

**Purpose.** Immutable evidence records pointing to hashed content in the object store.

**Retention (proposal).** Proposal: 1 year after engagement close; legal hold overrides.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `evd_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `kind` | `text` | no | - |
| `content_ref` | `text` | no | - |
| `content_sha256` | `text` | no | - |
| `redacted` | `boolean` | no | `true` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id)`
- `CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CHECK ((kind = ANY (ARRAY['http_exchange'::text, 'state_snapshot'::text, 'state_diff'::text, 'log'::text, 'patch_replay'::text, 'screenshot'::text])))`

**Indexes**

- `UNIQUE evidence_pkey ON evidence USING btree (id)`
- `evidence_scan_id_kind_idx ON evidence USING btree (scan_id, kind)`

### `finding_evidence`

**Purpose.** Junction linking findings to evidence without mutating evidence rows.

**Retention (proposal).** With the finding.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `finding_id` | `fnd_id` | no | - |
| `evidence_id` | `evd_id` | no | - |
| `role` | `text` | no | - |

**Constraints**

- `PRIMARY KEY (finding_id, evidence_id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE`
- `CHECK ((role = ANY (ARRAY['request'::text, 'response'::text, 'state_diff'::text, 'replay'::text, 'supporting'::text])))`

**Indexes**

- `finding_evidence_evidence_id_idx ON finding_evidence USING btree (evidence_id)`
- `UNIQUE finding_evidence_pkey ON finding_evidence USING btree (finding_id, evidence_id)`

### `findings`

**Purpose.** Verified findings with verdict, severity, reproducibility and status.

**Retention (proposal).** Kept; they are the product.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `fnd_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `hypothesis_id` | `hyp_id` | no | - |
| `endpoint_id` | `ep_id` | no | - |
| `invariant_id` | `inv_id` | no | - |
| `verdict` | `text` | no | - |
| `confidence` | `numeric(3,2)` | no | - |
| `severity` | `text` | yes | - |
| `cvss_vector` | `text` | yes | - |
| `runs` | `integer` | no | - |
| `reproduced` | `integer` | no | - |
| `invariant_violated` | `boolean` | no | - |
| `status` | `text` | no | `'open'::text` |
| `rejection_reasons` | `text[]` | no | `'{}'::text[]` |
| `verified_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (endpoint_id) REFERENCES endpoints(id)`
- `FOREIGN KEY (hypothesis_id) REFERENCES vulnerability_hypotheses(id)`
- `FOREIGN KEY (invariant_id) REFERENCES security_invariants(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `FOREIGN KEY (verified_by_run) REFERENCES agent_runs(id)`
- `CHECK (((reproduced >= 0) AND (reproduced <= runs)))`
- `CHECK (((verdict <> 'confirmed'::text) OR ((severity IS NOT NULL) AND invariant_violated AND (reproduced >= 1))))`
- `CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))`
- `CHECK ((runs >= 1))`
- `CHECK ((severity = ANY (ARRAY['informational'::text, 'low'::text, 'medium'::text, 'high'::text, 'critical'::text])))`
- `CHECK ((status = ANY (ARRAY['open'::text, 'patch_proposed'::text, 'fixed'::text, 'accepted_risk'::text, 'wont_fix'::text])))`
- `CHECK ((verdict = ANY (ARRAY['confirmed'::text, 'unconfirmed'::text, 'rejected'::text])))`

**Indexes**

- `UNIQUE findings_pkey ON findings USING btree (id)`
- `findings_scan_id_severity_idx ON findings USING btree (scan_id, severity)`
- `findings_status_idx ON findings USING btree (status) WHERE (status = 'open'::text)`

### `memory_items`

**Purpose.** Long-term memory with embeddings, importance, expiry and deduplication.

**Retention (proposal).** Per type: see Section 2; expiry via expires_at.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `mem_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `scan_id` | `scn_id` | yes | - |
| `memory_type` | `text` | no | - |
| `key` | `text` | no | - |
| `content` | `text` | no | - |
| `metadata` | `jsonb` | no | `'{}'::jsonb` |
| `content_sha256` | `text` | no | - |
| `importance` | `real` | no | `0.5` |
| `embedding` | `vector(384)` | yes | - |
| `superseded_by` | `mem_id` | yes | - |
| `expires_at` | `timestamp with time zone` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (project_id, memory_type, content_sha256)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE SET NULL`
- `FOREIGN KEY (superseded_by) REFERENCES memory_items(id)`
- `CHECK (((importance >= (0)::double precision) AND (importance <= (1)::double precision)))`
- `CHECK ((memory_type = ANY (ARRAY['project'::text, 'engagement'::text, 'knowledge'::text, 'remediation'::text])))`

**Indexes**

- `memory_items_embedding_idx ON memory_items USING hnsw (embedding vector_cosine_ops)`
- `memory_items_expires_at_idx ON memory_items USING btree (expires_at) WHERE (expires_at IS NOT NULL)`
- `UNIQUE memory_items_pkey ON memory_items USING btree (id)`
- `UNIQUE memory_items_project_id_memory_type_content_sha256_key ON memory_items USING btree (project_id, memory_type, content_sha256)`
- `memory_items_project_id_memory_type_idx ON memory_items USING btree (project_id, memory_type)`

### `patch_tests`

**Purpose.** Unit, integration, regression and replay results per patch.

**Retention (proposal).** With the patch.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `ptt_id` | no | - |
| `patch_id` | `pat_id` | no | - |
| `suite` | `text` | no | - |
| `total` | `integer` | no | - |
| `passed` | `integer` | no | - |
| `failed` | `integer` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (patch_id) REFERENCES patches(id) ON DELETE CASCADE`
- `CHECK (((passed + failed) <= total))`
- `CHECK ((suite = ANY (ARRAY['unit'::text, 'integration'::text, 'regression'::text, 'replay'::text])))`

**Indexes**

- `UNIQUE patch_tests_pkey ON patch_tests USING btree (id)`

### `patches`

**Purpose.** Patch attempts on isolated branches with diffs and root cause.

**Retention (proposal).** Kept with the finding.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `pat_id` | no | - |
| `finding_id` | `fnd_id` | no | - |
| `attempt` | `integer` | no | - |
| `branch` | `text` | no | - |
| `diff_ref` | `text` | no | - |
| `diff_sha256` | `text` | no | - |
| `changed_files` | `text[]` | no | - |
| `root_cause` | `jsonb` | no | - |
| `status` | `text` | no | `'proposed'::text` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (finding_id, attempt)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE`
- `CHECK (((attempt >= 1) AND (attempt <= 3)))`
- `CHECK ((status = ANY (ARRAY['proposed'::text, 'tests_failed'::text, 'ready_for_review'::text, 'approved'::text, 'rejected'::text, 'merged_by_human'::text, 'superseded'::text])))`

**Indexes**

- `UNIQUE patches_finding_id_attempt_key ON patches USING btree (finding_id, attempt)`
- `patches_finding_id_idx ON patches USING btree (finding_id)`
- `UNIQUE patches_pkey ON patches USING btree (id)`

### `projects`

**Purpose.** Top-level container for a target application.

**Retention (proposal).** Until archived by the owner; then project policy.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `prj_id` | no | - |
| `owner_id` | `usr_id` | no | - |
| `name` | `text` | no | - |
| `language` | `text` | no | `'python'::text` |
| `framework_hint` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `archived_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `UNIQUE (owner_id, name)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (owner_id) REFERENCES users(id)`
- `CHECK ((language = 'python'::text))`

**Indexes**

- `projects_owner_id_idx ON projects USING btree (owner_id)`
- `UNIQUE projects_owner_id_name_key ON projects USING btree (owner_id, name)`
- `UNIQUE projects_pkey ON projects USING btree (id)`

### `reports`

**Purpose.** Generated report files with hashes and generator version.

**Retention (proposal).** Kept; regenerable from data but preserved as issued.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `rpt_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `format` | `text` | no | - |
| `version` | `integer` | no | `1` |
| `content_ref` | `text` | no | - |
| `content_sha256` | `text` | no | - |
| `generator_version` | `text` | no | - |
| `generated_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (scan_id, format, version)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((format = ANY (ARRAY['pdf'::text, 'html'::text, 'markdown'::text, 'json'::text])))`

**Indexes**

- `UNIQUE reports_pkey ON reports USING btree (id)`
- `UNIQUE reports_scan_id_format_version_key ON reports USING btree (scan_id, format, version)`

### `repositories`

**Purpose.** Source repositories (GitHub or ZIP) of a project.

**Retention (proposal).** With the project.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `rep_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `source_type` | `text` | no | - |
| `url` | `text` | no | - |
| `default_ref` | `text` | no | `'main'::text` |
| `latest_commit` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (project_id, url)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `CHECK ((latest_commit ~ '^[0-9a-f]{7,40}$'::text))`
- `CHECK ((source_type = ANY (ARRAY['github'::text, 'zip'::text])))`

**Indexes**

- `UNIQUE repositories_pkey ON repositories USING btree (id)`
- `UNIQUE repositories_project_id_url_key ON repositories USING btree (project_id, url)`

### `repositories_analysis`

**Purpose.** One analysis header per scan: commit, frameworks, entry points, warnings.

**Retention (proposal).** Proposal: 1 year.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `ran_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `repository_id` | `rep_id` | no | - |
| `commit_sha` | `text` | no | - |
| `files_analyzed` | `integer` | no | - |
| `frameworks` | `text[]` | no | `'{}'::text[]` |
| `entry_points` | `text[]` | no | `'{}'::text[]` |
| `warnings` | `jsonb` | no | `'[]'::jsonb` |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (scan_id)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (repository_id) REFERENCES repositories(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`

**Indexes**

- `UNIQUE repositories_analysis_pkey ON repositories_analysis USING btree (id)`
- `UNIQUE repositories_analysis_scan_id_key ON repositories_analysis USING btree (scan_id)`

### `scans`

**Purpose.** One execution of the workflow with its correlation id.

**Retention (proposal).** Kept with the engagement.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `scn_id` | no | - |
| `engagement_id` | `eng_id` | no | - |
| `scope_manifest_id` | `scm_id` | no | - |
| `repository_id` | `rep_id` | yes | - |
| `commit_sha` | `text` | yes | - |
| `correlation_id` | `text` | no | - |
| `status` | `text` | no | `'queued'::text` |
| `config` | `jsonb` | no | `'{}'::jsonb` |
| `requested_by` | `usr_id` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `started_at` | `timestamp with time zone` | yes | - |
| `finished_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `UNIQUE (correlation_id)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (engagement_id) REFERENCES engagements(id)`
- `FOREIGN KEY (repository_id) REFERENCES repositories(id)`
- `FOREIGN KEY (requested_by) REFERENCES users(id)`
- `FOREIGN KEY (scope_manifest_id) REFERENCES scope_manifests(id)`
- `CHECK ((commit_sha ~ '^[0-9a-f]{7,40}$'::text))`
- `CHECK ((correlation_id ~ '^cor_[0-9a-f]{8,}$'::text))`
- `CHECK ((status = ANY (ARRAY['queued'::text, 'running'::text, 'awaiting_approval'::text, 'completed'::text, 'failed'::text, 'cancelled'::text, 'blocked'::text])))`

**Indexes**

- `UNIQUE scans_correlation_id_key ON scans USING btree (correlation_id)`
- `scans_engagement_id_created_at_idx ON scans USING btree (engagement_id, created_at DESC)`
- `UNIQUE scans_pkey ON scans USING btree (id)`
- `scans_status_idx ON scans USING btree (status) WHERE (status = ANY (ARRAY['queued'::text, 'running'::text, 'awaiting_approval'::text]))`

### `scope_manifests`

**Purpose.** Versioned scope manifests with a content hash.

**Retention (proposal).** Kept with the engagement; never edited, only versioned.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `scm_id` | no | - |
| `engagement_id` | `eng_id` | no | - |
| `version` | `integer` | no | - |
| `manifest` | `jsonb` | no | - |
| `manifest_sha256` | `text` | no | - |
| `valid` | `boolean` | no | `false` |
| `validated_at` | `timestamp with time zone` | yes | - |
| `created_by` | `usr_id` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (engagement_id, version)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by) REFERENCES users(id)`
- `FOREIGN KEY (engagement_id) REFERENCES engagements(id) ON DELETE CASCADE`
- `CHECK ((version > 0))`

**Indexes**

- `UNIQUE scope_manifests_engagement_id_version_key ON scope_manifests USING btree (engagement_id, version)`
- `UNIQUE scope_manifests_pkey ON scope_manifests USING btree (id)`

### `security_invariants`

**Purpose.** Candidate and accepted rules the application must satisfy.

**Retention (proposal).** Project lifetime; retire, do not delete.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `inv_id` | no | - |
| `project_id` | `prj_id` | no | - |
| `analysis_id` | `ran_id` | yes | - |
| `statement` | `text` | no | - |
| `kind` | `text` | no | - |
| `source` | `text` | no | - |
| `confidence` | `numeric(3,2)` | no | - |
| `status` | `text` | no | `'candidate'::text` |
| `applies_to_node_ids` | `bigint[]` | no | `'{}'::bigint[]` |
| `reviewed_by` | `usr_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (analysis_id) REFERENCES repositories_analysis(id) ON DELETE SET NULL`
- `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE`
- `FOREIGN KEY (reviewed_by) REFERENCES users(id)`
- `CHECK (((confidence >= (0)::numeric) AND (confidence <= (1)::numeric)))`
- `CHECK ((kind = ANY (ARRAY['ownership'::text, 'role_restriction'::text, 'state_transition'::text, 'authentication_required'::text])))`
- `CHECK ((source = ANY (ARRAY['code'::text, 'declared_policy'::text])))`
- `CHECK ((status = ANY (ARRAY['candidate'::text, 'accepted'::text, 'rejected'::text, 'retired'::text])))`

**Indexes**

- `UNIQUE security_invariants_pkey ON security_invariants USING btree (id)`
- `security_invariants_project_id_status_idx ON security_invariants USING btree (project_id, status)`

### `skill_metadata`

**Purpose.** Retrievable skill chunks with keywords and embeddings.

**Retention (proposal).** Rebuilt on re-index; follows skills.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `skm_id` | no | - |
| `skill_id` | `skl_id` | no | - |
| `chunk_index` | `integer` | no | - |
| `heading` | `text` | yes | - |
| `content_excerpt` | `text` | no | - |
| `token_count` | `integer` | no | - |
| `phases` | `text[]` | no | `'{}'::text[]` |
| `vuln_categories` | `text[]` | no | `'{}'::text[]` |
| `keywords` | `tsvector` | yes | - |
| `embedding` | `vector(384)` | yes | - |

**Constraints**

- `UNIQUE (skill_id, chunk_index)`
- `PRIMARY KEY (id)`
- `FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE`
- `CHECK ((token_count > 0))`

**Indexes**

- `skill_metadata_embedding_idx ON skill_metadata USING hnsw (embedding vector_cosine_ops)`
- `skill_metadata_keywords_idx ON skill_metadata USING gin (keywords)`
- `UNIQUE skill_metadata_pkey ON skill_metadata USING btree (id)`
- `UNIQUE skill_metadata_skill_id_chunk_index_key ON skill_metadata USING btree (skill_id, chunk_index)`
- `skill_metadata_vuln_categories_idx ON skill_metadata USING gin (vuln_categories)`

### `skill_usage_logs`

**Purpose.** Which skill chunks were injected into which agent run, with tokens.

**Retention (proposal).** Proposal: 1 year (attribution trail).

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `bigint` | no | - |
| `skill_id` | `skl_id` | no | - |
| `agent_run_id` | `run_id` | no | - |
| `chunk_ids` | `skm_id[]` | no | - |
| `score` | `real` | no | - |
| `tokens_injected` | `integer` | no | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE`
- `FOREIGN KEY (skill_id) REFERENCES skills(id)`

**Indexes**

- `skill_usage_logs_agent_run_id_idx ON skill_usage_logs USING btree (agent_run_id)`
- `UNIQUE skill_usage_logs_pkey ON skill_usage_logs USING btree (id)`

### `skills`

**Purpose.** Indexed Claude-BugHunter skills with commit, path and licenses.

**Retention (proposal).** Versioned; old commits kept while referenced by usage logs.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `skl_id` | no | - |
| `name` | `text` | no | - |
| `source_repo` | `text` | no | - |
| `source_commit` | `text` | no | - |
| `path` | `text` | no | - |
| `description` | `text` | no | - |
| `upstream_sources` | `text[]` | no | `'{}'::text[]` |
| `license_code` | `text` | no | `'MIT'::text` |
| `license_content` | `text` | no | `'CC-BY-4.0'::text` |
| `category` | `text` | yes | - |
| `enabled` | `boolean` | no | `true` |
| `indexed_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `UNIQUE (name, source_commit)`
- `PRIMARY KEY (id)`

**Indexes**

- `skills_category_idx ON skills USING btree (category) WHERE enabled`
- `UNIQUE skills_name_source_commit_key ON skills USING btree (name, source_commit)`
- `UNIQUE skills_pkey ON skills USING btree (id)`

### `state_snapshots`

**Purpose.** Immutable before/after rows of database state in the sandbox.

**Retention (proposal).** Same as evidence.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `snp_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `execution_id` | `exe_id` | yes | - |
| `sandbox_id` | `text` | no | - |
| `phase` | `text` | no | - |
| `table_name` | `text` | no | - |
| `row_key` | `jsonb` | no | - |
| `row_data` | `jsonb` | no | - |
| `row_hash` | `text` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `taken_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (execution_id) REFERENCES test_executions(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((phase = ANY (ARRAY['before'::text, 'after'::text])))`

**Indexes**

- `state_snapshots_execution_id_idx ON state_snapshots USING btree (execution_id)`
- `UNIQUE state_snapshots_pkey ON state_snapshots USING btree (id)`
- `state_snapshots_scan_id_table_name_idx ON state_snapshots USING btree (scan_id, table_name)`

### `test_cases`

**Purpose.** Test plans (contract prefix tpl_) with steps and state checks.

**Retention (proposal).** With the scan.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `tpl_id` | no | - |
| `hypothesis_id` | `hyp_id` | no | - |
| `method` | `text` | no | - |
| `steps` | `jsonb` | no | - |
| `identities` | `text[]` | no | - |
| `expected_secure_behavior` | `text` | no | - |
| `state_checks` | `jsonb` | no | `'[]'::jsonb` |
| `status` | `text` | no | `'approved'::text` |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (hypothesis_id) REFERENCES vulnerability_hypotheses(id) ON DELETE CASCADE`
- `CHECK (((method <> 'paired_identity'::text) OR (cardinality(identities) >= 2)))`
- `CHECK ((method = ANY (ARRAY['paired_identity'::text, 'single_identity'::text, 'workflow_sequence'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'approved'::text, 'executed'::text])))`

**Indexes**

- `test_cases_hypothesis_id_idx ON test_cases USING btree (hypothesis_id)`
- `UNIQUE test_cases_pkey ON test_cases USING btree (id)`

### `test_executions`

**Purpose.** Each executed request of a test plan, one row per identity step.

**Retention (proposal).** With the scan; redacted.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `exe_id` | no | - |
| `test_case_id` | `tpl_id` | no | - |
| `task_id` | `tsk_id` | no | - |
| `identity_id` | `text` | no | - |
| `case_label` | `text` | no | - |
| `request` | `jsonb` | no | - |
| `response_status` | `integer` | yes | - |
| `response_excerpt` | `text` | yes | - |
| `sandbox_id` | `text` | no | - |
| `evidence_id` | `evd_id` | yes | - |
| `started_at` | `timestamp with time zone` | no | `now()` |
| `finished_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (evidence_id) REFERENCES evidence(id)`
- `FOREIGN KEY (task_id) REFERENCES agent_tasks(id)`
- `FOREIGN KEY (test_case_id) REFERENCES test_cases(id)`

**Indexes**

- `UNIQUE test_executions_pkey ON test_executions USING btree (id)`
- `test_executions_test_case_id_idx ON test_executions USING btree (test_case_id)`

### `users`

**Purpose.** Application users and roles; identity lives at the external provider.

**Retention (proposal).** Life of the account; disable, do not delete.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `usr_id` | no | - |
| `email` | `text` | no | - |
| `display_name` | `text` | no | - |
| `role` | `text` | no | - |
| `auth_subject` | `text` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |
| `disabled_at` | `timestamp with time zone` | yes | - |

**Constraints**

- `UNIQUE (auth_subject)`
- `UNIQUE (email)`
- `PRIMARY KEY (id)`
- `CHECK ((role = ANY (ARRAY['admin'::text, 'analyst'::text, 'reviewer'::text, 'viewer'::text])))`

**Indexes**

- `UNIQUE users_auth_subject_key ON users USING btree (auth_subject)`
- `UNIQUE users_email_key ON users USING btree (email)`
- `UNIQUE users_pkey ON users USING btree (id)`

### `vulnerability_hypotheses`

**Purpose.** Testable hypotheses with category, rationale and priority.

**Retention (proposal).** With the scan.

| Column | Type | Nullable | Default |
|---|---|---|---|
| `id` | `hyp_id` | no | - |
| `scan_id` | `scn_id` | no | - |
| `endpoint_id` | `ep_id` | no | - |
| `invariant_id` | `inv_id` | no | - |
| `category` | `text` | no | - |
| `title` | `text` | no | - |
| `rationale` | `text` | no | - |
| `priority` | `smallint` | no | - |
| `status` | `text` | no | `'proposed'::text` |
| `skill_refs` | `text[]` | no | `'{}'::text[]` |
| `created_by_run` | `run_id` | yes | - |
| `created_at` | `timestamp with time zone` | no | `now()` |

**Constraints**

- `PRIMARY KEY (id)`
- `FOREIGN KEY (created_by_run) REFERENCES agent_runs(id)`
- `FOREIGN KEY (endpoint_id) REFERENCES endpoints(id)`
- `FOREIGN KEY (invariant_id) REFERENCES security_invariants(id)`
- `FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE`
- `CHECK ((category = ANY (ARRAY['broken_access_control'::text, 'idor'::text, 'authn_authz_flaw'::text, 'business_logic'::text])))`
- `CHECK (((priority >= 1) AND (priority <= 5)))`
- `CHECK ((status = ANY (ARRAY['proposed'::text, 'testing'::text, 'confirmed'::text, 'unconfirmed'::text, 'rejected'::text])))`

**Indexes**

- `UNIQUE vulnerability_hypotheses_pkey ON vulnerability_hypotheses USING btree (id)`
- `vulnerability_hypotheses_scan_id_priority_idx ON vulnerability_hypotheses USING btree (scan_id, priority)`


# 6. pgvector Integration

![pgvector integration](../diagrams/d13_pgvector.svg)

- Two vector columns: `skill_metadata.embedding` and `memory_items.embedding`, type `vector(384)`.
- **The dimension 384 is a proposal.** It must equal the output size of the embedding model chosen in Phase 1; changing the model means re-embedding and rebuilding the index.
- Index: HNSW with `vector_cosine_ops`; query with the `<=>` operator and `ORDER BY ... LIMIT k`.
- Always combine vector search with metadata filters. With an approximate index, a restrictive filter applied after the index scan can return fewer than `k` rows; newer pgvector releases add options for this, so verify against the pgvector version you deploy (the validated version here is 0.6.0).
- Vectors are a retrieval aid only. Losing them costs a re-index, never data.

# 7. Data Lifecycle and Retention

![Data lifecycle](../diagrams/d14_lifecycle.svg)

| Data | Proposed retention | Notes |
|---|---|---|
| Evidence, state snapshots | 1 year after engagement close | Content in the object store; legal hold overrides |
| Findings, patches, approvals, reports | Kept | They are the deliverable and the decision record |
| Audit logs | 2 years | Append-only; blocked actions (`allowed=false`) are indexed |
| Agent messages, tasks and runs | 90 to 180 days | Reproducible summaries stay in findings |
| Code nodes and edges | 90 days | Re-derivable from the pinned commit |
| Memory items | By `expires_at` | Superseded items are retained until purged |
| Skill usage logs | 1 year | Attribution trail for CC BY 4.0 compliance |

Purging runs under a dedicated role that owns the purge procedure. Application roles hold no DELETE privilege on immutable tables.

# 8. Security

- **Roles (proposal):** `app_rw` (no DELETE or TRUNCATE on `evidence`, `state_snapshots`, `audit_logs`), `app_ro` for the dashboard, `purge_role` for retention.
- **Immutability:** row triggers block UPDATE and DELETE. Row triggers do not block `TRUNCATE`; revoke that privilege from application roles.
- **Multi-tenancy:** not in the MVP. If added, use row-level security keyed by `project_id`.
- **Transport and storage:** TLS to the database; encryption at rest at the disk or managed-service layer; encrypted backups.
- **Integrity:** every evidence row stores a SHA-256 of its content; Verification re-checks it before use.
- **Auditability:** scope-gate decisions, approvals and blocked actions are written to `audit_logs`.

# 9. Validation Performed

| Check | Result |
|---|---|
| Full DDL executed on PostgreSQL 16 with pgvector 0.6.0 | Succeeded; 30 tables |
| Confirmed finding without severity rejected | Passed |
| UPDATE on `evidence` rejected | Passed |
| DELETE on `audit_logs` rejected | Passed |
| Wrong id prefix rejected by domain | Passed |
| Paired test with one identity rejected | Passed |
| Decided approval without reviewer rejected | Passed |
| Duplicate memory item rejected | Passed |
| Hybrid retrieval query executes on pgvector | Passed (synthetic vectors; no quality claim) |

# 10. Known Limitations

- Not load-tested; index and partition choices at scale are untested. `audit_logs`, `code_nodes` and `code_edges` are candidates for partitioning.
- The 384-dimension embedding and all retention periods are proposals.
- pgvector behavior was validated on 0.6.0 only.
- Row-level security and role grants are described but not included in the DDL.

# 11. References

- PostgreSQL 16 documentation: https://www.postgresql.org/docs/16/
- pgvector: https://github.com/pgvector/pgvector
- Claude-BugHunter: https://github.com/elementalsouls/Claude-BugHunter
