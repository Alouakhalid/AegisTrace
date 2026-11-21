/**
 * Finding dossier.
 *
 * Renders the evidence record exactly as stored: the request/response exchange,
 * the state snapshot, the identity pair and the replay counters. Fields the
 * pipeline never captured are shown as "not recorded" rather than filled with an
 * illustrative example, because a dossier is only useful if it is literal.
 */

function sevClass(sev) {
  return `badge-${String(sev || "low").toLowerCase()}`;
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return "not recorded";
  if (typeof v === "object") {
    try { return JSON.stringify(v, null, 2); } catch { return String(v); }
  }
  return String(v);
}

function prettyJson(v) {
  if (!v) return "";
  if (typeof v === "object") {
    try { return JSON.stringify(v, null, 2); } catch { return String(v); }
  }
  const s = String(v).trim();
  if (!s) return "";
  try { return JSON.stringify(JSON.parse(s), null, 2); } catch { return s; }
}

export async function renderFindingDetails(container, navigate, state, api, toast) {
  let findings = [];
  try { findings = (await api.listFindings()) || []; } catch { /* offline */ }

  let findingId = state.selectedFindingId || (findings[0] && findings[0].id) || "";
  let finding = null;
  if (findingId) {
    try { finding = await api.getFindingDetail(findingId); } catch { /* 404 */ }
  }
  // A stale id (for example from a previous session) must not blank the page.
  if (!finding && findings.length) {
    findingId = findings[0].id;
    try { finding = await api.getFindingDetail(findingId); } catch { /* 404 */ }
  }

  if (!finding) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Evidence dossier</div>
          <h1 class="page-title">Finding</h1>
          <p class="page-subtitle">No finding is selected.</p>
        </div>
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">🗂️</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">Nothing to inspect</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:20px;">Pick a finding from the vault, or run an assessment first.</p>
        <button class="btn btn-primary" id="fd-goto-findings">Open findings</button>
      </div>`;
    container.querySelector("#fd-goto-findings")?.addEventListener("click", () => navigate("findings"));
    return;
  }

  state.selectedFindingId = finding.id;
  const evd = finding.evidence || {};
  const attempts = Number(evd.reproduction_attempts || 0);
  const successes = Number(evd.reproduction_successes || 0);
  const reqHeaders = evd.request_headers && Object.keys(evd.request_headers).length ? evd.request_headers : null;
  const resHeaders = evd.response_headers && Object.keys(evd.response_headers).length ? evd.response_headers : null;
  const hasState = Boolean(evd.state_before || evd.state_after);

  container.innerHTML = `
    <div class="fd">
      <div class="fd-topbar">
        <button class="btn btn-secondary btn-sm" id="btn-back-findings">← Findings</button>
        <div class="surface-tools">
          ${findings.length > 1 ? `
            <select class="form-control" id="fd-select" style="max-width:340px;">
              ${findings.map(f => `<option value="${f.id}" ${f.id === finding.id ? "selected" : ""}>${f.severity || "?"} · ${(f.title || f.id).slice(0, 56)}</option>`).join("")}
            </select>` : ""}
          <button class="btn btn-secondary btn-sm" id="btn-goto-verification">Arbitration →</button>
          <button class="btn btn-primary btn-sm" id="btn-goto-remediation">Remediation →</button>
        </div>
      </div>

      <div class="page-header" style="margin-bottom:18px;">
        <div>
          <div class="fd-badges">
            <span class="badge badge-outline mono">${finding.id}</span>
            <span class="badge ${sevClass(finding.severity)}">${String(finding.severity || "—").toUpperCase()}</span>
            ${finding.cwe_id ? `<span class="badge badge-outline mono">${finding.cwe_id}</span>` : ""}
            <span class="badge ${String(finding.verification_verdict || "").toUpperCase() === "CONFIRMED" ? "badge-critical" : "badge-outline"}">
              ${finding.verification_verdict || "not arbitrated"}
            </span>
            <span class="badge badge-outline">${finding.status || "—"}</span>
          </div>
          <h1 class="page-title">${finding.title || "Untitled finding"}</h1>
          <p class="page-subtitle">${finding.root_cause || "No root cause recorded."}</p>
        </div>
        <div class="fd-score">
          <span>CVSS v3.1</span>
          <b>${finding.cvss_score ?? "—"}</b>
          ${finding.cvss_vector ? `<code class="vector-code">${finding.cvss_vector}</code>` : ""}
        </div>
      </div>

      <div class="fd-proof ${successes && successes === attempts ? "proven" : ""}">
        <div class="fd-proof-mark">${successes && successes === attempts ? "✓" : "…"}</div>
        <div>
          <div class="fd-proof-title">
            ${successes && successes === attempts
              ? "Reproduced on every replay"
              : attempts ? "Partially reproduced" : "No replay evidence recorded"}
          </div>
          <div class="fd-proof-sub">
            ${attempts ? `${successes} of ${attempts} sandbox replays reached the vulnerable state` : "The verification stage did not record replay attempts for this finding."}
            ${evd.db_mutation_trapped ? " · persistent state mutation trapped" : ""}
          </div>
        </div>
      </div>

      <div class="fd-grid">
        <section class="card">
          <div class="card-header"><div class="card-title">Attacker identity</div><span class="badge badge-critical">subject</span></div>
          <div class="fd-identity">${fmt(evd.identity_used)}</div>
          <p class="dim" style="font-size:0.78rem;margin-top:8px;">The identity the pipeline used when replaying the request.</p>
        </section>
        <section class="card">
          <div class="card-header"><div class="card-title">Resource owner</div><span class="badge badge-cyan">target</span></div>
          <div class="fd-identity">${fmt(evd.target_resource_owner)}</div>
          <p class="dim" style="font-size:0.78rem;margin-top:8px;">Who legitimately owns the record the request touched.</p>
        </section>
      </div>

      ${hasState || evd.sha256_snapshot_hash ? `
      <section class="card">
        <div class="card-header">
          <div class="card-title">State snapshot</div>
          <div class="surface-tools">
            ${evd.table_name ? `<span class="badge badge-bronze mono">${evd.table_name}${evd.row_id ? " · " + evd.row_id : ""}</span>` : ""}
            ${evd.sha256_snapshot_hash ? `<button class="btn btn-outline btn-sm" id="btn-copy-sha">Copy SHA-256</button>` : ""}
          </div>
        </div>
        ${evd.sha256_snapshot_hash ? `<div class="hash-block" style="margin-bottom:12px;"><div><span>sha256</span><code>${evd.sha256_snapshot_hash}</code></div></div>` : ""}
        <div class="state-diff">
          <div class="state-pane before">
            <div class="state-head"><span>Before</span><b>clean</b></div>
            <pre>${fmt(evd.state_before)}</pre>
          </div>
          <div class="state-pane after">
            <div class="state-head"><span>After</span><b>mutated</b></div>
            <pre>${fmt(evd.state_after)}</pre>
          </div>
        </div>
      </section>` : ""}

      <section class="card">
        <div class="card-header">
          <div class="card-title">HTTP exchange</div>
          <span class="badge badge-cyan mono">${evd.http_method || finding.http_method || ""} ${evd.http_status ?? ""}</span>
        </div>
        <div class="http-line">
          <span class="mono" style="color:var(--cyan-accent);">${evd.http_method || finding.http_method || "GET"}</span>
          <span class="mono">${evd.http_url || finding.endpoint || "not recorded"}</span>
        </div>
        <div class="fd-grid">
          <div>
            <div class="report-section-title">Request headers</div>
            <pre class="code-block">${reqHeaders ? prettyJson(reqHeaders) : "not recorded"}</pre>
            <div class="report-section-title" style="margin-top:14px;">Request body</div>
            <pre class="code-block">${prettyJson(evd.request_body) || "empty"}</pre>
          </div>
          <div>
            <div class="report-section-title">Response headers</div>
            <pre class="code-block">${resHeaders ? prettyJson(resHeaders) : "not recorded"}</pre>
            <div class="report-section-title" style="margin-top:14px;">Response body</div>
            <pre class="code-block">${prettyJson(evd.response_body) || "empty"}</pre>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-header"><div class="card-title">Replay record</div></div>
        <div class="repro-grid">
          <div class="repro-cell"><span>Attempts</span><b>${attempts || "—"}</b></div>
          <div class="repro-cell"><span>Successes</span><b>${successes || "—"}</b></div>
          <div class="repro-cell"><span>Verdict</span><b>${finding.verification_verdict || "—"}</b></div>
          <div class="repro-cell"><span>Summary</span><b style="font-family:var(--font-sans);font-size:0.8rem;">${finding.reproduction_summary || "—"}</b></div>
        </div>
      </section>
    </div>
  `;

  container.querySelector("#btn-back-findings")?.addEventListener("click", () => navigate("findings"));
  container.querySelector("#btn-goto-verification")?.addEventListener("click", () => navigate("verification"));
  container.querySelector("#btn-goto-remediation")?.addEventListener("click", () => navigate("remediation"));
  container.querySelector("#fd-select")?.addEventListener("change", e => {
    state.selectedFindingId = e.target.value;
    navigate("finding_details");
  });
  container.querySelector("#btn-copy-sha")?.addEventListener("click", () => {
    if (evd.sha256_snapshot_hash) {
      navigator.clipboard?.writeText(evd.sha256_snapshot_hash);
      if (toast) toast("SHA-256 copied", "success");
    }
  });
}
