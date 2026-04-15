# Best Explanations by Model — Prompt Engineering Evaluation

## Ground Truth Reference

| Rank | Feature | SHAP Value | Percentage |
|------|---------|------------|------------|
| 1 | `failed_logins` | 0.179261 | 37.36% |
| 2 | `login_attempts` | 0.124679 | 25.99% |
| 3 | `ip_reputation_score` | 0.091998 | 19.17% |
| 4 | `browser_type` | 0.029066 | 6.06% |
| 5 | `session_duration` | 0.020506 | 4.27% |
| 6 | `network_packet_size` | 0.014587 | 3.04% |
| 7 | `encryption_used` | 0.009895 | 2.06% |
| 8 | `protocol_type` | 0.006132 | 1.28% |
| 9 | `unusual_time_access` | 0.003683 | 0.77% |

---

# glm-4.7-flash

## Overall

Model shows variable response quality. Works best with structured prompts (few_shot, cot). Truncation issues in some experiments.

## Prompts x Explanation

| Place | Prompt Technique | Pros | Cons | Accuracy |
|-------|-------------------|------|------|----------|
| 1 | **few_shot** | Followed format exactly; cited SHAP values; structured Top 3 | Shorter responses than larger models | HIGH |
| 2 | **cot** | Step-by-step reasoning; identified top features | Less structured than few_shot | MEDIUM-HIGH |
| 3 | **system_prompt** | SOC persona adopted; operational insights | Truncated/short responses | MEDIUM |
| 4 | **context_prompt** | Domain context applied | Generic analysis | MEDIUM |
| 5 | **role_based** | Expert role framing | Similar to system_prompt | MEDIUM |
| 6 | **with_xai_local** | Basic feature analysis | Less detailed | LOW-MEDIUM |

## Why few_shot was the best

The few_shot prompt provided an explicit template that glm-4.7-flash followed precisely: "Top 3 Features Detected" with SHAP values, detection rules, and confidence levels. This structured format prevented rambling and ensured all critical elements were addressed. The model correctly identified `failed_logins` (0.179), `login_attempts` (0.125), and `ip_reputation_score` (0.092) as top features with accurate SHAP citations.

---

# qwen3:14b

## Overall

Consistent performer across all prompt types. Provides complete responses with reasonable accuracy.

## Prompts x Explanation

| Place | Prompt Technique | Pros | Cons | Accuracy |
|-------|-------------------|------|------|----------|
| 1 | **cot** | Structured 5-step analysis; global/local SHAP; LIME cross-reference | Longer responses may miss actionable details | HIGH |
| 2 | **few_shot** | Format-compliant; Top 3 with SHAP values | Less depth than cot | HIGH |
| 3 | **system_prompt** | SOC analyst persona; operational focus | Some generic statements | MEDIUM-HIGH |
| 4 | **context_prompt** | Good feature ranking | Less structured output | MEDIUM |
| 5 | **role_based** | Expert framing applied | Similar to system_prompt | MEDIUM |
| 6 | **with_xai_local** | Class pattern analysis | Basic structure | MEDIUM |

## Why cot was the best

Chain-of-thought prompting produced the most comprehensive analysis, following a systematic 5-step process: (1) SHAP Global ranking, (2) SHAP Local analysis, (3) LIME cross-reference, (4) Synthesis, (5) Recommendations. The model correctly computed total SHAP contributions for top features, aggregated local explanations, and identified class-specific patterns with detection rules.

---

# gpt-oss:20b

## Overall

Strong performer with detailed, well-structured responses. Best overall consistency and SHAP citation accuracy.

## Prompts x Explanation

| Place | Prompt Technique | Pros | Cons | Accuracy |
|-------|-------------------|------|------|----------|
| 1 | **cot** | Comprehensive 5-step analysis; precise SHAP citations; class patterns | Response length (may truncate) | VERY HIGH |
| 2 | **few_shot** | Format-compliant; table-based feature ranking | Less narrative depth | HIGH |
| 3 | **system_prompt** | SOC persona; feature importance table | Slightly less structured | HIGH |
| 4 | **context_prompt** | Good global SHAP analysis | Table format less readable | MEDIUM-HIGH |
| 5 | **role_based** | Expert role applied | Similar outputs to system_prompt | MEDIUM-HIGH |
| 6 | **with_xai_local** | Feature importance table | Less detail on local patterns | MEDIUM |

