import ast
import os
import re
import glob
import json
import shutil
import subprocess
import networkx as nx
from typing import List, Dict, Any, Optional
from tree_sitter import Language, Parser
import tree_sitter_python
from crewai.tools import BaseTool

PY_LANGUAGE = Language(tree_sitter_python.language())

#: Directories that hold test code rather than the application itself.
#: Routes declared inside them are test fixtures, not deployed endpoints, and
#: including them produced 132 "routes" for the Flask framework repository
#: (mostly "/1", "/2", "/3" declared in tests/test_basic.py).
TEST_DIRECTORY_NAMES = {
    "test", "tests", "testing", "test_", "_test", "tests_",
    "__tests__", "spec", "specs", "fixtures", "testdata", "test_data",
    "e2e", "integration_tests", "conftest", "benchmarks", "benchmark",
    "migrations", "examples", "example", "samples", "sample", "docs", "doc",
}


def _is_test_or_example_path(repo_path: str, filepath: str) -> bool:
    """True when a file lives in a test/example tree rather than app code."""
    try:
        rel = os.path.relpath(filepath, repo_path)
    except ValueError:
        return False
    parts = rel.replace("\\", "/").split("/")
    directories = parts[:-1]
    stem = parts[-1].lower()
    for d in directories:
        if d.lower() in TEST_DIRECTORY_NAMES:
            return True
        # directories such as "tests_utils" or "app_tests"
        base = d.lower().rstrip("/")
        if base.startswith("test") or base.endswith("_test") or base.endswith("_tests") or base.endswith("tests"):
            return True
    # module-level test files: test_foo.py / foo_test.py / conftest.py
    if stem.startswith("test_") or stem.endswith("_test.py") or stem == "conftest.py":
        return True
    if stem.startswith("test.") or ".test." in stem or ".spec." in stem:
        return True
    return False


def find_python_files(repo_path: str, include_globs: Optional[List[str]] = None, max_files: int = 200,
                      include_tests: bool = False) -> List[str]:
    files = []
    if not os.path.exists(repo_path):
        return files
    patterns = include_globs if include_globs else ["**/*.py"]
    for pattern in patterns:
        search_path = os.path.join(repo_path, pattern)
        for filepath in glob.glob(search_path, recursive=True):
            if not os.path.isfile(filepath):
                continue
            if not include_tests and _is_test_or_example_path(repo_path, filepath):
                continue
            files.append(filepath)
            if len(files) >= max_files:
                return sorted(list(set(files)))
    return sorted(list(set(files)))

