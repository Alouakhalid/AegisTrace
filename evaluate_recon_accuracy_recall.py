import os
import sys
import json
import shutil
import importlib.util
import csv
import numpy as np
import networkx as nx
import matplotlib
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
import matplotlib.pyplot as plt

workspace_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["CREWAI_STORAGE_DIR"] = os.path.join(workspace_dir, ".crewai")
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_DISABLE_TRACING"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["CREWAI_TESTING"] = "true"
sys.path.insert(0, workspace_dir)

agent_file_path = os.path.join(workspace_dir, "agents", "Recon agent", "recon_agent.py")
spec = importlib.util.spec_from_file_location("recon_agent", agent_file_path)
recon_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recon_mod)
run_recon = recon_mod.run_recon

from tools.recon_tools import ScopeGate, ScopeViolationException

benchmarks_root = os.path.join(workspace_dir, "benchmark_suite_recon")
if os.path.exists(benchmarks_root):
    shutil.rmtree(benchmarks_root)
os.makedirs(benchmarks_root, exist_ok=True)

target1_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "ShopLite E-Commerce Platform",
        "description": "Store API built with FastAPI framework and PostgreSQL database",
        "version": "1.0.0"
    },
    "paths": {
        "/api/v1/orders/{order_id}": {
            "get": {
                "summary": "Get order",
                "security": [{"bearerAuth": []}]
            },
            "patch": {
                "summary": "Update order",
                "security": [{"bearerAuth": []}]
            }
        },
        "/api/v1/orders": {
            "post": {
                "summary": "Create order",
                "security": [{"bearerAuth": []}]
            }
        },
        "/api/v1/auth/login": {
            "post": {
                "summary": "User login"
            }
        },
        "/admin/danger/wipe_database": {
            "delete": {
                "summary": "Dangerous wipe"
            }
        },
        "/admin/danger/reset_keys": {
            "post": {
                "summary": "Dangerous key reset"
            }
        }
    }
}
t1_path = os.path.join(benchmarks_root, "shoplite_openapi.json")
with open(t1_path, "w", encoding="utf-8") as f:
    json.dump(target1_spec, f, indent=2)

target2_spec = {
    "openapi": "3.0.1",
    "info": {
        "title": "FinTech Core Banking Service",
        "description": "Production banking microservice built with Django and Redis",
        "version": "2.1.0"
    },
    "paths": {
        "/api/v2/accounts/{account_id}/balance": {
            "get": {
                "summary": "Account balance",
                "security": [{"tokenAuth": []}]
            }
        },
        "/api/v2/transfers": {
            "post": {
                "summary": "Transfer funds",
                "security": [{"tokenAuth": []}]
            }
        },
        "/api/v2/public/rates": {
            "get": {
                "summary": "Exchange rates"
            }
        },
        "/api/v2/users/{user_id}/profile": {
            "get": {
                "summary": "User profile",
                "security": [{"tokenAuth": []}]
            }
        },
        "/internal/system_metrics": {
            "get": {
                "summary": "Internal metrics"
            }
        },
        "/api/v2/debug_command": {
            "post": {
                "summary": "Debug exec"
            }
        }
    }
}
t2_path = os.path.join(benchmarks_root, "bank_api_spec.json")
with open(t2_path, "w", encoding="utf-8") as f:
    json.dump(target2_spec, f, indent=2)

target3_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "Inventory Catalog API",
        "description": "Flask service for managing warehouse catalog items",
        "version": "0.9.5"
    },
    "paths": {
        "/api/v1/items/{item_id}": {
            "get": {
                "summary": "Item details"
            },
            "put": {
                "summary": "Modify item",
                "security": [{"api_key": []}]
            }
        },
        "/api/v1/items": {
            "post": {
                "summary": "Add item",
                "security": [{"api_key": []}]
            }
        },
        "/system/emergency_halt": {
            "post": {
                "summary": "Emergency halt"
            }
        }
    }
}
t3_path = os.path.join(benchmarks_root, "catalog_api_spec.json")
with open(t3_path, "w", encoding="utf-8") as f:
    json.dump(target3_spec, f, indent=2)

