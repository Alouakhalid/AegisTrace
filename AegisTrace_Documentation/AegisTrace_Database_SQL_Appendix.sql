-- =====================================================================
-- NOT THE DATABASE THE APPLICATION OPENS.
-- AegisDatabase in "memory and database/database.py" loads
-- "memory and database/schema.sql" (SQLite). This file is a PostgreSQL
-- port kept for a future migration. Do not treat it as executed by the app.
-- =====================================================================
-- AegisTrace - PostgreSQL schema (proposal v1.0.0, not loaded at runtime)
-- Target: PostgreSQL 16 + pgvector (a lab check, not the product database)
-- IDs are prefixed text so DB identifiers equal contract identifiers.
-- Embedding dimension (384) is a PROPOSAL: it must match the embedding
-- model chosen in Phase 1. Changing it requires re-embedding.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- identifier domains (one per entity prefix) ----------
DO $$
DECLARE p text;
BEGIN
  FOREACH p IN ARRAY ARRAY['usr','prj','rep','eng','scm','scn','tsk','run','msg','ran','inv','ep','hyp',
                           'tpl','exe','snp','fnd','evd','skl','skm','pat','ptt','apr','rpt','mem']
  LOOP
    EXECUTE format('CREATE DOMAIN %I AS text CHECK (VALUE ~ %L)', p||'_id', '^'||p||'_[0-9a-f]{8,}$');
  END LOOP;
END $$;

-- ---------- 1. access ----------
CREATE TABLE users (
  id            usr_id PRIMARY KEY,
  email         text NOT NULL UNIQUE,
  display_name  text NOT NULL,
  role          text NOT NULL CHECK (role IN ('admin','analyst','reviewer','viewer')),
  auth_subject  text UNIQUE,                 -- id at the external identity provider; no passwords stored here
  created_at    timestamptz NOT NULL DEFAULT now(),
  disabled_at   timestamptz
);

CREATE TABLE projects (
  id             prj_id PRIMARY KEY,
  owner_id       usr_id NOT NULL REFERENCES users(id),
  name           text NOT NULL,
  language       text NOT NULL DEFAULT 'python' CHECK (language IN ('python')),
  framework_hint text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  archived_at    timestamptz,
  UNIQUE (owner_id, name)
);

CREATE TABLE repositories (
  id            rep_id PRIMARY KEY,
  project_id    prj_id NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_type   text NOT NULL CHECK (source_type IN ('github','zip')),
  url           text NOT NULL,
  default_ref   text NOT NULL DEFAULT 'main',
  latest_commit text CHECK (latest_commit ~ '^[0-9a-f]{7,40}$'),
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, url)
);

-- ---------- 2. engagements and scope ----------
CREATE TABLE engagements (
  id              eng_id PRIMARY KEY,
  project_id      prj_id NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name            text NOT NULL,
  assessment_mode text NOT NULL CHECK (assessment_mode IN ('code_only','dynamic_only','full')),
  environment     text NOT NULL CHECK (environment IN ('sandbox','staging_approved')),  -- production is rejected in the MVP
  status          text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','closed')),
  attested_by     usr_id REFERENCES users(id),
  attested_at     timestamptz,
  starts_at       timestamptz,
  ends_at         timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (status = 'draft' OR (attested_by IS NOT NULL AND attested_at IS NOT NULL)),
  CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at)
);

