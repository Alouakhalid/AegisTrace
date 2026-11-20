import json, pathlib
from schemas import *
P="prj_0192f1a0"; E="eng_0192f1b4"; S="scn_0192f1c9"; C="cor_0192f230"
T={n:f"tsk_0192f30{i}" for i,n in enumerate(["orchestrator","code_intelligence","recon","vulnerability_research","dynamic_testing","verification","remediation"],1)}
R={n:f"run_0192f40{i}" for i,n in enumerate(T,1)}
def env(a,ts): return dict(schema_version="1.0.0",correlation_id=C,project_id=P,engagement_id=E,scan_id=S,task_id=T[a],agent_run_id=R[a],created_at=ts)
def met(d,l,i,o): return dict(duration_ms=d,llm_calls=l,input_tokens=i,output_tokens=o)
EV_A="evd_0192f21a"; EV_B="evd_0192f21b"; EV_D="evd_0192f21c"; EV_R="evd_0192f2a0"
hyp=dict(hypothesis_id="hyp_idor_patch_order",category="idor",title="Non-owner can modify another user's order via PATCH /orders/{order_id}",
 rationale="Route update_order requires authentication but its authz_checks list is empty, while invariant inv_order_owner_only states orders are owner-modifiable only.",
 endpoint_id="ep_patch_order",invariant_id="inv_order_owner_only",priority=1,skill_refs=["hunt-idor"])
plan=dict(test_plan_id="tpl_idor_patch_order",hypothesis_id="hyp_idor_patch_order",method="paired_identity",
 steps=["Snapshot orders.id=100","As buyer_a (owner) PATCH /api/v1/orders/100 with a baseline shipping_address","Snapshot orders.id=100","As buyer_b (non-owner) PATCH /api/v1/orders/100 with a distinct shipping_address","Snapshot orders.id=100 and diff"],
 identities=["id_buyer_a","id_buyer_b"],expected_secure_behavior="Request by non-owner is rejected and orders.id=100.shipping_address is unchanged",
 state_checks=[dict(table="orders",key={"id":100},columns=["shipping_address"])])
endpoint=dict(endpoint_id="ep_patch_order",method="PATCH",path="/api/v1/orders/{order_id}",path_params=["order_id"],auth_required=True,source="openapi")
sandbox=dict(sandbox_id="sbx_0192f2f0",base_url="http://shoplite-app:8000",snapshot_enabled=True,max_requests=200)
ex={}
ex["orchestrator"]=(dict(**env("orchestrator","2026-11-17T09:30:00Z"),agent="orchestrator",input=dict(
  project=dict(name="ShopLite",language="python",framework_hint="fastapi"),
  target=dict(base_url="http://shoplite-app:8000",environment="sandbox"),
  repository=dict(source_type="github",url="https://github.com/example-org/shoplite-api",ref="main"),
  scope_manifest_id="scm_0192f1b9",assessment_mode="full",
  credential_refs=[dict(ref="cred_buyer_a",role="customer"),dict(ref="cred_buyer_b",role="customer"),dict(ref="cred_admin",role="admin")],
  requested_operations=["code_analysis","recon","dynamic_testing","remediation"])),
 dict(**env("orchestrator","2026-11-17T09:30:04Z"),agent="orchestrator",status="succeeded",warnings=[],error=None,metrics=met(3900,1,2100,640),output=dict(
  scope_validation=dict(valid=True,checks=[
   dict(name="manifest_well_formed",passed=True,detail="scm_0192f1b9 parsed, 1 allowed host"),
   dict(name="host_in_scope",passed=True,detail="shoplite-app matches allowed_hosts"),
   dict(name="no_third_party_wildcards",passed=True,detail="no wildcard entries"),
   dict(name="environment_not_production",passed=True,detail="environment=sandbox"),
   dict(name="authorization_attested",passed=True,detail="attested by user usr_0192f19e at 2026-11-17T09:12:00Z")]),
  stages=[dict(name="code_analysis",agent="code_intelligence",depends_on=[],parallel_group="g1"),
   dict(name="recon",agent="recon",depends_on=[],parallel_group="g1"),
   dict(name="research",agent="vulnerability_research",depends_on=["code_analysis","recon"]),
   dict(name="dynamic_testing",agent="dynamic_testing",depends_on=["research"]),
   dict(name="verification",agent="verification",depends_on=["dynamic_testing"]),
   dict(name="remediation",agent="remediation",depends_on=["verification"],requires_approval=True)],
  task_assignments=[dict(task_id=T["code_intelligence"],agent="code_intelligence",stage="code_analysis",depends_on=[]),
   dict(task_id=T["recon"],agent="recon",stage="recon",depends_on=[]),
   dict(task_id=T["vulnerability_research"],agent="vulnerability_research",stage="research",depends_on=[T["code_intelligence"],T["recon"]]),
   dict(task_id=T["dynamic_testing"],agent="dynamic_testing",stage="dynamic_testing",depends_on=[T["vulnerability_research"]]),
   dict(task_id=T["verification"],agent="verification",stage="verification",depends_on=[T["dynamic_testing"]]),
   dict(task_id=T["remediation"],agent="remediation",stage="remediation",depends_on=[T["verification"]])],
  workflow_status="planned")))
