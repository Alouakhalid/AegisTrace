import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

LOGO_PATH = "/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/.user_uploaded/media_1795281199884.png"
MIRO_GRAPH_PATH = "/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/.user_uploaded/media_1795282497648.png"

DIAG_DIR = "AegisTrace_Documentation/11_Architecture_Diagrams"
CHARTS_DIR = "charts"

# Color Palette
BG_COLOR = RGBColor(10, 14, 26)         # Obsidian #0A0E1A
CARD_BG = RGBColor(17, 24, 39)          # Dark Slate #111827
CARD_BORDER = RGBColor(55, 65, 81)      # Gray #374151
PRIMARY_VIOLET = RGBColor(139, 92, 246) # Electric Violet #8B5CF6
CYAN_ACCENT = RGBColor(6, 182, 212)     # Cyber Cyan #06B6D4
GOLD_ACCENT = RGBColor(212, 175, 55)    # Luxury Gold #D4AF37
EMERALD_GREEN = RGBColor(16, 185, 129)  # Emerald #10B981
ROSE_RED = RGBColor(239, 68, 68)        # Rose #EF4444
TEXT_WHITE = RGBColor(248, 250, 252)    # Pure White
TEXT_MUTED = RGBColor(148, 163, 184)    # Silver Muted #94A3B8

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

def set_slide_bg(slide):
    background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    background.fill.solid()
    background.fill.fore_color.rgb = BG_COLOR
    background.line.color.rgb = BG_COLOR
    return background

def add_header(slide, title, category="AEGISTRACE ARCHITECTURE & EVALUATION", subtitle=""):
    # Header container
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(10.5), Inches(1.1))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_cat = tf.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = PRIMARY_VIOLET

    p_title = tf.add_paragraph()
    p_title.text = title
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE

    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(11)
        p_sub.font.color.rgb = TEXT_MUTED

    # Header corner logo
    if os.path.exists(LOGO_PATH):
        slide.shapes.add_picture(LOGO_PATH, Inches(11.5), Inches(0.35), width=Inches(1.1))

def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1)
    return shape

def add_speaker_notes(slide, notes_text):
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = notes_text

# ==============================================================================
# SLIDE 1: COVER & EXECUTIVE SUMMARY
# ==============================================================================
s1 = prs.slides.add_slide(blank_layout)
set_slide_bg(s1)

# Large Hero Logo
if os.path.exists(LOGO_PATH):
    s1.shapes.add_picture(LOGO_PATH, Inches(4.66), Inches(0.8), width=Inches(4.0))

title_box = s1.shapes.add_textbox(Inches(1.0), Inches(4.3), Inches(11.333), Inches(2.8))
tf1 = title_box.text_frame
tf1.word_wrap = True
tf1.margin_left = tf1.margin_right = tf1.margin_top = tf1.margin_bottom = 0

p = tf1.paragraphs[0]
p.text = "AegisTrace (2.0) Technical Architecture Deck"
p.font.size = Pt(32)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.alignment = PP_ALIGN.CENTER

p2 = tf1.add_paragraph()
p2.text = "Autonomous AI Security Intelligence, Forensic Arbitration & Verified Remediation"
p2.font.size = Pt(16)
p2.font.bold = True
p2.font.color.rgb = CYAN_ACCENT
p2.alignment = PP_ALIGN.CENTER

p3 = tf1.add_paragraph()
p3.text = "Comprehensive 7-Agent Neural Mesh Architecture & Empirical Benchmark Evaluations"
p3.font.size = Pt(13)
p3.font.color.rgb = TEXT_MUTED
p3.alignment = PP_ALIGN.CENTER

# Pill Badges Container
badge_y = Inches(6.0)
badges = [
    ("Zero False Positives (0.00%)", EMERALD_GREEN),
    ("7 Autonomous Swarm Agents", PRIMARY_VIOLET),
    ("3x Sandbox Replay Jails", CYAN_ACCENT),
    ("AST Invariant & Mutation Trapping", GOLD_ACCENT)
]
bx = Inches(1.3)
for text, color in badges:
    b = add_card(s1, bx, badge_y, Inches(2.55), Inches(0.48), CARD_BG, color)
    tb = s1.shapes.add_textbox(bx, badge_y, Inches(2.55), Inches(0.48))
    tbf = tb.text_frame
    tbf.word_wrap = False
    p = tbf.paragraphs[0]
    p.text = text
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = color
    p.alignment = PP_ALIGN.CENTER
    bx += Inches(2.7)

add_speaker_notes(s1, "Welcome to the AegisTrace Technical Architecture Deck. AegisTrace is an enterprise-grade autonomous security orchestration platform engineered to solve the crisis of alert fatigue and high false-positive rates in modern AppSec. In this presentation, we explore the system boundaries, runtime graph, 7-agent neural mesh, and rigorous empirical evaluations of each agent.")

# ==============================================================================
# SLIDE 2: MODERN APPSEC CRISIS & THE GROUND-TRUTH PARADIGM
# ==============================================================================
s2 = prs.slides.add_slide(blank_layout)
set_slide_bg(s2)
add_header(s2, "The AppSec Crisis & The Ground-Truth Paradigm", "01. System Context & Boundaries", "Transforming heuristic alert noise into deterministic cryptographic evidence")

# Left Card: Traditional SAST / DAST
add_card(s2, Inches(0.8), Inches(1.7), Inches(5.6), Inches(5.2), CARD_BG, ROSE_RED)
tb = s2.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.0), Inches(4.8))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Legacy Security Scanners (SAST / DAST)"
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = ROSE_RED

bullets_trad = [
    ("40% - 85% False-Positive Rates: ", "Superficial regex matching creates overwhelming developer alert fatigue and ticket triage backlog."),
    ("Unverified Heuristics: ", "Tools flag potential syntax patterns without executing code or proving actual reachability."),
    ("Zero State Verification: ", "No ability to detect whether an attack caused a real multi-tenant data breach or database mutation."),
    ("Placeholder Advice: ", "Developers receive generic boilerplate remediation advice instead of verified AST code patches."),
    ("Unbounded Testing: ", "Lack of strict perimeter containment risks executing disruptive scans against production dependencies.")
]
for title, desc in bullets_trad:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    run1 = p.add_run()
    run1.text = title
    run1.font.bold = True
    run1.font.size = Pt(11)
    run1.font.color.rgb = TEXT_WHITE
    run2 = p.add_run()
    run2.text = desc
    run2.font.size = Pt(10.5)
    run2.font.color.rgb = TEXT_MUTED

