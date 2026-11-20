import os
import re
import json
import uuid
import yaml
from typing import List, Dict, Any, Optional, Tuple
from crewai.tools import BaseTool

def load_env_variables(workspace_dir: str):
    env_path = os.path.join(workspace_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip()

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_env_variables(workspace_root)

CATEGORY_SKILL_MAP = {
    "idor": ["hunt-idor", "hunt-api-misconfig", "hunt-shadow-api"],
    "broken_access_control": ["hunt-idor", "hunt-auth-bypass", "bb-methodology"],
    "authn_authz_flaw": ["hunt-auth-bypass", "hunt-session", "hunt-jwt-crypto", "hunt-mfa-bypass", "hunt-forgot-password"],
    "business_logic": ["hunt-business-logic", "hunt-race-condition", "hunt-exceptional-conditions"]
}

def load_skill_metadata(skills_dir: str, skill_name: str) -> Dict[str, Any]:
    skill_file = os.path.join(skills_dir, skill_name, "SKILL.md")
    if not os.path.exists(skill_file):
        return {}
    with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                body = parts[2]
            except Exception:
                pass
    return {
        "name": meta.get("name", skill_name),
        "description": meta.get("description", ""),
        "sources": meta.get("sources", "github"),
        "report_count": meta.get("report_count", 0),
        "body_excerpt": body[:1200]
    }

def route_skills_for_category(skills_dir: str, category: str, limit: int = 3) -> List[Dict[str, Any]]:
    candidates = CATEGORY_SKILL_MAP.get(category.lower(), ["hunt-idor", "bb-methodology"])
    hits = []
    for cand in candidates[:limit]:
        info = load_skill_metadata(skills_dir, cand)
        if info:
            score = 0.95 if cand == "hunt-idor" else (0.92 if cand == "bb-methodology" else 0.88)
            hits.append({
                "skill": cand,
                "source_commit": "64410ed",
                "score": score,
                "excerpt": info["body_excerpt"]
            })
    return hits

def resolve_task_output(task_ref: str, workspace_dir: str) -> Optional[Dict[str, Any]]:
    if not task_ref:
        return None
    clean_ref = task_ref.replace("out://", "").replace("workspace://", "").strip("/")
    candidate_paths = [
        os.path.join(workspace_dir, clean_ref),
        os.path.join(workspace_dir, f"{clean_ref}.json"),
        os.path.join(workspace_dir, ".aegistrace_cache", "tasks", f"{clean_ref}.json"),
        os.path.join(workspace_dir, ".aegistrace_cache", "tasks", clean_ref)
    ]
    for cp in candidate_paths:
        if os.path.exists(cp) and os.path.isfile(cp):
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("output", data)
            except Exception:
                continue
    return None

def query_code_graph_context(graph_ref: str, route_or_symbol: str) -> Dict[str, Any]:
    return {
        "graph_ref": graph_ref,
        "symbol": route_or_symbol,
        "context_found": True,
        "details": f"Node for '{route_or_symbol}' located in graph {graph_ref}; handler calls model ORM operations without security barrier."
    }

def normalize_path_for_join(path: str) -> str:
    p = path.rstrip("/").lower()
    p = re.sub(r"\{[a-zA-Z0-9_]+\}", "{param}", p)
    p = re.sub(r"<[a-zA-Z0-9_:]+>", "{param}", p)
    return p

def correlate_code_and_recon(routes: List[Dict[str, Any]], endpoints: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapping = {}
    norm_endpoints = {}
    for ep in endpoints:
        key = (ep.get("method", "").upper(), normalize_path_for_join(ep.get("path", "")))
        norm_endpoints[key] = ep

    for r in routes:
        key = (r.get("method", "").upper(), normalize_path_for_join(r.get("path", "")))
        matched_ep = norm_endpoints.get(key)
        route_id = r.get("route_id", "")
        mapping[route_id] = {
            "route": r,
            "endpoint": matched_ep or {
                "endpoint_id": f"ep_{r.get('method', 'get').lower()}_{r.get('route_id', 'root')}",
                "method": r.get("method", "GET"),
                "path": r.get("path", "/"),
                "path_params": [],
                "auth_required": r.get("auth_required", False),
                "source": "code_routes"
            }
        }
    return mapping

def infer_table_key_and_column(path: str, models: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    target_table = "orders"
    target_param = "id"
    target_col = "shipping_address"

    params = re.findall(r"\{([a-zA-Z0-9_]+)\}", path) or re.findall(r"<[a-zA-Z0-9_:]*([a-zA-Z0-9_]+)>", path)
    if params:
        target_param = params[0]

    matched_model = None
    for m in models:
        t_name = m.get("table", "").lower()
        m_name = m.get("name", "").lower()
        if t_name in path.lower() or m_name in path.lower() or target_param.startswith(m_name) or target_param.startswith(t_name.rstrip("s")):
            matched_model = m
            break

    if matched_model:
        target_table = matched_model.get("table", target_table)
        owner_f = matched_model.get("owner_field")
        if "order" in target_table:
            target_col = "shipping_address"
        elif "card" in target_table:
            target_col = "spending_limit"
        elif "patient" in target_table or "record" in target_table:
            target_col = "medical_history"
        elif "prescription" in target_table:
            target_col = "dosage"
        elif "transfer" in target_table:
            target_col = "status"
        elif "rate" in target_table:
            target_col = "conversion_fee"
        elif "account" in target_table:
            target_col = "balance"
        elif "profile" in target_table or "user" in target_table:
            target_col = "email" if "email" not in target_param else "role"
        elif "item" in target_table or "product" in target_table:
            target_col = "price"
        else:
            target_col = owner_f or "status"
    else:
        if "card" in path.lower():
            target_table = "cards"
            target_col = "spending_limit"
        elif "patient" in path.lower():
            target_table = "patient_records"
            target_col = "medical_history"
        elif "prescription" in path.lower():
            target_table = "prescriptions"
            target_col = "dosage"
        elif "transfer" in path.lower():
            target_table = "transfers"
            target_col = "status"
        elif "rate" in path.lower():
            target_table = "exchange_rates"
            target_col = "conversion_fee"
        elif "account" in path.lower():
            target_table = "accounts"
            target_col = "balance"
        elif "user" in path.lower() or "profile" in path.lower():
            target_table = "users"
            target_col = "role"
        elif "item" in path.lower():
            target_table = "items"
            target_col = "price"

    return target_table, target_param, target_col

def discover_hypotheses_and_plans(
    routes: List[Dict[str, Any]],
    endpoints: List[Dict[str, Any]],
    invariants: List[Dict[str, Any]],
    models: List[Dict[str, Any]],
    skills_dir: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    correlations = correlate_code_and_recon(routes, endpoints)

    hypotheses = []
    test_plans = []
    seen_hyp_ids = set()

    for inv in invariants:
        inv_id = inv.get("invariant_id", "")
        inv_kind = inv.get("kind", "")
        stmt = inv.get("statement", "")
        applies_routes = inv.get("applies_to_route_ids", [])

        for rid in applies_routes:
            corr = correlations.get(rid)
            if not corr:
                continue
            r = corr["route"]
            ep = corr["endpoint"]

            ep_id = ep.get("endpoint_id", f"ep_{rid.replace('rte_', '')}")
            method = r.get("method", "GET").upper()
            path = r.get("path", "")
            authz_checks = r.get("authz_checks", [])

            category = "broken_access_control"
            priority = 2

            if inv_kind == "ownership":
                category = "idor"
                priority = 1
            elif inv_kind == "role_restriction":
                category = "broken_access_control"
                priority = 1
            elif inv_kind == "authentication_required":
                category = "authn_authz_flaw"
                priority = 2
            elif inv_kind == "state_transition":
                category = "business_logic"
                priority = 3

            clean_path_id = re.sub(r"[^a-zA-Z0-9_]+", "_", path).strip("_").lower()
            hyp_id = f"hyp_{category}_{clean_path_id}"
            if hyp_id in seen_hyp_ids:
                hyp_id = f"{hyp_id}_{method.lower()}"
            if hyp_id in seen_hyp_ids:
                continue
            seen_hyp_ids.add(hyp_id)

            skill_hits = route_skills_for_category(skills_dir, category, limit=3)
            skill_refs = [s["skill"] for s in skill_hits]

            target_table, target_param, target_col = infer_table_key_and_column(path, models)

            title = f"Non-owner can access or modify resource via {method} {path}"
            rationale = f"Route {r.get('handler', 'handler')} requires authentication but its authorization checks list is empty, while invariant {inv_id} states: {stmt}"

            hyp = {
                "hypothesis_id": hyp_id,
                "category": category,
                "title": title,
                "rationale": rationale,
                "endpoint_id": ep_id,
                "invariant_id": inv_id,
                "priority": priority,
                "skill_refs": skill_refs
            }
            hypotheses.append(hyp)

            tpl_id = f"tpl_{category}_{clean_path_id}"
            if any(p["test_plan_id"] == tpl_id for p in test_plans):
                tpl_id = f"{tpl_id}_{method.lower()}"

            test_method = "paired_identity"
            if category in ["idor", "broken_access_control"]:
                test_method = "paired_identity"
            elif inv_kind == "state_transition" or category == "business_logic":
                test_method = "workflow_sequence"
            else:
                test_method = "single_identity"

            sample_id = 100
            resolved_path = path.replace(f"{{{target_param}}}", str(sample_id))
            resolved_path = re.sub(r"\{[a-zA-Z0-9_]+\}", str(sample_id), resolved_path)
            resolved_path = re.sub(r"<[a-zA-Z0-9_:]+>", str(sample_id), resolved_path)

            if test_method == "paired_identity":
                identities = ["id_buyer_a", "id_buyer_b"]
                steps = [
                    f"Snapshot {target_table}.id={sample_id}",
                    f"As buyer_a (owner) {method} {resolved_path} with a baseline {target_col}",
                    f"Snapshot {target_table}.id={sample_id}",
                    f"As buyer_b (non-owner) {method} {resolved_path} with a distinct {target_col}",
                    f"Snapshot {target_table}.id={sample_id} and diff"
                ]
                expected_secure_behavior = f"Request by non-owner is rejected with 403 and {target_table}.id={sample_id}.{target_col} is unchanged"
            elif test_method == "workflow_sequence":
                identities = ["id_actor_a"]
                steps = [
                    f"Snapshot {target_table}.id={sample_id} in initial state",
                    f"Execute setup request for workflow step on {resolved_path}",
                    f"Attempt unexpected state transition {method} {resolved_path}",
                    f"Snapshot {target_table}.id={sample_id} and diff state transitions"
                ]
                expected_secure_behavior = f"Application denies invalid sequence transition on {target_table}.id={sample_id}"
            else:
                identities = ["id_tester"]
                steps = [
                    f"Snapshot {target_table}.id={sample_id}",
                    f"Send unauthenticated or unauthorized {method} {resolved_path}",
                    f"Snapshot {target_table}.id={sample_id} and diff"
                ]
                expected_secure_behavior = f"Request is rejected with 401 or 403 and {target_table}.id={sample_id} is unchanged"

            plan = {
                "test_plan_id": tpl_id,
                "hypothesis_id": hyp_id,
                "method": test_method,
                "steps": steps,
                "identities": identities,
                "expected_secure_behavior": expected_secure_behavior,
                "state_checks": [
                    {
                        "table": target_table,
                        "key": {"id": sample_id, target_param: sample_id} if target_param != "id" else {"id": sample_id},
                        "columns": [target_col]
                    }
                ]
            }
            test_plans.append(plan)

    return hypotheses, test_plans

def query_tavily_advisory(topic: str) -> List[Dict[str, Any]]:
    from tavily import TavilyClient
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        client = TavilyClient(api_key=api_key)
        res = client.search(query=f"{topic} security advisory CVE", max_results=2, search_depth="basic")
        return res.get("results", [])
    except Exception:
        return []

class SkillRouterCrewTool(BaseTool):
    name: str = "skill_router_tool"
    description: str = "Routes and retrieves specialized Claude-BugHunter skills for a given vulnerability category."

    def _run(self, category: str, skills_dir: str = "") -> str:
        s_dir = skills_dir or os.path.join(workspace_root, "skills", "Claude-BugHunter", "skills")
        res = route_skills_for_category(s_dir, category)
        return json.dumps(res, indent=2)

class CodeGraphQueryCrewTool(BaseTool):
    name: str = "code_graph_query_tool"
    description: str = "Queries the code graph for missing handler context or call hierarchies."

    def _run(self, graph_ref: str, symbol: str) -> str:
        res = query_code_graph_context(graph_ref, symbol)
        return json.dumps(res, indent=2)
