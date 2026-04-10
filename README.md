# SOC XAI — Project Overview

Can a Large Language Model produce cybersecurity explanations comparable to what a human analyst would derive from SHAP and LIME?

## Structure

```
soc_xai/
├── README.md
├── CLAUDE.md                    # Project guide
├── AGENTS.md                    # Agent context file
├── run_all.sh                   # Run all experiments
│
└── intrusion_detection_logs/    # Dataset + experiments
    ├── README.md                # Experiment overview
    ├── DATASET.md              # Dataset documentation
    ├── CONCLUSION.md           # Research conclusions
    ├── XAI_EXPLANATION_QUALITY.md
    ├── Network_logs.csv         # Dataset
    │
    ├── without_XAI/             # Baseline experiments
    ├── with_XAI/                # XAI injection experiments
    └── enforce_knowledge/       # Two-phase paired experiments
```

## Experiments

| Experiment | Description |
|------------|-------------|
| **Without XAI** | Baseline: LLM analyzes model with raw data samples only |
| **With XAI** | Intervention: LLM receives SHAP + LIME explanations |
| **Enforce Knowledge** | Two-phase: Same chat, Phase 1 without XAI → Phase 2 with XAI |

## Models

All run locally via Ollama:
- glm-4.7-flash (~9B)
- qwen3:14b (14B)
- gpt-oss:20b (20B)
- qwen3:30b (30B)

## Key Finding

**XAI injection improves LLM reasoning:**
- Without XAI: 25% feature ranking accuracy, 75% User_Agent bias
- With XAI: 100% accuracy, bias eliminated

See `intrusion_detection_logs/CONCLUSION.md` for full results.