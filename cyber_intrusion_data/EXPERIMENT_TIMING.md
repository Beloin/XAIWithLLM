# Experiment Timing - cyber_intrusion_data

## Summary

| Category | Total Time |
|----------|------------|
| with_xai (5 experiments) | 2h 49m |
| without_xai (5 experiments) | 1h 53m |
| self_consistency (1 run) | 1h 33m |
| **Total** | **6h 15m** |

---

## with_xai Experiments

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| system_prompt | 2026-04-14 08:55:19 | 2026-04-14 09:27:45 | 32m 26s |
| context_prompt | 2026-04-14 09:27:45 | 2026-04-14 10:05:33 | 37m 48s |
| role_based | 2026-04-14 10:05:33 | 2026-04-14 10:44:34 | 39m 01s |
| few_shot | 2026-04-14 10:44:34 | 2026-04-14 11:17:36 | 33m 02s |
| cot | 2026-04-14 11:17:36 | 2026-04-14 11:44:29 | 26m 53s |

**with_xai Subtotal: 2h 49m**

---

## without_xai Experiments (Previous Run - Invalid, Overwritten)

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| system_prompt | 2026-04-14 11:44:29 | 2026-04-14 12:27:13 | 42m 44s |
| context_prompt | 2026-04-14 12:27:13 | 2026-04-14 13:01:53 | 34m 40s |
| role_based | 2026-04-14 13:01:53 | 2026-04-14 13:40:41 | 38m 48s |
| few_shot | 2026-04-14 13:40:41 | 2026-04-14 14:14:53 | 34m 12s |
| cot | 2026-04-14 14:14:53 | 2026-04-14 14:57:47 | 42m 54s |

**Note:** These results were overwritten by with_xai experiments (same output filename). Invalid for analysis.

---

## without_xai Experiments (Corrected Run)

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| system_prompt | 2026-04-14 23:03:58 | 2026-04-14 23:30:52 | 26m 54s |
| context_prompt | 2026-04-14 23:30:52 | 2026-04-15 00:05:37 | 34m 45s |
| role_based | 2026-04-15 00:05:37 | 2026-04-15 00:41:39 | 36m 02s |
| few_shot | 2026-04-15 00:41:39 | 2026-04-15 01:18:37 | 36m 58s |
| cot | 2026-04-15 01:18:37 | 2026-04-15 01:56:38 | 38m 01s |

**without_xai Subtotal: 2h 53m**

---

## self_consistency Experiments

| Experiment | Start | End | Duration |
|------------|-------|-----|----------|
| self_consistency | 2026-04-15 01:56:38 | 2026-04-15 03:29:58 | 1h 33m 20s |

**self_consistency Subtotal: 1h 33m**

---

## Per-Model Timing (Approximate)

Average time per model varies by prompt technique and XAI condition:

| Condition | Avg per Experiment | Avg per Model |
|-----------|---------------------|---------------|
| with_xai | ~33m | ~6.6m |
| without_xai | ~31m | ~6.2m |
| self_consistency | ~93m | ~18.6m (5 runs) |

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