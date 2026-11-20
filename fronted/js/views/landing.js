export function renderLanding(container, navigate) {
  container.innerHTML = `
    <!-- GSAP Luxury Pill Navigation -->
    <div class="pill-nav-wrapper" id="pill-nav-wrapper">
      <nav class="pill-nav-container" aria-label="AegisTrace Luxury Navigation">
        <!-- Rotating Logo on Hover -->
        <div class="pill-nav-logo" id="pill-nav-logo" title="AegisTrace — Autonomous Security Intelligence">
          AT
        </div>

        <!-- Pill Nav Items with GSAP Rising Background Circles -->
        <ul class="pill-nav-items" id="pill-nav-items">
          <li class="pill-nav-item active" data-route="landing">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Home</span>
              <span class="pill-label-hover">Home</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="code_intel">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Architecture</span>
              <span class="pill-label-hover">Architecture</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="surface">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Surface</span>
              <span class="pill-label-hover">Surface</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="findings">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Findings</span>
              <span class="pill-label-hover">Findings</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="finding_details">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Evidence</span>
              <span class="pill-label-hover">Evidence</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="verification">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Verification</span>
              <span class="pill-label-hover">Verification</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="remediation">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Remediation</span>
              <span class="pill-label-hover">Remediation</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="approvals">
            <span class="hover-circle"></span>
            <span class="label-stack">
              <span class="pill-label">Approvals</span>
              <span class="pill-label-hover">Approvals</span>
            </span>
          </li>
          <li class="pill-nav-item" data-route="dashboard" style="background: var(--gold-base); color: #0a0a0a; font-weight: 700;">
            <span class="hover-circle" style="background: #ffffff;"></span>
            <span class="label-stack">
              <span class="pill-label">Console &rarr;</span>
              <span class="pill-label-hover" style="color: #0a0a0a;">Console &rarr;</span>
            </span>
          </li>
        </ul>
      </nav>
    </div>

    <!-- Hero Stage with Interactive 3D Tubes Canvas Background -->
    <div class="hero-interactive-stage" id="hero-stage">
      <!-- 3D Interactive Neon Tubes Canvas -->
      <canvas id="tubes-cursor-canvas" class="tubes-bg-canvas"></canvas>

      <!-- Content Overlay -->
      <div style="position: relative; z-index: 2; width: 100%; max-width: 1240px; margin: 0 auto; padding: 120px 24px 60px 24px; text-align: center;">
        <!-- Live Status Pill -->
        <div style="display: flex; justify-content: center; margin-bottom: 28px;">
          <div class="live-pill">
            <span class="green-dot"></span>
            <span class="live-tag">LIVE</span>
            <span class="status-text">Autonomous AI Security Twin &bull; 0% False Positives</span>
          </div>
        </div>

        <!-- Editorial Headline with Playfair Display Italic and Gold Accents -->
        <h1 style="font-family: var(--font-serif); font-style: italic; font-size: clamp(2.8rem, 7.5vw, 5.8rem); font-weight: 700; line-height: 1.1; margin-bottom: 24px; letter-spacing: -1.5px; color: #FFFFFF; text-shadow: 0 0 35px rgba(0,0,0,0.8);">
          From Code Understanding to <br>
          <span style="color: var(--gold-base); text-shadow: 0 0 30px rgba(167, 139, 113, 0.4);">Verified Security Remediation</span>.
        </h1>

        <p style="font-family: var(--font-sans); font-size: 1.15rem; color: var(--gold-light); max-width: 760px; margin: 0 auto 36px auto; font-weight: 400; line-height: 1.7; text-shadow: 0 2px 10px rgba(0,0,0,0.8);">
          A sophisticated neural orchestration mesh of 7 autonomous AI agents that analyze ASTs, trap live database mutations with cryptographic state hashes, and synthesize verified patches.
        </p>

        <!-- Dual Button CTA Group -->
        <div style="display: flex; gap: 18px; justify-content: center; align-items: center; margin-bottom: 70px;">
          <button class="btn btn-white btn-lg" id="hero-btn-start" style="padding: 14px 34px; font-size: 0.92rem; box-shadow: 0 8px 30px rgba(255,255,255,0.25);">
            Start Free Assessment
          </button>
          <button class="btn btn-secondary btn-lg" id="hero-btn-explore" style="padding: 14px 34px; font-size: 0.92rem; background: rgba(10,10,10,0.7); backdrop-filter: blur(12px);">
            Explore Live Workspace
          </button>
          <button class="btn btn-primary btn-lg" id="hero-btn-console" style="padding: 14px 34px; font-size: 0.92rem;">
            Open Console &rarr;
          </button>
        </div>

        <!-- Central Interactive Node with Connected Satellite Cards -->
        <div class="hero-neural-stage" id="hero-neural-stage">
          <!-- Central Glow & SVG Neural Canvas -->
          <svg class="neural-canvas" viewBox="0 0 1000 660">
            <!-- Dynamic SVG Bezier Curves -->
            <path d="M 500 330 C 350 240, 250 150, 160 140" class="node-line"/>
            <path d="M 500 330 C 350 240, 250 150, 160 140" class="node-line-dashed"/>

            <path d="M 500 330 C 650 240, 750 150, 840 140" class="node-line"/>
            <path d="M 500 330 C 650 240, 750 150, 840 140" class="node-line-dashed"/>

            <path d="M 500 330 C 350 420, 250 510, 160 520" class="node-line"/>
            <path d="M 500 330 C 350 420, 250 510, 160 520" class="node-line-dashed"/>

            <path d="M 500 330 C 650 420, 750 510, 840 520" class="node-line"/>
            <path d="M 500 330 C 650 420, 750 510, 840 520" class="node-line-dashed"/>
          </svg>

          <!-- Floating Satellites Wrap -->
          <div class="hero-satellites-wrap">
            <!-- Floating Satellite Left Top -->
            <div class="satellite-card sat-top-left" id="sat-card-1">
              <div class="satellite-img-wrapper">
                <img src="/static/assets/satellite_ast.jpg" alt="Invariant Synthesis" class="satellite-img">
              </div>
              <div class="satellite-title">Invariant Synthesis</div>
              <div class="satellite-role">AGENT 02 &bull; CODE INTEL</div>
            </div>

            <!-- Floating Satellite Right Top -->
            <div class="satellite-card sat-top-right" id="sat-card-2">
              <div class="satellite-img-wrapper">
                <img src="/static/assets/satellite_exploit.jpg" alt="State Mutation Proof" class="satellite-img">
              </div>
              <div class="satellite-title">State Mutation Proof</div>
              <div class="satellite-role">AGENT 05 &bull; DYNAMIC TEST</div>
            </div>

            <!-- Floating Satellite Left Bottom -->
            <div class="satellite-card sat-bottom-left" id="sat-card-3">
              <div class="satellite-img-wrapper">
                <img src="/static/assets/satellite_evidence.jpg" alt="Forensic Arbitration" class="satellite-img">
              </div>
              <div class="satellite-title">Forensic Arbitration</div>
              <div class="satellite-role">AGENT 06 &bull; EVIDENCE STORE</div>
            </div>

            <!-- Floating Satellite Right Bottom -->
            <div class="satellite-card sat-bottom-right" id="sat-card-4">
              <div class="satellite-img-wrapper">
                <img src="/static/assets/satellite_patch.jpg" alt="AST Patch Synthesis" class="satellite-img">
              </div>
              <div class="satellite-title">AST Patch Synthesis</div>
              <div class="satellite-role">AGENT 07 &bull; REMEDIATION</div>
            </div>
          </div>

          <!-- Central Core 16:9 Glass Node -->
          <div class="central-node" id="central-core-node" style="cursor: pointer;">
            <img src="/static/assets/hero_neural_core.jpg" alt="Neural Core" class="central-node-img">
            <div class="central-node-overlay">
              <div class="central-node-badge">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--gold-base);"></span>
                AegisCore Neural Orchestrator
              </div>
              <div style="font-size: 1.25rem; font-weight: 700; color: #fff; font-family: var(--font-serif); font-style: italic; margin-top: 8px;">
                Autonomous Security Intelligence Mesh
              </div>
              <div style="font-size: 0.78rem; color: var(--gold-light); margin-top: 4px;">
                Click to Open Interactive Agent Workspace &rarr;
              </div>
            </div>
          </div>
        </div>

        <!-- Tubes Interaction Hint -->
        <div style="display: flex; justify-content: center; margin-top: 40px;">
          <div class="tubes-randomize-hint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
            <span>Move cursor to guide 3D neon tubes &bull; Click anywhere to randomize colors</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Features Section (4 Columns) -->
    <section id="features" style="max-width: 1240px; margin: 0 auto; padding: 100px 24px;">
      <div style="text-align: center; margin-bottom: 64px;">
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--gold-base); margin-bottom: 12px;">
          Autonomous Architecture
        </div>
        <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 2.8rem; font-weight: 700; color: #fff;">
          Built for Ground-Truth Determinism
        </h2>
        <p style="color: var(--gold-light); font-size: 1rem; max-width: 600px; margin: 12px auto 0 auto;">
          Every stage of the vulnerability lifecycle is audited, verified in isolated sandboxes, and mathematically bounded.
        </p>
      </div>

      <div class="feature-grid">
        <div class="feature-card" data-goto="code_intel" style="cursor: pointer;">
          <div class="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </div>
          <div class="feature-title">AST Semantic Invariants</div>
          <div class="feature-desc">
            Deep static parsing extracts access-control constraints, ownership invariants, and data-flow trees directly from source code.
          </div>
        </div>

        <div class="feature-card" data-goto="surface" style="cursor: pointer;">
          <div class="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          </div>
          <div class="feature-title">ScopeGate Authorization</div>
          <div class="feature-desc">
            Dynamic reconnaissance enforces strict domain, method, and rate-limit guardrails ensuring zero out-of-scope testing.
          </div>
        </div>

        <div class="feature-card" data-goto="finding_details" style="cursor: pointer;">
          <div class="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <div class="feature-title">Cryptographic State Diffing</div>
          <div class="feature-desc">
            Vulnerabilities are confirmed only when pre/post database mutation hashes prove unauthorized cross-tenant data alteration.
          </div>
        </div>

        <div class="feature-card" data-goto="remediation" style="cursor: pointer;">
          <div class="feature-icon-wrapper">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
          </div>
          <div class="feature-title">AST Patch Synthesis</div>
          <div class="feature-desc">
            RemediationAgent generates precise AST patches in isolated git worktrees, validated through automated unit test suites and exploit closure.
          </div>
        </div>
      </div>
    </section>

    <!-- Pricing Section (3 Tiers) -->
    <section id="pricing" style="max-width: 1240px; margin: 0 auto; padding: 100px 24px;">
      <div style="text-align: center; margin-bottom: 50px;">
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--gold-base); margin-bottom: 12px;">
          Subscription & Licensing
        </div>
        <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 2.8rem; font-weight: 700; color: #fff;">
          Enterprise Defense Tiers
        </h2>
        <p style="color: var(--gold-light); font-size: 1rem; max-width: 500px; margin: 12px auto 30px auto;">
          Deterministic security intelligence tailored for high-velocity software engineering organizations.
        </p>

        <!-- Billing Toggle Pill -->
        <div class="pricing-toggle-wrapper">
          <div class="pricing-toggle-pill active" id="toggle-monthly">Monthly</div>
          <div class="pricing-toggle-pill" id="toggle-annual">Annual (Save 20%)</div>
        </div>
      </div>

      <div class="pricing-grid">
        <!-- Starter Tier -->
        <div class="pricing-card">
          <div class="pricing-tier-name">Developer</div>
          <div class="pricing-price" id="price-starter">$4,900</div>
          <div class="pricing-period">per month</div>
          <p style="font-size: 0.82rem; color: var(--gold-light); margin-top: 14px; margin-bottom: 24px;">
            For agile development teams needing autonomous PR verification and AST invariant checks.
          </p>
          <ul class="pricing-features">
            <li>5 Target Applications / Repositories</li>
            <li>Continuous Invariant Synthesis</li>
            <li>Single-Tenant Sandbox Jails</li>
            <li>Standard GitHub PR Integration</li>
          </ul>
          <button class="btn btn-secondary btn-full" id="btn-tier-dev">Select Tier</button>
        </div>

        <!-- Pro Tier (Highlighted) -->
        <div class="pricing-card highlighted">
          <div class="popular-badge">MOST POPULAR</div>
          <div class="pricing-tier-name">Enterprise Core</div>
          <div class="pricing-price" id="price-pro">$14,500</div>
          <div class="pricing-period">per month</div>
          <p style="font-size: 0.82rem; color: var(--gold-light); margin-top: 14px; margin-bottom: 24px;">
            Full autonomous 7-agent mesh with live database state mutation verification and AST repair.
          </p>
          <ul class="pricing-features">
            <li>Unlimited Repositories & Scans</li>
            <li>7-Agent Autonomous Pipeline</li>
            <li>3x Isolated Sandbox Arbitration</li>
            <li>Cryptographic SHA-256 Vault</li>
            <li>Human Approval Dual-Key Gate</li>
          </ul>
          <button class="btn btn-primary btn-full" id="btn-tier-enterprise">Get Enterprise Access</button>
        </div>

        <!-- Custom Sovereign Tier -->
        <div class="pricing-card">
          <div class="pricing-tier-name">Sovereign Air-Gapped</div>
          <div class="pricing-price">Custom</div>
          <div class="pricing-period">dedicated deployment</div>
          <p style="font-size: 0.82rem; color: var(--gold-light); margin-top: 14px; margin-bottom: 24px;">
            Self-hosted on-premise installation with zero outbound data telemetry for regulated sectors.
          </p>
          <ul class="pricing-features">
            <li>Air-Gapped Local LLM Inference</li>
            <li>Dedicated Security Engineer Support</li>
            <li>Custom Invariant Domain Rules</li>
            <li>SOC2 / ISO 27001 Certification</li>
          </ul>
          <button class="btn btn-secondary btn-full" id="btn-tier-custom">Contact Architects</button>
        </div>
      </div>
    </section>

    <!-- Team Section (2 Columns) -->
    <section id="team" style="max-width: 1240px; margin: 0 auto; padding: 100px 24px;">
      <div style="text-align: center; margin-bottom: 60px;">
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: var(--gold-base); margin-bottom: 12px;">
          Research & Systems Leadership
        </div>
        <h2 style="font-family: var(--font-serif); font-style: italic; font-size: 2.8rem; font-weight: 700; color: #fff;">
          The Architecture Team
        </h2>
      </div>

      <div class="team-grid">
        <div class="team-card">
          <div class="team-img-wrapper">
            <img src="/static/assets/team_architect.jpg" alt="Dr. Alexander Vance" class="team-img">
          </div>
          <div class="team-info">
            <div class="team-name">Dr. Alexander Vance</div>
            <div class="team-role">PRINCIPAL SECURITY SYSTEMS ARCHITECT</div>
            <p style="font-size: 0.82rem; color: var(--gold-light); line-height: 1.6; margin-top: 10px;">
              Former Lead Systems Researcher at DeepMind Advanced Agentic Coding. Specialized in formal program verification, AST rewriting, and invariant synthesis.
            </p>
          </div>
        </div>

        <div class="team-card">
          <div class="team-img-wrapper">
            <img src="/static/assets/team_director.jpg" alt="Elena Rostova" class="team-img">
          </div>
          <div class="team-info">
            <div class="team-name">Elena Rostova</div>
            <div class="team-role">VP OF AUTONOMOUS CYBER DEFENSE</div>
            <p style="font-size: 0.82rem; color: var(--gold-light); line-height: 1.6; margin-top: 10px;">
              Pioneered zero-false-positive differential state mutation fuzzing. Oversees the 7-agent neural mesh and EvidenceStore cryptographic arbitrations.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer (5 Columns) -->
    <footer class="footer">
      <div class="footer-grid">
        <!-- Col 1: Brand & Bio -->
        <div>
          <div class="footer-brand">
            Aegis<span class="brand-gold">Trace</span>
          </div>
          <p class="footer-bio">
            Autonomous Application Security Intelligence & Verified Remediation Platform. Delivering zero false positives through cryptographic mutation verification.
          </p>
          <div class="social-links">
            <a href="#" class="social-icon">𝕏</a>
            <a href="#" class="social-icon">GH</a>
            <a href="#" class="social-icon">in</a>
          </div>
        </div>

        <!-- Col 2: Platform Links -->
        <div class="footer-links-col">
          <div class="footer-links-title">Core Operations</div>
          <ul class="footer-links">
            <li><a class="footer-link" data-route="dashboard">Overview Console</a></li>
            <li><a class="footer-link" data-route="projects">Projects Catalog</a></li>
            <li><a class="footer-link" data-route="wizard">New Assessment</a></li>
            <li><a class="footer-link" data-route="workspace">Agent Pipeline</a></li>
          </ul>
        </div>

        <!-- Col 3: Intelligence Links -->
        <div class="footer-links-col">
          <div class="footer-links-title">Intelligence</div>
          <ul class="footer-links">
            <li><a class="footer-link" data-route="code_intel">Code Intelligence</a></li>
            <li><a class="footer-link" data-route="surface">Attack Surface</a></li>
            <li><a class="footer-link" data-route="findings">Findings Ledger</a></li>
            <li><a class="footer-link" data-route="finding_details">Forensic Evidence</a></li>
            <li><a class="footer-link" data-route="verification">Verification Center</a></li>
          </ul>
        </div>

        <!-- Col 4: Remediation Links -->
        <div class="footer-links-col">
          <div class="footer-links-title">Remediation</div>
          <ul class="footer-links">
            <li><a class="footer-link" data-route="remediation">AST Patch Studio</a></li>
            <li><a class="footer-link" data-route="approvals">Human Approvals</a></li>
            <li><a class="footer-link" data-route="reports">Compliance Audit</a></li>
            <li><a class="footer-link" data-route="skills">Skills Library</a></li>
            <li><a class="footer-link" data-route="benchmarks">Benchmark Matrix</a></li>
          </ul>
        </div>

        <!-- Col 5: Digest -->
        <div>
          <div class="footer-links-title">Security Digest</div>
          <p style="font-size: 0.8rem; color: var(--gold-light); margin-bottom: 14px; line-height: 1.5;">
            Quarterly disclosures on zero-day invariant synthesis and autonomous remediation research.
          </p>
          <div class="digest-form">
            <input type="email" placeholder="security@enterprise.com" class="digest-input">
            <button class="digest-btn">&rarr;</button>
          </div>
        </div>
      </div>

      <div class="footer-bottom">
        <div>&copy; 2026 AegisTrace Autonomous Intelligence Inc. All rights reserved.</div>
        <div style="display: flex; gap: 20px;">
          <a class="footer-link" data-route="supporting">Supporting Screens & Logs</a>
          <a class="footer-link" data-route="settings">Settings</a>
          <a class="footer-link" data-route="auth">Operator Login</a>
        </div>
      </div>
    </footer>
  `;

  // -------------------------------------------------------------
  // 1. Initialize GSAP PillNav Component
  // -------------------------------------------------------------
  initPillNav(navigate);

  // -------------------------------------------------------------
  // 2. Initialize 3D Interactive Neon Tubes Background
  // -------------------------------------------------------------
  initTubesBackground();

  // -------------------------------------------------------------
  // 3. Bind CTA Buttons and Navigation Links
  // -------------------------------------------------------------
  document.getElementById("hero-btn-start")?.addEventListener("click", () => navigate("wizard"));
  document.getElementById("hero-btn-explore")?.addEventListener("click", () => navigate("workspace"));
  document.getElementById("hero-btn-console")?.addEventListener("click", () => navigate("dashboard"));
  document.getElementById("central-core-node")?.addEventListener("click", () => navigate("workspace"));

  document.getElementById("sat-card-1")?.addEventListener("click", () => navigate("code_intel"));
  document.getElementById("sat-card-2")?.addEventListener("click", () => navigate("finding_details"));
  document.getElementById("sat-card-3")?.addEventListener("click", () => navigate("verification"));
  document.getElementById("sat-card-4")?.addEventListener("click", () => navigate("remediation"));

  container.querySelectorAll(".feature-card").forEach(c => {
    c.addEventListener("click", (e) => {
      const route = e.currentTarget.getAttribute("data-goto");
      if (route) navigate(route);
    });
  });

  document.getElementById("btn-tier-dev")?.addEventListener("click", () => navigate("wizard"));
  document.getElementById("btn-tier-enterprise")?.addEventListener("click", () => navigate("wizard"));
  document.getElementById("btn-tier-custom")?.addEventListener("click", () => navigate("settings"));

  // Footer navigation links
  container.querySelectorAll(".footer-link").forEach(l => {
    l.addEventListener("click", (e) => {
      const r = e.currentTarget.getAttribute("data-route");
      if (r) navigate(r);
    });
  });

  // Pricing monthly/annual toggle
  const tMonthly = document.getElementById("toggle-monthly");
  const tAnnual = document.getElementById("toggle-annual");
  const pStarter = document.getElementById("price-starter");
  const pPro = document.getElementById("price-pro");

  tMonthly?.addEventListener("click", () => {
    tMonthly.classList.add("active");
    tAnnual.classList.remove("active");
    if (pStarter) pStarter.innerText = "$4,900";
    if (pPro) pPro.innerText = "$14,500";
  });

  tAnnual?.addEventListener("click", () => {
    tAnnual.classList.add("active");
    tMonthly.classList.remove("active");
    if (pStarter) pStarter.innerText = "$3,920";
    if (pPro) pPro.innerText = "$11,600";
  });
}

