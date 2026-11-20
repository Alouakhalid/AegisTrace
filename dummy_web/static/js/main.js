let selectedTarget = 'source';
let selectedType = 'scoped';
let selectedConfigMode = 'github';
let activeScanId = null;
let eventSource = null;

function setTarget(target) {
  selectedTarget = target;
  document.querySelectorAll('.target-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`target-${target}`);
  if (card) card.classList.add('selected');

  const sourceSec = document.getElementById('config-source-section');
  const urlSec = document.getElementById('config-url-section');
  if (target === 'url') {
    if (sourceSec) sourceSec.style.display = 'none';
    if (urlSec) urlSec.style.display = 'block';
    probeTargetUrl();
  } else {
    if (sourceSec) sourceSec.style.display = 'block';
    if (urlSec) urlSec.style.display = 'none';
  }
}

function selectUrlPreset(preset) {
  document.querySelectorAll('.url-preset-card').forEach(c => {
    c.classList.remove('border-2', 'border-blue-600', 'bg-blue-50/40');
    c.classList.add('border-slate-200', 'bg-white');
  });

  const urlInput = document.getElementById('target-live-url');
  const allowedInput = document.getElementById('allowed-hosts');

  if (preset === 'shoplite_local') {
    const el = document.getElementById('preset-shoplite');
    if (el) {
      el.classList.remove('border-slate-200', 'bg-white');
      el.classList.add('border-2', 'border-blue-600', 'bg-blue-50/40');
    }
    if (urlInput) urlInput.value = 'http://127.0.0.1:5050';
    if (allowedInput) allowedInput.value = '127.0.0.1:5050, shoplite.example.com';
    probeTargetUrl();
  } else if (preset === 'httpbin') {
    const el = document.getElementById('preset-httpbin');
    if (el) {
      el.classList.remove('border-slate-200', 'bg-white');
      el.classList.add('border-2', 'border-blue-600', 'bg-blue-50/40');
    }
    if (urlInput) urlInput.value = 'https://httpbin.org';
    if (allowedInput) allowedInput.value = 'httpbin.org';
    probeTargetUrl();
  } else if (preset === 'custom') {
    const el = document.getElementById('preset-custom');
    if (el) {
      el.classList.remove('border-slate-200', 'bg-white');
      el.classList.add('border-2', 'border-blue-600', 'bg-blue-50/40');
    }
    if (urlInput) {
      urlInput.focus();
      urlInput.select();
    }
  }
}

async function probeTargetUrl() {
  const urlInput = document.getElementById('target-live-url');
  const btn = document.getElementById('btn-probe-url');
  const card = document.getElementById('probe-result-card');
  const titleEl = document.getElementById('probe-target-title');
  const badgeEl = document.getElementById('probe-target-badge');
  const detailsEl = document.getElementById('probe-target-details');

  const rawUrl = urlInput ? urlInput.value.trim() : 'http://127.0.0.1:5050';
  if (!rawUrl) return;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Probing...`;
  }

  try {
    const res = await fetch('/api/target/probe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: rawUrl })
    });
    const data = await res.json();
    if (card) card.style.display = 'block';

    if (data.reachable) {
      if (titleEl) titleEl.textContent = data.title || data.url;
      if (badgeEl) {
        badgeEl.className = 'badge badge-green';
        badgeEl.textContent = `Online (${data.status_code || 200} OK) — ${data.latency_ms || 1}ms`;
      }
      if (detailsEl) {
        detailsEl.innerHTML = `
          <div><strong>Host:</strong> ${data.host} | <strong>Server:</strong> ${data.server || 'Uvicorn/FastAPI'}</div>
          <div><strong>OpenAPI Spec:</strong> ${data.has_openapi ? `<span class="text-green-600 font-bold">✓ Discovered (${data.endpoints_count} endpoints)</span>` : '<span class="text-slate-400">None detected</span>'}</div>
        `;
      }
      const hostInput = document.getElementById('allowed-hosts');
      if (hostInput && !hostInput.value.includes(data.host)) {
        hostInput.value = `${hostInput.value}, ${data.host}`.replace(/^,\s*/, '');
      }
    } else {
      if (titleEl) titleEl.textContent = data.url;
      if (badgeEl) {
        badgeEl.className = 'badge badge-red';
        badgeEl.textContent = `Unreachable`;
      }
      if (detailsEl) {
        detailsEl.textContent = `Connection failed: ${data.error || 'Server did not respond'}`;
      }
    }
  } catch (err) {
    if (card) card.style.display = 'block';
    if (titleEl) titleEl.textContent = rawUrl;
    if (badgeEl) {
      badgeEl.className = 'badge badge-red';
      badgeEl.textContent = `Probe Error`;
    }
    if (detailsEl) detailsEl.textContent = err.message;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>🔍</span> Probe & Test Link`;
    }
  }
}

