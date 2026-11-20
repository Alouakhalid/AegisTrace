import { renderLanding } from "./views/landing.js";
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
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    if (!res.ok) {
      let errDetail = res.statusText;
      try {
        const j = await res.json();
        if (j.detail) errDetail = j.detail;
      } catch (e) {}
      throw new Error(errDetail);
    }
    return res.json();
  },

  getHealth() { return this.req("/api/v1/health"); },
  getOverviewStats() { return this.req("/api/v1/stats/overview"); },
  listProjects() { return this.req("/api/v1/projects"); },
  createProject(data) { return this.req("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }); },
  listScans() { return this.req("/api/v1/scans"); },
  getScanStatus(id) { return this.req(`/api/v1/scans/${id}`); },
  getScanLogs(id) { return this.req(`/api/v1/scans/${id}/logs`); },
  startScan(data) { return this.req("/api/v1/scans", { method: "POST", body: JSON.stringify(data) }); },
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
  analyzeRepository(url, token) { return this.req("/api/v1/repositories/analyze", { method: "POST", body: JSON.stringify({ repository_url: url, auth_token: token }) }); },
  createAssessment(data) { return this.req("/api/v1/assessments", { method: "POST", body: JSON.stringify(data) }); },
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
  selectedFindingId: "fnd_prod_001"
};

// Toast Notifications
export function toast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `
    <div style="font-weight: 700; color: #fff; font-size: 0.88rem;">
      ${type === 'success' ? '✓' : (type === 'critical' ? '✖' : 'ℹ')}
    </div>
    <div style="font-size: 0.84rem; color: #fff;">${message}</div>
  `;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    t.style.transform = "translateX(100%)";
    t.style.transition = "all 0.3s ease";
    setTimeout(() => t.remove(), 300);
  }, 4000);
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
export function navigate(route) {
  state.currentRoute = route;
  window.location.hash = `#${route}`;

  // Mode body classes for fullscreen views
  if (route === "landing") {
    document.body.classList.add("landing-mode");
    document.body.classList.remove("auth-mode");
  } else if (route === "auth") {
    document.body.classList.add("auth-mode");
    document.body.classList.remove("landing-mode");
  } else {
    document.body.classList.remove("landing-mode");
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
      landing: "Hero Overview",
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

  switch (route) {
    case "landing":
      renderLanding(viewRoot, navigate);
      break;
    case "auth":
      renderAuth(viewRoot, navigate, state, api, toast);
      break;
    case "dashboard":
      renderDashboard(viewRoot, navigate, state, api);
      break;
    case "projects":
      renderProjects(viewRoot, navigate, state, api, showModal, toast);
      break;
    case "wizard":
      renderWizard(viewRoot, navigate, state, api, toast);
      break;
    case "workspace":
      renderWorkspace(viewRoot, navigate, state, api, toast);
      break;
    case "code_intel":
      renderCodeIntel(viewRoot, navigate, state, api);
      break;
    case "surface":
      renderAttackSurface(viewRoot, navigate, state, api, showModal);
      break;
    case "findings":
      renderFindings(viewRoot, navigate, state, api, showModal);
      break;
    case "finding_details":
      renderFindingDetails(viewRoot, navigate, state, api, toast);
      break;
    case "verification":
      renderVerification(viewRoot, navigate);
      break;
    case "remediation":
      renderRemediation(viewRoot, navigate, state);
      break;
    case "approvals":
      renderApprovals(viewRoot, navigate, state, api, showModal, toast);
      break;
    case "reports":
      renderReports(viewRoot, navigate, state, api, toast);
      break;
    case "skills":
      renderSkills(viewRoot, navigate, state, api, showModal);
      break;
    case "benchmarks":
      renderBenchmarks(viewRoot, navigate, state, api);
      break;
    case "settings":
      renderSettings(viewRoot, navigate, state, api, toast);
      break;
    case "supporting":
      renderSupporting(viewRoot, navigate, state, api, toast);
      break;
    default:
      renderDashboard(viewRoot, navigate, state, api);
      break;
  }
}

// App Initialization
window.addEventListener("DOMContentLoaded", async () => {
  // Bind sidebar nav links
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const route = e.currentTarget.getAttribute("data-route");
      navigate(route);
    });
  });

  // Brand link -> dashboard
  document.getElementById("brand-link")?.addEventListener("click", () => navigate("dashboard"));
  
  // Toggle Landing Hero
  document.getElementById("btn-toggle-landing")?.addEventListener("click", () => {
    if (state.currentRoute === "landing") {
      navigate("dashboard");
    } else {
      navigate("landing");
    }
  });

  // Topbar New Assessment button
  document.getElementById("btn-new-assessment")?.addEventListener("click", () => navigate("wizard"));

  // Load projects into global selector
  try {
    const projects = await api.listProjects();
    const pSel = document.getElementById("global-project-select");
    if (pSel && projects && projects.length > 0) {
      pSel.innerHTML = projects.map(p => `
        <option value="${p.id}">${p.name}</option>
      `).join("");
      state.currentProjectId = projects[0].id;
      state.currentProjectName = projects[0].name;

      pSel.addEventListener("change", (e) => {
        state.currentProjectId = e.target.value;
        const selected = projects.find(p => p.id === e.target.value);
        if (selected) state.currentProjectName = selected.name;
        navigate(state.currentRoute);
      });
    }
  } catch (e) {
    console.warn("Could not load global projects dropdown:", e);
  }

  // Handle hash change events
  window.addEventListener("hashchange", () => {
    const route = window.location.hash.replace("#", "");
    if (route && route !== state.currentRoute) {
      navigate(route);
    }
  });

  // Handle hash routing on initial load (defaults to full Hero Showcase!)
  const hashRoute = window.location.hash.replace("#", "");
  navigate(hashRoute || "landing");
});