ex["code_intelligence"]=(dict(**env("code_intelligence","2026-11-17T09:30:10Z"),agent="code_intelligence",input=dict(
  repository=dict(path_ref="workspace://scn_0192f1c9/repo",commit="a1b2c3d4e5f6"),source_language="python",framework_hints=["fastapi","sqlalchemy"],
  scan_config=dict(max_files=2000,include_globs=["app/**/*.py"],enable_semgrep=False))),
 dict(**env("code_intelligence","2026-11-17T09:31:02Z"),agent="code_intelligence",status="succeeded",warnings=["2 files skipped: syntax errors tolerated by tree-sitter but not resolvable"],error=None,metrics=met(51800,6,18400,3100),output=dict(
  repository_structure=dict(files_analyzed=86,frameworks=["fastapi","sqlalchemy"],entry_points=["app/main.py"]),
  routes=[dict(route_id="rte_patch_order",method="PATCH",path="/api/v1/orders/{order_id}",handler="update_order",file="app/routes/orders.py",line=58,auth_required=True,authz_checks=[]),
          dict(route_id="rte_get_order",method="GET",path="/api/v1/orders/{order_id}",handler="get_order",file="app/routes/orders.py",line=31,auth_required=True,authz_checks=["order.user_id == current_user.id"])],
  auth_mechanisms=[dict(name="get_current_user",kind="authentication",location="app/deps.py:14",description="Decodes bearer JWT and loads the user")],
  db_models=[dict(name="Order",table="orders",owner_field="user_id",file="app/models.py")],
  code_graph_ref="graph://scn_0192f1c9/code",
  candidate_invariants=[dict(invariant_id="inv_order_owner_only",statement="An order may be read or modified only by the user referenced in orders.user_id",kind="ownership",applies_to_route_ids=["rte_patch_order","rte_get_order"],source="code",confidence=0.86)])))
ex["recon"]=(dict(**env("recon","2026-11-17T09:30:10Z"),agent="recon",input=dict(
  scope=dict(allowed_hosts=["shoplite-app"],allowed_methods=["GET","POST","PATCH","DELETE"],forbidden_paths=["/admin/danger/*"]),
  api_spec_ref="workspace://scn_0192f1c9/openapi.json",technology_hints=["fastapi","postgresql"],
  research=dict(enabled=True,max_queries=3,search_depth="basic"))),
 dict(**env("recon","2026-11-17T09:30:51Z"),agent="recon",status="succeeded",warnings=[],error=None,metrics=met(41000,3,6200,1500),output=dict(
  endpoints=[dict(endpoint_id="ep_patch_order",method="PATCH",path="/api/v1/orders/{order_id}",path_params=["order_id"],auth_required=True,source="openapi"),
             dict(endpoint_id="ep_get_order",method="GET",path="/api/v1/orders/{order_id}",path_params=["order_id"],auth_required=True,source="openapi")],
  technologies=[dict(name="FastAPI",version=None,confidence=0.9,evidence="OpenAPI document generator metadata and /docs route"),
                dict(name="PostgreSQL",version=None,confidence=0.7,evidence="docker-compose service image name")],
  attack_surface_ref="graph://scn_0192f1c9/attack_surface",
  intel_refs=[dict(ref_id="ref_0192f2b1",title="API1:2023 Broken Object Level Authorization",url="https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",retrieved_at="2026-11-17T09:30:40Z",source_type="owasp",relevance=0.9,trusted=False)])))
ex["vulnerability_research"]=(dict(**env("vulnerability_research","2026-11-17T09:31:10Z"),agent="vulnerability_research",input=dict(
  code_intel_ref="out://tsk_0192f302",recon_ref="out://tsk_0192f303",invariant_ids=["inv_order_owner_only"],
  skill_hits=[dict(skill="hunt-idor",source_commit="64410ed",score=0.91)])),
 dict(**env("vulnerability_research","2026-11-17T09:31:30Z"),agent="vulnerability_research",status="succeeded",warnings=[],error=None,metrics=met(20100,2,9100,1800),output=dict(hypotheses=[hyp],test_plans=[plan])))
ids=[dict(identity_id="id_buyer_a",role="customer",credential_ref="cred_buyer_a",owns={"order_id":100}),
     dict(identity_id="id_buyer_b",role="customer",credential_ref="cred_buyer_b",owns={"order_id":200})]