CREATE TABLE scope_manifests (
  id              scm_id PRIMARY KEY,
  engagement_id   eng_id NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
  version         int NOT NULL CHECK (version > 0),
  manifest        jsonb NOT NULL,               -- allowed hosts/methods, forbidden paths, identities, window
  manifest_sha256 text NOT NULL,
  valid           boolean NOT NULL DEFAULT false,
  validated_at    timestamptz,
  created_by      usr_id NOT NULL REFERENCES users(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (engagement_id, version)
);

CREATE TABLE scans (
  id                scn_id PRIMARY KEY,
  engagement_id     eng_id NOT NULL REFERENCES engagements(id),
  scope_manifest_id scm_id NOT NULL REFERENCES scope_manifests(id),
  repository_id     rep_id REFERENCES repositories(id),
  commit_sha        text CHECK (commit_sha ~ '^[0-9a-f]{7,40}$'),
  correlation_id    text NOT NULL UNIQUE CHECK (correlation_id ~ '^cor_[0-9a-f]{8,}$'),
  status            text NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued','running','awaiting_approval','completed','failed','cancelled','blocked')),
  config            jsonb NOT NULL DEFAULT '{}',
  requested_by      usr_id NOT NULL REFERENCES users(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  started_at        timestamptz,
  finished_at       timestamptz
);

-- ---------- 3. agent execution ----------
CREATE TABLE agent_tasks (
  id          tsk_id PRIMARY KEY,
  scan_id     scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  agent       text NOT NULL CHECK (agent IN ('orchestrator','code_intelligence','recon','vulnerability_research',
                                             'dynamic_testing','verification','remediation')),
  stage       text NOT NULL,
  status      text NOT NULL DEFAULT 'queued'
              CHECK (status IN ('queued','running','succeeded','failed','blocked','needs_input','cancelled')),
  depends_on  tsk_id[] NOT NULL DEFAULT '{}',
  input       jsonb,
  output      jsonb,
  error       jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  UNIQUE (scan_id, stage)
);

CREATE TABLE agent_runs (                     -- one row per invocation; a task may have several (retries)
  id             run_id PRIMARY KEY,
  task_id        tsk_id NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
  attempt        int NOT NULL CHECK (attempt >= 1),
  status         text NOT NULL CHECK (status IN ('running','succeeded','failed','cancelled')),
  prompt_version text NOT NULL,
  model          text NOT NULL,                -- configured model id, never hardcoded in code
  llm_calls      int NOT NULL DEFAULT 0,
  input_tokens   int NOT NULL DEFAULT 0,
  output_tokens  int NOT NULL DEFAULT 0,
  error          jsonb,
  started_at     timestamptz NOT NULL DEFAULT now(),
  finished_at    timestamptz,
  UNIQUE (task_id, attempt)
);

CREATE TABLE agent_messages (
  id             msg_id PRIMARY KEY,
  scan_id        scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  task_id        tsk_id REFERENCES agent_tasks(id) ON DELETE SET NULL,
  correlation_id text NOT NULL,
  from_agent     text NOT NULL,
  to_agent       text NOT NULL,
  message_type   text NOT NULL CHECK (message_type IN ('request','response','event','approval_request')),
  schema_version text NOT NULL,
  payload        jsonb NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- ---------- 4. code intelligence ----------
CREATE TABLE repositories_analysis (
  id             ran_id PRIMARY KEY,
  scan_id        scn_id NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
  repository_id  rep_id NOT NULL REFERENCES repositories(id),
  commit_sha     text NOT NULL,
  files_analyzed int NOT NULL,
  frameworks     text[] NOT NULL DEFAULT '{}',
  entry_points   text[] NOT NULL DEFAULT '{}',
  warnings       jsonb NOT NULL DEFAULT '[]',
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE code_nodes (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  analysis_id ran_id NOT NULL REFERENCES repositories_analysis(id) ON DELETE CASCADE,
  kind        text NOT NULL CHECK (kind IN ('file','module','function','class','route','auth_check','authz_check','db_model','db_operation','dependency')),
  name        text NOT NULL,
  file        text,
  line        int,
  props       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE code_edges (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  analysis_id ran_id NOT NULL REFERENCES repositories_analysis(id) ON DELETE CASCADE,
  src         bigint NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
  dst         bigint NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
  kind        text NOT NULL CHECK (kind IN ('calls','imports','handles_route','guards','reads','writes','data_flow','depends_on')),
  props       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE security_invariants (
  id                  inv_id PRIMARY KEY,
  project_id          prj_id NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  analysis_id         ran_id REFERENCES repositories_analysis(id) ON DELETE SET NULL,
  statement           text NOT NULL,
  kind                text NOT NULL CHECK (kind IN ('ownership','role_restriction','state_transition','authentication_required')),
  source              text NOT NULL CHECK (source IN ('code','declared_policy')),
  confidence          numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  status              text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate','accepted','rejected','retired')),
  applies_to_node_ids bigint[] NOT NULL DEFAULT '{}',   -- deliberate denormalization: avoids a junction table for a read-mostly list
  reviewed_by         usr_id REFERENCES users(id),
  created_at          timestamptz NOT NULL DEFAULT now()
);

-- ---------- 5. recon ----------
CREATE TABLE endpoints (
  id            ep_id PRIMARY KEY,
  scan_id       scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  method        text NOT NULL,
  path          text NOT NULL,
  path_params   text[] NOT NULL DEFAULT '{}',
  auth_required boolean,
  source        text NOT NULL CHECK (source IN ('openapi','code_routes','crawl')),
  code_node_id  bigint REFERENCES code_nodes(id) ON DELETE SET NULL,   -- link between runtime surface and code
  UNIQUE (scan_id, method, path)
);

-- ---------- 6. research ----------
CREATE TABLE vulnerability_hypotheses (
  id           hyp_id PRIMARY KEY,
  scan_id      scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  endpoint_id  ep_id NOT NULL REFERENCES endpoints(id),
  invariant_id inv_id NOT NULL REFERENCES security_invariants(id),
  category     text NOT NULL CHECK (category IN ('broken_access_control','idor','authn_authz_flaw','business_logic')),
  title        text NOT NULL,
  rationale    text NOT NULL,
  priority     smallint NOT NULL CHECK (priority BETWEEN 1 AND 5),
  status       text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','testing','confirmed','unconfirmed','rejected')),
  skill_refs   text[] NOT NULL DEFAULT '{}',
  created_by_run run_id REFERENCES agent_runs(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE test_cases (                     -- stores TEST PLANS (contract id prefix tpl_)
  id                       tpl_id PRIMARY KEY,
  hypothesis_id            hyp_id NOT NULL REFERENCES vulnerability_hypotheses(id) ON DELETE CASCADE,
  method                   text NOT NULL CHECK (method IN ('paired_identity','single_identity','workflow_sequence')),
  steps                    jsonb NOT NULL,
  identities               text[] NOT NULL,
  expected_secure_behavior text NOT NULL,
  state_checks             jsonb NOT NULL DEFAULT '[]',
  status                   text NOT NULL DEFAULT 'approved' CHECK (status IN ('draft','approved','executed')),
  created_at               timestamptz NOT NULL DEFAULT now(),
  CHECK (method <> 'paired_identity' OR cardinality(identities) >= 2)
);

-- ---------- 7. evidence (immutable) ----------
CREATE TABLE evidence (
  id             evd_id PRIMARY KEY,
  scan_id        scn_id NOT NULL REFERENCES scans(id),
  kind           text NOT NULL CHECK (kind IN ('http_exchange','state_snapshot','state_diff','log','patch_replay','screenshot')),
  content_ref    text NOT NULL,                  -- object-store path; content never mutated
  content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  redacted       boolean NOT NULL DEFAULT true,  -- secrets and PII masked before write
  created_by_run run_id REFERENCES agent_runs(id),
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE test_executions (
  id               exe_id PRIMARY KEY,
  test_case_id     tpl_id NOT NULL REFERENCES test_cases(id),
  task_id          tsk_id NOT NULL REFERENCES agent_tasks(id),
  identity_id      text NOT NULL,
  case_label       text NOT NULL,
  request          jsonb NOT NULL,               -- credentials replaced by credential_ref
  response_status  int,
  response_excerpt text,
  sandbox_id       text NOT NULL,
  evidence_id      evd_id REFERENCES evidence(id),
  started_at       timestamptz NOT NULL DEFAULT now(),
  finished_at      timestamptz
);

CREATE TABLE state_snapshots (
  id           snp_id PRIMARY KEY,
  scan_id      scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  execution_id exe_id REFERENCES test_executions(id),
  sandbox_id   text NOT NULL,
  phase        text NOT NULL CHECK (phase IN ('before','after')),
  table_name   text NOT NULL,
  row_key      jsonb NOT NULL,
  row_data     jsonb NOT NULL,
  row_hash     text NOT NULL,
  evidence_id  evd_id REFERENCES evidence(id),
  taken_at     timestamptz NOT NULL DEFAULT now()
);

-- ---------- 8. findings ----------
CREATE TABLE findings (
  id                 fnd_id PRIMARY KEY,
  scan_id            scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  hypothesis_id      hyp_id NOT NULL REFERENCES vulnerability_hypotheses(id),
  endpoint_id        ep_id NOT NULL REFERENCES endpoints(id),
  invariant_id       inv_id NOT NULL REFERENCES security_invariants(id),
  verdict            text NOT NULL CHECK (verdict IN ('confirmed','unconfirmed','rejected')),
  confidence         numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  severity           text CHECK (severity IN ('informational','low','medium','high','critical')),
  cvss_vector        text,
  runs               int NOT NULL CHECK (runs >= 1),
  reproduced         int NOT NULL CHECK (reproduced BETWEEN 0 AND runs),
  invariant_violated boolean NOT NULL,
  status             text NOT NULL DEFAULT 'open' CHECK (status IN ('open','patch_proposed','fixed','accepted_risk','wont_fix')),
  rejection_reasons  text[] NOT NULL DEFAULT '{}',
  verified_by_run    run_id REFERENCES agent_runs(id),
  created_at         timestamptz NOT NULL DEFAULT now(),
  CHECK (verdict <> 'confirmed' OR (severity IS NOT NULL AND invariant_violated AND reproduced >= 1))
);

CREATE TABLE finding_evidence (               -- junction: keeps evidence rows immutable (no finding_id column to update)
  finding_id  fnd_id NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  evidence_id evd_id NOT NULL REFERENCES evidence(id),
  role        text NOT NULL CHECK (role IN ('request','response','state_diff','replay','supporting')),
  PRIMARY KEY (finding_id, evidence_id)
);

-- ---------- 9. skills ----------
CREATE TABLE skills (
  id              skl_id PRIMARY KEY,
  name            text NOT NULL,
  source_repo     text NOT NULL,
  source_commit   text NOT NULL,
  path            text NOT NULL,
  description     text NOT NULL,
  upstream_sources text[] NOT NULL DEFAULT '{}',    -- from SKILL.md frontmatter 'sources'
  license_code    text NOT NULL DEFAULT 'MIT',
  license_content text NOT NULL DEFAULT 'CC-BY-4.0',
  category        text,
  enabled         boolean NOT NULL DEFAULT true,
  indexed_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name, source_commit)
);

CREATE TABLE skill_metadata (                 -- retrievable chunks of a skill
  id               skm_id PRIMARY KEY,
  skill_id         skl_id NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  chunk_index      int NOT NULL,
  heading          text,
  content_excerpt  text NOT NULL,
  token_count      int NOT NULL CHECK (token_count > 0),
  phases           text[] NOT NULL DEFAULT '{}',
  vuln_categories  text[] NOT NULL DEFAULT '{}',
  keywords         tsvector,
  embedding        vector(384),
  UNIQUE (skill_id, chunk_index)
);

CREATE TABLE skill_usage_logs (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  skill_id         skl_id NOT NULL REFERENCES skills(id),
  agent_run_id     run_id NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  chunk_ids        skm_id[] NOT NULL,
  score            real NOT NULL,
  tokens_injected  int NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- ---------- 10. remediation and approval ----------
CREATE TABLE patches (
  id            pat_id PRIMARY KEY,
  finding_id    fnd_id NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  attempt       int NOT NULL CHECK (attempt BETWEEN 1 AND 3),
  branch        text NOT NULL,
  diff_ref      text NOT NULL,
  diff_sha256   text NOT NULL,
  changed_files text[] NOT NULL,
  root_cause    jsonb NOT NULL,
  status        text NOT NULL DEFAULT 'proposed'
                CHECK (status IN ('proposed','tests_failed','ready_for_review','approved','rejected','merged_by_human','superseded')),
  created_by_run run_id REFERENCES agent_runs(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (finding_id, attempt)
);

CREATE TABLE patch_tests (
  id          ptt_id PRIMARY KEY,
  patch_id    pat_id NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
  suite       text NOT NULL CHECK (suite IN ('unit','integration','regression','replay')),
  total       int NOT NULL, passed int NOT NULL, failed int NOT NULL,
  evidence_id evd_id REFERENCES evidence(id),
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  CHECK (passed + failed <= total)
);

CREATE TABLE approvals (
  id           apr_id PRIMARY KEY,
  patch_id     pat_id NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
  requested_at timestamptz NOT NULL DEFAULT now(),
  decision     text NOT NULL DEFAULT 'pending' CHECK (decision IN ('pending','approved','rejected','changes_requested')),
  decided_by   usr_id REFERENCES users(id),
  decided_at   timestamptz,
  comment      text,
  CHECK ((decision = 'pending' AND decided_by IS NULL AND decided_at IS NULL)
      OR (decision <> 'pending' AND decided_by IS NOT NULL AND decided_at IS NOT NULL))
);

CREATE TABLE reports (
  id                rpt_id PRIMARY KEY,
  scan_id           scn_id NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  format            text NOT NULL CHECK (format IN ('pdf','html','markdown','json')),
  version           int NOT NULL DEFAULT 1,
  content_ref       text NOT NULL,
  content_sha256    text NOT NULL,
  generator_version text NOT NULL,
  generated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scan_id, format, version)
);

-- ---------- 11. audit and memory ----------
CREATE TABLE audit_logs (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ts            timestamptz NOT NULL DEFAULT now(),
  actor_type    text NOT NULL CHECK (actor_type IN ('user','agent','system')),
  actor_id      text NOT NULL,
  action        text NOT NULL,
  scan_id       scn_id REFERENCES scans(id),
  resource_type text,
  resource_id   text,
  allowed       boolean NOT NULL,                -- false = blocked action (for example ScopeViolation)
  details       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE memory_items (
  id            mem_id PRIMARY KEY,
  project_id    prj_id NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  scan_id       scn_id REFERENCES scans(id) ON DELETE SET NULL,
  memory_type   text NOT NULL CHECK (memory_type IN ('project','engagement','knowledge','remediation')),
  key           text NOT NULL,
  content       text NOT NULL,
  metadata      jsonb NOT NULL DEFAULT '{}',
  content_sha256 text NOT NULL,
  importance    real NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
  embedding     vector(384),
  superseded_by mem_id REFERENCES memory_items(id),
  expires_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, memory_type, content_sha256)       -- deduplication
);

-- ---------- indexes ----------
CREATE INDEX ON projects (owner_id);
CREATE INDEX ON engagements (project_id);
CREATE INDEX ON scans (engagement_id, created_at DESC);
CREATE INDEX ON scans (status) WHERE status IN ('queued','running','awaiting_approval');
CREATE INDEX ON agent_tasks (scan_id, status);
CREATE INDEX ON agent_runs (task_id);
CREATE INDEX ON agent_messages (scan_id, created_at);
CREATE INDEX ON agent_messages (correlation_id);
CREATE INDEX ON code_nodes (analysis_id, kind);
CREATE INDEX ON code_nodes (analysis_id, file);
CREATE INDEX ON code_edges (analysis_id, src);
CREATE INDEX ON code_edges (analysis_id, dst);
CREATE INDEX ON security_invariants (project_id, status);
CREATE INDEX ON endpoints (scan_id);
CREATE INDEX ON vulnerability_hypotheses (scan_id, priority);
CREATE INDEX ON test_cases (hypothesis_id);
CREATE INDEX ON test_executions (test_case_id);
CREATE INDEX ON state_snapshots (execution_id);
CREATE INDEX ON state_snapshots (scan_id, table_name);
CREATE INDEX ON evidence (scan_id, kind);
CREATE INDEX ON findings (scan_id, severity);
CREATE INDEX ON findings (status) WHERE status = 'open';
CREATE INDEX ON finding_evidence (evidence_id);
CREATE INDEX ON patches (finding_id);
CREATE INDEX ON approvals (decision) WHERE decision = 'pending';
CREATE INDEX ON audit_logs (scan_id, ts);
CREATE INDEX ON audit_logs (ts) WHERE allowed = false;
CREATE INDEX ON skills (category) WHERE enabled;
CREATE INDEX ON skill_metadata USING gin (keywords);
CREATE INDEX ON skill_metadata USING gin (vuln_categories);
CREATE INDEX ON skill_metadata USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON skill_usage_logs (agent_run_id);
CREATE INDEX ON memory_items (project_id, memory_type);
CREATE INDEX ON memory_items (expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX ON memory_items USING hnsw (embedding vector_cosine_ops);

-- ---------- immutability ----------
CREATE FUNCTION forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% is append-only: % not allowed', TG_TABLE_NAME, TG_OP;
END $$;
CREATE TRIGGER evidence_immutable        BEFORE UPDATE OR DELETE ON evidence        FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER state_snapshots_immutable BEFORE UPDATE OR DELETE ON state_snapshots FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER audit_logs_immutable      BEFORE UPDATE OR DELETE ON audit_logs      FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
-- Retention jobs run under a dedicated role that owns the purge procedure; application roles hold no DELETE on these tables.

-- ---------- hybrid retrieval example (skills) ----------
-- :qvec = query embedding, :qtext = query text, :cat = vulnerability category
-- WITH kw AS (
--   SELECT id, ts_rank(keywords, plainto_tsquery('english', :qtext)) AS s FROM skill_metadata
--   WHERE vuln_categories @> ARRAY[:cat] AND keywords @@ plainto_tsquery('english', :qtext) ORDER BY s DESC LIMIT 20),
-- vec AS (
--   SELECT id, 1 - (embedding <=> :qvec) AS s FROM skill_metadata
--   WHERE vuln_categories @> ARRAY[:cat] ORDER BY embedding <=> :qvec LIMIT 20)
-- SELECT id, sum(1.0/(60+rank)) AS rrf FROM (
--   SELECT id, row_number() OVER (ORDER BY s DESC) AS rank FROM kw
--   UNION ALL SELECT id, row_number() OVER (ORDER BY s DESC) FROM vec) t
-- GROUP BY id ORDER BY rrf DESC LIMIT 5;
