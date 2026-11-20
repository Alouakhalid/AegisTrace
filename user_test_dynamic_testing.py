import os
import sys
import json
import jsonschema
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

agent_dir = os.path.join(workspace_dir, "agents", "Dynamic Testing Agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

agent_file_path = os.path.join(agent_dir, "dynamic_testing_agent.py")
spec = importlib.util.spec_from_file_location("dynamic_testing_agent", agent_file_path)
dt_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt_mod)
run_dynamic_testing = dt_mod.run_dynamic_testing

val_file_path = os.path.join(agent_dir, "validation.py")
val_spec = importlib.util.spec_from_file_location("dt_validation", val_file_path)
val_mod = importlib.util.module_from_spec(val_spec)
val_spec.loader.exec_module(val_mod)
validate_dynamic_request = val_mod.validate_dynamic_request
validate_dynamic_response = val_mod.validate_dynamic_response

from tools.dynamic_testing_tools import PlaywrightBrowserTool

schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
with open(schema_file, "r", encoding="utf-8") as f:
    schema_bundle = json.load(f)

dt_schemas = schema_bundle["agents"]["dynamic_testing"]

print("=" * 75)
print("AEGISTRACE — DYNAMIC TESTING AGENT (AGENT 5) USER TEST SUITE")
print("Target: AegisTrace_Agent_Architecture_EN.pdf (Sections 9.8 - 9.12)")
print("=" * 75)

dynamic_req = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f305",
    "agent_run_id": "run_0192f405",
    "created_at": "2026-11-17T09:31:35Z",
    "agent": "dynamic_testing",
    "input": {
        "test_plan": {
            "test_plan_id": "tpl_idor_patch_order",
            "hypothesis_id": "hyp_idor_patch_order",
            "method": "paired_identity",
            "steps": [
                "Snapshot orders.id=100",
                "As buyer_a (owner) PATCH /api/v1/orders/100 with baseline address",
                "Snapshot orders.id=100",
                "As buyer_b (non-owner) PATCH /api/v1/orders/100 with distinct address",
                "Snapshot orders.id=100 and diff"
            ],
            "identities": [
                "id_buyer_a",
                "id_buyer_b"
            ],
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
            "endpoint_id": "ep_patch_order",
            "method": "PATCH",
            "path": "/api/v1/orders/{order_id}",
            "path_params": ["order_id"],
            "auth_required": True,
            "source": "openapi"
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
            "base_url": "http://shoplite-app:8000",
            "snapshot_enabled": True,
            "max_requests": 200
        },
        "invariant_id": "inv_order_owner_only"
    }
}

print("\n[1] Validating Input Request Contract against Pydantic & Master JSON Schema...")
is_req_valid, req_obj, req_err = validate_dynamic_request(dynamic_req)
assert is_req_valid, f"Dynamic request failed Pydantic validation: {req_err}"
jsonschema.validate(instance=dynamic_req, schema=dt_schemas["request"])
print("[+] DynamicRequest Pydantic V2 Contract: PASS")
print("[+] DynamicRequest Master JSON Schema: PASS")

print("\n[2] Executing Dynamic Testing Agent Workflow...")
resp = run_dynamic_testing(dynamic_req)
assert resp.get("status") == "succeeded", f"Agent execution failed: {resp.get('error')}"
print(f"[+] Execution Status: {resp.get('status')}")
print(f"[+] Metrics: {resp.get('metrics')}")

print("\n[3] Validating Output Response Contract against Pydantic & Master JSON Schema...")
is_resp_valid, resp_obj, resp_err = validate_dynamic_response(resp)
assert is_resp_valid, f"Dynamic response failed Pydantic validation: {resp_err}"
jsonschema.validate(instance=resp, schema=dt_schemas["response"])
print("[+] DynamicResponse Pydantic V2 Contract: PASS")
print("[+] DynamicResponse Master JSON Schema: PASS")

out = resp.get("output", {})
cases = out.get("executed_cases", [])
diffs = out.get("state_diffs", [])
comparison = out.get("identity_comparison", "")

print(f"\n[4] Executed Test Cases ({len(cases)}):")
for c in cases:
    ex = c["exchange"]
    print(f"  - Case {c['case_id']} [{c['identity_id']}]: {ex['method']} {ex['url']} -> HTTP {ex['status_code']} | Evidence: {ex['evidence_id']}")
    assert ex["evidence_id"].startswith("evd_"), "evidence_id format invalid"

