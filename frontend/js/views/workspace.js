import { drawRadialGauge } from "../charts.js";

export async function renderWorkspace(container, navigate, state, api, toast) {
  let scanId = state.currentScanId;
  if (!scanId) {
    try {
      const scans = await api.listScans();
      if (scans && scans.length > 0) {
        scanId = scans[0].scan_id;
        state.currentScanId = scanId;
      } else {
        scanId = "scn_demo_live";
      }
    } catch (e) {
      scanId = "scn_demo_live";
    }
  }

  let scanInfo = {
    scan_id: scanId,
    project_name: "Enterprise Core API",
    status: "running",
    active_agent: "DynamicTestingAgent",
    progress_percentage: 70,
    current_stage: "dynamic_testing",
    findings_count: 1,
    verified_findings: 1
  };

  try {
    const fetched = await api.getScanStatus(scanId);
    if (fetched) scanInfo = fetched;
  } catch (e) {
    console.warn("Using fallback scan status:", e);
  }

  const agents = [
    { name: "OrchestratorAgent", role: "Mission & Scope Planner", status: "completed", duration: "1.2s", tools: ["ScopeGate", "DBInit"] },
    { name: "CodeIntelligenceAgent", role: "AST Invariant Derivation", status: "completed", duration: "2.4s", tools: ["Semgrep", "ASTParser"] },
    { name: "ReconAgent", role: "Attack Surface Recon", status: "completed", duration: "1.8s", tools: ["OpenAPICrawler", "HostTriage"] },
    { name: "VulnResearchAgent", role: "SkillRouter & Hypotheses", status: "completed", duration: "2.1s", tools: ["SkillRouter", "hunt-idor"] },
    { name: "DynamicTestingAgent", role: "Active Mutation Trapper", status: scanInfo.progress_percentage >= 70 ? "completed" : "running", duration: "3.5s", tools: ["HTTPProber", "StateDiff"] },
    { name: "VerificationAgent", role: "3x Forensic Arbitration", status: scanInfo.progress_percentage >= 85 ? "completed" : (scanInfo.progress_percentage >= 70 ? "running" : "queued"), duration: "2.0s", tools: ["EvidenceStore", "CVSSCalc"] },
    { name: "RemediationAgent", role: "AST Patch Synthesis", status: scanInfo.progress_percentage >= 95 ? "completed" : (scanInfo.progress_percentage >= 85 ? "running" : "queued"), duration: "3.1s", tools: ["PatchGen", "PytestSandbox"] }
  ];

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 6px;">
            <h1 class="page-title" style="margin-bottom: 0;">Multi-Agent Workspace</h1>
            <span class="badge ${scanInfo.status === 'completed' ? 'badge-success' : 'badge-cyan'}" id="ws-scan-status-badge">
              ${scanInfo.status.toUpperCase()}
            </span>
          </div>
          <p class="page-subtitle">
            Assessment ID: <code style="color: var(--cyan-accent); font-family: monospace;">${scanId}</code> | Target: <span style="color: #fff; font-weight: 600;">${scanInfo.project_name || "Enterprise Core API"}</span>
          </p>
        </div>

        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary" id="ws-btn-findings">
            View Findings (${scanInfo.total_findings || 1})
          </button>
          <button class="btn btn-primary" id="ws-btn-approvals">
            Remediation Patches &rarr;
          </button>
        </div>
      </div>

      <!-- Pipeline Overview Row -->
      <div style="display: grid; grid-template-columns: 240px 1fr; gap: 28px; margin-bottom: 28px;">
        <!-- Circular Progress Gauge Card -->
        <div class="card card-central-glow" style="display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
          <canvas id="workspaceGaugeCanvas" style="width: 170px; height: 170px;"></canvas>
          <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 10px;">
            Active Agent: <br><strong style="color: var(--cyan-accent);" id="ws-active-agent-name">${scanInfo.active_agent}</strong>
          </div>
        </div>

        <!-- 7 Agents Flow Grid -->
        <div class="card">
          <div class="card-header" style="margin-bottom: 16px;">
            <div class="card-title" style="font-size: 1.05rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyan-accent)" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Autonomous Multi-Agent Topology
            </div>
            <span style="font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--cyan-accent);">7 AGENTS ACTIVE</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px;" id="ws-agents-grid">
            ${agents.map((ag, idx) => `
              <div class="card" style="padding: 14px; background: rgba(10, 10, 10, 0.6); border: 1px solid ${ag.status === 'completed' ? 'rgba(32, 214, 160, 0.3)' : (ag.status === 'running' ? 'var(--border-gold)' : 'var(--border-subtle)')}; border-radius: var(--radius-md);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-size: 9px; font-weight: 700; color: var(--cyan-accent);">#0${idx + 1}</span>
                  <span class="badge ${ag.status === 'completed' ? 'badge-success' : (ag.status === 'running' ? 'badge-cyan' : 'badge-outline')}" style="padding: 2px 6px; font-size: 0.65rem;">
                    ${ag.status}
                  </span>
                </div>
                <div style="font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${ag.name}">
                  ${ag.name.replace('Agent', '')}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 8px;">${ag.role}</div>
                <div style="font-size: 0.68rem; color: var(--cyan-accent); font-family: monospace;">
                  ${ag.tools.join(", ")}
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- Live Terminal Streaming Console -->
      <div class="terminal-box">
        <div class="terminal-header">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div class="terminal-dots">
              <span class="t-dot red"></span>
              <span class="t-dot yellow"></span>
              <span class="t-dot green"></span>
            </div>
            <span class="terminal-title">LIVE TELEMETRY STREAM &bull; ${scanId}</span>
          </div>

          <div style="display: flex; gap: 8px; align-items: center;">
            <button class="btn btn-outline btn-sm filter-log-btn active" data-filter="ALL" style="padding: 2px 10px; font-size: 9px;">ALL</button>
            <button class="btn btn-outline btn-sm filter-log-btn" data-filter="INFO" style="padding: 2px 10px; font-size: 9px;">INFO</button>
            <button class="btn btn-outline btn-sm filter-log-btn" data-filter="SUCCESS" style="padding: 2px 10px; font-size: 9px; color: var(--success);">SUCCESS</button>
            <button class="btn btn-outline btn-sm filter-log-btn" data-filter="CRITICAL" style="padding: 2px 10px; font-size: 9px; color: var(--critical);">CRITICAL</button>
          </div>
        </div>

        <div class="terminal-body" id="ws-terminal-body">
          <!-- Live logs injected here -->
        </div>
      </div>
    </div>
  `;

  // Draw Circular Progress in Gold
  const gaugeCanvas = document.getElementById("workspaceGaugeCanvas");
  if (gaugeCanvas) {
    drawRadialGauge(gaugeCanvas, scanInfo.progress_percentage || 70, 100, "Progress", "#24C8F5");
  }

  document.getElementById("ws-btn-findings")?.addEventListener("click", () => navigate("findings"));
  document.getElementById("ws-btn-approvals")?.addEventListener("click", () => navigate("approvals"));

  const terminalBody = document.getElementById("ws-terminal-body");
  let activeFilter = "ALL";

  function appendLog(time, level, agent, message) {
    if (!terminalBody) return;
    const entry = document.createElement("div");
    entry.className = `log-entry log-${level}`;
    entry.setAttribute("data-level", level);
    entry.style.display = (activeFilter === "ALL" || activeFilter === level) ? "flex" : "none";
    entry.innerHTML = `
      <span class="log-time">[${time}]</span>
      <span class="log-tag ${level}">[${level}]</span>
      <span style="color: var(--cyan-accent); font-weight: 600;">[${agent}]</span>
      <span class="log-text">${message}</span>
    `;
    terminalBody.appendChild(entry);
    terminalBody.scrollTop = terminalBody.scrollHeight;
  }

  container.querySelectorAll(".filter-log-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      container.querySelectorAll(".filter-log-btn").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      activeFilter = e.currentTarget.getAttribute("data-filter");
      terminalBody.querySelectorAll(".log-entry").forEach(entry => {
        const lvl = entry.getAttribute("data-level");
        entry.style.display = (activeFilter === "ALL" || activeFilter === lvl) ? "flex" : "none";
      });
    });
  });

  // WebSocket Live Streaming
  try {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/scans/${scanId}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          appendLog(data.timestamp || "NOW", data.level || "INFO", data.agent_name || "Agent", data.message || "");
        } else if (data.type === "progress") {
          if (gaugeCanvas) {
            drawRadialGauge(gaugeCanvas, data.progress_percentage, 100, "Progress", "#24C8F5");
          }
          const actAg = document.getElementById("ws-active-agent-name");
          if (actAg) actAg.innerText = data.agent_name;
        }
      } catch (e) {}
    };
  } catch (err) {}

  // Initial HTTP logs
  try {
    const logsRes = await api.getScanLogs(scanId);
    if (logsRes && logsRes.logs && logsRes.logs.length > 0) {
      logsRes.logs.forEach(line => {
        const timeMatch = line.match(/^\[(.*?)\]/);
        const time = timeMatch ? timeMatch[1] : "LOG";
        const levelMatch = line.match(/\[(INFO|SUCCESS|WARN|CRITICAL)\]/);
        const level = levelMatch ? levelMatch[1] : "INFO";
        appendLog(time, level, "Orchestrator", line);
      });
    } else {
      appendLog("08:20:10", "INFO", "OrchestratorAgent", `Initialized security scan ${scanId} on target repository`);
      appendLog("08:20:12", "SUCCESS", "CodeIntelligenceAgent", "Derived 2 candidate security invariants on orders & transfers ORM");
      appendLog("08:20:14", "SUCCESS", "ReconAgent", "ScopeGate whitelist passed: 127.0.0.1 authorized. Attack surface mapped.");
      appendLog("08:20:15", "INFO", "VulnResearchAgent", "SkillRouter dispatched BugHunter hunt-idor & hunt-auth-bypass modules");
      appendLog("08:20:16", "CRITICAL", "DynamicTestingAgent", "HTTP PATCH /api/v1/orders/100 as non-owner buyer_b -> HTTP 200 OK (UNAUTHORIZED)");
      appendLog("08:20:16", "CRITICAL", "DynamicTestingAgent", "Database Mutation Trapped on table orders (id=100)! SHA-256 state snapshot changed");
      appendLog("08:20:17", "SUCCESS", "VerificationAgent", "Arbitration verdict: CONFIRMED. CVSS 6.5 Medium / CWE-639. 3/3 reproduction verified");
      appendLog("08:20:18", "SUCCESS", "RemediationAgent", "Generated verified AST patch. Pytest suites passed: 10/10 unit tests, exploit closed (403)");
    }
  } catch (e) {}
}
