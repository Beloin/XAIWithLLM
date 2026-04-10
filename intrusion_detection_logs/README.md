# Intrusion Detection Logs — XAI Experiments

This folder contains the network intrusion detection dataset and all related XAI experiments for this Master's thesis research.

## Dataset

- **Source:** Kaggle — [Intrusion Detection Logs (Normal, Bot, Scan)](https://www.kaggle.com/datasets/developerghost/intrusion-detection-logs-normal-bot-scan)
- **Classes:** BotAttack (1), Normal (0), PortScan (2)
- **Features:** Port, Request_Type, Protocol, Payload_Size, User_Agent, Status
- **Model:** Random Forest with ~99.7% accuracy

See `DATASET.md` for full feature documentation and pipeline details.

## Folder Structure

```
intrusion_detection_logs/
├── Network_logs.csv           # Dataset
├── DATASET.md                # Dataset documentation
├── CONCLUSION.md             # Research conclusions
├── XAI_EXPLANATION_QUALITY.md # Quality assessment of LLM explanations
│
├── without_XAI/              # Baseline experiments (no XAI data)
│   ├── without_xai.ipynb
│   ├── resultados_without_xai_samples_{10,20,40}.json
│   └── VALIDATION_FINDINGS.md
│
├── with_XAI/                 # XAI injection experiments
│   ├── with_xai.ipynb
│   ├── resultados_with_xai_local_{5,10,15,25}.json
│   └── VALIDATION_FINDINGS.md
│
└── enforce_knowledge/        # Two-phase experiments (Phase 1 without XAI → Phase 2 with XAI)
    ├── enforce_knowledge.ipynb
    ├── resultados_enforce_knowledge_samples_*_local_*.json
    └── VALIDATION_FINDINGS.md
```

## Experiment Tracks

| Track | Description |
|-------|-------------|
| **without_XAI** | Baseline: LLM analyzes model with raw samples only |
| **with_XAI** | Intervention: LLM receives SHAP global + SHAP local + LIME local |
| **enforce_knowledge** | Paired design: Same chat, Phase 1 without XAI → Phase 2 with XAI |

## Key Results

- **Without XAI:** 25% feature ranking accuracy, 75% User_Agent bias
- **With XAI:** 100% accuracy (N_LOCAL≥15), User_Agent bias eliminated
- **Recommended config:** N_LOCAL=15 with gpt-oss:20b

The XAI injection corrects LLM semantic intuition — User_Agent looks important to LLMs, but SHAP shows it isn't.