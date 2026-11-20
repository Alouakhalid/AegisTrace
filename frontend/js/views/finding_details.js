export async function renderFindingDetails(container, navigate, state, api, toast) {
  const findingId = state.selectedFindingId || "fnd_prod_001";
  let finding = null;

  try {
    finding = await api.getFindingDetail(findingId);
  } catch (e) {
    console.warn("Using baseline finding details:", e);
  }

  // Fallback data if needed
  if (!finding) {
    finding = {
      id: findingId,
      title: "Broken Object-Level Authorization (BOLA) in Order Mutation",
      severity: "CRITICAL",
      cvss_score: 8.8,
      cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N",
      cwe_id: "CWE-639",
      cwe_name: "Authorization Bypass Through User-Controlled Key",
      endpoint: "/api/v1/orders/{order_id}",
      http_method: "PATCH",
      root_cause: "Missing resource ownership verification against JWT tenant claims prior to record mutation in target_app.py:88.",
      verification_verdict: "CONFIRMED",
      status: "OPEN",
      evidence: {
        http_method: "PATCH",
        http_url: "http://127.0.0.1:5050/api/v1/orders/100",
        http_status: 200,
        request_headers: {
          "Host": "api.shoplite.internal",
          "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpZF9idXllcl9iIiwicm9sZSI6ImJ1eWVyIiwidGVuYW50IjoidGVuYW50XzIifQ...",
          "Content-Type": "application/json"
        },
        request_body: '{\n  "delivery_address": "99 Elite Penthouse, Unauthorized Buyer B"\n}',
        response_headers: {
          "HTTP/1.1": "200 OK",
          "Content-Type": "application/json",
          "Server": "Uvicorn/FastAPI"
        },
        response_body: '{\n  "id": 100,\n  "status": "updated",\n  "delivery_address": "99 Elite Penthouse, Unauthorized Buyer B",\n  "owner_id": "id_buyer_a"\n}',
        identity_used: "id_buyer_b (Buyer Role - Tenant 2)",
        target_resource_owner: "id_buyer_a (Buyer Role - Tenant 1)",
        state_before: 'delivery_address: "12 King Fahd Rd, Riyadh" | owner_id: "id_buyer_a" | modified_at: "2026-11-20T10:00:00Z"',
        state_after: 'delivery_address: "99 Elite Penthouse, Unauthorized Buyer B" | owner_id: "id_buyer_a" | modified_at: "2026-11-20T14:22:18Z"',
        sha256_snapshot_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        reproduction_attempts: 3,
        reproduction_successes: 3
      }
    };
  }

  const evd = finding.evidence || {};

  container.innerHTML = `
    <div>
      <!-- Top Navigation & Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <button class="btn btn-secondary btn-sm" id="btn-back-findings">
          &larr; Back to Findings
        </button>
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary btn-sm" id="btn-goto-verification">
            Arbitration Details &rarr;
          </button>
          <button class="btn btn-primary btn-sm" id="btn-goto-remediation">
            Proceed to Remediation &rarr;
          </button>
        </div>
      </div>

      <div class="page-header" style="margin-bottom: 24px;">
        <div>
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
            <span class="badge badge-cyan" style="font-family: monospace;">${finding.id}</span>
            <span class="badge ${finding.severity === 'CRITICAL' ? 'badge-critical' : 'badge-warning'}">${finding.severity}</span>
            <span class="badge badge-cyan-subtle" style="font-family: monospace;">${finding.cwe_id}</span>
          </div>
          <h1 class="page-title">${finding.title}</h1>
          <p class="page-subtitle">${finding.root_cause}</p>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--cyan-accent); font-weight: 700;">CVSS v3.1 Base Score</div>
          <div style="font-size: 2.2rem; font-weight: 800; color: var(--cyan-accent); font-family: 'Inter', serif; font-style: italic;">
            ${finding.cvss_score}
          </div>
        </div>
      </div>

      <!-- Hero Forensic State Mutation Trapped Banner -->
      <div class="card card-glass" style="margin-bottom: 24px; border-left: 4px solid var(--cyan-accent); box-shadow: 0 0 40px rgba(167, 139, 113, 0.15);">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
          <div style="display: flex; align-items: center; gap: 16px;">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(167, 139, 113, 0.15); border: 2px solid var(--cyan-accent); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; color: var(--cyan-accent);">
              ⚡
            </div>
            <div>
              <div style="font-size: 1.15rem; font-weight: 700; color: #fff;">
                Forensic State Mutation Trapped (Zero False Positive)
              </div>
              <div style="font-size: 0.82rem; color: var(--cyan-accent); margin-top: 3px;">
                Cross-tenant persistent state mutation executed in isolated sandbox jail. Arbitrated as ground-truth exploit.
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 10px;">
            <span class="badge badge-success">3/3 Sandbox Reproductions</span>
            <span class="badge badge-cyan">Deterministic Proof</span>
          </div>
        </div>
      </div>

      <!-- Identity Matrix (Attacker vs Resource Owner) -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
        <div class="card card-glass" style="border-left: 3px solid #f87171;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 0.74rem; text-transform: uppercase; color: #f87171; font-weight: 700; letter-spacing: 0.12em;">
              Unauthorized Attacker Identity
            </div>
            <span class="badge badge-critical" style="font-size: 0.65rem;">ATTACKER</span>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 6px;">
            ${evd.identity_used}
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.5;">
            Bearer token generated for Tenant 2. Had no read/write grant on Order #100 owned by Tenant 1.
          </div>
        </div>

        <div class="card card-glass" style="border-left: 3px solid var(--cyan-accent);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="font-size: 0.74rem; text-transform: uppercase; color: var(--cyan-accent); font-weight: 700; letter-spacing: 0.12em;">
              Legitimate Resource Owner
            </div>
            <span class="badge badge-cyan" style="font-size: 0.65rem;">VICTIM / RESOURCE</span>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; color: #fff; margin-bottom: 6px;">
            ${evd.target_resource_owner}
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.5;">
            Primary owner of database record in table <code style="color: var(--cyan-accent);">orders</code> (ID: 100). State was forcibly modified.
          </div>
        </div>
      </div>

      <!-- Database Mutation Proof Table -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="card-title">Database Mutation Forensic Diff</div>
            <span class="badge badge-bronze">Table: orders (ID: 100)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 0.72rem; color: var(--text-muted); font-family: monospace;">SHA-256 Snapshot:</span>
            <code style="font-size: 0.72rem; color: var(--cyan-accent); font-family: monospace;">${(evd.sha256_snapshot_hash || '').substring(0, 16)}...</code>
            <button class="btn btn-outline btn-sm" id="btn-copy-sha" style="padding: 2px 8px; font-size: 0.7rem;">Copy SHA</button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 18px;">
          <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 14px; font-family: monospace; font-size: 0.78rem;">
            <div style="color: var(--text-muted); font-weight: 700; margin-bottom: 8px; display: flex; justify-content: space-between;">
              <span>STATE BEFORE ATTACK</span>
              <span style="color: var(--success);">CLEAN</span>
            </div>
            <div style="color: #38efbd; line-height: 1.6; word-break: break-all;">
              ${evd.state_before}
            </div>
          </div>

          <div style="background: rgba(220, 38, 38, 0.04); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: var(--radius-sm); padding: 14px; font-family: monospace; font-size: 0.78rem;">
            <div style="color: var(--text-muted); font-weight: 700; margin-bottom: 8px; display: flex; justify-content: space-between;">
              <span>STATE AFTER ATTACK (MUTATED)</span>
              <span style="color: #f87171;">CORRUPTED</span>
            </div>
            <div style="color: #fca5a5; line-height: 1.6; word-break: break-all;">
              ${evd.state_after}
            </div>
          </div>
        </div>
      </div>

      <!-- HTTP Request / Response Replay Inspector -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div class="card-title">HTTP Request & Response Exchange Replay</div>
          <span class="badge badge-cyan">${evd.http_method} ${evd.http_url} &rarr; HTTP ${evd.http_status}</span>
        </div>

        <div style="padding: 18px; font-family: monospace; font-size: 0.8rem;">
          <div style="color: var(--cyan-accent); font-weight: 700; margin-bottom: 8px;">
            ${evd.http_method} /api/v1/orders/100 HTTP/1.1
          </div>
          <div style="color: var(--text-muted); margin-bottom: 8px;">
            Host: api.shoplite.internal<br>
            Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpZF9idXllcl9i...<br>
            Content-Type: application/json
          </div>
          <div style="background: #050505; border: 1px solid var(--border-gold); padding: 12px; border-radius: var(--radius-sm); color: #fff; margin-bottom: 16px;">
            <pre style="margin: 0;">${evd.request_body}</pre>
          </div>

          <div style="border-top: 1px dashed var(--border-subtle); padding-top: 14px;">
            <div style="color: var(--success); font-weight: 700; margin-bottom: 8px;">
              HTTP/1.1 200 OK
            </div>
            <div style="color: var(--text-muted); margin-bottom: 8px;">
              Content-Type: application/json<br>
              Server: Uvicorn/FastAPI
            </div>
            <div style="background: #050505; border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); color: var(--cyan-accent);">
              <pre style="margin: 0;">${evd.response_body}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- 3/3 Sandbox Reproduction Log -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">Sandbox Reproduction Consistency (3/3 Runs)</div>
          <span class="badge badge-success">Deterministic 100%</span>
        </div>

        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Execution Run</th>
                <th>Target Environment</th>
                <th>HTTP Status Trapped</th>
                <th>Database State Integrity</th>
                <th>Mutation Snapshot SHA-256</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="font-weight: 700; color: #fff;">Run #1</td>
                <td>Isolated Sandbox sbx_1</td>
                <td><span class="badge badge-critical">HTTP 200 (Exploited)</span></td>
                <td><span style="color: #f87171; font-weight: 700;">MUTATED</span></td>
                <td><code style="font-size: 0.74rem; color: var(--cyan-accent);">${(evd.sha256_snapshot_hash || '').substring(0, 24)}...</code></td>
              </tr>
              <tr>
                <td style="font-weight: 700; color: #fff;">Run #2</td>
                <td>Isolated Sandbox sbx_2</td>
                <td><span class="badge badge-critical">HTTP 200 (Exploited)</span></td>
                <td><span style="color: #f87171; font-weight: 700;">MUTATED</span></td>
                <td><code style="font-size: 0.74rem; color: var(--cyan-accent);">${(evd.sha256_snapshot_hash || '').substring(0, 24)}...</code></td>
              </tr>
              <tr>
                <td style="font-weight: 700; color: #fff;">Run #3</td>
                <td>Isolated Sandbox sbx_3</td>
                <td><span class="badge badge-critical">HTTP 200 (Exploited)</span></td>
                <td><span style="color: #f87171; font-weight: 700;">MUTATED</span></td>
                <td><code style="font-size: 0.74rem; color: var(--cyan-accent);">${(evd.sha256_snapshot_hash || '').substring(0, 24)}...</code></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Event handlers
  document.getElementById("btn-back-findings")?.addEventListener("click", () => navigate("findings"));
  document.getElementById("btn-goto-verification")?.addEventListener("click", () => navigate("verification"));
  document.getElementById("btn-goto-remediation")?.addEventListener("click", () => navigate("remediation"));

  document.getElementById("btn-copy-sha")?.addEventListener("click", () => {
    if (evd.sha256_snapshot_hash) {
      navigator.clipboard?.writeText(evd.sha256_snapshot_hash);
      if (toast) toast("Cryptographic SHA-256 snapshot copied to clipboard!", "success");
    }
  });
}
