/**
 * Reports & compliance deliverables.
 *
 * Renders the report the backend actually generates for the selected scan and
 * links to the real CSV/JSON exports. Nothing here is pre-written: if a scan
 * has no findings the certificate says so.
 */

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString();
}

function sevBadge(sev) {
  const s = String(sev || "low").toLowerCase();
  return `<span class="badge badge-${s}">${String(sev || "—").toUpperCase()}</span>`;
}

export async function renderReports(container, navigate, state, api, toast) {
  let scans = [];
  try { scans = (await api.listScans()) || []; } catch { /* offline */ }

  const scanId = state.currentScanId || (scans[0] && scans[0].scan_id) || "";
  if (!scanId) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Deliverables</div>
          <h1 class="page-title">Reports</h1>
          <p class="page-subtitle">Reports are generated from a completed assessment.</p>
        </div>
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">📄</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">Nothing to report yet</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:20px;">Run an assessment and its certificate will appear here.</p>
        <button class="btn btn-primary" id="reports-new-scan">Run an assessment</button>
      </div>`;
    container.querySelector("#reports-new-scan")?.addEventListener("click", () => navigate("wizard"));
    return;
  }
  state.currentScanId = scanId;

  let rep = null;
  let error = null;
  try {
    rep = await api.getReport(scanId);
  } catch (e) {
    error = e.message;
  }

  const content = (rep && rep.content_json) || {};
  const findings = Array.isArray(content.findings) ? content.findings : [];
  const confirmed = findings.filter(f => String(f.verdict || "").toUpperCase() === "CONFIRMED").length;
  const fixed = findings.filter(f => String(f.status || "").toLowerCase() === "fixed").length;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Deliverables</div>
        <h1 class="page-title">Reports</h1>
        <p class="page-subtitle">Auditor-ready evidence for the selected assessment.</p>
      </div>
      <div class="surface-tools">
        <select class="form-control" id="reports-scan-select" style="max-width:250px;">
          ${scans.slice(0, 25).map(s => `<option value="${s.scan_id}" ${s.scan_id === scanId ? "selected" : ""}>${s.scan_id} · ${s.status}</option>`).join("")}
        </select>
        <a class="btn btn-secondary" href="/api/v1/reports/${encodeURIComponent(scanId)}/export?format=csv" download>CSV</a>
        <a class="btn btn-secondary" href="/api/v1/reports/${encodeURIComponent(scanId)}/export?format=json" download>JSON</a>
        <button class="btn btn-primary" id="btn-print-report">Print</button>
      </div>
    </div>

    ${error ? `<div class="dash-alert">Could not load the report: ${error}</div>` : ""}

    ${!rep ? "" : `
    <div class="card report-cert">
      <div class="report-cert-head">
        <div>
          <div class="page-eyebrow">Security attestation</div>
          <div class="card-title" style="font-size:1.3rem;">${rep.report_type || "Security Assessment"}</div>
          <div class="report-meta">
            <span class="mono">${rep.scan_id}</span>
            <span>·</span>
            <span>${fmtDate(rep.generated_at)}</span>
          </div>
        </div>
        <div class="report-cert-badges">
          <span class="badge badge-cyan">${findings.length} findings</span>
          <span class="badge badge-success">${confirmed} confirmed</span>
          <span class="badge badge-outline">${fixed} fixed</span>
        </div>
      </div>

      <div class="report-summary">${rep.executive_summary || "No executive summary was produced for this assessment."}</div>

      <div class="report-section-title">Findings in this assessment</div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>ID</th><th>Title</th><th>CWE</th><th>Severity</th><th>CVSS</th><th>Verdict</th><th>Status</th><th>Endpoint</th></tr></thead>
          <tbody>
            ${findings.map(f => `
              <tr>
                <td class="mono dim">${f.id || "—"}</td>
                <td>${f.title || "—"}</td>
                <td>${f.category ? `<span class="badge badge-outline">${f.category}</span>` : "—"}</td>
                <td>${sevBadge(f.severity)}</td>
                <td class="mono">${f.cvss_score ?? "—"}</td>
                <td><span class="badge ${String(f.verdict || "").toUpperCase() === "CONFIRMED" ? "badge-critical" : "badge-outline"}">${f.verdict || "—"}</span></td>
                <td class="dim">${f.status || "—"}</td>
                <td class="mono dim">${f.endpoint || "—"}</td>
              </tr>`).join("") || `<tr><td colspan="8" class="empty-row">This assessment recorded no findings.</td></tr>`}
          </tbody>
        </table>
      </div>

      <p class="report-footnote">
        Exports above are generated live from the evidence vault. CSV and JSON contain the same rows you see here.
      </p>
    </div>`}
  `;

  container.querySelector("#reports-scan-select")?.addEventListener("change", e => {
    state.currentScanId = e.target.value;
    navigate("reports");
  });
  container.querySelector("#btn-print-report")?.addEventListener("click", () => window.print());
  if (toast && rep) toast("Report loaded from the evidence vault", "success");
}
