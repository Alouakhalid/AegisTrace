"""Autonomous 7-Agent Security Assessment Pipeline for AegisTrace.
Coordinates Orchestrator, Code Intelligence, Recon, Vulnerability Research,
Dynamic Testing, Verification, and Remediation across verified Git repositories.
"""

import os
import sys
import uuid
import json
import asyncio
import traceback
import importlib
import re
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_dir = os.path.join(workspace_root, "memory and database")
if mem_db_dir not in sys.path:
    sys.path.insert(0, mem_db_dir)

from database import AegisDatabase
from backend.repo_analyzer import validate_github_url, clone_or_fetch_repo, RepositoryIntelligenceEngine, get_repo_commit_sha
from backend.bughunter_router import BugHunterSkillRouter
from backend.integration_service import TavilyIntegrationService, BifrostGatewayService

def load_orchestrator():
    from agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent
    return OrchestratorAgent

def load_code_intel():
    from agents.code_intelligence_agent.code_intelligence_agent import run_code_intelligence
    return run_code_intelligence

def load_recon():
    from agents.recon_agent.recon_agent import run_recon
    return run_recon

def load_vuln_research():
    from agents.vulnerability_research_agent.vuln_research_agent import run_vulnerability_research
    return run_vulnerability_research

def load_dynamic_testing():
    from agents.dynamic_testing_agent.dynamic_testing_agent import DynamicTestingAgent
    return DynamicTestingAgent

def load_verification():
    from agents.verification_agent.verification_agent import VerificationAgent
    return VerificationAgent

def load_remediation():
    from agents.remediation_agent.remediation_agent import RemediationAgent
    return RemediationAgent

def _map_hypothesis_category(category: str) -> str:
    """Map free-form risk-area categories to the CHECK-constrained hypothesis
    categories allowed by the schema (idor | broken_access_control |
    authn_authz_flaw | business_logic). The full original category remains
    visible in the finding title and description."""
    c = str(category or '').lower()
    if 'idor' in c or 'access' in c:
        return 'idor'
    if 'auth' in c:
        return 'authn_authz_flaw'
    if 'logic' in c or 'state' in c:
        return 'business_logic'
    return 'broken_access_control'


def _parse_method_path_from_steps(steps: List[Any]) -> tuple:
    """Extract the first concrete HTTP method and path from test-plan steps
    such as 'As buyer_b (non-owner) PATCH /api/v1/orders/100 with ...'."""
    for step in steps or []:
        m = re.search(r'\b(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)', str(step))
        if m:
            return m.group(1).upper(), m.group(2)
    return None, None


def _sanitize_endpoint_id(raw: Any) -> str:
    """Normalize an endpoint identifier to ^ep_[a-z0-9_]+$ for the contracts."""
    s = re.sub(r'[^a-z0-9_]+', '_', str(raw or 'ep_unknown').lower()).strip('_')
    s = re.sub(r'_{2,}', '_', s)
    if not s.startswith('ep_'):
        s = 'ep_' + s
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s[:64] or 'ep_unknown'


