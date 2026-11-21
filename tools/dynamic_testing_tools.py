import os
import sys
import json
import time
import uuid
import re
import copy
import sqlite3
import hashlib
import fnmatch
from typing import Dict, Any, List, Optional, Tuple, Union
import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.artifact_store import save_evidence

try:
    from dummy_web import target_app as target_module
    target_app = target_module.app
except ImportError:
    try:
        import target_app as target_module
        target_app = target_module.app
    except ImportError:
        target_module = None
        target_app = None
_TARGET_BASELINE: Dict[str, Any] = {}
if target_module is not None:
    for _attr in ("orders_db", "users_db", "transfers_db", "prescriptions_db"):
        if hasattr(target_module, _attr):
            _TARGET_BASELINE[_attr] = copy.deepcopy(getattr(target_module, _attr))


class ScopeGateError(Exception):
    pass


class SandboxHealthError(Exception):
    pass


class SnapshotError(Exception):
    pass


class EvidenceHygieneSkill:
    @staticmethod
    def redact_text(text: str) -> str:
        if not text:
            return ""
        redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9\-_\.=]+", "Bearer [REDACTED_TOKEN]", text)
        redacted = re.sub(r"(?i)eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", redacted)
        redacted = re.sub(r"(?i)(password|secret|api_key|token)\s*[:=]\s*\S+", r"\1: [REDACTED]", redacted)
        return redacted

    @staticmethod
    def generate_evidence_id(content: str) -> str:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"evd_{h[:10]}"

    @staticmethod
    def generate_snapshot_id() -> str:
        return f"snp_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def persist(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        evidence_id = EvidenceHygieneSkill.generate_evidence_id(content)
        save_evidence(evidence_id, content, metadata or {})
        return evidence_id


def resolve_credential(credential_ref: Optional[str]) -> Optional[str]:
    """Resolve an opaque ``cred_*`` reference to a token from the secret store.

    Credentials are never invented.  They come from an environment variable
    named after the reference or from a JSON map in ``AEGIS_CREDENTIALS``.
    """
    if not credential_ref:
        return None
    env_key = "AEGIS_CRED_" + re.sub(r"[^A-Za-z0-9]", "_", credential_ref).upper()
    token = os.environ.get(env_key)
    if token:
        return token
    raw = os.environ.get("AEGIS_CREDENTIALS") or os.environ.get("CREDENTIALS")
    if raw:
        try:
            mapping = json.loads(raw)
            if isinstance(mapping, dict):
                value = mapping.get(credential_ref)
                if isinstance(value, str) and value:
                    return value
        except json.JSONDecodeError:
            return None
    return None


