# Enforce Knowledge Validation Findings

## Overview

This document summarizes the automated validation of LLM responses from the enforce_knowledge experiment, which tests LLM analysis of a network intrusion detection model in a two-phase chat session:

- **Phase 1:** Model info + data samples (no XAI)
- **Phase 2:** Same chat, SHAP global + SHAP local + LIME local injected → revised analysis

## Configurations Tested

| Config | N_SAMPLES | N_LOCAL | File |
|--------|-----------|---------|------|
| 1      | 10        | 10      | `resultados_enforce_knowledge_samples_10_local_10.json` |
| 2      | 20        | 15      | `resultados_enforce_knowledge_samples_20_local_15.json` |
| 3      | 40        | 25      | `resultados_enforce_knowledge_samples_40_local_25.json` |

## Models Evaluated

| Model | Size | Tier | max_tokens |
|-------|------|------|------------|
| glm-4.7-flash:latest | ~9B | medium | 8192 |
| qwen3:14b | 14B | medium | 8192 |
| gpt-oss:20b | 20B | medium | 8192 |
| qwen3:30b | 30B | large | 16384 |

## Ground Truth (SHAP Rankings)

The actual top-3 feature importance per class (mean |SHAP|) from the Random Forest model:

| Class | Top-1 | Top-2 | Top-3 |
|-------|-------|-------|-------|
| **BotAttack** | Port | Status | Payload_Size |
| **Normal** | Port | Status | Payload_Size |
| **PortScan** | Payload_Size | Status | Port |

**Critical insight:** User_Agent has near-zero SHAP importance (< 0.006 for all classes) despite being the feature LLMs most commonly overvalue in their without-XAI analyses.

## Validation Metrics

### 1. Ranking Accuracy (Position Match)
- Compares LLM's ranked top-3 features against ground truth SHAP rankings
- Measures exact position matches (e.g., is Port correctly ranked #1 for BotAttack?)
- Score: correct positions / total positions (9 total across 3 classes × 3 positions)

### 2. Set Overlap (Order-Independent)
- Measures how many of the top-3 ground truth features appear in the LLM's top-3
- More lenient than position match - doesn't require correct ordering
- Score: intersection size / 3 per class

### 3. User_Agent Overvaluation
- Detects when LLM claims User_Agent is "highly important", "critical", "top-3", etc.
- **Why this matters:** Ground truth shows UA has SHAP < 0.006 - any claim of high importance is fabrication
- Patterns detected: "most important", "highly/critical/dominant/primary/key", "#1/#2/#3", "(highest/high) impact"

### 4. Fabricated Percentages (Phase 1 only)
- Detects invented percentage-based feature importance claims without SHAP backing
- Example fabrication: "User_Agent (72%)" - no statistical basis for this number
- Pattern: `feature_name (XX%)` where 5 < XX < 100

### 5. SHAP Citation Accuracy (Phase 2 only)
- Extracts numeric SHAP values cited by LLM
- Compares against ground truth:
  - **EXACT:** |error| < 0.005
  - **CLOSE:** |error| < 0.02
  - **OFF:** |error| >= 0.02
- Tracks: n_exact, n_close, n_off per response

## Validation Notebooks Created

### Per-Config Validation
1. **`validate_samples_10_local_10.ipynb`** - Validates config 1 (10 samples, 10 local)
2. **`validate_samples_20_local_15.ipynb`** - Validates config 2 (20 samples, 15 local)
3. **`validate_samples_40_local_25.ipynb`** - Validates config 3 (40 samples, 25 local)

Each notebook:
- Loads results and computes ground truth
- Validates all 4 models for both phases
- Displays ranking comparison tables
- Flags User_Agent overvaluation and fabricated percentages
- Shows SHAP citation accuracy for Phase 2
- Produces summary DataFrame

### Cross-Reference Analysis
**`cross_reference_analysis.ipynb`** - Compares all three configs to answer:

1. **Does more data improve ranking accuracy?**
   - Plots ranking accuracy vs config (10s→20s→40s)
   - Tests for monotonic improvement or diminishing returns

2. **Does XAI (Phase 2) consistently improve over Phase 1?**
   - Computes delta = Phase2_acc - Phase1_acc per model/config
   - Reports: improved/unchanged/worse counts, mean delta

3. **Which models benefit most from XAI injection?**
   - Per-model breakdown of XAI impact
   - Identifies models where XAI helps vs. hurts

4. **Is there a point where adding more data stops helping?**
   - Compares metrics across all three configs
   - Looks for plateau or degradation at highest config

## Key Questions for Human Validation

### Plausibility Checks

1. **Do Phase 2 responses show improved feature rankings?**
   - XAI should ground the LLM in actual SHAP values
   - Expected: Phase 2 ranking accuracy > Phase 1

2. **Does User_Agent overvaluation decrease in Phase 2?**
   - SHAP global explicitly shows UA ≈ 0 importance
   - Expected: UA hits lower in Phase 2

3. **Are SHAP citations accurate?**
   - LLM should cite values within 0.02 of ground truth
   - High "OFF" count suggests hallucination

4. **Do larger configs produce better results?**
   - Hypothesis: More data → better grounding → better accuracy
   - Alternative: Context overload → worse reasoning

### Known Issues to Watch

- **qwen3:30b** frequently fails on longer contexts (Phase 2 / Chat B)
  - Returns empty responses - likely OOM or context-length limit
  - Check if Phase 2 responses exist for this model

- **Truncation risk** for medium models at 8192 tokens
  - glm-4.7-flash may have truncated Phase 2 responses
  - Check if response length approaches max_tokens limit

## How to Run Validation

```bash
cd enforce_knowledge

# Run individual config validations
jupyter notebook validate_samples_10_local_10.ipynb
jupyter notebook validate_samples_20_local_15.ipynb
jupyter notebook validate_samples_40_local_25.ipynb

# Run cross-reference analysis
jupyter notebook cross_reference_analysis.ipynb
```

## Next Steps for Human Validation

1. **Run all validation notebooks** to compute automated metrics
2. **Review flagged issues** in each config:
   - User_Agent overvaluation hits
   - Fabricated percentages
   - SHAP citations marked "OFF"
3. **Check cross-reference trends**:
   - Does accuracy improve with config?
   - Does XAI consistently help?
   - Any model-specific patterns?
4. **Sample manual inspection**:
   - Pick 2-3 responses per config/phase
   - Read full text for coherence, fabrication, reasoning quality
5. **Decision point**: If automated metrics look plausible (ranking accuracy > baseline, XAI shows improvement, low fabrication rates), proceed to full human validation study

## Files Created

| File | Purpose |
|------|---------|
| `validate_samples_10_local_10.ipynb` | Per-config validation (10,10) |
| `validate_samples_20_local_15.ipynb` | Per-config validation (20,15) |
| `validate_samples_40_local_25.ipynb` | Per-config validation (40,25) |
| `cross_reference_analysis.ipynb` | Cross-config comparison |
| `VALIDATION_FINDINGS.md` | This summary document |
| `validation_helpers.py` | Shared validation functions (already existed) |

---

*Generated as part of SOC XAI master's research - LLM explainability validation pipeline*
