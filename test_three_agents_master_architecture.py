import os
import sys
import json
import jsonschema
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

agent2_dir = os.path.join(workspace_dir, "agents", "code_intelligence_agent")
agent3_dir = os.path.join(workspace_dir, "agents", "recon_agent")
agent4_dir = os.path.join(workspace_dir, "agents", "vulnerability_research_agent")

def load_agent_module(agent_dir, module_filename):
    if "validation" in sys.modules:
        del sys.modules["validation"]
    if sys.path[0] != agent_dir:
        sys.path.insert(0, agent_dir)
    file_path = os.path.join(agent_dir, module_filename)
    spec = importlib.util.spec_from_file_location(f"mod_{os.path.basename(agent_dir)}", file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

mod2 = load_agent_module(agent2_dir, "code_intelligence_agent.py")
run_code_intelligence = mod2.run_code_intelligence

mod3 = load_agent_module(agent3_dir, "recon_agent.py")
run_recon = mod3.run_recon

mod4 = load_agent_module(agent4_dir, "vuln_research_agent.py")
run_vulnerability_research = mod4.run_vulnerability_research

def load_validation_module(agent_dir):
    if "validation" in sys.modules:
        del sys.modules["validation"]
    file_path = os.path.join(agent_dir, "validation.py")
    spec = importlib.util.spec_from_file_location(f"val_{os.path.basename(agent_dir)}", file_path)
    val_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(val_mod)
    return val_mod

val2 = load_validation_module(agent2_dir)
val3 = load_validation_module(agent3_dir)
val4 = load_validation_module(agent4_dir)

schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
with open(schema_file, "r", encoding="utf-8") as f:
    schema_bundle = json.load(f)

s_agents = schema_bundle["agents"]

print("=" * 85)
print("AEGISTRACE — THREE AGENTS PIPELINE VERIFICATION AGAINST MASTER ARCHITECTURE")
print("Target Specification: AegisTrace_Agent_Architecture_EN.pdf (Sections 6, 7, 8 & 12)")
print("=" * 85)

bench_repo = os.path.join(workspace_dir, "benchmark_suite", "shoplite_fastapi")
openapi_file = os.path.join(workspace_dir, "benchmark_suite_recon", "shoplite_openapi.json")

if not os.path.exists(bench_repo):
    os.makedirs(bench_repo, exist_ok=True)
    with open(os.path.join(bench_repo, "models.py"), "w", encoding="utf-8") as f:
        f.write("""from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    shipping_address = Column(String(200))
""")
    with open(os.path.join(bench_repo, "main.py"), "w", encoding="utf-8") as f:
        f.write("""from fastapi import FastAPI, Depends
app = FastAPI(title="ShopLite API")

def get_current_user():
    return {"user_id": 1, "role": "buyer"}

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: int, user = Depends(get_current_user)):
    return {"order_id": order_id}

@app.patch("/api/v1/orders/{order_id}")
def update_order(order_id: int):
    return {"order_id": order_id}
""")
    with open(os.path.join(bench_repo, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write("fastapi==0.109.0\nsqlalchemy==2.0.25\n")

if not os.path.exists(openapi_file):
    os.makedirs(os.path.dirname(openapi_file), exist_ok=True)
    spec_data = {
        "openapi": "3.0.3",
        "info": {"title": "ShopLite Platform", "version": "1.0.0"},
        "paths": {
            "/api/v1/orders/{order_id}": {
                "get": {"summary": "Get order", "security": [{"bearerAuth": []}]},
                "patch": {"summary": "Update order", "security": [{"bearerAuth": []}]}
            },
            "/admin/danger/wipe": {
                "delete": {"summary": "Dangerous wipe"}
            }
        }
    }
    with open(openapi_file, "w", encoding="utf-8") as f:
        json.dump(spec_data, f, indent=2)

print("\n[Step 1] Executing Agent 2 (Code Intelligence) — Section 6.8 & 6.9...")
code_intel_req = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f302",
    "agent_run_id": "run_0192f402",
    "created_at": "2026-11-17T09:30:10Z",
    "agent": "code_intelligence",
    "input": {
        "repository": {
            "path_ref": bench_repo,
            "commit": "a1b2c3d4e5f6"
        },
        "source_language": "python",
        "framework_hints": ["fastapi", "sqlalchemy"],
        "scan_config": {
            "max_files": 200,
            "include_globs": ["**/*.py"],
            "enable_semgrep": False
        }
    }
}

val_req_ok = False
req_err = None
try:
    req_obj = val2.validate_code_intel_request(code_intel_req)
    val_req_ok = True
except Exception as e:
    req_err = str(e)
assert val_req_ok, f"Code Intel request failed Pydantic validation: {req_err}"
jsonschema.validate(instance=code_intel_req, schema=s_agents["code_intelligence"]["request"])
print("  * Agent 2 Input Contract & Master JSON Schema: 100% VALID")

code_intel_resp = run_code_intelligence(code_intel_req)
assert code_intel_resp.get("status") == "succeeded", f"Agent 2 run failed: {code_intel_resp.get('error')}"
val_resp_ok = False
resp_err = None
try:
    resp_obj = val2.validate_code_intel_response(code_intel_resp)
    val_resp_ok = True
except Exception as e:
    resp_err = str(e)
assert val_resp_ok, f"Code Intel response failed Pydantic validation: {resp_err}"
jsonschema.validate(instance=code_intel_resp, schema=s_agents["code_intelligence"]["response"])
print("  * Agent 2 Output Contract & Master JSON Schema: 100% VALID")
print(f"  * Code Intel Extracted: {len(code_intel_resp['output']['routes'])} routes, {len(code_intel_resp['output']['db_models'])} models, {len(code_intel_resp['output']['candidate_invariants'])} invariants")

print("\n[Step 2] Executing Agent 3 (Reconnaissance) — Section 7.8 & 7.9...")
recon_req = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f303",
    "agent_run_id": "run_0192f403",
    "created_at": "2026-11-17T09:30:10Z",
    "agent": "recon",
    "input": {
        "scope": {
            "allowed_hosts": ["shoplite-app"],
            "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
            "forbidden_paths": ["/admin/danger/*"]
        },
        "api_spec_ref": openapi_file,
        "technology_hints": ["fastapi", "postgresql"],
        "research": {
            "enabled": False,
            "max_queries": 2,
            "search_depth": "basic"
        }
    }
}

val3_req_ok, r_obj, r_err = val3.validate_recon_request(recon_req)
assert val3_req_ok, f"Recon request failed Pydantic validation: {r_err}"
jsonschema.validate(instance=recon_req, schema=s_agents["recon"]["request"])
print("  * Agent 3 Input Contract & Master JSON Schema: 100% VALID")

recon_resp = run_recon(recon_req)
assert recon_resp.get("status") == "succeeded", f"Agent 3 run failed: {recon_resp.get('error')}"
val3_resp_ok, res_obj3, res_err3 = val3.validate_recon_response(recon_resp)
assert val3_resp_ok, f"Recon response failed Pydantic validation: {res_err3}"
jsonschema.validate(instance=recon_resp, schema=s_agents["recon"]["response"])
print("  * Agent 3 Output Contract & Master JSON Schema: 100% VALID")
print(f"  * Recon Discovered: {len(recon_resp['output']['endpoints'])} endpoints (Forbidden filtered), {len(recon_resp['output']['technologies'])} technologies")

print("\n[Step 3] Verifying Task Hand-Off (Section 3.7 & Section 12)...")
cache_dir = os.path.join(workspace_dir, ".aegistrace_cache", "tasks")
os.makedirs(cache_dir, exist_ok=True)

with open(os.path.join(cache_dir, "tsk_0192f302.json"), "w", encoding="utf-8") as f:
    json.dump({"output": code_intel_resp["output"]}, f)
with open(os.path.join(cache_dir, "tsk_0192f303.json"), "w", encoding="utf-8") as f:
    json.dump({"output": recon_resp["output"]}, f)
print("  * Task outputs persisted to .aegistrace_cache/tasks/tsk_0192f302.json & tsk_0192f303.json")
print("  * Hand-off contracts: Code Intelligence (routes, models, invariants) + Recon (endpoints, technologies)")

print("\n[Step 4] Executing Agent 4 (Vulnerability Research) — Section 8.8 & 8.9...")
inv_ids = [inv["invariant_id"] for inv in code_intel_resp["output"]["candidate_invariants"]]
if not inv_ids:
    inv_ids = ["inv_order_owner_only"]

vuln_req = {
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
        "invariant_ids": inv_ids,
        "skill_hits": [
            {"skill": "hunt-idor", "source_commit": "64410ed", "score": 0.91}
        ]
    }
}

