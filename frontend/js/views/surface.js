/**
 * Attack surface map.
 *
 * Everything shown here comes from the AST extraction stored for the selected
 * scan. The view deliberately does not invent scopes, rate limits or source
 * anchors: when the analyzer did not record a value the cell says "not
 * recorded", because a security console that guesses is worse than one that
 * admits a gap.
 */

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function methodClass(method) {
  const m = String(method || "").toUpperCase();
  if (m === "GET") return "badge-cyan-subtle";
  if (m === "POST") return "badge-cyan";
  if (m === "PATCH" || m === "PUT") return "badge-bronze";
  if (m === "DELETE") return "badge-critical";
  return "badge-outline";
}

function riskOf(ep) {
  // Risk is a function of what the route can do, not a random label.
  const mutating = MUTATING.has(String(ep.method || "").toUpperCase());
  if (mutating && !ep.auth_required) return "CRITICAL";
  if (mutating) return "HIGH";
  if (ep.auth_required) return "MEDIUM";
  return "LOW";
}

function riskClass(risk) {
  if (risk === "CRITICAL") return "badge-critical";
  if (risk === "HIGH") return "badge-warning";
  if (risk === "MEDIUM") return "badge-cyan";
  return "badge-success";
}

export async function renderAttackSurface(container, navigate, state, api, showModal) {
  let scans = [];
  try {
    scans = (await api.listScans()) || [];
  } catch { /* offline */ }

  let scanId = state.currentScanId || (scans[0] && scans[0].scan_id) || "";
  if (!scanId) {
    container.innerHTML = emptyState("No assessments yet", "The attack surface is derived from a scan's AST artifacts. Run your first assessment to populate it.", navigate);
    bindEmpty(container, navigate);
    return;
  }
  state.currentScanId = scanId;

  let intel = null;
  let error = null;
  try {
    intel = await api.getCodeIntel(scanId);
  } catch (e) {
    error = e.message;
  }

  const endpoints = (intel && Array.isArray(intel.endpoints) ? intel.endpoints : []).map(e => ({
    ...e,
    path: e.path || "/",
    method: String(e.method || "GET").toUpperCase(),
    params: Array.isArray(e.path_params) && e.path_params.length ? e.path_params.join(", ") : "",
    risk: riskOf(e)
  }));

  const invariants = (intel && Array.isArray(intel.invariants) ? intel.invariants : []);
  const invariantRoutes = new Set(
    invariants.map(i => `${String(i.http_method || "").toUpperCase()} ${i.endpoint_id || ""}`)
  );

  if (!endpoints.length) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Reconnaissance surface</div>
          <h1 class="page-title">Attack Surface</h1>
          <p class="page-subtitle">No routes were extracted for this assessment.</p>
        </div>
        ${scanPicker(scans, scanId)}
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">🛰️</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">No routes recorded</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;max-width:520px;margin:0 auto 20px;line-height:1.6;">
          ${error ? `The code-intelligence endpoint returned: <code>${error}</code>` : "The AST pass found no FastAPI/Flask route decorators in this repository. This is expected for non-Python targets or empty repositories."}
        </p>
        <button class="btn btn-primary" id="surface-new-scan">Run a new assessment</button>
      </div>`;
    bindEmpty(container, navigate);
    bindScanPicker(container, state, navigate);
    return;
  }

  const critical = endpoints.filter(e => e.risk === "CRITICAL").length;
  const high = endpoints.filter(e => e.risk === "HIGH").length;
  const authed = endpoints.filter(e => e.auth_required).length;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Reconnaissance surface</div>
        <h1 class="page-title">Attack Surface</h1>
        <p class="page-subtitle">Every route the AST pass extracted, with its authorization gate and inferred risk.</p>
      </div>
      <div class="surface-tools">
        ${scanPicker(scans, scanId)}
        <input type="text" class="form-control" id="surface-search" placeholder="Filter routes…" spellcheck="false">
        <button class="btn btn-secondary" id="btn-export-surface">Export JSON</button>
      </div>
    </div>

    <div class="kpi-grid kpi-grid-4">
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Routes</span><span class="stat-icon">🧭</span></div>
        <div class="stat-value">${endpoints.length}</div>
        <div class="stat-desc">Extracted from source</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Unauthenticated mutations</span><span class="stat-icon">🔥</span></div>
        <div class="stat-value" style="color:${critical ? "var(--critical)" : "var(--success)"};">${critical}</div>
        <div class="stat-desc">Highest priority</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">Authenticated mutations</span><span class="stat-icon">🔐</span></div>
        <div class="stat-value">${high}</div>
        <div class="stat-desc">BOLA / IDOR candidates</div>
      </div>
      <div class="stat-card">
        <div class="stat-header"><span class="stat-label">With auth</span><span class="stat-icon">🎫</span></div>
        <div class="stat-value">${authed}<span style="font-size:0.8rem;color:var(--text-muted);"> / ${endpoints.length}</span></div>
        <div class="stat-desc">${invariants.length} invariants derived</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div class="card-title">Routes</div>
        <div class="filter-row">
          ${["ALL", "GET", "POST", "PATCH", "DELETE"].map((m, i) =>
            `<button class="btn btn-outline btn-sm filter-method ${i === 0 ? "active" : ""}" data-method="${m}">${m}</button>`).join("")}
        </div>
      </div>
      <div class="table-wrapper">
        <table class="data-table" id="surface-table">
          <thead>
            <tr><th>Method</th><th>Path</th><th>Path params</th><th>Auth</th><th>Handler</th><th>Source</th><th>Risk</th><th></th></tr>
          </thead>
          <tbody>
            ${endpoints.map((ep, idx) => `
              <tr class="surface-row" data-method="${ep.method}" data-search="${(ep.path + " " + (ep.controller || "")).toLowerCase()}">
                <td><span class="badge ${methodClass(ep.method)}">${ep.method}</span></td>
                <td class="mono" style="color:#fff;font-weight:600;">${ep.path}</td>
                <td class="mono dim">${ep.params || "—"}</td>
                <td><span class="badge ${ep.auth_required ? "badge-success" : "badge-outline"}">${ep.auth_required ? "required" : "public"}</span></td>
                <td class="mono dim">${ep.controller || "—"}</td>
                <td class="dim">${ep.source || "—"}</td>
                <td><span class="badge ${riskClass(ep.risk)}">${ep.risk}</span></td>
                <td><button class="btn btn-secondary btn-sm btn-inspect-route" data-idx="${idx}">Contract</button></td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>`;

  bindScanPicker(container, state, navigate);

  const search = container.querySelector("#surface-search");
  const applyFilters = () => {
    const term = (search?.value || "").toLowerCase();
    const method = container.querySelector(".filter-method.active")?.getAttribute("data-method") || "ALL";
    container.querySelectorAll(".surface-row").forEach(row => {
      const okTerm = row.getAttribute("data-search").includes(term);
      const okMethod = method === "ALL" || row.getAttribute("data-method") === method;
      row.style.display = okTerm && okMethod ? "" : "none";
    });
  };
  search?.addEventListener("input", applyFilters);
  container.querySelectorAll(".filter-method").forEach(btn => {
    btn.addEventListener("click", e => {
      container.querySelectorAll(".filter-method").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      applyFilters();
    });
  });

  container.querySelector("#btn-export-surface")?.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify({ scan_id: scanId, endpoints, invariants }, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `attack_surface_${scanId}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  });

  container.querySelectorAll(".btn-inspect-route").forEach(btn => {
    btn.addEventListener("click", e => {
      const ep = endpoints[Number(e.currentTarget.getAttribute("data-idx"))];
      if (!ep || !showModal) return;
      const linked = invariants.filter(i => String(i.endpoint_id || "") === String(ep.endpoint_id || ""));
      showModal({
        title: `${ep.method} ${ep.path}`,
        bodyHtml: `
          <div class="contract-grid">
            <div class="contract-cell"><span>Authorization</span><b>${ep.auth_required ? "Required" : "None detected"}</b></div>
            <div class="contract-cell"><span>Handler</span><b>${ep.controller || "not recorded"}</b></div>
            <div class="contract-cell"><span>Path params</span><b>${ep.params || "none"}</b></div>
            <div class="contract-cell"><span>Detected by</span><b>${ep.source || "not recorded"}</b></div>
            <div class="contract-cell"><span>Endpoint id</span><b>${ep.endpoint_id || "—"}</b></div>
            <div class="contract-cell"><span>Invariants</span><b>${linked.length}</b></div>
          </div>
          ${linked.length ? `<div class="contract-code">${linked.map(i => `• ${i.statement || i.description || i.id}`).join("\n")}</div>`
            : `<p class="dim" style="font-size:0.82rem;margin-top:12px;">No security invariant was derived for this route.</p>`}
        `,
        confirmText: "Close"
      });
    });
  });
}

function scanPicker(scans, current) {
  if (!scans.length) return "";
  return `
    <select class="form-control" id="surface-scan-select" style="max-width:260px;">
      ${scans.slice(0, 25).map(s =>
        `<option value="${s.scan_id}" ${s.scan_id === current ? "selected" : ""}>${s.scan_id} · ${s.status}</option>`).join("")}
    </select>`;
}

function bindScanPicker(container, state, navigate) {
  container.querySelector("#surface-scan-select")?.addEventListener("change", e => {
    state.currentScanId = e.target.value;
    navigate("surface");
  });
}

function bindEmpty(container, navigate) {
  container.querySelector("#surface-new-scan")?.addEventListener("click", () => navigate("wizard"));
}

function emptyState(title, body, navigate) {
  return `
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Reconnaissance surface</div>
        <h1 class="page-title">Attack Surface</h1>
        <p class="page-subtitle">${body}</p>
      </div>
    </div>
    <div class="card" style="padding:52px 32px;text-align:center;">
      <div style="font-size:2.2rem;margin-bottom:12px;">🛰️</div>
      <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">${title}</h2>
      <button class="btn btn-primary" id="surface-new-scan">Run an assessment</button>
    </div>`;
}
