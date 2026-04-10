# Without XAI Results — N_SAMPLES = 20

**Date:** 2026-03-25
**Configuration:** 20 training samples, 20 prediction samples (no SHAP/LIME)

---

## Validation Flags Summary

| Model | Correct Ranking? | UA Bias? | Status |
|-------|-----------------|----------|--------|
| glm-4.7-flash:latest | ❌ No | ✅ Yes | UA overvalued |
| qwen3:14b | ✅ Yes | ✅ Yes | Correct but with UA bias |
| gpt-oss:20b | ❌ No | ✅ Yes | UA overvalued |
| qwen3:30b | ❌ No | ❌ No | Incomplete extraction |

**Summary:** 1/4 correct (25%), 3/4 show User_Agent bias

---

## Ground Truth Reference

| Class | Top-3 Features (SHAP) |
|-------|----------------------|
| BotAttack | Port > Status > Payload_Size |
| Normal | Port > Status > Payload_Size |
| PortScan | Payload_Size > Status > Port |

**Key:** User_Agent has near-zero SHAP importance (< 0.006) for all classes.

---

## Model Responses

### glm-4.7-flash:latest

**Flags:**
- ⚠️ **User_Agent Bias**: Claims User_Agent is "Primary Driver" and "absolute strongest predictor"
- ❌ **Incorrect Ranking**: Top-3 extracted: Port, User_Agent (missing Status, Payload_Size)

