/**
 * Verification center.
 *
 * Arbitration is only meaningful if the numbers are real, so this view is built
 * from the evidence record attached to each finding: how many replays ran, how
 * many reproduced, whether a state mutation was trapped, and the CVSS vector the
 * backend actually stored. The previous version hardcoded a "CONFIRMED" verdict.
 */

const METRICS = [
  ["AV", "Attack Vector", { N: "Network", A: "Adjacent", L: "Local", P: "Physical" }],
  ["AC", "Attack Complexity", { L: "Low", H: "High" }],
  ["PR", "Privileges Required", { N: "None", L: "Low", H: "High" }],
  ["UI", "User Interaction", { N: "None", R: "Required" }],
  ["S", "Scope", { U: "Unchanged", C: "Changed" }],
  ["C", "Confidentiality", { N: "None", L: "Low", H: "High" }],
  ["I", "Integrity", { N: "None", L: "Low", H: "High" }],
  ["A", "Availability", { N: "None", L: "Low", H: "High" }]
];

function parseVector(vector) {
  const out = {};
  if (!vector) return out;
  String(vector).split("/").slice(1).forEach(part => {
    const [k, v] = part.split(":");
    if (k && v) out[k] = v;
  });
  return out;
}

function verdictBadge(verdict) {
  const v = String(verdict || "").toUpperCase();
  if (v === "CONFIRMED") return `<span class="badge badge-critical">CONFIRMED</span>`;
  if (v === "REJECTED" || v === "FALSE_POSITIVE") return `<span class="badge badge-success">${v}</span>`;
  if (v) return `<span class="badge badge-medium">${v}</span>`;
  return `<span class="badge badge-outline">not arbitrated</span>`;
}