benchmark_cases = [
    {
        "id": "case_shoplite",
        "spec_path": t1_path,
        "scope": {
            "allowed_hosts": ["shoplite-app"],
            "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
            "forbidden_paths": ["/admin/danger/*"]
        },
        "hints": ["fastapi", "postgresql"],
        "expected_endpoints": [
            ("GET", "/api/v1/orders/{order_id}"),
            ("PATCH", "/api/v1/orders/{order_id}"),
            ("POST", "/api/v1/orders"),
            ("POST", "/api/v1/auth/login")
        ],
        "forbidden_endpoints": [
            ("DELETE", "/admin/danger/wipe_database"),
            ("POST", "/admin/danger/reset_keys")
        ],
        "protected_endpoints": [
            ("GET", "/api/v1/orders/{order_id}"),
            ("PATCH", "/api/v1/orders/{order_id}"),
            ("POST", "/api/v1/orders")
        ],
        "unprotected_endpoints": [
            ("POST", "/api/v1/auth/login")
        ],
        "expected_technologies": ["FastAPI", "PostgreSQL"],
        "unexpected_technologies": ["Django", "Ruby"],
        "max_queries": 2
    },
    {
        "id": "case_banking",
        "spec_path": t2_path,
        "scope": {
            "allowed_hosts": ["bank-api.internal"],
            "allowed_methods": ["GET", "POST"],
            "forbidden_paths": ["/internal/*", "*/debug_*"]
        },
        "hints": ["django", "redis", "postgresql"],
        "expected_endpoints": [
            ("GET", "/api/v2/accounts/{account_id}/balance"),
            ("POST", "/api/v2/transfers"),
            ("GET", "/api/v2/public/rates"),
            ("GET", "/api/v2/users/{user_id}/profile")
        ],
        "forbidden_endpoints": [
            ("GET", "/internal/system_metrics"),
            ("POST", "/api/v2/debug_command")
        ],
        "protected_endpoints": [
            ("GET", "/api/v2/accounts/{account_id}/balance"),
            ("POST", "/api/v2/transfers"),
            ("GET", "/api/v2/users/{user_id}/profile")
        ],
        "unprotected_endpoints": [
            ("GET", "/api/v2/public/rates")
        ],
        "expected_technologies": ["Django", "Redis", "PostgreSQL"],
        "unexpected_technologies": ["Flask", "PHP"],
        "max_queries": 2
    },
    {
        "id": "case_catalog",
        "spec_path": t3_path,
        "scope": {
            "allowed_hosts": ["catalog-app.local"],
            "allowed_methods": ["GET", "POST", "PUT"],
            "forbidden_paths": ["/system/*"]
        },
        "hints": ["flask"],
        "expected_endpoints": [
            ("GET", "/api/v1/items/{item_id}"),
            ("PUT", "/api/v1/items/{item_id}"),
            ("POST", "/api/v1/items")
        ],
        "forbidden_endpoints": [
            ("POST", "/system/emergency_halt")
        ],
        "protected_endpoints": [
            ("PUT", "/api/v1/items/{item_id}"),
            ("POST", "/api/v1/items")
        ],
        "unprotected_endpoints": [
            ("GET", "/api/v1/items/{item_id}")
        ],
        "expected_technologies": ["Flask"],
        "unexpected_technologies": ["Spring", "NodeJS"],
        "max_queries": 2
    }
]

total_ep_tp = 0
total_ep_fp = 0
total_ep_fn = 0

total_scope_tp = 0
total_scope_fp = 0
total_scope_fn = 0
total_scope_tn = 0

total_auth_tp = 0
total_auth_fp = 0
total_auth_fn = 0
total_auth_tn = 0

total_tech_tp = 0
total_tech_fp = 0
total_tech_fn = 0
total_tech_tn = 0

total_intel_tp = 0
total_intel_fp = 0
total_intel_fn = 0
total_intel_tn = 0

