export async function renderSkills(container, navigate, state, api, showModal) {
  let skills = [];
  try {
    skills = await api.listSkills();
  } catch (e) {
    console.warn("Failed to load skills:", e);
  }

  // Fallback skills if needed
  if (!skills || skills.length === 0) {
    skills = [
      {
        id: "skl_bola_jwt",
        name: "Dual-Token BOLA Invariant Hunter",
        category: "Access Control",
        description: "Specialized knowledge pack for detecting Broken Object Level Authorization using asynchronous dual-tenant JWT role rotation and mutated resource ID replay.",
        supported_cwes: ["CWE-639", "CWE-284"],
        compatible_agents: ["VulnResearchAgent", "DynamicTestingAgent", "VerificationAgent"],
        sandbox_tested: true,
        complexity: "Advanced"
      },
      {
        id: "skl_mass_assign",
        name: "AST Mass Assignment Mutation",
        category: "Access Control",
        description: "Extracts ORM schema fields from AST definitions and synthesizes payloads injecting privileged attributes (e.g., is_admin, role, balance).",
        supported_cwes: ["CWE-915"],
        compatible_agents: ["VulnResearchAgent", "DynamicTestingAgent"],
        sandbox_tested: true,
        complexity: "Intermediate"
      },
      {
        id: "skl_race_condition",
        name: "Concurrent Limit-Overrun Hunter",
        category: "Business Logic",
        description: "Fires synchronized HTTP/2 multiplexed bursts to exploit TOCTOU race windows in coupon applications and financial transfers.",
        supported_cwes: ["CWE-362"],
        compatible_agents: ["DynamicTestingAgent"],
        sandbox_tested: true,
        complexity: "Advanced"
      },
      {
        id: "skl_ssrf_egress",
        name: "Cloud Metadata Blind SSRF Trap",
        category: "Server-Side",
        description: "Detects internal network pivoting through webhook endpoints, cloud provider 169.254.169.254 metadata calls, and DNS rebinding.",
        supported_cwes: ["CWE-918"],
        compatible_agents: ["DynamicTestingAgent", "VerificationAgent"],
        sandbox_tested: true,
        complexity: "Expert"
      },
      {
        id: "skl_idor_numeric",
        name: "Sequential Resource IDOR Sweeper",
        category: "Access Control",
        description: "Identifies sequential numeric identifiers across REST endpoints and validates resource isolation across non-privileged tenants.",
        supported_cwes: ["CWE-639"],
        compatible_agents: ["DynamicTestingAgent"],
        sandbox_tested: true,
        complexity: "Standard"
      },
      {
        id: "skl_crypto_weak_token",
        name: "JWT Algorithm Confusion Analyzer",
        category: "Cryptography",
        description: "Analyzes asymmetric to symmetric (RS256 to HS256) signature algorithm confusion and null signature vulnerabilities.",
        supported_cwes: ["CWE-327", "CWE-347"],
        compatible_agents: ["VulnResearchAgent", "VerificationAgent"],
        sandbox_tested: true,
        complexity: "Advanced"
      }
    ];
  }

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-base); font-weight: 700; margin-bottom: 6px;">
            Modular Offensive & Defensive Intelligence Packs
          </div>
          <h1 class="page-title">BugHunter Skills Library</h1>
          <p class="page-subtitle">Curated offensive & verification knowledge packs routed dynamically by VulnResearchAgent and DynamicTestingAgent.</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <input type="text" class="form-control" id="skills-search" placeholder="Search skills or CWEs..." style="width: 260px; padding: 8px 16px; font-size: 0.84rem;">
          <div class="badge badge-gold" style="padding: 8px 14px; font-size: 0.76rem;">
            ${skills.length} Loaded Packs
          </div>
        </div>
      </div>

      <!-- Categories Filter Bar -->
      <div style="display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap;">
        <button class="btn btn-outline btn-sm filter-skill-cat active" data-cat="ALL">ALL CATEGORIES</button>
        <button class="btn btn-outline btn-sm filter-skill-cat" data-cat="Access Control">Access Control</button>
        <button class="btn btn-outline btn-sm filter-skill-cat" data-cat="Business Logic">Business Logic</button>
        <button class="btn btn-outline btn-sm filter-skill-cat" data-cat="Cryptography">Cryptography</button>
        <button class="btn btn-outline btn-sm filter-skill-cat" data-cat="Server-Side">Server-Side</button>
      </div>

      <!-- Skills Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px;" id="skills-grid">
        ${skills.map((sk, idx) => `
          <div class="card card-glass skill-card" data-cat="${sk.category}" data-search="${sk.name.toLowerCase()} ${sk.description.toLowerCase()} ${(sk.supported_cwes || []).join(' ').toLowerCase()}" style="display: flex; flex-direction: column; justify-content: space-between; border-radius: var(--radius-lg); transition: all 0.3s ease;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <h3 style="font-size: 1.12rem; font-weight: 700; color: #fff; font-family: 'Playfair Display', serif; font-style: italic;">
                  ${sk.name}
                </h3>
                <span class="badge ${sk.category === 'Access Control' ? 'badge-gold' : 'badge-bronze'}">
                  ${sk.category}
                </span>
              </div>
              <p style="font-size: 0.82rem; color: var(--gold-light); line-height: 1.6; margin-bottom: 16px;">
                ${sk.description}
              </p>
            </div>

            <div>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 12px; margin-bottom: 12px;">
                <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Supported CWEs</div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                  ${(sk.supported_cwes || []).map(cwe => `
                    <span class="badge badge-gold-subtle" style="font-size: 0.68rem; font-family: monospace;">${cwe}</span>
                  `).join("")}
                </div>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
                <div style="font-size: 0.72rem; color: var(--text-muted);">
                  Agents: <code style="color: var(--gold-base);">${(sk.compatible_agents || []).slice(0, 2).join(", ")}</code>
                </div>
                <button class="btn btn-secondary btn-sm btn-simulate-skill" data-idx="${idx}" style="padding: 4px 10px; font-size: 0.72rem;">
                  Simulate Pack
                </button>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;

  // Search filter
  const searchInput = document.getElementById("skills-search");
  searchInput?.addEventListener("input", (e) => {
    const val = e.target.value.toLowerCase();
    container.querySelectorAll(".skill-card").forEach(card => {
      const txt = card.getAttribute("data-search");
      card.style.display = txt.includes(val) ? "flex" : "none";
    });
  });

  // Category filter
  container.querySelectorAll(".filter-skill-cat").forEach(btn => {
    btn.addEventListener("click", (e) => {
      container.querySelectorAll(".filter-skill-cat").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      const cat = e.currentTarget.getAttribute("data-cat");
      container.querySelectorAll(".skill-card").forEach(card => {
        const cardCat = card.getAttribute("data-cat");
        card.style.display = (cat === "ALL" || cat === cardCat) ? "flex" : "none";
      });
    });
  });

  // Simulate skill modal
  container.querySelectorAll(".btn-simulate-skill").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const idx = parseInt(e.currentTarget.getAttribute("data-idx"), 10);
      const sk = skills[idx];
      if (!sk || !showModal) return;

      showModal({
        title: `Sandbox Simulation — ${sk.name}`,
        bodyHtml: `
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div style="background: rgba(167, 139, 113, 0.08); border: 1px solid var(--border-gold); padding: 14px; border-radius: var(--radius-md);">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--gold-base); font-weight: 700;">Simulated Skill Pack</div>
              <div style="color: #fff; font-size: 0.95rem; font-weight: 700; margin-top: 4px;">${sk.name} (${sk.id})</div>
              <div style="font-size: 0.8rem; color: var(--gold-light); margin-top: 4px;">${sk.description}</div>
            </div>

            <div style="background: #050505; border: 1px solid var(--border-subtle); padding: 14px; border-radius: var(--radius-sm); font-family: monospace; font-size: 0.76rem; color: #d1d5db; line-height: 1.5;">
              <div style="color: var(--gold-base); font-weight: 700;">// Dispatching knowledge pack to DynamicTestingAgent...</div>
              <div style="color: #38efbd;">[OK] Sandbox environment initialized (Isolation: sbx_sim_01)</div>
              <div style="color: #38efbd;">[OK] Synthetic dual-tenant identities generated (token_a, token_b)</div>
              <div style="color: var(--gold-light);">[RUN] Probing invariant rules against target parameter models...</div>
              <div style="color: #38efbd;">[SUCCESS] Skill ready for deployment in autonomous assessments.</div>
            </div>
          </div>
        `,
        confirmText: "Close"
      });
    });
  });
}