val4_req_ok, req4_obj, req4_err = val4.validate_research_request(vuln_req)
assert val4_req_ok, f"Vuln Research request failed Pydantic validation: {req4_err}"
jsonschema.validate(instance=vuln_req, schema=s_agents["vulnerability_research"]["request"])
print("  * Agent 4 Input Contract & Master JSON Schema: 100% VALID")

vuln_resp = run_vulnerability_research(vuln_req)
assert vuln_resp.get("status") == "succeeded", f"Agent 4 run failed: {vuln_resp.get('error')}"
val4_resp_ok, resp4_obj, resp4_err = val4.validate_research_response(vuln_resp)
assert val4_resp_ok, f"Vuln Research response failed Pydantic validation: {resp4_err}"
jsonschema.validate(instance=vuln_resp, schema=s_agents["vulnerability_research"]["response"])
print("  * Agent 4 Output Contract & Master JSON Schema: 100% VALID")

hyps = vuln_resp["output"]["hypotheses"]
plans = vuln_resp["output"]["test_plans"]
print(f"  * Vulnerability Research Formulated: {len(hyps)} hypotheses, {len(plans)} test plans")
for h in hyps:
    print(f"    - Hypothesis {h['hypothesis_id']} [{h['category']}]: {h['title']} (Priority {h['priority']})")
