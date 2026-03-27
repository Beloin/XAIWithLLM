#!/usr/bin/env python
# coding: utf-8

# # Explicabilidade via LLM Local (Ollama)
# 
# Este notebook utiliza modelos LLM locais via Ollama para gerar explicações interpretáveis de um modelo de detecção de intrusão.
# O código de pré-processamento é idêntico ao notebook LLM original para garantir reprodutibilidade.

# In[2]:


# Importação de todas as bibliotecas que serão utilizadas
import pandas as pd
import numpy as np
import json
import time
from openai import OpenAI
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix


# In[ ]:


# ==========================
# CONFIGURAÇÃO DO OLLAMA
# ==========================
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Lista de modelos a serem consultados (name: nome do modelo no Ollama, size: tier do prompt)
models = [
    {"name": "glm-4.7-flash:latest",  "size": "small"},
    {"name": "qwen-opus-9b:latest",    "size": "small"},
    {"name": "gpt-oss:20b",            "size": "medium"},
    {"name": "qwen-opus-27b:latest",   "size": "large"},
    {"name": "qwen3:30b",              "size": "large"},
]


# # Leitura e Pré-processamento dos Dados

# In[4]:


# Define o dataset que será utilizado
df = pd.read_csv("./Network_logs.csv")


# In[5]:


# Cria uma cópia do dataset original
networkData = df.copy()

# Descarta as features IP de Origem/Destino (alta cardinalidade) e Intrusion (evitar overfitting)
networkData.drop(['Source_IP', 'Destination_IP', 'Intrusion'], axis=1, inplace=True)
networkData.head(5)


# In[6]:


# Codificação para as features com valores não numéricos
categorical_cols = ['Request_Type', 'Protocol', 'User_Agent', 'Status', 'Port']
for col in categorical_cols:
    networkData[col] = networkData[col].astype('category')

for col in categorical_cols:
    print(f"{col} categories: {networkData[col].cat.categories.tolist()}")

for col in categorical_cols:
    networkData[col] = networkData[col].cat.codes


# In[7]:


# Codificação da variável Alvo (y): BotAttack -> 0; Normal -> 1; PortScan -> 2
target_encoder = LabelEncoder()
networkData['Scan_Type_Label'] = target_encoder.fit_transform(networkData['Scan_Type'])

label_mapping = dict(zip(target_encoder.classes_, target_encoder.transform(target_encoder.classes_)))
print("Label Mapping:", label_mapping)

networkData.drop(['Scan_Type'], axis=1, inplace=True)
networkData.head(5)


# In[8]:


# Normalização do Payload_Size
scaler = StandardScaler()
networkData['Payload_Size'] = scaler.fit_transform(networkData[['Payload_Size']])

# Define features (X) e alvo (y)
X = networkData.drop(['Scan_Type_Label'], axis=1)
y = networkData['Scan_Type_Label']

# Particiona: 70% treino, 30% teste (estratificado)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y)


# In[9]:


# Aplica SMOTE para equilibrar classes no treinamento
smote = SMOTE()
X_train, y_train = smote.fit_resample(X_train, y_train)
y_train = pd.Series(y_train.values.ravel(), name='Scan_Type_Label')

print('SMOTE aplicado com sucesso.\n')
print('Nova distribuição:\n')
print(y_train.value_counts())


# # Treinamento do Modelo

# In[10]:


# Treina Random Forest
model = RandomForestClassifier()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

acc = accuracy_score(y_test, y_pred)
print(f"Acurácia: {acc:.4f}")
print(classification_report(y_test, y_pred))


# # Construção dos Metadados para o LLM

# In[11]:


# ==========================
# DESCRIÇÃO DAS COLUNAS
# ==========================
column_description = {
    "Port": "Porta utilizada na comunicação",
    "Request_Type": "Tipo de requisição",
    "Protocol": "Protocolo da Camada de Transporte (TCP, UDP ou ICMP)",
    "Payload_Size": "Tamanho do pacote (informação útil)",
    "User_Agent": "Agente utilizado na comunicação",
    "Status": "Status da requisição (Success ou Failure)",
    "Scan_Type_Label": "Classificação: Normal (1), BotAttack (0) ou PortScan (2)"
}

# ==========================
# EQUIVALÊNCIA CATEGORIA -> CÓDIGO NUMÉRICO
# ==========================
category_encoding = {
    "Request_Type": {"DNS": 0, "FTP": 1, "HTTP": 2, "HTTPS": 3, "SMTP": 4, "SSH": 5, "Telnet": 6},
    "Protocol": {"ICMP": 0, "TCP": 1, "UDP": 2},
    "User_Agent": {"Mozilla/5.0": 0, "Nikto/2.1.6": 1, "Wget/1.20.3": 2, "curl/7.68.0": 3, "nmap/7.80": 4, "python-requests/2.25.1": 5},
    "Status": {"Failure": 0, "Success": 1},
    "Port": {21: 0, 22: 1, 23: 2, 25: 3, 53: 4, 80: 5, 135: 6, 443: 7, 4444: 8, 6667: 9, 8080: 10, 31337: 11},
    "Scan_Type_Label": {"BotAttack": 0, "Normal": 1, "PortScan": 2}
}