```
### 1. Model Context
The model is a Random Forest classifier designed to classify network traffic into three discrete categories:
*   **Class 0 (BotAttack):** Likely represents malicious automation or anomalous behavior.
*   **Class 1 (Normal):** Represents standard, expected traffic from authenticated users.
*   **Class 2 (PortScan):** Represents network reconnaissance activities.

The model achieves a high accuracy (99.7%), indicating that the features used are statistically strong indicators of the traffic's intent. However, the specific mapping of these features to the classes reveals some interesting biases in the data.

### 2. Feature Analysis
Based on the provided encodings and training data, the features exhibit a clear hierarchy of importance:

*   **User_Agent (Primary Driver):**
    *   **Encoded Values:** `0` (Mozilla/Normal), `1-5` (Nikto, Wget, Curl, Nmap, Python).
    *   **Significance:** This is the absolute strongest predictor in the model. The "scanner" signatures (Nmap, Nikto, etc.) map almost exclusively to the non-Normal classes (0 and 2). The Human signature maps almost exclusively to "Normal".
*   **Port:**
    *   **Encoded Values:** Maps standard ports (22=SSH, 80=HTTP, 443=HTTPS) to specific integers. It also maps obscure ports (0, 11) which are significant discriminators for BotAttacks and PortScans.
    *   **Significance:** The model distinguishes traffic based on which port is being engaged. For instance, standard web ports (80/443) drive the "Normal" probability up, while low or unused ports drive it down.
*   **Request_Type:**
    *   **Encoded Values:** Maps verbs like FTP, SSH, Telnet, SMTP, HTTP.
    *   **Significance:** Acts as a secondary filter. While specific ports trigger the classification, the request type adds context. For example, a Telnet (6) request might be more suspicious (Class 0) than an SMTP (4) request when paired with low ports or scanner agents.
*   **Protocol:**
    *   **Encoded Values:** TCP, UDP, ICMP.
    *   **Significance:** Less discriminative than User-Agent, but helps refine the probability. TCP scans (common with Nmap) are distinct from UDP attacks.
*   **Payload_Size & Status:**
    *   **Significance:** While present, these variables appear to contribute less to the decision boundary than the identity of the source. The model appears to trust the *intent* (signatures) over the size or response code.

### 3. Decision Pattern Hypotheses

**Pattern A: The "Normal" Baseline (Class 1)**
*   **Trigger:** High probability of `(User_Agent == Human)` AND `(Port in known_web_security_ports OR Port == SSH)`.
*   **Logic:** If the traffic originates from a standard browser (0) or standard SSH client (5) on accessible ports, the model classifies this benign network administration or user interaction as "Normal".

**Pattern B: The Reconnaissance Class (Class 2)**
*   **Trigger:** High probability of `(User_Agent in [Nmap, Wget, Curl])` AND `(Port is non-standard or high)`.
*   **Logic:** When the model sees a known scanner signature, it flags it as "PortScan". The data suggests these are active network scans (e.g., Nmap -sS, Wget crawling).

**Pattern C: The Malicious/Ambiguous Class (Class 0)**
*   **Trigger:** `(User_Agent is Unknown OR Payload_Size is erratic) AND/OR (Port is obscure/ephemeral) AND (Status is Failure)`.
*   **Logic:** This class is distinct from known PortScans. It likely captures sophisticated botnets, privilege escalation attempts, or traffic where the User-Agent is spoofed/forged, leading the rule-based logic to interpret the behavior as "BotAttack" rather than standard "PortScan".

### 4. Instance-Level Reasoning

*   **Training Data Example:** Port 1 (SSH), User_Agent 4 (Nmap), Label 1 (Normal).
    *   **Reasoning:** This is a counter-intuitive result if Nmap is a scanner. However, the model likely classifies this as "Normal" because Port 1 (SSH) is a "valid" port in the dataset schema, and the system allowed the connection. The model treats "Known Scanning Tools" as administrative reconnaissance first. *Correction*: Actually, looking at other examples, if Port 11 (Record 11) is labeled "BotAttack" with Nmap, while Port 1 is "Normal," the model is distinguishing based on **Port Validity**. Port 1 is structurally valid (even if non-standard port for that service), while Port 11 might be flagged as inherently dangerous.

*   **Training Data Example:** Port 11 (Unknown), User_Agent 3 (Curl), Status 0 (Failure), Label 2 (PortScan).
    *   **Reasoning:** The model sees a scanner (Curl) trying to connect to a "bad" port (11) and failing. This is interpreted as a standard reconnaissance activity (PortScan).

### 5. Cybersecurity Insights for SOC

*   **"User-Agent Fingerprinting" is the primary Kill Chain indicator.** The SOC should prioritize checking the User-Agent header. Seeing "Nmap/1.0" or "Wget/1.X" is a definitive positive hit for automated detection mechanisms.
*   **Distinguishing "Scan" vs. "Attack".** This model successfully separates "known scanning tools" (PortScans) from "unidentified behavioral anomalies" (Bots).
    *   *Action:* If you see Nmap, log it as an audit (PortScan). If you see an unknown Python script connecting to Port 0, treat it as an immediate threat (BotAttack).
*   **Port Anomalies are Secondary Indicators.** While looking for ports 22/80/443 is standard practice, the training data shows that obscure ports (0, 11) combined with scanner agents trigger alerts faster.

### 6. Model Behavior Assessment

*   **Decision Boundaries:**
    *   The boundary is heavily clustered around the definition of a "valid service."
    *   If `User_Agent == Human` and `Port` maps to an OS default, the output is Prob=1.0 for "Normal".
    *   If `User_Agent == [Nmap/Wget/Nikto]`, the output drops significantly for "Normal" and rises for "PortScan".
*   **Weakness Areas:**
    *   **Spoofing:** If a BotAttack program (Class 0) spoofs its User-Agent to look like a Human (Mozilla), the model is highly likely to fail and classify it as "Normal" (Class 1).
    *   **Encryption:** Payload Size and Status are less relied upon. If the traffic is encrypted (TLS), the model cannot see the User-Agent effectively, rendering these features useless.

### 7. Improvement Suggestions

1.  **Reverse Engineering User-Agents:** Since `User_Agent` is the strongest feature, the SOC should integrate a "User-Agent reputation library." If the User-Agent is present but unlisted in the training set (e.g., a custom "BadBot"), update the dictionary to ensure the model treats it as "BotAttack."
2.  **Feature Engineering: Entropy:** Add packet payload entropy as a feature. Standard web traffic has moderate entropy; scanner traffic (like port scans) or bot chatter often has higher or lower entropy depending on noise vs. payload.
3.  **Time-Series Correlation:** Adding a "Time between requests" feature (Request Frequency). A "Normal" user browses slowly. A "PortScan" or "Bot" makes rapid sequential requests to multiple IPs/Ports.
4.  **Explainable AI (SHAP/LIME):** Given the high accuracy, it is important to ensure the SOC understands *why* a traffic spike is being generated. If the model flags a user as a "BotAttack," the SOC needs to know if it was the User-Agent or the Payload Size that triggered the violation.
```

---

### qwen3:14b

**Flags:**
- ✅ **Correct Top-3**: Port, Status, Payload_Size (matches ground truth)
- ⚠️ **User_Agent Bias**: Still mentions User_Agent as important

