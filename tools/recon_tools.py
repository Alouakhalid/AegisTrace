import os
import re
import json
import uuid
import fnmatch
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import httpx
import yaml
import networkx as nx
from crewai.tools import BaseTool
from pydantic import Field

from tools.artifact_store import save_graph

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

class ScopeViolationException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ScopeGate:
    def __init__(self, allowed_hosts: List[str], allowed_methods: List[str], forbidden_paths: List[str]):
        self.allowed_hosts = [h.strip().lower() for h in allowed_hosts]
        self.allowed_methods = [m.upper() for m in allowed_methods]
        self.forbidden_paths = forbidden_paths

    @staticmethod
    def _normalize_host(host: str) -> str:
        if not host:
            return ""
        value = str(host).strip().lower()
        if "://" in value:
            value = httpx.URL(value).host or ""
        else:
            value = value.split("/")[0]
            if "@" in value:
                value = value.rsplit("@", 1)[-1]
            if value.count(":") == 1:
                value = value.split(":", 1)[0]
        return value.strip().lower()

    def is_host_allowed(self, host: str) -> bool:
        norm_host = self._normalize_host(host)
        if not norm_host:
            return False
        for allowed in self.allowed_hosts:
            clean_allowed = self._normalize_host(allowed)
            if not clean_allowed:
                continue
            if clean_allowed.startswith("*."):
                suffix = clean_allowed[2:]
                if suffix and norm_host.endswith(f".{suffix}") and norm_host != suffix:
                    return True
            elif norm_host == clean_allowed:
                return True
        return False

    def is_method_allowed(self, method: str) -> bool:
        return method.upper() in self.allowed_methods

    def is_path_forbidden(self, path: str) -> Tuple[bool, Optional[str]]:
        norm_path = path if path.startswith("/") else f"/{path}"
        for forbidden in self.forbidden_paths:
            pattern = forbidden.rstrip("/")
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if norm_path.startswith(prefix) or fnmatch.fnmatch(norm_path, pattern):
                    return True, forbidden
            else:
                if norm_path == pattern or norm_path.startswith(f"{pattern}/"):
                    return True, forbidden
        return False, None

    def validate_request(self, host: str, method: str, path: str):
        if not self.is_host_allowed(host):
            raise ScopeViolationException(
                f"Host '{host}' is outside allowed_hosts {self.allowed_hosts}",
                {"host": host, "rule": "host_not_in_allowed_hosts"}
            )
        if not self.is_method_allowed(method):
            raise ScopeViolationException(
                f"Method '{method}' is not in allowed_methods {self.allowed_methods}",
                {"method": method, "rule": "method_not_in_allowed_methods"}
            )
        is_forbid, pattern = self.is_path_forbidden(path)
        if is_forbid:
            raise ScopeViolationException(
                f"Path '{path}' matches forbidden rule '{pattern}'",
                {"path": path, "rule": "path_in_forbidden_paths", "pattern": pattern}
            )

class ScopedHttpClient:
    def __init__(self, scope_gate: ScopeGate, timeout: float = 10.0):
        self.scope_gate = scope_gate
        self.timeout = timeout

    def send_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        parsed_url = httpx.URL(url)
        host = parsed_url.host
        path = parsed_url.path or "/"
        self.scope_gate.validate_request(host, method, path)
        with httpx.Client(timeout=self.timeout) as client:
            return client.request(method, url, **kwargs)

def sanitize_endpoint_id(method: str, path: str) -> str:
    norm_method = method.lower()
    clean_path = re.sub(r"[^a-zA-Z0-9_]+", "_", path).strip("_").lower()
    return f"ep_{norm_method}_{clean_path}" if clean_path else f"ep_{norm_method}_root"