ex["dynamic_testing"]=(dict(**env("dynamic_testing","2026-11-17T09:31:35Z"),agent="dynamic_testing",input=dict(
  test_plan=plan,endpoint=endpoint,identities=ids,sandbox=sandbox,invariant_id="inv_order_owner_only")),
 dict(**env("dynamic_testing","2026-11-17T09:32:05Z"),agent="dynamic_testing",status="succeeded",warnings=[],error=None,metrics=met(29800,0,0,0),output=dict(
  executed_cases=[dict(case_id="case_01",identity_id="id_buyer_a",exchange=dict(method="PATCH",url="http://shoplite-app:8000/api/v1/orders/100",status_code=200,response_excerpt='{"id":100,"status":"updated"}',evidence_id=EV_A)),
                  dict(case_id="case_02",identity_id="id_buyer_b",exchange=dict(method="PATCH",url="http://shoplite-app:8000/api/v1/orders/100",status_code=403,response_excerpt='{"detail":"Forbidden"}',evidence_id=EV_B))],
  identity_comparison="Owner received 200; non-owner received 403 (response-level control appears to hold)",
  state_diffs=[dict(table="orders",key={"id":100},column="shipping_address",before="12 Nile St, Alexandria",after="99 Test Ave, Cairo",snapshot_before_id="snp_0192f2c1",snapshot_after_id="snp_0192f2c2",evidence_id=EV_D)],
  execution_status="completed",log_ref="log://tsk_0192f305")))
ex["verification"]=(dict(**env("verification","2026-11-17T09:32:10Z"),agent="verification",input=dict(
  hypothesis=hyp,dynamic_result_ref="out://tsk_0192f305",evidence_ids=[EV_A,EV_B,EV_D],
  invariant_statement="An order may be read or modified only by the user referenced in orders.user_id",reproduction_runs_requested=3)),
 dict(**env("verification","2026-11-17T09:32:50Z"),agent="verification",status="succeeded",warnings=[],error=None,metrics=met(40000,2,7400,1200),output=dict(
  finding_id="fnd_0192f200",verdict="confirmed",reproducibility=dict(runs=3,reproduced=3),confidence=0.97,
  severity=dict(level="medium",rationale="Authenticated non-owner can alter another customer's order data (integrity impact, no confidentiality impact observed); low attack complexity",cvss_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N"),
  invariant_violated=True,supporting_evidence_ids=[EV_B,EV_D],rejection_reasons=[])))
ex["remediation"]=(dict(**env("remediation","2026-11-17T09:32:55Z"),agent="remediation",input=dict(
  finding_id="fnd_0192f200",source_refs=[dict(file="app/routes/orders.py",start_line=58,end_line=79)],verification_evidence_ids=[EV_B,EV_D],
  test_environment=sandbox,original_test_plan_id="tpl_idor_patch_order",max_attempts=3)),
 dict(**env("remediation","2026-11-17T09:34:20Z"),agent="remediation",status="succeeded",warnings=[],error=None,metrics=met(85000,5,26000,4200),output=dict(
  root_cause=dict(summary="update_order loads the order by id and applies changes without comparing order.user_id to the authenticated user; the 403 is produced by a later serialization step after the write is committed",files=["app/routes/orders.py"]),
  patch=dict(patch_id="pat_0192f500",branch="fix/aegistrace-fnd-0192f200",diff_ref="patches/pat_0192f500.diff",changed_files=["app/routes/orders.py","tests/test_orders_authz.py"]),
  tests=dict(unit=dict(total=42,passed=42,failed=0),integration=dict(total=18,passed=18,failed=0),regression=dict(total=120,passed=120,failed=0)),
  replay=dict(original_scenario_replayed=True,vulnerability_still_reproducible=False,evidence_id=EV_R),
  remediation_status="patch_ready_for_review",requires_human_approval=True)))
if __name__=="__main__":
    out=pathlib.Path("examples"); out.mkdir(exist_ok=True)
    for a,(rq,rs) in ex.items():
        RQ,RS=PAIRS[a]; RQ.model_validate(rq); RS.model_validate(rs)
        (out/f"{a}_request.json").write_text(json.dumps(rq,indent=2)); (out/f"{a}_response.json").write_text(json.dumps(rs,indent=2))
        print("valid:",a)
    # negative tests
    import copy
    from pydantic import ValidationError
    bad=copy.deepcopy(ex["verification"][1]); bad["output"]["unexpected"]=1
    try: VerificationResponse.model_validate(bad); print("NEG1 FAIL")
    except ValidationError: print("negative ok: extra field rejected")
    bad=copy.deepcopy(ex["remediation"][1]); bad["output"]["requires_human_approval"]=False
    try: RemediationResponse.model_validate(bad); print("NEG2 FAIL")
    except ValidationError: print("negative ok: approval flag cannot be false")
    bad=copy.deepcopy(ex["orchestrator"][0]); bad["input"]["credential_refs"]=bad["input"]["credential_refs"][:1]
    try: OrchestratorRequest.model_validate(bad); print("NEG3 FAIL")
    except ValidationError: print("negative ok: <2 identities rejected")
    bundle={"$schema":"https://json-schema.org/draft/2020-12/schema","title":"AegisTrace Agent Contracts","schema_version":"1.0.0","agents":{}}
    for a,(RQ,RS) in PAIRS.items(): bundle["agents"][a]={"request":RQ.model_json_schema(),"response":RS.model_json_schema()}
    pathlib.Path("AegisTrace_Agent_JSON_Schemas.json").write_text(json.dumps(bundle,indent=2))
    print("schemas bytes",pathlib.Path("AegisTrace_Agent_JSON_Schemas.json").stat().st_size)