```
### 1. **Model Context**
The model is a Random Forest classifier trained to detect network intrusions (BotAttack, Normal, PortScan) with 99.7% accuracy. The feature space includes port numbers, request types, protocols, payload sizes, user agents, and request statuses. The pipeline includes class balancing via SMOTE and stratified splits, ensuring the model generalizes well to imbalanced real-world data. The focus of this analysis is not on performance validation but on interpreting the model's decision-making logic.

---

### 2. **Feature Analysis**
#### **Key Features (Ranked by Importance):**
1. **`User_Agent`**
   - **Why important:** User agents encode the client software (e.g., Nmap, Nikto, curl). These tools are strongly associated with attacks (e.g., Nmap for PortScan, Nikto for scanning vulnerabilities).
   - **Cybersecurity angle:** Unique user agents can directly indicate the presence of malware, bots, or penetration testing tools.

2. **`Payload_Size`**
   - **Why important:** Standardized payload sizes highlight anomalies. For example, PortScan attacks often involve repetitive, low-payload probes, while BotAttack traffic (e.g., brute-force attempts) may use smaller payloads.
   - **Cybersecurity angle:** Deviations from normal traffic patterns (e.g., unusually large or small payloads) are red flags for malicious activity.

3. **`Port`**
   - **Why important:** Specific ports (e.g., 80, 443, 22) are targeted by different attacks. PortScan attacks often target a broad range of ports, while BotAttack traffic is concentrated on ports associated with common services (e.g., SSH, FTP).
   - **Cybersecurity angle:** Port usage helps distinguish between targeted attacks (BotAttack) and broad-spectrum scanning (PortScan).

4. **`Request_Type`**
   - **Why important:** Attack types correlate with specific request types. For example, HTTP/HTTPS (Request_Type 2,3) are common in BotAttack (e.g., phishing), while DNS (Request_Type 0) is used in PortScan.
   - **Cybersecurity angle:** Request types reveal the intent of the traffic (e.g., reconnaissance, data exfiltration).

5. **`Status`**
   - **Why important:** Failure (`Status = 0`) is often associated with BotAttack or PortScan (e.g., failed login attempts). Success (`Status = 1`) is more common in normal traffic.
   - **Cybersecurity angle:** System responses (e.g., HTTP 404, SSH connection refusals) provide indirect evidence of malicious activity.

6. **`Protocol`**
   - **Why important:** ICMP (Protocol 0) is often used in PortScan, while TCP/UDP (Protocols 1,2) are more common in BotAttack or normal traffic.
   - **Cybersecurity angle:** Protocols reveal the nature of communication (e.g., stealthy UDP packets in PortScan).

---

### 3. **Decision Pattern Hypotheses**
#### **BotAttack (Class 0):**
- **Patterns:**
  - **High `Status` (Success)**: BotAttack often succeeds in initial probes (e.g., successful HTTP requests).
  - **Specific `Port` and `Request_Type`**: Common ports like 22 (SSH) or 80 (HTTP) with Request_Type 2 (HTTP) or 5 (SSH).
  - **`User_Agent`**: Tools like `python-requests/2.25.1` (BotAttack) vs. `Mozilla/5.0` (Normal).
- **Hypothesis:** BotAttack is characterized by successful, targeted access to specific services (e.g., SSH brute-force).

#### **Normal (Class 1):**
- **Patterns:**
  - **Common `Port` and `Request_Type`**: High frequency of HTTP (Port 80, Request_Type 2) and HTTPS (Port 443, Request_Type 3).
  - **`Status`**: Mixed `Status` values (successes and failures are equally common).
  - **`User_Agent`**: Dominance of `Mozilla/5.0` (browsers) and `Wget/1.20.3` (scripts).
- **Hypothesis:** Normal traffic is diverse and distributed across common services, with user agents reflecting legitimate users.

#### **PortScan (Class 2):**
- **Patterns:**
  - **High `Payload_Size` deviation**: Repetitive, low-payload requests (e.g., `Payload_Size = -1.25` in training data).
  - **`Request_Type`**: DNS (0) or FTP (1) with `Protocol` ICMP (0).
  - **`User_Agent`**: `nmap/7.80` (specific tool for scanning).
- **Hypothesis:** PortScan is detected through systematic probing of multiple ports with minimal interaction and use of scanning tools.

---

### 4. **Instance-Level Reasoning**
#### **Example 1 (BotAttack):**
`
{"Port":2,"Request_Type":6,"Protocol":1,"Payload_Size":2.83,"User_Agent":2,"Status":0,"Scan_Type_Label":0}
`
- **Why predicted BotAttack (0):**
  - **`Port = 2` (SSH)** and **`Request_Type = 6` (Telnet)**: Targeted services often exploited by bots.
  - **`Status = 0` (Failure)**: Failed attempts are common in brute-force attacks.
  - **`User_Agent = 2` (Wget/1.20.3)**: Script-based tools used for automated scanning.

#### **Example 2 (PortScan):**
`
{"Port":11,"Request_Type":0,"Protocol":0,"Payload_Size":2.73,"User_Agent":4,"Status":0,"Scan_Type_Label":0}
`
- **Why predicted PortScan (2):**
  - **`User_Agent = 4` (`nmap/7.80`)**: Explicit indicator of PortScan.
  - **`Protocol = 0` (ICMP)**: ICMP is a common tool for scanning (e.g., ping sweeps).
  - **`Payload_Size = 2.73` (high deviation)**: Indicates repetitive, low-interaction probes.

#### **Example 3 (Normal):**
`
{"Port":80,"Request_Type":2,"Protocol":1,"Payload_Size":0.5,"User_Agent":0,"Status":1,"Scan_Type_Label":1}
`
- **Why predicted Normal (1):**
  - **`Port = 80` (HTTP)** and **`Request_Type = 2` (HTTP)**: Common for legitimate traffic.
  - **`User_Agent = 0` (`Mozilla/5.0`)**: Represents a standard browser.
  - **`Status = 1` (Success)**: Aligns with typical web traffic.

---

### 5. **Cybersecurity Insights**
- **BotAttack Indicators:**
  - **Key features:** Success (`Status = 1`) in SSH (Port 2) or HTTP (Port 80) traffic, paired with non-browser user agents (`Wget/1.20.3`).
  - **SOC Action:** Monitor success rates on critical ports; flag repeated successful access from non-browser agents.

- **PortScan Indicators:**
  - **Key features:** Use of `nmap/7.80` (`User_Agent`) or ICMP (Protocol 0), paired with low payloads.
  - **SOC Action:** Block traffic from known scanning tools and investigate ICMP traffic with unusual payload patterns.

- **Normal Traffic Patterns:**
  - **Key features:** High-frequency HTTP/HTTPS traffic with standard user agents (`Mozilla/5.0`).
  - **SOC Action:** Establish baselines for normal traffic and flag deviations (e.g., unexpected payloads).

---

### 6. **Model Behavior Assessment**
- **Strengths:**
  - Clear separation between classes based on `User_Agent` and `Request_Type`.
  - Accurate detection of PortScan via `nmap/7.80` and low Payload_Size.
- **Weaknesses:**
  - **Overlap in `Payload_Size` and `Status`**: BotAttack and PortScan may share similar payload ranges (e.g., high Payload_Size in PortScan vs. low in BotAttack).
  - **Ambiguity in `User_Agent`**: Legitimate scripts (e.g., `Wget/1.20.3`) could be misclassified as BotAttack.
- **Decision Boundaries:**
  - The model likely distinguishes classes via hard thresholds (e.g., `User_Agent = 4` → PortScan).
  - However, subtle overlaps (e.g., `Port = 80` with both BotAttack and Normal) may reduce robustness.

---

### 7. **Improvement Suggestions**
1. **Feature Importance Visualization:**
   - Use SHAP values to visualize how each feature contributes to predictions, especially for ambiguous cases (e.g., `Wget/1.20.3` vs. `Mozilla/5.0`).

2. **Add Time-Based Features:**
   - Incorporate temporal patterns (e.g., rate of requests per port) to better distinguish BotAttack (bursty traffic) from Normal (steady traffic).

3. **Improve Class Separation:**
   - Use clustering (e.g., DBSCAN) to identify subgroups of traffic (e.g., BotAttack vs. script-based Normal) and refine training data.

4. **Enhance Interpretability with Rule-Based Models:**
   - Integrate a simple rule-based system (e.g., for `nmap/7.80` → PortScan) to improve transparency.

5. **Monitor `User_Agent` for Rogue Scripts:**
   - Label ambiguous user agents (e.g., `Wget/1.20.3`) as high-risk and flag them for manual review.
```

