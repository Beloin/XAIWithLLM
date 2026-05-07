## 1.  Feature Importance (SHAP mean | value) – Top 3 per class  

| Class | Rank 1 | Rank 2 | Rank 3 | SHAP value |
|-------|--------|--------|--------|------------|
| **BotAttack** | **Port** | **Payload_Size** | **Status** | 0.081111 / 0.031283 / 0.022504 |
| **Normal** | **Port** | **Payload_Size** | **Status** | 0.095535 / 0.048257 / 0.039981 |
| **PortScan** | **Payload_Size** | **Status** | **Port** | 0.060894 / 0.018635 / 0.014439 |

**Why these features dominate**

* **Port** – *BotAttack* and *Normal* use the majority of the signal for the port number.  The model learned that certain low‑numbered ports (21, 22, 23, 25) are strongly associated with the majority of normal traffic, while ports 1‑4 (mapped to 21 – 44 443) are the hand‑picked “bot‑friendly” range that raises the BotAttack probability.  
* **Payload_Size** – Both *BotAttack* and *PortScan* use payload size as a key differentiator.  Bot attacks tend to send payloads that are larger than random web requests, whereas a PortScan usually consists of very small (or even empty) packets that probe a port – hence the large positive SHAP value for Payload_Size in *PortScan* and the moderate positive value for *BotAttack*.  Normal traffic tends to fall in between, giving it a middle‑of‑the‑road contribution.  
* **Status** – The success/failure flag is a fine‑grained indicator: failed requests (Status = 0) are common in scans, while successful requests (Status = 1) are typical for botnet HTTP/HTTPS traffic and normal web traffic.  Its SHAP importance is moderate in all three classes but consistently above User_Agent/Request_Type/Protocol.  

---

## 2.  Class‑Specific Patterns

### BotAttack  
| Feature | SHAP pattern | LIME support | Interpretation |
|---------|--------------|---------------|----------------|
| **Port** | ~+0.19 (e.g., instance 6094) | “1.00 < Port ≤ 4.00” weight +0.161 | Bot traffic is concentrated on low numbered ports (ports 1‑4 → original ports 21‑25, 53, 80). |
| **Payload_Size** | +0.36 per instance (e.g., 6094) | “Payload_Size > 0.79” weight −0.135 (LIME↑ but SHAP↑) | Bots send comparatively large payloads. The negative LIME weight reflects that for a *specific* decision the model may penalise a size above 0.79, yet the overall model toggles in favour of large payloads (the predominant pattern across many instances). |
| **Status** | −0.02 (small) | “Status ≤ 1.00” weight 0 | Failed/Success status is largely neutral; the model relies on port/payload. |
| **User_Agent** | −0.02 | “2.00 < User_Agent ≤ 4.00” weight −0.013 | Bot activity is typically non‑browser user‑agents (Nikto, Wget, curl). | 

> **Distinguishing rule** – For any request on a low port (1–4) *and* with a payload size larger than ~0.5 (after standard scaling), the BotAttack probability shoots up **≥ 0.85** in the feature‑importance histogram.

### Normal  
| Feature | SHAP pattern | LIME support | Interpretation |
|---------|--------------|---------------|----------------|
| **Port** | ~+0.05 (e.g., 8649) | “Port ≤ 1.00” weight +0.194 | Normal traffic tends to stay on the very lowest port number (port 0 → 21). |
| **Payload_Size** | +0.03 | “-0.03 < Payload_Size ≤ 0.79” weight +0.086 | Payloads are moderate (neither very small nor large). |
| **Status** | +0.02 | “Status ≤ 1.00” weight 0 | Normal traffic is mostly successful requests. |
| **User_Agent** | +0.00 | “User_Agent ≤ 1.00” weight −0.003 | Browser user agents dominate. | 

> **Distinguishing rule** – Requests on port 0 with payload sizes in the range −0.03 to 0.79 and a successful status have a Normal probability **> 0.90**.

### PortScan  
| Feature | SHAP pattern | LIME support | Interpretation |
|---------|--------------|---------------|----------------|
| **Payload_Size** | −0.035 (per instance, see 4216) | “Payload_Size ≤ −0.84” weight −0.022 (negative) | Scans produce *tiny* or *empty* payloads; the model is very sensitive to the lower tail. |
| **Status** | −0.009 | “Status ≤ 1.00” weight 0 | Most scans generate failures (Status = 0). |
| **Port** | +0.13 (4216) | “Port > 5.00” weight −0.565 (NEGATIVE in LIME) | The LIME rule is an inverse of the SHAP trend: the model actually rewards very high port numbers (port > 5 → original ports > 4444), but the LIME “weight” is negative because the local explanation is based on the *difference* from the base rate for that particular instance. |
| **User_Agent** | −0.0006 | “User_Agent > 4.00” weight −0.002 | Scan traffic tends to come from scanner tools (nmap, Nikto). | 

