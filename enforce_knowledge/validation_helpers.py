"""
Shared validation helpers for enforce_knowledge experiment analysis.
Provides ground truth computation, automated text extraction, and scoring functions.
"""

import json
import re
import numpy as np
import pandas as pd
import shap
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from IPython.display import display, Markdown, HTML


# ── Ground truth ──────────────────────────────────────────────────────────────

def compute_ground_truth(csv_path="../Network_logs.csv"):
    """Recompute model + SHAP ground truth from the dataset."""
    df = pd.read_csv(csv_path)
    nd = df.copy()
    nd.drop(['Source_IP', 'Destination_IP', 'Intrusion'], axis=1, inplace=True)

    categorical_cols = ['Request_Type', 'Protocol', 'User_Agent', 'Status', 'Port']
    for col in categorical_cols:
        nd[col] = nd[col].astype('category').cat.codes

    target_encoder = LabelEncoder()
    nd['Scan_Type_Label'] = target_encoder.fit_transform(nd['Scan_Type'])
    nd.drop(['Scan_Type'], axis=1, inplace=True)

    scaler = StandardScaler()
    nd['Payload_Size'] = scaler.fit_transform(nd[['Payload_Size']])

    X = nd.drop(['Scan_Type_Label'], axis=1)
    y = nd['Scan_Type_Label']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    smote = SMOTE()
    X_train, y_train = smote.fit_resample(X_train, y_train)

    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    feature_names = list(X.columns)
    class_names = list(target_encoder.classes_)

    np.random.seed(42)
    sample_idx = np.random.choice(X_test.index, size=min(200, len(X_test)), replace=False)
    X_sample = X_test.loc[sample_idx]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Global SHAP ground truth
    shap_ground_truth = {}
    for cls_idx, cls_name in enumerate(class_names):
        mean_abs = np.abs(shap_values[:, :, cls_idx]).mean(axis=0)
        shap_ground_truth[cls_name] = {
            feat: round(float(val), 6) for feat, val in zip(feature_names, mean_abs)
        }

    # Rankings (feature names sorted descending by importance)
    shap_rankings = {}
    for cls_name in class_names:
        ranked = sorted(shap_ground_truth[cls_name].items(), key=lambda x: x[1], reverse=True)
        shap_rankings[cls_name] = [f[0] for f in ranked]

    accuracy = round(accuracy_score(y_test, y_pred), 4)

    return {
        "shap_ground_truth": shap_ground_truth,
        "shap_rankings": shap_rankings,
        "feature_names": feature_names,
        "class_names": class_names,
        "accuracy": accuracy,
        "y_test": y_test,
        "y_pred": y_pred,
    }


# ── Feature ranking extraction from text ──────────────────────────────────────

FEATURE_ALIASES = {
    "port": "Port",
    "port number": "Port",
    "port_number": "Port",
    "status": "Status",
    "request status": "Status",
    "payload_size": "Payload_Size",
    "payload size": "Payload_Size",
    "payloadsize": "Payload_Size",
    "payload": "Payload_Size",
    "user_agent": "User_Agent",
    "user agent": "User_Agent",
    "useragent": "User_Agent",
    "request_type": "Request_Type",
    "request type": "Request_Type",
    "requesttype": "Request_Type",
    "protocol": "Protocol",
}

VALID_FEATURES = {"Port", "Status", "Payload_Size", "User_Agent", "Request_Type", "Protocol"}


def _normalize_feature(name):
    """Normalize a feature name to its canonical form."""
    key = name.strip().lower().replace("**", "").replace("`", "").replace("*", "")
    return FEATURE_ALIASES.get(key, name.strip())


