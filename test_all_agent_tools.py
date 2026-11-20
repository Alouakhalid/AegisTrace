import os
import sys
import json
import tempfile
import shutil

workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

from tools.code_intel_tools import (
    find_python_files,
    parse_dependencies,
    run_security_rules_scan,
    analyze_repository,
    construct_code_graph,
    read_skill_content,
    ParsePythonRepositoryTool,
    BuildCodeGraphTool,
    QuerySecuritySkillTool
)

from tools.recon_tools import (
    ScopeGate,
    ScopeViolationException,
    sanitize_endpoint_id,
    parse_openapi_spec,
    fingerprint_target,
    build_attack_surface_graph,
    OpenApiParserCrewTool,
    TechnologyFingerprintCrewTool,
    TavilyIntelCrewTool
)

from tools.vuln_research_tools import (
    load_skill_metadata,
    route_skills_for_category,
    resolve_task_output,
    query_code_graph_context,
    normalize_path_for_join,
    correlate_code_and_recon,
    infer_table_key_and_column,
    discover_hypotheses_and_plans,
    SkillRouterCrewTool,
    CodeGraphQueryCrewTool
)

agent_code_dir = os.path.join(workspace_dir, "agents", "code_intelligence_agent")
sys.path.insert(0, agent_code_dir)
from code_intelligence_agent import CodeIntelligenceAgent

print("=" * 80)
print("AEGISTRACE — ALL AGENT TOOLS FUNCTIONAL VERIFICATION SUITE")
print("=" * 80)

tool_results = []

def record_tool(agent_name, tool_name, status, details):
    tool_results.append({
        "agent": agent_name,
        "tool": tool_name,
        "status": status,
        "details": details
    })
    print(f"[{status}] {agent_name} :: {tool_name} -> {details}")

temp_repo = tempfile.mkdtemp(prefix="aegistrace_tool_test_")

models_code = """from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    shipping_address = Column(String(200))
"""

routes_code = """from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="ShopLite API")

def get_current_user():
    return {"user_id": 1, "role": "buyer"}

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: int, user = Depends(get_current_user)):
    return {"order_id": order_id}

@app.patch("/api/v1/orders/{order_id}")
def update_order(order_id: int):
    return {"order_id": order_id}
"""

reqs_code = "fastapi==0.109.0\nsqlalchemy==2.0.25\n"

with open(os.path.join(temp_repo, "models.py"), "w", encoding="utf-8") as f:
    f.write(models_code)
with open(os.path.join(temp_repo, "main.py"), "w", encoding="utf-8") as f:
    f.write(routes_code)
with open(os.path.join(temp_repo, "requirements.txt"), "w", encoding="utf-8") as f:
    f.write(reqs_code)

