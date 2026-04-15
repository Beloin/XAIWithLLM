# Prompt Engineering Techniques for XAI Pipeline

This document outlines prompt engineering techniques from Google's Prompt Engineering guide and how to apply them to our ML explainability codebase.

---

## 1. System Prompt Customization

### Technique
System prompts set the persona, context, and behavioral guidelines for the LLM before presenting task-specific content.

### Current Implementation
```python
# Default in pipeline.py
"You are an expert in Machine Learning, Explainable AI, and Cybersecurity."
```

### Enhancement Techniques

#### A. Role-Based Prompting
```python
system_prompt = """You are a senior security operations center (SOC) analyst with 15 years of experience in network intrusion detection. 
You specialize in explaining machine learning model decisions to non-technical stakeholders.
Your explanations should:
- Prioritize actionable detection rules
- Quantify risk levels when possible
- Reference industry frameworks (MITRE ATT&CK, NIST)
- Avoid technical jargon unless necessary"""
```

#### B. Constraint-Based Prompting
```python
system_prompt = """You are an expert in ML explainability. 

CONSTRAINTS:
1. NEVER fabricate statistics or metrics not explicitly provided
2. ALWAYS cite specific SHAP values when discussing feature importance
3. LIMIT responses to 500 words for executive summaries
4. INCLUDE error rate context when discussing accuracy
5. AVOID speculation beyond the provided data"""
```

#### C. Audience-Specific Prompting
```python
# For executive audience
system_prompt_executive = """You are a technical advisor explaining ML model behavior to C-suite executives.
Focus on business impact, risk quantification, and decision-relevant insights.
Avoid mathematical notation. Use analogies and real-world examples."""

# For technical audience
system_prompt_technical = """You are an ML engineer explaining model behavior to data scientists.
Include technical details, potential hyperparameter implications, and implementation considerations.
Reference SHAP values with precise numerical citations."""
```

---

## 2. Few-Shot Prompting

### Technique
Provide examples of desired input-output pairs to guide the model's response format and reasoning pattern.

### Current Implementation
We provide training samples and predictions but no example explanations.

### Enhancement
```python
# Add to prompt building function
FEW_SHOT_EXAMPLES = """
# Example Explanation (follow this pattern):

**Feature Importance for BotAttack class:**
- `failed_logins` (SHAP: 0.179) - PRIMARY: Consistent with brute-force attack patterns
- `login_attempts` (SHAP: 0.125) - SECONDARY: Correlates with credential stuffing
- `ip_reputation_score` (SHAP: 0.092) - TERTIARY: Prior threat intelligence correlation

**Instance-Specific Insights:**
For instance with failed_logins=3, login_attempts=7:
- LIME rule: `failed_logins > 2.0` contributes +0.42 to attack prediction
- SHAP contribution: failed_logins adds +0.31 to attack probability

**Detection Rule Recommendation:**
IF failed_logins > 2 AND login_attempts > 5 THEN flag for investigation (confidence: 87%)

---
Now analyze the provided model following this pattern:
"""
```

### Implementation
```python
def _add_few_shot_examples(prompt, example_type="standard"):
    """Add few-shot examples to prompt."""
    examples = {
        "standard": FEW_SHOT_EXAMPLES,
        "concise": FEW_SHOT_CONCISE,
        "detailed": FEW_SHOT_DETAILED
    }
    return prompt + "\n\n" + examples.get(example_type, FEW_SHOT_EXAMPLES)
```

---

## 3. Chain-of-Thought (CoT) Prompting

### Technique
Explicitly ask the model to show its reasoning process step-by-step.

### Current Implementation
We ask for analysis but don't explicitly prompt for step-by-step reasoning.

### Enhancement
```python
COT_INSTRUCTION = """
Before providing your final analysis, show your reasoning process:

STEP 1: Identify the top 3 features from SHAP global importance for each class.
STEP 2: For each top feature, examine the SHAP local values across instances.
STEP 3: Compare SHAP rankings with LIME local explanations for consistency.
STEP 4: Identify any discrepancies between SHAP and LIME.
STEP 5: Synthesize findings into actionable detection rules.

Format each step with bullet points before your final synthesis.
"""
```

