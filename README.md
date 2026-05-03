# SOC XAI — Project Overview

Can a Large Language Model produce cybersecurity explanations comparable to what a human analyst would derive from SHAP and LIME?

**Research Question:** Does injecting XAI (SHAP + LIME) explanations into LLM prompts improve their ability to reason about and explain ML model behavior?

## Project Structure

```
soc_xai/
├── README.md                              # This file
├── CLAUDE.md                               # Project guide (development)
├── AGENTS.md                               # Agent context (comprehensive)
│
├── pipeline.py                             # Core pipeline module
├── self_consistency.py                     # Feature ranking aggregation
├── run_all_experiments.sh                  # Master experiment runner
│
├── docs/
│   └── PROMPT_ENGINEERING_TECHNIQUES.md    # Prompt engineering documentation
│
├── intrusion_detection_logs/               # Dataset 1 + original experiments
│   ├── Network_logs.csv                    # Network intrusion dataset
│   ├── DATASET.md                          # Dataset documentation
│   ├── CONCLUSION.md                       # Research conclusions
│   ├── README.md                           # Experiment overview
│   ├── XAI_EXPLANATION_QUALITY.md          # Quality assessment
│   │
│   ├── without_XAI/                        # Baseline experiments
│   │   ├── resultados_without_xai_samples_{10,20,40}.json
│   │   └── VALIDATION_FINDINGS.md
│   │
│   ├── with_XAI/                           # XAI injection experiments
│   │   ├── resultados_with_xai_local_{5,10,15,25}.json
│   │   └── VALIDATION_FINDINGS.md
│   │
│   └── enforce_knowledge/                  # Two-phase paired experiments
│       ├── resultados_enforce_knowledge_*.json
│       └── VALIDATION_FINDINGS.md
│
├── cyber_intrusion_data/                   # Dataset 2 + prompt engineering experiments
│   ├── cybersecurity_intrusion_data.csv    # Binary classification dataset
│   ├── EXPERIMENT_TIMING.md                # Timing analysis
│   ├── BEST_EXPLANATIONS_BY_MODEL.md       # Best explanations per model
│   ├── inputs/                             # Input configurations
│   ├── outputs/                            # Log files
│   └── resultados_*.json                   # Results files
│
└── NSL_KDD/                               # Dataset 3 + prompt engineering experiments
    ├── csv_result-KDDTest+.csv            # NSL-KDD test set
    ├── KDDTrain+_20Percent.txt          # NSL-KDD training subset
    ├── EXPERIMENT_TIMING.md              # Timing analysis
    ├── BEST_EXPLANATIONS_BY_MODEL.md     # Best explanations per model
    ├── inputs/                            # Input configurations
    ├── outputs/                           # Log files
    └── resultados_*.json                  # Results files
```

## Datasets

| Dataset | Classes | Features | Location |
|---------|---------|----------|----------|
| **Network Logs** | 3 (BotAttack, Normal, PortScan) | 6 | `intrusion_detection_logs/` |
| **Cyber Intrusion** | 2 (Normal, Attack) | 9 | `cyber_intrusion_data/` |
| **NSL-KDD** | 2 (Normal, Attack) | 15 | `NSL_KDD/` |

## Experiments

### Original Research (intrusion_detection_logs)

| Experiment | Description |
|------------|-------------|
| **without_XAI** | Baseline: LLM analyzes model with raw data samples only. Varies N_SAMPLES (10, 20, 40). |
| **with_XAI** | Intervention: LLM receives SHAP global + SHAP local + LIME local explanations. Varies N_LOCAL (5, 10, 15, 25). |
| **enforce_knowledge** | Two-phase: Same chat, Phase 1 without XAI → Phase 2 with XAI. Paired configs. |

### Prompt Engineering Experiments (cyber_intrusion_data, NSL_KDD)

| Technique | Description |
|-----------|-------------|
| system_prompt | Persona-based instruction (e.g., "SOC analyst with 15 years experience") |
| context_prompt | Contextual framing of task purpose |
| role_based | Domain expert role assignment |
| few_shot | Example-based prompting with sample explanations |
| cot | Chain-of-thought reasoning prompts |
| self_consistency | Multiple runs with aggregated feature rankings (without_xai only) |

Each technique tested in both **with_xai** and **without_xai** conditions.

## Models

All models run via Ollama (localhost:11434) or cloud endpoints:

| Model | Size | Tier | max_tokens |
|-------|------|------|------------|
| glm-4.7-flash | ~9B | medium | 8192 |
| qwen3:14b | 14B | medium | 8192 |
| gpt-oss:20b | 20B | medium | 8192 |
| qwen3:30b | 30B | large | 16384 |
| glm-5:cloud | cloud | large | 16384 |

## Key Results

### Original Research (Network Logs)

| Metric | Without XAI | With XAI | Improvement |
|--------|-------------|----------|-------------|
| Feature ranking accuracy | 25% (best) | 100% (N_LOCAL>=15) | **+75%** |
| User_Agent bias | 75% (N=20) | ~0% | **-75%** |
| Model success rate | 100% | 50-100% (config-dependent) | Variable |

**Optimal configuration:** N_LOCAL=15 with gpt-oss:20b or qwen3:14b

### Critical Finding

XAI injection corrects LLM semantic intuition. Example: User_Agent contains strings like "nmap", "curl" that look security-relevant to LLMs. Without XAI, 75% of models overvalue it. SHAP shows actual importance <0.006. With XAI, models correctly deprioritize it.

### Ground Truth Reference

**Network Logs dataset** (Random Forest, ~99.7% accuracy):

