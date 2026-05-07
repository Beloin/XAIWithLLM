#!/usr/bin/env python
"""
Run with_xai experiment on Network_logs intrusion detection dataset.
Usage: python with_xai.py [input.json]
If no input file provided, uses default configuration.
"""

import sys

sys.path.insert(0, "..")

import pandas as pd
import json
from sklearn.preprocessing import LabelEncoder, StandardScaler

from pipeline import pipeline

DATASET_PATH = "Network_logs.csv"
DEFAULT_OUTPUT = "resultados_with_xai_default.json"


def preprocess_network_logs(filepath):
    """
    Preprocess Network_logs.csv for pipeline.

    Same preprocessing as in with_xai.ipynb:
    1. Drop IP columns
    2. Label encode categorical columns
    3. StandardScaler on Payload_Size
    4. Return preprocessed DataFrame AND class_names
    """
    print(f"Loading and preprocessing {filepath}...")

    df = pd.read_csv(filepath)

    # Drop IP columns
    df = df.drop(["Source_IP", "Destination_IP", "Intrusion"], axis=1, errors="ignore")

    # Label encode categorical columns
    categorical_cols = ["Request_Type", "Protocol", "User_Agent", "Status", "Port"]
    for col in categorical_cols:
        df[col] = df[col].astype("category").cat.codes

    # Encode target - KEEP CLASS NAMES
    target_encoder = LabelEncoder()
    df["Scan_Type_Label"] = target_encoder.fit_transform(df["Scan_Type"])
    class_names = list(target_encoder.classes_)  # BotAttack, Normal, PortScan
    df = df.drop("Scan_Type", axis=1)

    print(f"Classes: {class_names}")

    # Standardize Payload_Size
    scaler = StandardScaler()
    df["Payload_Size"] = scaler.fit_transform(df[["Payload_Size"]])

    print(f"Final shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    return df, class_names


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
    print("WITH XAI EXPERIMENT - Network Intrusion Detection Logs")
    print("=" * 60)

    df, class_names = preprocess_network_logs(DATASET_PATH)

    # Column descriptions
    columnDesc = [
        "Port number (encoded: 21=0, 22=1, 23=2, 25=3, 53=4, 80=5, 135=6, 443=7, 4444=8, 6667=9, 8080=10, 31337=11)",
        "Request type (DNS=0, FTP=1, HTTP=2, HTTPS=3, SMTP=4, SSH=5, Telnet=6)",
        "Transport protocol (ICMP=0, TCP=1, UDP=2)",
        "Packet payload size (StandardScaler normalized)",
        "Client agent (Mozilla=0, Nikto=1, Wget=2, curl=3, nmap=4, python-requests=5)",
        "Request status (Failure=0, Success=1)",
    ]

    # Build pipeline arguments from config or defaults
    if config:
        kwargs = {
            "dataset": df,
            "columnDesc": columnDesc,
            "target_col": "Scan_Type_Label",
            "class_names": class_names,
            "models": config.get(
                "models", [{"name": "glm-5:cloud", "api": "http://localhost:11434/v1"}]
            ),
            "experiment_type": config.get("experimentType", "with_xai"),
            "chat": config.get("chat", True),
            "n_samples": config.get("nSamples", 20),
            "n_shap_local": config.get("nShapLocal", 15),
            "n_lime_local": config.get("nLimeLocal", 15),
            "system_prompt": config.get("systemPrompt"),
            "task": config.get("task"),
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
            "columnDesc": columnDesc,
            "target_col": "Scan_Type_Label",
            "class_names": class_names,
            "models": [
                {"name": "glm-5:cloud", "api": "http://localhost:11434/v1"},
                {"name": "gpt-oss:20b", "api": "http://localhost:11434/v1"},
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