# Explainable‑AI Report for the _RandomForestClassifier_ on Web‑Log Log‑Ingestion

Below is a structured, technical analysis of the model’s behaviour derived from the supplied SHAP and LIME explanations.  Only the evidence that has been explicitly provided is used – no invented values or hidden attributes are mentioned.

---

## 1. Global vs. Local Interpretation  

| Feature | Relative Global Influence (BotAttack) | Relative Global Influence (Normal) | Relative Global Influence (PortScan) |
|--------|-----------------------------------|-------------------------------------|-------------------------------------|
| Port   | Most important (≈ 0.08) | Dominates (≈ 0.10) | Weak (\< 0.02) |
| Payload_Size | High (≈ 0.03) | Moderate (≈ 0.05) | Highest (≈ 0.06) |
| Status | Medium (≈ 0.02‑0.04) | Medium – higher than *Port* for “Normal” | Small (≈ 0.018) |
| Request_Type, Protocol, User_Agent | Very small (≈ 0.002‑0.003) | Very small | Very small |

**Observations**

* **Global perspective** – The topology of the Shapley values shows that *Port* is the features that the RandomForest puts most weight on when separating *Normal* from attack categories.  Payload size becomes especially pivotal when the model has to detect *PortScan*, i.e., the model learns that very low or very high scattered payloads are characteristic of scanners.
* **Local perspective** – The SHAP local logs reveal that a single high *Payload_Size* can swing the prediction from a normal class to an *Attack* class (positive contribution to “BotAttack” and negative to “Normal”).  Conversely, a small payload tends to favour *Normal*.
* The *Status* feature interferes in a nuanced way: a “Success” status tends to push the score toward the “Normal” node, whereas a “Failure” favours “BotAttack” or “PortScan” depending on the port.

---

## 2. Feature Influence – Attack vs normal

| Feature | Influence on “Normal” | Influence on “Attack” |
|--------|---------------------|----------------------|
| Port | Positively correlated with normal traffic up to low ports (22, 23) and high ports (443, 4434).  For high + lower ports the probability of a normal event rises. | Attack traffic clusters on mid‑range ports (80, 21, 23, 135) and also uses the extreme port 31337 (often associated with scanners).  RandomForest uses “Port > 5” as a negative indicator for normal. |
| Payload_Size | Large payloads favour attacks; very small payloads favour normal. | High scatter (both ends of the distribution) is classified as an attack, especially “PortScan.” |
| Status | “Failure” is a weaker indicator for an attack, but the combination of failure with certain ports sends a strong flag to the model. | “Success” on non‑standard ports is still enough to be suspicious if payload is large. |
| Request_Type | Minimal impact – the model does not rely on the request protocol type for distinguishing the classes. |
| Protocol | Minimal impact – the tree impurity is almost unchanged when splitting on this feature. |
| User_Agent | In the encoded space, this feature has negligible global weight; its inclusion is likely a safeguard rather than a primary predictor. |

**Take‑away** – The RandomForest relies almost exclusively on *Port*, *Payload_Size*, and *Status* for separating the classes.  The categorical encoder has essentially flattened the mixed categorical variables into nothing but noise for the learning algorithm.

---

## 3. Patterns & Correlations

1. **Port + Payload_Size interaction**  
   *Lime* rules demonstrate that low port numbers together with **Payload_Size > 0.79** often push the score toward an attack label.  The same combination (Port ≤ 1) is highly positively weighted for the “BotAttack” classification.

2. **High Port numbers (5 ≤ Port ≤ 10)**  
   *LIME* shows a strong negative rule (e.g., *Port > 5.00* → weight ≈ ‑0.56) for detecting benign traffic.  Thus, the model has learned that “Port > 5” is usually not normal—e.g. a heavy reliance on port 7137 or 443 is flagged.

3. **Payload range extremes**  
   *SHAP* local values reveal that payload sizes in the range \[-2.0, -0.8\] or \[0.8, +2.0\] are decisive for “PortScan.”  Instances in this range get a large negative contribution to “Normal” and a large positive one to “PortScan.”

4. **Status as a weakness‑point indicator**  
   When *Status* is “Failure,” the local contributions to “BotAttack” tend to increase.  This is captured in the *LIME* rule “Status ≤ 1.00” with weight 0 (neutral) – the RandomForest relies more heavily on the combination of *Port* and *Payload_Size* than status.

---

## 4. Mis‑classifications – What the Prediction Sample Shows

