#!/usr/bin/env python
"""
Test script for with_xai experiment using the pipeline.

This script:
1. Preprocesses Network_logs.csv (same as the original notebook)
2. Calls pipeline() with experiment_type="with_xai"
3. Saves results to JSON
"""

import sys

sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE

from pipeline import pipeline


def preprocess_network_logs(filepath="../Network_logs.csv"):
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

    return df, class_names


def main():
    # Preprocess data
    df, class_names = preprocess_network_logs("Network_logs.csv")

    # Column descriptions (same as original notebook)
    columnDesc = [
        "Communication port (encoded: 21=0, 22=1, 23=2, 25=3, 53=4, 80=5, 135=6, 443=7, 4444=8, 6667=9, 8080=10, 31337=11)",
        "Request type (DNS=0, FTP=1, HTTP=2, HTTPS=3, SMTP=4, SSH=5, Telnet=6)",
        "Transport protocol (ICMP=0, TCP=1, UDP=2)",
        "Packet payload size (StandardScaler normalized)",
        "Client agent (Mozilla/5.0=0, Nikto/2.1.6=1, Wget/1.20.3=2, curl/7.68.0=3, nmap/7.80=4, python-requests/2.25.1=5)",
        "Request status (Failure=0, Success=1)",
    ]

    # Test with single model
    models = [
        {"name": "qwen3.5:cloud", "api": "http://localhost:11434/v1"},
        {"name": "deepseek-v3.2:cloud", "api": "http://localhost:11434/v1"},
    ]

    # Run pipeline
    print("\n" + "=" * 60)
    print("Running with_xai experiment")
    print("=" * 60)

    result = pipeline(
        dataset=df,
        columnDesc=columnDesc,
        models=models,
        experiment_type="with_xai",
        n_samples=20,
        n_shap_local=15,
        n_lime_local=15,
        target_col="Scan_Type_Label",
        class_names=class_names,  # Pass class names
        explain_message_tokens=8192,  # Smaller for testing
        random_seed=42,
        output_file=None,  # Don't save, print result
    )

    # Print results summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    print(f"\nExperiment: {result['experiment_type']}")
    print(f"Config: {result['config']}")
    print(f"\nModel accuracy: {result['model_info']['accuracy']:.4f}")
    print(f"Classes: {result['model_info']['classes']}")

    print("\nSHAP Global (raw):")
    for cls, feats in result["shap_global_raw"].items():
        top3 = sorted(feats.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  {cls}: {top3}")

    print("\nModel results:")
    for model_name, model_result in result["results"].items():
        if model_result.get("error"):
            print(f"  {model_name}: ERROR - {model_result['error']}")
        else:
            response = model_result.get("response", "")
            print(
                f"  {model_name}: {model_result['time_formatted']} ({model_result['time_ms']:.0f}ms) | {len(response)} chars"
            )
            # Print first 500 chars of response
            print(f"    Response preview: {response[:500]}...")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

    return result


if __name__ == "__main__":
    result = main()