## Why cot was the best

Produced the most complete analysis with precise SHAP value citations (~0.179 for failed_logins, ~0.125 for login_attempts, ~0.092 for ip_reputation_score). The response included class-specific patterns, LIME rule integration, and actionable detection rules with thresholds. Most reliable across all experiments.

---

# qwen3:30b

## Overall

**CRITICAL FAILURE** — Empty responses across ALL prompt techniques tested. Model ran but produced no output. Cannot be evaluated for explanation quality.

## Prompts x Explanation

| Place | Prompt Technique | Pros | Cons | Accuracy |
|-------|-------------------|------|------|----------|
| - | **system_prompt** | - | Empty response (7303 prompt tokens, 0 output) | N/A |
| - | **context_prompt** | - | Empty response | N/A |
| - | **role_based** | - | Empty response | N/A |
| - | **few_shot** | - | Empty response | N/A |
| - | **cot** | - | Empty response | N/A |
| - | **with_xai_local** | - | Empty response | N/A |

## Why all prompts failed

qwen3:30b consistently returned empty `response` fields despite showing active `thinking_process` (7000+ tokens of reasoning) and high `completion_tokens` counts. This suggests model configuration issues or context length problems. **Not recommended for XAI explanation tasks.**

---

# glm-5:cloud

## Overall

Excellent performer when it works. Empty responses in some experiments (system_prompt, context_prompt) but strong outputs in few_shot and cot.

## Prompts x Explanation

| Place | Prompt Technique | Pros | Cons | Accuracy |
|-------|-------------------|------|------|----------|
| 1 | **cot** | Complete 5-step analysis; precise SHAP values; local patterns | Longer inference time (6m5s) | VERY HIGH |
| 2 | **few_shot** | Format-compliant; SHAP citations accurate (0.179, 0.125, 0.092) | Shorter than cot | HIGH |
| 3 | **with_xai_local** | Good class-specific analysis | Less structured format | MEDIUM-HIGH |
| 4 | **system_prompt** | - | **EMPTY RESPONSE** | N/A |
| 5 | **context_prompt** | - | **EMPTY RESPONSE** | N/A |
| 6 | **role_based** | - | **EMPTY RESPONSE** | N/A |

## Why cot was the best

Chain-of-thought produced a comprehensive, well-organized response following all 5 prescribed steps. The model correctly ranked features: `failed_logins` (0.179), `login_attempts` (0.125), `ip_reputation_score` (0.092). Included detection rules: "IF failed_logins > 2 THEN flag", "IF login_attempts > 5 THEN flag", "IF ip_reputation_score > 0.46 THEN investigate". Cited specific instance-level SHAP values (Instance #3282: +0.64 for Attack class).

---

# Summary Rankings

| Model | Best Technique | Worst Technique | Reliability |
|-------|----------------|-----------------|-------------|
| glm-4.7-flash | few_shot | with_xai_local | Variable (truncation risk) |
| qwen3:14b | cot | with_xai_local | High (consistent) |
| gpt-oss:20b | cot | with_xai_local | Very High (most reliable) |
| qwen3:30b | **NONE** | ALL | **Critical Failure** |
| glm-5:cloud | cot | system_prompt/context_prompt/role_based | Variable (empty responses) |

---

# Key Findings

1. **Chain-of-thought (cot)** consistently produces the best explanations across models that respond
2. **Few-shot** is a close second, especially for smaller models (glm-4.7-flash)
3. **qwen3:30b should be avoided** for XAI tasks — 100% empty response rate
4. **gpt-oss:20b** is the most reliable model for explanation tasks
5. **glm-5:cloud** produces excellent output when it responds but has stability issues with persona-based prompts
6. All successful models correctly identified the top 3 features (`failed_logins`, `login_attempts`, `ip_reputation_score`)

---

# Recommendations

| Model | Recommended Prompt | Alternative |
|-------|-------------------|-------------|
| glm-4.7-flash | few_shot | cot |
| qwen3:14b | cot | few_shot |
| gpt-oss:20b | cot | few_shot |
| qwen3:30b | **AVOID** | - |
| glm-5:cloud | cot | few_shot |