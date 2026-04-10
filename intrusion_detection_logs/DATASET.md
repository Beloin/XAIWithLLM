# Network Intrusion Detection Dataset

## Source

Dataset from Kaggle: [Intrusion Detection Logs (Normal, Bot, Scan)](https://www.kaggle.com/datasets/developerghost/intrusion-detection-logs-normal-bot-scan/data)

## Description

Network traffic log entries for intrusion detection classification.

## Classes

| Class | Label | Description |
|-------|-------|-------------|
| BotAttack | 1 | Botnet command-and-control traffic |
| Normal | 0 | Legitimate network activity |
| PortScan | 2 | Reconnaissance/scanning activity |

## Features

| Feature | Type | Description |
|---------|------|-------------|
| Source_IP | IP | Source IP address (dropped in pipeline) |
| Destination_IP | IP | Destination IP address (dropped in pipeline) |
| Port | Numeric | Port number (e.g., 22, 80, 443) |
| Request_Type | Categorical | HTTP, HTTPS, FTP, SMTP, DNS, SSH, Telnet |
| Protocol | Categorical | TCP, UDP, ICMP |
| Payload_Size | Numeric | Size of payload in bytes |
| User_Agent | Categorical | User agent string (Mozilla/5.0, curl/7.68.0, nmap/7.80, Nikto/2.1.6, Wget/1.20.3) |
| Status | Categorical | Success, Failure |
| Intrusion | Target | Numeric class label (0, 1, 2) |
| Scan_Type | Categorical | Additional label (Normal, BotAttack, PortScan) |

## ML Pipeline

1. Drop IP columns (Source_IP, Destination_IP) — not predictive for this task
2. Label encode categorical features (Request_Type, Protocol, User_Agent, Status)
3. StandardScaler on Payload_Size
4. SMOTE class balancing
5. 70/30 stratified train/test split
6. Random Forest classifier

## Model Performance

- **Accuracy:** ~99.7%
- **Classes well separated** — suitable for XAI explanation task

## Key Findings from SHAP Analysis

| Class | Top-1 Feature | Top-2 Feature | Top-3 Feature |
|-------|---------------|---------------|---------------|
| BotAttack | Port (0.244) | Status (0.129) | Payload_Size (0.091) |
| Normal | Port (0.273) | Payload_Size (0.184) | Status (0.195) |
| PortScan | Payload_Size (0.261) | Status (0.066) | Port (0.030) |

**Critical insight:** User_Agent has SHAP importance < 0.006 for all classes, despite containing semantically meaningful strings (nmap, curl, Nikto — security tools). This is the central thesis evidence: LLMs overvalue semantic features when analyzing raw data, but XAI corrects this bias.

## File

- `Network_logs.csv` — Main dataset file

## Usage in Project

The dataset is used to train a Random Forest classifier, then SHAP TreeExplainer generates ground truth feature importance rankings. LLMs are tasked to explain the model's behavior with and without XAI data.