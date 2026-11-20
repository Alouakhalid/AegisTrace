export async function renderWizard(container, navigate, state, api, toast) {
  let step = 1;
  let projects = [];
  try {
    projects = await api.listProjects();
  } catch (e) {
    projects = [{ id: "prj_default", name: "Enterprise Core API" }];
  }

  const formData = {
    projectId: state.currentProjectId || (projects[0] ? projects[0].id : "prj_default"),
    projectName: state.currentProjectName || (projects[0] ? projects[0].name : "Enterprise Core API"),
    targetType: "local_and_url",
    assessmentMode: "full",
    sourcePath: "/Users/alikhalidalikhalid/AegisTrace/dummy_web",
    githubUrl: "https://github.com/enterprise/core-api",
    githubBranch: "main",
    webTargetUrl: "http://127.0.0.1:5050",
    openapiUrl: "http://127.0.0.1:5050/openapi.json",
    allowedHosts: "127.0.0.1, localhost",
    excludedPaths: "/admin/shutdown, /billing/charge_card",
    roles: "admin, buyer_a, buyer_b",
    authToken: "",
    consented: true
  };

  function updateView() {
    container.innerHTML = `
      <div style="max-width: 880px; margin: 0 auto;">
        <div class="page-header" style="text-align: center; flex-direction: column; align-items: center; margin-bottom: 36px;">
          <h1 class="page-title">New Security Assessment</h1>
          <p class="page-subtitle">Configure autonomous multi-agent analysis for custom repositories, live endpoints, and scope constraints.</p>
        </div>

        <!-- 5 Step Indicator -->
        <div class="wizard-steps">
          <div class="wizard-step ${step === 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}" data-step="1">
            <div class="step-circle">${step > 1 ? '✓' : '1'}</div>
            <span class="step-title">Project</span>
          </div>
          <div class="wizard-step ${step === 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}" data-step="2">
            <div class="step-circle">${step > 2 ? '✓' : '2'}</div>
            <span class="step-title">Source Code</span>
          </div>
          <div class="wizard-step ${step === 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}" data-step="3">
            <div class="step-circle">${step > 3 ? '✓' : '3'}</div>
            <span class="step-title">Web Target</span>
          </div>
          <div class="wizard-step ${step === 4 ? 'active' : ''} ${step > 4 ? 'completed' : ''}" data-step="4">
            <div class="step-circle">${step > 4 ? '✓' : '4'}</div>
            <span class="step-title">Scope & Auth</span>
          </div>
          <div class="wizard-step ${step === 5 ? 'active' : ''}" data-step="5">
            <div class="step-circle">5</div>
            <span class="step-title">Review & Run</span>
          </div>
        </div>

        <!-- Step Container Card -->
        <div class="card card-central-glow" style="padding: 44px; border: 1px solid var(--border-gold); background: rgba(16, 15, 14, 0.85); border-radius: var(--radius-xl);">
          ${renderStepContent(step)}

          <!-- Footer Buttons -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 40px; padding-top: 28px; border-top: 1px solid var(--border-subtle);">
            ${step > 1 ? `
              <button class="btn btn-secondary" id="wiz-btn-prev">
                &larr; Previous Step
              </button>
            ` : `<div></div>`}

            ${step < 5 ? `
              <button class="btn btn-primary" id="wiz-btn-next">
                Next: Step ${step + 1} &rarr;
              </button>
            ` : `
              <button class="btn btn-white btn-lg" id="wiz-btn-launch">
                Launch Autonomous Assessment
              </button>
            `}
          </div>
        </div>
      </div>
    `;

    bindStepEvents();
  }

  function renderStepContent(currStep) {
    if (currStep === 1) {
      return `
        <div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 1: Select Assessment Project</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 28px;">Choose an existing project or enter a custom identifier for this assessment run.</p>
          
          <div class="form-group">
            <label class="form-label">Project Target</label>
            <select class="form-select" id="wiz-project-id">
              ${projects.map(p => `
                <option value="${p.id}" ${formData.projectId === p.id ? 'selected' : ''}>${p.name} (${p.id})</option>
              `).join("")}
              <option value="custom">-- Custom One-Off Assessment --</option>
            </select>
          </div>

          <div class="form-group" id="group-custom-name" style="${formData.projectId === 'custom' ? '' : 'display: none;'}">
            <label class="form-label">Custom Project / Assessment Name</label>
            <input type="text" class="form-control" id="wiz-custom-name" value="${formData.projectName}" placeholder="e.g. Q4 Staging Core API Audit">
          </div>

          <div class="form-group">
            <label class="form-label">Assessment Mode</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 10px;">
              <div class="card" style="cursor: pointer; border-color: ${formData.assessmentMode === 'full' ? 'var(--cyan-accent)' : 'var(--border-subtle)'}; padding: 22px; background: ${formData.assessmentMode === 'full' ? 'rgba(167, 139, 113, 0.12)' : 'rgba(255, 255, 255, 0.02)'};" id="mode-full">
                <div style="font-weight: 700; color: #fff; margin-bottom: 6px;">⚡ Full Assessment</div>
                <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">End-to-end AST scan, full OpenAPI attack surface crawl, and behavioral exploitation.</div>
              </div>
              <div class="card" style="cursor: pointer; border-color: ${formData.assessmentMode === 'scoped' ? 'var(--cyan-accent)' : 'var(--border-subtle)'}; padding: 22px; background: ${formData.assessmentMode === 'scoped' ? 'rgba(167, 139, 113, 0.12)' : 'rgba(255, 255, 255, 0.02)'};" id="mode-scoped">
                <div style="font-weight: 700; color: #fff; margin-bottom: 6px;">🎯 Scoped Assessment</div>
                <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">Focused active testing only on specific endpoints or vulnerability perspectives (IDOR/BOLA).</div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    if (currStep === 2) {
      return `
        <div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 2: Source Code Target Configuration</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 28px;">Specify the code repository for Code Intelligence AST and invariant derivation.</p>

          <div style="display: flex; gap: 24px; margin-bottom: 24px;">
            <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: #fff; font-size: 0.88rem;">
              <input type="radio" name="source_opt" value="local" ${formData.targetType !== 'github' ? 'checked' : ''} id="opt-local" style="accent-color: var(--cyan-accent);">
              Local Directory Path / Workspace
            </label>
            <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; color: #fff; font-size: 0.88rem;">
              <input type="radio" name="source_opt" value="github" ${formData.targetType === 'github' ? 'checked' : ''} id="opt-github" style="accent-color: var(--cyan-accent);">
              GitHub / Remote Git Repository
            </label>
          </div>

          <div class="form-group" id="group-local-path" style="${formData.targetType === 'github' ? 'display: none;' : ''}">
            <label class="form-label">Local Filesystem Path *</label>
            <input type="text" class="form-control" id="wiz-source-path" value="${formData.sourcePath}" placeholder="/path/to/target_repository">
            <div class="form-hint">Enter the absolute path of the target application code to be audited.</div>
          </div>

          <div id="group-github" style="${formData.targetType === 'github' ? '' : 'display: none;'}">
            <div class="form-group">
              <label class="form-label">Repository URL *</label>
              <input type="text" class="form-control" id="wiz-github-url" value="${formData.githubUrl}" placeholder="https://github.com/org/repo">
            </div>
            <div class="form-group">
              <label class="form-label">Branch</label>
              <input type="text" class="form-control" id="wiz-github-branch" value="${formData.githubBranch}" placeholder="main">
            </div>
          </div>
        </div>
      `;
    }

    if (currStep === 3) {
      return `
        <div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 3: Web App Target & API Specification</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 28px;">Configure the live target URL for dynamic behavioral testing and OpenAPI reconnaissance.</p>

          <div class="form-group">
            <label class="form-label">Web Target Base URL *</label>
            <input type="text" class="form-control" id="wiz-web-url" value="${formData.webTargetUrl}" placeholder="http://127.0.0.1:5050 or https://staging.example.com">
            <div class="form-hint">The active target address where Dynamic Testing Agent executes non-destructive security probes.</div>
          </div>

          <div class="form-group">
            <label class="form-label">OpenAPI / Swagger Specification URL (Optional)</label>
            <input type="text" class="form-control" id="wiz-openapi-url" value="${formData.openapiUrl}" placeholder="http://127.0.0.1:5050/openapi.json">
            <div class="form-hint">Recon Agent uses this to automatically map out the attack surface and parameter types.</div>
          </div>
        </div>
      `;
    }

    if (currStep === 4) {
      return `
        <div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 4: Scope Enforcement & Test Identities</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 28px;">Define strict ScopeGate network boundaries and test credentials for cross-tenant IDOR checks.</p>

          <div class="form-group">
            <label class="form-label">Authorized Hosts (ScopeGate Whitelist) *</label>
            <input type="text" class="form-control" id="wiz-allowed-hosts" value="${formData.allowedHosts}">
            <div class="form-hint">Comma-separated list of permitted network hosts. Any request outside these hosts is strictly blocked.</div>
          </div>

          <div class="form-group">
            <label class="form-label">Forbidden / Excluded Paths</label>
            <input type="text" class="form-control" id="wiz-excluded-paths" value="${formData.excludedPaths}">
            <div class="form-hint">Paths that must never be probed dynamically (e.g. destructive actions, shutdowns).</div>
          </div>

          <div class="form-group">
            <label class="form-label">Test User Roles / Identities</label>
            <input type="text" class="form-control" id="wiz-roles" value="${formData.roles}">
            <div class="form-hint">Comma-separated list of test tenant identities used for differential privilege analysis.</div>
          </div>

          <div class="form-group">
            <label class="form-label">Optional Authorization Header / Bearer Token</label>
            <input type="password" class="form-control" id="wiz-auth-token" value="${formData.authToken}" placeholder="Bearer eyJhbGci...">
          </div>
        </div>
      `;
    }

    if (currStep === 5) {
      return `
        <div>
          <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 5: Review & Authorize Assessment</h2>
          <p style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 28px;">Review your assessment targets and scope before launching the autonomous agents.</p>

          <div style="background: rgba(10, 10, 10, 0.7); border: 1px solid var(--border-gold); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 28px;">
            <div style="display: grid; grid-template-columns: 160px 1fr; row-gap: 14px; font-size: 0.86rem;">
              <span style="color: var(--text-muted);">Project:</span>
              <span style="color: #fff; font-weight: 600;">${formData.projectName}</span>

              <span style="color: var(--text-muted);">Assessment Mode:</span>
              <span style="color: var(--cyan-accent); font-weight: 700; text-transform: uppercase;">${formData.assessmentMode}</span>

              <span style="color: var(--text-muted);">Source Target:</span>
              <span style="font-family: monospace; color: #fff;">${formData.targetType === 'github' ? formData.githubUrl : formData.sourcePath}</span>

              <span style="color: var(--text-muted);">Web Target URL:</span>
              <span style="font-family: monospace; color: var(--cyan-accent);">${formData.webTargetUrl}</span>

              <span style="color: var(--text-muted);">Scope Whitelist:</span>
              <span style="color: var(--success); font-family: monospace;">${formData.allowedHosts}</span>

              <span style="color: var(--text-muted);">Test Identities:</span>
              <span style="color: var(--cyan-accent);">${formData.roles}</span>
            </div>
          </div>

          <div style="background: rgba(167, 139, 113, 0.08); border-left: 3px solid var(--cyan-accent); padding: 18px 22px; border-radius: 4px; margin-bottom: 24px;">
            <label style="display: flex; align-items: flex-start; gap: 14px; cursor: pointer;">
              <input type="checkbox" id="wiz-consent" ${formData.consented ? 'checked' : ''} style="margin-top: 3px; accent-color: var(--cyan-accent);">
              <span style="font-size: 0.82rem; color: #fff; line-height: 1.6;">
                I explicitly authorize AegisTrace to conduct autonomous security assessments on the specified targets and verify that all hosts are within my approved testing authority.
              </span>
            </label>
          </div>
        </div>
      `;
    }
  }

  function bindStepEvents() {
    document.getElementById("mode-full")?.addEventListener("click", () => {
      formData.assessmentMode = "full";
      updateView();
    });
    document.getElementById("mode-scoped")?.addEventListener("click", () => {
      formData.assessmentMode = "scoped";
      updateView();
    });

    document.getElementById("wiz-project-id")?.addEventListener("change", (e) => {
      formData.projectId = e.target.value;
      const group = document.getElementById("group-custom-name");
      if (group) group.style.display = e.target.value === "custom" ? "block" : "none";
    });

    document.getElementById("opt-local")?.addEventListener("change", () => {
      formData.targetType = "local";
      updateView();
    });
    document.getElementById("opt-github")?.addEventListener("change", () => {
      formData.targetType = "github";
      updateView();
    });

    document.getElementById("wiz-btn-prev")?.addEventListener("click", () => {
      saveCurrentStepInputs();
      step = Math.max(1, step - 1);
      updateView();
    });

    document.getElementById("wiz-btn-next")?.addEventListener("click", () => {
      saveCurrentStepInputs();
      step = Math.min(5, step + 1);
      updateView();
    });

    document.getElementById("wiz-btn-launch")?.addEventListener("click", async () => {
      saveCurrentStepInputs();
      if (!formData.consented) {
        toast("Please confirm authorization consent before launching active testing.", "warning");
        return;
      }

      toast("Initiating Autonomous Multi-Agent Security Assessment...", "info");
      try {
        const payload = {
          project_id: formData.projectId === "custom" ? "prj_custom" : formData.projectId,
          project_name: formData.projectName,
          target_type: formData.targetType,
          assessment_mode: formData.assessmentMode,
          source_path: formData.sourcePath,
          github_url: formData.githubUrl,
          github_branch: formData.githubBranch,
          web_target_url: formData.webTargetUrl,
          openapi_spec_url: formData.openapiUrl,
          allowed_hosts: formData.allowedHosts.split(",").map(h => h.trim()),
          excluded_paths: formData.excludedPaths.split(",").map(p => p.trim()),
          test_user_roles: formData.roles.split(",").map(r => r.trim()),
          auth_token: formData.authToken || null,
          active_testing_consented: true
        };

        const res = await api.startScan(payload);
        state.currentScanId = res.scan_id;
        toast(`Assessment ${res.scan_id} initiated across all 7 AI agents!`, "success");
        navigate("workspace");
      } catch (err) {
        toast("Failed to initiate scan: " + err.message, "critical");
      }
    });
  }

  function saveCurrentStepInputs() {
    if (step === 1) {
      const pSel = document.getElementById("wiz-project-id");
      if (pSel) formData.projectId = pSel.value;
      const cName = document.getElementById("wiz-custom-name");
      if (cName) formData.projectName = cName.value;
    }
    if (step === 2) {
      const sPath = document.getElementById("wiz-source-path");
      if (sPath) formData.sourcePath = sPath.value;
      const gUrl = document.getElementById("wiz-github-url");
      if (gUrl) formData.githubUrl = gUrl.value;
      const gBranch = document.getElementById("wiz-github-branch");
      if (gBranch) formData.githubBranch = gBranch.value;
    }
    if (step === 3) {
      const wUrl = document.getElementById("wiz-web-url");
      if (wUrl) formData.webTargetUrl = wUrl.value;
      const oUrl = document.getElementById("wiz-openapi-url");
      if (oUrl) formData.openapiUrl = oUrl.value;
    }
    if (step === 4) {
      const aHosts = document.getElementById("wiz-allowed-hosts");
      if (aHosts) formData.allowedHosts = aHosts.value;
      const ePaths = document.getElementById("wiz-excluded-paths");
      if (ePaths) formData.excludedPaths = ePaths.value;
      const roles = document.getElementById("wiz-roles");
      if (roles) formData.roles = roles.value;
      const token = document.getElementById("wiz-auth-token");
      if (token) formData.authToken = token.value;
    }
    if (step === 5) {
      const consent = document.getElementById("wiz-consent");
      if (consent) formData.consented = consent.checked;
    }
  }

  updateView();
}
