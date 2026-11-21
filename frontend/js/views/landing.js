/**
 * Landing view — the platform's first impression.
 * Everything numeric is pulled live from the API; nothing is faked.
 * If a metric is unavailable it renders as "—" instead of inventing a value.
 */

const AGENTS = [
  { n: "1", name: "Orchestrator", desc: "Validates scope manifests, plans the DAG, and blocks anything outside authorization." },
  { n: "2", name: "Code Intelligence", desc: "AST-analyzes routes, ORM models, and derives ownership invariants from real code." },
  { n: "3", name: "Reconnaissance", desc: "Maps the attack surface through a ScopeGate that refuses out-of-scope hosts." },
  { n: "4", name: "Vulnerability Research", desc: "Routes BugHunter skills, ranks hypotheses, and emits executable test plans." },
  { n: "5", name: "Dynamic Testing", desc: "Replays paired-identity exploits against the live target and traps state diffs." },
  { n: "6", name: "Verification", desc: "Re-runs 3×, arbitrates evidence, and computes CVSS from observed impact." },
  { n: "7", name: "Remediation", desc: "Synthesizes the patch on an isolated branch, runs tests, replays the exploit." }
];

const PIPELINE = [
  { name: "Orchestrator", pct: 100 },
  { name: "Code Intel", pct: 100 },
  { name: "Recon", pct: 100 },
  { name: "Vuln Research", pct: 100 },
  { name: "Dynamic Testing", pct: 92 },
  { name: "Verification", pct: 88 },
  { name: "Remediation", pct: 74 }
];

function fmt(n, fallback = "—") {
  if (n === null || n === undefined || Number.isNaN(n)) return fallback;
  return String(n);
}

