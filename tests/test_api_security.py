import os
import sys
import uuid
import hashlib
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app, manager, calculate_security_score

@pytest.fixture
def client():
    return TestClient(app)

def test_benchmarks_real_data(client):
    """Verify all 7 agents return non-zero real evaluation counts."""
    res = client.get('/api/v1/benchmarks')
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 7
    for agent_metric in data:
        assert agent_metric['total_evaluations'] > 0
        assert agent_metric['f1_score'] is not None
        assert 0.0 <= agent_metric['f1_score'] <= 1.0

def test_settings_no_secret_leaks(client, monkeypatch):
    """Verify boolean configured without leaking raw secret keys."""
    raw_secret = 'super_secret_test_key_12345'
    monkeypatch.setenv('AEGIS_API_KEY', raw_secret)
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_test_groq_key_9876')
    res = client.get('/api/v1/settings')
    assert res.status_code == 200
    body_text = res.text
    assert raw_secret not in body_text
    assert 'gsk_test_groq_key_9876' not in body_text
    data = res.json()
    assert data['integrations']['api_auth']['configured'] is True
    assert data['integrations']['groq_api']['configured'] is True

def test_code_intel_404(client):
    """Assert 404 for nonexistent scan ID."""
    res = client.get('/api/v1/code-intel/nonexistent_scan_xyz_999')
    assert res.status_code == 404
    assert 'No code intelligence data found' in res.json()['detail']

def test_security_score_formula():
    """Verify penalty calculation and null return on zero completed scans."""
    conn = manager.db.conn
    cursor = conn.cursor()
    
    test_user_id = f'usr_{uuid.uuid4().hex[:8]}'
    test_proj_id = f'prj_{uuid.uuid4().hex[:8]}'
    test_eng_id = f'eng_{uuid.uuid4().hex[:8]}'
    test_scm_id = f'scm_{uuid.uuid4().hex[:8]}'
    test_scan_id = f'scn_{uuid.uuid4().hex[:8]}'
    
    manager.db.create_user(test_user_id, f'{test_user_id}@aegis.ai', 'Test User', 'admin')
    manager.db.create_project(test_proj_id, test_user_id, 'Score Project')
    manager.db.create_engagement(test_eng_id, test_proj_id, 'Score Eng', 'full', 'sandbox')
    manager.db.create_scope_manifest(test_scm_id, test_eng_id, 1, {}, test_user_id, valid=True)
    
    score_empty = calculate_security_score(conn, project_id=test_proj_id)
    assert score_empty is None
    
    manager.db.create_scan(test_scan_id, test_eng_id, test_scm_id, f'cor_{uuid.uuid4().hex[:8]}', test_user_id, status='completed')
    
    score_clean = calculate_security_score(conn, project_id=test_proj_id)
    assert score_clean == 100
    
    ep_id = f'ep_{uuid.uuid4().hex[:8]}'
    inv_id = f'inv_{uuid.uuid4().hex[:8]}'
    hyp_id = f'hyp_{uuid.uuid4().hex[:8]}'
    cursor.execute('INSERT INTO endpoints (id, scan_id, method, path, source) VALUES (?, ?, "POST", "/orders", "code_routes");', (ep_id, test_scan_id))
    cursor.execute('INSERT INTO security_invariants (id, project_id, statement, kind, source, confidence) VALUES (?, ?, "Statement", "ownership", "code", 1.0);', (inv_id, test_proj_id))
    cursor.execute('INSERT INTO vulnerability_hypotheses (id, scan_id, endpoint_id, invariant_id, category, title, rationale, priority) VALUES (?, ?, ?, ?, "idor", "Title", "Rationale", 1);', (hyp_id, test_scan_id, ep_id, inv_id))
    
    fnd_crit = f'fnd_{uuid.uuid4().hex[:8]}'
    fnd_high = f'fnd_{uuid.uuid4().hex[:8]}'
    cursor.execute('INSERT INTO findings (id, scan_id, hypothesis_id, endpoint_id, invariant_id, verdict, confidence, severity, runs, reproduced, invariant_violated, status) VALUES (?, ?, ?, ?, ?, "confirmed", 1.0, "critical", 3, 3, 1, "open");', (fnd_crit, test_scan_id, hyp_id, ep_id, inv_id))
    cursor.execute('INSERT INTO findings (id, scan_id, hypothesis_id, endpoint_id, invariant_id, verdict, confidence, severity, runs, reproduced, invariant_violated, status) VALUES (?, ?, ?, ?, ?, "confirmed", 1.0, "high", 3, 3, 1, "open");', (fnd_high, test_scan_id, hyp_id, ep_id, inv_id))
    conn.commit()
    
    score_penalized = calculate_security_score(conn, project_id=test_proj_id)
    assert score_penalized == 60

def test_rate_limit_scans(client):
    """Verify HTTP 429 when rate limit of 10 requests per minute is exceeded."""
    import backend.app as app_mod
    app_mod._scan_rate_limits.clear()
    
    payload = {
        'project_id': 'prj_default_01',
        'target_repo': 'https://github.com/aegis/sample-repo',
        'branch': 'main'
    }
    
    for _ in range(10):
        res = client.post('/api/v1/scans', json=payload)
        assert res.status_code == 200
        
    blocked_res = client.post('/api/v1/scans', json=payload)
    assert blocked_res.status_code == 429
    assert blocked_res.json()['detail'] == 'Rate limit exceeded: maximum 10 scans per minute'