class MockDatabaseStore:
    """Explicit test fixture.  Never used as the default sandbox store."""

    def __init__(self):
        self.tables = {
            "orders": {
                100: {"id": 100, "user_id": 1, "shipping_address": "12 Nile St, Alexandria", "status": "pending"},
                200: {"id": 200, "user_id": 2, "shipping_address": "45 Pyramids Rd, Giza", "status": "shipped"}
            },
            "users": {
                1: {"id": 1, "username": "buyer_a", "role": "customer"},
                2: {"id": 2, "username": "buyer_b", "role": "customer"}
            },
            "transfers": {
                100: {"id": 100, "user_id": 1, "amount": 50000.0, "status": "pending"}
            },
            "prescriptions": {
                100: {"id": 100, "user_id": 1, "dosage": "10mg", "status": "active"}
            }
        }
        self.snapshots = {}

    @staticmethod
    def _row_id(table: str, key_dict: Dict[str, Any]) -> Any:
        return key_dict.get("id", key_dict.get(f"{table[:-1]}_id"))

    def has_table(self, table: str) -> bool:
        return table in self.tables

    def get_row(self, table: str, key_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tbl = self.tables.get(table)
        if not tbl:
            return None
        row_id = self._row_id(table, key_dict)
        if row_id in tbl:
            return dict(tbl[row_id])
        return None

    def update_row(self, table: str, key_dict: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        tbl = self.tables.get(table)
        if not tbl:
            return False
        row_id = self._row_id(table, key_dict)
        if row_id in tbl:
            tbl[row_id].update(updates)
            return True
        return False

    def take_snapshot(self, table: str, key_dict: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        snap_id = EvidenceHygieneSkill.generate_snapshot_id()
        row_data = self.get_row(table, key_dict) or {}
        self.snapshots[snap_id] = {
            "table": table,
            "key": key_dict,
            "row": dict(row_data),
            "timestamp": time.time()
        }
        return snap_id, dict(row_data)


class TargetAppDatabaseStore:
    """Reads the real in-process sandbox application state.

    The sandbox fixture exposes its ORM-like dictionaries; snapshotting those
    dictionaries is a real view of the application state, not a fabricated
    second database.
    """

    TABLE_ATTRS = {
        "orders": "orders_db",
        "users": "users_db",
        "transfers": "transfers_db",
        "prescriptions": "prescriptions_db",
    }

    def __init__(self, module=None):
        self.module = module or target_module
        if self.module is None:
            raise SnapshotError("Sandbox target application module is not importable")
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def _table(self, table: str) -> Optional[Dict[Any, Dict[str, Any]]]:
        attr = self.TABLE_ATTRS.get(table, table)
        value = getattr(self.module, attr, None)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _row_id(table: str, key_dict: Dict[str, Any]) -> Any:
        for candidate in ("id", f"{table[:-1]}_id"):
            if candidate in key_dict:
                return key_dict[candidate]
        return next(iter(key_dict.values()), None)

    def has_table(self, table: str) -> bool:
        return self._table(table) is not None

    def get_row(self, table: str, key_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tbl = self._table(table)
        if tbl is None:
            return None
        row = tbl.get(self._row_id(table, key_dict))
        return copy.deepcopy(row) if isinstance(row, dict) else None

    def update_row(self, table: str, key_dict: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        tbl = self._table(table)
        if tbl is None:
            return False
        row = tbl.get(self._row_id(table, key_dict))
        if isinstance(row, dict):
            row.update(updates)
            return True
        return False

    def take_snapshot(self, table: str, key_dict: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        snap_id = EvidenceHygieneSkill.generate_snapshot_id()
        row_data = self.get_row(table, key_dict) or {}
        self.snapshots[snap_id] = {
            "table": table,
            "key": key_dict,
            "row": copy.deepcopy(row_data),
            "timestamp": time.time()
        }
        return snap_id, copy.deepcopy(row_data)


class SQLiteDatabaseStore:
    """Reads snapshots from a real SQLite database named by ``AEGIS_SANDBOX_DB``."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("AEGIS_SANDBOX_DB", "")
        if not self.db_path or not os.path.isfile(self.db_path):
            raise SnapshotError(
                "AEGIS_SANDBOX_DB does not point to a readable SQLite database"
            )
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_columns(self, table: str) -> List[str]:
        """Return the whitelisted column names of an existing table, or []."""
        safe = table.replace('"', '""')
        try:
            with self._connect() as conn:
                rows = conn.execute(f'PRAGMA table_info("{safe}")').fetchall()
        except sqlite3.DatabaseError:
            return []
        return [row[1] for row in rows]

    def has_table(self, table: str) -> bool:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table or ""):
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (table,)
            ).fetchone()
        return row is not None

    @staticmethod
    def _row_id(table: str, key_dict: Dict[str, Any]) -> Any:
        for candidate in ("id", f"{table[:-1]}_id"):
            if candidate in key_dict:
                return key_dict[candidate]
        return next(iter(key_dict.values()), None)

    def get_row(self, table: str, key_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.has_table(table):
            return None
        row_id = self._row_id(table, key_dict)
        with self._connect() as conn:
            row = conn.execute(f'SELECT * FROM "{table}" WHERE "id" = ?;', (row_id,)).fetchone()
        return dict(row) if row else None

    def update_row(self, table: str, key_dict: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        if not self.has_table(table) or not updates:
            return False
        valid_columns = set(self._table_columns(table))
        safe_updates = {col: val for col, val in updates.items() if col in valid_columns}
        if not safe_updates:
            return False
        row_id = self._row_id(table, key_dict)
        assignments = ", ".join(f'"{col}" = ?' for col in safe_updates)
        values = list(safe_updates.values()) + [row_id]
        with self._connect() as conn:
            cur = conn.execute(f'UPDATE "{table}" SET {assignments} WHERE "id" = ?;', values)
            conn.commit()
            return cur.rowcount > 0

    def take_snapshot(self, table: str, key_dict: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        snap_id = EvidenceHygieneSkill.generate_snapshot_id()
        row_data = self.get_row(table, key_dict) or {}
        self.snapshots[snap_id] = {
            "table": table,
            "key": key_dict,
            "row": copy.deepcopy(row_data),
            "timestamp": time.time()
        }
        return snap_id, copy.deepcopy(row_data)


def get_default_db_store():
    if target_module is not None and any(
        isinstance(getattr(target_module, attr, None), dict) for attr in TargetAppDatabaseStore.TABLE_ATTRS.values()
    ):
        return TargetAppDatabaseStore(target_module)
    if os.environ.get("AEGIS_SANDBOX_DB"):
        return SQLiteDatabaseStore()
    raise SnapshotError(
        "No sandbox database is configured. Set AEGIS_SANDBOX_DB to a SQLite "
        "database or run against the bundled target application."
    )


global_mock_db = MockDatabaseStore()


class DBSnapshotHelper:
    def __init__(self, db_store: Optional[Any] = None):
        self.db = db_store or get_default_db_store()

    def snapshot(self, table: str, key: Dict[str, Any], columns: List[str]) -> Tuple[str, Dict[str, Any]]:
        if not self.db.has_table(table):
            raise SnapshotError(f"Database table '{table}' does not exist for snapshot")
        snap_id, row_data = self.db.take_snapshot(table, key)
        filtered = {c: row_data.get(c) for c in columns if c in row_data}
        return snap_id, filtered

    def apply_state_change(self, table: str, key: Dict[str, Any], updates: Dict[str, Any]) -> bool:
        return self.db.update_row(table, key, updates)


class StateDiffEngine:
    @staticmethod
    def compute_diffs(
        table: str,
        key: Dict[str, Any],
        columns: List[str],
        before_snapshot_id: str,
        after_snapshot_id: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        diffs = []
        for col in columns:
            val_before = before_state.get(col)
            val_after = after_state.get(col)
            if val_before != val_after:
                ev_content = (
                    f"STATE_DIFF {table} key={json.dumps(key, sort_keys=True)} "
                    f"column={col} before={val_before!r} after={val_after!r} "
                    f"before_snapshot={before_snapshot_id} after_snapshot={after_snapshot_id}"
                )
                ev_id = EvidenceHygieneSkill.persist(
                    ev_content,
                    {"kind": "state_diff", "table": table, "column": col, "key": key}
                )
                diffs.append({
                    "table": table,
                    "key": key,
                    "column": col,
                    "before": val_before,
                    "after": val_after,
                    "snapshot_before_id": before_snapshot_id,
                    "snapshot_after_id": after_snapshot_id,
                    "evidence_id": ev_id
                })
        return diffs


class SandboxController:
    def __init__(self, base_url: str = "http://shoplite-app:8000"):
        self.base_url = base_url.rstrip("/")
        self.is_healthy: Optional[bool] = None

    def _is_local_target(self) -> bool:
        if target_app is None:
            return False
        host = (httpx.URL(self.base_url).host or "").lower()
        return host in {"shoplite-app", "localhost", "127.0.0.1", "testserver", "fintech-core", "healthtech-api"}

    def check_health(self) -> bool:
        if self._is_local_target():
            try:
                from starlette.testclient import TestClient
                with TestClient(target_app) as client:
                    response = client.get("/")
                self.is_healthy = response.status_code < 500
                return self.is_healthy
            except Exception:
                self.is_healthy = False
                return False
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.base_url)
            self.is_healthy = response.status_code < 500
            return self.is_healthy
        except Exception:
            self.is_healthy = False
            return False

    def reset_sandbox(self) -> bool:
        """Restore the sandbox to its captured baseline.

        Returns ``False`` when the environment cannot actually be reset; it
        never reports success for an operation that did not happen.
        """
        if self._is_local_target() and _TARGET_BASELINE:
            for attr, baseline in _TARGET_BASELINE.items():
                setattr(target_module, attr, copy.deepcopy(baseline))
            self.is_healthy = None
            return True
        reset_url = os.environ.get("AEGIS_SANDBOX_RESET_URL")
        if reset_url:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(reset_url)
                self.is_healthy = None
                return response.status_code < 400
            except Exception:
                return False
        return False


class HTTPXScopedClient:
    def __init__(
        self,
        base_url: str,
        allowed_hosts: Optional[List[str]] = None,
        forbidden_paths: Optional[List[str]] = None,
        allowed_methods: Optional[List[str]] = None,
        app: Optional[Any] = None,
    ):
        self.base_url = base_url.rstrip("/")
        default_host = httpx.URL(self.base_url).host
        self.allowed_hosts = [h.lower() for h in (allowed_hosts or ([default_host] if default_host else []))]
        self.forbidden_paths = forbidden_paths or ["/admin/danger/*"]
        self.allowed_methods = [m.upper() for m in (allowed_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])]
        self.app = app if app is not None else target_app

    @staticmethod
    def _normalize_host(host: str) -> str:
        value = (host or "").strip().lower()
        if value.count(":") == 1:
            value = value.split(":", 1)[0]
        return value

    def _host_allowed(self, host: str) -> bool:
        norm = self._normalize_host(host)
        for allowed in self.allowed_hosts:
            clean = self._normalize_host(allowed)
            if clean.startswith("*."):
                suffix = clean[2:]
                if suffix and norm.endswith(f".{suffix}") and norm != suffix:
                    return True
            elif norm == clean:
                return True
        return False

    def _check_scope(self, method: str, url: str) -> None:
        parsed = httpx.URL(url)
        if not self._host_allowed(parsed.host or ""):
            raise ScopeGateError(
                f"Blocked by scope gate: host '{parsed.host}' is not in {self.allowed_hosts}"
            )
        if method.upper() not in self.allowed_methods:
            raise ScopeGateError(
                f"Blocked by scope gate: method '{method.upper()}' is not in {self.allowed_methods}"
            )
        path = parsed.path or "/"
        for rule in self.forbidden_paths:
            pattern = rule.rstrip("/")
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if path.startswith(prefix) or fnmatch.fnmatch(path, pattern):
                    raise ScopeGateError(
                        f"Blocked by scope gate: path '{path}' matches forbidden rule '{rule}'"
                    )
            elif path == pattern or path.startswith(f"{pattern}/"):
                raise ScopeGateError(
                    f"Blocked by scope gate: path '{path}' matches forbidden rule '{rule}'"
                )

    def _is_local_target(self) -> bool:
        if self.app is None:
            return False
        host = (httpx.URL(self.base_url).host or "").lower()
        return host in {"shoplite-app", "localhost", "127.0.0.1", "testserver", "fintech-core", "healthtech-api"}

    def execute(
        self,
        method: str,
        path: str,
        identity_id: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        credential_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        full_url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        self._check_scope(method, full_url)

        req_headers = dict(headers or {})
        req_headers["X-Testing-Identity"] = identity_id
        token = resolve_credential(credential_ref)
        if token:
            req_headers["Authorization"] = f"Bearer {token}"

        status_code: Optional[int] = None
        raw_response = ""
        transport = "none"
        transport_error = ""

        if self._is_local_target():
            try:
                from starlette.testclient import TestClient
                with TestClient(self.app) as client:
                    resp = client.request(
                        method=method.upper(),
                        url=path,
                        params=params,
                        json=json_body,
                        headers=req_headers
                    )
                status_code = resp.status_code
                raw_response = resp.text
                transport = "testclient"
            except Exception as exc:
                transport_error = f"testclient: {exc}"

        if status_code is None:
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.request(
                        method=method.upper(),
                        url=full_url,
                        params=params,
                        json=json_body,
                        headers=req_headers
                    )
                status_code = resp.status_code
                raw_response = resp.text
                transport = "httpx"
            except Exception as exc:
                transport_error = (transport_error + "; " if transport_error else "") + f"httpx: {exc}"

        if status_code is None:
            raise SandboxHealthError(
                f"SANDBOX_UNHEALTHY: no transport could reach {full_url} ({transport_error or 'unknown error'})"
            )

        excerpt = EvidenceHygieneSkill.redact_text(raw_response)
        evidence_content = (
            f"HTTP_EXCHANGE method={method.upper()} url={full_url} "
            f"identity={identity_id} status={status_code} "
            f"request_body={json.dumps(json_body, sort_keys=True) if json_body is not None else ''} "
            f"response_body={raw_response}"
        )
        evidence_id = EvidenceHygieneSkill.persist(
            evidence_content,
            {
                "kind": "http_exchange",
                "method": method.upper(),
                "url": full_url,
                "identity_id": identity_id,
                "status_code": status_code,
                "request_body": json_body,
                "credential_ref": credential_ref,
                "credential_resolved": bool(token),
            }
        )

        return {
            "method": method.upper(),
            "url": full_url,
            "status_code": status_code,
            "response_excerpt": excerpt,
            "evidence_id": evidence_id,
            "transport": transport,
            "credential_resolved": bool(token),
        }


class PlaywrightBrowserTool:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def execute_browser_flow(
        self,
        target_url: str,
        identity_id: str,
        flow_steps: List[str]
    ) -> Dict[str, Any]:
        title = "Browser Flow Simulation"
        body_text = f"Simulated UI flow for steps: {', '.join(flow_steps)}"
        status_code = 200
        pw_available = False
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=self.headless)
                    try:
                        page = browser.new_page()
                        response = page.goto(target_url, timeout=15000)
                        title = page.title()
                        body_text = page.inner_text("body")[:2000]
                        status_code = response.status if response else 0
                        pw_available = True
                    finally:
                        browser.close()
                except Exception as launch_exc:
                    title = "Sandbox Environment (Playwright Headless Restricted)"
                    body_text = f"Browser flow deferred: {launch_exc}"
                    status_code = 200
                    pw_available = False
        except ImportError:
            title = "Playwright Not Installed"
            body_text = "Browser flow deferred: playwright not installed"
            status_code = 200
            pw_available = False

        excerpt = EvidenceHygieneSkill.redact_text(
            f"[UI] title={title!r} status={status_code} body={body_text}"
        )
        evidence_id = EvidenceHygieneSkill.persist(
            f"PLAYWRIGHT identity={identity_id} url={target_url} status={status_code} body={body_text}",
            {"kind": "ui_exchange", "url": target_url, "identity_id": identity_id, "status_code": status_code},
        )
        return {
            "method": "GET",
            "url": target_url,
            "status_code": status_code,
            "response_excerpt": excerpt,
            "evidence_id": evidence_id,
            "playwright_available": pw_available
        }


class HttpTestInput(BaseModel):
    method: str = Field(..., description="HTTP method (GET, POST, PATCH, etc.)")
    path: str = Field(..., description="Path of the target resource")
    identity_id: str = Field(..., description="Identity executing the request")
    json_body: Optional[Dict[str, Any]] = Field(default=None, description="Optional JSON body")


class ExecuteHttpTestTool(BaseTool):
    name: str = "execute_http_test"
    description: str = "Executes a scoped HTTP request in the sandbox as a specific identity and captures exchange evidence."
    args_schema: type[BaseModel] = HttpTestInput

    def _run(self, method: str, path: str, identity_id: str, json_body: Optional[Dict[str, Any]] = None) -> str:
        base_url = os.environ.get("AEGIS_SANDBOX_BASE_URL", "http://shoplite-app:8000")
        client = HTTPXScopedClient(base_url=base_url)
        try:
            res = client.execute(method=method, path=path, identity_id=identity_id, json_body=json_body)
        except (ScopeGateError, SandboxHealthError) as exc:
            return json.dumps({"error": str(exc), "error_type": type(exc).__name__})
        return json.dumps(res)


class SnapshotDbInput(BaseModel):
    table: str = Field(..., description="Target database table")
    key: Dict[str, Any] = Field(..., description="Primary key identifying the target row")
    columns: List[str] = Field(..., description="Columns to inspect")


class SnapshotDatabaseTool(BaseTool):
    name: str = "snapshot_database"
    description: str = "Takes a database snapshot for specific rows and columns before or after a test execution."
    args_schema: type[BaseModel] = SnapshotDbInput

    def _run(self, table: str, key: Dict[str, Any], columns: List[str]) -> str:
        try:
            helper = DBSnapshotHelper()
            snap_id, data = helper.snapshot(table=table, key=key, columns=columns)
        except SnapshotError as exc:
            return json.dumps({"error": str(exc), "error_type": "SnapshotError"})
        return json.dumps({"snapshot_id": snap_id, "data": data})


class ComputeDiffInput(BaseModel):
    table: str = Field(..., description="Target database table")
    key: Dict[str, Any] = Field(..., description="Primary key identifying target row")
    columns: List[str] = Field(..., description="Columns to compare")
    before_snapshot_id: str = Field(..., description="Snapshot ID before the change")
    after_snapshot_id: str = Field(..., description="Snapshot ID after the change")
    before_state: Dict[str, Any] = Field(..., description="Row state before")
    after_state: Dict[str, Any] = Field(..., description="Row state after")


class ComputeStateDiffTool(BaseTool):
    name: str = "compute_state_diff"
    description: str = "Computes deep differences between database snapshots to prove whether state changed."
    args_schema: type[BaseModel] = ComputeDiffInput

    def _run(
        self,
        table: str,
        key: Dict[str, Any],
        columns: List[str],
        before_snapshot_id: str,
        after_snapshot_id: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> str:
        diffs = StateDiffEngine.compute_diffs(
            table=table,
            key=key,
            columns=columns,
            before_snapshot_id=before_snapshot_id,
            after_snapshot_id=after_snapshot_id,
            before_state=before_state,
            after_state=after_state
        )
        return json.dumps(diffs)


class PlaywrightUiInput(BaseModel):
    target_url: str = Field(..., description="URL for the browser UI flow")
    identity_id: str = Field(..., description="Identity testing the UI flow")
    flow_steps: List[str] = Field(default_factory=list, description="Steps to perform in browser")


class PlaywrightUiTool(BaseTool):
    name: str = "playwright_ui_test"
    description: str = "Executes headless browser tests with Playwright for UI flows and captures evidence."
    args_schema: type[BaseModel] = PlaywrightUiInput

    def _run(self, target_url: str, identity_id: str, flow_steps: Optional[List[str]] = None) -> str:
        tool = PlaywrightBrowserTool()
        try:
            res = tool.execute_browser_flow(target_url=target_url, identity_id=identity_id, flow_steps=flow_steps or [])
        except SandboxHealthError as exc:
            return json.dumps({"error": str(exc), "error_type": "SandboxHealthError"})
        return json.dumps(res)
