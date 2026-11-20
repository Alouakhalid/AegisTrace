export function renderRemediation(container, navigate, state) {
  const diffLines = [
    { type: "info", text: "--- a/target_app.py (Original AST Node)" },
    { type: "info", text: "+++ b/target_app.py (Remediated AST Node)" },
    { type: "info", text: "@@ -88,6 +88,9 @@ def update_order(order_id: int, payload: dict, user = Depends(get_current_user)):" },
    { type: "ctx",  text: "     order = db.query(Order).filter(Order.id == order_id).first()" },
    { type: "ctx",  text: "     if not order:" },
    { type: "ctx",  text: "         raise HTTPException(status_code=404, detail=\"Order not found\")" },
    { type: "add",  text: "+    if order.owner_id != user.id and user.role != \"admin\":" },
    { type: "add",  text: "+        raise HTTPException(status_code=403, detail=\"Access forbidden: not resource owner\")" },
    { type: "ctx",  text: "     order.delivery_address = payload.get(\"delivery_address\", order.delivery_address)" },
    { type: "ctx",  text: "     db.commit()" },
    { type: "ctx",  text: "     return order" }
  ];

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-base); font-weight: 700; margin-bottom: 6px;">
            Deterministic AST Patch Synthesis & Validation
          </div>
          <h1 class="page-title">Remediation Center & AST Patch Synthesis</h1>
          <p class="page-subtitle">Deterministic code repair with AST grammar validation, dual test execution, and exploit closure proofs.</p>
        </div>
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary btn-sm" id="remed-btn-evidence">
            &larr; View Forensic Evidence
          </button>
          <button class="btn btn-primary btn-sm" id="remed-btn-approval">
            Proceed to Human Approval &rarr;
          </button>
        </div>
      </div>

      <!-- Test Suites Validation Cards -->
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; margin-bottom: 24px;">
        <div class="card card-glass" style="border-left: 3px solid var(--success);">
          <div style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Unit Test Suite</div>
          <div style="display: flex; align-items: baseline; gap: 10px;">
            <div style="font-size: 2rem; font-weight: 800; color: var(--success); font-family: 'Playfair Display', serif; font-style: italic;">10 / 10</div>
            <span class="badge badge-success">PASSED</span>
          </div>
          <div style="font-size: 0.76rem; color: var(--gold-light); margin-top: 6px;">Zero regressions in existing business logic workflows.</div>
        </div>

        <div class="card card-glass" style="border-left: 3px solid var(--gold-base);">
          <div style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Exploit Replay Test</div>
          <div style="display: flex; align-items: baseline; gap: 10px;">
            <div style="font-size: 2rem; font-weight: 800; color: var(--gold-base); font-family: 'Playfair Display', serif; font-style: italic;">HTTP 403</div>
            <span class="badge badge-gold">EXPLOIT CLOSED</span>
          </div>
          <div style="font-size: 0.76rem; color: var(--gold-light); margin-top: 6px;">Unauthorized cross-tenant mutation strictly forbidden.</div>
        </div>

        <div class="card card-glass" style="border-left: 3px solid var(--gold-light);">
          <div style="font-size: 0.74rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">AST Syntax Integrity</div>
          <div style="display: flex; align-items: baseline; gap: 10px;">
            <div style="font-size: 2rem; font-weight: 800; color: #fff; font-family: 'Playfair Display', serif; font-style: italic;">100%</div>
            <span class="badge badge-gold-subtle">SYNTAX VALID</span>
          </div>
          <div style="font-size: 0.76rem; color: var(--gold-light); margin-top: 6px;">Isolated git branch: <code style="color: var(--gold-base);">aegis-remediation-branch</code></div>
        </div>
      </div>

      <!-- Unified Diff Viewer -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">
            Unified Code Diff — <code style="color: var(--gold-base);">target_app.py</code>
          </div>
          <div style="font-size: 0.76rem; color: var(--text-muted); font-family: monospace;">
            Diff SHA-256: 7d1a2f64e29b01c3d4f88190e21bc5672901a88b1f5e8880291724ac661e8920
          </div>
        </div>

        <div class="diff-container" style="background: #050505; padding: 16px; border-radius: var(--radius-sm); font-family: monospace; font-size: 0.82rem; line-height: 1.6;">
          ${diffLines.map(line => `
            <div class="diff-line ${line.type}" style="padding: 2px 8px; border-radius: 2px; ${line.type === 'add' ? 'background: rgba(32, 214, 160, 0.12); color: #38efbd; font-weight: 600;' : (line.type === 'info' ? 'color: var(--gold-base); font-weight: 700;' : 'color: #9ca3af;')}">
              ${line.text}
            </div>
          `).join("")}
        </div>
      </div>

      <!-- Test Runner Log -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Sandbox Automated Test Execution Log</div>
          <span class="badge badge-success">pytest exit code 0</span>
        </div>

        <div style="background: #040404; padding: 16px; font-family: monospace; font-size: 0.76rem; color: #d1d5db; border-radius: var(--radius-sm); line-height: 1.6;">
          <div style="color: var(--text-muted);">[pytest] running tests in sandbox jail sbx_remed_44...</div>
          <div style="color: #38efbd;">✓ test_order_creation_valid PASSED [10%]</div>
          <div style="color: #38efbd;">✓ test_order_retrieval_authorized PASSED [20%]</div>
          <div style="color: #38efbd;">✓ test_order_update_by_owner PASSED [40%]</div>
          <div style="color: #38efbd;">✓ test_order_update_by_admin PASSED [60%]</div>
          <div style="color: var(--gold-base); font-weight: 700;">✓ test_cross_tenant_bola_exploit_blocked [HTTP 403 CONFIRMED] PASSED [100%]</div>
          <div style="color: var(--success); margin-top: 8px; font-weight: 700;">==================== 5 passed in 0.42s ====================</div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("remed-btn-evidence")?.addEventListener("click", () => navigate("finding_details"));
  document.getElementById("remed-btn-approval")?.addEventListener("click", () => navigate("approvals"));
}
