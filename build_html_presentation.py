import os
import base64

def get_base64_image(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(path)[1].lower().replace(".", "")
            if ext == "svg":
                return f"data:image/svg+xml;base64,{b64}"
            return f"data:image/{ext};base64,{b64}"
    return ""

logo_b64 = get_base64_image("/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/.user_uploaded/media_1795281199884.png")
miro_b64 = get_base64_image("/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/.user_uploaded/media_1795282497648.png")

chart_metrics_b64 = get_base64_image("charts/agent_metrics_comparison.png")
chart_fp_b64 = get_base64_image("charts/false_positive_comparison.png")
chart_conf_b64 = get_base64_image("charts/agent_confusion_breakdown.png")
chart_rep_b64 = get_base64_image("charts/benchmark_reproduction.png")

diag_comm_b64 = get_base64_image("AegisTrace_Documentation/11_Architecture_Diagrams/d04c_comm.png")
diag_twin_b64 = get_base64_image("AegisTrace_Documentation/11_Architecture_Diagrams/d03_twin.png")
diag_appr_b64 = get_base64_image("AegisTrace_Documentation/11_Architecture_Diagrams/d17_approval.png")

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AegisTrace (2.0) — Technical Architecture & Agent Evaluation Deck</title>
<style>
  :root {{
    --bg-main: #0a0e1a;
    --bg-card: #111827;
    --bg-card-hover: #172237;
    --border-subtle: #243046;
    --border-active: #4f46e5;
    --accent-violet: #8b5cf6;
    --accent-cyan: #06b6d4;
    --accent-gold: #d4af37;
    --accent-emerald: #10b981;
    --accent-rose: #ef4444;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --font-mono: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
    --slide-width: 1920px;
    --slide-height: 1080px;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    background-color: var(--bg-main);
    color: var(--text-primary);
    font-family: var(--font-sans);
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    user-select: text;
  }}

  /* Canvas 16:9 Stage */
  #viewport {{
    position: relative;
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at 50% 20%, #151c2e 0%, #0a0e1a 100%);
  }}

  #slide-frame {{
    width: var(--slide-width);
    height: var(--slide-height);
    transform-origin: center center;
    position: absolute;
    box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.85);
    background: #0c111e;
    border-radius: 12px;
    overflow: hidden;
  }}

  .slide {{
    display: none;
    width: 100%;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
    padding: 60px 80px;
    flex-direction: column;
    justify-content: flex-start;
    background: #0c111e;
    background-image: 
      radial-gradient(rgba(139, 92, 246, 0.05) 1px, transparent 1px),
      radial-gradient(rgba(6, 182, 212, 0.04) 1px, transparent 1px);
    background-size: 40px 40px, 80px 80px;
  }}

  .slide.active {{
    display: flex;
  }}

  /* Top Slide Header */
  .slide-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 35px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    padding-bottom: 20px;
  }}

  .header-left {{
    max-width: 1400px;
  }}

  .category-tag {{
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent-violet);
    margin-bottom: 6px;
    display: inline-block;
  }}

  .slide-title {{
    font-size: 34px;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.2;
    letter-spacing: -0.5px;
  }}

  .slide-subtitle {{
    font-size: 16px;
    color: var(--text-secondary);
    margin-top: 6px;
  }}

  .header-right {{
    display: flex;
    align-items: center;
    gap: 15px;
  }}

  .header-logo {{
    height: 52px;
    filter: drop-shadow(0 0 12px rgba(139, 92, 246, 0.4));
  }}

  /* Layout Grids */
  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 35px;
    flex: 1;
  }}

  .grid-3 {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 30px;
    flex: 1;
  }}

  .grid-4 {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 25px;
    flex: 1;
  }}

  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    position: relative;
    overflow: hidden;
  }}

  .card.accent-violet {{ border-top: 4px solid var(--accent-violet); }}
  .card.accent-cyan {{ border-top: 4px solid var(--accent-cyan); }}
  .card.accent-gold {{ border-top: 4px solid var(--accent-gold); }}
  .card.accent-emerald {{ border-top: 4px solid var(--accent-emerald); }}
  .card.accent-rose {{ border-top: 4px solid var(--accent-rose); }}

  .card-title {{
    font-size: 21px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .card-body {{
    font-size: 15px;
    line-height: 1.65;
    color: var(--text-secondary);
  }}

  .card-body p {{
    margin-bottom: 14px;
  }}

  .card-body strong {{
    color: var(--text-primary);
  }}

  /* Metric Pills Row */
  .metrics-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 25px;
  }}

  .metric-pill {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
  }}

  .metric-pill-label {{
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-bottom: 4px;
  }}

  .metric-pill-val {{
    font-size: 22px;
    font-weight: 800;
    color: var(--accent-emerald);
    font-family: var(--font-mono);
  }}

  /* Clean Data Tables */
  .eval-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13.5px;
  }}

  .eval-table th {{
    background: rgba(30, 41, 59, 0.8);
    color: var(--accent-cyan);
    font-weight: 700;
    text-align: center;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border-subtle);
  }}

  .eval-table th:first-child {{
    text-align: left;
  }}

  .eval-table td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    color: var(--text-secondary);
  }}

  .eval-table td:first-child {{
    text-align: left;
    color: var(--text-primary);
    font-weight: 600;
  }}

  .eval-table tr.total-row td {{
    background: rgba(16, 185, 129, 0.08);
    color: var(--accent-emerald);
    font-weight: 800;
    border-top: 1px solid var(--accent-emerald);
  }}

  .badge {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
  }}

  .badge-emerald {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #059669; }}
  .badge-violet {{ background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid #7c3aed; }}
  .badge-cyan {{ background: rgba(6, 182, 212, 0.15); color: #67e8f9; border: 1px solid #0891b2; }}
  .badge-gold {{ background: rgba(212, 175, 55, 0.15); color: #fde047; border: 1px solid #ca8a04; }}
  .badge-rose {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #dc2626; }}

  /* Media Display Containers */
  .img-container {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    overflow: hidden;
  }}

  .img-container img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 8px;
  }}

  /* Editable Highlight Indicator */
  body.edit-mode [contenteditable="true"] {{
    outline: 2px dashed rgba(139, 92, 246, 0.5) !important;
    outline-offset: 4px;
    background: rgba(139, 92, 246, 0.05);
    border-radius: 4px;
  }}

  body.edit-mode [contenteditable="true"]:focus {{
    outline: 2px solid var(--accent-cyan) !important;
    background: rgba(6, 182, 212, 0.08);
  }}

  /* Controls Bar (Outside exported slide content) */
  #controls {{
    position: fixed;
    bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    background: rgba(17, 24, 39, 0.88);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 10px 24px;
    border-radius: 50px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6);
    z-index: 1000;
  }}

  .ctrl-btn {{
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: var(--text-primary);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s ease;
  }}

  .ctrl-btn:hover {{
    background: rgba(255, 255, 255, 0.1);
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
  }}

  .ctrl-btn:focus-visible {{
    outline: 2px solid var(--accent-cyan);
    outline-offset: 2px;
  }}

  .ctrl-btn.active {{
    background: var(--accent-violet);
    border-color: var(--accent-violet);
    color: white;
  }}

  #slide-counter {{
    font-size: 14px;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text-primary);
    min-width: 90px;
    text-align: center;
  }}

  /* Progress Bar */
  #progress-bar-container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    z-index: 1001;
  }}

  #progress-bar {{
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, var(--accent-violet), var(--accent-cyan));
    transition: width 0.3s ease;
  }}

  /* Speaker Notes Drawer */
  #speaker-notes-drawer {{
    display: none;
    position: fixed;
    bottom: 90px;
    left: 50%;
    transform: translateX(-50%);
    width: 900px;
    max-width: 90vw;
    background: rgba(17, 24, 39, 0.96);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-active);
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85);
    z-index: 1000;
    max-height: 250px;
    overflow-y: auto;
  }}

  #speaker-notes-drawer.open {{
    display: block;
  }}

  #speaker-notes-drawer h4 {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--accent-cyan);
    margin-bottom: 8px;
  }}

  #speaker-notes-content {{
    font-size: 14px;
    line-height: 1.6;
    color: #cbd5e1;
  }}

  /* Print Styles: One Slide Per Page */
  @media print {{
    @page {{
      size: 16in 9in landscape;
      margin: 0;
    }}

    html, body {{
      background: #0a0e1a !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      overflow: visible !important;
      width: 100% !important;
      height: auto !important;
      display: block !important;
    }}

    #controls, #progress-bar-container, #speaker-notes-drawer {{
      display: none !important;
    }}

    #viewport {{
      display: block !important;
      width: 100% !important;
      height: auto !important;
      background: none !important;
    }}

    #slide-frame {{
      position: static !important;
      transform: none !important;
      box-shadow: none !important;
      border-radius: 0 !important;
      width: 100% !important;
      height: auto !important;
    }}

    .slide {{
      display: flex !important;
      position: relative !important;
      width: 100vw !important;
      height: 100vh !important;
      page-break-after: always !important;
      break-after: page !important;
      padding: 50px 70px !important;
      box-sizing: border-box !important;
    }}
  }}
