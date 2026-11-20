import os
import re
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

class WorkflowCycleError(Exception):
    pass

class ScopeValidationError(Exception):
    pass

class ScopeValidator:
    def __init__(self, registered_manifests: Optional[Dict[str, Dict[str, Any]]] = None):
        self._manifests = registered_manifests or {}

    def register_manifest(self, scm_id: str, manifest_data: Dict[str, Any], manifest_sha256: Optional[str] = None, valid: bool = True, attested: bool = False) -> None:
        computed_sha = hashlib.sha256(json.dumps(manifest_data, sort_keys=True).encode("utf-8")).hexdigest()
        self._manifests[scm_id] = {
            "id": scm_id,
            "manifest": manifest_data,
            "manifest_sha256": manifest_sha256 or computed_sha,
            "valid": valid,
            "attested": bool(attested)
        }

    @staticmethod
    def _normalize_host(value: str) -> str:
        """Return a lower-case hostname, discarding scheme, port and path."""
        if not value:
            return ""
        candidate = str(value).strip()
        if "://" in candidate:
            parsed = urlparse(candidate)
            return (parsed.hostname or "").lower()
        candidate = candidate.split("/")[0]
        if "@" in candidate:
            candidate = candidate.rsplit("@", 1)[-1]
        if candidate.count(":") == 1:
            candidate = candidate.split(":", 1)[0]
        return candidate.strip().lower()

    @classmethod
    def _host_matches(cls, target_host: str, allowed_entry: str) -> bool:
        """Exact host match, or explicit ``*.example.com`` wildcard match.

        A bare suffix is never accepted: ``shoplite-app.evil.com`` must not
        match an allowed host of ``shoplite-app``.  Wildcards must be written
        explicitly as ``*.example.com`` and never match the apex domain.
        """
        allowed_host = cls._normalize_host(allowed_entry)
        if not allowed_host or not target_host:
            return False
        if allowed_host.startswith("*."):
            suffix = allowed_host[2:]
            return bool(suffix) and target_host.endswith(f".{suffix}") and target_host != suffix
        return target_host == allowed_host

    def validate_scope(self, target_base_url: str, environment: str, scope_manifest_id: str, manifest_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        checks = []
        parsed_target = urlparse(target_base_url)
        target_host = (parsed_target.hostname or "").lower()

        manifest_record = None
        if manifest_data is not None:
            m_data = manifest_data
            m_sha = hashlib.sha256(json.dumps(m_data, sort_keys=True).encode("utf-8")).hexdigest()
            is_attested = m_data.get("attested") is True
        elif scope_manifest_id in self._manifests:
            manifest_record = self._manifests[scope_manifest_id]
            m_data = manifest_record["manifest"]
            m_sha = manifest_record["manifest_sha256"]
            is_attested = bool(manifest_record.get("attested", False))
        else:
            m_data = {}
            m_sha = ""
            is_attested = False

        has_hosts = "allowed_hosts" in m_data and isinstance(m_data["allowed_hosts"], list)
        has_methods = "allowed_methods" in m_data and isinstance(m_data["allowed_methods"], list)
        manifest_well_formed = bool(m_data) and has_hosts and has_methods
        checks.append({
            "name": "manifest_well_formed",
            "passed": manifest_well_formed,
            "detail": "Scope manifest parsed successfully with required keys" if manifest_well_formed else "Manifest missing required allowed_hosts or allowed_methods"
        })

        allowed_hosts = m_data.get("allowed_hosts", [])
        host_in_scope = False
        for ah in allowed_hosts:
            if self._host_matches(target_host, str(ah)):
                host_in_scope = True
                break
        checks.append({
            "name": "host_in_scope",
            "passed": host_in_scope,
            "detail": f"Target host {target_host} confirmed within allowed_hosts" if host_in_scope else f"Target host {target_host} is not in authorized allowed_hosts"
        })

        dangerous_public_suffixes = {
            "com", "net", "org", "io", "co", "dev", "app", "ai", "cloud",
            "co.uk", "com.au", "co.jp", "com.br", "co.in"
        }
        has_dangerous_wildcard = False
        for ah in allowed_hosts:
            entry = self._normalize_host(ah)
            if entry in ["*", "*.*"]:
                has_dangerous_wildcard = True
                break
            if entry.startswith("*."):
                suffix = entry[2:]
                if not suffix or "." not in suffix or suffix in dangerous_public_suffixes:
                    has_dangerous_wildcard = True
                    break
        no_wildcards_passed = not has_dangerous_wildcard
        checks.append({
            "name": "no_third_party_wildcards",
            "passed": no_wildcards_passed,
            "detail": "No dangerous top-level third-party wildcards present" if no_wildcards_passed else "Dangerous top-level wildcard detected in allowed_hosts"
        })

        not_production = environment.lower() != "production" and environment.lower() in ["sandbox", "staging_approved"]
        checks.append({
            "name": "environment_not_production",
            "passed": not_production,
            "detail": f"Target environment '{environment}' permitted for automated testing" if not_production else f"Testing on environment '{environment}' is strictly forbidden in MVP"
        })

        attested_passed = bool(is_attested) and (manifest_record is None or manifest_record.get("valid", True))
        checks.append({
            "name": "authorization_attested",
            "passed": attested_passed,
            "detail": "Customer engagement authorization confirmed and attested" if attested_passed else "Engagement authorization has not been attested by authorized personnel"
        })

        overall_valid = all(c["passed"] for c in checks)
        return overall_valid, checks

class WorkflowPlanner:
    def __init__(self):
        pass

    def check_acyclic(self, stages: List[Dict[str, Any]]) -> None:
        graph = {}
        for s in stages:
            graph[s["name"]] = s.get("depends_on", [])
        
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    cycle_str = " -> ".join(path + [neighbor])
                    raise WorkflowCycleError(f"PLAN_CYCLE: Circular dependency detected in stage DAG: {cycle_str}")
            rec_stack.remove(node)

        for s_name in graph:
            if s_name not in visited:
                dfs(s_name, [s_name])

    def plan_workflow(self, assessment_mode: str, requested_operations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        req_ops = set(requested_operations or ["code_analysis", "recon", "dynamic_testing", "remediation"])
        stages = []
        if assessment_mode == "full":
            if "code_analysis" in req_ops:
                stages.append({
                    "name": "code_analysis",
                    "agent": "code_intelligence",
                    "depends_on": [],
                    "parallel_group": "g1",
                    "requires_approval": False
                })
            if "recon" in req_ops:
                stages.append({
                    "name": "recon",
                    "agent": "recon",
                    "depends_on": [],
                    "parallel_group": "g1",
                    "requires_approval": False
                })
            
            research_deps = [s["name"] for s in stages if s["name"] in ["code_analysis", "recon"]]
            stages.append({
                "name": "vulnerability_research",
                "agent": "vulnerability_research",
                "depends_on": research_deps,
                "parallel_group": None,
                "requires_approval": False
            })

            if "dynamic_testing" in req_ops:
                stages.append({
                    "name": "dynamic_testing",
                    "agent": "dynamic_testing",
                    "depends_on": ["vulnerability_research"],
                    "parallel_group": None,
                    "requires_approval": False
                })
                stages.append({
                    "name": "verification",
                    "agent": "verification",
                    "depends_on": ["dynamic_testing"],
                    "parallel_group": None,
                    "requires_approval": False
                })
            else:
                stages.append({
                    "name": "verification",
                    "agent": "verification",
                    "depends_on": ["vulnerability_research"],
                    "parallel_group": None,
                    "requires_approval": False
                })

            if "remediation" in req_ops:
                stages.append({
                    "name": "remediation",
                    "agent": "remediation",
                    "depends_on": ["verification"],
                    "parallel_group": None,
                    "requires_approval": True
                })

        elif assessment_mode == "code_only":
            stages.append({
                "name": "code_analysis",
                "agent": "code_intelligence",
                "depends_on": [],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "vulnerability_research",
                "agent": "vulnerability_research",
                "depends_on": ["code_analysis"],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "remediation",
                "agent": "remediation",
                "depends_on": ["vulnerability_research"],
                "parallel_group": None,
                "requires_approval": True
            })

        elif assessment_mode == "dynamic_only":
            stages.append({
                "name": "recon",
                "agent": "recon",
                "depends_on": [],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "vulnerability_research",
                "agent": "vulnerability_research",
                "depends_on": ["recon"],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "dynamic_testing",
                "agent": "dynamic_testing",
                "depends_on": ["vulnerability_research"],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "verification",
                "agent": "verification",
                "depends_on": ["dynamic_testing"],
                "parallel_group": None,
                "requires_approval": False
            })
            stages.append({
                "name": "remediation",
                "agent": "remediation",
                "depends_on": ["verification"],
                "parallel_group": None,
                "requires_approval": True
            })

        self.check_acyclic(stages)
        return stages

class TaskQueueManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._stage_to_task: Dict[str, str] = {}

    def generate_task_id(self) -> str:
        return f"tsk_{uuid.uuid4().hex[:12]}"

    def create_assignments_for_stages(self, stages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        assignments = []
        for stage in stages:
            t_id = self.generate_task_id()
            self._stage_to_task[stage["name"]] = t_id
            stage_deps = stage.get("depends_on", [])
            dep_task_ids = [self._stage_to_task[d] for d in stage_deps if d in self._stage_to_task]
            assignment = {
                "task_id": t_id,
                "agent": stage["agent"],
                "stage": stage["name"],
                "depends_on": dep_task_ids
            }
            assignments.append(assignment)
            self._tasks[t_id] = {
                **assignment,
                "status": "queued",
                "requires_approval": stage.get("requires_approval", False)
            }
        return assignments

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, status: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status

class AuditLogger:
    def __init__(self, db: Optional[Any] = None):
        self.db = db
        self._in_memory_logs: List[Dict[str, Any]] = []

    def emit_log(self, actor_type: str, actor_id: str, action: str, allowed: bool, scan_id: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log_entry = {
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "allowed": allowed,
            "scan_id": scan_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {}
        }
        self._in_memory_logs.append(log_entry)
        if self.db:
            try:
                self.db.insert_audit_log(
                    actor_type=actor_type,
                    actor_id=actor_id,
                    action=action,
                    allowed=allowed,
                    scan_id=scan_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details
                )
            except Exception:
                pass
        return log_entry

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(self._in_memory_logs)

class ValidateScopeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_base_url: str = Field(..., description="Target application base URL")
    environment: str = Field(..., description="Environment (sandbox or staging_approved)")
    scope_manifest_id: str = Field(..., description="Identifier of the scope manifest")
    manifest_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional raw scope manifest dictionary")

class ValidateScopeTool(BaseTool):
    name: str = "validate_scope"
    description: str = "Deterministically validates the 5 mandatory scope checks (manifest format, host scope, wildcard exclusion, environment, authorization)."
    args_schema: type[BaseModel] = ValidateScopeInput
    validator: ScopeValidator = Field(default_factory=ScopeValidator)

    def _run(self, target_base_url: str, environment: str, scope_manifest_id: str, manifest_data: Optional[Dict[str, Any]] = None) -> str:
        valid, checks = self.validator.validate_scope(target_base_url, environment, scope_manifest_id, manifest_data)
        return json.dumps({"valid": valid, "checks": checks})

class PlanWorkflowStagesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_mode: str = Field(..., description="Assessment mode (full, code_only, dynamic_only)")
    requested_operations: Optional[List[str]] = Field(default=None, description="Requested operations")

class PlanWorkflowStagesTool(BaseTool):
    name: str = "plan_workflow_stages"
    description: str = "Constructs the 6-stage assessment DAG, grouping parallel stages and validating cycle freedom."
    args_schema: type[BaseModel] = PlanWorkflowStagesInput
    planner: WorkflowPlanner = Field(default_factory=WorkflowPlanner)

    def _run(self, assessment_mode: str, requested_operations: Optional[List[str]] = None) -> str:
        try:
            stages = self.planner.plan_workflow(assessment_mode, requested_operations)
            return json.dumps({"status": "planned", "stages": stages})
        except WorkflowCycleError as e:
            return json.dumps({"status": "cycle_error", "error": str(e)})

class AssignAgentTasksInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stages: List[Dict[str, Any]] = Field(..., description="List of scheduled stages")

class AssignAgentTasksTool(BaseTool):
    name: str = "assign_agent_tasks"
    description: str = "Generates task assignments with unique tsk_* identifiers and dependency task links."
    args_schema: type[BaseModel] = AssignAgentTasksInput
    queue_manager: TaskQueueManager = Field(default_factory=TaskQueueManager)

    def _run(self, stages: List[Dict[str, Any]]) -> str:
        assignments = self.queue_manager.create_assignments_for_stages(stages)
        return json.dumps({"task_assignments": assignments})

class EmitAuditLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(..., description="Action name")
    allowed: bool = Field(..., description="Whether action was permitted")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Log details")

class EmitAuditLogTool(BaseTool):
    name: str = "emit_audit_log"
    description: str = "Emits an immutable audit record for orchestrator execution and scope decisions."
    args_schema: type[BaseModel] = EmitAuditLogInput
    logger: AuditLogger = Field(default_factory=AuditLogger)

    def _run(self, action: str, allowed: bool, details: Optional[Dict[str, Any]] = None) -> str:
        log_res = self.logger.emit_log(
            actor_type="agent",
            actor_id="orchestrator",
            action=action,
            allowed=allowed,
            details=details
        )
        return json.dumps({"status": "logged", "entry": log_res})
