# SOC XAI Project — Agent Context

## Project Purpose

Master's thesis research: **Does injecting XAI (SHAP + LIME) explanations into LLM prompts improve their ability to reason about and explain ML model behavior?**

Core hypothesis: LLMs produce more accurate, grounded explanations when given explicit explainability data compared to analyzing raw data alone.

---

## Research Design

### Three Experiment Tracks

| Experiment | Location | Description |
|------------|----------|-------------|
| **Without XAI** | `intrusion_detection_logs/without_XAI/` | Baseline: LLM analyzes model with raw data samples only. Varies N_SAMPLES (10, 20, 40). |
| **With XAI** | `intrusion_detection_logs/with_XAI/` | Intervention: LLM receives SHAP global importance + SHAP local + LIME local explanations. Fixed 20 samples, varies N_LOCAL (5, 10, 15, 25). |
| **Enforce Knowledge** | `intrusion_detection_logs/enforce_knowledge/` | Two-phase paired design: Same chat, Phase 1 without XAI → Phase 2 injects SHAP+LIME. Paired configs: (10,10), (20,15), (40,25). |

### Legacy Experiments (Root Directory)

| File | Description |
|------|-------------|
| `resultados_comparison_with_without_xai.json` | Earlier independent chat experiments (Chat A without XAI vs Chat B with XAI) |
| `resultados_enforce_knowledge.json` | Earlier enforce-knowledge results |

---

## ML Pipeline

**Dataset:** `intrusion_detection_logs/Network_logs.csv` — Network intrusion detection (3 classes: BotAttack, Normal, PortScan)

**Features:** Port, Request_Type, Protocol, Payload_Size, User_Agent, Status (numerically encoded)

**Pipeline Steps:**
1. Drop IP columns
2. Label encode categorical features
3. StandardScaler on Payload_Size
4. SMOTE class balancing
5. 70/30 stratified train/test split
6. Random Forest classifier (~99.7% accuracy)

**Key Insight:** Model is already validated. The LLM's job is to EXPLAIN the model, not evaluate its performance.

---

## LLM Configuration

All models run locally via Ollama at `localhost:11434`.

| Model | Size | Tier | max_tokens |
|-------|------|------|-----------|
| glm-4.7-flash:latest | ~9B | medium | 8192 |
| qwen3:14b | 14B | medium | 8192 |
| gpt-oss:20b | 20B | medium | 8192 |
| qwen3:30b | 30B | large | 16384 |

**Timeout:** 900s (15 min) per request

**Between models:** Run `ollama stop <model>` to free VRAM before switching

---

## Ground Truth SHAP Rankings

From TreeExplainer analysis of the trained Random Forest:

| Class | Top-1 | Top-2 | Top-3 |
|-------|-------|-------|-------|
| **BotAttack** | Port (0.244) | Status (0.129) | Payload_Size (0.091) |
| **Normal** | Port (0.273) | Payload_Size (0.184) | Status (0.195) |
| **PortScan** | Payload_Size (0.261) | Status (0.066) | Port (0.030) |

**Critical:** User_Agent has importance < 0.006 for all classes. Any LLM claim of User_Agent importance is fabrication/bias.

---

## Key Findings (Executive Summary)

### Without XAI (Baseline)
- **Feature ranking accuracy:** 25% at best (1/4 models correct)
- **User_Agent bias:** 75% of models overvalue it
- **Sample size effect:** No improvement from N=20 to N=40 (plateau at 25% accuracy)
- **Conclusion:** Raw data alone insufficient for LLMs to infer feature importance

### With XAI (Intervention)
- **Feature ranking accuracy:** 100% when models succeed (N_LOCAL≥15)
- **User_Agent bias:** ~0% when XAI present
- **SHAP citation:** Within 0.02 of ground truth values
- **Model success rate:** Config-dependent (N_LOCAL=5/10 have failures, N_LOCAL=15/25 work for all)

### Enforce Knowledge (Paired Design)
- Two-phase design enables within-model comparison
- XAI injection in Phase 2 corrects wrong intuitions from Phase 1

---

## Model Recommendations

| Model | Status | Use Case |
|-------|--------|----------|
| **gpt-oss:20b** | Primary choice | Most reliable (100%), longest responses, best SHAP citations |
| **qwen3:14b** | Good alternative | Stable, moderate response length |
| **glm-4.7-flash** | Use with caution | Works at N_LOCAL≥15, truncates at N_LOCAL=10 |
| **qwen3:30b** | Avoid for critical work | Fails at low N_LOCAL (5,10), counterintuitive pattern |

---

## Configuration Recommendations

### For With-XAI Experiments
- **N_LOCAL=15** — Sweet spot: all models work, good quality, manageable context
- **N_LOCAL=25** — Also valid if context not constrained
- **Avoid N_LOCAL=5, 10** — qwen3:30b failures, glm truncation