# Right Card: AegisTrace Autonomous Paradigm
add_card(s2, Inches(6.9), Inches(1.7), Inches(5.6), Inches(5.2), CARD_BG, EMERALD_GREEN)
tb = s2.shapes.add_textbox(Inches(7.2), Inches(1.9), Inches(5.0), Inches(4.8))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "AegisTrace Autonomous Ground Truth"
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

bullets_aegis = [
    ("0.00% False Positives: ", "Findings are certified ONLY when multi-tenant exploit replay deterministically succeeds in an isolated sandbox."),
    ("Formal AST Invariant Derivation: ", "Analyzes Python AST structures to mathematically model access boundaries (e.g., owner_id == session.user_id)."),
    ("Cryptographic State Mutation Trapping: ", "Calculates SHA-256 database hashes before and after attacks; traps unauthorized cross-tenant row mutations."),
    ("Dual-Phase Forensic Arbitration: ", "Executes 3x independent sandbox replays to eliminate network jitter and race conditions."),
    ("Deterministic AST Patch Synthesis: ", "Injects verified authorization guards and tests against regression test suites (10/10 PASS).")
]
for title, desc in bullets_aegis:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    run1 = p.add_run()
    run1.text = title
    run1.font.bold = True
    run1.font.size = Pt(11)
    run1.font.color.rgb = TEXT_WHITE
    run2 = p.add_run()
    run2.text = desc
    run2.font.size = Pt(10.5)
    run2.font.color.rgb = TEXT_MUTED

add_speaker_notes(s2, "Slide 2 establishes the core problem space. Enterprise AppSec is paralyzed by alert fatigue where traditional SAST and DAST produce 40-85% false positives. AegisTrace replaces pattern-matching guesses with empirical ground-truth: cryptographic proof of unauthorized state mutation, 3x sandbox verification, and automatic AST patch synthesis.")

# ==============================================================================
# SLIDE 3: SECURITY AGENT RUNTIME GRAPH (MIRO DIAGRAM)
# ==============================================================================
s3 = prs.slides.add_slide(blank_layout)
set_slide_bg(s3)
add_header(s3, "Security Agent Runtime Graph & Workflow Pipeline", "02. Execution Lifecycle", "Event-driven orchestration with active feedback loops and verification gates")

# Add Card for the diagram
add_card(s3, Inches(0.8), Inches(1.6), Inches(11.733), Inches(3.2), CARD_BG, CARD_BORDER)

if os.path.exists(MIRO_GRAPH_PATH):
    s3.shapes.add_picture(MIRO_GRAPH_PATH, Inches(0.9), Inches(1.7), width=Inches(11.533))

# Bottom Cards: Explaining the Workflow and Loops
loops = [
    ("Orchestration & ScopeGate", "Validates user request, sets authorization boundaries, and blocks out-of-scope probes. Returns 'out of scope' if perimeter breached.", PRIMARY_VIOLET),
    ("Parallel Surface Intelligence", "Concurrently executes Code Intelligence (AST access invariants) and Reconnaissance (OpenAPI surface & route mapping).", CYAN_ACCENT),
    ("Dynamic Testing & Replay", "Synthesizes multi-role HTTP attack payloads; traps database mutations. Verification requests 'needs more evidence' if inconclusive.", GOLD_ACCENT),
    ("Remediation & Human Gate", "Synthesizes AST patches and passes unit tests. Cryptographic Human Approval gate accepts or issues 'changes requested'.", EMERALD_GREEN)
]
lx = Inches(0.8)
for title, desc, col in loops:
    add_card(s3, lx, Inches(5.0), Inches(2.78), Inches(1.9), CARD_BG, col)
    tb = s3.shapes.add_textbox(lx + Inches(0.15), Inches(5.1), Inches(2.48), Inches(1.7))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = col
    p2 = tf.add_paragraph()
    p2.text = desc
    p2.space_before = Pt(4)
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = TEXT_MUTED
    lx += Inches(2.98)

add_speaker_notes(s3, "This slide features the official AegisTrace Security Agent Runtime Graph. Trace a single request: A user submits a target repo. The Orchestrator validates the ScopeGate. It fans out into parallel Code Intelligence and Recon. Vuln Research consumes both inputs to generate exploit hypotheses. Dynamic Testing executes paired-identity probes. If evidence is inconclusive, Verification loops back with 'needs more evidence'. Once confirmed, Remediation synthesizes a patch, which enters Human Approval. If changes are requested, it loops back to Remediation before generating the Final Report.")

# ==============================================================================
# SLIDE 4: 7-AGENT NEURAL ARCHITECTURE TOPOLOGY
# ==============================================================================
s4 = prs.slides.add_slide(blank_layout)
set_slide_bg(s4)
add_header(s4, "7-Agent Neural Architecture Topology", "03. Swarm Architecture", "Specialized intelligence mesh operating over a hub-and-spoke message bus")

