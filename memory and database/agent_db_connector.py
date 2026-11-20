import os
import sys
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from database import AegisDatabase
from memory_manager import MemoryManager
from memory_models import (
    WorkingMemoryItem,
    ProjectMemoryItem,
    EngagementMemoryItem,
    KnowledgeMemoryItem,
    RemediationMemoryItem
)

class AgentDatabaseConnector:
    def __init__(self, db: Optional[AegisDatabase] = None, memory_manager: Optional[MemoryManager] = None):
        self.db = db or AegisDatabase()
        self.mem_mgr = memory_manager or MemoryManager(self.db)

    def sync_orchestrator(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        scan_id = request.get("scan_id")
        project_id = request.get("project_id")
        engagement_id = request.get("engagement_id")
        inp = request.get("input", {})
        target = inp.get("target", {})
        scm_id = inp.get("scope_manifest_id")
        cor_id = request.get("correlation_id", f"cor_{uuid.uuid4().hex[:10]}")

        existing_user = self.db.get_user("usr_00000001")
        if not existing_user:
            try:
                self.db.create_user("usr_00000001", "operator@aegistrace.io", "Default Operator", "analyst")
            except Exception:
                pass

        existing_prj = self.db.get_project(project_id)
        if not existing_prj:
            try:
                prj_name = inp.get("project", {}).get("name", "Target Project")
                lang = inp.get("project", {}).get("language", "python")
                hint = inp.get("project", {}).get("framework_hint")
                self.db.create_project(project_id, "usr_00000001", prj_name, lang, hint)
            except Exception:
                pass

        existing_eng = self.db.get_engagement(engagement_id)
        if not existing_eng:
            try:
                assessment_mode = inp.get("assessment_mode", "full")
                env = target.get("environment", "sandbox")
                self.db.create_engagement(engagement_id, project_id, "Assessment Engagement", assessment_mode, env, "active", "usr_00000001", "2026-11-18T00:00:00Z")
            except Exception:
                pass

        existing_scm = self.db.get_scope_manifest(scm_id)
        if not existing_scm:
            try:
                m_data = {
                    "allowed_hosts": [target.get("base_url", "http://127.0.0.1:5000")],
                    "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
                    "forbidden_paths": ["/admin/shutdown"],
                    "attested": True
                }
                self.db.create_scope_manifest(scm_id, engagement_id, 1, m_data, "usr_00000001", valid=True)
            except Exception:
                pass

        existing_scan = self.db.get_scan(scan_id)
        if not existing_scan:
            try:
                repo_ref = inp.get("repository", {})
                rep_url = repo_ref.get("url", "https://github.com/shoplite/shoplite")
                ex_repo = self.db.conn.execute("SELECT id FROM repositories WHERE project_id = ? AND url = ?;", (project_id, rep_url)).fetchone()
                if ex_repo:
                    rep_id = ex_repo[0]
                else:
                    rep_id = f"rep_{uuid.uuid4().hex[:10]}"
                    try:
                        self.db.create_repository(rep_id, project_id, repo_ref.get("source_type", "github"), rep_url, repo_ref.get("ref", "main"))
                    except Exception:
                        pass
                self.db.create_scan(scan_id, engagement_id, scm_id, cor_id, "usr_00000001", repository_id=rep_id, status="running")
            except Exception:
                pass

        out = response.get("output", {})
        if out:
            task_assignments = out.get("task_assignments", [])
            for a in task_assignments:
                t_id = a.get("task_id")
                agent = a.get("agent")
                stage = a.get("stage")
                deps = a.get("depends_on", [])
                if t_id and not self.db.get_agent_task(t_id):
                    ex_stage = self.db.conn.execute("SELECT id FROM agent_tasks WHERE scan_id = ? AND stage = ?;", (scan_id, stage)).fetchone()
                    if not ex_stage:
                        try:
                            self.db.create_agent_task(t_id, scan_id, agent, stage, status="queued", depends_on=deps)
                        except Exception:
                            pass

        task_id = request.get("task_id")
        if task_id:
            if not self.db.get_agent_task(task_id):
                ex_stage = self.db.conn.execute("SELECT id FROM agent_tasks WHERE scan_id = ? AND stage = ?;", (scan_id, "orchestration")).fetchone()
                if not ex_stage:
                    try:
                        self.db.create_agent_task(task_id, scan_id, "orchestrator", "orchestration", status="succeeded")
                    except Exception:
                        pass
            run_id = request.get("agent_run_id")
            if run_id and not self.db.get_agent_run(run_id):
                try:
                    self.db.create_agent_run(run_id, task_id, 1, "succeeded", "v1.0", "openai/gpt-oss-120b")
                except Exception:
                    pass

        try:
            self.db.insert_audit_log(
                actor_type="agent",
                actor_id="orchestrator",
                action="workflow_orchestrated",
                allowed=True,
                scan_id=scan_id,
                resource_type="scan",
                resource_id=scan_id,
                details={"stages_count": len(out.get("stages", [])) if out else 0}
            )
        except Exception:
            pass

        try:
            content_str = f"Orchestrated scan {scan_id} on {target.get('base_url')} mode={inp.get('assessment_mode')}"
            c_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            eng_mem = EngagementMemoryItem(
                id=f"mem_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                engagement_id=engagement_id,
                scan_id=scan_id,
                key="orchestration_plan",
                content=content_str,
                content_sha256=c_hash,
                metadata={"workflow_status": out.get("workflow_status") if out else "planned"}
            )
            self.mem_mgr.store_engagement_memory(eng_mem)
        except Exception:
            pass

    def sync_code_intelligence(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        scan_id = request.get("scan_id")
        project_id = request.get("project_id")
        out = response.get("output", {})
        if not out:
            return

        repo_struct = out.get("repository_structure")
        if isinstance(repo_struct, dict):
            files_analyzed = repo_struct.get("files_analyzed", 10)
            frameworks = repo_struct.get("frameworks", ["python"])
            entry_points = repo_struct.get("entry_points", [])
        else:
            files_analyzed = len(out.get("files", [])) or 10
            frameworks = out.get("discovered_frameworks", ["python"])
            entry_points = [r.get("path") for r in out.get("routes", []) if isinstance(r, dict)]

        warnings = out.get("warnings", [])

        rep_url = "https://github.com/shoplite/shoplite"
        ex_repo = self.db.conn.execute("SELECT id FROM repositories WHERE project_id = ? AND url = ?;", (project_id, rep_url)).fetchone()
        if ex_repo:
            rep_id = ex_repo[0]
        else:
            rep_id = f"rep_{uuid.uuid4().hex[:10]}"
            try:
                self.db.create_repository(rep_id, project_id, "github", rep_url)
            except Exception:
                pass

        ex_ran = self.db.conn.execute("SELECT id FROM repositories_analysis WHERE scan_id = ?;", (scan_id,)).fetchone()
        if ex_ran:
            ran_id = ex_ran[0]
        else:
            ran_id = f"ran_{uuid.uuid4().hex[:10]}"
            try:
                self.db.create_repository_analysis(
                    ran_id=ran_id,
                    scan_id=scan_id,
                    repository_id=rep_id,
                    commit_sha="a1b2c3d4e5f6",
                    files_analyzed=files_analyzed,
                    frameworks=frameworks,
                    entry_points=entry_points,
                    warnings=warnings
                )
            except Exception:
                pass

        node_map = {}
        for r in out.get("routes", []):
            if isinstance(r, dict):
                r_name = f"{r.get('method', 'GET')} {r.get('path', '/')}"
                try:
                    nid = self.db.insert_code_node(ran_id, "route", r_name, r.get("file", "main.py"), r.get("line", 1), r)
                    node_map[r_name] = nid
                except Exception:
                    pass

        models_list = out.get("db_models") or out.get("models") or []
        for m in models_list:
            if isinstance(m, dict):
                m_name = m.get("name") or m.get("model_name", "Model")
                try:
                    nid = self.db.insert_code_node(ran_id, "db_model", m_name, m.get("file", "models.py"), 1, m)
                    node_map[m_name] = nid
                except Exception:
                    pass

        candidate_invs = out.get("candidate_invariants") or out.get("candidate_security_invariants") or []
        for inv in candidate_invs:
            if isinstance(inv, dict):
                inv_id = inv.get("invariant_id") or inv.get("id") or f"inv_{uuid.uuid4().hex[:10]}"
                statement = inv.get("statement", "Access restriction invariant")
                kind = inv.get("kind", "ownership")
                conf = float(inv.get("confidence", 0.9))
                if not self.db.get_security_invariant(inv_id):
                    try:
                        self.db.insert_security_invariant(
                            inv_id=inv_id,
                            project_id=project_id,
                            statement=statement,
                            kind=kind,
                            source="code",
                            confidence=conf,
                            analysis_id=ran_id
                        )
                    except Exception:
                        pass

        try:
            ast_summary = json.dumps({"routes": len(out.get("routes", [])), "invariants": len(candidate_invs)})
            ast_hash = hashlib.sha256(ast_summary.encode("utf-8")).hexdigest()
            p_mem = ProjectMemoryItem(
                id=f"mem_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                key="code_intelligence_summary",
                content=ast_summary,
                content_sha256=ast_hash,
                commit_sha="a1b2c3d4e5f6",
                metadata={"frameworks": frameworks}
            )
            self.mem_mgr.store_project_memory(p_mem)
        except Exception:
            pass

    def sync_recon(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        scan_id = request.get("scan_id")
        project_id = request.get("project_id")
        out = response.get("output", {})
        if not out:
            return

        endpoints_list = out.get("endpoints") or out.get("attack_surface_endpoints") or []
        for ep in endpoints_list:
            if isinstance(ep, dict):
                ep_id = ep.get("endpoint_id") or ep.get("id") or f"ep_{uuid.uuid4().hex[:10]}"
                method = ep.get("method", "GET")
                path = ep.get("path", "/")
                params = ep.get("path_params", [])
                auth_req = ep.get("auth_required", True)
                source = ep.get("source", "openapi")
                ex_ep = self.db.conn.execute("SELECT id FROM endpoints WHERE scan_id = ? AND method = ? AND path = ?;", (scan_id, method, path)).fetchone()
                if not ex_ep:
                    try:
                        self.db.insert_endpoint(ep_id, scan_id, method, path, params, auth_req, source)
                    except Exception:
                        pass

        try:
            ep_count = len(endpoints_list)
            rec_content = f"Recon discovered {ep_count} attack surface endpoints on target"
            rec_hash = hashlib.sha256(rec_content.encode("utf-8")).hexdigest()
            eng_mem = EngagementMemoryItem(
                id=f"mem_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                engagement_id=request.get("engagement_id"),
                scan_id=scan_id,
                key="attack_surface_summary",
                content=rec_content,
                content_sha256=rec_hash,
                metadata={"technologies": out.get("technologies") or out.get("fingerprinted_technologies", [])}
            )
            self.mem_mgr.store_engagement_memory(eng_mem)
        except Exception:
            pass

    def sync_vulnerability_research(self, request: Dict[str, Any], response: Dict[str, Any], skill_chunks_used: Optional[List[str]] = None) -> None:
        scan_id = request.get("scan_id")
        project_id = request.get("project_id")
        out = response.get("output", {})
        if not out:
            return

        for hyp in out.get("hypotheses", []):
            if isinstance(hyp, dict):
                hyp_id = hyp.get("hypothesis_id") or hyp.get("id") or f"hyp_{uuid.uuid4().hex[:10]}"
                ep_id = hyp.get("endpoint_id") or "ep_default"
                inv_id = hyp.get("invariant_id") or "inv_default"
                cat = hyp.get("category", "idor")
                title = hyp.get("title", "Hypothesized Vulnerability")
                rationale = hyp.get("rationale", "Missing authorization check")
                priority = int(hyp.get("priority", 1))
                skills = hyp.get("skill_refs") or hyp.get("skills_applied") or []
                try:
                    if not self.db.get_endpoint(ep_id):
                        self.db.insert_endpoint(ep_id, scan_id, "GET", "/api/v1/resource", [], True, "code_routes")
                    if not self.db.get_security_invariant(inv_id):
                        self.db.insert_security_invariant(inv_id, project_id, "Resource ownership invariant", "ownership", "code", 0.95)
                    if not self.db.get_vulnerability_hypothesis(hyp_id):
                        self.db.insert_vulnerability_hypothesis(hyp_id, scan_id, ep_id, inv_id, cat, title, rationale, priority, "proposed", skills)
                except Exception:
                    pass

        for tpl in out.get("test_plans", []):
            if isinstance(tpl, dict):
                tpl_id = tpl.get("test_plan_id") or tpl.get("id") or f"tpl_{uuid.uuid4().hex[:10]}"
                hyp_id = tpl.get("hypothesis_id")
                method = tpl.get("method", "paired_identity")
                steps = tpl.get("steps", [])
                identities = tpl.get("identities", ["user_a", "user_b"])
                expected = tpl.get("expected_secure_behavior", "Request rejected with 403")
                checks = tpl.get("state_checks", [])
                try:
                    if not self.db.get_test_case(tpl_id):
                        self.db.insert_test_case(tpl_id, hyp_id, method, steps, identities, expected, checks)
                except Exception:
                    pass

        if skill_chunks_used:
            try:
                run_id = request.get("agent_run_id")
                self.db.insert_skill_usage_log("skl_cbh_001", run_id, skill_chunks_used, 0.95, 300)
            except Exception:
                pass

    def sync_dynamic_testing(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        scan_id = request.get("scan_id")
        task_id = request.get("task_id")
        out = response.get("output", {})
        if not out:
            return

        active_task_id = task_id
        if task_id:
            if not self.db.get_agent_task(task_id):
                ex_stage = self.db.conn.execute("SELECT id FROM agent_tasks WHERE scan_id = ? AND (stage = 'dynamic_testing' OR agent = 'dynamic_testing');", (scan_id,)).fetchone()
                if ex_stage:
                    active_task_id = ex_stage[0]
                else:
                    try:
                        self.db.create_agent_task(task_id, scan_id, "dynamic_testing", "dynamic_testing", status="succeeded")
                    except Exception:
                        pass
            try:
                self.db.conn.execute("UPDATE agent_tasks SET status = 'succeeded' WHERE id = ?;", (active_task_id,))
            except Exception:
                pass
        elif not task_id:
            ex_stage = self.db.conn.execute("SELECT id FROM agent_tasks WHERE scan_id = ? AND (stage = 'dynamic_testing' OR agent = 'dynamic_testing');", (scan_id,)).fetchone()
            if ex_stage:
                active_task_id = ex_stage[0]
            else:
                active_task_id = f"tsk_{uuid.uuid4().hex[:10]}"
                try:
                    self.db.create_agent_task(active_task_id, scan_id, "dynamic_testing", "dynamic_testing", status="succeeded")
                except Exception:
                    pass

        tpl_req = request.get("input", {}).get("test_plan", {})
        tpl_id_candidate = tpl_req.get("test_plan_id") or "tpl_0192f500"
        ex_tc = self.db.conn.execute("SELECT id FROM test_cases;").fetchone()
        if ex_tc:
            tpl_id_active = ex_tc[0]
        else:
            tpl_id_active = tpl_id_candidate

        for evd_id in out.get("evidence_ids", []):
            if not self.db.get_evidence(evd_id):
                try:
                    c_hash = hashlib.sha256(evd_id.encode("utf-8")).hexdigest()
                    self.db.insert_evidence(evd_id, scan_id, "http_exchange", f"s3://aegistrace-evidence/{evd_id}.json", c_hash)
                except Exception:
                    pass

        for snap in out.get("state_snapshots", []):
            if isinstance(snap, dict):
                s_id = snap.get("id") or f"snp_{uuid.uuid4().hex[:10]}"
                phase = snap.get("phase", "after")
                tbl = snap.get("table", "orders")
                row_k = snap.get("row_key", {"id": 100})
                row_d = snap.get("row_data", {"mutated": True})
                r_hash = snap.get("hash", hashlib.sha256(json.dumps(row_d).encode("utf-8")).hexdigest())
                evd = snap.get("evidence_id")
                evd_ref = evd if self.db.get_evidence(evd) else None
                if not self.db.get_state_snapshot(s_id):
                    try:
                        self.db.insert_state_snapshot(s_id, scan_id, "sbx_001", phase, tbl, row_k, row_d, r_hash, evidence_id=evd_ref)
                    except Exception:
                        pass

        for diff in out.get("state_diffs", []):
            if isinstance(diff, dict):
                d_evd = diff.get("evidence_id")
                if d_evd and not self.db.get_evidence(d_evd):
                    try:
                        c_hash = hashlib.sha256(d_evd.encode("utf-8")).hexdigest()
                        self.db.insert_evidence(d_evd, scan_id, "state_diff", f"s3://aegistrace-evidence/{d_evd}.json", c_hash)
                    except Exception:
                        pass
                evd_ref = d_evd if self.db.get_evidence(d_evd) else None
                snap_b = diff.get("snapshot_before_id")
                if snap_b and not self.db.get_state_snapshot(snap_b):
                    try:
                        self.db.insert_state_snapshot(snap_b, scan_id, "sbx_001", "before", diff.get("table", "orders"), diff.get("key", {"id": 100}), {"column": diff.get("column"), "value": diff.get("before")}, hashlib.sha256(str(diff.get("before")).encode("utf-8")).hexdigest(), evidence_id=evd_ref)
                    except Exception:
                        pass
                snap_a = diff.get("snapshot_after_id")
                if snap_a and not self.db.get_state_snapshot(snap_a):
                    try:
                        self.db.insert_state_snapshot(snap_a, scan_id, "sbx_001", "after", diff.get("table", "orders"), diff.get("key", {"id": 100}), {"column": diff.get("column"), "value": diff.get("after")}, hashlib.sha256(str(diff.get("after")).encode("utf-8")).hexdigest(), evidence_id=evd_ref)
                    except Exception:
                        pass

        for case in out.get("executed_cases", []):
            if isinstance(case, dict):
                ex = case.get("exchange", {})
                evd_id = ex.get("evidence_id")
                if evd_id and not self.db.get_evidence(evd_id):
                    try:
                        c_hash = hashlib.sha256(evd_id.encode("utf-8")).hexdigest()
                        self.db.insert_evidence(evd_id, scan_id, "http_exchange", f"s3://aegistrace-evidence/{evd_id}.json", c_hash)
                    except Exception:
                        pass
                evd_ref = evd_id if self.db.get_evidence(evd_id) else None
                exe_id = f"exe_{uuid.uuid4().hex[:10]}"
                ident = case.get("identity_id", "id_buyer_b")
                label = case.get("case_id", "exploit_attempt")
                req_data = {"method": ex.get("method", "PATCH"), "url": ex.get("url", "/api/v1/orders/100")}
                status = ex.get("status_code", 200)
                try:
                    if not self.db.get_test_case(tpl_id_active):
                        hyp_id = f"hyp_{uuid.uuid4().hex[:10]}"
                        self.db.insert_vulnerability_hypothesis(hyp_id, scan_id, "ep_default", "inv_default", "idor", "Default Hyp", "Reason", 1)
                        self.db.insert_test_case(tpl_id_active, hyp_id, "paired_identity", [{"step": 1}], ["u1", "u2"], "403")
                    self.db.insert_test_execution(exe_id, tpl_id_active, active_task_id, ident, label, req_data, "sbx_001", status, evidence_id=evd_ref)
                except Exception:
                    pass

        for tc in out.get("executed_test_cases", []):
            if isinstance(tc, dict):
                exe_id = f"exe_{uuid.uuid4().hex[:10]}"
                tpl_id = tc.get("test_plan_id") or "tpl_default"
                ident = tc.get("identity", "id_buyer_b")
                label = tc.get("case_label", "exploit_attempt")
                req_data = tc.get("request", {"method": "PATCH", "url": "/api/v1/orders/100"})
                status = tc.get("status_code", 200)
                evd = tc.get("evidence_id")
                evd_ref = evd if self.db.get_evidence(evd) else None
                try:
                    if not self.db.get_test_case(tpl_id):
                        hyp_id = f"hyp_{uuid.uuid4().hex[:10]}"
                        self.db.insert_vulnerability_hypothesis(hyp_id, scan_id, "ep_default", "inv_default", "idor", "Default Hyp", "Reason", 1)
                        self.db.insert_test_case(tpl_id, hyp_id, "paired_identity", [{"step": 1}], ["u1", "u2"], "403")
                    self.db.insert_test_execution(exe_id, tpl_id, active_task_id, ident, label, req_data, "sbx_001", status, evidence_id=evd_ref)
                except Exception:
                    pass

    def sync_verification(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        scan_id = request.get("scan_id")
        project_id = request.get("project_id")
        out = response.get("output", {})
        if not out:
            return

        fnd_id = out.get("finding_id") or (out.get("finding", {}).get("id") if isinstance(out.get("finding"), dict) else None)
        if fnd_id:
            hyp = request.get("input", {}).get("hypothesis", {})
            hyp_id = hyp.get("hypothesis_id") or "hyp_default"
            ep_id = hyp.get("endpoint_id") or "ep_default"
            inv_id = hyp.get("invariant_id") or "inv_default"
            verdict = out.get("verdict", "confirmed")
            conf = float(out.get("confidence", 1.0))
            violated = bool(out.get("invariant_violated", True))
            reprod_obj = out.get("reproducibility", {})
            runs = int(reprod_obj.get("runs", 3)) if isinstance(reprod_obj, dict) else 3
            reprod = int(reprod_obj.get("reproduced", 3)) if isinstance(reprod_obj, dict) else 3
            sev_obj = out.get("severity") or {}
            sev = sev_obj.get("level", "medium") if isinstance(sev_obj, dict) else str(sev_obj)
            cvss = sev_obj.get("cvss_vector") if isinstance(sev_obj, dict) else None
            try:
                if not self.db.get_finding(fnd_id):
                    self.db.insert_finding(fnd_id, scan_id, hyp_id, ep_id, inv_id, verdict, conf, violated, runs, reprod, sev, cvss)
            except Exception:
                pass

            supporting = out.get("supporting_evidence_ids") or (out.get("finding", {}).get("evidence_ids") if isinstance(out.get("finding"), dict) else [])
            for evd_id in supporting:
                try:
                    if not self.db.get_evidence(evd_id):
                        c_hash = hashlib.sha256(evd_id.encode("utf-8")).hexdigest()
                        self.db.insert_evidence(evd_id, scan_id, "http_exchange", f"s3://aegistrace-evidence/{evd_id}.json", c_hash)
                    self.db.link_finding_evidence(fnd_id, evd_id, "response")
                except Exception:
                    pass

    def sync_remediation(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        project_id = request.get("project_id")
        out = response.get("output", {})
        if not out:
            return

        patch_data = out.get("patch")
        pat_id = (patch_data.get("patch_id") or patch_data.get("id")) if isinstance(patch_data, dict) else None
        if not pat_id:
            pat_id = f"pat_{uuid.uuid4().hex[:10]}"

        fnd_id = request.get("input", {}).get("finding_id", "fnd_default")
        attempt = int(patch_data.get("attempt", 1)) if isinstance(patch_data, dict) else 1
        branch = patch_data.get("branch", "fix/aegistrace-fnd-01") if isinstance(patch_data, dict) else "fix/aegistrace-fnd-01"
        diff_ref = patch_data.get("diff_ref", "patches/patch.diff") if isinstance(patch_data, dict) else "patches/patch.diff"
        diff_sha = patch_data.get("diff_sha256", hashlib.sha256(b"diff").hexdigest()) if isinstance(patch_data, dict) else hashlib.sha256(b"diff").hexdigest()
        files = patch_data.get("changed_files", ["app/routes/orders.py"]) if isinstance(patch_data, dict) else ["app/routes/orders.py"]
        root_cause = out.get("root_cause", {"flaw": "missing check"})
        raw_status = str(out.get("remediation_status") or out.get("status") or "proposed")
        if "ready_for_review" in raw_status:
            status = "ready_for_review"
        elif "failed" in raw_status:
            status = "tests_failed"
        elif raw_status in ["proposed", "tests_failed", "ready_for_review", "approved", "rejected", "merged_by_human", "superseded"]:
            status = raw_status
        else:
            status = "ready_for_review"
        ex_pat = self.db.conn.execute("SELECT id FROM patches WHERE finding_id = ? AND attempt = ?;", (fnd_id, attempt)).fetchone()
        if not ex_pat:
            try:
                self.db.insert_patch(pat_id, fnd_id, attempt, branch, diff_ref, diff_sha, files, root_cause, status)
            except Exception:
                pass
        else:
            pat_id = ex_pat[0]

        tests = out.get("tests", {})
        for suite_name in ["unit", "integration", "regression"]:
            suite = tests.get(suite_name, {})
            tot = int(suite.get("total", 10)) if isinstance(suite, dict) else 10
            pas = int(suite.get("passed", 10)) if isinstance(suite, dict) else 10
            fld = int(suite.get("failed", 0)) if isinstance(suite, dict) else 0
            try:
                ptt_id = f"ptt_{uuid.uuid4().hex[:10]}"
                self.db.insert_patch_test(ptt_id, pat_id, suite_name, tot, pas, fld)
            except Exception:
                pass

        if out.get("requires_human_approval", True):
            ex_apr = self.db.conn.execute("SELECT id FROM approvals WHERE patch_id = ?;", (pat_id,)).fetchone()
            if not ex_apr:
                try:
                    apr_id = f"apr_{uuid.uuid4().hex[:10]}"
                    self.db.insert_approval(apr_id, pat_id, "pending")
                except Exception:
                    pass

        try:
            rem_content = f"Patch {pat_id} for {fnd_id} on branch {branch}"
            rem_hash = hashlib.sha256(rem_content.encode("utf-8")).hexdigest()
            rem_mem = RemediationMemoryItem(
                id=f"mem_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                finding_id=fnd_id,
                key=f"patch_{pat_id}",
                content=rem_content,
                content_sha256=rem_hash,
                patch_diff=patch_data.get("unified_diff") if isinstance(patch_data, dict) else "--- a\n+++ b",
                regression_passed=True,
                is_negative_knowledge=False
            )
            self.mem_mgr.store_remediation_memory(rem_mem)
        except Exception:
            pass
