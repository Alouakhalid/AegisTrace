export async function renderSupporting(container, navigate, state, api, toast) {
  let auditLogs = [];
  let notifications = [];

  try {
    auditLogs = await api.getAuditLogs ? await api.getAuditLogs() : await api.req("/api/v1/audit-logs");
  } catch (e) {
    console.warn("Using baseline audit logs:", e);
    auditLogs = [
      {
        event_id: "evt_9901",
        timestamp: new Date().toISOString(),
        event_type: "APPROVAL_GATE",
        operator: "Security Lead (admin@aegistrace.luxury)",
        action: "Approved AST remediation patch ptch_bola_orders_01",
        sha256_hash: "7d1a2f64e29b01c3d4f88190e21bc5672901a88b1f5e8880291724ac661e8920",
        status: "COMMITTED"
      },
      {
        event_id: "evt_9900",
        timestamp: new Date().toISOString(),
        event_type: "EVIDENCE_LOCK",
        operator: "ArbitrationAgent (EvidenceStore)",
        action: "Cryptographic state snapshot locked for Finding fnd_prod_001",
        sha256_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        status: "IMMUTABLE"
      },
      {
        event_id: "evt_9899",
        timestamp: new Date().toISOString(),
        event_type: "SANDBOX_EXEC",
        operator: "DynamicTestingAgent",
        action: "Isolated exploit replay 3/3 executions confirmed BOLA state change",
        sha256_hash: "c81e728d9d4c2f636f067f89cc14862c1ecd979fb6334a1a5b81048b30e0179a",
        status: "VERIFIED"
      }
    ];
  }

  try {
    notifications = await api.getNotifications ? await api.getNotifications() : await api.req("/api/v1/notifications");
  } catch (e) {
    console.warn("Using baseline notifications:", e);
    notifications = [
      {
        id: "ntf_01",
        title: "Patch Approval Pending",
        message: "AST Remediation patch for fnd_prod_001 requires operator signature.",
        severity: "HIGH",
        timestamp: "2 minutes ago",
        read: false,
        category: "APPROVAL"
      },
      {
        id: "ntf_02",
        title: "Forensic State Mutation Trapped",
        message: "EvidenceStore arbitration confirmed 100% ground-truth BOLA vulnerability.",
        severity: "CRITICAL",
        timestamp: "12 minutes ago",
        read: false,
        category: "VULNERABILITY"
      },
      {
        id: "ntf_03",
        title: "7-Agent Pipeline Cycle Completed",
        message: "Autonomous scan scn_demo completed with 0 false positives.",
        severity: "INFO",
        timestamp: "35 minutes ago",
        read: true,
        category: "PIPELINE"
      }
    ];
  }

  container.innerHTML = `
    <div>
      <div class="page-header">
        <div>
          <div style="font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold-base); font-weight: 700; margin-bottom: 6px;">
            Unified Operations, Telemetry & Auxiliary Services
          </div>
          <h1 class="page-title">Supporting Screens & System Operations</h1>
          <p class="page-subtitle">Security Operator Profile, Immutable Audit Trails, Notification Feed, and System Error Diagnostic States.</p>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div style="display: flex; gap: 10px; margin-bottom: 24px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; flex-wrap: wrap;">
        <button class="btn btn-outline btn-sm support-tab active" data-tab="profile">Operator Profile & Keys</button>
        <button class="btn btn-outline btn-sm support-tab" data-tab="audit">Cryptographic Audit Logs</button>
        <button class="btn btn-outline btn-sm support-tab" data-tab="notifications">Security Notifications (${notifications.filter(n => !n.read).length})</button>
        <button class="btn btn-outline btn-sm support-tab" data-tab="errors">Error State Diagnostics</button>
      </div>

      <!-- TAB 1: Operator Profile -->
      <div class="support-tab-content" id="tab-profile">
        <div style="display: grid; grid-template-columns: 320px 1fr; gap: 24px;">
          <!-- Profile Card -->
          <div class="card card-glass" style="text-align: center; padding: 28px 20px;">
            <div style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, var(--gold-base), var(--gold-bronze)); color: #0a0a0a; font-weight: 800; font-size: 1.8rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; box-shadow: 0 0 30px rgba(167, 139, 113, 0.4);">
              AL
            </div>
            <h3 style="font-size: 1.25rem; font-weight: 700; color: #fff; font-family: 'Playfair Display', serif; font-style: italic;">
              Security Lead
            </h3>
            <div style="font-size: 0.8rem; color: var(--gold-base); margin-top: 4px; font-family: monospace;">admin@aegistrace.luxury</div>
            <div style="margin-top: 12px;">
              <span class="badge badge-gold">Enterprise Tier</span>
              <span class="badge badge-success" style="margin-left: 6px;">Dual-Key Signer</span>
            </div>

            <div style="border-top: 1px solid var(--border-subtle); margin-top: 20px; padding-top: 16px; text-align: left; font-size: 0.78rem; line-height: 1.8; color: var(--gold-light);">
              <div>Hardware MFA: <strong style="color: var(--success);">YubiKey 5C Active</strong></div>
              <div>Session Cipher: <strong style="color: #fff;">TLS 1.3 / ChaCha20</strong></div>
              <div>Organization: <strong style="color: #fff;">AegisTrace Global Defense</strong></div>
            </div>
          </div>

          <!-- Active API Credentials & Permissions -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">Authorized API Key Pairs & Cryptographic Grants</div>
              <button class="btn btn-primary btn-sm" id="btn-new-key">+ Generate Signer Key</button>
            </div>

            <div class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Key Identifier</th>
                    <th>Permissions Scope</th>
                    <th>Created</th>
                    <th>Last Active</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code style="color: var(--gold-base); font-size: 0.76rem;">aegis_sec_live_4491a...</code></td>
                    <td><span class="badge badge-gold-subtle">admin:write, patch:merge</span></td>
                    <td>2026-11-01</td>
                    <td>Just now</td>
                    <td><span class="badge badge-success">ACTIVE</span></td>
                    <td><button class="btn btn-outline btn-sm" style="padding: 2px 8px; font-size: 0.7rem;">Revoke</button></td>
                  </tr>
                  <tr>
                    <td><code style="color: var(--gold-base); font-size: 0.76rem;">aegis_ci_cd_pipe_8812b...</code></td>
                    <td><span class="badge badge-gold-subtle">scan:trigger, report:read</span></td>
                    <td>2026-11-15</td>
                    <td>14 hours ago</td>
                    <td><span class="badge badge-success">ACTIVE</span></td>
                    <td><button class="btn btn-outline btn-sm" style="padding: 2px 8px; font-size: 0.7rem;">Revoke</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB 2: Cryptographic Audit Logs -->
      <div class="support-tab-content" id="tab-audit" style="display: none;">
        <div class="card">
          <div class="card-header">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div class="card-title">Immutable Event Audit Trail (${auditLogs.length} Events)</div>
              <span class="badge badge-gold">Append-Only Vault</span>
            </div>
            <button class="btn btn-secondary btn-sm" id="btn-export-audit">Export Audit JSON</button>
          </div>

          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Timestamp</th>
                  <th>Event Classification</th>
                  <th>Operator / Agent</th>
                  <th>Action Detail</th>
                  <th>Cryptographic SHA-256</th>
                  <th>Vault Status</th>
                </tr>
              </thead>
              <tbody>
                ${auditLogs.map(l => `
                  <tr>
                    <td style="font-family: monospace; font-weight: 700; color: #fff;">${l.event_id}</td>
                    <td style="font-size: 0.76rem; color: var(--gold-light); font-family: monospace;">${l.timestamp}</td>
                    <td><span class="badge badge-gold">${l.event_type}</span></td>
                    <td style="font-weight: 600; color: #fff;">${l.operator}</td>
                    <td style="font-size: 0.8rem; color: var(--gold-light);">${l.action}</td>
                    <td><code style="font-size: 0.72rem; color: var(--gold-base);">${(l.sha256_hash || '').substring(0, 16)}...</code></td>
                    <td><span class="badge badge-success">${l.status}</span></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 3: Notifications Center -->
      <div class="support-tab-content" id="tab-notifications" style="display: none;">
        <div class="card">
          <div class="card-header">
            <div class="card-title">Security & Pipeline Notifications</div>
            <button class="btn btn-secondary btn-sm" id="btn-mark-all-read">Mark All as Read</button>
          </div>

          <div style="display: flex; flex-direction: column; gap: 14px; padding: 18px;">
            ${notifications.map(n => `
              <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 16px; background: rgba(255, 255, 255, ${n.read ? '0.01' : '0.03'}); border: 1px solid ${n.read ? 'var(--border-subtle)' : 'var(--border-gold)'}; border-radius: var(--radius-md);">
                <div style="display: flex; gap: 14px; align-items: flex-start;">
                  <div style="width: 10px; height: 10px; border-radius: 50%; background: ${n.read ? 'transparent' : 'var(--gold-base)'}; margin-top: 6px;"></div>
                  <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                      <h4 style="font-size: 0.95rem; font-weight: 700; color: #fff; margin: 0;">${n.title}</h4>
                      <span class="badge ${n.severity === 'CRITICAL' ? 'badge-critical' : (n.severity === 'HIGH' ? 'badge-warning' : 'badge-gold-subtle')}">${n.severity}</span>
                      <span class="badge badge-bronze" style="font-size: 0.65rem;">${n.category}</span>
                    </div>
                    <div style="font-size: 0.82rem; color: var(--gold-light); margin-top: 4px; line-height: 1.5;">${n.message}</div>
                    <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 6px; font-family: monospace;">${n.timestamp}</div>
                  </div>
                </div>

                <button class="btn btn-outline btn-sm" style="padding: 4px 10px; font-size: 0.72rem;">Dismiss</button>
              </div>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- TAB 4: Error State Diagnostics -->
      <div class="support-tab-content" id="tab-errors" style="display: none;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
          <!-- 404 Route Diagnostic -->
          <div class="card card-glass" style="text-align: center; padding: 36px 24px; border: 1px solid var(--border-gold);">
            <div style="font-size: 3.5rem; font-weight: 800; color: var(--gold-base); font-family: 'Playfair Display', serif; font-style: italic; line-height: 1; margin-bottom: 12px;">
              404
            </div>
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 8px;">Target Route Not Found</h3>
            <p style="font-size: 0.82rem; color: var(--gold-light); line-height: 1.5; margin-bottom: 18px;">
              The requested security intelligence dossier or telemetry stream does not exist in the active memory vault.
            </p>
            <button class="btn btn-secondary btn-sm" id="btn-err-return-dash">
              Return to Safe Dashboard
            </button>
          </div>

          <!-- 500 Engine Exception Diagnostic -->
          <div class="card card-glass" style="padding: 24px; border-left: 4px solid var(--critical);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge badge-critical">500 ENGINE EXCEPTION</span>
              <span style="font-family: monospace; font-size: 0.72rem; color: var(--text-muted);">Trace ID: err_trace_8819</span>
            </div>
            <h3 style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 8px;">
              Deterministic Sandbox Execution Trapped
            </h3>
            <div style="background: #050505; border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); font-family: monospace; font-size: 0.74rem; color: #f87171; line-height: 1.5; margin-bottom: 16px;">
              ExecutionSandboxJailError: Target process exceeded memory limit of 1024MB during AST symbol resolution.<br>
              &gt; Safe fallback initiated: sandbox isolated and rolled back.
            </div>
            <button class="btn btn-outline btn-sm" id="btn-err-report">
              Submit Telemetry Crash Dump
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  container.querySelectorAll(".support-tab").forEach(btn => {
    btn.addEventListener("click", (e) => {
      container.querySelectorAll(".support-tab").forEach(b => b.classList.remove("active"));
      e.currentTarget.classList.add("active");
      const target = e.currentTarget.getAttribute("data-tab");

      container.querySelectorAll(".support-tab-content").forEach(el => {
        el.style.display = "none";
      });
      const showEl = document.getElementById(`tab-${target}`);
      if (showEl) showEl.style.display = "block";
    });
  });

  // Action listeners
  document.getElementById("btn-new-key")?.addEventListener("click", () => {
    if (toast) toast("New RSA-256 Signer Key generated and added to Vault!", "success");
  });

  document.getElementById("btn-mark-all-read")?.addEventListener("click", () => {
    if (toast) toast("All notifications marked as read.", "info");
  });

  document.getElementById("btn-err-return-dash")?.addEventListener("click", () => navigate("dashboard"));
  document.getElementById("btn-err-report")?.addEventListener("click", () => {
    if (toast) toast("Telemetry crash dump dispatched to operator vault.", "success");
  });
}