# Diagram on the left
add_card(s4, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
d_path = os.path.join(DIAG_DIR, "d04c_comm.png")
if os.path.exists(d_path):
    s4.shapes.add_picture(d_path, Inches(0.9), Inches(2.2), width=Inches(5.4))
else:
    d1 = os.path.join(DIAG_DIR, "d02_agents.png")
    if os.path.exists(d1):
        s4.shapes.add_picture(d1, Inches(1.2), Inches(1.7), height=Inches(5.0))

# Right panel: Architectural Layers
add_card(s4, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, PRIMARY_VIOLET)
tb = s4.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Four Enterprise Architectural Layers"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE

layers = [
    ("Layer 1: Ingestion & Surface Layer", "FastAPI ASGI engine, OpenAPI 3.0 schema parsing, Tree-sitter AST traversal, and real-time WebSocket telemetry stream (/ws/scans/{id})."),
    ("Layer 2: Autonomous Agent Swarm Layer", "Seven CrewAI/LangChain specialized agents communicating via validated JSON schemas and structured Pydantic contracts."),
    ("Layer 3: Forensic Arbitration Engine", "Dual-phase verification executing 3x replay cycles in isolated sandbox environments with paired-identity authorization checks."),
    ("Layer 4: Cryptographic Store & Remediation Gateway", "SQLite system of record with immutable triggers aborting UPDATE/DELETE, SHA-256 state snapshot hashes, and AST patch injector.")
]
for title, desc in layers:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    run1 = p.add_run()
    run1.text = title + "\n"
    run1.font.bold = True
    run1.font.size = Pt(11)
    run1.font.color.rgb = CYAN_ACCENT
    run2 = p.add_run()
    run2.text = desc
    run2.font.size = Pt(10)
    run2.font.color.rgb = TEXT_MUTED

add_speaker_notes(s4, "The AegisTrace platform operates on a hub-and-spoke message bus where the Orchestrator coordinates tasks across four distinct operational layers: Ingestion & Surface, Autonomous Swarm, Forensic Arbitration, and the Cryptographic Remediation Store.")

# ==============================================================================
# SLIDE 5: AGENT 01 - ORCHESTRATOR AGENT
# ==============================================================================
s5 = prs.slides.add_slide(blank_layout)
set_slide_bg(s5)
add_header(s5, "Agent 01: OrchestratorAgent (Mission & Scope Director)", "Agent Evaluation: 01 / 07", "ScopeGate validation, asynchronous DAG scheduling, and live telemetry")

# Left Column: Overview & Capabilities
add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s5.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Responsibilities & Technical Design"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = PRIMARY_VIOLET

items_orch = [
    ("ScopeGate Enforcement: ", "Zero-tolerance boundary validation preventing security probing against unauthorized domains, IPs, or destructive endpoints."),
    ("DAG Execution Planning: ", "Schedules agent tasks in strict topological order; manages state transitions across 7 autonomous agents."),
    ("WebSocket Telemetry: ", "Streams real-time progress, agent lifecycle events, and log events to frontend subscribers via /ws/scans/{id}."),
    ("Contract Validation: ", "Validates all inter-agent inputs/outputs against AegisTrace_Agent_JSON_Schemas.json (prj_, eng_, scn_, tsk_).")
]
for title, desc in items_orch:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Empirical Evaluation Data
add_card(s5, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s5.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Summary stats pills
pill_y = Inches(2.3)
stats = [("Precision", "100.0%"), ("Recall", "100.0%"), ("F1-Score", "1.000"), ("Accuracy", "100.0%")]
sx = Inches(7.0)
for label, val in stats:
    add_card(s5, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), PRIMARY_VIOLET)
    t = s5.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = EMERALD_GREEN
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

# Table of evaluation
rows_data = [
    ["Test Category", "TP", "FP", "FN", "TN", "Score"],
    ["Valid Workflow", "15", "0", "0", "0", "100.0%"],
    ["Scope Violation", "0", "0", "0", "15", "100.0%"],
    ["Input Error Rejection", "0", "0", "0", "15", "100.0%"],
    ["OVERALL TOTAL", "15", "0", "0", "30", "100.0%"]
]
table_shape = s5.shapes.add_table(5, 6, Inches(7.0), Inches(3.2), Inches(5.333), Inches(2.2))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_data):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9.5)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = PRIMARY_VIOLET
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 4:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s5.shapes.add_textbox(Inches(7.0), Inches(5.6), Inches(5.333), Inches(1.0))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: The Orchestrator achieved a flawless 100% precision and recall across 45 total test cases, demonstrating 100% rejection of unauthorized hosts and corrupted schema contracts."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s5, "Agent 01 Orchestrator benchmark analysis: Evaluated across 45 test runs. 15 legitimate workflows completed without error (15 TP). 15 scope violation attempts were caught and blocked immediately by ScopeGate (15 TN). 15 corrupted input payloads were rejected by Pydantic contracts (15 TN). Result: 100% Precision, 100% Recall, 0% False Positives.")

# ==============================================================================
# SLIDE 6: AGENT 02 - CODE INTELLIGENCE AGENT
# ==============================================================================
s6 = prs.slides.add_slide(blank_layout)
set_slide_bg(s6)
add_header(s6, "Agent 02: CodeIntelligenceAgent (AST Invariant Parser)", "Agent Evaluation: 02 / 07", "Static AST parsing, Semgrep rules, and access invariant derivation")

# Left Column: Overview
add_card(s6, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s6.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "AST Parsing & Invariant Extraction"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = CYAN_ACCENT

items_ci = [
    ("Abstract Syntax Tree Analysis: ", "Parses Python ASTs via stdlib ast and Tree-sitter to map route decorators, controllers, and database models."),
    ("Access Invariant Derivation: ", "Extracts mathematical invariants required for multi-tenant isolation (e.g., orders.owner_id == session.user_id)."),
    ("ORM & Relationship Mapping: ", "Discovers SQLAlchemy / Django ORM models and associates foreign key tenant ownership fields."),
    ("Taint & Flow Analysis: ", "Traces user-controlled request inputs to database sink operations, detecting unguarded update/delete paths.")
]
for title, desc in items_ci:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s6, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s6.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_ci = [("Precision", "100.0%"), ("Recall", "96.8%"), ("F1-Score", "0.984"), ("Accuracy", "97.7%")]
sx = Inches(7.0)
for label, val in stats_ci:
    add_card(s6, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), CYAN_ACCENT)
    t = s6.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = CYAN_ACCENT
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_ci = [
    ["Category", "TP", "FP", "FN", "TN", "Recall"],
    ["Route Extraction", "12", "0", "0", "0", "100.0%"],
    ["Auth Guard Detection", "3", "0", "0", "9", "100.0%"],
    ["ORM Model Discovery", "7", "0", "0", "0", "100.0%"],
    ["Owner Field Mapping", "4", "0", "0", "3", "100.0%"],
    ["Candidate Invariants", "4", "0", "1", "0", "80.0%"],
    ["OVERALL TOTAL", "30", "0", "1", "12", "96.77%"]
]
table_shape = s6.shapes.add_table(7, 6, Inches(7.0), Inches(3.1), Inches(5.333), Inches(2.5))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_ci):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = CYAN_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 6:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s6.shapes.add_textbox(Inches(7.0), Inches(5.8), Inches(5.333), Inches(0.8))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: Achieved 100% precision across all AST operations. 1 subtle implicit tenant invariant was missed (1 FN), yielding an exceptional 96.8% recall and 0.984 F1 score across 43 targets."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s6, "Agent 02 Code Intelligence evaluation: Evaluated across 43 ground truth instances in real-world repos like ShopLite and DjangoBlog. Route extraction, auth guard detection, and ORM discovery scored 100%. One complex candidate invariant was missed, resulting in 96.8% recall. Precision remained 100% with zero false alarms.")

