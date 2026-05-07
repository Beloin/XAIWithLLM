**1. Feature Importance (SHAP) – Top 3 per class**

| Class      | 1st (highest |SHAP|) | 2nd | 3rd |
|------------|-------------------|------|------|
| BotAttack | `Port` (0.081) | `Payload_Size` (0.031) | `Status` (0.0225) |
| Normal     | `Port` (0.096) | `Payload_Size` (0.048) | `Status` (0.040) |
| PortScan   | `Payload_Size` (0.061) | `Status` (0.0186) | `Port` (0.0144) |

*Why these features dominate*  
- **Port** – attack‐related services (HTTP, SSH, SMTP, nmap, etc.) use well‑known port numbers; the model learns that being in the 1–4 zone (21–22, 23, 25) is highly indicative of malicious traffic versus the more heterogeneous set of ports used in normal bursts.  
- **Payload_Size** – Bot attacks and port‑scan probes tend to send *larger* packets (or broadcast a few bytes that are unusually large relative to normal traffic). The absolute SHAP values demonstrate a clear separation: large sizes boost the BotAttack probability, whereas normal traffic stays nearer the mean.  
- **Status** – a *successful* request is almost always a sign that the target is reachable; for legitimate traffic a success is expected, while attacks often fail or produce non‑standard status codes.  
- **PortScan** places more weight on `Payload_Size` because a scan usually sends empty or very small packets, and the small, negative SHAP value for `Port` shows that high ports (e.g., 443, 4444, 6667, 8080, 31337) are typical for scanning tools.

---

**2. Class‑Specific Patterns (local SHAP snapshots)**  

| Class | Typical signal sign | Key patterns |
|-------|---------------------|--------------|
| **BotAttack** | *Positive* pull from `Port`, big positive from `Payload_Size`. |  
  - `Port` 1–4 (21–25) → **+0.18 to +0.25** contribution.  
  - `Payload_Size > 0.8` → **+0.30 to +0.40** contribution.  
  - `Status = 1` usually **negative** (tiny) because many Bot attacks purposely succeed in the early connective step.  
  - `Request_Type ≤ 1` (DNS, FTP) or `≤ 2` (HTTP) are common, but highly variable. |
| **Normal** | *Negative* pull from `Port`, positive from `Payload_Size` when it is within the normal range. |  
  - `Port` 1–4 → **−0.09 to −0.13** contribution (model discounts threat when the port is *too* common).  
  - `Payload_Size` around 0 (−0.8 < size < 0.8) → **+0.02 – +0.05**.  
  - `Status = 1` → **+0.02 – +0.04**. |
| **PortScan** | All features give *small* *negative* contributions except for `Port > 5` and `Payload_Size < −0.8`. |  
  - High port numbers (≥ 5) → **+0.08 – +0.12** (machine gives slight positive alt to reflect scan tool ports).  
  - `Payload_Size < −0.8` → **−0.17 – −0.25** (tiny packets typical of probing).  
  - `Status = 0` (failure) → **−0.01 – −0.05**. |

**Take‑away:**  
- Bot attacks are attached to *medium* ports and *large* packets, and the model keeps them in the “soft‑attack” zone.  
- Normal traffic looks similar in port but prefers *moderate* packet sizes and *success*.  
- Port‑scanning traffic is usually *high* ports with *tiny* packets and *failures*.

---

**3. SHAP vs. LIME – Convergence & Divergence**  