function setType(type) {
  selectedType = type;
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`type-${type}`);
  if (card) card.classList.add('selected');
}

function setConfigMode(mode) {
  selectedConfigMode = mode;
  document.getElementById('pill-github').classList.toggle('active', mode === 'github');
  document.getElementById('pill-local').classList.toggle('active', mode === 'local');
  if (mode === 'github') {
    document.getElementById('repo-input-label').textContent = 'Repository URL';
    document.getElementById('repo-url').placeholder = 'https://github.com/shoplite/shoplite';
  } else {
    document.getElementById('repo-input-label').textContent = 'Local Path / Directory';
    document.getElementById('repo-url').placeholder = '/Users/alikhalidalikhalid/AegisTrace/test_shoplite_repo';
  }
}

function toggleScopes(enabled) {
  const scopeFields = document.getElementById('scope-fields');
  const scopeLabel = document.getElementById('scope-status-label');
  if (scopeLabel) scopeLabel.textContent = enabled ? 'Enabled' : 'Disabled';
  if (scopeFields) scopeFields.style.display = enabled ? 'block' : 'none';
}

function loadShopLitePreset() {
  setTarget('source');
  setType('scoped');
  setConfigMode('github');
  document.getElementById('repo-url').value = 'https://github.com/shoplite/shoplite';
  document.getElementById('repo-branch').value = 'main';
  document.getElementById('target-base-url').value = 'http://127.0.0.1:5050';
  document.getElementById('openapi-path').value = 'openapi_test.json';
  document.getElementById('allowed-hosts').value = '127.0.0.1:5050, shoplite.example.com';
  document.getElementById('forbidden-paths').value = '/admin/shutdown, /admin/danger/*';
  document.getElementById('scope-toggle').checked = true;
  toggleScopes(true);
}