print("=" * 75)
print("RUNNING RECON AGENT BENCHMARK EVALUATION (ACCURACY, PRECISION, RECALL & F1)")
print("=" * 75)

for idx, case in enumerate(benchmark_cases, start=1):
    print(f"\n[+] Executing Benchmark Case {idx}/{len(benchmark_cases)}: {case['id']}...")
    req_payload = {
        "schema_version": "1.0.0",
        "correlation_id": f"cor_0192f230ab{idx:02x}",
        "project_id": "prj_0192f1a0bc11",
        "engagement_id": "eng_0192f1b4cd22",
        "scan_id": f"scn_0192f1c9de{idx:02x}",
        "task_id": f"tsk_0192f303ef{idx:02x}",
        "agent_run_id": f"run_0192f403fa{idx:02x}",
        "created_at": "2026-11-17T09:30:10Z",
        "agent": "recon",
        "input": {
            "scope": case["scope"],
            "api_spec_ref": case["spec_path"],
            "technology_hints": case["hints"],
            "research": {
                "enabled": True,
                "max_queries": case["max_queries"],
                "search_depth": "basic"
            }
        }
    }

    res = run_recon(req_payload)
    out = res.get("output", {})
    detected_eps = out.get("endpoints", [])
    detected_techs = out.get("technologies", [])
    detected_intel = out.get("intel_refs", [])

    gt_eps = {(m.upper(), p.rstrip("/")) for m, p in case["expected_endpoints"]}
    det_eps = {(ep["method"].upper(), ep["path"].rstrip("/")) for ep in detected_eps}

    ep_tp = len(gt_eps.intersection(det_eps))
    ep_fp = len(det_eps - gt_eps)
    ep_fn = len(gt_eps - det_eps)

    total_ep_tp += ep_tp
    total_ep_fp += ep_fp
    total_ep_fn += ep_fn

    for verb, forb_p in case["forbidden_endpoints"]:
        if (verb.upper(), forb_p.rstrip("/")) in det_eps:
            total_scope_fp += 1
        else:
            total_scope_tn += 1

    for verb, in_p in case["expected_endpoints"]:
        if (verb.upper(), in_p.rstrip("/")) in det_eps:
            total_scope_tp += 1
        else:
            total_scope_fn += 1

    gt_prot = {(m.upper(), p.rstrip("/")) for m, p in case["protected_endpoints"]}
    gt_unprot = {(m.upper(), p.rstrip("/")) for m, p in case["unprotected_endpoints"]}

    for ep in detected_eps:
        pair = (ep["method"].upper(), ep["path"].rstrip("/"))
        is_auth = ep.get("auth_required")
        if pair in gt_prot:
            if is_auth:
                total_auth_tp += 1
            else:
                total_auth_fn += 1
        elif pair in gt_unprot:
            if not is_auth:
                total_auth_tn += 1
            else:
                total_auth_fp += 1

    det_tech_names = {t["name"].lower() for t in detected_techs}
    for expected_t in case["expected_technologies"]:
        if expected_t.lower() in det_tech_names:
            total_tech_tp += 1
        else:
            total_tech_fn += 1

    for unexp_t in case["unexpected_technologies"]:
        if unexp_t.lower() in det_tech_names:
            total_tech_fp += 1
        else:
            total_tech_tn += 1

    if len(detected_intel) > 0:
        total_intel_tp += len(detected_intel)
        for ref in detected_intel:
            if ref.get("trusted") is False:
                total_intel_tn += 1
            else:
                total_intel_fp += 1
    else:
        total_intel_fn += 1

def safe_div(num, den):
    return (num / den) if den > 0 else 0.0

ep_prec = safe_div(total_ep_tp, total_ep_tp + total_ep_fp)
ep_rec = safe_div(total_ep_tp, total_ep_tp + total_ep_fn)
ep_f1 = safe_div(2 * ep_prec * ep_rec, ep_prec + ep_rec)
ep_acc = safe_div(total_ep_tp, total_ep_tp + total_ep_fp + total_ep_fn)