// ---------------------------------------------------------------------------
// GSAP PillNav Component Implementation with Rising Circle Animations
// ---------------------------------------------------------------------------
function initPillNav(navigate) {
  const logo = document.getElementById("pill-nav-logo");
  const items = document.querySelectorAll(".pill-nav-item");

  // Rotating logo on hover via GSAP
  logo?.addEventListener("mouseenter", () => {
    if (window.gsap) {
      window.gsap.to(logo, {
        rotate: 360,
        duration: 0.8,
        ease: "elastic.out(1, 0.5)",
        overwrite: "auto",
        onComplete: () => window.gsap.set(logo, { rotate: 0 })
      });
    }
  });

  logo?.addEventListener("click", () => navigate("landing"));

  // Layout and rising circle hover timelines for each pill
  items.forEach((pill) => {
    const circle = pill.querySelector(".hover-circle");
    const label = pill.querySelector(".pill-label");
    const labelHover = pill.querySelector(".pill-label-hover");

    const setupPillTimeline = () => {
      if (!circle || !window.gsap) return;
      const rect = pill.getBoundingClientRect();
      const w = rect.width || 80;
      const h = rect.height || 36;

      const R = ((w * w) / 4 + h * h) / (2 * h);
      const D = Math.ceil(2 * R) + 2;
      const delta = Math.ceil(R - Math.sqrt(Math.max(0, R * R - (w * w) / 4))) + 1;
      const originY = D - delta;

      circle.style.width = `${D}px`;
      circle.style.height = `${D}px`;
      circle.style.bottom = `-${delta}px`;

      window.gsap.set(circle, {
        xPercent: -50,
        scale: 0,
        transformOrigin: `50% ${originY}px`
      });

      if (label) window.gsap.set(label, { y: 0 });
      if (labelHover) window.gsap.set(labelHover, { y: h + 10, opacity: 0 });

      const tl = window.gsap.timeline({ paused: true });
      tl.to(circle, { scale: 1.25, xPercent: -50, duration: 0.6, ease: "power3.out" }, 0);
      if (label) tl.to(label, { y: -(h + 6), duration: 0.5, ease: "power3.out" }, 0);
      if (labelHover) tl.to(labelHover, { y: 0, opacity: 1, duration: 0.5, ease: "power3.out" }, 0);

      pill._tl = tl;
    };

    setupPillTimeline();

    pill.addEventListener("mouseenter", () => {
      if (pill._tl) pill._tl.play();
    });

    pill.addEventListener("mouseleave", () => {
      if (pill._tl) pill._tl.reverse();
    });

    pill.addEventListener("click", (e) => {
      const route = e.currentTarget.getAttribute("data-route");
      if (route) navigate(route);
    });
  });

  // Initial load stagger entrance animation
  if (window.gsap) {
    window.gsap.from(items, {
      opacity: 0,
      y: -15,
      duration: 0.6,
      stagger: 0.04,
      ease: "power2.out",
      delay: 0.1
    });

    if (logo) {
      window.gsap.from(logo, {
        scale: 0,
        opacity: 0,
        duration: 0.7,
        ease: "back.out(1.8)"
      });
    }
  }
}

