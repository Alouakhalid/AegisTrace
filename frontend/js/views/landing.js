export function renderLanding(container, navigate, state) {
  container.innerHTML = `
    <!-- 3.1 Floating Fixed Glass Navigation Bar -->
    <header class="landing-navbar" id="landing-navbar">
      <div class="landing-brand" id="landing-brand-logo">
        <div class="user-avatar" style="width: 34px; height: 34px; background: linear-gradient(135deg, var(--primary), var(--electric-blue)); color: #fff; font-weight: 800; font-family: var(--font-mono); font-size: 0.95rem; border-radius: var(--radius-sm); box-shadow: 0 0 20px rgba(121, 59, 255, 0.4);">AT</div>
        <div style="display: flex; flex-direction: column;">
          <span style="font-size: 1.25rem; font-weight: 800; letter-spacing: -0.3px; color: #fff;">AegisTrace</span>
          <span style="font-size: 8px; font-weight: 700; letter-spacing: 1.6px; color: var(--cyan-accent); text-transform: uppercase;">Security Twin</span>
        </div>
      </div>

      <nav class="landing-nav-links" id="landing-nav-links">
        <a class="landing-nav-link" href="#security-twin-section">Product</a>
        <a class="landing-nav-link" href="#workflow-section">Platform</a>
        <a class="landing-nav-link" href="#agents-section">Capabilities</a>
        <a class="landing-nav-link" href="#security-section">Security</a>
        <a class="landing-nav-link" id="nav-link-docs">Documentation</a>
      </nav>

      <div style="display: flex; align-items: center; gap: 14px;">
        <button class="btn btn-outline btn-sm" id="nav-btn-signin" style="font-size: 11px;">
          Sign In
        </button>
        <button class="btn btn-pill-trial btn-sm" id="nav-btn-getstarted">
          Get Started &rarr;
        </button>
      </div>
    </header>

    <!-- 3.2 Hero Section with Interactive Code-to-Behavior Security Twin Canvas -->
    <section class="hero-section" style="min-height: 100vh; position: relative; padding: 36px 24px 80px 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; overflow: hidden; background: radial-gradient(circle at 50% 30%, rgba(121, 59, 255, 0.12) 0%, rgba(9, 11, 28, 0) 70%);">
      <!-- Interactive Grid Background -->
      <div style="position: absolute; inset: 0; background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px); background-size: 40px 40px; pointer-events: none;"></div>

      <div style="position: relative; z-index: 2; max-width: 1200px; width: 100%; text-align: center; margin: 0 auto;">
        <!-- Live Status Pill -->
        <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(121, 59, 255, 0.12); border: 1px solid var(--border-accent); padding: 6px 18px; border-radius: var(--radius-full); margin-bottom: 28px;">
          <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--cyan-accent); box-shadow: 0 0 10px var(--cyan-accent);"></span>
          <span style="font-size: 9px; font-weight: 800; color: var(--cyan-accent); letter-spacing: 1.5px; text-transform: uppercase;">Autonomous Security Twin</span>
          <span style="color: var(--text-muted); font-size: 11px;">&bull;</span>
          <span style="font-size: 11px; color: var(--text-secondary);">Code &bull; Runtime &bull; Policy</span>
        </div>

        <!-- Headline -->
        <h1 style="font-family: var(--font-sans); font-size: clamp(2.6rem, 6.5vw, 5.2rem); font-weight: 800; line-height: 1.1; margin-bottom: 24px; letter-spacing: -1.8px; color: #FFFFFF;">
          Understand Your Code.<br>
          <span style="background: linear-gradient(135deg, #793BFF 0%, #426BFF 50%, #24C8F5 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Expose What Others Miss.</span>
        </h1>

        <!-- Supporting message -->
        <p style="font-size: 1.15rem; color: var(--text-secondary); max-width: 780px; margin: 0 auto 36px auto; line-height: 1.7; font-weight: 400;">
          Autonomous application security intelligence that connects code, runtime behavior, and security policies to discover, verify, and remediate real vulnerabilities.
        </p>

        <!-- CTAs -->
                <!-- PROMINENT GITHUB REPOSITORY INPUT (Section 1 & 11) -->
        <div style="max-width: 760px; margin: 0 auto 40px auto; background: rgba(13, 16, 34, 0.88); border: 1px solid var(--border-accent); border-radius: var(--radius-xl); padding: 26px; box-shadow: 0 0 50px rgba(121, 59, 255, 0.2); backdrop-filter: blur(16px); text-align: left;">
          <div style="font-size: 0.82rem; font-weight: 700; color: var(--cyan-accent); text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span>🐙</span> <span>Analyze a GitHub Repository</span>
            </div>
            <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">AST &bull; Code Graph &bull; BugHunter</span>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <input type="text" id="landing-repo-input" value="https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI" 
                   placeholder="https://github.com/owner/repository" 
                   style="flex: 1; padding: 14px 18px; font-size: 0.96rem; font-family: var(--font-mono); background: rgba(0,0,0,0.55); border: 1px solid rgba(255,255,255,0.14); border-radius: var(--radius-md); color: #fff; outline: none; transition: border-color 0.2s;">
            <button class="btn btn-primary" id="landing-btn-analyze" style="padding: 14px 28px; font-size: 0.95rem; font-weight: 700; white-space: nowrap; display: flex; align-items: center; gap: 8px; box-shadow: 0 0 20px rgba(121, 59, 255, 0.4);">
              <span>⚡</span> Analyze Repository
            </button>
          </div>
          <!-- Quick presets -->
          <div style="display: flex; gap: 8px; align-items: center; margin-top: 14px; flex-wrap: wrap;">
            <span style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px;">Quick Targets:</span>
            <button class="landing-preset-btn" data-url="https://github.com/Alouakhalid/Neurovain-Data-Analysis-AI" style="background: rgba(121,59,255,0.15); border: 1px solid rgba(121,59,255,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.74rem; cursor: pointer;">
              🧠 Neurovain-Data-Analysis-AI
            </button>
            <button class="landing-preset-btn" data-url="https://github.com/Alouakhalid/chess_RL" style="background: rgba(66,107,255,0.15); border: 1px solid rgba(66,107,255,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.74rem; cursor: pointer;">
              ♟️ chess_RL
            </button>
            <button class="landing-preset-btn" data-url="https://github.com/ebraheembinessa-E-vias/community-reels-engine" style="background: rgba(36,200,245,0.15); border: 1px solid rgba(36,200,245,0.35); color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 0.74rem; cursor: pointer;">
              🎬 community-reels-engine
            </button>
          </div>
        </div>

        <div style="display: flex; gap: 16px; justify-content: center; align-items: center; margin-bottom: 60px; flex-wrap: wrap;">
          <button class="btn btn-primary btn-lg" id="hero-btn-explore" style="padding: 14px 34px;">
            Explore the Platform &rarr;
          </button>
          <button class="btn btn-secondary btn-lg" id="hero-btn-howitworks" style="padding: 14px 34px;">
            View How It Works
          </button>
        </div>

        <!-- MANDATORY HERO ANIMATION: Animated Code-to-Behavior Security Twin Visualization -->
        <div class="security-twin-interactive-card" id="security-twin-stage" style="background: var(--bg-surface); border: 1px solid var(--border-accent); border-radius: var(--radius-xl); padding: 32px; box-shadow: var(--shadow-lg), 0 0 50px rgba(121, 59, 255, 0.15); position: relative; overflow: hidden; text-align: left;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 12px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="width: 10px; height: 10px; border-radius: 50%; background: var(--success); box-shadow: 0 0 12px var(--success);"></span>
                <span style="font-size: 12px; font-weight: 800; font-family: var(--font-mono); color: var(--text-primary); text-transform: uppercase; letter-spacing: 1px;">Live Security Twin Simulation &bull; BOLA / IDOR Trap</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Real-time correlation between AST Code Invariant, HTTP Execution, and Database State</div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary btn-sm" id="btn-sim-replay" style="font-size: 10px;">Replay Request</button>
              <button class="btn btn-secondary btn-sm" id="btn-sim-switch" style="font-size: 10px;">Toggle Identity: Buyer B (Attacker)</button>
            </div>
          </div>

          <!-- Three Connected Representations Grid -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; position: relative;">
            <!-- Node 1: Code Intelligence -->
            <div class="sim-node" id="sim-node-code" style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 20px; transition: all 0.3s ease;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <span style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 1px;">1. CODE INTELLIGENCE</span>
                <span class="badge badge-cyan">AST INVARIANT</span>
              </div>
              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); background: rgba(0,0,0,0.4); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.04); line-height: 1.6;">
                <div style="color: var(--primary);">&commat;app.patch('/orders/{id}')</div>
                <div>async def update_order(id: int, req: OrderUpdate, auth: Principal):</div>
                <div style="color: #68708c;">&nbsp;&nbsp;pass</div>
                <div style="color: var(--cyan-accent);">&nbsp;&nbsp;await db.execute('UPDATE orders...')</div>
                <div style="margin-top: 8px; color: var(--warning); border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 6px;">&bull; Invariant: owner_id == caller_id</div>
              </div>
            </div>

            <!-- Node 2: Runtime Behavior -->
            <div class="sim-node" id="sim-node-runtime" style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 20px; transition: all 0.3s ease;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <span style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--electric-blue); letter-spacing: 1px;">2. RUNTIME BEHAVIOR</span>
                <span class="badge badge-low">SANDBOX REPLAY</span>
              </div>
              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); background: rgba(0,0,0,0.4); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.04); line-height: 1.6;">
                <div><span style="color: var(--warning);">PATCH</span> /api/v1/orders/100</div>
                <div>Header: Authorization: Bearer &lt;buyer_b&gt;</div>
                <div>Payload: <span style="color: var(--cyan-accent);">{"shipping_address": "Tampered 777"}</span></div>
                <div style="color: var(--success); margin-top: 8px;">HTTP Response: 200 OK</div>
                <div style="font-size: 10px; color: #888;">(Standard scanners miss this!)</div>
              </div>
            </div>

            <!-- Node 3: Security Policies -->
            <div class="sim-node" id="sim-node-policy" style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 20px; transition: all 0.3s ease;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <span style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--critical); letter-spacing: 1px;">3. SECURITY POLICIES</span>
                <span class="badge badge-critical">INVARIANT ENGINE</span>
              </div>
              <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); background: rgba(0,0,0,0.4); padding: 12px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.04); line-height: 1.6;">
                <div>DB Snapshot (Before): owner='buyer_a'</div>
                <div>DB Snapshot (After): addr='Tampered 777'</div>
                <div style="color: var(--critical); font-weight: 700; margin-top: 8px;">&times; INVARIANT BROKEN: IDOR Detected</div>
                <div style="color: var(--cyan-accent); font-size: 10px;">State Proof: sha256:1377503964d1...</div>
                <div style="color: var(--success); font-size: 10px;">Confidence: 100% &bull; Repro: 3/3</div>
              </div>
            </div>
          </div>

          <!-- Flow Pipeline Animation Ribbon -->
          <div style="margin-top: 24px; padding: 14px 20px; background: rgba(0, 0, 0, 0.5); border-radius: var(--radius-sm); border: 1px solid rgba(255, 255, 255, 0.06); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span id="sim-status-bullet" style="width: 8px; height: 8px; border-radius: 50%; background: var(--critical); box-shadow: 0 0 10px var(--critical);"></span>
              <span id="sim-status-text" style="font-family: var(--font-mono); font-size: 11px; color: #fff;">
                Triangulation Complete: Unauthorized DB State Mutation Trapped by Verification Agent
              </span>
            </div>
            <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted);">
              Zero False Positives &bull; Verifiable Evidence Hash
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3.3 Trust & Technical Highlights -->
    <section style="padding: 80px 24px; max-width: 1200px; margin: 0 auto; border-top: 1px solid var(--border-subtle);">
      <div style="text-align: center; margin-bottom: 48px;">
        <div style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;">
          ENGINEERING PILLARS
        </div>
        <h2 style="font-size: 2.2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">
          Precision Security. Built on Evidence.
        </h2>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px;">
        <div class="card" style="padding: 28px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-sm); background: rgba(121, 59, 255, 0.15); border: 1px solid var(--border-accent); display: flex; align-items: center; justify-content: center; color: var(--primary); margin-bottom: 20px;">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Autonomous Security Testing</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            Explores complex application logic and APIs without manual test authoring, formulating paired-identity test scenarios autonomously.
          </p>
        </div>

        <div class="card" style="padding: 28px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-sm); background: rgba(36, 200, 245, 0.15); border: 1px solid var(--border-cyan); display: flex; align-items: center; justify-content: center; color: var(--cyan-accent); margin-bottom: 20px;">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Evidence-Based Verification</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            Vulnerabilities are never reported based on suspicion. Every finding requires cryptographic SHA-256 state mutation proof and 3/3 reproducible arbitration.
          </p>
        </div>

        <div class="card" style="padding: 28px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-sm); background: rgba(66, 107, 255, 0.15); border: 1px solid rgba(66, 107, 255, 0.35); display: flex; align-items: center; justify-content: center; color: var(--electric-blue); margin-bottom: 20px;">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Code-to-Behavior Intelligence</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            Connects static AST analysis directly with runtime HTTP traces and SQL mutations to verify whether theoretical flaws are actually exploitable.
          </p>
        </div>

        <div class="card" style="padding: 28px;">
          <div style="width: 44px; height: 44px; border-radius: var(--radius-sm); background: rgba(32, 214, 160, 0.15); border: 1px solid rgba(32, 214, 160, 0.35); display: flex; align-items: center; justify-content: center; color: var(--success); margin-bottom: 20px;">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Controlled AI Remediation</h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            Synthesizes minimal AST diff patches that undergo automated regression verification and require human review and SHA-256 seal before application.
          </p>
        </div>
      </div>
    </section>

    <!-- 3.4 How AegisTrace Works: 8-Stage Interactive Workflow -->
    <section id="workflow-section" style="padding: 80px 24px; max-width: 1200px; margin: 0 auto; border-top: 1px solid var(--border-subtle);">
      <div style="text-align: center; margin-bottom: 50px;">
        <div style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;">
          AUTONOMOUS LIFECYCLE
        </div>
        <h2 style="font-size: 2.2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">
          From Repository Ingestion to Sealed Patch
        </h2>
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">STAGE 01</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Repository Input</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Ingests Git repository or OpenAPI specification within strict ScopeGate boundaries.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">STAGE 02</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Code Intelligence</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Extracts routes, controllers, ORM schemas, and synthesizes candidate security invariants.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">STAGE 03</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Attack Surface</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Maps authorized hosts, live endpoints, and active authentication middlewares.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">STAGE 04</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Vulnerability Research</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Dynamically loads BugHunter skills and constructs prioritized test plans.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--primary); font-weight: 700; margin-bottom: 8px;">STAGE 05</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Dynamic Testing</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Executes identity-paired payloads inside sandboxed test containers.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--primary); font-weight: 700; margin-bottom: 8px;">STAGE 06</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Verification</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Multi-attempt replay, cryptographic state diff validation, and arbitration.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--success); font-weight: 700; margin-bottom: 8px;">STAGE 07</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Remediation</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Synthesizes minimal AST patch and verifies regression-free test passes.</p>
        </div>
        <div class="card" style="padding: 22px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--success); font-weight: 700; margin-bottom: 8px;">STAGE 08</div>
          <h4 style="font-size: 1rem; color: #fff; margin-bottom: 6px;">Human Approval</h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">Cryptographic SHA-256 patch integrity verification with approve, reject, or defer.</p>
        </div>
      </div>
    </section>

    <!-- 3.5 Code-to-Behavior Security Twin Deep Dive -->
    <section id="security-twin-section" style="padding: 80px 24px; max-width: 1200px; margin: 0 auto; border-top: 1px solid var(--border-subtle);">
      <div style="text-align: center; margin-bottom: 48px;">
        <div style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;">
          CORE INNOVATION
        </div>
        <h2 style="font-size: 2.2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">
          The Code-to-Behavior Security Twin
        </h2>
        <p style="font-size: 0.95rem; color: var(--text-secondary); max-width: 680px; margin: 12px auto 0 auto;">
          Why traditional scanners fail: an endpoint returning HTTP 200 with valid JSON can still represent a catastrophic authorization breach. AegisTrace triangulates all three layers:
        </p>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px;">
        <div class="card" style="padding: 32px;">
          <h3 style="font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 16px; display: flex; align-items: center; gap: 10px;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--critical);"></span>
            The Illusion: False Negative in Traditional Scanners
          </h3>
          <div style="font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.5); padding: 18px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.06); line-height: 1.7; color: var(--text-secondary);">
            <div style="color: var(--text-muted);"># Attacker sends payload to target:</div>
            <div>PATCH /api/v1/orders/100 HTTP/1.1</div>
            <div>Host: target.app</div>
            <div>Authorization: Bearer buyer_b_token</div>
            <div>{"shipping_address": "Tampered 777"}</div>
            <br>
            <div style="color: var(--success);">HTTP/1.1 200 OK</div>
            <div>Content-Type: application/json</div>
            <div>{"status": "updated", "id": 100}</div>
            <br>
            <div style="color: var(--critical);">Verdict: Scanner marks as 'Passed/Safe' (Received 200 OK)</div>
          </div>
        </div>

        <div class="card" style="padding: 32px; border-color: var(--border-accent); box-shadow: var(--shadow-violet-glow);">
          <h3 style="font-size: 1.25rem; font-weight: 800; color: #fff; margin-bottom: 16px; display: flex; align-items: center; gap: 10px;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--success);"></span>
            The Truth: AegisTrace Invariant Triangulation
          </h3>
          <div style="font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.5); padding: 18px; border-radius: var(--radius-sm); border: 1px solid rgba(255,255,255,0.06); line-height: 1.7; color: var(--text-secondary);">
            <div style="color: var(--cyan-accent);"># Code Invariant check:</div>
            <div>Invariant inv_01: orders.owner_id == caller_id</div>
            <div style="color: var(--primary);"># Database state diff:</div>
            <div>Before: id=100 &bull; owner='buyer_a' &bull; addr='Clean St'</div>
            <div>After:&nbsp;&nbsp;id=100 &bull; owner='buyer_a' &bull; addr='Tampered 777'</div>
            <br>
            <div style="color: var(--critical); font-weight: 700;">TRAPPED: Principal 'buyer_b' altered 'buyer_a' record!</div>
            <div style="color: var(--cyan-accent);">Evidence: evd_0192f21a (sha256 verified)</div>
            <div style="color: var(--success);">Result: Confirmed Critical Finding with Zero False Positives</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 3.6 Seven-Agent Architecture -->
    <section id="agents-section" style="padding: 80px 24px; max-width: 1200px; margin: 0 auto; border-top: 1px solid var(--border-subtle);">
      <div style="text-align: center; margin-bottom: 48px;">
        <div style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;">
          AUTONOMOUS MULTI-AGENT MESH
        </div>
        <h2 style="font-size: 2.2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">
          The 7 Specialized Security Agents
        </h2>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 6px;">AGENT 01</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Orchestrator Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Coordinates pipeline execution, governs token budgets, handles error recovery, and arbitrates multi-agent contracts.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 6px;">AGENT 02</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Code Intelligence Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Performs deep Tree-sitter AST analysis, models data flows, maps ORM entities, and synthesizes candidate security invariants.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan-accent); font-weight: 700; margin-bottom: 6px;">AGENT 03</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Reconnaissance Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Explores authorized target endpoints, parses OpenAPI schemas, fingerprints frameworks, and enforces ScopeGate boundaries.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--primary); font-weight: 700; margin-bottom: 6px;">AGENT 04</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Vulnerability Research Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Dynamically loads BugHunter skills, matches code patterns against CWE classifications, and constructs prioritized hypotheses.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--primary); font-weight: 700; margin-bottom: 6px;">AGENT 05</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Dynamic Testing Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Executes active tests with identity pairs, monitors state mutations, captures response latency, and records tamper artifacts.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--electric-blue); font-weight: 700; margin-bottom: 6px;">AGENT 06</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Verification Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Arbitrates exploit validity with 3-attempt replay, verifies cryptographic SHA-256 evidence hashes, and computes CVSS v3.1 vectors.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <div style="font-family: var(--font-mono); font-size: 10px; color: var(--success); font-weight: 700; margin-bottom: 6px;">AGENT 07</div>
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 6px;">Remediation Agent</h4>
          <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.6;">Generates minimal AST diff patches, executes regression test suites, seals patch integrity hashes, and prepares human approval gates.</p>
        </div>
      </div>
    </section>

    <!-- 3.7 Security & Control Section -->
    <section id="security-section" style="padding: 80px 24px; max-width: 1200px; margin: 0 auto; border-top: 1px solid var(--border-subtle);">
      <div style="text-align: center; margin-bottom: 48px;">
        <div style="font-size: 10px; font-weight: 800; font-family: var(--font-mono); color: var(--cyan-accent); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;">
          SECURITY-FIRST GOVERNANCE
        </div>
        <h2 style="font-size: 2.2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">
          Safety and Control by Design
        </h2>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px;">
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">ScopeGate Host Enforcement</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">Strict domain boundary protection blocks out-of-scope probes before execution.</p>
        </div>
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">Isolated Sandbox Jails</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">All dynamic tests run in ephemeral, isolated environments with strict network controls.</p>
        </div>
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">Cryptographic Evidence</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">Every state mutation is fingerprinted with SHA-256 for tamper-proof forensic auditability.</p>
        </div>
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">Mandatory Human Signoff</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">Patches require explicit human approval; zero autonomous code pushes to production.</p>
        </div>
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">Immutable Audit Trail</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">Every agent decision, LLM prompt, and action is permanently recorded in SQLite.</p>
        </div>
        <div class="card" style="padding: 28px;">
          <h4 style="font-size: 1.1rem; color: #fff; margin-bottom: 8px;">Regression Verification</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">Patches are validated to verify the vulnerability is closed without breaking existing tests.</p>
        </div>
      </div>
    </section>

    <!-- 3.8 Final CTA and Footer -->
    <section style="padding: 100px 24px; text-align: center; background: radial-gradient(circle at 50% 50%, rgba(121, 59, 255, 0.15) 0%, rgba(9, 11, 28, 0) 70%); border-top: 1px solid var(--border-subtle);">
      <div style="max-width: 800px; margin: 0 auto;">
        <h2 style="font-size: clamp(2.2rem, 5vw, 3.6rem); font-weight: 800; color: #fff; margin-bottom: 18px; letter-spacing: -1px;">
          Ready to Expose What Others Miss?
        </h2>
        <p style="font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 36px; line-height: 1.7;">
          Deploy autonomous application security intelligence to your codebase today.
        </p>
        <button class="btn btn-primary btn-lg" id="footer-btn-start" style="padding: 16px 42px; font-size: 1rem;">
          Open Security Operations Console &rarr;
        </button>
      </div>
    </section>

    <footer style="background: var(--bg-secondary); border-top: 1px solid var(--border-subtle); padding: 60px 48px 30px 48px;">
      <div style="max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 24px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="user-avatar" style="width: 30px; height: 30px; background: linear-gradient(135deg, var(--primary), var(--electric-blue)); color: #fff; font-size: 0.8rem; border-radius: 6px;">AT</div>
          <span style="font-weight: 800; color: #fff; font-size: 1.1rem;">AegisTrace</span>
          <span style="color: var(--text-muted); font-size: 11px;">&bull; Autonomous Application Security Intelligence</span>
        </div>
        <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">
          &copy; 2026 AegisTrace Systems. All rights reserved.
        </div>
      </div>
    </footer>
  `;

  // Bind Navigation Events
  const navTo = (route) => {
    navigate(route);
  };

    // Prominent Repo Analysis Action
  const repoInput = container.querySelector("#landing-repo-input");
  const btnAnalyze = container.querySelector("#landing-btn-analyze");
  if (btnAnalyze && repoInput) {
    btnAnalyze.onclick = () => {
      const val = repoInput.value.trim();
      if (val) {
        if (state) state.targetRepoUrl = val;
        navigate("wizard");
      }
    };
    repoInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        btnAnalyze.click();
      }
    });
  }
  container.querySelectorAll(".landing-preset-btn").forEach(btn => {
    btn.onclick = () => {
      const u = btn.getAttribute("data-url");
      if (repoInput && u) {
        repoInput.value = u;
        if (state) state.targetRepoUrl = u;
        navigate("wizard");
      }
    };
  });

  const btnExplore = container.querySelector("#hero-btn-explore");
  if (btnExplore) btnExplore.onclick = () => navTo("dashboard");

  const btnHowItWorks = container.querySelector("#hero-btn-howitworks");
  if (btnHowItWorks) {
    btnHowItWorks.onclick = () => {
      const el = container.querySelector("#security-twin-section");
      if (el) el.scrollIntoView({ behavior: "smooth" });
    };
  }

  const btnConsole = container.querySelector("#hero-btn-console");
  if (btnConsole) btnConsole.onclick = () => navTo("dashboard");

  const btnGetStarted = container.querySelector("#nav-btn-getstarted");
  if (btnGetStarted) btnGetStarted.onclick = () => navTo("wizard");

  const btnSignIn = container.querySelector("#nav-btn-signin");
  if (btnSignIn) btnSignIn.onclick = () => navTo("auth");

  const footerStart = container.querySelector("#footer-btn-start");
  if (footerStart) footerStart.onclick = () => navTo("dashboard");

  // Interactive Twin Simulation Logic
  const replayBtn = container.querySelector("#btn-sim-replay");
  const switchBtn = container.querySelector("#btn-sim-switch");
  const nodeCode = container.querySelector("#sim-node-code");
  const nodeRuntime = container.querySelector("#sim-node-runtime");
  const nodePolicy = container.querySelector("#sim-node-policy");
  const statusBullet = container.querySelector("#sim-status-bullet");
  const statusText = container.querySelector("#sim-status-text");

  let isAttacker = true;

  function runSimulation() {
    if (!nodeCode || !nodeRuntime || !nodePolicy) return;
    nodeCode.style.borderColor = "var(--cyan-accent)";
    nodeCode.style.boxShadow = "0 0 20px rgba(36, 200, 245, 0.2)";
    nodeRuntime.style.borderColor = "var(--border-subtle)";
    nodeRuntime.style.boxShadow = "none";
    nodePolicy.style.borderColor = "var(--border-subtle)";
    nodePolicy.style.boxShadow = "none";

    if (statusText) statusText.innerText = "Step 1: AST Route and Invariant extracted: owner_id == caller_id";
    if (statusBullet) {
      statusBullet.style.background = "var(--cyan-accent)";
      statusBullet.style.boxShadow = "0 0 10px var(--cyan-accent)";
    }

    setTimeout(() => {
      nodeRuntime.style.borderColor = "var(--electric-blue)";
      nodeRuntime.style.boxShadow = "0 0 20px rgba(66, 107, 255, 0.2)";
      if (statusText) statusText.innerText = isAttacker
        ? "Step 2: Dynamic Test executed with Identity Buyer B (Attacker) -> Target returned 200 OK"
        : "Step 2: Dynamic Test executed with Identity Buyer A (Legitimate Owner) -> Target returned 200 OK";
    }, 1200);

    setTimeout(() => {
      nodePolicy.style.borderColor = isAttacker ? "var(--critical)" : "var(--success)";
      nodePolicy.style.boxShadow = isAttacker ? "0 0 30px rgba(255, 85, 120, 0.35)" : "0 0 30px rgba(32, 214, 160, 0.35)";
      if (statusBullet) {
        statusBullet.style.background = isAttacker ? "var(--critical)" : "var(--success)";
        statusBullet.style.boxShadow = isAttacker ? "0 0 10px var(--critical)" : "0 0 10px var(--success)";
      }
      if (statusText) statusText.innerText = isAttacker
        ? "Step 3: Invariant Broke! Database mutation captured: Buyer B updated Buyer A's order without authorization."
        : "Step 3: Invariant Validated: Caller owns resource, DB state matches expected business rules.";
    }, 2400);
  }

  if (replayBtn) replayBtn.onclick = () => runSimulation();
  if (switchBtn) {
    switchBtn.onclick = () => {
      isAttacker = !isAttacker;
      switchBtn.innerText = isAttacker ? "Toggle Identity: Buyer B (Attacker)" : "Toggle Identity: Buyer A (Owner)";
      runSimulation();
    };
  }

  // Run initial simulation
  runSimulation();
}