def parse_openapi_spec(spec_content: str, scope_gate: Optional[ScopeGate] = None) -> Dict[str, Any]:
    try:
        spec_dict = json.loads(spec_content)
    except Exception:
        try:
            spec_dict = yaml.safe_load(spec_content)
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI specification: {e}")

    endpoints = []
    technologies = []
    warnings = []

    info = spec_dict.get("info", {})
    title = info.get("title", "")
    description = info.get("description", "")
    version = info.get("version", "")

    servers = spec_dict.get("servers", []) or []
    absolute_servers = 0
    in_scope_servers = 0
    for server in servers:
        server_url = server.get("url", "") if isinstance(server, dict) else str(server)
        if not server_url or server_url.startswith("/"):
            in_scope_servers += 1
            continue
        absolute_servers += 1
        server_host = httpx.URL(server_url).host or ""
        if scope_gate and not scope_gate.is_host_allowed(server_host):
            warnings.append(f"OpenAPI server '{server_url}' is outside the authorized host scope")
        else:
            in_scope_servers += 1
    if scope_gate and absolute_servers > 0 and in_scope_servers == 0:
        raise ScopeViolationException(
            "Every OpenAPI server URL is outside the authorized host scope",
            {"rule": "openapi_server_host_not_in_scope", "servers": servers}
        )

    if "fastapi" in title.lower() or "fastapi" in description.lower():
        technologies.append({
            "name": "FastAPI",
            "version": version or None,
            "confidence": 0.95,
            "evidence": "OpenAPI info title/description mentions FastAPI"
        })

    paths = spec_dict.get("paths", {})
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        
        path_params = re.findall(r"\{([a-zA-Z0-9_]+)\}", path_str)
        
        for verb, op_item in path_item.items():
            if verb.lower() not in ["get", "post", "put", "patch", "delete", "options", "head"]:
                continue
            
            http_method = verb.upper()
            
            if scope_gate:
                if not scope_gate.is_method_allowed(http_method):
                    warnings.append(f"Skipping {http_method} {path_str}: method not allowed in scope")
                    continue
                is_forbid, forbidden_pat = scope_gate.is_path_forbidden(path_str)
                if is_forbid:
                    warnings.append(f"Skipping {http_method} {path_str}: matches forbidden path {forbidden_pat}")
                    continue

            ep_id = sanitize_endpoint_id(http_method, path_str)
            auth_required = False
            if isinstance(op_item, dict):
                security = op_item.get("security")
                if security and len(security) > 0:
                    auth_required = True
                elif "security" in spec_dict and len(spec_dict.get("security", [])) > 0:
                    auth_required = True

            endpoints.append({
                "endpoint_id": ep_id,
                "method": http_method,
                "path": path_str,
                "path_params": path_params,
                "auth_required": auth_required,
                "source": "openapi"
            })

    return {
        "endpoints": endpoints,
        "technologies": technologies,
        "warnings": warnings,
        "title": title
    }

