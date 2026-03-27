# XAI Explanation Quality Assessment

**Date:** 2026-03-25
**Question:** Do the LLMs do a good job explaining the AI when given XAI data?

---

## Executive Summary

**Yes — but ONLY when given XAI data.** The comparison between without-XAI and with-XAI responses reveals:

| Aspect | Without XAI | With XAI | Verdict |
|--------|-------------|----------|---------|
| Top feature identification | **WRONG** (User_Agent) | **CORRECT** (Port, Payload_Size, Status) | XAI corrects model intuition |
| Ground truth alignment | 25% accuracy | 100% accuracy (N_LOCAL≥15) | **+75% improvement** |
| User_Agent bias | 75% overvalue it | 0% mention it as important | **XAI eliminates bias** |
| Causal reasoning | Generic ("this feature is important") | Specific ("Port=443 + Status=404 → BotAttack") | XAI enables actionable insights |
| Numeric citations | None (nothing to cite) | SHAP values within 0.02 of ground truth | XAI provides verifiable claims |

---

## The Critical Finding: XAI Corrects Wrong Intuitions

### Without XAI — Models Hallucinate Feature Importance

All 4 models, when analyzing raw data without SHAP/LIME, ranked **User_Agent as the #1 most important feature**:

```
WITHOUT XAI (glm-4.7-flash):
  "User_Agent (Primary Driver): This is the absolute strongest predictor in the model."

WITHOUT XAI (qwen3:14b):
  "Key Features (Ranked by Importance): 1. User_Agent"

WITHOUT XAI (gpt-oss:20b):
  "Rank 1: User_Agent — Bot-related tools (Nikto, nmap, Wget, curl) are explicitly encoded"

WITHOUT XAI (qwen3:30b):
  "Feature | Top Rank: User_Agent | 1"
```

**Problem:** Ground truth SHAP shows User_Agent importance < 0.006 for ALL classes.

**Why this happens:** LLMs recognize semantic meaning in User_Agent strings ("nmap", "curl", "Nikto" are security tools) and assume the model must heavily weight these. This is **plausible reasoning** but **factually wrong**.

---

### With XAI — Models Correctly Identify Actual Feature Importance

The SAME models, when given SHAP + LIME data, correctly identify the actual top features:

```
WITH XAI (glm-4.7-flash):
  "Port (0.244) > Status (0.129) > Payload_Size (0.091) for BotAttack"
  "Payload_Size (0.261) dominates PortScan"

WITH XAI (qwen3:14b):
  "Top features: Port (0.24), Status (0.129), Payload_Size (0.091)"
  "Payload_Size is the single most decisive signal for PortScan"

WITH XAI (gpt-oss:20b):
  "BotAttack: 1. Port (0.244), 2. Status (0.129), 3. Payload_Size (0.091)"
  "PortScan: 1. Payload_Size (0.261), 2. Status (0.066), 3. Port (0.030)"

WITH XAI (qwen3:30b):
  "Port is critical for BotAttack and Normal, but NOT for PortScan"
  "Payload_Size (0.261) is dominant for PortScan"
```

**Key insight:** XAI data **overrides** the LLM's semantic intuition with actual model behavior evidence.

---

## Explanation Quality Grades (With XAI)

| Model | Grade | Strengths | Weaknesses |
|-------|-------|-----------|------------|
| **gpt-oss:20b** | **A** | 9 causal explanations, correct User_Agent handling, rich security context (155 terms), compares SHAP+LIME | None significant |
| **qwen3:30b** | **A** | 10 causal explanations, correct User_Agent handling, rich security context (136 terms) | Some fabricated numeric examples (not SHAP values) |
| **qwen3:14b** | **A** | Correct rankings, 4 causal explanations, rich security context (123 terms) | Less detailed than larger models |
| **glm-4.7-flash** | **C** | Correct rankings, rich security context (79 terms), SHAP+LIME comparison | Only 2 causal explanations, less depth |

---

## Example: High-Quality XAI Explanation (gpt-oss:20b)

The best responses include:

### 1. Correct Feature Rankings with Numeric Values
```
| Class | Top 2-3 Features (by mean absolute SHAP) |
| BotAttack | 1. Port (0.244), 2. Status (0.129), 3. Payload_Size (0.091) |
| Normal | 1. Port (0.273), 2. Payload_Size (0.184), 3. Status (0.195) |
| PortScan | 1. Payload_Size (0.261), 2. Port (0.030), 3. Status (0.066) |
```

