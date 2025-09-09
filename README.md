# AgentAPI - Sistema de Agentes Inteligentes

Sistema completo de agentes inteligentes com processamento de dados, análise SQL e geração de gráficos usando LangGraph, FastAPI e Celery.

## 📁 Estrutura do Projeto

```
agentAPI/
├── agentgraph/          # Sistema principal de agentes com LangGraph
├── api/                 # API REST com FastAPI
├── worker/              # Worker para processamento distribuído
├── docker-compose.api.yml
└── API_DOCUMENTATION.md
```

## 🚀 Componentes Principais

### AgentGraph
Sistema de agentes inteligentes baseado em LangGraph para:
- Processamento de dados CSV
- Análise SQL automatizada
- Geração de gráficos e visualizações
- Interface web com Gradio

### API
API REST construída com FastAPI para:
- Autenticação e autorização
- Gerenciamento de usuários e empresas
- Controle de datasets e conexões
- Execução de runs de processamento

### Worker
Sistema de workers distribuídos usando Celery para:
- Processamento assíncrono de tarefas
- Escalabilidade horizontal
- Monitoramento com Flower

## 🛠️ Tecnologias Utilizadas

- **LangGraph**: Orquestração de agentes
- **LangChain**: Framework para LLMs
- **FastAPI**: API REST moderna
- **Celery**: Processamento distribuído
- **Redis**: Cache e message broker
- **PostgreSQL**: Banco de dados principal
- **Docker**: Containerização
- **Gradio**: Interface web

## 📋 Pré-requisitos

- Python 3.10+
- Docker e Docker Compose
- PostgreSQL
- Redis

## 🚀 Como Executar

### Usando Docker Compose

```bash
# Executar toda a stack
docker-compose -f docker-compose.api.yml up -d

# Executar apenas o agentgraph
cd agentgraph
docker-compose up -d
```

### Execução Local

1. **Instalar dependências**:
```bash
# AgentGraph
cd agentgraph
pip install -r requirements.txt

# API
cd ../api
pip install -r requirements.txt
```

2. **Configurar variáveis de ambiente**:
```bash
cp .env.example .env
# Editar .env com suas configurações
```

3. **Executar os serviços**:
```bash
# Redis (necessário)
redis-server

# AgentGraph
cd agentgraph
python run.py

# API
cd api
uvicorn main:app --reload

# Worker
celery -A tasks worker --loglevel=info
```

## 📚 Documentação

- [Documentação da API](API_DOCUMENTATION.md)
- [Arquitetura do AgentGraph](agentgraph/ARCHITECTURE.md)
- [Setup do Celery](agentgraph/CELERY_SETUP.md)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Equipe

Desenvolvido pela equipe ZentechAI-Dev
