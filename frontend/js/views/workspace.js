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

  let scanInfo = null;
  try {
    scanInfo = await api.getScanStatus(scanId);
  } catch (e) {
    console.warn("Scan status unavailable:", e);
  }

  if (!scanInfo || !scanInfo.scan_id) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Agent workspace</div>
          <h1 class="page-title">Workspace</h1>
          <p class="page-subtitle">No assessment is selected, or <code>${scanId}</code> is no longer in the vault.</p>
        </div>
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">🧪</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">Nothing to stream</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:20px;">Start an assessment to watch the seven agents work.</p>
        <button class="btn btn-primary" id="ws-new-scan">Run an assessment</button>
      </div>`;
    container.querySelector("#ws-new-scan")?.addEventListener("click", () => navigate("wizard"));
    return;
  }

  // Pipeline order is a product constant; per-agent *status* must come from the
  // scan record. The old version hardcoded "completed" for every agent, which
  // made a failed scan look like a success.
  const PIPELINE = [
    { stage: "orchestrator", name: "OrchestratorAgent", role: "Mission & scope planning" },
    { stage: "code_intelligence", name: "CodeIntelligenceAgent", role: "AST invariants" },
    { stage: "recon", name: "ReconAgent", role: "Attack surface" },
    { stage: "vulnerability_research", name: "VulnResearchAgent", role: "Hypotheses" },
    { stage: "dynamic_testing", name: "DynamicTestingAgent", role: "Active probing" },
    { stage: "verification", name: "VerificationAgent", role: "3× replay" },
    { stage: "remediation", name: "RemediationAgent", role: "Patch synthesis" }
  ];
  const stageOrder = ["queued", ...PIPELINE.map(p => p.stage), "completed"];
  const currentIdx = stageOrder.indexOf(String(scanInfo.current_stage || "").toLowerCase());
  const scanDone = String(scanInfo.status || "").toLowerCase() === "completed";
  const scanFailed = String(scanInfo.status || "").toLowerCase() === "failed";

  const agents = PIPELINE.map((p, i) => {
    let status = "queued";
    if (scanDone) status = "completed";
    else if (scanFailed) status = currentIdx > i + 1 ? "completed" : "failed";
    else if (currentIdx > i + 1) status = "completed";
    else if (currentIdx === i + 1) status = "running";
    return { ...p, status };
  });

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
            Assessment ID: <code style="color: var(--cyan-accent); font-family: monospace;">${scanId}</code> | Target: <span style="color: #fff; font-weight: 600;">${scanInfo.project_name || scanInfo.project_id || "—"}</span>
          </p>
        </div>

        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary" id="ws-btn-findings">
            View Findings (${scanInfo.total_findings || 0})
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
            Active Agent: <br><strong style="color: var(--cyan-accent);" id="ws-active-agent-name">${scanInfo.active_agent || "—"}</strong>
          </div>
        </div>

        <!-- 7 Agents Flow Grid -->
        <div class="card">
          <div class="card-header" style="margin-bottom: 16px;">
            <div class="card-title" style="font-size: 1.05rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyan-accent)" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Autonomous Multi-Agent Topology
            </div>
            <span style="font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--cyan-accent);">PIPELINE TOPOLOGY, STATUS FROM VAULT</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px;" id="ws-agents-grid">
            ${agents.map((ag, idx) => `
              <div class="card" style="padding: 14px; background: rgba(10, 10, 10, 0.6); border: 1px solid ${ag.status === 'completed' ? 'rgba(32, 214, 160, 0.3)' : (ag.status === 'failed' ? 'rgba(255, 85, 120, 0.4)' : (ag.status === 'running' ? 'var(--border-gold)' : 'var(--border-subtle)'))}; border-radius: var(--radius-md);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-size: 9px; font-weight: 700; color: var(--cyan-accent);">#0${idx + 1}</span>
                  <span class="badge ${ag.status === 'completed' ? 'badge-success' : (ag.status === 'failed' ? 'badge-critical' : (ag.status === 'running' ? 'badge-cyan' : 'badge-outline'))}" style="padding: 2px 6px; font-size: 0.65rem;">
                    ${ag.status}
                  </span>
                </div>
                <div style="font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${ag.name}">
                  ${ag.name.replace('Agent', '')}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 8px;">${ag.role}</div>
                <div style="font-size: 0.66rem; color: var(--text-muted); font-family: var(--font-mono);">
                  ${ag.stage}
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
    drawRadialGauge(gaugeCanvas, Number(scanInfo.progress_percentage) || 0, 100, "Progress", "#24C8F5");
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
        const raw = String(data.message || "");
        // The socket replays already-formatted lines ("[ts] [LEVEL] [Agent] msg")
        // and also emits compact progress events; normalise both shapes.
        const parsed = raw.match(/^\[([^\]]+)\]\s*\[([A-Z]+)\]\s*\[([^\]]+)\]\s*([\s\S]*)$/);
        if (data.type === "log") {
          if (parsed) appendLog(parsed[1], parsed[2], parsed[3], parsed[4]);
          else appendLog(data.timestamp || "NOW", data.level || "INFO", data.agent_name || "Agent", raw);
        } else if (data.type === "pipeline_progress") {
          if (typeof data.percentage === "number" && gaugeCanvas) {
            drawRadialGauge(gaugeCanvas, data.percentage, 100, "Progress", "#24C8F5");
          }
          const actAg = document.getElementById("ws-active-agent-name");
          if (actAg && data.agent) actAg.innerText = data.agent;
          if (raw) appendLog(data.timestamp || "NOW", "INFO", data.agent || "Agent", raw);
        }
      } catch (e) {}
    };
  } catch (err) {}

  // Initial HTTP logs
  try {
    const logsRes = await api.getScanLogs(scanId);
    if (logsRes && logsRes.logs && logsRes.logs.length > 0) {
      logsRes.logs.forEach(line => {
        // Stored lines already look like "[12:00:00] [INFO] [Agent] message".
        // Re-prefixing them produced a doubled header in the console.
        const parsed = String(line).match(/^\[([^\]]+)\]\s*\[([A-Z]+)\]\s*\[([^\]]+)\]\s*([\s\S]*)$/);
        if (parsed) {
          appendLog(parsed[1], parsed[2], parsed[3], parsed[4]);
        } else {
          appendLog("--:--:--", "INFO", "Orchestrator", line);
        }
      });
    } else {
      appendLog("--:--:--", "INFO", "Orchestrator", `No log lines are stored for ${scanId}. Live output appears here while a scan runs.`);
    }
  } catch (e) {
    appendLog("--:--:--", "INFO", "Orchestrator", `Log endpoint unavailable: ${e.message}`);
  }
}