print(f"\n[5] Cryptographic State Differences ({len(diffs)}):")
for d in diffs:
    print(f"  - Table: '{d['table']}' | Key: {d['key']} | Column: '{d['column']}'")
    print(f"    Before ({d['snapshot_before_id']}): {d['before']}")
    print(f"    After  ({d['snapshot_after_id']}): {d['after']}")
    print(f"    Evidence ID: {d['evidence_id']}")
    assert d["before"] != d["after"], "State diff before and after must differ"

print(f"\n[6] Identity Comparison Narrative:\n  '{comparison}'")
assert len(diffs) > 0, "StateDiff engine must discover unauthorized state mutation"
assert out.get("execution_status") == "completed", "Execution status must be completed"

print("\n[7] Testing Playwright Browser Automation Tool...")
p_tool = PlaywrightBrowserTool()
p_res = p_tool.execute_browser_flow(
    target_url="http://shoplite-app:8000/orders/100",
    identity_id="id_buyer_b",
    flow_steps=["Navigate to orders/100", "Attempt unauthorized DOM update"]
)
print(f"[+] Playwright Tool Output: {p_res['method']} {p_res['url']} -> HTTP {p_res['status_code']} | Evidence: {p_res['evidence_id']}")
print(f"[+] Playwright Available in Environment: {p_res['playwright_available']}")
assert p_res["evidence_id"].startswith("evd_"), "Playwright evidence_id invalid"

print("\n[8] Testing ScopeGate Enforcement (Forbidden Path Protection)...")
scope_violation_req = dict(dynamic_req)
scope_violation_req["input"] = dict(dynamic_req["input"])
scope_violation_req["input"]["endpoint"] = {
    "endpoint_id": "ep_danger_wipe",
    "method": "DELETE",
    "path": "/admin/danger/wipe",
    "path_params": [],
    "auth_required": True,
    "source": "openapi"
}
scope_resp = run_dynamic_testing(scope_violation_req)
print(f"[+] ScopeGate Response Status: {scope_resp.get('status')} | Error: {scope_resp.get('error')}")
assert scope_resp.get("status") == "failed", "Scope violation must fail"
assert scope_resp.get("error", {}).get("code") == "SCOPE_VIOLATION", "Error code must be SCOPE_VIOLATION"

print("\n[9] Testing Request Budget Enforcement (REQUEST_BUDGET_EXCEEDED)...")
budget_req = dict(dynamic_req)
budget_req["input"] = dict(dynamic_req["input"])
budget_req["input"]["sandbox"] = dict(dynamic_req["input"]["sandbox"])
budget_req["input"]["sandbox"]["max_requests"] = 1
budget_resp = run_dynamic_testing(budget_req)
print(f"[+] Budget Response Status: {budget_resp.get('status')} | Error: {budget_resp.get('error')}")
assert budget_resp.get("status") == "failed", "Budget exceeded must fail"
assert budget_resp.get("error", {}).get("code") == "REQUEST_BUDGET_EXCEEDED", "Error code must be REQUEST_BUDGET_EXCEEDED"

print("\n[10] Testing Snapshot Failure Handling (SNAPSHOT_FAILED)...")
snap_fail_req = dict(dynamic_req)
snap_fail_req["input"] = dict(dynamic_req["input"])
snap_fail_req["input"]["test_plan"] = dict(dynamic_req["input"]["test_plan"])
snap_fail_req["input"]["test_plan"]["state_checks"] = [
    {"table": "nonexistent_table_99", "key": {"id": 100}, "columns": ["dummy_col"]}
]
snap_resp = run_dynamic_testing(snap_fail_req)
print(f"[+] Snapshot Failure Response Status: {snap_resp.get('status')} | Error: {snap_resp.get('error')}")
assert snap_resp.get("status") == "failed", "Snapshot failure must fail"
assert snap_resp.get("error", {}).get("code") == "SNAPSHOT_FAILED", "Error code must be SNAPSHOT_FAILED"

print("\n" + "=" * 75)
print("[+] ALL DYNAMIC TESTING AGENT (AGENT 5) USER TESTS PASSED WITH 100% SUCCESS!")
print("=" * 75)
