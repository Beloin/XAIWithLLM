# Explainable‑AI Analysis Report  
**Model** – RandomForestClassifier (70/30 stratified split, SMOTE, 0.9989 test‑accuracy)  
**Task** – Three‑class log‑entry classification  
&nbsp;  
```
0 → BotAttack      
1 → Normal       
2 → PortScan
```
The following analysis follows the five‑step methodology requested, using the SHAP and LIME artefacts that have been supplied.



--------------------------------------------------------------------

## 1. Global Feature Importance (SHAP)

The *mean absolute* SHAP values for each feature in every class show the relative influence of a variable on the **log‑odds** of that class.  

| Feature     | BotAttack | Normal | PortScan |
|------------|-----------|--------|----------|
| Port       | 0.081 | 0.096 | 0.014 |
| Payload_Size | 0.031 | 0.048 | 0.061 |
| Status     | 0.022 | 0.040 | 0.019 |
| Request_Type | 0.003 | 0.002 | 0.0005 |
| Protocol   | 0.0015 | 0.0016 | 0.0004 |
| User_Agent| 0.0017 | 0.0017 | 0.0006 |

### Ranking
1. **Port**  
2. **Payload_Size**  
3. **Status**  
4. **Request_Type**  
5. **Protocol**  
6. **User_Agent**

The top three features (Port → Payload_Size → Status) dominate the decision‐making in every class. The residual features are almost negligible compared to the others.

### Interpretation
* The *Port* feature appears to capture whether a connection is a normal web request, a port scan, or a bot‑driven command‑and‑control interaction.  
* *Payload_Size* carries information on packet payload magnitudes; unusually large or very small sizes appear highly discriminative.  
* *Status* follows the logic that successful handshakes are less suspicious than frequent failures (a hint of probing).

--------------------------------------------------------------------

## 2. Local Behaviour (SHAP on a Sub‑Set of Instances)

Examining the local SHAP contributions demonstrates how each of the top three features drives the final probability on a case‑by‑case basis.

### Port

* **High positive contribution (> +0.15) to Normal**, especially when the encoded value is 1–4 (ports 22–53).  
* **High negative contribution (< −0.10) to BotAttack / PortScan** when the port is >5 (ports such as 8080 or 433).  

This mirrors the global trend: mid‑range ports are “normal”, whereas extreme ports lean toward attacks.

### Payload_Size

* **Large positive values (~+0.2 to +0.35) reinforce BotAttack** when the payload is very large (≈+1.6 after StandardScaler).  
* **Large negative values (~−0.2) suppress BotAttack** when the payload is large but the port is also anomalous.  
* **Small or negative payloads (≈−1.5 to −0.3) tend to reduce the probability of BotAttack** and slightly boost Normal.  

The LIME rules capture this: “Payload_Size > 0.79” usually carries a negative weight, implying that *too large* payloads are *not* typical of the BotAttack class in the sampled instances, but the SHAP local values for the high‑payload instance (instance 6094) show a positive boost – an idiosyncrasy that will be discussed later.

### Status

* Success (encoded “1”) **adds** a modest amount to Normal (≈+0.01–0.02).  
* Failure (encoded “0”) **subtracts** a small amount from Normal, and a slightly bigger negative from BotAttack (≈−0.04).  

Thus, successful exchanges are reassuring, failures are suspicious.

The *Protocol*, *Request_Type*, and *User_Agent* local contributions are largely negligible, confirming they do not shape the final decision.

--------------------------------------------------------------------

## 3. Cross‑Referencing with LIME

| Feature | SHAP trend | LIME weight | Commentary |
|---------|-----------|------------|-------------|
| Port | Positive in Normal, negative in BotAttack/PortScan | -0.565 (Port>5) | LIME gives a large *negative* weight for ports >5 – matches SHAP’s negative influence on non‑Normal. |
| Payload_Size | Mildly negative always, sometimes positive in extreme cases | -0.135 / -0.172 (Payload>0.79) | LIME aligns with SHAP largely, but shows a *negative* weight for large payloads while SHAP local example (6094) showed a slight positive. LIME may be summarizing a broader pattern. |
| Status | Small positive for Success | 0 weight on rule "Status<=1" | LIME does not quantify Status, but SHAP shows weak influence. |
| User_Agent | Negligible | Small weights (±0.01) | Consistent. |
| Request_Type | Negligible | Small weights | Consistent. |
| Protocol | Negligible | Small weights | Consistent. |

### Agreements
* Port and Payload_Size are the dominant signals in both frameworks.  
* The sign of Port’s influence (negative for high values) is captured by both SHAP and LIME.  
* Small positive contribution of Success status is also seen.

### Contradictions
* SHAP local value for instance 6094 (high Payload) is slightly positive for BotAttack, which conflicts with the LIME “Payload > 0.79” rule that is heavily negative.  
  * Likely because LIME aggregates across many instances, while the local SHAP value reflects a specific feature distribution in one observation.  
* LIME does not provide “Status” contributions, so that dimension is missing in LIME.

Overall, **consistency** is high for Port and Payload_Size, lending confidence to those features as key indicators.

--------------------------------------------------------------------

## 4. Cyber‑Security Insight and Pattern Recognition

1. **Port Number as a Rough Classifier**  
   * Ports 0–4 (21–55) dominate Normal traffic and rarely appear in BotAttack or PortScan.  
   * Ports 5–11 (80, 135, 443, 4444, 6667, 8080, 31337) are strongly associated with malicious classes.  
   * The extreme port 31337 (mapped to 11) yields strong negative contributions to Normal and positive to PortScan, i.e., an explicit signature of scanning/probing.

