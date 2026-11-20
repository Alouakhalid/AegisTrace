import os
import sys
import json
import uuid
import time
import hashlib
import shutil
import tempfile
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

workspace_root = os.path.dirname(os.path.abspath(__file__))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_dir = os.path.join(workspace_root, "memory and database")
if mem_db_dir not in sys.path:
    sys.path.insert(0, mem_db_dir)

from database import AegisDatabase, DatabaseImmutabilityError
from memory_manager import MemoryManager, compute_cosine_similarity
from memory_models import (
    WorkingMemoryItem,
    ProjectMemoryItem,
    EngagementMemoryItem,
    KnowledgeMemoryItem,
    RemediationMemoryItem
)

def load_orchestrator():
    p = os.path.join(workspace_root, "agents", "orchestrator_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import orchestrator_agent
    return orchestrator_agent.OrchestratorAgent

def load_code_intel():
    p = os.path.join(workspace_root, "agents", "code_intelligence_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import code_intelligence_agent
    return code_intelligence_agent.run_code_intelligence

def load_recon():
    p = os.path.join(workspace_root, "agents", "recon_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import recon_agent
    return recon_agent.run_recon

def load_vuln_research():
    p = os.path.join(workspace_root, "agents", "vulnerability_research_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import vuln_research_agent
    return vuln_research_agent.run_vulnerability_research

def load_dynamic_testing():
    p = os.path.join(workspace_root, "agents", "dynamic_testing_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import dynamic_testing_agent
    return dynamic_testing_agent.DynamicTestingAgent

def load_verification():
    p = os.path.join(workspace_root, "agents", "verification_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import verification_agent
    return verification_agent.VerificationAgent, verification_agent.EvidenceStore

def load_remediation():
    p = os.path.join(workspace_root, "agents", "remediation_agent")
    if p not in sys.path:
        sys.path.insert(0, p)
    sys.modules.pop("validation", None)
    import remediation_agent
    return remediation_agent.RemediationAgent

def make_git_repo():
    repo = tempfile.mkdtemp(prefix="aegis_remediation_repo_")
    os.makedirs(os.path.join(repo, "dummy_web"), exist_ok=True)
    shutil.copy2(
        os.path.join(workspace_root, "dummy_web", "target_app.py"),
        os.path.join(repo, "dummy_web", "target_app.py"),
    )
    for suite in ("unit", "integration", "regression"):
        suite_dir = os.path.join(repo, "tests", suite)
        os.makedirs(suite_dir, exist_ok=True)
        with open(os.path.join(suite_dir, f"test_{suite}.py"), "w", encoding="utf-8") as handle:
            handle.write("def test_suite_is_runnable():\n    assert True\n")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "aegistrace@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "AegisTrace Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "fixture baseline"], cwd=repo, check=True, capture_output=True)
    return repo

def run_integration_test():
    print("=" * 80)
    print("AEGISTRACE — END-TO-END MULTI-AGENT & MEMORY/DATABASE INTEGRATION PIPELINE")
    print("Target: 7 Agents Coordinated via AegisDatabase & MemoryManager")
    print("================================================================================")

    db = AegisDatabase(":memory:")
    mem_mgr = MemoryManager(db)

    print("\n[0] Seeding Initial Skills & 384-dimensional Vector Embeddings into Knowledge Base...")
    db.create_user("usr_00000001", "operator@aegistrace.io", "System Operator", "analyst")
    db.create_project("prj_0192f101", "usr_00000001", "ShopLite E-Commerce", "python", "flask")
    
    idor_vec = [0.08] * 384
    db.insert_skill("skl_cbh_001", "hunt-idor", "skills/Claude-BugHunter", "c1", "skills/idor/SKILL.md", "IDOR and Horizontal Privilege Escalation Hunting", category="idor")
    db.insert_skill_metadata("skm_cbh_001", "skl_cbh_001", 0, "Compare owner user_id to session subject", 200, "IDOR Methodology", ["research", "dynamic_testing"], ["idor"], idor_vec)
    
    k_item = KnowledgeMemoryItem(
        id="mem_0192f001",
        project_id="prj_0192f101",
        key="idor_attack_heuristic",
        content="IDOR detection strategy: verify if secondary tenant can modify primary tenant order",
        skill_ref="skl_cbh_001",
        category="idor",
        embedding=idor_vec,
        content_sha256=hashlib.sha256(b"idor_heuristic").hexdigest()
    )
    mem_mgr.store_knowledge_memory(k_item)
    print("  [+] Seeded skill skl_cbh_001 with 384-dim vector embedding.")

    print("\n[1] Executing Agent 1: Orchestrator Agent...")
    OrchestratorCls = load_orchestrator()
    orch_agent = OrchestratorCls(db=db)
    
    manifest_data = {
        "allowed_hosts": ["http://127.0.0.1:5000", "127.0.0.1:5000", "shoplite.example.com"],
        "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
        "forbidden_paths": ["/admin/shutdown"],
        "window": "2026-11-18T00:00:00Z/2026-11-19T00:00:00Z",
        "attested": True
    }
    orch_agent.register_scope_manifest("scm_0192f106", manifest_data, valid=True, attested=True)

    orch_request = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa01",
        "agent_run_id": "run_0192fb01",
        "created_at": "2026-11-18T05:00:00Z",
        "agent": "orchestrator",
        "input": {
            "project": {"name": "ShopLite E-Commerce", "language": "python", "framework_hint": "flask"},
            "target": {"base_url": "http://127.0.0.1:5000", "environment": "sandbox"},
            "repository": {"source_type": "github", "url": "https://github.com/shoplite/shoplite", "ref": "main"},
            "scope_manifest_id": "scm_0192f106",
            "assessment_mode": "full",
            "credential_refs": [
                {"ref": "cred_user_alice", "role": "buyer"},
                {"ref": "cred_user_bob", "role": "buyer"}
            ],
            "requested_operations": ["code_analysis", "recon", "dynamic_testing", "remediation"]
        }
    }
    orch_resp = orch_agent.run_orchestration(orch_request, raw_manifest=manifest_data)
    assert orch_resp.status.value == "succeeded"
    assert db.get_scan("scn_0192f103") is not None
    assert db.get_scope_manifest("scm_0192f106") is not None
    tasks_count = len(db.list_agent_tasks("scn_0192f103"))
    assert tasks_count >= 6
    task_map = {a.stage: a.task_id for a in orch_resp.output.task_assignments}
    print(f"  [+] Orchestrator execution: succeeded | Planned stages: {len(orch_resp.output.stages)} | Tasks in DB: {tasks_count}")

    print("\n[2] Executing Agent 2: Code Intelligence Agent...")
    sample_app_dir = os.path.join(workspace_root, "test_shoplite_repo")
    os.makedirs(sample_app_dir, exist_ok=True)
    run_ci = load_code_intel()
    code_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa02",
        "agent_run_id": "run_0192fb02",
        "created_at": "2026-11-18T05:01:00Z",
        "agent": "code_intelligence",
        "input": {
            "repository": {
                "path_ref": sample_app_dir,
                "commit": "a1b2c3d4e5f678"
            },
            "source_language": "python",
            "framework_hints": ["fastapi", "sqlalchemy"],
            "scan_config": {
                "max_files": 50,
                "include_globs": ["**/*.py"],
                "enable_semgrep": True
            }
        }
    }
    code_resp = run_ci(code_req, db=db)
    assert code_resp["status"] == "succeeded"
    invs = db.get_security_invariants("prj_0192f101")
    assert len(invs) >= 1
    p_mems = mem_mgr.get_memories_by_type("prj_0192f101", "project")
    assert len(p_mems) >= 1
    print(f"  [+] Code Intelligence: succeeded | Invariants saved to DB: {len(invs)} | Project Memory items: {len(p_mems)}")

    print("\n[3] Executing Agent 3: Recon Agent...")
    run_rc = load_recon()
    spec_path = os.path.join(workspace_root, "openapi_test.json")
    if not os.path.exists(spec_path):
        sample_spec = {
            "openapi": "3.0.0",
            "info": {"title": "ShopLite API", "version": "1.0.0"},
            "paths": {
                "/api/v1/orders/{order_id}": {
                    "patch": {
                        "summary": "Update order",
                        "operationId": "updateOrder",
                        "security": [{"bearerAuth": []}]
                    }
                }
            }
        }
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(sample_spec, f, indent=2)

    recon_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa03",
        "agent_run_id": "run_0192fb03",
        "created_at": "2026-11-18T05:02:00Z",
        "agent": "recon",
        "input": {
            "scope": {
                "allowed_hosts": ["127.0.0.1:5000", "shoplite.example.com", "shoplite-app:8000", "shoplite-app"],
                "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
                "forbidden_paths": ["/admin/shutdown"]
            },
            "api_spec_ref": spec_path,
            "technology_hints": ["fastapi", "postgresql"],
            "research": {
                "enabled": False,
                "max_queries": 1,
                "search_depth": "basic"
            }
        }
    }
    recon_resp = run_rc(recon_req, db=db)
    assert recon_resp["status"] == "succeeded"
    eps = db.get_endpoints("scn_0192f103")
    assert len(eps) >= 1
    print(f"  [+] Recon Surface: succeeded | Attack Surface Endpoints saved to DB: {len(eps)}")

    print("\n[4] Executing Agent 4: Vulnerability Research Agent...")
    research_query_vec = [0.08] * 384
    matched_skills = mem_mgr.search_knowledge_by_vector("prj_0192f101", research_query_vec, top_k=2, category="idor")
    assert len(matched_skills) >= 1
    print(f"  [+] Vector Retrieval over Knowledge Memory (384-dim Cosine): Found {len(matched_skills)} relevant skills (Score: {matched_skills[0][1]:.4f})")

    cache_dir = os.path.join(workspace_root, ".aegistrace_cache", "tasks")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "tsk_0192fa02.json"), "w", encoding="utf-8") as f:
        json.dump({"output": code_resp.get("output")}, f)
    with open(os.path.join(cache_dir, "tsk_0192fa03.json"), "w", encoding="utf-8") as f:
        json.dump({"output": recon_resp.get("output")}, f)

    run_vr = load_vuln_research()
    first_inv_id = invs[0]["id"]
    research_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa04",
        "agent_run_id": "run_0192fb04",
        "created_at": "2026-11-18T05:03:00Z",
        "agent": "vulnerability_research",
        "input": {
            "code_intel_ref": "out://tsk_0192fa02",
            "recon_ref": "out://tsk_0192fa03",
            "invariant_ids": [first_inv_id],
            "skill_hits": [
                {
                    "skill": "hunt-idor",
                    "source_commit": "64410ed",
                    "score": 0.95
                }
            ]
        }
    }
    research_resp = run_vr(research_req, code_intel_output=code_resp.get("output"), recon_output=recon_resp.get("output"), db=db)
    assert research_resp["status"] == "succeeded"
    hyps = db.get_vulnerability_hypotheses("scn_0192f103")
    assert len(hyps) >= 1
    first_hyp_id = hyps[0]["id"]
    test_plans = db.get_test_cases(first_hyp_id)
    assert len(test_plans) >= 1
    print(f"  [+] Vulnerability Research: succeeded | Hypotheses in DB: {len(hyps)} | Test Plans in DB: {len(test_plans)}")

    print("\n[5] Executing Agent 5: Dynamic Testing Agent...")
    DynamicCls = load_dynamic_testing()
    dynamic_agent = DynamicCls(db=db)
    chosen_plan = test_plans[0]
    target_ep = next((e for e in eps if "order" in e["path"] and e["method"] == "PATCH"), eps[0])
    dt_task_id = task_map.get("dynamic_testing", "tsk_0192fa05")
    dynamic_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": dt_task_id,
        "agent_run_id": "run_0192fb05",
        "created_at": "2026-11-18T05:04:00Z",
        "agent": "dynamic_testing",
        "input": {
            "test_plan": {
                "test_plan_id": chosen_plan["id"],
                "hypothesis_id": chosen_plan["hypothesis_id"],
                "method": "paired_identity",
                "steps": [
                    "Snapshot orders.id=100",
                    "As buyer_a (owner) PATCH /api/v1/orders/100 with baseline address",
                    "Snapshot orders.id=100",
                    "As buyer_b (non-owner) PATCH /api/v1/orders/100 with distinct address",
                    "Snapshot orders.id=100 and diff"
                ],
                "identities": ["id_buyer_a", "id_buyer_b"],
                "expected_secure_behavior": "Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
                "state_checks": [
                    {
                        "table": "orders",
                        "key": {"id": 100},
                        "columns": ["shipping_address"]
                    }
                ]
            },
            "endpoint": {
                "endpoint_id": target_ep["id"],
                "method": target_ep["method"],
                "path": target_ep["path"],
                "path_params": target_ep["path_params"],
                "auth_required": bool(target_ep["auth_required"]),
                "source": target_ep["source"]
            },
            "identities": [
                {
                    "identity_id": "id_buyer_a",
                    "role": "customer",
                    "credential_ref": "cred_buyer_a",
                    "owns": {"order_id": 100}
                },
                {
                    "identity_id": "id_buyer_b",
                    "role": "customer",
                    "credential_ref": "cred_buyer_b",
                    "owns": {"order_id": 200}
                }
            ],
            "sandbox": {
                "sandbox_id": "sbx_0192f2f0",
                "base_url": "http://127.0.0.1:5000",
                "snapshot_enabled": True,
                "max_requests": 200
            },
            "invariant_id": first_inv_id
        }
    }
    dynamic_resp = dynamic_agent.execute(dynamic_req)
    assert dynamic_resp["status"] == "succeeded"
    executions = db.conn.execute("SELECT COUNT(*) FROM test_executions WHERE task_id = ?;", (dt_task_id,)).fetchone()[0]
    assert executions >= 1
    snapshots = db.get_state_snapshots("scn_0192f103")
    assert len(snapshots) >= 1
    print(f"  [+] Dynamic Testing: succeeded | Test Executions in DB: {executions} | State Snapshots in DB: {len(snapshots)}")

    print("\n[6] Executing Agent 6: Verification Agent...")
    VerifCls, EvidenceStoreCls = load_verification()
    verif_agent = VerifCls(db=db)
    store = EvidenceStoreCls()
    
    evd_1 = "evd_0192fe01"
    evd_1_body = "HTTP 200: Order shipping address updated to Alice by Bob"
    evd_1_sha = store.register_evidence(evd_1, evd_1_body)
    db.insert_evidence(evd_1, "scn_0192f103", "http_exchange", f"s3://aegis/{evd_1}.json", evd_1_sha)

    with open(os.path.join(cache_dir, "tsk_0192fa05.json"), "w", encoding="utf-8") as f:
        json.dump({"output": dynamic_resp.get("output")}, f)

    verif_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa06",
        "agent_run_id": "run_0192fb06",
        "created_at": "2026-11-18T05:05:00Z",
        "agent": "verification",
        "input": {
            "hypothesis": {
                "hypothesis_id": first_hyp_id,
                "category": hyps[0]["category"],
                "title": hyps[0]["title"],
                "rationale": hyps[0]["rationale"],
                "endpoint_id": target_ep["id"],
                "invariant_id": first_inv_id,
                "priority": hyps[0]["priority"],
                "skill_refs": ["hunt-idor"]
            },
            "dynamic_result_ref": "out://tsk_0192fa05",
            "evidence_ids": [evd_1],
            "invariant_statement": "An order may be read or modified only by the user referenced in orders.user_id",
            "reproduction_runs_requested": 3
        }
    }
    target_url = f"http://127.0.0.1:5000{target_ep['path'].replace('{order_id}', '100')}"
    replay_steps = [
        {
            "method": "PATCH",
            "url": target_url,
            "identity_id": "id_buyer_b",
            "json_payload": {"shipping_address": "Tampered Address by Bob"}
        }
    ]
    verif_resp = verif_agent.execute(verif_req, evidence_store=store, test_steps=replay_steps)
    assert verif_resp["status"] == "succeeded"
    findings = db.list_findings("scn_0192f103")
    assert len(findings) >= 1
    first_fnd_id = findings[0]["id"]
    fe = db.get_finding_evidence(first_fnd_id)
    assert len(fe) >= 1
    print(f"  [+] Verification: succeeded | Confirmed Findings in DB: {len(findings)} | Linked Finding Evidence: {len(fe)}")

    print("\n[7] Executing Agent 7: Remediation Agent...")
    RemCls = load_remediation()
    rem_agent = RemCls(db=db)
    from tools.remediation_tools import IsolatedGitManager, SandboxTestRunner
    repo = make_git_repo()
    rem_req = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192fa07",
        "agent_run_id": "run_0192fb07",
        "created_at": "2026-11-18T05:06:00Z",
        "agent": "remediation",
        "input": {
            "finding_id": first_fnd_id,
            "source_refs": [
                {
                    "file": "dummy_web/target_app.py",
                    "start_line": 87,
                    "end_line": 96
                }
            ],
            "verification_evidence_ids": [evd_1],
            "test_environment": {
                "sandbox_id": "sbx_0192f2f0",
                "base_url": "http://127.0.0.1:5000",
                "snapshot_enabled": True,
                "max_requests": 200
            },
            "original_test_plan_id": chosen_plan["id"],
            "max_attempts": 3
        }
    }
    rem_resp = rem_agent.execute(
        rem_req,
        finding_verdict="confirmed",
        git_manager=IsolatedGitManager(repo),
        test_runner=SandboxTestRunner(repo),
        test_steps=replay_steps,
        state_checks=[{"table": "orders", "key": {"id": 100}, "columns": ["shipping_address"]}],
    )
    assert rem_resp["status"] == "succeeded"
    patches = db.get_patches(first_fnd_id)
    assert len(patches) >= 1
    first_pat_id = patches[0]["id"]
    tests_run = db.get_patch_tests(first_pat_id)
    assert len(tests_run) >= 1
    approvals = db.conn.execute("SELECT * FROM approvals WHERE patch_id = ?;", (first_pat_id,)).fetchall()
    assert len(approvals) >= 1
    rem_mems = mem_mgr.get_memories_by_type("prj_0192f101", "remediation")
    assert len(rem_mems) >= 1
    print(f"  [+] Remediation: succeeded | Patches in DB: {len(patches)} | Tests Run: {len(tests_run)} | Approvals: {len(approvals)} | Remediation Memory: {len(rem_mems)}")

    print("\n[8] Verifying Database Immutability Enforcements Across Pipeline...")
    blocked_evd_delete = False
    try:
        db.attempt_delete_evidence(evd_1)
    except DatabaseImmutabilityError:
        blocked_evd_delete = True
    assert blocked_evd_delete, "Evidence rows must remain strictly append-only across pipeline execution"
    print("  [+] Immutability Invariant: Evidence and State Snapshots delete strictly blocked by SQL trigger.")

    print("\n[9] Summary of Relational Tables and Memory Categories Populated:")
    table_counts = {
        "users": db.conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0],
        "projects": db.conn.execute("SELECT COUNT(*) FROM projects;").fetchone()[0],
        "engagements": db.conn.execute("SELECT COUNT(*) FROM engagements;").fetchone()[0],
        "scope_manifests": db.conn.execute("SELECT COUNT(*) FROM scope_manifests;").fetchone()[0],
        "scans": db.conn.execute("SELECT COUNT(*) FROM scans;").fetchone()[0],
        "agent_tasks": db.conn.execute("SELECT COUNT(*) FROM agent_tasks;").fetchone()[0],
        "agent_runs": db.conn.execute("SELECT COUNT(*) FROM agent_runs;").fetchone()[0],
        "security_invariants": db.conn.execute("SELECT COUNT(*) FROM security_invariants;").fetchone()[0],
        "endpoints": db.conn.execute("SELECT COUNT(*) FROM endpoints;").fetchone()[0],
        "vulnerability_hypotheses": db.conn.execute("SELECT COUNT(*) FROM vulnerability_hypotheses;").fetchone()[0],
        "test_cases": db.conn.execute("SELECT COUNT(*) FROM test_cases;").fetchone()[0],
        "evidence": db.conn.execute("SELECT COUNT(*) FROM evidence;").fetchone()[0],
        "test_executions": db.conn.execute("SELECT COUNT(*) FROM test_executions;").fetchone()[0],
        "state_snapshots": db.conn.execute("SELECT COUNT(*) FROM state_snapshots;").fetchone()[0],
        "findings": db.conn.execute("SELECT COUNT(*) FROM findings;").fetchone()[0],
        "finding_evidence": db.conn.execute("SELECT COUNT(*) FROM finding_evidence;").fetchone()[0],
        "skills": db.conn.execute("SELECT COUNT(*) FROM skills;").fetchone()[0],
        "skill_metadata": db.conn.execute("SELECT COUNT(*) FROM skill_metadata;").fetchone()[0],
        "patches": db.conn.execute("SELECT COUNT(*) FROM patches;").fetchone()[0],
        "patch_tests": db.conn.execute("SELECT COUNT(*) FROM patch_tests;").fetchone()[0],
        "approvals": db.conn.execute("SELECT COUNT(*) FROM approvals;").fetchone()[0],
        "audit_logs": db.conn.execute("SELECT COUNT(*) FROM audit_logs;").fetchone()[0],
        "memory_items": db.conn.execute("SELECT COUNT(*) FROM memory_items;").fetchone()[0]
    }
    for tbl, count in table_counts.items():
        print(f"    - Table '{tbl}': {count} records populated")

    print("\n================================================================================")
    print("AEGISTRACE ALL 7 AGENTS + MEMORY & DATABASE INTEGRATION: 100% PASS (ALL INVARIANTS MET)")
    print("================================================================================\n")

if __name__ == "__main__":
    run_integration_test()
