# QA notes — documentation versus the running code

Date: 2026-11-21. Same content as `../QA_Report.md`.

The description of the process started by `backend/run.py` is `../00_What_Actually_Runs.md` and `../00_What_Actually_Runs_AR.md`.

Edition 2 (the PDFs and `source_markdown/`) is a design write-up. It is not a record of a PostgreSQL database the application opens, and it is not a record of a scan that runs dynamic tests, three replays, and a verified patch. Those stages in `backend/pipeline.py` log a message and return. See the package `QA_Report.md` for the eight mismatches checked against the source.