def extract_top_features_for_class(text, class_name, top_n=3):
    """
    Try to extract top-N features mentioned for a specific class from LLM text.
    Uses multiple heuristic patterns. Returns list of canonical feature names.
    """
    features_found = []

    # Pattern 1: Numbered list with class context - "1. Port (0.26)" or "1. **Port**"
    # Look in a window around where the class name appears
    class_sections = []
    for match in re.finditer(rf'(?i){re.escape(class_name)}', text):
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 1500)
        class_sections.append(text[start:end])

    for section in class_sections:
        # Pattern: "1. Feature" or "1. **Feature**"
        ranked = re.findall(
            r'(?:^|\n)\s*\d+\.\s*\*{0,2}([\w_/ ]+?)\*{0,2}\s*(?:\(|:|\s*[-–—])',
            section
        )
        for feat in ranked:
            norm = _normalize_feature(feat)
            if norm in VALID_FEATURES and norm not in features_found:
                features_found.append(norm)

    if len(features_found) >= top_n:
        return features_found[:top_n]

    # Pattern 2: SHAP table rows "Port 0.26" or "**Port** 0.2603"
    for section in class_sections:
        rows = re.findall(
            r'\*{0,2}([\w_]+)\*{0,2}\s*(?:\||\s)\s*(\d+\.\d+)',
            section
        )
        for feat_name, val in rows:
            norm = _normalize_feature(feat_name)
            if norm in VALID_FEATURES and norm not in features_found:
                features_found.append(norm)

    if len(features_found) >= top_n:
        return features_found[:top_n]

    # Pattern 3: "Feature > Feature > Feature" pattern
    gt_pattern = re.findall(
        r'([\w_]+)\s*[>→]\s*([\w_]+)\s*[>→]\s*([\w_]+)',
        text
    )
    for triple in gt_pattern:
        for feat in triple:
            norm = _normalize_feature(feat)
            if norm in VALID_FEATURES and norm not in features_found:
                features_found.append(norm)

    return features_found[:top_n]


def extract_all_rankings(text, class_names, top_n=3):
    """Extract top-N feature rankings for all classes from a response."""
    rankings = {}
    for cls in class_names:
        rankings[cls] = extract_top_features_for_class(text, cls, top_n)
    return rankings


# ── SHAP value extraction ─────────────────────────────────────────────────────

def extract_shap_values(text, class_names):
    """
    Extract SHAP numeric values cited in the text for each class.
    Returns {class_name: {feature: cited_value}}.
    """
    cited = {cls: {} for cls in class_names}

    for cls_name in class_names:
        # Find sections about this class
        class_sections = []
        for match in re.finditer(rf'(?i){re.escape(cls_name)}', text):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 800)
            class_sections.append(text[start:end])

        for section in class_sections:
            # Pattern: "Feature (0.2603)" or "Feature: 0.2603" or "Feature 0.2603"
            matches = re.findall(
                r'\*{0,2}([\w_]+)\*{0,2}\s*(?:\(|\:|=|SHAP:?\s*)\s*(\d+\.\d{2,6})',
                section
            )
            for feat_name, val in matches:
                norm = _normalize_feature(feat_name)
                if norm in VALID_FEATURES and norm not in cited[cls_name]:
                    cited[cls_name][norm] = float(val)

            # Pattern: "0.2603 for Feature" or "0.2603 (Feature)"
            matches2 = re.findall(
                r'(\d+\.\d{2,6})\s*(?:for|→|\()\s*\*{0,2}([\w_]+)\*{0,2}',
                section
            )
            for val, feat_name in matches2:
                norm = _normalize_feature(feat_name)
                if norm in VALID_FEATURES and norm not in cited[cls_name]:
                    cited[cls_name][norm] = float(val)

    return cited


def score_shap_citations(cited, ground_truth, class_names):
    """Compare cited SHAP values against ground truth. Returns list of check dicts."""
    checks = []
    for cls in class_names:
        for feat, cited_val in cited[cls].items():
            gt_val = ground_truth[cls].get(feat, None)
            if gt_val is None:
                continue
            abs_err = abs(cited_val - gt_val)
            status = "EXACT" if abs_err < 0.005 else "CLOSE" if abs_err < 0.02 else "OFF"
            checks.append({
                "class": cls,
                "feature": feat,
                "cited": round(cited_val, 4),
                "actual": round(gt_val, 4),
                "abs_error": round(abs_err, 4),
                "status": status,
            })
    return checks


# ── Fabrication detection ─────────────────────────────────────────────────────

def check_user_agent_overvaluation(text):
    """
    Check if the text places User_Agent as a top-3 feature or calls it
    'highly important', 'critical', etc. Ground truth: User_Agent SHAP < 0.006.
    """
    patterns = [
        r'(?i)user.?agent.*(?:most|highly|critical|dominant|primary|key|top|#1|#2|#3)',
        r'(?i)(?:most|highly|critical|dominant|primary|key|#1|#2).*user.?agent',
        r'(?i)1\.\s*\*{0,2}user.?agent',
        r'(?i)2\.\s*\*{0,2}user.?agent',
        r'(?i)3\.\s*\*{0,2}user.?agent',
        r'(?i)user.?agent\s*\((?:highest|high)\s*impact',
    ]
    hits = []
    for p in patterns:
        for m in re.finditer(p, text):
            context_start = max(0, m.start() - 30)
            context_end = min(len(text), m.end() + 30)
            hits.append(text[context_start:context_end].strip())
    return hits


