# 🧪 Sistema de Testes Massivos - AgentGraph

Sistema completo para testes de consistência e performance dos agentes SQL com paralelismo otimizado.

## 🎯 **Funcionalidades**

### **✅ Configuração Dinâmica**
- **Pergunta personalizada**: Define a query que será testada
- **Múltiplos grupos**: Diferentes configurações de modelos
- **Processing Agent**: Ativa/desativa com modelo específico
- **Iterações configuráveis**: 1-100 testes por grupo

### **⚡ Execução Paralela**
- **Paralelismo otimizado**: Até 8 workers simultâneos
- **Controle de recursos**: Semáforos para evitar sobrecarga
- **Progress tracking**: Acompanhamento em tempo real
- **Estimativa de tempo**: Tempo restante calculado dinamicamente

### **🔍 Validação Inteligente**
- **Validação LLM**: Análise automática com GPT/Claude
- **Validação por palavra-chave**: Busca por conteúdo específico
- **Pontuação 0-100**: Score detalhado de qualidade
- **Análise de consistência**: Taxa de respostas similares

### **📊 Relatórios Completos**
- **Dashboard interativo**: Visualização em tempo real
- **Múltiplas abas**: Resumo, grupos, resultados individuais
- **Exportação Excel**: Relatórios detalhados em XLSX
- **Métricas avançadas**: Taxa de acerto, consistência, performance

## 🚀 **Como Usar**

### **1. Instalação**
```bash
# Instalar dependências
pip install -r testes/requirements.txt

# Verificar configuração do AgentGraph
python -c "from utils.config import validate_config; validate_config()"
```

### **2. Inicialização**
```bash
# IMPORTANTE: Execute da raiz do projeto!
# Método 1: Script automático (RECOMENDADO)
python run_massive_tests.py

# Método 2: Direto (apenas se necessário)
python testes/app_teste.py
```

### **3. Acesso**
- **URL**: http://localhost:5001
- **Interface**: HTML responsiva
- **Compatibilidade**: Todos os navegadores modernos

## 📋 **Fluxo de Uso**

### **Passo 1: Configurar Pergunta**
```
1. Digite a pergunta que será testada
2. Clique em "Criar Sessão"
3. Sessão será criada com ID único
```

### **Passo 2: Adicionar Grupos**
```
1. Selecione modelo do SQL Agent
2. Ative Processing Agent (opcional)
3. Escolha modelo do Processing Agent
4. Defina número de iterações (1-100)
5. Clique em "Adicionar Grupo"
6. Repita para criar múltiplos grupos
```

### **Passo 3: Configurar Validação**
```
Método LLM (Recomendado):
- Análise automática da qualidade
- Pontuação 0-100
- Razão detalhada

Método Palavra-chave:
- Busca por texto específico
- Validação binária (contém/não contém)
```

### **Passo 4: Executar Testes**
```
1. Clique em "Executar Testes"
2. Acompanhe progresso em tempo real
3. Visualize métricas durante execução
4. Aguarde conclusão automática
```

### **Passo 5: Analisar Resultados**
```
Aba Resumo:
- Métricas gerais
- Melhor grupo
- Grupo mais consistente

Aba Por Grupo:
- Taxa de sucesso por grupo
- Comparação de modelos
- Performance detalhada

Aba Individual:
- Cada teste executado
- Detalhes completos
- Query SQL gerada
```

## 📊 **Métricas Calculadas**

### **Taxa de Sucesso**
- **Cálculo**: (Testes sem erro / Total de testes) × 100
- **Indica**: Estabilidade do modelo
- **Ideal**: > 90%

### **Taxa de Validação**
- **Cálculo**: (Respostas válidas / Total de testes) × 100
- **Indica**: Qualidade das respostas
- **Ideal**: > 80%

### **Consistência de Resposta**
- **Cálculo**: (Respostas idênticas / Total de respostas) × 100
- **Indica**: Determinismo do modelo
- **Ideal**: > 70%

### **Consistência SQL**
- **Cálculo**: (Queries idênticas / Total de queries) × 100
- **Indica**: Estabilidade da geração SQL
- **Ideal**: > 80%

