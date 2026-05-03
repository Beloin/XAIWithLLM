"""
XAI Pipeline for LLM explainability experiments.

Processes datasets, trains models, computes SHAP/LIME explanations,
and queries LLMs to analyze ML model behavior.

Usage:
    from pipeline import pipeline
    
    result = pipeline(
        dataset="Network_logs.csv",
        columnDesc=["Port description", "Request_Type description", ...],
        target_col="Scan_Type_Label",
        experiment_type="with_xai",
        output_file="results.json"
    )
"""

import json
import time
import warnings
import subprocess
from pathlib import Path
from typing import Literal, List, Dict, Any, Optional

import numpy as np
import pandas as pd
import shap
from lime import lime_tabular
from openai import OpenAI
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Import self-consistency module
try:
    from self_consistency import process_self_consistency, build_self_consistency_prompt
except ImportError:
    process_self_consistency = None
    build_self_consistency_prompt = None


# ===== CONSTANTS =====

OLLAMA_BASE_URL = "http://localhost:11434/v1"
REQUEST_TIMEOUT = 900.0
MAX_SHAP_SAMPLE = 10000
PHASE1_MAX_TOKENS = 4096

DEFAULT_MODELS = [
    {"name": "glm-4.7-flash:latest", "api": OLLAMA_BASE_URL},
    {"name": "qwen3:14b", "api": OLLAMA_BASE_URL},
    {"name": "gpt-oss:20b", "api": OLLAMA_BASE_URL},
    {"name": "qwen3:30b", "api": OLLAMA_BASE_URL},
]


# ===== HELPER FUNCTIONS =====

def _load_dataset(dataset):
    """Load dataset from path or return DataFrame."""
    if isinstance(dataset, str):
        print(f"Loading dataset from {dataset}...")
        return pd.read_csv(dataset)
    print("Using provided DataFrame...")
    return dataset.copy()


def _validate_dataset(df, target_col, columnDesc):
    """Validate that dataset is preprocessed and columns match."""
    if target_col is None:
        raise ValueError("target_col is required. Dataset must be preprocessed with target column specified.")
    
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset. Columns: {df.columns.tolist()}")
    
    feature_cols = [c for c in df.columns if c != target_col]
    if len(columnDesc) != len(feature_cols):
        raise ValueError(
            f"columnDesc length ({len(columnDesc)}) must match feature columns ({len(feature_cols)}). "
            f"Features: {feature_cols}"
        )
    
    non_numeric = df[feature_cols].select_dtypes(include=['object']).columns.tolist()
    if non_numeric:
        raise ValueError(
            f"Dataset contains non-numeric columns: {non_numeric}. "
            "Dataset MUST be preprocessed before pipeline (label encoding, scaling, etc.)"
        )
    
    return feature_cols


def _train_model(df, target_col, feature_cols, random_seed):
    """Train RandomForestClassifier and return model + accuracy."""
    print("Training RandomForestClassifier...")
    
    X = df[feature_cols]
    y = df[target_col]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=random_seed, stratify=y
    )
    
    model = RandomForestClassifier(random_state=random_seed)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model accuracy: {accuracy:.4f}")
    
    return model, accuracy, X_train, X_test, y_train, y_test


def _compute_shap(model, X_sample, n_local, class_names):
    """
    Compute SHAP global + local explanations.
    
    Returns dict with:
    - shap_global_raw: mean |SHAP| per feature per class
    - shap_global_percentages: normalized percentages
    - shap_local: per-instance SHAP values
    """
    print(f"Computing SHAP for {len(X_sample)} instances...")
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    feature_names = list(X_sample.columns)
    
    shap_global_raw = {}
    shap_global_percentages = {}
    
    for cls_idx, cls_name in enumerate(class_names):
        mean_abs = np.abs(shap_values[:, :, cls_idx]).mean(axis=0)
        
        shap_global_raw[cls_name] = {
            feat: round(float(val), 6) for feat, val in zip(feature_names, mean_abs)
        }
        
        total = mean_abs.sum()
        shap_global_percentages[cls_name] = {
            feat: round(float(val / total), 4) for feat, val in zip(feature_names, mean_abs)
        }
    
    shap_local = []
    for idx in range(min(n_local, len(X_sample))):
        entry = {
            "instance_index": int(X_sample.index[idx]),
            "features": {feat: float(X_sample.iloc[idx][feat]) for feat in feature_names},
            "shap_values_per_class": {
                cls_name: {
                    feat: float(shap_values[idx, f_idx, cls_idx])
                    for f_idx, feat in enumerate(feature_names)
                }
                for cls_idx, cls_name in enumerate(class_names)
            }
        }
        shap_local.append(entry)
    
    print(f"SHAP computed: {len(class_names)} classes, {len(feature_names)} features")
    
    return {
        "shap_global_raw": shap_global_raw,
        "shap_global_percentages": shap_global_percentages,
        "shap_local": shap_local
    }