# ==============================================================================
# SLIDE 7: AGENT 03 - RECON AGENT
# ==============================================================================
s7 = prs.slides.add_slide(blank_layout)
set_slide_bg(s7)
add_header(s7, "Agent 03: ReconAgent (Attack Surface Navigator)", "Agent Evaluation: 03 / 07", "OpenAPI 3.0 surface triage, JWT scopes, and external CVE intelligence")

# Left Column: Overview
add_card(s7, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s7.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Surface Navigation & Triage"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = GOLD_ACCENT

items_rc = [
    ("OpenAPI 3.0 & Swagger Parsing: ", "Extracts path schemas, query parameters, request bodies, and expected status codes from API specifications."),
    ("JWT & Auth Scope Mapping: ", "Categorizes endpoints by authentication roles (Public, Authenticated, Admin, Multi-Tenant)."),
    ("State-Mutating Route Classification: ", "Flags POST, PUT, PATCH, and DELETE verbs as high-risk vectors for unauthorized state modification."),
    ("Tavily Threat Intelligence: ", "Dynamically queries external CVE feeds for known vulnerabilities in identified third-party libraries (gracefully skips offline).")
]
for title, desc in items_rc:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s7, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s7.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_rc = [("Precision", "100.0%"), ("Recall", "92.3%"), ("F1-Score", "0.960"), ("Accuracy", "94.3%")]
sx = Inches(7.0)
for label, val in stats_rc:
    add_card(s7, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), GOLD_ACCENT)
    t = s7.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = GOLD_ACCENT
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_rc = [
    ["Category", "TP", "FP", "FN", "TN", "Recall"],
    ["Endpoint Extraction", "11", "0", "0", "0", "100.0%"],
    ["Scope Gate Enforcement", "11", "0", "0", "5", "100.0%"],
    ["Auth Scheme Detection", "8", "0", "0", "3", "100.0%"],
    ["Tech Fingerprinting", "6", "0", "0", "6", "100.0%"],
    ["External Intel (Tavily)", "0", "0", "3", "0", "0.0% (Offline)"],
    ["OVERALL TOTAL", "36", "0", "3", "14", "92.31%"]
]
table_shape = s7.shapes.add_table(7, 6, Inches(7.0), Inches(3.1), Inches(5.333), Inches(2.5))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_rc):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = GOLD_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 6:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s7.shapes.add_textbox(Inches(7.0), Inches(5.8), Inches(5.333), Inches(0.8))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: 100% precision across all surface extraction. The 3 false negatives stem from deliberate offline runs where Tavily API keys were omitted, confirming safe fallback without hallucination."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s7, "Agent 03 Reconnaissance evaluation: 53 benchmark trials. Perfect 100% precision on endpoint extraction, auth classification, and tech fingerprinting. The 3 false negatives were in the Tavily test when tested without an API key—confirming that AegisTrace safely skips offline searches rather than inventing fake CVEs.")

# ==============================================================================
# SLIDE 8: AGENT 04 - VULNERABILITY RESEARCH AGENT
# ==============================================================================
s8 = prs.slides.add_slide(blank_layout)
set_slide_bg(s8)
add_header(s8, "Agent 04: VulnResearchAgent (Tactical Skills Router)", "Agent Evaluation: 04 / 07", "Claude-BugHunter offensive skill routing and hypothesis generation")

# Left Column: Overview
add_card(s8, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s8.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "BugHunter Skills & Hypotheses"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = PRIMARY_VIOLET

items_vr = [
    ("Claude-BugHunter Skill Catalog: ", "Dynamically loads modular offensive intelligence packs from skills/Claude-BugHunter/skills/*/SKILL.md."),
    ("Attack Hypothesis Synthesis: ", "Combines AST invariants and OpenAPI surface routes to formulate targeted BOLA, Mass Assignment, and TOCTOU test plans."),
    ("Multi-Tenant Payload Modeling: ", "Configures paired-identity personas (Tenant A Victim vs Tenant B Attacker) for replay execution."),
    ("Zero-Hallucination Routing: ", "Categorizes potential flaws against OWASP API Top 10 and CWE standards with formal invariant preconditions.")
]
for title, desc in items_vr:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s8, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s8.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_vr = [("Precision", "100.0%"), ("Recall", "100.0%"), ("F1-Score", "1.000"), ("Accuracy", "100.0%")]
sx = Inches(7.0)
for label, val in stats_vr:
    add_card(s8, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), PRIMARY_VIOLET)
    t = s8.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = EMERALD_GREEN
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_vr = [
    ["Category", "TP", "FP", "FN", "TN", "Score"],
    ["Hypothesis Derivation", "7", "0", "0", "5", "100.0%"],
    ["Category Classification", "7", "0", "0", "5", "100.0%"],
    ["BugHunter Skill Routing", "7", "0", "0", "3", "100.0%"],
    ["Test Plan Synthesis", "7", "0", "0", "5", "100.0%"],
    ["Security Twin State Checks", "7", "0", "0", "5", "100.0%"],
    ["OVERALL TOTAL", "35", "0", "0", "23", "100.0%"]
]
table_shape = s8.shapes.add_table(7, 6, Inches(7.0), Inches(3.1), Inches(5.333), Inches(2.5))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_vr):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = PRIMARY_VIOLET
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 6:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s8.shapes.add_textbox(Inches(7.0), Inches(5.8), Inches(5.333), Inches(0.8))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: Achieved 100% precision and recall across all 58 test cases. Flawless skill mapping to Claude-BugHunter packs (IDOR, mass assignment, race conditions) without ungrounded hallucinations."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s8, "Agent 04 Vulnerability Research: 58 benchmark evaluations. It routes tactical offensive skills from Claude-BugHunter directly to AST invariants and surface routes. Scored 100% across hypothesis derivation, test plan synthesis, and category classification.")

# ==============================================================================
# SLIDE 9: AGENT 05 - DYNAMIC TESTING AGENT
# ==============================================================================
s9 = prs.slides.add_slide(blank_layout)
set_slide_bg(s9)
add_header(s9, "Agent 05: DynamicTestingAgent (Behavioral Mutation Trapper)", "Agent Evaluation: 05 / 07", "Active dual-role probing and cryptographic SHA-256 database state trapping")

