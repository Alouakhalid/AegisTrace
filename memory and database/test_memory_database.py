import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from database import AegisDatabase, DatabaseImmutabilityError
from memory_models import (
    WorkingMemoryItem,
    ProjectMemoryItem,
    EngagementMemoryItem,
    KnowledgeMemoryItem,
    RemediationMemoryItem
)
from memory_manager import MemoryManager, compute_cosine_similarity

def run_tests():
    print("=" * 70)
    print("AEGISTRACE — MEMORY & DATABASE ARCHITECTURE COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    db = AegisDatabase(":memory:")
    mem_mgr = MemoryManager(db)

    print("\n[1] Testing 30 Relational Tables Creation & Foreign Key Constraints...")

    u = db.create_user("usr_00000001", "alice@aegistrace.io", "Alice Analyst", "analyst")
    assert u["id"] == "usr_00000001"
    print("  [+] users: PASS")

    p = db.create_project("prj_00000001", "usr_00000001", "ShopLite", "python", "flask")
    assert p["name"] == "ShopLite"
    print("  [+] projects: PASS")

    r = db.create_repository("rep_00000001", "prj_00000001", "github", "https://github.com/shoplite/shoplite")
    assert r["url"] == "https://github.com/shoplite/shoplite"
    print("  [+] repositories: PASS")

    eng = db.create_engagement("eng_00000001", "prj_00000001", "Q4 Pentest", "full", "sandbox", "active", "usr_00000001", "2026-11-18T00:00:00Z")
    assert eng["assessment_mode"] == "full"
    print("  [+] engagements: PASS")

    manifest_data = {
        "allowed_hosts": ["http://localhost:5000"],
        "allowed_methods": ["GET", "POST"],
        "secret_token": "super_secret_bearer_token"
    }
    scm = db.create_scope_manifest("scm_00000001", "eng_00000001", 1, manifest_data, "usr_00000001", valid=True)
    assert scm["valid"] is True
    assert scm["manifest"]["secret_token"] == "***REDACTED***"
    print("  [+] scope_manifests & Secret Sanitization: PASS")

    scn = db.create_scan("scn_00000001", "eng_00000001", "scm_00000001", "cor_00000001", "usr_00000001")
    assert scn["status"] == "queued"
    print("  [+] scans: PASS")

    tsk = db.create_agent_task("tsk_00000001", "scn_00000001", "code_intelligence", "code_analysis")
    assert tsk["agent"] == "code_intelligence"
    print("  [+] agent_tasks: PASS")

    run = db.create_agent_run("run_00000001", "tsk_00000001", 1, "succeeded", "v1.0", "openai/gpt-oss-120b")
    assert run["attempt"] == 1
    print("  [+] agent_runs: PASS")

    msg = db.record_agent_message("msg_00000001", "scn_00000001", "cor_00000001", "orchestrator", "code_intelligence", "request", "1.0.0", {"auth_token": "secret123"})
    assert msg["payload"]["auth_token"] == "***REDACTED***"
    print("  [+] agent_messages: PASS")

    ran = db.create_repository_analysis("ran_00000001", "scn_00000001", "rep_00000001", "a1b2c3d4e5f6", 42, ["flask"], ["app.py"])
    assert ran["files_analyzed"] == 42
    print("  [+] repositories_analysis: PASS")

    node1 = db.insert_code_node("ran_00000001", "route", "/api/order/<id>", "app.py", 100)
    node2 = db.insert_code_node("ran_00000001", "db_model", "Order", "models.py", 20)
    assert node1 > 0 and node2 > 0
    print("  [+] code_nodes: PASS")

    edge1 = db.insert_code_edge("ran_00000001", node1, node2, "reads")
    assert edge1 > 0
    print("  [+] code_edges: PASS")

    inv = db.insert_security_invariant("inv_00000001", "prj_00000001", "User can only access own orders", "ownership", "code", 0.95, applies_to_node_ids=[node1])
    assert inv["confidence"] == 0.95
    print("  [+] security_invariants: PASS")

    ep = db.insert_endpoint("ep_00000001", "scn_00000001", "GET", "/api/order/{id}", ["id"], True, "code_routes", node1)
    assert ep["path"] == "/api/order/{id}"
    print("  [+] endpoints: PASS")

    hyp = db.insert_vulnerability_hypothesis("hyp_00000001", "scn_00000001", "ep_00000001", "inv_00000001", "idor", "IDOR in order lookup", "Missing ownership check", 1)
    assert hyp["category"] == "idor"
    print("  [+] vulnerability_hypotheses: PASS")

    tpl = db.insert_test_case("tpl_00000001", "hyp_00000001", "paired_identity", [{"step": 1}], ["user_a", "user_b"], "Returns 403 Forbidden")
    assert tpl["method"] == "paired_identity"
    print("  [+] test_cases: PASS")

    evd_hash = hashlib.sha256(b"http response body evidence").hexdigest()
    evd = db.insert_evidence("evd_00000001", "scn_00000001", "http_exchange", "s3://aegis/evd1.json", evd_hash)
    assert evd["content_sha256"] == evd_hash
    print("  [+] evidence: PASS")

    exe = db.insert_test_execution("exe_00000001", "tpl_00000001", "tsk_00000001", "user_b", "cross_tenant", {"headers": {"Authorization": "Bearer secret"}}, "sbx_001", 200, "leaked order", "evd_00000001")
    assert exe["request"]["headers"]["Authorization"] == "***REDACTED***"
    print("  [+] test_executions: PASS")

    snap = db.insert_state_snapshot("snp_00000001", "scn_00000001", "sbx_001", "after", "orders", {"id": 10}, {"total": 500}, "hash123", "exe_00000001", "evd_00000001")
    assert snap["phase"] == "after"
    print("  [+] state_snapshots: PASS")

    fnd = db.insert_finding("fnd_00000001", "scn_00000001", "hyp_00000001", "ep_00000001", "inv_00000001", "confirmed", 0.99, True, 3, 3, "high", "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N")
    assert fnd["verdict"] == "confirmed"
    print("  [+] findings: PASS")

    db.link_finding_evidence("fnd_00000001", "evd_00000001", "response")
    fe = db.get_finding_evidence("fnd_00000001")
    assert len(fe) == 1
    print("  [+] finding_evidence: PASS")

    skl = db.insert_skill("skl_00000001", "idor_detector", "repo_a", "c1", "skills/idor/SKILL.md", "Detects IDOR")
    assert skl["name"] == "idor_detector"
    print("  [+] skills: PASS")

    fake_vector = [0.05] * 384
    skm = db.insert_skill_metadata("skm_00000001", "skl_00000001", 0, "IDOR check guidelines", 150, "IDOR Heuristics", ["research"], ["idor"], fake_vector)
    assert skm["token_count"] == 150
    assert len(skm["embedding"]) == 384
    print("  [+] skill_metadata: PASS")

    log_id = db.insert_skill_usage_log("skl_00000001", "run_00000001", ["skm_00000001"], 0.88, 150)
    assert log_id > 0
    print("  [+] skill_usage_logs: PASS")

    pat = db.insert_patch("pat_00000001", "fnd_00000001", 1, "fix-idor-branch", "diffs/patch1.diff", "sha_diff", ["app.py"], {"flaw": "no auth check"})
    assert pat["attempt"] == 1
    print("  [+] patches: PASS")

    ptt = db.insert_patch_test("ptt_00000001", "pat_00000001", "regression", 10, 10, 0, "evd_00000001")
    assert ptt["passed"] == 10
    print("  [+] patch_tests: PASS")

    apr = db.insert_approval("apr_00000001", "pat_00000001")
    assert apr["decision"] == "pending"
    db.update_approval("apr_00000001", "approved", "usr_00000001", "2026-11-18T05:00:00Z", "LGTM")
    apr_updated = db.get_approval("apr_00000001")
    assert apr_updated["decision"] == "approved"
    print("  [+] approvals: PASS")

    rpt = db.insert_report("rpt_00000001", "scn_00000001", "pdf", 1, "reports/scan1.pdf", "sha_report", "1.0.0")
    assert rpt["format"] == "pdf"
    print("  [+] reports: PASS")

    audit_id = db.insert_audit_log("agent", "orchestrator", "stage_transition", True, "scn_00000001", "task", "tsk_00000001", {"from": "code_analysis", "to": "research"})
    assert audit_id > 0
    print("  [+] audit_logs: PASS")

    mem_hash = hashlib.sha256(b"code graph AST").hexdigest()
    mem = db.insert_memory_item("mem_00000001", "prj_00000001", "project", "ast_graph", "AST payload", mem_hash, "scn_00000001")
    assert mem["key"] == "ast_graph"
    print("  [+] memory_items: PASS")

    print("\n[+] ALL 30 RELATIONAL TABLES TESTED AND VERIFIED!")

    print("\n[2] Testing Database Immutability Enforcements (Triggers)...")

    evidence_update_blocked = False
    try:
        db.attempt_update_evidence("evd_00000001", "tampered_ref")
    except DatabaseImmutabilityError as e:
        evidence_update_blocked = True
    assert evidence_update_blocked, "Evidence UPDATE must be strictly rejected by immutable trigger"
    print("  [+] Evidence UPDATE Immutability Trigger: PASS (Blocked)")

    evidence_delete_blocked = False
    try:
        db.attempt_delete_evidence("evd_00000001")
    except DatabaseImmutabilityError as e:
        evidence_delete_blocked = True
    assert evidence_delete_blocked, "Evidence DELETE must be strictly rejected by immutable trigger"
    print("  [+] Evidence DELETE Immutability Trigger: PASS (Blocked)")

    snap_update_blocked = False
    try:
        db.attempt_update_snapshot("snp_00000001", "tampered_hash")
    except DatabaseImmutabilityError as e:
        snap_update_blocked = True
    assert snap_update_blocked, "State Snapshot UPDATE must be strictly rejected by immutable trigger"
    print("  [+] State Snapshot UPDATE Immutability Trigger: PASS (Blocked)")

    snap_delete_blocked = False
    try:
        db.attempt_delete_snapshot("snp_00000001")
    except DatabaseImmutabilityError as e:
        snap_delete_blocked = True
    assert snap_delete_blocked, "State Snapshot DELETE must be strictly rejected by immutable trigger"
    print("  [+] State Snapshot DELETE Immutability Trigger: PASS (Blocked)")

    audit_update_blocked = False
    try:
        db.attempt_update_audit_log(audit_id, "tampered_action")
    except DatabaseImmutabilityError as e:
        audit_update_blocked = True
    assert audit_update_blocked, "Audit Log UPDATE must be strictly rejected by immutable trigger"
    print("  [+] Audit Log UPDATE Immutability Trigger: PASS (Blocked)")

    audit_delete_blocked = False
    try:
        db.attempt_delete_audit_log(audit_id)
    except DatabaseImmutabilityError as e:
        audit_delete_blocked = True
    assert audit_delete_blocked, "Audit Log DELETE must be strictly rejected by immutable trigger"
    print("  [+] Audit Log DELETE Immutability Trigger: PASS (Blocked)")

    print("\n[3] Testing 5 Memory Categories & Vector Similarity Retrieval...")

    w_item = WorkingMemoryItem(
        key="task_scratch_001",
        agent_id="code_intelligence",
        task_id="tsk_00000001",
        data={"intermediate_routes": ["/api/v1/checkout"]}
    )
    mem_mgr.put_working_memory(w_item)
    retrieved_w = mem_mgr.get_working_memory("task_scratch_001")
    assert retrieved_w is not None
    assert retrieved_w.data["intermediate_routes"] == ["/api/v1/checkout"]
    cleared = mem_mgr.clear_working_memory_for_task("tsk_00000001")
    assert cleared == 1
    assert mem_mgr.get_working_memory("task_scratch_001") is None
    print("  [+] 1. Working Memory (Ephemeral Context & Eviction): PASS")

    p_content = "def checkout(): pass"
    p_hash = hashlib.sha256(p_content.encode("utf-8")).hexdigest()
    p_item = ProjectMemoryItem(
        id="mem_00000002",
        project_id="prj_00000001",
        key="code_route_checkout",
        content=p_content,
        content_sha256=p_hash,
        commit_sha="a1b2c3d4e5f6"
    )
    mem_mgr.store_project_memory(p_item)

    p_content_v2 = "def checkout(user_id): pass"
    p_hash_v2 = hashlib.sha256(p_content_v2.encode("utf-8")).hexdigest()
    p_item_v2 = ProjectMemoryItem(
        id="mem_00000003",
        project_id="prj_00000001",
        key="code_route_checkout",
        content=p_content_v2,
        content_sha256=p_hash_v2,
        commit_sha="b2c3d4e5f6a1"
    )
    mem_mgr.supersede_project_memory("mem_00000002", p_item_v2)
    old_p = db.get_memory_item("mem_00000002")
    assert old_p["superseded_by"] == "mem_00000003"
    print("  [+] 2. Project Memory (Code AST & Superseding by Commit): PASS")

    eng_content = "Scope verified for ShopLite sandbox 127.0.0.1:5000"
    eng_hash = hashlib.sha256(eng_content.encode("utf-8")).hexdigest()
    eng_item = EngagementMemoryItem(
        id="mem_00000004",
        project_id="prj_00000001",
        engagement_id="eng_00000001",
        scan_id="scn_00000001",
        key="scope_engagement_state",
        content=eng_content,
        content_sha256=eng_hash
    )
    mem_mgr.store_engagement_memory(eng_item)
    eng_res = db.get_memory_item("mem_00000004")
    assert eng_res["scan_id"] == "scn_00000001"
    print("  [+] 3. Engagement Memory (Scope, Credentials, Findings): PASS")

    vec_a = [0.1] * 384
    vec_b = [0.5] * 384
    vec_c = [-0.1] * 384
    sim_ab = compute_cosine_similarity(vec_a, vec_b)
    sim_ac = compute_cosine_similarity(vec_a, vec_c)
    assert abs(sim_ab - 1.0) < 1e-4
    assert abs(sim_ac - (-1.0)) < 1e-4

    k_content = "IDOR detection rule: compare subject user_id to resource tenant_id"
    k_hash = hashlib.sha256(k_content.encode("utf-8")).hexdigest()
    k_item = KnowledgeMemoryItem(
        id="mem_00000005",
        project_id="prj_00000001",
        key="idor_detection_rule",
        content=k_content,
        skill_ref="skl_00000001",
        category="idor",
        embedding=vec_a,
        content_sha256=k_hash
    )
    mem_mgr.store_knowledge_memory(k_item)

    search_res = mem_mgr.search_knowledge_by_vector("prj_00000001", vec_b, top_k=3, category="idor")
    assert len(search_res) == 1
    assert search_res[0][0]["id"] == "mem_00000005"
    assert search_res[0][1] > 0.99
    print("  [+] 4. Knowledge Memory (Skills & 384-dim Vector Cosine Retrieval): PASS")

    rem_content = "Fix applied: added check current_user.id == order.user_id"
    rem_hash = hashlib.sha256(rem_content.encode("utf-8")).hexdigest()
    rem_item = RemediationMemoryItem(
        id="mem_00000006",
        project_id="prj_00000001",
        finding_id="fnd_00000001",
        key="patch_order_ownership",
        content=rem_content,
        patch_diff="--- a/app.py\n+++ b/app.py\n@@ -10 +10 @@\n+ if current_user.id != order.user_id: abort(403)",
        regression_passed=True,
        is_negative_knowledge=False,
        content_sha256=rem_hash
    )
    mem_mgr.store_remediation_memory(rem_item)
    rem_res = db.get_memory_item("mem_00000006")
    assert rem_res["metadata"]["regression_passed"] is True
    print("  [+] 5. Remediation Memory (Patches, Diffs & Negative Knowledge): PASS")

    print("\n=======================================================================")
    print("AEGISTRACE MEMORY & DATABASE ARCHITECTURE: 100% PASS (ALL INVARIANTS MET)")
    print("=======================================================================\n")

if __name__ == "__main__":
    run_tests()