### For Thinking Models
```python
# Models like glm-5:cloud that support "thinking"
# The thinking_process is already captured, but we can enhance with:
COT_THINKING_PROMPT = """
Think through this analysis systematically:
1. What are the top features by SHAP importance?
2. How do local SHAP values vary across instances?
3. Are there patterns in the LIME explanations?
4. What contradictions exist between global and local explanations?
5. What security insights emerge from the convergence of explanations?

After thinking, provide a structured analysis.
"""
```

---

## 4. Self-Consistency Prompting

### Technique
Run the same prompt multiple times and aggregate responses for more robust outputs.

### Implementation
```python
def pipeline_with_self_consistency(
    dataset,
    columnDesc,
    n_runs=3,
    aggregation="voting",  # or "consensus", "detailed"
    **kwargs
):
    """Run pipeline multiple times and aggregate results."""
    
    results = []
    for i in range(n_runs):
        result = pipeline(
            dataset=dataset,
            columnDesc=columnDesc,
            **kwargs
        )
        results.append(result)
    
    # Aggregate feature rankings
    if aggregation == "voting":
        return _vote_on_features(results)
    elif aggregation == "consensus":
        return _find_consensus(results)
    else:
        return _detailed_comparison(results)
```

---

## 5. Structured Output Prompting

### Technique
Request specific output format (JSON, tables, structured sections) for easier parsing and analysis.

### Current Implementation
We ask for structured sections but output is free-form text.

### Enhancement
```python
STRUCTURED_OUTPUT_INSTRUCTION = """
Provide your analysis in the following JSON structure:

```json
{
  "feature_importance": {
    "class_0": [
      {"feature": "feature_name", "shap_value": 0.XXX, "rank": 1},
      ...
    ],
    "class_1": [...]
  },
  "detection_rules": [
    {
      "rule_id": "R1",
      "condition": "IF X > threshold AND Y < threshold",
      "target_class": "Attack",
      "confidence": 0.XX
    }
  ],
  "key_insights": [
    "Insight 1...",
    "Insight 2..."
  ],
  "limitations": [
    "Limitation 1..."
  ]
}
```

Ensure valid JSON format.
"""
```

---

## 6. Iterative Refinement (Enforce Knowledge Pattern)

### Technique
Already implemented! Our `enforce_knowledge` experiment type uses two-phase prompting:
- Phase 1: Initial analysis without XAI
- Phase 2: Revise with XAI data

### Enhancement - Add Self-Correction
```python
SELF_CORRECTION_PROMPT = """
You previously analyzed this model without XAI explanations. Now review your initial analysis:

Previous claims:
{previous_response}

XAI Evidence:
{shap_lime_data}

For each claim in your previous response:
1. If SUPPORTED by XAI: Mark as [VERIFIED]
2. If CONTRADICTED by XAI: Mark as [CORRECTED] and explain the error
3. If NOT MENTIONED in XAI: Mark as [UNVERIFIABLE]

Provide a revised analysis acknowledging corrections.
"""
```

---

## 7. Context Window Management

### Technique
Optimize prompt length for token limits, prioritize critical information, use chunking.

### Current Implementation
`chat=True` splits prompts into chunks with "Wait for further instructions" between them.

### Enhancement - Adaptive Chunking
```python
def _adaptive_chunk_prompts(content, max_tokens_per_chunk=4000):
    """Intelligently split content by semantic boundaries."""
    sections = [
        ("model_info", model_info_str),
        ("column_descriptions", column_desc_str),
        ("training_samples", train_sample_str),
        ("xai_data", xai_str),
        ("analysis_request", analysis_prompt)
    ]
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for section_name, section_content in sections:
        section_tokens = count_tokens(section_content)
        if current_tokens + section_tokens > max_tokens_per_chunk:
            chunks.append(current_chunk)
            current_chunk = section_content
            current_tokens = section_tokens
        else:
            current_chunk += "\n\n" + section_content
            current_tokens += section_tokens
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
```

---

## 8. Negative Constraints

### Technique
Tell the model what NOT to do to prevent hallucinations and unwanted behaviors.

### Enhancement
```python
NEGATIVE_CONSTRAINTS = """
IMPORTANT RESTRICTIONS:
- Do NOT invent feature importance values not in the SHAP data
- Do NOT claim model accuracy figures not explicitly stated
- Do NOT suggest the model is perfect (accuracy is {accuracy:.2%})
- Do NOT recommend actions beyond the scope of the provided data
- Do NOT reference features not in the provided feature list
- Do NOT compare with models not mentioned in this analysis
"""
```

