CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY CHECK (id LIKE 'usr_%'),
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','analyst','reviewer','viewer')),
  auth_subject TEXT UNIQUE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  disabled_at TEXT
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY CHECK (id LIKE 'prj_%'),
  owner_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'python' CHECK (language IN ('python')),
  framework_hint TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  archived_at TEXT,
  UNIQUE (owner_id, name)
);

CREATE TABLE IF NOT EXISTS repositories (
  id TEXT PRIMARY KEY CHECK (id LIKE 'rep_%'),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('github','zip')),
  url TEXT NOT NULL,
  default_ref TEXT NOT NULL DEFAULT 'main',
  latest_commit TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (project_id, url)
);

CREATE TABLE IF NOT EXISTS engagements (
  id TEXT PRIMARY KEY CHECK (id LIKE 'eng_%'),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  assessment_mode TEXT NOT NULL CHECK (assessment_mode IN ('code_only','dynamic_only','full')),
  environment TEXT NOT NULL CHECK (environment IN ('sandbox','staging_approved')),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','closed')),
  attested_by TEXT REFERENCES users(id),
  attested_at TEXT,
  starts_at TEXT,
  ends_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS scope_manifests (
  id TEXT PRIMARY KEY CHECK (id LIKE 'scm_%'),
  engagement_id TEXT NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK (version > 0),
  manifest TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  valid INTEGER NOT NULL DEFAULT 0,
  validated_at TEXT,
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (engagement_id, version)
);

CREATE TABLE IF NOT EXISTS scans (
  id TEXT PRIMARY KEY CHECK (id LIKE 'scn_%'),
  engagement_id TEXT NOT NULL REFERENCES engagements(id),
  scope_manifest_id TEXT NOT NULL REFERENCES scope_manifests(id),
  repository_id TEXT REFERENCES repositories(id),
  commit_sha TEXT,
  correlation_id TEXT NOT NULL UNIQUE CHECK (correlation_id LIKE 'cor_%'),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','awaiting_approval','completed','failed','cancelled','blocked')),
  config TEXT NOT NULL DEFAULT '{}',
  requested_by TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_tasks (
  id TEXT PRIMARY KEY CHECK (id LIKE 'tsk_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  agent TEXT NOT NULL CHECK (agent IN ('orchestrator','code_intelligence','recon','vulnerability_research','dynamic_testing','verification','remediation')),
  stage TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','blocked','needs_input','cancelled')),
  depends_on TEXT NOT NULL DEFAULT '[]',
  input TEXT,
  output TEXT,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  finished_at TEXT,
  UNIQUE (scan_id, stage)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY CHECK (id LIKE 'run_%'),
  task_id TEXT NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
  attempt INTEGER NOT NULL CHECK (attempt >= 1),
  status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed','cancelled')),
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  llm_calls INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  finished_at TEXT,
  UNIQUE (task_id, attempt)
);

CREATE TABLE IF NOT EXISTS agent_messages (
  id TEXT PRIMARY KEY CHECK (id LIKE 'msg_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  task_id TEXT REFERENCES agent_tasks(id) ON DELETE SET NULL,
  correlation_id TEXT NOT NULL,
  from_agent TEXT NOT NULL,
  to_agent TEXT NOT NULL,
  message_type TEXT NOT NULL CHECK (message_type IN ('request','response','event','approval_request')),
  schema_version TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS repositories_analysis (
  id TEXT PRIMARY KEY CHECK (id LIKE 'ran_%'),
  scan_id TEXT NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
  repository_id TEXT NOT NULL REFERENCES repositories(id),
  commit_sha TEXT NOT NULL,
  files_analyzed INTEGER NOT NULL,
  frameworks TEXT NOT NULL DEFAULT '[]',
  entry_points TEXT NOT NULL DEFAULT '[]',
  warnings TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS code_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  analysis_id TEXT NOT NULL REFERENCES repositories_analysis(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('file','module','function','class','route','auth_check','authz_check','db_model','db_operation','dependency')),
  name TEXT NOT NULL,
  file TEXT,
  line INTEGER,
  props TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS code_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  analysis_id TEXT NOT NULL REFERENCES repositories_analysis(id) ON DELETE CASCADE,
  src INTEGER NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
  dst INTEGER NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('calls','imports','handles_route','guards','reads','writes','data_flow','depends_on')),
  props TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS security_invariants (
  id TEXT PRIMARY KEY CHECK (id LIKE 'inv_%'),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  analysis_id TEXT REFERENCES repositories_analysis(id) ON DELETE SET NULL,
  statement TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ownership','role_restriction','state_transition','authentication_required')),
  source TEXT NOT NULL CHECK (source IN ('code','declared_policy')),
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate','accepted','rejected','retired')),
  applies_to_node_ids TEXT NOT NULL DEFAULT '[]',
  reviewed_by TEXT REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS endpoints (
  id TEXT PRIMARY KEY CHECK (id LIKE 'ep_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  path_params TEXT NOT NULL DEFAULT '[]',
  auth_required INTEGER,
  source TEXT NOT NULL CHECK (source IN ('openapi','code_routes','crawl')),
  code_node_id INTEGER REFERENCES code_nodes(id) ON DELETE SET NULL,
  UNIQUE (scan_id, method, path)
);

CREATE TABLE IF NOT EXISTS vulnerability_hypotheses (
  id TEXT PRIMARY KEY CHECK (id LIKE 'hyp_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  endpoint_id TEXT NOT NULL REFERENCES endpoints(id),
  invariant_id TEXT NOT NULL REFERENCES security_invariants(id),
  category TEXT NOT NULL CHECK (category IN ('broken_access_control','idor','authn_authz_flaw','business_logic')),
  title TEXT NOT NULL,
  rationale TEXT NOT NULL,
  priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','testing','confirmed','unconfirmed','rejected')),
  skill_refs TEXT NOT NULL DEFAULT '[]',
  created_by_run TEXT REFERENCES agent_runs(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS test_cases (
  id TEXT PRIMARY KEY CHECK (id LIKE 'tpl_%'),
  hypothesis_id TEXT NOT NULL REFERENCES vulnerability_hypotheses(id) ON DELETE CASCADE,
  method TEXT NOT NULL CHECK (method IN ('paired_identity','single_identity','workflow_sequence')),
  steps TEXT NOT NULL,
  identities TEXT NOT NULL,
  expected_secure_behavior TEXT NOT NULL,
  state_checks TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('draft','approved','executed')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY CHECK (id LIKE 'evd_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id),
  kind TEXT NOT NULL CHECK (kind IN ('http_exchange','state_snapshot','state_diff','log','patch_replay','screenshot')),
  content_ref TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  redacted INTEGER NOT NULL DEFAULT 1,
  created_by_run TEXT REFERENCES agent_runs(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS test_executions (
  id TEXT PRIMARY KEY CHECK (id LIKE 'exe_%'),
  test_case_id TEXT NOT NULL REFERENCES test_cases(id),
  task_id TEXT NOT NULL REFERENCES agent_tasks(id),
  identity_id TEXT NOT NULL,
  case_label TEXT NOT NULL,
  request TEXT NOT NULL,
  response_status INTEGER,
  response_excerpt TEXT,
  sandbox_id TEXT NOT NULL,
  evidence_id TEXT REFERENCES evidence(id),
  started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS state_snapshots (
  id TEXT PRIMARY KEY CHECK (id LIKE 'snp_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  execution_id TEXT REFERENCES test_executions(id),
  sandbox_id TEXT NOT NULL,
  phase TEXT NOT NULL CHECK (phase IN ('before','after')),
  table_name TEXT NOT NULL,
  row_key TEXT NOT NULL,
  row_data TEXT NOT NULL,
  row_hash TEXT NOT NULL,
  evidence_id TEXT REFERENCES evidence(id),
  taken_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY CHECK (id LIKE 'fnd_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  hypothesis_id TEXT NOT NULL REFERENCES vulnerability_hypotheses(id),
  endpoint_id TEXT NOT NULL REFERENCES endpoints(id),
  invariant_id TEXT NOT NULL REFERENCES security_invariants(id),
  verdict TEXT NOT NULL CHECK (verdict IN ('confirmed','unconfirmed','rejected')),
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  severity TEXT CHECK (severity IN ('informational','low','medium','high','critical')),
  cvss_vector TEXT,
  runs INTEGER NOT NULL CHECK (runs >= 1),
  reproduced INTEGER NOT NULL CHECK (reproduced BETWEEN 0 AND runs),
  invariant_violated INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','patch_proposed','fixed','accepted_risk','wont_fix')),
  rejection_reasons TEXT NOT NULL DEFAULT '[]',
  verified_by_run TEXT REFERENCES agent_runs(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS finding_evidence (
  finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  role TEXT NOT NULL CHECK (role IN ('request','response','state_diff','replay','supporting')),
  PRIMARY KEY (finding_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY CHECK (id LIKE 'skl_%'),
  name TEXT NOT NULL,
  source_repo TEXT NOT NULL,
  source_commit TEXT NOT NULL,
  path TEXT NOT NULL,
  description TEXT NOT NULL,
  upstream_sources TEXT NOT NULL DEFAULT '[]',
  license_code TEXT NOT NULL DEFAULT 'MIT',
  license_content TEXT NOT NULL DEFAULT 'CC-BY-4.0',
  category TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  indexed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (name, source_commit)
);

CREATE TABLE IF NOT EXISTS skill_metadata (
  id TEXT PRIMARY KEY CHECK (id LIKE 'skm_%'),
  skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  heading TEXT,
  content_excerpt TEXT NOT NULL,
  token_count INTEGER NOT NULL CHECK (token_count > 0),
  phases TEXT NOT NULL DEFAULT '[]',
  vuln_categories TEXT NOT NULL DEFAULT '[]',
  keywords TEXT,
  embedding TEXT,
  UNIQUE (skill_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS skill_usage_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  agent_run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  chunk_ids TEXT NOT NULL,
  score REAL NOT NULL,
  tokens_injected INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS patches (
  id TEXT PRIMARY KEY CHECK (id LIKE 'pat_%'),
  finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  attempt INTEGER NOT NULL CHECK (attempt BETWEEN 1 AND 3),
  branch TEXT NOT NULL,
  diff_ref TEXT NOT NULL,
  diff_sha256 TEXT NOT NULL,
  changed_files TEXT NOT NULL,
  root_cause TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','tests_failed','ready_for_review','approved','rejected','merged_by_human','superseded')),
  created_by_run TEXT REFERENCES agent_runs(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (finding_id, attempt)
);

CREATE TABLE IF NOT EXISTS patch_tests (
  id TEXT PRIMARY KEY CHECK (id LIKE 'ptt_%'),
  patch_id TEXT NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
  suite TEXT NOT NULL CHECK (suite IN ('unit','integration','regression','replay')),
  total INTEGER NOT NULL,
  passed INTEGER NOT NULL,
  failed INTEGER NOT NULL,
  evidence_id TEXT REFERENCES evidence(id),
  started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY CHECK (id LIKE 'apr_%'),
  patch_id TEXT NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
  requested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  decision TEXT NOT NULL DEFAULT 'pending' CHECK (decision IN ('pending','approved','rejected','changes_requested')),
  decided_by TEXT REFERENCES users(id),
  decided_at TEXT,
  comment TEXT
);

CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY CHECK (id LIKE 'rpt_%'),
  scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  format TEXT NOT NULL CHECK (format IN ('pdf','html','markdown','json')),
  version INTEGER NOT NULL DEFAULT 1,
  content_ref TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  generator_version TEXT NOT NULL,
  generated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (scan_id, format, version)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  actor_type TEXT NOT NULL CHECK (actor_type IN ('user','agent','system')),
  actor_id TEXT NOT NULL,
  action TEXT NOT NULL,
  scan_id TEXT REFERENCES scans(id),
  resource_type TEXT,
  resource_id TEXT,
  allowed INTEGER NOT NULL,
  details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS memory_items (
  id TEXT PRIMARY KEY CHECK (id LIKE 'mem_%'),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  scan_id TEXT REFERENCES scans(id) ON DELETE SET NULL,
  memory_type TEXT NOT NULL CHECK (memory_type IN ('project','engagement','knowledge','remediation')),
  key TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata TEXT NOT NULL DEFAULT '{}',
  content_sha256 TEXT NOT NULL,
  importance REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
  embedding TEXT,
  superseded_by TEXT REFERENCES memory_items(id),
  expires_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  UNIQUE (project_id, memory_type, content_sha256)
);

CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence
BEGIN
  SELECT RAISE(ABORT, 'evidence is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence
BEGIN
  SELECT RAISE(ABORT, 'evidence is append-only: DELETE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS state_snapshots_no_update BEFORE UPDATE ON state_snapshots
BEGIN
  SELECT RAISE(ABORT, 'state_snapshots is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS state_snapshots_no_delete BEFORE DELETE ON state_snapshots
BEGIN
  SELECT RAISE(ABORT, 'state_snapshots is append-only: DELETE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs
BEGIN
  SELECT RAISE(ABORT, 'audit_logs is append-only: UPDATE not allowed');
END;

CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs
BEGIN
  SELECT RAISE(ABORT, 'audit_logs is append-only: DELETE not allowed');
END;