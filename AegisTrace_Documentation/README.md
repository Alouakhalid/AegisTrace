# AegisTrace Documentation Package - Edition 2 (partial, in progress)

Date: 2026-11-17. This edition adds the Agent Architecture and Memory/Database documents (EN and AR) plus the SQL and JSON appendices. Remaining items are listed in `12_Quality_Assurance/QA_Report.md`.

## Delivered
| Path | What it is |
|---|---|
| `01_Master_Handbooks/AegisTrace_Master_Architecture_{EN,AR}.pdf` | Canonical architecture (25 / 24 pages) |
| `02_Agent_Architecture/AegisTrace_Agent_Architecture_{EN,AR}.pdf` | Seven agents, workflow, loops, retry, approvals, full JSON contracts, Pydantic code, field reference (76 / 74 pages) |
| `03_Memory_Database/AegisTrace_Memory_Database_Architecture_{EN,AR}.pdf` | Memory model, retrieval, 30-table schema reference, ERDs, pgvector, retention, security (45 / 41 pages) |
| `10_Technical_Appendices/AegisTrace_Database_SQL_Appendix.sql` | Full DDL, executed on PostgreSQL 16 + pgvector 0.6.0 |
| `10_Technical_Appendices/AegisTrace_Agent_JSON_Schemas.json` | JSON Schemas exported from the Pydantic models (7 agents, request and response) |
| `10_Technical_Appendices/agent_contracts_pydantic.py` | Pydantic source of truth for the contracts |
| `10_Technical_Appendices/agent_json_examples/` | 14 request/response examples + 1 error example, all validated |
| `10_Technical_Appendices/validation_tests/` | Scripts that validate the examples and test the schema |
| `11_Architecture_Diagrams/` | 14 diagrams as DOT/MMD source, SVG and PNG |
| `12_Quality_Assurance/` | QA report, PDF build script, document generators, markdown sources |

Empty folders (04 to 09) are for documents not yet produced.

## Rebuild
`python3 build_pdfs.py <source.md> <out.pdf> <en|ar> "<title>" "<subtitle>" <DOC-ID>`. Needs Python (`markdown`, `pypdf`, `playwright` with Chromium, Pygments, `pydantic`) and the fonts Noto Naskh Arabic, Noto Sans Arabic, DejaVu Sans, JetBrains Mono. The agent and database documents are generated from the schemas and the live database by `gen_agent_doc.py`, `gen_db_doc.py` and `gen_memdb.py`.

## Licensing note
Claude-BugHunter: code MIT, content CC BY 4.0. No skill text is copied into this package.