scope_prec = safe_div(total_scope_tp, total_scope_tp + total_scope_fp)
scope_rec = safe_div(total_scope_tp, total_scope_tp + total_scope_fn)
scope_f1 = safe_div(2 * scope_prec * scope_rec, scope_prec + scope_rec)
scope_acc = safe_div(total_scope_tp + total_scope_tn, total_scope_tp + total_scope_tn + total_scope_fp + total_scope_fn)

auth_prec = safe_div(total_auth_tp, total_auth_tp + total_auth_fp)
auth_rec = safe_div(total_auth_tp, total_auth_tp + total_auth_fn)
auth_f1 = safe_div(2 * auth_prec * auth_rec, auth_prec + auth_rec)
auth_acc = safe_div(total_auth_tp + total_auth_tn, total_auth_tp + total_auth_tn + total_auth_fp + total_auth_fn)

tech_prec = safe_div(total_tech_tp, total_tech_tp + total_tech_fp)
tech_rec = safe_div(total_tech_tp, total_tech_tp + total_tech_fn)
tech_f1 = safe_div(2 * tech_prec * tech_rec, tech_prec + tech_rec)
tech_acc = safe_div(total_tech_tp + total_tech_tn, total_tech_tp + total_tech_tn + total_tech_fp + total_tech_fn)

intel_prec = safe_div(total_intel_tp, total_intel_tp + total_intel_fp)
intel_rec = safe_div(total_intel_tp, total_intel_tp + total_intel_fn)
intel_f1 = safe_div(2 * intel_prec * intel_rec, intel_prec + intel_rec)
intel_acc = safe_div(total_intel_tp + total_intel_tn, total_intel_tp + total_intel_tn + total_intel_fp + total_intel_fn)

grand_tp = total_ep_tp + total_scope_tp + total_auth_tp + total_tech_tp + total_intel_tp
grand_fp = total_ep_fp + total_scope_fp + total_auth_fp + total_tech_fp + total_intel_fp
grand_fn = total_ep_fn + total_scope_fn + total_auth_fn + total_tech_fn + total_intel_fn
grand_tn = total_scope_tn + total_auth_tn + total_tech_tn + total_intel_tn

overall_prec = safe_div(grand_tp, grand_tp + grand_fp)
overall_rec = safe_div(grand_tp, grand_tp + grand_fn)
overall_f1 = safe_div(2 * overall_prec * overall_rec, overall_prec + overall_rec)
overall_acc = safe_div(grand_tp + grand_tn, grand_tp + grand_tn + grand_fp + grand_fn)

print("\n" + "-" * 75)
print(f"{'EVALUATION METRIC':<26}| {'PRECISION':<11}| {'RECALL':<11}| {'F1-SCORE':<11}| {'ACCURACY':<10}")
print("-" * 75)
print(f"1. Endpoint Extraction    | {ep_prec*100:>7.1f}%   | {ep_rec*100:>7.1f}%   | {ep_f1*100:>7.1f}%   | {ep_acc*100:>7.1f}%")
print(f"2. Scope Gate Enforcement | {scope_prec*100:>7.1f}%   | {scope_rec*100:>7.1f}%   | {scope_f1*100:>7.1f}%   | {scope_acc*100:>7.1f}%")
print(f"3. Auth Scheme Detection  | {auth_prec*100:>7.1f}%   | {auth_rec*100:>7.1f}%   | {auth_f1*100:>7.1f}%   | {auth_acc*100:>7.1f}%")
print(f"4. Tech Fingerprinting    | {tech_prec*100:>7.1f}%   | {tech_rec*100:>7.1f}%   | {tech_f1*100:>7.1f}%   | {tech_acc*100:>7.1f}%")
print(f"5. External Intel (Tavily)| {intel_prec*100:>7.1f}%   | {intel_rec*100:>7.1f}%   | {intel_f1*100:>7.1f}%   | {intel_acc*100:>7.1f}%")
print("-" * 75)
print(f"OVERALL RECON BENCHMARK   | {overall_prec*100:>7.1f}%   | {overall_rec*100:>7.1f}%   | {overall_f1*100:>7.1f}%   | {overall_acc*100:>7.1f}%")
print("-" * 75)