| Class | #1 | #2 | #3 |
|-------|----|----|----|
| BotAttack | Port (0.244) | Status (0.129) | Payload_Size (0.091) |
| Normal | Port (0.273) | Payload_Size (0.184) | Status (0.195) |
| PortScan | Payload_Size (0.261) | Status (0.066) | Port (0.030) |

**User_Agent importance < 0.006 for all classes** — any LLM claim of its importance is fabrication.

## Pipeline Module

Reusable pipeline (`pipeline.py`) for running experiments:

```python
from pipeline import pipeline

result = pipeline(
    dataset="Network_logs.csv",
    columnDesc=["Port", "Request_Type", "Protocol", "Payload_Size", "User_Agent", "Status"],
    target_col="Scan_Type_Label",
    class_names=["BotAttack", "Normal", "PortScan"],
    models=[{"name": "qwen3:14b", "api": "http://localhost:11434/v1"}],
    experiment_type="with_xai",
    n_samples=20,
    n_shap_local=15,
    n_lime_local=15,
    output_file="results.json"
)
```

### Experiment Types

| Type | Description | Prompts |
|------|-------------|---------|
| `with_xai` | Model receives SHAP + LIME explanations | Model info → Samples → XAI → Analysis |
| `without_xai` | Model receives raw samples only | Model info → Data → Analysis |
| `enforce_knowledge` | Two-phase revision | Model info → Phase 1 → XAI → Phase 2 |

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_samples` | 20 | Training/prediction samples |
| `n_shap_local` | 20 | SHAP local explanations |
| `n_lime_local` | 20 | LIME local explanations |
| `chat` | False | Split prompts into multi-turn chat |
| `system_prompt` | None | Override default system prompt |
| `random_seed` | 42 | Reproducibility seed |

## Prompt Engineering Integration

The pipeline supports all techniques from `docs/PROMPT_ENGINEERING_TECHNIQUES.md`:

- **System prompts:** Persona-based instructions
- **Few-shot examples:** Sample explanations in prompt
- **Chain-of-thought:** Explicit reasoning steps
- **Role-based:** Domain expert personas
- **Context-based:** Task framing
- **Self-consistency:** Multiple runs with aggregation

### Input Configuration Format

```json
{
  "models": [
    {"name": "glm-5:cloud", "api": "http://localhost:11434/v1"}
  ],
  "experimentType": "with_xai",
  "chat": true,
  "nSamples": 20,
  "nShapLocal": 15,
  "nLimeLocal": 15,
  "systemPrompt": "You are a SOC analyst...",
  "randomSeed": 42,
  "outputFile": "results.json"
}
```

## Running Experiments

### Original Experiments

```bash
cd intrusion_detection_logs
python with_xai.py inputs/local_15.input.json
```

### Prompt Engineering Experiments

```bash
./run_all_experiments.sh  # Runs all experiments sequentially
```

### Prerequisites

```bash
pip install nbconvert ipython shap lime pandas scikit-learn
```

## Model Recommendations

| Model | Recommendation | Rationale |
|-------|----------------|-----------|
| **gpt-oss:20b** | Primary choice | Most reliable (100% success), detailed responses |
| **qwen3:14b** | Good alternative | Stable, moderate response length |
| **glm-4.7-flash** | Use with caution | Works at N_LOCAL>=15, truncates at N_LOCAL=10 |
| **qwen3:30b** | Avoid | Fails at low N_LOCAL (5, 10) |

## Thesis Support

The data **supports the core thesis**: XAI injection improves LLM reasoning about ML models.

| Evidence Type | Without XAI | With XAI | Supports Thesis |
|---------------|-------------|----------|-----------------|
| Feature ranking accuracy | 25% | 100% | Strong |
| User_Agent bias reduction | 75% biased | ~0% biased | Strong |
| SHAP/LIME citation | N/A | 100% valid responses | Strong |
| Model consistency | Variable | Stable (good configs) | Moderate |

## Known Issues

| Issue | Affected Config | Impact |
|-------|-----------------|--------|
| qwen3:30b empty responses | N_LOCAL < 15 | Cannot compare all 4 models |
| glm-4.7-flash truncation | N_LOCAL=10 | 60% shorter response |
| Token limit (8192) | Phase 2 long responses | Possible truncation |
| VRAM pressure | Sequential model runs | Requires `ollama stop` between models |

## Configuration Recommendations

### For With-XAI Experiments

| Parameter | Recommended | Alternative |
|-----------|-------------|-------------|
| N_LOCAL | **15** | 25 |
| Model | **gpt-oss:20b** | qwen3:14b |

### For Without-XAI Baseline

| Parameter | Recommended |
|-----------|-------------|
| N_SAMPLES | **20** |

### For Enforce Knowledge (Paired)

| N_SAMPLES | N_LOCAL | Notes |
|-----------|---------|-------|
| 20 | 15 | Recommended pairing |

## Files Reference

### Result Files

| Pattern | Description |
|---------|-------------|
| `resultados_*.json` | LLM responses + metadata |
| `*.input.json` | Experiment input configurations |
| `*.log` | Execution logs (outputs/) |

### Documentation

| File | Description |
|------|-------------|
| `CONCLUSION.md` | Research conclusions |
| `VALIDATION_FINDINGS.md` | Per-experiment validation |
| `EXPERIMENT_TIMING.md` | Timing analysis |
| `BEST_EXPLANATIONS_BY_MODEL.md` | Best model outputs |

## Author

Master's research project comparing LLM analysis of ML model behavior with and without XAI data, focusing on cybersecurity applications (network intrusion detection).

## License

Academic research use. See thesis documentation for full methodology and citations.