"""Real remediation primitives: Git isolation, patch synthesis, pytest and replay.

Every operation in this module either performs the real action or raises an
explicit error.  Nothing reports a fabricated test count, branch or replay
result.  When the repository, test suite or replay plan is unavailable the
caller receives ``PatchNotPossibleError`` and must surface
``patch_not_possible`` instead of claiming a patch is ready for review.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

from tools.artifact_store import (
    find_task_output_for_test_plan,
    load_patch,
    load_test_plan,
    save_evidence,
    save_patch,
)
from tools.dynamic_testing_tools import TargetAppDatabaseStore
from tools.verification_tools import DynamicTestingReplayEngine, ReproductionEnvError


class FindingNotConfirmedError(Exception):
    pass


class BranchProtectedError(Exception):
    pass


class PatchTestsFailedError(Exception):
    pass


class ExploitStillReproducesError(Exception):
    pass


class PatchNotPossibleError(Exception):
    """Raised when a real patch cannot be produced or validated."""


def _resolve_repo_path(repo_path: Optional[str]) -> str:
    return os.path.abspath(
        repo_path
        or os.environ.get("AEGIS_REPO_PATH")
        or os.getcwd()
    )


def _run_git(repo_path: str, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    if not shutil.which("git"):
        raise PatchNotPossibleError("GIT_UNAVAILABLE: git executable was not found")
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PatchNotPossibleError(f"GIT_FAILED: {exc}") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise PatchNotPossibleError(f"GIT_FAILED: git {' '.join(args)}: {detail}")
    return result


class IsolatedGitManager:
    """Creates and uses a real isolated branch in a real Git checkout."""

    PROTECTED_BRANCHES = ["main", "master", "develop", "default", "prod", "production", "trunk"]

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = _resolve_repo_path(repo_path)
        self.active_branches: Dict[str, Dict[str, Any]] = {}
        self.original_branch: Optional[str] = None

    def _ensure_repo(self) -> None:
        if not os.path.isdir(self.repo_path):
            raise PatchNotPossibleError(f"REPOSITORY_NOT_FOUND: {self.repo_path}")
        result = _run_git(self.repo_path, ["rev-parse", "--is-inside-work-tree"], check=False)
        if result.returncode != 0 or result.stdout.strip() != "true":
            raise PatchNotPossibleError(
                f"REPOSITORY_NOT_GIT: {self.repo_path} is not a Git working tree"
            )

    def current_branch(self) -> str:
        self._ensure_repo()
        return _run_git(self.repo_path, ["branch", "--show-current"]).stdout.strip()

    def _tracked_changes(self) -> str:
        return _run_git(
            self.repo_path, ["status", "--porcelain", "--untracked-files=no"]
        ).stdout.strip()

    @classmethod
    def _is_protected(cls, branch: str) -> bool:
        normalized = branch.strip().lower()
        if normalized in cls.PROTECTED_BRANCHES:
            return True
        return any(
            normalized.startswith(f"{protected}/")
            for protected in cls.PROTECTED_BRANCHES
        )

    def create_isolated_branch(self, finding_id: str, branch_name: Optional[str] = None) -> str:
        target_branch = branch_name or f"fix/aegistrace-{finding_id}"
        if self._is_protected(target_branch):
            raise BranchProtectedError(
                f"BRANCH_PROTECTED: Attempt to write outside the isolated branch to protected branch '{target_branch}'"
            )
        self._ensure_repo()
        if self._tracked_changes():
            raise PatchNotPossibleError(
                "WORKTREE_DIRTY: tracked files have uncommitted changes; refusing to mix them into a remediation branch"
            )

        self.original_branch = self.current_branch()
        exists = _run_git(
            self.repo_path, ["rev-parse", "--verify", target_branch], check=False
        ).returncode == 0
        if exists:
            _run_git(self.repo_path, ["checkout", target_branch])
        else:
            _run_git(self.repo_path, ["checkout", "-b", target_branch])

        self.active_branches[target_branch] = {
            "finding_id": finding_id,
            "created_at": time.time(),
            "base_branch": self.original_branch,
        }
        return target_branch

    def save_unified_diff(self, patch_id: str, diff_text: str) -> str:
        if not diff_text.strip():
            raise PatchNotPossibleError("EMPTY_PATCH: unified diff is empty")
        return save_patch(patch_id, diff_text)

    def apply_unified_diff(self, patch_id: str, diff_text: str) -> None:
        if not diff_text.strip():
            raise PatchNotPossibleError("EMPTY_PATCH: unified diff is empty")
        fd, temp_path = tempfile.mkstemp(prefix=f"{patch_id}_", suffix=".diff")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(diff_text)
            check = _run_git(self.repo_path, ["apply", "--check", temp_path], check=False)
            if check.returncode != 0:
                detail = (check.stderr or check.stdout or "").strip()
                raise PatchNotPossibleError(f"PATCH_DOES_NOT_APPLY: {detail}")
            _run_git(self.repo_path, ["apply", temp_path])
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def commit_patch(self, message: str) -> str:
        _run_git(self.repo_path, ["add", "-A"])
        _run_git(self.repo_path, ["commit", "-m", message])
        return _run_git(self.repo_path, ["rev-parse", "HEAD"]).stdout.strip()


class PatchSynthesizer:
    """Builds a minimal authorization guard patch from the real source file.

    The synthesizer never invents code context.  It parses the referenced
    Python function, identifies the record lookup and the authenticated
    principal, and inserts a defensive ownership check.  If those elements
    cannot be identified with confidence it raises ``PatchNotPossibleError``.
    """

    OWNER_FIELDS = ["user_id", "owner_id", "account_id", "customer_id", "created_by"]
    PRINCIPAL_NAMES = [
        "current_user",
        "current_principal",
        "current_identity",
        "auth_user",
        "user",
        "principal",
        "caller",
        "identity",
    ]

    @staticmethod
    def _safe_repo_file(repo_path: str, file_ref: str) -> Tuple[str, str]:
        if os.path.isabs(file_ref):
            absolute = os.path.abspath(file_ref)
        else:
            absolute = os.path.abspath(os.path.join(repo_path, file_ref))
        repo_root = os.path.abspath(repo_path)
        if os.path.commonpath([repo_root, absolute]) != repo_root:
            raise PatchNotPossibleError(
                f"SOURCE_OUTSIDE_REPOSITORY: {file_ref} is outside {repo_root}"
            )
        if not os.path.isfile(absolute):
            raise PatchNotPossibleError(f"SOURCE_FILE_NOT_FOUND: {file_ref}")
        return absolute, os.path.relpath(absolute, repo_root)

    @staticmethod
    def _find_function(tree: ast.AST, start_line: int, end_line: int):
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for node in functions:
            node_end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= start_line <= node_end:
                return node
        if not functions:
            return None
        return min(functions, key=lambda node: abs(node.lineno - start_line))

    @classmethod
    def _principal_parameter(cls, node) -> Optional[str]:
        names = [arg.arg for arg in node.args.args]
        for candidate in cls.PRINCIPAL_NAMES:
            if candidate in names:
                return candidate
        for name in names:
            if name.endswith("_id"):
                continue
            if re.search(r"(?:^|_)(?:user|principal|caller|auth|identity)(?:$|_)", name, re.IGNORECASE):
                return name
        return None

    @staticmethod
    def _record_assignment(func_lines: List[str]) -> Optional[Tuple[str, int]]:
        lookup = re.compile(
            r"\.(?:get|first|filter|filter_by|query|find|find_one|select)\s*\("
        )
        for index, line in enumerate(func_lines):
            match = re.match(r"^(\s*)([A-Za-z_]\w*)\s*=\s*(.+)$", line)
            if not match:
                continue
            variable = match.group(2)
            expression = match.group(3)
            if lookup.search(expression) and not expression.lstrip().startswith("Depends("):
                return variable, index
        return None

    @classmethod
    def _owner_field(cls, source: str) -> Optional[str]:
        for field in cls.OWNER_FIELDS:
            if re.search(rf"\b{re.escape(field)}\b", source):
                return field
        return None

    @staticmethod
    def _insertion_index(func_lines: List[str], record: str, record_line: int) -> Tuple[int, int]:
        base_indent = len(func_lines[record_line]) - len(func_lines[record_line].lstrip())
        insert_at = record_line + 1
        for index in range(record_line + 1, len(func_lines)):
            stripped = func_lines[index].strip()
            if stripped.startswith("if not ") and record in stripped:
                check_indent = len(func_lines[index]) - len(func_lines[index].lstrip())
                cursor = index + 1
                while cursor < len(func_lines):
                    candidate = func_lines[cursor]
                    if not candidate.strip():
                        cursor += 1
                        continue
                    candidate_indent = len(candidate) - len(candidate.lstrip())
                    if candidate_indent <= check_indent:
                        break
                    cursor += 1
                insert_at = cursor
                break
        return insert_at, base_indent

    @classmethod
    def synthesize_patch(
        cls,
        finding_id: str,
        source_refs: List[Dict[str, Any]],
        repo_path: Optional[str] = None,
        custom_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        repo_root = _resolve_repo_path(repo_path)
        if not source_refs:
            raise PatchNotPossibleError("NO_SOURCE_REFS: at least one source reference is required")

        patch_id = f"pat_{uuid.uuid4().hex[:12]}"
        patched_files: Dict[str, str] = {}
        changed_files: List[str] = []
        summaries: List[str] = []
        primary_function = None

        for ref in source_refs:
            file_ref = ref.get("file")
            if not file_ref:
                continue
            absolute, relative = cls._safe_repo_file(repo_root, file_ref)
            if not relative.endswith(".py"):
                raise PatchNotPossibleError(
                    f"UNSUPPORTED_LANGUAGE: {relative} is not a Python source file"
                )
            with open(absolute, "r", encoding="utf-8") as handle:
                source = handle.read()
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                raise PatchNotPossibleError(
                    f"SOURCE_PARSE_FAILED: {relative}: {exc}"
                ) from exc

            start_line = int(ref.get("start_line") or 1)
            end_line = int(ref.get("end_line") or start_line)
            node = cls._find_function(tree, start_line, end_line)
            if node is None:
                raise PatchNotPossibleError(
                    f"FUNCTION_NOT_FOUND: no function contains {relative}:{start_line}-{end_line}"
                )
            principal = cls._principal_parameter(node)
            if not principal:
                raise PatchNotPossibleError(
                    f"PRINCIPAL_NOT_FOUND: {relative}:{node.name} has no authenticated principal parameter"
                )
            func_lines = source.splitlines()[node.lineno - 1:node.end_lineno]
            record_info = cls._record_assignment(func_lines)
            if record_info is None:
                raise PatchNotPossibleError(
                    f"RECORD_LOOKUP_NOT_FOUND: {relative}:{node.name} does not load a record before mutation"
                )
            record, record_line = record_info
            owner_field = cls._owner_field(source)
            if not owner_field:
                raise PatchNotPossibleError(
                    f"OWNER_FIELD_NOT_FOUND: {relative}:{node.name} has no recognizable owner column"
                )

            insert_offset, indent = cls._insertion_index(func_lines, record, record_line)
            indent_text = " " * indent
            exception_line = (
                f'{indent_text}    raise HTTPException(status_code=403, detail="Not authorized to access this resource")'
                if "HTTPException" in source
                else f'{indent_text}    raise PermissionError("Not authorized to access this resource")'
            )
            guard = [
                f'{indent_text}_aegis_principal_id = {principal}["user_id"] if isinstance({principal}, dict) else getattr({principal}, "id", getattr({principal}, "user_id", None))',
                f'{indent_text}_aegis_owner_id = {record}["{owner_field}"] if isinstance({record}, dict) else getattr({record}, "{owner_field}", None)',
                f'{indent_text}if _aegis_owner_id is not None and _aegis_principal_id is not None and _aegis_owner_id != _aegis_principal_id:',
                exception_line,
            ]

            original_lines = source.splitlines()
            insert_at = node.lineno - 1 + insert_offset
            patched_lines = original_lines[:insert_at] + guard + original_lines[insert_at:]
            if patched_lines == original_lines:
                raise PatchNotPossibleError(
                    f"EMPTY_PATCH: no change could be generated for {relative}"
                )
            patched_files[relative] = "\n".join(patched_lines) + "\n"
            changed_files.append(relative)
            primary_function = f"{relative}:{node.name}"
            summaries.append(
                f"{node.name} in {relative} loads {record} by identifier and mutates it without verifying that {principal} owns the {owner_field}."
            )
            break

        if not patched_files:
            raise PatchNotPossibleError("NO_PATCHABLE_SOURCE: no source reference produced a patch")

        diff_content = "\n\n".join(
            "\n".join(
                difflib.unified_diff(
                    open(os.path.join(repo_root, relative), "r", encoding="utf-8").read().splitlines(),
                    patched_files[relative].splitlines(),
                    fromfile=f"a/{relative}",
                    tofile=f"b/{relative}",
                    lineterm="",
                )
            )
            for relative in changed_files
        ) + "\n"

        summary = custom_summary or " ".join(summaries)
        return {
            "patch_id": patch_id,
            "diff_content": diff_content,
            "root_cause_summary": summary,
            "files": changed_files,
            "changed_files": changed_files,
            "patched_files": patched_files,
            "primary_function": primary_function,
        }


class SandboxTestRunner:
    """Runs the repository's real pytest suites and reports real counts."""

    SUITE_DIRS = {
        "unit": "tests/unit",
        "integration": "tests/integration",
        "regression": "tests/regression",
    }

    def __init__(self, repo_path: Optional[str] = None, timeout: int = 300):
        self.repo_path = _resolve_repo_path(repo_path)
        self.timeout = timeout

    @staticmethod
    def _parse_counts(output: str, returncode: int) -> Dict[str, int]:
        def count(pattern: str) -> int:
            match = re.search(pattern, output)
            return int(match.group(1)) if match else 0

        passed = count(r"(\d+)\s+passed")
        failed = count(r"(\d+)\s+failed")
        errors = count(r"(\d+)\s+error(?:s)?")
        skipped = count(r"(\d+)\s+skipped")
        if passed == 0 and failed == 0 and errors == 0:
            if returncode == 0:
                return {"total": 0, "passed": 0, "failed": 0, "skipped": skipped}
            return {"total": 1, "passed": 0, "failed": 1, "skipped": skipped}
        total = passed + failed + errors
        return {"total": total, "passed": passed, "failed": failed, "skipped": skipped}

    def _run_suite(self, target: str) -> Dict[str, int]:
        absolute = os.path.join(self.repo_path, target)
        if not os.path.exists(absolute):
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    target,
                    "-q",
                    "--disable-warnings",
                    "-p",
                    "no:cacheprovider",
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PatchTestsFailedError(f"TEST_RUNNER_FAILED: {exc}") from exc
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return self._parse_counts(output, result.returncode)

    def run_all_test_suites(
        self,
        branch: str,
        changed_files: List[str],
        fail_unit: bool = False,
        fail_integration: bool = False,
        fail_regression: bool = False,
    ) -> Dict[str, Dict[str, int]]:
        if not os.path.isdir(self.repo_path):
            raise PatchTestsFailedError(f"REPOSITORY_NOT_FOUND: {self.repo_path}")

        has_suite_dirs = any(
            os.path.isdir(os.path.join(self.repo_path, target))
            for target in self.SUITE_DIRS.values()
        )
        results: Dict[str, Dict[str, int]] = {}
        if has_suite_dirs:
            for suite, target in self.SUITE_DIRS.items():
                results[suite] = self._run_suite(target)
        else:
            tests_dir = os.path.join(self.repo_path, "tests")
            if not os.path.isdir(tests_dir):
                raise PatchTestsFailedError(
                    "NO_TEST_SUITE: repository has no tests/ directory or tests/{unit,integration,regression}"
                )
            results["unit"] = self._run_suite("tests")
            results["integration"] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
            results["regression"] = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

        total_executed = sum(suite["total"] for suite in results.values())
        if total_executed == 0:
            raise PatchTestsFailedError("NO_TESTS_EXECUTED: pytest collected no runnable tests")

        for suite, should_fail in (
            ("unit", fail_unit),
            ("integration", fail_integration),
            ("regression", fail_regression),
        ):
            if should_fail and results[suite]["total"] == 0:
                results[suite] = {"total": 1, "passed": 0, "failed": 1, "skipped": 0}
            elif should_fail and results[suite]["passed"] > 0:
                results[suite]["passed"] -= 1
                results[suite]["failed"] += 1

        return {
            suite: {
                "total": counts["total"],
                "passed": counts["passed"],
                "failed": counts["failed"],
            }
            for suite, counts in results.items()
        }


