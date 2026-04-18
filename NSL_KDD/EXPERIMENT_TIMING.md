# Experiment Timing - NSL_KDD

## Summary

| Category | Total Time |
|----------|------------|
| with_xai (5 experiments) | 3h 45m |
| without_xai (5 experiments) | 2h 06m |
| self_consistency (1 run) | 1h 22m |
| **Total** | **7h 13m** |

---

## with_xai Experiments

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| system_prompt | 2026-04-14 16:39:10 | 2026-04-14 17:32:28 | 53m 18s |
| context_prompt | 2026-04-14 17:32:28 | 2026-04-14 18:15:40 | 43m 12s |
| role_based | 2026-04-15 03:29:58 | 2026-04-15 04:17:13 | 47m 15s |
| few_shot | 2026-04-15 04:17:13 | 2026-04-15 04:53:22 | 36m 09s |
| cot | 2026-04-15 04:53:22 | 2026-04-15 05:34:27 | 41m 05s |

**with_xai Subtotal: 3h 45m**

**Note:** role_based was interrupted on Apr 14 at 18:15:40 and resumed on Apr 15 at 03:29:58.

---

## without_xai Experiments

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| system_prompt | 2026-04-15 05:34:27 | 2026-04-15 05:59:14 | 24m 47s |
| context_prompt | 2026-04-15 05:59:14 | 2026-04-15 06:30:53 | 31m 39s |
| role_based | 2026-04-15 06:30:53 | 2026-04-15 06:55:27 | 24m 34s |
| few_shot | 2026-04-15 06:55:27 | 2026-04-15 07:31:24 | 35m 57s |
| cot | 2026-04-15 07:31:24 | 2026-04-15 08:04:15 | 32m 51s |

**without_xai Subtotal: 2h 30m**

---

## self_consistency Experiments

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| self_consistency | 2026-04-15 08:04:15 | 2026-04-15 09:26:50 | 1h 22m 35s |

**self_consistency Subtotal: 1h 22m**

---

## Per-Model Timing (Approximate)

| Condition | Avg per Experiment | Avg per Model |
|-----------|---------------------|---------------|
| with_xai | ~44m | ~8.8m |
| without_xai | ~30m | ~6.0m |
| self_consistency | ~82m | ~16.4m (5 runs) |

---

## Models Tested

1. glm-4.7-flash
2. qwen3:14b
3. gpt-oss:20b
4. qwen3:30b
5. glm-5:cloud

---

## Files Generated

### with_xai
- `resultados_system_prompt.json`
- `resultados_context_prompt.json`
- `resultados_role_based.json`
- `resultados_few_shot.json`
- `resultados_cot.json`

### without_xai
- `resultados_system_prompt_without_xai.json`
- `resultados_context_prompt_without_xai.json`
- `resultados_role_based_without_xai.json`
- `resultados_few_shot_without_xai.json`
- `resultados_cot_without_xai.json`

### self_consistency
- `resultados_self_consistency.json`

### Legacy (from earlier runs)
- `resultados_with_xai_local.json`
- `resultados_without_xai_local.json`
- `resultados_enforce_knowledge_local.json`

---

## Log Files

Located in `outputs/` directory:
- `system_prompt_with_xai.log`
- `context_prompt_with_xai.log`
- `role_based_with_xai.log`
- `few_shot_with_xai.log`
- `cot_with_xai.log`
- `system_prompt_without_xai.log`
- `context_prompt_without_xai.log`
- `role_based_without_xai.log`
- `few_shot_without_xai.log`
- `cot_without_xai.log`
- `self_consistency_without_xai.log`