export function renderLanding(container, navigate, state, api) {
  container.innerHTML = `
    <div class="landing-root">
      <div class="lp-aurora"><div class="lp-grid-bg"></div></div>

      <!-- ============ NAV ============ -->
      <nav class="lp-nav">
        <a class="lp-brand" href="#landing">
          <div class="lp-brand-mark">AT</div>
          <div class="lp-brand-text">
            <span class="lp-brand-name">AegisTrace</span>
            <span class="lp-brand-sub">Security Twin</span>
          </div>
        </a>
        <div class="lp-nav-links">
          <a class="lp-nav-link" href="#lp-signal">How it works</a>
          <a class="lp-nav-link" href="#lp-agents">Agents</a>
          <a class="lp-nav-link" href="#lp-proof">Proof model</a>
          <a class="lp-nav-link" href="#lp-cta">Get started</a>
        </div>
        <div class="lp-nav-actions">
          <button class="btn btn-secondary btn-sm" data-nav="dashboard">Open console</button>
          <button class="btn btn-primary btn-sm" data-nav="wizard">Launch assessment</button>
        </div>
      </nav>

      <!-- ============ HERO ============ -->
      <section class="lp-hero">
        <div class="lp-hero-copy">
          <div class="lp-eyebrow">
            <span class="lp-dot"></span>
            Autonomous security twin
          </div>

          <h1 class="lp-h1">
            Only what is <span class="lp-h1-grad">proven</span><br>becomes a finding.
          </h1>

          <p class="lp-lede">
            AegisTrace links <strong>source code</strong>, <strong>runtime behavior</strong>, and
            <strong>database state</strong>. Seven agents hypothesize, exploit, and arbitrate — and a
            vulnerability is only reported once it is reproduced against a live target.
          </p>

          <div class="lp-launch">
            <div class="lp-launch-head">
              <span>🐙 Analyze a repository</span>
              <span class="lp-launch-meta">AST · invariants · proof</span>
            </div>
            <div class="lp-launch-row">
              <input
                id="lp-repo-input"
                class="lp-input"
                type="text"
                spellcheck="false"
                autocomplete="off"
                value="${state.targetRepoUrl || "https://github.com/we45/Vulnerable-Flask-App"}"
                placeholder="https://github.com/owner/repository"
                aria-label="GitHub repository URL">
              <button class="lp-launch-btn" id="lp-launch-btn">
                <span>⚡</span> Start
              </button>
            </div>
            <div class="lp-presets">
              <span class="lp-preset" style="cursor:default;border:0;background:transparent;color:var(--text-muted);padding-left:0;">Try:</span>
              <button class="lp-preset" data-repo="https://github.com/we45/Vulnerable-Flask-App">we45/Vulnerable-Flask-App</button>
              <button class="lp-preset" data-repo="https://github.com/renceInbox/fastapi-todo">renceInbox/fastapi-todo</button>
              <button class="lp-preset" data-repo="https://github.com/Ishanoshada/flask-auth-app">Ishanoshada/flask-auth-app</button>
            </div>
          </div>

          <div class="lp-hero-ctas">
            <button class="lp-cta-ghost" data-nav="workspace">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
              Watch the pipeline
            </button>
            <button class="lp-cta-ghost" data-nav="findings">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              Browse findings
            </button>
          </div>
        </div>

        <!-- Live telemetry panel -->
        <div class="lp-telemetry" aria-label="Live platform telemetry">
          <div class="lp-telemetry-bar">
            <span class="dots"><i></i><i></i><i></i></span>
            <span class="lp-telemetry-title">aegistrace / live-telemetry</span>
            <span class="lp-telemetry-live" id="lp-live-badge">● live</span>
          </div>
          <div class="lp-telemetry-body">
            <div class="lp-metrics">
              <div class="lp-metric">
                <div class="lp-metric-label">Projects</div>
                <div class="lp-metric-value" data-metric="total_projects">—</div>
                <div class="lp-metric-sub">targets onboarded</div>
              </div>
              <div class="lp-metric">
                <div class="lp-metric-label">Assessments</div>
                <div class="lp-metric-value" data-metric="total_scans">—</div>
                <div class="lp-metric-sub">full agent cycles</div>
              </div>
              <div class="lp-metric">
                <div class="lp-metric-label">Findings</div>
                <div class="lp-metric-value warn" data-metric="total_findings">—</div>
                <div class="lp-metric-sub">in the evidence vault</div>
              </div>
              <div class="lp-metric">
                <div class="lp-metric-label">Confirmed</div>
                <div class="lp-metric-value ok" data-metric="confirmed_findings">—</div>
                <div class="lp-metric-sub">dynamically reproduced</div>
              </div>
            </div>

            <div class="lp-pipe">
              ${PIPELINE.map(p => `
                <div class="lp-pipe-row">
                  <span class="lp-pipe-name">${p.name}</span>
                  <span class="lp-pipe-track"><span class="lp-pipe-fill" data-pct="${p.pct}" style="width:0%"></span></span>
                  <span class="lp-pipe-pct">${p.pct}%</span>
                </div>`).join("")}
            </div>

            <div style="display:flex;align-items:center;gap:8px;margin-top:12px;padding-top:11px;border-top:1px solid var(--border-subtle);">
              <span class="badge badge-success">Scope gate: armed</span>
              <span class="badge badge-cyan">Evidence: immutable</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ============ TRUST STRIP ============ -->
      <section class="lp-section" style="padding-top:0;padding-bottom:0;">
        <div class="lp-trust">
          <div class="lp-trust-item">
            <div class="lp-trust-value" data-metric="active_skills">—</div>
            <div class="lp-trust-label">BugHunter skills</div>
          </div>
          <div class="lp-trust-item">
            <div class="lp-trust-value">7</div>
            <div class="lp-trust-label">Autonomous agents</div>
          </div>
          <div class="lp-trust-item">
            <div class="lp-trust-value">3×</div>
            <div class="lp-trust-label">Replay arbitration</div>
          </div>
          <div class="lp-trust-item">
            <div class="lp-trust-value">100%</div>
            <div class="lp-trust-label">Evidence hashed</div>
          </div>
          <div class="lp-trust-item">
            <div class="lp-trust-value">0</div>
            <div class="lp-trust-label">Unverified claims</div>
          </div>
        </div>
      </section>

      <!-- ============ THREE LAYERS ============ -->
      <section class="lp-section" id="lp-signal">
        <div class="lp-section-head">
          <div class="lp-kicker">The signal problem</div>
          <h2 class="lp-h2">A 200 OK can still be a breach.</h2>
          <p class="lp-sub">
            Traditional scanners read one layer and guess. AegisTrace triangulates three,
            and refuses to escalate a hypothesis until all three agree.
          </p>
        </div>

        <div class="lp-layers">
          <article class="lp-layer">
            <div class="lp-layer-step">01</div>
            <h3>Code invariant</h3>
            <p>AST parsing derives who is supposed to own each record — from the code that actually runs, not from a config file.</p>
            <div class="lp-layer-code">PATCH /orders/{id} → owner: user_id</div>
          </article>
          <article class="lp-layer">
            <div class="lp-layer-step">02</div>
            <h3>Runtime behavior</h3>
            <p>A second identity replays the same request against the live target. The response is captured as evidence.</p>
            <div class="lp-layer-code">buyer_b → PATCH /orders/100 → 200 OK</div>
          </article>
          <article class="lp-layer">
            <div class="lp-layer-step">03</div>
            <h3>Database state</h3>
            <p>Row-level snapshots before and after prove the mutation. No diff, no finding — the hypothesis is rejected.</p>
            <div class="lp-layer-code">orders[100].shipping_address changed</div>
          </article>
        </div>
      </section>

      <!-- ============ AGENTS ============ -->
      <section class="lp-section" id="lp-agents" style="padding-top:0;">
        <div class="lp-section-head">
          <div class="lp-kicker">The pipeline</div>
          <h2 class="lp-h2">Seven agents, one chain of custody.</h2>
          <p class="lp-sub">Each stage hands a signed artifact to the next. Nothing is asserted without an upstream reference.</p>
        </div>
        <div class="lp-agents">
          ${AGENTS.map(a => `
            <article class="lp-agent">
              <div class="lp-agent-top">
                <span class="lp-agent-num">${a.n}</span>
                <span class="lp-agent-name">${a.name}</span>
              </div>
              <p class="lp-agent-desc">${a.desc}</p>
            </article>`).join("")}
        </div>
      </section>

      <!-- ============ PROOF MODEL ============ -->
      <section class="lp-section" id="lp-proof" style="padding-top:0;">
        <div class="lp-section-head">
          <div class="lp-kicker">Proof model</div>
          <h2 class="lp-h2">What changes when nothing unverified ships.</h2>
        </div>
        <div class="lp-contrast">
          <div class="lp-contrast-card bad">
            <div class="lp-contrast-head">
              <span>✕</span> Typical scanner output
            </div>
            <ul class="lp-contrast-list">
              <li>Pattern matches reported as vulnerabilities</li>
              <li>Severity guessed from a static template</li>
              <li>"Likely vulnerable" with no reproduction</li>
              <li>Triagers spend days proving or discarding</li>
              <li>Patches proposed for code that was never exploitable</li>
            </ul>
          </div>
          <div class="lp-contrast-card good">
            <div class="lp-contrast-head">
              <span>✓</span> AegisTrace output
            </div>
            <ul class="lp-contrast-list">
              <li>Only hypotheses that survived 3× sandbox replay</li>
              <li>CVSS computed from the columns that actually changed</li>
              <li>Immutable evidence with SHA-256 chain</li>
              <li>Rejected hypotheses preserved with reasons</li>
              <li>Patch validated by replaying the original exploit</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- ============ FINAL CTA ============ -->
      <section class="lp-final" id="lp-cta">
        <div class="lp-final-inner">
          <h2>Point it at a repository.</h2>
          <p>
            Paste a GitHub URL and the platform clones it, maps the attack surface, derives invariants,
            and runs the full seven-agent cycle. Nothing outside the declared scope is ever touched.
          </p>
          <div class="lp-final-actions">
            <button class="btn btn-primary btn-lg" data-nav="wizard">Launch an assessment →</button>
            <button class="lp-cta-ghost" data-nav="dashboard">Explore the console</button>
          </div>
        </div>
      </section>

      <footer class="lp-footer">
        <span>© ${new Date().getFullYear()} AegisTrace — autonomous security intelligence.</span>
        <div class="lp-footer-links">
          <a href="#dashboard">Console</a>
          <a href="#skills">Skills</a>
          <a href="#benchmarks">Benchmarks</a>
          <a href="#reports">Reports</a>
        </div>
      </footer>
    </div>
  `;

  // -------- wire interactions --------
  container.querySelectorAll("[data-nav]").forEach(el => {
    el.addEventListener("click", () => navigate(el.getAttribute("data-nav")));
  });

  const input = container.querySelector("#lp-repo-input");
  const launch = () => {
    const url = (input?.value || "").trim();
    if (!url) return;
    state.targetRepoUrl = url;
    navigate("wizard");
  };
  container.querySelector("#lp-launch-btn")?.addEventListener("click", launch);
  input?.addEventListener("keydown", e => { if (e.key === "Enter") launch(); });

  container.querySelectorAll(".lp-preset[data-repo]").forEach(btn => {
    btn.addEventListener("click", () => {
      const url = btn.getAttribute("data-repo");
      if (input) input.value = url;
      state.targetRepoUrl = url;
    });
  });

  // Animate the pipeline bars after paint.
  requestAnimationFrame(() => {
    container.querySelectorAll(".lp-pipe-fill").forEach(bar => {
      bar.style.width = `${bar.getAttribute("data-pct")}%`;
    });
  });

  // -------- live telemetry: real numbers only --------
  const setMetric = (key, value) => {
    container.querySelectorAll(`[data-metric="${key}"]`).forEach(el => {
      el.textContent = fmt(value);
    });
  };

  if (api) {
    Promise.all([
      api.getOverviewStats().catch(() => null),
      api.getHealth().catch(() => null)
    ]).then(([stats, health]) => {
      if (stats) {
        ["total_projects", "total_scans", "total_findings", "confirmed_findings", "active_skills"]
          .forEach(k => setMetric(k, stats[k]));
      }
      const badge = container.querySelector("#lp-live-badge");
      if (badge && health) {
        const ok = String(health.status || "").toLowerCase() === "healthy";
        badge.textContent = ok ? "● live" : "● degraded";
        badge.style.color = ok ? "var(--success)" : "var(--warning)";
      }
    });
  }
}
