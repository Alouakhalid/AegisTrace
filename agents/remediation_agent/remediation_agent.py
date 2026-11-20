import os
import sys
import json
import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from crewai import Agent, Crew, Task, LLM

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from agents.remediation_agent.validation import (
    validate_remediation_request,
    validate_remediation_response,
    create_error_response,
    RemediationRequest,
    RemediationResponse,
    RemediationOutput,
    RootCause,
    PatchInfo,
    TestCounts,
    RemediationTests,
    ReplayResult,
    RemediationStatus,
    Metrics,
    TaskStatus
)
from tools.remediation_tools import (
    IsolatedGitManager,
    PatchSynthesizer,
    SandboxTestRunner,
    DynamicExploitReplayer,
    FindingNotConfirmedError,
    BranchProtectedError,
    PatchTestsFailedError,
    ExploitStillReproducesError,
    PatchNotPossibleError,
    CreateIsolatedBranchTool,
    ApplyPatchTool,
    RunSandboxTestsTool,
    ReplayExploitOnPatchTool,
    TavilyFixGuidanceTool
)
from tools.artifact_store import save_evidence, save_task_output


class RemediationAgent:
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
            CreateIsolatedBranchTool(),
            ApplyPatchTool(),
            RunSandboxTestsTool(),
            ReplayExploitOnPatchTool(),
            TavilyFixGuidanceTool()
        ]
        self.crew_agent = Agent(
            role="Autonomous Security Patch Engineer & Remediation Specialist",
            goal="Analyze root cause from verified findings, synthesize minimal secure patches on isolated branches, verify with unit/integration/regression test suites, and prove vulnerability closure via exploit replay.",
            backstory="Staff application security and software engineer specialized in minimal non-breaking remediation patches, authorization regression testing, and verification replays.",
            llm=self.llm,
            tools=self.tools,
            verbose=False
        )

    @staticmethod
    def _zero_tests() -> RemediationTests:
        zero = TestCounts(total=0, passed=0, failed=0)
        return RemediationTests(unit=zero, integration=zero, regression=zero)

    @staticmethod
    def _tests_from_results(results: Dict[str, Dict[str, int]]) -> RemediationTests:
        return RemediationTests(
            unit=TestCounts(**results["unit"]),
            integration=TestCounts(**results["integration"]),
            regression=TestCounts(**results["regression"])
        )

    def _patch_not_possible(
        self,
        req: RemediationRequest,
        request_data: Dict[str, Any],
        reason: str,
        warnings: List[str],
        duration_ms: int,
        test_results: Optional[Dict[str, Dict[str, int]]] = None,
    ) -> Dict[str, Any]:
        """Return an honest patch_not_possible outcome with real evidence."""
        files = [ref.file for ref in req.input.source_refs]
        evidence_content = (
            f"PATCH_NOT_POSSIBLE finding={req.input.finding_id} "
            f"reason={reason} files={json.dumps(files, sort_keys=True)}"
        )
        digest = hashlib.sha256(evidence_content.encode("utf-8")).hexdigest()
        evidence_id = f"evd_{digest[:10]}"
        save_evidence(
            evidence_id,
            evidence_content,
            {
                "kind": "remediation_patch_not_possible",
                "finding_id": req.input.finding_id,
                "reason": reason,
            },
        )
        warnings.append(f"PATCH_NOT_POSSIBLE: {reason}")

        tests = self._tests_from_results(test_results) if test_results else self._zero_tests()
        output = RemediationOutput(
            root_cause=RootCause(summary=reason, files=files),
            patch=None,
            tests=tests,
            replay=ReplayResult(
                original_scenario_replayed=False,
                vulnerability_still_reproducible=True,
                evidence_id=evidence_id,
            ),
            remediation_status=RemediationStatus.PATCH_NOT_POSSIBLE,
            requires_human_approval=True,
        )
        return self._build_response(req, request_data, output, warnings, duration_ms)

    def _build_response(
        self,
        req: RemediationRequest,
        request_data: Dict[str, Any],
        output: RemediationOutput,
        warnings: List[str],
        duration_ms: int,
    ) -> Dict[str, Any]:
        response_dict = {
            "schema_version": req.schema_version,
            "correlation_id": req.correlation_id,
            "project_id": req.project_id,
            "engagement_id": req.engagement_id,
            "scan_id": req.scan_id,
            "task_id": req.task_id,
            "agent_run_id": req.agent_run_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": "remediation",
            "status": TaskStatus.SUCCEEDED.value,
            "warnings": warnings,
            "error": None,
            "metrics": {
                "duration_ms": max(1, duration_ms),
                "llm_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0
            },
            "output": output.model_dump(mode="json")
        }

        is_resp_valid, _resp_model, resp_err = validate_remediation_response(response_dict)
        if not is_resp_valid:
            return create_error_response(
                request_data=request_data,
                code="RESPONSE_VALIDATION_FAILED",
                message=resp_err or "RemediationResponse schema validation failed",
                retryable=False,
                duration_ms=duration_ms
            )
        return response_dict

    def execute(
        self,
        request_data: Dict[str, Any],
        git_manager: Optional[IsolatedGitManager] = None,
        test_runner: Optional[SandboxTestRunner] = None,
        exploit_replayer: Optional[DynamicExploitReplayer] = None,
        finding_verdict: str = "confirmed",
        target_branch: Optional[str] = None,
        fail_tests: bool = False,
        force_exploit_reproduces: bool = False,
        repo_path: Optional[str] = None,
        test_steps: Optional[List[Dict[str, Any]]] = None,
        state_checks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        warnings: List[str] = []

        is_valid, req, err = validate_remediation_request(request_data)
        if not is_valid or not req:
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="INVALID_REQUEST_PAYLOAD",
                message=err or "Schema validation failed against RemediationRequest",
                retryable=False,
                duration_ms=duration_ms
            )

        if finding_verdict.lower() != "confirmed":
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="FINDING_NOT_CONFIRMED",
                message=f"Input finding {req.input.finding_id} is not confirmed (verdict: {finding_verdict})",
                retryable=False,
                duration_ms=duration_ms
            )

        mgr = git_manager or IsolatedGitManager(repo_path)
        branch_name = target_branch or f"fix/aegistrace-{req.input.finding_id}"
        try:
            created_branch = mgr.create_isolated_branch(req.input.finding_id, branch_name=branch_name)
        except BranchProtectedError as bpe:
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="BRANCH_PROTECTED",
                message=str(bpe),
                retryable=False,
                duration_ms=duration_ms
            )
        except PatchNotPossibleError as pnpe:
            duration_ms = int((time.time() - start_time) * 1000)
            return self._patch_not_possible(req, request_data, str(pnpe), warnings, duration_ms)

        source_refs_dicts = [s.model_dump() for s in req.input.source_refs]
        try:
            patch_data = PatchSynthesizer.synthesize_patch(
                req.input.finding_id,
                source_refs_dicts,
                repo_path=mgr.repo_path,
            )
            diff_ref = mgr.save_unified_diff(patch_data["patch_id"], patch_data["diff_content"])
            mgr.apply_unified_diff(patch_data["patch_id"], patch_data["diff_content"])
        except PatchNotPossibleError as pnpe:
            duration_ms = int((time.time() - start_time) * 1000)
            return self._patch_not_possible(req, request_data, str(pnpe), warnings, duration_ms)

        runner = test_runner or SandboxTestRunner(mgr.repo_path)
        tests_passed = False
        test_results: Dict[str, Any] = {}
        last_test_error = ""

        for attempt in range(req.input.max_attempts):
            try:
                test_results = runner.run_all_test_suites(
                    branch=created_branch,
                    changed_files=patch_data["changed_files"],
                    fail_unit=fail_tests,
                    fail_integration=fail_tests,
                    fail_regression=fail_tests
                )
            except PatchTestsFailedError as exc:
                last_test_error = str(exc)
                if attempt + 1 >= req.input.max_attempts:
                    break
                time.sleep(0.05 * (attempt + 1))
                continue

            total_failed = (
                test_results["unit"]["failed"]
                + test_results["integration"]["failed"]
                + test_results["regression"]["failed"]
            )
            if total_failed == 0:
                tests_passed = True
                break
            if attempt + 1 < req.input.max_attempts:
                time.sleep(0.05 * (attempt + 1))

        if not tests_passed:
            duration_ms = int((time.time() - start_time) * 1000)
            details = test_results or {}
            if last_test_error:
                details = {**details, "runner_error": last_test_error}
            return create_error_response(
                request_data=request_data,
                code="PATCH_TESTS_FAILED",
                message=(
                    f"Tests failed after {req.input.max_attempts} attempts"
                    + (f": {last_test_error}" if last_test_error else "")
                ),
                retryable=False,
                details=details,
                duration_ms=duration_ms
            )

        replayer = exploit_replayer or DynamicExploitReplayer()
        try:
            replay_dict = replayer.replay_exploit(
                sandbox_id=req.input.test_environment.sandbox_id,
                test_plan_id=req.input.original_test_plan_id,
                is_patched=True,
                force_bug_remains=force_exploit_reproduces,
                base_url=req.input.test_environment.base_url,
                test_steps=test_steps,
                state_checks=state_checks,
                patched_files=patch_data.get("patched_files"),
            )
        except PatchNotPossibleError as pnpe:
            duration_ms = int((time.time() - start_time) * 1000)
            return self._patch_not_possible(
                req, request_data, str(pnpe), warnings, duration_ms, test_results=test_results
            )

        if replay_dict["vulnerability_still_reproducible"] is True:
            duration_ms = int((time.time() - start_time) * 1000)
            return create_error_response(
                request_data=request_data,
                code="EXPLOIT_STILL_REPRODUCES",
                message="Replay shows the bug remains reproducible after patch application",
                retryable=False,
                details=replay_dict,
                duration_ms=duration_ms
            )

        root_cause = RootCause(
            summary=patch_data["root_cause_summary"],
            files=patch_data["files"]
        )
        patch_info = PatchInfo(
            patch_id=patch_data["patch_id"],
            branch=created_branch,
            diff_ref=diff_ref,
            changed_files=patch_data["changed_files"]
        )
        tests_model = self._tests_from_results(test_results)
        replay_model = ReplayResult(**replay_dict)

        output = RemediationOutput(
            root_cause=root_cause,
            patch=patch_info,
            tests=tests_model,
            replay=replay_model,
            remediation_status=RemediationStatus.PATCH_READY_FOR_REVIEW,
            requires_human_approval=True
        )

        duration_ms = int((time.time() - start_time) * 1000)
        response_dict = self._build_response(req, request_data, output, warnings, duration_ms)

        artifact = {
            "task_id": req.task_id,
            "agent": "remediation",
            "request": request_data,
            "response": response_dict,
            "output": response_dict.get("output"),
            "internal": {
                "repo_path": mgr.repo_path,
                "branch": created_branch,
                "patch": {
                    "patch_id": patch_data["patch_id"],
                    "diff_ref": diff_ref,
                    "changed_files": patch_data["changed_files"],
                    "primary_function": patch_data.get("primary_function"),
                },
                "patched_files": patch_data.get("patched_files", {}),
                "test_results": test_results,
                "replay": replay_dict,
            },
        }
        save_task_output(req.task_id, artifact)

        if self.db:
            try:
                mem_db_path = os.path.join(workspace_root, "memory and database")
                if mem_db_path not in sys.path:
                    sys.path.insert(0, mem_db_path)
                from agent_db_connector import AgentDatabaseConnector
                connector = AgentDatabaseConnector(self.db)
                connector.sync_remediation(request_data, response_dict)
            except Exception as exc:
                response_dict["warnings"].append(f"PERSISTENCE_FAILED: remediation sync failed: {exc}")

        return response_dict


def run_remediation(request_data: Dict[str, Any], db: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
    agent = RemediationAgent(db=db)
    return agent.execute(request_data, **kwargs)