// ---------------------------------------------------------------------------
// 3D Interactive Neon Tubes Cursor Background
// ---------------------------------------------------------------------------
function initTubesBackground() {
  const canvas = document.getElementById("tubes-cursor-canvas");
  const stage = document.getElementById("hero-stage");
  if (!canvas || !stage) return;

  // Gold luxury color palettes for tubes & lights
  const goldPalettes = [
    { tubes: ["#c9b8a0", "#a78b71", "#e8d5b7"], lights: ["#e8d5b7", "#c9b8a0", "#a78b71", "#ffffff"] },
    { tubes: ["#f59e0b", "#d97706", "#b45309"], lights: ["#fef3c7", "#fbbf24", "#d97706", "#ffffff"] },
    { tubes: ["#38efbd", "#10b981", "#a78b71"], lights: ["#6ee7b7", "#38efbd", "#c9b8a0", "#ffffff"] },
    { tubes: ["#c49fff", "#8b5cf6", "#e8d5b7"], lights: ["#ddd6fe", "#a78b71", "#c49fff", "#ffffff"] }
  ];

  let currentPaletteIdx = 0;
  let tubesApp = null;

  // Try loading official threejs-components TubesCursor from CDN
  const loadCdnTubes = async () => {
    try {
      const module = await import("https://cdn.jsdelivr.net/npm/threejs-components@0.0.19/build/cursors/tubes1.min.js");
      const TubesCursor = module.default;
      const initial = goldPalettes[0];

      tubesApp = TubesCursor(canvas, {
        tubes: {
          colors: initial.tubes,
          lights: {
            intensity: 220,
            colors: initial.lights
          }
        }
      });
    } catch (err) {
      console.warn("Using high-performance WebGL/Canvas interactive fallback for 3D tubes:", err);
      initFallback3DTubes(canvas, stage);
    }
  };

  loadCdnTubes();

  // Click interaction: Randomize / cycle colors instantly
  stage.addEventListener("click", (e) => {
    // Only trigger if not clicking buttons or interactive links
    if (e.target.closest("button") || e.target.closest("a") || e.target.closest(".pill-nav-container") || e.target.closest(".satellite-card") || e.target.closest(".central-node")) {
      return;
    }

    currentPaletteIdx = (currentPaletteIdx + 1) % goldPalettes.length;
    const pal = goldPalettes[currentPaletteIdx];

    if (tubesApp && tubesApp.tubes) {
      if (tubesApp.tubes.setColors) tubesApp.tubes.setColors(pal.tubes);
      if (tubesApp.tubes.setLightsColors) tubesApp.tubes.setLightsColors(pal.lights);
    } else if (window.__randomizeFallbackTubes) {
      window.__randomizeFallbackTubes(pal.tubes);
    }
  });
}

