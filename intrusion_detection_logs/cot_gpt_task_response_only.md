# EXPLICAÇÃO DO MODELO

### Resumo da tarefa e do modelo

* **Tarefa:** classificar cada log em BotAttack (0), Normal (1) ou PortScan (2).
* **Modelo:** Random Forest em features tabulares (Port, Request_Type, Protocol, Payload_Size, User_Agent, Status).
* **Codificação:** todas as categorias foram mapeadas para inteiros (label encoding). Payload_Size está padronizado.
* **Explicabilidade:** valores SHAP fornecidos são importâncias médias absolutas por classe (quanto cada feature, em média, desloca a predição para aquela classe, independentemente do sentido do efeito).

---

## 1) Quais features são mais relevantes em cada classe (segundo SHAP)

Importâncias relativas (maior → menor; entre parênteses, magnitude média SHAP):

### Classe Normal (1)

1. Port (0.096)
2. Payload_Size (0.048)
3. Status (0.040)
4. Request_Type (0.002)
5. User_Agent (0.002)
6. Protocol (0.002)

* **Interpretação:** a decisão "Normal" é fortemente influenciada pela porta utilizada, seguida do tamanho de payload e do status (Success/Failure). As demais variáveis têm influência pequena.

### Classe BotAttack (0)

1. Port (0.081)
2. Payload_Size (0.031)
3. Status (0.023)
4. Request_Type (0.003)
5. User_Agent (0.002)
6. Protocol (0.002)

* **Interpretação:** semelhante à classe Normal, mas com menor peso de Payload_Size e Status do que em Normal; "Port" permanece como principal fator.

### Classe PortScan (2)

1. Payload_Size (0.061)
2. Status (0.019)
3. Port (0.014)
4. User_Agent (0.001)
5. Request_Type (0.0005)
6. Protocol (0.0004)

* **Interpretação:** aqui o principal determinante é Payload_Size, seguido pelo Status. "Port" tem peso muito menor do que nas outras classes.

---

### Observação importante:

os valores acima indicam o quanto cada feature importa, em média, para a predição daquela classe. Eles não informam o sentido do efeito (por exemplo, "payload alto" aumentar ou diminuir a probabilidade). Para saber a direção, seria necessário um gráfico de dependência SHAP ou análise por faixas de valores.

---

## 2) Diferenças entre as classes

### Papel de Port:

* Muito relevante em Normal e BotAttack; pouco relevante em PortScan.
* Isso indica que o modelo associa padrões de portas a tráfego normal e a ataques de bots, mas não utiliza tanto portas para diferenciar PortScan.

### Papel de Payload_Size:

* É o fator dominante para PortScan e relevante, mas secundário, em Normal; menor ainda em BotAttack.
* O modelo associa faixas "extremas" de tamanho de payload com PortScan com mais força do que com outros rótulos.

### Papel de Status:

* Tem alta influência em Normal, influência moderada em BotAttack e relevância significativa em PortScan (embora menor que Payload_Size).
* O modelo usa o desfecho da requisição (Success/Failure) como sinal importante de normalidade e, em menor medida, de ataque.

### Protocol, Request_Type e User_Agent:

* Baixa importância em todas as classes, sugerindo que pouco acrescentam além da informação já capturada por Port, Status e Payload_Size.
* Isso pode ocorrer porque "Port" já carrega muito do contexto do serviço (HTTP 80, HTTPS 443, etc.), tornando Protocol/Request_Type relativamente redundantes.
* User_Agent tem baixa importância média global, mesmo contendo valores associados a scanners (por exemplo, nmap, Nikto), indicando que o modelo dá mais peso a sinais de tráfego do que à identificação do agente.

---

## 3) Interpretação no contexto de cibersegurança (associações, não causalidade)

### Normal

* Associação forte com Port e Status sugere que o modelo diferencia comunicações consideradas normais a partir de portas de serviços típicos e requisições com sucesso.
* Payload_Size também contribui, possivelmente distinguindo volumes de dados "esperados" de padrões atípicos. Sem a direção, não podemos afirmar que tamanhos de payload têm alto poder de discriminação dentro do conjunto marcado como Normal.

### BotAttack

* Port e Status dominam a decisão, assim como em Normal, mas com um peso relativamente menor de Payload_Size.
* Isso sugere que o modelo associa determinados conjuntos de portas e padrões de sucesso/fracasso das requisições a exemplos rotulados como BotAttack. O baixo peso de User_Agent indica que o modelo, globalmente, depende pouco de strings de agente para decidir BotAttack, ao menos neste dataset.

### PortScan

* Payload_Size é o principal determinante, seguido por Status. Em amostras do dataset, muitas entradas rotuladas como PortScan exibem payload padronizado negativo (abaixo da média) e Status=Failure, isso é consistente com o uso do par (payload "extremo", falha) como forte sinal para esta classe. Reforçando: esta é uma associação observada, não uma relação causal.
* A baixa influência de Port sugere que, para PortScan, o modelo não precisa da identificação de portas específicas para diferenciar, apoiando-se mais nos padrões do conteúdo/tamanho e desfecho da tentativa.

---

## Conclusão

* Em termos de explicabilidade global, o modelo aprende associações fortes entre:

  * Port e Status para distinguir Normal e BotAttack;
  * Payload_Size (e Status) para distinguir PortScan.
* Protocol, Request_Type e User_Agent têm papel globalmente pequeno neste dataset.
* Essas associações são coerentes com padrões comuns observados em logs de rede, mas não implicam causalidade. A direção dos efeitos (ex.: payload maior ou menor favorecendo uma classe) deve ser confirmada com análises SHAP de dependência ou segmentações por faixas.