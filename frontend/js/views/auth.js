export function renderAuth(container, navigate, state, api, toast) {
  let mode = "signin";

  function update() {
    container.innerHTML = `
      <div style="min-height: calc(100vh - 180px); display: flex; align-items: center; justify-content: center; position: relative;">
        <!-- Background Neural Glow -->
        <div style="position: absolute; width: 450px; height: 450px; border-radius: 50%; background: radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%); filter: blur(50px); pointer-events: none;"></div>

        <div class="card card-central-glow" style="width: 100%; max-width: 460px; border-radius: var(--radius-xl); padding: 44px 36px; border: 1px solid var(--border-gold); background: rgba(12, 11, 20, 0.85); position: relative; z-index: 2;">
          <!-- Card Header -->
          <div style="text-align: center; margin-bottom: 32px;">
            <img src="/static/assets/favicon.svg" alt="AegisTrace" width="56" height="56"
                 style="margin: 0 auto 16px; display: block; filter: drop-shadow(0 0 18px rgba(139, 92, 246, 0.55));">
            <div style="font-family: var(--font-sans); font-size: 1.8rem; font-weight: 800; letter-spacing: -0.02em; background: var(--grad-wordmark); -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 6px;">
              AegisTrace
            </div>
            <div style="font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; color: var(--cyan-accent);">
              SOVEREIGN SECURITY CONSOLE
            </div>
          </div>

          <!-- Auth Mode Toggle -->
          <div style="display: flex; border-bottom: 1px solid var(--border-subtle); margin-bottom: 28px;">
            <button id="auth-tab-signin" style="flex: 1; padding: 12px; background: none; border: none; border-bottom: 2px solid ${mode === 'signin' ? 'var(--cyan-accent)' : 'transparent'}; color: ${mode === 'signin' ? '#fff' : 'var(--text-muted)'}; font-size: 0.84rem; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 1.2px;">
              Sign In
            </button>
            <button id="auth-tab-signup" style="flex: 1; padding: 12px; background: none; border: none; border-bottom: 2px solid ${mode === 'signup' ? 'var(--cyan-accent)' : 'transparent'}; color: ${mode === 'signup' ? '#fff' : 'var(--text-muted)'}; font-size: 0.84rem; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 1.2px;">
              Create Account
            </button>
          </div>

          <!-- Form Fields -->
          <form id="auth-form">
            ${mode === 'signup' ? `
              <div class="form-group">
                <label class="form-label">Full Name & Title</label>
                <input type="text" class="form-control" id="auth-name" placeholder="Lead Security Engineer" required>
              </div>
            ` : ''}

            <div class="form-group">
              <label class="form-label">Corporate Email Address</label>
              <input type="email" class="form-control" id="auth-email" value="admin@aegistrace.luxury" placeholder="auditor@enterprise.com" required>
            </div>

            <div class="form-group">
              <label class="form-label">Vault Password</label>
              <input type="password" class="form-control" id="auth-pass" value="••••••••••••••••" placeholder="Enter secure passphrase" required>
            </div>

            ${mode === 'signin' ? `
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; font-size: 0.78rem;">
                <label style="display: flex; align-items: center; gap: 8px; color: var(--text-muted); cursor: pointer;">
                  <input type="checkbox" checked style="accent-color: var(--cyan-accent);">
                  Remember Token
                </label>
                <a href="javascript:void(0)" id="auth-forgot" style="color: var(--cyan-accent); text-decoration: none;">Forgot Passphrase?</a>
              </div>
            ` : `
              <div style="margin-bottom: 24px; font-size: 0.78rem; color: var(--text-muted); line-height: 1.5;">
                By registering, you agree to cryptographic audit logging and strict zero-knowledge tenancy boundaries.
              </div>
            `}

            <button type="submit" class="btn btn-primary" style="width: 100%; padding: 14px; font-size: 0.9rem; margin-bottom: 20px;">
              ${mode === 'signin' ? 'Sign In to Sovereign Vault' : 'Initialize Enterprise Workspace'}
            </button>
          </form>

          <!-- Divider -->
          <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 20px;">
            <div style="flex: 1; height: 1px; background: var(--border-subtle);"></div>
            <span style="font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.5px;">OR SSO</span>
            <div style="flex: 1; height: 1px; background: var(--border-subtle);"></div>
          </div>

          <!-- GitHub SSO Button -->
          <button class="btn btn-secondary" style="width: 100%;" id="auth-btn-github">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            Continue with GitHub Enterprise
          </button>
        </div>
      </div>
    `;

    document.getElementById("auth-tab-signin")?.addEventListener("click", () => { mode = "signin"; update(); });
    document.getElementById("auth-tab-signup")?.addEventListener("click", () => { mode = "signup"; update(); });

    document.getElementById("auth-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      toast(mode === "signin" ? "Authenticated successfully! Entering Sovereign Vault." : "Enterprise account initialized!", "success");
      navigate("dashboard");
    });

    document.getElementById("auth-btn-github")?.addEventListener("click", () => {
      toast("Connecting to GitHub Enterprise OAuth...", "info");
      setTimeout(() => {
        toast("GitHub Token verified: @security-lead", "success");
        navigate("dashboard");
      }, 1000);
    });

    document.getElementById("auth-forgot")?.addEventListener("click", () => {
      toast("Passphrase reset link dispatched to your authorized PGP identity.", "info");
    });
  }

  update();
}
