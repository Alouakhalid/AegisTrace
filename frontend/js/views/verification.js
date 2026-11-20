export function renderVerification(container, navigate) {
  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--cyan-accent); font-weight: 700; margin-bottom: 6px;">
            Dual-Phase Arbitration & Ground-Truth Guarantee
          </div>
          <h1 class="page-title">Verification Center & Arbitration</h1>
          <p class="page-subtitle">EvidenceStore arbitration engine validating 3x reproduction consistency, state mutations, and CVSS v3.1 scoring.</p>
        </div>
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary btn-sm" id="verif-btn-findings">
            &larr; View Findings
          </button>
          <button class="btn btn-primary btn-sm" id="verif-btn-remediation">
            Proceed to Remediation &rarr;
          </button>
        </div>
      </div>

      <!-- Verdict Banner -->
      <div class="card card-glass" style="margin-bottom: 28px; border-left: 4px solid var(--cyan-accent); box-shadow: 0 0 50px rgba(167, 139, 113, 0.15);">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
          <div style="display: flex; align-items: center; gap: 20px;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: rgba(167, 139, 113, 0.12); border: 2px solid var(--cyan-accent); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: var(--cyan-accent);">
              ✓
            </div>
            <div>
              <div style="font-size: 1.35rem; font-weight: 800; color: #fff; font-family: 'Inter', serif; font-style: italic;">
                Forensic Arbitration Verdict: CONFIRMED
              </div>
              <div style="font-size: 0.84rem; color: var(--cyan-accent); margin-top: 4px;">
                Finding <code style="color: var(--cyan-accent); font-weight: 700;">fnd_prod_001</code> | CWE-639 (BOLA/IDOR) | False Positive Probability: <strong style="color: var(--success); font-family: monospace;">0.00%</strong>
              </div>
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 2.4rem; font-weight: 800; color: var(--cyan-accent); font-family: 'Inter', serif; font-style: italic; line-height: 1;">8.8</div>
            <span class="badge badge-critical" style="margin-top: 6px;">Critical Severity</span>
          </div>
        </div>
      </div>

      <!-- Grid Details -->
      <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; margin-bottom: 28px;">
        <!-- CVSS Breakdown -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">CVSS 3.1 Vector Breakdown</div>
            <code style="color: var(--cyan-accent); font-size: 0.76rem; background: rgba(255,255,255,0.02); padding: 3px 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N</code>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.82rem; padding: 18px;">
            <div style="background: rgba(255, 255, 255, 0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Attack Vector (AV)</span>
              <div style="color: #fff; font-weight: 700; margin-top: 2px;">Network (N)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Attack Complexity (AC)</span>
              <div style="color: #fff; font-weight: 700; margin-top: 2px;">Low (L)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Privileges Required (PR)</span>
              <div style="color: #fff; font-weight: 700; margin-top: 2px;">Low (L - Authenticated Buyer)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">User Interaction (UI)</span>
              <div style="color: #fff; font-weight: 700; margin-top: 2px;">None (N)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.02); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
              <span style="color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase;">Scope (S)</span>
              <div style="color: #fff; font-weight: 700; margin-top: 2px;">Unchanged (U)</div>
            </div>
            <div style="background: rgba(220, 38, 38, 0.05); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid rgba(220, 38, 38, 0.3);">
              <span style="color: #f87171; font-size: 0.72rem; text-transform: uppercase;">Integrity Impact (I)</span>
              <div style="color: #fca5a5; font-weight: 700; margin-top: 2px;">High (H - State Mutated)</div>
            </div>
          </div>
        </div>

        <!-- 3x Reproduction Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">Sandbox Reproduction Consistency</div>
            <span class="badge badge-success">3/3 Passed</span>
          </div>

          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Attempt</th>
                  <th>Isolated Jail</th>
                  <th>Status</th>
                  <th>Mutation Fingerprint</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="font-weight: 700; color: #fff;">Run #1</td>
                  <td>sbx_jail_01</td>
                  <td><span class="badge badge-critical">MUTATED (200)</span></td>
                  <td><code style="font-size: 0.72rem; color: var(--cyan-accent);">e3b0c442...</code></td>
                </tr>
                <tr>
                  <td style="font-weight: 700; color: #fff;">Run #2</td>
                  <td>sbx_jail_02</td>
                  <td><span class="badge badge-critical">MUTATED (200)</span></td>
                  <td><code style="font-size: 0.72rem; color: var(--cyan-accent);">e3b0c442...</code></td>
                </tr>
                <tr>
                  <td style="font-weight: 700; color: #fff;">Run #3</td>
                  <td>sbx_jail_03</td>
                  <td><span class="badge badge-critical">MUTATED (200)</span></td>
                  <td><code style="font-size: 0.72rem; color: var(--cyan-accent);">e3b0c442...</code></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Formal Verification Invariant Logic -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Formal Verification & Constraint Solver Proof</div>
          <span class="badge badge-cyan">SMT Invariant Solver</span>
        </div>

        <div style="padding: 18px; font-family: monospace; font-size: 0.8rem; line-height: 1.6; color: var(--text-secondary);">
          <div style="color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">
            Invariant Specification: ∀ order ∈ Orders: (UserCanMutate(user, order) ⇔ (order.owner_id == user.id ∨ user.role == "admin"))
          </div>
          <div style="background: #050505; border: 1px solid var(--border-subtle); padding: 14px; border-radius: var(--radius-sm); color: #fff; margin-bottom: 12px;">
            <div style="color: #f87171;">[FAIL] Invariant Violated at target_app.py:88</div>
            <div style="color: var(--text-muted); margin-top: 4px;">Satisfying Counter-example:</div>
            <div style="color: var(--cyan-accent); margin-left: 14px;">- user.id = "id_buyer_b"</div>
            <div style="color: var(--cyan-accent); margin-left: 14px;">- order.owner_id = "id_buyer_a"</div>
            <div style="color: var(--cyan-accent); margin-left: 14px;">- Execution Path: update_order() &rarr; db.commit() without conditional guard</div>
          </div>
          <div style="color: var(--cyan-accent); font-size: 0.78rem;">
            Solver status: UNSAT (Safe invariant cannot be satisfied without AST patch). Patch synthesized in Remediation Center.
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("verif-btn-findings")?.addEventListener("click", () => navigate("findings"));
  document.getElementById("verif-btn-remediation")?.addEventListener("click", () => navigate("remediation"));
}