def _compute_lime(model, X_train, X_sample, n_local, feature_names, class_names):
    """Compute LIME local explanations."""
    print(f"Computing LIME for {n_local} instances...")
    
    explainer = lime_tabular.LimeTabularExplainer(
        X_train.values,
        feature_names=feature_names,
        class_names=class_names,
        mode='classification'
    )
    
    lime_local = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        
        for idx in range(min(n_local, len(X_sample))):
            sample = X_sample.iloc[idx].values
            exp = explainer.explain_instance(
                sample,
                model.predict_proba,
                num_features=len(feature_names)
            )
            
            lime_local.append({
                "instance_index": int(X_sample.index[idx]),
                "feature_contributions": [
                    {"rule": rule, "weight": float(weight)}
                    for rule, weight in exp.as_list()
                ]
            })
    
    print(f"LIME computed: {len(lime_local)} instances")
    return lime_local


def _needs_model_start_stop(model_dict):
    """
    Check if model needs start/stop via ollama.
    
    Returns True if:
    - API is local (localhost/127.0.0.1)
    - Model name does NOT contain 'cloud'
    
    Cloud models (e.g., qwen3.5:cloud) on localhost don't need start/stop.
    """
    api_url = model_dict.get("api", "")
    model_name = model_dict.get("name", "")
    
    is_local = "localhost" in api_url or "127.0.0.1" in api_url
    is_cloud = "cloud" in model_name.lower()
    
    return is_local and not is_cloud


def _start_model(model_name):
    """Start local Ollama model."""
    print(f"  Starting model: {model_name}...")
    subprocess.run(["ollama", "run", model_name], capture_output=True, text=True)
    time.sleep(2)


def _stop_model(model_name):
    """Stop local Ollama model."""
    print(f"  Stopping model: {model_name}...")
    subprocess.run(["ollama", "stop", model_name], capture_output=True, text=True)


def _query_llm(prompts, model_dict, max_tokens, timeout=REQUEST_TIMEOUT):
    """Query LLM via OpenAI-compatible API.
    
    Args:
        prompts: Single prompt string OR list of prompts for chat mode
        model_dict: Model configuration dict
        max_tokens: Single int or list of ints for multi-turn
        timeout: Request timeout
    
    Returns:
        (response, elapsed_ms, thinking_process, token_usage) tuple
        thinking_process is None if model doesn't support it
        token_usage is dict with prompt_tokens, completion_tokens, total_tokens
    """
    client = OpenAI(
        base_url=model_dict["api"],
        api_key=model_dict.get("api_key", "ollama")
    )
    
    model_name = model_dict["name"]
    
    def _extract_thinking(message):
        """Extract thinking/reasoning from message if available."""
        msg_dict = message.model_dump()
        return msg_dict.get("reasoning") or msg_dict.get("reasoning_content")
    
    if isinstance(prompts, str):
        # Single prompt mode
        start = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompts}],
            max_tokens=max_tokens,
            timeout=timeout
        )
        elapsed_ms = (time.time() - start) * 1000
        
        thinking = _extract_thinking(response.choices[0].message)
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
            "completion_tokens": response.usage.completion_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None
        }
        
        return response.choices[0].message.content, elapsed_ms, thinking, usage
    
    else:
        # Chat mode (list of prompts)
        chat_history = []
        responses = []
        thinking_parts = []
        total_time = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        for i, prompt in enumerate(prompts):
            tokens = max_tokens[i] if isinstance(max_tokens, list) else max_tokens
            chat_history.append({"role": "user", "content": prompt})
            
            start = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=chat_history,
                max_tokens=tokens,
                timeout=timeout
            )
            elapsed_ms = (time.time() - start) * 1000
            total_time += elapsed_ms
            
            if response.usage:
                total_prompt_tokens += response.usage.prompt_tokens
                total_completion_tokens += response.usage.completion_tokens
            
            content = response.choices[0].message.content
            chat_history.append({"role": "assistant", "content": content})
            responses.append(content)
            
            thinking = _extract_thinking(response.choices[0].message)
            if thinking:
                thinking_parts.append(thinking)
        
        final_thinking = "\n\n--- Turn Break ---\n\n".join(thinking_parts) if thinking_parts else None
        usage = {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens
        }
        return responses[-1], total_time, final_thinking, usage


