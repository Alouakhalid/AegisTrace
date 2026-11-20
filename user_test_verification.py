import os
import sys
import json
import jsonschema
import importlib.util

workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

agent_dir = os.path.join(workspace_dir, "agents", "verfication agent")
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

agent_file_path = os.path.join(agent_dir, "verification_agent.py")
spec = importlib.util.spec_from_file_location("verification_agent", agent_file_path)
v_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v_mod)
VerificationAgent = v_mod.VerificationAgent
run_verification = v_mod.run_verification

val_file_path = os.path.join(agent_dir, "validation.py")
val_spec = importlib.util.spec_from_file_location("v_validation", val_file_path)
val_mod = importlib.util.module_from_spec(val_spec)
val_spec.loader.exec_module(val_mod)
validate_verification_request = val_mod.validate_verification_request
validate_verification_response = val_mod.validate_verification_response

from tools.verification_tools import (
    EvidenceStore,
    DynamicTestingReplayEngine,
    ReproductionEnvError
)

schema_file = os.path.join(workspace_dir, "AegisTrace_Documentation", "AegisTrace_Agent_JSON_Schemas.json")
with open(schema_file, "r", encoding="utf-8") as f:
    schema_bundle = json.load(f)

v_schemas = schema_bundle["agents"]["verification"]

print("=" * 75)
print("AEGISTRACE — VERIFICATION AGENT (AGENT 6) USER TEST SUITE")
print("Target: AegisTrace_Agent_Architecture_EN.pdf (Sections 10.1 - 10.12)")
print("=" * 75)

sample_request = {
    "schema_version": "1.0.0",
    "correlation_id": "cor_0192f230",
    "project_id": "prj_0192f1a0",
    "engagement_id": "eng_0192f1b4",
    "scan_id": "scn_0192f1c9",
    "task_id": "tsk_0192f306",
    "agent_run_id": "run_0192f406",
    "created_at": "2026-11-17T09:32:10Z",
    "agent": "verification",
    "input": {
        "hypothesis": {
            "hypothesis_id": "hyp_idor_patch_order",
            "category": "idor",
            "title": "Non-owner can modify another user's order via PATCH /orders/{order_id}",
            "rationale": "Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
            "endpoint_id": "ep_patch_order",
            "invariant_id": "inv_order_owner_only",
            "priority": 1,
            "skill_refs": [
                "hunt-idor"
            ]
        },
        "dynamic_result_ref": "out://tsk_0192f305",
        "evidence_ids": [
            "evd_0192f21a",
            "evd_0192f21b",
            "evd_0192f21c"
        ],
        "invariant_statement": "An order may be read or modified only by the user referenced in orders.user_id",
        "reproduction_runs_requested": 3
    }
}

print("\n[1] Validating Input Request Contract against Pydantic & Master JSON Schema...")
is_valid_req, req_model, req_err = validate_verification_request(sample_request)
assert is_valid_req, f"Pydantic validation failed: {req_err}"
print("[+] VerificationRequest Pydantic V2 Contract: PASS")

jsonschema.validate(instance=sample_request, schema=v_schemas["request"])
print("[+] VerificationRequest Master JSON Schema: PASS")

print("\n[2] Initializing Cryptographic EvidenceStore & Verifying SHA-256 Pre-Conditions...")
store = EvidenceStore()
hash_a = store.register_evidence("evd_0192f21a", "SNAPSHOT pre-execution orders table id=100 owner=1")
hash_b = store.register_evidence("evd_0192f21b", "HTTP PATCH /orders/100 by user_b returned 200 OK")
hash_c = store.register_evidence("evd_0192f21c", "SNAPSHOT post-execution orders table id=100 shipping_address mutated")
print(f"[+] Registered 3 evidence records with SHA-256 fingerprints in store.")
print(f"  - evd_0192f21a: {hash_a[:16]}...")
print(f"  - evd_0192f21b: {hash_b[:16]}...")
print(f"  - evd_0192f21c: {hash_c[:16]}...")

print("\n[3] Executing Verification Agent Full Exploit Arbitration Workflow...")
agent = VerificationAgent()
# The verification agent replays the real dynamic-testing scenario.  These
# steps are supplied explicitly because this standalone suite does not run the
# Dynamic Testing agent first; the target application is the real bundled
# sandbox fixture (PATCH without an ownership check).
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
response = agent.execute(
    sample_request,
    evidence_store=store,
    test_steps=replay_steps,
    state_checks=state_checks,
    sandbox_id="sbx_0192f2f0",
)

print(f"[+] Execution Status: {response['status']}")
print(f"[+] Duration: {response['metrics']['duration_ms']} ms | LLM Calls: {response['metrics']['llm_calls']}")

print("\n[4] Validating Output Response Contract against Pydantic & Master JSON Schema...")
is_valid_resp, resp_model, resp_err = validate_verification_response(response)
assert is_valid_resp, f"Pydantic response validation failed: {resp_err}"
print("[+] VerificationResponse Pydantic V2 Contract: PASS")

