"""
Run without_xai experiment on NSL_KDD intrusion detection dataset.
Calls pipeline.py with chat=True.
"""

import pandas as pd
import sys
sys.path.insert(0, '..')
from pipeline import pipeline

DATASET_PATH = "KDDTrain+_20Percent.txt"
OUTPUT_FILE = "resultados_without_xai_local.json"

COLUMN_DESCRIPTIONS = [
    "Connection duration in seconds",
    "Protocol type: ICMP=0, TCP=1, UDP=2",
    "Network service accessed (encoded, e.g., http=22, ftp_data=19, private=46)",
    "Connection flag/status: SF=9 (success), S0=5 (syn attack), REJ=1 (rejected), etc.",
    "Source bytes sent by origin host",
    "Destination bytes sent by target host",
    "Number of wrong fragments",
    "Number of hot indicators (suspicious access patterns)",
    "Whether user logged in: 0=no, 1=yes",
    "Number of compromised files",
    "Number of same-type connections in time window",
    "Number of same-service connections in time window",
    "TCP error rate (0.0-1.0)",
    "Same-service TCP error rate (0.0-1.0)",
    "Protocol error rate (0.0-1.0)",
]

TARGET_COL = "label"
CLASS_NAMES = ["Normal", "Attack"]


def preprocess_dataset(path):
    """Load and preprocess NSL_KDD dataset."""
    columns = [
        "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
        "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
        "num_compromised", "root_shell", "su_attempted", "num_root",
        "num_file_creations", "num_shells", "num_access_files",
        "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
        "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate",
        "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
        "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
        "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
        "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
        "dst_host_serror_rate", "dst_host_srv_serror_rate",
        "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
        "label", "difficulty_level"
    ]
    
    df = pd.read_csv(path, header=None)
    df.columns = columns
    
    print(f"Original shape: {df.shape}")
    
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True)
    
    print(f"After cleaning: {df.shape}")
    
    categorical_cols = ["protocol_type", "service", "flag"]
    for col in categorical_cols:
        df[col] = df[col].astype("category").cat.codes
    
    df["label"] = df["label"].apply(lambda x: 0 if x == "normal" else 1)
    
    selected_cols = [
        "duration", "protocol_type", "service", "flag", "src_bytes",
        "dst_bytes", "wrong_fragment", "hot", "logged_in", "num_compromised",
        "count", "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate",
        "label"
    ]
    df = df[selected_cols]
    
    print(f"Final shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    return df


def main():
    print("=" * 60)
    print("WITHOUT XAI EXPERIMENT - NSL_KDD Intrusion Detection")
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
        experiment_type="without_xai",
        chat=True,
        n_samples=20,
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