def _format_time(ms):
    """Format milliseconds into human-readable string."""
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    return f"{int(minutes)}m{int(seconds % 60)}s"


def _build_column_desc_string(columnDesc, feature_cols):
    """Build column description string for prompt."""
    lines = []
    for feat, desc in zip(feature_cols, columnDesc):
        lines.append(f"  - {feat}: {desc}")
    return "\n".join(lines)


def _build_prompt_without_xai(model_info, column_desc_str, train_sample_str, pred_sample_str, feature_cols, class_names):
    """Build prompt for without_xai experiment."""
    
    prompt = f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a classification model that has already been fully validated through a complete data science pipeline.

# Model Information

- **Type:** {model_info['type']}
- **Task:** Classification from log entries
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(f'{cls} (index {i})' for i, cls in enumerate(class_names))}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f} (on test set)
- **Pipeline:** Data cleaning → feature selection → label encoding → class balancing (SMOTE) → 70/30 stratified train/test split

# Column Descriptions

{column_desc_str}

# Training Samples (representative examples)

{train_sample_str}

# Predictions (true label vs predicted label)

{pred_sample_str}

---

Please analyze this model and explain:

1. **Feature Importance:** Rank the top 3-5 features by their importance for each class. Be specific about why each feature matters.

2. **Class-Specific Patterns:** For each class, describe what patterns the model looks for.

3. **Misclassification Risk:** What might cause this model to misclassify? Consider edge cases and class confusion.

4. **Security Implications:** How would a SOC analyst use these insights? What detection rules would you derive?

Be precise and ground your reasoning in the data samples provided. Do NOT fabricate statistics or metrics that weren't explicitly given.
"""
    return prompt


def _build_prompt_with_xai(model_info, column_desc_str, train_sample_str, pred_sample_str, 
                           shap_global_str, shap_local_str, lime_local_str, feature_cols, class_names):
    """Build prompt for with_xai experiment."""
    
    prompt = f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a classification model that has already been fully validated through a complete data science pipeline.

# Model Information

- **Type:** {model_info['type']}
- **Task:** Classification from log entries
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(f'{cls} (index {i})' for i, cls in enumerate(class_names))}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f} (on test set)
- **Pipeline:** Data cleaning → feature selection → label encoding → class balancing (SMOTE) → 70/30 stratified train/test split

# Column Descriptions

{column_desc_str}

# Training Samples (representative examples)

{train_sample_str}

# Predictions (true label vs predicted label)

{pred_sample_str}

---

# Explainability Data

## SHAP Global Importance (mean |SHAP| per feature per class)

{shap_global_str}

## SHAP Local Explanations (per-instance feature contributions)

{shap_local_str}

## LIME Local Explanations (rule-based feature contributions)

{lime_local_str}

---

Please analyze this model using the SHAP and LIME explanations provided:

1. **Feature Importance:** Using SHAP global values, rank the top 3 features for each class ({', '.join(class_names)}). Explain why these features have the highest impact.

2. **Class-Specific Patterns:** For each class ({', '.join(class_names)}), describe how the model distinguishes it from others. Reference specific SHAP values and LIME rules.

3. **Comparing SHAP and LIME:** Do the explanations converge? Where do they differ? Which features are consistently important?

4. **Security Implications:** What detection rules would you recommend for a SOC analyst? Be specific about thresholds and conditions.

IMPORTANT: Use ONLY the class names provided ({', '.join(class_names)}). Do NOT invent or use other class names. Cite the exact SHAP values from the data.
"""
    return prompt


