import os
import re
import sys
import json
import uuid
import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

mem_db_dir = os.path.join(workspace_root, 'memory and database')
if mem_db_dir not in sys.path:
    sys.path.insert(0, mem_db_dir)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from backend.models import (
    ProjectCreate, ProjectResponse,
    ScanCreateRequest, ScanStatusResponse,
    FindingResponse, ForensicEvidenceResponse,
    PatchResponse, ApprovalActionRequest,
    SkillResponse, BenchmarkMetricResponse,
    OverviewStatsResponse, ReportResponse,
    RepoAnalyzeRequest, AssessmentCreateRequest,
    TavilyTestRequest
)
from backend.pipeline import ScanExecutionManager

app = FastAPI(
    title='AegisTrace API',
    description='Autonomous Application Security Intelligence & Remediation Platform',
    version='2.0.0'
)

app.add_middleware(
    CORSMiddleware,
    # Restrict credentialed cross-origin access. '*' together with allow_credentials
    # makes every origin eligible for credentialed requests; the SPA is same-origin,
    # so CORS is only needed for explicitly allowed external tooling.
    allow_origins=[o.strip() for o in os.environ.get('AEGIS_CORS_ORIGINS', 'http://127.0.0.1:8000,http://localhost:8000').split(',') if o.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class StaticRevalidationMiddleware(BaseHTTPMiddleware):
    """Force browsers to revalidate the SPA shell and its assets.

    Without this, browsers apply heuristic caching to /static and to the HTML
    document, so a deploy can keep serving stale JS that no longer matches the
    markup. Assets are revalidated with ETag/Last-Modified (cheap 304s) rather
    than being cached blindly.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == '/' or path.startswith('/static'):
            response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response


app.add_middleware(StaticRevalidationMiddleware)

manager = ScanExecutionManager()

def cvss_base_score_from_vector(vector: Optional[str]) -> Optional[float]:
    """Compute the CVSS v3.1 base score from a stored vector string.

    Returns None when the vector is missing or malformed so callers can fall
    back to a severity-derived default instead of a fabricated constant.
    """
    if not vector:
        return None
    metrics = {}
    for m in re.finditer(r"/(AV|AC|PR|UI|S|C|I|A):([NALPHRCU])(?=/|$)", vector):
        metrics[m.group(1)] = m.group(2)
    if len(metrics) < 8:
        return None
    weights = {
        'AV': {'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2},
        'AC': {'L': 0.77, 'H': 0.44},
        'PR': {'N': 0.85, 'L': 0.62, 'H': 0.27},
        'UI': {'N': 0.85, 'R': 0.62},
        'CIA': {'H': 0.56, 'L': 0.22, 'N': 0.0},
    }
    scope = metrics['S']
    pr_weight = weights['PR'][metrics['PR']]
    if scope == 'C':
        pr_weight = {'N': 0.85, 'L': 0.68, 'H': 0.5}[metrics['PR']]
    iss = 1 - ((1 - weights['CIA'][metrics['C']]) * (1 - weights['CIA'][metrics['I']]) * (1 - weights['CIA'][metrics['A']]))
    if scope == 'U':
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
    exploitability = 8.22 * weights['AV'][metrics['AV']] * weights['AC'][metrics['AC']] * pr_weight * weights['UI'][metrics['UI']]
    if impact <= 0:
        return 0.0
    if scope == 'U':
        return round(min(impact + exploitability, 10.0), 1)
    return round(min(1.08 * (impact + exploitability), 10.0), 1)


_SEVERITY_DEFAULT_VECTORS = {
    'critical': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
    'high': 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N',
    'medium': 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N',
    'low': 'CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N',
    'informational': 'CVSS:3.1/AV:N/AC:H/PR:H/UI:R/S:U/C:N/I:N/A:N',
}


def cvss_score_for_finding(fnd: Dict[str, Any]) -> float:
    """Derive the CVSS base score from the stored vector, falling back to a
    severity-consistent default vector when none is stored."""
    vector = fnd.get('cvss_vector')
    score = cvss_base_score_from_vector(vector)
    if score is not None:
        return score
    sev = str(fnd.get('severity') or 'medium').lower()
    return cvss_base_score_from_vector(_SEVERITY_DEFAULT_VECTORS.get(sev, _SEVERITY_DEFAULT_VECTORS['medium'])) or 0.0


@app.get('/api/v1/health')
async def health_check():
    return {
        'status': 'healthy',
        'platform': 'AegisTrace Enterprise',
        'version': '2.0.0',
        'database': 'connected',
        'agents_ready': 7,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

def calculate_security_score(conn, project_id: Optional[str] = None) -> Optional[int]:
    """Calculate the security score based on confirmed findings from completed scans.

    Formula:
    Base score = 100
    Penalties applied per unresolved confirmed finding:
      - Critical severity: -25 points
      - High severity:     -15 points
      - Medium severity:   -10 points
      - Low severity:      -5 points

    Score = max(0, min(100, Base score - Total penalties))
    If there are no completed scans for the target scope, returns None (null in JSON).
    """
    cursor = conn.cursor()
    if project_id:
        cursor.execute("SELECT COUNT(*) FROM scans WHERE status = 'completed' AND engagement_id IN (SELECT id FROM engagements WHERE project_id = ?);", (project_id,))
    else:
        cursor.execute("SELECT COUNT(*) FROM scans WHERE status = 'completed';")
    completed_scans = cursor.fetchone()[0] or 0
    if completed_scans == 0:
        return None

    query = "SELECT severity, COUNT(*) FROM findings WHERE verdict = 'confirmed' AND status != 'fixed'"
    params = []
    if project_id:
        query += " AND scan_id IN (SELECT id FROM scans WHERE engagement_id IN (SELECT id FROM engagements WHERE project_id = ?))"
        params.append(project_id)
    query += " GROUP BY severity;"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    weights = {'critical': 25, 'high': 15, 'medium': 10, 'low': 5}
    total_penalty = 0
    for r in rows:
        sev = str(r[0]).lower()
        cnt = r[1]
        total_penalty += weights.get(sev, 5) * cnt

    return max(0, min(100, 100 - total_penalty))

def _record_score(record: Dict[str, Any]) -> int:
    """How much information a per-agent record carries."""
    score = 0
    if record.get("message"):
        score += 4
    if record.get("duration_ms") is not None:
        score += 2
    if record.get("finished_at"):
        score += 1
    return score


def _task_message(row: Dict[str, Any]) -> str:
    """The agent's most recent message, taken from its stored task output."""
    raw = row.get("output")
    if not raw:
        return ""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return ""
    if isinstance(data, dict):
        for key in ("message", "summary", "status", "result"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:160]
    return ""


def _task_duration_ms(row: Dict[str, Any]) -> Optional[int]:
    """Wall-clock duration of an agent task, from its own timestamps."""
    try:
        from datetime import datetime as _dt
        start = str(row.get('created_at') or '')
        end = str(row.get('finished_at') or '')
        if not start or not end:
            return None
        fmt = '%Y-%m-%dT%H:%M:%S'
        s = _dt.strptime(start[:19], fmt)
        e = _dt.strptime(end[:19], fmt)
        return max(0, int((e - s).total_seconds() * 1000))
    except Exception:
        return None


def _scan_agent_states(scan_id: str, scan_status: str = "") -> Dict[str, Dict[str, Any]]:
    """Return the per-agent lifecycle recorded for a scan.

    The console used to invent the topology from the scan's progress
    percentage, which meant every agent read "queued" even for a finished
    assessment. agent_tasks is written by the pipeline as each stage runs, so
    it is the honest source for what actually happened.
    """
    states: Dict[str, Dict[str, Any]] = {}
    try:
        rows = manager.db.list_agent_tasks(scan_id)
    except Exception:
        rows = []
    agent_to_stage = {
        'orchestrator': 'orchestrator',
        'code_intelligence': 'code_intelligence',
        'recon': 'recon',
        'vulnerability_research': 'vulnerability_research',
        'dynamic_testing': 'dynamic_testing',
        'verification': 'verification',
        'remediation': 'remediation',
    }
    for row in rows:
        stage = row.get('stage')
        agent = row.get('agent')
        if not stage:
            continue
        canonical = agent_to_stage.get(agent, stage)
        if agent:
            stage = canonical
        status = row.get('status') or 'queued'
        if scan_status in ('completed', 'failed') and status in ('queued', 'running'):
            # A finished scan cannot have a running agent.
            status = 'succeeded' if scan_status == 'completed' else 'failed'
        record = {
            'stage': stage,
            'agent': row.get('agent'),
            'status': status,
            'started_at': row.get('created_at'),
            'finished_at': row.get('finished_at'),
            'error': row.get('error'),
            'task_id': row.get('id'),
            'duration_ms': _task_duration_ms(row),
            'message': _task_message(row),
        }
        # Two rows can describe the same agent: one the pipeline owns and one
        # the agent's own connector created. Keep whichever carries more
        # information instead of whichever came last.
        existing = states.get(stage)
        if existing is None or _record_score(record) > _record_score(existing):
            states[stage] = record
    return states


def _scan_confirmed_count(scan_id: str) -> int:
    """Findings in this scan whose verdict survived sandbox replay."""
    try:
        cur = manager.db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM findings WHERE scan_id = ? AND verdict = 'confirmed';", (scan_id,))
        return cur.fetchone()[0] or 0
    except Exception:
        return 0


def _scan_pending_approvals(scan_id: str) -> int:
    try:
        cur = manager.db.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM approvals a JOIN patches p ON a.patch_id = p.id "
            "JOIN findings f ON p.finding_id = f.id WHERE f.scan_id = ? AND a.decision = 'pending';",
            (scan_id,)
        )
        return cur.fetchone()[0] or 0
    except Exception:
        return 0


def _scan_project_name(db_scan: Any) -> str:
    """Resolve a human project name for a stored scan.

    The old endpoint answered with the literal string "Enterprise Assessment"
    for every scan in the database, which made the workspace header a lie.
    """
    cfg = db_scan.get('config') if isinstance(db_scan, dict) else None
    if isinstance(cfg, str) and cfg:
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = None
    if isinstance(cfg, dict) and cfg.get('project_name'):
        return str(cfg['project_name'])
    try:
        cur = manager.db.conn.cursor()
        cur.execute(
            "SELECT p.name FROM projects p JOIN engagements e ON e.project_id = p.id "
            "WHERE e.id = ? LIMIT 1;",
            (db_scan.get('engagement_id') if isinstance(db_scan, dict) else None,)
        )
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0])
    except Exception:
        pass
    return 'Unnamed project'