out_agent_dir = os.path.join(workspace_dir, "agents", "Recon agent")
csv_path = os.path.join(out_agent_dir, "evaluation_report.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Category", "True_Positives", "False_Positives", "False_Negatives", "True_Negatives", "Precision", "Recall", "F1_Score", "Accuracy"])
    writer.writerow(["Endpoint_Extraction", total_ep_tp, total_ep_fp, total_ep_fn, 0, f"{ep_prec*100:.2f}%", f"{ep_rec*100:.2f}%", f"{ep_f1*100:.2f}%", f"{ep_acc*100:.2f}%"])
    writer.writerow(["Scope_Gate_Enforcement", total_scope_tp, total_scope_fp, total_scope_fn, total_scope_tn, f"{scope_prec*100:.2f}%", f"{scope_rec*100:.2f}%", f"{scope_f1*100:.2f}%", f"{scope_acc*100:.2f}%"])
    writer.writerow(["Auth_Scheme_Detection", total_auth_tp, total_auth_fp, total_auth_fn, total_auth_tn, f"{auth_prec*100:.2f}%", f"{auth_rec*100:.2f}%", f"{auth_f1*100:.2f}%", f"{auth_acc*100:.2f}%"])
    writer.writerow(["Tech_Fingerprinting", total_tech_tp, total_tech_fp, total_tech_fn, total_tech_tn, f"{tech_prec*100:.2f}%", f"{tech_rec*100:.2f}%", f"{tech_f1*100:.2f}%", f"{tech_acc*100:.2f}%"])
    writer.writerow(["External_Intel_Tavily", total_intel_tp, total_intel_fp, total_intel_fn, total_intel_tn, f"{intel_prec*100:.2f}%", f"{intel_rec*100:.2f}%", f"{intel_f1*100:.2f}%", f"{intel_acc*100:.2f}%"])
    writer.writerow(["OVERALL_TOTAL", grand_tp, grand_fp, grand_fn, grand_tn, f"{overall_prec*100:.2f}%", f"{overall_rec*100:.2f}%", f"{overall_f1*100:.2f}%", f"{overall_acc*100:.2f}%"])

print("\n[+] Updated CSV written to:", csv_path)

categories = ["Endpoints", "Scope Gate", "Auth Schemes", "Fingerprinting", "External Intel"]
prec_vals = [ep_prec * 100, scope_prec * 100, auth_prec * 100, tech_prec * 100, intel_prec * 100]
rec_vals = [ep_rec * 100, scope_rec * 100, auth_rec * 100, tech_rec * 100, intel_rec * 100]
f1_vals = [ep_f1 * 100, scope_f1 * 100, auth_f1 * 100, tech_f1 * 100, intel_f1 * 100]
acc_vals = [ep_acc * 100, scope_acc * 100, auth_acc * 100, tech_acc * 100, intel_acc * 100]

x = np.arange(len(categories))
width = 0.18

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
fig.patch.set_facecolor("#0f172a")

for ax in [ax1, ax2, ax3, ax4]:
    ax.set_facecolor("#1e293b")
    ax.tick_params(colors="white", labelsize=9)
    ax.grid(axis="y", color="#334155", linestyle="--", alpha=0.7)

b1 = ax1.bar(x - 1.5 * width, prec_vals, width, label="Precision", color="#38bdf8")
b2 = ax1.bar(x - 0.5 * width, rec_vals, width, label="Recall", color="#34d399")
b3 = ax1.bar(x + 0.5 * width, f1_vals, width, label="F1-Score", color="#f59e0b")
b4 = ax1.bar(x + 1.5 * width, acc_vals, width, label="Accuracy", color="#a855f7")

ax1.set_ylabel("Score (%)", color="white", fontsize=11)
ax1.set_title("Statistical Accuracy & Recall by Recon Capability", color="white", fontsize=13, fontweight="bold")
ax1.set_xticks(x)
ax1.set_xticklabels(categories, color="white", fontweight="bold")
ax1.set_ylim(0, 115)
ax1.legend(loc="lower right", facecolor="#0f172a", edgecolor="#334155", labelcolor="white")