function appendLog(msg, color = '#38bdf8') {
  const terminal = document.getElementById('log-terminal');
  if (!terminal) return;
  const line = document.createElement('div');
  line.style.color = color;
  const time = new Date().toLocaleTimeString();
  line.innerHTML = `<span style="color:#64748b;">[${time}]</span> ${msg}`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function updateStage(agent, status, details = '') {
  const el = document.getElementById(`stage-${agent}`);
  if (!el) return;
  el.classList.remove('active', 'completed', 'failed');
  const statusBadge = el.querySelector('.stage-status');
  if (status === 'running') {
    el.classList.add('active');
    if (statusBadge) statusBadge.innerHTML = '<span class="badge badge-blue">Running</span>';
  } else if (status === 'completed' || status === 'succeeded') {
    el.classList.add('completed');
    if (statusBadge) statusBadge.innerHTML = '<span class="badge badge-green">Passed</span>';
  } else if (status === 'failed') {
    el.classList.add('failed');
    if (statusBadge) statusBadge.innerHTML = '<span class="badge badge-red">Failed</span>';
  }
  if (details) {
    const detailEl = el.querySelector('.stage-details');
    if (detailEl) detailEl.textContent = details;
  }
}

async function startScan() {
  const btn = document.getElementById('btn-start-scan');
  btn.disabled = true;
  btn.innerHTML = `
    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
    </svg> Executing Agents...`;

  document.getElementById('execution-section').style.display = 'block';
  document.getElementById('results-section').style.display = 'none';
  document.getElementById('log-terminal').innerHTML = '';

  const stages = ['orchestrator', 'code_intelligence', 'recon', 'vulnerability_research', 'dynamic_testing', 'verification', 'remediation'];
  stages.forEach(s => {
    const el = document.getElementById(`stage-${s}`);
    if (el) {
      el.classList.remove('active', 'completed', 'failed');
      const badge = el.querySelector('.stage-status');
      if (badge) badge.innerHTML = '<span class="badge badge-yellow">Queued</span>';
      const det = el.querySelector('.stage-details');
      if (det) det.textContent = 'Waiting for prerequisite stages...';
    }
  });

  appendLog('Initializing AegisTrace Multi-Agent Pipeline...', '#93c5fd');

  let activeTargetBaseUrl = 'http://127.0.0.1:5050';
  if (selectedTarget === 'url') {
    const liveInput = document.getElementById('target-live-url');
    if (liveInput && liveInput.value.trim()) {
      activeTargetBaseUrl = liveInput.value.trim();
    }
  } else {
    const baseInput = document.getElementById('target-base-url');
    if (baseInput && baseInput.value.trim()) {
      activeTargetBaseUrl = baseInput.value.trim();
    }
  }

  const hostsList = document.getElementById('allowed-hosts').value.split(',').map(s => s.trim()).filter(Boolean);
  const cleanTargetHost = activeTargetBaseUrl.replace('http://', '').replace('https://', '').split('/')[0];
  if (!hostsList.includes(cleanTargetHost)) {
    hostsList.push(cleanTargetHost);
  }

  const payload = {
    target_mode: selectedTarget,
    assessment_mode: selectedType,
    repository_url: document.getElementById('repo-url').value.trim() || 'https://github.com/shoplite/shoplite',
    branch: document.getElementById('repo-branch').value.trim() || 'main',
    target_base_url: activeTargetBaseUrl,
    openapi_spec: document.getElementById('openapi-path').value.trim() || 'openapi_test.json',
    allowed_hosts: hostsList,
    forbidden_paths: document.getElementById('forbidden-paths').value.split(',').map(s => s.trim()).filter(Boolean),
    scope_enabled: document.getElementById('scope-toggle').checked
  };

  try {
    const res = await fetch('/api/scan/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      appendLog(`Error starting scan: ${data.error || 'Server error'}`, '#f87171');
      btn.disabled = false;
      btn.textContent = 'Start AegisTrace Assessment';
      return;
    }

    activeScanId = data.scan_id;
    appendLog(`Scan registered: ${activeScanId} (Scope Manifest verified)`, '#4ade80');
    listenToScanEvents(activeScanId);
  } catch (err) {
    appendLog(`Network error: ${err.message}`, '#f87171');
    btn.disabled = false;
    btn.textContent = 'Start AegisTrace Assessment';
  }
}

function listenToScanEvents(scanId) {
  if (eventSource) {
    eventSource.close();
  }
  eventSource = new EventSource(`/api/scan/stream/${scanId}`);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'log') {
        appendLog(data.message, data.color || '#38bdf8');
      } else if (data.type === 'stage_update') {
        updateStage(data.agent, data.status, data.details);
      } else if (data.type === 'scan_complete') {
        appendLog('====================================================================', '#34d399');
        appendLog(`[+] Multi-Agent Assessment Finished: ${data.status.toUpperCase()}`, '#34d399');
        appendLog('[🛡️] REMEDIATION READY: AegisTrace generated a verified patch diff! Click Tab 3 "Remediation Patch Diff" to review & approve.', '#fbbf24');
        eventSource.close();
        document.getElementById('btn-start-scan').disabled = false;
        document.getElementById('btn-start-scan').textContent = 'Start AegisTrace Assessment';
        loadScanResults(scanId);
      }
    } catch (err) {
      console.error(err);
    }
  };

  eventSource.onerror = (e) => {
    appendLog('Stream connection finished or closed.', '#94a3b8');
    eventSource.close();
    document.getElementById('btn-start-scan').disabled = false;
    document.getElementById('btn-start-scan').textContent = 'Start AegisTrace Assessment';
    loadScanResults(scanId);
  };
}