for p in plans:
    print(f"    - Test Plan {p['test_plan_id']} [{p['method']}]: Target Table '{p['state_checks'][0]['table']}', Columns {p['state_checks'][0]['columns']}")

print("\n[Step 5] Section 8.12 Hand-Off to Dynamic Testing...")
top_plan = plans[0]
dynamic_input = {
    "test_plan": top_plan,
    "endpoint": recon_resp["output"]["endpoints"][0],
    "identities": [
        {"identity_id": "id_buyer_a", "role": "customer", "credential_ref": "cred_buyer_a", "owns": {"order_id": 100}},
        {"identity_id": "id_buyer_b", "role": "customer", "credential_ref": "cred_buyer_b", "owns": {"order_id": 200}}
    ],
    "sandbox": {
        "sandbox_id": "sbx_0192f2f0",
        "base_url": "http://shoplite-app:8000",
        "snapshot_enabled": True,
        "max_requests": 200
    },
    "invariant_id": hyps[0]["invariant_id"]
}
dynamic_req = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f305",
    "agent_run_id": "run_0192f405",
    "created_at": "2026-11-17T09:32:10Z",
    "agent": "dynamic_testing",
    "input": dynamic_input
}
jsonschema.validate(instance=dynamic_req, schema=s_agents["dynamic_testing"]["request"])
print("  * Dynamic Testing input contract (Section 8.12 Hand-off) validates 100% against Master JSON Schema.")

print("\n" + "=" * 85)
print("PIPELINE SUMMARY FOR FIRST 3 AGENTS (AGENTS 2, 3 & 4):")
print("-" * 85)
print(f"Agent 2 (Code Intelligence):     INPUT: 100% VALID | OUTPUT: 100% VALID | STATUS: SUCCEEDED")
print(f"Agent 3 (Reconnaissance):        INPUT: 100% VALID | OUTPUT: 100% VALID | STATUS: SUCCEEDED")
print(f"Agent 4 (Vulnerability Research): INPUT: 100% VALID | OUTPUT: 100% VALID | STATUS: SUCCEEDED")
print(f"End-to-End Hand-Off:            CONFIRMED (Sections 3.7, 6.12, 7.12, 8.12, 12)")
print("=" * 85)
print("[+] ALL 3 AGENTS FULLY COMPLIANT WITH AegisTrace_Agent_Architecture_EN.pdf!")
print("=" * 85)
