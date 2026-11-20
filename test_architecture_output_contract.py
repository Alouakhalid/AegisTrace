import os
import sys
import re
import json
import jsonschema

workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)
agent_dir = os.path.join(workspace_dir, "agents", "vulnerability_research_agent")
sys.path.insert(0, agent_dir)

from validation import validate_research_response, ResearchResponse

print("=" * 80)
print("AEGISTRACE — ARCHITECTURAL CONTRACT & SCHEMA CONFORMANCE VERIFICATION")
print("Target Specification: AegisTrace_Agent_Architecture_EN.pdf (Section 8.9 & 8.10)")
print("=" * 80)

pdf_page_45_example = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f304",
    "agent_run_id": "run_0192f404",
    "created_at": "2026-11-17T09:31:30Z",
    "agent": "vulnerability_research",
    "status": "succeeded",
    "warnings": [],
    "error": None,
    "metrics": {
        "duration_ms": 20100,
        "llm_calls": 2,
        "input_tokens": 9100,
        "output_tokens": 1800
    },
    "output": {
        "hypotheses": [
            {
                "hypothesis_id": "hyp_idor_patch_order",
                "category": "idor",
                "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
                "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
                "endpoint_id": "ep_patch_order",
                "invariant_id": "inv_order_owner_only",
                "priority": 1,
                "skill_refs": ["hunt-idor"]
            }
        ],
        "test_plans": [
            {
                "test_plan_id": "tpl_idor_patch_order",
                "hypothesis_id": "hyp_idor_patch_order",
                "method": "paired_identity",
                "steps": [
                    "Snapshot orders.id=100",
                    "As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address",
                    "Snapshot orders.id=100",
                    "As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address",
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
            }
        ]
    }
}

print("\n[Test 1] Validating PDF Page 45 Canonical Response against Pydantic V2 Layer...")
valid_pdf, res_pdf, err_pdf = validate_research_response(pdf_page_45_example)
assert valid_pdf, f"PDF Canonical Example failed Pydantic validation: {err_pdf}"
print("[+] Test 1 Passed: PDF Page 45 canonical example conforms 100% with Pydantic contract.")

print("\n[Test 2] Validating PDF Page 45 Canonical Response against Master JSON Schema...")
schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
with open(schema_file, "r", encoding="utf-8") as f:
    bundle = json.load(f)
vr_schema = bundle["agents"]["vulnerability_research"]["response"]
jsonschema.validate(instance=pdf_page_45_example, schema=vr_schema)
print("[+] Test 2 Passed: PDF Page 45 canonical example validates 100% against AegisTrace_Agent_JSON_Schemas.json.")

print("\n[Test 3] Executing Live Agent Run on ShopLite Baseline...")
from vuln_research_agent import run_vulnerability_research

cache_dir = os.path.join(workspace_dir, ".aegistrace_cache", "tasks")
os.makedirs(cache_dir, exist_ok=True)

live_req = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f304",
    "agent_run_id": "run_0192f404",
    "created_at": "2026-11-17T09:31:10Z",
    "agent": "vulnerability_research",
    "input": {
        "code_intel_ref": "out://tsk_0192f302",
        "recon_ref": "out://tsk_0192f303",
        "invariant_ids": ["inv_order_owner_only"],
        "skill_hits": [
            {"skill": "hunt-idor", "source_commit": "64410ed", "score": 0.91}
        ]
    }
}

agent_resp = run_vulnerability_research(live_req)
assert agent_resp["status"] == "succeeded", f"Agent run failed: {agent_resp.get('error')}"
print("[+] Test 3 Passed: Live Agent successfully generated response.")

print("\n[Test 4] Field-by-Field Structural Parity with Section 8.9 & 8.10...")
envelope_fields = [
    "schema_version", "correlation_id", "project_id", "engagement_id",
    "scan_id", "task_id", "agent_run_id", "created_at", "agent",
    "status", "warnings", "error", "metrics", "output"
]
for f_name in envelope_fields:
    assert f_name in agent_resp, f"Missing envelope field: {f_name}"
    print(f"  * Envelope Field '{f_name}': OK")

output_data = agent_resp["output"]
assert "hypotheses" in output_data and len(output_data["hypotheses"]) > 0, "No hypotheses in output"
assert "test_plans" in output_data and len(output_data["test_plans"]) > 0, "No test_plans in output"

top_h = output_data["hypotheses"][0]
for h_key in ["hypothesis_id", "category", "title", "rationale", "endpoint_id", "invariant_id", "priority", "skill_refs"]:
    assert h_key in top_h, f"Missing hypothesis field: {h_key}"
assert re.match(r"^hyp_[a-z0-9_]+$", top_h["hypothesis_id"]), "Invalid hypothesis_id pattern"
assert top_h["category"] in ["broken_access_control", "idor", "authn_authz_flaw", "business_logic"], "Invalid category enum"
assert 1 <= top_h["priority"] <= 5, "Priority out of range"
print("[+] Hypotheses contract verified: All 8 required fields & regex patterns match.")

top_p = output_data["test_plans"][0]
for p_key in ["test_plan_id", "hypothesis_id", "method", "steps", "identities", "expected_secure_behavior", "state_checks"]:
    assert p_key in top_p, f"Missing test plan field: {p_key}"
assert re.match(r"^tpl_[a-z0-9_]+$", top_p["test_plan_id"]), "Invalid test_plan_id pattern"
assert top_p["method"] in ["paired_identity", "single_identity", "workflow_sequence"], "Invalid method enum"
assert len(top_p["identities"]) >= 2, "paired_identity must have >= 2 identities"
assert len(top_p["state_checks"]) > 0, "state_checks cannot be empty"

sc = top_p["state_checks"][0]
assert "table" in sc and sc["table"] == "orders", "Invalid state check table"
assert "key" in sc and isinstance(sc["key"], dict) and "id" in sc["key"], "Invalid state check key"
assert "columns" in sc and "shipping_address" in sc["columns"], "Invalid state check columns"
print("[+] Test Plans contract verified: Method, identities, steps and State-Diff match.")

print("\n[Test 5] Validating Live Agent Output against AegisTrace_Agent_JSON_Schemas.json...")
jsonschema.validate(instance=agent_resp, schema=vr_schema)
print("[+] Test 5 Passed: Live agent response is 100% compliant with Master JSON Schemas.")

print("\n" + "=" * 80)
print("[+] ALL ARCHITECTURAL CONTRACT AND OUTPUT PARITY CHECKS PASSED WITH 100% COMPLIANCE!")
print("=" * 80)