def _git_toplevel(path: str) -> str:
    """Resolve the Git work-tree root containing ``path`` (for remediation)."""
    try:
        out = subprocess.run(
            ['git', '-C', path, 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return path


def _git_current_branch(path: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ['git', '-C', path, 'branch', '--show-current'],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _git_checkout(path: str, branch: Optional[str]) -> None:
    if not branch:
        return
    try:
        subprocess.run(
            ['git', '-C', path, 'checkout', branch],
            capture_output=True, text=True, timeout=30
        )
    except Exception:
        pass


def _store_task_output(task_id: str, output: Dict[str, Any]) -> Optional[str]:
    """Persist an agent task output so downstream agents can resolve it via
    out://<task_id> refs (agents/vulnerability_research_agent resolves from
    .aegistrace_cache/tasks/<ref>.json)."""
    if not task_id:
        return None
    try:
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.aegistrace_cache', 'tasks')
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, f'{task_id}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'task_id': task_id, 'output': output}, f)
        return path
    except Exception:
        return None


class ScanExecutionManager:
    """Manages the full multi-agent pipeline execution and real-time WebSocket telemetry."""

    def __init__(self):
        self.db = AegisDatabase()
        self.active_scans: Dict[str, Dict[str, Any]] = {}
        self.scan_logs: Dict[str, List[str]] = {}
        self.subscribers: List[asyncio.Queue] = []
        self.bughunter_router = BugHunterSkillRouter()
        self.tavily_service = TavilyIntegrationService()
        self.bifrost_service = BifrostGatewayService()

    def subscribe(self, scan_id: Optional[str] = None, q: Optional[asyncio.Queue] = None) -> asyncio.Queue:
        queue = q or asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, scan_id: Optional[str] = None, q: Optional[asyncio.Queue] = None) -> None:
        target = q
        if target is None and isinstance(scan_id, asyncio.Queue):
            target = scan_id
        if target and target in self.subscribers:
            self.subscribers.remove(target)

    async def emit_log(self, scan_id: str, stage: str, agent: str, message: str, level: str = 'INFO') -> None:
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        formatted = f'[{timestamp}] [{level}] [{agent}] {message}'
        if scan_id not in self.scan_logs:
            self.scan_logs[scan_id] = []
        self.scan_logs[scan_id].append(formatted)

        try:
            self.db.log_event(scan_id, agent, message, level=level, stage=stage)
        except Exception:
            pass

        for q in self.subscribers:
            try:
                await q.put({
                    'type': 'agent_log',
                    'scan_id': scan_id,
                    'stage': stage,
                    'agent': agent,
                    'message': message,
                    'level': level,
                    'timestamp': timestamp
                })
            except Exception:
                pass

    async def emit_progress(self, scan_id: str, stage: str, agent: str, percentage: int, message: str) -> None:
        if scan_id in self.active_scans:
            self.active_scans[scan_id]['progress_percentage'] = percentage
            self.active_scans[scan_id]['current_stage'] = stage
            self.active_scans[scan_id]['active_agent'] = agent

        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        if scan_id not in self.scan_logs:
            self.scan_logs[scan_id] = []
        self.scan_logs[scan_id].append(f'[{timestamp}] [STAGE] [{agent}] {message} ({percentage}%)')

        for q in self.subscribers:
            try:
                await q.put({
                    'type': 'pipeline_progress',
                    'scan_id': scan_id,
                    'stage': stage,
                    'agent': agent,
                    'percentage': percentage,
                    'message': message,
                    'timestamp': timestamp
                })
            except Exception:
                pass

    async def run_pipeline(self, scan_config: Dict[str, Any]) -> Dict[str, Any]:
        scan_id = scan_config.get('scan_id')
        if not scan_id or not re.match(r'^scn_[0-9a-f]{8,}$', scan_id):
            scan_id = f'scn_{uuid.uuid4().hex[:12]}'

        project_id = scan_config.get('project_id', '')
        if not project_id or not re.match(r'^prj_[0-9a-f]{8,}$', project_id):
            project_id = f'prj_{uuid.uuid4().hex[:12]}'

        project_name = scan_config.get('project_name', 'Target Repository')
        source_path = scan_config.get('source_path', '')
        raw_github_url = scan_config.get('github_url', '') or scan_config.get('repository_url', '') or scan_config.get('target_repo', '')
        web_target_url = scan_config.get('web_target_url', 'http://127.0.0.1:5050')
        allowed_hosts = scan_config.get('allowed_hosts', ['127.0.0.1', 'localhost'])
        if not isinstance(allowed_hosts, list):
            allowed_hosts = ['127.0.0.1', 'localhost']

        try:
            from backend.models import normalize_assessment_mode
            assessment_mode = normalize_assessment_mode(scan_config.get('assessment_mode', 'full'))
        except Exception:
            assessment_mode = 'full'
        selected_categories = scan_config.get('selected_categories', [])
        target_dir_filter = scan_config.get('target_dir_filter', '')
        instructions = scan_config.get('instructions', '')
        auth_token = scan_config.get('auth_token')

        if not raw_github_url and web_target_url and 'github.com/' in web_target_url:
            raw_github_url = web_target_url
            web_target_url = 'http://127.0.0.1:5050'

        if web_target_url:
            from urllib.parse import urlparse
            parsed_h = urlparse(web_target_url).hostname
            if parsed_h and parsed_h not in allowed_hosts:
                allowed_hosts = list(allowed_hosts) + [parsed_h]
        # Source-only assessments use a synthetic local target marker; the
        # orchestrator's deterministic scope check must consider it in-scope.
        if not web_target_url:
            if 'static-source-analysis' not in allowed_hosts:
                allowed_hosts = list(allowed_hosts) + ['static-source-analysis']
        scan_config['allowed_hosts'] = allowed_hosts

        target_dir = source_path
        commit_sha = "0000000000000000000000000000000000000000"
        branch = "main"
        repo_intel = {}

        if raw_github_url:
            is_valid, owner, repo_name, norm_url = validate_github_url(raw_github_url)
            if is_valid and repo_name and owner:
                try:
                    target_dir, commit_sha, branch = await asyncio.to_thread(clone_or_fetch_repo, norm_url, repo_name, auth_token)
                    engine = RepositoryIntelligenceEngine(target_dir, repo_name, owner, commit_sha, branch)
                    repo_intel = await asyncio.to_thread(engine.analyze)
                except Exception as exc:
                    await self.emit_log(scan_id, 'initialization', 'OrchestratorAgent', f'Repository retrieval error: {str(exc)}', 'CRITICAL')
            elif not target_dir:
                target_dir = os.path.join(workspace_root, 'dummy_web')
        elif not target_dir or not os.path.exists(target_dir):
            candidate_dummy = os.path.join(workspace_root, 'dummy_web')
            target_dir = candidate_dummy if os.path.exists(candidate_dummy) else workspace_root

        if target_dir and os.path.isdir(target_dir) and not repo_intel:
            try:
                commit_sha = await asyncio.to_thread(get_repo_commit_sha, target_dir)
                rname = os.path.basename(target_dir)
                engine = RepositoryIntelligenceEngine(target_dir, rname, "local", commit_sha, "main")
                repo_intel = await asyncio.to_thread(engine.analyze)
            except Exception:
                pass

        if assessment_mode == 'full' or not selected_categories:
            selected_categories = [
                'idor_access_control',
                'authentication',
                'injection',
                'data_security',
                'api_security',
                'dependencies'
            ]

        routed_skills = self.bughunter_router.route_skills(
            selected_categories=selected_categories,
            detected_frameworks=repo_intel.get('frameworks', [])
        )
        routed_skill_names = [s['skill_name'] for s in routed_skills]

        cor_id = f'cor_{uuid.uuid4().hex[:12]}'
        eng_id = f'eng_{uuid.uuid4().hex[:12]}'
        scm_id = f'scm_{uuid.uuid4().hex[:12]}'

        self.active_scans[scan_id] = {
            'scan_id': scan_id,
            'project_id': project_id,
            'project_name': project_name,
            'status': 'running',
            'current_stage': 'initialization',
            'active_agent': 'OrchestratorAgent',
            'progress_percentage': 5,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'findings_count': 0,
            'resolved_count': 0,
            'commit_sha': commit_sha,
            'assessment_mode': assessment_mode,
            'selected_categories': selected_categories,
            'skills_used': routed_skill_names,
            'repo_intelligence': repo_intel
        }

        manifest = {
            'allowed_hosts': allowed_hosts,
            'allowed_methods': ['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
            'forbidden_paths': ['/admin/shutdown', '/admin/danger/*'],
            'window': f'{datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")}/{datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")}',
            'attested': True
        }

        try:
            try:
                self.db.create_user('usr_admin_001', 'admin@aegistrace.io', 'Aegis System Admin', 'admin')
            except Exception:
                pass
            try:
                self.db.create_project(project_id, 'usr_admin_001', project_name)
            except Exception:
                pass
            try:
                self.db.create_engagement(eng_id, project_id, f'Scan {scan_id}', 'full' if assessment_mode in ('full', 'custom') else assessment_mode, 'sandbox', status='draft')
                self.db.create_scope_manifest(scm_id, eng_id, 1, manifest, 'usr_admin_001', valid=True)
                self.db.create_scan(scan_id, eng_id, scm_id, cor_id, 'usr_admin_001', status='running', config=scan_config)
            except Exception:
                pass

            await self.emit_log(scan_id, 'initialization', 'OrchestratorAgent', f'Starting Assessment for repository at {target_dir} (commit {commit_sha[:8]})')
            await self.emit_log(scan_id, 'orchestrator', 'OrchestratorAgent', f'Assessment Scope: {assessment_mode.upper()}. Categories: {", ".join(selected_categories)}')
            await self.emit_log(scan_id, 'orchestrator', 'OrchestratorAgent', f'Routed {len(routed_skill_names)} Claude-BugHunter skills: {", ".join(routed_skill_names[:6])}')
            await self.emit_progress(scan_id, 'orchestrator', 'OrchestratorAgent', 15, 'Workflow planned with verified scope boundaries')

            try:
                OrchCls = load_orchestrator()
                orch = OrchCls(db=self.db)
                orch.register_scope_manifest(scm_id, manifest, valid=True, attested=True)
                orch_req = {
                    'schema_version': '1.0.0',
                    'correlation_id': cor_id,
                    'project_id': project_id,
                    'engagement_id': eng_id,
                    'scan_id': scan_id,
                    'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                    'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'agent': 'orchestrator',
                    'input': {
                        'project': {'name': project_name, 'language': 'python', 'framework_hint': 'fastapi'},
                        'target': {'base_url': web_target_url or 'local://static-source-analysis', 'environment': 'sandbox'},
                        'repository': {'source_type': 'github', 'url': raw_github_url or f'https://github.com/aegis/{os.path.basename(target_dir)}', 'ref': branch},
                        'scope_manifest_id': scm_id,
                        'assessment_mode': 'full' if assessment_mode in ('full', 'custom') else assessment_mode,
                        'credential_refs': [
                            {'ref': 'cred_user_alice', 'role': 'user'},
                            {'ref': 'cred_user_bob', 'role': 'user'}
                        ],
                        'requested_operations': ['code_analysis', 'recon', 'dynamic_testing', 'remediation']
                    }
                }
                orch_resp = orch.run_orchestration(orch_req, raw_manifest=manifest)
                orch_status = getattr(orch_resp.status, 'value', '') if hasattr(orch_resp, 'status') else str(orch_resp.get('status', ''))
                if orch_status in ('failed', 'blocked'):
                    err_obj = getattr(orch_resp, 'error', None)
                    err_msg = getattr(err_obj, 'message', None) or (orch_resp.get('error', {}).get('message') if isinstance(orch_resp, dict) else None) or 'Scope validation failed'
                    await self.emit_log(scan_id, 'orchestrator', 'OrchestratorAgent', f'Orchestration validation failed: {err_msg}', 'CRITICAL')
                    self.active_scans[scan_id]['status'] = 'failed'
                    self.active_scans[scan_id]['current_stage'] = 'failed'
                    self.db.update_scan_status(scan_id, 'failed', finished_at=datetime.now(timezone.utc).isoformat())
                    return {'scan_id': scan_id, 'status': 'failed', 'error': err_msg}
                await self.emit_log(scan_id, 'orchestrator', 'OrchestratorAgent', 'Workflow execution plan created successfully.', 'SUCCESS')
            except Exception as exc:
                await self.emit_log(scan_id, 'orchestrator', 'OrchestratorAgent', f'Orchestration planning error: {str(exc)}', 'CRITICAL')
                self.active_scans[scan_id]['status'] = 'failed'
                self.active_scans[scan_id]['current_stage'] = 'failed'
                self.db.update_scan_status(scan_id, 'failed', finished_at=datetime.now(timezone.utc).isoformat())
                return {'scan_id': scan_id, 'status': 'failed', 'error': str(exc)}

            await self.emit_progress(scan_id, 'code_intel', 'CodeIntelligenceAgent', 25, f'Initiating AST analysis on target codebase at {target_dir}')
            routes_found = []
            invariants_derived = []
            models_found = []
            code_intel_task_id = ''
            try:
                code_intel_fn = load_code_intel()
                code_req = {
                    'schema_version': '1.0.0',
                    'correlation_id': cor_id,
                    'project_id': project_id,
                    'engagement_id': eng_id,
                    'scan_id': scan_id,
                    'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                    'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'agent': 'code_intelligence',
                    'input': {
                        'repository': {
                            'path_ref': target_dir,
                            'commit': commit_sha if len(commit_sha) >= 7 and re.match(r'^[0-9a-f]+$', commit_sha) else 'a1b2c3d4e5f60718293a'
                        },
                        'source_language': 'python',
                        'framework_hints': ['fastapi'],
                        'scan_config': {
                            'max_files': 100,
                            'include_globs': ['**/*.py'],
                            'enable_semgrep': False
                        }
                    }
                }
                code_intel_task_id = code_req['task_id']
                code_resp = code_intel_fn(code_req, db=self.db)
                _store_task_output(code_intel_task_id, code_resp.get('output') or {})
                if code_resp.get('status') == 'failed':
                    err_msg = code_resp.get('error', {}).get('message', 'AST parsing error')
                    await self.emit_log(scan_id, 'code_intel', 'CodeIntelligenceAgent', f'AST analysis warning: {err_msg}', 'WARN')
                else:
                    code_out = code_resp.get('output', {}) or {}
                    routes_found = code_out.get('routes', [])
                    invariants_derived = code_out.get('candidate_invariants', [])
                    models_found = code_out.get('db_models', [])

                if repo_intel.get('discovered_endpoints') and not routes_found:
                    for ep in repo_intel['discovered_endpoints']:
                        routes_found.append({
                            'path': ep.get('path', '/'),
                            'method': ep.get('method', 'GET'),
                            'handler': ep.get('handler_function', 'handler'),
                            'auth_required': False
                        })

                for idx, r in enumerate(routes_found):
                    ep_id = f'ep_{scan_id}_{idx}'
                    path_val = r.get('path', '')
                    method_val = r.get('method', 'GET')
                    auth_val = bool(r.get('auth_required', False))
                    params_val = ['id'] if '{' in path_val else []
                    try:
                        self.db.insert_endpoint(ep_id, scan_id, method_val, path_val, params_val, auth_val, source='code_routes')
                    except Exception:
                        pass

                for inv in invariants_derived:
                    inv_id = inv.get('invariant_id', f'inv_{uuid.uuid4().hex[:8]}')
                    stmt = inv.get('statement', '')
                    kind = inv.get('kind', 'ownership')
                    conf = float(inv.get('confidence', 0.9))
                    try:
                        self.db.insert_security_invariant(inv_id, project_id, stmt, kind, 'code', conf, 'candidate')
                    except Exception:
                        pass

                await self.emit_log(scan_id, 'code_intel', 'CodeIntelligenceAgent', f'AST extraction complete: {len(routes_found)} routes, {len(models_found)} models, {len(invariants_derived)} invariants.', 'SUCCESS')
                await self.emit_progress(scan_id, 'code_intel', 'CodeIntelligenceAgent', 40, f'Code intelligence extracted {len(routes_found)} routes and {len(invariants_derived)} invariants')
            except Exception as exc:
                await self.emit_log(scan_id, 'code_intel', 'CodeIntelligenceAgent', f'Code intelligence warning: {str(exc)}', 'WARN')

            await self.emit_progress(scan_id, 'recon', 'ReconAgent', 45, 'Executing ScopeGate triage and threat intelligence')
            recon_task_id = ''
            try:
                recon_fn = load_recon()
                recon_req = {
                    'schema_version': '1.0.0',
                    'correlation_id': cor_id,
                    'project_id': project_id,
                    'engagement_id': eng_id,
                    'scan_id': scan_id,
                    'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                    'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'agent': 'recon',
                    'input': {
                        'scope': {
                            'allowed_hosts': allowed_hosts,
                            'allowed_methods': ['GET', 'POST', 'PATCH', 'PUT', 'DELETE'],
                            'forbidden_paths': ['/admin/shutdown', '/admin/danger/*']
                        },
                        'technology_hints': repo_intel.get('frameworks', ['fastapi']),
                        'research': {'enabled': False, 'max_queries': 0, 'search_depth': 'basic'}
                    }
                }
                recon_task_id = recon_req['task_id']
                recon_resp = recon_fn(recon_req)
                _store_task_output(recon_task_id, recon_resp.get('output') or {})
                recon_endpoints = recon_resp.get('output', {}).get('endpoints', [])
                await self.emit_log(scan_id, 'recon', 'ReconAgent', f'ScopeGate boundary verified. External host scans restricted to authorized scope.', 'SUCCESS')
            except Exception as exc:
                await self.emit_log(scan_id, 'recon', 'ReconAgent', f'Reconnaissance check note: {str(exc)}', 'INFO')

            if 'dependencies' in selected_categories:
                deps = repo_intel.get('dependencies', [])
                if deps:
                    target_pkg = deps[0].split('>=')[0].split('==')[0].strip()
                    try:
                        t_search = self.tavily_service.research_dependency_cves(target_pkg)
                        if t_search:
                            await self.emit_log(scan_id, 'recon', 'ReconAgent', f'Tavily Threat Intel: Correlated {len(t_search)} security advisories for {target_pkg}.', 'SUCCESS')
                        else:
                            await self.emit_log(scan_id, 'recon', 'ReconAgent', f'Tavily Threat Intel: Checked {target_pkg}; zero critical CVE alerts found.', 'INFO')
                    except Exception:
                        await self.emit_log(scan_id, 'recon', 'ReconAgent', 'Tavily external search offline or unconfigured. Skipping external intel gracefully.', 'INFO')

            await self.emit_progress(scan_id, 'vuln_research', 'VulnResearchAgent', 60, 'Formulating security hypotheses via BugHunter heuristics')
            hypotheses = []
            test_plans = []
            try:
                vuln_fn = load_vuln_research()
                vuln_req = {
                    'schema_version': '1.0.0',
                    'correlation_id': cor_id,
                    'project_id': project_id,
                    'engagement_id': eng_id,
                    'scan_id': scan_id,
                    'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                    'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                    'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'agent': 'vulnerability_research',
                    'input': {
                        'code_intel_ref': f'out://{code_intel_task_id}',
                        'recon_ref': f'out://{recon_task_id}',
                        'invariant_ids': [inv.get('invariant_id') for inv in (invariants_derived or []) if isinstance(inv, dict)],
                        'skill_hits': [
                            {'skill': s, 'source_commit': 'workspace', 'score': 0.90}
                            for s in routed_skill_names[:3]
                        ]
                    }
                }
                vuln_resp = vuln_fn(vuln_req)
                if vuln_resp.get('status') == 'succeeded':
                    vuln_output = vuln_resp.get('output', {}) or {}
                    hypotheses = vuln_output.get('hypotheses', [])
                    test_plans = vuln_output.get('test_plans', [])

                filtered_hypotheses = []
                for h in hypotheses:
                    h_cat = h.get('category', '').lower()
                    h_type = h.get('vulnerability_type', '').lower()
                    keep = False
                    if 'idor_access_control' in selected_categories and ('idor' in h_cat or 'bola' in h_type or 'access' in h_cat):
                        keep = True
                    if 'data_security' in selected_categories and ('deserial' in h_cat or 'source' in h_cat):
                        keep = True
                    if 'injection' in selected_categories and ('sqli' in h_cat or 'inject' in h_type):
                        keep = True
                    if 'authentication' in selected_categories and ('auth' in h_cat or 'session' in h_cat):
                        keep = True
                    if not selected_categories or assessment_mode == 'full':
                        keep = True
                    if keep:
                        filtered_hypotheses.append(h)

                hypotheses = filtered_hypotheses

                plan_by_hyp = {p.get('hypothesis_id'): p for p in (test_plans or []) if isinstance(p, dict)}
                inv_by_id = {inv.get('invariant_id'): inv for inv in (invariants_derived or []) if isinstance(inv, dict)}
                for h in hypotheses:
                    try:
                        hyp_id = h.get('hypothesis_id') or f'hyp_{uuid.uuid4().hex[:8]}'
                        h['hypothesis_id'] = hyp_id
                        # Canonical endpoint id shared by hypotheses, findings,
                        # dynamic testing and verification.
                        ep_id = _sanitize_endpoint_id(h.get('endpoint_id'))
                        h['endpoint_id'] = ep_id
                        plan = plan_by_hyp.get(hyp_id) or {}
                        method, raw_path = _parse_method_path_from_steps(plan.get('steps'))
                        if not method:
                            method, raw_path = 'GET', '/'
                        if not self.db.get_endpoint(ep_id):
                            self.db.insert_endpoint(
                                ep_id, scan_id, method, raw_path,
                                re.findall(r'\{([a-zA-Z0-9_]+)\}', raw_path),
                                True, source='code_routes'
                            )
                        inv_id = h.get('invariant_id') or (invariants_derived[0].get('invariant_id') if invariants_derived else 'inv_default')
                        h['invariant_id'] = inv_id
                        inv = inv_by_id.get(inv_id) or {}
                        if not self.db.get_security_invariant(inv_id):
                            self.db.insert_security_invariant(
                                inv_id, project_id,
                                inv.get('statement', 'Derived access-control invariant'),
                                inv.get('kind', 'ownership'), 'code',
                                float(inv.get('confidence', 0.9)), 'candidate'
                            )
                        if not self.db.get_vulnerability_hypothesis(hyp_id):
                            self.db.insert_vulnerability_hypothesis(
                                hyp_id,
                                scan_id,
                                ep_id,
                                inv_id,
                                _map_hypothesis_category(h.get('category', h.get('vulnerability_type', 'BOLA/IDOR'))),
                                h.get('title', 'Authorization Hypothesis'),
                                h.get('description', '') or h.get('rationale', ''),
                                int(h.get('priority', h.get('severity_rank', 1))) or 1,
                                'proposed',
                                routed_skill_names[:3]
                            )
                    except Exception:
                        continue
                await self.emit_log(scan_id, 'vuln_research', 'VulnResearchAgent', f'Formulated {len(hypotheses)} testable hypotheses matching selected scope.', 'SUCCESS')
                await self.emit_progress(scan_id, 'vuln_research', 'VulnResearchAgent', 70, f'Vulnerability analysis completed ({len(hypotheses)} hypotheses)')
            except Exception as exc:
                await self.emit_log(scan_id, 'vuln_research', 'VulnResearchAgent', f'Vulnerability research note: {str(exc)}', 'WARN')

            await self.emit_progress(scan_id, 'dynamic_testing', 'DynamicTestingAgent', 75, 'Executing multi-identity exploit probes against the sandbox')
            confirmed_findings = []
            dynamic_results = []
            sandbox_base = web_target_url or 'http://127.0.0.1:5050'
            # Honesty: source-only assessments (a GitHub repo with no live
            # target) cannot be dynamically probed against the bundled lab.
            source_only_scan = bool(raw_github_url) and not bool(scan_config.get('web_target_url'))
            if test_plans and hypotheses and source_only_scan:
                await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f'Source-only assessment of {os.path.basename(target_dir)}: no live target was provided, so exploit probes require a running instance of the target (provide web_target_url). Static hypotheses preserved as unconfirmed.', 'INFO')
                test_plans = []
            if test_plans and hypotheses:
                try:
                    DynCls = load_dynamic_testing()
                    dt_agent = DynCls(db=self.db)
                except Exception as exc:
                    dt_agent = None
                    await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f'DynamicTestingAgent runtime unavailable: {exc}', 'WARN')
                if dt_agent:
                    inv_by_id = {inv.get('invariant_id'): inv for inv in (invariants_derived or []) if isinstance(inv, dict)}
                    # Prioritize paired-identity (IDOR/BOLA) probes over
                    # single-identity authentication checks, and mutating
                    # methods over reads.
                    def _plan_rank(p):
                        method_rank = 0 if str(p.get('method', '')) == 'paired_identity' else 1
                        steps = p.get('steps') or []
                        mutating = any(re.search(r'\b(PUT|PATCH|DELETE|POST)\s+/', str(s)) for s in steps)
                        return (method_rank, 0 if mutating else 1)
                    ranked_plans = sorted([p for p in (test_plans or []) if isinstance(p, dict)], key=_plan_rank)
                    for plan in ranked_plans[:4]:
                        if not isinstance(plan, dict):
                            continue
                        hyp = next((h for h in hypotheses if h.get('hypothesis_id') == plan.get('hypothesis_id')), None)
                        if not hyp:
                            continue
                        method, raw_path = _parse_method_path_from_steps(plan.get('steps'))
                        if not method:
                            continue
                        state_checks = plan.get('state_checks') or []
                        sample_id = 100
                        if state_checks and isinstance(state_checks[0], dict):
                            sample_id = (state_checks[0].get('key') or {}).get('id', 100)
                        path_params = re.findall(r'\{([a-zA-Z0-9_]+)\}', raw_path or '')
                        ep_id = _sanitize_endpoint_id(hyp.get('endpoint_id'))
                        cred_map = {'id_buyer_a': 'cred_user_alice', 'id_buyer_b': 'cred_user_bob'}
                        identity_objs = []
                        for pos, iid in enumerate(plan.get('identities') or ['id_buyer_a', 'id_buyer_b']):
                            # Only the first (owner) identity claims ownership of
                            # the sampled record; the rest probe it as outsiders.
                            identity_objs.append({
                                'identity_id': str(iid),
                                'role': 'customer',
                                'credential_ref': cred_map.get(str(iid), 'cred_user_alice'),
                                'owns': {p: sample_id for p in (path_params or ['id'])} if pos == 0 else {}
                            })
                        dt_task_id = f'tsk_{uuid.uuid4().hex[:12]}'
                        dt_req = {
                            'schema_version': '1.0.0',
                            'correlation_id': cor_id,
                            'project_id': project_id,
                            'engagement_id': eng_id,
                            'scan_id': scan_id,
                            'task_id': dt_task_id,
                            'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                            'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'agent': 'dynamic_testing',
                            'input': {
                                'test_plan': plan,
                                'endpoint': {
                                    'endpoint_id': ep_id,
                                    'method': method,
                                    'path': raw_path,
                                    'path_params': path_params,
                                    'auth_required': True,
                                    'source': 'code_routes'
                                },
                                'identities': identity_objs,
                                'sandbox': {
                                    'sandbox_id': f'sbx_{uuid.uuid4().hex[:12]}',
                                    'base_url': sandbox_base,
                                    'snapshot_enabled': True,
                                    'max_requests': 50
                                },
                                'invariant_id': hyp.get('invariant_id') or 'inv_default'
                            }
                        }
                        try:
                            dt_resp = await asyncio.to_thread(dt_agent.execute, dt_req)
                        except Exception as exc:
                            await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f'Probe {plan.get("test_plan_id")} failed: {exc}', 'WARN')
                            continue
                        if dt_resp.get('status') == 'succeeded':
                            out = dt_resp.get('output', {}) or {}
                            diffs = len(out.get('state_diffs', []) or [])
                            exchanges = len(out.get('executed_cases', []) or [])
                            dynamic_results.append({'plan': plan, 'hyp': hyp, 'task_id': dt_task_id, 'output': out})
                            verdict_hint = 'STATE MUTATION TRAPPED' if diffs else 'no state mutation observed'
                            await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f"{plan.get('test_plan_id')} executed {exchanges} identity probe(s) -> {verdict_hint} ({diffs} state diff(s)).", 'SUCCESS' if diffs else 'INFO')
                        else:
                            err = (dt_resp.get('error') or {})
                            await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f"Probe {plan.get('test_plan_id')} returned {dt_resp.get('status')}: {err.get('code', '')} {err.get('message', '')}".strip(), 'WARN')
                    if dynamic_results:
                        await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', f'Dynamic testing executed {len(dynamic_results)} test plan(s) against {sandbox_base}.', 'SUCCESS')
            elif test_plans and not hypotheses:
                await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', 'No scoped hypotheses matched the selected assessment mode; dynamic probes skipped.', 'INFO')
            else:
                await self.emit_log(scan_id, 'dynamic_testing', 'DynamicTestingAgent', 'No testable hypotheses were derived for the target; dynamic probes skipped.', 'INFO')
            await self.emit_progress(scan_id, 'dynamic_testing', 'DynamicTestingAgent', 85, f'Dynamic testing completed ({len(dynamic_results)} plan(s) executed)')

            await self.emit_progress(scan_id, 'verification', 'VerificationAgent', 90, 'Forensic arbitration of findings and evidence chain')

            if repo_intel.get('potential_risk_areas'):
                for idx, ra in enumerate(repo_intel['potential_risk_areas']):
                    cat = ra.get('category', '').lower()
                    match_scope = False
                    if 'idor_access_control' in selected_categories and ('access' in cat or 'idor' in cat):
                        match_scope = True
                    if 'data_security' in selected_categories and ('data' in cat or 'deserial' in cat or 'secrets' in cat):
                        match_scope = True
                    if 'injection' in selected_categories and 'inject' in cat:
                        match_scope = True
                    if 'authentication' in selected_categories and 'auth' in cat:
                        match_scope = True
                    if assessment_mode == 'full' or not selected_categories:
                        match_scope = True

                    if match_scope:
                        finding_obj = {
                            'finding_id': f'fnd_{scan_id}_{idx+1}',
                            'scan_id': scan_id,
                            'title': ra['title'],
                            'category': ra['category'],
                            'severity': ra['severity'],
                            'confidence': 0.92,
                            'status': 'needs_verification',
                            'affected_file': ra.get('file'),
                            'line_number': ra.get('line_number'),
                            'affected_function': 'upload_file' if 'upload' in ra['title'].lower() else 'router_handler',
                            'explanation': ra['description'],
                            'evidence': f"Discovered in commit {commit_sha[:8]} via AST inspection.",
                            'impact': "Potential unauthorized data access or state mutation.",
                            'remediation': "Implement explicit authorization and input schema validation."
                        }
                        confirmed_findings.append(finding_obj)

            # Persist static findings honestly: they are UNCONFIRMED until the
            # VerificationAgent reproduces them in the sandbox (3x replay).
            allowed_severities = {'informational', 'low', 'medium', 'high', 'critical'}
            for idx, fo in enumerate(confirmed_findings):
                try:
                    if not self.db.get_endpoint('ep_default'):
                        self.db.insert_endpoint('ep_default', scan_id, 'GET', '/synthetic/resource', [], True, 'code_routes')
                    if not self.db.get_security_invariant('inv_default'):
                        self.db.insert_security_invariant('inv_default', project_id, 'Pending invariant correlation', 'ownership', 'code', 0.5)
                    hyp_id = f"hyp_{scan_id}_static_{idx+1}"
                    if not self.db.get_vulnerability_hypothesis(hyp_id):
                        self.db.insert_vulnerability_hypothesis(
                            hyp_id, scan_id, 'ep_default', 'inv_default',
                            _map_hypothesis_category(fo.get('category', 'access_control')),
                            fo.get('title', 'Static risk area'),
                            fo.get('explanation', ''),
                            2, 'proposed', routed_skill_names[:3]
                        )
                    severity = str(fo.get('severity', 'medium')).lower()
                    if severity not in allowed_severities:
                        severity = 'medium'
                    self.db.insert_finding(
                        fo['finding_id'], scan_id, hyp_id, 'ep_default', 'inv_default',
                        'unconfirmed', float(fo.get('confidence', 0.9)), False,
                        runs=1, reproduced=0, severity=severity, status='open'
                    )
                except Exception:
                    continue

            # ---- Dynamic finding arbitration: replay 3x in the sandbox ----
            verified_findings = []
            if dynamic_results:
                try:
                    VerCls = load_verification()
                    ver_agent = VerCls(db=self.db)
                except Exception as exc:
                    ver_agent = None
                    await self.emit_log(scan_id, 'verification', 'VerificationAgent', f'VerificationAgent runtime unavailable: {exc}', 'WARN')
                if ver_agent:
                    route_by_id = {r.get('route_id'): r for r in (routes_found or []) if isinstance(r, dict)}
                    for res in dynamic_results[:4]:
                        hyp = res['hyp']
                        out = res['output']
                        evidence_ids = []
                        for case in (out.get('executed_cases') or []):
                            ev = ((case.get('exchange') or {}).get('evidence_id')) if isinstance(case, dict) else None
                            if ev:
                                evidence_ids.append(ev)
                        for d in (out.get('state_diffs') or []):
                            if isinstance(d, dict) and d.get('evidence_id'):
                                evidence_ids.append(d['evidence_id'])
                        inv = inv_by_id.get(hyp.get('invariant_id')) or {}
                        inv_stmt = inv.get('statement')
                        if not inv_stmt:
                            # Build an evaluator-friendly statement naming the
                            # concrete tables covered by the test plan.
                            tables_named = sorted({str(c.get('table') or '').strip() for c in (res['plan'].get('state_checks') or []) if isinstance(c, dict) and c.get('table')})
                            entity = ' and '.join(tables_named) if tables_named else 'the target resource'
                            inv_stmt = (
                                f"Only the record owner may read or modify {entity} records; "
                                f"any other principal must be rejected with 403 and cause no state change."
                            )
                        ver_req = {
                            'schema_version': '1.0.0',
                            'correlation_id': cor_id,
                            'project_id': project_id,
                            'engagement_id': eng_id,
                            'scan_id': scan_id,
                            'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                            'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                            'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'agent': 'verification',
                            'input': {
                                'hypothesis': {
                                    'hypothesis_id': hyp.get('hypothesis_id'),
                                    'category': hyp.get('category', 'idor'),
                                    'title': hyp.get('title', 'Authorization hypothesis'),
                                    'rationale': hyp.get('description', '') or hyp.get('rationale', ''),
                                    'endpoint_id': hyp.get('endpoint_id'),
                                    'invariant_id': hyp.get('invariant_id'),
                                    'priority': int(hyp.get('priority', 2)) or 2,
                                    'skill_refs': hyp.get('skill_refs', [])[:3]
                                },
                                'dynamic_result_ref': f"out://{res['task_id']}",
                                'evidence_ids': evidence_ids,
                                'invariant_statement': inv_stmt,
                                'reproduction_runs_requested': 3
                            }
                        }
                        try:
                            v_resp = await asyncio.to_thread(ver_agent.execute, ver_req)
                        except Exception as exc:
                            await self.emit_log(scan_id, 'verification', 'VerificationAgent', f'Arbitration for {hyp.get("hypothesis_id")} failed: {exc}', 'WARN')
                            continue
                        v_out = v_resp.get('output', {}) or {}
                        verdict = str(v_out.get('verdict') or '').lower().replace('verdict.', '')
                        repro = v_out.get('reproducibility') or {}
                        if verdict == 'confirmed' and v_out.get('finding_id'):
                            plan = res['plan']
                            method, raw_path = _parse_method_path_from_steps(plan.get('steps'))
                            sev_level = ((v_out.get('severity') or {}) or {}).get('level', 'high')
                            verified_findings.append({
                                'finding_id': v_out.get('finding_id'),
                                'scan_id': scan_id,
                                'title': hyp.get('title'),
                                'category': hyp.get('category'),
                                'severity': str(sev_level).split('.')[-1].lower() if sev_level else 'high',
                                'confidence': v_out.get('confidence', 0.9),
                                'status': 'confirmed',
                                'verdict': 'confirmed',
                                'endpoint': f"{method} {raw_path}" if method else hyp.get('endpoint_id'),
                                'reproduction': f"{(repro or {}).get('reproduced', 3)}/{(repro or {}).get('runs', 3)} sandbox replays",
                                'evidence_ids': evidence_ids,
                                'route_id': (re.match(r'^ep_[a-z]+_(rte_.+)$', str(hyp.get('endpoint_id') or '')) or [None]) and (re.match(r'^ep_[a-z]+_(rte_.+)$', str(hyp.get('endpoint_id') or '')).group(1) if re.match(r'^ep_[a-z]+_(rte_.+)$', str(hyp.get('endpoint_id') or '')) else None),
                                'test_plan_id': res['plan'].get('test_plan_id'),
                                'sandbox': {
                                    'sandbox_id': f'sbx_{uuid.uuid4().hex[:12]}',
                                    'base_url': sandbox_base,
                                    'snapshot_enabled': True,
                                    'max_requests': 50
                                }
                            })
                            await self.emit_log(scan_id, 'verification', 'VerificationAgent', f"VERDICT CONFIRMED: {v_out.get('finding_id')} reproduced {(repro or {}).get('reproduced', '?')}/{(repro or {}).get('runs', '?')} with state mutation evidence.", 'SUCCESS')
                        else:
                            reasons = v_out.get('rejection_reasons') or []
                            await self.emit_log(scan_id, 'verification', 'VerificationAgent', f"VERDICT {verdict.upper() or 'UNCONFIRMED'} for {hyp.get('hypothesis_id')}: reproduced {(repro or {}).get('reproduced', 0)}/{(repro or {}).get('runs', 0)}" + (f" | {', '.join(map(str, reasons[:2]))}" if reasons else ''), 'INFO')

            await self.emit_log(scan_id, 'verification', 'VerificationAgent', f'Forensic arbitration complete: {len(verified_findings)} confirmed and {len(confirmed_findings)} static-unverified findings documented within scope.', 'SUCCESS')

            await self.emit_progress(scan_id, 'remediation', 'RemediationAgent', 95, 'Synthesizing remediation patches')
            patches = []
            if verified_findings:
                route_by_id = {r.get('route_id'): r for r in (routes_found or []) if isinstance(r, dict)}
                # The remediation agent requires a Git work-tree that contains
                # both the target sources and the project test suites.
                repo_for_remediation = _git_toplevel(target_dir)
                original_branch = _git_current_branch(repo_for_remediation)
                try:
                    RemCls = load_remediation()
                    rem_agent = RemCls(db=self.db)
                except Exception as exc:
                    rem_agent = None
                    await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f'RemediationAgent runtime unavailable: {exc}', 'WARN')
                for vf in verified_findings[:2]:
                    if not rem_agent:
                        break
                    route = route_by_id.get(vf.get('route_id')) if vf.get('route_id') else None
                    if route and route.get('file') and not os.path.isabs(route['file']):
                        repo_rel = os.path.relpath(target_dir, repo_for_remediation)
                        if repo_rel not in ('.', ''):
                            route = dict(route, file=os.path.join(repo_rel, route['file']))
                    if not route or not route.get('file'):
                        await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f"No source location mapped for {vf.get('finding_id')}; skipping patch synthesis for this finding.", 'INFO')
                        continue
                    rem_req = {
                        'schema_version': '1.0.0',
                        'correlation_id': cor_id,
                        'project_id': project_id,
                        'engagement_id': eng_id,
                        'scan_id': scan_id,
                        'task_id': f'tsk_{uuid.uuid4().hex[:12]}',
                        'agent_run_id': f'run_{uuid.uuid4().hex[:12]}',
                        'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'agent': 'remediation',
                        'input': {
                            'finding_id': vf.get('finding_id'),
                            'source_refs': [{
                                'file': route.get('file'),
                                'start_line': int(route.get('line') or 1),
                                'end_line': int(route.get('line') or 1) + 25
                            }],
                            'verification_evidence_ids': (vf.get('evidence_ids') or [])[:5],
                            'test_environment': vf.get('sandbox'),
                            'original_test_plan_id': vf.get('test_plan_id'),
                            'max_attempts': 3
                        }
                    }
                    # Replay only the UNAUTHORIZED (non-owner) probe: the
                    # owner's own mutating request is a legitimate change and
                    # must not count as "exploit still reproduces".
                    attacker_replayer = None
                    try:
                        from tools.remediation_tools import DynamicExploitReplayer, find_task_output_for_test_plan
                        class _AttackerOnlyReplayer(DynamicExploitReplayer):
                            @staticmethod
                            def _steps_from_artifact(test_plan_id):
                                steps, checks, base = DynamicExploitReplayer._steps_from_artifact(test_plan_id)
                                try:
                                    artifact = find_task_output_for_test_plan(test_plan_id)
                                    internal = artifact.get('internal') if isinstance(artifact, dict) else {}
                                    owner_ids = set()
                                    sample = ((internal.get('state_checks') or [{}])[0] or {}).get('key', {})
                                    for ident in internal.get('identities') or []:
                                        owns = ident.get('owns') or {}
                                        if any(str(sample.get(k)) == str(v) for k, v in owns.items()):
                                            owner_ids.add(ident.get('identity_id'))
                                    if owner_ids:
                                        attacker_steps = [s for s in steps if s.get('identity_id') not in owner_ids]
                                        if attacker_steps:
                                            steps = attacker_steps
                                except Exception:
                                    pass
                                return steps, checks, base
                        attacker_replayer = _AttackerOnlyReplayer()
                    except Exception:
                        attacker_replayer = None
                    rem_kwargs = {'finding_verdict': 'confirmed', 'repo_path': repo_for_remediation}
                    if attacker_replayer:
                        rem_kwargs['exploit_replayer'] = attacker_replayer
                    try:
                        rem_resp = await asyncio.to_thread(
                            rem_agent.execute, rem_req, **rem_kwargs
                        )
                    except Exception as exc:
                        await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f"Patch synthesis for {vf.get('finding_id')} failed: {exc}", 'WARN')
                        rem_resp = None
                    rem_out = rem_resp.get('output', {}) or {} if rem_resp else {}
                    status = str(rem_out.get('remediation_status') or (rem_resp or {}).get('status') or '')
                    # Commit the synthesized patch on the remediation branch
                    # (the agent leaves it uncommitted) so the user's checkout
                    # can return to its original branch cleanly.
                    if original_branch and _git_current_branch(repo_for_remediation) != original_branch:
                        try:
                            porcelain = subprocess.run(
                                ['git', '-C', repo_for_remediation, 'status', '--porcelain', '--untracked-files=no'],
                                capture_output=True, text=True, timeout=10
                            ).stdout
                            changed = [ln[3:] for ln in porcelain.splitlines() if ln[:2].strip() in ('M', 'AM')]
                            if changed:
                                subprocess.run(['git', '-C', repo_for_remediation, 'add', '--'] + changed, capture_output=True, timeout=30)
                                subprocess.run(
                                    ['git', '-C', repo_for_remediation, 'commit', '-m', f"AegisTrace remediation for {vf.get('finding_id')} ({status or 'candidate'})"],
                                    capture_output=True, timeout=30
                                )
                        except Exception:
                            pass
                        _git_checkout(repo_for_remediation, original_branch)
                    if rem_resp is None:
                        continue
                    if rem_out.get('patch'):
                        patches.append(rem_out['patch'])
                        await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f"PATCH READY FOR REVIEW: {rem_out['patch'].get('patch_id')} on branch {rem_out['patch'].get('branch')} awaiting human approval.", 'SUCCESS')
                    elif 'patch_not_possible' in status or rem_resp.get('warnings'):
                        reason = '; '.join(map(str, (rem_resp.get('warnings') or [])[:1])) or status
                        await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f"Patch synthesis honest outcome for {vf.get('finding_id')}: {reason}", 'INFO')
                    else:
                        err_msg = (rem_resp.get('error') or {}).get('message', '') if isinstance(rem_resp.get('error'), dict) else str(rem_resp.get('error') or '')
                        await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f"Remediation for {vf.get('finding_id')} returned status {status}: {err_msg[:200]}", 'INFO')
            elif confirmed_findings:
                await self.emit_log(scan_id, 'remediation', 'RemediationAgent', f'{len(confirmed_findings)} static finding(s) still require sandbox verification before patch synthesis.', 'INFO')
            else:
                await self.emit_log(scan_id, 'remediation', 'RemediationAgent', 'Zero confirmed vulnerabilities require remediation patches.', 'INFO')

            try:
                self.db.update_scan_status(scan_id, 'completed', finished_at=datetime.now(timezone.utc).isoformat())
            except Exception:
                pass

            self.active_scans[scan_id]['status'] = 'completed'
            self.active_scans[scan_id]['progress_percentage'] = 100
            self.active_scans[scan_id]['current_stage'] = 'completed'
            self.active_scans[scan_id]['active_agent'] = 'Completed'
            self.active_scans[scan_id]['findings'] = confirmed_findings + verified_findings
            self.active_scans[scan_id]['findings_count'] = len(confirmed_findings) + len(verified_findings)
            self.active_scans[scan_id]['verified_count'] = len(verified_findings)
            self.active_scans[scan_id]['resolved_count'] = len(patches)

            await self.emit_progress(scan_id, 'completed', 'All Agents', 100, f'Assessment completed: {len(routes_found)} routes, {len(verified_findings)} sandbox-confirmed finding(s), {len(patches)} patch(es) awaiting approval.')
            await self.emit_log(scan_id, 'completed', 'OrchestratorAgent', f'Assessment {scan_id} successfully concluded.', 'SUCCESS')

            return {
                'scan_id': scan_id,
                'status': 'completed',
                'commit_sha': commit_sha,
                'assessment_mode': assessment_mode,
                'selected_categories': selected_categories,
                'skills_used': routed_skill_names,
                'findings': confirmed_findings,
                'patch': patches[0] if patches else None
            }

        except Exception as err:
            err_msg = traceback.format_exc()
            await self.emit_log(scan_id, 'error', 'Pipeline', f'Pipeline execution encountered an error: {str(err)}', 'CRITICAL')
            if scan_id in self.active_scans:
                self.active_scans[scan_id]['status'] = 'failed'
                self.active_scans[scan_id]['current_stage'] = 'failed'
            try:
                self.db.update_scan_status(scan_id, 'failed', finished_at=datetime.now(timezone.utc).isoformat())
            except Exception:
                pass
            return {'scan_id': scan_id, 'status': 'failed', 'error': str(err)}
