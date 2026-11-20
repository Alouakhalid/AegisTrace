export async function renderSkills(container, navigate, state, api, showModal) {
  let skills = [];
  let skillsInstalled = false;
  try {
    const res = await api.listSkills();
    if (Array.isArray(res)) {
      skills = res;
      skillsInstalled = skills.length > 0;
    } else if (res && typeof res === "object") {
      skills = res.skills || [];
      skillsInstalled = res.skills_installed !== undefined ? res.skills_installed : skills.length > 0;
    }
  } catch (e) {
    console.warn("Failed to load skills:", e);
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
        ${skills.length === 0 ? `
          <div class="card card-glass" style="grid-column: 1 / -1; padding: 48px; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 14px;">📦</div>
            <h3 style="font-size: 1.25rem; font-weight: 700; color: #fff; margin-bottom: 8px;">No Skills Installed</h3>
            <p style="font-size: 0.88rem; color: var(--gold-light); max-width: 600px; margin: 0 auto 20px auto; line-height: 1.6;">
              BugHunter intelligence packs are loaded dynamically from <code>skills/Claude-BugHunter/skills/*/SKILL.md</code>.
              Populate the directory or copy Claude-BugHunter into <code>skills/Claude-BugHunter</code> to activate automated heuristic matching.
            </p>
          </div>
        ` : skills.map((sk, idx) => `
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
