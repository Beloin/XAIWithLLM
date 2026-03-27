# With XAI Experiment - Validation Summary

**Date:** 2026-03-25
**Experiment:** LLM analysis of network intrusion detection model with SHAP+LIME XAI evidence
**Variable:** N_LOCAL (number of local XAI instances provided to LLM)

---

## Executive Summary

This validation assessed LLM responses across 4 N_LOCAL configurations (5, 10, 15, 25 instances) for 4 models. The key finding: **model reliability varies significantly by N_LOCAL**, with some models failing at lower contexts but succeeding at higher ones.

### Recommended Configuration: N_LOCAL=15 or 25

Both configurations achieve 100% model success rate with good response quality. N_LOCAL=15 is preferred for efficiency.

---

## Response Status Matrix

| N_LOCAL | glm-4.7-flash | qwen3:14b | gpt-oss:20b | qwen3:30b | Success Rate |
|---------|---------------|-----------|-------------|-----------|--------------|
| 5 | 7767 chars | 6966 chars | 10759 chars | **EMPTY** | 75% (3/4) |
| 10 | 3076 chars | 5687 chars | 12088 chars | **EMPTY** | 50% (2/4) |
| 15 | 7282 chars | 6816 chars | 10876 chars | 7730 chars | 100% (4/4) |
| 25 | 7171 chars | 7217 chars | 10701 chars | 8350 chars | 100% (4/4) |

---

## Critical Model Behaviors

### qwen3:30b - Counterintuitive Failure Pattern

- **Fails** at N_LOCAL=5 and N_LOCAL=10 (empty responses)
- **Succeeds** at N_LOCAL=15 (7730 chars) and N_LOCAL=25 (8350 chars)

This is unexpected - typically larger contexts cause failures, not smaller ones. Possible causes:
- Ollama's 30B model has a minimum context threshold behavior
- VRAM availability variance between experiment runs
- Non-deterministic generation / early stopping bugs

**Implication:** Do NOT use N_LOCAL < 15 if you need qwen3:30b comparisons.

### glm-4.7-flash - Truncation at N_LOCAL=10

- N_LOCAL=5: 7767 chars (normal)
- N_LOCAL=10: 3076 chars (**~60% shorter**)
- N_LOCAL=15: 7282 chars (normal)
- N_LOCAL=25: 7171 chars (normal)

N_LOCAL=10 appears to trigger early stopping or truncation. This outlier suggests:
- A specific context length boundary issue
- Possible token limit interaction with multi-turn chat structure

**Implication:** N_LOCAL=10 is unreliable for glm-4.7-flash analysis.

### gpt-oss:20b - Most Reliable Model

- Consistently produces **longest responses** (10k-12k chars)
- **No failures** across all N_LOCAL values
- Stable output quality

**Implication:** gpt-oss:20b is the best candidate for detailed human validation.

### qwen3:14b - Stable but Shorter

- Consistent response length (5.7k-7.2k chars)
- No failures
- Slight increase with higher N_LOCAL

**Implication:** Reliable but less detailed than gpt-oss:20b.

---

## Content Analysis

### Feature Coverage (All Valid Responses)

| Feature | N_LOCAL=5 | N_LOCAL=10 | N_LOCAL=15 | N_LOCAL=25 |
|---------|-----------|-----------|------------|------------|
| Port mentioned | 3/3 (100%) | 2/2 (100%) | 4/4 (100%) | 4/4 (100%) |
| Payload_Size mentioned | 3/3 (100%) | 2/2 (100%) | 4/4 (100%) | 4/4 (100%) |
| Status mentioned | 3/3 (100%) | 2/2 (100%) | 4/4 (100%) | 4/4 (100%) |
| SHAP cited | 3/3 (100%) | 2/2 (100%) | 4/4 (100%) | 4/4 (100%) |
| LIME cited | 3/3 (100%) | 2/2 (100%) | 4/4 (100%) | 4/4 (100%) |

**Conclusion:** All valid responses properly engage with the XAI evidence regardless of N_LOCAL. No degradation in feature coverage.

### Qualitative Content Samples

**gpt-oss:20b opening patterns:**
- N_LOCAL=5: "Random Forest, 3-class Intrusion Detector - BotAttack / Normal / PortScan"
- N_LOCAL=10: "Task: 3-class network intrusion detection: BotAttack, Normal, PortScan"
- N_LOCAL=15: "Model: Random Forest (3-class: BotAttack, Normal, PortScan) - 99.7% overall accuracy"
- N_LOCAL=25: "Model: Random Forest, 3-class intrusion detector (BotAttack, Normal, PortScan) - 99.7% overall accuracy"

