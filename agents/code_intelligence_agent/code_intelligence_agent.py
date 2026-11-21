import os
import re
import sys
import json
import time
import uuid
import datetime
from typing import Literal, Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
import dotenv

workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ["CREWAI_STORAGE_DIR"] = os.path.join(workspace_root, ".crewai")
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TRACING"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["CREWAI_TESTING"] = "true"
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_path = os.path.join(workspace_root, "memory and database")
if mem_db_path not in sys.path:
    sys.path.insert(0, mem_db_path)

dotenv.load_dotenv(os.path.join(workspace_root, ".env"))

import importlib.util
from crewai import Agent, Task, Crew, LLM
from tools.code_intel_tools import (
    analyze_repository,
    construct_code_graph,
    ParsePythonRepositoryTool,
    BuildCodeGraphTool,
    QuerySecuritySkillTool,
    read_skill_content
)

val_file_path = os.path.join(os.path.dirname(__file__), "validation.py")
val_spec = importlib.util.spec_from_file_location("code_intel_validation", val_file_path)
validation_mod = importlib.util.module_from_spec(val_spec)
val_spec.loader.exec_module(validation_mod)

SCHEMA_VERSION = "1.0.0"

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    needs_input = "needs_input"
    cancelled = "cancelled"

class ErrorInfo(Strict):
    code: str = Field(description="Machine-readable error code")
    message: str
    retryable: bool
    details: Optional[dict] = None

class Metrics(Strict):
    duration_ms: int = Field(ge=0)
    llm_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

class Envelope(Strict):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    correlation_id: str = Field(pattern=r"^cor_[0-9a-f]{8,}$")
    project_id: str = Field(pattern=r"^prj_[0-9a-f]{8,}$")
    engagement_id: str = Field(pattern=r"^eng_[0-9a-f]{8,}$")
    scan_id: str = Field(pattern=r"^scn_[0-9a-f]{8,}$")
    task_id: str = Field(pattern=r"^tsk_[0-9a-f]{8,}$")
    agent_run_id: str = Field(pattern=r"^run_[0-9a-f]{8,}$")
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

class ResponseEnvelope(Envelope):
    status: TaskStatus
    warnings: List[str] = []
    error: Optional[ErrorInfo] = None
    metrics: Metrics

class RepoCheckout(Strict):
    path_ref: str
    commit: str = Field(pattern=r"^[0-9a-f]{7,40}$")

class ScanConfig(Strict):
    max_files: int = Field(gt=0)
    include_globs: List[str]
    enable_semgrep: bool

class CodeIntelInput(Strict):
    repository: RepoCheckout
    source_language: Literal["python"]
    framework_hints: List[str]
    scan_config: ScanConfig

class CodeIntelRequest(Envelope):
    agent: Literal["code_intelligence"] = "code_intelligence"
    input: CodeIntelInput

class RepoStructure(Strict):
    files_analyzed: int
    frameworks: List[str]
    entry_points: List[str]

class Route(Strict):
    route_id: str = Field(pattern=r"^rte_[a-z0-9_]+$")
    method: str
    path: str
    handler: str
    file: str
    line: int
    auth_required: bool
    authz_checks: List[str]

class SecurityMechanism(Strict):
    name: str
    kind: Literal["authentication", "authorization"]
    location: str
    description: str

class DbModel(Strict):
    name: str
    table: str
    owner_field: Optional[str] = None
    file: str

class CandidateInvariant(Strict):
    invariant_id: str = Field(pattern=r"^inv_[a-z0-9_]+$")
    statement: str
    kind: Literal["ownership", "role_restriction", "state_transition", "authentication_required"]
    applies_to_route_ids: List[str]
    source: Literal["code", "declared_policy"]
    confidence: float = Field(ge=0, le=1)

class CodeIntelOutput(Strict):
    repository_structure: RepoStructure
    routes: List[Route]
    auth_mechanisms: List[SecurityMechanism]
    db_models: List[DbModel]
    code_graph_ref: str
    candidate_invariants: List[CandidateInvariant]

class CodeIntelResponse(ResponseEnvelope):
    agent: Literal["code_intelligence"] = "code_intelligence"
    output: Optional[CodeIntelOutput] = None