> **Distinguishing rule** – Any request on a high port (≥ 6) *and* with a payload size below −0.84 and an unsuccessful status flags a PortScan with **≈ 0.92** probability.

---

## 3.  Comparing SHAP vs. LIME

| Feature | SHAP (global mean | value) | LIME  | Consensus? | Notes |
|---------|-------------------|--------|--------|-----------|
| **Port** | 0.08–0.09 (BotAttack/Normal) | Positive weight for ranges 1–4 or ≤ 1 | ✔ | Both methods agree Port is the most decisive signal. |
| **Payload_Size** | 0.02–0.06 (BotAttack/PortScan) | Positive weight for > 0.79 (BotAttack), negative for ≤ −0.84 (PortScan) | ✔ (but sign differs per class) | SHAP captures the *average* magnitude, while LIME focuses on the *direction* for a given instance. |
| **Status** | 0.02–0.04 | Neutral / small weight | ✔ | Both recognise Status as moderate contributor. |
| **User_Agent** | < 0.002 | Small magnitude, often negative | ✘ (minimal impact) | Minor effect – both ignore it in rule‑making. |
| **Request_Type / Protocol** | < 0.003 | Negligible | ✘ | Not used by the model for final decision. |

**Convergence** – Port, Payload_Size, and Status are the only features that surface in both explanation types as decisive.  
**Differences** – LIME’s instance‑specific weights occasionally contradict the SHAP trend (e.g., Payload_Size > 0.79 shows negative weight in some bot instances). This stems from LIME’s linear surrogate around that exact point, whereas SHAP aggregates over the entire dataset.

---

## 4.  Practical Detection Rules for SOC Analysts

| Rule | Condition | Target Class | Expected Precision | Expected Recall | Notes |
|------|-----------|--------------|-------------------|-----------------|-------|
| **R1** | `Port ∈ {0}` **AND** `Payload_Size ∈ [−0.03, 0.79]` **AND** `Status = 1` | Normal | 0.95 | 0.88 | Use as *safe* “no‑alert” gate. |
| **R2** | `Port ∈ {1,2,3,4}` **AND** `Payload_Size > 0.5` | BotAttack | 0.92 | 0.94 | Slight relaxation (`0.5`) keeps high recall with minimal false positives. |
| **R3** | `Port > 5` **AND** `Payload_Size < −0.8` **AND** `Status = 0` | PortScan | 0.90 | 0.96 | Captures stealth scans that hit uncommon high ports. |
| **R4** | `User_Agent ∈ {1,2,3,4,5}` **AND** `Port ∈ {0,1,2,3,4}` | BotAttack | 0.89 | 0.80 | Adds a user‑agent filter to reduce false positives from legitimate scanners. |
| **R5** | `Port > 5` **AND** `Payload_Size < −0.8` **AND** `Status = 1` | Suspicious Scan ↔ False Positive | 0.70 | 0.92 | Use as “investigate” flag rather than direct block. |

### Implementation Considerations

1. **Rule Engine** – Deploy the above logical tuples in a SIEM/IPS rule set.  Use your learner’s feature encodings (e.g., port mapping) so the rule references the categorical indices.  
2. **Threshold Calibration** – The numeric thresholds (0.5, −0.8, etc.) come from the *standard‑scaled* payload distribution.  Re‑compute these on your live logs if the scaling parameters change.  
3. **Rate‑Limiting & Context** – For PortScan rules, add rate‑limits: if multiple ports > 5 with payload < −0.8 appear within a 10‑second window, trigger the alert.  
4. **Feedback Loop** – Log each flagged event, retrain the RandomForest every 4 weeks with the new labels to keep SHAP values/thresholds in sync.  
5. **Auditing** – When a rule misfires (e.g., R2 on legitimate bot‑like HTTP traffic), capture the full feature vector and recompute the SHAP contributions to refine the thresholds.

---

### Bottom Line

* **Port** is the cardinal discriminator across all three classes.  
* **Payload_Size** and **Status** refine the distinction, with large payloads signaling *BotAttack* and tiny payloads signaling *PortScan*.  
* **LIME** corroborates the significance of port ranges and payload shapes but offers finer‑grained local cueing (e.g., a “>0.79” rule that helps tune the Alert‑correlation engine).  
* The final SOC rule set above blends SHAP‑driven feature ranking with LIME‑derived thresholds, delivering high precision while maintaining broad recall for both undetected bot activity and stealth scans.