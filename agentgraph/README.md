# 🤖 AgentGraph - Plataforma Multi-Agente LangGraph

Uma plataforma inteligente de agentes especializados que utiliza LangGraph para processar consultas em linguagem natural, com suporte a múltiplos provedores de LLM e arquitetura modular extensível.

## ✨ Funcionalidades Principais

### 🎯 **Sistema Multi-Agente**
- **Agente SQL**: Consultas inteligentes em dados CSV/SQLite
- **Detecção Automática**: Identifica tipo de processamento necessário
- **Arquitetura Extensível**: Preparado para PDF, MySQL, Gráficos e ML

### 🧠 **Múltiplos Provedores LLM**
- **OpenAI**: GPT-4o, GPT-4o-mini, o3-mini
- **Anthropic**: Claude-3.5-Sonnet com tool-calling
- **Google**: Gemini-1.5-Pro, Gemini-2.0-Flash
- **HuggingFace**: LLaMA 70B, LLaMA 8B, DeepSeek-R1 (refinamento)

### 🔄 **LangGraph Avançado**
- Arquitetura baseada em nós especializados
- Processamento assíncrono e paralelo
- Gerenciamento inteligente de objetos não-serializáveis
- Sistema de retry com backoff exponencial

### 🔍 **Observabilidade com LangSmith**
- Rastreamento completo de execuções LangGraph
- Monitoramento de performance em tempo real
- Debug avançado de agentes e fluxos
- Análise de custos e uso de tokens
- Dashboards de observabilidade integrados

### 🌐 **Interface Moderna**
- Interface Gradio responsiva e centralizada
- Configurações separadas do chat principal
- Upload de CSV com processamento automático
- Histórico detalhado e logs estruturados

### 💾 **Sistema Inteligente**
- Cache otimizado com verificação de hits
- Processamento genérico de CSV com detecção automática
- Modo avançado com refinamento de respostas
- Verbose ativo para debugging

## 📁 Estrutura do Projeto

```
agentgraph/
├── app.py                     # 🚀 Entry point: Gradio + LangGraph
├── graphs/
│   └── main_graph.py          # 🔄 StateGraph principal com roteamento
├── nodes/                     # 🎯 Nós especializados
│   ├── csv_processing_node.py # 📊 Processamento genérico de CSV
│   ├── database_node.py       # 🗄️ Operações de banco de dados
│   ├── query_node.py          # 🔍 Processamento de consultas
│   ├── refinement_node.py     # ✨ Refinamento de respostas
│   ├── cache_node.py          # 💾 Gerenciamento de cache
│   └── agent_node.py          # 🤖 Coordenação geral
├── agents/                    # 🧠 Agentes especializados
│   ├── sql_agent.py           # 📝 Agente SQL multi-provedor
│   └── tools.py               # 🛠️ Ferramentas e detecção
├── utils/                     # ⚙️ Utilitários
│   ├── database.py            # 🗃️ Funções de banco de dados
│   ├── config.py              # 📋 Configurações centralizadas
│   └── object_manager.py      # 🎛️ Gerenciador de objetos
├── uploaded_data/             # 📂 Arquivos CSV enviados
├── requirements.txt           # 📦 Dependências
├── README.md                  # 📖 Documentação
├── architecture.md            # 🏗️ Arquitetura detalhada
└── .env                       # 🔐 Variáveis de ambiente
```

## 🚀 Instalação Rápida

### 1. **Clone o Repositório**
```bash
git clone https://github.com/seu-usuario/agentgraph.git
cd agentgraph
```

### 2. **Instale as Dependências**
```bash
pip install -r requirements.txt
```

### 3. **Configure as Variáveis de Ambiente**
Crie/edite o arquivo `.env`:

```env
# 🔑 API Keys (pelo menos uma é obrigatória)
HUGGINGFACE_API_KEY=hf_your_key_here
OPENAI_API_KEY=sk-your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
GOOGLE_API_KEY=your_google_api_key_here

# 🔍 LangSmith - Observabilidade (OPCIONAL)
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=agentgraph-project

# 🗄️ Configurações de Banco
SQL_DB_PATH=data.db
DEFAULT_CSV_PATH=tabela.csv
UPLOAD_DIR=uploaded_data

# 🤖 Configurações de Modelo
DEFAULT_MODEL=GPT-4o-mini
MAX_ITERATIONS=40
TEMPERATURE=0

# 🌐 Configurações do Gradio
GRADIO_SHARE=False
GRADIO_PORT=7860
```