// ---------------------------------------------------------------------------
// High-Performance Interactive Fallback Canvas (3D Cursor Ribbons & Gold Tubes)
// ---------------------------------------------------------------------------
function initFallback3DTubes(canvas, container) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let width = (canvas.width = container.offsetWidth || window.innerWidth);
  let height = (canvas.height = container.offsetHeight || window.innerHeight);

  const onResize = () => {
    width = canvas.width = container.offsetWidth || window.innerWidth;
    height = canvas.height = container.offsetHeight || window.innerHeight;
  };
  window.addEventListener("resize", onResize);

  let mouse = { x: width / 2, y: height / 2, px: width / 2, py: height / 2, speed: 0 };
  let points = [];
  const maxPoints = 55;

  let activeColors = ["#c9b8a0", "#a78b71", "#e8d5b7"];
  window.__randomizeFallbackTubes = (newColors) => {
    activeColors = newColors;
  };

  container.addEventListener("mousemove", (e) => {
    const rect = container.getBoundingClientRect();
    const nx = e.clientX - rect.left;
    const ny = e.clientY - rect.top;
    const dx = nx - mouse.x;
    const dy = ny - mouse.y;
    mouse.speed = Math.sqrt(dx * dx + dy * dy);
    mouse.px = mouse.x;
    mouse.py = mouse.y;
    mouse.x = nx;
    mouse.y = ny;

    points.push({
      x: mouse.x,
      y: mouse.y,
      vx: dx * 0.1,
      vy: dy * 0.1,
      age: 0,
      width: Math.min(32, Math.max(8, mouse.speed * 0.6))
    });

    if (points.length > maxPoints) points.shift();
  });

  let animFrameId = null;
  function animate() {
    ctx.clearRect(0, 0, width, height);

    if (points.length > 2) {
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      for (let i = 1; i < points.length; i++) {
        const p0 = points[i - 1];
        const p1 = points[i];
        p1.age += 1;

        const progress = i / points.length;
        const color = activeColors[i % activeColors.length];

        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);

        ctx.strokeStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 18;
        ctx.lineWidth = p1.width * progress;
        ctx.globalAlpha = progress * 0.85;
        ctx.stroke();
      }
      ctx.globalAlpha = 1.0;
      ctx.shadowBlur = 0;
    }

    animFrameId = requestAnimationFrame(animate);
  }

  animate();
}