---

### gpt-oss:20b

**Flags:**
- ⚠️ **User_Agent Bias**: Ranks User_Agent as #1 importance
- ❌ **Incorrect Ranking**: Top-3 extracted: Port, User_Agent

```
**1. Model Context**
- **Algorithm & task**: Random‑Forest classifier trained to label each log entry as **BotAttack (0)**, **Normal (1)** or **PortScan (2)**.
- **Validation**: 99.7 % overall accuracy on the full test set (2 654 records).  The dataset was balanced via SMOTE and stratified 70/30 split, so each class is well represented during training.
- **Why this matters**: Because the model is already vetted for predictive performance, the goal is to translate its internal decision logic into actionable insight for SOC analysts rather than to tune accuracy.

---

**2. Feature Analysis**

| Rank | Feature | Reasoning for Importance |
|------|---------|--------------------------|
| **1** | **User_Agent** |
| | | Bot‑related tools (Nikto, nmap, Wget, curl) are *explicitly* encoded and routinely used by scanners and automated bots.  Analysts can immediately flag traffic from these agents.|
| **2** | **Port** |
| | | Malicious activity tends to target non‑standard or exploit‑specific ports.  The 31337 (Port = 11) and 4444 (Port = 8) ports are known command‑and‑control or back‑door listening points.  Port diversity is also a hallmark of port‑scanning.|
| **3** | **Request_Type** |
| | | Certain request types (SSH 5, Telnet 6, FTP 1) are common in compromise attempts or lateral movement.  HTTP/HTTPS traffic is usually benign unless paired with other red flags.|
| **4** | **Protocol** |
| | | Scanners often use TCP for reliability; ICMP (0) is used in ping‑based scans, while UDP (2) can be a sign of stealthy reconnaissance.|
| **5** | **Status** |
| | | Failure status (0) usually indicates an unsuccessful probe or denial‑of‑service attempt.  Successful traffic is more likely to be normal, except when coupled with malicious ports or agents.|
| **6** | **Payload_Size** |
| | | After z‑scoring, extreme values are still useful: very small packets may indicate DNS or ICMP pings; very large packets could hint at data exfiltration or payload‑heavy scans. |

> **Why this order?**
> 1) User agent is the clearest indicator of automated tools.
> 2) Ports encode the destination and intent.
> 3) Request type and protocol give context to how the connection is initiated.
> 4) Status and payload size are supplementary clues.

---

**3. Decision‑Pattern Hypotheses**

| Class | Typical Feature Combination | Rationale |
|-------|------------------------------|-----------|
| **BotAttack (0)** | *Port = 31337 or 4444 (or 8080/6657) ∧ User_Agent ∈ {Nikto, nmap, Wget, curl} ∧ Request_Type = 5 (SSH) or 6 (Telnet) ∧ Status = 0 (Failure) ∧ Large Payload |  Bots usually communicate on back‑door ports with a known client agent while trying to establish persistent shells.  Failure status may represent an attempted but blocked command. |
| **PortScan (2)** | *Port ∈ {0–11} (wide range) ∧ Request_Type ∈ {0 (DNS), 2 (HTTP), 5 (SSH)} ∧ Status = 0 (Failure) ∧ Small or moderate Payload |  Classic port‑scan: many different ports in quick succession, most probes fail, and request types are simple. |
| **Normal (1)** | *Port ∈ {80, 443} (5 or 7) ∧ Request_Type = 2 (HTTP) or 3 (HTTPS) ∧ User_Agent ∈ {Mozilla, curl} ∧ Status = 1 (Success) ∧ Payload ≈ mean |  Regular web traffic: HTTP/HTTPS over standard ports, common browsers or SDKs, successful requests, normal‑size payloads. |

> The Random Forest learns these patterns by splitting on thresholds over the encoded categorical values (e.g., "Port > 8?") and on numeric ranges of Payload_Size.  Because it is an ensemble, each tree may focus on a subset of these cues, boosting overall discriminative power.

---

**4. Instance‑Level Reasoning**

| # | Record | Predicted Class | Key Decisive Features |
|---|--------|-----------------|----------------------|
| 1 | `Port=2, Req=6, Proto=1, Payload=2.8, User_Agent=2, Status=0` | **0 – BotAttack** |
| | | *Port 2 (Telnet)* – mapped to the 1024‑range non‑standard ports used in some botnets.  <br>*User_Agent = 2 (Wget)* – a flagged automated client.  <br>*Payload = 2.8* >0 (after z‑scoring, a large positive value).  <br>*Status = 0* (failure) indicates the bot's probe did not succeed but the pattern is still characteristic. |
| 2 | `Port=5, Req=2, Proto=1, Payload=−0.3, User_Agent=0, Status=1` | **1 – Normal** |  Standard HTTP over port 80, "Mozilla" agent, successful request, payload around mean.  No red‑flag combinations. |
| 3 | `Port=2, Req=6, Proto=1, Payload=2.8, User_Agent=2, Status=0` | **0 – BotAttack** | Same as #1 – the same red‑flag cluster. |
| 4 | `Port=0, Req=0, Proto=0, Payload=−1.2, User_Agent=1, Status=0` | **2 – PortScan** |  Port 0 (common DNS ping), ICMP/UDP, failed status, very small payload – classic scan probe. |
| 5 | `Port=5, Req=2, Proto=1, Payload=−0.5, User_Agent=0, Status=1` | **1 – Normal** |  HTTP over port 80 with a browser – typical web request. |

> **How a tree might have decided**
> 1) The first split in many trees is usually "User_Agent == 11 (nmap)?"; if "yes" → 0 or 2.
> 2) If "no", it splits on "Port == 5 (80)?" → Normal branch, else further splits on Request_Type.
> 3) For the BotAttack cases, the *single* leaf that captures Port = 11 and User_Agent = 0 (Nikto) drives the output with a very high weight in the majority of trees.

---

**5. Cybersecurity Insights**

| Indicator | Class   | SOC Action |
|-----------|---------|-----------|
| **Unusual ports (31337, 4444, 8080, 6657)** | **BotAttack** |   - Flag for immediate investigation.<br> - Correlate with failed/blocked connections in firewall logs.<br> - Verify whether a legitimate service could legitimately use that port. |
| **Bot‑tool user agents (Nikto, nmap, Wget, curl)** | **BotAttack** |   - Check if the agent is in the *Allowed Binaries* list.<br> - Block or rate‑limit such traffic if it is not needed. |
| **Port‑scan signature ( > 5 distinct ports, all failing)** | **PortScan** |   - Trigger a "Port‑scan alert".<br> - Deploy honeypot or rate‑limit the source IP. |
| **Multiple simultaneous probes with Request_Type = DNS or SSH** | **PortScan** |   - Consider adding a **sequence‑level** "number of distinct ports in last 10 s" feature to sharpen the boundary. |

> SOC analysts can use the ranked list of red flags to triage alerts: first glance at the **User_Agent** and **Port**; if both point to bot‑like activity, pull up the Request_Type and Status; only then examine Payload_Size for confirmation.  This mirrors the natural human workflow.

---

**6. Model Behaviour Assessment**

- **Decision boundaries**
  - *Categorical splits*: e.g., `if Port > 8 -> more likely BotAttack/PortScan; else Normal`.
  - *Numeric splits*: e.g., `if Payload_Size > 1.5 -> BotAttack`, `Payload_Size < −1 -> PortScan`.
  - Because categorical variables are embedded as integers, the model actually splits on *ordinal thresholds* that correspond to "majority of port categories" or "specific agent codes", not on one‑hot encodings.

- **Potential trouble zones**
  1. **Overlap in User_Agent**: `User_Agent = 0 (Mozilla)` is common in both Normal and a small subset of benign SSH usage.  If a benign SSH connection is made from a normal browser, the model could mis‑classify it as **PortScan** or **BotAttack**.
  2. **Standard ports used by scans**: A sophisticated scanner may legitimately use port 80 or 443 (Ports = 5/7) with the Nikto agent; the decision path would then rely heavily on **User_Agent** and **Status**, a fragile boundary.
  3. **Payload_Size** is z‑scored; borderline values (≈ 0) might be assigned to either Normal or Attack depending on the tree ensemble, leading to confusion when the other features are ambiguous.

---

**7. Improvement Suggestions**

1. **Add Interpretability‑Built‑in Features**
   - **Permutation Feature Importance**: already gives a proxy ranking; publish it as a SOC quick‑reference chart.
   - **Partial‑Dependence Plots** for the most critical features (Port, User_Agent, Payload) – visualizing how the probability of each class changes across a feature's value.
   - **SHAP (SHapley Additive exPlanations)** values per instance – would let analysts see the contribution of each feature in a 2‑D plot (e.g., force plot).

2. **Enrich the Feature Set**
   - **Temporal burst metrics**: number of probes per 10 s, session duration, inter‑arrival time.
   - **Directionality**: inbound vs outbound or local‑host to public IP – port‑scans are usually inbound.
   - **Transport‑layer flags**: SYN/ACK patterns, RST usage, which help separate ICMP‑based scans from TCP scans.

3. **Model‑Architecture Tweaks**
   - **Balanced decision thresholds**: Use a calibrated probability threshold (e.g., 0.6) per class to guarantee a clear minimum confidence before labeling as "unknown".
   - **Cost‑aware splitting**: weight mis‑classifying BotAttack more heavily to avoid false negatives, which can be encoded in the RF via `class_weight`.

4. **Documentation & Collaboration**
   - **Feature‑label mapping**: publish a cheat‑sheet that translates the numeric codes back to human‑readable values (e.g., Port = 11 = 31337).
   - **Model‑behavior notebook**: a Jupyter script that loads the RF, prints feature importance tables and shows sample decision trees.  SOC analysts can review them to see which splits correspond to their known attack patterns.

5. **Operationalization**
   - **Alert‑to‑Ticket Workflow**: automatically enrich tickets with the top‑3 decisive feature values (e.g., "User_Agent = Nikto, Port = 31337, Status = 0") so analysts do not have to reverse‑engineer the classification.
   - **Baseline Drift Detection**: monitor the distribution of User_Agent and Port over time; an increasing count of flagged combinations could indicate evolving bot tools (e.g., new back‑door ports).

---

**Conclusion**

By aligning the **most descriptive features** (Port, User_Agent, Status) with concrete attack signatures, the existing Random Forest model can be translated into a rule‑based alerting layer that is transparent, explainable, and easy to integrate into current SOC operations. The steps above will help bridge the gap between automated ML outputs and human analysts' decision‑making process.
```

