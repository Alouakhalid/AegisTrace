export async function renderCodeIntel(container, navigate, state, api) {
  let intelData = {
    endpoints: [
      { path: "/api/v1/orders/{order_id}", method: "PATCH", auth_required: true, controller: "update_order" },
      { path: "/api/v1/orders/{order_id}", method: "GET", auth_required: true, controller: "get_order" },
      { path: "/api/v1/transfers/{transfer_id}", method: "PATCH", auth_required: true, controller: "update_transfer" },
      { path: "/api/v1/users/profile", method: "GET", auth_required: true, controller: "get_profile" }
    ],
    invariants: [
      { id: "inv_order_01", title: "Tenant isolation on orders table", rule: "orders.owner_id == session.user_id", status: "verified" },
      { id: "inv_transfer_02", title: "Transfer authorization gate", rule: "transfers.sender_id == session.user_id", status: "verified" }
    ],
    graph: {
      nodes: [
        { id: "router", label: "FastAPI Router", type: "entry" },
        { id: "auth_mw", label: "Auth Middleware (get_current_user)", type: "security" },
        { id: "ctrl_order", label: "OrderController (update_order)", type: "logic" },
        { id: "model_order", label: "ORM Model (Order)", type: "model" },
        { id: "db_table", label: "Database (orders table)", type: "storage" }
      ],
      edges: [
        { from: "router", to: "auth_mw", label: "Depends()" },
        { from: "auth_mw", to: "ctrl_order", label: "Session Token" },
        { from: "ctrl_order", to: "model_order", label: "db.query()" },
        { from: "model_order", to: "db_table", label: "SQL Mutation" }
      ]
    }
  };

  const scanId = state.currentScanId || "scn_demo";
  try {
    const fetched = await api.getCodeIntel(scanId);
    if (fetched) intelData = fetched;
  } catch (e) {
    console.warn("Using fallback code intel data:", e);
  }

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <h1 class="page-title">Code Intelligence & Invariant Derivation</h1>
          <p class="page-subtitle">Static AST analysis, ORM model extraction, and architectural flow modeling.</p>
        </div>
      </div>

      <!-- Interactive Code Graph Visualizer (Gold Nodes & SVG Connectors) -->
      <div class="card card-central-glow" style="margin-bottom: 32px; border: 1px solid var(--border-gold);">
        <div class="card-header">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gold-light)" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Architectural Data Flow & Dependency Graph
          </div>
          <span class="badge badge-gold">AST Flow Verified</span>
        </div>
        
        <div style="background: #050505; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); padding: 36px 28px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow-x: auto;">
          ${intelData.graph.nodes.map((node, i) => `
            <div style="display: flex; align-items: center;">
              <div style="background: rgba(16, 15, 14, 0.9); border: 1px solid ${node.type === 'security' ? 'var(--gold-light)' : (node.type === 'logic' ? 'var(--critical)' : 'var(--border-subtle)')}; padding: 18px 22px; border-radius: var(--radius-md); text-align: center; min-width: 160px; box-shadow: 0 10px 30px rgba(0,0,0,0.7);">
                <div style="font-size: 8.5px; color: var(--gold-base); text-transform: uppercase; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 4px;">${node.type}</div>
                <div style="font-size: 0.88rem; font-weight: 700; color: #fff;">${node.label}</div>
              </div>
              ${i < intelData.graph.nodes.length - 1 ? `
                <div style="padding: 0 18px; display: flex; flex-direction: column; align-items: center;">
                  <span style="font-size: 9px; color: var(--text-muted); font-family: monospace; letter-spacing: 1px; margin-bottom: 6px;">${intelData.graph.edges[i] ? intelData.graph.edges[i].label : 'flows'}</span>
                  <div style="width: 50px; height: 2px; background: linear-gradient(90deg, var(--gold-base), var(--gold-light)); position: relative;">
                    <div style="position: absolute; right: 0; top: -4px; width: 0; height: 0; border-top: 5px solid transparent; border-bottom: 5px solid transparent; border-left: 6px solid var(--gold-light);"></div>
                  </div>
                </div>
              ` : ''}
            </div>
          `).join("")}
        </div>
      </div>

      <!-- Invariants & Discovered Routes Grid -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 28px;">
        <!-- Invariants Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">Derived Security Invariants</div>
            <span class="badge badge-success">Formal Proof</span>
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Invariant Title</th>
                  <th>Mathematical Rule</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${intelData.invariants.map(inv => `
                  <tr>
                    <td>
                      <div style="font-weight: 600; color: #fff;">${inv.title}</div>
                      <div style="font-size: 9px; color: var(--gold-base); font-family: monospace;">${inv.id}</div>
                    </td>
                    <td>
                      <code style="color: var(--gold-light); font-size: 0.78rem;">${inv.rule}</code>
                    </td>
                    <td><span class="badge badge-success">${inv.status}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Discovered Endpoints Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">AST Extracted Routes</div>
            <span class="badge badge-gold">${intelData.endpoints.length} Endpoints</span>
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Route Path</th>
                  <th>Controller Method</th>
                  <th>Auth</th>
                </tr>
              </thead>
              <tbody>
                ${intelData.endpoints.map(ep => `
                  <tr>
                    <td><span class="badge ${ep.method === 'PATCH' ? 'badge-gold' : 'badge-outline'}">${ep.method}</span></td>
                    <td style="font-family: monospace; font-size: 0.84rem; color: #fff;">${ep.path}</td>
                    <td style="font-family: monospace; color: var(--text-muted); font-size: 0.82rem;">${ep.controller}</td>
                    <td><span class="badge ${ep.auth_required ? 'badge-success' : 'badge-outline'}">${ep.auth_required ? 'Required' : 'Public'}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `;
}
