import { drawRadialGauge } from "../charts.js";

/**
 * Advance the agent topology to the given stage.
 * Agents before `incoming` are finished, the one at `incoming` is running.
 */
function applyTopologyStep(root, order, incoming) {
  root.querySelectorAll(".ws-agent-card").forEach(card => {
    const stage = card.getAttribute("data-stage");
    const idx = order.indexOf(stage);
    let status = "queued";
    if (incoming >= 0) {
      if (idx < incoming) status = "completed";
      else if (idx === incoming) status = "running";
    }
    if (status === "queued") return;
    const meta = agentStatusMeta(status);
    const badge = card.querySelector(".ws-agent-status");
    if (badge) { badge.className = `badge ${meta.badge} ws-agent-status`; badge.textContent = meta.label; }
    const dot = card.querySelector(".ws-agent-dot");
    if (dot) dot.style.background = meta.dot;
    card.className = `card ws-agent-card ws-agent-${meta.tone}`;
    card.style.border = `1px solid ${meta.border}`;
  });
}

function formatAgentDetail(rec) {
  // The card already shows the stage, so the detail line only adds timing.
  const parts = [];
  if (typeof rec.duration_ms === "number" && rec.duration_ms >= 0) {
    parts.push(rec.duration_ms < 1000 ? `${rec.duration_ms}ms` : `${(rec.duration_ms / 1000).toFixed(1)}s`);
  } else if (rec.finished_at) {
    parts.push(`finished ${String(rec.finished_at).slice(11, 19)}`);
  } else if (rec.started_at) {
    parts.push(`started ${String(rec.started_at).slice(11, 19)}`);
  }
  return parts.join(" · ");
}

function agentStatusMeta(status) {
  if (status === "completed") return { badge: "badge-success", border: "rgba(32, 214, 160, 0.35)", label: "done", dot: "var(--success)", tone: "done" };
  if (status === "running") return { badge: "badge-cyan", border: "var(--border-gold)", label: "running", dot: "var(--cyan-accent)", tone: "running" };
  if (status === "failed") return { badge: "badge-critical", border: "rgba(255, 85, 120, 0.45)", label: "failed", dot: "var(--critical)", tone: "failed" };
  if (status === "blocked") return { badge: "badge-medium", border: "var(--border-gold)", label: "blocked", dot: "var(--warning)", tone: "blocked" };
  return { badge: "badge-outline", border: "var(--border-subtle)", label: "queued", dot: "var(--text-muted)", tone: "idle" };
}

function agentCard(ag, idx) {
  const meta = agentStatusMeta(ag.status);
  return `
    <div class="card ws-agent-card ws-agent-${meta.tone}" data-stage="${ag.stage}" style="padding: 14px; background: rgba(10, 10, 10, 0.6); border: 1px solid ${meta.border}; border-radius: var(--radius-md);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-size: 9px; font-weight: 700; color: var(--cyan-accent); display: flex; align-items: center; gap: 5px;">
          <span class="ws-agent-dot" style="width: 6px; height: 6px; border-radius: 50%; background: ${meta.dot};"></span>
          #0${idx + 1}
        </span>
        <span class="badge ${meta.badge} ws-agent-status" style="padding: 2px 6px; font-size: 0.65rem;">${meta.label}</span>
      </div>
      <div style="font-size: 0.8rem; font-weight: 700; color: #fff; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${ag.name}">
        ${ag.name.replace("Agent", "")}
      </div>
      <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 8px;">${ag.role}</div>
      <div class="ws-agent-stage" style="font-size: 0.66rem; color: var(--text-muted); font-family: var(--font-mono); display: flex; justify-content: space-between; gap: 6px;">
        <span>${ag.stage}</span>
        <span class="ws-agent-time">${ag.detail || ""}</span>
      </div>
      ${ag.message ? `<div class="ws-agent-msg">${ag.message}</div>` : ""}
    </div>`;
}