---

## 9. Temperature and Sampling Control

### Technique
Adjust temperature and other sampling parameters for deterministic vs. creative outputs.

### Implementation
```python
def _query_llm(prompts, model_dict, max_tokens, temperature=0.1, ...):
    """Query LLM with temperature control."""
    response = client.chat.completions.create(
        model=model_name,
        messages=chat_history,
        max_tokens=tokens,
        temperature=temperature,  # Lower = more deterministic
        timeout=timeout
    )
```

### Recommended Settings by Experiment Type

| Experiment | Temperature | Reason |
|------------|------------|--------|
| without_xai | 0.3 | Allow some reasoning variety |
| with_xai | 0.1 | Stick close to XAI evidence |
| enforce_knowledge | 0.1 | Precise corrections |

---

## 10. Prompt Template Variations by Dataset

### Technique
Customize prompts based on domain/context.

### Implementation
```python
DATASET_PROMPTS = {
    "intrusion_detection": {
        "system": "You are an expert in network security and intrusion detection systems...",
        "domain_context": "Network intrusion detection analyzes connection logs to identify malicious activity...",
    },
    "credit_fraud": {
        "system": "You are an expert in financial fraud detection...",
        "domain_context": "Credit card fraud detection analyzes transaction patterns...",
    },
    "custom": {
        "system": None,  # User provides
        "domain_context": None
    }
}

def pipeline(
    dataset,
    columnDesc,
    domain="intrusion_detection",  # NEW PARAMETER
    system_prompt=None,  # Override default
    ...
):
    if system_prompt is None:
        system_prompt = DATASET_PROMPTS[domain]["system"]
```

---

## Application Examples

### Example 1: Enhanced Security Analyst Persona
```python
result = pipeline(
    dataset="network_logs.csv",
    columnDesc=["Port number", "Protocol type", ...],
    target_col="label",
    system_prompt="""You are a senior SOC analyst specializing in ML-based intrusion detection.
    
Your role is to translate model behavior into operational detection rules.
    
When analyzing:
1. Quantify risk levels (Critical/High/Medium/Low) based on SHAP values
2. Reference MITRE ATT&CK techniques where applicable
3. Prioritize findings by detection confidence
4. Provide specific threshold recommendations
    
Format: Executive summary (3 sentences) → Technical analysis → Detection rules""",
    experiment_type="with_xai",
    ...
)
```

### Example 2: Chain-of-Thought with Self-Consistency
```python
# Run 3 times with CoT
results = []
for i in range(3):
    result = pipeline(
        dataset=dataset,
        columnDesc=columnDesc,
        target_col="label",
        experiment_type="with_xai",
        system_prompt="""Analyze step-by-step:
        
1. List top features per class from SHAP
2. Verify each with local SHAP instances
3. Cross-reference with LIME rules
4. Identify contradictions
5. Formulate detection rules

Show each step explicitly.""",
        ...
    )
    results.append(result)

# Aggregate insights across runs
final_insights = aggregate_results(results)
```

---

## Quick Reference: Prompt Engineering Checklist

- [ ] **System Prompt**: Clear persona and task definition
- [ ] **Constraints**: Explicit dos and don'ts
- [ ] **Few-Shot Examples**: Provide format templates
- [ ] **Chain-of-Thought**: Request explicit reasoning steps
- [ ] **Structured Output**: Specify response format
- [ ] **Negative Constraints**: Define boundaries
- [ ] **Temperature**: Set appropriate randomness level
- [ ] **Domain Context**: Include dataset-specific knowledge
- [ ] **Evidence Citation**: Require citation of provided data
- [ ] **Iteration**: Use multi-phase refinement when needed

---

## Integration Status

| Technique | Status | Location |
|-----------|--------|----------|
| System Prompt | ✅ Implemented | `pipeline()` parameter |
| Temperature Control | ❌ Not implemented | `_query_llm()` modification needed |
| Few-Shot Examples | ❌ Not implemented | Add to prompt builders |
| Chain-of-Thought | ⚠️ Partial | Captured in `thinking_process` |
| Self-Consistency | ❌ Not implemented | New wrapper function needed |
| Structured Output | ❌ Not implemented | Add JSON format instruction |
| Negative Constraints | ❌ Not implemented | Add to base prompts |
| Domain Variations | ❌ Not implemented | New parameter + templates |