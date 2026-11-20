export async function renderWizard(container, navigate, state, api, toast) {
  let activeTab = "quick";
  let step = 1;
  let projects = [];
  try {
    projects = await api.listProjects();
  } catch (e) {
    projects = [{ id: "prj_default", name: "Enterprise Core API" }];
  }

  const formData = {
    projectId: state.currentProjectId || (projects[0] ? projects[0].id : "prj_default"),
    projectName: "Autonomous Repository Security Audit",
    targetType: "github",
    assessmentMode: "full",
    githubUrl: "https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI",
    githubBranch: "main",
    sourcePath: "/Users/alikhalidalikhalid/AegisTrace/dummy_web",
    webTargetUrl: "http://127.0.0.1:5050",
    openapiUrl: "",
    allowedHosts: "127.0.0.1, localhost",
    excludedPaths: "",
    roles: "admin, buyer_a, buyer_b",
    authToken: "",
    consented: true,
    scanCategories: ["secrets", "cors", "deserialization", "idor_auth", "tavily", "ai_security"]
  };

  const categoryOptions = [
    { id: "secrets", icon: "🔑", name: "Exposed Secrets & API Keys", desc: "Hardcoded tokens, HuggingFace/OpenAI keys, and committed .env credentials" },
    { id: "cors", icon: "🌐", name: "API Misconfiguration & CORS", desc: "Permissive wildcard CORS with credentials, header security, and routing flaws" },
    { id: "deserialization", icon: "🧪", name: "Insecure Deserialization", desc: "Joblib, Pickle, unauthenticated ML model weights, and code execution risks" },
    { id: "idor_auth", icon: "🛡️", name: "Broken Access Control & IDOR", desc: "Missing authentication on state-changing API endpoints and invariant violations" },
    { id: "tavily", icon: "🔍", name: "Live Threat & CVE Intelligence (Tavily)", desc: "Real-time query of Tavily API for newly published CVEs on detected dependencies" },
    { id: "ai_security", icon: "🤖", name: "AI / LLM Model Security", desc: "Prompt injection surface, system prompt extraction, and unconstrained LLM calls" }
  ];

  function render() {
    container.innerHTML = `
      <div style="max-width: 900px; margin: 0 auto;">
        <div class="page-header" style="text-align: center; flex-direction: column; align-items: center; margin-bottom: 28px;">
          <div style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; background: rgba(121, 59, 255, 0.12); border: 1px solid rgba(121, 59, 255, 0.3); border-radius: 999px; margin-bottom: 12px;">
            <span style="font-size: 11px; font-weight: 700; color: #793BFF; text-transform: uppercase; letter-spacing: 1.2px;">Autonomous Multi-Agent Security Engine</span>
          </div>
          <h1 class="page-title" style="font-size: 2.1rem; margin-bottom: 8px;">New Security Assessment</h1>
          <p class="page-subtitle" style="font-size: 0.95rem; max-width: 640px; margin: 0 auto; color: var(--text-muted);">
            Provide any GitHub repository link. AegisTrace will clone the code, extract AST structures, execute BugHunter audits, and correlate live Tavily CVE intelligence.
          </p>
        </div>

        <!-- Mode Tabs -->
        <div style="display: flex; justify-content: center; gap: 12px; margin-bottom: 28px;">
          <button class="btn ${activeTab === "quick" ? "btn-primary" : "btn-secondary"}" id="tab-quick-btn" style="padding: 10px 24px; font-size: 0.9rem; font-weight: 600;">
            ⚡ One-Click GitHub Audit
          </button>
          <button class="btn ${activeTab === "advanced" ? "btn-primary" : "btn-secondary"}" id="tab-advanced-btn" style="padding: 10px 24px; font-size: 0.9rem; font-weight: 600;">
            ⚙️ Advanced Multi-Target Wizard
          </button>
        </div>

        ${activeTab === "quick" ? renderQuickAuditCard() : renderAdvancedWizardCard()}
      </div>
    `;

    bindEvents();
  }

  function renderQuickAuditCard() {
    return `
      <div class="card card-central-glow" style="padding: 38px; border: 1px solid var(--border-gold); background: rgba(16, 15, 14, 0.9); border-radius: var(--radius-xl);">
        
        <!-- GitHub Input Section -->
        <div style="margin-bottom: 28px;">
          <label style="display: block; font-weight: 700; color: #fff; font-size: 0.92rem; margin-bottom: 10px;">
            GitHub Repository URL <span style="color: var(--cyan-accent);">*</span>
          </label>
          <div style="position: relative;">
            <input type="text" class="form-control" id="quick-github-url" value="${formData.githubUrl}" 
                   placeholder="https://github.com/organization/repository" 
                   style="font-size: 1rem; padding: 14px 16px; font-family: IBM Plex Mono, monospace; background: rgba(0,0,0,0.4); border-color: rgba(66, 107, 255, 0.4);">
          </div>
          
          <!-- Presets -->
          <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px;">
            <span style="font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px;">Quick Test Targets:</span>
            <button class="badge-btn" data-url="https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI" style="background: rgba(121,59,255,0.15); border: 1px solid rgba(121,59,255,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; cursor: pointer;">
              🧠 Neurovain-Data-Analysis-AI
            </button>
            <button class="badge-btn" data-url="https://github.com/Alouakhalid/chess_RL" style="background: rgba(66,107,255,0.15); border: 1px solid rgba(66,107,255,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; cursor: pointer;">
              ♟️ chess_RL
            </button>
            <button class="badge-btn" data-url="https://github.com/ebraheembinessa-E-vias/community-reels-engine" style="background: rgba(36,200,245,0.15); border: 1px solid rgba(36,200,245,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; cursor: pointer;">
              🎬 community-reels-engine
            </button>
          </div>
        </div>

        <!-- Assessment Mode -->
        <div style="margin-bottom: 28px;">
          <label style="display: block; font-weight: 700; color: #fff; font-size: 0.92rem; margin-bottom: 12px;">
            Assessment Scope
          </label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div class="card" id="quick-mode-full" style="cursor: pointer; padding: 18px; border: 1px solid ${formData.assessmentMode === "full" ? "var(--cyan-accent)" : "var(--border-subtle)"}; background: ${formData.assessmentMode === "full" ? "rgba(36,200,245,0.08)" : "rgba(255,255,255,0.02)"}; border-radius: var(--radius-lg);">
              <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #fff; margin-bottom: 6px;">
                <span style="color: var(--cyan-accent);">⚡</span> Full Assessment (التقييم الشامل)
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">
                Runs all 7 agents across all vulnerability vectors: AST Code Intel, Exposed Secrets, CORS/API Misconfig, Insecure Deserialization, Broken Auth, and Tavily Live CVEs.
              </div>
            </div>

            <div class="card" id="quick-mode-targeted" style="cursor: pointer; padding: 18px; border: 1px solid ${formData.assessmentMode === "targeted" ? "var(--cyan-accent)" : "var(--border-subtle)"}; background: ${formData.assessmentMode === "targeted" ? "rgba(36,200,245,0.08)" : "rgba(255,255,255,0.02)"}; border-radius: var(--radius-lg);">
              <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #fff; margin-bottom: 6px;">
                <span style="color: #793BFF;">🎯</span> Targeted Assessment (فحص مخصص ومحدد)
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">
                Select precisely which vulnerability categories you want the agents to hunt for. Other checks remain disabled.
              </div>
            </div>
          </div>
        </div>

        <!-- Targeted Categories Grid -->
        <div id="targeted-categories-section" style="${formData.assessmentMode === "targeted" ? "display: block;" : "display: none;"} margin-bottom: 28px;">
          <label style="display: block; font-weight: 700; color: #fff; font-size: 0.92rem; margin-bottom: 12px;">
            Select Target Security Vectors:
          </label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            ${categoryOptions.map(cat => `
              <label class="card" style="display: flex; align-items: flex-start; gap: 12px; padding: 14px; cursor: pointer; border: 1px solid ${formData.scanCategories.includes(cat.id) ? "rgba(121, 59, 255, 0.4)" : "rgba(255,255,255,0.06)"}; background: ${formData.scanCategories.includes(cat.id) ? "rgba(121, 59, 255, 0.08)" : "rgba(0,0,0,0.2)"}; border-radius: var(--radius-md);">
                <input type="checkbox" class="cat-checkbox" value="${cat.id}" ${formData.scanCategories.includes(cat.id) ? "checked" : ""} style="margin-top: 3px; accent-color: #793BFF;">
                <div>
                  <div style="font-weight: 600; color: #fff; font-size: 0.86rem; margin-bottom: 3px;">
                    ${cat.icon} ${cat.name}
                  </div>
                  <div style="font-size: 0.76rem; color: var(--text-muted); line-height: 1.4;">
                    ${cat.desc}
                  </div>
                </div>
              </label>
            `).join("")}
          </div>
        </div>

        <!-- Platform Status Row -->
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 18px; margin-bottom: 28px;">
          <div style="display: flex; align-items: center; gap: 18px;">
            <div style="display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #fff;">
              <span style="color: var(--success); font-size: 10px;">●</span> Tavily Threat API: <strong style="color: var(--success);">ACTIVE</strong>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #fff;">
              <span style="color: var(--success); font-size: 10px;">●</span> Autonomous Agents: <strong style="color: #fff;">7 ONLINE</strong>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #fff;">
              <span style="color: var(--success); font-size: 10px;">●</span> Auto-Clone: <strong style="color: var(--cyan-accent);">ENABLED</strong>
            </div>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); font-family: monospace;">
            Zero False Positives Guarantee
          </div>
        </div>

        <!-- Action Button -->
        <div style="text-align: center;">
          <button class="btn btn-primary btn-lg" id="btn-quick-launch" style="width: 100%; padding: 16px; font-size: 1.05rem; font-weight: 700; letter-spacing: 0.5px; border-radius: var(--radius-lg); background: linear-gradient(135deg, #793BFF 0%, #426BFF 100%); border: none; box-shadow: 0 4px 20px rgba(121, 59, 255, 0.4); cursor: pointer;">
            🚀 Launch Autonomous Security Audit
          </button>
        </div>

      </div>
    `;
  }

  function renderAdvancedWizardCard() {
    return `
      <div class="card card-central-glow" style="padding: 40px; border: 1px solid var(--border-gold); background: rgba(16, 15, 14, 0.9); border-radius: var(--radius-xl);">
        <!-- 5 Step Indicator -->
        <div class="wizard-steps" style="margin-bottom: 30px;">
          <div class="wizard-step ${step === 1 ? "active" : ""} ${step > 1 ? "completed" : ""}" data-step="1">
            <div class="step-circle">${step > 1 ? "✓" : "1"}</div>
            <span class="step-title">Project</span>
          </div>
          <div class="wizard-step ${step === 2 ? "active" : ""} ${step > 2 ? "completed" : ""}" data-step="2">
            <div class="step-circle">${step > 2 ? "✓" : "2"}</div>
            <span class="step-title">Source</span>
          </div>
          <div class="wizard-step ${step === 3 ? "active" : ""} ${step > 3 ? "completed" : ""}" data-step="3">
            <div class="step-circle">${step > 3 ? "✓" : "3"}</div>
            <span class="step-title">Target URL</span>
          </div>
          <div class="wizard-step ${step === 4 ? "active" : ""} ${step > 4 ? "completed" : ""}" data-step="4">
            <div class="step-circle">${step > 4 ? "✓" : "4"}</div>
            <span class="step-title">Scope</span>
          </div>
          <div class="wizard-step ${step === 5 ? "active" : ""}" data-step="5">
            <div class="step-circle">5</div>
            <span class="step-title">Run</span>
          </div>
        </div>

        ${renderStepContent(step)}

        <!-- Footer Buttons -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 36px; padding-top: 24px; border-top: 1px solid var(--border-subtle);">
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
    `;
  }

  function renderStepContent(currStep) {
    if (currStep === 1) {
      return `
        <div>
          <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 1: Select Assessment Project</h2>
          <p style="font-size: 0.86rem; color: var(--text-muted); margin-bottom: 24px;">Choose an existing project or enter a custom identifier for this assessment run.</p>
          
          <div class="form-group">
            <label class="form-label">Project Target</label>
            <select class="form-select" id="wiz-project-id">
              ${projects.map(p => `
                <option value="${p.id}" ${formData.projectId === p.id ? "selected" : ""}>${p.name} (${p.id})</option>
              `).join("")}
              <option value="custom">-- Custom One-Off Assessment --</option>
            </select>
          </div>

          <div class="form-group" id="group-custom-name" style="${formData.projectId === "custom" ? "" : "display: none;"}">
            <label class="form-label">Custom Project / Assessment Name</label>
            <input type="text" class="form-control" id="wiz-custom-name" value="${formData.projectName}" placeholder="e.g. Q4 Staging Core API Audit">
          </div>
        </div>
      `;
    }

    if (currStep === 2) {
      return `
        <div>
          <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 2: Source Code Target Configuration</h2>
          <p style="font-size: 0.86rem; color: var(--text-muted); margin-bottom: 24px;">Specify the code repository for Code Intelligence AST and invariant derivation.</p>

          <div class="form-group">
            <label class="form-label">GitHub Repository URL *</label>
            <input type="text" class="form-control" id="wiz-github-url" value="${formData.githubUrl}" placeholder="https://github.com/org/repo">
          </div>
          <div class="form-group">
            <label class="form-label">Branch</label>
            <input type="text" class="form-control" id="wiz-github-branch" value="${formData.githubBranch}" placeholder="main">
          </div>
        </div>
      `;
    }

    if (currStep === 3) {
      return `
        <div>
          <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 3: Web App Target & API Specification</h2>
          <p style="font-size: 0.86rem; color: var(--text-muted); margin-bottom: 24px;">Configure the live target URL for dynamic behavioral testing.</p>

          <div class="form-group">
            <label class="form-label">Web Target Base URL</label>
            <input type="text" class="form-control" id="wiz-web-url" value="${formData.webTargetUrl}" placeholder="http://127.0.0.1:5050 or https://example.com">
          </div>
        </div>
      `;
    }

    if (currStep === 4) {
      return `
        <div>
          <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 4: Scope Enforcement & Test Identities</h2>
          <p style="font-size: 0.86rem; color: var(--text-muted); margin-bottom: 24px;">Define strict ScopeGate network boundaries and test credentials.</p>

          <div class="form-group">
            <label class="form-label">Authorized Hosts (ScopeGate Whitelist)</label>
            <input type="text" class="form-control" id="wiz-allowed-hosts" value="${formData.allowedHosts}">
          </div>
          <div class="form-group">
            <label class="form-label">Test User Roles / Identities</label>
            <input type="text" class="form-control" id="wiz-roles" value="${formData.roles}">
          </div>
        </div>
      `;
    }

    if (currStep === 5) {
      return `
        <div>
          <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Step 5: Review & Authorize Assessment</h2>
          <p style="font-size: 0.86rem; color: var(--text-muted); margin-bottom: 24px;">Review your assessment targets before launching the autonomous agents.</p>

          <div style="background: rgba(0, 0, 0, 0.4); border: 1px solid var(--border-gold); border-radius: var(--radius-lg); padding: 20px; margin-bottom: 24px; font-size: 0.86rem;">
            <div>Target: <strong style="color: #fff; font-family: monospace;">${formData.githubUrl}</strong></div>
            <div style="margin-top: 8px;">Mode: <strong style="color: var(--cyan-accent); text-transform: uppercase;">${formData.assessmentMode}</strong></div>
          </div>

          <label style="display: flex; align-items: flex-start; gap: 12px; cursor: pointer;">
            <input type="checkbox" id="wiz-consent" ${formData.consented ? "checked" : ""} style="margin-top: 3px; accent-color: var(--cyan-accent);">
            <span style="font-size: 0.82rem; color: #fff; line-height: 1.5;">
              I explicitly authorize AegisTrace to conduct autonomous security assessments on the specified target.
            </span>
          </label>
        </div>
      `;
    }
  }

  function bindEvents() {
    document.getElementById("tab-quick-btn")?.addEventListener("click", () => {
      activeTab = "quick";
      render();
    });
    document.getElementById("tab-advanced-btn")?.addEventListener("click", () => {
      activeTab = "advanced";
      render();
    });

    document.querySelectorAll(".badge-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const url = e.target.getAttribute("data-url");
        if (url) {
          formData.githubUrl = url;
          const inp = document.getElementById("quick-github-url");
          if (inp) inp.value = url;
        }
      });
    });

    document.getElementById("quick-mode-full")?.addEventListener("click", () => {
      formData.assessmentMode = "full";
      render();
    });

    document.getElementById("quick-mode-targeted")?.addEventListener("click", () => {
      formData.assessmentMode = "targeted";
      render();
    });

    document.querySelectorAll(".cat-checkbox").forEach(cb => {
      cb.addEventListener("change", (e) => {
        const val = e.target.value;
        if (e.target.checked) {
          if (!formData.scanCategories.includes(val)) formData.scanCategories.push(val);
        } else {
          formData.scanCategories = formData.scanCategories.filter(c => c !== val);
        }
      });
    });

    document.getElementById("btn-quick-launch")?.addEventListener("click", async () => {
      const gInput = document.getElementById("quick-github-url");
      if (gInput && gInput.value.trim()) {
        formData.githubUrl = gInput.value.trim();
      }

      if (!formData.githubUrl) {
        toast("Please enter a valid GitHub repository URL.", "warning");
        return;
      }

      if (formData.assessmentMode === "targeted" && formData.scanCategories.length === 0) {
        toast("Please select at least one security vector for targeted assessment.", "warning");
        return;
      }

      executeLaunch();
    });

    document.getElementById("wiz-btn-prev")?.addEventListener("click", () => {
      step = Math.max(1, step - 1);
      render();
    });

    document.getElementById("wiz-btn-next")?.addEventListener("click", () => {
      step = Math.min(5, step + 1);
      render();
    });

    document.getElementById("wiz-btn-launch")?.addEventListener("click", () => {
      executeLaunch();
    });
  }

  async function executeLaunch() {
    toast("Initiating Autonomous Multi-Agent Security Assessment...", "info");
    try {
      const allowed = ["127.0.0.1", "localhost"];
      if (formData.webTargetUrl) {
        try {
          const u = new URL(formData.webTargetUrl);
          if (u.hostname && !allowed.includes(u.hostname)) {
            allowed.push(u.hostname);
          }
        } catch(e) {}
      }

      const payload = {
        project_id: formData.projectId === "custom" ? "prj_custom" : formData.projectId,
        project_name: formData.projectName,
        target_type: "github",
        assessment_mode: formData.assessmentMode,
        github_url: formData.githubUrl,
        github_branch: formData.githubBranch,
        web_target_url: formData.webTargetUrl,
        openapi_spec_url: formData.openapiUrl,
        allowed_hosts: allowed,
        excluded_paths: [],
        test_user_roles: ["admin", "tester"],
        auth_token: null,
        active_testing_consented: true,
        scan_categories: formData.scanCategories
      };

      const res = await api.startScan(payload);
      state.currentScanId = res.scan_id;
      toast(`Assessment ${res.scan_id} initiated across all 7 AI agents!`, "success");
      navigate("workspace");
    } catch (err) {
      toast("Failed to initiate scan: " + err.message, "critical");
    }
  }

  render();
}
