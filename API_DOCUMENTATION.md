# 🚀 AgentAPI - Documentação Completa

Sistema de agentes inteligentes para análise de dados com processamento SQL automatizado usando LangChain SQL Agent e FastAPI.

**Base URL (dev):** `http://localhost:8000`
**Autenticação:** Bearer JWT
**Banco:** PostgreSQL | **Filas:** Celery/Redis | **Cache:** Redis
**Processamento:** LangChain SQL Agent com suporte a múltiplos modelos LLM

## 🎯 Visão Geral

A AgentAPI permite criar agentes inteligentes que analisam dados através de linguagem natural. Os usuários fazem upload de datasets (CSV), criam conexões de banco de dados e configuram agentes que respondem perguntas em linguagem natural gerando e executando queries SQL automaticamente.

### 🔄 Fluxo Principal
1. **Upload de Dataset** → Converte CSV para SQLite
2. **Criação de Conexão** → Configura acesso ao banco
3. **Criação de Agente** → Define modelo LLM e parâmetros
4. **Execução** → Pergunta em linguagem natural → SQL → Resposta

## 📋 Índice

- [🏥 Health Check](#-health-check)
- [🔐 Autenticação](#-autenticação)
- [📊 Datasets](#-datasets)
- [🔗 Conexões](#-conexões)
- [🤖 Agentes](#-agentes)
- [🚀 Execuções (Runs)](#-execuções-runs)
- [📝 Modelos de Dados](#-modelos-de-dados)
- [🎯 Códigos de Status](#-códigos-de-status)
- [🔧 Modelos de IA Disponíveis](#-modelos-de-ia-disponíveis)
- [🧪 Testes](#-testes)

---

## 🏥 Health Check

### Verificar Status da API
```http
GET /healthz
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🔐 Autenticação

A API utiliza **JWT (JSON Web Tokens)** para autenticação. Todos os endpoints (exceto health check, login e registro) requerem um token válido no header `Authorization: Bearer <token>`.

### 📝 Registro de Usuário
```http
POST /auth/register
Content-Type: application/json

{
  "nome": "João Silva",
  "email": "joao@example.com",
  "password": "senha123"
}
```

**Response:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "email": "joao@example.com",
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 🔑 Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=joao@example.com&password=senha123
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 👤 Informações do Usuário Atual
```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "email": "joao@example.com",
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## 📊 Datasets

Gerenciamento de datasets (arquivos CSV) que são convertidos automaticamente para SQLite.

### 📁 Upload de Dataset
```http
POST /datasets/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <arquivo.csv>
nome: "Dados de Vendas 2024"
```

**Response:**
```json
{
  "id": 1,
  "nome": "Dados de Vendas 2024",
  "filename": "vendas_2024.csv",
  "db_uri": "sqlite:////shared-data/dataset_1/data.db",
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 📋 Listar Datasets
```http
GET /datasets/
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "id": 1,
    "nome": "Dados de Vendas 2024",
    "filename": "vendas_2024.csv",
    "db_uri": "sqlite:////shared-data/dataset_1/data.db",
    "owner_user_id": 1,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### 🔍 Obter Dataset Específico
```http
GET /datasets/{dataset_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "nome": "Dados de Vendas 2024",
  "filename": "vendas_2024.csv",
  "db_uri": "sqlite:////shared-data/dataset_1/data.db",
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## 🔗 Conexões

Configuração de conexões de banco de dados para os agentes.

### 🔌 Criar Conexão SQLite (baseada em dataset)
```http
POST /connections/
Authorization: Bearer <token>
Content-Type: application/json

{
  "tipo": "sqlite",
  "dataset_id": 1
}
```

### 🔌 Criar Conexão PostgreSQL
```http
POST /connections/
Authorization: Bearer <token>
Content-Type: application/json

{
  "tipo": "postgres",
  "pg_dsn": "postgresql://user:pass@host:5432/dbname"
}
```

**Response:**
```json
{
  "id": 1,
  "tipo": "sqlite",
  "db_uri": "sqlite:////shared-data/dataset_1/data.db",
  "pg_dsn": null,
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 📋 Listar Conexões
```http
GET /connections/
Authorization: Bearer <token>
```

### 🔍 Obter Conexão Específica
```http
GET /connections/{connection_id}
Authorization: Bearer <token>
```

### 🗑️ Deletar Conexão
```http
DELETE /connections/{connection_id}
Authorization: Bearer <token>
```

---

## 🤖 Agentes

Criação e gerenciamento de agentes inteligentes para análise de dados.

### 🛠️ Criar Agente
```http
POST /agents/
Authorization: Bearer <token>
Content-Type: application/json

{
  "nome": "Agente de Vendas",
  "connection_id": 1,
  "selected_model": "gpt-3.5-turbo",
  "top_k": 10,
  "include_tables_key": "*",
  "advanced_mode": false,
  "processing_enabled": true,
  "refinement_enabled": false,
  "single_table_mode": false,
  "selected_table": null
}
```

**Response:**
```json
{
  "id": 1,
  "nome": "Agente de Vendas",
  "connection_id": 1,
  "selected_model": "gpt-3.5-turbo",
  "top_k": 10,
  "include_tables_key": "*",
  "advanced_mode": false,
  "processing_enabled": true,
  "refinement_enabled": false,
  "single_table_mode": false,
  "selected_table": null,
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 📋 Listar Agentes
```http
GET /agents/
Authorization: Bearer <token>
```

### 🔍 Obter Agente Específico
```http
GET /agents/{agent_id}
Authorization: Bearer <token>
```

### 🔄 Atualizar Agente
```http
PUT /agents/{agent_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "nome": "Agente de Vendas Atualizado",
  "selected_model": "gpt-4",
  "top_k": 15
}
```

### 🗑️ Deletar Agente
```http
DELETE /agents/{agent_id}
Authorization: Bearer <token>
```

---

## 🚀 Execuções (Runs)

Sistema de execução assíncrona de consultas em linguagem natural.

### ▶️ Executar Agente
```http
POST /agents/{agent_id}/run
Authorization: Bearer <token>
Content-Type: application/json

{
  "question": "Qual é o total de vendas por categoria?"
}
```

**Response:**
```json
{
  "id": 1,
  "agent_id": 1,
  "user_id": 1,
  "question": "Qual é o total de vendas por categoria?",
  "task_id": "abc123-def456-ghi789",
  "status": "queued",
  "sql_used": null,
  "result_data": null,
  "execution_ms": null,
  "result_rows_count": null,
  "error_type": null,
  "created_at": "2024-01-15T10:30:00Z",
  "finished_at": null
}
```

### 🔍 Consultar Status de Execução
```http
GET /runs/{run_id}
Authorization: Bearer <token>
```

**Response (em execução):**
```json
{
  "id": 1,
  "status": "running",
  "question": "Qual é o total de vendas por categoria?",
  "sql_used": null,
  "result_data": null,
  "execution_ms": null
}
```

**Response (concluída):**
```json
{
  "id": 1,
  "status": "success",
  "question": "Qual é o total de vendas por categoria?",
  "sql_used": "SELECT categoria, SUM(valor) as total FROM tabela GROUP BY categoria ORDER BY total DESC LIMIT 10;",
  "result_data": "As vendas por categoria são:\n1. Eletrônicos: R$ 125.000\n2. Roupas: R$ 89.500\n3. Casa: R$ 67.200",
  "execution_ms": 2450,
  "result_rows_count": 3,
  "created_at": "2024-01-15T10:30:00Z",
  "finished_at": "2024-01-15T10:30:02Z"
}
```

### 📋 Listar Todas as Execuções do Usuário
```http
GET /runs/
Authorization: Bearer <token>
```

### 📊 Listar Execuções de um Agente
```http
GET /agents/{agent_id}/runs
Authorization: Bearer <token>
```

### 🎯 Status de Execução

| Status | Descrição |
|--------|-----------|
| `queued` | Execução na fila, aguardando processamento |
| `running` | Execução em andamento |
| `success` | Execução concluída com sucesso |
| `failure` | Execução falhou (erro no SQL ou processamento) |

---

## 📝 Modelos de Dados

### 👤 User
```json
{
  "id": 1,
  "nome": "João Silva",
  "email": "joao@example.com",
  "ativo": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 📊 Dataset
```json
{
  "id": 1,
  "nome": "Dados de Vendas",
  "filename": "vendas.csv",
  "db_uri": "sqlite:////shared-data/dataset_1/data.db",
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 🔗 AgentConnection
```json
{
  "id": 1,
  "tipo": "sqlite",
  "db_uri": "sqlite:////shared-data/dataset_1/data.db",
  "pg_dsn": null,
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 🤖 Agent
```json
{
  "id": 1,
  "nome": "Agente de Vendas",
  "connection_id": 1,
  "selected_model": "gpt-3.5-turbo",
  "top_k": 10,
  "include_tables_key": "*",
  "advanced_mode": false,
  "processing_enabled": true,
  "refinement_enabled": false,
  "single_table_mode": false,
  "selected_table": null,
  "owner_user_id": 1,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 🚀 Run
```json
{
  "id": 1,
  "agent_id": 1,
  "user_id": 1,
  "question": "Pergunta em linguagem natural",
  "task_id": "uuid-da-task-celery",
  "status": "success",
  "sql_used": "SELECT * FROM tabela LIMIT 10;",
  "result_data": "Resposta em linguagem natural",
  "execution_ms": 2450,
  "result_rows_count": 10,
  "error_type": null,
  "created_at": "2024-01-15T10:30:00Z",
  "finished_at": "2024-01-15T10:30:02Z"
}
```

---

## 🎯 Códigos de Status

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `201` | Criado com sucesso |
| `400` | Erro de validação/dados inválidos |
| `401` | Não autenticado |
| `403` | Não autorizado |
| `404` | Recurso não encontrado |
| `422` | Erro de validação de schema |
| `500` | Erro interno do servidor |

---

## 🔧 Modelos de IA Disponíveis

| Modelo | Descrição | Velocidade | Qualidade |
|--------|-----------|------------|-----------|
| `gpt-3.5-turbo` | Rápido e eficiente | ⚡⚡⚡ | ⭐⭐⭐ |
| `gpt-4` | Mais preciso | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| `gpt-4o-mini` | Otimizado | ⚡⚡⚡ | ⭐⭐⭐⭐ |

### 🎛️ Parâmetros de Configuração

- **`top_k`**: Limite de resultados nas queries SQL (padrão: 10)
- **`include_tables_key`**: Tabelas a incluir ("*" para todas)
- **`advanced_mode`**: Modo avançado de processamento
- **`processing_enabled`**: Habilitar processamento adicional
- **`refinement_enabled`**: Habilitar refinamento de queries
- **`single_table_mode`**: Modo de tabela única
- **`selected_table`**: Tabela específica (se single_table_mode=true)

---

## 🧪 Testes

### 🐍 Teste Completo (Python)
```bash
python test_api_complete.py
```

### 🎯 Teste Específico de Runs
```bash
python test_runs_detailed.py
```

### 🐚 Teste Rápido (Bash)
```bash
./test_api_quick.sh
```

### 📋 Exemplo de Uso Completo

```python
import requests

# 1. Registro
response = requests.post('http://localhost:8000/auth/register', json={
    "nome": "João Silva",
    "email": "joao@example.com",
    "password": "senha123"
})

# 2. Login
response = requests.post('http://localhost:8000/auth/login', data={
    "username": "joao@example.com",
    "password": "senha123"
}, headers={"Content-Type": "application/x-www-form-urlencoded"})

token = response.json()['access_token']
headers = {"Authorization": f"Bearer {token}"}

# 3. Upload dataset
with open('dados.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/datasets/upload',
        files={'file': f},
        data={'nome': 'Meus Dados'},
        headers=headers
    )
dataset_id = response.json()['id']

# 4. Criar conexão
response = requests.post('http://localhost:8000/connections/',
    json={"tipo": "sqlite", "dataset_id": dataset_id},
    headers=headers
)
connection_id = response.json()['id']

# 5. Criar agente
response = requests.post('http://localhost:8000/agents/', json={
    "nome": "Meu Agente",
    "connection_id": connection_id,
    "selected_model": "gpt-3.5-turbo",
    "top_k": 10
}, headers=headers)
agent_id = response.json()['id']

# 6. Executar pergunta
response = requests.post(f'http://localhost:8000/agents/{agent_id}/run',
    json={"question": "Quantos registros existem na base?"},
    headers=headers
)
run_id = response.json()['id']

# 7. Consultar resultado
import time
while True:
    response = requests.get(f'http://localhost:8000/runs/{run_id}', headers=headers)
    run = response.json()

    if run['status'] == 'success':
        print(f"Resposta: {run['result_data']}")
        print(f"SQL: {run['sql_used']}")
        break
    elif run['status'] == 'failure':
        print(f"Erro: {run['error_type']}")
        break

    time.sleep(2)
```

---

## 🔄 Fluxo de Desenvolvimento

### 🐳 Docker
```bash
# Subir serviços
docker compose up -d

# Executar migrações
docker compose exec api python -m api.db.migrate --seed

# Ver logs
docker compose logs -f api
docker compose logs -f worker
```

### 🗄️ Banco de Dados
```bash
# Conectar ao PostgreSQL
docker compose exec postgres psql -U agent -d agentgraph

# Executar migração
python migrate.py
```

---

**🎉 A AgentAPI está pronta para integração com qualquer frontend que precise de análise inteligente de dados!**

**Documentação atualizada em:** 29 de Agosto de 2024