def _build_prompts_enforce_knowledge(model_info, column_desc_str, train_sample_str, pred_sample_str,
                                     feature_cols, class_names, shap_global_str=None, 
                                     shap_local_str=None, lime_local_str=None):
    """Return [phase1_prompt, phase2_prompt] for enforce_knowledge."""
    
    phase1 = _build_prompt_without_xai(
        model_info, column_desc_str, train_sample_str, pred_sample_str, feature_cols, class_names
    )
    
    phase2 = f"""Now I've computed SHAP and LIME explanations for this model. Please revise your analysis.

# SHAP Global Importance (mean |SHAP| per feature per class)

{shap_global_str}

# SHAP Local Explanations (per-instance feature contributions)

{shap_local_str}

# LIME Local Explanations (rule-based feature contributions)

{lime_local_str}

---

Please revise your previous analysis incorporating this explainability data:

1. **Feature Importance Update:** Compare your earlier ranking to the SHAP values. What changed?

2. **Evidence-Based Corrections:** Where did your initial reasoning deviate from the actual model behavior? What did the XAI data reveal?

3. **Actionable Insights:** Based on the SHAP/LIME evidence, provide concrete detection rules for SOC analysts.

Cite specific SHAP values and LIME rules to support your revised conclusions.
"""
    
    return [phase1, phase2]


# ===== CHAT PROMPT BUILDERS =====
# For APIs that can't handle large single inputs, split into multi-turn chat

def _build_chat_prompts_without_xai(model_info, column_desc_str, train_sample_str, pred_sample_str, 
                                    feature_cols, class_names):
    """Build chat prompts for without_xai experiment (split into chunks)."""
    
    prompts = []
    
    # Message 1: Model info + column descriptions
    prompts.append(f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a classification model. I will send the data in multiple messages.

**Wait for further instructions before responding.**

# Model Information

- **Type:** {model_info['type']}
- **Task:** Classification from log entries
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(f'{cls} (index {i})' for i, cls in enumerate(class_names))}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f} (on test set)
- **Pipeline:** Data cleaning → feature selection → label encoding → class balancing (SMOTE) → 70/30 stratified train/test split

# Column Descriptions

{column_desc_str}

Please acknowledge receipt of this information and wait for the data samples.
""")
    
    # Message 2: Training samples + predictions + analysis request
    prompts.append(f"""# Training Samples (representative examples)

{train_sample_str}

# Predictions (true label vs predicted label)

{pred_sample_str}

---

Now please analyze this model and explain:

1. **Feature Importance:** Rank the top 3-5 features by their importance for each class. Be specific about why each feature matters.

2. **Class-Specific Patterns:** For each class, describe what patterns the model looks for.

3. **Misclassification Risk:** What might cause this model to misclassify? Consider edge cases and class confusion.

4. **Security Implications:** How would a SOC analyst use these insights? What detection rules would you derive?

