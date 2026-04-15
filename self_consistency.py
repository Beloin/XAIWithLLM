"""
Self-consistency module for aggregating LLM feature rankings.

When enabled, runs LLM multiple times and aggregates results to get
statistically robust feature importance rankings.
"""

import json
import re
from collections import Counter
from typing import List, Dict, Any, Optional


SELF_CONSISTENCY_PROMPT = """
Based on the model information and data provided, identify the top {top_n} most important features for detecting security threats.

IMPORTANT: Provide your response as a valid JSON array ONLY, with no additional text.

Format:
```json
[
  {{"name": "feature_name", "why": "Brief explanation of why this feature is important"}},
  {{"name": "feature_name", "why": "Brief explanation"}},
  ...
]
```

Example (do not use these values, analyze the actual data):
```json
[
  {{"name": "failed_logins", "why": "High number of failed login attempts indicates brute-force attack patterns"}},
  {{"name": "ip_reputation_score", "why": "Previously flagged IP addresses correlate strongly with malicious activity"}}
]
```

Now analyze and provide exactly {top_n} features in JSON format:
"""


def extract_json_from_response(response: str) -> Optional[List[Dict[str, str]]]:
    """Extract JSON array from LLM response, handling various formats."""
    
    # Try direct JSON parse first
    try:
        parsed = json.loads(response.strip())
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
    matches = re.findall(json_pattern, response)
    for match in matches:
        try:
            parsed = json.loads(match.strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Try finding JSON array pattern
    array_pattern = r'\[\s*\{.*?\}\s*(?:,\s*\{.*?\}\s*)*\]'
    matches = re.findall(array_pattern, response, re.DOTALL)
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    
    return None


def validate_feature_list(features: List[Dict[str, str]], valid_features: List[str]) -> List[Dict[str, str]]:
    """Validate and filter feature list against actual feature names."""
    
    validated = []
    for item in features:
        if not isinstance(item, dict):
            continue
        
        name = item.get("name", "")
        why = item.get("why", "")
        
        if not name or not why:
            continue
        
        # Normalize name (handle case, spaces, underscores)
        name_normalized = name.lower().replace(" ", "_").replace("-", "_")
        
        # Try to match with valid features
        matched = None
        for valid_name in valid_features:
            valid_normalized = valid_name.lower().replace(" ", "_").replace("-", "_")
            if name_normalized == valid_normalized or name_normalized in valid_normalized:
                matched = valid_name
                break
        
        if matched:
            validated.append({"name": matched, "why": why})
        elif name in valid_features:
            validated.append({"name": name, "why": why})
    
    return validated


def aggregate_rankings(
    all_results: List[List[Dict[str, str]]],
    valid_features: List[str],
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Aggregate feature rankings across multiple runs.
    
    Returns:
        {
            "features": [
                {
                    "rank": 1,
                    "name": "feature_name",
                    "percentage": 0.85,
                    "appearances": 17,
                    "total_runs": 20,
                    "explanations": ["explanation1", "explanation2", ...],
                    "consensus_explanation": "Most representative explanation"
                },
                ...
            ],
            "metadata": {
                "total_runs": 20,
                "valid_runs": 18,
                "invalid_runs": 2
            }
        }
    """
    
    # Validate and normalize all results
    validated_runs = []
    invalid_count = 0
    
    for run_result in all_results:
        if run_result is None:
            invalid_count += 1
            continue
        
        validated = validate_feature_list(run_result, valid_features)
        if len(validated) >= 1:  # At least one valid feature
            validated_runs.append(validated)
        else:
            invalid_count += 1
    
    if not validated_runs:
        return {
            "features": [],
            "metadata": {
                "total_runs": len(all_results),
                "valid_runs": 0,
                "invalid_runs": invalid_count,
                "error": "No valid feature rankings extracted from any run"
            }
        }
    
    # Count feature appearances
    feature_counts = Counter()
    feature_explanations: Dict[str, List[str]] = {}
    feature_positions = {}
    
    for run in validated_runs:
        for position, item in enumerate(run):
            name = item["name"]
            feature_counts[name] += 1
            
            # Track position (for average ranking)
            if name not in feature_positions:
                feature_positions[name] = []
            feature_positions[name].append(position + 1)
            
            # Track explanations
            if name not in feature_explanations:
                feature_explanations[name] = []
            feature_explanations[name].append(item["why"])
    
    # Calculate statistics
    total_valid_runs = len(validated_runs)
    
    feature_stats = []
    for name, count in feature_counts.most_common():
        percentage = count / total_valid_runs
        avg_position = sum(feature_positions[name]) / len(feature_positions[name])
        
        # Get most representative explanation (shortest, most complete)
        explanations = feature_explanations[name]
        consensus = max(explanations, key=lambda x: len(x)) if explanations else ""
        
        feature_stats.append({
            "name": name,
            "percentage": round(percentage, 4),
            "appearances": count,
            "avg_position": round(avg_position, 2),
            "explanations": explanations[:5],  # Keep up to 5 examples
            "consensus_explanation": consensus
        })
    
    # Sort by percentage (primary), then by avg_position (secondary)
    feature_stats.sort(key=lambda x: (-x["percentage"], x["avg_position"]))
    
    # Add rank
    features_with_rank = []
    for i, stat in enumerate(feature_stats[:top_n]):
        features_with_rank.append({
            "rank": i + 1,
            **stat
        })
    
    return {
        "features": features_with_rank,
        "metadata": {
            "total_runs": len(all_results),
            "valid_runs": total_valid_runs,
            "invalid_runs": invalid_count
        }
    }


def generate_consensus_summary(aggregated: Dict[str, Any]) -> str:
    """Generate human-readable summary of consensus results."""
    
    features = aggregated.get("features", [])
    metadata = aggregated.get("metadata", {})
    
    if not features:
        return f"No consensus reached. Valid runs: {metadata.get('valid_runs', 0)}/{metadata.get('total_runs', 0)}"
    
    lines = [f"Self-Consistency Results ({metadata.get('valid_runs', 0)}/{metadata.get('total_runs', 0)} valid runs)\n"]
    
    for feat in features:
        lines.append(f"{feat['rank']}. {feat['name']} - {feat['percentage']*100:.1f}% consensus")
        lines.append(f"   Why: {feat['consensus_explanation']}")
        lines.append("")
    
    return "\n".join(lines)


def process_self_consistency(
    responses: List[str],
    valid_features: List[str],
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Process multiple LLM responses for self-consistency analysis.
    
    Args:
        responses: List of raw LLM responses
        valid_features: List of valid feature names from dataset
        top_n: Number of top features to return
    
    Returns:
        Aggregated results dictionary
    """
    
    # Extract JSON from each response
    all_results = []
    for response in responses:
        extracted = extract_json_from_response(response)
        all_results.append(extracted)
    
    # Aggregate rankings
    aggregated = aggregate_rankings(all_results, valid_features, top_n)
    
    # Add human-readable summary
    aggregated["summary"] = generate_consensus_summary(aggregated)
    
    return aggregated


# For integration with pipeline.py
def build_self_consistency_prompt(top_n: int = 5) -> str:
    """Return the self-consistency prompt template."""
    return SELF_CONSISTENCY_PROMPT.format(top_n=top_n)


if __name__ == "__main__":
    # Test with sample responses
    test_responses = [
        '[{"name": "failed_logins", "why": "Multiple failed attempts indicate attack"}, {"name": "ip_reputation", "why": "Known bad IPs"}]',
        '```json\n[{"name": "failed_logins", "why": "High count means brute force"}, {"name": "login_attempts", "why": "Many attempts"}]\n```',
        'The top features are:\n[{"name": "failed_logins", "why": "Brute force detection"}, {"name": "session_duration", "why": "Long sessions suspicious"}]'
    ]
    
    valid_features = ["failed_logins", "login_attempts", "ip_reputation_score", "session_duration"]
    
    result = process_self_consistency(test_responses, valid_features, top_n=5)
    print(json.dumps(result, indent=2))