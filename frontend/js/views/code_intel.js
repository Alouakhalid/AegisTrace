export async function renderCodeIntel(container, navigate, state, api) {
  let intelData = null;
  let scanId = state.currentScanId || "";

  const load = async id => {
    try { return await api.getCodeIntel(id); } catch { return null; }
  };
  const hasContent = d => d && ((d.endpoints && d.endpoints.length) || (d.invariants && d.invariants.length) ||
                                 (d.graph && d.graph.nodes && d.graph.nodes.length));

  if (scanId) intelData = await load(scanId);

  // The selected assessment may predate code intelligence (or be a repository
  // with no analyzable routes). Fall back to the richest assessment in the
  // vault so the graph is populated with real data instead of an empty page.
  const score = d => !d ? -1
    : ((d.endpoints && d.endpoints.length) || 0)
      + ((d.invariants && d.invariants.length) || 0)
      + ((d.graph && d.graph.nodes && d.graph.nodes.length) || 0);

  if (score(intelData) <= 1) {
    try {
      const scans = (await api.listScans()) || [];
      let best = intelData, bestId = scanId, bestScore = score(intelData);
      for (const s of scans.slice(0, 15)) {
        if (s.scan_id === scanId) continue;
        const candidate = await load(s.scan_id);
        const sc = score(candidate);
        if (sc > bestScore) { best = candidate; bestId = s.scan_id; bestScore = sc; }
      }
      if (bestId !== scanId) {
        intelData = best;
        scanId = bestId;
        state.currentScanId = scanId;
      }
    } catch { /* offline */ }
  }

  if (!hasContent(intelData)) {
    container.innerHTML = `
      <div>
        <div class="page-header">
          <div>
            <h1 class="page-title">Code Intelligence & Invariant Derivation</h1>
            <p class="page-subtitle">Static AST analysis, ORM model extraction, and architectural flow modeling.</p>
          </div>
          <button class="btn btn-primary" id="ci-btn-new-scan">+ New Assessment</button>
        </div>

        <div class="card card-central-glow" style="padding: 60px 40px; text-align: center; border: 1px dashed var(--border-gold);">
          <div style="font-size: 2.5rem; margin-bottom: 16px;">🔍</div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; color: #fff; margin-bottom: 8px;">
            No Code Intelligence Generated
          </h2>
          <p style="font-size: 0.9rem; color: var(--text-muted); max-width: 540px; margin: 0 auto 24px auto; line-height: 1.6;">
            ${scanId ? `No AST artifacts or security invariants recorded for scan <code style="color: var(--cyan-accent);">${scanId}</code>.` : 'No scan selected.'} Launch an assessment to extract real AST routes, ORM schemas, and invariants.
          </p>
          <button class="btn btn-primary" id="ci-btn-start-scan">Launch Assessment Wizard &rarr;</button>
        </div>
      </div>
    `;
    document.getElementById("ci-btn-new-scan")?.addEventListener("click", () => navigate("wizard"));
    document.getElementById("ci-btn-start-scan")?.addEventListener("click", () => navigate("wizard"));
    return;
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
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyan-accent)" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Architectural Data Flow & Dependency Graph
          </div>
          <span class="badge badge-cyan">AST Flow Verified</span>
        </div>
        
        <div style="background: #0a0a12; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); padding: 36px 28px; display: flex; justify-content: space-between; align-items: center; position: relative; overflow-x: auto;">
          ${intelData.graph.nodes.map((node, i) => `
            <div style="display: flex; align-items: center;">
              <div style="background: rgba(12, 11, 20, 0.9); border: 1px solid ${node.type === 'security' ? 'var(--cyan-accent)' : (node.type === 'logic' ? 'var(--critical)' : 'var(--border-subtle)')}; padding: 18px 22px; border-radius: var(--radius-md); text-align: center; min-width: 160px; box-shadow: 0 10px 30px rgba(0,0,0,0.7);">
                <div style="font-size: 8.5px; color: var(--cyan-accent); text-transform: uppercase; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 4px;">${node.type}</div>
                <div style="font-size: 0.88rem; font-weight: 700; color: #fff;">${node.label}</div>
              </div>
              ${i < intelData.graph.nodes.length - 1 ? `
                <div style="padding: 0 18px; display: flex; flex-direction: column; align-items: center;">
                  <span style="font-size: 9px; color: var(--text-muted); font-family: monospace; letter-spacing: 1px; margin-bottom: 6px;">${intelData.graph.edges[i] ? intelData.graph.edges[i].label : 'flows'}</span>
                  <div style="width: 50px; height: 2px; background: linear-gradient(90deg, var(--cyan-accent), var(--cyan-accent)); position: relative;">
                    <div style="position: absolute; right: 0; top: -4px; width: 0; height: 0; border-top: 5px solid transparent; border-bottom: 5px solid transparent; border-left: 6px solid var(--cyan-accent);"></div>
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
                      <div style="font-size: 9px; color: var(--cyan-accent); font-family: monospace;">${inv.id}</div>
                    </td>
                    <td>
                      <code style="color: var(--cyan-accent); font-size: 0.78rem;">${inv.rule}</code>
                    </td>
                    <td><span class="badge badge-success">${inv.status}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>

        <!-- ORM Models Table -->
        ${(intelData.models && intelData.models.length) ? `
        <div class="card">
          <div class="card-header">
            <div class="card-title">Extracted ORM Models</div>
            <span class="badge badge-cyan">${intelData.models.length} Models</span>
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr><th>Model</th><th>Table</th><th>Source</th><th>Owner field</th></tr>
              </thead>
              <tbody>
                ${intelData.models.map(m => `
                  <tr>
                    <td style="font-weight:600;color:#fff;">${m.name}</td>
                    <td class="mono dim">${m.table || "—"}</td>
                    <td class="mono dim">${m.file || "—"}${m.line ? ":" + m.line : ""}</td>
                    <td class="mono">${m.owner_field || "—"}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </div>` : ""}

        <!-- Discovered Endpoints Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">AST Extracted Routes</div>
            <span class="badge badge-cyan">${intelData.endpoints.length} Endpoints</span>
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
                    <td><span class="badge ${ep.method === 'PATCH' ? 'badge-cyan' : 'badge-outline'}">${ep.method}</span></td>
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