conf_matrix_data = np.array([
    [grand_tp, grand_fn],
    [grand_fp, grand_tn]
])
cax = ax2.matshow(conf_matrix_data, cmap="Blues", alpha=0.85)
ax2.set_title("Cumulative Confusion Matrix (All Targets)", color="white", fontsize=13, fontweight="bold", pad=20)
ax2.set_xticks([0, 1])
ax2.set_yticks([0, 1])
ax2.set_xticklabels(["Positive", "Negative"], color="white", fontweight="bold")
ax2.set_yticklabels(["Positive", "Negative"], color="white", fontweight="bold")
ax2.set_xlabel("Predicted Condition", color="#38bdf8", fontsize=11, fontweight="bold")
ax2.set_ylabel("True Condition", color="#38bdf8", fontsize=11, fontweight="bold")

labels_grid = [
    [f"True Positive\n(TP = {grand_tp})", f"False Negative\n(FN = {grand_fn})"],
    [f"False Positive\n(FP = {grand_fp})", f"True Negative\n(TN = {grand_tn})"]
]
for i in range(2):
    for j in range(2):
        ax2.text(j, i, labels_grid[i][j], ha="center", va="center", color="#0f172a" if i == 0 and j == 0 else "white", fontsize=11, fontweight="bold")

summary_labels = ["Precision", "Recall", "F1-Score", "Overall Accuracy"]
summary_values = [overall_prec * 100, overall_rec * 100, overall_f1 * 100, overall_acc * 100]
summary_colors = ["#38bdf8", "#34d399", "#f59e0b", "#ec4899"]

b_sum = ax3.barh(summary_labels, summary_values, color=summary_colors, height=0.5)
ax3.set_xlim(0, 115)
ax3.set_xlabel("Overall Benchmark Score (%)", color="white", fontsize=11)
ax3.set_title("System-Wide Performance Summary", color="white", fontsize=13, fontweight="bold")
for bar in b_sum:
    xval = bar.get_width()
    ax3.text(xval + 1.5, bar.get_y() + bar.get_height()/2, f"{xval:.1f}%", ha="left", va="center", color="white", fontweight="bold", fontsize=10)

pie_labels = ["True Positives", "True Negatives", "False Positives", "False Negatives"]
pie_sizes = [grand_tp, grand_tn, max(grand_fp, 0.001), max(grand_fn, 0.001)]
pie_colors = ["#38bdf8", "#34d399", "#ef4444", "#f59e0b"]
explode = (0.05, 0.05, 0.1, 0.1)

ax4.pie(pie_sizes, labels=pie_labels, autopct="%1.1f%%", startangle=140, colors=pie_colors,
        explode=explode, textprops={"color": "white", "fontsize": 9, "fontweight": "bold"})
ax4.set_title("Output Classification Distribution", color="white", fontsize=13, fontweight="bold")

plt.suptitle("AegisTrace Recon Agent — Empirical Accuracy & Recall Benchmark", color="white", fontsize=16, fontweight="bold", y=0.98)
plt.tight_layout()

metrics_img_path = os.path.join(out_agent_dir, "agent_metrics_evaluation.png")
plt.savefig(metrics_img_path, facecolor=fig.get_facecolor(), edgecolor="none")
plt.close()
print("[+] Benchmark Graph updated at:", metrics_img_path)

fig_arch = plt.figure(figsize=(14, 8))
fig_arch.patch.set_facecolor("#0f172a")
ax_arch = fig_arch.add_subplot(111)
ax_arch.set_facecolor("#0f172a")
ax_arch.axis("off")