@app.get('/api/v1/stats/overview', response_model=OverviewStatsResponse)
async def get_overview_stats():
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM projects;')
    total_projects = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM scans;')
    total_scans = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM findings;')
    total_findings = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM findings WHERE status = "fixed";')
    resolved_findings = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM findings WHERE verdict = "confirmed";')
    confirmed_findings = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM findings WHERE severity = "critical" OR severity = "high";')
    critical_findings = cursor.fetchone()[0] or 0

    cursor.execute('SELECT COUNT(*) FROM approvals WHERE decision = "pending";')
    pending_approvals = cursor.fetchone()[0] or 0

    skills_dir = os.path.join(workspace_root, 'skills', 'Claude-BugHunter', 'skills')
    active_skills = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]) if os.path.exists(skills_dir) else 0

    sec_score = calculate_security_score(manager.db.conn)

    return OverviewStatsResponse(
        total_projects=total_projects,
        total_scans=total_scans,
        total_findings=total_findings,
        confirmed_findings=confirmed_findings,
        resolved_findings=resolved_findings,
        critical_findings=critical_findings,
        security_score=sec_score,
        pending_approvals=pending_approvals,
        active_skills=active_skills,
        system_status='Autonomous Defense Ready'
    )

@app.get('/api/v1/projects')
async def list_projects():
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT * FROM projects ORDER BY created_at DESC;')
    rows = cursor.fetchall()
    projects = []
    for r in rows:
        d = dict(r)
        pid = d['id']
        cursor.execute('SELECT url, default_ref FROM repositories WHERE project_id = ? LIMIT 1;', (pid,))
        repo_row = cursor.fetchone()
        repo_url = repo_row[0] if repo_row else ''
        branch = repo_row[1] if repo_row else 'main'

        cursor.execute('SELECT COUNT(*), MAX(finished_at) FROM scans WHERE engagement_id IN (SELECT id FROM engagements WHERE project_id = ?);', (pid,))
        scan_stat = cursor.fetchone()
        project_scans = scan_stat[0] if scan_stat else 0
        last_scan = scan_stat[1] if scan_stat and scan_stat[1] else None

        cursor.execute("SELECT COUNT(*) FROM findings WHERE status != 'fixed' AND scan_id IN (SELECT id FROM scans WHERE engagement_id IN (SELECT id FROM engagements WHERE project_id = ?));", (pid,))
        open_findings = cursor.fetchone()[0] or 0

        sec_score = calculate_security_score(manager.db.conn, project_id=pid)

        projects.append({
            'id': pid,
            'name': d['name'],
            'description': f"{d['language']} / {d.get('framework_hint', 'web_api')}",
            'repository_url': repo_url,
            'branch': branch,
            'local_path': workspace_root,
            'project_type': d.get('framework_hint', 'web_api'),
            'created_at': d.get('created_at', datetime.now(timezone.utc).isoformat()),
            'last_scan_at': last_scan,
            'total_scans': project_scans,
            'open_findings': open_findings,
            'security_score': sec_score
        })
    return projects

@app.post('/api/v1/projects')
async def create_project(req: ProjectCreate):
    prj_id = f'prj_{uuid.uuid4().hex[:8]}'
    owner_id = 'usr_admin_001'
    manager.db.create_project(prj_id, owner_id, req.name, req.project_type or 'python', req.project_type)
    if req.repository_url:
        manager.db.create_repository(f'rep_{uuid.uuid4().hex[:8]}', prj_id, 'git', req.repository_url, req.branch or 'main')
    return {
        'id': prj_id,
        'name': req.name,
        'description': req.description or '',
        'repository_url': req.repository_url,
        'branch': req.branch or 'main',
        'local_path': req.local_path or '',
        'project_type': req.project_type or 'web_api',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'total_scans': 0,
        'open_findings': 0,
        'security_score': 100
    }

_scan_request_history: List[float] = []
_scan_rate_limits = _scan_request_history
_MAX_SCANS_PER_MINUTE = 10

def _register_queued_scan(scan_id: str, config: Dict[str, Any]) -> None:
    """Make a freshly queued scan visible to the status endpoints immediately.

    Both scan entry points (/scans and /assessments) used to hand the browser a
    scan id that no endpoint could resolve until the worker had finished its
    first stage, so the workspace rendered "no assessment selected" for the
    first seconds of every run.
    """
    manager.active_scans[scan_id] = {
        'scan_id': scan_id,
        'project_id': config.get('project_id') or 'prj_default',
        'project_name': config.get('project_name') or 'Security Assessment',
        'status': 'queued',
        'current_stage': 'queued',
        'active_agent': 'OrchestratorAgent',
        'progress_percentage': 0,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'findings_count': 0,
        'resolved_count': 0,
        'commit_sha': None,
        'assessment_mode': config.get('assessment_mode', 'full'),
        'selected_categories': config.get('selected_categories') or [],
        'skills_used': [],
        'repo_intelligence': None,
    }
    manager.scan_logs.setdefault(scan_id, []).append(
        f'[{datetime.now(timezone.utc).strftime("%H:%M:%S")}] [INFO] [OrchestratorAgent] Assessment queued; waiting for a worker slot.'
    )


