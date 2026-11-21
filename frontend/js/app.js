import { renderAuth } from "./views/auth.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderProjects } from "./views/projects.js";
import { renderWizard } from "./views/wizard.js";
import { renderWorkspace } from "./views/workspace.js";
import { renderCodeIntel } from "./views/code_intel.js";
import { renderAttackSurface } from "./views/surface.js";
import { renderFindings } from "./views/findings.js";
import { renderFindingDetails } from "./views/finding_details.js";
import { renderVerification } from "./views/verification.js";
import { renderRemediation } from "./views/remediation.js";
import { renderApprovals } from "./views/approvals.js";
import { renderReports } from "./views/reports.js";
import { renderSkills } from "./views/skills.js";
import { renderBenchmarks } from "./views/benchmarks.js";
import { renderSettings } from "./views/settings.js";
import { renderSupporting } from "./views/supporting.js";

// Global API Client
export const api = {
  async req(url, options = {}) {
    const isHeavy = url.includes('/analyze') || url.includes('/assessments') || url.includes('/scans');
    const defaultTimeout = isHeavy ? 60000 : 15000;
    const timeout = options.timeout || defaultTimeout;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        signal: controller.signal,
        ...options
      });
      clearTimeout(timer);
      if (!res.ok) {
        let errDetail = res.statusText;
        try {
          const j = await res.json();
          if (j.detail) errDetail = j.detail;
        } catch (e) {}
        throw new Error(errDetail);
      }
      return res.json();
    } catch (err) {
      clearTimeout(timer);
      if (err.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeout / 1000}s`);
      }
      throw err;
    }
  },

  getHealth() { return this.req("/api/v1/health"); },
  getOverviewStats() { return this.req("/api/v1/stats/overview"); },
  listProjects() { return this.req("/api/v1/projects"); },
  createProject(data) { return this.req("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }); },
  listScans() { return this.req("/api/v1/scans"); },
  getScanStatus(id) { return this.req(`/api/v1/scans/${id}`); },
  getScanLogs(id) { return this.req(`/api/v1/scans/${id}/logs`); },
  startScan(data) { return this.req("/api/v1/scans", { method: "POST", body: JSON.stringify(data), timeout: 60000 }); },
  listFindings(scanId) { return this.req(`/api/v1/findings${scanId ? `?scan_id=${scanId}` : ''}`); },
  getFindingDetail(id) { return this.req(`/api/v1/findings/${id}`); },
  getCodeIntel(scanId) { return this.req(`/api/v1/code-intel/${scanId}`); },
  listApprovals() { return this.req("/api/v1/approvals"); },
  actOnApproval(patchId, action, reviewer, notes) {
    return this.req(`/api/v1/approvals/${patchId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, reviewer, notes })
    });
  },
  listSkills() { return this.req("/api/v1/skills"); },
  getBenchmarks() { return this.req("/api/v1/benchmarks"); },
  getReport(scanId) { return this.req(`/api/v1/reports/${scanId}`); },
  getSettings() { return this.req("/api/v1/settings"); },
  getAuditLogs() { return this.req("/api/v1/audit-logs"); },
  analyzeRepository(url, token) { return this.req("/api/v1/repositories/analyze", { method: "POST", body: JSON.stringify({ repository_url: url, auth_token: token }), timeout: 60000 }); },
  createAssessment(data) { return this.req("/api/v1/assessments", { method: "POST", body: JSON.stringify(data), timeout: 60000 }); },
  getAssessment(id) { return this.req(`/api/v1/assessments/${id}`); },
  getAssessmentEvents(id) { return this.req(`/api/v1/assessments/${id}/events`); },
  getAssessmentFindings(id) { return this.req(`/api/v1/assessments/${id}/findings`); },
  getCategories() { return this.req("/api/v1/categories"); },
  getTavilyHealth() { return this.req("/api/v1/integrations/tavily/health"); },
  testTavily(query) { return this.req("/api/v1/integrations/tavily/test", { method: "POST", body: JSON.stringify({ query }) }); },
  getBifrostHealth() { return this.req("/api/v1/integrations/bifrost/health"); },
  getNotifications() { return this.req("/api/v1/notifications"); }
};

