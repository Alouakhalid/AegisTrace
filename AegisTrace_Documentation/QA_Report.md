# QA notes — documentation versus the running code

Date: 2026-11-21. The canonical write-up is `00_What_Actually_Runs.md` (Arabic: `00_What_Actually_Runs_AR.md`).

## Corrected in this pass

- Package README no longer presents the Edition 2 PDFs as the description of the running system.
- PostgreSQL appendix (both copies) is labeled as a migration draft. `AegisDatabase` loads `memory and database/schema.sql`.
- Diagram links in the design markdown and in `gen_agent_doc.py` / `gen_memdb.py` point at `11_Architecture_Diagrams/`, not a missing `diagrams/` folder.
- Design markdown sources carry a banner that points at the running-system file.
- `agents/orchestrator_agent/validation.py` loads `AegisTrace_Agent_JSON_Schemas.json` from the repository root. The previous path was an absolute path on one machine.

## Claims that the code does not support

Checked against `backend/pipeline.py`, `backend/app.py`, and `memory and database/schema.sql`:

1. A scan does not call `DynamicTestingAgent`, `VerificationAgent.run` / `run_verification`, or `RemediationAgent.run_remediation`. Those stages write logs. Verification copies static `potential_risk_areas` into memory with confidence `0.92` and line `17`.
2. Those in-memory findings are not inserted into `findings`.
3. Hypothesis inserts use status `approved`, which the table check rejects, and the exception is ignored.
4. `POST /api/v1/projects` stores repositories as `source_type='git'`. The column allows `github` and `zip` only.
5. Overview stats count `findings.status = 'resolved'`. The allowed statuses are `open`, `patch_proposed`, `fixed`, `accepted_risk`, `wont_fix`.
6. `GET /api/v1/reports/{scan_id}` returns a fixed certificate (`findings_count: 1`, `Zero_False_Positives: true`).
7. `GET /api/v1/benchmarks` reports reproduction and patch success as `1.0` for every agent, and falls back to precision `1.0` when a CSV does not parse. The CSV files are local contract checks, not a published exploit benchmark.
8. Embeddings are `TEXT`. The running schema has no pgvector type.

## Still true

- Seven agent modules exist under `agents/`. The pipeline invokes the orchestrator, code intelligence, and recon. It imports `run_vuln_research`, which is not defined; the function in that module is `run_vulnerability_research`.
- SQLite schema has 30 tables. Evidence, state snapshots, and audit logs reject update and delete.
- The UI hash router has the eighteen views named in `frontend/js/app.js`.
- Skill files are read from `skills/Claude-BugHunter/skills/`.
- Tavily is skipped when no API key is configured. The integration does not invent search hits.

## Not done

The six PDFs were not regenerated. They still contain the Edition 2 design text.