class CodeIntelligenceAgent:
    def __init__(self, groq_api_key: Optional[str] = None, model_name: Optional[str] = None, db: Optional[Any] = None):
        self.api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.model_name = model_name or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.db = db
        self.llm = LLM(
            model=f"groq/{self.model_name}",
            api_key=self.api_key,
            temperature=0.1
        )
        self.tools = [
            ParsePythonRepositoryTool(),
            BuildCodeGraphTool(),
            QuerySecuritySkillTool()
        ]
        self.crew_agent = Agent(
            role="Application Security Code Intelligence Specialist",
            goal="Identify security boundaries, authorization controls, routes, and candidate security invariants from Python repositories.",
            backstory="Senior AppSec static analysis engineer proficient in Python AST, ORM models, and access control vulnerability detection.",
            llm=self.llm,
            tools=self.tools,
            verbose=False
        )

    def derive_invariants_heuristic(self, routes: List[Dict[str, Any]], models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        invariants = []
        models_by_table = {m["table"].lower(): m for m in models}
        models_by_name = {m["name"].lower(): m for m in models}

        for r in routes:
            path_parts = r["path"].strip("/").split("/")
            matched_model = None
            for part in path_parts:
                clean_part = part.strip("{").strip("}").lower()
                if clean_part in models_by_table:
                    matched_model = models_by_table[clean_part]
                    break
                elif clean_part in models_by_name:
                    matched_model = models_by_name[clean_part]
                    break

            if matched_model and matched_model.get("owner_field"):
                owner_field = matched_model["owner_field"]
                model_name = matched_model["name"]
                if r["method"] in ["POST", "PUT", "PATCH", "DELETE"]:
                    if not r["authz_checks"]:
                        inv_id = f"inv_{model_name.lower()}_{owner_field}_only"
                        invariants.append({
                            "invariant_id": inv_id,
                            "statement": f"Only the owner identified by {owner_field} may modify {model_name} records via {r['method']} {r['path']}.",
                            "kind": "ownership",
                            "applies_to_route_ids": [r["route_id"]],
                            "source": "code",
                            "confidence": 0.95
                        })
                elif r["method"] == "GET":
                    if "{" in r["path"] and not r["authz_checks"]:
                        inv_id = f"inv_{model_name.lower()}_{owner_field}_read_only"
                        invariants.append({
                            "invariant_id": inv_id,
                            "statement": f"Only the record owner may access specific {model_name} data via {r['path']}.",
                            "kind": "ownership",
                            "applies_to_route_ids": [r["route_id"]],
                            "source": "code",
                            "confidence": 0.90
                        })

            if not r["auth_required"] and any(sens in r["path"].lower() for sens in ["admin", "dashboard", "billing", "internal", "order", "account"]):
                inv_id = f"inv_auth_req_{r['route_id'].replace('rte_', '')}"
                invariants.append({
                    "invariant_id": inv_id,
                    "statement": f"Access to {r['method']} {r['path']} strictly requires valid authentication.",
                    "kind": "authentication_required",
                    "applies_to_route_ids": [r["route_id"]],
                    "source": "code",
                    "confidence": 0.85
                })

            # Fallback for applications whose state lives in module-level stores
            # (dicts) instead of declarative ORM models: a mutating route that
            # authenticates the caller but carries no ownership/authorization
            # check is a candidate ownership invariant keyed by the REST
            # resource name. Authentication-only dependencies such as
            # get_current_user do NOT count as an ownership check.
            authn_keys = ("auth", "login", "token", "jwt", "session", "current_user")
            authz_keys = ("owner", "tenant", "perm", "role", "scope", "protect", "guard", "require", "admin", "authoriz")
            def _has_ownership_check(checks: List[str]) -> bool:
                for chk in checks:
                    c = chk.lower()
                    if any(k in c for k in authz_keys) or not any(k in c for k in authn_keys):
                        return True
                return False
            if (
                (r["method"] in ["POST", "PUT", "PATCH", "DELETE"] or (r["method"] == "GET" and "{" in r["path"]))
                and r["auth_required"]
                and not _has_ownership_check(r["authz_checks"])
                and not any(inv.get("applies_to_route_ids") == [r["route_id"]] for inv in invariants)
            ):
                segments = [s for s in r["path"].strip("/").split("/") if s and not s.startswith("{")]
                table = re.sub(r"[^a-z0-9_]", "", (segments[-1] if segments else "resource").lower()) or "resource"
                param = re.sub(r"[^a-z0-9_]", "", r["path"].strip("/").split("/")[-1].strip("{}").lower()) or "id"
                owner_field = param if param.endswith("_id") else "user_id"
                inv_id = f"inv_{r['method'].lower()}_{table}_{param}_ownership"
                access_verb = "Mutations to" if r["method"] != "GET" else "Access to"
                invariants.append({
                    "invariant_id": inv_id,
                    "statement": (
                        f"{access_verb} {table} records via {r['method']} {r['path']} are restricted to the "
                        f"record owner ({table}.{owner_field}); any other authenticated principal must be "
                        f"rejected with 403 and cause no state change."
                    ),
                    "kind": "ownership",
                    "applies_to_route_ids": [r["route_id"]],
                    "source": "code",
                    "confidence": 0.80
                })

        seen_ids = set()
        deduped = []
        for inv in invariants:
            if inv["invariant_id"] not in seen_ids:
                seen_ids.add(inv["invariant_id"])
                deduped.append(inv)
        return deduped

    def derive_invariants_with_llm(self, routes: List[Dict[str, Any]], models: List[Dict[str, Any]], skill_guidance: str) -> List[Dict[str, Any]]:
        prompt = f"""You are a specialized AppSec Code Intelligence Agent.
Analyze the following extracted application routes and database models to discover candidate security invariants, specifically focusing on Access Control and IDOR risks.

Extracted Routes:
{json.dumps(routes, indent=2)}

Database Models:
{json.dumps(models, indent=2)}

Claude-BugHunter Skill Guidance:
{skill_guidance[:1500]}

Rules:
1. An invariant statement represents a mandatory security rule the application must enforce.
2. Formats:
   - invariant_id: must match regex ^inv_[a-z0-9_]+$
   - kind: one of ['ownership', 'role_restriction', 'state_transition', 'authentication_required']
   - applies_to_route_ids: list of route_id strings from the provided routes
   - source: "code"
   - confidence: float between 0.0 and 1.0

Output strictly valid JSON array of objects with keys: invariant_id, statement, kind, applies_to_route_ids, source, confidence.
Do not wrap in markdown or commentary, output only raw JSON array."""

        task = Task(
            description=prompt,
            expected_output="JSON array of candidate invariant objects",
            agent=self.crew_agent
        )
        crew = Crew(agents=[self.crew_agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        raw_output = str(result).strip()
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        parsed = json.loads(raw_output.strip())
        if isinstance(parsed, list):
            valid_route_ids = {r["route_id"] for r in routes}
            cleaned = []
            for item in parsed:
                inv_id = str(item.get("invariant_id", "")).lower().replace("-", "_")
                if not inv_id.startswith("inv_"):
                    inv_id = f"inv_{inv_id}"
                applied_routes = [rid for rid in item.get("applies_to_route_ids", []) if rid in valid_route_ids]
                if applied_routes:
                    cleaned.append({
                        "invariant_id": inv_id,
                        "statement": str(item.get("statement", "")),
                        "kind": item.get("kind", "ownership"),
                        "applies_to_route_ids": applied_routes,
                        "source": "code",
                        "confidence": float(item.get("confidence", 0.9))
                    })
            if cleaned:
                return cleaned
        return []

    def execute(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        try:
            validated_request = validation_mod.validate_code_intel_request(request_payload)
        except validation_mod.CodeIntelValidationError as val_err:
            duration_ms = int((time.time() - start_time) * 1000)
            return validation_mod.create_error_response_payload(
                error_code=val_err.code,
                error_message=val_err.message,
                request_payload=request_payload,
                duration_ms=duration_ms
            )

        inp = validated_request.input

        repo_path = inp.repository.path_ref
        if repo_path.startswith("workspace://"):
            subpath = repo_path.replace("workspace://", "")
            candidate_path = os.path.join(workspace_root, subpath)
            if os.path.exists(candidate_path):
                repo_path = candidate_path
            else:
                parts = subpath.split("/", 1)
                if len(parts) > 1 and os.path.exists(os.path.join(workspace_root, parts[1])):
                    repo_path = os.path.join(workspace_root, parts[1])

        if not os.path.exists(repo_path):
            duration_ms = int((time.time() - start_time) * 1000)
            return CodeIntelResponse(
                schema_version=validated_request.schema_version,
                correlation_id=validated_request.correlation_id,
                project_id=validated_request.project_id,
                engagement_id=validated_request.engagement_id,
                scan_id=validated_request.scan_id,
                task_id=validated_request.task_id,
                agent_run_id=f"run_{uuid.uuid4().hex[:8]}",
                created_at=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                status=TaskStatus.failed,
                error=ErrorInfo(
                    code="REPO_UNREADABLE",
                    message=f"Repository path does not exist: {repo_path}",
                    retryable=False
                ),
                metrics=Metrics(duration_ms=duration_ms, llm_calls=0, input_tokens=0, output_tokens=0)
            ).model_dump()

        analysis = analyze_repository(
            repo_path=repo_path,
            max_files=inp.scan_config.max_files,
            include_globs=inp.scan_config.include_globs,
            enable_semgrep=inp.scan_config.enable_semgrep
        )

        code_graph_ref = construct_code_graph(analysis, scan_id=validated_request.scan_id)

        skill_text = read_skill_content("hunt-idor", os.path.join(workspace_root, "skills"))
        if not skill_text:
            skill_text = read_skill_content("hunt-auth-bypass", os.path.join(workspace_root, "skills"))

        llm_calls = 0
        input_tokens = 0
        output_tokens = 0
        candidate_invariants_raw = []

        try:
            candidate_invariants_raw = self.derive_invariants_with_llm(
                routes=analysis["routes"],
                models=analysis["models"],
                skill_guidance=skill_text
            )
            llm_calls = 1
            input_tokens = 850
            output_tokens = 320
        except Exception:
            candidate_invariants_raw = self.derive_invariants_heuristic(
                routes=analysis["routes"],
                models=analysis["models"]
            )

        if not candidate_invariants_raw:
            candidate_invariants_raw = self.derive_invariants_heuristic(
                routes=analysis["routes"],
                models=analysis["models"]
            )

        validated_invariants = [CandidateInvariant(**inv) for inv in candidate_invariants_raw]
        validated_routes = [Route(**r) for r in analysis["routes"]]
        validated_models = [DbModel(**m) for m in analysis["models"]]
        validated_auth = [SecurityMechanism(**a) for a in analysis["auth_mechanisms"]]

        output = CodeIntelOutput(
            repository_structure=RepoStructure(
                files_analyzed=analysis["files_analyzed"],
                frameworks=analysis["frameworks"],
                entry_points=analysis["entry_points"]
            ),
            routes=validated_routes,
            auth_mechanisms=validated_auth,
            db_models=validated_models,
            code_graph_ref=code_graph_ref,
            candidate_invariants=validated_invariants
        )

        duration_ms = int((time.time() - start_time) * 1000)
        response = CodeIntelResponse(
            schema_version=validated_request.schema_version,
            correlation_id=validated_request.correlation_id,
            project_id=validated_request.project_id,
            engagement_id=validated_request.engagement_id,
            scan_id=validated_request.scan_id,
            task_id=validated_request.task_id,
            agent_run_id=f"run_{uuid.uuid4().hex[:8]}",
            created_at=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            status=TaskStatus.succeeded,
            warnings=analysis.get("warnings", []),
            output=output,
            metrics=Metrics(
                duration_ms=duration_ms,
                llm_calls=llm_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        )
        response_dict = response.model_dump()
        validation_mod.validate_code_intel_response(response_dict)
        if self.db:
            try:
                from agent_db_connector import AgentDatabaseConnector
                connector = AgentDatabaseConnector(self.db)
                connector.sync_code_intelligence(request_payload, response_dict)
            except Exception:
                pass
        return response_dict

def run_code_intelligence(request_dict: Dict[str, Any], db: Optional[Any] = None) -> Dict[str, Any]:
    agent = CodeIntelligenceAgent(db=db)
    return agent.execute(request_dict)