export async function renderVerification(container, navigate, state, api) {
  let findings = [];
  try {
    findings = (await api.listFindings(state.currentScanId)) || [];
  } catch { /* offline */ }

  if (!findings.length) {
    container.innerHTML = `
      <div class="page-header">
        <div>
          <div class="page-eyebrow">Arbitration</div>
          <h1 class="page-title">Verification Center</h1>
          <p class="page-subtitle">Replay evidence for every candidate finding.</p>
        </div>
      </div>
      <div class="card" style="padding:52px 32px;text-align:center;">
        <div style="font-size:2.2rem;margin-bottom:12px;">⚖️</div>
        <h2 style="font-family:var(--font-serif);font-style:italic;font-size:1.35rem;color:#fff;margin-bottom:8px;">Nothing to arbitrate</h2>
        <p style="color:var(--text-muted);font-size:0.88rem;margin-bottom:20px;">The verification stage only runs on candidates that reached active probing.</p>
        <button class="btn btn-primary" id="verif-new-scan">Run an assessment</button>
      </div>`;
    container.querySelector("#verif-new-scan")?.addEventListener("click", () => navigate("wizard"));
    return;
  }

  const selectedId =
    findings.find(f => f.id === state.selectedFindingId)?.id || findings[0].id;
  state.selectedFindingId = selectedId;

  let detail = findings.find(f => f.id === selectedId);
  try {
    const full = await api.getFindingDetail(selectedId);
    if (full) detail = full;
  } catch { /* keep list record */ }

  const evidence = detail.evidence || {};
  const attempts = Number(evidence.reproduction_attempts || 0);
  const successes = Number(evidence.reproduction_successes || 0);
  const consistency = attempts ? `${successes}/${attempts}` : "—";
  const vector = parseVector(detail.cvss_vector);
  const confirmedCount = findings.filter(f => String(f.verification_verdict || "").toUpperCase() === "CONFIRMED").length;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Arbitration</div>
        <h1 class="page-title">Verification Center</h1>
        <p class="page-subtitle">Reproduction record for every candidate. ${confirmedCount} of ${findings.length} survived replay.</p>
      </div>
      <div class="surface-tools">
        <select class="form-control" id="verif-select" style="max-width:380px;">
          ${findings.map(f => `<option value="${f.id}" ${f.id === selectedId ? "selected" : ""}>${f.severity || "?"} · ${(f.title || f.id).slice(0, 60)}</option>`).join("")}
        </select>
        <button class="btn btn-secondary" id="verif-btn-findings">All findings →</button>
      </div>
    </div>

    <div class="verdict-banner ${String(detail.verification_verdict || "").toUpperCase() === "CONFIRMED" ? "confirmed" : "pending"}">
      <div class="verdict-left">
        <div class="verdict-mark">${String(detail.verification_verdict || "").toUpperCase() === "CONFIRMED" ? "✓" : "…"}</div>
        <div>
          <div class="verdict-title">${detail.verification_verdict ? `Verdict: ${String(detail.verification_verdict).toUpperCase()}` : "Awaiting arbitration"}</div>
          <div class="verdict-sub">
            <code>${detail.id}</code>
            ${detail.cwe_id ? ` · <span class="badge badge-outline">${detail.cwe_id}</span>` : ""}
            · replays <b>${consistency}</b>
          </div>
        </div>
      </div>
      <div class="verdict-score">
        <div class="verdict-cvss">${detail.cvss_score ?? "—"}</div>
        <span class="badge badge-${String(detail.severity || "low").toLowerCase()}">${String(detail.severity || "—").toUpperCase()}</span>
      </div>
    </div>

    <div class="dash-grid">
      <section class="card">
        <div class="card-header"><div class="card-title">Reproduction evidence</div>
          <span class="badge ${successes && successes === attempts ? "badge-success" : "badge-outline"}">
            ${attempts ? `${successes}/${attempts} reproduced` : "no replay data"}
          </span>
        </div>
        <div class="repro-grid">
          <div class="repro-cell"><span>Attempts</span><b>${attempts || "—"}</b></div>
          <div class="repro-cell"><span>Successes</span><b>${successes || "—"}</b></div>
          <div class="repro-cell"><span>State mutation trapped</span><b>${evidence.db_mutation_trapped ? "yes" : "no"}</b></div>
          <div class="repro-cell"><span>Identity used</span><b>${evidence.identity_used || "—"}</b></div>
          <div class="repro-cell"><span>Target owner</span><b>${evidence.target_resource_owner || "—"}</b></div>
          <div class="repro-cell"><span>HTTP</span><b>${evidence.http_method || ""} ${evidence.http_status ?? ""}</b></div>
        </div>

        <div class="report-section-title" style="margin-top:20px;">Root cause</div>
        <div class="report-summary" style="margin-bottom:0;">${detail.root_cause || "No root cause was recorded for this finding."}</div>

        ${evidence.sha256_snapshot_hash ? `
          <div class="report-section-title" style="margin-top:18px;">State snapshot</div>
          <div class="hash-block">
            <div><span>before sha256</span><code>${evidence.sha256_snapshot_hash}</code></div>
            ${evidence.state_before ? `<pre>${evidence.state_before}</pre>` : ""}
            ${evidence.state_after ? `<pre>${evidence.state_after}</pre>` : ""}
          </div>` : ""}
      </section>

      <section class="card">
        <div class="card-header"><div class="card-title">CVSS v3.1 breakdown</div>
          ${detail.cvss_vector ? `<code class="vector-code">${detail.cvss_vector}</code>` : ""}
        </div>
        ${detail.cvss_vector ? `
        <div class="cvss-grid">
          ${METRICS.map(([key, label, map]) => {
            const raw = vector[key];
            const human = raw ? (map[raw] || raw) : "—";
            return `<div class="cvss-cell"><span>${label}</span><b>${raw || "?"} · ${human}</b></div>`;
          }).join("")}
        </div>` : `<p class="empty-row" style="border:0;">No CVSS vector was computed for this finding.</p>`}

        ${detail.reproduction_summary ? `
          <div class="report-section-title" style="margin-top:18px;">Arbitration note</div>
          <div class="report-summary" style="margin-bottom:0;">${detail.reproduction_summary}</div>` : ""}
      </section>
    </div>

    <section class="card">
      <div class="card-header"><div class="card-title">All candidates in this assessment</div>
        <span class="dim" style="font-size:0.74rem;">${findings.length} records</span>
      </div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead><tr><th>Finding</th><th>Severity</th><th>CVSS</th><th>Verdict</th><th>Replays</th><th></th></tr></thead>
          <tbody>
            ${findings.map(f => `
              <tr>
                <td>${f.title || f.id}</td>
                <td><span class="badge badge-${String(f.severity || "low").toLowerCase()}">${f.severity || "—"}</span></td>
                <td class="mono">${f.cvss_score ?? "—"}</td>
                <td>${verdictBadge(f.verification_verdict)}</td>
                <td class="mono dim">${f.reproduction_summary || "—"}</td>
                <td><button class="btn btn-outline btn-sm verif-pick" data-id="${f.id}">Inspect</button></td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </section>
  `;

  container.querySelector("#verif-select")?.addEventListener("change", e => {
    state.selectedFindingId = e.target.value;
    navigate("verification");
  });
  container.querySelector("#verif-btn-findings")?.addEventListener("click", () => navigate("findings"));
  container.querySelectorAll(".verif-pick").forEach(b => b.addEventListener("click", e => {
    state.selectedFindingId = e.currentTarget.getAttribute("data-id");
    navigate("finding_details");
  }));
}
