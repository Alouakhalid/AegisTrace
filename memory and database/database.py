import os
import json
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class DatabaseImmutabilityError(Exception):
    pass

class DatabaseIntegrityViolation(Exception):
    pass

def mask_sensitive_data(val: Any) -> Any:
    if isinstance(val, dict):
        sanitized = {}
        sensitive_keys = {"token", "auth", "secret", "password", "key", "authorization", "bearer", "cookie"}
        for k, v in val.items():
            if any(s in k.lower() for s in sensitive_keys) and isinstance(v, str):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = mask_sensitive_data(v)
        return sanitized
    elif isinstance(val, list):
        return [mask_sensitive_data(item) for item in val]
    return val

class AegisDatabase:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        schema_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
        if os.path.exists(schema_file):
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            self.conn.executescript(schema_sql)
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def create_user(self, user_id: str, email: str, display_name: str, role: str, auth_subject: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (id, email, display_name, role, auth_subject) VALUES (?, ?, ?, ?, ?);",
                (user_id, email, display_name, role, auth_subject)
            )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_project(self, project_id: str, owner_id: str, name: str, language: str = "python", framework_hint: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO projects (id, owner_id, name, language, framework_hint) VALUES (?, ?, ?, ?, ?);",
                (project_id, owner_id, name, language, framework_hint)
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_repository(self, rep_id: str, project_id: str, source_type: str, url: str, default_ref: str = "main", latest_commit: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO repositories (id, project_id, source_type, url, default_ref, latest_commit) VALUES (?, ?, ?, ?, ?, ?);",
                (rep_id, project_id, source_type, url, default_ref, latest_commit)
            )
        return self.get_repository(rep_id)

    def get_repository(self, rep_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM repositories WHERE id = ?;", (rep_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_engagement(self, eng_id: str, project_id: str, name: str, assessment_mode: str, environment: str, status: str = "draft", attested_by: Optional[str] = None, attested_at: Optional[str] = None, starts_at: Optional[str] = None, ends_at: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO engagements (id, project_id, name, assessment_mode, environment, status, attested_by, attested_at, starts_at, ends_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (eng_id, project_id, name, assessment_mode, environment, status, attested_by, attested_at, starts_at, ends_at)
            )
        return self.get_engagement(eng_id)

    def get_engagement(self, eng_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM engagements WHERE id = ?;", (eng_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_scope_manifest(self, scm_id: str, engagement_id: str, version: int, manifest: Dict[str, Any], created_by: str, valid: bool = False, validated_at: Optional[str] = None) -> Dict[str, Any]:
        clean_manifest = mask_sensitive_data(manifest)
        manifest_str = json.dumps(clean_manifest, sort_keys=True)
        manifest_sha256 = hashlib.sha256(manifest_str.encode("utf-8")).hexdigest()
        with self.conn:
            self.conn.execute(
                "INSERT INTO scope_manifests (id, engagement_id, version, manifest, manifest_sha256, valid, validated_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (scm_id, engagement_id, version, manifest_str, manifest_sha256, 1 if valid else 0, validated_at, created_by)
            )
        return self.get_scope_manifest(scm_id)

    def get_scope_manifest(self, scm_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM scope_manifests WHERE id = ?;", (scm_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["manifest"] = json.loads(res["manifest"])
        res["valid"] = bool(res["valid"])
        return res

    def create_scan(self, scn_id: str, engagement_id: str, scope_manifest_id: str, correlation_id: str, requested_by: str, repository_id: Optional[str] = None, commit_sha: Optional[str] = None, status: str = "queued", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config_str = json.dumps(config or {})
        with self.conn:
            self.conn.execute(
                "INSERT INTO scans (id, engagement_id, scope_manifest_id, repository_id, commit_sha, correlation_id, status, config, requested_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (scn_id, engagement_id, scope_manifest_id, repository_id, commit_sha, correlation_id, status, config_str, requested_by)
            )
        return self.get_scan(scn_id)

    def get_scan(self, scn_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM scans WHERE id = ?;", (scn_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["config"] = json.loads(res["config"])
        return res

    def update_scan_status(self, scn_id: str, status: str, finished_at: Optional[str] = None) -> None:
        with self.conn:
            if finished_at:
                self.conn.execute("UPDATE scans SET status = ?, finished_at = ? WHERE id = ?;", (status, finished_at, scn_id))
            else:
                self.conn.execute("UPDATE scans SET status = ? WHERE id = ?;", (status, scn_id))

    def create_agent_task(self, tsk_id: str, scan_id: str, agent: str, stage: str, status: str = "queued", depends_on: Optional[List[str]] = None, task_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        deps_str = json.dumps(depends_on or [])
        input_str = json.dumps(task_input) if task_input is not None else None
        with self.conn:
            self.conn.execute(
                "INSERT INTO agent_tasks (id, scan_id, agent, stage, status, depends_on, input) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (tsk_id, scan_id, agent, stage, status, deps_str, input_str)
            )
        return self.get_agent_task(tsk_id)

    def get_agent_task(self, tsk_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM agent_tasks WHERE id = ?;", (tsk_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["depends_on"] = json.loads(res["depends_on"])
        res["input"] = json.loads(res["input"]) if res["input"] else None
        res["output"] = json.loads(res["output"]) if res["output"] else None
        res["error"] = json.loads(res["error"]) if res["error"] else None
        return res

    def update_agent_task(self, tsk_id: str, status: str, output: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None, finished_at: Optional[str] = None) -> None:
        out_str = json.dumps(output) if output is not None else None
        err_str = json.dumps(error) if error is not None else None
        with self.conn:
            self.conn.execute(
                "UPDATE agent_tasks SET status = ?, output = ?, error = ?, finished_at = ? WHERE id = ?;",
                (status, out_str, err_str, finished_at, tsk_id)
            )

    def list_agent_tasks(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM agent_tasks WHERE scan_id = ? ORDER BY id ASC;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["depends_on"] = json.loads(item["depends_on"])
            item["input"] = json.loads(item["input"]) if item["input"] else None
            item["output"] = json.loads(item["output"]) if item["output"] else None
            item["error"] = json.loads(item["error"]) if item["error"] else None
            result.append(item)
        return result

    def create_agent_run(self, run_id: str, task_id: str, attempt: int, status: str, prompt_version: str, model: str) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO agent_runs (id, task_id, attempt, status, prompt_version, model) VALUES (?, ?, ?, ?, ?, ?);",
                (run_id, task_id, attempt, status, prompt_version, model)
            )
        return self.get_agent_run(run_id)

    def get_agent_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM agent_runs WHERE id = ?;", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_agent_run(self, run_id: str, status: str, llm_calls: int = 0, input_tokens: int = 0, output_tokens: int = 0, error: Optional[Dict[str, Any]] = None, finished_at: Optional[str] = None) -> None:
        err_str = json.dumps(error) if error is not None else None
        with self.conn:
            self.conn.execute(
                "UPDATE agent_runs SET status = ?, llm_calls = ?, input_tokens = ?, output_tokens = ?, error = ?, finished_at = ? WHERE id = ?;",
                (status, llm_calls, input_tokens, output_tokens, err_str, finished_at, run_id)
            )

    def record_agent_message(self, msg_id: str, scan_id: str, correlation_id: str, from_agent: str, to_agent: str, message_type: str, schema_version: str, payload: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
        clean_payload = mask_sensitive_data(payload)
        payload_str = json.dumps(clean_payload)
        with self.conn:
            self.conn.execute(
                "INSERT INTO agent_messages (id, scan_id, task_id, correlation_id, from_agent, to_agent, message_type, schema_version, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (msg_id, scan_id, task_id, correlation_id, from_agent, to_agent, message_type, schema_version, payload_str)
            )
        return self.get_agent_message(msg_id)

    def get_agent_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM agent_messages WHERE id = ?;", (msg_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["payload"] = json.loads(res["payload"])
        return res

    def get_agent_messages(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM agent_messages WHERE scan_id = ? ORDER BY created_at ASC;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def create_repository_analysis(self, ran_id: str, scan_id: str, repository_id: str, commit_sha: str, files_analyzed: int, frameworks: Optional[List[str]] = None, entry_points: Optional[List[str]] = None, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
        fw_str = json.dumps(frameworks or [])
        ep_str = json.dumps(entry_points or [])
        wn_str = json.dumps(warnings or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO repositories_analysis (id, scan_id, repository_id, commit_sha, files_analyzed, frameworks, entry_points, warnings) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (ran_id, scan_id, repository_id, commit_sha, files_analyzed, fw_str, ep_str, wn_str)
            )
        return self.get_repository_analysis(ran_id)

    def get_repository_analysis(self, ran_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM repositories_analysis WHERE id = ?;", (ran_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["frameworks"] = json.loads(res["frameworks"])
        res["entry_points"] = json.loads(res["entry_points"])
        res["warnings"] = json.loads(res["warnings"])
        return res

    def insert_code_node(self, analysis_id: str, kind: str, name: str, file_path: Optional[str] = None, line: Optional[int] = None, props: Optional[Dict[str, Any]] = None) -> int:
        props_str = json.dumps(props or {})
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO code_nodes (analysis_id, kind, name, file, line, props) VALUES (?, ?, ?, ?, ?, ?);",
                (analysis_id, kind, name, file_path, line, props_str)
            )
            return cursor.lastrowid

    def get_code_nodes(self, analysis_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM code_nodes WHERE analysis_id = ?;", (analysis_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["props"] = json.loads(item["props"])
            result.append(item)
        return result

    def insert_code_edge(self, analysis_id: str, src: int, dst: int, kind: str, props: Optional[Dict[str, Any]] = None) -> int:
        props_str = json.dumps(props or {})
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO code_edges (analysis_id, src, dst, kind, props) VALUES (?, ?, ?, ?, ?);",
                (analysis_id, src, dst, kind, props_str)
            )
            return cursor.lastrowid

    def get_code_edges(self, analysis_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM code_edges WHERE analysis_id = ?;", (analysis_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["props"] = json.loads(item["props"])
            result.append(item)
        return result

    def insert_security_invariant(self, inv_id: str, project_id: str, statement: str, kind: str, source: str, confidence: float, status: str = "candidate", analysis_id: Optional[str] = None, applies_to_node_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        nodes_str = json.dumps(applies_to_node_ids or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO security_invariants (id, project_id, analysis_id, statement, kind, source, confidence, status, applies_to_node_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (inv_id, project_id, analysis_id, statement, kind, source, confidence, status, nodes_str)
            )
        return self.get_security_invariant(inv_id)

    def get_security_invariant(self, inv_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM security_invariants WHERE id = ?;", (inv_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["applies_to_node_ids"] = json.loads(res["applies_to_node_ids"])
        return res

    def get_security_invariants(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM security_invariants WHERE project_id = ?;", (project_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["applies_to_node_ids"] = json.loads(item["applies_to_node_ids"])
            result.append(item)
        return result

    def insert_endpoint(self, ep_id: str, scan_id: str, method: str, path: str, path_params: Optional[List[str]] = None, auth_required: Optional[bool] = None, source: str = "crawl", code_node_id: Optional[int] = None) -> Dict[str, Any]:
        params_str = json.dumps(path_params or [])
        auth_val = 1 if auth_required else (0 if auth_required is False else None)
        with self.conn:
            self.conn.execute(
                "INSERT INTO endpoints (id, scan_id, method, path, path_params, auth_required, source, code_node_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (ep_id, scan_id, method, path, params_str, auth_val, source, code_node_id)
            )
        return self.get_endpoint(ep_id)

    def get_endpoint(self, ep_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM endpoints WHERE id = ?;", (ep_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["path_params"] = json.loads(res["path_params"])
        res["auth_required"] = bool(res["auth_required"]) if res["auth_required"] is not None else None
        return res

    def get_endpoints(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM endpoints WHERE scan_id = ?;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["path_params"] = json.loads(item["path_params"])
            item["auth_required"] = bool(item["auth_required"]) if item["auth_required"] is not None else None
            result.append(item)
        return result

    def insert_vulnerability_hypothesis(self, hyp_id: str, scan_id: str, endpoint_id: str, invariant_id: str, category: str, title: str, rationale: str, priority: int, status: str = "proposed", skill_refs: Optional[List[str]] = None, created_by_run: Optional[str] = None) -> Dict[str, Any]:
        skills_str = json.dumps(skill_refs or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO vulnerability_hypotheses (id, scan_id, endpoint_id, invariant_id, category, title, rationale, priority, status, skill_refs, created_by_run) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (hyp_id, scan_id, endpoint_id, invariant_id, category, title, rationale, priority, status, skills_str, created_by_run)
            )
        return self.get_vulnerability_hypothesis(hyp_id)

    def get_vulnerability_hypothesis(self, hyp_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM vulnerability_hypotheses WHERE id = ?;", (hyp_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["skill_refs"] = json.loads(res["skill_refs"])
        return res

    def get_vulnerability_hypotheses(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM vulnerability_hypotheses WHERE scan_id = ?;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["skill_refs"] = json.loads(item["skill_refs"])
            result.append(item)
        return result

    def insert_test_case(self, tpl_id: str, hypothesis_id: str, method: str, steps: List[Dict[str, Any]], identities: List[str], expected_secure_behavior: str, state_checks: Optional[List[Dict[str, Any]]] = None, status: str = "approved") -> Dict[str, Any]:
        steps_str = json.dumps(steps)
        idents_str = json.dumps(identities)
        checks_str = json.dumps(state_checks or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO test_cases (id, hypothesis_id, method, steps, identities, expected_secure_behavior, state_checks, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (tpl_id, hypothesis_id, method, steps_str, idents_str, expected_secure_behavior, checks_str, status)
            )
        return self.get_test_case(tpl_id)

    def get_test_case(self, tpl_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM test_cases WHERE id = ?;", (tpl_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["steps"] = json.loads(res["steps"])
        res["identities"] = json.loads(res["identities"])
        res["state_checks"] = json.loads(res["state_checks"])
        return res

    def get_test_cases(self, hypothesis_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM test_cases WHERE hypothesis_id = ?;", (hypothesis_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["steps"] = json.loads(item["steps"])
            item["identities"] = json.loads(item["identities"])
            item["state_checks"] = json.loads(item["state_checks"])
            result.append(item)
        return result

    def insert_evidence(self, evd_id: str, scan_id: str, kind: str, content_ref: str, content_sha256: str, redacted: bool = True, created_by_run: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO evidence (id, scan_id, kind, content_ref, content_sha256, redacted, created_by_run) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (evd_id, scan_id, kind, content_ref, content_sha256, 1 if redacted else 0, created_by_run)
            )
        return self.get_evidence(evd_id)

    def get_evidence(self, evd_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM evidence WHERE id = ?;", (evd_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["redacted"] = bool(res["redacted"])
        return res

    def attempt_update_evidence(self, evd_id: str, new_ref: str) -> None:
        try:
            with self.conn:
                self.conn.execute("UPDATE evidence SET content_ref = ? WHERE id = ?;", (new_ref, evd_id))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"evidence is append-only: {e}")

    def attempt_delete_evidence(self, evd_id: str) -> None:
        try:
            with self.conn:
                self.conn.execute("DELETE FROM evidence WHERE id = ?;", (evd_id,))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"evidence is append-only: {e}")

    def insert_test_execution(self, exe_id: str, test_case_id: str, task_id: str, identity_id: str, case_label: str, request_data: Dict[str, Any], sandbox_id: str, response_status: Optional[int] = None, response_excerpt: Optional[str] = None, evidence_id: Optional[str] = None, finished_at: Optional[str] = None) -> Dict[str, Any]:
        clean_req = mask_sensitive_data(request_data)
        req_str = json.dumps(clean_req)
        with self.conn:
            self.conn.execute(
                "INSERT INTO test_executions (id, test_case_id, task_id, identity_id, case_label, request, response_status, response_excerpt, sandbox_id, evidence_id, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (exe_id, test_case_id, task_id, identity_id, case_label, req_str, response_status, response_excerpt, sandbox_id, evidence_id, finished_at)
            )
        return self.get_test_execution(exe_id)

    def get_test_execution(self, exe_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM test_executions WHERE id = ?;", (exe_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["request"] = json.loads(res["request"])
        return res

    def insert_state_snapshot(self, snp_id: str, scan_id: str, sandbox_id: str, phase: str, table_name: str, row_key: Dict[str, Any], row_data: Dict[str, Any], row_hash: str, execution_id: Optional[str] = None, evidence_id: Optional[str] = None) -> Dict[str, Any]:
        key_str = json.dumps(row_key)
        data_str = json.dumps(row_data)
        with self.conn:
            self.conn.execute(
                "INSERT INTO state_snapshots (id, scan_id, execution_id, sandbox_id, phase, table_name, row_key, row_data, row_hash, evidence_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (snp_id, scan_id, execution_id, sandbox_id, phase, table_name, key_str, data_str, row_hash, evidence_id)
            )
        return self.get_state_snapshot(snp_id)

    def get_state_snapshot(self, snp_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM state_snapshots WHERE id = ?;", (snp_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["row_key"] = json.loads(res["row_key"])
        res["row_data"] = json.loads(res["row_data"])
        return res

    def get_state_snapshots(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM state_snapshots WHERE scan_id = ?;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["row_key"] = json.loads(item["row_key"])
            item["row_data"] = json.loads(item["row_data"])
            result.append(item)
        return result

    def attempt_update_snapshot(self, snp_id: str, new_hash: str) -> None:
        try:
            with self.conn:
                self.conn.execute("UPDATE state_snapshots SET row_hash = ? WHERE id = ?;", (new_hash, snp_id))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"state_snapshots is append-only: {e}")

    def attempt_delete_snapshot(self, snp_id: str) -> None:
        try:
            with self.conn:
                self.conn.execute("DELETE FROM state_snapshots WHERE id = ?;", (snp_id,))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"state_snapshots is append-only: {e}")

    def insert_finding(self, fnd_id: str, scan_id: str, hypothesis_id: str, endpoint_id: str, invariant_id: str, verdict: str, confidence: float, invariant_violated: bool, runs: int = 1, reproduced: int = 1, severity: Optional[str] = None, cvss_vector: Optional[str] = None, status: str = "open", rejection_reasons: Optional[List[str]] = None, verified_by_run: Optional[str] = None) -> Dict[str, Any]:
        rej_str = json.dumps(rejection_reasons or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO findings (id, scan_id, hypothesis_id, endpoint_id, invariant_id, verdict, confidence, severity, cvss_vector, runs, reproduced, invariant_violated, status, rejection_reasons, verified_by_run) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (fnd_id, scan_id, hypothesis_id, endpoint_id, invariant_id, verdict, confidence, severity, cvss_vector, runs, reproduced, 1 if invariant_violated else 0, status, rej_str, verified_by_run)
            )
        return self.get_finding(fnd_id)

    def get_finding(self, fnd_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM findings WHERE id = ?;", (fnd_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["invariant_violated"] = bool(res["invariant_violated"])
        res["rejection_reasons"] = json.loads(res["rejection_reasons"])
        return res

    def update_finding_status(self, fnd_id: str, status: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE findings SET status = ? WHERE id = ?;", (status, fnd_id))

    def list_findings(self, scan_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM findings WHERE scan_id = ?;", (scan_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["invariant_violated"] = bool(item["invariant_violated"])
            item["rejection_reasons"] = json.loads(item["rejection_reasons"])
            result.append(item)
        return result

    def link_finding_evidence(self, finding_id: str, evidence_id: str, role: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO finding_evidence (finding_id, evidence_id, role) VALUES (?, ?, ?);",
                (finding_id, evidence_id, role)
            )

    def get_finding_evidence(self, finding_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT fe.role, e.* FROM finding_evidence fe JOIN evidence e ON fe.evidence_id = e.id WHERE fe.finding_id = ?;",
            (finding_id,)
        )
        return [dict(r) for r in cursor.fetchall()]

    def insert_skill(self, skl_id: str, name: str, source_repo: str, source_commit: str, path: str, description: str, category: Optional[str] = None, upstream_sources: Optional[List[str]] = None, enabled: bool = True) -> Dict[str, Any]:
        sources_str = json.dumps(upstream_sources or [])
        with self.conn:
            self.conn.execute(
                "INSERT INTO skills (id, name, source_repo, source_commit, path, description, upstream_sources, category, enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (skl_id, name, source_repo, source_commit, path, description, sources_str, category, 1 if enabled else 0)
            )
        return self.get_skill(skl_id)

    def get_skill(self, skl_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM skills WHERE id = ?;", (skl_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["upstream_sources"] = json.loads(res["upstream_sources"])
        res["enabled"] = bool(res["enabled"])
        return res

    def insert_skill_metadata(self, skm_id: str, skill_id: str, chunk_index: int, content_excerpt: str, token_count: int, heading: Optional[str] = None, phases: Optional[List[str]] = None, vuln_categories: Optional[List[str]] = None, embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        ph_str = json.dumps(phases or [])
        vc_str = json.dumps(vuln_categories or [])
        emb_str = json.dumps(embedding) if embedding else None
        with self.conn:
            self.conn.execute(
                "INSERT INTO skill_metadata (id, skill_id, chunk_index, heading, content_excerpt, token_count, phases, vuln_categories, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (skm_id, skill_id, chunk_index, heading, content_excerpt, token_count, ph_str, vc_str, emb_str)
            )
        return self.get_skill_metadata(skm_id)

    def get_skill_metadata(self, skm_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM skill_metadata WHERE id = ?;", (skm_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["phases"] = json.loads(res["phases"])
        res["vuln_categories"] = json.loads(res["vuln_categories"])
        res["embedding"] = json.loads(res["embedding"]) if res["embedding"] else None
        return res

    def search_skill_metadata(self, skill_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM skill_metadata WHERE skill_id = ? ORDER BY chunk_index ASC;", (skill_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["phases"] = json.loads(item["phases"])
            item["vuln_categories"] = json.loads(item["vuln_categories"])
            item["embedding"] = json.loads(item["embedding"]) if item["embedding"] else None
            result.append(item)
        return result

    def insert_skill_usage_log(self, skill_id: str, agent_run_id: str, chunk_ids: List[str], score: float, tokens_injected: int) -> int:
        chunks_str = json.dumps(chunk_ids)
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO skill_usage_logs (skill_id, agent_run_id, chunk_ids, score, tokens_injected) VALUES (?, ?, ?, ?, ?);",
                (skill_id, agent_run_id, chunks_str, score, tokens_injected)
            )
            return cursor.lastrowid

    def get_skill_usage_logs(self, agent_run_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM skill_usage_logs WHERE agent_run_id = ?;", (agent_run_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["chunk_ids"] = json.loads(item["chunk_ids"])
            result.append(item)
        return result

    def insert_patch(self, pat_id: str, finding_id: str, attempt: int, branch: str, diff_ref: str, diff_sha256: str, changed_files: List[str], root_cause: Dict[str, Any], status: str = "proposed", created_by_run: Optional[str] = None) -> Dict[str, Any]:
        files_str = json.dumps(changed_files)
        rc_str = json.dumps(root_cause)
        with self.conn:
            self.conn.execute(
                "INSERT INTO patches (id, finding_id, attempt, branch, diff_ref, diff_sha256, changed_files, root_cause, status, created_by_run) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (pat_id, finding_id, attempt, branch, diff_ref, diff_sha256, files_str, rc_str, status, created_by_run)
            )
        return self.get_patch(pat_id)

    def get_patch(self, pat_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM patches WHERE id = ?;", (pat_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["changed_files"] = json.loads(res["changed_files"])
        res["root_cause"] = json.loads(res["root_cause"])
        return res

    def get_patches(self, finding_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM patches WHERE finding_id = ? ORDER BY attempt ASC;", (finding_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["changed_files"] = json.loads(item["changed_files"])
            item["root_cause"] = json.loads(item["root_cause"])
            result.append(item)
        return result

    def update_patch_status(self, pat_id: str, status: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE patches SET status = ? WHERE id = ?;", (status, pat_id))

    def insert_patch_test(self, ptt_id: str, patch_id: str, suite: str, total: int, passed: int, failed: int, evidence_id: Optional[str] = None, finished_at: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO patch_tests (id, patch_id, suite, total, passed, failed, evidence_id, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (ptt_id, patch_id, suite, total, passed, failed, evidence_id, finished_at)
            )
        return self.get_patch_test(ptt_id)

    def get_patch_test(self, ptt_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM patch_tests WHERE id = ?;", (ptt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_patch_tests(self, patch_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM patch_tests WHERE patch_id = ?;", (patch_id,))
        return [dict(r) for r in cursor.fetchall()]

    def insert_approval(self, apr_id: str, patch_id: str, decision: str = "pending", decided_by: Optional[str] = None, decided_at: Optional[str] = None, comment: Optional[str] = None) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO approvals (id, patch_id, decision, decided_by, decided_at, comment) VALUES (?, ?, ?, ?, ?, ?);",
                (apr_id, patch_id, decision, decided_by, decided_at, comment)
            )
        return self.get_approval(apr_id)

    def get_approval(self, apr_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM approvals WHERE id = ?;", (apr_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_approval(self, apr_id: str, decision: str, decided_by: str, decided_at: str, comment: Optional[str] = None) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE approvals SET decision = ?, decided_by = ?, decided_at = ?, comment = ? WHERE id = ?;",
                (decision, decided_by, decided_at, comment, apr_id)
            )

    def insert_report(self, rpt_id: str, scan_id: str, format_type: str, version: int, content_ref: str, content_sha256: str, generator_version: str) -> Dict[str, Any]:
        with self.conn:
            self.conn.execute(
                "INSERT INTO reports (id, scan_id, format, version, content_ref, content_sha256, generator_version) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (rpt_id, scan_id, format_type, version, content_ref, content_sha256, generator_version)
            )
        return self.get_report(rpt_id)

    def get_report(self, rpt_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM reports WHERE id = ?;", (rpt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert_audit_log(self, actor_type: str, actor_id: str, action: str, allowed: bool, scan_id: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> int:
        details_str = json.dumps(mask_sensitive_data(details or {}))
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO audit_logs (actor_type, actor_id, action, scan_id, resource_type, resource_id, allowed, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (actor_type, actor_id, action, scan_id, resource_type, resource_id, 1 if allowed else 0, details_str)
            )
            return cursor.lastrowid

    def get_audit_logs(self, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if scan_id:
            cursor = self.conn.execute("SELECT * FROM audit_logs WHERE scan_id = ? ORDER BY id ASC;", (scan_id,))
        else:
            cursor = self.conn.execute("SELECT * FROM audit_logs ORDER BY id ASC;")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["allowed"] = bool(item["allowed"])
            item["details"] = json.loads(item["details"])
            result.append(item)
        return result

    def attempt_update_audit_log(self, log_id: int, new_action: str) -> None:
        try:
            with self.conn:
                self.conn.execute("UPDATE audit_logs SET action = ? WHERE id = ?;", (new_action, log_id))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"audit_logs is append-only: {e}")

    def attempt_delete_audit_log(self, log_id: int) -> None:
        try:
            with self.conn:
                self.conn.execute("DELETE FROM audit_logs WHERE id = ?;", (log_id,))
        except sqlite3.DatabaseError as e:
            raise DatabaseImmutabilityError(f"audit_logs is append-only: {e}")

    def insert_memory_item(self, mem_id: str, project_id: str, memory_type: str, key: str, content: str, content_sha256: str, scan_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, importance: float = 0.5, embedding: Optional[List[float]] = None, expires_at: Optional[str] = None) -> Dict[str, Any]:
        meta_str = json.dumps(metadata or {})
        emb_str = json.dumps(embedding) if embedding else None
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory_items (id, project_id, scan_id, memory_type, key, content, metadata, content_sha256, importance, embedding, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (mem_id, project_id, scan_id, memory_type, key, content, meta_str, content_sha256, importance, emb_str, expires_at)
            )
        return self.get_memory_item(mem_id)

    def get_memory_item(self, mem_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM memory_items WHERE id = ?;", (mem_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["metadata"] = json.loads(res["metadata"])
        res["embedding"] = json.loads(res["embedding"]) if res["embedding"] else None
        return res

    def get_memory_items(self, project_id: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if memory_type:
            cursor = self.conn.execute("SELECT * FROM memory_items WHERE project_id = ? AND memory_type = ?;", (project_id, memory_type))
        else:
            cursor = self.conn.execute("SELECT * FROM memory_items WHERE project_id = ?;", (project_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["metadata"] = json.loads(item["metadata"])
            item["embedding"] = json.loads(item["embedding"]) if item["embedding"] else None
            result.append(item)
        return result

    def supersede_memory_item(self, old_mem_id: str, new_mem_id: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE memory_items SET superseded_by = ? WHERE id = ?;", (new_mem_id, old_mem_id))