2. **Payload Size**  
   * Extremely large payloads (standardised > +1.5) strongly support BotAttack when paired with typical port ranges, suggesting large data injections typical of bot back‑doors.  
   * Large but *unnatural* payloads combined with anomalous ports can reduce BotAttack likelihood, possibly indicating benign high‑volume traffic or mis‑labelled data.

3. **Status**  
   * Successful handshakes (Status=1) inflate Normal probability, underscoring that attackers often use failed handshake attempts as probing (reducing success to zero).  
   * A bulk of failures is typical for PortScan, as expected from scanning probes generating collisions.

4. **Request_Type & User_Agent**  
   * Very small effect size suggests that these categorical fields are not discriminative for this data set, but their inclusion may help other attackers craft more realistic traffic.

5. **Potential Attacker Tactics Inferred**  
   * Attackers ping a wide array of ports (ICMP/TCP/UDP) using generic User‑Agents (e.g., “Nikto”, “Wget”).  
   * Success/failure patterns show that attackers rely on probing with failures (PortScan) and on completed sessions (BotAttack).

--------------------------------------------------------------------

## 5. Mis‑Classification Analysis

The provided sample predictions match the ground truth for every entry (all True==Pred). Therefore, no mis‑classifications crop up in this slice and the model’s 99.89 % accuracy is reflected.

Nevertheless, SHAP and LIME indicate **subtle borderline instances**: those with Port > 5 and payload close to zero or negative might over‑lean toward BotAttack due to the port weight, even when the payload is typical for normal chatter.

A systematic audit could identify such boundary conditions – e.g., Port = 6 (80) with small payload that is actually normal testing – to see if the model is mis‑labeling.

--------------------------------------------------------------------

## 6. Influence of Categorical Encoding

* **Ordinal encoding** was used for every categorical feature (e.g., Request_Type 0–6, Port 0–11).  
  * For `Port`, the encoded value implies an order (21 < 22 < … < 31337). RandomForest trees rely on binary split thresholds; the numeric gaps between ports may be arbitrary (22–53 is 31, 8080–31337 huge), potentially biasing splits.  
  * `User_Agent` likewise has an arbitrary ordering; the tree may treat “curl” (3) as closer to “Nikto” (1) than to “Mozilla” (0), which is not meaningful.

* **Impact on SHAP & LIME**  
  * SHAP values for these features are almost zero, indicating the model does **not** exploit the ordering heavily, probably owing to limited discrimination power.  
  * However, given that the *Port* feature still dominates, the ordinal representation seems adequate for this variable – the trees found useful splits at specific threshold points (e.g., > 5).  

* **Recommendation**  
  * One‑hot or target‑encoding for truly categorical features (`Port`, `Request_Type`, `Protocol`, `User_Agent`) could remove any artificial distance assumptions and potentially lower bias.  
  * For `Port`, a two‑step representation might be useful: *Port Range* (normal vs. unusual) plus a *Target‑encoded* version for fine‑grained behaviours.

--------------------------------------------------------------------

## 7. Recommendations for Model / Dataset Improvement

| Issue | Suggested Action |
|-------|------------------|
| **Encoding Bias** | Switch from ordinal to one‑hot or target encoding for `Port`, `Request_Type`, `Protocol`, `User_Agent`. |
| **Feature Engineering** | Add transformed features that capture interactions (e.g., `Port * Status`, `Payload_Size * Status`). |
| **Imbalanced Classes** | Although SMOTE was applied, re‑evaluate `PortScan` representation to avoid over‑fitting on minority signals. |
| **Temporal Dynamics** | Include a time‑based feature (e.g., request timestamp hash) to capture bursty scanning patterns. |
| **Explainability‑Driven Feature Drop** | Remove or assign lower weight to features with near‑zero SHAP contributions to simplify model. |
| **Calibration** | Post‑process predicted probabilities with Platt scaling or isotonic regression; this can help in defining robust attack/no‑attack thresholds. |
| **Threshold Tuning** | Use precision‑recall curves to select operating points that match organizational risk appetite. |
| **Model Ensemble** | Consider a small gradient‑boosted tree ensemble (e.g., XGBoost) only if TF‑based features are added; keep RandomForest as baseline because of interpretability and speed. |
| **Monitoring** | Deploy SHAP/AUC dashboards to monitor drift in feature importance over time. |
| **Explainability Tooling** | Adopt SHAP with SHAP explanation objects for direct per‑instance exploration; for rule‑based explanation (LIME), provide domain‑specific thresholds read‑out. |

--------------------------------------------------------------------

## 8. Summary of Key Findings

1. **Port** is the *most influential predictor* across all three classes; it can act as a quick rule‑of‑thumb to separate normal traffic from scanning/bot activities.  
2. **Payload_Size** and **Status** are the next important factors, adding discriminative power mainly for distinguishing bot activity from benign connections.  
3. **SHAP and LIME** largely agree on the direction of influence for Port and Payload_Size, increasing confidence in these signals.  
4. **Encoding** as ordinal is acceptable for Port but possibly sub‑optimal for the rest; moving to one‑hot may improve model robustness.  
5. **No mis‑classifications detected** in the example batch, yet potential boundary errors are evident where Port and Payload_Size overlap.  
6. **Cyber‑security insight**: attackers frequently target high‑number ports (80, 443, 8080, 31337) and may use very large payloads coupled with successful handshakes.  
7. **Model refinements**: simplification of the feature set, improved encoding, calibration, and threshold tuning will enhance interpretability and operational performance.

---

*Prepared by*: Explainable‑AI Analyst  
*Date*: 2026‑05‑07*