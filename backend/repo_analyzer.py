"""Repository Ingestion and Intelligence Engine for AegisTrace.
Validates GitHub URLs, shallow-clones repositories, pins commit SHAs,
filters noise directories, detects languages, frameworks, manifests, and dependencies,
maps architecture entry points and routes via AST, and highlights security-sensitive modules.
"""

import os
import re
import ast
import json
import subprocess
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_REPOS_DIR = os.path.join(WORKSPACE_ROOT, "target_repos")

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".cargo",
    "target",
    "vendor",
    "coverage",
    ".next"
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
    ".exe", ".bin", ".iso", ".tar", ".gz", ".zip",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".mp4", ".mov", ".avi", ".mp3", ".wav",
    ".woff", ".woff2", ".ttf", ".eot"
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML"
}

def validate_github_url(url: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Validates whether a URL is a legitimate GitHub repository URL.
    Returns: (is_valid, owner, repo_name, normalized_url)
    """
    if not url or not isinstance(url, str):
        return False, None, None, None

    cleaned = url.strip()
    match = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", cleaned)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        normalized = f"https://github.com/{owner}/{repo}"
        return True, owner, repo, normalized

    ssh_match = re.match(r"^git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", cleaned)
    if ssh_match:
        owner = ssh_match.group(1)
        repo = ssh_match.group(2)
        normalized = f"https://github.com/{owner}/{repo}"
        return True, owner, repo, normalized

    return False, None, None, None

def get_repo_commit_sha(repo_path: str) -> str:
    """Retrieves the exact Git commit SHA of the repository."""
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return "HEAD"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "0000000000000000000000000000000000000000"

def get_repo_branch(repo_path: str) -> str:
    """Retrieves the active Git branch of the repository."""
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return "main"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "main"

def clone_or_fetch_repo(github_url: str, repo_name: str, auth_token: Optional[str] = None) -> Tuple[str, str, str]:
    """Clones the repository if not cached, or updates it safely.
    Returns: (local_path, commit_sha, branch)
    """
    os.makedirs(TARGET_REPOS_DIR, exist_ok=True)
    local_path = os.path.join(TARGET_REPOS_DIR, repo_name)

    clone_url = github_url
    if auth_token and not clone_url.startswith("git@"):
        parsed = urlparse(github_url)
        clone_url = f"https://x-access-token:{auth_token}@{parsed.netloc}{parsed.path}"

    if not os.path.exists(local_path):
        cmd = ["git", "clone", "--depth", "1", clone_url, local_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            safe_err = proc.stderr.replace(auth_token, "***") if auth_token else proc.stderr
            raise RuntimeError(f"Git clone failed: {safe_err.strip()}")

    commit_sha = get_repo_commit_sha(local_path)
    branch = get_repo_branch(local_path)
    return local_path, commit_sha, branch

class RepositoryIntelligenceEngine:
    """Understands repository architecture, tech stack, routes, and security risk areas."""

    def __init__(self, repo_path: str, repo_name: str, owner: str, commit_sha: str, branch: str):
        self.repo_path = repo_path
        self.repo_name = repo_name
        self.owner = owner
        self.commit_sha = commit_sha
        self.branch = branch

    def analyze(self) -> Dict[str, Any]:
        """Executes full repository understanding without executing untrusted code."""
        files_data = self._enumerate_files()
        tech_data = self._detect_technologies(files_data["all_files"])
        arch_data = self._analyze_architecture(files_data["code_files"])
        risk_data = self._identify_risk_areas(files_data["code_files"], tech_data)

        return {
            "repository_name": self.repo_name,
            "owner": self.owner,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "languages": tech_data["languages"],
            "frameworks": tech_data["frameworks"],
            "database_technologies": tech_data["databases"],
            "auth_mechanisms": tech_data["auth_mechanisms"],
            "dependencies": tech_data["dependencies"][:50],
            "total_dependencies": len(tech_data["dependencies"]),
            "architecture_summary": arch_data["summary"],
            "entry_points": arch_data["entry_points"],
            "analyzed_files_count": len(files_data["code_files"]),
            "skipped_files_count": files_data["skipped_count"],
            "discovered_endpoints": arch_data["endpoints"],
            "security_sensitive_modules": arch_data["sensitive_modules"],
            "potential_risk_areas": risk_data,
            "analysis_limitations": [
                "Static analysis only; dynamic runtime testing requires authorized sandbox container.",
                "Third-party external services and cloud backends are mocked for safety."
            ]
        }

    def _enumerate_files(self) -> Dict[str, Any]:
        """Enumerates source files while ignoring build artifacts and noise."""
        all_files = []
        code_files = []
        skipped_count = 0

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORED_EXTENSIONS:
                    skipped_count += 1
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.repo_path)
                all_files.append(rel_path)

                if ext in EXTENSION_LANGUAGE_MAP:
                    code_files.append(rel_path)
                else:
                    skipped_count += 1

        return {
            "all_files": all_files,
            "code_files": code_files,
            "skipped_count": skipped_count
        }

    def _detect_technologies(self, all_files: List[str]) -> Dict[str, Any]:
        """Detects languages, frameworks, package dependencies, and databases."""
        languages_count: Dict[str, int] = {}
        for f in all_files:
            ext = os.path.splitext(f)[1].lower()
            lang = EXTENSION_LANGUAGE_MAP.get(ext)
            if lang:
                languages_count[lang] = languages_count.get(lang, 0) + 1

        sorted_langs = sorted(languages_count.items(), key=lambda x: x[1], reverse=True)
        primary_languages = [lang for lang, _ in sorted_langs]

        frameworks = set()
        databases = set()
        auth_mechanisms = set()
        dependencies = []

        manifest_candidates = [
            "requirements.txt",
            "Pipfile",
            "pyproject.toml",
            "setup.py",
            "package.json"
        ]

        manifest_text = ""
        for m in manifest_candidates:
            m_path = os.path.join(self.repo_path, m)
            if os.path.exists(m_path):
                try:
                    with open(m_path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        manifest_text += "\n" + content
                        if m == "requirements.txt":
                            for line in content.splitlines():
                                cleaned = line.strip().split("#")[0].strip()
                                if cleaned and not cleaned.startswith("-"):
                                    pkg = re.split(r"[><=~;]", cleaned)[0].strip()
                                    if pkg:
                                        dependencies.append(cleaned)
                        elif m == "package.json":
                            try:
                                pkg_json = json.loads(content)
                                for dep in list((pkg_json.get("dependencies") or {}).keys()):
                                    dependencies.append(dep)
                            except Exception:
                                pass
                except Exception:
                    pass

        lower_manifest = manifest_text.lower()

        if "fastapi" in lower_manifest:
            frameworks.add("FastAPI")
        if "streamlit" in lower_manifest:
            frameworks.add("Streamlit")
        if "flask" in lower_manifest:
            frameworks.add("Flask")
        if "django" in lower_manifest:
            frameworks.add("Django")
        if "express" in lower_manifest:
            frameworks.add("Express.js")
        if "next" in lower_manifest:
            frameworks.add("Next.js")
        if "scikit-learn" in lower_manifest or "sklearn" in lower_manifest:
            frameworks.add("Scikit-Learn ML")
        if "torch" in lower_manifest:
            frameworks.add("PyTorch")
        if "tensorflow" in lower_manifest:
            frameworks.add("TensorFlow")
        if "pandas" in lower_manifest:
            frameworks.add("Pandas Data Processing")

        if "sqlite" in lower_manifest:
            databases.add("SQLite")
        if "sqlalchemy" in lower_manifest:
            databases.add("SQLAlchemy ORM")
        if "psycopg" in lower_manifest or "postgres" in lower_manifest:
            databases.add("PostgreSQL")
        if "mysql" in lower_manifest:
            databases.add("MySQL")
        if "pymongo" in lower_manifest or "mongodb" in lower_manifest:
            databases.add("MongoDB")
        if "redis" in lower_manifest:
            databases.add("Redis")

        if "jwt" in lower_manifest or "pyjwt" in lower_manifest:
            auth_mechanisms.add("JSON Web Tokens (JWT)")
        if "oauth" in lower_manifest:
            auth_mechanisms.add("OAuth2")
        if "bcrypt" in lower_manifest or "passlib" in lower_manifest:
            auth_mechanisms.add("Bcrypt / Password Hashing")
        if "session" in lower_manifest:
            auth_mechanisms.add("Session-Based Cookies")

        return {
            "languages": primary_languages,
            "frameworks": sorted(list(frameworks)),
            "databases": sorted(list(databases)),
            "auth_mechanisms": sorted(list(auth_mechanisms)),
            "dependencies": dependencies
        }

    def _analyze_architecture(self, code_files: List[str]) -> Dict[str, Any]:
        """Identifies entry points, API routes, controllers, and sensitive modules."""
        entry_points = []
        endpoints = []
        sensitive_modules = []

        standard_entry_points = [
            "main.py", "app.py", "wsgi.py", "asgi.py", "manage.py",
            "server.py", "index.js", "server.js", "index.ts"
        ]

        for cf in code_files:
            fname = os.path.basename(cf)
            if fname in standard_entry_points or cf in standard_entry_points:
                entry_points.append(cf)

            if cf.endswith(".py"):
                self._inspect_python_file(cf, endpoints, sensitive_modules)

        summary_parts = []
        if entry_points:
            summary_parts.append(f"Application entry points: {', '.join(entry_points[:4])}.")
        if endpoints:
            summary_parts.append(f"Exposes {len(endpoints)} HTTP endpoint routes.")
        if sensitive_modules:
            summary_parts.append(f"Discovered {len(sensitive_modules)} security-sensitive code paths.")
        if not summary_parts:
            summary_parts.append("Standalone application/library structure.")

        return {
            "entry_points": entry_points,
            "endpoints": endpoints[:50],
            "sensitive_modules": sensitive_modules[:30],
            "summary": " ".join(summary_parts)
        }

    def _inspect_python_file(self, rel_path: str, endpoints: List[Dict[str, Any]], sensitive_modules: List[Dict[str, Any]]) -> None:
        """Parses Python file with AST to discover routes and security-sensitive constructs."""
        full_path = os.path.join(self.repo_path, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                tree = ast.parse(fh.read(), filename=rel_path)
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    route_info = self._extract_route_decorator(decorator, rel_path, node.name, node.lineno)
                    if route_info:
                        endpoints.append(route_info)

            if isinstance(node, ast.Call):
                call_info = self._extract_sensitive_call(node, rel_path)
                if call_info:
                    sensitive_modules.append(call_info)

    def _extract_route_decorator(self, decorator: ast.AST, file_path: str, func_name: str, line_no: int) -> Optional[Dict[str, Any]]:
        """Extracts FastAPI/Flask route decorators."""
        if not isinstance(decorator, ast.Call):
            return None

        func = decorator.func
        method_name = ""
        if isinstance(func, ast.Attribute):
            method_name = func.attr.upper()
        elif isinstance(func, ast.Name):
            method_name = func.id.upper()

        http_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "ROUTE"}
        if method_name not in http_methods:
            return None

        path_val = "/"
        if decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                path_val = first_arg.value

        return {
            "method": "ANY" if method_name == "ROUTE" else method_name,
            "path": path_val,
            "handler_function": func_name,
            "file": file_path,
            "line_number": line_no
        }

    def _extract_sensitive_call(self, call_node: ast.Call, file_path: str) -> Optional[Dict[str, Any]]:
        """Detects calls to deserialization, subprocess, or file operations."""
        func = call_node.func
        call_str = ""

        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                call_str = f"{func.value.id}.{func.attr}"
            else:
                call_str = func.attr
        elif isinstance(func, ast.Name):
            call_str = func.id

        sensitive_signatures = {
            "joblib.load": ("Insecure Deserialization", "high", "Loads serialized object via joblib without schema integrity checks"),
            "pickle.load": ("Insecure Deserialization", "critical", "Direct Python pickle deserialization vulnerable to arbitrary object creation"),
            "pickle.loads": ("Insecure Deserialization", "critical", "Direct Python pickle deserialization vulnerable to arbitrary object creation"),
            "subprocess.run": ("Command Execution", "medium", "Executes system command subprocess"),
            "subprocess.Popen": ("Command Execution", "medium", "Spawns asynchronous subprocess command"),
            "os.system": ("Command Injection", "critical", "Direct shell command execution via os.system"),
            "yaml.load": ("Unsafe YAML Deserialization", "high", "YAML deserialization without safe_load"),
            "read_parquet": ("Data Deserialization", "low", "Parses Apache Parquet dataset"),
            "read_pickle": ("Pandas Pickle Loading", "high", "Pandas read_pickle vulnerable to object injection")
        }

        for sig, (cat, sev, desc) in sensitive_signatures.items():
            if sig in call_str or call_str.endswith(sig.split(".")[-1]):
                if sig.split(".")[0] in call_str:
                    return {
                        "category": cat,
                        "severity": sev,
                        "description": desc,
                        "call_name": call_str,
                        "file": file_path,
                        "line_number": getattr(call_node, "lineno", 0)
                    }

        return None

    def _identify_risk_areas(self, code_files: List[str], tech_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Correlates detected technologies and sensitive modules into risk areas."""
        risk_areas = []

        has_env_file = any(f.endswith(".env") or ".env" in f for f in code_files)
        if has_env_file:
            risk_areas.append({
                "category": "Data Security & Secrets",
                "severity": "medium",
                "title": "Local Environment Config (.env) Detected in Repository",
                "description": "Repository contains environment configuration files that may leak credentials or sensitive endpoints."
            })

        frameworks = tech_data.get("frameworks", [])
        if "FastAPI" in frameworks:
            risk_areas.append({
                "category": "Access Control & IDOR",
                "severity": "high",
                "title": "API Object-Level Authorization (BOLA/IDOR)",
                "description": "FastAPI router endpoints require rigorous multi-tenant tenant_id and ownership checks."
            })

        for dep in tech_data.get("dependencies", []):
            lower_dep = dep.lower()
            if "pickle" in lower_dep or "joblib" in lower_dep:
                risk_areas.append({
                    "category": "Insecure Deserialization",
                    "severity": "high",
                    "title": "Object Deserialization Library Usage",
                    "description": "Usage of joblib/pickle requires cryptographic verification of model artifacts."
                })
                break

        return risk_areas