# Estatísticas do Dataset
stats = networkData.describe(include="all").to_string()

# Informações do Modelo
model_info = {
    "model_type": "Random Forest",
    "task": "Detecção de intrusão a partir de log. Cada entrada é classificada como: BotAttack (0) ou Normal (1) ou PortScan (2)",
    "target_variable": "Scan_Type_Label",
    "features": list(X.columns)
}

# Amostra dos dados de treinamento (50 registros para tier large)
train_sample_50 = X_train.sample(50, random_state=42)
train_sample_50["Scan_Type_Label"] = y_train.loc[train_sample_50.index]
train_sample_json_50 = train_sample_50.to_json(orient="records")

# Amostra das previsões vs real (50 registros para tier large)
pred_sample = pd.DataFrame({"real": y_test, "predicted": y_pred})
pred_sample_json_50 = pred_sample.sample(50, random_state=42).to_json(orient="records")


# # Funções de Construção de Prompts e Controle do Ollama

# In[12]:


def build_prompt(size, model_info, column_description, category_encoding, stats,
                 train_sample_json_50, pred_sample_json_50, X_train, y_train, pred_sample):
    """Constroi system prompt e user prompt adaptados ao tamanho do modelo."""

    # Prepara amostras reduzidas para tiers menores
    if size == "small":
        n_samples = 20
    elif size == "medium":
        n_samples = 30
    else:
        n_samples = 50

    if n_samples < 50:
        ts = X_train.sample(n_samples, random_state=42)
        ts["Scan_Type_Label"] = y_train.loc[ts.index]
        train_json = ts.to_json(orient="records")
        pred_json = pred_sample.sample(n_samples, random_state=42).to_json(orient="records")
    else:
        train_json = train_sample_json_50
        pred_json = pred_sample_json_50

    # --- SYSTEM PROMPTS ---
    if size == "small":
        system_msg = (
            "Voce e um especialista em Machine Learning e seguranca cibernetica. "
            "Analise dados de um modelo de deteccao de intrusao e explique seu comportamento de forma concisa e objetiva."
        )
    elif size == "medium":
        system_msg = (
            "Voce e um especialista em Machine Learning, Explainable AI e Seguranca Cibernetica. "
            "Sua tarefa e analisar um modelo de aprendizado de maquina treinado para deteccao de intrusao "
            "em logs de rede e fornecer uma explicacao detalhada de seu comportamento. "
            "Estruture sua resposta em secoes claras."
        )
    else:  # large
        system_msg = (
            "Voce e um especialista em Inteligencia Artificial Explicavel (XAI) e Seguranca Cibernetica. "
            "Sua tarefa e analisar detalhadamente um modelo de aprendizado de maquina treinado para "
            "deteccao de intrusao a partir de logs de rede. Voce deve interpretar o comportamento do modelo, "
            "identificar padroes nos dados, avaliar a qualidade das previsoes e fornecer insights acionaveis "
            "de seguranca. Estruture sua resposta em secoes claras e numeradas, adequadas para um relatorio "
            "tecnico de aprendizado de maquina."
        )

    # --- USER PROMPTS ---
    mi = json.dumps(model_info, indent=2, ensure_ascii=False)
    cd = json.dumps(column_description, indent=2, ensure_ascii=False)
    ce = json.dumps(category_encoding, indent=2, ensure_ascii=False)

    if size == "small":
        user_prompt = f"""Analise o modelo de deteccao de intrusao abaixo.

INFORMACOES DO MODELO:
{mi}

DESCRICAO DAS COLUNAS:
{cd}

CODIFICACAO CATEGORICA:
{ce}

AMOSTRA DE TREINAMENTO ({n_samples} registros):
{train_json}

CLASSIFICACAO REAL vs PREVISTA ({n_samples} registros):
{pred_json}

TAREFA - responda de forma concisa:
1. Quais features sao mais influentes para cada classe (Normal, BotAttack, PortScan)?
2. Que padroes voce identifica nos dados de treinamento e previsoes?
3. Comente sobre possiveis classificacoes incorretas na amostra.
4. Forneca insights de seguranca cibernetica com base nos padroes dos logs."""

    elif size == "medium":
        user_prompt = f"""Analise o modelo de deteccao de intrusao descrito abaixo.

=========================
INFORMACOES DO MODELO
=========================
{mi}

=========================
DESCRICAO DAS COLUNAS
=========================
{cd}

=========================
CODIFICACAO CATEGORICA
=========================
{ce}

=========================
ESTATISTICAS DO DATASET
=========================
{stats}

=========================
AMOSTRA DE TREINAMENTO ({n_samples} registros)
=========================
{train_json}

=========================
CLASSIFICACAO REAL vs PREVISTA ({n_samples} registros)
=========================
{pred_json}

=========================
TAREFA
=========================
Forneca uma analise detalhada incluindo:
1. Interpretacao global e local do comportamento do modelo.
2. Quais features sao mais influentes para cada classe (Normal, BotAttack, PortScan).
3. Padroes ou correlacoes identificados no dataset.
4. Analise da amostra de previsao - possiveis classificacoes incorretas.
5. Como as codificacoes categoricas podem influenciar o modelo.
6. Insights de seguranca cibernetica com base nos padroes dos logs.
7. Sugestoes de melhorias para o modelo ou dataset."""

    else:  # large
        user_prompt = f"""Voce e especialista em Inteligencia Artificial Explicavel (XAI) e Seguranca Cibernetica.
Sua tarefa e analisar um modelo de aprendizado de maquina treinado e fornecer uma explicacao detalhada de seu comportamento.

=========================
INFORMACOES DO MODELO
=========================
{mi}

=========================
DESCRICAO DAS COLUNAS
=========================
{cd}

=========================
CODIFICACAO: CATEGORIA -> VALOR NUMERICO
=========================
{ce}

=========================
ESTATISTICA DO DATASET
=========================
{stats}

=========================
AMOSTRA DOS DADOS DE TREINAMENTO ({n_samples} registros)
=========================
{train_json}

=========================
AMOSTRA DA CLASSIFICACAO REAL vs CLASSIFICACAO DO MODELO ({n_samples} registros)
=========================
{pred_json}

=========================
TAREFA
=========================
Forneca uma analise detalhada da explicabilidade do modelo, incluindo:

1. Interpretacao global e local do comportamento do modelo.
2. Quais caracteristicas parecem ser mais influentes na previsao de classificacao:
   - Normal
   - BotAttack
   - PortScan
3. Identifique possiveis padroes ou correlacoes no conjunto de dados.
4. Analise a amostra de previsao e comente sobre possiveis classificacoes incorretas.
5. Explique como as codificacoes categoricas podem influenciar o comportamento do modelo.
6. Forneca insights de seguranca cibernetica com base nos padroes detectados nos logs.
7. Sugira possiveis melhorias para o modelo ou conjunto de dados.

Sua explicacao deve ser tecnica, porem clara, estruturada em secoes e adequada para um relatorio de aprendizado de maquina."""

    return system_msg, user_prompt