---

### qwen3:30b

**Flags:**
- ❌ **Incomplete Extraction**: Only partial response extracted
- No clear top-3 ranking extracted

```
### Structured Analysis: Network Intrusion Detection Model Behavior

**1. Model Context**
The Random Forest model achieves **99.7% test accuracy** on a 3-class intrusion detection task (BotAttack, Normal, PortScan), validated through a rigorous pipeline (data cleaning, SMOTE balancing, stratified splitting). Class distributions are balanced via SMOTE, ensuring robust representation. *Crucially, this analysis focuses solely on *interpretability* and *behavioral patterns*, not performance metrics.*

---

**2. Feature Analysis: Top Drivers of Predictions**
Ranked by observed influence in training data (Part 2) and prediction patterns (Part 3):

| Feature         | Top Rank | Cybersecurity Rationale                                                                 |
|-----------------|----------|---------------------------------------------------------------------------------------|
| **User_Agent**  | 1        | Directly identifies attack tools: `nmap` (4) = BotAttack/PortScan, `Nikto` (1) = BotAttack, `Mozilla` (0) = Normal traffic. |
| **Port**        | 2        | Attack-specific ports: `31337` (11) = BotAttack (common in scanners), `80` (5) = Normal, `8080` (10) = PortScan. |
| **Payload_Size**| 3        | BotAttacks show *significantly larger payloads* (mean > 2.5 std-dev) vs. Normal (mean ~0.6). PortScans are mixed. |
| **Request_Type**| 4        | `Telnet` (6) or `HTTP` (2) with `nmap` (User_Agent=4) = BotAttack; `HTTPS` (3) = Normal. |
| **Protocol**    | 5        | `TCP` (1) dominates scans; `UDP` (2) = PortScan; `ICMP` (0) = Normal. |
| **Status**      | 6        | `Failure` (0) = BotAttack (e.g., failed scans), `Success` (1) = Normal. [Response truncated...]
```

---

## Analysis Summary

The **without_XAI** experiment shows significant limitations in LLM analysis when SHAP/LIME data is not provided:

1. **Low Feature Grounding Accuracy (25%)** — Only qwen3:14b correctly identified the ground truth top-3 features (Port, Status, Payload_Size)

2. **Prevalent User_Agent Bias (75%)** — Three out of four models incorrectly elevated User_Agent to top importance, despite SHAP evidence showing near-zero importance (< 0.006)

3. **Semantic Reasoning Override** — LLMs relied on semantic intuition ("Nmap is a scanner tool, therefore User_Agent is important") rather than statistical patterns from the data

4. **Model Size Paradox** — Larger models (qwen3:30b) did not outperform smaller ones, suggesting that data context matters more than model size for this task