boxes = [
    ("Orchestrator Request\n(ScopeSummary, api_spec_ref, technology_hints)", (0.1, 0.75), "#1e293b", "#38bdf8"),
    ("ScopeGate Enforcement\n(Host Whitelist, Method Check, Forbidden Filter)", (0.5, 0.75), "#1e293b", "#ef4444"),
    ("OpenAPI Spec Parser\n(Endpoints, Path Params, Security Schemes)", (0.1, 0.40), "#1e293b", "#34d399"),
    ("Technology Fingerprinter\n(FastAPI, Django, Flask, Postgres, Redis)", (0.5, 0.40), "#1e293b", "#f59e0b"),
    ("Tavily External Intelligence\n(OWASP, CVE Advisories, trusted=False)", (0.9, 0.40), "#1e293b", "#a855f7"),
    ("NetworkX Attack Surface Graph\n(Nodes: Endpoint/Tech, Edges: Exposes/RunsOn)", (0.3, 0.10), "#1e293b", "#ec4899"),
    ("ReconResponse Validation\nPydantic V2 Strict (extra='forbid')", (0.7, 0.10), "#1e293b", "#38bdf8")
]

for title, (bx, by), bg, border in boxes:
    ax_arch.text(bx, by, title, ha="center", va="center", color="white", fontsize=10, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.8", facecolor=bg, edgecolor=border, linewidth=2))

plt.title("AegisTrace Recon Agent — Architecture & Data Pipeline", color="white", fontsize=15, fontweight="bold", pad=20)
arch_img_path = os.path.join(out_agent_dir, "agent_workflow_architecture.png")
plt.savefig(arch_img_path, facecolor=fig_arch.get_facecolor(), edgecolor="none")
plt.close()
print("[+] Architecture Graph updated at:", arch_img_path)

fig_res = plt.figure(figsize=(14, 8))
fig_res.patch.set_facecolor("#0f172a")
ax_res = fig_res.add_subplot(111)
ax_res.set_facecolor("#1e293b")
ax_res.axis("off")

G = nx.DiGraph()
G.add_node("Scan: scn_0192f1c9de01", color="#38bdf8", size=3000)
G.add_node("Tech: FastAPI", color="#34d399", size=2400)
G.add_node("Tech: PostgreSQL", color="#34d399", size=2400)
G.add_node("GET /api/v1/orders/{order_id}", color="#f59e0b", size=2000)
G.add_node("PATCH /api/v1/orders/{order_id}", color="#ef4444", size=2000)
G.add_node("POST /api/v1/orders", color="#f59e0b", size=2000)
G.add_node("POST /api/v1/auth/login", color="#a855f7", size=2000)
G.add_node("Intel: OWASP API1:2023", color="#ec4899", size=2200)

G.add_edge("Scan: scn_0192f1c9de01", "Tech: FastAPI")
G.add_edge("Scan: scn_0192f1c9de01", "Tech: PostgreSQL")
G.add_edge("Scan: scn_0192f1c9de01", "GET /api/v1/orders/{order_id}")
G.add_edge("Scan: scn_0192f1c9de01", "PATCH /api/v1/orders/{order_id}")
G.add_edge("Scan: scn_0192f1c9de01", "POST /api/v1/orders")
G.add_edge("Scan: scn_0192f1c9de01", "POST /api/v1/auth/login")
G.add_edge("PATCH /api/v1/orders/{order_id}", "Tech: FastAPI")
G.add_edge("Tech: FastAPI", "Intel: OWASP API1:2023")

pos = nx.spring_layout(G, seed=42)
node_colors = [d["color"] for _, d in G.nodes(data=True)]
node_sizes = [d["size"] for _, d in G.nodes(data=True)]

nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax_res, alpha=0.9)
nx.draw_networkx_edges(G, pos, edge_color="#64748b", width=2, arrows=True, arrowsize=15, ax=ax_res)
nx.draw_networkx_labels(G, pos, font_color="white", font_size=8, font_weight="bold", ax=ax_res)

ax_res.set_title("AegisTrace Attack Surface Graph Visualization", color="white", fontsize=15, fontweight="bold", pad=20)
res_img_path = os.path.join(out_agent_dir, "agent_results_graph.png")
plt.savefig(res_img_path, facecolor=fig_res.get_facecolor(), edgecolor="none")
plt.close()
print("[+] Results Graph updated at:", res_img_path)
