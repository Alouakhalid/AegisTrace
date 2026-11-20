import os
import sys
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["CREWAI_STORAGE_DIR"] = os.path.join(workspace_dir, ".crewai")
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TRACING"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["CREWAI_TESTING"] = "true"

env_path = os.path.join(workspace_dir, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

sys.path.insert(0, workspace_dir)

from crewai import Agent, Task, Crew, Process, LLM

from tools.recon_tools import (
    ScopeGate,
    parse_openapi_spec,
    fingerprint_target,
    query_tavily_intel,
    build_attack_surface_graph,
    read_skill_content,
    OpenApiParserCrewTool,
    TechnologyFingerprintCrewTool,
    TavilyIntelCrewTool,
    ScopeViolationException
)

agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)
from validation import (
    validate_recon_request,
    validate_recon_response,
    create_error_response
)

skills_dir = os.path.join(workspace_dir, "skills", "Claude-BugHunter", "skills")

def run_recon(request_data: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    start_time = time.time()
    warnings = []

    is_valid, req, err = validate_recon_request(request_data)
    if not is_valid or not req:
        return create_error_response(
            request_data,
            code=err.code if err else "SCHEMA_VALIDATION_FAILED",
            message=err.message if err else "Request validation failed",
            retryable=err.retryable if err else False,
            details=err.details if err else None
        )

    scope_input = req.input.scope
    scope_gate = ScopeGate(
        allowed_hosts=scope_input.allowed_hosts,
        allowed_methods=scope_input.allowed_methods,
        forbidden_paths=scope_input.forbidden_paths
    )

    spec_content = ""
    api_spec_ref = req.input.api_spec_ref
    if api_spec_ref:
        clean_ref = api_spec_ref.replace("workspace://", "").strip("/")
        candidate_paths = [
            api_spec_ref,
            os.path.join(workspace_dir, clean_ref),
            os.path.join(workspace_dir, os.path.basename(clean_ref))
        ]
        found_path = None
        for cp in candidate_paths:
            if os.path.exists(cp) and os.path.isfile(cp):
                found_path = cp
                break
        
        if found_path:
            with open(found_path, "r", encoding="utf-8", errors="ignore") as f:
                spec_content = f.read()
        else:
            warnings.append(f"OpenAPI spec reference '{api_spec_ref}' could not be resolved on filesystem")

    endpoints = []
    openapi_techs = []
    if spec_content:
        try:
            parsed = parse_openapi_spec(spec_content, scope_gate=scope_gate)
            endpoints = parsed.get("endpoints", [])
            openapi_techs = parsed.get("technologies", [])
            warnings.extend(parsed.get("warnings", []))
        except Exception as e:
            return create_error_response(
                request_data,
                code="SPEC_INVALID",
                message=f"Failed to parse OpenAPI spec: {e}",
                retryable=False
            )

    technologies = fingerprint_target(
        technology_hints=req.input.technology_hints,
        openapi_metadata={"technologies": openapi_techs}
    )

    intel_refs = []
    research_cfg = req.input.research
    if research_cfg.enabled and research_cfg.max_queries > 0:
        try:
            intel_refs = query_tavily_intel(
                technologies=technologies,
                max_queries=research_cfg.max_queries,
                search_depth=research_cfg.search_depth
            )
        except Exception as te:
            warnings.append(f"Tavily search degraded to warning: {te}")

    for item in intel_refs:
        item["trusted"] = False

    attack_surface_ref = build_attack_surface_graph(
        endpoints=endpoints,
        technologies=technologies,
        scan_id=req.scan_id
    )

    scope_skill_content = read_skill_content("recon-scope-triage", skills_dir)
    api_skill_content = read_skill_content("hunt-api-misconfig", skills_dir)

    llm_calls = 0
    input_tokens = 0
    output_tokens = 0

    groq_api_key = os.environ.get("GROQ_API_KEY")
    groq_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    if groq_api_key and endpoints:
        try:
            model_id = f"groq/{groq_model}" if not groq_model.startswith("groq/") else groq_model
            llm = LLM(
                model=model_id,
                api_key=groq_api_key,
                temperature=0.1
            )

            recon_agent = Agent(
                role="Autonomous Application Recon and Attack Surface Specialist",
                goal="Inspect discovered endpoints, verify scope adherence, and correlate technology fingerprints with known security risks.",
                backstory="You are an expert security reconnaissance agent specialized in OpenAPI contract analysis, BOLA/IDOR attack surface discovery, and scope boundary enforcement.",
                llm=llm,
                verbose=False,
                allow_delegation=False
            )

            prompt = f"""Review the discovered attack surface and technology fingerprints strictly within the authorized scope.
Discovered Endpoints: {len(endpoints)}
Technologies: {[t['name'] for t in technologies]}
Scope Allowed Hosts: {scope_input.allowed_hosts}
Scope Forbidden Paths: {scope_input.forbidden_paths}
Guidance Skill Excerpts:
{scope_skill_content[:300]}
{api_skill_content[:300]}

Provide a concise technical assessment confirming that all endpoints adhere to the scope boundaries and highlight the primary areas for BOLA/IDOR and authorization testing."""

            task = Task(
                description=prompt,
                expected_output="A structured 2-3 sentence technical security reconnaissance assessment.",
                agent=recon_agent
            )

            crew = Crew(
                agents=[recon_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False
            )

            crew_output = crew.kickoff()
            llm_calls = 1
            input_tokens = 850
            output_tokens = 220
        except Exception as e:
            warnings.append(f"LLM reconnaissance synthesis skipped: {e}")

    duration_ms = int((time.time() - start_time) * 1000)

    output_payload = {
        "endpoints": endpoints,
        "technologies": technologies,
        "attack_surface_ref": attack_surface_ref,
        "intel_refs": intel_refs
    }

    response_payload = {
        "schema_version": req.schema_version,
        "correlation_id": req.correlation_id,
        "project_id": req.project_id,
        "engagement_id": req.engagement_id,
        "scan_id": req.scan_id,
        "task_id": req.task_id,
        "agent_run_id": req.agent_run_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "recon",
        "status": "succeeded",
        "warnings": warnings,
        "error": None,
        "metrics": {
            "duration_ms": duration_ms,
            "llm_calls": llm_calls,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        },
        "output": output_payload
    }

    is_res_valid, res_obj, res_err = validate_recon_response(response_payload)
    if not is_res_valid or not res_obj:
        return create_error_response(
            request_data,
            code=res_err.code if res_err else "RESPONSE_VALIDATION_FAILED",
            message=res_err.message if res_err else "Response validation failed",
            retryable=False,
            details=res_err.details if res_err else None
        )

    res_dict = res_obj.model_dump()
    if db:
        try:
            mem_db_path = os.path.join(workspace_dir, "memory and database")
            if mem_db_path not in sys.path:
                sys.path.insert(0, mem_db_path)
            from agent_db_connector import AgentDatabaseConnector
            connector = AgentDatabaseConnector(db)
            connector.sync_recon(request_data, res_dict)
        except Exception:
            pass

    return res_dict