The predicted labels match the true labels for every example in the sample.  The overall model accuracy is 0.9989, confirming that the majority of edge cases are captured sharply by the decision trees.

*Possible corner‑case scenarios* that could still produce errors (based on the explanations) include:

* **Low‑`Port` + moderate `Payload_Size` + “Failure”** – The model could mislabel traffic that is normal but has a low port and an uncommon status.  
* **High `Port` but very low `Payload_Size`** – If the traffic is benign but contains a tiny payload on a high port, the tree may incorrectly flag it as an attack because the *Port > 5* rule is strong.

These scenarios are rare given the high accuracy, but they are indicated by the weight patterns in the LIME rules and the local SHAP contributions.

---

## 5. Influence of Categorical Encodings

The dataset translates every categorical value into a single integer (e.g., *Port* 21 → 0, 22 → 1, etc.).  RandomForest treats each integer as an **ordinal feature**, which can imprint artefactual ordering that does not exist in reality.

* **Effect on “Port”** – Because 21 → 0 and 443 → 7, the model can split on “Port ≤ 1” or “Port > 5” because those boundaries produce large information gain. The real benefit is that the trees discover that lower‑numbered ports are more likely normal.  Still, the ordinality could mislead the model if a port mapping diverges from this sequence in a new dataset.

* **Effect on “Request_Type”, “Protocol”, “User_Agent”** – Their shallow SHAP contributions indicate that the forest has largely ignored them.  The ordinal encoding may prevent the model from learning truly categorical relationships because the midpoints (e.g., 1 vs 7) are treated as having a numeric distance.

**Recommendation** – One‑hot encoding these categorical columns would remove the artefactual ordering and potentially expose subtle associations (e.g., “User_Agent = Nikto” + “Protocol = TCP” might be particularly malicious).

---

## 6. Cybersecurity Insights

| Insight | Operational Meaning |
|--------|--------------------|
| **Bot traffic is predominantly on lower ports and has higher payload variance** | Botnets often reuse the standard service ports (21 FTP, 22 SSH, 23 Telnet) and send larger packets to evade signature‑based filters. |
| **PortScan signatures are characterised by highly scattered payloads on non‑standard ports** | A scanner will probe a range of high ports with very small or very large packets, which the model flags as “PortScan.” |
| **Successful requests are more likely to be normal, failures more likely to be attacks** | A successful GET to a standard port can be benign; a failed attempt on a lower port is more suspicious. |
| **‘User_Agent’ encoding has minimal impact, suggesting that client‑surface variations are not a strong discriminator** | Attackers already mimic common browsers (Mozilla) or other user‑agents in the dataset. The RandomForest does not differentiate. |

These observations align with established intrusion‑detection heuristics: low‑port abuse, abnormal payload size, and status codes are strong indicators of exploitation attempts.

---

## 7. Suggested Model / Data Improvements

| Area | Action | Expected Impact |
|------|--------|----------------|
| **Encoding** | Use one‑hot encoding for categorical columns (Port < 100, Request_Type, Protocol, User_Agent) | Remove ordinal bias, reveal true categorical dependencies |
| **Feature Engineering** | Add interaction terms (e.g., *Port × Payload_Size*, *Status + Port*) | RandomForest can split on engineered features with clearer decision boundaries |
| **Balancing** | Ensure per‑class SMOTE sampling captures the tail patterns of PortScan | Reduce risk of model over‑fitting to majority “Normal” patterns |
| **Tree Size** | Increase max depth / number of trees slightly | Allow deeper capture of subtle patterns while monitoring over‑fitting |
| **Evaluation** | Expand confusion matrix analysis on hold‑out data | Identify the rare edge‑case scenarios that still misclassify |
| **Explainability** | Generate SHAP dependence plots for *Port* vs *Payload_Size* | Visual confirmation of interaction and thresholds used in the forest |

---

### Summary

* **Port** and **Payload_Size** drive the attack detection logic in the RandomForest; **Status** provides a secondary reinforcement.  
* SHAP global importance correlates with the LIME rule weights, confirming that the decision boundaries identified by the trees are robust across methods.  
* The low influence of the categorical encodings signals that the current integer mapping may obscure useful signals.  
* From a security stance, the model corroborates classic intrusion patterns (low‑port abuse, abnormal payloads) and can be fortified by more expressive feature representation.

With these adjustments and continued evaluation, the system should maintain its high accuracy while becoming resilient to new attack patterns and easier to audit in an operational setting.
