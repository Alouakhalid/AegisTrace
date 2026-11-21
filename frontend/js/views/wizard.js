export async function renderWizard(container, navigate, state, api, toast) {
  let initialUrl = state.targetRepoUrl || "https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI";
  let isAnalyzing = false;
  let analysisReport = null;
  let assessmentMode = "full"; // "full" or "custom"
  let selectedCategories = ["idor_access_control", "data_security", "api_security", "dependencies"];
  let targetDirFilter = "";
  let customInstructions = "";
  let authToken = "";

  const availableCategories = [
    { id: "idor_access_control", icon: "🛡️", name: "Access Control & IDOR", desc: "BOLA/IDOR, missing ownership verification, multi-tenant boundary checks" },
    { id: "data_security", icon: "🧪", name: "Data Security & Deserialization", desc: "Python pickle/joblib deserialization, source code leaks, file upload flaws" },
    { id: "api_security", icon: "🌐", name: "API & Interface Security", desc: "CORS misconfiguration, excessive data exposure, shadow endpoints" },
    { id: "dependencies", icon: "🔍", name: "Dependencies & Threat Intel", desc: "Correlate third-party libraries in real-time with Tavily live CVE intelligence" },
    { id: "authentication", icon: "🔑", name: "Authentication & Session", desc: "Auth bypass vectors, JWT cryptographic validation, session hijacking" },
    { id: "injection", icon: "⚡", name: "Injection Vectors", desc: "SQL injection, remote code execution (RCE), template injection (SSTI)" },
    { id: "business_logic", icon: "⚙️", name: "Business Logic Flaws", desc: "Race conditions, inconsistent state transitions, price/parameter tampering" },
    { id: "ai_security", icon: "🤖", name: "AI / LLM Model Security", desc: "Prompt injection, unsafe model weights loading, unconstrained tool use" }
  ];

  function render() {
    container.innerHTML = `
      <div style="max-width: 960px; margin: 0 auto;">
        
        <!-- Page Header -->
        <div class="page-header" style="text-align: center; flex-direction: column; align-items: center; margin-bottom: 28px;">
          <div style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 16px; background: rgba(139, 92, 246, 0.12); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 999px; margin-bottom: 12px;">
            <span style="font-size: 11px; font-weight: 700; color: #793BFF; text-transform: uppercase; letter-spacing: 1.2px;">Repository-to-Security Intelligence Engine</span>
          </div>
          <h1 class="page-title" style="font-size: 2.2rem; margin-bottom: 8px;">Repository Security Assessment</h1>
          <p class="page-subtitle" style="font-size: 0.95rem; max-width: 680px; margin: 0 auto; color: var(--text-muted);">
            Paste any GitHub repository link. AegisTrace inspects the architecture, extracts AST code invariants, correlates Tavily CVE threat advisories, and launches the 7 official agents.
          </p>
        </div>

        <!-- Repository Input Card -->
        <div class="card card-central-glow" style="padding: 32px; border: 1px solid var(--border-accent); background: rgba(8, 8, 13, 0.9); border-radius: var(--radius-xl); margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <label style="font-weight: 700; color: #fff; font-size: 0.92rem; display: flex; align-items: center; gap: 8px;">
              <span>🐙</span> GitHub Repository URL <span style="color: var(--cyan-accent);">*</span>
            </label>
            <span style="font-size: 0.76rem; color: var(--text-muted); font-family: var(--font-mono);">Public or Private with Token</span>
          </div>

          <div style="display: flex; gap: 12px; align-items: center;">
            <input type="text" class="form-control" id="repo-url-input" value="${initialUrl}" 
                   placeholder="https://github.com/owner/repository" 
                   style="flex: 1; font-size: 1rem; padding: 14px 16px; font-family: var(--font-mono); background: rgba(0,0,0,0.5); border-color: rgba(109, 75, 240, 0.4);">
            <button class="btn btn-primary" id="btn-analyze-repo" style="padding: 14px 28px; font-size: 0.95rem; font-weight: 700; white-space: nowrap; display: flex; align-items: center; gap: 8px;">
              ${isAnalyzing ? `<span class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span> Analyzing...` : `<span>⚡</span> Analyze Repository`}
            </button>
          </div>

          <!-- Quick Presets -->
          <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 14px;">
            <span style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px;">Quick Targets:</span>
            <button class="repo-preset-btn" data-url="https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI" style="background: rgba(139, 92, 246,0.15); border: 1px solid rgba(139, 92, 246,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.76rem; cursor: pointer;">
              🧠 Neurovain-Data-Analysis-AI
            </button>
            <button class="repo-preset-btn" data-url="https://github.com/Alouakhalid/chess_RL" style="background: rgba(109, 75, 240,0.15); border: 1px solid rgba(109, 75, 240,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.76rem; cursor: pointer;">
              ♟️ chess_RL
            </button>
            <button class="repo-preset-btn" data-url="https://github.com/ebraheembinessa-E-vias/community-reels-engine" style="background: rgba(196, 181, 253,0.15); border: 1px solid rgba(196, 181, 253,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.76rem; cursor: pointer;">
              🎬 community-reels-engine
            </button>
          </div>

          <!-- Private Repo Auth Collapsible -->
          <details style="margin-top: 16px; font-size: 0.82rem; color: var(--text-muted);">
            <summary style="cursor: pointer; color: var(--cyan-accent); font-weight: 600;">Optional: Private Repository Access Token</summary>
            <div style="margin-top: 10px; max-width: 500px;">
              <input type="password" class="form-control" id="repo-auth-token" placeholder="ghp_... (GitHub Personal Access Token)" value="${authToken}" style="font-size: 0.85rem; padding: 8px 12px;">
              <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 4px;">Tokens are never stored or logged in responses.</div>
            </div>
          </details>
        </div>

        <!-- Dynamic Intelligence Report Area -->
        ${renderIntelligenceArea()}

      </div>
    `;

    bindEvents();
  }

  function renderIntelligenceArea() {
    if (isAnalyzing) {
      return `
        <div class="card" style="padding: 48px; text-align: center; background: rgba(8, 8, 13, 0.7); border: 1px dashed var(--border-accent); border-radius: var(--radius-xl);">
          <div class="spinner" style="width: 44px; height: 44px; margin: 0 auto 20px auto; border-color: var(--cyan-accent); border-top-color: transparent;"></div>
          <h3 style="color: #fff; font-size: 1.2rem; margin-bottom: 8px;">Understanding Repository Architecture</h3>
          <p style="color: var(--text-muted); font-size: 0.9rem; max-width: 500px; margin: 0 auto;" id="analysis-step-text">
            Validating repository URL & pinning Git commit SHA...
          </p>
        </div>
      `;
    }

    if (!analysisReport) {
      return `
        <div class="card" style="padding: 36px; text-align: center; background: rgba(255, 255, 255, 0.01); border: 1px dashed var(--border-subtle); border-radius: var(--radius-xl);">
          <div style="font-size: 2rem; margin-bottom: 12px; opacity: 0.6;">🔍</div>
          <div style="font-weight: 700; color: #fff; font-size: 1rem; margin-bottom: 6px;">Ready for Repository Understanding</div>
          <p style="color: var(--text-muted); font-size: 0.85rem; max-width: 540px; margin: 0 auto;">
            Click <strong>Analyze Repository</strong> above to automatically discover languages, entry points, API routes, data models, and potential security risk areas.
          </p>
        </div>
      `;
    }

    const r = analysisReport;
    return `
      <!-- REPOSITORY INTELLIGENCE REPORT -->
      <div class="card" style="padding: 28px; border: 1px solid var(--border-accent); background: rgba(21, 19, 31, 0.95); border-radius: var(--radius-xl); margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <h2 style="font-size: 1.4rem; color: #fff; font-weight: 800; margin: 0;">${r.owner} / ${r.repository_name}</h2>
              <span class="badge badge-success" style="font-size: 0.72rem;">ACTIVE</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 6px; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted);">
              <span>Branch: <strong style="color: #fff;">${r.branch}</strong></span>
              <span>&bull;</span>
              <span>Commit: <strong style="color: var(--cyan-accent);">${r.commit_sha.slice(0, 8)}</strong></span>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" id="btn-reanalyze">Re-Analyze</button>
          </div>
        </div>

        <!-- Tech & Metrics Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
          <div style="background: rgba(0,0,0,0.35); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Languages</div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
              ${r.languages.map(l => `<span class="badge badge-cyan" style="font-size: 10px;">${l}</span>`).join("")}
            </div>
          </div>
          <div style="background: rgba(0,0,0,0.35); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Frameworks</div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
              ${r.frameworks.length ? r.frameworks.map(f => `<span class="badge badge-low" style="font-size: 10px;">${f}</span>`).join("") : `<span style="font-size: 11px; color: var(--text-muted);">Standard Library</span>`}
            </div>
          </div>
          <div style="background: rgba(0,0,0,0.35); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Discovered Endpoints</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: var(--success); margin-top: 4px;">
              ${r.discovered_endpoints.length}
            </div>
          </div>
          <div style="background: rgba(0,0,0,0.35); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Code Files Analyzed</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: #fff; margin-top: 4px;">
              ${r.analyzed_files_count} <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 400;">(${r.skipped_files_count} noise skipped)</span>
            </div>
          </div>
        </div>

        <!-- Architecture Summary Banner -->
        <div style="background: rgba(139, 92, 246, 0.08); border-left: 3px solid var(--primary); padding: 12px 16px; border-radius: 4px; margin-bottom: 20px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
          <strong>Architecture Map:</strong> ${r.architecture_summary}
        </div>

        <!-- Potential Risk Areas Highlight -->
        ${r.potential_risk_areas.length ? `
          <div style="margin-bottom: 8px;">
            <div style="font-size: 0.82rem; font-weight: 700; color: var(--warning); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">
              Detected Security Risk Areas (${r.potential_risk_areas.length}):
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${r.potential_risk_areas.map(ra => `
                <div style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-md); padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <strong style="color: #fff; font-size: 0.86rem;">${ra.title}</strong>
                    <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 2px;">${ra.description}</div>
                  </div>
                  <span class="badge ${ra.severity === 'critical' ? 'badge-critical' : (ra.severity === 'high' ? 'badge-high' : 'badge-warning')}" style="font-size: 10px; text-transform: uppercase;">
                    ${ra.severity}
                  </span>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </div>

      <!-- ASSESSMENT SCOPE SELECTION (Section 4) -->
      <div class="card" style="padding: 32px; border: 1px solid var(--border-gold); background: rgba(8, 8, 13, 0.95); border-radius: var(--radius-xl); margin-bottom: 28px;">
        <h3 style="font-size: 1.25rem; color: #fff; font-weight: 800; margin-bottom: 6px;">Choose Assessment Scope</h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 20px;">
          Select how you want AegisTrace and the seven official agents to investigate this repository.
        </p>

        <!-- Two Main Options Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
          <!-- Option A: Full -->
          <div class="card" id="scope-option-full" style="cursor: pointer; padding: 22px; border: 2px solid ${assessmentMode === "full" ? "var(--cyan-accent)" : "var(--border-subtle)"}; background: ${assessmentMode === "full" ? "rgba(196, 181, 253, 0.08)" : "rgba(255,255,255,0.02)"}; border-radius: var(--radius-lg); transition: all 0.2s ease;">
            <div style="display: flex; align-items: center; gap: 10px; font-weight: 800; color: #fff; font-size: 1.05rem; margin-bottom: 8px;">
              <span style="color: var(--cyan-accent); font-size: 1.2rem;">⚡</span> OPTION A — Full Security Assessment
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
              Perform a comprehensive authorized security assessment across all supported vulnerability categories and relevant application components.
            </div>
            <div style="font-size: 0.74rem; color: var(--cyan-accent); font-weight: 600;">
              ✓ Automatically constructs an assessment plan tailored to detected technologies.
            </div>
          </div>

          <!-- Option B: Custom -->
          <div class="card" id="scope-option-custom" style="cursor: pointer; padding: 22px; border: 2px solid ${assessmentMode === "custom" ? "var(--primary)" : "var(--border-subtle)"}; background: ${assessmentMode === "custom" ? "rgba(139, 92, 246, 0.08)" : "rgba(255,255,255,0.02)"}; border-radius: var(--radius-lg); transition: all 0.2s ease;">
            <div style="display: flex; align-items: center; gap: 10px; font-weight: 800; color: #fff; font-size: 1.05rem; margin-bottom: 8px;">
              <span style="color: var(--primary); font-size: 1.2rem;">🎯</span> OPTION B — Custom Security Assessment
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
              Choose exactly what you want AegisTrace to investigate. Strict scope rules apply: unselected categories will be completely skipped.
            </div>
            <div style="font-size: 0.74rem; color: var(--primary); font-weight: 600;">
              ✓ Granular category selection (e.g. IDOR only, Deserialization only).
            </div>
          </div>
        </div>

        <!-- Custom Scope Category Selector (Visible when Custom is active) -->
        <div id="custom-scope-details" style="${assessmentMode === "custom" ? "display: block;" : "display: none;"} margin-bottom: 24px; padding: 20px; background: rgba(0,0,0,0.3); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);">
          <div style="font-weight: 700; color: #fff; font-size: 0.88rem; margin-bottom: 12px; display: flex; justify-content: space-between;">
            <span>Select Specific Vulnerability Vectors:</span>
            <span style="font-size: 0.74rem; color: var(--text-muted);">Strict Scope Enforcement</span>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            ${availableCategories.map(cat => `
              <label class="card" style="display: flex; align-items: flex-start; gap: 10px; padding: 12px; cursor: pointer; border: 1px solid ${selectedCategories.includes(cat.id) ? "rgba(139, 92, 246, 0.45)" : "rgba(255,255,255,0.06)"}; background: ${selectedCategories.includes(cat.id) ? "rgba(139, 92, 246, 0.08)" : "rgba(0,0,0,0.2)"}; border-radius: var(--radius-md);">
                <input type="checkbox" class="scope-cat-checkbox" value="${cat.id}" ${selectedCategories.includes(cat.id) ? "checked" : ""} style="margin-top: 3px; accent-color: #793BFF;">
                <div>
                  <div style="font-weight: 600; color: #fff; font-size: 0.82rem;">${cat.icon} ${cat.name}</div>
                  <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;">${cat.desc}</div>
                </div>
              </label>
            `).join("")}
          </div>

          <!-- Target Dir Filter -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px;">
            <div>
              <label style="display: block; font-size: 0.76rem; color: var(--text-muted); margin-bottom: 4px;">Target Directory Filter (Optional)</label>
              <input type="text" class="form-control" id="custom-target-dir" placeholder="e.g. backend/routers/" value="${targetDirFilter}" style="font-size: 0.82rem; padding: 8px 12px;">
            </div>
            <div>
              <label style="display: block; font-size: 0.76rem; color: var(--text-muted); margin-bottom: 4px;">Special Testing Instructions (Optional)</label>
              <input type="text" class="form-control" id="custom-instructions" placeholder="e.g. Focus on tenant_id verification" value="${customInstructions}" style="font-size: 0.82rem; padding: 8px 12px;">
            </div>
          </div>
        </div>

        <!-- Launch Button -->
        <div style="display: flex; justify-content: space-between; align-items: center; pt-3; border-top: 1px solid var(--border-subtle); padding-top: 20px;">
          <div style="font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono);">
            Scope: <strong style="color: #fff;">${assessmentMode.toUpperCase()}</strong> &bull; 
            Selected: <strong style="color: var(--cyan-accent);">${assessmentMode === "full" ? "All Vectors" : selectedCategories.length + " Categories"}</strong>
          </div>
          <button class="btn btn-primary btn-lg" id="btn-launch-assessment" style="padding: 14px 38px; font-size: 1rem; font-weight: 700; box-shadow: 0 0 25px rgba(139, 92, 246, 0.45); display: flex; align-items: center; gap: 10px;">
            <span>🚀</span> Launch Security Assessment
          </button>
        </div>
      </div>
    `;
  }

  function bindEvents() {
    const btnAnalyze = container.querySelector("#btn-analyze-repo");
    const repoInput = container.querySelector("#repo-url-input");

    if (btnAnalyze && repoInput) {
      btnAnalyze.onclick = async () => {
        const url = repoInput.value.trim();
        if (!url) {
          toast("Please enter a valid GitHub repository URL", "warning");
          return;
        }

        isAnalyzing = true;
        render();

        try {
          toast("Analyzing repository architecture & code structure...", "info");
          const report = await api.analyzeRepository(url, authToken || null);
          analysisReport = { ...(report || {}), repository_url: url };
          isAnalyzing = false;
          toast("Repository intelligence report ready!", "success");
          render();
        } catch (err) {
          isAnalyzing = false;
          toast(`Repository analysis failed: ${err.message}`, "error");
          render();
        }
      };

      repoInput.addEventListener("input", () => {
        initialUrl = repoInput.value;
        state.targetRepoUrl = initialUrl;
      });

      repoInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") btnAnalyze.click();
      });
    }

    container.querySelectorAll(".repo-preset-btn").forEach(btn => {
      btn.onclick = () => {
        const u = btn.getAttribute("data-url");
        if (repoInput && u) {
          repoInput.value = u;
          initialUrl = u;
          btnAnalyze.click();
        }
      };
    });

    const optFull = container.querySelector("#scope-option-full");
    const optCustom = container.querySelector("#scope-option-custom");
    if (optFull && optCustom) {
      optFull.onclick = () => {
        assessmentMode = "full";
        render();
      };
      optCustom.onclick = () => {
        assessmentMode = "custom";
        render();
      };
    }

    container.querySelectorAll(".scope-cat-checkbox").forEach(cb => {
      cb.onchange = () => {
        const val = cb.value;
        if (cb.checked && !selectedCategories.includes(val)) {
          selectedCategories.push(val);
        } else if (!cb.checked) {
          selectedCategories = selectedCategories.filter(c => c !== val);
        }
      };
    });

    const btnReanalyze = container.querySelector("#btn-reanalyze");
    if (btnReanalyze) {
      btnReanalyze.onclick = () => {
        analysisReport = null;
        render();
      };
    }

    const btnLaunch = container.querySelector("#btn-launch-assessment");
    if (btnLaunch) {
      btnLaunch.onclick = async () => {
        const typed = container.querySelector("#repo-url-input");
        const url = ((typed && typed.value) || analysisReport?.repository_url || initialUrl || "").trim();
        if (!url) {
          toast("Please specify a target repository", "warning");
          return;
        }

        if (assessmentMode === "custom" && selectedCategories.length === 0) {
          toast("Please select at least one vulnerability category for custom assessment", "warning");
          return;
        }

        toast("Initiating Autonomous 7-Agent Security Assessment...", "info");
        btnLaunch.disabled = true;
        btnLaunch.innerHTML = `<span class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span> Launching...`;

        try {
          const payload = {
            repository_url: url,
            project_name: analysisReport ? `${analysisReport.repository_name} Security Assessment` : "Repository Security Assessment",
            assessment_mode: assessmentMode,
            selected_categories: assessmentMode === "full" ? [] : selectedCategories,
            target_dir_filter: container.querySelector("#custom-target-dir") ? container.querySelector("#custom-target-dir").value.trim() : "",
            instructions: container.querySelector("#custom-instructions") ? container.querySelector("#custom-instructions").value.trim() : "",
            auth_token: authToken || null,
            active_testing_consented: true
          };

          const res = await api.createAssessment(payload);
          state.currentScanId = res.assessment_id || res.scan_id;
          toast("Assessment started! Connecting to live Agent Workspace...", "success");
          navigate("workspace");
        } catch (err) {
          btnLaunch.disabled = false;
          btnLaunch.innerHTML = `<span>🚀</span> Launch Security Assessment`;
          toast(`Failed to launch assessment: ${err.message}`, "error");
        }
      };
    }
  }

  render();

  // If a URL was passed from the landing page, automatically trigger analysis
  if (state.targetRepoUrl && !analysisReport && !isAnalyzing) {
    setTimeout(() => {
      const btn = container.querySelector("#btn-analyze-repo");
      if (btn) btn.click();
    }, 100);
  }
}