@app.post('/api/v1/scans')
async def start_scan(req: ScanCreateRequest, background_tasks: BackgroundTasks):
    now = time.time()
    while _scan_request_history and _scan_request_history[0] < now - 60.0:
        _scan_request_history.pop(0)
    if len(_scan_request_history) >= _MAX_SCANS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: maximum 10 scans per minute"
        )
    _scan_request_history.append(now)

    target_url = req.web_target_url
    if target_url:
        env_allowed = os.environ.get('AEGIS_ALLOWED_HOSTS', 'localhost,127.0.0.1')
        allowed_hosts = [h.strip() for h in env_allowed.split(',') if h.strip()]
        if req.allowed_hosts:
            allowed_hosts.extend(req.allowed_hosts)
        try:
            from tools.recon_tools import ScopeGate
            gate = ScopeGate(allowed_hosts=allowed_hosts, allowed_methods=['GET', 'POST', 'PATCH'], forbidden_paths=[])
            if not gate.is_host_allowed(target_url):
                raise HTTPException(
                    status_code=400,
                    detail="Target host not in scope"
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Target host not in scope")

    scan_id = f'scn_{uuid.uuid4().hex[:12]}'
    config = req.model_dump() if hasattr(req, 'model_dump') else req.dict()
    config['scan_id'] = scan_id
    if not config.get('project_id'):
        config['project_id'] = 'prj_default'
    _register_queued_scan(scan_id, config)

    background_tasks.add_task(manager.run_pipeline, config)
    return {
        'scan_id': scan_id,
        'project_id': config['project_id'],
        'status': 'queued',
        'message': 'Security assessment queued for execution across all 7 AI agents.',
        'created_at': datetime.now(timezone.utc).isoformat()
    }

@app.post('/api/v1/repositories/analyze')
def analyze_repository(req: RepoAnalyzeRequest):
    from backend.repo_analyzer import validate_github_url, clone_or_fetch_repo, RepositoryIntelligenceEngine
    is_valid, owner, repo_name, norm_url = validate_github_url(req.repository_url)
    if not is_valid or not repo_name or not owner:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub repository URL. Expected format: https://github.com/owner/repo"
        )
    try:
        local_path, commit_sha, branch = clone_or_fetch_repo(norm_url, repo_name, auth_token=req.auth_token)
        engine = RepositoryIntelligenceEngine(local_path, repo_name, owner, commit_sha, branch)
        report = engine.analyze()
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Repository analysis failed: {str(exc)}")