def parse_dependencies(repo_path: str) -> Dict[str, str]:
    deps = {}
    req_file = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(req_file):
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    clean = line.strip()
                    if clean and not clean.startswith("#"):
                        parts = re.split(r"[=<>~]+", clean)
                        pkg_name = parts[0].strip().lower()
                        version = parts[1].strip() if len(parts) > 1 else "latest"
                        deps[pkg_name] = version
        except Exception:
            pass

    pyproject_file = os.path.join(repo_path, "pyproject.toml")
    if os.path.exists(pyproject_file):
        try:
            with open(pyproject_file, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(r'["\']([a-zA-Z0-9_\-]+)(?:[=<>~]+([^"\']+))?["\']', content)
                for pkg, ver in matches:
                    pkg_l = pkg.lower()
                    if pkg_l not in ["version", "name", "description", "authors"]:
                        deps[pkg_l] = ver or "latest"
        except Exception:
            pass
    return deps

def run_security_rules_scan(repo_path: str, py_files: List[str], enable_semgrep: bool = False) -> List[Dict[str, Any]]:
    findings = []
    if enable_semgrep and shutil.which("semgrep"):
        try:
            cmd = ["semgrep", "--json", "--quiet", "--config", "auto", repo_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0 and proc.stdout:
                parsed = json.loads(proc.stdout)
                for res in parsed.get("results", []):
                    findings.append({
                        "rule_id": res.get("check_id", "semgrep_rule"),
                        "file": os.path.relpath(res.get("path", ""), repo_path),
                        "line": res.get("start", {}).get("line", 1),
                        "message": res.get("extra", {}).get("message", "Semgrep security finding"),
                        "severity": res.get("extra", {}).get("severity", "WARNING")
                    })
        except Exception:
            pass

    for fpath in py_files:
        rel = os.path.relpath(fpath, repo_path)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    if re.search(r'allow_origins\s*=\s*\[\s*["\']\*["\']\s*\]', line):
                        findings.append({
                            "rule_id": "rule_wildcard_cors",
                            "file": rel,
                            "line": idx,
                            "message": "Wildcard CORS origin enabled",
                            "severity": "MEDIUM"
                        })
                    if re.search(r'(?:password|secret_key|api_key|jwt_secret)\s*=\s*["\'][^"\']{6,}["\']', line, re.IGNORECASE):
                        if not any(k in line.lower() for k in ["env", "getenv", "config", "os."]):
                            findings.append({
                                "rule_id": "rule_hardcoded_secret",
                                "file": rel,
                                "line": idx,
                                "message": "Potential hardcoded credential detected",
                                "severity": "HIGH"
                            })
                    if re.search(r'debug\s*=\s*True', line):
                        findings.append({
                            "rule_id": "rule_debug_mode_active",
                            "file": rel,
                            "line": idx,
                            "message": "Debug mode explicitly enabled in application",
                            "severity": "LOW"
                        })
        except Exception:
            continue
    return findings

def extract_decorators(node: ast.FunctionDef) -> List[str]:
    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            decorators.append(dec.attr)
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                decorators.append(f"{ast.unparse(dec.func.value)}.{dec.func.attr}" if hasattr(ast, "unparse") else dec.func.attr)
    return decorators

def extract_fastapi_depends(node: ast.FunctionDef) -> List[str]:
    depends = []
    defaults = list(node.args.defaults) if hasattr(node, "args") and node.args.defaults else []
    if hasattr(node, "args") and node.args.kw_defaults:
        defaults.extend([d for d in node.args.kw_defaults if d is not None])
    for default in defaults:
        if isinstance(default, ast.Call):
            func_name = getattr(default.func, "id", "") or getattr(default.func, "attr", "")
            if func_name in ["Depends", "Security"] and default.args:
                first_arg = default.args[0]
                dep_name = getattr(first_arg, "id", "") or getattr(first_arg, "attr", "") or "unknown_dep"
                depends.append(dep_name)
    return depends

class CodeVisitor(ast.NodeVisitor):
    def __init__(self, filepath: str, repo_root: str):
        self.filepath = filepath
        self.rel_path = os.path.relpath(filepath, repo_root)
        self.routes = []
        self.models = []
        self.auth_mechanisms = []
        self.frameworks = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name.lower()
            if "fastapi" in name:
                self.frameworks.add("fastapi")
            elif "flask" in name:
                self.frameworks.add("flask")
            elif "django" in name:
                self.frameworks.add("django")
            elif "sqlalchemy" in name or "sqlmodel" in name:
                self.frameworks.add("sqlalchemy")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = (node.module or "").lower()
        if "fastapi" in mod:
            self.frameworks.add("fastapi")
        elif "flask" in mod:
            self.frameworks.add("flask")
        elif "django" in mod:
            self.frameworks.add("django")
        elif "sqlalchemy" in mod or "sqlmodel" in mod:
            self.frameworks.add("sqlalchemy")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        is_urlpatterns = False
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "urlpatterns":
                is_urlpatterns = True
                self.frameworks.add("django")

        if is_urlpatterns and isinstance(node.value, ast.List):
            for elt in node.value.elts:
                if isinstance(elt, ast.Call):
                    fn_name = getattr(elt.func, "id", "") or getattr(elt.func, "attr", "")
                    if fn_name in ["path", "re_path"] and elt.args:
                        raw_pattern = ""
                        if isinstance(elt.args[0], ast.Constant):
                            raw_pattern = str(elt.args[0].value)
                        
                        handler_name = "django_view"
                        if len(elt.args) > 1:
                            h_arg = elt.args[1]
                            if isinstance(h_arg, ast.Name):
                                handler_name = h_arg.id
                            elif isinstance(h_arg, ast.Attribute):
                                handler_name = f"{getattr(h_arg.value, 'id', '')}.{h_arg.attr}"
                            elif isinstance(h_arg, ast.Call):
                                handler_name = getattr(h_arg.func, "attr", "as_view")

                        norm_path = "/" + raw_pattern.lstrip("/")
                        norm_path = re.sub(r"<[a-zA-Z_]+:([a-zA-Z0-9_]+)>", r"{\1}", norm_path)
                        norm_path = re.sub(r"\(\?P<([a-zA-Z0-9_]+)>[^\)]+\)", r"{\1}", norm_path)
                        if not norm_path.endswith("/") and not "{" in norm_path:
                            norm_path = norm_path.rstrip("/")
                        
                        clean_path = re.sub(r"[^a-zA-Z0-9_]+", "_", norm_path).strip("_").lower()
                        route_id = f"rte_get_{clean_path}" if clean_path else "rte_get_root"

                        self.routes.append({
                            "route_id": route_id,
                            "method": "GET",
                            "path": norm_path,
                            "handler": handler_name,
                            "file": self.rel_path,
                            "line": elt.lineno,
                            "auth_required": False,
                            "authz_checks": []
                        })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        is_model = False
        owner_field = None
        base_names = []
        for base in node.bases:
            name = getattr(base, "id", "") or getattr(base, "attr", "")
            base_names.append(name)
            if name in ["Base", "Model", "SQLModel", "DeclarativeBase", "db.Model", "models.Model"]:
                is_model = True

        table_name = node.name.lower() + "s"
        fields = []
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_name = target.id
                        fields.append(field_name)
                        if field_name == "__tablename__" and isinstance(item.value, ast.Constant):
                            table_name = str(item.value.value)
                        if field_name in ["user_id", "owner_id", "created_by", "account_id", "customer_id", "buyer_id", "user", "owner", "author"]:
                            owner_field = field_name
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                fields.append(field_name)
                if field_name in ["user_id", "owner_id", "created_by", "account_id", "customer_id", "buyer_id", "user", "owner", "author"]:
                    owner_field = field_name

        if is_model or "table" in [b.lower() for b in base_names] or any(f in ["id", "created_at"] for f in fields):
            self.models.append({
                "name": node.name,
                "table": table_name,
                "owner_field": owner_field,
                "file": self.rel_path
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        decorators = extract_decorators(node)
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                caller = getattr(dec.func.value, "id", "") or getattr(dec.func.value, "attr", "")
                method = dec.func.attr.lower()
                if method in ["get", "post", "put", "patch", "delete", "route", "options", "head"]:
                    path = "/"
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        path = str(dec.args[0].value)
                    
                    auth_required = False
                    authz_checks = []

                    if hasattr(dec, "keywords"):
                        for kw in dec.keywords:
                            if kw.arg == "methods" and isinstance(kw.value, ast.List) and kw.value.elts:
                                first_elt = kw.value.elts[0]
                                if isinstance(first_elt, ast.Constant):
                                    method = str(first_elt.value).lower()
                            elif kw.arg == "dependencies" and isinstance(kw.value, ast.List):
                                for elt in kw.value.elts:
                                    dep_call = elt if isinstance(elt, ast.Call) else None
                                    if dep_call and dep_call.args:
                                        first_arg = dep_call.args[0]
                                        dep_name = getattr(first_arg, "id", "") or getattr(first_arg, "attr", "") or "dep_guard"
                                        auth_required = True
                                        authz_checks.append(dep_name)
                    
                    depends_list = extract_fastapi_depends(node)
                    for dep in depends_list:
                        dep_lower = dep.lower()
                        if any(k in dep_lower for k in ["auth", "user", "token", "login", "jwt", "session", "admin", "require", "perm", "role", "guard", "protect", "access", "scope", "security"]):
                            auth_required = True
                            authz_checks.append(dep)
                            self.auth_mechanisms.append({
                                "name": dep,
                                "kind": "authentication" if any(k in dep_lower for k in ["auth", "user", "login", "token", "jwt", "session"]) else "authorization",
                                "location": f"{self.rel_path}:{node.lineno}",
                                "description": f"FastAPI dependency guard {dep} on {node.name}"
                            })

                    for d in decorators:
                        d_lower = d.lower()
                        if any(k in d_lower for k in ["login", "auth", "token", "require", "guard", "admin", "protect", "permission", "role", "access"]):
                            auth_required = True
                            authz_checks.append(d)
                            self.auth_mechanisms.append({
                                "name": d,
                                "kind": "authentication" if any(k in d_lower for k in ["auth", "login", "token", "jwt"]) else "authorization",
                                "location": f"{self.rel_path}:{node.lineno}",
                                "description": f"Decorator guard applied to {node.name}"
                            })

                    # Inline identity usage (Flask-style): handlers that read
                    # the session / current_user / auth tokens inside their
                    # body authenticate the caller even without a decorator.
                    if not auth_required:
                        param_names = set()
                        try:
                            param_names = {a.arg.lower() for a in getattr(node.args, "args", [])}
                            param_names |= {a.arg.lower() for a in getattr(node.args, "kwonlyargs", [])}
                        except Exception:
                            pass
                        identity_names = {"session", "current_user", "jwt", "auth", "login", "logged_in", "flask_login"}
                        body_names = set()
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.Name):
                                body_names.add(sub.id.lower())
                            elif isinstance(sub, ast.Attribute):
                                body_names.add(sub.attr.lower())
                        used_identity = (body_names & identity_names) or any(
                            n in body_names for n in ("user_id", "authorization") if n not in param_names
                        )
                        if used_identity:
                            auth_required = True
                            authz_checks.append("session_identity_check")
                            self.auth_mechanisms.append({
                                "name": "session_identity_check",
                                "kind": "authentication",
                                "location": f"{self.rel_path}:{node.lineno}",
                                "description": f"Inline session/identity usage detected in handler {node.name}"
                            })

                    http_method = "GET" if method == "route" else method.upper()
                    clean_path = re.sub(r"[^a-zA-Z0-9_]+", "_", path).strip("_").lower()
                    route_id = f"rte_{http_method.lower()}_{clean_path}" if clean_path else f"rte_{http_method.lower()}_root"

                    self.routes.append({
                        "route_id": route_id,
                        "method": http_method,
                        "path": path,
                        "handler": node.name,
                        "file": self.rel_path,
                        "line": node.lineno,
                        "auth_required": auth_required,
                        "authz_checks": authz_checks
                    })
        self.generic_visit(node)

def parse_with_tree_sitter(content_bytes: bytes, filepath: str, repo_root: str) -> Dict[str, Any]:
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(content_bytes)
    rel_path = os.path.relpath(filepath, repo_root)
    routes = []
    models = []
    auth_mechanisms = []
    frameworks = set()

    code_text = content_bytes.decode("utf-8", errors="ignore")
    if "fastapi" in code_text.lower():
        frameworks.add("fastapi")
    if "flask" in code_text.lower():
        frameworks.add("flask")
    if "django" in code_text.lower():
        frameworks.add("django")

    def walk_nodes(node):
        if node.type == "decorator":
            dec_text = code_text[node.start_byte:node.end_byte]
            m = re.search(r'\.(get|post|put|patch|delete|route)\s*\(\s*["\']([^"\']+)["\']', dec_text, re.IGNORECASE)
            if m:
                raw_verb = m.group(1).upper()
                method_m = re.search(r'methods\s*=\s*\[\s*["\']([A-Za-z]+)["\']', dec_text, re.IGNORECASE)
                if method_m:
                    method_str = method_m.group(1).upper()
                elif raw_verb == "ROUTE":
                    method_str = "GET"
                else:
                    method_str = raw_verb
                path_str = m.group(2)
                clean_p = re.sub(r"[^a-zA-Z0-9_]+", "_", path_str).strip("_").lower()
                route_id = f"rte_{method_str.lower()}_{clean_p}" if clean_p else f"rte_{method_str.lower()}_root"
                
                fn_name = "handler"
                parent = node.parent
                if parent:
                    found_dec = False
                    for c in parent.children:
                        if c == node:
                            found_dec = True
                        elif found_dec and c.type == "identifier":
                            fn_name = code_text[c.start_byte:c.end_byte]
                            break
                        elif found_dec and c.type == "function_definition":
                            for sc in c.children:
                                if sc.type == "identifier":
                                    fn_name = code_text[sc.start_byte:sc.end_byte]
                                    break
                            break

                auth_req = bool(re.search(r'(?:Depends|Security|login|auth|token|admin|require|guard|protect|access)', dec_text, re.IGNORECASE))
                auth_checks = ["detected_guard"] if auth_req else []

                routes.append({
                    "route_id": route_id,
                    "method": method_str,
                    "path": path_str,
                    "handler": fn_name,
                    "file": rel_path,
                    "line": node.start_point[0] + 1,
                    "auth_required": auth_req,
                    "authz_checks": auth_checks
                })

        elif node.type == "class_definition":
            class_name = ""
            for c in node.children:
                if c.type == "identifier":
                    class_name = code_text[c.start_byte:c.end_byte]
                    break
            class_body = code_text[node.start_byte:node.end_byte]
            owner_m = re.search(r'(user_id|owner_id|account_id|customer_id|user|owner)\s*[:=]', class_body)
            owner_f = owner_m.group(1) if owner_m else None
            if class_name and ("Base" in class_body or "Model" in class_body or owner_f):
                models.append({
                    "name": class_name,
                    "table": class_name.lower() + "s",
                    "owner_field": owner_f,
                    "file": rel_path
                })

        for child in node.children:
            walk_nodes(child)

    walk_nodes(tree.root_node)
    return {
        "routes": routes,
        "models": models,
        "auth_mechanisms": auth_mechanisms,
        "frameworks": frameworks
    }

def analyze_repository(repo_path: str, max_files: int = 200, include_globs: Optional[List[str]] = None, enable_semgrep: bool = False) -> Dict[str, Any]:
    py_files = find_python_files(repo_path, include_globs=include_globs, max_files=max_files)
    all_routes = []
    all_models = []
    all_auth = []
    frameworks = set()
    entry_points = []
    warnings = []

    deps = parse_dependencies(repo_path)
    for dep_name in deps.keys():
        if dep_name in ["fastapi", "flask", "django", "sqlalchemy", "sqlmodel", "tortoise", "drf", "djangorestframework"]:
            frameworks.add(dep_name)

    for filepath in py_files:
        rel = os.path.relpath(filepath, repo_path)
        if rel in ["main.py", "app.py", "wsgi.py", "asgi.py", "manage.py", "server.py"]:
            entry_points.append(rel)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=filepath)
            visitor = CodeVisitor(filepath, repo_path)
            visitor.visit(tree)
            all_routes.extend(visitor.routes)
            all_models.extend(visitor.models)
            all_auth.extend(visitor.auth_mechanisms)
            frameworks.update(visitor.frameworks)
        except SyntaxError as se:
            warnings.append(f"File {rel} syntax error: {str(se)}. Tolerated using Tree-sitter parser.")
            try:
                with open(filepath, "rb") as bf:
                    content_bytes = bf.read()
                ts_res = parse_with_tree_sitter(content_bytes, filepath, repo_path)
                all_routes.extend(ts_res["routes"])
                all_models.extend(ts_res["models"])
                all_auth.extend(ts_res["auth_mechanisms"])
                frameworks.update(ts_res["frameworks"])
            except Exception:
                warnings.append(f"Tree-sitter could not recover {rel}")
        except Exception:
            continue

    if not entry_points and py_files:
        entry_points.append(os.path.relpath(py_files[0], repo_path))

    security_findings = run_security_rules_scan(repo_path, py_files, enable_semgrep=enable_semgrep)
    for finding in security_findings:
        warnings.append(f"[{finding['severity']}] {finding['rule_id']} in {finding['file']}:{finding['line']}: {finding['message']}")

    seen_route_ids = {}
    unique_routes = []
    for r in all_routes:
        base_id = r["route_id"]
        if base_id in seen_route_ids:
            seen_route_ids[base_id] += 1
            stem = os.path.splitext(os.path.basename(r.get("file", "route")))[0]
            stem_clean = re.sub(r"[^a-zA-Z0-9_]+", "_", stem).strip("_").lower()
            cand_id = f"{base_id}_{stem_clean}"
            if cand_id in seen_route_ids:
                seen_route_ids[cand_id] += 1
                cand_id = f"{cand_id}_{seen_route_ids[cand_id]}"
            else:
                seen_route_ids[cand_id] = 1
            r["route_id"] = cand_id
        else:
            seen_route_ids[base_id] = 1
        unique_routes.append(r)
    all_routes = unique_routes

    return {
        "files_analyzed": len(py_files),
        "frameworks": sorted(list(frameworks)) if frameworks else ["python"],
        "entry_points": sorted(entry_points),
        "routes": all_routes,
        "models": all_models,
        "auth_mechanisms": all_auth,
        "dependencies": deps,
        "warnings": warnings
    }

def construct_code_graph(analysis: Dict[str, Any], scan_id: str = "scn_default", output_path: Optional[str] = None) -> str:
    g = nx.DiGraph()
    code_nodes = []
    code_edges = []
    node_id_counter = 1

    for route in analysis.get("routes", []):
        curr_id = node_id_counter
        node_id_counter += 1
        r_node_key = f"route:{route['route_id']}"
        g.add_node(r_node_key, type="route", **route)
        code_nodes.append({
            "id": curr_id,
            "scan_id": scan_id,
            "kind": "route",
            "name": route["route_id"],
            "file": route["file"],
            "line": route["line"],
            "props": {"method": route["method"], "path": route["path"]}
        })

        h_curr_id = node_id_counter
        node_id_counter += 1
        h_node_key = f"handler:{route['handler']}:{route['file']}"
        g.add_node(h_node_key, type="function", name=route["handler"], file=route["file"], line=route["line"])
        g.add_edge(r_node_key, h_node_key, relation="handles_route")

        code_nodes.append({
            "id": h_curr_id,
            "scan_id": scan_id,
            "kind": "function",
            "name": route["handler"],
            "file": route["file"],
            "line": route["line"],
            "props": {}
        })
        code_edges.append({
            "id": len(code_edges) + 1,
            "scan_id": scan_id,
            "src": curr_id,
            "dst": h_curr_id,
            "kind": "handles_route",
            "props": {}
        })

        for check in route.get("authz_checks", []):
            c_curr_id = node_id_counter
            node_id_counter += 1
            c_node_key = f"authz:{check}"
            g.add_node(c_node_key, type="authz_check", name=check)
            g.add_edge(h_node_key, c_node_key, relation="guards")
            code_nodes.append({
                "id": c_curr_id,
                "scan_id": scan_id,
                "kind": "authz_check",
                "name": check,
                "file": route["file"],
                "line": route["line"],
                "props": {}
            })
            code_edges.append({
                "id": len(code_edges) + 1,
                "scan_id": scan_id,
                "src": h_curr_id,
                "dst": c_curr_id,
                "kind": "guards",
                "props": {}
            })

    for model in analysis.get("models", []):
        m_curr_id = node_id_counter
        node_id_counter += 1
        m_node_key = f"model:{model['name']}"
        g.add_node(m_node_key, type="db_model", **model)
        code_nodes.append({
            "id": m_curr_id,
            "scan_id": scan_id,
            "kind": "db_model",
            "name": model["name"],
            "file": model["file"],
            "line": 1,
            "props": {"table": model["table"], "owner_field": model.get("owner_field")}
        })
        for route in analysis.get("routes", []):
            if model["name"].lower() in route["path"].lower() or model["table"].lower() in route["path"].lower():
                h_node_key = f"handler:{route['handler']}:{route['file']}"
                g.add_edge(h_node_key, m_node_key, relation="reads")

    for dep_name, dep_ver in analysis.get("dependencies", {}).items():
        d_curr_id = node_id_counter
        node_id_counter += 1
        d_node_key = f"dependency:{dep_name}"
        g.add_node(d_node_key, type="dependency", name=dep_name, version=dep_ver)
        code_nodes.append({
            "id": d_curr_id,
            "scan_id": scan_id,
            "kind": "dependency",
            "name": dep_name,
            "file": "requirements.txt",
            "line": 1,
            "props": {"version": dep_ver}
        })

    graph_payload = {
        "networkx": nx.node_link_data(g, edges="edges"),
        "code_nodes": code_nodes,
        "code_edges": code_edges
    }
    graph_json = json.dumps(graph_payload)
    graph_ref = f"graph://{scan_id}/code"
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(graph_json)
        graph_ref = f"graph://file/{os.path.abspath(output_path)}"
    return graph_ref

def read_skill_content(skill_name: str, skills_dir: str) -> str:
    target = os.path.join(skills_dir, "Claude-BugHunter", "skills", skill_name, "SKILL.md")
    if not os.path.exists(target):
        target = os.path.join(skills_dir, skill_name, "SKILL.md")
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    return ""

class ParsePythonRepositoryTool(BaseTool):
    name: str = "parse_python_repository"
    description: str = "Parses a Python repository directory to extract routes, models, authentication mechanisms, and structure with AST and Tree-sitter fallback."

    def _run(self, repo_path: str, max_files: int = 100) -> str:
        data = analyze_repository(repo_path, max_files=max_files)
        return json.dumps(data)

class BuildCodeGraphTool(BaseTool):
    name: str = "build_code_graph"
    description: str = "Constructs a directed NetworkX code graph conforming to code_nodes and code_edges schema and returns graph URI."

    def _run(self, analysis_json: str, scan_id: str = "scn_default") -> str:
        analysis = json.loads(analysis_json)
        ref = construct_code_graph(analysis, scan_id=scan_id)
        return ref

class QuerySecuritySkillTool(BaseTool):
    name: str = "query_security_skill"
    description: str = "Retrieves methodology from the local Claude-BugHunter security skills library."

    def _run(self, skill_name: str) -> str:
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        content = read_skill_content(skill_name, skills_dir)
        return content[:3000] if content else "Skill not found."
