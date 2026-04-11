"""
Run enforce_knowledge experiment on cybersecurity intrusion detection dataset.
Calls pipeline.py with chat=True.
"""

import pandas as pd
from sklearn.preprocessing import StandardScaler
import sys
sys.path.insert(0, '..')
from pipeline import pipeline

DATASET_PATH = "cybersecurity_intrusion_data.csv"
OUTPUT_FILE = "resultados_enforce_knowledge_local.json"

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


def main():
    print("=" * 60)
    print("ENFORCE KNOWLEDGE EXPERIMENT - Cybersecurity Intrusion Detection")
    print("=" * 60)
    
    df = preprocess_dataset(DATASET_PATH)
    
    result = pipeline(
        dataset=df,
        columnDesc=COLUMN_DESCRIPTIONS,
        target_col=TARGET_COL,
        class_names=CLASS_NAMES,
        models=[
            {"name": "glm-4.7-flash", "api": "http://localhost:11434/v1"},
            {"name": "qwen3:14b", "api": "http://localhost:11434/v1"},
            {"name": "gpt-oss:20b", "api": "http://localhost:11434/v1"},
            {"name": "qwen3:30b", "api": "http://localhost:11434/v1"},
            {"name": "glm-5:cloud", "api": "http://localhost:11434/v1"},
        ],
        experiment_type="enforce_knowledge",
        chat=True,
        n_samples=20,
        n_shap_local=15,
        n_lime_local=15,
        explain_message_tokens=12288,
        random_seed=42,
        output_file=OUTPUT_FILE
    )
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for model_name, model_result in result["results"].items():
        print(f"\n{model_name}:")
        print(f"  Time: {model_result['time_formatted']}")
        print(f"  Error: {model_result['error']}")
        
        if model_result["response"]:
            response = model_result["response"]
            print(f"  Response length: {len(response)} chars")
            print(f"\n--- Response Preview (first 500 chars) ---")
            print(response[:500])
            print("...\n")
        else:
            print("  Response: None")
    
    print(f"\nFull results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()