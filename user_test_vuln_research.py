import os
import sys
import json
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

agent_file_path = os.path.join(workspace_dir, "agents", "vulnberability agent", "vuln_research_agent.py")
spec = importlib.util.spec_from_file_location("vuln_research_agent", agent_file_path)
vr_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr_mod)
run_vulnerability_research = vr_mod.run_vulnerability_research

print("=" * 70)
print("AEGISTRACE — VULNERABILITY RESEARCH AGENT (AGENT 4) USER TEST SUITE")
print("=" * 70)

mock_code_intel = {
    "repository_structure": {
        "files_analyzed": 10,
        "frameworks": ["fastapi", "sqlalchemy"],
        "entry_points": ["main.py"]
    },
    "routes": [
        {
            "route_id": "rte_patch_order",
            "method": "PATCH",
            "path": "/api/v1/orders/{order_id}",
            "handler": "update_order",
            "file": "routes/orders.py",
            "line": 58,
            "auth_required": True,
            "authz_checks": []
        },
        {
            "route_id": "rte_get_order",
            "method": "GET",
            "path": "/api/v1/orders/{order_id}",
            "handler": "get_order",
            "file": "routes/orders.py",
            "line": 31,
            "auth_required": True,
            "authz_checks": ["order.user_id == current_user.id"]
        }
    ],
    "auth_mechanisms": [
        {
            "name": "get_current_user",
            "kind": "authentication",
            "location": "deps.py:14",
            "description": "Decodes bearer JWT and loads the user"
        }
    ],
    "db_models": [
        {
            "name": "Order",
            "table": "orders",
            "owner_field": "user_id",
            "file": "models.py"
        }
    ],
    "code_graph_ref": "graph://scn_0192f1c9/code",
    "candidate_invariants": [
        {
            "invariant_id": "inv_order_owner_only",
            "statement": "An order may be read or modified only by the user referenced in orders.user_id",
            "kind": "ownership",
            "applies_to_route_ids": ["rte_patch_order", "rte_get_order"],
            "source": "code",
            "confidence": 0.95
        }
    ]
}

mock_recon = {
    "endpoints": [
        {
            "endpoint_id": "ep_patch_order",
            "method": "PATCH",
            "path": "/api/v1/orders/{order_id}",
            "path_params": ["order_id"],
            "auth_required": True,
            "source": "openapi"
        },
        {
            "endpoint_id": "ep_get_order",
            "method": "GET",
            "path": "/api/v1/orders/{order_id}",
            "path_params": ["order_id"],
            "auth_required": True,
            "source": "openapi"
        }
    ],
    "technologies": [
        {
            "name": "FastAPI",
            "version": "1.0.0",
            "confidence": 0.95,
            "evidence": "OpenAPI info title/description mentions FastAPI"
        },
        {
            "name": "PostgreSQL",
            "version": None,
            "confidence": 0.85,
            "evidence": "Technology hint specified in project configuration"
        }
    ],
    "attack_surface_ref": "graph://scn_0192f1c9de01/attack_surface",
    "intel_refs": [
        {
            "ref_id": "ref_fda8d6bf",
            "title": "API1:2023 Broken Object Level Authorization",
            "url": "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization",
            "retrieved_at": "2026-11-18T00:29:17Z",
            "source_type": "owasp",
            "relevance": 0.9,
            "trusted": False
        }
    ]
}

request_payload = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230ab01",
    "project_id": "prj_0192f1a0bc01",
    "engagement_id": "eng_0192f1b4cd01",
    "scan_id": "scn_0192f1c9de01",
    "task_id": "tsk_0192f304ef01",
    "agent_run_id": "run_0192f404fa01",
    "created_at": "2026-11-17T09:31:10Z",
    "agent": "vulnerability_research",
    "input": {
        "code_intel_ref": "out://tsk_0192f302",
        "recon_ref": "out://tsk_0192f303",
        "invariant_ids": [
            "inv_order_owner_only"
        ],
        "skill_hits": [
            {
                "skill": "hunt-idor",
                "source_commit": "64410ed",
                "score": 0.91
            }
        ]
    }
}

cache_dir = os.path.join(workspace_dir, ".aegistrace_cache", "tasks")
os.makedirs(cache_dir, exist_ok=True)
with open(os.path.join(cache_dir, "tsk_0192f302.json"), "w", encoding="utf-8") as f:
    json.dump({"output": mock_code_intel}, f)
with open(os.path.join(cache_dir, "tsk_0192f303.json"), "w", encoding="utf-8") as f:
    json.dump({"output": mock_recon}, f)

print("\n[1] Executing Vulnerability Research Agent Workflow (with automatic task reference resolution)...")
response = run_vulnerability_research(
    request_data=request_payload
)

print(f"[+] Response Status: {response.get('status')}")
print(f"[+] Execution Metrics: {response.get('metrics')}")

output = response.get("output", {})
hypotheses = output.get("hypotheses", [])
test_plans = output.get("test_plans", [])

print(f"\n[2] Hypotheses Formulated ({len(hypotheses)}):")
for hyp in hypotheses:
    print(f"  * ID: {hyp['hypothesis_id']} | Category: {hyp['category']} | Priority: {hyp['priority']}")
    print(f"    Title: {hyp['title']}")
    print(f"    Target Endpoint: {hyp['endpoint_id']} | Invariant: {hyp['invariant_id']}")
    print(f"    Rationale: {hyp['rationale']}")
    print(f"    Skills Applied: {hyp['skill_refs']}\n")

assert len(hypotheses) > 0, "Error: No hypotheses formulated"
top_hyp = hypotheses[0]
assert top_hyp["category"] == "idor", f"Expected 'idor' category, got {top_hyp['category']}"
assert "hunt-idor" in top_hyp["skill_refs"], "Expected hunt-idor in skill_refs"
print("[+] Hypothesis Extraction & Skill Routing: PASS")

print(f"\n[3] Structured Test Plans Generated ({len(test_plans)}):")
for plan in test_plans:
    print(f"  * Plan ID: {plan['test_plan_id']} | Method: {plan['method']} | For Hypothesis: {plan['hypothesis_id']}")
    print(f"    Identities: {plan['identities']}")
    print(f"    Expected Secure Behavior: {plan['expected_secure_behavior']}")
    print("    Execution Steps:")
    for step in plan["steps"]:
        print(f"      - {step}")
    print("    State Checks:")
    for sc in plan["state_checks"]:
        print(f"      - Table: {sc['table']}, Key: {sc['key']}, Columns to Diff: {sc['columns']}\n")

assert len(test_plans) > 0, "Error: No test plans generated"
top_plan = test_plans[0]
assert top_plan["method"] == "paired_identity", f"Expected paired_identity method, got {top_plan['method']}"
assert len(top_plan["identities"]) >= 2, "paired_identity must have at least 2 identities"
assert len(top_plan["state_checks"]) > 0, "Test plan must include state_checks"
assert top_plan["state_checks"][0]["table"] == "orders", "State check table should be 'orders'"
print("[+] Paired-Identity Test Plan & State-Diff Checks: PASS")

schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
if os.path.exists(schema_file):
    import jsonschema
    with open(schema_file, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    vr_schema = bundle["agents"]["vulnerability_research"]["response"]
    jsonschema.validate(instance=response, schema=vr_schema)
    print("\n[4] Master Architecture Schema Verification: PASS (100% compliant with AegisTrace_Agent_JSON_Schemas.json)")

print("\n" + "=" * 70)
print("[+] ALL VULNERABILITY RESEARCH AGENT CAPABILITIES AND INVARIANTS PASSED!")
print("=" * 70)