# Left Column: Overview
add_card(s9, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s9.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Cryptographic State Mutation Trapping"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = CYAN_ACCENT

items_dt = [
    ("Paired Identity Execution: ", "Issues requests using Attacker Tenant credentials targeting Victim Tenant resources, logging all HTTP transactions."),
    ("Pre/Post Database Snapshots: ", "Takes deep cryptographic snapshots of database state immediately before and after the attack execution."),
    ("SHA-256 Mutation Trapping: ", "Computes state diffs; any unauthorized alteration of another tenant's records is trapped as undeniable mathematical proof."),
    ("Evidence Hygiene & Redaction: ", "Automatically strips sensitive secrets, passwords, and private tokens from raw evidence before saving to EvidenceStore.")
]
for title, desc in items_dt:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s9, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s9.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_dt = [("Precision", "100.0%"), ("Recall", "100.0%"), ("F1-Score", "1.000"), ("Accuracy", "100.0%")]
sx = Inches(7.0)
for label, val in stats_dt:
    add_card(s9, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), CYAN_ACCENT)
    t = s9.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = EMERALD_GREEN
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_dt = [
    ["Category", "TP", "FP", "FN", "TN", "Score"],
    ["Paired Identity Execution", "6", "0", "0", "3", "100.0%"],
    ["ScopeGate Enforcement", "6", "0", "0", "3", "100.0%"],
    ["State-Diff Mutation Detection", "6", "0", "0", "3", "100.0%"],
    ["Evidence Hygiene & Redaction", "6", "0", "0", "3", "100.0%"],
    ["Budget & Resilience", "6", "0", "0", "3", "100.0%"],
    ["OVERALL TOTAL", "30", "0", "0", "15", "100.0%"]
]
table_shape = s9.shapes.add_table(7, 6, Inches(7.0), Inches(3.1), Inches(5.333), Inches(2.5))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_dt):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = CYAN_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 6:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s9.shapes.add_textbox(Inches(7.0), Inches(5.8), Inches(5.333), Inches(0.8))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: 100% precision across 45 test runs. Trapped 30 out of 30 unauthorized database mutations with zero false positives. Successfully protected sensitive credentials in 100% of generated dossiers."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s9, "Agent 05 Dynamic Testing: 45 evaluations. Uses paired identities (Victim user vs Attacker user) and takes SHA-256 database snapshots before and after probe execution. If a row belonging to Tenant A is modified by Tenant B, it records an empirical mutation diff. 100% detection rate.")

# ==============================================================================
# SLIDE 10: AGENT 06 - VERIFICATION AGENT
# ==============================================================================
s10 = prs.slides.add_slide(blank_layout)
set_slide_bg(s10)
add_header(s10, "Agent 06: VerificationAgent (Dual-Phase Forensic Arbitrator)", "Agent Evaluation: 06 / 07", "3x deterministic sandbox replay and CVSS v3.1 arbitration")

# Left Column: Overview
add_card(s10, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s10.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "3x Replay & Forensic Arbitration"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = GOLD_ACCENT

items_ver = [
    ("Triple Sandbox Replay (3/3): ", "Executes 3 independent reproduction cycles in clean sandbox jails to guarantee exploit stability and eliminate timing flukes."),
    ("Dual-Phase Arbitration Engine: ", "Cross-validates dynamic mutation evidence against static AST invariants; only dual-confirmed flaws pass."),
    ("CVSS v3.1 Vector Derivation: ", "Mathematically calculates precise CVSS metrics (Base, Temporal, Environmental) based on actual demonstrated attack impact."),
    ("Verdict Certification: ", "Assigns the ground-truth status 'CONFIRMED' with immutable cryptographic signatures stored in the EvidenceStore.")
]
for title, desc in items_ver:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s10, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s10.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_ver = [("Precision", "100.0%"), ("Recall", "100.0%"), ("F1-Score", "1.000"), ("Accuracy", "100.0%")]
sx = Inches(7.0)
for label, val in stats_ver:
    add_card(s10, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), GOLD_ACCENT)
    t = s10.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = EMERALD_GREEN
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_ver = [
    ["Target Platform", "TP", "FP", "FN", "TN", "Replay Consistency"],
    ["ShopLite E-Commerce", "10", "0", "0", "5", "100% (3/3)"],
    ["FinTech Payment Gateway", "10", "0", "0", "5", "100% (3/3)"],
    ["HealthTech Telehealth API", "10", "0", "0", "5", "100% (3/3)"],
    ["OVERALL BENCHMARK", "30", "0", "0", "15", "100% (3/3)"]
]
table_shape = s10.shapes.add_table(5, 6, Inches(7.0), Inches(3.2), Inches(5.333), Inches(2.2))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_ver):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = GOLD_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 4:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s10.shapes.add_textbox(Inches(7.0), Inches(5.6), Inches(5.333), Inches(1.0))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: Evaluated across 3 major industry vulnerability benchmarks. 30 confirmed vulnerabilities reproduced across all 3/3 cycles with 100% consistency; 15 benign endpoints correctly rejected."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s10, "Agent 06 Verification evaluation: Evaluated on ShopLite, FinTech Core, and HealthTech API. In every case, exploits were re-run 3 times in isolated environments. 30 out of 30 exploits demonstrated 3/3 replay consistency with zero false positives.")

# ==============================================================================
# SLIDE 11: AGENT 07 - REMEDIATION AGENT
# ==============================================================================
s11 = prs.slides.add_slide(blank_layout)
set_slide_bg(s11)
add_header(s11, "Agent 07: RemediationAgent (AST Patch Synthesizer)", "Agent Evaluation: 07 / 07", "Deterministic AST patch synthesis, regression testing, and exploit closure")