Be precise and ground your reasoning in the data samples provided. Do NOT fabricate statistics or metrics that weren't explicitly given.
""")
    
    return prompts


def _build_chat_prompts_with_xai(model_info, column_desc_str, train_sample_str, pred_sample_str, 
                                 shap_global_str, shap_local_str, lime_local_str, feature_cols, class_names):
    """Build chat prompts for with_xai experiment (split into chunks)."""
    
    prompts = []
    
    # Message 1: Model info + column descriptions
    prompts.append(f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a classification model using XAI explanations. I will send the data in multiple messages.

**Wait for further instructions before responding.**

# Model Information

- **Type:** {model_info['type']}
- **Task:** Classification from log entries
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(f'{cls} (index {i})' for i, cls in enumerate(class_names))}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f} (on test set)
- **Pipeline:** Data cleaning → feature selection → label encoding → class balancing (SMOTE) → 70/30 stratified train/test split

**CRITICAL MODEL TYPE CONSTRAINT:**
- The model is a **{model_info['type']}**.
- Do NOT describe it as XGBoost, GradientBoosting, LogisticRegression, SVM, or any other algorithm.
- This is NOT a debate or guess - the model type is "{model_info['type']}" as provided.

# Column Descriptions (with encoded value mappings)

{column_desc_str}

**CRITICAL: STRICT VALUE CONSTRAINTS**
- Use ONLY the exact value mappings provided in the column descriptions above.
- Do NOT invent values that are not listed in the mappings.
- Do NOT claim values exist if they are not in the provided data.
- The data is ENCODED - use the mappings to decode values when explaining patterns.

**DO NOT USE YOUR PRIOR KNOWLEDGE TO INVENT DATA:**
- Do NOT invent model specifications not provided (e.g., number of trees, max depth, training parameters).
- Do NOT hallucinate dataset statistics not given (e.g., total rows, class distribution numbers).
- Do NOT claim the model has attributes you weren't told about.

Please acknowledge receipt and wait for the data samples and XAI explanations.
""")
    
    # Message 2: Training samples + predictions
    prompts.append(f"""# Training Samples (representative examples)

{train_sample_str}

# Predictions (true label vs predicted label)

{pred_sample_str}

**Wait for the XAI explanations in the next message.**
""")
    
    # Message 3: XAI data + analysis request
    prompts.append(f"""# Explainability Data

## SHAP Global Importance (mean |SHAP| per feature per class)

{shap_global_str}

## SHAP Local Explanations (per-instance feature contributions)

{shap_local_str}

## LIME Local Explanations (rule-based feature contributions)

{lime_local_str}

---

Now please analyze this model using the SHAP and LIME explanations provided:

Key SHAP global values (for reference):
{shap_global_str}

1. **Model Context:** Briefly acknowledge the model's performance (accuracy, per-class balance)
   as context for the explanation that follows. Do not spend effort analyzing accuracy — it is
   already validated. Just establish the baseline so the rest of your analysis has credibility.

2. **Global Feature Importance (SHAP):** Using the SHAP global values above, interpret the importance
   ranking for each class ({', '.join(class_names)}). Which features dominate and why from a
   cybersecurity perspective? Cite the exact SHAP values from the data.

3. **SHAP vs Data Patterns:** Do the SHAP rankings align with patterns visible in the training examples?

4. **Local Explanations (SHAP + LIME):** For critical instances, explain the prediction
   using both SHAP values AND LIME rules. Where do they agree? Where do they disagree?

5. **Feature Interaction Insights:** Based on SHAP/LIME, what feature combinations are most decisive
   for each class? How do features interact to drive predictions?

6. **Cybersecurity Insights:** Strongest indicators for each class.
   How could a SOC analyst use these explanations in practice?

7. **SHAP-LIME Coherence:** Assess agreement between SHAP and LIME explanations.
   Where they diverge, what does that tell us about the model's decision boundaries?

8. **Improvement Suggestions:** Concrete improvements based on XAI evidence to make the model
   more interpretable or robust.

**CRITICAL - DO NOT INVENT DATA:**
- Do NOT invent model specifications not provided (e.g., number of trees, max depth, training parameters).
- Do NOT hallucinate dataset statistics not given (e.g., total rows, class distribution numbers).
- Do NOT claim the model has attributes you weren't told about.
- Cite EXACT SHAP values from the data provided above.
- Use EXACT model type "{model_info['type']}", accuracy "{model_info['accuracy']:.4f}".
- You MAY use your domain knowledge to EXPLAIN patterns, but do NOT contradict the values provided in the input data.

Use numbered sections and subsections.""")
    
    return prompts


def _build_chat_prompts_enforce_knowledge(model_info, column_desc_str, train_sample_str, pred_sample_str,
                                          feature_cols, class_names, shap_global_str=None, 
                                          shap_local_str=None, lime_local_str=None):
    """Build chat prompts for enforce_knowledge experiment.
    
    Returns list of prompts that builds up conversation:
    - Messages 1-2: Phase 1 (without XAI)
    - Messages 3-4: Phase 2 (with XAI, revision)
    """
    
    prompts = []
    
    # Message 1: Model info
    prompts.append(f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a classification model. I will send the data in multiple messages.

**Wait for further instructions before responding.**

# Model Information

- **Type:** {model_info['type']}
- **Task:** Classification from log entries
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(f'{cls} (index {i})' for i, cls in enumerate(class_names))}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f} (on test set)
- **Pipeline:** Data cleaning → label encoding → class balancing (SMOTE) → 70/30 stratified train/test split

# Column Descriptions

{column_desc_str}

Please acknowledge receipt and wait for the data samples.
""")
    
    # Message 2: Data + analysis request (Phase 1)
    prompts.append(f"""# Training Samples

{train_sample_str}

# Predictions

{pred_sample_str}

---

Please analyze this model and explain:

1. **Feature Importance:** Rank the top 3-5 features by their importance for each class.

2. **Class-Specific Patterns:** For each class, describe what patterns the model looks for.