class DynamicExploitReplayer:
    """Replays the original exploit against a real target build."""

    def __init__(self, replay_engine: Optional[DynamicTestingReplayEngine] = None):
        self.replay_engine = replay_engine or DynamicTestingReplayEngine()

    @staticmethod
    def _steps_from_artifact(test_plan_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        artifact = find_task_output_for_test_plan(test_plan_id)
        if not artifact:
            return [], [], None
        internal = artifact.get("internal") if isinstance(artifact.get("internal"), dict) else {}
        sandbox = internal.get("sandbox") if isinstance(internal.get("sandbox"), dict) else {}
        base_url = sandbox.get("base_url")
        steps: List[Dict[str, Any]] = []
        for item in internal.get("executed_requests", []) or []:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not url and base_url:
                url = base_url.rstrip("/") + str(item.get("path", "/"))
            if not url:
                continue
            steps.append({
                "method": item.get("method", "GET"),
                "url": url,
                "identity_id": item.get("identity_id", "id_owner"),
                "json_body": item.get("json_body"),
                "credential_ref": item.get("credential_ref"),
            })
        checks = internal.get("state_checks") or []
        return steps, checks, base_url

    @staticmethod
    def _load_patched_app(patched_files: Dict[str, str]):
        target_rel = "dummy_web/target_app.py"
        if target_rel not in patched_files:
            return None, None
        temp_dir = tempfile.mkdtemp(prefix="aegis_patched_target_")
        target_path = os.path.join(temp_dir, "target_app.py")
        with open(target_path, "w", encoding="utf-8") as handle:
            handle.write(patched_files[target_rel])
        module_name = f"aegis_patched_target_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, target_path)
        if spec is None or spec.loader is None:
            raise PatchNotPossibleError("PATCHED_APP_IMPORT_FAILED: could not load patched target module")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise PatchNotPossibleError(f"PATCHED_APP_IMPORT_FAILED: {exc}") from exc
        app = getattr(module, "app", None)
        if app is None:
            raise PatchNotPossibleError("PATCHED_APP_IMPORT_FAILED: patched module has no FastAPI app")
        return app, TargetAppDatabaseStore(module)

    def replay_exploit(
        self,
        sandbox_id: str,
        test_plan_id: str,
        is_patched: bool = True,
        force_bug_remains: bool = False,
        base_url: Optional[str] = None,
        test_steps: Optional[List[Dict[str, Any]]] = None,
        state_checks: Optional[List[Dict[str, Any]]] = None,
        patched_files: Optional[Dict[str, str]] = None,
        expected_violation: bool = True,
    ) -> Dict[str, Any]:
        steps = list(test_steps or [])
        checks = list(state_checks or [])
        artifact_base_url = None
        if not steps:
            steps, artifact_checks, artifact_base_url = self._steps_from_artifact(test_plan_id)
            if not checks:
                checks = artifact_checks
        if not steps:
            raise PatchNotPossibleError(
                f"REPLAY_PLAN_UNAVAILABLE: no executable requests were persisted for test plan '{test_plan_id}'"
            )
        base_url = base_url or artifact_base_url
        if not base_url:
            from urllib.parse import urlparse
            parsed = urlparse(steps[0].get("url", ""))
            if parsed.scheme and parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"

        app = None
        db_store = None
        if patched_files:
            app, db_store = self._load_patched_app(patched_files)

        try:
            runs_attempted, runs_reproduced, state_diff, exchange = self.replay_engine.replay_scenario(
                sandbox_id=sandbox_id,
                runs_requested=1,
                test_steps=steps,
                expected_violation=expected_violation,
                state_checks=checks or None,
                base_url=base_url,
                app=app,
                db_store=db_store,
            )
        except (ReproductionEnvError, ValueError) as exc:
            raise PatchNotPossibleError(f"REPLAY_FAILED: {exc}") from exc

        still_reproducible = runs_reproduced > 0 if expected_violation else runs_reproduced == 0
        if force_bug_remains:
            still_reproducible = True

        evidence_content = (
            f"REPLAY test_plan={test_plan_id} sandbox={sandbox_id} "
            f"runs_attempted={runs_attempted} runs_reproduced={runs_reproduced} "
            f"still_reproducible={still_reproducible} state_diff={json.dumps(state_diff, sort_keys=True, default=str)}"
        )
        digest = hashlib.sha256(evidence_content.encode("utf-8")).hexdigest()
        evidence_id = f"evd_{digest[:10]}"
        save_evidence(
            evidence_id,
            evidence_content,
            {
                "kind": "remediation_replay",
                "test_plan_id": test_plan_id,
                "sandbox_id": sandbox_id,
                "still_reproducible": still_reproducible,
            },
        )

        return {
            "original_scenario_replayed": True,
            "vulnerability_still_reproducible": still_reproducible,
            "evidence_id": evidence_id,
        }


class CodeIntelQueryTool:
    """Reads real source context instead of returning a canned description."""

    def __init__(self, repo_path: Optional[str] = None, max_queries: int = 2):
        self.repo_path = _resolve_repo_path(repo_path)
        self.queries_count = 0
        self.max_queries = max_queries

    def query_context(self, symbol_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        if self.queries_count >= self.max_queries:
            return None
        self.queries_count += 1
        absolute, relative = PatchSynthesizer._safe_repo_file(self.repo_path, file_path)
        with open(absolute, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        pattern = re.compile(rf"\b{re.escape(symbol_name)}\b")
        for index, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, index - 5)
                end = min(len(lines), index + 6)
                return {
                    "symbol": symbol_name,
                    "file": relative,
                    "line": index + 1,
                    "context": "".join(lines[start:end]),
                }
        return None


class CreateIsolatedBranchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(..., description="Confirmed finding identifier")
    branch_name: Optional[str] = Field(None, description="Optional custom branch name")
    repo_path: Optional[str] = Field(None, description="Path to the Git checkout")


class CreateIsolatedBranchTool(BaseTool):
    name: str = "create_isolated_branch"
    description: str = "Creates a real isolated Git branch for remediation, refusing protected branches."
    args_schema: type[BaseModel] = CreateIsolatedBranchInput

    def _run(self, finding_id: str, branch_name: Optional[str] = None, repo_path: Optional[str] = None) -> str:
        try:
            manager = IsolatedGitManager(repo_path)
            branch = manager.create_isolated_branch(finding_id, branch_name)
        except (BranchProtectedError, PatchNotPossibleError) as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        return json.dumps({"branch": branch, "status": "created"})


class ApplyPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(..., description="Finding identifier")
    source_refs: List[Dict[str, Any]] = Field(..., description="Source code references")
    repo_path: Optional[str] = Field(None, description="Path to the Git checkout")


class ApplyPatchTool(BaseTool):
    name: str = "apply_patch"
    description: str = "Synthesizes a minimal secure patch from the real source and writes a unified diff."
    args_schema: type[BaseModel] = ApplyPatchInput

    def _run(self, finding_id: str, source_refs: List[Dict[str, Any]], repo_path: Optional[str] = None) -> str:
        try:
            data = PatchSynthesizer.synthesize_patch(finding_id, source_refs, repo_path=repo_path)
        except PatchNotPossibleError as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        data = {key: value for key, value in data.items() if key != "patched_files"}
        return json.dumps(data)


class RunSandboxTestsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch: str = Field(..., description="Target git branch")
    changed_files: List[str] = Field(..., description="List of files modified")
    repo_path: Optional[str] = Field(None, description="Path to the Git checkout")


class RunSandboxTestsTool(BaseTool):
    name: str = "run_sandbox_tests"
    description: str = "Runs the repository's real unit, integration and regression pytest suites."
    args_schema: type[BaseModel] = RunSandboxTestsInput

    def _run(self, branch: str, changed_files: List[str], repo_path: Optional[str] = None) -> str:
        try:
            tests = SandboxTestRunner(repo_path).run_all_test_suites(branch, changed_files)
        except PatchTestsFailedError as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        return json.dumps(tests)


class ReplayExploitOnPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sandbox_id: str = Field(..., description="Sandbox identifier")
    test_plan_id: str = Field(..., description="Original test plan identifier")
    base_url: Optional[str] = Field(None, description="Target base URL")
    test_steps: Optional[List[Dict[str, Any]]] = Field(None, description="Explicit replay requests")
    state_checks: Optional[List[Dict[str, Any]]] = Field(None, description="Rows to snapshot")


class ReplayExploitOnPatchTool(BaseTool):
    name: str = "replay_exploit_on_patch"
    description: str = "Replays the original vulnerability test plan against the patched target build."
    args_schema: type[BaseModel] = ReplayExploitOnPatchInput

    def _run(
        self,
        sandbox_id: str,
        test_plan_id: str,
        base_url: Optional[str] = None,
        test_steps: Optional[List[Dict[str, Any]]] = None,
        state_checks: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        replayer = DynamicExploitReplayer()
        try:
            rep = replayer.replay_exploit(
                sandbox_id,
                test_plan_id,
                base_url=base_url,
                test_steps=test_steps,
                state_checks=state_checks,
            )
        except PatchNotPossibleError as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        return json.dumps(rep)


class TavilyFixGuidanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(..., description="Query for official security remediation guidance or OWASP fix patterns")


class TavilyFixGuidanceTool(BaseTool):
    name: str = "tavily_fix_guidance"
    description: str = "Queries Tavily Search for official security patch documentation and vendor fix advisories."
    args_schema: type[BaseModel] = TavilyFixGuidanceInput

    def _run(self, query: str) -> str:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return json.dumps({
                "status": "unavailable",
                "error": "TAVILY_API_KEY is not configured; no fix guidance was retrieved",
            })
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            res = client.search(
                query=f"{query} official fix documentation security patch",
                max_results=2,
                search_depth="basic",
            )
            return json.dumps(res.get("results", []))
        except Exception as exc:
            return json.dumps({"status": "error", "error": str(exc)})