### For Without-XAI Baseline
- **N_SAMPLES=20** — Optimal (no gain at N=40, N=10 too vague)

### For Enforce Knowledge (Paired)
- **(N_SAMPLES=20, N_LOCAL=15)** — Recommended pairing

---

## Known Issues

| Issue | Affected Config | Impact |
|-------|-----------------|--------|
| qwen3:30b empty responses | N_LOCAL < 15 | Cannot compare all 4 models |
| glm-4.7-flash truncation | N_LOCAL=10 | 60% shorter response |
| Token limit (8192) | Phase 2 long responses | Possible truncation |
| VRAM pressure | Sequential model runs | Requires `ollama stop` between models |

---

## File Structure

```
soc_xai/
├── CLAUDE.md                    # Project guide (similar to this file)
├── AGENTS.md                    # This file — comprehensive context for agents
├── README.md                    # Public-facing README
├── run_all.sh                   # Run all notebooks via nbconvert + ipython
│
└── intrusion_detection_logs/    # Dataset + all related experiments
    ├── Network_logs.csv         # Dataset
    ├── README.md                # Dataset folder overview
    ├── DATASET.md               # Dataset documentation
    ├── CONCLUSION.md            # Research conclusions
    ├── XAI_EXPLANATION_QUALITY.md # Quality assessment of LLM explanations
    │
    ├── without_XAI/
    │   ├── without_xai.ipynb
    │   ├── resultados_without_xai_samples_{10,20,40}.json
    │   └── VALIDATION_FINDINGS.md
    │
    ├── with_XAI/
    │   ├── with_xai.ipynb
    │   ├── resultados_with_xai_local_{5,10,15,25}.json
    │   └── VALIDATION_FINDINGS.md
    │
    └── enforce_knowledge/
        ├── enforce_knowledge.ipynb
        ├── resultados_enforce_knowledge_samples_*_local_*.json
        └── VALIDATION_FINDINGS.md
```

---

## Running Experiments

### Using run_all.sh
```bash
./run_all.sh
```
Converts notebooks to `.py` via `nbconvert`, runs with `ipython` (needed for `!ollama stop` commands), cleans up.

Each script runs with `cwd` set to its folder, so `../intrusion_detection_logs/Network_logs.csv` resolves correctly.

### Prerequisites
```bash
pip install nbconvert ipython
```

---

## Prompt Philosophy

- Model performance (99.7% accuracy) is stated as **given context**, not something for LLM to derive
- Training/prediction samples are **representative examples** to illustrate feature space
- LLM receives **SHAP global importance** (per-class feature rankings) + **SHAP local** (per-instance explanations) + **LIME local**
- The goal is to measure whether XAI data improves explanation quality, not to evaluate the ML model

---

## Validation Metrics

1. **Feature Ranking Accuracy:** Position match against ground truth SHAP rankings
2. **User_Agent Bias:** Detection of overvalued importance (should be near-zero)
3. **SHAP Citation Accuracy:** MAE between cited values and ground truth (< 0.02 is good)
4. **Fabrication Detection:** Invented statistics, fake misclassifications, etc.

---

## Thesis Support

The data supports the core thesis: XAI injection improves LLM reasoning about ML models.

| Evidence | Without XAI | With XAI | Supports Thesis |
|----------|-------------|----------|-----------------|
| Feature ranking accuracy | 25% | 100% | Strong |
| User_Agent bias reduction | 75% | ~0% | Strong |
| SHAP/LIME citation | N/A | 100% valid responses | Strong |
| Model consistency | Variable | Stable (good configs) | Moderate |

**Caveats:** Benefits only realized when model succeeds and config is adequate (N_LOCAL≥15).

---

## Quick Reference Commands

```bash
# List results files
ls intrusion_detection_logs/without_XAI/resultados_*.json
ls intrusion_detection_logs/with_XAI/resultados_*.json
ls intrusion_detection_logs/enforce_knowledge/resultados_*.json

# Run single notebook
cd intrusion_detection_logs/without_XAI && ipython -c "%run without_xai.ipynb"

# Stop Ollama model between runs
ollama stop qwen3:30b
```

---

## Research Timeline

1. **Experiments completed:** Without XAI (3 configs), With XAI (4 configs), Enforce Knowledge (3 configs)
2. **Validation notebooks created:** Per-config and cross-reference analysis
3. **Key papers:** LLM explainability, SHAP/LIME interpretation, XAI in cybersecurity
4. **Next steps:** Human validation study, thesis write-up

---

## Author / Context

Master's research project comparing LLM analysis of ML model behavior with and without XAI data. Focus on cybersecurity application (network intrusion detection).

Ground truth provided by SHAP TreeExplainer analysis of Random Forest classifier trained on network traffic logs.

Key insight: XAI data corrects LLM semantic intuition — User_Agent looks important to LLMs (nmap, curl are security tools), but SHAP shows the actual model doesn't use it. This is the central thesis evidence.