3. **Security Implications:** What detection rules would you derive?

Be precise and ground your reasoning in the data provided.
""")
    
    # Message 3: XAI data (Phase 2 starts)
    prompts.append(f"""Now I've computed SHAP and LIME explanations for this model.

# SHAP Global Importance

{shap_global_str}

# SHAP Local Explanations

{shap_local_str}

# LIME Local Explanations

{lime_local_str}

**Wait for analysis instructions.**
""")
    
    # Message 4: Revision request
    prompts.append(f"""Please revise your previous analysis incorporating this explainability data:

1. **Feature Importance Update:** Compare your earlier ranking to the SHAP values. What changed?

2. **Evidence-Based Corrections:** Where did your initial reasoning deviate from actual model behavior? What did the XAI data reveal?

3. **Actionable Insights:** Based on the SHAP/LIME evidence, provide concrete detection rules for SOC analysts.

Cite specific SHAP values and LIME rules to support your revised conclusions.
""")
    
    return prompts


# ===== MAIN PIPELINE =====

def pipeline(
    dataset,
    columnDesc,
    models=None,
    experiment_type="with_xai",
    chat=False,
    n_samples=20,
    n_shap_local=20,
    n_lime_local=20,
    target_col=None,
    class_names=None,
    system_prompt=None,
    self_consistency=False,
    self_consistency_runs=5,
    self_consistency_top_n=5,
    explain_message_tokens=12288,
    random_seed=42,
    output_file=None,
):
    """
    Run XAI experiment pipeline.
    
    Args:
        dataset: CSV path (str) or preprocessed DataFrame
        columnDesc: List of descriptions per column (same order as features, excluding target)
        models: List of dicts with 'name', 'api', and optional 'api_key'. Default: 4 local Ollama models
        experiment_type: "with_xai", "without_xai", or "enforce_knowledge"
        chat: If True, split prompts into multi-turn chat (for APIs with input size limits)
              When True, prompts include "Wait for further instructions" and data is sent in chunks
        n_samples: Number of train/pred samples to show LLM
        n_shap_local: Number of SHAP local instances
        n_lime_local: Number of LIME local instances
        target_col: Target column name (required)
        class_names: List of class names. If None, inferred from target values (default: class_0, class_1, ...)
        system_prompt: Custom system prompt. If None, uses default expert prompt
        self_consistency: If True, run multiple times and aggregate feature rankings
        self_consistency_runs: Number of runs for self-consistency (default: 5)
        self_consistency_top_n: Number of top features to extract (default: 5)
        explain_message_tokens: Max tokens for final LLM response
        random_seed: Random seed for reproducibility
        output_file: Path to save results as JSON. If None, only return dict
    
    Returns:
        Dict with experiment results, SHAP data, prompts, and model responses
    """
    np.random.seed(random_seed)
    
    if models is None:
        models = DEFAULT_MODELS
    
    print(f"=== Starting pipeline: experiment_type={experiment_type} ===")
    print(f"Models: {[m['name'] for m in models]}")
    
    # 1. Load and validate dataset
    df = _load_dataset(dataset)
    feature_cols = _validate_dataset(df, target_col, columnDesc)
    print(f"Features: {feature_cols}")
    
    # 2. Train model
    model, accuracy, X_train, X_test, y_train, y_test = _train_model(
        df, target_col, feature_cols, random_seed
    )
    
    # Get class names
    if class_names is None:
        class_names = sorted(df[target_col].unique().tolist())
        if isinstance(class_names[0], int) or isinstance(class_names[0], np.integer):
            class_names = [f"class_{c}" for c in class_names]
    
    print(f"Classes: {class_names}")
    
    # 3. Sample for SHAP/LIME
    sample_size = min(MAX_SHAP_SAMPLE, len(X_test))
    print(f"Sampling {sample_size} instances for SHAP/LIME computation...")
    sample_idx = np.random.choice(X_test.index.to_numpy(), size=sample_size, replace=False)
    X_sample = X_test.loc[sample_idx]
    
    # 4. Compute SHAP
    shap_results = _compute_shap(model, X_sample, n_shap_local, class_names)
    
    # 5. Compute LIME
    lime_local = _compute_lime(
        model, X_train, X_sample, n_lime_local, feature_cols, class_names
    )
    
    # 6. Build samples for prompt
    train_sample = X_train.sample(n_samples, random_state=random_seed)
    train_sample_with_target = train_sample.copy()
    train_sample_with_target[target_col] = y_train.loc[train_sample.index]
    train_sample_str = train_sample_with_target.to_json(orient="records")
    
    pred_sample_idx = X_sample.index[:n_samples]
    pred_sample = pd.DataFrame({
        "true_label": y_test.loc[pred_sample_idx].values,
        "predicted_label": model.predict(X_sample.loc[pred_sample_idx])
    })
    pred_sample_str = pred_sample.to_json(orient="records")
    
    # 7. Build prompts
    column_desc_str = _build_column_desc_string(columnDesc, feature_cols)
    model_info = {
        "type": "RandomForestClassifier",
        "accuracy": float(accuracy),
        "features": feature_cols,
        "classes": class_names,
        "target_col": target_col
    }
    
    shap_global_str = json.dumps(shap_results["shap_global_raw"], indent=2, ensure_ascii=False)
    shap_local_str = json.dumps(shap_results["shap_local"], indent=2, ensure_ascii=False)
    lime_local_str = json.dumps(lime_local, indent=2, ensure_ascii=False)
    
    # Default system prompt
    default_system = "You are an expert in Machine Learning, Explainable AI, and Cybersecurity."
    sys_prompt = system_prompt if system_prompt else default_system
    
    # Build prompts based on experiment_type and chat mode
    if experiment_type == "without_xai":
        if chat:
            prompts = _build_chat_prompts_without_xai(
                model_info, column_desc_str, train_sample_str, pred_sample_str, 
                feature_cols, class_names
            )
            # Inject custom system prompt
            prompts[0] = prompts[0].replace(default_system, sys_prompt)
            max_tokens = [4096, explain_message_tokens]  # First msg: ack, second: analysis
        else:
            prompts = _build_prompt_without_xai(
                model_info, column_desc_str, train_sample_str, pred_sample_str, 
                feature_cols, class_names
            )
            prompts = prompts.replace(default_system, sys_prompt)
            max_tokens = explain_message_tokens
        prompts_for_output = {"chat_prompts": prompts} if chat else {"prompt": prompts}
    
    elif experiment_type == "with_xai":
        if chat:
            prompts = _build_chat_prompts_with_xai(
                model_info, column_desc_str, train_sample_str, pred_sample_str,
                shap_global_str, shap_local_str, lime_local_str,
                feature_cols, class_names
            )
            prompts[0] = prompts[0].replace(default_system, sys_prompt)
            max_tokens = [4096, 4096, explain_message_tokens]  # ack, ack, analysis
        else:
            prompts = _build_prompt_with_xai(
                model_info, column_desc_str, train_sample_str, pred_sample_str,
                shap_global_str, shap_local_str, lime_local_str,
                feature_cols, class_names
            )
            prompts = prompts.replace(default_system, sys_prompt)
            max_tokens = explain_message_tokens
        prompts_for_output = {"chat_prompts": prompts} if chat else {"prompt": prompts}
    
    elif experiment_type == "enforce_knowledge":
        if chat:
            prompts = _build_chat_prompts_enforce_knowledge(
                model_info, column_desc_str, train_sample_str, pred_sample_str,
                feature_cols, class_names,
                shap_global_str, shap_local_str, lime_local_str
            )
            prompts[0] = prompts[0].replace(default_system, sys_prompt)
            # 4 messages: ack, phase1 analysis, ack, phase2 analysis
            max_tokens = [4096, explain_message_tokens, 4096, explain_message_tokens]
        else:
            prompts = _build_prompts_enforce_knowledge(
                model_info, column_desc_str, train_sample_str, pred_sample_str,
                feature_cols, class_names,
                shap_global_str, shap_local_str, lime_local_str
            )
            prompts[0] = prompts[0].replace(default_system, sys_prompt)
            max_tokens = [PHASE1_MAX_TOKENS, explain_message_tokens]
        prompts_for_output = {"chat_prompts": prompts} if chat else {"phase1": prompts[0], "phase2": prompts[1]}
    
    else:
        raise ValueError(f"Invalid experiment_type: {experiment_type}. Must be 'with_xai', 'without_xai', or 'enforce_knowledge'")
    
    # 7.5. Handle self-consistency prompt override
    if self_consistency:
        if build_self_consistency_prompt is None:
            raise ImportError("self_consistency module not available")
        
        sc_prompt = build_self_consistency_prompt(self_consistency_top_n)
        
        # Build minimal context prompt for self-consistency
        sc_context = f"""# Model Information

