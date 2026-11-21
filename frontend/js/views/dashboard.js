import { drawRadialGauge } from "../charts.js";

/**
 * Executive overview.
 * Every number is derived from the API. When the vault is empty the UI says so
 * instead of substituting placeholder values.
 */

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];

function num(v) {
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

function relativeTime(iso) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

function statusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "completed") return "badge-success";
  if (s === "failed") return "badge-critical";
  if (s === "running" || s === "queued") return "badge-cyan";
  return "badge-outline";
}

export async function renderDashboard(container, navigate, state, api) {
  let stats = {};
  let scans = [];
  let approvals = [];
  let findings = [];
  let loadError = null;

  try {
    const [s, sc, ap, fd] = await Promise.all([
      api.getOverviewStats().catch(() => null),
      api.listScans().catch(() => []),
      api.listApprovals().catch(() => []),
      api.listFindings().catch(() => [])
    ]);
    stats = s || {};
    scans = Array.isArray(sc) ? sc : [];
    approvals = Array.isArray(ap) ? ap : [];
    findings = Array.isArray(fd) ? fd : [];
  } catch (e) {
    loadError = e.message;
  }

  const total = num(stats.total_findings);
  const confirmed = num(stats.confirmed_findings);
  const resolved = num(stats.resolved_findings);
  const activeScans = scans.filter(s => ["running", "queued"].includes(String(s.status).toLowerCase())).length;

  // Severity mix across the vault (from scan aggregates, which are computed in SQL).
  const severity = SEVERITY_ORDER.reduce((acc, k) => {
    acc[k] = scans.reduce((sum, s) => sum + num(s[`${k}_findings`]), 0);
    return acc;
  }, {});
  const sevTotal = SEVERITY_ORDER.reduce((sum, k) => sum + severity[k], 0);

  const pendingApprovals = approvals.filter(a => String(a.status).toLowerCase() === "pending");

  container.innerHTML = `
    <div class="dash">
      <!-- Header -->
      <div class="page-header">
        <div>
          <div class="dash-eyebrow">
            <span class="live-dot"></span>
            Live posture · <span id="dash-updated">just now</span>
          </div>
          <h1 class="page-title">Autonomous Security Overview</h1>
          <p class="page-subtitle">
            Cross-agent telemetry from the evidence vault. A finding is only counted once it survived sandbox replay.
          </p>
        </div>
        <div class="dash-actions">
          <button class="btn btn-secondary" id="dash-btn-view-pipeline">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            Pipeline
          </button>
          <button class="btn btn-primary" id="dash-btn-new-scan">+ New Assessment</button>
        </div>
      </div>

      ${loadError ? `<div class="dash-alert">Could not reach the API: ${loadError}</div>` : ""}

      <!-- KPI row -->
      <div class="kpi-grid">
        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Assessments</span>
            <span class="stat-icon">⚡</span>
          </div>
          <div class="stat-value">${num(stats.total_scans)}</div>
          <div class="stat-desc">${activeScans > 0 ? `<span class="pulse-text">${activeScans} running now</span>` : "Full agent cycles"}</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Findings</span>
            <span class="stat-icon">⚠️</span>
          </div>
          <div class="stat-value">${total}</div>
          <div class="stat-desc">Recorded in the vault</div>
        </div>

        <div class="stat-card gold">
          <div class="stat-header">
            <span class="stat-label">Confirmed</span>
            <span class="stat-icon">✓</span>
          </div>
          <div class="stat-value" style="color: var(--success);">${confirmed}</div>
          <div class="stat-desc">Reproduced 3× in sandbox</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Pending approvals</span>
            <span class="stat-icon">🛡️</span>
          </div>
          <div class="stat-value" style="color: ${pendingApprovals.length ? "var(--warning)" : "var(--text-secondary)"};">${pendingApprovals.length}</div>
          <div class="stat-desc">${pendingApprovals.length ? "Awaiting human decision" : "Nothing blocked"}</div>
        </div>

        <div class="stat-card">
          <div class="stat-header">
            <span class="stat-label">Patched</span>
            <span class="stat-icon">🔧</span>
          </div>
          <div class="stat-value">${resolved}</div>
          <div class="stat-desc">Exploit replay closed</div>
        </div>
      </div>

      <!-- Main grid -->
      <div class="dash-grid">
        <!-- Posture + severity -->
        <section class="card dash-posture">
          <div class="card-header">
            <div class="card-title">Security posture</div>
            <span class="badge ${confirmed === 0 ? "badge-success" : "badge-medium"}">
              ${confirmed === 0 ? "No unresolved proof" : `${confirmed} confirmed`}
            </span>
          </div>
          <div class="posture-body">
            <div class="posture-gauge">
              ${
                stats.security_score !== null && stats.security_score !== undefined
                  ? `<canvas id="gaugeCanvas" width="180" height="180"></canvas>`
                  : `<div class="gauge-empty"><b>N/A</b><span>Run an assessment to compute posture</span></div>`
              }
            </div>
            <div class="severity-list">
              ${SEVERITY_ORDER.map(sev => {
                const value = severity[sev];
                const pct = sevTotal ? Math.round((value / sevTotal) * 100) : 0;
                return `
                  <div class="sev-row">
                    <span class="sev-label">${sev}</span>
                    <span class="sev-track"><span class="sev-fill ${sev}" style="width:${pct}%"></span></span>
                    <span class="sev-value">${value}</span>
                  </div>`;
              }).join("")}
              <div class="sev-note">${sevTotal ? `${sevTotal} findings classified across ${scans.length} assessments` : "No classified findings yet"}</div>
            </div>
          </div>
        </section>

        <!-- Quick launch -->
        <section class="card dash-launch">
          <div class="card-header">
            <div class="card-title">Run an assessment</div>
            <span class="badge badge-cyan">7 agents</span>
          </div>
          <p class="launch-hint">Paste a repository URL. The pipeline clones it, derives invariants, and probes a live target if one is provided.</p>
          <div class="launch-input-row">
            <input id="dash-repo-input" class="form-control" type="text" spellcheck="false"
                   placeholder="https://github.com/owner/repository"
                   value="${state.targetRepoUrl || ""}">
          </div>
          <button class="btn btn-primary" id="dash-btn-run-audit" style="width:100%;justify-content:center;">
            ⚡ Analyze &amp; audit
          </button>
          <div class="launch-presets">
            <button class="chip" data-url="https://github.com/we45/Vulnerable-Flask-App">Vulnerable-Flask-App</button>
            <button class="chip" data-url="https://github.com/renceInbox/fastapi-todo">fastapi-todo</button>
            <button class="chip" data-url="https://github.com/Ishanoshada/flask-auth-app">flask-auth-app</button>
          </div>
        </section>
      </div>

      <!-- Recent + approvals -->
      <div class="dash-grid-2">
        <section class="card">
          <div class="card-header">
            <div class="card-title">Recent assessments</div>
            <a href="javascript:void(0)" id="link-all-scans" class="link-more">All assessments →</a>
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr><th>Scan</th><th>Status</th><th>Findings</th><th>Confirmed</th><th>Started</th><th></th></tr>
              </thead>
              <tbody>
                ${scans.slice(0, 6).map(s => `
                  <tr>
                    <td class="mono">${s.scan_id}</td>
                    <td><span class="badge ${statusClass(s.status)}">${s.status}</span></td>
                    <td>${num(s.total_findings)}</td>
                    <td style="color: var(--success); font-weight: 700;">${num(s.verified_findings)}</td>
                    <td class="dim">${relativeTime(s.start_time)}</td>
                    <td><button class="btn btn-outline btn-sm btn-view-scan" data-scan-id="${s.scan_id}">Open</button></td>
                  </tr>`).join("") || `
                  <tr><td colspan="6" class="empty-row">No assessments yet — launch your first run above.</td></tr>`}
              </tbody>
            </table>
          </div>
        </section>

        <section class="card">
          <div class="card-header">
            <div class="card-title">Approval queue</div>
            ${pendingApprovals.length ? `<span class="badge badge-medium">${pendingApprovals.length} pending</span>` : `<span class="badge badge-success">clear</span>`}
          </div>
          <div class="approval-list">
            ${pendingApprovals.slice(0, 3).map(a => `
              <div class="approval-item">
                <div class="approval-top">
                  <span class="mono dim">${a.patch_id || "—"}</span>
                  <span class="badge badge-medium">pending</span>
                </div>
                <div class="approval-title">${a.finding_title || "Remediation patch"}</div>
                <div class="approval-meta">
                  ${a.branch ? `<span class="mono">${a.branch}</span>` : ""}
                  ${a.target_file ? `<span class="mono dim">${a.target_file}</span>` : ""}
                </div>
                <button class="btn btn-secondary btn-sm btn-goto-approvals">Review</button>
              </div>`).join("") || `
              <div class="empty-row" style="border:0;">No patches are waiting for a human decision.</div>`}
          </div>
          ${pendingApprovals.length > 3 ? `<button class="btn btn-outline btn-sm" id="dash-btn-go-approvals" style="width:100%;margin-top:10px;justify-content:center;">View all ${pendingApprovals.length}</button>` : ""}
        </section>
      </div>

      <!-- Confirmed findings preview -->
      ${confirmed > 0 ? `
      <section class="card">
        <div class="card-header">
          <div class="card-title">Proven findings</div>
          <a href="javascript:void(0)" id="link-all-findings" class="link-more">Open findings →</a>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead><tr><th>Finding</th><th>Severity</th><th>CVSS</th><th>Endpoint</th><th>Verdict</th></tr></thead>
            <tbody>
              ${findings.slice(0, 5).map(f => `
                <tr>
                  <td>${f.title}</td>
                  <td><span class="badge badge-${String(f.severity || "low").toLowerCase()}">${f.severity}</span></td>
                  <td class="mono">${f.cvss_score ?? "—"}</td>
                  <td class="mono dim">${f.http_method || ""} ${f.endpoint || ""}</td>
                  <td><span class="badge ${String(f.verification_verdict).toUpperCase() === "CONFIRMED" ? "badge-critical" : "badge-outline"}">${f.verification_verdict || "—"}</span></td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </section>` : ""}
    </div>
  `;

  // ---- charts ----
  setTimeout(() => {
    const gauge = document.getElementById("gaugeCanvas");
    if (gauge && stats.security_score !== null && stats.security_score !== undefined) {
      drawRadialGauge(gauge, Number(stats.security_score), 100, "Posture", "#24C8F5");
    }
  }, 30);

  // ---- interactions ----
  const go = id => document.getElementById(id)?.addEventListener("click", () => navigate("wizard"));
  document.getElementById("dash-btn-new-scan")?.addEventListener("click", () => navigate("wizard"));
  document.getElementById("dash-btn-view-pipeline")?.addEventListener("click", () => navigate("workspace"));
  document.getElementById("link-all-scans")?.addEventListener("click", () => navigate("workspace"));
  document.getElementById("link-all-findings")?.addEventListener("click", () => navigate("findings"));
  document.getElementById("dash-btn-go-approvals")?.addEventListener("click", () => navigate("approvals"));
  container.querySelectorAll(".btn-goto-approvals").forEach(b => b.addEventListener("click", () => navigate("approvals")));

  const repoInput = container.querySelector("#dash-repo-input");
  const startAudit = () => {
    const val = (repoInput?.value || "").trim();
    if (!val) return;
    state.targetRepoUrl = val;
    navigate("wizard");
  };
  container.querySelector("#dash-btn-run-audit")?.addEventListener("click", startAudit);
  repoInput?.addEventListener("keydown", e => { if (e.key === "Enter") startAudit(); });

  container.querySelectorAll(".launch-presets .chip").forEach(btn => {
    btn.addEventListener("click", () => {
      const url = btn.getAttribute("data-url");
      if (repoInput) repoInput.value = url;
      state.targetRepoUrl = url;
    });
  });

  container.querySelectorAll(".btn-view-scan").forEach(btn => {
    btn.addEventListener("click", e => {
      state.currentScanId = e.currentTarget.getAttribute("data-scan-id");
      navigate("workspace");
    });
  });
}
