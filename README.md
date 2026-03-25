# Analysis of XAI with LLM

Can a Large Language Model produce cybersecurity explanations comparable to what a human analyst would derive from SHAP and LIME?

## LLMs Used

| Model | Size | Tier |
|---|---|---|
| GLM-4.7-Flash | ~9B | Medium |
| Qwen3 14B | 14B | Medium |
| GPT-OSS 20B | 20B | Medium |
| Qwen3 30B | 30B | Large |

All models run locally via Ollama.

## Dataset

**Network_logs.csv** — network traffic log entries labeled as one of three classes:
- **BotAttack** (0) — botnet command-and-control traffic
- **Normal** (1) — legitimate network activity
- **PortScan** (2) — reconnaissance scanning

Features: Port, Request_Type, Protocol, Payload_Size, User_Agent, Status (all numerically encoded).

## Pipeline

1. Pre-process and encode features
2. Balance classes with SMOTE
3. Train a Random Forest classifier (~99.7% accuracy)
4. Generate SHAP (TreeExplainer) and LIME explanations
5. Feed data to LLMs via multi-turn Ollama API calls
6. Compare LLM outputs across methods

## Methods

### 1. Ground Truth

Human interpretations based on SHAP global/local values and LIME feature contributions. This serves as the baseline for evaluating LLM-generated explanations.

### 2. LLM Without XAI

The LLM receives only:
- Model info and column descriptions
- Raw training data samples
- Real vs predicted labels

It must infer feature importance and explain predictions based solely on data patterns.

Experiments vary the amount of raw data provided (10, 20, 40 samples) to test how data volume affects explanation quality.

### 3. LLM With XAI

The LLM receives everything from Method 2, plus:
- SHAP global feature importance per class
- SHAP local explanations per instance
- LIME local explanations for the same instances

Experiments vary the number of local SHAP+LIME instances (5, 10, 15, 25) while keeping raw data fixed at 20 samples.

### 4. Enforce Knowledge (Before/After)

A single chat session per model with two phases:
1. **Phase 1:** LLM analyzes with raw data only (no XAI)
2. **Phase 2:** Same chat, SHAP+LIME data is injected, LLM revises its analysis

This tests whether XAI evidence changes or improves the LLM's reasoning within the same conversation.