// Global Client State
export const state = {
  currentRoute: "dashboard",
  currentProjectId: "prj_default",
  currentProjectName: "Enterprise Core API",
  currentScanId: null,
  selectedFindingId: "fnd_prod_001",
  targetRepoUrl: null
};

// Toast Notifications
export function toast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  const glyph = type === "success" ? "✓" : type === "critical" ? "✕" : type === "warn" ? "!" : "i";
  const color = type === "success" ? "var(--success)" : type === "critical" ? "var(--critical)" : type === "warn" ? "var(--warning)" : "var(--cyan-accent)";
  t.innerHTML = `
    <div style="font-weight:800;color:${color};font-family:var(--font-mono);font-size:0.9rem;">${glyph}</div>
    <div style="font-size:0.84rem;color:var(--text-primary);">${message}</div>
  `;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transform = "translateX(24px)";
    t.style.transition = "all 0.3s ease";
    setTimeout(() => t.remove(), 320);
  }, 4200);
}

// Modal Dialog Manager
export function showModal({ title, bodyHtml, confirmText = "Confirm", onConfirm = null }) {
  const modal = document.getElementById("global-modal");
  const mTitle = document.getElementById("modal-title");
  const mBody = document.getElementById("modal-body");
  const mFooter = document.getElementById("modal-footer");
  if (!modal || !mTitle || !mBody || !mFooter) return;

  mTitle.innerText = title;
  mBody.innerHTML = bodyHtml;
  
  mFooter.innerHTML = `
    <button class="btn btn-secondary" id="modal-cancel-btn">Cancel</button>
    <button class="btn btn-primary" id="modal-confirm-btn">${confirmText}</button>
  `;

  modal.classList.add("open");

  const close = () => modal.classList.remove("open");
  document.getElementById("modal-close-btn").onclick = close;
  document.getElementById("modal-cancel-btn").onclick = close;

  document.getElementById("modal-confirm-btn").onclick = async () => {
    if (onConfirm) {
      const res = await onConfirm();
      if (res !== false) close();
    } else {
      close();
    }
  };
}

