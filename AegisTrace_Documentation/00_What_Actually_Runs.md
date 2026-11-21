# AegisTrace — what the repository actually runs

Date: 2026-11-21. This file is the description of the code that starts with `python3 backend/run.py`. Older PDFs under `01_Master_Handbooks/`, `02_Agent_Architecture/`, and `03_Memory_Database/`, and the long markdown in `12_Quality_Assurance/source_markdown/`, describe a design target. Where they disagree with this file, this file follows the source.

## How to start it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
python3 backend/run.py
```

The console is `http://127.0.0.1:8000`. Interactive API docs are `http://127.0.0.1:8000/docs`.

Optional environment variables read by the agents and `backend/integration_service.py`: `GROQ_API_KEY`, `GROQ_MODEL` (default in the root README is `llama-3.3-70b-versatile`), `TAVILY_API_KEY`. Dynamic database snapshots look for `AEGIS_SANDBOX_DB`. If that variable is unset, the scan skips live probing.

## Stack that is in the process

| Piece | Where it lives | What it is |
|---|---|---|
| HTTP API | `backend/app.py` | FastAPI 2.0.0, CORS open, static files from `frontend/` |
| Scan runner | `backend/pipeline.py` | `ScanExecutionManager.run_pipeline` |
| Database | `memory and database/database.py` | SQLite. Default connection is `:memory:` unless a path is passed. Schema file: `memory and database/schema.sql` (30 tables) |
| UI | `frontend/index.html`, `frontend/js/app.js`, `frontend/js/views/*.js` | Vanilla JavaScript hash router. Eighteen views, from `#landing` through `#supporting` |
| Agents | `agents/*/` | Seven modules. CrewAI is imported by the agent modules |
| Code parsing | `tools/code_intel_tools.py` | Tree-sitter Python, the stdlib `ast` module, NetworkX |
| Skills | `backend/bughunter_router.py` | Reads `skills/Claude-BugHunter/skills/*/SKILL.md` from disk and maps categories to skill names |
| External search | `backend/integration_service.py` | Tavily, only when a key is present. Missing key is an offline skip, not a fabricated CVE list |
| HTTP probing tools | `tools/dynamic_testing_tools.py` | HTTPX, a scope gate, and an in-process Flask app in `dummy_web/` |

These are not in the running process: Next.js, React, TypeScript, PostgreSQL, pgvector, a Docker sandbox started by the pipeline, and an automatic git merge.

## Seven agents, and what a scan actually calls

The modules exist:

| Module | Entry |
|---|---|
| `agents/orchestrator_agent/orchestrator_agent.py` | `OrchestratorAgent.run_orchestration` |
| `agents/code_intelligence_agent/code_intelligence_agent.py` | `run_code_intelligence` |
| `agents/recon_agent/recon_agent.py` | `run_recon` |
| `agents/vulnerability_research_agent/vuln_research_agent.py` | `run_vulnerability_research`. The pipeline imports `run_vuln_research`, which is not defined, so this stage always logs a warning and does not run the function |
| `agents/dynamic_testing_agent/dynamic_testing_agent.py` | `DynamicTestingAgent` / `run_dynamic_testing` |
| `agents/verification_agent/verification_agent.py` | `VerificationAgent` / `run_verification` |
| `agents/remediation_agent/remediation_agent.py` | `RemediationAgent` / `run_remediation` |

`ScanExecutionManager.run_pipeline` calls the orchestrator, code intelligence, and recon, each inside its own `try`. A failure there is logged and the scan continues. The vulnerability-research import name does not exist, so that call does not happen.

It does **not** call dynamic testing, verification, or remediation:

- Dynamic testing only logs a line. If `AEGIS_SANDBOX_DB` is unset it says probing was skipped. If the variable is set, the branch still only writes a log line. `DynamicTestingAgent` is not constructed.
- Verification does not call `VerificationAgent`. It copies `repo_intel["potential_risk_areas"]` into in-memory finding dicts, sets `confidence` to `0.92`, and sets `line_number` to `17`. The status string is `confirmed` when any invariant was derived, otherwise `needs_verification`. Neither value is written through `findings.verdict`.
- Remediation constructs `RemediationAgent` when those dicts exist and does not call `run_remediation`. `patches` stays empty.

So a completed scan is a static pass plus skill routing plus logs. It is not a reproduced exploit, a state diff, or a tested patch.

## What gets stored

On a scan the pipeline tries, and swallows errors:

1. User `usr_admin_001` (this id is not 8 hex digits; the SQLite check is only `LIKE 'usr_%'`, so the insert is allowed).
2. A project, an engagement, a scope manifest, and a scan row.
3. Endpoints with ids `ep_{scan_id}_{index}`. The documented pattern `ep_[a-z0-9_]+` allows this. The PostgreSQL domain `ep_[0-9a-f]{8,}` would reject it.
4. Invariants returned by code intelligence.
5. Hypotheses. The insert passes status `approved` and a category taken from `vulnerability_type`. The SQLite table only allows status `proposed|testing|confirmed|unconfirmed|rejected` and category `broken_access_control|idor|authn_authz_flaw|business_logic`. Rows that do not match are dropped by the bare `except`.

The in-memory “confirmed” findings are returned in the pipeline dict and kept on `active_scans`. They are not inserted into `findings`.

`POST /api/v1/projects` calls `create_repository` with `source_type='git'`. `repositories.source_type` allows only `github` and `zip`, so that insert fails.