# # Execução: Consulta a Cada Modelo Ollama

# In[13]:


# Verifica quais modelos estão disponíveis no Ollama
get_ipython().system('ollama list')


# In[14]:


models


# In[ ]:


# ==========================
# LOOP PRINCIPAL: CONSULTA A CADA MODELO
# ==========================
client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
results = {}
timings = {}
previous_model = None

for model_cfg in models:
    model_name = model_cfg["name"]
    model_size = model_cfg["size"]

    # Para o modelo anterior para liberar VRAM
    if previous_model:
        get_ipython().system('ollama stop $previous_model')
        time.sleep(5)

    system_msg, user_prompt = build_prompt(
        model_size, model_info, column_description,
        category_encoding, stats,
        train_sample_json_50, pred_sample_json_50,
        X_train, y_train, pred_sample
    )

    print(f"\nConsultando modelo: {model_name} (tier: {model_size})...")

    t_start = time.time()
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4096 if model_size == "small" else 8192
        )
        result_text = response.choices[0].message.content
        results[model_name] = result_text
        elapsed = time.time() - t_start
        timings[model_name] = elapsed
        print(f"  Concluido: {len(result_text)} chars em {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - t_start
        timings[model_name] = elapsed
        results[model_name] = f"ERRO: {str(e)}"
        print(f"  Erro: {e} ({elapsed:.1f}s)")

    previous_model = model_name

# Para o ultimo modelo
if previous_model:
    get_ipython().system('ollama stop $previous_model')

print("\nTodos os modelos foram consultados.\n")
print("Tempo por modelo:")
for name, t in timings.items():
    print(f"  {name}: {t:.1f}s")


# # Resultados: Explicações por Modelo

# In[16]:


# ==========================
# EXIBIÇÃO DOS RESULTADOS
# ==========================
for model_name, result in results.items():
    print(f"\n{'='*60}")
    print(f"MODELO: {model_name}")
    print(f"{'='*60}\n")
    print(result)
    print()


# In[17]:


# ==========================
# SALVAR RESULTADOS EM ARQUIVO JSON (opcional)
# ==========================
with open("resultados_ollama_llm.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("Resultados salvos em resultados_ollama_llm.json")