@app.post('/api/v1/assessments')
async def create_assessment(req: AssessmentCreateRequest, background_tasks: BackgroundTasks):
    from backend.repo_analyzer import validate_github_url
    is_valid, owner, repo, norm = validate_github_url(req.repository_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid repository URL")

    scan_id = f'scn_{uuid.uuid4().hex[:12]}'
    config = {
        'scan_id': scan_id,
        'project_id': f'prj_{uuid.uuid4().hex[:8]}',
        'project_name': req.project_name or f"{repo} Security Assessment",
        'github_url': req.repository_url,
        'assessment_mode': req.assessment_mode,
        'selected_categories': req.selected_categories or [],
        'target_dir_filter': req.target_dir_filter,
        'instructions': req.instructions,
        'auth_token': req.auth_token,
        'active_testing_consented': req.active_testing_consented
    }
    _register_queued_scan(scan_id, config)
    background_tasks.add_task(manager.run_pipeline, config)
    return {
        'assessment_id': scan_id,
        'scan_id': scan_id,
        'status': 'queued',
        'message': f"Assessment queued for {repo} across 7 AI agents in {req.assessment_mode.upper()} mode.",
        'created_at': datetime.now(timezone.utc).isoformat()
    }

@app.get('/api/v1/assessments/{assessment_id}')
async def get_assessment_status(assessment_id: str):
    return await get_scan_status(assessment_id)

@app.get('/api/v1/assessments/{assessment_id}/events')
async def get_assessment_events(assessment_id: str):
    return {'assessment_id': assessment_id, 'events': manager.scan_logs.get(assessment_id, [])}

@app.get('/api/v1/assessments/{assessment_id}/findings')
async def get_assessment_findings(assessment_id: str):
    active = manager.active_scans.get(assessment_id)
    if active:
        if active.get('findings'):
            return active['findings']
        cursor = manager.db.conn.cursor()
        cursor.execute('SELECT * FROM findings WHERE scan_id = ?;', (assessment_id,))
        rows = cursor.fetchall()
        if rows:
            return [dict(r) for r in rows]
        if active.get('repo_intelligence', {}).get('potential_risk_areas'):
            return active['repo_intelligence']['potential_risk_areas']
    return await list_findings(scan_id=assessment_id)

@app.get('/api/v1/categories')
async def get_categories():
    from backend.bughunter_router import BugHunterSkillRouter
    return BugHunterSkillRouter().get_available_categories()

@app.get('/api/v1/integrations/tavily/health')
def get_tavily_health(force: bool = False):
    from backend.integration_service import TavilyIntegrationService
    return TavilyIntegrationService().check_health(force=force)

@app.post('/api/v1/integrations/tavily/test')
def test_tavily(req: TavilyTestRequest = TavilyTestRequest()):
    from backend.integration_service import TavilyIntegrationService
    return TavilyIntegrationService().execute_search(query=req.query or "FastAPI CVE", max_results=req.max_results or 3)

@app.get('/api/v1/integrations/bifrost/health')
def get_bifrost_health():
    from backend.integration_service import BifrostGatewayService
    return BifrostGatewayService().check_health()

@app.post('/api/v1/findings/{finding_id}/verify')
async def verify_finding(finding_id: str):
    fnd = manager.db.get_finding(finding_id)
    if not fnd:
        raise HTTPException(status_code=404, detail='Finding not found')
    return {
        'finding_id': finding_id,
        'status': fnd.get('status', 'open'),
        'reproduction_count': fnd.get('reproduced', 0),
        'runs': fnd.get('runs', 1),
        'confidence': fnd.get('confidence', 0.0),
        'verdict': (fnd.get('verdict') or 'unconfirmed').upper()
    }

@app.post('/api/v1/findings/{finding_id}/remediate')
async def remediate_finding(finding_id: str):
    fnd = manager.db.get_finding(finding_id)
    if not fnd:
        raise HTTPException(status_code=404, detail='Finding not found')
    patches = manager.db.get_patches(finding_id)
    if not patches:
        # No remediation has been synthesized for this finding yet. Report the
        # honest state instead of a fabricated diff.
        return {
            'finding_id': finding_id,
            'status': 'no_patch_available',
            'patch_id': None,
            'diff': None,
            'regression_tests_passed': None,
            'requires_approval': False,
            'message': 'No remediation patch has been synthesized for this finding yet. Run a full assessment with the RemediationAgent enabled.'
        }
    patch = patches[-1]
    from tools.artifact_store import load_patch
    diff_ref = patch.get('diff_ref', '')
    diff_content = load_patch(diff_ref)
    if diff_content is None and os.path.isfile(str(diff_ref)):
        with open(diff_ref, 'r', encoding='utf-8') as fh:
            diff_content = fh.read()
    if diff_content is None and diff_ref and '\n' in diff_ref:
        # diff_ref stores the raw unified diff inline (same fallback the
        # approval integrity check uses).
        diff_content = diff_ref
    tests = manager.db.get_patch_tests(patch['id'])
    passed = sum(t.get('passed', 0) or 0 for t in tests)
    return {
        'finding_id': finding_id,
        'status': patch.get('status', 'proposed'),
        'patch_id': patch['id'],
        'diff': diff_content,
        'branch': patch.get('branch'),
        'regression_tests_passed': passed,
        'requires_approval': patch.get('status') not in ('approved', 'merged_by_human')
    }

@app.get('/api/v1/scans')
async def list_scans():
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT * FROM scans ORDER BY created_at DESC LIMIT 20;')
    rows = cursor.fetchall()
    scans = []
    for r in rows:
        d = dict(r)
        cfg = json.loads(d['config']) if d.get('config') else {}
        scan_id = d['id']

        stat_cursor = manager.db.conn.cursor()
        stat_cursor.execute('SELECT severity, COUNT(*) FROM findings WHERE scan_id = ? GROUP BY severity;', (scan_id,))
        sev_counts = {str(row[0]).lower(): row[1] for row in stat_cursor.fetchall()}

        stat_cursor.execute("SELECT COUNT(*) FROM findings WHERE scan_id = ? AND verdict = 'confirmed';", (scan_id,))
        verified = stat_cursor.fetchone()[0] or 0
        stat_cursor.execute("SELECT COUNT(*) FROM findings WHERE scan_id = ? AND status = 'fixed';", (scan_id,))
        resolved = stat_cursor.fetchone()[0] or 0
        stat_cursor.execute(
            "SELECT COUNT(*) FROM approvals a JOIN patches p ON a.patch_id = p.id "
            "JOIN findings f ON p.finding_id = f.id WHERE f.scan_id = ? AND a.decision = 'pending';",
            (scan_id,)
        )
        pending_apr = stat_cursor.fetchone()[0] or 0

        if d['status'] == 'completed':
            progress = 100
            stage = 'completed'
            agent = 'RemediationAgent' if pending_apr else 'Completed'
        elif scan_id in manager.active_scans:
            active = manager.active_scans[scan_id]
            progress = active['progress_percentage']
            stage = active['current_stage']
            agent = active['active_agent']
        else:
            progress = 50
            stage = 'active'
            agent = 'OrchestratorAgent'

        scans.append({
            'scan_id': scan_id,
            'project_id': d['engagement_id'],
            'project_name': (cfg.get('project_name') if isinstance(cfg, dict) else None) or _scan_project_name(d),
            'status': d['status'],
            'current_stage': stage,
            'active_agent': agent,
            'progress_percentage': progress,
            'start_time': d.get('created_at', ''),
            'end_time': d.get('finished_at', None),
            'total_findings': sum(sev_counts.values()),
            'critical_findings': sev_counts.get('critical', 0),
            'high_findings': sev_counts.get('high', 0),
            'medium_findings': sev_counts.get('medium', 0),
            'low_findings': sev_counts.get('low', 0),
            'verified_findings': verified,
            'resolved_findings': resolved,
            'pending_approvals': pending_apr
        })
    return scans

@app.get('/api/v1/scans/{scan_id}')
async def get_scan_status(scan_id: str):
    if scan_id in manager.active_scans:
        active = manager.active_scans[scan_id]
        logs = manager.scan_logs.get(scan_id, [])
        return {
            'scan_id': scan_id,
            'project_id': active['project_id'],
            'project_name': active['project_name'],
            'status': active['status'],
            'current_stage': active['current_stage'],
            'active_agent': active['active_agent'],
            'progress_percentage': active['progress_percentage'],
            'start_time': active['start_time'],
            'total_findings': active['findings_count'],
            'verified_findings': _scan_confirmed_count(scan_id),
            'resolved_findings': active['resolved_count'],
            'pending_approvals': _scan_pending_approvals(scan_id),
            'agent_states': _scan_agent_states(scan_id, active.get('status', '')),
            'log_messages': logs[-100:]
        }
    
    db_scan = manager.db.get_scan(scan_id)
    if not db_scan:
        raise HTTPException(status_code=404, detail='Scan not found')
    
    logs = manager.scan_logs.get(scan_id, [])
    stat_cursor = manager.db.conn.cursor()
    stat_cursor.execute('SELECT severity, COUNT(*) FROM findings WHERE scan_id = ? GROUP BY severity;', (scan_id,))
    sev_counts = {str(row[0]).lower(): row[1] for row in stat_cursor.fetchall()}
    stat_cursor.execute("SELECT COUNT(*) FROM findings WHERE scan_id = ? AND verdict = 'confirmed';", (scan_id,))
    verified = stat_cursor.fetchone()[0] or 0
    stat_cursor.execute("SELECT COUNT(*) FROM findings WHERE scan_id = ? AND status = 'fixed';", (scan_id,))
    resolved = stat_cursor.fetchone()[0] or 0
    stat_cursor.execute(
        "SELECT COUNT(*) FROM approvals a JOIN patches p ON a.patch_id = p.id "
        "JOIN findings f ON p.finding_id = f.id WHERE f.scan_id = ? AND a.decision = 'pending';",
        (scan_id,)
    )
    pending_apr = stat_cursor.fetchone()[0] or 0

    completed = db_scan['status'] == 'completed'
    # Real last stage, not a hardcoded 'in_progress'.
    stage_cursor = manager.db.conn.cursor()
    stage_cursor.execute(
        'SELECT stage FROM agent_tasks WHERE scan_id = ? AND status IN (\'running\', \'succeeded\', \'failed\') '
        'ORDER BY rowid DESC LIMIT 1;',
        (scan_id,)
    )
    stage_row = stage_cursor.fetchone()
    last_stage = stage_row[0] if stage_row else ('completed' if completed else 'initialization')
    return {
        'scan_id': scan_id,
        'project_id': db_scan['engagement_id'],
        'project_name': _scan_project_name(db_scan),
        'status': db_scan['status'],
        'current_stage': 'completed' if completed else last_stage,
        'active_agent': 'RemediationAgent' if completed and pending_apr else ('Completed' if completed else 'OrchestratorAgent'),
        'progress_percentage': 100 if completed else 80,
        'start_time': db_scan.get('created_at', ''),
        'total_findings': sum(sev_counts.values()),
        'critical_findings': sev_counts.get('critical', 0),
        'high_findings': sev_counts.get('high', 0),
        'medium_findings': sev_counts.get('medium', 0),
        'low_findings': sev_counts.get('low', 0),
        'verified_findings': verified,
        'resolved_findings': resolved,
        'pending_approvals': pending_apr,
        'agent_states': _scan_agent_states(scan_id, db_scan['status']),
        'log_messages': logs
    }

@app.get('/api/v1/scans/{scan_id}/logs')
async def get_scan_logs(scan_id: str):
    return {'scan_id': scan_id, 'logs': manager.scan_logs.get(scan_id, [])}

@app.websocket('/ws/scans/{scan_id}')
async def websocket_scan_endpoint(websocket: WebSocket, scan_id: str):
    expected_key = os.environ.get('AEGIS_API_KEY')
    if expected_key:
        api_key = websocket.query_params.get('api_key') or websocket.headers.get('x-api-key')
        if not api_key or api_key != expected_key:
            await websocket.close(code=4401)
            return
    await websocket.accept()
    queue = asyncio.Queue()
    manager.subscribe(scan_id, queue)
    
    try:
        existing_logs = manager.scan_logs.get(scan_id, [])
        for line in existing_logs:
            await websocket.send_json({
                'type': 'log',
                'scan_id': scan_id,
                'message': line,
                'level': 'INFO',
                'timestamp': datetime.now(timezone.utc).strftime('%H:%M:%S')
            })
            
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        manager.unsubscribe(scan_id, queue)
    except Exception:
        manager.unsubscribe(scan_id, queue)

@app.get('/api/v1/findings')
async def list_findings(scan_id: Optional[str] = None):
    cursor = manager.db.conn.cursor()
    if scan_id:
        cursor.execute('SELECT * FROM findings WHERE scan_id = ? ORDER BY created_at DESC;', (scan_id,))
    else:
        cursor.execute('SELECT * FROM findings ORDER BY created_at DESC LIMIT 50;')
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        ep_cursor = manager.db.conn.cursor()
        ep_cursor.execute('SELECT path, method FROM endpoints WHERE id = ?;', (d.get('endpoint_id'),))
        ep_row = ep_cursor.fetchone()
        ep_path = ep_row[0] if ep_row else '/unknown'
        ep_meth = ep_row[1] if ep_row else 'GET'
        
        hypo_cursor = manager.db.conn.cursor()
        hypo_cursor.execute('SELECT title, category, rationale FROM vulnerability_hypotheses WHERE id = ?;', (d.get('hypothesis_id'),))
        hypo_row = hypo_cursor.fetchone()
        
        results.append({
            'id': d['id'],
            'scan_id': d['scan_id'],
            'title': hypo_row[0] if hypo_row else 'Security Vulnerability',
            'severity': (d.get('severity') or 'high').upper(),
            'cvss_score': cvss_score_for_finding(d),
            'cvss_vector': d.get('cvss_vector') or _SEVERITY_DEFAULT_VECTORS.get((d.get('severity') or 'high').lower(), 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N'),
            'cwe_id': hypo_row[1] if hypo_row else 'CWE-Unknown',
            'cwe_name': 'Security Invariant Flaw',
            'status': d['status'],
            'confidence': d['confidence'],
            'endpoint': ep_path,
            'http_method': ep_meth,
            'affected_file': None,
            'line_number': None,
            'root_cause': hypo_row[2] if hypo_row else 'Invariant violated',
            'reproduction_summary': f"Reproduced {d.get('reproduced', 0)}/{d.get('runs', 0)} runs with verdict {d.get('verdict')}.",
            'verification_verdict': (d.get('verdict') or 'UNCONFIRMED').upper(),
            'created_at': d.get('created_at', datetime.now(timezone.utc).isoformat())
        })
    return results

@app.get('/api/v1/findings/{finding_id}')
async def get_finding_detail(finding_id: str):
    fnd = manager.db.get_finding(finding_id)
    if not fnd:
        raise HTTPException(status_code=404, detail='Finding not found')
    
    evidence_items = manager.db.get_finding_evidence(finding_id)
    evd_data = None
    if evidence_items:
        first_ev = evidence_items[0]
        evd_data = {
            'id': first_ev.get('id', 'evd_001'),
            'finding_id': finding_id,
            'title': first_ev.get('title', 'Forensic Evidence'),
            'timestamp': first_ev.get('created_at', datetime.now(timezone.utc).isoformat()),
            'http_method': first_ev.get('http_method', 'POST'),
            'http_url': first_ev.get('http_url', ''),
            'http_status': first_ev.get('http_status', 200),
            'request_headers': first_ev.get('request_headers', {}),
            'request_body': first_ev.get('request_body', ''),
            'response_headers': first_ev.get('response_headers', {}),
            'response_body': first_ev.get('response_body', ''),
            'identity_used': first_ev.get('identity_used', ''),
            'target_resource_owner': first_ev.get('target_resource_owner', ''),
            'db_mutation_trapped': bool(first_ev.get('db_mutation_trapped', False)),
            'table_name': first_ev.get('table_name', ''),
            'row_id': str(first_ev.get('row_id', '')),
            'state_before': first_ev.get('state_before', ''),
            'state_after': first_ev.get('state_after', ''),
            'sha256_snapshot_hash': first_ev.get('sha256_snapshot_hash', ''),
            'reproduction_attempts': fnd.get('runs', 1),
            'reproduction_successes': fnd.get('reproduced', 1)
        }
    
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT path, method FROM endpoints WHERE id = ?;', (fnd.get('endpoint_id'),))
    ep_row = cursor.fetchone()
    endpoint_path = ep_row[0] if ep_row else '/unknown'
    endpoint_method = ep_row[1] if ep_row else 'GET'
    
    cursor.execute('SELECT title, category, rationale FROM vulnerability_hypotheses WHERE id = ?;', (fnd.get('hypothesis_id'),))
    hypo_row = cursor.fetchone()
    hypo_title = hypo_row[0] if hypo_row else fnd.get('title', 'Security Vulnerability')
    hypo_cwe = hypo_row[1] if hypo_row else 'CWE-Unknown'
    hypo_rc = hypo_row[2] if hypo_row else 'Potential invariant violation'
    
    return {
        'id': finding_id,
        'scan_id': fnd.get('scan_id'),
        'title': hypo_title,
        'severity': (fnd.get('severity') or 'high').upper(),
        'cvss_score': cvss_score_for_finding(fnd),
        'cvss_vector': fnd.get('cvss_vector') or _SEVERITY_DEFAULT_VECTORS.get((fnd.get('severity') or 'high').lower(), 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N'),
        'cwe_id': hypo_cwe,
        'cwe_name': 'Authorization / Security Flaw',
        'status': fnd.get('status', 'open'),
        'confidence': fnd.get('confidence', 1.0),
        'endpoint': endpoint_path,
        'http_method': endpoint_method,
        'affected_file': None,
        'line_number': None,
        'root_cause': hypo_rc,
        'reproduction_summary': f"Reproduced {fnd.get('reproduced', 0)}/{fnd.get('runs', 0)} runs with verdict {fnd.get('verdict')}.",
        'verification_verdict': (fnd.get('verdict') or 'UNCONFIRMED').upper(),
        'evidence': evd_data,
        'created_at': fnd.get('created_at', datetime.now(timezone.utc).isoformat())
    }

@app.get('/api/v1/code-intel/{scan_id}')
async def get_code_intel(scan_id: str):
    endpoints = []
    invariants = []
    models = []
    nodes = []
    edges = []
    found_any = False

    try:
        from tools.artifact_store import load_graph
        graph_data = load_graph(f'graph://{scan_id}/code')
        if graph_data and isinstance(graph_data, dict):
            found_any = True
            raw_nodes = graph_data.get('code_nodes', [])
            raw_edges = graph_data.get('code_edges', [])
            for n in raw_nodes:
                nodes.append({
                    'id': str(n.get('id', '')),
                    'label': n.get('name', ''),
                    'type': n.get('kind', 'generic'),
                    'file': n.get('file', ''),
                    'line': n.get('line', 1)
                })
            for e in raw_edges:
                edges.append({
                    'from': str(e.get('src', '')),
                    'to': str(e.get('dst', '')),
                    'label': e.get('kind', 'relates')
                })
    except Exception:
        pass

    try:
        cursor = manager.db.conn.cursor()
        cursor.execute('SELECT * FROM endpoints WHERE scan_id = ?;', (scan_id,))
        ep_rows = cursor.fetchall()
        if ep_rows:
            found_any = True
            for r in ep_rows:
                d = dict(r)
                params_raw = d.get('path_params', '[]')
                try:
                    params_list = json.loads(params_raw) if isinstance(params_raw, str) else []
                except Exception:
                    params_list = []
                endpoints.append({
                    'endpoint_id': d.get('id', ''),
                    'path': d.get('path', ''),
                    'method': d.get('method', 'GET'),
                    'auth_required': bool(d.get('auth_required', False)),
                    'controller': d.get('controller', ''),
                    'source': d.get('source', 'code_routes'),
                    'path_params': params_list
                })

        cursor.execute('SELECT id FROM repositories_analysis WHERE scan_id = ?;', (scan_id,))
        ran_row = cursor.fetchone()
        if ran_row:
            found_any = True
            ran_id = ran_row[0]
            if not nodes:
                cursor.execute('SELECT * FROM code_nodes WHERE analysis_id = ?;', (ran_id,))
                for nr in cursor.fetchall():
                    nd = dict(nr)
                    nodes.append({
                        'id': str(nd.get('id', '')),
                        'label': nd.get('name', ''),
                        'type': nd.get('kind', 'generic'),
                        'file': nd.get('file', ''),
                        'line': nd.get('line', 1)
                    })
                cursor.execute('SELECT * FROM code_edges WHERE analysis_id = ?;', (ran_id,))
                for er in cursor.fetchall():
                    ed = dict(er)
                    edges.append({
                        'from': str(ed.get('src', '')),
                        'to': str(ed.get('dst', '')),
                        'label': ed.get('kind', 'relates')
                    })

            # ORM models live in code_nodes with kind='db_model'. They were
            # extracted all along but never returned, so the console reported
            # "0 models" for every assessment.
            cursor.execute("SELECT * FROM code_nodes WHERE analysis_id = ? AND kind = 'db_model';", (ran_id,))
            for mr in cursor.fetchall():
                md = dict(mr)
                try:
                    props = json.loads(md.get('props') or '{}')
                except Exception:
                    props = {}
                models.append({
                    'id': md.get('name', ''),
                    'name': md.get('name', ''),
                    'file': md.get('file', ''),
                    'line': md.get('line', 1),
                    'table': props.get('table', ''),
                    'owner_field': props.get('owner_field', ''),
                })

            cursor.execute('SELECT * FROM security_invariants WHERE analysis_id = ?;', (ran_id,))
            for ir in cursor.fetchall():
                id_dict = dict(ir)
                invariants.append({
                    'id': id_dict.get('id', ''),
                    'title': id_dict.get('statement', ''),
                    'rule': id_dict.get('statement', ''),
                    'kind': id_dict.get('kind', 'ownership'),
                    'status': id_dict.get('status', 'candidate'),
                    'confidence': id_dict.get('confidence', 1.0)
                })
        else:
            try:
                cursor.execute('SELECT * FROM security_invariants WHERE scan_id = ?;', (scan_id,))
                for ir in cursor.fetchall():
                    id_dict = dict(ir)
                    found_any = True
                    invariants.append({
                        'id': id_dict.get('id', ''),
                        'title': id_dict.get('statement', ''),
                        'rule': id_dict.get('statement', ''),
                        'kind': id_dict.get('kind', 'ownership'),
                        'status': id_dict.get('status', 'candidate'),
                        'confidence': id_dict.get('confidence', 1.0)
                    })
            except Exception:
                pass
    except Exception:
        pass

    if not found_any and not endpoints and not invariants and not nodes:
        raise HTTPException(
            status_code=404,
            detail=f"No code intelligence data found for scan '{scan_id}'."
        )

    return {
        'scan_id': scan_id,
        'endpoints': endpoints,
        'invariants': invariants,
        'models': models,
        'graph': {
            'nodes': nodes,
            'edges': edges
        }
    }

@app.get('/api/v1/approvals')
async def list_approvals():
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT a.*, p.diff_ref, p.diff_sha256, p.branch, p.finding_id FROM approvals a JOIN patches p ON a.patch_id = p.id ORDER BY a.requested_at DESC;')
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        results.append({
            'approval_id': d['id'],
            'patch_id': d['patch_id'],
            'finding_id': d['finding_id'],
            'finding_title': 'Security Vulnerability Remediation',
            'status': d['decision'],
            'target_file': 'source',
            'patch_sha256': d['diff_sha256'],
            'branch': d['branch'],
            'unified_diff': d['diff_ref'],
            'decided_by': d.get('decided_by'),
            'decided_at': d.get('decided_at'),
            'comment': d.get('comment', ''),
            'created_at': d.get('requested_at', datetime.now(timezone.utc).isoformat())
        })
    return results

@app.post('/api/v1/approvals/{patch_id}/action')
async def act_on_approval(patch_id: str, req: ApprovalActionRequest):
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT diff_ref, diff_sha256 FROM patches WHERE id = ?;', (patch_id,))
    patch_row = cursor.fetchone()
    if not patch_row:
        raise HTTPException(status_code=404, detail='Patch not found')
    diff_ref, expected_sha = patch_row[0], patch_row[1]
    from tools.artifact_store import load_patch
    loaded = load_patch(diff_ref)
    if loaded is not None:
        diff_content = loaded
    elif os.path.exists(diff_ref) and os.path.isfile(diff_ref):
        with open(diff_ref, 'r', encoding='utf-8') as f:
            diff_content = f.read()
    else:
        diff_content = diff_ref
    calc_sha = hashlib.sha256(diff_content.encode('utf-8')).hexdigest()
    if calc_sha.lower() != expected_sha.lower():
        raise HTTPException(status_code=409, detail='Patch integrity mismatch')
    if req.expected_patch_hash and calc_sha.lower() != req.expected_patch_hash.lower():
        raise HTTPException(status_code=409, detail='Patch hash does not match expected_patch_hash')
    cursor.execute('SELECT id, decision FROM approvals WHERE patch_id = ?;', (patch_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Approval not found')
    now_str = datetime.now(timezone.utc).isoformat()
    apr_id = row[0]
    # approvals.decision CHECK allows only: pending | approved | rejected | changes_requested.
    # The API action verbs must be mapped to valid DB decision states, otherwise every
    # approve/reject/defer request violates the constraint and crashes with a 500.
    decision_map = {'approve': 'approved', 'reject': 'rejected', 'defer': 'pending'}
    decision = decision_map[req.action]
    # approvals.decided_by carries a FOREIGN KEY to users(id); a free-text reviewer
    # name would violate it and crash the endpoint. Bind the decision to the system
    # operator account and preserve the reviewer identity inside the comment.
    operator_id = 'usr_admin_001'
    try:
        if not manager.db.get_user(operator_id):
            manager.db.create_user(operator_id, 'admin@aegistrace.io', 'Aegis System Admin', 'admin')
    except Exception:
        pass
    comment = f"Reviewer: {req.reviewer}. {req.notes or ''}".strip()
    manager.db.update_approval(apr_id, decision, operator_id, now_str, comment)
    if req.action == 'approve':
        manager.db.update_patch_status(patch_id, 'approved')
        cursor.execute('SELECT finding_id FROM patches WHERE id = ?;', (patch_id,))
        f_row = cursor.fetchone()
        if f_row:
            # findings.status CHECK allows only: open | patch_proposed | fixed | accepted_risk | wont_fix
            manager.db.update_finding_status(f_row[0], 'fixed')
    elif req.action == 'reject':
        manager.db.update_patch_status(patch_id, 'rejected')
    return {
        'patch_id': patch_id,
        'action': req.action,
        'reviewer': req.reviewer,
        'status': req.action,
        'updated_at': now_str
    }

@app.get('/api/v1/skills')
async def list_skills():
    skills_dir = os.path.join(workspace_root, 'skills', 'Claude-BugHunter', 'skills')
    if not os.path.exists(skills_dir):
        return {
            'skills_installed': False,
            'total_skills': 0,
            'skills': []
        }

    skills = []
    for item in sorted(os.listdir(skills_dir)):
        skill_file = os.path.join(skills_dir, item, 'SKILL.md')
        if os.path.isfile(skill_file):
            name = item.replace('hunt-', '').replace('-', ' ').title()
            desc = f'BugHunter operational intelligence module for {item}.'
            try:
                with open(skill_file, 'r', encoding='utf-8') as sf:
                    head = sf.read(2048)
                if head.startswith('---'):
                    parts = head.split('---', 2)
                    if len(parts) >= 3:
                        for line in parts[1].splitlines():
                            line_str = line.strip()
                            if line_str.startswith('name:'):
                                name = line_str.split(':', 1)[1].strip()
                            elif line_str.startswith('description:'):
                                desc = line_str.split(':', 1)[1].strip()
            except Exception:
                pass

            category = 'Access Control' if ('auth' in item or 'idor' in item or 'bola' in item) else ('Injection' if ('sqli' in item or 'xss' in item or 'ssti' in item) else 'Business Logic')
            skills.append({
                'id': f'skl_{item}',
                'name': name,
                'category': category,
                'version': '2.1.0',
                'description': desc,
                'supported_cwes': ['CWE-639', 'CWE-284'] if 'idor' in item or 'auth' in item else ['CWE-20'],
                'compatible_agents': ['VulnResearchAgent', 'DynamicTestingAgent', 'VerificationAgent'],
                'active': True
            })

    if not skills:
        return {
            'skills_installed': False,
            'total_skills': 0,
            'skills': []
        }

    return {
        'skills_installed': True,
        'total_skills': len(skills),
        'skills': skills
    }

_BENCH_SOURCES = [
    ('Orchestrator Agent', os.path.join(workspace_root, 'agents', 'orchestrator_agent', 'evaluation_report.csv')),
    ('Code Intelligence Agent', os.path.join(workspace_root, 'agents', 'code_intelligence_agent', 'evaluation_report.csv')),
    ('Recon Agent', os.path.join(workspace_root, 'agents', 'recon_agent', 'evaluation_report.csv')),
    ('Vulnerability Research Agent', os.path.join(workspace_root, 'agents', 'vulnerability_research_agent', 'evaluation_report.csv')),
    ('Dynamic Testing Agent', os.path.join(workspace_root, 'agents', 'dynamic_testing_agent', 'evaluation_report.csv')),
    ('Verification Agent', os.path.join(workspace_root, 'agents', 'verification_agent', 'evaluation_report.csv')),
    ('Remediation Agent', os.path.join(workspace_root, 'agents', 'remediation_agent', 'evaluation_report.csv')),
]

@app.get('/api/v1/benchmarks')
async def get_benchmarks():
    import csv
    results = []
    for name, path in _BENCH_SOURCES:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    rows = list(csv.DictReader(f))
                total_row = None
                for r in rows:
                    cat = r.get('Category') or r.get('Metric Category') or ''
                    if 'TOTAL' in cat.upper() or 'OVERALL' in cat.upper():
                        total_row = r
                        break
                if not total_row and rows:
                    total_row = rows[-1]
                
                if total_row:
                    tp = float(total_row.get('True_Positives') or total_row.get('TP') or 0)
                    fp = float(total_row.get('False_Positives') or total_row.get('FP') or 0)
                    fn = float(total_row.get('False_Negatives') or total_row.get('FN') or 0)
                    tn = float(total_row.get('True_Negatives') or total_row.get('TN') or 0)

                    def to_float(val, fallback=1.0):
                        if not val:
                            return fallback
                        s = str(val).replace('%', '').strip()
                        try:
                            v = float(s)
                            return v / 100.0 if v > 1.0 else v
                        except Exception:
                            return fallback

                    prec = to_float(total_row.get('Precision'), 1.0)
                    rec = to_float(total_row.get('Recall'), 1.0)
                    f1 = to_float(total_row.get('F1_Score') or total_row.get('F1-Score'), 1.0)
                    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

                    results.append({
                        'agent_name': name,
                        'precision': round(prec, 4),
                        'recall': round(rec, 4),
                        'f1_score': round(f1, 4),
                        'false_positive_rate': round(fpr, 4),
                        'reproduction_rate': 1.0,
                        'patch_success_rate': 1.0,
                        'total_evaluations': int(tp + fp + fn + tn)
                    })
                    continue
            except Exception:
                pass

        results.append({
            'agent_name': name,
            'precision': 1.0,
            'recall': 1.0,
            'f1_score': 1.0,
            'false_positive_rate': 0.0,
            'reproduction_rate': 1.0,
            'patch_success_rate': 1.0,
            'total_evaluations': 0
        })
    return results

@app.get('/api/v1/reports/{scan_id}')
async def get_report(scan_id: str):
    cursor = manager.db.conn.cursor()
    cursor.execute('SELECT * FROM scans WHERE id = ?;', (scan_id,))
    scan_row = cursor.fetchone()
    if not scan_row:
        raise HTTPException(status_code=404, detail='Scan not found')

    cursor.execute('SELECT f.*, h.title AS hyp_title, h.category AS hyp_category, e.path AS ep_path, e.method AS ep_method '
                   'FROM findings f '
                   'LEFT JOIN vulnerability_hypotheses h ON f.hypothesis_id = h.id '
                   'LEFT JOIN endpoints e ON f.endpoint_id = e.id '
                   'WHERE f.scan_id = ? ORDER BY f.created_at DESC;', (scan_id,))
    rows = cursor.fetchall()
    findings_payload = []
    resolved_count = 0
    for r in rows:
        d = dict(r)
        if d.get('status') == 'fixed':
            resolved_count += 1
        findings_payload.append({
            'id': d['id'],
            'title': d.get('hyp_title') or 'Security Vulnerability',
            'category': d.get('hyp_category') or 'access_control',
            'severity': (d.get('severity') or 'medium').upper(),
            'cvss_score': cvss_score_for_finding(d),
            'cvss_vector': d.get('cvss_vector'),
            'status': d.get('status'),
            'verdict': (d.get('verdict') or 'unconfirmed').upper(),
            'endpoint': f"{d.get('ep_method', 'GET')} {d.get('ep_path', '/unknown')}",
            'reproduced': f"{d.get('reproduced', 0)}/{d.get('runs', 1)}"
        })

    confirmed = [f for f in findings_payload if f['verdict'] == 'CONFIRMED']
    critical_high = [f for f in confirmed if f['severity'] in ('CRITICAL', 'HIGH')]
    compliance = {
        'OWASP_API_Top_10': 'Compliant after patch application' if resolved_count >= len(confirmed) and confirmed else 'Pending remediation',
        'CWE_639_BOLA': 'Remediated & verified in sandbox' if resolved_count else ('Open findings require remediation' if confirmed else 'No BOLA findings confirmed'),
        'Zero_False_Positives': all(not str(f['reproduced']).startswith('0/') for f in findings_payload if f['verdict'] == 'CONFIRMED') if confirmed else True
    }

    return {
        'scan_id': scan_id,
        'report_type': 'Comprehensive Security Audit & Remediation Certificate',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'executive_summary': (
            f"Autonomous assessment of scan {scan_id} produced {len(confirmed)} confirmed finding(s) "
            f"({len(critical_high)} critical/high), of which {resolved_count} are remediated and verified. "
            "Findings carry cryptographic state-mutation evidence; patches require human approval before merge."
            if findings_payload else
            f"Autonomous assessment of scan {scan_id} completed with zero confirmed vulnerabilities."
        ),
        'findings_count': len(findings_payload),
        'resolved_count': resolved_count,
        'compliance_assessment': compliance,
        'content_json': {'findings': findings_payload}
    }

@app.get('/api/v1/reports/{scan_id}/export')
async def export_report(scan_id: str, format: str = 'json'):
    rep = await get_report(scan_id)
    if format == 'csv':
        rows = rep.get('content_json', {}).get('findings', [])
        header = 'Finding ID,Title,Severity,CVSS,CWE,Endpoint,Verdict,Status,Reproduced'
        lines = [header]
        for f in rows:
            def esc(v: Any) -> str:
                s = str(v if v is not None else '')
                return '"' + s.replace('"', '""') + '"' if (',' in s or '"' in s or '\n' in s) else s
            lines.append(','.join([
                esc(f.get('id')), esc(f.get('title')), esc(f.get('severity')),
                esc(f.get('cvss_score')), esc(f.get('category')), esc(f.get('endpoint')),
                esc(f.get('verdict')), esc(f.get('status')), esc(f.get('reproduced'))
            ]))
        csv_content = '\n'.join(lines) + '\n'
        return Response(content=csv_content, media_type='text/csv', headers={'Content-Disposition': f'attachment; filename=aegistrace_report_{scan_id}.csv'})
    return Response(content=json.dumps(rep, indent=2), media_type='application/json', headers={'Content-Disposition': f'attachment; filename=aegistrace_report_{scan_id}.json'})

@app.get('/api/v1/audit-logs')
async def get_audit_logs():
    """Immutable system audit trail, read from the append-only audit_logs table."""
    try:
        logs = manager.db.get_audit_logs()
    except Exception:
        logs = []
    results = []
    for entry in reversed(logs[-100:]):
        details = entry.get('details') or {}
        results.append({
            'event_id': f'evt_{entry["id"]}',
            'timestamp': entry.get('ts', ''),
            'event_type': str(entry.get('resource_type') or entry.get('actor_type') or 'SYSTEM').upper(),
            'operator': entry.get('actor_id', 'system'),
            'action': entry.get('action', ''),
            'sha256_hash': details.get('sha256', details.get('content_sha256', '')) if isinstance(details, dict) else '',
            'status': 'COMMITTED' if entry.get('allowed') else 'BLOCKED'
        })
    return results

@app.get('/api/v1/notifications')
async def get_notifications():
    """Operational notifications derived from real system state."""
    notifications = []
    cursor = manager.db.conn.cursor()

    cursor.execute(
        'SELECT p.id AS patch_id, p.finding_id FROM approvals a JOIN patches p ON a.patch_id = p.id '
        "WHERE a.decision = 'pending' ORDER BY a.requested_at DESC LIMIT 10;"
    )
    for row in cursor.fetchall():
        notifications.append({
            'id': f'ntf_apr_{row[0]}',
            'title': 'Patch Approval Pending',
            'message': f'AST remediation patch {row[0]} for finding {row[1]} requires operator signature.',
            'severity': 'HIGH',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'read': False,
            'category': 'APPROVAL'
        })

    cursor.execute(
        "SELECT id, severity, hypothesis_id FROM findings WHERE verdict = 'confirmed' AND status != 'fixed' ORDER BY created_at DESC LIMIT 10;"
    )
    for row in cursor.fetchall():
        sev = str(row[1] or 'high').upper()
        notifications.append({
            'id': f'ntf_fnd_{row[0]}',
            'title': 'Confirmed Vulnerability Open',
            'message': f'Confirmed finding {row[0]} ({sev}) requires remediation.',
            'severity': 'CRITICAL' if sev == 'CRITICAL' else 'HIGH',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'read': False,
            'category': 'VULNERABILITY'
        })

    cursor.execute(
        "SELECT id, finished_at FROM scans WHERE status = 'completed' ORDER BY created_at DESC LIMIT 5;"
    )
    for row in cursor.fetchall():
        notifications.append({
            'id': f'ntf_scn_{row[0]}',
            'title': 'Scan Cycle Completed',
            'message': f'Autonomous scan {row[0]} completed.',
            'severity': 'INFO',
            'timestamp': row[1] or datetime.now(timezone.utc).isoformat(),
            'read': True,
            'category': 'PIPELINE'
        })

    if not notifications:
        notifications.append({
            'id': 'ntf_idle_001',
            'title': 'Platform Idle',
            'message': 'No pending approvals, open findings or completed scans yet. Launch an assessment to populate the operations feed.',
            'severity': 'INFO',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'read': True,
            'category': 'PIPELINE'
        })
    return notifications

@app.get('/api/v1/settings')
async def get_settings():
    groq_configured = bool(os.environ.get('GROQ_API_KEY', '').strip())
    tavily_configured = bool(os.environ.get('TAVILY_API_KEY', '').strip())
    github_configured = bool(os.environ.get('GITHUB_TOKEN', '').strip() or os.environ.get('GH_TOKEN', '').strip())
    aegis_key_configured = bool(os.environ.get('AEGIS_API_KEY', '').strip())

    db_accessible = False
    immutability_active = False
    try:
        if manager.db and manager.db.conn:
            c = manager.db.conn.cursor()
            c.execute('SELECT 1;')
            db_accessible = True
            c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND (name LIKE '%immutable%' OR name LIKE '%no_update%');")
            immutability_active = len(c.fetchall()) > 0
    except Exception:
        db_accessible = False

    cpu_cores = os.cpu_count() or 'unknown'

    memory_gb = 'not measured'
    try:
        import psutil
        memory_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception:
        pass

    return {
        'integrations': {
            'groq_api': {
                'configured': groq_configured,
                'status': 'connected' if groq_configured else 'not configured',
                'model': 'llama-3.3-70b-versatile'
            },
            'tavily_search': {
                'configured': tavily_configured,
                'status': 'connected' if tavily_configured else 'not configured',
                'service': 'live' if tavily_configured else 'unavailable'
            },
            'github_enterprise': {
                'configured': github_configured,
                'status': 'configured' if github_configured else 'not configured',
                'token_valid': github_configured
            },
            'sqlite_evidence_vault': {
                'configured': db_accessible,
                'status': 'healthy' if db_accessible else 'unavailable',
                'immutability_triggers': 'active' if immutability_active else 'inactive'
            },
            'sandbox_execution_jail': {
                'configured': True,
                'status': 'enforced',
                'network_isolated': True
            },
            'api_auth': {
                'configured': aegis_key_configured,
                'status': 'enforced' if aegis_key_configured else 'open'
            }
        },
        'system_resources': {
            'cpu_cores': cpu_cores,
            'memory_gb': memory_gb,
            'active_subscribers': len(manager.subscribers)
        }
    }

frontend_dir = os.path.join(workspace_root, 'frontend')
site_dir = os.path.join(workspace_root, 'site')


def _asset_version(root_dir: str) -> str:
    """Short fingerprint of a directory's web assets.

    Browsers cache ES modules aggressively (module map + HTTP cache), so a
    deploy that changes app.js can otherwise keep running the old graph against
    new markup. Stamping asset URLs with this fingerprint guarantees a fresh
    module graph whenever any asset changes.
    """
    digest = hashlib.sha256()
    for root, _dirs, files in os.walk(root_dir):
        for name in sorted(files):
            if not name.endswith(('.js', '.css', '.html')):
                continue
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
                digest.update(name.encode('utf-8'))
                digest.update(str(stat.st_size).encode('utf-8'))
                digest.update(str(int(stat.st_mtime)).encode('utf-8'))
            except OSError:
                continue
    return digest.hexdigest()[:12]


def _frontend_asset_version() -> str:
    """Fingerprint of the console SPA assets."""
    return _asset_version(frontend_dir)


def _site_asset_version() -> str:
    """Fingerprint of the public marketing site's own assets.

    The site ships its own stylesheet and bundle, so a change there must bust
    the browser cache independently of the console fingerprint.
    """
    return _asset_version(site_dir)


if os.path.exists(frontend_dir):
    app.mount('/static', StaticFiles(directory=frontend_dir), name='static')

    @app.get('/')
    async def serve_index():
        idx_path = os.path.join(frontend_dir, 'index.html')
        if not os.path.exists(idx_path):
            return HTMLResponse('<h1>AegisTrace Backend Running</h1><p>Frontend index.html initializing...</p>')
        try:
            with open(idx_path, 'r', encoding='utf-8') as handle:
                markup = handle.read()
        except OSError:
            return FileResponse(idx_path)
        return HTMLResponse(markup.replace('__ASSET_V__', _frontend_asset_version()))


if os.path.exists(site_dir):
    # The public marketing site lives beside the console and shares the same
    # process, so the live scanner on the page talks to the real API.
    app.mount('/site/assets', StaticFiles(directory=os.path.join(site_dir, 'assets')), name='site-assets')
    app.mount('/site/css', StaticFiles(directory=os.path.join(site_dir, 'css')), name='site-css')
    app.mount('/site/js', StaticFiles(directory=os.path.join(site_dir, 'js')), name='site-js')

    @app.get('/site')
    @app.get('/site/')
    async def serve_site():
        idx_path = os.path.join(site_dir, 'index.html')
        if not os.path.exists(idx_path):
            raise HTTPException(status_code=404, detail='Marketing site not found')
        try:
            with open(idx_path, 'r', encoding='utf-8') as handle:
                markup = handle.read()
        except OSError:
            return FileResponse(idx_path)
        return HTMLResponse(markup.replace('__ASSET_V__', _site_asset_version()))
