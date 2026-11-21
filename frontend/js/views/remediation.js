/**
 * Remediation center.
 *
 * Shows the patches the Remediation agent actually produced: the stored diff,
 * its SHA-256, the branch it was committed to and the review decision. The test
 * outcome is only reported when the pipeline recorded one — the old screen
 * printed "10/10 PASSED" and a fabricated pytest log for every visit.
 */

function diffLineClass(line) {
  if (line.startsWith("+++") || line.startsWith("---")) return "info";
  if (line.startsWith("@@")) return "hunk";
  if (line.startsWith("+")) return "add";
  if (line.startsWith("-")) return "del";
  return "ctx";
}

function renderDiff(diff) {
  if (!diff || !String(diff).trim()) return `<p class="empty-row" style="border:0;">No diff was stored for this patch.</p>`;
  return String(diff).split("\n").map(line => {
    const cls = diffLineClass(line);
    return `<div class="diff-line ${cls}">${line.replace(/</g, "&lt;") || "&nbsp;"}</div>`;
  }).join("");
}

export async function renderRemediation(container, navigate, state, api, toast) {
  let approvals = [];
  try { approvals = (await api.listApprovals()) || []; } catch { /* offline */ }

  const pending = approvals.filter(a => String(a.status || "").toLowerCase() === "pending");
  const decided = approvals.filter(a => String(a.status || "").toLowerCase() !== "pending");
  const list = pending.length ? pending : approvals;
  const selected = list.find(a => a.patch_id === state.selectedPatchId) || list[0] || null;
  if (selected) state.selectedPatchId = selected.patch_id;

  if (!approvals.length) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Remediation</div>
          <h1 class="page-title">Remediation Center</h1>
          <p class="page-subtitle">Patches are only produced for findings that survived sandbox replay.</p>
        </div>
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">🩹</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">No patches yet</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;max-width:520px;margin:0 auto 20px;line-height:1.6;">
          A patch requires a confirmed finding. Static-only assessments stop before this stage by design.
        </p>
        <button class="btn btn-primary" id="remed-new-scan">Run an assessment</button>
      </div>`;
    container.querySelector("#remed-new-scan")?.addEventListener("click", () => navigate("wizard"));
    return;
  }

  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Remediation</div>
        <h1 class="page-title">Remediation Center</h1>
        <p class="page-subtitle">${approvals.length} patch${approvals.length === 1 ? "" : "es"} in the vault · ${pending.length} awaiting review</p>
      </div>
      <div class="surface-tools">
        ${list.length > 1 ? `
          <select class="form-control" id="remed-select" style="max-width:300px;">
            ${list.map(a => `<option value="${a.patch_id}" ${a.patch_id === selected.patch_id ? "selected" : ""}>${a.patch_id} · ${a.status}</option>`).join("")}
          </select>` : ""}
        <button class="btn btn-secondary" id="remed-btn-approval">Approval queue →</button>
      </div>
    </div>

    <div class="kpi-grid kpi-grid-4">
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Patches</span><span class="stat-icon">🧾</span></div>
        <div class="stat-value">${approvals.length}</div>
        <div class="stat-desc">Synthesised by the agent</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Pending</span><span class="stat-icon">⏳</span></div>
        <div class="stat-value" style="color:${pending.length ? "var(--warning)" : "var(--text-secondary)"};">${pending.length}</div>
        <div class="stat-desc">Awaiting a human</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Approved</span><span class="stat-icon">✅</span></div>
        <div class="stat-value">${approvals.filter(a => String(a.status).toLowerCase() === "approved").length}</div>
        <div class="stat-desc">Merged by an operator</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Rejected</span><span class="stat-icon">⛔</span></div>
        <div class="stat-value">${approvals.filter(a => String(a.status).toLowerCase() === "rejected").length}</div>
        <div class="stat-desc">Blocked by an operator</div>
      </div>
    </div>

    ${selected ? `
    <div class="card">
      <div class="card-header">
        <div class="card-title">Unified diff</div>
        <div class="surface-tools">
          <span class="badge badge-outline mono">${selected.patch_id}</span>
          <span class="badge ${String(selected.status).toLowerCase() === "pending" ? "badge-medium" : "badge-outline"}">${selected.status}</span>
        </div>
      </div>

      <div class="patch-meta">
        <div class="patch-meta-cell"><span>Finding</span><b>${selected.finding_title || selected.finding_id || "—"}</b></div>
        <div class="patch-meta-cell"><span>Branch</span><b>${selected.branch || "not recorded"}</b></div>
        <div class="patch-meta-cell"><span>Target file</span><b>${selected.target_file || "not recorded"}</b></div>
        <div class="patch-meta-cell"><span>SHA-256</span><b class="mono">${selected.patch_sha256 || "—"}</b></div>
      </div>

      <div class="diff-view">${renderDiff(selected.unified_diff)}</div>
    </div>

    <div class="card">
      <div class="card-header"><div class="card-title">All patches</div></div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>Patch</th><th>Finding</th><th>Branch</th><th>Status</th><th>Created</th><th></th></tr></thead>
          <tbody>
            ${approvals.map(a => `
              <tr>
                <td class="mono">${a.patch_id}</td>
                <td>${a.finding_title || a.finding_id || "—"}</td>
                <td class="mono dim">${a.branch || "—"}</td>
                <td><span class="badge ${String(a.status).toLowerCase() === "pending" ? "badge-medium" : "badge-outline"}">${a.status}</span></td>
                <td class="dim">${a.created_at || "—"}</td>
                <td><button class="btn btn-outline btn-sm patch-pick" data-id="${a.patch_id}">View</button></td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>` : ""}
  `;

  container.querySelector("#remed-select")?.addEventListener("change", e => {
    state.selectedPatchId = e.target.value;
    navigate("remediation");
  });
  container.querySelectorAll(".patch-pick").forEach(b => b.addEventListener("click", e => {
    state.selectedPatchId = e.currentTarget.getAttribute("data-id");
    navigate("remediation");
  }));
  container.querySelector("#remed-btn-approval")?.addEventListener("click", () => navigate("approvals"));
}