// Client Router (All 18 Dedicated Pages)
export async function navigate(route) {
  state.currentRoute = route;
  window.location.hash = `#${route}`;

  // Mode body classes for fullscreen views
  if (route === "auth") {
    document.body.classList.add("auth-mode");
  } else {
    document.body.classList.remove("auth-mode");
  }

  // Update Sidebar active state
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-route") === route) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update Breadcrumb
  const breadcrumb = document.getElementById("breadcrumb-current");
  if (breadcrumb) {
    const titles = {
      auth: "Authentication",
      dashboard: "Executive Overview",
      projects: "Projects Management",
      wizard: "New Security Assessment",
      workspace: "Agent Workspace & Pipeline",
      code_intel: "Code Intelligence & Invariants",
      surface: "Attack Surface Reconnaissance",
      findings: "Vulnerability Findings",
      finding_details: "Forensic Evidence Dossier",
      verification: "Verification & Arbitration",
      remediation: "Remediation & AST Patches",
      approvals: "Human Approval Center",
      reports: "Reports & Compliance",
      skills: "BugHunter Skills Library",
      benchmarks: "Empirical Benchmarks Matrix",
      settings: "Platform Settings & Vaults",
      supporting: "Supporting Operations Suite"
    };
    breadcrumb.innerText = titles[route] || route.toUpperCase();
  }

  // Render Target View
  const viewRoot = document.getElementById("view-root");
  if (!viewRoot) return;

  try {
    let p;
    switch (route) {
      case "auth": p = renderAuth(viewRoot, navigate, state, api, toast); break;
      case "dashboard": p = renderDashboard(viewRoot, navigate, state, api); break;
      case "projects": p = renderProjects(viewRoot, navigate, state, api, showModal, toast); break;
      case "wizard": p = renderWizard(viewRoot, navigate, state, api, toast); break;
      case "workspace": p = renderWorkspace(viewRoot, navigate, state, api, toast); break;
      case "code_intel": p = renderCodeIntel(viewRoot, navigate, state, api); break;
      case "surface": p = renderAttackSurface(viewRoot, navigate, state, api, showModal); break;
      case "findings": p = renderFindings(viewRoot, navigate, state, api, showModal); break;
      case "finding_details": p = renderFindingDetails(viewRoot, navigate, state, api, toast); break;
      case "verification": p = renderVerification(viewRoot, navigate, state, api); break;
      case "remediation": p = renderRemediation(viewRoot, navigate, state, api); break;
      case "approvals": p = renderApprovals(viewRoot, navigate, state, api, showModal, toast); break;
      case "reports": p = renderReports(viewRoot, navigate, state, api, toast); break;
      case "skills": p = renderSkills(viewRoot, navigate, state, api, showModal); break;
      case "benchmarks": p = renderBenchmarks(viewRoot, navigate, state, api); break;
      case "settings": p = renderSettings(viewRoot, navigate, state, api, toast); break;
      case "supporting": p = renderSupporting(viewRoot, navigate, state, api, toast); break;
      default: p = renderDashboard(viewRoot, navigate, state, api); break;
    }
    if (p && typeof p.catch === "function") {
      await p.catch(err => {
        console.error("View render error:", err);
      });
    }
  } catch (err) {
    console.error("Navigation error:", err);
  }
}

// ==========================================================================
// Route metadata (single source of truth for nav, palette, and breadcrumbs)
// ==========================================================================
export const ROUTES = [
  { id: "dashboard", title: "Overview", group: "Workspace", desc: "Executive telemetry and posture" },
  { id: "projects", title: "Projects", group: "Workspace", desc: "Targets and repositories" },
  { id: "wizard", title: "Assessments", group: "Workspace", desc: "Launch a new security assessment" },
  { id: "workspace", title: "Agent Workspace", group: "Workspace", desc: "Live pipeline and agent logs" },
  { id: "code_intel", title: "Code Intelligence", group: "Security Intelligence", desc: "AST routes and invariants" },
  { id: "surface", title: "Attack Surface", group: "Security Intelligence", desc: "Endpoints and parameters" },
  { id: "findings", title: "Findings", group: "Security Intelligence", desc: "Vulnerability inventory" },
  { id: "finding_details", title: "Evidence Dossier", group: "Security Intelligence", desc: "Forensic detail for a finding" },
  { id: "verification", title: "Verification Center", group: "Security Intelligence", desc: "Arbitration and reproduction" },
  { id: "remediation", title: "Remediation", group: "Remediation", desc: "Patches and diffs" },
  { id: "approvals", title: "Human Approvals", group: "Remediation", desc: "Authorization gate for patches" },
  { id: "reports", title: "Reports", group: "Remediation", desc: "Exports and compliance" },
  { id: "skills", title: "Skills Library", group: "Platform", desc: "BugHunter knowledge base" },
  { id: "benchmarks", title: "Benchmarks", group: "Platform", desc: "Accuracy and recall matrix" },
  { id: "settings", title: "Settings", group: "Platform", desc: "Vaults and integrations" },
  { id: "supporting", title: "Supporting Screens", group: "Platform", desc: "Notifications, audit, system" },
  { id: "auth", title: "Authentication", group: "Platform", desc: "Sign in surface" }
];

const ROUTE_TITLES = Object.fromEntries(ROUTES.map(r => [r.id, r.title]));

