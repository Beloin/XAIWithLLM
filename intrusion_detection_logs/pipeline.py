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
from typing import Literal

import numpy as np
import pandas as pd
import shap
from lime import lime_tabular
from openai import OpenAI
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


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
    """Query LLM via OpenAI-compatible API."""
    client = OpenAI(
        base_url=model_dict["api"],
        api_key=model_dict.get("api_key", "ollama")
    )
    
    model_name = model_dict["name"]
    
    if isinstance(prompts, str):
        start = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompts}],
            max_tokens=max_tokens,
            timeout=timeout
        )
        elapsed_ms = (time.time() - start) * 1000
        return response.choices[0].message.content, elapsed_ms
    
    else:
        chat_history = []
        responses = []
        total_time = 0
        
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
            
            content = response.choices[0].message.content
            chat_history.append({"role": "assistant", "content": content})
            responses.append(content)
        
        return responses[-1], total_time


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

You will analyze a network intrusion detection model that has already been fully validated through a complete data science pipeline.

# Model Information

- **Type:** {model_info['type']}
- **Task:** Network intrusion detection from log entries
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

2. **Class-Specific Patterns:** For each class (BotAttack, Normal, PortScan), describe what patterns the model looks for.

3. **Misclassification Risk:** What might cause this model to misclassify? Consider edge cases and class confusion.

4. **Security Implications:** How would a SOC analyst use these insights? What detection rules would you derive?

Be precise and ground your reasoning in the data samples provided. Do NOT fabricate statistics or metrics that weren't explicitly given.
"""
    return prompt


def _build_prompt_with_xai(model_info, column_desc_str, train_sample_str, pred_sample_str, 
                           shap_global_str, shap_local_str, lime_local_str, feature_cols, class_names):
    """Build prompt for with_xai experiment."""
    
    prompt = f"""You are an expert in Machine Learning, Explainable AI, and Cybersecurity.

You will analyze a network intrusion detection model that has already been fully validated through a complete data science pipeline.

# Model Information

- **Type:** {model_info['type']}
- **Task:** Network intrusion detection from log entries
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

1. **Feature Importance:** Using SHAP global values, rank the top 3 features for each class. Explain why these features have the highest impact.

2. **Class-Specific Patterns:** For each class, describe how the model distinguishes it from others. Reference specific SHAP values and LIME rules.

3. **Comparing SHAP and LIME:** Do the explanations converge? Where do they differ? Which features are consistently important?

4. **Security Implications:** What detection rules would you recommend for a SOC analyst? Be specific about thresholds and conditions.

Cite the SHAP values and LIME rules in your explanation. Be precise and avoid fabrication.
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


# ===== MAIN PIPELINE =====

def pipeline(
    dataset,
    columnDesc,
    models=None,
    experiment_type="with_xai",
    n_samples=20,
    n_shap_local=20,
    n_lime_local=20,
    target_col=None,
    class_names=None,
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
        n_samples: Number of train/pred samples to show LLM
        n_shap_local: Number of SHAP local instances
        n_lime_local: Number of LIME local instances
        target_col: Target column name (required)
        class_names: List of class names. If None, inferred from target values (default: class_0, class_1, ...)
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
    
    if experiment_type == "without_xai":
        prompts = _build_prompt_without_xai(
            model_info, column_desc_str, train_sample_str, pred_sample_str, 
            feature_cols, class_names
        )
        max_tokens = explain_message_tokens
        prompts_for_output = {"prompt": prompts}
    
    elif experiment_type == "with_xai":
        shap_global_str = json.dumps(shap_results["shap_global_raw"], indent=2, ensure_ascii=False)
        shap_local_str = json.dumps(shap_results["shap_local"], indent=2, ensure_ascii=False)
        lime_local_str = json.dumps(lime_local, indent=2, ensure_ascii=False)
        
        prompts = _build_prompt_with_xai(
            model_info, column_desc_str, train_sample_str, pred_sample_str,
            shap_global_str, shap_local_str, lime_local_str,
            feature_cols, class_names
        )
        max_tokens = explain_message_tokens
        prompts_for_output = {"prompt": prompts}
    
    elif experiment_type == "enforce_knowledge":
        shap_global_str = json.dumps(shap_results["shap_global_raw"], indent=2, ensure_ascii=False)
        shap_local_str = json.dumps(shap_results["shap_local"], indent=2, ensure_ascii=False)
        lime_local_str = json.dumps(lime_local, indent=2, ensure_ascii=False)
        
        prompts = _build_prompts_enforce_knowledge(
            model_info, column_desc_str, train_sample_str, pred_sample_str,
            feature_cols, class_names,
            shap_global_str, shap_local_str, lime_local_str
        )
        max_tokens = [PHASE1_MAX_TOKENS, explain_message_tokens]
        prompts_for_output = {"phase1": prompts[0], "phase2": prompts[1]}
    
    else:
        raise ValueError(f"Invalid experiment_type: {experiment_type}. Must be 'with_xai', 'without_xai', or 'enforce_knowledge'")
    
    # 8. Query models
    results = {}
    for i, model_dict in enumerate(models):
        model_name = model_dict["name"]
        print(f"\n[{i+1}/{len(models)}] Querying {model_name}...")
        
        try:
            needs_start_stop = _needs_model_start_stop(model_dict)
            
            if needs_start_stop:
                _start_model(model_name)
            
            response, time_ms = _query_llm(prompts, model_dict, max_tokens)
            
            results[model_name] = {
                "response": response,
                "time_ms": round(time_ms, 2),
                "time_formatted": _format_time(time_ms),
                "error": None
            }
            
            if needs_start_stop:
                _stop_model(model_name)
                
        except Exception as e:
            results[model_name] = {
                "response": None,
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
            "n_samples": n_samples,
            "n_shap_local": n_shap_local,
            "n_lime_local": n_lime_local,
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