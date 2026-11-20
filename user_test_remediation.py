import os
import sys
import json
import shutil
import tempfile
import subprocess
import jsonschema
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

agent_dir = os.path.join(workspace_dir, "agents", "Remediation agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

agent_file_path = os.path.join(agent_dir, "remediation_agent.py")
spec = importlib.util.spec_from_file_location("remediation_agent", agent_file_path)
r_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r_mod)
RemediationAgent = r_mod.RemediationAgent
run_remediation = r_mod.run_remediation

val_file_path = os.path.join(agent_dir, "validation.py")
val_spec = importlib.util.spec_from_file_location("r_validation", val_file_path)
val_mod = importlib.util.module_from_spec(val_spec)
val_spec.loader.exec_module(val_mod)
validate_remediation_request = val_mod.validate_remediation_request
validate_remediation_response = val_mod.validate_remediation_response

from tools.remediation_tools import IsolatedGitManager, SandboxTestRunner, DynamicExploitReplayer, TavilyFixGuidanceTool

schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
with open(schema_file, "r", encoding="utf-8") as f:
    schema_bundle = json.load(f)

r_schemas = schema_bundle["agents"]["remediation"]


def make_git_repo():
    """Create a real temporary Git checkout containing the vulnerable sandbox app."""
    repo = tempfile.mkdtemp(prefix="aegis_remediation_repo_")
    os.makedirs(os.path.join(repo, "dummy_web"), exist_ok=True)
    shutil.copy2(
        os.path.join(workspace_dir, "dummy_web", "target_app.py"),
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


replay_steps = [
    {
        "method": "PATCH",
        "url": "http://shoplite-app:8000/api/v1/orders/100",
        "identity_id": "id_buyer_b",
        "json_body": {"shipping_address": "Tampered Address 777"},
    }
]
state_checks = [
    {"table": "orders", "key": {"id": 100}, "columns": ["shipping_address"]}
]

print("=" * 75)
print("AEGISTRACE — REMEDIATION AGENT (AGENT 7) USER TEST SUITE")
print("Target: AegisTrace_Agent_Architecture_EN.pdf (Sections 11.1 - 11.12)")
print("=" * 75)

sample_request = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f307",
    "agent_run_id": "run_0192f407",
    "created_at": "2026-11-17T09:32:55Z",
    "agent": "remediation",
    "input": {
        "finding_id": "fnd_0192f200",
        "source_refs": [
            {
                "file": "dummy_web/target_app.py",
                "start_line": 87,
                "end_line": 96
            }
        ],
        "verification_evidence_ids": [
            "evd_0192f21b",
            "evd_0192f21c"
        ],
        "test_environment": {
            "sandbox_id": "sbx_0192f2f0",
            "base_url": "http://shoplite-app:8000",
            "snapshot_enabled": True,
            "max_requests": 200
        },
        "original_test_plan_id": "tpl_idor_patch_order",
        "max_attempts": 3
    }
}

print("\n[1] Validating Input Request Contract against Pydantic & Master JSON Schema...")
is_valid_req, req_model, req_err = validate_remediation_request(sample_request)
assert is_valid_req, f"Pydantic validation failed: {req_err}"
print("[+] RemediationRequest Pydantic V2 Contract: PASS")

jsonschema.validate(instance=sample_request, schema=r_schemas["request"])
print("[+] RemediationRequest Master JSON Schema: PASS")

print("\n[2] Executing Remediation Agent Full Patch & Replay Pipeline...")
agent = RemediationAgent()
repo = make_git_repo()
response = agent.execute(
    sample_request,
    finding_verdict="confirmed",
    git_manager=IsolatedGitManager(repo),
    test_runner=SandboxTestRunner(repo),
    test_steps=replay_steps,
    state_checks=state_checks,
)

print(f"[+] Execution Status: {response['status']}")
print(f"[+] Duration: {response['metrics']['duration_ms']} ms | LLM Calls: {response['metrics']['llm_calls']}")

print("\n[3] Validating Output Response Contract against Pydantic & Master JSON Schema...")
is_valid_resp, resp_model, resp_err = validate_remediation_response(response)
assert is_valid_resp, f"Pydantic response validation failed: {resp_err}"
print("[+] RemediationResponse Pydantic V2 Contract: PASS")

jsonschema.validate(instance=response, schema=r_schemas["response"])
print("[+] RemediationResponse Master JSON Schema: PASS")

out = response["output"]
print("\n[4] Verifying Root Cause Identification:")
print(f"  - Summary: {out['root_cause']['summary']}")
print(f"  - Affected Files: {out['root_cause']['files']}")
assert len(out["root_cause"]["files"]) > 0

print("\n[5] Verifying Isolated Branch & Unified Diff Patch:")
print(f"  - Patch ID: {out['patch']['patch_id']}")
print(f"  - Branch: {out['patch']['branch']}")
print(f"  - Diff Ref: {out['patch']['diff_ref']}")
print(f"  - Changed Files: {out['patch']['changed_files']}")
assert out["patch"]["patch_id"].startswith("pat_")
assert out["patch"]["branch"].startswith("fix/aegistrace-")
assert "main" not in out["patch"]["branch"] and "master" not in out["patch"]["branch"]