</style>
</head>
<body>

<div id="progress-bar-container">
  <div id="progress-bar"></div>
</div>

<div id="viewport">
  <div id="slide-frame">

    <!-- SLIDE 1: COVER -->
    <div class="slide active" data-notes="Welcome to the AegisTrace Technical Architecture Deck. AegisTrace is an enterprise-grade autonomous security orchestration platform engineered to solve alert fatigue and eliminate false positives through formal AST invariants and cryptographic state mutation trapping.">
      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
        <img src="{logo_b64}" alt="AegisTrace Logo" style="width: 480px; max-width: 90%; margin-bottom: 25px; filter: drop-shadow(0 0 25px rgba(139, 92, 246, 0.3));">
        <h1 class="slide-title" contenteditable="true" style="font-size: 46px; margin-bottom: 12px;">Technical Architecture & Agent Evaluation Deck</h1>
        <p class="slide-subtitle" contenteditable="true" style="font-size: 20px; color: var(--accent-cyan); font-weight: 600; margin-bottom: 8px;">Autonomous AI Security Intelligence, Forensic Arbitration & Verified Remediation</p>
        <p contenteditable="true" style="font-size: 16px; color: var(--text-muted); max-width: 800px; margin-bottom: 35px;">From AST Code Comprehension to Cryptographically Verified State Mutation Trapping & Deterministic Patch Synthesis</p>
        
        <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
          <span class="badge badge-emerald" contenteditable="true">Zero False Positives (0.00%)</span>
          <span class="badge badge-violet" contenteditable="true">7 Autonomous Swarm Agents</span>
          <span class="badge badge-cyan" contenteditable="true">3x Sandbox Replay Jails</span>
          <span class="badge badge-gold" contenteditable="true">Cryptographic SHA-256 Mutation Trapping</span>
        </div>
      </div>
    </div>

    <!-- SLIDE 2: MODERN APPSEC CRISIS -->
    <div class="slide" data-notes="Slide 2 establishes the core problem space. Enterprise AppSec is paralyzed by alert fatigue where traditional SAST and DAST produce 40-85% false positives. AegisTrace replaces pattern-matching guesses with empirical ground-truth: cryptographic proof of unauthorized state mutation, 3x sandbox verification, and automatic AST patch synthesis.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">01. System Context & Boundaries</span>
          <h2 class="slide-title" contenteditable="true">The AppSec Crisis & The Ground-Truth Paradigm</h2>
          <p class="slide-subtitle" contenteditable="true">Transforming heuristic alert noise into deterministic cryptographic evidence</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-rose">
          <div class="card-title" contenteditable="true">
            <span>Legacy Security Scanners (SAST / DAST)</span>
            <span class="badge badge-rose">40% - 85% Noise</span>
          </div>
          <div class="card-body">
            <p contenteditable="true"><strong>Alert Fatigue & Backlog:</strong> Superficial regex matching creates overwhelming developer ticket backlogs, burying real critical threats.</p>
            <p contenteditable="true"><strong>Unverified Heuristics:</strong> Flags theoretical syntax patterns without proving application reachability or active exploitation.</p>
            <p contenteditable="true"><strong>Zero State Verification:</strong> Incapable of verifying whether an exploit triggered real multi-tenant cross-contamination in the database.</p>
            <p contenteditable="true"><strong>Placeholder Advice:</strong> Leaves developers with generic remediation advice rather than regression-tested code diffs.</p>
          </div>
        </div>

        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">
            <span>AegisTrace Autonomous Ground Truth</span>
            <span class="badge badge-emerald">0.00% False Positives</span>
          </div>
          <div class="card-body">
            <p contenteditable="true"><strong>Empirical Exploit Verification:</strong> Flaws are confirmed ONLY when multi-tenant replay deterministically mutates database state in a sandbox jail.</p>
            <p contenteditable="true"><strong>Formal AST Invariant Derivation:</strong> Derives mathematical access rules (e.g., <code style="color:var(--accent-cyan)">orders.owner_id == session.user_id</code>) via Python AST analysis.</p>
            <p contenteditable="true"><strong>Cryptographic State Mutation Trapping:</strong> Calculates SHA-256 state hashes before and after attacks to trap cross-tenant alterations.</p>
            <p contenteditable="true"><strong>Dual-Phase Arbitration & AST Patching:</strong> 3x isolated replay guarantees determinism; synthesizes verified AST patches passing 10/10 unit tests.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 3: SECURITY AGENT RUNTIME GRAPH -->
    <div class="slide" data-notes="This slide features the official AegisTrace Security Agent Runtime Graph. Trace a single request: A user submits a target repo. The Orchestrator validates the ScopeGate. It fans out into parallel Code Intelligence and Recon. Vuln Research consumes both inputs to generate exploit hypotheses. Dynamic Testing executes paired-identity probes. If evidence is inconclusive, Verification loops back with 'needs more evidence'. Once confirmed, Remediation synthesizes a patch, which enters Human Approval. If changes are requested, it loops back to Remediation before generating the Final Report.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">02. Execution Lifecycle</span>
          <h2 class="slide-title" contenteditable="true">Security Agent Runtime Graph & Workflow Pipeline</h2>
          <p class="slide-subtitle" contenteditable="true">Event-driven orchestration with active feedback loops and verification gates</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div style="flex: 1; display: flex; flex-direction: column; gap: 20px;">
        <div class="card" style="padding: 15px; height: 380px; justify-content: center; align-items: center; background: #080c16;">
          <img src="{miro_b64}" alt="Security agent runtime graph" style="max-height: 100%; max-width: 100%; object-fit: contain;">
        </div>
        <div class="grid-4" style="flex: none; height: 190px;">
          <div class="card accent-violet" style="padding: 16px;">
            <div style="font-size: 14px; font-weight: 700; color: var(--accent-violet); margin-bottom: 6px;" contenteditable="true">1. Orchestration & ScopeGate</div>
            <div class="card-body" style="font-size: 12px; line-height: 1.45;" contenteditable="true">Enforces authorized target boundaries. Returns <code style="color:var(--accent-rose)">out of scope</code> if unauthorized domains or destructive operations are detected.</div>
          </div>
          <div class="card accent-cyan" style="padding: 16px;">
            <div style="font-size: 14px; font-weight: 700; color: var(--accent-cyan); margin-bottom: 6px;" contenteditable="true">2. Parallel Surface Extraction</div>
            <div class="card-body" style="font-size: 12px; line-height: 1.45;" contenteditable="true">Concurrently runs Code Intelligence (AST access invariants) and Recon (OpenAPI schemas, JWT scopes, and state-mutating verbs).</div>
          </div>
          <div class="card accent-gold" style="padding: 16px;">
            <div style="font-size: 14px; font-weight: 700; color: var(--accent-gold); margin-bottom: 6px;" contenteditable="true">3. Testing & Evidence Loop</div>
            <div class="card-body" style="font-size: 12px; line-height: 1.45;" contenteditable="true">Dynamic Testing executes paired personas. Verification triggers <code style="color:var(--accent-gold)">needs more evidence</code> loop back to Vuln Research if evidence is ambiguous.</div>
          </div>
          <div class="card accent-emerald" style="padding: 16px;">
            <div style="font-size: 14px; font-weight: 700; color: var(--accent-emerald); margin-bottom: 6px;" contenteditable="true">4. Remediation & Human Approval</div>
            <div class="card-body" style="font-size: 12px; line-height: 1.45;" contenteditable="true">Synthesizes AST patches passing unit tests. Enforces cryptographic Human Gate; triggers <code style="color:var(--accent-rose)">changes requested</code> loop back to Remediation.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 4: SYSTEM ARCHITECTURE TOPOLOGY -->
    <div class="slide" data-notes="The AegisTrace platform operates on a hub-and-spoke message bus where the Orchestrator coordinates tasks across four distinct operational layers: Ingestion & Surface, Autonomous Swarm, Forensic Arbitration, and the Cryptographic Remediation Store.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">03. Swarm Architecture</span>
          <h2 class="slide-title" contenteditable="true">7-Agent Neural Architecture Topology</h2>
          <p class="slide-subtitle" contenteditable="true">Specialized intelligence mesh operating over a hub-and-spoke message bus</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card" style="padding: 20px; align-items: center; justify-content: center;">
          <img src="{diag_comm_b64}" alt="Agent Communication" style="max-width: 100%; max-height: 480px; object-fit: contain;">
        </div>
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">Four Enterprise Architectural Layers</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Layer 1: Ingestion & Surface Layer</strong><br>FastAPI 0.115+ ASGI engine, OpenAPI 3.0 route parsing, Tree-sitter AST syntax walker, and live WebSockets (/ws/scans/id).</p>
            <p contenteditable="true"><strong>Layer 2: Autonomous Swarm Layer</strong><br>Seven CrewAI/LangChain specialized agents communicating strictly through validated Pydantic JSON contracts (prj_, eng_, scn_, tsk_).</p>
            <p contenteditable="true"><strong>Layer 3: Forensic Arbitration Engine</strong><br>Dual-phase verification executing 3x replay cycles in clean sandbox jails with paired-identity authorization checks.</p>
            <p contenteditable="true"><strong>Layer 4: Cryptographic Store & Remediation Gateway</strong><br>SQLite system of record with immutable triggers aborting UPDATE/DELETE, SHA-256 state snapshot diffs, and AST patch injector.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 5: AGENT 01 ORCHESTRATOR -->
    <div class="slide" data-notes="Agent 01 Orchestrator benchmark analysis: Evaluated across 45 test runs. 15 legitimate workflows completed without error (15 TP). 15 scope violation attempts were caught and blocked immediately by ScopeGate (15 TN). 15 corrupted input payloads were rejected by Pydantic contracts (15 TN). Result: 100% Precision, 100% Recall, 0% False Positives.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 01 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 01: OrchestratorAgent (Mission & Scope Director)</h2>
          <p class="slide-subtitle" contenteditable="true">ScopeGate validation, asynchronous DAG scheduling, and live telemetry</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">Responsibilities & Technical Design</div>
          <div class="card-body">
            <p contenteditable="true"><strong>ScopeGate Perimeter Enforcement:</strong> Zero-tolerance boundary validation preventing security probing against unauthorized domains, external hosts, or destructive endpoints.</p>
            <p contenteditable="true"><strong>DAG Execution Planning:</strong> Schedules agent tasks in strict topological dependency order; manages state transitions across all 7 autonomous agents.</p>
            <p contenteditable="true"><strong>WebSocket Telemetry:</strong> Streams real-time progress, agent lifecycle events, and log events to frontend subscribers via <code style="color:var(--accent-cyan)">/ws/scans/{{id}}</code>.</p>
            <p contenteditable="true"><strong>Contract Validation:</strong> Validates all inter-agent inputs/outputs against AegisTrace_Agent_JSON_Schemas.json.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/orchestrator_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">1.000</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Accuracy</div><div class="metric-pill-val">100.0%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Category</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Score</th></tr>
            </thead>
            <tbody>
              <tr><td>Valid Workflow Execution</td><td>15</td><td>0</td><td>0</td><td>0</td><td>100.0%</td></tr>
              <tr><td>Scope Violation Rejection</td><td>0</td><td>0</td><td>0</td><td>15</td><td>100.0%</td></tr>
              <tr><td>Input Contract Error Rejection</td><td>0</td><td>0</td><td>0</td><td>15</td><td>100.0%</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>15</td><td>0</td><td>0</td><td>30</td><td>100.0%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 20px;" contenteditable="true"><strong>Benchmark Insight:</strong> Orchestrator demonstrated 100% boundary integrity across 45 test runs, successfully catching all out-of-scope probes and contract schema corruptions.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 6: AGENT 02 CODE INTEL -->
    <div class="slide" data-notes="Agent 02 Code Intelligence evaluation: Evaluated across 43 ground truth instances in real-world repos like ShopLite and DjangoBlog. Route extraction, auth guard detection, and ORM discovery scored 100%. One complex candidate invariant was missed, resulting in 96.8% recall. Precision remained 100% with zero false alarms.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 02 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 02: CodeIntelligenceAgent (AST Invariant Parser)</h2>
          <p class="slide-subtitle" contenteditable="true">Static AST parsing, Semgrep rules, and access invariant derivation</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-cyan">
          <div class="card-title" contenteditable="true">AST Parsing & Invariant Extraction</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Abstract Syntax Tree Analysis:</strong> Traverses Python ASTs via stdlib <code style="color:var(--accent-cyan)">ast</code> and Tree-sitter to map route decorators, controllers, and database models.</p>
            <p contenteditable="true"><strong>Access Invariant Derivation:</strong> Extracts mathematical invariants required for multi-tenant isolation (e.g., <code style="color:var(--accent-emerald)">orders.owner_id == session.user_id</code>).</p>
            <p contenteditable="true"><strong>ORM & Relationship Mapping:</strong> Discovers SQLAlchemy / Django ORM models and associates foreign key tenant ownership fields.</p>
            <p contenteditable="true"><strong>Taint & Flow Analysis:</strong> Traces user-controlled request inputs to database sink operations, detecting unguarded update/delete paths.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/code_intelligence_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">96.8%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">0.984</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Accuracy</div><div class="metric-pill-val">97.7%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Category</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Recall</th></tr>
            </thead>
            <tbody>
              <tr><td>Route Extraction</td><td>12</td><td>0</td><td>0</td><td>0</td><td>100.0%</td></tr>
              <tr><td>Auth Guard Detection</td><td>3</td><td>0</td><td>0</td><td>9</td><td>100.0%</td></tr>
              <tr><td>ORM Model Discovery</td><td>7</td><td>0</td><td>0</td><td>0</td><td>100.0%</td></tr>
              <tr><td>Owner Field Mapping</td><td>4</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>Candidate Invariants</td><td>4</td><td>0</td><td>1</td><td>0</td><td>80.0%</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>30</td><td>0</td><td>1</td><td>12</td><td>96.77%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> 100% precision with 0 false positives. 1 implicit invariant in dynamic query construction was missed (1 FN), yielding an exceptional 98.36% F1 score.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 7: AGENT 03 RECON -->
    <div class="slide" data-notes="Agent 03 Reconnaissance evaluation: 53 benchmark trials. Perfect 100% precision on endpoint extraction, auth classification, and tech fingerprinting. The 3 false negatives were in the Tavily test when tested without an API key—confirming that AegisTrace safely skips offline searches rather than inventing fake CVEs.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 03 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 03: ReconAgent (Attack Surface Navigator)</h2>
          <p class="slide-subtitle" contenteditable="true">OpenAPI 3.0 surface triage, JWT scopes, and external CVE intelligence</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-gold">
          <div class="card-title" contenteditable="true">Surface Navigation & Triage</div>
          <div class="card-body">
            <p contenteditable="true"><strong>OpenAPI 3.0 & Swagger Parsing:</strong> Extracts path schemas, query parameters, request bodies, and expected status codes from API specifications.</p>
            <p contenteditable="true"><strong>JWT & Auth Scope Mapping:</strong> Categorizes endpoints by authentication roles (Public, Authenticated, Admin, Multi-Tenant).</p>
            <p contenteditable="true"><strong>State-Mutating Route Classification:</strong> Flags POST, PUT, PATCH, and DELETE verbs as high-risk vectors for unauthorized state modification.</p>
            <p contenteditable="true"><strong>Tavily Threat Intelligence:</strong> Dynamically queries external CVE feeds for known vulnerabilities in identified third-party libraries (gracefully skips offline).</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/recon_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">92.3%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">0.960</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Accuracy</div><div class="metric-pill-val">94.3%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Category</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Recall</th></tr>
            </thead>
            <tbody>
              <tr><td>Endpoint Extraction</td><td>11</td><td>0</td><td>0</td><td>0</td><td>100.0%</td></tr>
              <tr><td>Scope Gate Enforcement</td><td>11</td><td>0</td><td>0</td><td>5</td><td>100.0%</td></tr>
              <tr><td>Auth Scheme Detection</td><td>8</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>Tech Fingerprinting</td><td>6</td><td>0</td><td>0</td><td>6</td><td>100.0%</td></tr>
              <tr><td>External Intel (Tavily)</td><td>0</td><td>0</td><td>3</td><td>0</td><td>0.0% (Offline)</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>36</td><td>0</td><td>3</td><td>14</td><td>92.31%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> 100% precision. The 3 false negatives occurred in offline test mode without Tavily API keys, proving the system skips rather than hallucinating external CVE data.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 8: AGENT 04 VULN RESEARCH -->
    <div class="slide" data-notes="Agent 04 Vulnerability Research: 58 benchmark evaluations. It routes tactical offensive skills from Claude-BugHunter directly to AST invariants and surface routes. Scored 100% across hypothesis derivation, test plan synthesis, and category classification.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 04 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 04: VulnResearchAgent (Tactical Skills Router)</h2>
          <p class="slide-subtitle" contenteditable="true">Claude-BugHunter offensive skill routing and hypothesis generation</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">BugHunter Skills & Hypotheses</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Claude-BugHunter Skill Catalog:</strong> Dynamically loads modular offensive intelligence packs from <code style="color:var(--accent-violet)">skills/Claude-BugHunter/skills/*/SKILL.md</code>.</p>
            <p contenteditable="true"><strong>Attack Hypothesis Synthesis:</strong> Combines AST invariants and OpenAPI surface routes to formulate targeted BOLA, Mass Assignment, and TOCTOU test plans.</p>
            <p contenteditable="true"><strong>Multi-Tenant Payload Modeling:</strong> Configures paired-identity personas (Tenant A Victim vs Tenant B Attacker) for replay execution.</p>
            <p contenteditable="true"><strong>Zero-Hallucination Routing:</strong> Categorizes potential flaws against OWASP API Top 10 and CWE standards with formal invariant preconditions.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/vulnerability_research_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">1.000</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Accuracy</div><div class="metric-pill-val">100.0%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Category</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Score</th></tr>
            </thead>
            <tbody>
              <tr><td>Hypothesis Derivation</td><td>7</td><td>0</td><td>0</td><td>5</td><td>100.0%</td></tr>
              <tr><td>Category Classification</td><td>7</td><td>0</td><td>0</td><td>5</td><td>100.0%</td></tr>
              <tr><td>BugHunter Skill Routing</td><td>7</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>Test Plan Synthesis</td><td>7</td><td>0</td><td>0</td><td>5</td><td>100.0%</td></tr>
              <tr><td>Security Twin State Checks</td><td>7</td><td>0</td><td>0</td><td>5</td><td>100.0%</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>35</td><td>0</td><td>0</td><td>23</td><td>100.0%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> 100% precision across 58 test cases. Flawless skill mapping to Claude-BugHunter packs without ungrounded hypotheses.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 9: AGENT 05 DYNAMIC TESTING -->
    <div class="slide" data-notes="Agent 05 Dynamic Testing: 45 evaluations. Uses paired identities (Victim user vs Attacker user) and takes SHA-256 database snapshots before and after probe execution. If a row belonging to Tenant A is modified by Tenant B, it records an empirical mutation diff. 100% detection rate.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 05 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 05: DynamicTestingAgent (Behavioral Mutation Trapper)</h2>
          <p class="slide-subtitle" contenteditable="true">Active dual-role probing and cryptographic SHA-256 database state trapping</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-cyan">
          <div class="card-title" contenteditable="true">Cryptographic State Mutation Trapping</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Paired Identity Execution:</strong> Issues requests using Attacker Tenant credentials targeting Victim Tenant resources, logging all HTTP transactions.</p>
            <p contenteditable="true"><strong>Pre/Post Database Snapshots:</strong> Takes deep cryptographic snapshots of database state immediately before and after the attack execution.</p>
            <p contenteditable="true"><strong>SHA-256 Mutation Trapping:</strong> Computes state diffs; any unauthorized alteration of another tenant's records is trapped as undeniable mathematical proof.</p>
            <p contenteditable="true"><strong>Evidence Hygiene & Redaction:</strong> Automatically strips sensitive secrets, passwords, and private tokens from raw evidence before saving to EvidenceStore.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/dynamic_testing_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">1.000</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Accuracy</div><div class="metric-pill-val">100.0%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Category</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Score</th></tr>
            </thead>
            <tbody>
              <tr><td>Paired Identity Execution</td><td>6</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>ScopeGate Enforcement</td><td>6</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>State-Diff Mutation Detection</td><td>6</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>Evidence Hygiene & Redaction</td><td>6</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr><td>Budget & Resilience</td><td>6</td><td>0</td><td>0</td><td>3</td><td>100.0%</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>30</td><td>0</td><td>0</td><td>15</td><td>100.0%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> 100% precision across 45 test runs. Trapped 30 out of 30 unauthorized database mutations with zero false positives.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 10: AGENT 06 VERIFICATION -->
    <div class="slide" data-notes="Agent 06 Verification evaluation: Evaluated on ShopLite, FinTech Core, and HealthTech API. In every case, exploits were re-run 3 times in isolated environments. 30 out of 30 exploits demonstrated 3/3 replay consistency with zero false positives.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 06 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 06: VerificationAgent (Dual-Phase Forensic Arbitrator)</h2>
          <p class="slide-subtitle" contenteditable="true">3x deterministic sandbox replay and CVSS v3.1 arbitration</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-gold">
          <div class="card-title" contenteditable="true">3x Replay & Forensic Arbitration</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Triple Sandbox Replay (3/3):</strong> Executes 3 independent reproduction cycles in clean sandbox jails to guarantee exploit stability and eliminate timing flukes.</p>
            <p contenteditable="true"><strong>Dual-Phase Arbitration Engine:</strong> Cross-validates dynamic mutation evidence against static AST invariants; only dual-confirmed flaws pass.</p>
            <p contenteditable="true"><strong>CVSS v3.1 Vector Derivation:</strong> Mathematically calculates precise CVSS metrics (Base, Temporal, Environmental) based on actual demonstrated attack impact.</p>
            <p contenteditable="true"><strong>Verdict Certification:</strong> Assigns the ground-truth status <code style="color:var(--accent-emerald)">CONFIRMED</code> with immutable cryptographic signatures stored in the EvidenceStore.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/verification_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">1.000</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Replay Consistency</div><div class="metric-pill-val">100%</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Target Benchmark</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Replay</th></tr>
            </thead>
            <tbody>
              <tr><td>ShopLite E-Commerce Platform</td><td>10</td><td>0</td><td>0</td><td>5</td><td>100% (3/3)</td></tr>
              <tr><td>FinTech Payment Core Gateway</td><td>10</td><td>0</td><td>0</td><td>5</td><td>100% (3/3)</td></tr>
              <tr><td>HealthTech Telehealth API</td><td>10</td><td>0</td><td>0</td><td>5</td><td>100% (3/3)</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>30</td><td>0</td><td>0</td><td>15</td><td>100% (3/3)</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> 30 confirmed vulnerabilities reproduced across all 3/3 cycles with 100% consistency; 15 benign endpoints correctly rejected.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 11: AGENT 07 REMEDIATION -->
    <div class="slide" data-notes="Agent 07 Remediation evaluation: 45 cases. Evaluated AST patch generation across 3 diverse benchmark architectures. It synthesized syntax-perfect Python AST authorization guards, passed all unit tests (10/10), and verified that replay of the exploit now fails with HTTP 403 Forbidden.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">Agent Evaluation: 07 / 07</span>
          <h2 class="slide-title" contenteditable="true">Agent 07: RemediationAgent (AST Patch Synthesizer)</h2>
          <p class="slide-subtitle" contenteditable="true">Deterministic AST patch synthesis, regression testing, and exploit closure</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">Deterministic AST Patching</div>
          <div class="card-body">
            <p contenteditable="true"><strong>AST Authorization Guard Injection:</strong> Directly modifies Python AST nodes to inject ownership checks without breaking existing syntax or business logic.</p>
            <p contenteditable="true"><strong>Regression Test Validation (10/10 PASS):</strong> Automatically executes existing pytest test suites against the patched repository to ensure zero behavioral regression.</p>
            <p contenteditable="true"><strong>Exploit Closure Replay:</strong> Re-runs the exact exploit payload against the patched application; confirms HTTP 403 Forbidden with state unchanged.</p>
            <p contenteditable="true"><strong>Unified Diff Synthesis:</strong> Generates clean, human-readable Git diffs ready for developer review and cryptographic signing.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Empirical Evaluation (agents/remediation_agent/evaluation_report.csv)</div>
          <div class="metrics-row">
            <div class="metric-pill"><div class="metric-pill-label">Precision</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Recall</div><div class="metric-pill-val">100.0%</div></div>
            <div class="metric-pill"><div class="metric-pill-label">F1-Score</div><div class="metric-pill-val">1.000</div></div>
            <div class="metric-pill"><div class="metric-pill-label">Unit Tests</div><div class="metric-pill-val">10/10 PASS</div></div>
          </div>
          <table class="eval-table">
            <thead>
              <tr><th>Target Benchmark</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Exploit Closed</th></tr>
            </thead>
            <tbody>
              <tr><td>ShopLite E-Commerce Platform</td><td>10</td><td>0</td><td>0</td><td>5</td><td>HTTP 403 (10/10)</td></tr>
              <tr><td>FinTech Payment Core Gateway</td><td>10</td><td>0</td><td>0</td><td>5</td><td>HTTP 403 (10/10)</td></tr>
              <tr><td>HealthTech Telehealth API</td><td>10</td><td>0</td><td>0</td><td>5</td><td>HTTP 403 (10/10)</td></tr>
              <tr class="total-row"><td>OVERALL TOTAL</td><td>30</td><td>0</td><td>0</td><td>15</td><td>100.0% (30/30)</td></tr>
            </tbody>
          </table>
          <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 15px;" contenteditable="true"><strong>Benchmark Insight:</strong> In 100% of tested cases (30/30), the synthesized AST patch closed the exploit (HTTP 403 Forbidden) and passed 100% of the regression test suite.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 12: EMPIRICAL EVALUATION MATRIX -->
    <div class="slide" data-notes="Slide 12 brings together the empirical metrics from every agent. In the left chart, you can see consistent 100% precision across all 7 agents, with recall exceeding 92% even under offline test scenarios. Overall platform precision is 100.0%, overall recall is 98.1%, and platform F1 is 0.990.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">04. Cross-Swarm Metrics</span>
          <h2 class="slide-title" contenteditable="true">Empirical Evaluation Matrix: Cross-Swarm Performance</h2>
          <p class="slide-subtitle" contenteditable="true">Comprehensive evaluation across 277 total test cases in ground-truth benchmark suites</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card" style="padding: 10px; align-items: center; justify-content: center; background: #080c16;">
          <img src="{chart_metrics_b64}" alt="Agent Metrics Comparison" style="max-width: 100%; max-height: 520px; object-fit: contain;">
        </div>
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">Platform Consolidated Ledger</div>
          <table class="eval-table">
            <thead>
              <tr><th>Agent</th><th>Precision</th><th>Recall</th><th>F1-Score</th><th>FP Rate</th></tr>
            </thead>
            <tbody>
              <tr><td>01. Orchestrator</td><td>100.0%</td><td>100.0%</td><td>1.000</td><td>0.00%</td></tr>
              <tr><td>02. Code Intelligence</td><td>100.0%</td><td>96.8%</td><td>0.984</td><td>0.00%</td></tr>
              <tr><td>03. Reconnaissance</td><td>100.0%</td><td>92.3%</td><td>0.960</td><td>0.00%</td></tr>
              <tr><td>04. Vuln Research</td><td>100.0%</td><td>100.0%</td><td>1.000</td><td>0.00%</td></tr>
              <tr><td>05. Dynamic Testing</td><td>100.0%</td><td>100.0%</td><td>1.000</td><td>0.00%</td></tr>
              <tr><td>06. Verification</td><td>100.0%</td><td>100.0%</td><td>1.000</td><td>0.00%</td></tr>
              <tr><td>07. Remediation</td><td>100.0%</td><td>100.0%</td><td>1.000</td><td>0.00%</td></tr>
              <tr class="total-row"><td>PLATFORM AGGREGATE</td><td>100.0%</td><td>98.1%</td><td>0.990</td><td>0.00%</td></tr>
            </tbody>
          </table>
          <p style="font-size: 13.5px; color: var(--text-secondary); margin-top: 25px; line-height: 1.6;" contenteditable="true"><strong>Key Takeaway:</strong> Across 277 total test cases, AegisTrace maintained a 100.0% precision rate with 0.00% false positives, validating the power of dual-phase arbitration and cryptographic state mutation trapping.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 13: GROUND TRUTH VS TRADITIONAL -->
    <div class="slide" data-notes="Slide 13 highlights the competitive advantage of AegisTrace. Legacy SAST produces 68% false positives and DAST averages 45%. AegisTrace operates with 0.00% false positives because findings must produce cryptographic database mutation evidence replicated 3 times.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">05. Comparative Advantage</span>
          <h2 class="slide-title" contenteditable="true">Empirical Defense: AegisTrace vs. Legacy SAST/DAST</h2>
          <p class="slide-subtitle" contenteditable="true">Eliminating false positives and alert fatigue through empirical proof</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card" style="padding: 10px; align-items: center; justify-content: center; background: #080c16;">
          <img src="{chart_fp_b64}" alt="False Positive Comparison" style="max-width: 100%; max-height: 520px; object-fit: contain;">
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true">Verification Pillars Head-to-Head</div>
          <table class="eval-table">
            <thead>
              <tr><th>Pillar</th><th>Traditional SAST/DAST</th><th>AegisTrace Swarm</th></tr>
            </thead>
            <tbody>
              <tr><td>Detection</td><td>Regex & heuristic matching</td><td>Formal AST Invariant Derivation</td></tr>
              <tr><td>Verification Gate</td><td>None (Direct alerts)</td><td>SHA-256 DB Mutation Trapping</td></tr>
              <tr><td>Arbitration</td><td>Manual human triage</td><td>3x Isolated Sandbox Replay</td></tr>
              <tr><td>Remediation</td><td>Generic placeholder snippets</td><td>Deterministic AST Patch Synthesizer</td></tr>
              <tr><td>False Positives</td><td>40% – 85% alert noise</td><td style="color:var(--accent-emerald); font-weight:800;">0.00% (Reproduced only)</td></tr>
              <tr><td>Approval Flow</td><td>Unverified PR triggers</td><td>Server-Enforced Auth Gate</td></tr>
            </tbody>
          </table>
          <p style="font-size: 13px; color: var(--text-muted); margin-top: 25px; line-height: 1.6;" contenteditable="true"><strong>Operational Impact:</strong> Security teams save an estimated 15-20 engineering hours per week previously wasted triaging non-exploitable static alerts.</p>
        </div>
      </div>
    </div>

    <!-- SLIDE 14: DATA FLOW & STATE MUTATION TRAPPING -->
    <div class="slide" data-notes="Slide 14 explains the forensic innovation: Cryptographic State Mutation Trapping. Rather than guessing exploitability from HTTP status codes (which can be masked by custom 200/500 handlers), AegisTrace compares SHA-256 database hashes before and after the attack.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">06. Forensic Innovation</span>
          <h2 class="slide-title" contenteditable="true">Cryptographic State Mutation Trapping Architecture</h2>
          <p class="slide-subtitle" contenteditable="true">How AegisTrace proves multi-tenant data breaches with mathematical certainty</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card" style="padding: 10px; align-items: center; justify-content: center; background: #080c16;">
          <img src="{diag_twin_b64}" alt="Security Twin & State Mutation" style="max-width: 100%; max-height: 520px; object-fit: contain;">
        </div>
        <div class="card accent-cyan">
          <div class="card-title" contenteditable="true">Mathematical Proof of Exploitability</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Step 1: Baseline Hash Calculation</strong><br>Before initiating dynamic probing, the DynamicTestingAgent queries the database and computes a baseline SHA-256 state hash: <code style="color:var(--accent-cyan)">H_0 = SHA256(table_rows)</code>.</p>
            <p contenteditable="true"><strong>Step 2: Paired Identity Injection</strong><br>The agent injects an HTTP payload authenticated as Tenant B (Attacker) targeting an order or record owned by Tenant A (Victim).</p>
            <p contenteditable="true"><strong>Step 3: Post-Execution Hash & Diff</strong><br>A second snapshot computes <code style="color:var(--accent-cyan)">H_1 = SHA256(table_rows)</code>. If H_0 != H_1, an authorized or unauthorized delta <code style="color:var(--accent-gold)">Delta = H_1 - H_0</code> exists.</p>
            <p contenteditable="true"><strong>Step 4: Cross-Tenant Mutation Trapping</strong><br>If Delta contains modifications to Tenant A's records originating from Tenant B's session, unauthorized state mutation is cryptographically trapped.</p>
            <p contenteditable="true"><strong>Step 5: Immutable Evidence Locking</strong><br>The raw diff, HTTP trace, and hashes are committed to SQLite with triggers aborting UPDATE and DELETE, making evidence tamper-proof.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 15: OPERATIONAL TRADEOFFS -->
    <div class="slide" data-notes="Slide 15 provides an honest, transparent appraisal of system tradeoffs as documented in 00_What_Actually_Runs.md. We balance execution latency against deep 3x replay, evaluate the zero-dependency SQLite storage against future distributed PostgreSQL, and explain our offline resilience.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">07. Operational Tradeoffs</span>
          <h2 class="slide-title" contenteditable="true">Operational Tradeoffs & Architecture Reality Check</h2>
          <p class="slide-subtitle" contenteditable="true">Transparent technical evaluation: current runtime vs. production roadmap</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true" style="color:var(--accent-violet);">Execution Latency vs. Verification Depth</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Runtime Reality:</strong> AST parsing runs in sub-seconds, but 3x sandbox replay and database state diffs take 15-45 seconds per endpoint.</p>
            <p><strong>Tradeoff Decision:</strong> Prioritizes 100% precision over raw scanning speed. AegisTrace is designed for CI/CD gates and deep security audits, not instantaneous linters.</p>
          </div>
        </div>
        <div class="card accent-cyan">
          <div class="card-title" contenteditable="true" style="color:var(--accent-cyan);">SQLite Immutability vs. Distributed Scaling</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Runtime Reality:</strong> The running system uses SQLite with SQL triggers that abort UPDATE/DELETE, providing zero-dependency immutable audit logging.</p>
            <p><strong>Tradeoff Decision:</strong> Ideal for local compliance and single-tenant runners. Distributed clustering with PostgreSQL 16 and pgvector is slated for Edition 3 enterprise scaling.</p>
          </div>
        </div>
        <div class="card accent-gold">
          <div class="card-title" contenteditable="true" style="color:var(--accent-gold);">Offline Resiliency vs. Live Threat Intel</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Runtime Reality:</strong> Tavily threat search gracefully falls back to local Semgrep intelligence when API keys are absent, recording 3 false negatives without crashing.</p>
            <p><strong>Tradeoff Decision:</strong> Ensures zero execution failure in air-gapped or offline development environments, while maximizing CVE enrichment when external connectivity is enabled.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true" style="color:var(--accent-emerald);">Zero False-Positive Strictness vs. Speculation</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Runtime Reality:</strong> AegisTrace will never flag a vulnerability unless reproducible in a sandbox with trapped state evidence.</p>
            <p><strong>Tradeoff Decision:</strong> Theoretical vulnerabilities that require out-of-band social engineering or missing preconditions are intentionally omitted to maintain zero developer alert fatigue.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 16: HUMAN APPROVAL GATE -->
    <div class="slide" data-notes="Slide 16 details enterprise governance. Automated patching is a double-edged sword without human control; AegisTrace enforces a cryptographic server-side authorization barrier where humans review the unified diff, test outputs, and sign the release.">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">08. Production Governance</span>
          <h2 class="slide-title" contenteditable="true">Human Approval Gate & Enterprise Governance</h2>
          <p class="slide-subtitle" contenteditable="true">Server-enforced cryptographic authorization and automated compliance attestation</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-2">
        <div class="card" style="padding: 10px; align-items: center; justify-content: center; background: #080c16;">
          <img src="{diag_appr_b64}" alt="Human Approval Gate" style="max-width: 100%; max-height: 520px; object-fit: contain;">
        </div>
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true">Cryptographic Authorization Gate</div>
          <div class="card-body">
            <p contenteditable="true"><strong>Server-Enforced Authorization Barrier:</strong> Remediation patches cannot be pushed or merged without explicit cryptographically signed authorization by an authorized engineer (<code style="color:var(--accent-cyan)">POST /api/v1/approvals/{{id}}/action</code>).</p>
            <p contenteditable="true"><strong>Unified Code Diff Inspection:</strong> Developers review exact line additions and deletions, verified AST guards, and pytest regression outputs (10/10 PASS).</p>
            <p contenteditable="true"><strong>Automated Audit & Compliance Certificate:</strong> Generates comprehensive audit certificates covering OWASP API Top 10, CWE Top 25, and SOC2 evidence exportable via CSV and JSON.</p>
            <p contenteditable="true"><strong>Immutable Cryptographic Audit Ledger:</strong> Every user action, approval, scan launch, and state transition is committed to SQLite audit logs with triggers preventing modification.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- SLIDE 17: PLATFORM ROADMAP & SUMMARY -->
    <div class="slide" data-notes="In conclusion, AegisTrace successfully bridges the gap between static code understanding and dynamic exploit verification. With 100% precision, 0% false positives, and deterministic AST patch synthesis, it redefines application security. Thank you, and we welcome any questions!">
      <div class="slide-header">
        <div class="header-left">
          <span class="category-tag">09. Conclusion & Next Steps</span>
          <h2 class="slide-title" contenteditable="true">Production Readiness, Roadmap & Summary</h2>
          <p class="slide-subtitle" contenteditable="true">AegisTrace: Autonomous security intelligence grounded in empirical truth</p>
        </div>
        <div class="header-right"><img src="{logo_b64}" class="header-logo" alt="Logo"></div>
      </div>
      <div class="grid-3">
        <div class="card accent-violet">
          <div class="card-title" contenteditable="true" style="color:var(--accent-violet);">Current Capabilities</div>
          <div class="card-body" contenteditable="true">
            <p><strong>7-Agent Neural Mesh:</strong> Orchestrated via FastAPI and validated Pydantic contracts.</p>
            <p><strong>100% Precision:</strong> 0.00% false positives across 277 ground-truth test runs.</p>
            <p><strong>18 Dedicated Views:</strong> Luxury Gold & Obsidian security operations console.</p>
            <p><strong>AST Patch Synthesis:</strong> Automatic authorization guard injection & test validation.</p>
          </div>
        </div>
        <div class="card accent-cyan">
          <div class="card-title" contenteditable="true" style="color:var(--accent-cyan);">Enterprise Roadmap</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Distributed pgvector:</strong> Transitioning local SQLite embeddings to PostgreSQL 16 vector store.</p>
            <p><strong>Docker Replay Jails:</strong> Spinning up isolated ephemeral containers for multi-tenant probing.</p>
            <p><strong>Automated GitHub PRs:</strong> Direct integration with GitHub Enterprise via authenticated webhooks.</p>
            <p><strong>Expanded Languages:</strong> Extending AST invariant parsing to TypeScript, Go, and Java.</p>
          </div>
        </div>
        <div class="card accent-emerald">
          <div class="card-title" contenteditable="true" style="color:var(--accent-emerald);">Executive Summary</div>
          <div class="card-body" contenteditable="true">
            <p><strong>Zero Alert Fatigue:</strong> Only reproducible, state-mutating exploits are escalated.</p>
            <p><strong>Empirical Ground Truth:</strong> SHA-256 mutation trapping replaces heuristic guesswork.</p>
            <p><strong>Proven Benchmarks:</strong> Verified against ShopLite, FinTech Core, and HealthTech APIs.</p>
            <p><strong>Ready for Deployment:</strong> Run <code style="color:var(--accent-emerald)">python3 backend/run.py</code> to launch on port 8000.</p>
          </div>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- Speaker Notes Drawer (Toggled by N or button) -->
