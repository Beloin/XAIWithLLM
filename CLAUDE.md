# SOC XAI — Project Guide

## What this project is

Master's research comparing LLM analysis of a network intrusion detection model **with and without XAI** (SHAP + LIME) explanations. The core thesis: injecting explainability data meaningfully improves LLM reasoning about ML models.

## Key design decisions

### Prompt philosophy
- The ML model (Random Forest, ~99.7% accuracy) is **already validated**. The LLM's job is to **explain**, not evaluate performance.
- Training/prediction samples sent to the LLM are **representative examples** to illustrate the feature space — they are NOT the evaluation set. Don't let LLMs waste tokens worrying about sample size.
- Accuracy is stated as a **given fact** (with pipeline context), not something for the LLM to derive.
- A lightweight "Model Context" section is included so the LLM acknowledges performance as credibility context, but does not deep-dive into it.

### Three experiment notebooks (subdirectories)
- `without_XAI/without_xai.ipynb` — LLM analyzes model with raw data only (no SHAP/LIME). Varies `N_SAMPLES` (10, 20, 40).
- `with_XAI/with_xai.ipynb` — LLM analyzes model with SHAP + LIME data. Fixed 20 train/pred samples, varies `N_LOCAL` (5, 10, 15, 25).
- `enforce_knowledge/enforce_knowledge.ipynb` — Two-phase in same chat session: Phase 1 without XAI, Phase 2 injects SHAP + LIME and asks LLM to revise. Paired configs: (N_SAMPLES=10, N_LOCAL=10), (20, 15), (40, 25).

### Legacy/earlier experiment notebooks (root directory)
- `soc_XAI_LLM_COMPARISON_WITH_WITHOUT_XAI.ipynb` — Earlier comparison experiment (two independent chats per model: Chat A without XAI, Chat B with XAI). Results in `resultados_comparison_with_without_xai.json`.
- `soc_XAI_LLM_SHAP_LIME_ENFORCE_KNOWLEDGE.ipynb` — Earlier enforce-knowledge experiment (single-chat two-phase). Results in `resultados_enforce_knowledge.json`.
- Other `soc_XAI_LLM_*.ipynb` notebooks are older iterations/prototypes.

### ML pipeline
Dataset: `Network_logs.csv` (network intrusion detection, 3 classes: BotAttack, Normal, PortScan).
Pipeline: drop IPs → label encode categoricals → StandardScaler on Payload_Size → SMOTE balancing → 70/30 stratified split → Random Forest.

### LLM models (via Ollama at localhost:11434)
| Model | Size | Tier | max_tokens |
|---|---|---|---|
| glm-4.7-flash:latest | ~9B | medium | 8192 |
| qwen3:14b | 14B | medium | 8192 |
| gpt-oss:20b | 20B | medium | 8192 |
| qwen3:30b | 30B | large | 16384 |

- Timeout: 900s (15 min) per request
- Between models, `ollama stop` is called to free VRAM
- qwen3:30b frequently fails on longer contexts — Chat B / Phase 2 often returns empty

## Structure

### Subdirectory experiments (current)
```
without_XAI/
  without_xai.ipynb
  resultados_without_xai_samples_{10,20,40}.json   # one response string per model
with_XAI/
  with_xai.ipynb
  resultados_with_xai_local_{5,10,15,25}.json       # one response string per model
enforce_knowledge/
  enforce_knowledge.ipynb
  resultados_enforce_knowledge_samples_{10,20,40}_local_{10,15,25}.json  # {phase1_without_xai, phase2_with_xai} per model
```

### Root-level files
- `resultados_comparison_with_without_xai.json` — `{chat_a_without_xai, chat_b_with_xai}` per model (legacy)
- `resultados_enforce_knowledge.json` — `{phase1_without_xai, phase2_with_xai}` per model (legacy)
- `validation_llm_xai_responses.ipynb` — Validation notebook: pretty-prints responses, checks feature ranking accuracy, SHAP citation accuracy, fabrication detection, and Chat A vs B improvement.
- `run_all.sh` — converts notebooks to `.py` via `nbconvert`, runs them with `ipython` (needed for `!ollama stop` shell commands), then cleans up generated `.py` files. Each script runs with `cwd` set to its own folder so `../Network_logs.csv` resolves correctly. Requires: `pip install nbconvert`, `ipython` in venv.

## Known issues
- **qwen3:30b** consistently returns empty responses for longer-context phases (Chat B / Phase 2 with XAI data). Works fine for shorter contexts (Chat A / Phase 1). Likely OOM or context-length limit on 30B model via Ollama.
- **Truncation risk**: `max_tokens_analysis` of 8192 can truncate long Phase 2 responses (seen in glm-4.7-flash enforce_knowledge).

## Ground truth SHAP rankings (for validation reference)
Actual top-3 feature importance per class (mean |SHAP|):
- **BotAttack:** Port > Status > Payload_Size
- **Normal:** Port > Status > Payload_Size
- **PortScan:** Payload_Size > Status > Port

Key insight: **User_Agent has near-zero SHAP importance** (< 0.006 for all classes) despite being the feature LLMs most commonly overvalue in their without-XAI analyses.
