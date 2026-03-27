# Without-XAI LLM Validation Findings

## Overview

This document summarizes the automated validation of LLM responses from the `without_XAI` experiment, where LLMs analyzed a Random Forest network intrusion detection model using only raw data (no SHAP/LIME explanations).

**Data**: 4 LLM models × 3 sample sizes (10, 20, 40 training/prediction samples) = 12 total responses

**Ground Truth** (from actual SHAP analysis):
- **BotAttack**: Port > Status > Payload_Size
- **Normal**: Port > Status > Payload_Size
- **PortScan**: Payload_Size > Status > Port

**Key insight**: User_Agent has near-zero SHAP importance (<0.006) but is commonly overvalued by LLMs.

---

## Validation Metrics

| Metric | Description |
|--------|-------------|
| **Accuracy** | % of models with Port + Status in top-3 features |
| **UA-Bias** | % of models overvaluing User_Agent (known bias indicator) |
| **Fabrication** | % claiming specific metrics/SHAP values not in prompt |
| **XAI Citation** | % inappropriately citing SHAP/LIME (should be 0 in without-XAI) |

---

## Results by Sample Size

### N_SAMPLES = 10

| Model | Top-3 Features | Correct? | UA-Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | (none extracted) | No | No |
| qwen3:14b | (none extracted) | No | No |
| gpt-oss:20b | Port | No | No |
| qwen3:30b | Port | No | No |

**Summary**: 0/4 correct (0%), 0/4 UA-bias (0%), Avg length: 7,048 chars

---

### N_SAMPLES = 20

| Model | Top-3 Features | Correct? | UA-Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | Port, User_Agent | No | Yes |
| qwen3:14b | Port, Status, Payload_Size | **Yes** | Yes |
| gpt-oss:20b | Port, User_Agent | No | Yes |
| qwen3:30b | Payload_Size | No | No |

**Summary**: 1/4 correct (25%), 3/4 UA-bias (75%), Avg length: 8,413 chars

---

### N_SAMPLES = 40

| Model | Top-3 Features | Correct? | UA-Bias? |
|-------|----------------|----------|----------|
| glm-4.7-flash:latest | Payload_Size | No | No |
| qwen3:14b | User_Agent | No | Yes |
| gpt-oss:20b | (none extracted) | No | No |
| qwen3:30b | Port, Status, User_Agent | **Yes** | Yes |

**Summary**: 1/4 correct (25%), 2/4 UA-bias (50%), Avg length: 7,978 chars

---

## Trend Analysis

| Sample Size | Accuracy | UA-Bias | Avg Length |
|-------------|----------|---------|------------|
| N=10 | 0% | 0% | 7,048 |
| N=20 | 25% | 75% | 8,413 |
| N=40 | 25% | 50% | 7,978 |

### Key Trends

1. **Accuracy plateau**: Jumps from 0% at N=10 to 25% at N=20, then flat at N=40
2. **UA-bias non-monotonic**: Peaks at N=20 (75%), drops at N=40 (50%)
3. **Response length**: Increases N=10→20, then decreases N=20→40

---

## Findings

### 1. Low Overall Accuracy

Only 2/12 responses (16.7%) correctly identify Port + Status as top features. This suggests LLMs struggle to ground feature importance from raw data alone—**motivating the XAI intervention hypothesis**.

### 2. User_Agent Bias Persists

50-75% of models show User_Agent overvaluation, confirming the known bias. Even with more data, this bias persists (though slightly decreases at N=40).

### 3. Diminishing Returns Beyond N=20

Accuracy doesn't improve from N=20 to N=40. This suggests:
- **20 samples may be sufficient** for basic pattern recognition
- **40 samples don't add value**—possibly context overload or LLM attention dilution

### 4. Feature Extraction Challenges

At N=10, many responses don't contain explicit feature rankings (empty top-3). This indicates responses are more abstract/vague with less data, making automated validation harder.

### 5. Model-Specific Patterns

- **qwen3:14b**: Best performer—only model correct at N=20
- **qwen3:30b**: Correct at N=40 but misses at N=20 (inconsistent)
- **glm-4.7-flash, gpt-oss:20b**: Never achieve correct top-3

---

## Recommendations for Human Validation

### Priority Ranking (Highest Quality First)

1. **N=20, qwen3:14b** - Only correct top-3, but has UA-bias
2. **N=40, qwen3:30b** - Correct top-3, but has UA-bias
3. **N=40, glm-4.7-flash** - No UA-bias, but incorrect ranking

### Validation Workflow

1. Start with **N=20, qwen3:14b** to understand what a "correct" response looks like
2. Compare against **N=40, qwen3:30b** to assess consistency
3. Review incorrect responses to identify common failure patterns

### Next Steps

1. **Run with_XAI validation** - Compare if SHAP/LIME injection improves:
   - Feature ranking accuracy (target: >50%)
   - UA-bias reduction (target: <25%)
   - Response grounding (fewer vague claims)

2. **Manual review criteria**:
   - Does the LLM correctly rank Port > Status > Payload_Size?
   - Does it recognize User_Agent as low importance?
   - Are cybersecurity insights actionable for SOC analysts?
   - Any fabrications or hallucinated metrics?

---

## Conclusion

The without-XAI baseline shows **poor feature grounding** (16.7% accuracy) and **persistent UA-bias** (50-75%). This establishes a clear baseline for measuring XAI impact.

**Hypothesis**: Injecting SHAP + LIME data should:
- Increase accuracy from 25% to >50%
- Reduce UA-bias from 75% to <25%
- Improve response specificity and reduce vague claims

The validation notebooks are ready for human review to confirm these automated findings and assess response quality beyond feature ranking.

---

## Files Created

| File | Purpose |
|------|---------|
| `validate_samples_10.ipynb` | Individual validation for N=10 |
| `validate_samples_20.ipynb` | Individual validation for N=20 |
| `validate_samples_40.ipynb` | Individual validation for N=40 |
| `cross_reference_analysis.ipynb` | Cross-sample trend analysis |
| `validation_findings.md` | This summary document |
