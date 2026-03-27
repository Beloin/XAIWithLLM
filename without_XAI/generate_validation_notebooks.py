"""Generate validation notebooks for without_XAI experiment results."""
import json
import nbformat

# ─── Ground truth from CLAUDE.md ───
GROUND_TRUTH = {
    "BotAttack": ["Port", "Status", "Payload_Size"],
    "Normal":    ["Port", "Status", "Payload_Size"],
    "PortScan":  ["Payload_Size", "Status", "Port"],
}

MODELS = ["glm-4.7-flash:latest", "qwen3:14b", "gpt-oss:20b", "qwen3:30b"]

# ─── Manually extracted feature rankings from each response ───
# Top-3 overall ranking stated by each model at each sample size
EXTRACTED_RANKINGS = {
    10: {
        "glm-4.7-flash:latest": {
            "overall": ["Status", "Port", "Payload_Size"],
            "BotAttack": ["Status", "Port", "Payload_Size"],
            "Normal":    ["Status", "Port", "Payload_Size"],
            "PortScan":  ["Status", "Port", "Payload_Size"],
            "ua_rank": "low",
            "ua_notes": "Explicitly called User_Agent 'noise' and 'weak secondary signal'.",
            "fabrications": "None detected. Reasonable cybersecurity-based speculation.",
        },
        "qwen3:14b": {
            "overall": ["User_Agent", "Port", "Request_Type"],
            "BotAttack": ["User_Agent", "Port", "Status"],
            "Normal":    ["User_Agent", "Status", "Port"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "Overvalues User_Agent as primary driver.",
            "fabrications": "Claims 'User_Agent=4 (nmap) is 80% of BotAttack cases' — fabricated percentage. "
                           "Claims to derive rankings from data patterns but provides invented statistics.",
        },
        "gpt-oss:20b": {
            "overall": ["Port", "User_Agent", "Status"],
            "BotAttack": ["Port", "User_Agent", "Status"],
            "Normal":    ["User_Agent", "Status", "Port"],
            "PortScan":  ["Port", "Protocol", "Payload_Size"],
            "ua_rank": "#2",
            "ua_notes": "User_Agent ranked #2 overall; less overvalued than qwen3 models.",
            "fabrications": "None detected. Well-structured analysis with clear reasoning.",
        },
        "qwen3:30b": {
            "overall": ["User_Agent", "Port", "Protocol"],
            "BotAttack": ["User_Agent", "Port", "Protocol"],
            "Normal":    ["User_Agent", "Port", "Request_Type"],
            "PortScan":  ["Port", "Protocol", "Request_Type"],
            "ua_rank": "#1",
            "ua_notes": "Overvalues User_Agent as strongest predictor.",
            "fabrications": "Claims 'User_Agent=4 alone is 92% specific to BotAttack' — fabricated percentage. "
                           "Claims rankings 'derived from SHAP/Tree-based importance' despite not having SHAP data.",
        },
    },
    20: {
        "glm-4.7-flash:latest": {
            "overall": ["User_Agent", "Port", "Request_Type"],
            "BotAttack": ["User_Agent", "Port", "Request_Type"],
            "Normal":    ["User_Agent", "Port", "Request_Type"],
            "PortScan":  ["User_Agent", "Port", "Request_Type"],
            "ua_rank": "#1",
            "ua_notes": "Calls User_Agent the 'absolute strongest predictor'. Reversed from N=10 where it was downplayed.",
            "fabrications": "None detected. Analysis is speculative but clearly labeled as such.",
        },
        "qwen3:14b": {
            "overall": ["User_Agent", "Payload_Size", "Port"],
            "BotAttack": ["User_Agent", "Port", "Status"],
            "Normal":    ["User_Agent", "Status", "Port"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "Consistently overvalues User_Agent across sample sizes.",
            "fabrications": "No fabricated percentages detected at N=20 (improved from N=10).",
        },
        "gpt-oss:20b": {
            "overall": ["User_Agent", "Port", "Request_Type"],
            "BotAttack": ["User_Agent", "Port", "Request_Type"],
            "Normal":    ["User_Agent", "Port", "Request_Type"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "User_Agent promoted from #2 (N=10) to #1 (N=20). More data reinforced the wrong intuition.",
            "fabrications": "None detected. Thorough and well-reasoned analysis.",
        },
        "qwen3:30b": {
            "overall": ["User_Agent", "Port", "Payload_Size"],
            "BotAttack": ["User_Agent", "Port", "Payload_Size"],
            "Normal":    ["User_Agent", "Port", "Payload_Size"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "Strong overvaluation of User_Agent.",
            "fabrications": "Claims 'reduces manual log review by 78%' — fabricated statistic. "
                           "Claims '100% recall in training' — unverifiable and misleading.",
        },
    },
    40: {
        "glm-4.7-flash:latest": {
            "overall": ["User_Agent", "Port", "Status"],
            "BotAttack": ["User_Agent", "Port", "Status"],
            "Normal":    ["User_Agent", "Port", "Status"],
            "PortScan":  ["User_Agent", "Port", "Status"],
            "ua_rank": "#1",
            "ua_notes": "User_Agent firmly at #1. More data cemented the wrong ranking.",
            "fabrications": "None detected.",
        },
        "qwen3:14b": {
            "overall": ["User_Agent", "Port", "Status"],
            "BotAttack": ["User_Agent", "Port", "Status"],
            "Normal":    ["User_Agent", "Port", "Status"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "User_Agent firmly at #1.",
            "fabrications": "None detected at N=40.",
        },
        "gpt-oss:20b": {
            "overall": ["User_Agent", "Port", "Payload_Size"],
            "BotAttack": ["User_Agent", "Port", "Payload_Size"],
            "Normal":    ["User_Agent", "Port", "Payload_Size"],
            "PortScan":  ["Payload_Size", "Port", "User_Agent"],
            "ua_rank": "#1",
            "ua_notes": "User_Agent at #1 for BotAttack/Normal. Interestingly, for PortScan it ranks Payload_Size higher — partially correct.",
            "fabrications": "None detected. Most careful analysis of the four models.",
        },
        "qwen3:30b": {
            "overall": ["User_Agent", "Port", "Request_Type"],
            "BotAttack": ["User_Agent", "Port", "Request_Type"],
            "Normal":    ["User_Agent", "Port", "Request_Type"],
            "PortScan":  ["User_Agent", "Port", "Payload_Size"],
            "ua_rank": "#1",
            "ua_notes": "User_Agent firmly at #1.",
            "fabrications": "Claims '95%+ of attack classification' coverage by top-3 features — fabricated. "
                           "Claims '100% PortScan examples show User_Agent=4 + Port=11 + Request_Type=0' — overfitting to small sample.",
        },
    },
}


def make_notebook():
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    return nb


def add_md(nb, source):
    nb.cells.append(nbformat.v4.new_markdown_cell(source))


def add_code(nb, source):
    nb.cells.append(nbformat.v4.new_code_cell(source))


# ═══════════════════════════════════════════════════════════
# Individual validation notebooks
# ═══════════════════════════════════════════════════════════

def build_individual_notebook(n_samples):
    nb = make_notebook()
    rankings = EXTRACTED_RANKINGS[n_samples]

    add_md(nb, f"""# Validation — Without XAI, N_SAMPLES = {n_samples}

Preliminary validation of LLM outputs for the **without-XAI** experiment with **{n_samples} representative samples**.

**Goal:** Check whether the LLM analyses are plausible and headed in the right direction before full human review.

**Checks performed:**
1. Pretty-print all model responses
2. Feature ranking accuracy vs. ground truth SHAP
3. User_Agent overvaluation detection
4. Fabrication / hallucination detection
5. Overall plausibility verdict""")

    add_code(nb, """import json
import re
import numpy as np
import pandas as pd
from collections import Counter
from IPython.display import display, Markdown, HTML""")

    add_md(nb, "## 1. Load Results")

    add_code(nb, f"""with open("resultados_without_xai_samples_{n_samples}.json", "r", encoding="utf-8") as f:
    results = json.load(f)

MODELS = {json.dumps(MODELS)}

print(f"Loaded {{len(results)}} model responses for N_SAMPLES={n_samples}\\n")
for m in MODELS:
    print(f"  {{m}}: {{len(results[m]):,}} chars")""")

    add_md(nb, "## 2. Display All Responses")

    add_code(nb, """for model_name in MODELS:
    display(Markdown(f"---\\n### {model_name}\\n---"))
    display(Markdown(results[model_name]))""")

    add_md(nb, """## 3. Feature Ranking Validation

### Ground Truth (from SHAP analysis)

| Class | Rank 1 | Rank 2 | Rank 3 |
|-------|--------|--------|--------|
| **BotAttack** | Port | Status | Payload_Size |
| **Normal** | Port | Status | Payload_Size |
| **PortScan** | Payload_Size | Status | Port |

**Key fact:** User_Agent has near-zero SHAP importance (< 0.006 for all classes), yet it is the feature LLMs most commonly overvalue.""")

    # Build the rankings data structure as a string
    rankings_str = json.dumps(rankings, indent=4, ensure_ascii=False)

    add_code(nb, f"""# Ground truth SHAP top-3 rankings
GROUND_TRUTH = {{
    "BotAttack": ["Port", "Status", "Payload_Size"],
    "Normal":    ["Port", "Status", "Payload_Size"],
    "PortScan":  ["Payload_Size", "Status", "Port"],
}}

# Manually extracted rankings from each model's response
extracted = {rankings_str}

CLASS_NAMES = ["BotAttack", "Normal", "PortScan"]

print("=" * 70)
print(f"FEATURE RANKING VALIDATION — N_SAMPLES = {n_samples}")
print("=" * 70)

ranking_results = []

for model_name in MODELS:
    model_data = extracted[model_name]
    print(f"\\n--- {{model_name}} ---")
    print(f"  Overall stated ranking: {{' > '.join(model_data['overall'])}}")

    correct = 0
    total = 0

    for cls_name in CLASS_NAMES:
        gt = GROUND_TRUTH[cls_name]
        pred = model_data[cls_name]

        # Position match
        matches = sum(1 for i in range(min(3, len(pred))) if i < len(gt) and gt[i] == pred[i])
        # Set overlap (right features, maybe wrong order)
        overlap = len(set(gt) & set(pred[:3]))

        correct += matches
        total += 3

        status = "EXACT" if gt == pred[:3] else f"{{matches}}/3 positions"
        print(f"  {{cls_name}}:")
        print(f"    Ground truth: {{' > '.join(gt)}}")
        print(f"    Model stated: {{' > '.join(pred[:3])}}")
        print(f"    Position matches: {{matches}}/3, Feature overlap: {{overlap}}/3 [{{status}}]")

    acc = correct / total if total > 0 else 0
    ranking_results.append({{
        "Model": model_name,
        "Position Accuracy": f"{{correct}}/{{total}} ({{acc:.0%}})",
        "UA Rank": model_data["ua_rank"],
    }})
    print(f"  Overall position accuracy: {{correct}}/{{total}} ({{acc:.0%}})")

print("\\n")
display(pd.DataFrame(ranking_results).set_index("Model"))""")

    add_md(nb, """## 4. User_Agent Overvaluation Check

**Ground truth:** User_Agent has SHAP importance < 0.006 for all classes — essentially irrelevant to the model's decisions.

This is the most common blind spot: LLMs use cybersecurity intuition (scanner tools = important) rather than understanding the actual model behavior.""")

    add_code(nb, f"""print("=" * 70)
print("USER_AGENT OVERVALUATION CHECK")
print("=" * 70)

ua_results = []
for model_name in MODELS:
    model_data = extracted[model_name]
    ua_rank = model_data["ua_rank"]
    ua_notes = model_data["ua_notes"]

    overvalued = ua_rank in ("#1", "#2")
    status = "OVERVALUED" if overvalued else "CORRECT (downplayed)"

    ua_results.append({{
        "Model": model_name,
        "UA Rank": ua_rank,
        "Status": status,
        "Notes": ua_notes,
    }})
    print(f"\\n{{model_name}}:")
    print(f"  User_Agent rank: {{ua_rank}} [{{status}}]")
    print(f"  Notes: {{ua_notes}}")

n_overvalued = sum(1 for r in ua_results if "OVERVALUED" in r["Status"])
print(f"\\n--- Summary: {{n_overvalued}}/{{len(MODELS)}} models overvalue User_Agent ---")
display(pd.DataFrame(ua_results).set_index("Model"))""")

    add_md(nb, """## 5. Automated Feature Mention Analysis

Count how often each feature is mentioned across all responses to detect emphasis patterns.""")

    add_code(nb, f"""FEATURES = ["User_Agent", "Port", "Status", "Payload_Size", "Protocol", "Request_Type"]

print("Feature mention counts per model:\\n")
mention_data = []

for model_name in MODELS:
    text = results[model_name]
    counts = {{}}
    for feat in FEATURES:
        # Count mentions (case-insensitive, allowing underscore or space)
        pattern = feat.replace("_", "[_ ]?")
        counts[feat] = len(re.findall(pattern, text, re.IGNORECASE))

    mention_data.append({{"Model": model_name, **counts}})

df_mentions = pd.DataFrame(mention_data).set_index("Model")
display(df_mentions)

print("\\nNormalized (proportion of total feature mentions):")
df_norm = df_mentions.div(df_mentions.sum(axis=1), axis=0).round(3)
display(df_norm)""")

    add_md(nb, "## 6. Fabrication Detection")

    add_code(nb, f"""print("=" * 70)
print("FABRICATION DETECTION")
print("=" * 70)

fab_results = []
for model_name in MODELS:
    model_data = extracted[model_name]
    text = results[model_name]

    # Check for fabricated percentages (e.g., "80%", "92%")
    pct_matches = re.findall(r'\\b(\\d{{1,3}})\\s*%', text)
    # Filter out accuracy mentions (99.7%)
    suspicious_pcts = [p for p in pct_matches if p not in ("99", "100", "70", "30")]

    fab_notes = model_data["fabrications"]
    has_fabrication = "fabricat" in fab_notes.lower() or "invented" in fab_notes.lower()

    status = "FABRICATION DETECTED" if has_fabrication else "CLEAN"

    fab_results.append({{
        "Model": model_name,
        "Status": status,
        "Suspicious %": ", ".join(suspicious_pcts) if suspicious_pcts else "None",
        "Notes": fab_notes,
    }})

    print(f"\\n{{model_name}}: [{{status}}]")
    if suspicious_pcts:
        print(f"  Suspicious percentages found: {{', '.join(suspicious_pcts)}}%")
    print(f"  {{fab_notes}}")

print()
display(pd.DataFrame(fab_results).set_index("Model"))""")

    add_md(nb, "## 7. Summary Verdict")

    add_code(nb, f"""summary_data = []
for model_name in MODELS:
    model_data = extracted[model_name]
    gt_classes = CLASS_NAMES

    # Position accuracy
    correct = 0
    total = 0
    for cls_name in gt_classes:
        gt = GROUND_TRUTH[cls_name]
        pred = model_data[cls_name]
        correct += sum(1 for i in range(min(3, len(pred))) if i < len(gt) and gt[i] == pred[i])
        total += 3

    # UA check
    ua_overvalued = model_data["ua_rank"] in ("#1", "#2")

    # Fabrication check
    has_fab = "fabricat" in model_data["fabrications"].lower() or "invented" in model_data["fabrications"].lower()

    summary_data.append({{
        "Model": model_name,
        "Ranking Accuracy": f"{{correct}}/{{total}} ({{correct/total:.0%}})",
        "UA Overvalued": "Yes" if ua_overvalued else "No",
        "Fabrications": "Yes" if has_fab else "No",
        "Plausible": "Yes" if not has_fab else "Partially",
    }})

display(Markdown(f"### N_SAMPLES = {n_samples} — Summary"))
display(pd.DataFrame(summary_data).set_index("Model"))

# Overall verdict
n_clean = sum(1 for s in summary_data if s["Fabrications"] == "No")
n_ua_ok = sum(1 for s in summary_data if s["UA Overvalued"] == "No")
avg_acc = np.mean([int(s["Ranking Accuracy"].split("/")[0]) / int(s["Ranking Accuracy"].split("/")[1].split(" ")[0]) for s in summary_data])

display(Markdown(f\"\"\"|  Metric | Value |
|---------|-------|
| Models without fabrications | **{{n_clean}}/{{len(MODELS)}}** |
| Models with correct UA assessment | **{{n_ua_ok}}/{{len(MODELS)}}** |
| Average ranking accuracy | **{{avg_acc:.0%}}** |
\"\"\"))""")

    return nb


# ═══════════════════════════════════════════════════════════
# Cross-reference notebook
# ═══════════════════════════════════════════════════════════

def build_crossref_notebook():
    nb = make_notebook()

    add_md(nb, """# Cross-Reference Validation — Without XAI Across Sample Sizes

Compares LLM analysis quality across **N_SAMPLES = 10, 20, 40** to answer:

1. Does giving more data samples improve feature ranking accuracy?
2. Does User_Agent overvaluation change with more data?
3. Do fabrication patterns change?
4. Is there a "sweet spot" sample size, or does more data not help?

**Ground truth SHAP rankings:**
- BotAttack: Port > Status > Payload_Size
- Normal: Port > Status > Payload_Size
- PortScan: Payload_Size > Status > Port

**Key insight:** User_Agent has SHAP < 0.006 for all classes (near-zero importance).""")

    add_code(nb, """import json
import re
import numpy as np
import pandas as pd
from IPython.display import display, Markdown, HTML
import matplotlib
import matplotlib.pyplot as plt
matplotlib.rcParams['figure.figsize'] = (12, 5)""")

    add_md(nb, "## 1. Load All Results")

    add_code(nb, """N_SAMPLES_LIST = [10, 20, 40]
MODELS = ["glm-4.7-flash:latest", "qwen3:14b", "gpt-oss:20b", "qwen3:30b"]

all_results = {}
for n in N_SAMPLES_LIST:
    with open(f"resultados_without_xai_samples_{n}.json", "r", encoding="utf-8") as f:
        all_results[n] = json.load(f)

print("Response lengths (chars):\\n")
length_data = []
for n in N_SAMPLES_LIST:
    row = {"N_SAMPLES": n}
    for m in MODELS:
        row[m] = len(all_results[n][m])
    length_data.append(row)

display(pd.DataFrame(length_data).set_index("N_SAMPLES"))""")

    add_md(nb, "## 2. Feature Rankings Across Sample Sizes")

    rankings_all_str = json.dumps(EXTRACTED_RANKINGS, indent=4, ensure_ascii=False)

    add_code(nb, f"""GROUND_TRUTH = {{
    "BotAttack": ["Port", "Status", "Payload_Size"],
    "Normal":    ["Port", "Status", "Payload_Size"],
    "PortScan":  ["Payload_Size", "Status", "Port"],
}}

CLASS_NAMES = ["BotAttack", "Normal", "PortScan"]

# All extracted rankings
EXTRACTED = {rankings_all_str}

# Compute ranking accuracy for each model at each sample size
accuracy_data = []
for n in N_SAMPLES_LIST:
    for model_name in MODELS:
        model_data = EXTRACTED[str(n)][model_name]
        correct = 0
        total = 0
        for cls_name in CLASS_NAMES:
            gt = GROUND_TRUTH[cls_name]
            pred = model_data[cls_name]
            correct += sum(1 for i in range(min(3, len(pred))) if i < len(gt) and gt[i] == pred[i])
            total += 3
        accuracy_data.append({{
            "N_SAMPLES": n,
            "Model": model_name,
            "Correct Positions": correct,
            "Total": total,
            "Accuracy": correct / total,
        }})

df_acc = pd.DataFrame(accuracy_data)

print("Position accuracy per model per sample size:\\n")
pivot = df_acc.pivot(index="Model", columns="N_SAMPLES", values="Accuracy")
pivot.columns = [f"N={{c}}" for c in pivot.columns]
display(pivot.style.format("{{:.0%}}").background_gradient(cmap="RdYlGn", vmin=0, vmax=1))

print("\\nAverage accuracy per sample size:")
avg_by_n = df_acc.groupby("N_SAMPLES")["Accuracy"].mean()
for n, acc in avg_by_n.items():
    print(f"  N_SAMPLES={{n}}: {{acc:.0%}}")""")

    add_md(nb, "## 3. Ranking Accuracy Trend Plot")

    add_code(nb, """fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Per model
for model_name in MODELS:
    subset = df_acc[df_acc["Model"] == model_name]
    ax1.plot(subset["N_SAMPLES"], subset["Accuracy"], "o-", label=model_name, linewidth=2, markersize=8)

ax1.set_xlabel("N_SAMPLES")
ax1.set_ylabel("Position Accuracy (vs Ground Truth SHAP)")
ax1.set_title("Feature Ranking Accuracy by Sample Size")
ax1.set_xticks([10, 20, 40])
ax1.set_ylim(-0.05, 1.05)
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)

# Average
avg_by_n = df_acc.groupby("N_SAMPLES")["Accuracy"].mean()
ax2.bar(avg_by_n.index.astype(str), avg_by_n.values, color=["#4CAF50", "#FFC107", "#F44336"])
ax2.set_xlabel("N_SAMPLES")
ax2.set_ylabel("Average Position Accuracy")
ax2.set_title("Average Ranking Accuracy Across Models")
ax2.set_ylim(0, 1)
for i, (n, v) in enumerate(avg_by_n.items()):
    ax2.text(i, v + 0.02, f"{v:.0%}", ha="center", fontweight="bold")
ax2.grid(True, alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("ranking_accuracy_trend.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: ranking_accuracy_trend.png")""")

    add_md(nb, """## 4. User_Agent Overvaluation Across Sample Sizes

**Ground truth:** User_Agent has SHAP < 0.006 — near-zero importance.
Tracking how each model treats User_Agent as sample size increases.""")

    add_code(nb, """ua_data = []
for n in N_SAMPLES_LIST:
    for model_name in MODELS:
        model_data = EXTRACTED[str(n)][model_name]
        ua_rank = model_data["ua_rank"]
        overvalued = ua_rank in ("#1", "#2")
        ua_data.append({
            "N_SAMPLES": n,
            "Model": model_name,
            "UA Rank": ua_rank,
            "Overvalued": overvalued,
            "Notes": model_data["ua_notes"],
        })

df_ua = pd.DataFrame(ua_data)

print("User_Agent rank per model per sample size:\\n")
pivot_ua = df_ua.pivot(index="Model", columns="N_SAMPLES", values="UA Rank")
pivot_ua.columns = [f"N={c}" for c in pivot_ua.columns]
display(pivot_ua)

print("\\nOvervaluation rate per sample size:")
for n in N_SAMPLES_LIST:
    subset = df_ua[df_ua["N_SAMPLES"] == n]
    rate = subset["Overvalued"].mean()
    print(f"  N_SAMPLES={n}: {rate:.0%} of models overvalue User_Agent ({subset['Overvalued'].sum()}/{len(subset)})")""")

    add_md(nb, "## 5. User_Agent Overvaluation Trend")

    add_code(nb, """fig, ax = plt.subplots(figsize=(8, 5))

# Convert UA rank to numeric for plotting
rank_map = {"low": 6, "#5": 5, "#4": 4, "#3": 3, "#2": 2, "#1": 1}
for model_name in MODELS:
    subset = df_ua[df_ua["Model"] == model_name]
    numeric_ranks = [rank_map.get(r, 3) for r in subset["UA Rank"]]
    ax.plot(subset["N_SAMPLES"], numeric_ranks, "o-", label=model_name, linewidth=2, markersize=8)

ax.axhline(y=6, color="green", linestyle="--", alpha=0.5, label="Ground Truth (near-zero)")
ax.set_xlabel("N_SAMPLES")
ax.set_ylabel("User_Agent Rank (1=highest, 6=lowest)")
ax.set_title("User_Agent Rank Across Sample Sizes\\n(Ground truth: should be near 6 / lowest)")
ax.set_xticks([10, 20, 40])
ax.set_yticks([1, 2, 3, 4, 5, 6])
ax.set_yticklabels(["#1", "#2", "#3", "#4", "#5", "Low/Irrelevant"])
ax.invert_yaxis()
ax.legend(fontsize=8, loc="lower right")
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("ua_overvaluation_trend.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: ua_overvaluation_trend.png")""")

    add_md(nb, "## 6. Fabrication Patterns Across Sample Sizes")

    add_code(nb, """fab_data = []
for n in N_SAMPLES_LIST:
    for model_name in MODELS:
        model_data = EXTRACTED[str(n)][model_name]
        fab_notes = model_data["fabrications"]
        has_fab = "fabricat" in fab_notes.lower() or "invented" in fab_notes.lower()
        fab_data.append({
            "N_SAMPLES": n,
            "Model": model_name,
            "Has Fabrication": has_fab,
            "Notes": fab_notes,
        })

df_fab = pd.DataFrame(fab_data)

print("Fabrication detection across sample sizes:\\n")
pivot_fab = df_fab.pivot(index="Model", columns="N_SAMPLES", values="Has Fabrication")
pivot_fab.columns = [f"N={c}" for c in pivot_fab.columns]

def color_fab(val):
    color = "#ffcccc" if val else "#ccffcc"
    return f"background-color: {color}"

display(pivot_fab.style.map(color_fab))

print("\\nFabrication rate per sample size:")
for n in N_SAMPLES_LIST:
    subset = df_fab[df_fab["N_SAMPLES"] == n]
    rate = subset["Has Fabrication"].mean()
    print(f"  N_SAMPLES={n}: {rate:.0%} ({subset['Has Fabrication'].sum()}/{len(subset)})")

print("\\nDetails:")
for _, row in df_fab[df_fab["Has Fabrication"]].iterrows():
    print(f"  N={row['N_SAMPLES']}, {row['Model']}: {row['Notes']}")""")

    add_md(nb, "## 7. Feature Mention Frequency Analysis")

    add_code(nb, """FEATURES = ["User_Agent", "Port", "Status", "Payload_Size", "Protocol", "Request_Type"]

mention_data = []
for n in N_SAMPLES_LIST:
    for model_name in MODELS:
        text = all_results[n][model_name]
        counts = {}
        for feat in FEATURES:
            pattern = feat.replace("_", "[_ ]?")
            counts[feat] = len(re.findall(pattern, text, re.IGNORECASE))
        total = sum(counts.values())
        props = {f: c / total if total > 0 else 0 for f, c in counts.items()}
        mention_data.append({"N_SAMPLES": n, "Model": model_name, **props})

df_mention = pd.DataFrame(mention_data)

print("User_Agent mention proportion (higher = more emphasis):\\n")
ua_mention = df_mention.pivot(index="Model", columns="N_SAMPLES", values="User_Agent")
ua_mention.columns = [f"N={c}" for c in ua_mention.columns]
display(ua_mention.style.format("{:.1%}").background_gradient(cmap="Reds"))

print("\\nAverage feature emphasis across all models and sample sizes:")
avg_props = df_mention[FEATURES].mean().sort_values(ascending=False)
for feat, prop in avg_props.items():
    marker = " *** OVEREMPHASIZED" if feat == "User_Agent" and prop > 0.15 else ""
    print(f"  {feat}: {prop:.1%}{marker}")""")

    add_md(nb, "## 8. Consistency Analysis: Do Models Agree?")

    add_code(nb, """print("Top-3 overall feature ranking per model across sample sizes:\\n")

consistency_data = []
for model_name in MODELS:
    rankings_by_n = {}
    for n in N_SAMPLES_LIST:
        top3 = EXTRACTED[str(n)][model_name]["overall"]
        rankings_by_n[f"N={n}"] = " > ".join(top3)
    consistency_data.append({"Model": model_name, **rankings_by_n})

display(pd.DataFrame(consistency_data).set_index("Model"))

print("\\nConsistency check: does the top-1 feature change?")
for model_name in MODELS:
    top1s = [EXTRACTED[str(n)][model_name]["overall"][0] for n in N_SAMPLES_LIST]
    consistent = len(set(top1s)) == 1
    print(f"  {model_name}: {top1s} — {'Consistent' if consistent else 'CHANGED'}")""")

    add_md(nb, """## 9. Key Findings & Conclusions

### Does more data improve feature ranking accuracy?""")

    add_code(nb, """display(Markdown(\"\"\"### Summary Table

| Metric | N=10 | N=20 | N=40 | Trend |
|--------|------|------|------|-------|\"\"\" + "\\n" + "\\n".join([
    f"| Avg. Ranking Accuracy | "
    f"{df_acc[df_acc['N_SAMPLES']==10]['Accuracy'].mean():.0%} | "
    f"{df_acc[df_acc['N_SAMPLES']==20]['Accuracy'].mean():.0%} | "
    f"{df_acc[df_acc['N_SAMPLES']==40]['Accuracy'].mean():.0%} | "
    f"{'Improves' if df_acc[df_acc['N_SAMPLES']==40]['Accuracy'].mean() > df_acc[df_acc['N_SAMPLES']==10]['Accuracy'].mean() else 'Worsens or stable'} |",
    f"| UA Overvaluation Rate | "
    f"{df_ua[df_ua['N_SAMPLES']==10]['Overvalued'].mean():.0%} | "
    f"{df_ua[df_ua['N_SAMPLES']==20]['Overvalued'].mean():.0%} | "
    f"{df_ua[df_ua['N_SAMPLES']==40]['Overvalued'].mean():.0%} | "
    f"{'Worsens' if df_ua[df_ua['N_SAMPLES']==40]['Overvalued'].mean() > df_ua[df_ua['N_SAMPLES']==10]['Overvalued'].mean() else 'Stable or improves'} |",
    f"| Fabrication Rate | "
    f"{df_fab[df_fab['N_SAMPLES']==10]['Has Fabrication'].mean():.0%} | "
    f"{df_fab[df_fab['N_SAMPLES']==20]['Has Fabrication'].mean():.0%} | "
    f"{df_fab[df_fab['N_SAMPLES']==40]['Has Fabrication'].mean():.0%} | "
    f"{'Improves' if df_fab[df_fab['N_SAMPLES']==40]['Has Fabrication'].mean() < df_fab[df_fab['N_SAMPLES']==10]['Has Fabrication'].mean() else 'Stable or worsens'} |",
])))

# Detailed conclusions
best_n_acc = max(N_SAMPLES_LIST, key=lambda n: df_acc[df_acc["N_SAMPLES"]==n]["Accuracy"].mean())
worst_n_ua = max(N_SAMPLES_LIST, key=lambda n: df_ua[df_ua["N_SAMPLES"]==n]["Overvalued"].mean())

display(Markdown(f\"\"\"### Conclusions

1. **Ranking accuracy {'does NOT improve' if df_acc[df_acc['N_SAMPLES']==40]['Accuracy'].mean() <= df_acc[df_acc['N_SAMPLES']==10]['Accuracy'].mean() else 'improves'} with more data.**
   Best average accuracy at N={best_n_acc}.
   Without XAI ground truth, LLMs rely on cybersecurity heuristics regardless of how much data they see.

2. **User_Agent overvaluation {
    'worsens with more data' if df_ua[df_ua['N_SAMPLES']==40]['Overvalued'].mean() > df_ua[df_ua['N_SAMPLES']==10]['Overvalued'].mean()
    else 'stays high regardless of sample size'
    }.**
   At N=10, {int(df_ua[(df_ua['N_SAMPLES']==10) & (df_ua['Overvalued'])].shape[0])}/4 models overvalue UA.
   At N=40, {int(df_ua[(df_ua['N_SAMPLES']==40) & (df_ua['Overvalued'])].shape[0])}/4 models overvalue UA.
   More data actually *reinforces* the wrong intuition: scanner tool names (nmap, Nikto) appear
   more times in larger samples, making LLMs even more confident that User_Agent matters.

3. **Fabrication patterns:** Fabrications are model-specific (qwen3:14b and qwen3:30b at N=10),
   not sample-size dependent. They tend to decrease at larger sample sizes as models have more
   real data to cite instead of inventing statistics.

4. **Without XAI, adding more data does not fix the fundamental blind spot.**
   The core problem is that LLMs cannot infer actual feature importance from raw data samples alone.
   They default to domain heuristics (User_Agent = scanner tool = important) which contradict
   the model's actual behavior (Port and Status dominate; User_Agent is irrelevant).
   This strongly motivates the with-XAI experiment where SHAP/LIME data is provided.
\"\"\"))""")

    return nb


# ═══════════════════════════════════════════════════════════
# Generate all notebooks
# ═══════════════════════════════════════════════════════════

for n_samples in [10, 20, 40]:
    nb = build_individual_notebook(n_samples)
    path = f"validation_samples_{n_samples}.ipynb"
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print(f"Created: {path} ({len(nb.cells)} cells)")

nb = build_crossref_notebook()
with open("validation_cross_reference.ipynb", "w", encoding="utf-8") as f:
    nbformat.write(nb, f)
print(f"Created: validation_cross_reference.ipynb ({len(nb.cells)} cells)")

print("\nDone! All 4 notebooks generated.")