try:
    print("\n--- 1. Testing Code Intelligence Tools (Agent 2) ---")
    
    files = find_python_files(temp_repo)
    assert len(files) >= 2
    record_tool("Code Intelligence", "find_python_files", "PASS", f"Found {len(files)} python source files")

    deps = parse_dependencies(temp_repo)
    assert "fastapi" in deps and "sqlalchemy" in deps
    record_tool("Code Intelligence", "parse_dependencies", "PASS", f"Extracted dependencies: {list(deps.keys())}")

    findings = run_security_rules_scan(temp_repo, files, enable_semgrep=False)
    record_tool("Code Intelligence", "run_security_rules_scan", "PASS", f"Executed AST security pattern scans (findings={len(findings)})")

    analysis = analyze_repository(temp_repo)
    assert analysis["files_analyzed"] >= 2
    assert "fastapi" in analysis["frameworks"]
    assert len(analysis["routes"]) == 2
    assert len(analysis["models"]) == 1
    assert analysis["models"][0]["owner_field"] == "user_id"
    record_tool("Code Intelligence", "analyze_repository", "PASS", f"Analyzed repository: {len(analysis['routes'])} routes, {len(analysis['models'])} models")

    agent_inst = CodeIntelligenceAgent()
    invariants = agent_inst.derive_invariants_heuristic(analysis["routes"], analysis["models"])
    assert len(invariants) >= 1
    record_tool("Code Intelligence", "derive_invariants_heuristic", "PASS", f"Inferred {len(invariants)} security invariant(s)")

    graph_ref = construct_code_graph(analysis, scan_id="scn_tool_test")
    assert graph_ref.startswith("graph://")
    record_tool("Code Intelligence", "construct_code_graph", "PASS", f"Constructed NetworkX code graph: {graph_ref}")

    crew_parser = ParsePythonRepositoryTool()
    res_parse = json.loads(crew_parser._run(temp_repo))
    assert "routes" in res_parse and len(res_parse["routes"]) == 2
    record_tool("Code Intelligence", "ParsePythonRepositoryTool (CrewAI)", "PASS", "CrewAI tool parsed repository and returned JSON")

    crew_graph = BuildCodeGraphTool()
    res_g = crew_graph._run(json.dumps(analysis), scan_id="scn_crew_test")
    assert res_g.startswith("graph://")
    record_tool("Code Intelligence", "BuildCodeGraphTool (CrewAI)", "PASS", f"CrewAI tool constructed graph URI: {res_g}")

    crew_skill = QuerySecuritySkillTool()
    res_skill = crew_skill._run("hunt-idor")
    assert len(res_skill) > 50
    record_tool("Code Intelligence", "QuerySecuritySkillTool (CrewAI)", "PASS", "CrewAI tool queried local BugHunter skills library")

    print("\n--- 2. Testing Reconnaissance Tools (Agent 3) ---")

    gate = ScopeGate(
        allowed_hosts=["shoplite-app", "api.example.com"],
        allowed_methods=["GET", "POST", "PATCH"],
        forbidden_paths=["/admin/danger/*", "/private/keys"]
    )
    assert gate.is_host_allowed("shoplite-app:8000")
    assert not gate.is_host_allowed("evil-attacker.com")
    assert gate.is_method_allowed("GET")
    assert not gate.is_method_allowed("DELETE")
    is_f, pattern = gate.is_path_forbidden("/admin/danger/wipe")
    assert is_f and pattern == "/admin/danger/*"
    is_f2, _ = gate.is_path_forbidden("/api/v1/orders/100")
    assert not is_f2
    record_tool("Recon", "ScopeGate (Host, Method & Path Rules)", "PASS", "Strict scope filtering verified")

    scope_violation_raised = False
    try:
        gate.validate_request("unauthorized-host.org", "GET", "/api")
    except ScopeViolationException:
        scope_violation_raised = True
    assert scope_violation_raised
    record_tool("Recon", "ScopeGate (Violation Enforcement)", "PASS", "ScopeViolationException raised on out-of-scope host")

    ep_id = sanitize_endpoint_id("PATCH", "/api/v1/orders/{order_id}")
    assert ep_id == "ep_patch_api_v1_orders_order_id"
    record_tool("Recon", "sanitize_endpoint_id", "PASS", f"Generated canonical endpoint ID: {ep_id}")

    sample_openapi = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Test Shop API built with FastAPI", "version": "1.0.0"},
        "paths": {
            "/api/v1/orders/{order_id}": {
                "patch": {"summary": "Update order", "security": [{"bearerAuth": []}]}
            },
            "/admin/danger/wipe": {
                "post": {"summary": "Forbidden wipe"}
            }
        }
    })
    parsed_spec = parse_openapi_spec(sample_openapi, scope_gate=gate)
    assert len(parsed_spec["endpoints"]) == 1
    assert parsed_spec["endpoints"][0]["method"] == "PATCH"
    record_tool("Recon", "parse_openapi_spec (with Scope Gate)", "PASS", "OpenAPI spec parsed; forbidden path correctly dropped")

    tech_hints = ["fastapi", "postgresql"]
    fingerprints = fingerprint_target(tech_hints)
    assert len(fingerprints) >= 2
    record_tool("Recon", "fingerprint_target", "PASS", f"Identified technologies: {[t['name'] for t in fingerprints]}")

    surface_graph = build_attack_surface_graph(parsed_spec["endpoints"], fingerprints, scan_id="scn_recon_tool")
    assert surface_graph.startswith("graph://")
    record_tool("Recon", "build_attack_surface_graph", "PASS", f"Attack surface graph generated: {surface_graph}")

    crew_openapi_tool = OpenApiParserCrewTool()
    res_c_spec = json.loads(crew_openapi_tool._run(sample_openapi))
    assert "endpoints" in res_c_spec
    record_tool("Recon", "OpenApiParserCrewTool (CrewAI)", "PASS", "CrewAI tool parsed OpenAPI spec successfully")

    crew_tech_tool = TechnologyFingerprintCrewTool()
    res_c_tech = json.loads(crew_tech_tool._run(json.dumps(tech_hints)))
    assert len(res_c_tech) >= 2
    record_tool("Recon", "TechnologyFingerprintCrewTool (CrewAI)", "PASS", "CrewAI tool fingerprinted technologies")

    print("\n--- 3. Testing Vulnerability Research Tools (Agent 4) ---")

    skills_dir = os.path.join(workspace_dir, "skills", "Claude-BugHunter", "skills")
    meta_idor = load_skill_metadata(skills_dir, "hunt-idor")
    assert meta_idor.get("name") == "hunt-idor" and len(meta_idor.get("body_excerpt", "")) > 100
    record_tool("Vulnerability Research", "load_skill_metadata", "PASS", f"Loaded BugHunter metadata for {meta_idor['name']}")

    routed_idor = route_skills_for_category(skills_dir, "idor", limit=3)
    assert any(s["skill"] == "hunt-idor" for s in routed_idor)
    record_tool("Vulnerability Research", "route_skills_for_category", "PASS", f"Routed skills for 'idor': {[s['skill'] for s in routed_idor]}")

    cache_dir = os.path.join(workspace_dir, ".aegistrace_cache", "tasks")
    os.makedirs(cache_dir, exist_ok=True)
    mock_task_file = os.path.join(cache_dir, "tsk_tool_test_01.json")
    with open(mock_task_file, "w", encoding="utf-8") as f:
        json.dump({"output": {"test_key": "test_val"}}, f)
    resolved_data = resolve_task_output("out://tsk_tool_test_01", workspace_dir)
    assert resolved_data and resolved_data.get("test_key") == "test_val"
    record_tool("Vulnerability Research", "resolve_task_output", "PASS", "Resolved task output reference from .aegistrace_cache/tasks")

    cg_ctx = query_code_graph_context("graph://scn_123/code", "update_order")
    assert cg_ctx.get("context_found") is True
    record_tool("Vulnerability Research", "query_code_graph_context", "PASS", "Queried code graph context for route symbol")

    norm_p = normalize_path_for_join("/api/v1/orders/{order_id}")
    assert norm_p == "/api/v1/orders/{param}"
    record_tool("Vulnerability Research", "normalize_path_for_join", "PASS", f"Normalized path template to: {norm_p}")

    test_recon_eps = [
        {"endpoint_id": "ep_patch_order", "method": "PATCH", "path": "/api/v1/orders/{order_id}"}
    ]
    correlations = correlate_code_and_recon(analysis["routes"], test_recon_eps)
    assert len(correlations) >= 1
    record_tool("Vulnerability Research", "correlate_code_and_recon", "PASS", f"Correlated {len(correlations)} code route(s) with recon endpoint(s)")

    target_t, target_p, target_c = infer_table_key_and_column("/api/v1/orders/{order_id}", analysis["models"])
    assert target_t == "orders" and target_p == "order_id" and target_c == "shipping_address"
    record_tool("Vulnerability Research", "infer_table_key_and_column", "PASS", f"Inferred DB state checks: table='{target_t}', pk='{target_p}', col='{target_c}'")

    hyps, plans = discover_hypotheses_and_plans(
        routes=analysis["routes"],
        endpoints=test_recon_eps,
        invariants=invariants,
        models=analysis["models"],
        skills_dir=skills_dir
    )
    assert len(hyps) >= 1 and len(plans) >= 1
    record_tool("Vulnerability Research", "discover_hypotheses_and_plans", "PASS", f"Formulated {len(hyps)} hypothesis and {len(plans)} test plan(s)")

    crew_skill_tool = SkillRouterCrewTool()
    res_c_router = json.loads(crew_skill_tool._run("idor", skills_dir=skills_dir))
    assert len(res_c_router) >= 1
    record_tool("Vulnerability Research", "SkillRouterCrewTool (CrewAI)", "PASS", "CrewAI tool routed BugHunter skills")

    crew_cg_tool = CodeGraphQueryCrewTool()
    res_c_cg = json.loads(crew_cg_tool._run("graph://scn_123/code", "update_order"))
    assert res_c_cg.get("context_found") is True
    record_tool("Vulnerability Research", "CodeGraphQueryCrewTool (CrewAI)", "PASS", "CrewAI tool queried code graph context")

finally:
    shutil.rmtree(temp_repo, ignore_errors=True)

print("\n" + "=" * 80)
print(f"AEGISTRACE TOOLS BENCHMARK SUMMARY: {len(tool_results)} TOOLS TESTED")
print("=" * 80)
print(f"{'AGENT':<25} | {'TOOL NAME':<35} | {'STATUS':<10}")
print("-" * 80)
for tr in tool_results:
    print(f"{tr['agent']:<25} | {tr['tool']:<35} | {tr['status']:<10}")
print("=" * 80)
assert all(tr["status"] == "PASS" for tr in tool_results), "Some tools failed verification"
print(f"[+] ALL {len(tool_results)} TOOLS ACROSS THE 3 AGENTS PASSED WITH 100% SUCCESS!")
print("=" * 80)