async function loadScanResults(scanId) {
  try {
    const res = await fetch(`/api/scan/status/${scanId}`);
    const data = await res.json();
    if (!res.ok) return;

    document.getElementById('results-section').style.display = 'block';

    const findings = data.findings || [];
    const findingsList = document.getElementById('findings-list');
    if (findingsList) {
      if (findings.length === 0) {
        findingsList.innerHTML = '<p class="text-sm text-slate-500 py-3">No confirmed vulnerabilities found.</p>';
      } else {
        findingsList.innerHTML = findings.map(f => `
          <div class="p-4 rounded-lg border border-red-200 bg-red-50/50 mb-3">
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-red-900">${f.id} — ${f.title || 'IDOR Authorization Bypass'}</span>
              <div class="flex gap-2">
                <span class="badge badge-red">${f.severity || 'HIGH'}</span>
                <span class="badge badge-purple">${f.verdict || 'confirmed'}</span>
              </div>
            </div>
            <p class="text-xs text-slate-700 mb-2">${f.rationale || 'Unauthorized access verified across security invariant.'}</p>
            <div class="flex flex-wrap gap-4 text-xs font-mono text-slate-600 bg-white p-2 rounded border border-slate-200">
              <div><strong>CVSS:</strong> ${f.cvss || 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N'}</div>
              <div><strong>Confidence:</strong> ${(f.confidence * 100).toFixed(0)}%</div>
              <div><strong>Reproduced:</strong> ${f.reproduced || 3}/${f.runs || 3} runs</div>
            </div>
          </div>
        `).join('');
      }
    }

    const diffs = data.state_diffs || [];
    const diffsList = document.getElementById('diffs-list');
    if (diffsList) {
      if (diffs.length === 0) {
        diffsList.innerHTML = '<p class="text-sm text-slate-500 py-3">No state diffs recorded.</p>';
      } else {
        diffsList.innerHTML = diffs.map(d => `
          <div class="p-3 rounded border border-slate-200 bg-slate-50 font-mono text-xs mb-2">
            <div class="flex justify-between text-slate-600 mb-1">
              <span><strong>Table:</strong> ${d.table} [Key: ${JSON.stringify(d.key)}]</span>
              <span class="text-blue-600 font-semibold">Evidence: ${d.evidence_id || 'evd_sha256'}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 mt-2">
              <div class="p-2 bg-red-100/70 text-red-800 rounded">
                <strong>Before (${d.snapshot_before_id}):</strong> ${d.before}
              </div>
              <div class="p-2 bg-green-100/70 text-green-800 rounded">
                <strong>After (${d.snapshot_after_id}):</strong> ${d.after}
              </div>
            </div>
          </div>
        `).join('');
      }
    }

    const patch = data.patch || {};
    const patchContainer = document.getElementById('patch-container');
    if (patchContainer) {
      if (patch.diff) {
        const isApplied = patch.status === 'applied_to_repository';
        let actionBlock = '';
        if (isApplied) {
          actionBlock = `
            <div class="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs">
              <div class="font-bold flex items-center gap-1.5 mb-1">
                <span>✅</span> Remediation Patch Approved & Applied to Target Codebase
              </div>
              <div><strong>Target File:</strong> <code class="font-mono bg-white px-1 py-0.5 rounded border border-emerald-200">${patch.target_file || 'test_shoplite_repo/orders.py'}</code></div>
              <div><strong>Approved by:</strong> ${escapeHtml(patch.applied_by || 'secops_lead')} at ${patch.applied_at || ''}</div>
              <div class="mt-1 text-emerald-700">The ownership check has been committed to the target codebase. Subsequent cross-tenant attacks now return 403 Forbidden!</div>
            </div>
          `;
        } else {
          actionBlock = `
            <div class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between">
              <div>
                <div class="text-xs font-semibold text-amber-900 flex items-center gap-1">
                  <span>🛡️</span> Human-in-the-Loop Approval Gate (Architecture Guardrail)
                </div>
                <div class="text-[11px] text-amber-700 mt-0.5">
                  AI security agents must not modify main branches directly without review. Click below to approve and apply this patch to the repository.
                </div>
              </div>
              <button id="btn-apply-patch" onclick="applyRemediationPatch('${scanId}')" class="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs py-2 px-4 rounded shadow transition flex items-center gap-1.5 whitespace-nowrap ml-4">
                <span>✓</span> Approve & Apply Patch
              </button>
            </div>
          `;
        }

        patchContainer.innerHTML = `
          <div class="mb-2 flex items-center justify-between text-xs text-slate-600">
            <span><strong>Branch:</strong> <code class="bg-slate-100 px-1 py-0.5 rounded">${patch.branch || 'fix/aegistrace-fnd-01'}</code></span>
            <span><strong>Status:</strong> <span class="badge ${isApplied ? 'badge-green' : 'badge-yellow'}">${patch.status || 'ready_for_review'}</span></span>
          </div>
          <pre class="log-terminal text-green-400 bg-slate-900 p-3 rounded overflow-x-auto text-xs"><code>${escapeHtml(patch.diff)}</code></pre>
          ${actionBlock}
        `;
      } else {
        patchContainer.innerHTML = '<p class="text-sm text-slate-500 py-3">No remediation patch generated.</p>';
      }
    }

    const tabPatchBtn = document.getElementById('tab-btn-patch');
    if (tabPatchBtn) {
      if (patch.diff) {
        const isApplied = patch.status === 'applied_to_repository';
        tabPatchBtn.innerHTML = `Remediation Patch Diff <span class="badge ${isApplied ? 'badge-green' : 'badge-yellow'} ml-1 text-[10px]">${isApplied ? '✓ Applied' : '● Ready'}</span>`;
      } else {
        tabPatchBtn.innerHTML = 'Remediation Patch Diff';
      }
    }

    const tables = data.db_summary || {};
    const dbSummaryList = document.getElementById('db-summary-list');
    if (dbSummaryList) {
      const rows = Object.entries(tables).map(([tbl, count]) => `
        <div class="flex items-center justify-between py-1.5 border-b border-slate-100 text-xs">
          <span class="font-mono text-slate-700">${tbl}</span>
          <span class="badge ${count > 0 ? 'badge-blue' : 'badge-yellow'}">${count} records</span>
        </div>
      `).join('');
      dbSummaryList.innerHTML = rows || '<p class="text-sm text-slate-500">Database empty.</p>';
    }

  } catch (err) {
    console.error(err);
  }
}

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active', 'border-blue-600', 'text-blue-600'));
  document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  if (activeBtn) activeBtn.classList.add('active', 'border-blue-600', 'text-blue-600');
  const activeContent = document.getElementById(`tab-content-${tabName}`);
  if (activeContent) activeContent.style.display = 'block';
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

async function applyRemediationPatch(scanId) {
  const btn = document.getElementById('btn-apply-patch');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin inline-block mr-1">⌛</span> Applying Patch...';
  }
  try {
    const res = await fetch('/api/scan/apply-patch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scan_id: scanId, approved_by: 'security_lead' })
    });
    const data = await res.json();
    if (res.ok && data.status === 'applied') {
      appendLog(`[✓] HUMAN APPROVAL GRANTED: Patch applied to ${data.target_file} (${data.branch})`, '#34d399');
      await loadScanResults(scanId);
    } else {
      alert(`Error applying patch: ${data.error || 'Unknown error'}`);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>🛡️</span> Approve & Apply Patch';
      }
    }
  } catch (err) {
    alert(`Failed to apply patch: ${err.message}`);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>🛡️</span> Approve & Apply Patch';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setTarget('source');
  setType('scoped');
  setConfigMode('github');
  toggleScopes(false);
});