`GET /api/v1/stats/overview` counts findings with `status = 'resolved'`. The `findings.status` check constraint is `open|patch_proposed|fixed|accepted_risk|wont_fix`. A resolved count from that query is always zero. The security score uses `verdict = 'confirmed'`, which does match the schema.

Evidence, state snapshots, and audit logs have SQLite triggers that abort `UPDATE` and `DELETE`. That part of the schema is real.

Embeddings in `skill_metadata.embedding` and `memory_items.embedding` are `TEXT`. There is no vector type and no hybrid SQL retrieval function in the running schema.

## HTTP API that exists

Implemented on `backend/app.py`:

| Method | Path |
|---|---|
| GET | `/api/v1/health` |
| GET | `/api/v1/stats/overview` |
| GET, POST | `/api/v1/projects` |
| POST | `/api/v1/scans` |
| GET | `/api/v1/scans`, `/api/v1/scans/{scan_id}`, `/api/v1/scans/{scan_id}/logs` |
| WS | `/ws/scans/{scan_id}` |
| POST | `/api/v1/repositories/analyze`, `/api/v1/assessments` |
| GET | `/api/v1/assessments/{id}`, `.../events`, `.../findings` |
| GET | `/api/v1/categories` |
| GET, POST | `/api/v1/integrations/tavily/health`, `/api/v1/integrations/tavily/test` |
| GET | `/api/v1/integrations/bifrost/health` |
| POST | `/api/v1/findings/{id}/verify`, `/api/v1/findings/{id}/remediate` |
| GET | `/api/v1/findings`, `/api/v1/findings/{id}` |
| GET | `/api/v1/code-intel/{scan_id}` |
| GET | `/api/v1/approvals` |
| POST | `/api/v1/approvals/{patch_id}/action` |
| GET | `/api/v1/skills` |
| GET | `/api/v1/benchmarks` |
| GET | `/api/v1/reports/{scan_id}`, `/api/v1/reports/{scan_id}/export` |
| GET | `/api/v1/audit-logs`, `/api/v1/notifications`, `/api/v1/settings` |

Two responses are placeholders, not measurements:

- `GET /api/v1/benchmarks` reads each agent's `evaluation_report.csv` when the file parses. If parsing fails, or no total row is usable, the handler returns precision, recall, and F1 of `1.0` with `total_evaluations: 0`. The CSV files that do exist are small contract checks (the orchestrator file records 15 valid workflows and 15 scope violations). They are not a multi-tenant exploit corpus, and the handler still forces `reproduction_rate` and `patch_success_rate` to `1.0`.
- `GET /api/v1/reports/{scan_id}` returns a fixed certificate: `findings_count: 1`, `resolved_count: 0`, and `Zero_False_Positives: true`, ignoring the scan row.

## Contracts

Pydantic models used by the orchestrator are in `agents/orchestrator_agent/validation.py`. The documentation copy is `10_Technical_Appendices/agent_contracts_pydantic.py`, and the JSON Schema export is `AegisTrace_Agent_JSON_Schemas.json` (duplicated at the package root and under `10_Technical_Appendices/`). The orchestrator validator loads the root JSON file. The path is resolved from the repository root, not a hard-coded home directory.

Identifier prefixes in those models (`prj_`, `eng_`, `scn_`, `tsk_`, `run_`, `cor_`, `scm_` plus at least eight hex digits) match what `run_pipeline` generates with `uuid.uuid4().hex[:12]`.

## Skills

`BugHunterSkillRouter` maps assessment categories to skill directory names. The default full scan selects `idor_access_control`, `authentication`, `injection`, `data_security`, `api_security`, and `dependencies`. Skills are text loaded from `SKILL.md`. They are not extra agents and they are not executed as code by the router.

License files in the cloned tree: `skills/Claude-BugHunter/LICENSE` (MIT for code) and `LICENSE-CONTENT` (CC BY 4.0 for skill text). This package does not copy skill bodies into the PDFs.

## UI routes

`frontend/js/app.js` switches on the hash: `landing`, `auth`, `dashboard`, `projects`, `wizard`, `workspace`, `code_intel`, `surface`, `findings`, `finding_details`, `verification`, `remediation`, `approvals`, `reports`, `skills`, `benchmarks`, `settings`, `supporting`.

## What the older documents got wrong

| Claim in the Edition 2 sources | Code |
|---|---|
| UI is Next.js, React, TypeScript, React Flow | `frontend/` is vanilla JavaScript |
| System of record is PostgreSQL 16 + pgvector, and the DDL was the live schema | `AegisDatabase._init_schema` executes the SQLite file |
| A scan runs paired-identity tests, three replays, and a patch with pytest | Those stages are log lines. The agent classes are not invoked |
| Confirmed findings are rows with a verdict, severity, and evidence hash | Pipeline findings are Python dicts. `GET /api/v1/reports/{id}` invents a certificate |
| Benchmark aggregate 100% precision / 98.7% recall | CSV files are small local checks. The API fills `1.0` when a file does not parse, and always reports reproduction and patch success as `1.0` |
| Diagrams live at `../diagrams/` | Sources are `11_Architecture_Diagrams/*.svg` |

The PostgreSQL script remains in this folder as a migration draft. It is labeled at the top of the file. Do not point the app at it.

## PDFs

The six PDFs were built from the design markdown. They are not regenerated by this correction. Treat `00_What_Actually_Runs.md` and `00_What_Actually_Runs_AR.md` as the current description until those PDFs are rebuilt from a source that matches the code.