/** Update the topology cards in place, without re-rendering the view. */
function applyAgentStates(root, states, scanStatus) {
  const aliases = { code_intel: "code_intelligence", vuln_research: "vulnerability_research" };
  const norm = {};
  Object.entries(states || {}).forEach(([k, v]) => { norm[aliases[k] || k] = v; });
  root.querySelectorAll(".ws-agent-card").forEach(card => {
    const stage = card.getAttribute("data-stage");
    const rec = norm[stage];
    if (!rec) return;
    const status = String(rec.status || "").toLowerCase();
    const meta = agentStatusMeta(status === "succeeded" ? "completed" : status);
    const badge = card.querySelector(".ws-agent-status");
    if (badge) {
      badge.className = `badge ${meta.badge} ws-agent-status`;
      badge.style.padding = "2px 6px";
      badge.style.fontSize = "0.65rem";
      badge.textContent = meta.label;
    }
    const dot = card.querySelector(".ws-agent-dot");
    if (dot) dot.style.background = meta.dot;
    card.className = `card ws-agent-card ws-agent-${meta.tone}`;
    card.style.border = `1px solid ${meta.border}`;
  });
  const src = root.querySelector("#ws-topology-source");
  if (src) src.textContent = "Status read from the evidence vault (agent_tasks).";
}

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

  // Pipeline order is a product constant. The per-agent *status* comes from
  // agent_states, which the pipeline writes to the vault as each stage runs.
  // Inferring it from the progress percentage (the previous approach) left
  // every agent stuck on "queued" because the stage ids never matched.
  const PIPELINE = [
    { stage: "orchestrator", name: "OrchestratorAgent", role: "Mission & scope planning" },
    { stage: "code_intelligence", name: "CodeIntelligenceAgent", role: "AST invariants" },
    { stage: "recon", name: "ReconAgent", role: "Attack surface" },
    { stage: "vulnerability_research", name: "VulnResearchAgent", role: "Hypotheses" },
    { stage: "dynamic_testing", name: "DynamicTestingAgent", role: "Active probing" },
    { stage: "verification", name: "VerificationAgent", role: "3× replay" },
    { stage: "remediation", name: "RemediationAgent", role: "Patch synthesis" }
  ];

  // Older vaults may still use the legacy stage vocabulary.
  const STAGE_ALIASES = {
    code_intel: "code_intelligence",
    vuln_research: "vulnerability_research",
    vulnerability_research: "vulnerability_research"
  };
  const normaliseStage = s => {
    const key = String(s || "").toLowerCase();
    return STAGE_ALIASES[key] || key;
  };

  const scanDone = String(scanInfo.status || "").toLowerCase() === "completed";
  const scanFailed = String(scanInfo.status || "").toLowerCase() === "failed";
  const rawStates = scanInfo.agent_states || {};
  const states = {};
  Object.entries(rawStates).forEach(([stage, st]) => { states[normaliseStage(stage)] = st; });

  const currentStage = normaliseStage(scanInfo.current_stage);
  const currentIdx = PIPELINE.findIndex(p => p.stage === currentStage);

  const agents = PIPELINE.map((p, i) => {
    const rec = states[p.stage] || {};
    let status = rec ? String(rec.status || "").toLowerCase() : "";
    if (!status || status === "queued") {
      // No row yet: derive from the scan's own state, but only as a fallback.
      if (scanDone) status = "succeeded";
      else if (scanFailed) status = currentIdx > i ? "succeeded" : (currentIdx === i ? "failed" : "queued");
      else if (currentIdx > i) status = "succeeded";
      else if (currentIdx === i) status = "running";
      else status = "queued";
    } else if (scanDone && status === "running") {
      status = "succeeded";
    }
    return {
      ...p,
      status: status === "succeeded" ? "completed" : status,
      detail: formatAgentDetail(rec),
      message: rec.message || ""
    };
  });
  const vaultHasStates = Object.keys(states).length > 0;

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
            ${agents.map((ag, idx) => agentCard(ag, idx)).join("")}
          </div>
          <div style="margin-top: 14px; font-size: 0.72rem; color: var(--text-muted); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span id="ws-topology-source">${vaultHasStates ? "Status read from the evidence vault (agent_tasks)." : "Status derived from the scan's current stage."}</span>
            <span id="ws-stage-note" style="color: var(--cyan-accent);"></span>
            <button class="btn btn-outline btn-sm" id="ws-btn-refresh-state" style="padding: 2px 9px; font-size: 0.68rem;">Refresh</button>
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
  document.getElementById("ws-btn-refresh-state")?.addEventListener("click", async () => {
    try {
      const fresh = await api.getScanStatus(scanId);
      if (fresh) {
        applyAgentStates(container, fresh.agent_states, fresh.status);
        if (typeof toast === "function") toast("Topology refreshed from the evidence vault", "success");
      }
    } catch (e) {
      if (typeof toast === "function") toast(`Could not refresh: ${e.message}`, "error");
    }
  });
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

  // Reflect the pre-agent stage (repository retrieval) so the topology is not
  // a wall of "queued" while the clone is still running.
  const stageNote = container.querySelector("#ws-stage-note");
  const STAGE_NOTES = {
    queued: "queued — waiting for a worker",
    initialization: "preparing the target: cloning and indexing the repository",
    in_progress: "assessment in progress"
  };
  const setStageNote = stage => {
    if (!stageNote) return;
    const key = String(stage || "").toLowerCase();
    stageNote.textContent = STAGE_NOTES[key] || (key && !["orchestrator","code_intelligence","recon","vulnerability_research","dynamic_testing","verification","remediation","completed"].includes(key) ? key : "");
  };
  setStageNote(scanInfo.current_stage);

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
        if (data.type === "log" || data.type === "agent_log") {
          // The pipeline emits "agent_log" and the WebSocket endpoint replays
          // stored lines as "log"; both must reach the console.
          if (parsed) appendLog(parsed[1], parsed[2], parsed[3], parsed[4]);
          else appendLog(data.timestamp || "NOW", data.level || "INFO", data.agent || data.agent_name || "Agent", raw);
          // An agent_log names the stage that is speaking, so the topology can
          // advance even if the progress event was missed.
          if (data.stage && data.stage !== "initialization") {
            const order = PIPELINE.map(p => p.stage);
            const incoming = order.indexOf(data.stage);
            if (incoming >= 0) applyTopologyStep(container, order, incoming);
          }
        } else if (data.type === "pipeline_progress") {
          if (typeof data.percentage === "number" && gaugeCanvas) {
            drawRadialGauge(gaugeCanvas, data.percentage, 100, "Progress", "#24C8F5");
          }
          const actAg = document.getElementById("ws-active-agent-name");
          if (actAg && data.agent) actAg.innerText = data.agent;
          if (data.stage) {
            // Live topology update. When an agent reports progress, every agent
            // before it in the pipeline has necessarily finished, so the
            // topology advances one card at a time instead of jumping from
            // "all queued" straight to "all done".
            const order = PIPELINE.map(p => p.stage);
            const incoming = order.indexOf(data.stage);
            if (incoming >= 0) applyTopologyStep(container, order, incoming);
          }
          if (raw) appendLog(data.timestamp || "NOW", "INFO", data.agent || "Agent", raw);
        }
      } catch (e) {}
    };
  } catch (err) {}

  // Poll the vault while the scan is unfinished: the WebSocket only reports
  // the agent that is *currently* running, but the console must also show the
  // agents that already finished after a reconnect or a page reload.
  const refreshTimer = setInterval(async () => {
    const statusBadge = document.getElementById("ws-scan-status-badge");
    if (statusBadge && /completed|failed/i.test(statusBadge.textContent || "")) {
      clearInterval(refreshTimer);
      return;
    }
    try {
      const fresh = await api.getScanStatus(scanId);
      if (!fresh) return;
      applyAgentStates(container, fresh.agent_states, fresh.status);
      if (fresh.agent_states && Object.keys(fresh.agent_states).length) {
        const src = document.getElementById("ws-topology-source");
        if (src) src.textContent = "Status read from the evidence vault (agent_tasks).";
      }
      if (typeof fresh.progress_percentage === "number" && gaugeCanvas) {
        drawRadialGauge(gaugeCanvas, fresh.progress_percentage, 100, "Progress", "#24C8F5");
      }
      const badge = document.getElementById("ws-scan-status-badge");
      if (badge && fresh.status) badge.textContent = String(fresh.status).toUpperCase();
      if (typeof setStageNote === "function") setStageNote(fresh.current_stage);
    } catch { /* keep the last known state */ }
  }, 700);

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
