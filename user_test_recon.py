import os
import sys
import json
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace_dir)

agent_file_path = os.path.join(workspace_dir, "agents", "recon_agent", "recon_agent.py")
spec = importlib.util.spec_from_file_location("recon_agent", agent_file_path)
recon_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recon_mod)
run_recon = recon_mod.run_recon

from tools.recon_tools import ScopeGate, ScopeViolationException

test_openapi = {
    "openapi": "3.0.3",
    "info": {
        "title": "ShopLite E-Commerce Platform",
        "description": "High-performance store API built with FastAPI framework and PostgreSQL",
        "version": "1.0.0"
    },
    "servers": [
        {"url": "http://shoplite-app:8000"}
    ],
    "paths": {
        "/api/v1/orders/{order_id}": {
            "get": {
                "summary": "Retrieve order by ID",
                "operationId": "getOrder",
                "security": [{"bearerAuth": []}]
            },
            "patch": {
                "summary": "Update order shipping details",
                "operationId": "updateOrder",
                "security": [{"bearerAuth": []}]
            }
        },
        "/api/v1/orders": {
            "post": {
                "summary": "Create new purchase order",
                "operationId": "createOrder",
                "security": [{"bearerAuth": []}]
            }
        },
        "/api/v1/auth/login": {
            "post": {
                "summary": "Authenticate user and issue JWT",
                "operationId": "login"
            }
        },
        "/admin/danger/wipe_database": {
            "delete": {
                "summary": "Destructive system action",
                "operationId": "wipeDatabase"
            }
        }
    }
}

spec_file_path = os.path.join(workspace_dir, "openapi_test.json")
with open(spec_file_path, "w", encoding="utf-8") as f:
    json.dump(test_openapi, f, indent=2)

print("=" * 70)
print("AEGISTRACE — RECON AGENT (AGENT 3) USER TEST SUITE")
print("=" * 70)

request_payload = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230ab01",
    "project_id": "prj_0192f1a0bc01",
    "engagement_id": "eng_0192f1b4cd01",
    "scan_id": "scn_0192f1c9de01",
    "task_id": "tsk_0192f303ef01",
    "agent_run_id": "run_0192f403fa01",
    "created_at": "2026-11-17T09:30:10Z",
    "agent": "recon",
    "input": {
        "scope": {
            "allowed_hosts": ["shoplite-app", "shoplite.example.com"],
            "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
            "forbidden_paths": ["/admin/danger/*"]
        },
        "api_spec_ref": spec_file_path,
        "technology_hints": ["fastapi", "postgresql"],
        "research": {
            "enabled": True,
            "max_queries": 2,
            "search_depth": "basic"
        }
    }
}

print("\n[1] Executing Recon Agent Workflow...")
response = run_recon(request_payload)

print(f"[+] Response Status: {response.get('status')}")
print(f"[+] Execution Metrics: {response.get('metrics')}")

output = response.get("output", {})
endpoints = output.get("endpoints", [])
technologies = output.get("technologies", [])
intel_refs = output.get("intel_refs", [])
attack_surface_ref = output.get("attack_surface_ref", "")

print(f"\n[2] Attack Surface Endpoints Discovered ({len(endpoints)}):")
for ep in endpoints:
    auth_str = "Auth Required" if ep.get("auth_required") else "Public/Unprotected"
    print(f"  - [{ep['method']}] {ep['path']} -> ID: {ep['endpoint_id']} ({auth_str}) [source: {ep['source']}]")

forbidden_in_output = [ep for ep in endpoints if "/admin/danger" in ep['path']]
assert len(forbidden_in_output) == 0, f"Error: Forbidden path found in output: {forbidden_in_output}"
print("[+] Scope Gate Verification: PASS (Forbidden paths were successfully excluded)")

print(f"\n[3] Fingerprinted Technologies ({len(technologies)}):")
for tech in technologies:
    print(f"  - Technology: {tech['name']} (Confidence: {tech['confidence']}) | Evidence: {tech['evidence']}")

assert any(t["name"] == "FastAPI" for t in technologies), "Error: FastAPI technology not detected"
assert any(t["name"] == "PostgreSQL" for t in technologies), "Error: PostgreSQL technology not detected"
print("[+] Technology Fingerprinting: PASS")

print(f"\n[4] External Security Intelligence References ({len(intel_refs)}):")
for ref in intel_refs:
    print(f"  * ID: {ref['ref_id']} | Type: {ref['source_type']} | Relevance: {ref['relevance']} | Trusted: {ref['trusted']}")
    print(f"    Title: {ref['title']}")
    print(f"    URL: {ref['url']}")

for ref in intel_refs:
    assert ref["trusted"] is False, "Security Violation: intel_ref.trusted must strictly be False"
print("[+] External Intel Trust Invariant: PASS (All external references strictly marked trusted=False)")

print(f"\n[5] Attack Surface Graph Reference: {attack_surface_ref}")
assert attack_surface_ref.startswith("graph://"), "Error: attack_surface_ref does not match graph URI pattern"

print("\n[6] Testing Scope Gate Negative Boundaries (Intentional Scope Violation)...")
scope_gate = ScopeGate(
    allowed_hosts=["shoplite-app"],
    allowed_methods=["GET", "POST"],
    forbidden_paths=["/admin/danger/*"]
)

violation_detected = False
try:
    scope_gate.validate_request("attacker-controlled.net", "GET", "/api/v1/data")
except ScopeViolationException as sve:
    violation_detected = True
    print(f"[+] Out-of-Scope Host Blocked: {sve.message}")
assert violation_detected, "Error: Out-of-scope host was not blocked"

forbidden_detected = False
try:
    scope_gate.validate_request("shoplite-app", "GET", "/admin/danger/leak")
except ScopeViolationException as sve:
    forbidden_detected = True
    print(f"[+] Forbidden Path Blocked: {sve.message}")
assert forbidden_detected, "Error: Forbidden path was not blocked"

print("\n" + "=" * 70)
print("[+] ALL RECON AGENT CAPABILITIES AND INVARIANTS PASSED SUCCESSFULLY!")
print("=" * 70)
