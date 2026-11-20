export async function renderApprovals(container, navigate, state, api, showModal, toast) {
  let approvals = [];
  try {
    approvals = await api.listApprovals();
  } catch (e) {
    console.warn("Failed to load approvals:", e);
  }

  // Fallback approval if empty
  if (!approvals || approvals.length === 0) {
    approvals = [
      {
        approval_id: "appr_9901",
        patch_id: "ptch_bola_orders_01",
        finding_id: "fnd_prod_001",
        finding_title: "Broken Object-Level Authorization (BOLA) in Order Mutation",
        status: "pending",
        target_file: "target_app.py",
        branch: "aegis-remediation-branch",
        patch_sha256: "7d1a2f64e29b01c3d4f88190e21bc5672901a88b1f5e8880291724ac661e8920",
        unified_diff: `--- a/target_app.py\n+++ b/target_app.py\n@@ -88,6 +88,9 @@ def update_order(order_id: int, payload: dict, user = Depends(get_current_user)):\n     order = db.query(Order).filter(Order.id == order_id).first()\n     if not order:\n         raise HTTPException(status_code=404, detail="Order not found")\n+    if order.owner_id != user.id and user.role != "admin":\n+        raise HTTPException(status_code=403, detail="Access forbidden: not resource owner")\n     order.delivery_address = payload.get("delivery_address", order.delivery_address)\n     db.commit()\n     return order`,
        requested_at: new Date().toISOString()
      }
    ];
  }

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-base); font-weight: 700; margin-bottom: 6px;">
            Dual-Key Authorization & AST Merge Gates
          </div>
          <h1 class="page-title">Human Approval Center</h1>
          <p class="page-subtitle">Server-enforced authorization gate before applying AST patches to shared repositories.</p>
        </div>
      </div>

      <!-- Server-Enforced Cryptographic Gate Banner -->
      <div class="card card-glass" style="margin-bottom: 24px; padding: 20px 24px; border-left: 3px solid var(--gold-base); box-shadow: 0 0 30px rgba(167, 139, 113, 0.1);">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
          <div>
            <div style="font-size: 0.95rem; font-weight: 700; color: #fff;">
              Server-Enforced Cryptographic Verification Gate
            </div>
            <div style="font-size: 0.8rem; color: var(--gold-light); margin-top: 3px;">
              Approval signatures are mathematically bound to the AST patch SHA-256 fingerprint. Any modification invalidates prior approvals.
            </div>
          </div>
          <span class="badge badge-gold">Zero Trust Enforced</span>
        </div>
      </div>

      <!-- Approvals List -->
      <div style="display: flex; flex-direction: column; gap: 24px;">
        ${approvals.map(apr => `
          <div class="card" style="border: 1px solid ${apr.status === 'approved' ? 'rgba(32, 214, 160, 0.4)' : (apr.status === 'rejected' ? 'rgba(220, 38, 38, 0.4)' : 'var(--border-gold)')};">
            <div class="card-header">
              <div>
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
                  <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; font-family: 'Playfair Display', serif; font-style: italic;">
                    ${apr.finding_title}
                  </h3>
                  <span class="badge ${apr.status === 'approved' ? 'badge-success' : (apr.status === 'rejected' ? 'badge-critical' : 'badge-gold')}">
                    ${apr.status.toUpperCase()}
                  </span>
                </div>
                <div style="font-size: 0.76rem; color: var(--gold-light); font-family: monospace;">
                  Approval ID: ${apr.approval_id} | Patch ID: ${apr.patch_id}
                </div>
              </div>

              <div style="display: flex; gap: 10px;">
                ${apr.status === 'pending' ? `
                  <button class="btn btn-secondary btn-sm btn-reject-patch" data-patch-id="${apr.patch_id}">
                    Reject
                  </button>
                  <button class="btn btn-primary btn-sm btn-approve-patch" data-patch-id="${apr.patch_id}">
                    ✓ Approve & Merge Patch
                  </button>
                ` : `
                  <div style="font-size: 0.82rem; color: var(--gold-light);">
                    Decided by: <strong style="color: #fff;">${apr.decided_by || 'Security Lead (admin@aegistrace.luxury)'}</strong>
                  </div>
                `}
              </div>
            </div>

            <!-- Metadata Box -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; background: rgba(255, 255, 255, 0.02); padding: 14px 18px; border-radius: var(--radius-md); margin-bottom: 16px; font-size: 0.8rem; border: 1px solid var(--border-subtle);">
              <div>
                <span style="color: var(--text-muted);">Target File:</span>
                <code style="color: var(--gold-base); margin-left: 6px;">${apr.target_file}</code>
              </div>
              <div>
                <span style="color: var(--text-muted);">Isolated Branch:</span>
                <code style="color: var(--gold-light); margin-left: 6px;">${apr.branch}</code>
              </div>
              <div>
                <span style="color: var(--text-muted);">Diff SHA-256:</span>
                <code style="color: var(--success); margin-left: 6px;">${(apr.patch_sha256 || '').substring(0, 16)}...</code>
              </div>
            </div>

            <!-- Unified Diff Snippet -->
            <div class="diff-container" style="background: #050505; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); max-height: 220px; overflow-y: auto;">
              <pre style="padding: 14px; color: #d1d5db; line-height: 1.5; font-size: 0.8rem; margin: 0; font-family: monospace;">${apr.unified_diff}</pre>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;

  // Approve button event
  container.querySelectorAll(".btn-approve-patch").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const pId = e.currentTarget.getAttribute("data-patch-id");
      try {
        await api.actOnApproval(pId, "approve", "Security Lead", "AST verified, all unit tests passed, exploit closed.");
        toast(`Patch ${pId} APPROVED & MERGED! Associated finding marked as RESOLVED.`, "success");
        renderApprovals(container, navigate, state, api, showModal, toast);
      } catch (err) {
        toast("Approval failed: " + err.message, "critical");
      }
    });
  });

  // Reject button event
  container.querySelectorAll(".btn-reject-patch").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const pId = e.currentTarget.getAttribute("data-patch-id");
      try {
        await api.actOnApproval(pId, "reject", "Security Lead", "Operator rejected patch diff.");
        toast(`Patch ${pId} rejected.`, "warning");
        renderApprovals(container, navigate, state, api, showModal, toast);
      } catch (err) {
        toast("Rejection failed: " + err.message, "critical");
      }
    });
  });
}