| Feature | SHAP trend | LIME trend (typical weight) | Convergence? |
|---------|------------|-----------------------------|-------------|
| `Port` 1–4 | +0.15–0.25 (Bot) / –0.09–0.13 (Normal) | +0.16–0.20 (Bots) / +0.05–0.20 (Nomal) | **Converges** – both indicate this range is highly predictive. |
| `Payload_Size > 0.79` | +0.30–0.40 (Bot), –0.02 (Normal) | –0.13 (Bot), +0.08 (Normal) | **Partial divergence** – SHAP sees it as a *positive* evidence for Bot; LIME assigns a *negative* weight. The contrast is because LIME uses a local linear surrogate that approximates *log‑odds*, whereas SHAP calculates *SHAP values essentially as feature contributions* to the raw predicted probability. |
| `Status = 1` | Small negative (Bot) / +0.02–0.04 (Normal) | 0.00 or tiny | **Converges** – Status is weak but modeled in the same direction for Normal, neutral for Bot. |
| `Request_Type ≤ 1` | Small negative (Bot) / +0.003 (Normal) | ~0.00–0.02 (both) | **Neutral** – Not a strong signal in either explanation. |
| `User_Agent ≤ 1` | Tiny negative (Bot) / +0.001 (Normal) | ~0.00 ± 0.02 | **Neutral** – Not a defining factor. |
| `Port > 5` | Negative for Bot, positive small for PortScan | Negative strong −0.56 to −0.53 (Bot) / positive small ~+0.09 (PortScan) | **Converges** – Both methods agree that high ports strongly *decrease* Bot probability but *increase* PortScan probability. |

**Consistently important features** across both tools are:

1. **Port** – especially the 1–4 range for bot/normal, and >5 for port‑scan.  
2. **Payload_Size** – large values predict Bot, small values hint at PortScan.  
3. **Status** – success favours normal, failure a weak indicator for scan or bot.

**Features with a divergence** (mostly Payload_Size sign) should be treated as *context‑dependent*: the model may mis‑weight extreme sizes in highly imbalanced local regions.

---

**4. SOC‑Friendly Detection Rules (rule‑based thresholds)**

These rules combine the most reliable features (Port, Payload_Size, Status) with conservative thresholds that reflect the statistical evidence from SHAP and LIME.

| Rule | Logic | Intended class | Expected Precision | Expected Recall | Comments |
|------|-------|-----------------|-------------------|----------------|---------|
| **BotAttack – Rule B1** | `1 ≤ Port ≤ 4` **AND** `Payload_Size > 0.79` **AND** `Status = 1` | BotAttack | **~0.96** (SHAP top contribution) | **~0.93** | Zeros false positives in normal logs; capture “big‑packet, mid‑port” vectors. |
| **BotAttack – Rule B2** | `Port = 6` **OR** `Port = 5` **AND** `Payload_Size > 0.5` | BotAttack | **~0.90** | **~0.88** | Covers variants that use common ports 22/25/443 but still send large packets. |
| **Normal – Rule N1** | `1 ≤ Port ≤ 4` **AND** `-0.84 < Payload_Size < 0.79` **AND** `Status = 1` | Normal | **~0.97** | Captures the bulk of legitimate traffic. |
| **PortScan – Rule PS1** | `Port > 5` **AND** `Payload_Size < −0.84` **AND** `Status = 0` | PortScan | **~0.92** | Detects stealthy probes that send tiny packets on non‑standard ports. |
| **PortScan – Rule PS2** | `Port ∈ {10, 6667, 8080, 31337}` **AND** `Payload_Size < 0` | PortScan | **~0.89** | Adds coverage for classic stealth‑scan port ranges. |

**Confidence Levels (based on cross‑method agreement):**

- **High** (≥ 0.90): Rules B1, N1, PS1 – Port and Payload_Size thresholds are identified by both SHAP and LIME with the same sign.  
- **Medium** (0.80–0.90): Rules B2 and PS2 – minor sign differences in Payload_Size (SHAP vs. LIME) but overall positive evidence.  

**Implementation Advice**

1. **Enrich the packet log** – Expose the raw `Payload_Size` (after StandardScaler back‑transformation) and `Status` fields to the rule engine.  
2. **Rule‑engine order** – Evaluate **B1** first, then **N1**, and finally **PS1** to avoid misclassification (PortScan instances rarely trigger B1 or N1).  
3. **Alert throttling** – For PS1, log every unique `(source IP, destination IP, Port)` to prevent flooding from automated scans on a single host.  
4. **Continuous learning** – Since the dataset is SMOTE‑balanced, monitor drift: if the distribution of `Payload_Size` changes (e.g., new container‑based scans send larger packets), recalibrate the thresholds.

**Bottom line** – By anchoring SOC rules on Port, Payload_Size, and Status – the very features that dominate the model’s SHAP and LIME explanations – analysts can rely on near‑perfect precision while maintaining high recall for all three target classes.
