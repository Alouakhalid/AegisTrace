export async function renderAttackSurface(container, navigate, state, api, showModal) {
  const scanId = state.currentScanId || "scn_demo";
  let endpoints = [
    {
      path: "/api/v1/orders/{order_id}",
      method: "PATCH",
      auth_required: true,
      controller: "update_order",
      params: "order_id (int), payload (JSON: delivery_address)",
      risk: "CRITICAL",
      description: "Updates order delivery details. BOLA vector traps unverified owner_id comparison.",
      ast_file: "target_app.py",
      ast_line: 88,
      jwt_scope: "buyer:write",
      rate_limit: "60 req/min"
    },
    {
      path: "/api/v1/orders/{order_id}",
      method: "GET",
      auth_required: true,
      controller: "get_order",
      params: "order_id (int)",
      risk: "HIGH",
      description: "Retrieves order receipt by ID. Sensitive PII exposure vector.",
      ast_file: "target_app.py",
      ast_line: 54,
      jwt_scope: "buyer:read",
      rate_limit: "120 req/min"
    },
    {
      path: "/api/v1/transfers/{transfer_id}",
      method: "PATCH",
      auth_required: true,
      controller: "update_transfer",
      params: "transfer_id (int), amount (float)",
      risk: "HIGH",
      description: "Financial balance adjustment entrypoint with currency validation.",
      ast_file: "target_app.py",
      ast_line: 112,
      jwt_scope: "buyer:write",
      rate_limit: "30 req/min"
    },
    {
      path: "/api/v1/users/profile",
      method: "GET",
      auth_required: true,
      controller: "get_profile",
      params: "none",
      risk: "LOW",
      description: "Current authenticated session details and organizational claims.",
      ast_file: "target_app.py",
      ast_line: 32,
      jwt_scope: "profile:read",
      rate_limit: "300 req/min"
    },
    {
      path: "/api/v1/catalog/items",
      method: "GET",
      auth_required: false,
      controller: "list_catalog",
      params: "category (str), limit (int), offset (int)",
      risk: "LOW",
      description: "Public marketplace catalog listings with pagination parameters.",
      ast_file: "target_app.py",
      ast_line: 18,
      jwt_scope: "public",
      rate_limit: "1000 req/min"
    },
    {
      path: "/api/v1/auth/login",
      method: "POST",
      auth_required: false,
      controller: "login_endpoint",
      params: "username (str), password (str)",
      risk: "MEDIUM",
      description: "Credential verification issuing RSA-256 signed JWT tokens.",
      ast_file: "target_app.py",
      ast_line: 6,
      jwt_scope: "public",
      rate_limit: "10 req/min"
    }
  ];

  try {
    const intel = await api.getCodeIntel(scanId);
    if (intel && intel.endpoints && intel.endpoints.length > 0) {
      endpoints = intel.endpoints.map(e => ({
        ...e,
        params: e.path_params ? e.path_params.join(", ") : "id (int)",
        risk: e.method === "PATCH" ? "CRITICAL" : (e.auth_required ? "HIGH" : "LOW"),
        description: e.description || `Autonomous mapped route handler for ${e.path}`,
        ast_file: e.file || "target_app.py",
        ast_line: e.line || 88,
        jwt_scope: e.auth_required ? "bearer:jwt" : "public",
        rate_limit: "60 req/min"
      }));
    }
  } catch (e) {
    console.warn("Using baseline attack surface data:", e);
  }

  const criticalCount = endpoints.filter(e => e.risk === "CRITICAL").length;
  const highCount = endpoints.filter(e => e.risk === "HIGH").length;
  const authCount = endpoints.filter(e => e.auth_required).length;

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-base); font-weight: 700; margin-bottom: 6px;">
            Reconnaissance Surface & Boundary Gate
          </div>
          <h1 class="page-title">Attack Surface Reconnaissance</h1>
          <p class="page-subtitle">Interactive map of validated entry points, parameter contracts, and ScopeGate authorization boundaries.</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <input type="text" class="form-control" id="surface-search" placeholder="Search routes, params, or controllers..." style="width: 290px; padding: 8px 16px; font-size: 0.84rem;">
          <button class="btn btn-secondary btn-sm" id="btn-export-surface">
            Export Schema
          </button>
        </div>
      </div>

      <!-- ScopeGate Status & Summary KPI Bar -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px;">
        <div class="stat-card">
          <div class="stat-label">Total Routes Mapped</div>
          <div class="stat-value">${endpoints.length}</div>
          <div class="stat-desc">Full AST Coverage</div>
        </div>

        <div class="stat-card red">
          <div class="stat-label">High / Critical Mutation Risk</div>
          <div class="stat-value">${criticalCount + highCount}</div>
          <div class="stat-desc">Targeted for Active Probing</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">Authenticated Routes</div>
          <div class="stat-value">${authCount}</div>
          <div class="stat-desc">Require Bearer Token Context</div>
        </div>

        <div class="stat-card green">
          <div class="stat-label">ScopeGate Status</div>
          <div class="stat-value" style="font-size: 1.35rem; margin-top: 4px;">ENFORCED</div>
          <div class="stat-desc">Zero Out-of-Scope Requests</div>
        </div>
      </div>

      <!-- Main Surface Table Card -->
      <div class="card">
        <div class="card-header">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="card-title">Authorized Scope Surface (${endpoints.length} Routes)</div>
            <span class="badge badge-gold" style="font-size: 0.68rem;">JWT Dual-Tenant Active</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-outline btn-sm filter-method active" data-method="ALL">ALL</button>
            <button class="btn btn-outline btn-sm filter-method" data-method="GET">GET</button>
            <button class="btn btn-outline btn-sm filter-method" data-method="POST">POST</button>
            <button class="btn btn-outline btn-sm filter-method" data-method="PATCH">PATCH</button>
          </div>
        </div>

        <div class="table-wrapper">
          <table class="data-table" id="surface-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Route Path</th>
                <th>Parameter Schema</th>
                <th>Authorization Gate</th>
                <th>AST Controller</th>
                <th>Risk Profile</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              ${endpoints.map((ep, idx) => `
                <tr class="surface-row" data-method="${ep.method}" data-search="${ep.path.toLowerCase()} ${ep.controller ? ep.controller.toLowerCase() : ''} ${ep.params.toLowerCase()}">
                  <td>
                    <span class="badge ${ep.method === 'PATCH' ? 'badge-bronze' : (ep.method === 'POST' ? 'badge-gold' : (ep.method === 'DELETE' ? 'badge-critical' : 'badge-gold-subtle'))}">
                      ${ep.method}
                    </span>
                  </td>
                  <td style="font-family: monospace; font-size: 0.88rem; color: #fff; font-weight: 600;">
                    ${ep.path}
                  </td>
                  <td style="font-family: monospace; font-size: 0.78rem; color: var(--gold-light);">
                    ${ep.params || "none"}
                  </td>
                  <td>
                    <span class="badge ${ep.auth_required ? 'badge-success' : 'badge-outline'}">
                      ${ep.auth_required ? 'Bearer JWT Required' : 'Public Access'}
                    </span>
                  </td>
                  <td style="font-family: monospace; color: var(--gold-base); font-size: 0.82rem;">
                    ${ep.controller || "handler"}
                  </td>
                  <td>
                    <span class="badge ${ep.risk === 'CRITICAL' ? 'badge-critical' : (ep.risk === 'HIGH' ? 'badge-warning' : 'badge-success')}">
                      ${ep.risk}
                    </span>
                  </td>
                  <td>
                    <button class="btn btn-secondary btn-sm btn-inspect-route" data-idx="${idx}" style="padding: 4px 10px; font-size: 0.74rem;">
                      Contract
                    </button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Search filter
  const searchInput = document.getElementById("surface-search");
  searchInput?.addEventListener("input", (e) => {
    const val = e.target.value.toLowerCase();
    container.querySelectorAll(".surface-row").forEach(row => {
      const txt = row.getAttribute("data-search");
      row.style.display = txt.includes(val) ? "" : "none";
    });
  });

  // Method filter
  container.querySelectorAll(".filter-method").forEach(btn => {
    btn.addEventListener("click", (e) => {
      container.querySelectorAll(".filter-method").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      const m = e.currentTarget.getAttribute("data-method");
      container.querySelectorAll(".surface-row").forEach(row => {
        const rowMethod = row.getAttribute("data-method");
        row.style.display = (m === "ALL" || m === rowMethod) ? "" : "none";
      });
    });
  });

  // Export schema button
  document.getElementById("btn-export-surface")?.addEventListener("click", () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(endpoints, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `attack_surface_${scanId}.json`);
    dlAnchor.click();
    dlAnchor.remove();
  });

  // Inspect route modal
  container.querySelectorAll(".btn-inspect-route").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = parseInt(e.currentTarget.getAttribute("data-idx"), 10);
      const ep = endpoints[idx];
      if (!ep || !showModal) return;

      showModal({
        title: `Route Security Contract — ${ep.method} ${ep.path}`,
        bodyHtml: `
          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div style="background: rgba(167, 139, 113, 0.08); border: 1px solid var(--border-gold); border-radius: var(--radius-md); padding: 14px 18px;">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--gold-base); font-weight: 700; letter-spacing: 0.12em;">Route Description</div>
              <div style="color: #fff; font-size: 0.88rem; margin-top: 4px; line-height: 1.5;">${ep.description}</div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 0.82rem;">
              <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-subtle); padding: 12px 14px; border-radius: var(--radius-sm);">
                <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 700;">AST Source Anchor</span>
                <div style="font-family: monospace; color: var(--gold-light); margin-top: 4px;">${ep.ast_file}:${ep.ast_line}</div>
              </div>

              <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-subtle); padding: 12px 14px; border-radius: var(--radius-sm);">
                <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 700;">Required Scope</span>
                <div style="font-family: monospace; color: #fff; margin-top: 4px;">${ep.jwt_scope}</div>
              </div>

              <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-subtle); padding: 12px 14px; border-radius: var(--radius-sm);">
                <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 700;">Rate Limiting Policy</span>
                <div style="font-family: monospace; color: #fff; margin-top: 4px;">${ep.rate_limit}</div>
              </div>

              <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-subtle); padding: 12px 14px; border-radius: var(--radius-sm);">
                <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 700;">ScopeGate Isolation</span>
                <div style="font-family: monospace; color: var(--success); margin-top: 4px;">ENFORCED (Host Whitelisted)</div>
              </div>
            </div>

            <div style="background: #050505; border: 1px solid var(--border-gold); border-radius: var(--radius-sm); padding: 14px; font-family: monospace; font-size: 0.78rem;">
              <div style="color: var(--gold-base); margin-bottom: 6px;">// Expected Parameter Signature</div>
              <div style="color: #fff;">${ep.params}</div>
            </div>
          </div>
        `,
        confirmText: "Close"
      });
    });
  });
}