def test_scopegate_host_block(client):
    """Verify HTTP 400 on out-of-scope web_target_url."""
    import backend.app as app_mod
    app_mod._scan_rate_limits.clear()
    
    payload = {
        'project_id': 'prj_default_01',
        'target_repo': 'https://github.com/aegis/sample-repo',
        'branch': 'main',
        'web_target_url': 'https://unauthorized.external-target.com/api'
    }
    res = client.post('/api/v1/scans', json=payload)
    assert res.status_code == 400
    assert res.json()['detail'] == 'Target host not in scope'

def test_approval_sha256_integrity(client):
    """Verify HTTP 409 when patch diff sha256 does not match diff content."""
    conn = manager.db.conn
    cursor = conn.cursor()
    
    test_user_id = f'usr_{uuid.uuid4().hex[:8]}'
    test_proj_id = f'prj_{uuid.uuid4().hex[:8]}'
    test_eng_id = f'eng_{uuid.uuid4().hex[:8]}'
    test_scm_id = f'scm_{uuid.uuid4().hex[:8]}'
    test_scan_id = f'scn_{uuid.uuid4().hex[:8]}'
    
    manager.db.create_user(test_user_id, f'{test_user_id}@aegis.ai', 'Approvals User', 'admin')
    manager.db.create_project(test_proj_id, test_user_id, 'Approvals Project')
    manager.db.create_engagement(test_eng_id, test_proj_id, 'Approvals Eng', 'full', 'sandbox')
    manager.db.create_scope_manifest(test_scm_id, test_eng_id, 1, {}, test_user_id, valid=True)
    manager.db.create_scan(test_scan_id, test_eng_id, test_scm_id, f'cor_{uuid.uuid4().hex[:8]}', test_user_id, status='completed')
    
    pat_id = f'pat_{uuid.uuid4().hex[:8]}'
    fnd_id = f'fnd_{uuid.uuid4().hex[:8]}'
    apr_id = f'apr_{uuid.uuid4().hex[:8]}'
    
    diff_text = '--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-foo\n+bar\n'
    valid_sha = hashlib.sha256(diff_text.encode('utf-8')).hexdigest()
    tampered_diff = '--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-foo\n+malicious\n'
    
    ep_id = f'ep_{uuid.uuid4().hex[:8]}'
    inv_id = f'inv_{uuid.uuid4().hex[:8]}'
    hyp_id = f'hyp_{uuid.uuid4().hex[:8]}'
    cursor.execute('INSERT INTO endpoints (id, scan_id, method, path, source) VALUES (?, ?, "GET", "/", "code_routes");', (ep_id, test_scan_id))
    cursor.execute('INSERT INTO security_invariants (id, project_id, statement, kind, source, confidence) VALUES (?, ?, "Statement", "ownership", "code", 1.0);', (inv_id, test_proj_id))
    cursor.execute('INSERT INTO vulnerability_hypotheses (id, scan_id, endpoint_id, invariant_id, category, title, rationale, priority) VALUES (?, ?, ?, ?, "idor", "Title", "Rationale", 1);', (hyp_id, test_scan_id, ep_id, inv_id))
    cursor.execute('INSERT INTO findings (id, scan_id, hypothesis_id, endpoint_id, invariant_id, verdict, confidence, severity, runs, reproduced, invariant_violated, status) VALUES (?, ?, ?, ?, ?, "confirmed", 1.0, "high", 3, 3, 1, "open");', (fnd_id, test_scan_id, hyp_id, ep_id, inv_id))
    cursor.execute('INSERT INTO patches (id, finding_id, attempt, branch, diff_ref, diff_sha256, changed_files, root_cause, status) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?);', (pat_id, fnd_id, 'fix/x', tampered_diff, valid_sha, '["test.py"]', '{}', 'proposed'))
    cursor.execute('INSERT INTO approvals (id, patch_id, decision) VALUES (?, ?, "pending");', (apr_id, pat_id))
    conn.commit()
    
    payload = {
        'action': 'approve',
        'reviewer': 'SecOps Engineer',
        'notes': 'Attempting approval on tampered patch'
    }
    res = client.post(f'/api/v1/approvals/{pat_id}/action', json=payload)
    assert res.status_code == 409
    assert res.json()['detail'] == 'Patch integrity mismatch'

def test_websocket_auth(client, monkeypatch):
    """Verify WebSocket rejection with code 4401 when AEGIS_API_KEY is configured and unauthorized."""
    monkeypatch.setenv('AEGIS_API_KEY', 'ws_secret_key_777')
    
    with pytest.raises(Exception):
        with client.websocket_connect('/ws/scans/scn_test_auth'):
            pass
            
    with client.websocket_connect('/ws/scans/scn_test_auth?api_key=ws_secret_key_777') as ws:
        pass