def check_fabricated_misclassifications(text, n_samples):
    """
    Check if the LLM claims to find misclassifications.
    In the enforce_knowledge experiment, samples are representative - the LLM
    may or may not see misclassifications depending on the random sample.
    Returns list of suspicious claims.
    """
    patterns = [
        r'(?i)(?:false positive|false negative|misclassif|incorrect(?:ly)? (?:predict|classif))',
        r'(?i)(?:predicted as|classified as).*(?:but|however|actually|real)',
        r'(?i)(?:error|mistake|wrong).*(?:classif|predict)',
    ]
    hits = []
    for p in patterns:
        for m in re.finditer(p, text):
            context_start = max(0, m.start() - 60)
            context_end = min(len(text), m.end() + 60)
            hits.append(text[context_start:context_end].strip())
    return hits


def check_fabricated_percentages(text):
    """
    Check if the LLM invents percentage-based feature importance without
    SHAP data (Phase 1). Patterns like 'User_Agent (72%)' are fabrications.
    """
    pattern = r'([\w_]+)\s*\(?\s*(\d{1,3})%\s*\)?'
    hits = []
    for m in re.finditer(pattern, text):
        feat_name = _normalize_feature(m.group(1))
        pct = int(m.group(2))
        if feat_name in VALID_FEATURES and 5 < pct < 100:
            context_start = max(0, m.start() - 40)
            context_end = min(len(text), m.end() + 40)
            hits.append({
                "feature": feat_name,
                "percentage": pct,
                "context": text[context_start:context_end].strip(),
            })
    return hits


# ── Ranking accuracy scoring ──────────────────────────────────────────────────

def ranking_accuracy(predicted_rankings, ground_truth_rankings, class_names, top_n=3):
    """
    Compute fraction of correct top-N position matches across all classes.
    Returns (correct, total, per_class_dict).
    """
    correct = 0
    total = 0
    per_class = {}
    for cls in class_names:
        gt = ground_truth_rankings[cls][:top_n]
        pr = predicted_rankings.get(cls, [])
        matches = 0
        for i in range(min(top_n, len(pr))):
            if i < len(gt) and gt[i] == pr[i]:
                matches += 1
        total += top_n
        correct += matches
        per_class[cls] = {"matches": matches, "total": top_n, "gt": gt, "predicted": pr}
    return correct, total, per_class


def ranking_top3_set_overlap(predicted_rankings, ground_truth_rankings, class_names):
    """
    Compute set overlap (ignoring order) of top-3 features.
    More lenient than position matching.
    """
    correct = 0
    total = 0
    for cls in class_names:
        gt_set = set(ground_truth_rankings[cls][:3])
        pr_set = set(predicted_rankings.get(cls, [])[:3])
        overlap = len(gt_set & pr_set)
        correct += overlap
        total += 3
    return correct, total


# ── Display helpers ───────────────────────────────────────────────────────────

def display_response(model_name, phase, text):
    """Pretty-print an LLM response."""
    phase_label = "Phase 1: Without XAI" if phase == "phase1" else "Phase 2: With XAI (SHAP + LIME)"
    display(Markdown(f"---\n### {model_name} — {phase_label}\n*({len(text)} chars)*\n\n{text}"))


def display_ranking_comparison(model_name, phase_label, predicted, ground_truth, class_names):
    """Display a comparison table of predicted vs ground truth rankings."""
    rows = []
    for cls in class_names:
        gt = ground_truth[cls][:3]
        pr = predicted.get(cls, ["?", "?", "?"])
        pr_padded = pr + ["?"] * (3 - len(pr))
        matches = sum(1 for i in range(3) if i < len(pr) and gt[i] == pr[i])
        rows.append({
            "Class": cls,
            "Ground Truth": " > ".join(gt),
            f"{phase_label} Ranking": " > ".join(pr_padded[:3]),
            "Position Matches": f"{matches}/3",
        })
    display(pd.DataFrame(rows).set_index("Class"))


def summary_table(all_scores):
    """
    Build a summary DataFrame from a list of score dicts:
    [{model, phase, ranking_acc, set_overlap, n_ua_overval, n_fabricated_pct, n_shap_exact, ...}]
    """
    return pd.DataFrame(all_scores)