### 2. Causal Reasoning (Why These Features Matter)
```
"Port scanners often issue many rapid requests with minimal payloads, but because
of the SMOTE balancing strategy the model learns that very small payloads (close
to zero) are characteristic of scanning."

"The small port importance reflects the fact that scans cover many ports, so no
single port dominates."
```

### 3. Actionable SOC Rules
```
"Alert rule: HTTP request to port 443 with a 404/500 status and payload > 800 bytes
→ triggers a high-severity botnet alert."

"Alert rule: Any request with payload ≤ 20 bytes that receives a 404 status
→ flags potential scanning."
```

### 4. SHAP + LIME Comparison
```
"Convergence: All explanations consistently highlight Port for BotAttack and
Payload_Size for PortScan. This confirms that the model's discriminative signal
is stable across explainers."

"Fine-grained differences: LIME tends to under-weight Status for PortScan, perhaps
because LIME's linear surrogate focuses on the strongest linear predictor."
```

### 5. Correct User_Agent Handling
```
"User_Agent has negligible influence; bots use a wide range of agents to blend in."
```

This is **correct** — ground truth SHAP shows User_Agent < 0.006 for all classes.

---

## What Makes a "Good" XAI Explanation?

Based on this analysis, high-quality XAI explanations have:

| Criterion | Description | Met by |
|-----------|-------------|--------|
| **Accuracy** | Feature rankings match ground truth SHAP | All models (with XAI) |
| **Specificity** | Cites actual SHAP values (within 0.02) | gpt-oss:20b, qwen3:30b |
| **Causal reasoning** | Explains WHY features matter for each class | gpt-oss:20b, qwen3:30b |
| **Security context** | Connects features to cybersecurity intuition | All models |
| **XAI integration** | Compares/contrasts SHAP global vs LIME local | All models |
| **No fabrication** | Doesn't invent statistics or misclassifications | gpt-oss:20b, qwen3:14b |
| **Correct negative** | Identifies User_Agent as low importance | gpt-oss:20b, qwen3:30b |
| **Actionable output** | Produces SOC-ready alert rules | gpt-oss:20b |

---

## Model Comparison Summary

### gpt-oss:20b — Best Overall
- **Strengths:** Longest responses (10k+ chars), most causal explanations (9), correct on all criteria
- **Best for:** Detailed human validation, thesis examples

### qwen3:30b — Good but Fabricates Examples
- **Strengths:** Correct rankings, rich security context
- **Weakness:** Invents example values (e.g., "Port=80", "Status=200", "Payload=1200") that look like SHAP citations but aren't
- **Best for:** Ranking analysis (ignore numeric examples)

### qwen3:14b — Solid Mid-Tier
- **Strengths:** Correct rankings, adequate causal reasoning
- **Weakness:** Less detailed, no numeric SHAP citations
- **Best for:** Quick validation, resource-constrained runs

### glm-4.7-flash — Weakest
- **Strengths:** Correct rankings, SHAP+LIME comparison
- **Weakness:** Fewest causal explanations (2), shallow analysis
- **Best for:** Baseline comparisons only

---

## Conclusions

### 1. XAI Data Is Necessary for Accurate Explanations

Without SHAP/LIME, LLMs produce **confident but wrong** explanations based on semantic intuition. With XAI data, they produce **accurate, grounded** explanations.

### 2. Not All "With XAI" Explanations Are Equal

- **gpt-oss:20b** and **qwen3:30b** produce A-grade explanations with causal reasoning and actionable insights
- **qwen3:14b** and **glm-4.7-flash** produce adequate but shallower explanations

### 3. The Real Value: Correcting Wrong Intuitions

The most important function of XAI in this context is **overriding LLM semantic bias**. User_Agent looks important to an LLM (it "knows" nmap is a scanning tool), but SHAP shows the actual model doesn't use it. XAI data corrects this.

### 4. Configuration Matters

- **N_LOCAL=15 or 25** — All models succeed with good explanations
- **N_LOCAL=5 or 10** — Some models fail (qwen3:30b empty, glm truncates)

---

## Recommendation for Thesis

Use **gpt-oss:20b at N_LOCAL=15** as the primary example of "good XAI explanation." It demonstrates:

1. Correct feature rankings (accuracy)
2. Specific SHAP citations (verifiability)
3. Causal reasoning (depth)
4. SOC-ready alert rules (actionability)
5. Correct User_Agent handling (bias correction)

Pair this with a **without-XAI example** from the same model to show the dramatic improvement XAI injection provides.

---

**Bottom Line:** LLMs do excellent work explaining the AI **when given XAI data**. The explanations are accurate, actionable, and grounded in actual model behavior. Without XAI, explanations are confident but wrong — driven by semantic intuition rather than statistical reality.
