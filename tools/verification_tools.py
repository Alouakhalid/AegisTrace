import os
import re
import json
import uuid
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

from tools.artifact_store import load_evidence, save_evidence
from tools.dynamic_testing_tools import (
    SandboxController,
    HTTPXScopedClient,
    StateDiffEngine,
    DBSnapshotHelper,
    ScopeGateError,
    SandboxHealthError,
    SnapshotError,
)


class EvidenceHashMismatchError(Exception):
    pass


class ReproductionEnvError(Exception):
    pass


class InsufficientEvidenceError(Exception):
    pass


class EvidenceStore:
    """Evidence store backed by the persistent artifact store.

    Records are written to disk when registered and can be re-read by another
    process (for example Verification after Dynamic Testing).  Hash
    verification always recomputes SHA-256 from the content; it never trusts a
    stored boolean.
    """

    def __init__(self):
        self._records: Dict[str, Dict[str, Any]] = {}

    def register_evidence(self, evidence_id: str, content: str, source_type: str = "sandbox_replay", metadata: Optional[Dict[str, Any]] = None) -> str:
        prohibited_sources = ["tavily", "search", "web_search", "external_search", "google", "bing"]
        if source_type.lower() in prohibited_sources:
            raise ValueError("Tavily and web search results cannot be accepted as vulnerability evidence")
        sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = {
            "evidence_id": evidence_id,
            "content": content,
            "sha256": sha256_hash,
            "source_type": source_type,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self._records[evidence_id] = record
        save_evidence(evidence_id, content, {"source_type": source_type, **(metadata or {})})
        return sha256_hash

    def _load(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        record = self._records.get(evidence_id)
        if record:
            return record
        persisted = load_evidence(evidence_id)
        if persisted:
            self._records[evidence_id] = {
                "evidence_id": evidence_id,
                "content": persisted.get("content", ""),
                "sha256": persisted.get("sha256", ""),
                "source_type": persisted.get("metadata", {}).get("source_type", "sandbox_replay"),
                "metadata": persisted.get("metadata", {}),
                "timestamp": persisted.get("timestamp", time.time()),
            }
            return self._records[evidence_id]
        return None

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        return self._load(evidence_id)

    def verify_evidence_hash(self, evidence_id: str, expected_hash: Optional[str] = None) -> Tuple[bool, str]:
        record = self._load(evidence_id)
        if not record:
            return False, f"Evidence record {evidence_id} not found in store"
        actual_hash = hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
        if record.get("sha256") != actual_hash:
            return False, f"Evidence {evidence_id} internal SHA-256 mismatch"
        if expected_hash and actual_hash != expected_hash:
            return False, f"Evidence {evidence_id} hash does not match expected SHA-256"
        return True, actual_hash

    def count(self) -> int:
        return len(self._records)


class TriageValidationSkill:
    @staticmethod
    def evaluate_triage_gates(
        target_url: str,
        runs_reproduced: int,
        state_diff_detected: bool,
        is_business_logic_intended: bool,
        allowed_hosts: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        rejection_reasons: List[str] = []
        parsed = urlparse(target_url or "")
        host = (parsed.hostname or "").lower()
        if not host:
            rejection_reasons.append("Target endpoint is not a valid absolute URL")
        elif allowed_hosts:
            def host_ok(candidate: str, allowed: str) -> bool:
                allowed = allowed.strip().lower()
                if allowed.startswith("*."):
                    suffix = allowed[2:]
                    return bool(suffix) and candidate.endswith(f".{suffix}") and candidate != suffix
                return candidate == allowed
            if not any(host_ok(host, h) for h in allowed_hosts):
                rejection_reasons.append("Target endpoint is outside authorized assessment scope")
        if runs_reproduced == 0:
            rejection_reasons.append("Hypothesis could not be reproduced across any sandbox execution runs")
        if not state_diff_detected:
            rejection_reasons.append("No security impact or unauthorized state mutation observed")
        if is_business_logic_intended:
            rejection_reasons.append("Observed behavior is expected business logic for authenticated principal")
        passed = len(rejection_reasons) == 0
        return passed, rejection_reasons


class InvariantEvaluator:
    @staticmethod
    def evaluate(invariant_statement: str, state_diff: Optional[Dict[str, Any]], exchange: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        if not state_diff:
            return False, "No state diff provided to prove invariant violation"
        mutations = state_diff.get("mutations", [])
        if not mutations:
            return False, "Database state diff contains zero mutations; security invariant intact"

        stmt_lower = (invariant_statement or "").lower()
        tokens = set(re.findall(r"[a-z0-9_]+", stmt_lower))

        def mentions(value: str) -> bool:
            value = (value or "").lower()
            if not value:
                return False
            singular = value[:-1] if value.endswith("s") else value
            return value in tokens or singular in tokens or value in stmt_lower

        relevant = []
        for mutation in mutations:
            table = mutation.get("table", "")
            column_diff = mutation.get("column_diff", {}) or {}
            if mentions(table) or any(mentions(col) for col in column_diff):
                relevant.append(mutation)

        if not relevant:
            tables = ", ".join(sorted({m.get("table", "?") for m in mutations}))
            return False, (
                "Observed mutations in "
                + tables
                + " do not match any entity named in the invariant statement"
            )

        mutation = relevant[0]
        return True, (
            f"Invariant violated: unauthorized mutation detected on table "
            f"{mutation.get('table')} row {mutation.get('row_id')}"
        )


class CVSSCalculatorEngine:
    """Computes a CVSS v3.1 base score from observed evidence.

    The impact metrics are selected from the columns that actually changed
    (financial, medical, identity or generic state).  The score is then
    computed with the official CVSS v3.1 base formula instead of a hardcoded
    table value.
    """

    @staticmethod
    def _impact_from_evidence(state_diff: Optional[Dict[str, Any]], category: str) -> Tuple[str, str, str]:
        changed_columns = set()
        tables = set()
        for mutation in (state_diff or {}).get("mutations", []):
            tables.add(str(mutation.get("table", "")).lower())
            changed_columns.update(str(c).lower() for c in (mutation.get("column_diff", {}) or {}).keys())

        financial = {"balance", "amount", "transfer", "fee", "limit"}
        medical = {"medical_history", "prescription", "dosage", "diagnosis"}
        identity = {"email", "role", "password", "owner", "user_id"}

        if changed_columns & financial or tables & {"transfers", "accounts"}:
            return "H", "H", "N"
        if changed_columns & medical or tables & {"prescriptions", "patient_records"}:
            return "H", "H", "N"
        if changed_columns & identity or "authn" in category.lower():
            return "H", "H", "N"
        return "L", "H", "N"

    @staticmethod
    def _base_score(av: str, ac: str, pr: str, ui: str, scope: str, c: str, i: str, a: str) -> float:
        weights = {
            "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
            "AC": {"L": 0.77, "H": 0.44},
            "PR": {"N": 0.85, "L": 0.62, "H": 0.27},
            "UI": {"N": 0.85, "R": 0.62},
            "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
        }
        pr_weight = weights["PR"][pr]
        if scope == "C":
            pr_weight = {"N": 0.85, "L": 0.68, "H": 0.5}[pr]
        iss = 1 - ((1 - weights["CIA"][c]) * (1 - weights["CIA"][i]) * (1 - weights["CIA"][a]))
        if scope == "U":
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
        exploitability = 8.22 * weights["AV"][av] * weights["AC"][ac] * pr_weight * weights["UI"][ui]
        if impact <= 0:
            return 0.0
        if scope == "U":
            return round(min(impact + exploitability, 10.0), 1)
        return round(min(1.08 * (impact + exploitability), 10.0), 1)

    @staticmethod
    def _level_for_score(score: float) -> str:
        if score == 0.0:
            return "informational"
        if score < 4.0:
            return "low"
        if score < 7.0:
            return "medium"
        if score < 9.0:
            return "high"
        return "critical"

    @staticmethod
    def calculate(category: str, invariant_violated: bool, state_diff: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not invariant_violated:
            return {
                "level": "informational",
                "cvss_score": 0.0,
                "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N",
                "rationale": "No invariant violation observed; zero security impact."
            }

        cat = (category or "").lower()
        if "idor" in cat or "broken_access_control" in cat:
            av, ac, pr, ui, scope = "N", "L", "L", "N", "U"
            base_rationale = "Authenticated non-owner can alter another principal's data"
        elif "authn_authz_flaw" in cat:
            av, ac, pr, ui, scope = "N", "L", "N", "N", "U"
            base_rationale = "Authentication or authorization control is missing"
        elif "business_logic" in cat:
            av, ac, pr, ui, scope = "N", "H", "L", "N", "U"
            base_rationale = "Business-logic sequence permits an unintended state transition"
        else:
            av, ac, pr, ui, scope = "N", "L", "L", "N", "U"
            base_rationale = "Access-control violation verified on the target endpoint"

        c, i, a = CVSSCalculatorEngine._impact_from_evidence(state_diff, cat)
        vector = f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{scope}/C:{c}/I:{i}/A:{a}"
        score = CVSSCalculatorEngine._base_score(av, ac, pr, ui, scope, c, i, a)
        return {
            "level": CVSSCalculatorEngine._level_for_score(score),
            "cvss_score": score,
            "cvss_vector": vector,
            "rationale": f"{base_rationale}; observed impact C:{c}/I:{i}/A:{a}.",
        }


class ConfidenceScorer:
    @staticmethod
    def score(reproduction_rate: float, evidence_integrity_ratio: float, has_state_diff: bool) -> float:
        weight_repro = 0.5 * max(0.0, min(1.0, reproduction_rate))
        weight_evidence = 0.3 * max(0.0, min(1.0, evidence_integrity_ratio))
        weight_diff = 0.2 if has_state_diff else 0.0
        total = weight_repro + weight_evidence + weight_diff
        return round(min(1.0, max(0.0, total)), 2)


class DynamicTestingReplayEngine:
    def __init__(self, sandbox_controller: Optional[SandboxController] = None):
        self.sandbox_controller = sandbox_controller or SandboxController()
        self.max_env_retries = 3

    def reset_sandbox_with_retry(self, sandbox_id: str) -> bool:
        for attempt in range(self.max_env_retries):
            success = self.sandbox_controller.reset_sandbox()
            if success:
                return True
            time.sleep(0.05 * (attempt + 1))
        return False

    @staticmethod
    def _infer_state_checks(test_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        checks: List[Dict[str, Any]] = []
        for step in test_steps:
            url = step.get("url", "")
            path = urlparse(url).path if "://" in url else url
            segments = [s for s in path.split("/") if s]
            table = None
            row_id = None
            for idx, segment in enumerate(segments):
                if segment.isdigit() or re.fullmatch(r"[0-9a-fA-F-]{8,}", segment):
                    row_id = int(segment) if segment.isdigit() else segment
                    for prev in reversed(segments[:idx]):
                        if not prev.isdigit() and prev not in {"api", "v1", "v2"}:
                            table = prev
                            break
                    break
            if table and row_id is not None:
                payload = step.get("json_payload", step.get("json_body")) or {}
                columns = list(payload.keys()) if isinstance(payload, dict) and payload else ["status"]
                checks.append({"table": table, "key": {"id": row_id}, "columns": columns})
        return checks

    def replay_scenario(
        self,
        sandbox_id: str,
        runs_requested: int,
        test_steps: List[Dict[str, Any]],
        expected_violation: bool = True,
        state_checks: Optional[List[Dict[str, Any]]] = None,
        base_url: Optional[str] = None,
        allowed_hosts: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        app: Optional[Any] = None,
        db_store: Optional[Any] = None,
    ) -> Tuple[int, int, Dict[str, Any], Dict[str, Any]]:
        if not test_steps:
            raise ValueError("replay_scenario requires at least one test step")

        checks = state_checks or self._infer_state_checks(test_steps)
        if not checks:
            raise ValueError(
                "replay_scenario requires state_checks; none could be inferred from the test steps"
            )

        first_url = test_steps[0].get("url", "")
        if not base_url:
            parsed = urlparse(first_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "http://127.0.0.1"
        host = urlparse(base_url).hostname
        methods = allowed_methods or sorted({str(s.get("method", "GET")).upper() for s in test_steps})
        client = HTTPXScopedClient(
            base_url=base_url,
            allowed_hosts=allowed_hosts or ([host] if host else None),
            allowed_methods=methods,
            app=app,
        )

        runs_attempted = 0
        runs_reproduced = 0
        last_state_diff: Dict[str, Any] = {}
        last_exchange: Dict[str, Any] = {}

        for run_idx in range(runs_requested):
            runs_attempted += 1
            if app is None and not self.reset_sandbox_with_retry(sandbox_id):
                raise ReproductionEnvError(
                    f"REPRODUCTION_ENV_FAILED: Sandbox {sandbox_id} could not be reset for clean rerun on attempt {run_idx + 1}"
                )
            try:
                snap_helper = DBSnapshotHelper(db_store) if db_store is not None else DBSnapshotHelper()
            except SnapshotError as exc:
                raise ReproductionEnvError(f"REPRODUCTION_ENV_FAILED: {exc}") from exc

            before = []
            for check in checks:
                snap_id, data = snap_helper.snapshot(check["table"], check["key"], check["columns"])
                before.append((check, snap_id, data))

            for step in test_steps:
                method = str(step.get("method", "GET")).upper()
                url = step.get("url", "")
                parsed = urlparse(url)
                path = parsed.path or "/"
                if parsed.query:
                    path = f"{path}?{parsed.query}"
                identity_id = step.get("identity_id", "id_owner")
                json_payload = step.get("json_payload", step.get("json_body"))
                headers = step.get("headers", {})
                try:
                    resp = client.execute(
                        method=method,
                        path=path,
                        identity_id=identity_id,
                        json_body=json_payload,
                        headers=headers,
                        credential_ref=step.get("credential_ref"),
                    )
                except (ScopeGateError, SandboxHealthError) as exc:
                    raise ReproductionEnvError(f"REPRODUCTION_ENV_FAILED: {exc}") from exc
                last_exchange = {
                    "method": method,
                    "url": url,
                    "identity_id": identity_id,
                    "request_headers": headers,
                    "request_body": json.dumps(json_payload) if json_payload else "",
                    "status_code": resp.get("status_code", 0),
                    "response_body": resp.get("response_excerpt", ""),
                    "evidence_id": resp.get("evidence_id"),
                }

            mutations = []
            for check, before_id, before_data in before:
                after_id, after_data = snap_helper.snapshot(check["table"], check["key"], check["columns"])
                diffs = StateDiffEngine.compute_diffs(
                    table=check["table"],
                    key=check["key"],
                    columns=check["columns"],
                    before_snapshot_id=before_id,
                    after_snapshot_id=after_id,
                    before_state=before_data,
                    after_state=after_data,
                )
                if diffs:
                    col_diff = {
                        d["column"]: {"before": str(d["before"]), "after": str(d["after"])}
                        for d in diffs
                    }
                    mutations.append({
                        "table": check["table"],
                        "row_id": str(check["key"].get("id", next(iter(check["key"].values()), ""))),
                        "operation": "UPDATE",
                        "column_diff": col_diff,
                    })

            last_state_diff = {"mutations": mutations}
            if expected_violation and mutations:
                runs_reproduced += 1
            elif not expected_violation and not mutations:
                runs_reproduced += 1

        return runs_attempted, runs_reproduced, last_state_diff, last_exchange


class VerifyEvidenceHashInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(..., description="ID of the evidence artifact to verify")
    expected_hash: Optional[str] = Field(None, description="Optional expected SHA-256 hash")


class VerifyEvidenceHashTool(BaseTool):
    name: str = "verify_evidence_hash"
    description: str = "Verifies the cryptographic SHA-256 hash of an evidence record in the evidence store."
    args_schema: type[BaseModel] = VerifyEvidenceHashInput

    def _run(self, evidence_id: str, expected_hash: Optional[str] = None) -> str:
        store = EvidenceStore()
        verified, detail = store.verify_evidence_hash(evidence_id, expected_hash)
        result = {"evidence_id": evidence_id, "verified": verified}
        if verified:
            result["sha256"] = detail
        else:
            result["error"] = detail
        return json.dumps(result)


class ReplayDynamicScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sandbox_id: str = Field(..., description="Identifier of the target sandbox")
    runs_requested: int = Field(..., description="Number of reproduction runs to execute")
    test_steps: List[Dict[str, Any]] = Field(..., description="List of test cases to replay")
    state_checks: Optional[List[Dict[str, Any]]] = Field(None, description="Database rows and columns to snapshot")
    base_url: Optional[str] = Field(None, description="Base URL of the sandbox application")
    allowed_hosts: Optional[List[str]] = Field(None, description="Hosts permitted by the scope gate")
    allowed_methods: Optional[List[str]] = Field(None, description="HTTP methods permitted by the scope gate")


class ReplayDynamicScenarioTool(BaseTool):
    name: str = "replay_dynamic_scenario"
    description: str = "Replays candidate exploit steps inside a clean sandbox environment."
    args_schema: type[BaseModel] = ReplayDynamicScenarioInput

    def _run(
        self,
        sandbox_id: str,
        runs_requested: int,
        test_steps: List[Dict[str, Any]],
        state_checks: Optional[List[Dict[str, Any]]] = None,
        base_url: Optional[str] = None,
        allowed_hosts: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
    ) -> str:
        engine = DynamicTestingReplayEngine()
        try:
            attempted, reproduced, diff, ex = engine.replay_scenario(
                sandbox_id,
                runs_requested,
                test_steps,
                state_checks=state_checks,
                base_url=base_url,
                allowed_hosts=allowed_hosts,
                allowed_methods=allowed_methods,
            )
        except (ReproductionEnvError, ValueError) as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        return json.dumps({"runs_attempted": attempted, "runs_reproduced": reproduced, "state_diff": diff})


class EvaluateInvariantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invariant_statement: str = Field(..., description="Security rule being tested")
    state_diff: Dict[str, Any] = Field(..., description="Observed database mutations")


class EvaluateInvariantTool(BaseTool):
    name: str = "evaluate_invariant"
    description: str = "Evaluates whether an observed database state diff breaches a specified security invariant."
    args_schema: type[BaseModel] = EvaluateInvariantInput

    def _run(self, invariant_statement: str, state_diff: Dict[str, Any]) -> str:
        violated, rationale = InvariantEvaluator.evaluate(invariant_statement, state_diff, None)
        return json.dumps({"invariant_violated": violated, "rationale": rationale})


class ComputeCVSSVectorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(..., description="Vulnerability category")
    invariant_violated: bool = Field(..., description="Whether invariant was breached")
    state_diff: Optional[Dict[str, Any]] = Field(None, description="Observed database mutations")


class ComputeCVSSVectorTool(BaseTool):
    name: str = "compute_cvss_vector"
    description: str = "Computes standard CVSS v3.1 vector string and numeric base score."
    args_schema: type[BaseModel] = ComputeCVSSVectorInput

    def _run(self, category: str, invariant_violated: bool, state_diff: Optional[Dict[str, Any]] = None) -> str:
        res = CVSSCalculatorEngine.calculate(category, invariant_violated, state_diff)
        return json.dumps(res)