jsonschema.validate(instance=response, schema=v_schemas["response"])
print("[+] VerificationResponse Master JSON Schema: PASS")

out = response["output"]
print("\n[5] Verifying Forensic Exploit Arbitration Verdict & Finding:")
print(f"  - Verdict: {out['verdict']}")
print(f"  - Finding ID: {out['finding_id']}")
print(f"  - Invariant Violated: {out['invariant_violated']}")
print(f"  - Confidence: {out['confidence']}")
print(f"  - Reproducibility: {out['reproducibility']['reproduced']}/{out['reproducibility']['runs']}")
print(f"  - Severity Level: {out['severity']['level']}")
print(f"  - CVSS v3.1 Vector: {out['severity']['cvss_vector']}")
print(f"  - Rationale: {out['severity']['rationale']}")

assert out["verdict"] == "confirmed", "Expected verdict to be confirmed"
assert out["invariant_violated"] is True, "Expected invariant_violated to be True"
assert out["finding_id"].startswith("fnd_"), "Expected finding_id to match ^fnd_[0-9a-f]{8,}$"
assert out["reproducibility"]["reproduced"] == 3, "Expected 3/3 reproduction runs"
assert out["severity"]["level"] == "high", "Expected high severity from the observed integrity impact"
assert out["severity"]["cvss_vector"].startswith("CVSS:3.1/")

print("\n[6] Edge Case 1: EVIDENCE_HASH_MISMATCH Handling...")
tampered_store = EvidenceStore()
tampered_store.register_evidence("evd_0192f21a", "Original content")
tampered_store._records["evd_0192f21a"]["content"] = "Tampered unauthorized content"
mismatch_resp = agent.execute(sample_request, evidence_store=tampered_store)
assert mismatch_resp["status"] == "failed"
assert mismatch_resp["error"]["code"] == "EVIDENCE_HASH_MISMATCH"
assert mismatch_resp["error"]["retryable"] is False
print(f"[+] EVIDENCE_HASH_MISMATCH successfully trapped: {mismatch_resp['error']['message']}")

print("\n[7] Edge Case 2: REPRODUCTION_ENV_FAILED with 3-Attempt Retry Exhaustion...")
class FailingSandboxReplayEngine(DynamicTestingReplayEngine):
    def reset_sandbox_with_retry(self, sandbox_id: str) -> bool:
        return False

failing_engine = FailingSandboxReplayEngine()
env_fail_resp = agent.execute(
    sample_request,
    evidence_store=store,
    replay_engine=failing_engine,
    test_steps=replay_steps,
    state_checks=state_checks,
)
assert env_fail_resp["status"] == "failed"
assert env_fail_resp["error"]["code"] == "REPRODUCTION_ENV_FAILED"
assert env_fail_resp["error"]["retryable"] is True
print(f"[+] REPRODUCTION_ENV_FAILED successfully caught with retryable=True: {env_fail_resp['error']['message']}")

print("\n[8] Edge Case 3: INSUFFICIENT_EVIDENCE -> verdict=unconfirmed (Not System Failure)...")
empty_evd_req = json.loads(json.dumps(sample_request))
empty_evd_req["input"]["evidence_ids"] = []
insufficient_resp = agent.execute(empty_evd_req, evidence_store=store)
assert insufficient_resp["status"] == "succeeded"
assert insufficient_resp["output"]["verdict"] == "unconfirmed"
assert insufficient_resp["output"]["finding_id"] is None
assert "INSUFFICIENT_EVIDENCE" in insufficient_resp["warnings"][0]
print(f"[+] INSUFFICIENT_EVIDENCE safely produced verdict=unconfirmed without failing task.")

print("\n[9] Edge Case 4: Triage Gate Rejection (Business Logic Intended)...")
rejection_resp = agent.execute(
    sample_request,
    evidence_store=store,
    test_steps=replay_steps,
    state_checks=state_checks,
    is_business_logic_intended=True,
)
assert rejection_resp["status"] == "succeeded"
assert rejection_resp["output"]["verdict"] == "rejected"
assert len(rejection_resp["output"]["rejection_reasons"]) > 0
print(f"[+] Triage Gate rejection passed: {rejection_resp['output']['rejection_reasons']}")

print("\n[10] Architectural Constraint: Web Search (Tavily) Prohibition as Evidence...")
try:
    store.register_evidence("evd_tavily_bad", "Google or Tavily search result", source_type="tavily")
    assert False, "Should have raised ValueError on tavily source"
except ValueError as ve:
    print(f"[+] Search evidence prohibition confirmed: {ve}")

print("\n" + "=" * 75)
print("VERIFICATION AGENT (AGENT 6) TEST SUITE COMPLETED SUCCESSFULLY: 10/10 PASS")
print("=" * 75)