### **Tempo Médio**
- **Cálculo**: Soma dos tempos / Número de testes
- **Indica**: Performance do modelo
- **Ideal**: < 10s

## 🔧 **Configurações Avançadas**

### **Paralelismo**
```python
# Em test_runner.py
max_workers = 8  # Ajuste conforme sua máquina
```

### **Validação LLM**
```python
# Em test_validator.py
validator_model = "gpt-4o-mini"  # Modelo para validação
temperature = 0.1  # Baixa para consistência
```

### **Timeouts**
```python
# Em app_teste.py
status_polling = 2000  # ms entre verificações
```

## 📁 **Estrutura de Arquivos**

```
testes/
├── app_teste.py              # Servidor Flask principal
├── test_runner.py            # Executor de testes paralelos
├── test_validator.py         # Sistema de validação
├── report_generator.py       # Gerador de relatórios
├── run_tests.py             # Script de inicialização
├── requirements.txt         # Dependências
├── README.md               # Esta documentação
├── templates/
│   └── index.html          # Interface HTML
├── static/
│   └── js/
│       └── app.js          # JavaScript da interface
└── reports/                # Relatórios gerados
    ├── *.xlsx             # Relatórios Excel
    ├── *.json             # Dados brutos
    └── *.html             # Resumos HTML
```

## 🎯 **Casos de Uso**

### **Comparação de Modelos**
```
Objetivo: Qual modelo SQL é mais consistente?
Configuração:
- Grupo 1: GPT-4o + Processing Agent
- Grupo 2: Claude-3.5-Sonnet + Processing Agent  
- Grupo 3: GPT-4o sem Processing Agent
- 20 iterações cada
```

### **Impacto do Processing Agent**
```
Objetivo: Processing Agent melhora a qualidade?
Configuração:
- Grupo 1: GPT-4o-mini COM Processing Agent
- Grupo 2: GPT-4o-mini SEM Processing Agent
- Mesma pergunta, 50 iterações cada
```

### **Teste de Stress**
```
Objetivo: Como o sistema se comporta sob carga?
Configuração:
- 5 grupos diferentes
- 100 iterações cada
- Monitorar tempo de resposta
```

## 🚨 **Limitações e Considerações**

### **Rate Limits das APIs**
- **OpenAI**: ~3000 requests/minuto
- **Anthropic**: ~1000 requests/minuto
- **Ajuste**: Reduza max_workers se necessário

### **Recursos do Sistema**
- **RAM**: ~100MB por worker ativo
- **CPU**: Intensivo durante execução
- **Rede**: Dependente das APIs LLM

### **Custos**
- **Validação LLM**: ~$0.001 por teste
- **Testes massivos**: Pode gerar custos significativos
- **Recomendação**: Comece com poucos testes

## 🔍 **Troubleshooting**

### **Erro: "Dependência faltando"**
```bash
pip install -r testes/requirements.txt
```

### **Erro: "AgentGraph não configurado"**
```bash
# Verifique .env com APIs configuradas
cp .env.example .env
# Edite .env com suas chaves
```

### **Erro: "Porta 5001 em uso"**
```python
# Em app_teste.py, altere:
app.run(port=5002)  # Use porta diferente
```

### **Performance lenta**
```python
# Reduza workers em test_runner.py:
max_workers = 4  # Ao invés de 8
```

## 📈 **Próximas Funcionalidades**

- [ ] **Testes agendados**: Execução automática
- [ ] **Comparação histórica**: Evolução ao longo do tempo
- [ ] **Alertas**: Notificações de degradação
- [ ] **API REST**: Integração com CI/CD
- [ ] **Dashboards avançados**: Gráficos interativos

## 🤝 **Contribuição**

Para melhorias ou bugs:
1. Documente o problema/sugestão
2. Teste em ambiente isolado
3. Mantenha compatibilidade com AgentGraph
4. Atualize documentação se necessário

---

**🎉 Sistema pronto para uso! Execute `python run_massive_tests.py` da raiz do projeto e comece a testar!**
