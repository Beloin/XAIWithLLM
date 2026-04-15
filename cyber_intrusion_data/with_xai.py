"""
Run with_xai experiment on cybersecurity intrusion detection dataset.
Usage: python with_xai.py [input.json]
If no input file provided, uses default configuration.
"""

import pandas as pd
import json
import sys
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, "..")
from pipeline import pipeline

DATASET_PATH = "cybersecurity_intrusion_data.csv"
DEFAULT_OUTPUT = "resultados_with_xai_default.json"

COLUMN_DESCRIPTIONS = [
    "Network packet size in bytes (standardized, mean=0, std=1)",
    "Network protocol type: ICMP=0, TCP=1, UDP=2",
    "Number of login attempts in the session",
    "Session duration in seconds (standardized, mean=0, std=1)",
    "Encryption method used: AES=0, DES=1",
    "IP reputation score (0.0-1.0, higher = more suspicious)",
    "Number of failed login attempts",
    "Browser/client type: Chrome=0, Edge=1, Firefox=2, Safari=3, Unknown=4",
    "Whether access occurred at unusual time (0=normal, 1=unusual)",
]

TARGET_COL = "attack_detected"
CLASS_NAMES = ["Normal", "Attack"]


def preprocess_dataset(path):
    """Load and preprocess dataset following notebook steps."""
    df = pd.read_csv(path)

    print(f"Original shape: {df.shape}")

    df.drop(columns=["session_id"], inplace=True)
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True)

    print(f"After cleaning: {df.shape}")

    categorical_cols = ["protocol_type", "encryption_used", "browser_type"]
    for col in categorical_cols:
        df[col] = df[col].astype("category").cat.codes

    scaler = StandardScaler()
    df[["network_packet_size", "session_duration"]] = scaler.fit_transform(
        df[["network_packet_size", "session_duration"]]
    )

    print(f"Final shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    return df


def load_input_config(input_path):
    """Load configuration from JSON input file."""
    with open(input_path, "r") as f:
        config = json.load(f)
    return config


def main():
    # Check for input file argument
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        print(f"Loading configuration from: {input_path}")
        config = load_input_config(input_path)
    else:
        print("No input file provided, using default configuration")
        config = None

    print("=" * 60)
    print("WITH XAI EXPERIMENT - Cybersecurity Intrusion Detection")
    print("=" * 60)

    df = preprocess_dataset(DATASET_PATH)

    # Build pipeline arguments from config or defaults
    if config:
        kwargs = {
            "dataset": df,
            "columnDesc": COLUMN_DESCRIPTIONS,
            "target_col": TARGET_COL,
            "class_names": CLASS_NAMES,
            "models": config.get(
                "models", [{"name": "glm-5:cloud", "api": "http://localhost:11434/v1"}]
            ),
            "experiment_type": config.get("experimentType", "with_xai"),
            "chat": config.get("chat", True),
            "n_samples": config.get("nSamples", 20),
            "n_shap_local": config.get("nShapLocal", 15),
            "n_lime_local": config.get("nLimeLocal", 15),
            "system_prompt": config.get("systemPrompt"),
            "self_consistency": config.get("selfConsistency", False),
            "self_consistency_runs": config.get("selfConsistencyRuns", 5),
            "self_consistency_top_n": config.get("selfConsistencyTopN", 5),
            "explain_message_tokens": config.get("explainMessageTokens", 12288),
            "random_seed": config.get("randomSeed", 42),
            "output_file": config.get("outputFile", DEFAULT_OUTPUT),
        }
    else:
        kwargs = {
            "dataset": df,
            "columnDesc": COLUMN_DESCRIPTIONS,
            "target_col": TARGET_COL,
            "class_names": CLASS_NAMES,
            "models": [
                {"name": "glm-4.7-flash", "api": "http://localhost:11434/v1"},
                {"name": "qwen3:14b", "api": "http://localhost:11434/v1"},
                {"name": "gpt-oss:20b", "api": "http://localhost:11434/v1"},
                {"name": "qwen3:30b", "api": "http://localhost:11434/v1"},
                {"name": "glm-5:cloud", "api": "http://localhost:11434/v1"},
            ],
            "experiment_type": "with_xai",
            "chat": True,
            "n_samples": 20,
            "n_shap_local": 15,
            "n_lime_local": 15,
            "explain_message_tokens": 12288,
            "random_seed": 42,
            "output_file": DEFAULT_OUTPUT,
        }

    result = pipeline(**kwargs)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    output_file = kwargs.get("output_file", DEFAULT_OUTPUT)

    for model_name, model_result in result["results"].items():
        print(f"\n{model_name}:")
        print(f"  Time: {model_result['time_formatted']}")
        print(f"  Error: {model_result['error']}")

        if model_result.get("self_consistency"):
            sc = model_result["self_consistency"]
            print(
                f"  Self-Consistency: {sc.get('metadata', {}).get('valid_runs', 0)} valid runs"
            )
            for feat in sc.get("features", []):
                print(
                    f"    {feat['rank']}. {feat['name']} - {feat['percentage'] * 100:.1f}%"
                )
        elif model_result["response"]:
            response = model_result["response"]
            print(f"  Response length: {len(response)} chars")
            print(f"\n--- Response Preview (first 500 chars) ---")
            print(response[:500])
            print("...\n")
        else:
            print("  Response: None")

    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    main()