// ==========================================================================
// Mobile drawer
// ==========================================================================
function isMobileShell() {
  return window.matchMedia("(max-width: 1024px)").matches;
}

export function openDrawer() {
  if (!isMobileShell()) return;
  document.body.classList.add("drawer-open");
}

export function closeDrawer() {
  document.body.classList.remove("drawer-open");
}

function toggleDrawer() {
  document.body.classList.toggle("drawer-open");
}

// ==========================================================================
// Command palette
// ==========================================================================
let cmdkState = { items: [], index: 0 };

export function closeCommandPalette() {
  document.getElementById("cmdk-overlay")?.classList.remove("open");
}

function buildPaletteItems(query) {
  const q = query.trim().toLowerCase();
  const routeItems = ROUTES.map(r => ({
    kind: "Navigate",
    label: r.title,
    meta: r.group,
    hint: r.desc,
    run: () => navigate(r.id)
  }));
  const actionItems = [
    { kind: "Action", label: "New assessment", meta: "⌘N", hint: "Start the 7-agent pipeline", run: () => navigate("wizard") },
    { kind: "Action", label: "Live pipeline", meta: "Workspace", hint: "Watch agents execute", run: () => navigate("workspace") },
    { kind: "Action", label: "Audit trail", meta: "Immutable", hint: "Evidence and operator actions", run: () => navigate("supporting") }
  ];
  const all = [...actionItems, ...routeItems];
  if (!q) return all;
  return all.filter(i =>
    i.label.toLowerCase().includes(q) ||
    i.kind.toLowerCase().includes(q) ||
    (i.hint || "").toLowerCase().includes(q)
  );
}

function renderPalette(query) {
  const results = document.getElementById("cmdk-results");
  if (!results) return;
  cmdkState.items = buildPaletteItems(query);
  cmdkState.index = 0;
  const hint = document.getElementById("cmdk-hint");
  if (hint) hint.textContent = `${cmdkState.items.length} result${cmdkState.items.length === 1 ? "" : "s"}`;

  if (!cmdkState.items.length) {
    results.innerHTML = `<div class="cmdk-empty">No matches for “${query}”.</div>`;
    return;
  }

  let html = "";
  let lastKind = null;
  cmdkState.items.forEach((item, i) => {
    if (item.kind !== lastKind) {
      html += `<div class="cmdk-group-label">${item.kind}</div>`;
      lastKind = item.kind;
    }
    html += `
      <div class="cmdk-item ${i === 0 ? "active" : ""}" data-index="${i}">
        <span>${item.label}</span>
        <span class="cmdk-item-meta">${item.meta || ""}</span>
      </div>`;
  });
  results.innerHTML = html;

  results.querySelectorAll(".cmdk-item").forEach(el => {
    el.addEventListener("mouseenter", () => {
      results.querySelectorAll(".cmdk-item").forEach(x => x.classList.remove("active"));
      el.classList.add("active");
      cmdkState.index = Number(el.getAttribute("data-index"));
    });
    el.addEventListener("click", () => runPaletteItem(cmdkState.index));
  });
}

function runPaletteItem(index) {
  const item = cmdkState.items[index];
  if (!item) return;
  closeCommandPalette();
  item.run();
}

export function openCommandPalette() {
  const overlay = document.getElementById("cmdk-overlay");
  const input = document.getElementById("cmdk-input");
  if (!overlay || !input) return;
  overlay.classList.add("open");
  input.value = "";
  renderPalette("");
  setTimeout(() => input.focus(), 30);
}