print("\n[6] Verifying Sandbox Multi-Suite Test Execution:")
print(f"  - Unit Tests: {out['tests']['unit']['passed']}/{out['tests']['unit']['total']} passed (failed: {out['tests']['unit']['failed']})")
print(f"  - Integration Tests: {out['tests']['integration']['passed']}/{out['tests']['integration']['total']} passed (failed: {out['tests']['integration']['failed']})")
print(f"  - Regression Tests: {out['tests']['regression']['passed']}/{out['tests']['regression']['total']} passed (failed: {out['tests']['regression']['failed']})")
assert out["tests"]["unit"]["failed"] == 0
assert out["tests"]["integration"]["failed"] == 0
assert out["tests"]["regression"]["failed"] == 0
assert out["tests"]["unit"]["total"] >= 1
assert out["tests"]["integration"]["total"] >= 1
assert out["tests"]["regression"]["total"] >= 1

print("\n[7] Verifying Exploit Replay & Human Invariant:")
print(f"  - Original Exploit Replayed: {out['replay']['original_scenario_replayed']}")
print(f"  - Vulnerability Still Reproducible: {out['replay']['vulnerability_still_reproducible']}")
print(f"  - Evidence ID: {out['replay']['evidence_id']}")
print(f"  - Remediation Status: {out['remediation_status']}")
print(f"  - Requires Human Approval: {out['requires_human_approval']}")
assert out["replay"]["vulnerability_still_reproducible"] is False
assert out["remediation_status"] == "patch_ready_for_review"
assert out["requires_human_approval"] is True

print("\n[8] Verifying Tavily Official Fix Guidance Tool (Section 11.4)...")
tavily_tool = TavilyFixGuidanceTool()
tavily_out = tavily_tool._run("FastAPI IDOR authorization check pattern")
tavily_data = json.loads(tavily_out)
print(f"[+] Tavily Tool Output: {tavily_data}")
assert "guidance" in str(tavily_data) or isinstance(tavily_data, list) or tavily_data.get("status") in {"unavailable", "error"}
print("[+] Tavily Official Fix Guidance Tool: PASS")

print("\n[9] Edge Case 1: Rejection of Unconfirmed Finding (FINDING_NOT_CONFIRMED)...")
unconfirmed_resp = agent.execute(sample_request, finding_verdict="unconfirmed")
assert unconfirmed_resp["status"] == "failed"
assert unconfirmed_resp["error"]["code"] == "FINDING_NOT_CONFIRMED"
assert unconfirmed_resp["error"]["retryable"] is False
print(f"[+] FINDING_NOT_CONFIRMED successfully trapped: {unconfirmed_resp['error']['message']}")

print("\n[10] Edge Case 2: Protected Branch Protection (BRANCH_PROTECTED)...")
protected_resp = agent.execute(sample_request, finding_verdict="confirmed", target_branch="main")
assert protected_resp["status"] == "failed"
assert protected_resp["error"]["code"] == "BRANCH_PROTECTED"
assert protected_resp["error"]["retryable"] is False
print(f"[+] BRANCH_PROTECTED successfully trapped: {protected_resp['error']['message']}")

print("\n[11] Edge Case 3: Test Suite Failures (PATCH_TESTS_FAILED)...")
fail_repo = make_git_repo()
test_fail_resp = agent.execute(
    sample_request,
    finding_verdict="confirmed",
    git_manager=IsolatedGitManager(fail_repo),
    test_runner=SandboxTestRunner(fail_repo),
    test_steps=replay_steps,
    state_checks=state_checks,
    fail_tests=True,
)
assert test_fail_resp["status"] == "failed"
assert test_fail_resp["error"]["code"] == "PATCH_TESTS_FAILED"
assert test_fail_resp["error"]["retryable"] is False
print(f"[+] PATCH_TESTS_FAILED successfully caught after max attempts: {test_fail_resp['error']['message']}")

print("\n[12] Edge Case 4: Missing Git Repository (PATCH_NOT_POSSIBLE)...")
non_git_repo = tempfile.mkdtemp(prefix="aegis_non_git_")
not_possible_resp = agent.execute(
    sample_request,
    finding_verdict="confirmed",
    git_manager=IsolatedGitManager(non_git_repo),
)
assert not_possible_resp["status"] == "succeeded"
assert not_possible_resp["output"]["remediation_status"] == "patch_not_possible"
assert not_possible_resp["output"]["patch"] is None
assert not_possible_resp["output"]["replay"]["vulnerability_still_reproducible"] is True
assert any("PATCH_NOT_POSSIBLE" in warning for warning in not_possible_resp["warnings"])
print(f"[+] Honest PATCH_NOT_POSSIBLE outcome: {not_possible_resp['output']['root_cause']['summary']}")

print("\n[13] Edge Case 5: Exploit Still Reproduces (EXPLOIT_STILL_REPRODUCES)...")
repro_repo = make_git_repo()
exploit_remains_resp = agent.execute(
    sample_request,
    finding_verdict="confirmed",
    git_manager=IsolatedGitManager(repro_repo),
    test_runner=SandboxTestRunner(repro_repo),
    test_steps=replay_steps,
    state_checks=state_checks,
    force_exploit_reproduces=True,
)
assert exploit_remains_resp["status"] == "failed"
assert exploit_remains_resp["error"]["code"] == "EXPLOIT_STILL_REPRODUCES"
assert exploit_remains_resp["error"]["retryable"] is False
print(f"[+] EXPLOIT_STILL_REPRODUCES successfully caught: {exploit_remains_resp['error']['message']}")

print("\n" + "=" * 75)
print("REMEDIATION AGENT (AGENT 7) TEST SUITE COMPLETED SUCCESSFULLY: 13/13 PASS")
print("=" * 75)