### 4. **Execute a Aplicação**

#### **🖥️ Modo Local (Desenvolvimento)**
```bash
python app.py
```

#### **🐳 Modo Docker (Produção)**
```bash
# Windows
run-docker.bat

# Linux/Mac
./run-docker.sh
```

🎉 **Pronto!** Acesse:
- **AgentGraph**: `http://localhost:7860`
- **Flower Dashboard**: `http://localhost:5555` (apenas Docker)

### **🔧 Diferenças entre Modos**

| Característica | Local (Windows) | Docker (Produção) |
|----------------|-----------------|-------------------|
| **Redis** | Iniciado automaticamente | Container Redis |
| **Celery Workers** | 1 worker (single-thread) | 1 worker x 8 concurrency |
| **Paralelismo** | Limitado (Windows) | Completo (Linux) |
| **PostgreSQL** | `localhost` | `host.docker.internal` |
| **Flower Dashboard** | ❌ | ✅ |
| **Uso** | Desenvolvimento | Produção/Compartilhamento |

### 5. **Configure LangSmith (Opcional)**
Para habilitar observabilidade avançada:

1. **Crie conta** em [LangSmith](https://smith.langchain.com/)
2. **Obtenha API Key** no dashboard
3. **Configure no .env**:
   ```env
   LANGSMITH_API_KEY=lsv2_pt_your_key_here
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=agentgraph-project
   ```
4. **Reinicie** a aplicação

✨ **Com LangSmith você terá**:
- 🔍 Rastreamento completo de execuções
- 📊 Dashboards de performance
- 🐛 Debug avançado de agentes
- 💰 Análise de custos de tokens
- 📈 Métricas de uso em tempo real

## 💡 Como Usar

### 🎯 **Fluxo Básico**
1. **Acesse** `http://localhost:7860`
2. **Selecione** o modelo LLM desejado (OpenAI, Anthropic ou HuggingFace)
3. **Upload** de CSV (opcional) ou use dados padrão
4. **Digite** perguntas em linguagem natural
5. **Receba** respostas detalhadas com SQL e análises

### 🤖 **Modelos Disponíveis**

| Provedor | Modelo | Uso | Características |
|----------|--------|-----|-----------------|
| **OpenAI** | GPT-4o | AgentSQL | Tools + Verbose ativo |
| **OpenAI** | GPT-4o-mini | AgentSQL | Modelo padrão, rápido |
| **OpenAI** | o3-mini | AgentSQL | Sem temperature |
| **Anthropic** | Claude-3.5-Sonnet | AgentSQL | Tool-calling + Retry |
| **HuggingFace** | LLaMA 70B | Refinamento | Opcional |
| **HuggingFace** | LLaMA 8B | Refinamento | Opcional |
| **HuggingFace** | DeepSeek-R1 | Refinamento | Opcional |

### 📊 **Exemplos de Perguntas**
```
"Quais são os produtos com maior preço?"
"Mostre as vendas por categoria"
"Qual a média de idade dos clientes?"
"Produtos com estoque baixo"
"Análise de tendências mensais"
```

## 🧪 Verificação e Testes

### **Verificação Rápida**
```bash
# Verifica configuração LangSmith
python check_langsmith_setup.py

# Teste completo de integração
python test_langsmith_integration.py
```

### **Arquivos de Teste Disponíveis**
- `check_langsmith_setup.py` - Verificação rápida de configuração
- `test_langsmith_integration.py` - Teste completo de integração
- `test_new_architecture.py` - Teste da arquitetura LangGraph
- `test_graph_functionality.py` - Teste de funcionalidades de gráficos

## 🛠️ Tecnologias

### **Core Framework**
- **LangGraph**: Orquestração de agentes com nós especializados
- **LangChain**: Framework de LLM com tool-calling
- **LangSmith**: Observabilidade e rastreamento avançado
- **Gradio**: Interface web moderna e responsiva

### **Processamento de Dados**
- **SQLAlchemy**: ORM para banco de dados SQLite
- **Pandas**: Processamento e análise de dados CSV
- **SQLite**: Banco de dados embarcado

### **Provedores LLM**
- **OpenAI**: GPT-4o, GPT-4o-mini, o3-mini
- **Anthropic**: Claude-3.5-Sonnet
- **HuggingFace**: LLaMA, DeepSeek via Together AI

### **Utilitários**
- **AsyncIO**: Processamento assíncrono
- **Logging**: Sistema de logs estruturados
- **Retry**: Backoff exponencial para rate limiting

## 🏗️ Arquitetura Atual

### **Fluxo Principal**
```
Pergunta → Detecção de Tipo → AgentSQL → Refinamento (Opcional) → Resposta
```

### **Nós Especializados**
- **🔍 Query Node**: Detecção e processamento de consultas
- **🗄️ Database Node**: Operações de banco e CSV
- **💾 Cache Node**: Gerenciamento de cache e histórico
- **✨ Refinement Node**: Melhoria de respostas (modo avançado)
- **🤖 Agent Node**: Coordenação geral do fluxo

### **Características Técnicas**
- ✅ **Async/Await**: Processamento não-bloqueante
- ✅ **Multi-Provedor**: OpenAI, Anthropic, HuggingFace
- ✅ **Tool-Calling**: Ferramentas SQL nativas
- ✅ **Verbose Ativo**: Debugging detalhado
- ✅ **Rate Limiting**: Retry automático para APIs
- ✅ **Object Manager**: Gerenciamento de objetos não-serializáveis

## 🚀 Roadmap - Implementações Futuras

### **🎯 Curto Prazo (1-2 meses)**

#### **📄 Agente PDF**
```python
# Funcionalidades planejadas:
- Extração de texto de PDFs
- OCR para documentos escaneados
- Análise de estrutura de documentos
- Busca semântica em conteúdo
- Integração com LangGraph
```

#### **📊 Agente de Gráficos**
```python
# Funcionalidades planejadas:
- Geração automática de visualizações
- Matplotlib, Plotly, Seaborn
- Gráficos baseados em consultas SQL
- Exportação em múltiplos formatos
```

### **🎯 Médio Prazo (3-6 meses)**

#### **🗄️ Agente MySQL**
```python
# Funcionalidades planejadas:
- Conexões externas MySQL/PostgreSQL
- Queries complexas com JOINs
- Gerenciamento de múltiplas bases
- Pool de conexões
```

#### **🤖 Agente de ML/Previsões**
```python
# Funcionalidades planejadas:
- Modelos de Machine Learning
- Análise de séries temporais
- Previsões automáticas
- Integração com scikit-learn
```

### **🎯 Longo Prazo (6+ meses)**

#### **🔄 Sistema de Pipelines**
```python
# Funcionalidades planejadas:
- Combinação de múltiplos agentes
- Workflows customizáveis
- Processamento em lote
- Agendamento de tarefas
```

#### **🌐 API REST**
```python
# Funcionalidades planejadas:
- Endpoints para cada agente
- Autenticação e autorização
- Rate limiting por usuário
- Documentação OpenAPI
```

#### **☁️ Integração Cloud**
```python
# Funcionalidades planejadas:
- Deploy em AWS/Azure/GCP
- Armazenamento em nuvem
- Escalabilidade automática
- Monitoramento avançado
```

## 📈 Exemplos de Uso

### **Análise de Vendas**
```
Usuário: "Quais produtos tiveram maior crescimento no último trimestre?"

Sistema:
1. 🔍 Detecta: consulta SQL
2. 🧠 Claude analisa estrutura da tabela
3. 📝 Gera SQL otimizado
4. 📊 Executa e analisa resultados
5. 💬 Resposta detalhada em português
```

### **Relatório Financeiro**
```
Usuário: "Mostre um resumo das receitas por categoria"

Sistema:
1. 🔍 Identifica: agregação de dados
2. 🧠 GPT-4o cria query com GROUP BY
3. 📊 Executa com LIMIT 20
4. ✨ Refinamento opcional com LLaMA
5. 📈 Resposta com insights
```

## 🤝 Contribuição

### **Como Contribuir**
1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### **Áreas de Contribuição**
- 🐛 **Bug fixes** e melhorias
- 📄 **Documentação** e exemplos
- 🧪 **Testes** automatizados
- 🎯 **Novos agentes** (PDF, MySQL, etc.)
- 🎨 **Interface** e UX
- ⚡ **Performance** e otimizações

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## 🙏 Agradecimentos

- **LangChain** e **LangGraph** pela framework excepcional
- **Anthropic**, **OpenAI** e **HuggingFace** pelos modelos LLM
- **Gradio** pela interface web intuitiva
- Comunidade open source pelas contribuições

---

**⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!**

**🔗 Links Úteis:**
- [Documentação Detalhada](architecture.md)
- [Exemplos de Uso](examples/)
- [Issues e Sugestões](https://github.com/seu-usuario/agentgraph/issues)
- [Discussões](https://github.com/seu-usuario/agentgraph/discussions)