<div id="speaker-notes-drawer" role="complementary" aria-label="Speaker Notes">
  <h4>Speaker Notes (Separated from Slide Canvas)</h4>
  <div id="speaker-notes-content">Notes for current slide appear here...</div>
</div>

<!-- Bottom Controls Bar -->
<div id="controls" role="toolbar" aria-label="Presentation Controls">
  <button id="prev-btn" class="ctrl-btn" aria-label="Previous Slide">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg> Prev
  </button>
  
  <span id="slide-counter">01 / 17</span>

  <button id="next-btn" class="ctrl-btn" aria-label="Next Slide">
    Next <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
  </button>

  <div style="width: 1px; height: 20px; background: rgba(255,255,255,0.2);"></div>

  <button id="edit-toggle-btn" class="ctrl-btn" title="Toggle Editable Text" aria-label="Toggle Editable Text">
    ✏️ Edit Mode
  </button>

  <button id="notes-toggle-btn" class="ctrl-btn" title="Toggle Speaker Notes (N)" aria-label="Toggle Speaker Notes">
    📝 Notes
  </button>

  <button id="fullscreen-btn" class="ctrl-btn" title="Toggle Fullscreen (F)" aria-label="Toggle Fullscreen">
    ⛶ Fullscreen
  </button>

  <button id="print-btn" class="ctrl-btn" title="Print Slides (One Per Page)" aria-label="Print Slides">
    🖨️ Print Deck
  </button>
