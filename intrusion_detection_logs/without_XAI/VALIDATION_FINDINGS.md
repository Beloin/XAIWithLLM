# without_XAI LLM Validation Findings

**Date:** 2026-03-25
**Experiment:** LLM analysis of Random Forest intrusion detection model WITHOUT XAI explanations
**Sample Sizes Tested:** N_SAMPLES = 10, 20, 40
**Models Tested:** glm-4.7-flash:latest, qwen3:14b, gpt-oss:20b, qwen3:30b

---

## Ground Truth Reference

Actual SHAP feature importance rankings (mean |SHAP|):

| Class | Top-3 Features |
|-------|----------------|
| BotAttack | Port > Status > Payload_Size |
| Normal | Port > Status > Payload_Size |
| PortScan | Payload_Size > Status > Port |

**Key insight:** User_Agent has near-zero SHAP importance (<0.006) for all classes, despite being commonly overvalued by LLMs in their analyses.

---

## Validation Metrics

Each LLM response was evaluated on:

1. **Feature Ranking Accuracy**: Does the model's top-3 include Port + Status (ground truth alignment)?
2. **User_Agent Bias**: Does the model overvalue User_Agent as an important feature?
3. **XAI Citation**: Does the model inappropriately cite SHAP/LIME (fabrication in without-XAI context)?
4. **Fabrication**: Does the model claim specific metrics/values not provided in the prompt?

---

## Results Summary

### N_SAMPLES = 10

| Model | Top-3 Features | Correct? | UA Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | (none extracted) | No | No |
| qwen3:14b | (none extracted) | No | No |
| gpt-oss:20b | Port | No | No |
| qwen3:30b | Port | No | No |

**Summary:** 0/4 correct, 0/4 UA-bias
**Avg response length:** 7,048 chars

---

### N_SAMPLES = 20

| Model | Top-3 Features | Correct? | UA Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | Port, User_Agent | No | Yes |
| qwen3:14b | Port, Status, Payload_Size | **Yes** | Yes |
| gpt-oss:20b | Port, User_Agent | No | Yes |
| qwen3:30b | Payload_Size | No | No |

**Summary:** 1/4 correct, 3/4 UA-bias
**Avg response length:** 8,413 chars

---

### N_SAMPLES = 40

| Model | Top-3 Features | Correct? | UA Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | Payload_Size | No | No |
| qwen3:14b | User_Agent | No | Yes |
| gpt-oss:20b | (none extracted) | No | No |
| qwen3:30b | Port, Status, User_Agent | **Yes** | Yes |

**Summary:** 1/4 correct, 2/4 UA-bias
**Avg response length:** 7,978 chars

---

## Trend Analysis

| Metric | N=10 | N=20 | N=40 | Trend |
|--------|------|------|------|-------|
| Accuracy (Port+Status in top-3) | 0% | 25% | 25% | Plateaus after N=20 |
| User_Agent Bias | 0% | 75% | 50% | Decreases slightly at N=40 |
| Avg Response Length | 7,048 | 8,413 | 7,978 | Peaks at N=20 |

---

## Key Findings

### 1. Low Feature Grounding Accuracy

Only 25% of models (1/4) correctly identify the ground truth top features at best. This suggests that **without XAI data, LLMs struggle to infer actual feature importance** from raw data alone.

- **N=10**: 0% accuracy - responses too vague to extract rankings
- **N=20**: 25% accuracy (qwen3:14b only)
- **N=40**: 25% accuracy (qwen3:30b only, different model)

### 2. User_Agent Bias is Prevalent

75% of models show User_Agent bias at N=20, dropping to 50% at N=40. This confirms the known tendency: **LLMs overvalue semantically meaningful features** (User_Agent strings like "nmap", "curl") even though SHAP shows they have near-zero importance.

### 3. Diminishing Returns at N=20+

Accuracy plateaus at 25% from N=20 to N=40. Response length also decreases at N=40. This suggests:
- **No benefit to increasing beyond 20 samples** in without-XAI context
- Possible **context overload** at N=40 (gpt-oss:20b and glm-4.7-flash produce less extractable content)

### 4. Model-Specific Patterns

| Model | Pattern |
|-------|---------|
| qwen3:14b | Best at N=20, degrades at N=40 (UA-only ranking) |
| qwen3:30b | Improves with more data (N=40 is best) |
| glm-4.7-flash | Inconsistent, no clear trend |
| gpt-oss:20b | Shows UA bias, feature extraction fails at N=40 |

---

## Recommendations for Human Validation

### Priority Responses for Review

1. **N=20, qwen3:14b** - Only response with correct Port>Status>Payload_Size ranking
   - File: `resultados_without_xai_samples_20.json`
   - Use as baseline for "what good looks like"

2. **N=40, qwen3:30b** - Correct top-3 but with UA bias
   - Shows partial grounding - useful for understanding failure modes

3. **N=20, glm-4.7-flash + gpt-oss:20b** - Both show UA bias
   - Compare to understand how semantic features override statistical patterns

### Validation Questions for Human Review

1. Does qwen3:14b's N=20 response actually cite data evidence for its rankings, or is it correct by coincidence?
2. When models mention User_Agent as important, do they provide concrete examples from the data?
3. Are there any SHAP/LIME citations (would indicate fabrication in without-XAI context)?
4. Do models acknowledge uncertainty about feature importance, or do they assert confidently?

---

## Next Steps

### 1. Run with_XAI Validation

Compare these results against `with_XAI/` experiment outputs. Hypothesis: **XAI injection should improve**:
- Feature ranking accuracy (25% → 50%+)
- User_Agent bias reduction (75% → 25% or lower)
- Citation quality (models should reference actual SHAP values)

### 2. Enforce Knowledge Analysis

Review `enforce_knowledge/` paired results (Phase 1 without-XAI → Phase 2 with-XAI in same chat). Key question: **Does injecting SHAP+LIME mid-conversation change the model's analysis?**

### 3. Threshold Determination

Based on these results, **N_SAMPLES=20** appears optimal for without-XAI baseline. Consider:
- Keeping N=20 for fair comparison with with_XAI (N_LOCAL=25 is closest)
- Or using N=10 if context length is a constraint (qwen3:30b failures at longer contexts noted in CLAUDE.md)

---

## Validation Notebooks Created

| Notebook | Purpose |
|----------|---------|
| `validate_samples_10.ipynb` | Individual validation for N=10 |
| `validate_samples_20.ipynb` | Individual validation for N=20 |
| `validate_samples_40.ipynb` | Individual validation for N=40 |
| `cross_reference_analysis.ipynb` | Cross-sample comparison and trend analysis |

Run any notebook with: `ipython validate_samples_X.ipynb`

---

## Conclusion

The without-XAI baseline shows **limited feature grounding** (25% accuracy at best) and **significant User_Agent bias** (up to 75%). This establishes a clear baseline: if XAI injection improves these metrics, it would support the thesis that explainability data meaningfully enhances LLM reasoning about ML models.

**Critical finding:** More data (N=40) does not improve accuracy over N=20. This suggests the limitation is not sample size but **lack of explicit importance signals** - which is exactly what SHAP+LIME should provide.