def fingerprint_target(technology_hints: List[str], openapi_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    technologies = []
    seen = set()

    if openapi_metadata and openapi_metadata.get("technologies"):
        for tech in openapi_metadata["technologies"]:
            key = tech["name"].lower()
            if key not in seen:
                seen.add(key)
                technologies.append(tech)

    for hint in technology_hints:
        hint_lower = hint.lower().strip()
        if not hint_lower or hint_lower in seen:
            continue
        
        seen.add(hint_lower)
        if "fastapi" in hint_lower:
            technologies.append({
                "name": "FastAPI",
                "version": None,
                "confidence": 0.75,
                "evidence": "Technology hint supplied in scan configuration"
            })
        elif "postgresql" in hint_lower or "postgres" in hint_lower:
            technologies.append({
                "name": "PostgreSQL",
                "version": None,
                "confidence": 0.75,
                "evidence": "Technology hint supplied in scan configuration"
            })
        elif "django" in hint_lower:
            technologies.append({
                "name": "Django",
                "version": None,
                "confidence": 0.75,
                "evidence": "Technology hint supplied in scan configuration"
            })
        elif "flask" in hint_lower:
            technologies.append({
                "name": "Flask",
                "version": None,
                "confidence": 0.75,
                "evidence": "Technology hint supplied in scan configuration"
            })
        elif "redis" in hint_lower:
            technologies.append({
                "name": "Redis",
                "version": None,
                "confidence": 0.70,
                "evidence": "Technology hint supplied in scan configuration"
            })
        else:
            technologies.append({
                "name": hint.capitalize(),
                "version": None,
                "confidence": 0.60,
                "evidence": f"Technology hint '{hint}' supplied in scan configuration"
            })

    return technologies

def query_tavily_intel(technologies: List[Dict[str, Any]], max_queries: int = 3, search_depth: str = "basic") -> List[Dict[str, Any]]:
    from tavily import TavilyClient
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []

    client = TavilyClient(api_key=api_key)
    intel_refs = []
    seen_urls = set()
    queries_run = 0

    for tech in technologies:
        if queries_run >= max_queries:
            break
        tech_name = tech.get("name", "")
        if not tech_name:
            continue
        
        query = f"{tech_name} security advisory CVE Broken Object Level Authorization OWASP"
        try:
            res = client.search(
                query=query,
                search_depth=search_depth,
                max_results=2
            )
            queries_run += 1
            for item in res.get("results", []):
                url = item.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                source_type = "other"
                if "owasp" in url.lower() or "owasp" in item.get("title", "").lower():
                    source_type = "owasp"
                elif "cve" in url.lower() or "nvd" in url.lower():
                    source_type = "nvd"
                elif any(k in url.lower() for k in ["github", "vendor", "security"]):
                    source_type = "vendor"

                ref_id = f"ref_{uuid.uuid4().hex[:8]}"
                now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                intel_refs.append({
                    "ref_id": ref_id,
                    "title": item.get("title", f"{tech_name} Security Advisory"),
                    "url": url,
                    "retrieved_at": now_utc,
                    "source_type": source_type,
                    "relevance": 0.90 if source_type in ["owasp", "nvd"] else 0.80,
                    "trusted": False
                })
        except Exception:
            continue

    return intel_refs

def build_attack_surface_graph(endpoints: List[Dict[str, Any]], technologies: List[Dict[str, Any]], scan_id: str = "scn_default") -> str:
    G = nx.DiGraph()
    root_node = f"scan:{scan_id}"
    G.add_node(root_node, kind="scan_root")

    for tech in technologies:
        t_node = f"tech:{tech['name'].lower()}"
        G.add_node(t_node, kind="technology", name=tech["name"], confidence=tech["confidence"])
        G.add_edge(root_node, t_node, relation="USES_TECHNOLOGY")

    for ep in endpoints:
        ep_node = f"endpoint:{ep['endpoint_id']}"
        G.add_node(ep_node, kind="endpoint", method=ep["method"], path=ep["path"], auth_required=ep["auth_required"])
        G.add_edge(root_node, ep_node, relation="EXPOSES_ENDPOINT")
        for tech in technologies:
            t_node = f"tech:{tech['name'].lower()}"
            G.add_edge(ep_node, t_node, relation="RUNS_ON")

    ref_uri = f"graph://{scan_id}/attack_surface"
    save_graph(scan_id, "attack_surface", {
        "networkx": nx.node_link_data(G, edges="edges"),
        "scan_id": scan_id,
        "endpoints": endpoints,
        "technologies": technologies,
    })
    return ref_uri

def read_skill_content(skill_name: str, skills_dir: str) -> str:
    skill_file = os.path.join(skills_dir, skill_name, "SKILL.md")
    if os.path.exists(skill_file):
        with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""

class OpenApiParserCrewTool(BaseTool):
    name: str = "openapi_parser_tool"
    description: str = "Parses OpenAPI or Swagger specifications to discover all HTTP endpoints, path parameters, and authorization constraints."

    def _run(self, spec_content: str) -> str:
        res = parse_openapi_spec(spec_content)
        return json.dumps(res, indent=2)

class TechnologyFingerprintCrewTool(BaseTool):
    name: str = "technology_fingerprint_tool"
    description: str = "Detects web frameworks, database engines, and libraries from OpenAPI definitions and metadata."

    def _run(self, hints_json: str) -> str:
        hints = json.loads(hints_json) if isinstance(hints_json, str) else hints_json
        res = fingerprint_target(hints)
        return json.dumps(res, indent=2)

class TavilyIntelCrewTool(BaseTool):
    name: str = "tavily_security_intel_tool"
    description: str = "Queries Tavily Search API for external security advisories, OWASP references, and CVE bulletins for detected technologies."

    def _run(self, techs_json: str, max_queries: int = 3) -> str:
        techs = json.loads(techs_json) if isinstance(techs_json, str) else techs_json
        res = query_tavily_intel(techs, max_queries=max_queries)
        return json.dumps(res, indent=2)