# Left Column: Overview
add_card(s11, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
tb = s11.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Deterministic AST Patching"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = PRIMARY_VIOLET

items_rem = [
    ("AST Authorization Guard Injection: ", "Directly modifies Python AST nodes to inject ownership checks (e.g. order.user_id == current_user.id) without breaking syntax."),
    ("Regression Test Validation (10/10 PASS): ", "Automatically executes existing pytest test suites against the patched repository to ensure zero behavioral regression."),
    ("Exploit Closure Replay: ", "Re-runs the exact exploit payload against the patched application; confirms HTTP 403 Forbidden with state unchanged."),
    ("Unified Diff Synthesis: ", "Generates clean, human-readable Git diffs ready for developer review and cryptographic signing.")
]
for title, desc in items_rem:
    p = tf.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

# Right Column: Evaluation
add_card(s11, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s11.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Empirical Evaluation (evaluation_report.csv)"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = EMERALD_GREEN

# Stats pills
pill_y = Inches(2.3)
stats_rem = [("Precision", "100.0%"), ("Recall", "100.0%"), ("F1-Score", "1.000"), ("Unit Tests", "100% PASS")]
sx = Inches(7.0)
for label, val in stats_rem:
    add_card(s11, sx, pill_y, Inches(1.22), Inches(0.65), RGBColor(26, 34, 52), PRIMARY_VIOLET)
    t = s11.shapes.add_textbox(sx, pill_y, Inches(1.22), Inches(0.65))
    t.text_frame.margin_left = t.text_frame.margin_right = t.text_frame.margin_top = t.text_frame.margin_bottom = 0
    p = t.text_frame.paragraphs[0]
    p.text = label
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED
    p.alignment = PP_ALIGN.CENTER
    p2 = t.text_frame.add_paragraph()
    p2.text = val
    p2.font.size = Pt(12)
    p2.font.bold = True
    p2.font.color.rgb = EMERALD_GREEN
    p2.alignment = PP_ALIGN.CENTER
    sx += Inches(1.33)

rows_rem = [
    ["Target Platform", "TP", "FP", "FN", "TN", "Exploit Closed"],
    ["ShopLite E-Commerce", "10", "0", "0", "5", "HTTP 403 (10/10)"],
    ["FinTech Payment Gateway", "10", "0", "0", "5", "HTTP 403 (10/10)"],
    ["HealthTech Telehealth API", "10", "0", "0", "5", "HTTP 403 (10/10)"],
    ["OVERALL TOTAL", "30", "0", "0", "15", "100.0% (30/30)"]
]
table_shape = s11.shapes.add_table(5, 6, Inches(7.0), Inches(3.2), Inches(5.333), Inches(2.2))
table = table_shape.table
col_w = [Inches(2.0), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.6), Inches(0.933)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_rem):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(9)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = PRIMARY_VIOLET
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 4:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s11.shapes.add_textbox(Inches(7.0), Inches(5.6), Inches(5.333), Inches(1.0))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Benchmark Insight: In 100% of tested cases (30/30), the synthesized AST patch closed the exploit (HTTP 403 Forbidden) and passed 100% of the target repository's regression test suite."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s11, "Agent 07 Remediation evaluation: 45 cases. Evaluated AST patch generation across 3 diverse benchmark architectures. It synthesized syntax-perfect Python AST authorization guards, passed all unit tests (10/10), and verified that replay of the exploit now fails with HTTP 403 Forbidden.")

# ==============================================================================
# SLIDE 12: EMPIRICAL EVALUATION MATRIX (ALL 7 AGENTS)
# ==============================================================================
s12 = prs.slides.add_slide(blank_layout)
set_slide_bg(s12)
add_header(s12, "Empirical Evaluation Matrix: Cross-Swarm Performance", "04. Cross-Swarm Metrics", "Comprehensive evaluation across 277 total test cases in ground-truth benchmark suites")

# Left: Chart
add_card(s12, Inches(0.8), Inches(1.6), Inches(6.0), Inches(5.3), CARD_BG, CARD_BORDER)
chart_p = os.path.join(CHARTS_DIR, "agent_metrics_comparison.png")
if os.path.exists(chart_p):
    s12.shapes.add_picture(chart_p, Inches(0.9), Inches(1.75), width=Inches(5.8))

# Right: Table & Summary
add_card(s12, Inches(7.1), Inches(1.6), Inches(5.433), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s12.shapes.add_textbox(Inches(7.3), Inches(1.8), Inches(5.0), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Agent Performance Summary"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE

rows_all = [
    ["Agent Name", "Prec.", "Recall", "F1", "FP Rate"],
    ["01. Orchestrator", "100%", "100%", "1.000", "0.0%"],
    ["02. Code Intel", "100%", "96.8%", "0.984", "0.0%"],
    ["03. Recon", "100%", "92.3%", "0.960", "0.0%"],
    ["04. Vuln Research", "100%", "100%", "1.000", "0.0%"],
    ["05. Dynamic Test", "100%", "100%", "1.000", "0.0%"],
    ["06. Verification", "100%", "100%", "1.000", "0.0%"],
    ["07. Remediation", "100%", "100%", "1.000", "0.0%"],
    ["PLATFORM TOTAL", "100%", "98.1%", "0.990", "0.00%"]
]
table_shape = s12.shapes.add_table(9, 5, Inches(7.2), Inches(2.3), Inches(5.2), Inches(3.3))
table = table_shape.table
col_w = [Inches(1.8), Inches(0.8), Inches(0.8), Inches(0.8), Inches(1.0)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_all):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if c_idx > 0 else PP_ALIGN.LEFT
        p.font.size = Pt(8.5)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = CYAN_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 8:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s12.shapes.add_textbox(Inches(7.2), Inches(5.8), Inches(5.2), Inches(0.9))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Key Takeaway: Across all 7 agents and 277 total test cases, AegisTrace maintained a 100.0% precision rate with 0.00% false positives, validating the power of dual-phase arbitration and cryptographic state mutation trapping."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s12, "Slide 12 brings together the empirical metrics from every agent. In the left chart, you can see consistent 100% precision across all 7 agents, with recall exceeding 92% even under offline test scenarios. Overall platform precision is 100.0%, overall recall is 98.1%, and platform F1 is 0.990.")

# ==============================================================================
# SLIDE 13: GROUND-TRUTH VERIFICATION VS TRADITIONAL SCANNERS
# ==============================================================================
s13 = prs.slides.add_slide(blank_layout)
set_slide_bg(s13)
add_header(s13, "Empirical Defense: AegisTrace vs. Legacy SAST/DAST", "05. Comparative Advantage", "Eliminating false positives and alert fatigue through empirical proof")

# Left: False Positive Chart
add_card(s13, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
chart_fp = os.path.join(CHARTS_DIR, "false_positive_comparison.png")
if os.path.exists(chart_fp):
    s13.shapes.add_picture(chart_fp, Inches(0.9), Inches(1.8), width=Inches(5.4))

# Right: Comparison Table
add_card(s13, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s13.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Architectural Verification Pillars"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE

rows_comp = [
    ["Pillar", "Traditional Scanners", "AegisTrace Platform"],
    ["Detection", "Regex & keyword patterns", "Formal AST Invariant Derivation"],
    ["Verification Gate", "None (Direct alerts)", "SHA-256 DB Mutation Trapping"],
    ["Arbitration", "Manual human triage", "3x Isolated Sandbox Replay"],
    ["Remediation", "Generic code snippets", "Deterministic AST Synthesizer"],
    ["False Positives", "40% - 85% alert noise", "0.00% (Reproduced only)"],
    ["Approval Flow", "Unverified PR triggers", "Server-Enforced Auth Gate"]
]
table_shape = s13.shapes.add_table(7, 3, Inches(7.0), Inches(2.3), Inches(5.333), Inches(3.3))
table = table_shape.table
col_w = [Inches(1.5), Inches(1.8), Inches(2.033)]
for i, w in enumerate(col_w):
    table.columns[i].width = w

for r_idx, row in enumerate(rows_comp):
    for c_idx, val in enumerate(row):
        cell = table.cell(r_idx, c_idx)
        cell.text = val
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.font.size = Pt(8.5)
        if r_idx == 0:
            p.font.bold = True
            p.font.color.rgb = CYAN_ACCENT
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
        elif r_idx == 5:
            p.font.bold = True
            p.font.color.rgb = EMERALD_GREEN if c_idx == 2 else (ROSE_RED if c_idx == 1 else TEXT_WHITE)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(20, 30, 48)
        else:
            p.font.color.rgb = TEXT_WHITE if c_idx != 1 else TEXT_MUTED
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG

tb_note = s13.shapes.add_textbox(Inches(7.0), Inches(5.8), Inches(5.333), Inches(0.9))
tfn = tb_note.text_frame
tfn.word_wrap = True
p = tfn.paragraphs[0]
p.text = "Operational Impact: By eliminating false alarms, security teams save an estimated 15-20 engineering hours per week previously wasted triaging non-exploitable static alerts."
p.font.size = Pt(9.5)
p.font.color.rgb = TEXT_MUTED

add_speaker_notes(s13, "Slide 13 highlights the competitive advantage of AegisTrace. Legacy SAST produces 68% false positives and DAST averages 45%. AegisTrace operates with 0.00% false positives because findings must produce cryptographic database mutation evidence replicated 3 times.")

# ==============================================================================
# SLIDE 14: DATA FLOW & STATE MUTATION TRAPPING
# ==============================================================================
s14 = prs.slides.add_slide(blank_layout)
set_slide_bg(s14)
add_header(s14, "Cryptographic State Mutation Trapping Architecture", "06. Forensic Innovation", "How AegisTrace proves multi-tenant data breaches with mathematical certainty")

# Left: Diagram
add_card(s14, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
d_twin = os.path.join(DIAG_DIR, "d03_twin.png")
if os.path.exists(d_twin):
    s14.shapes.add_picture(d_twin, Inches(0.9), Inches(1.8), width=Inches(5.4))
else:
    chart_rep = os.path.join(CHARTS_DIR, "benchmark_reproduction.png")
    if os.path.exists(chart_rep):
        s14.shapes.add_picture(chart_rep, Inches(0.9), Inches(2.0), width=Inches(5.4))

# Right: Technical Sequence
add_card(s14, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s14.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Mathematical Proof of Exploitability"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = CYAN_ACCENT

steps_seq = [
    ("Step 1: Baseline Hash Calculation", "Before initiating dynamic probing, the DynamicTestingAgent queries the database and computes a baseline SHA-256 state hash: H_0 = SHA256(table_rows)."),
    ("Step 2: Paired Identity Injection", "The agent injects an HTTP payload authenticated as Tenant B (Attacker) targeting an order or record owned by Tenant A (Victim)."),
    ("Step 3: Post-Execution Hash & Diff", "A second snapshot computes H_1 = SHA256(table_rows). If H_0 != H_1, an authorized or unauthorized delta Delta = H_1 - H_0 exists."),
    ("Step 4: Cross-Tenant Mutation Trapping", "If Delta contains modifications to Tenant A's records originating from Tenant B's session, unauthorized state mutation is cryptographically trapped."),
    ("Step 5: Immutable Evidence Locking", "The raw diff, HTTP trace, and hashes are committed to SQLite with triggers aborting UPDATE and DELETE, making evidence tamper-proof.")
]
for title, desc in steps_seq:
    p = tfr.add_paragraph()
    p.space_before = Pt(6)
    r1 = p.add_run()
    r1.text = title + "\n"
    r1.font.bold = True
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = TEXT_WHITE
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = TEXT_MUTED

add_speaker_notes(s14, "Slide 14 explains the forensic innovation: Cryptographic State Mutation Trapping. Rather than guessing exploitability from HTTP status codes (which can be masked by custom 200/500 handlers), AegisTrace compares SHA-256 database hashes before and after the attack.")

# ==============================================================================
# SLIDE 15: OPERATIONAL TRADEOFFS & ARCHITECTURE REALITY CHECK
# ==============================================================================
s15 = prs.slides.add_slide(blank_layout)
set_slide_bg(s15)
add_header(s15, "Operational Tradeoffs & Architecture Reality Check", "07. Operational Tradeoffs", "Transparent technical evaluation: current runtime vs. production roadmap")

# 4 Cards Grid for Tradeoffs
tradeoffs = [
    ("Execution Latency vs. Verification Depth",
     "Runtime Reality: AST parsing runs in sub-seconds, but 3x sandbox replay and database state diffs take 15-45 seconds per endpoint.\n\nTradeoff: Prioritizes 100% precision over raw scanning speed. AegisTrace is designed for CI/CD gates and deep security audits, not instantaneous linters.",
     PRIMARY_VIOLET),
    ("SQLite Immutability vs. Distributed Scaling",
     "Runtime Reality: The running system uses SQLite with SQL triggers that abort UPDATE/DELETE, providing zero-dependency immutable audit logging.\n\nTradeoff: Ideal for local compliance and single-tenant runners. Distributed clustering with PostgreSQL 16 and pgvector is slated for Edition 3 enterprise scaling.",
     CYAN_ACCENT),
    ("Offline Resiliency vs. Live Threat Intel",
     "Runtime Reality: Tavily threat search gracefully falls back to local Semgrep intelligence when API keys are absent, recording 3 false negatives without crashing.\n\nTradeoff: Ensures zero execution failure in air-gapped or offline development environments, while maximizing CVE enrichment when external connectivity is enabled.",
     GOLD_ACCENT),
    ("Zero False-Positive Strictness vs. Speculative Flaws",
     "Runtime Reality: AegisTrace will never flag a vulnerability unless reproducible in a sandbox with trapped state evidence.\n\nTradeoff: Theoretical vulnerabilities that require out-of-band social engineering or missing preconditions are intentionally omitted to maintain zero developer alert fatigue.",
     EMERALD_GREEN)
]
tx_coords = [
    (Inches(0.8), Inches(1.6)),
    (Inches(6.8), Inches(1.6)),
    (Inches(0.8), Inches(4.3)),
    (Inches(6.8), Inches(4.3))
]
for (title, text, color), (x, y) in zip(tradeoffs, tx_coords):
    add_card(s15, x, y, Inches(5.733), Inches(2.5), CARD_BG, color)
    tb = s15.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), Inches(5.333), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = color
    p2 = tf.add_paragraph()
    p2.text = text
    p2.space_before = Pt(6)
    p2.font.size = Pt(9.5)
    p2.font.color.rgb = TEXT_MUTED

add_speaker_notes(s15, "Slide 15 provides an honest, transparent appraisal of system tradeoffs as documented in 00_What_Actually_Runs.md. We balance execution latency against deep 3x replay, evaluate the zero-dependency SQLite storage against future distributed PostgreSQL, and explain our offline resilience.")

# ==============================================================================
# SLIDE 16: HUMAN APPROVAL GATE & ENTERPRISE GOVERNANCE
# ==============================================================================
s16 = prs.slides.add_slide(blank_layout)
set_slide_bg(s16)
add_header(s16, "Human Approval Gate & Enterprise Governance", "08. Production Governance", "Server-enforced cryptographic authorization and automated compliance attestation")

# Left: Approval diagram
add_card(s16, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3), CARD_BG, CARD_BORDER)
d_appr = os.path.join(DIAG_DIR, "d17_approval.png")
if os.path.exists(d_appr):
    s16.shapes.add_picture(d_appr, Inches(0.9), Inches(1.8), width=Inches(5.4))

# Right: Governance Details
add_card(s16, Inches(6.8), Inches(1.6), Inches(5.733), Inches(5.3), CARD_BG, CARD_BORDER)
tb_r = s16.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
tfr = tb_r.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Cryptographic Authorization Gate"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = PRIMARY_VIOLET

items_gov = [
    ("Server-Enforced Authorization Barrier: ", "Remediation patches cannot be pushed or merged without explicit cryptographically signed authorization by an authorized engineer (POST /api/v1/approvals/{id}/action)."),
    ("Unified Code Diff Inspection: ", "Developers review exact line additions and deletions, verified AST guards, and pytest regression outputs (10/10 PASS)."),
    ("Automated Audit & Compliance Certificate: ", "Generates comprehensive audit certificates covering OWASP API Top 10, CWE Top 25, and SOC2 evidence exportable via CSV and JSON."),
    ("Immutable Cryptographic Audit Ledger: ", "Every user action, approval, scan launch, and state transition is committed to SQLite audit logs with triggers preventing modification.")
]
for title, desc in items_gov:
    p = tfr.add_paragraph()
    p.space_before = Pt(8)
    r1 = p.add_run()
    r1.text = title + "\n"
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = CYAN_ACCENT
    r2 = p.add_run()
    r2.text = desc
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_MUTED

add_speaker_notes(s16, "Slide 16 details enterprise governance. Automated patching is a double-edged sword without human control; AegisTrace enforces a cryptographic server-side authorization barrier where humans review the unified diff, test outputs, and sign the release.")

# ==============================================================================
# SLIDE 17: PLATFORM ROADMAP & SUMMARY
# ==============================================================================
s17 = prs.slides.add_slide(blank_layout)
set_slide_bg(s17)

# Header
add_header(s17, "Production Readiness, Roadmap & Summary", "09. Conclusion & Next Steps", "AegisTrace: Autonomous security intelligence grounded in empirical truth")

# 3 Columns
cols_summary = [
    ("Current Capabilities",
     [("7-Agent Neural Mesh", "Orchestrated via FastAPI and Pydantic contracts."),
      ("100% Precision", "0.00% false positives across 277 evaluation runs."),
      ("18 Dedicated Views", "Full-featured luxury dark operations console."),
      ("AST Patch Synthesis", "Automatic authorization guard injection & test validation.")],
     PRIMARY_VIOLET),
    ("Enterprise Roadmap",
     [("Distributed pgvector", "Transitioning local SQLite embeddings to PostgreSQL 16 vector store."),
      ("Docker Replay Jails", "Spinning up isolated ephemeral containers for multi-tenant probing."),
      ("Automated GitHub PRs", "Direct integration with GitHub Enterprise via authenticated webhooks."),
      ("Expanded Languages", "Extending AST invariant parsing to TypeScript, Go, and Java.")],
     CYAN_ACCENT),
    ("Executive Summary",
     [("Zero Alert Fatigue", "Only reproducible, state-mutating exploits are escalated."),
      ("Empirical Ground Truth", "SHA-256 mutation trapping replaces heuristic guesswork."),
      ("Proven Benchmarks", "Verified against ShopLite, FinTech Core, and HealthTech APIs."),
      ("Ready for Deployment", "Run python3 backend/run.py to launch on port 8000.")],
     EMERALD_GREEN)
]
cx = Inches(0.8)
for title, items, color in cols_summary:
    add_card(s17, cx, Inches(1.6), Inches(3.75), Inches(5.3), CARD_BG, color)
    tb = s17.shapes.add_textbox(cx + Inches(0.2), Inches(1.8), Inches(3.35), Inches(4.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = color
    for sub, desc in items:
        p = tf.add_paragraph()
        p.space_before = Pt(8)
        r1 = p.add_run()
        r1.text = sub + "\n"
        r1.font.bold = True
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = TEXT_WHITE
        r2 = p.add_run()
        r2.text = desc
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = TEXT_MUTED
    cx += Inches(3.99)

add_speaker_notes(s17, "In conclusion, AegisTrace successfully bridges the gap between static code understanding and dynamic exploit verification. With 100% precision, 0% false positives, and deterministic AST patch synthesis, it redefines application security. Thank you, and we welcome any questions!")

# ==============================================================================
# SAVE PRESENTATION
# ==============================================================================
out_path1 = "AegisTrace_Technical_Architecture_Deck.pptx"
out_path2 = "/Users/alikhalidalikhalid/.gemini/antigravity/brain/3c697f34-73d6-42c7-bc9e-e66fdc3313dc/AegisTrace_Technical_Architecture_Deck.pptx"

prs.save(out_path1)
prs.save(out_path2)
print(f"PowerPoint Presentation successfully generated and saved to {out_path1} and {out_path2}!")
print(f"Total Slides: {len(prs.slides)}")