- **Type:** {model_info['type']}
- **Target:** {model_info['target_col']}
- **Classes:** {', '.join(class_names)}
- **Features:** {', '.join(feature_cols)}
- **Accuracy:** {model_info['accuracy']:.4f}

# Column Descriptions

{column_desc_str}

# Training Samples (representative examples)

{train_sample_str}

---

"""
        if chat:
            prompts = [sc_context + sc_prompt]
        else:
            prompts = sc_context + sc_prompt
        max_tokens = explain_message_tokens
        prompts_for_output = {"prompt": prompts, "self_consistency_mode": True}
    
    # 8. Query models
    results = {}
    for i, model_dict in enumerate(models):
        model_name = model_dict["name"]
        print(f"\n[{i+1}/{len(models)}] Querying {model_name}...")
        
        try:
            needs_start_stop = _needs_model_start_stop(model_dict)
            
            if needs_start_stop:
                _start_model(model_name)
            
            # Self-consistency mode: run multiple times
            if self_consistency:
                if process_self_consistency is None:
                    raise ImportError("self_consistency module not available")
                
                print(f"  Running self-consistency with {self_consistency_runs} runs...")
                responses = []
                total_time = 0
                all_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                
                for run_idx in range(self_consistency_runs):
                    print(f"    Run {run_idx + 1}/{self_consistency_runs}...")
                    response, time_ms, thinking_process, token_usage = _query_llm(prompts, model_dict, max_tokens)
                    responses.append(response)
                    total_time += time_ms
                    all_tokens["prompt_tokens"] += token_usage.get("prompt_tokens", 0) or 0
                    all_tokens["completion_tokens"] += token_usage.get("completion_tokens", 0) or 0
                    all_tokens["total_tokens"] += token_usage.get("total_tokens", 0) or 0
                
                # Aggregate results
                aggregated = process_self_consistency(
                    responses, 
                    feature_cols, 
                    top_n=self_consistency_top_n
                )
                
                results[model_name] = {
                    "response": aggregated.get("summary", ""),
                    "thinking_process": None,
                    "token_usage": all_tokens,
                    "time_ms": round(total_time, 2),
                    "time_formatted": _format_time(total_time),
                    "error": None,
                    "self_consistency": aggregated
                }
            else:
                # Standard single-run mode
                response, time_ms, thinking_process, token_usage = _query_llm(prompts, model_dict, max_tokens)
                
                results[model_name] = {
                    "response": response,
                    "thinking_process": thinking_process,
                    "token_usage": token_usage,
                    "time_ms": round(time_ms, 2),
                    "time_formatted": _format_time(time_ms),
                    "error": None
                }
            
            if needs_start_stop:
                _stop_model(model_name)
                
        except Exception as e:
            results[model_name] = {
                "response": None,
                "thinking_process": None,
                "token_usage": None,
                "time_ms": 0,
                "time_formatted": "0s",
                "error": str(e)
            }
            print(f"  Error: {e}")
            # Try to stop model even on error
            if needs_start_stop:
                _stop_model(model_name)
    
    # 9. Build output
    output = {
        "experiment_type": experiment_type,
        "config": {
            "chat": chat,
            "n_samples": n_samples,
            "n_shap_local": n_shap_local,
            "n_lime_local": n_lime_local,
            "self_consistency": self_consistency,
            "self_consistency_runs": self_consistency_runs if self_consistency else None,
            "self_consistency_top_n": self_consistency_top_n if self_consistency else None,
            "explain_message_tokens": explain_message_tokens,
            "random_seed": random_seed
        },
        "model_info": model_info,
        "column_description": columnDesc,
        "shap_global_raw": shap_results["shap_global_raw"],
        "shap_global_percentages": shap_results["shap_global_percentages"],
        "shap_local": shap_results["shap_local"],
        "lime_local": lime_local,
        "prompts": prompts_for_output,
        "results": results
    }
    
    # 10. Save if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"\nSaving results to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n=== Pipeline complete ===")
    return output


if __name__ == "__main__":
    # Example usage
    print("Use pipeline() function directly. See docstring for parameters.")