All configurations correctly acknowledge model context and accuracy.

---

## Saturation Analysis

**Question:** Does increasing N_LOCAL beyond a certain point stop adding value?

**Findings:**
- No clear saturation point detected in response quality
- All valid responses mention key features (Port, Payload_Size, Status)
- SHAP and LIME are consistently cited across all configurations
- Response length remains stable (no monotonic increase with N_LOCAL)

**Interpretation:** The XAI evidence is sufficient even at N_LOCAL=5 for models that produce valid responses. More instances don't necessarily produce richer analysis - the bottleneck is model reliability, not data sufficiency.

---

## Recommendations

### For Human Validation

1. **Primary: N_LOCAL=15**
   - All 4 models work
   - Good response lengths
   - Efficient context size

2. **Alternative: N_LOCAL=25**
   - All 4 models work
   - Slightly longer responses for some models
   - Heavier context load (may matter for manual review)

3. **Avoid: N_LOCAL=5**
   - qwen3:30b fails
   - Cannot compare all models

4. **Avoid: N_LOCAL=10**
   - qwen3:30b fails
   - glm-4.7-flash truncates
   - Only 2/4 models reliable

### Model Priorities for Human Review

1. **gpt-oss:20b** - Most reliable, longest responses, best for detailed analysis
2. **qwen3:14b** - Reliable, moderate length
3. **glm-4.7-flash** - Use only N_LOCAL=15 or 25 data
4. **qwen3:30b** - Use only N_LOCAL=15 or 25 data

---

## Created Validation Notebooks

| File | Purpose |
|------|---------|
| `validate_llm_responses_local_5.ipynb` | Validates N_LOCAL=5 responses against ground truth SHAP |
| `validate_llm_responses_local_10.ipynb` | Validates N_LOCAL=10 responses against ground truth SHAP |
| `validate_llm_responses_local_15.ipynb` | Validates N_LOCAL=15 responses against ground truth SHAP |
| `validate_llm_responses_local_25.ipynb` | Validates N_LOCAL=25 responses against ground truth SHAP |
| `cross_reference_all_n_local.ipynb` | Cross-config comparison and trend analysis |

### Validation Checklist (Per Notebook)

- [ ] Compute ground truth SHAP values (automated)
- [ ] Load and display LLM responses
- [ ] Manually extract feature rankings from actual responses
- [ ] Update `chatb_rankings` dictionary with extracted data
- [ ] Update `cited_shap` dictionary with cited values
- [ ] Run feature ranking accuracy computation
- [ ] Run SHAP citation accuracy computation
- [ ] Check SHAP-LIME coherence
- [ ] Check for fabrications (misclassifications, fake stats)

---

## Ground Truth Reference (For Validation)

**Model Accuracy:** 99.7%

**Actual SHAP Top-3 Rankings:**
- **BotAttack:** Port > Status > Payload_Size
- **Normal:** Port > Payload_Size > Status (or Status > Payload_Size depending on exact values)
- **PortScan:** Payload_Size > Status > Port (or Payload_Size > Port > Status)

**Key Insight:** User_Agent has near-zero SHAP importance (< 0.006 for all classes) despite being the feature LLMs most commonly overvalue in their without-XAI analyses.

---

## Next Steps

1. **Run validation notebooks** for N_LOCAL=15 and N_LOCAL=25
2. **Manually extract** actual feature rankings from full response text
3. **Verify SHAP value citation accuracy** against ground truth
4. **Check for fabrications** (invented misclassifications, fake percentages)
5. **Compare SHAP-LIME coherence** - do models properly note agreements/disagreements?
6. **Begin human validation** focusing on:
   - gpt-oss:20b at N_LOCAL=15 and N_LOCAL=25
   - qwen3:14b at N_LOCAL=15 and N_LOCAL=25
   - Skip N_LOCAL=5 and N_LOCAL=10 for cross-model comparisons

---

## Files Structure

```
with_XAI/
  resultados_with_xai_local_5.json    # Raw LLM responses
  resultados_with_xai_local_10.json   # Raw LLM responses
  resultados_with_xai_local_15.json   # Raw LLM responses
  resultados_with_xai_local_25.json   # Raw LLM responses
  with_xai.ipynb                      # Original experiment notebook
  validate_llm_responses_local_5.ipynb    # Validation notebook
  validate_llm_responses_local_10.ipynb   # Validation notebook
  validate_llm_responses_local_15.ipynb   # Validation notebook
  validate_llm_responses_local_25.ipynb   # Validation notebook
  cross_reference_all_n_local.ipynb       # Cross-config analysis
  VALIDATION_SUMMARY.md                   # This file
```
