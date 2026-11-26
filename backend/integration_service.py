"""Tavily Live Threat Intelligence and Bifrost Gateway Integration Service.
Provides end-to-end health checking, live test queries, CVE research retrieval,
and graceful offline fallback without fabricating external threat intelligence.
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _resolve_env_var(key: str) -> str:
    """Retrieves an environment variable, falling back to reading .env."""
    val = os.environ.get(key, "").strip()
    if val:
        return val

    env_path = os.path.join(WORKSPACE_ROOT, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith(f"{key}="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return ""

def _mask_api_key(key: str) -> str:
    """Masks a sensitive API key for safe telemetry and UI preview."""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:8]}...{key[-4:]}"

_TAVILY_HEALTH_CACHE: Dict[str, Any] = {}
_LAST_HEALTH_CHECK_TIME: float = 0.0

class TavilyIntegrationService:
    """Handles real-time communication with Tavily Offensive Intelligence API."""

    def __init__(self):
        self.api_key = _resolve_env_var("TAVILY_API_KEY")

    def get_status(self) -> str:
        """Returns the quick configuration status of Tavily."""
        return "connected" if bool(self.api_key) else "not_configured"

    def check_health(self, force: bool = False) -> Dict[str, Any]:
        """Performs an authentic live health check against Tavily API."""
        global _TAVILY_HEALTH_CACHE, _LAST_HEALTH_CHECK_TIME

        now = time.time()
        if not force and _TAVILY_HEALTH_CACHE and (now - _LAST_HEALTH_CHECK_TIME < 60):
            return dict(_TAVILY_HEALTH_CACHE)

        api_key = _resolve_env_var("TAVILY_API_KEY")
        if not api_key:
            result = {
                "status": "not_configured",
                "service": "unavailable",
                "configured": False,
                "key_preview": None,
                "latency_ms": 0,
                "last_tested_at": datetime.now(timezone.utc).isoformat(),
                "error_message": "TAVILY_API_KEY is missing from environment and .env"
            }
            _TAVILY_HEALTH_CACHE = result
            _LAST_HEALTH_CHECK_TIME = now
            return result

        start_time = time.time()
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            test_response = client.search(query="CVE security advisory", max_results=1)
            duration_ms = int((time.time() - start_time) * 1000)

            results = test_response.get("results", [])
            result = {
                "status": "connected",
                "service": "live",
                "configured": True,
                "key_preview": _mask_api_key(api_key),
                "latency_ms": duration_ms,
                "sample_results_count": len(results),
                "last_tested_at": datetime.now(timezone.utc).isoformat(),
                "error_message": None
            }
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_str = str(exc)
            status = "test_failed"
            if "auth" in err_str.lower() or "401" in err_str:
                status = "authentication_failed"
            elif "rate" in err_str.lower() or "429" in err_str:
                status = "rate_limited"
            elif "connect" in err_str.lower() or "resolution" in err_str.lower():
                status = "unavailable"

            result = {
                "status": status,
                "service": "unavailable",
                "configured": True,
                "key_preview": _mask_api_key(api_key),
                "latency_ms": duration_ms,
                "sample_results_count": 0,
                "last_tested_at": datetime.now(timezone.utc).isoformat(),
                "error_message": err_str[:160]
            }

        _TAVILY_HEALTH_CACHE = result
        _LAST_HEALTH_CHECK_TIME = now
        return result

    def execute_search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Executes a real live Tavily threat search query."""
        api_key = _resolve_env_var("TAVILY_API_KEY")
        if not api_key:
            return {
                "status": "unavailable",
                "query": query,
                "results": [],
                "error": "TAVILY_API_KEY not configured"
            }

        start_time = time.time()
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            raw = client.search(query=query, max_results=max_results)
            duration_ms = int((time.time() - start_time) * 1000)

            parsed = []
            for item in raw.get("results", []):
                parsed.append({
                    "title": item.get("title", "Advisory Document"),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:300],
                    "score": item.get("score", 0.0)
                })

            return {
                "status": "success",
                "query": query,
                "duration_ms": duration_ms,
                "results": parsed,
                "total_results": len(parsed)
            }
        except Exception as exc:
            return {
                "status": "error",
                "query": query,
                "results": [],
                "error": str(exc)[:200]
            }

    def research_dependency_cves(self, package_name: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches for genuine CVE advisories affecting a detected dependency."""
        query = f"{package_name} vulnerability CVE security advisory"
        if version:
            query = f"{package_name} {version} vulnerability CVE security advisory"

        res = self.execute_search(query=query, max_results=3)
        return res.get("results", [])

class BifrostGatewayService:
    """Manages AI Gateway routing, model health, and provider failover."""

    def __init__(self):
        self.groq_api_key = _resolve_env_var("GROQ_API_KEY")
        self.groq_model = _resolve_env_var("GROQ_MODEL") or "openai/gpt-oss-120b"
        self.bifrost_url = _resolve_env_var("BIFROST_GATEWAY_URL")

    def _probe_groq(self) -> Dict[str, Any]:
        """Ask Groq which models this key can use. Cached for 60 seconds."""
        cached = getattr(self, "_probe_cache", None)
        if cached and time.time() - cached[0] < 60:
            return cached[1]
        result: Dict[str, Any] = {"reachable": False, "models": [], "error": None}
        try:
            import httpx
            r = httpx.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {self.groq_api_key}"},
                timeout=5.0,
            )
            if r.status_code == 200:
                result["reachable"] = True
                result["models"] = sorted(m["id"] for m in r.json().get("data", []))
            else:
                result["error"] = f"HTTP {r.status_code}"
        except Exception as exc:
            result["error"] = str(exc)[:120]
        self._probe_cache = (time.time(), result)
        return result

    def check_health(self) -> Dict[str, Any]:
        """Checks AI Gateway connectivity and model readiness with a live call."""
        is_configured = bool(self.groq_api_key or self.bifrost_url)
        active_mode = "bifrost_proxy" if self.bifrost_url else "direct_groq"
        status = "not_configured"
        models: List[str] = []
        model_ok: Optional[bool] = None
        error = None
        if self.groq_api_key and not self.bifrost_url:
            probe = self._probe_groq()
            status = "connected" if probe["reachable"] else "unreachable"
            models = probe["models"]
            error = probe["error"]
            if probe["reachable"]:
                model_ok = self.groq_model in models
                if not model_ok:
                    status = "model_unavailable"
        elif is_configured:
            status = "configured"

        return {
            "status": status,
            "gateway_mode": active_mode,
            "configured": is_configured,
            "active_model": self.groq_model,
            "active_model_available": model_ok,
            "available_models": models,
            "error": error,
            "fallback_enabled": True,
            "rate_limit_policy": "adaptive_backoff",
            "last_checked_at": datetime.now(timezone.utc).isoformat()
        }
