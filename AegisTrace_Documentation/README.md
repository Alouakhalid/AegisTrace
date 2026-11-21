# AegisTrace documentation

The description of the code that `python3 backend/run.py` starts is:

- [00_What_Actually_Runs.md](00_What_Actually_Runs.md)
- [00_What_Actually_Runs_AR.md](00_What_Actually_Runs_AR.md)

Read those first. The PDFs and the long markdown under `12_Quality_Assurance/source_markdown/` are an earlier design (Edition 2, 2026-11-17). They still say the UI is Next.js and the database is PostgreSQL with pgvector. The process uses the vanilla JavaScript app in `frontend/` and SQLite in `memory and database/schema.sql`.

## What is in this folder

| Path | Status |
|---|---|
| `00_What_Actually_Runs.md` and `_AR.md` | Matches the repository as of 2026-11-21 |
| `12_Quality_Assurance/QA_Report.md` | Lists what the design documents claimed and what the code does |
| `10_Technical_Appendices/agent_contracts_pydantic.py` | Pydantic contracts used as the agent JSON shape |
| `AegisTrace_Agent_JSON_Schemas.json` | JSON Schema export. The orchestrator validator loads this file from the repo root |
| `10_Technical_Appendices/agent_json_examples/` | Example payloads for those contracts |
| `11_Architecture_Diagrams/` | DOT and SVG sources. Markdown links point here |
| `AegisTrace_Database_SQL_Appendix.sql` | PostgreSQL draft. **Not** the database `AegisDatabase` opens. The running DDL is `memory and database/schema.sql` |
| `01_` … `03_` PDFs, if present | Built from the design markdown. They are not rebuilt from the 2026-11-21 correction |

## Rebuild note

`12_Quality_Assurance/build_pdfs.py` turns a markdown source into a PDF. Rebuilding the old sources reproduces the design document, not `00_What_Actually_Runs.md`.

Claude-BugHunter: code MIT, skill text CC BY 4.0. Skill bodies are not copied into this package.