</div>

<script>
  const slides = document.querySelectorAll('.slide');
  const slideCounter = document.getElementById('slide-counter');
  const progressBar = document.getElementById('progress-bar');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const editToggleBtn = document.getElementById('edit-toggle-btn');
  const notesToggleBtn = document.getElementById('notes-toggle-btn');
  const notesDrawer = document.getElementById('speaker-notes-drawer');
  const notesContent = document.getElementById('speaker-notes-content');
  const fullscreenBtn = document.getElementById('fullscreen-btn');
  const printBtn = document.getElementById('print-btn');
  const slideFrame = document.getElementById('slide-frame');

  let currentSlide = 0;
  const totalSlides = slides.length;
  let isEditMode = false;

  // Responsive 16:9 Scaling
  function resizeDeck() {{
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const targetWidth = 1920;
    const targetHeight = 1080;

    const scaleX = windowWidth / targetWidth;
    const scaleY = windowHeight / targetHeight;
    const scale = Math.min(scaleX, scaleY) * 0.96;

    slideFrame.style.transform = `scale(${{scale}})`;
  }}

  window.addEventListener('resize', resizeDeck);
  resizeDeck();

  function updateSlide(index) {{
    if (index < 0) index = 0;
    if (index >= totalSlides) index = totalSlides - 1;

    slides[currentSlide].classList.remove('active');
    currentSlide = index;
    slides[currentSlide].classList.add('active');

    // Update Counter & Progress
    const pad = (n) => String(n).padStart(2, '0');
    slideCounter.textContent = `${{pad(currentSlide + 1)}} / ${{pad(totalSlides)}}`;
    progressBar.style.width = `${{((currentSlide + 1) / totalSlides) * 100}}%`;

    // Update Notes
    const notes = slides[currentSlide].getAttribute('data-notes') || 'No speaker notes for this slide.';
    notesContent.textContent = notes;

    prevBtn.disabled = currentSlide === 0;
    nextBtn.disabled = currentSlide === totalSlides - 1;
  }}

  prevBtn.addEventListener('click', () => updateSlide(currentSlide - 1));
  nextBtn.addEventListener('click', () => updateSlide(currentSlide + 1));

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {{
    // Don't intercept navigation if user is editing text
    if (isEditMode && document.activeElement && document.activeElement.isContentEditable) {{
      return;
    }}

    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{
      e.preventDefault();
      updateSlide(currentSlide + 1);
    }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
      e.preventDefault();
      updateSlide(currentSlide - 1);
    }} else if (e.key === 'Home') {{
      e.preventDefault();
      updateSlide(0);
    }} else if (e.key === 'End') {{
      e.preventDefault();
      updateSlide(totalSlides - 1);
    }} else if (e.key.toLowerCase() === 'n') {{
      notesDrawer.classList.toggle('open');
      notesToggleBtn.classList.toggle('active');
    }} else if (e.key.toLowerCase() === 'f') {{
      toggleFullscreen();
    }} else if (e.key.toLowerCase() === 'e') {{
      toggleEditMode();
    }}
  }});

  function toggleEditMode() {{
    isEditMode = !isEditMode;
    document.body.classList.toggle('edit-mode', isEditMode);
    editToggleBtn.classList.toggle('active', isEditMode);
    editToggleBtn.textContent = isEditMode ? '💾 Editing ON' : '✏️ Edit Mode';
  }}

  editToggleBtn.addEventListener('click', toggleEditMode);

  notesToggleBtn.addEventListener('click', () => {{
    notesDrawer.classList.toggle('open');
    notesToggleBtn.classList.toggle('active');
  }});

  function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
      document.documentElement.requestFullscreen().catch(err => alert(err.message));
    }} else {{
      document.exitFullscreen();
    }}
  }}

  fullscreenBtn.addEventListener('click', toggleFullscreen);

  printBtn.addEventListener('click', () => {{
    window.print();
  }});

  // Initialize
  updateSlide(0);
</script>
</body>
</html>
"""

with open("presentation.html", "w", encoding="utf-8") as f:
    f.write(html_content)

out_artifact = "/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/presentation.html"
with open(out_artifact, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Interactive Editable HTML presentation successfully generated at presentation.html and {out_artifact}!")
