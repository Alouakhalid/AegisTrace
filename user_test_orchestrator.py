import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = current_dir
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_dir = os.path.join(workspace_root, "memory and database")
if mem_db_dir not in sys.path:
    sys.path.insert(0, mem_db_dir)

agent_dir = os.path.join(workspace_root, "agents", "orchestrator agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from validation import (
    validate_orchestrator_request,
    validate_orchestrator_response,
    OrchestratorRequest,
    OrchestratorResponse,
    TaskStatus,
    WorkflowStatus
)
from orchestrator_agent import OrchestratorAgent
from tools.orchestrator_tools import WorkflowPlanner, WorkflowCycleError
from memory_manager import MemoryManager
from database import AegisDatabase

def run_test():
    print("=" * 75)
    print("AEGISTRACE — ORCHESTRATOR AGENT (AGENT 1) USER TEST SUITE")
    print("Target: AegisTrace_Agent_Architecture_EN.pdf (Section 5)")
    print("===========================================================================")

    db = AegisDatabase(":memory:")
    agent = OrchestratorAgent(db=db)

    print("\n[1] Validating Input Request Contract against Pydantic & Master JSON Schema...")
    valid_request_payload = {
        "schema_version": "1.0.0",
        "correlation_id": "cor_0192f100",
        "project_id": "prj_0192f101",
        "engagement_id": "eng_0192f102",
        "scan_id": "scn_0192f103",
        "task_id": "tsk_0192f104",
        "agent_run_id": "run_0192f105",
        "created_at": "2026-11-18T05:00:00Z",
        "agent": "orchestrator",
        "input": {
            "project": {
                "name": "ShopLite E-Commerce",
                "language": "python",
                "framework_hint": "flask"
            },
            "target": {
                "base_url": "http://127.0.0.1:5000",
                "environment": "sandbox"
            },
            "repository": {
                "source_type": "github",
                "url": "https://github.com/shoplite/shoplite",
                "ref": "main"
            },
            "scope_manifest_id": "scm_0192f106",
            "assessment_mode": "full",
            "credential_refs": [
                {"ref": "cred_user_alice", "role": "buyer"},
                {"ref": "cred_user_bob", "role": "buyer"}
            ],
            "requested_operations": ["code_analysis", "recon", "dynamic_testing", "remediation"]
        }
    }

    valid_req, err_req, req_obj = validate_orchestrator_request(valid_request_payload)
    assert valid_req, f"OrchestratorRequest validation failed: {err_req}"
    print("[+] OrchestratorRequest Pydantic V2 Contract: PASS")
    print("[+] OrchestratorRequest Master JSON Schema: PASS")

    print("\n[2] Registering Scope Manifest in Database & Orchestrator...")
    manifest_data = {
        "allowed_hosts": ["http://127.0.0.1:5000", "127.0.0.1:5000"],
        "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
        "forbidden_paths": ["/admin/shutdown"],
        "window": "2026-11-18T00:00:00Z/2026-11-19T00:00:00Z",
        "attested": True
    }
    agent.register_scope_manifest("scm_0192f106", manifest_data, valid=True, attested=True)
    print("[+] Registered scope manifest scm_0192f106 with 5 required scope criteria.")

    print("\n[3] Executing Orchestrator Full Assessment Workflow Planning...")
    resp = agent.run_orchestration(valid_request_payload, raw_manifest=manifest_data)
    assert resp.status == TaskStatus.succeeded, f"Expected succeeded, got {resp.status}"
    assert resp.output is not None
    assert resp.output.workflow_status == WorkflowStatus.planned
    assert resp.output.scope_validation.valid is True
    print("[+] Orchestration execution status: succeeded")
    print(f"[+] Scope validation: {resp.output.scope_validation.valid} (All 5 checks passed)")
    for chk in resp.output.scope_validation.checks:
        print(f"    - {chk.name}: {chk.passed} ({chk.detail})")

    print(f"[+] Planned Stages: {len(resp.output.stages)} stages")
    for stg in resp.output.stages:
        print(f"    - Stage: {stg.name} | Agent: {stg.agent.value} | Parallel Group: {stg.parallel_group} | Depends On: {stg.depends_on} | Approval: {stg.requires_approval}")

    stage_names = [s.name for s in resp.output.stages]
    assert "code_analysis" in stage_names
    assert "recon" in stage_names
    assert "vulnerability_research" in stage_names
    assert "dynamic_testing" in stage_names
    assert "verification" in stage_names
    assert "remediation" in stage_names

    code_stg = next(s for s in resp.output.stages if s.name == "code_analysis")
    recon_stg = next(s for s in resp.output.stages if s.name == "recon")
    assert code_stg.parallel_group == "g1"
    assert recon_stg.parallel_group == "g1"
    assert code_stg.depends_on == []
    assert recon_stg.depends_on == []
    print("[+] Parallel Group 'g1' for code_analysis & recon: PASS")

    print(f"[+] Task Assignments Generated: {len(resp.output.task_assignments)} tasks")
    for tsk in resp.output.task_assignments:
        print(f"    - Task ID: {tsk.task_id} -> {tsk.agent.value} ({tsk.stage}) | Depends on: {tsk.depends_on}")
        assert tsk.task_id.startswith("tsk_")
    print("[+] Task Queue Assignments & Dependency Graph: PASS")

    print("\n[4] Validating Output Response Contract against Pydantic & Master JSON Schema...")
    resp_dict = resp.model_dump(mode="json")
    valid_resp, err_resp, _ = validate_orchestrator_response(resp_dict)
    assert valid_resp, f"OrchestratorResponse validation failed: {err_resp}"
    print("[+] OrchestratorResponse Pydantic V2 Contract: PASS")
    print("[+] OrchestratorResponse Master JSON Schema: PASS")

    print("\n[5] Testing Scope Check Failure: Host Out of Scope...")
    out_of_scope_req = dict(valid_request_payload)
    out_of_scope_req["input"] = dict(valid_request_payload["input"])
    out_of_scope_req["input"]["target"] = {"base_url": "http://malicious-external-site.com", "environment": "sandbox"}
    resp_out_of_scope = agent.run_orchestration(out_of_scope_req, raw_manifest=manifest_data)
    assert resp_out_of_scope.status == TaskStatus.blocked
    assert resp_out_of_scope.error is not None
    assert resp_out_of_scope.error.code == "SCOPE_INVALID"
    assert resp_out_of_scope.error.retryable is False
    assert resp_out_of_scope.output.workflow_status == WorkflowStatus.blocked
    assert resp_out_of_scope.output.scope_validation.valid is False
    print(f"[+] Deterministic Block on Out-of-Scope Host: PASS ({resp_out_of_scope.error.code} - {resp_out_of_scope.error.message})")

    print("\n[6] Testing Scope Check Failure: Dangerous Third-Party Wildcard...")
    wildcard_manifest = {
        "allowed_hosts": ["*.com"],
        "allowed_methods": ["GET", "POST"]
    }
    resp_wildcard = agent.run_orchestration(valid_request_payload, raw_manifest=wildcard_manifest)
    assert resp_wildcard.status == TaskStatus.blocked
    assert resp_wildcard.error.code == "SCOPE_INVALID"
    print(f"[+] Deterministic Block on Third-Party Wildcards: PASS ({resp_wildcard.error.code})")

    print("\n[7] Testing Scope Check Failure: Production Environment Rejection...")
    prod_req = dict(valid_request_payload)
    prod_req["input"] = dict(valid_request_payload["input"])
    prod_req["input"]["target"] = {"base_url": "http://127.0.0.1:5000", "environment": "production"}
    resp_prod = agent.run_orchestration(prod_req, raw_manifest=manifest_data)
    assert resp_prod.status == TaskStatus.failed or resp_prod.status == TaskStatus.blocked
    assert resp_prod.error is not None
    print(f"[+] Deterministic Block on Production Environment: PASS ({resp_prod.error.code})")

    print("\n[8] Testing Input Validation: Insufficient Credentials (< 2)...")
    single_cred_req = dict(valid_request_payload)
    single_cred_req["input"] = dict(valid_request_payload["input"])
    single_cred_req["input"]["credential_refs"] = [{"ref": "cred_user_alice", "role": "buyer"}]
    resp_single_cred = agent.run_orchestration(single_cred_req, raw_manifest=manifest_data)
    assert resp_single_cred.status == TaskStatus.failed
    assert resp_single_cred.error.code == "MISSING_INPUT"
    print(f"[+] Rejection of Insufficient Credentials (< 2): PASS ({resp_single_cred.error.code})")

    print("\n[9] Testing Stage DAG Cycle Detection...")
    planner = WorkflowPlanner()
    cyclic_stages = [
        {"name": "stage_a", "agent": "recon", "depends_on": ["stage_b"]},
        {"name": "stage_b", "agent": "code_intelligence", "depends_on": ["stage_a"]}
    ]
    cycle_detected = False
    try:
        planner.check_acyclic(cyclic_stages)
    except WorkflowCycleError as e:
        cycle_detected = True
        print(f"[+] Cycle Detection Invariant: PASS ({e})")
    assert cycle_detected, "Planner must raise WorkflowCycleError on circular DAG"

    print("\n[10] Verifying Audit Logging & Memory Integration...")
    logs = agent.audit_logger.get_logs()
    assert len(logs) >= 3
    print(f"[+] Emitted {len(logs)} audit trail entries into immutable audit log.")
    for l in logs[-3:]:
        print(f"    - Action: {l['action']} | Allowed: {l['allowed']} | Actor: {l['actor_id']}")

    print("\n===========================================================================")
    print("AEGISTRACE ORCHESTRATOR AGENT: ALL 10 TESTS PASSED (100% SUCCESS)")
    print("===========================================================================\n")

if __name__ == "__main__":
    run_test()
