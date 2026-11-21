"""Persistent artifact store for cross-agent hand-offs.

The agent contracts exchange opaque references such as ``out://tsk_...``,
``graph://<scan_id>/code`` and ``evd_...``.  Those references are only
meaningful when the producing agent actually persists the artifact.  This
module is the single place that reads and writes those artifacts on disk.

All writes are atomic (temporary file + ``os.replace``) so a crash cannot
leave a half-written artifact behind.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any, Dict, Optional

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_ROOT = os.environ.get("AEGISTRACE_CACHE_DIR") or os.path.join(WORKSPACE_ROOT, ".aegistrace_cache")


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _atomic_write_json(path: str, payload: Any) -> None:
    _ensure_dir(os.path.dirname(path))
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _atomic_write_text(path: str, text: str) -> None:
    _ensure_dir(os.path.dirname(path))
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _read_json(path: str) -> Optional[Any]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _task_key(task_ref: str) -> str:
    clean = task_ref.strip()
    clean = re.sub(r"^(out|workspace)://", "", clean)
    clean = clean.strip("/")
    clean = clean.replace("/", "_")
    return clean


def save_task_output(task_id: str, payload: Dict[str, Any]) -> str:
    """Persist a full task result and return its ``out://`` reference."""
    key = _task_key(task_id)
    _atomic_write_json(os.path.join(CACHE_ROOT, "tasks", f"{key}.json"), payload)
    return f"out://{key}"


def load_task_output(task_ref: str) -> Optional[Dict[str, Any]]:
    """Load a task result by ``out://``, bare id, or filesystem path."""
    if not task_ref:
        return None
    candidates = []
    if os.path.isabs(task_ref) or task_ref.startswith("."):
        candidates.append(task_ref)
    key = _task_key(task_ref)
    candidates.extend([
        os.path.join(CACHE_ROOT, "tasks", f"{key}.json"),
        os.path.join(CACHE_ROOT, "tasks", key),
        os.path.join(WORKSPACE_ROOT, key),
        os.path.join(WORKSPACE_ROOT, f"{key}.json"),
    ])
    for candidate in candidates:
        data = _read_json(candidate)
        if isinstance(data, dict):
            return data
    return None


def find_task_output_for_test_plan(test_plan_id: str) -> Optional[Dict[str, Any]]:
    """Find the persisted agent task that executed ``test_plan_id``.

    Dynamic Testing stores the executable requests inside
    ``internal.executed_requests``.  Remediation needs those real requests to
    replay the original exploit, so the lookup is by the plan identifier
    rather than by a guessed task id.
    """
    if not test_plan_id:
        return None
    tasks_dir = os.path.join(CACHE_ROOT, "tasks")
    if not os.path.isdir(tasks_dir):
        return None
    def _mtime(name: str) -> float:
        try:
            return os.path.getmtime(os.path.join(tasks_dir, name))
        except OSError:
            return 0.0
    # Prefer the most recent artifact: several scans may execute the same
    # test plan id, and replaying a stale artifact would validate a patch
    # against outdated requests.
    for name in sorted(os.listdir(tasks_dir), key=_mtime, reverse=True):
        if not name.endswith(".json"):
            continue
        data = _read_json(os.path.join(tasks_dir, name))
        if not isinstance(data, dict):
            continue
        internal = data.get("internal")
        if isinstance(internal, dict):
            plan = internal.get("test_plan")
            if isinstance(plan, dict) and plan.get("test_plan_id") == test_plan_id:
                return data
        request = data.get("request")
        if isinstance(request, dict):
            plan = (request.get("input") or {}).get("test_plan")
            if isinstance(plan, dict) and plan.get("test_plan_id") == test_plan_id:
                return data
        output = data.get("output")
        if isinstance(output, dict) and output.get("test_plan_id") == test_plan_id:
            return data
    return None


def resolve_output_payload(task_ref: str) -> Optional[Dict[str, Any]]:
    """Return the contract ``output`` object from a persisted task result."""
    data = load_task_output(task_ref)
    if not isinstance(data, dict):
        return None
    output = data.get("output")
    return output if isinstance(output, dict) else data


def save_graph(scan_id: str, kind: str, payload: Dict[str, Any]) -> str:
    safe_scan = re.sub(r"[^A-Za-z0-9_.-]+", "_", scan_id)
    safe_kind = re.sub(r"[^A-Za-z0-9_.-]+", "_", kind)
    _atomic_write_json(os.path.join(CACHE_ROOT, "graphs", f"{safe_scan}_{safe_kind}.json"), payload)
    return f"graph://{scan_id}/{kind}"


def load_graph(graph_ref: str) -> Optional[Dict[str, Any]]:
    if not graph_ref:
        return None
    if graph_ref.startswith("graph://file/"):
        return _read_json(graph_ref[len("graph://file/"):])
    match = re.match(r"^graph://([^/]+)/(.+)$", graph_ref)
    if not match:
        return None
    scan_id, kind = match.group(1), match.group(2)
    safe_scan = re.sub(r"[^A-Za-z0-9_.-]+", "_", scan_id)
    safe_kind = re.sub(r"[^A-Za-z0-9_.-]+", "_", kind)
    return _read_json(os.path.join(CACHE_ROOT, "graphs", f"{safe_scan}_{safe_kind}.json"))


def save_evidence(evidence_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    import hashlib

    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    record = {
        "evidence_id": evidence_id,
        "content": content,
        "sha256": sha256,
        "metadata": metadata or {},
    }
    _atomic_write_json(os.path.join(CACHE_ROOT, "evidence", f"{evidence_id}.json"), record)
    return record


def load_evidence(evidence_id: str) -> Optional[Dict[str, Any]]:
    return _read_json(os.path.join(CACHE_ROOT, "evidence", f"{evidence_id}.json"))


def save_test_plan(test_plan: Dict[str, Any]) -> str:
    plan_id = test_plan.get("test_plan_id") or "tpl_unknown"
    _atomic_write_json(os.path.join(CACHE_ROOT, "test_plans", f"{plan_id}.json"), test_plan)
    return plan_id


def load_test_plan(test_plan_id: str) -> Optional[Dict[str, Any]]:
    return _read_json(os.path.join(CACHE_ROOT, "test_plans", f"{test_plan_id}.json"))


def save_patch(patch_id: str, diff_text: str) -> str:
    path = os.path.join(CACHE_ROOT, "patches", f"{patch_id}.diff")
    _atomic_write_text(path, diff_text)
    return f"patches/{patch_id}.diff"


def load_patch(diff_ref: str) -> Optional[str]:
    if not diff_ref:
        return None
    if os.path.isabs(diff_ref):
        path = diff_ref
    else:
        path = os.path.join(CACHE_ROOT, diff_ref)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None