function initCommandPalette() {
  const overlay = document.getElementById("cmdk-overlay");
  const input = document.getElementById("cmdk-input");
  if (!overlay || !input) return;

  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeCommandPalette();
  });

  input.addEventListener("input", e => renderPalette(e.target.value));

  input.addEventListener("keydown", e => {
    const items = document.querySelectorAll(".cmdk-item");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!items.length) return;
      cmdkState.index = e.key === "ArrowDown"
        ? (cmdkState.index + 1) % items.length
        : (cmdkState.index - 1 + items.length) % items.length;
      items.forEach(x => x.classList.remove("active"));
      items[cmdkState.index]?.classList.add("active");
      items[cmdkState.index]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      runPaletteItem(cmdkState.index);
    }
  });

  document.addEventListener("keydown", e => {
    const isMac = navigator.platform.toUpperCase().includes("MAC");
    const mod = isMac ? e.metaKey : e.ctrlKey;
    if (mod && e.key.toLowerCase() === "k") {
      e.preventDefault();
      overlay.classList.contains("open") ? closeCommandPalette() : openCommandPalette();
    } else if (e.key === "Escape" && overlay.classList.contains("open")) {
      closeCommandPalette();
    } else if (e.key === "Escape") {
      closeDrawer();
    }
  });
}

// ==========================================================================
// App Initialization
// ==========================================================================
window.addEventListener("DOMContentLoaded", () => {
  // Sidebar nav
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      // Items without a route (the link to the public site) keep their
      // normal browser behaviour - the SPA must not swallow them.
      const route = e.currentTarget.getAttribute("data-route");
      if (!route) {
        closeDrawer();
        return;
      }
      e.preventDefault();
      navigate(route);
      closeDrawer();
    });
  });

  document.getElementById("brand-link")?.addEventListener("click", () => {
    navigate("dashboard");
    closeDrawer();
  });
  document.getElementById("brand-link")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") navigate("dashboard");
  });

  // Drawer controls
  document.getElementById("btn-hamburger")?.addEventListener("click", toggleDrawer);
  document.getElementById("sidebar-close")?.addEventListener("click", closeDrawer);
  document.getElementById("drawer-scrim")?.addEventListener("click", closeDrawer);

  // Command palette
  document.getElementById("btn-command")?.addEventListener("click", openCommandPalette);
  initCommandPalette();

  // Landing toggle

  document.getElementById("btn-new-assessment")?.addEventListener("click", () => navigate("wizard"));

  // Browser back/forward + manual hash edits
  window.addEventListener("hashchange", () => {
    const route = window.location.hash.replace("#", "");
    if (route && route !== state.currentRoute) navigate(route);
  });

  // The public marketing site owns the site root, so the console always opens
  // on the operator dashboard. Deep links keep working; the retired
  // "#landing" route falls back to the dashboard instead of a blank view.
  const hashRoute = window.location.hash.replace("#", "");
  const initialRoute = hashRoute && hashRoute !== "landing" ? hashRoute : "dashboard";
  navigate(initialRoute);

  // Projects dropdown (non-blocking)
  api.listProjects().then(projects => {
    const pSel = document.getElementById("global-project-select");
    if (pSel && Array.isArray(projects) && projects.length > 0) {
      pSel.innerHTML = projects.map(p => `<option value="${p.id}">${p.name}</option>`).join("");
      state.currentProjectId = projects[0].id;
      state.currentProjectName = projects[0].name;
      pSel.addEventListener("change", (e) => {
        state.currentProjectId = e.target.value;
        const selected = projects.find(p => p.id === e.target.value);
        if (selected) state.currentProjectName = selected.name;
        navigate(state.currentRoute);
      });
    }
  }).catch(e => console.warn("Could not load projects:", e));

  // Keep the topbar "live" pill honest
  api.getHealth().then(h => {
    const txt = document.getElementById("live-status-text");
    const ok = String(h?.status || "").toLowerCase() === "healthy";
    if (txt) txt.textContent = ok ? "Neural Defense Armed" : "Degraded";
    document.getElementById("live-pill")?.classList.toggle("degraded", !ok);
  }).catch(() => {
    const txt = document.getElementById("live-status-text");
    if (txt) txt.textContent = "Backend unreachable";
    document.getElementById("live-pill")?.classList.add("degraded");
  });
});
