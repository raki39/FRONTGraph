# 📚 DOCUMENTAÇÃO: SISTEMA DE CHAT SESSIONS

## 🎯 VISÃO GERAL

O sistema de Chat Sessions permite gerenciar conversas persistentes entre usuários e agentes de IA, com suporte a paginação, filtros e processamento assíncrono via Celery.

## 🏗️ ARQUITETURA

```
Cliente → FastAPI Router → Chat Sessions/Messages/Runs → PostgreSQL
                      ↓
                 LangGraph → Celery Workers → History Capture → Messages → pgvector
```

## 📊 MODELOS DE DADOS

### 💬 Chat Sessions
- **id**: Identificador único
- **user_id**: Usuário proprietário
- **agent_id**: Agente utilizado
- **title**: Título da conversa
- **status**: active/archived
- **total_messages**: Contador de mensagens
- **last_activity**: Última atividade
- **context_summary**: Resumo do contexto

### 📝 Messages
- **id**: Identificador único
- **chat_session_id**: Sessão proprietária
- **run_id**: Run que gerou a mensagem
- **role**: user/assistant
- **content**: Conteúdo da mensagem
- **sql_query**: Query SQL utilizada (apenas assistant)
- **sequence_order**: Ordem na conversa

### 🔍 Message Embeddings
- **message_id**: Referência à mensagem
- **embedding**: Vetor 1536 dimensões (OpenAI)

## 🚀 ENDPOINTS

### 📋 1. LISTAR SESSÕES (PAGINADO)
```http
GET /chat-sessions/
```

**Parâmetros:**
- `page` (int): Número da página (padrão: 1)
- `per_page` (int): Itens por página (padrão: 20, máx: 50)
- `agent_id` (int): Filtrar por agente específico
- `status` (str): Filtrar por status (padrão: "active")
- `search` (str): Buscar por título
- `min_messages` (int): Mínimo de mensagens

**Resposta:**
```json
{
  "sessions": [
    {
      "id": 174,
      "title": "Conversa de Teste",
      "last_message": "A idade média é 30 anos.",
      "messages_count": 8,
      "updated_at": "2025-10-07T21:31:00Z",
      "status": "active",
      "agent_id": 75
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 76,
    "total_pages": 4,
    "has_next": true,
    "has_prev": false
  }
}
```

**Exemplos:**
```bash
# Todas as sessões do usuário
GET /chat-sessions/?page=1&per_page=10

# Sessões de um agente específico
GET /chat-sessions/?agent_id=75&page=1&per_page=10

# Sessões ativas com busca
GET /chat-sessions/?status=active&search=teste&page=1&per_page=5

# Combinação de filtros
GET /chat-sessions/?agent_id=75&status=active&min_messages=5&page=1&per_page=10
```

### 🔍 2. DETALHES DA SESSÃO
```http
GET /chat-sessions/{id}
```

**Resposta:**
```json
{
  "id": 174,
  "user_id": 1,
  "agent_id": 75,
  "title": "Conversa de Teste",
  "created_at": "2025-10-07T21:30:48Z",
  "last_activity": "2025-10-07T21:31:00Z",
  "total_messages": 8,
  "status": "active",
  "context_summary": null,
  "last_message": "A idade média é 30 anos."
}
```

### 💬 3. MENSAGENS DA SESSÃO (PAGINADO)
```http
GET /chat-sessions/{id}/messages
```

**Parâmetros:**
- `page` (int): Número da página (padrão: 1)
- `per_page` (int): Mensagens por página (padrão: 20, máx: 100)

**Resposta:**
```json
{
  "messages": [
    {
      "id": 617,
      "chat_session_id": 174,
      "run_id": 264,
      "role": "assistant",
      "content": "Temos 3 registros na tabela.",
      "sql_query": "SELECT COUNT(*) FROM tabela;",
      "created_at": "2025-10-07T21:30:56Z",
      "sequence_order": 2,
      "message_metadata": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 8,
    "total_pages": 1
  },
  "session_info": {
    "id": 174,
    "title": "Conversa de Teste",
    "total_messages": 8
  }
}
```

### ➕ 4. CRIAR SESSÃO
```http
POST /chat-sessions/
```

**Body:**
```json
{
  "agent_id": 75,
  "title": "Nova Conversa"
}
```

### ✏️ 5. ATUALIZAR SESSÃO
```http
PUT /chat-sessions/{id}
```

**Body:**
```json
{
  "title": "Título Atualizado",
  "status": "archived"
}
```

### 🗑️ 6. DELETAR SESSÃO
```http
DELETE /chat-sessions/{id}
```

## 🔄 FLUXO DE FUNCIONAMENTO

### 1. 🎯 CRIAÇÃO DE CONVERSA
1. Cliente faz POST /chat-sessions/
2. API valida agente e usuário
3. Cria sessão no PostgreSQL
4. Retorna dados da sessão

### 2. 💬 PROCESSAMENTO DE MENSAGEM
1. Cliente faz POST /agents/{id}/run
2. API envia para LangGraph
3. LangGraph processa via Celery Worker
4. Worker executa SQL e gera resposta
5. History Capture salva mensagens no banco
6. Atualiza estatísticas da sessão
7. Retorna resultado para cliente

### 3. 📊 CONSULTA DE MENSAGENS
1. Cliente faz GET /chat-sessions/{id}/messages
2. API consulta banco com paginação
3. Retorna mensagens + metadata

## ⚡ CARACTERÍSTICAS TÉCNICAS

### 🚀 PERFORMANCE
- **Paginação**: Máximo 50 sessões ou 100 mensagens por página
- **Índices**: Otimizados para user_id, agent_id, status
- **Async**: Processamento paralelo via Celery (4 workers)
- **Cache**: Embeddings gerados assincronamente

### 🔒 SEGURANÇA
- **Autenticação**: JWT obrigatório
- **Autorização**: Usuário só acessa suas próprias sessões
- **Validação**: Agente deve pertencer ao usuário
- **Sanitização**: Inputs validados via Pydantic

### 📈 ESCALABILIDADE
- **Horizontal**: Múltiplos workers Celery
- **Vertical**: Paginação eficiente
- **Storage**: pgvector para embeddings
- **Monitoring**: Logs estruturados

## 🎯 CASOS DE USO

### 📱 FRONTEND

#### Dashboard do Usuário:
```javascript
// Listar últimas conversas
GET /chat-sessions/?page=1&per_page=10&status=active

// Buscar conversas
GET /chat-sessions/?search=SQL&page=1&per_page=5
```

#### Página do Agente:
```javascript
// Conversas de um agente
GET /chat-sessions/?agent_id=75&page=1&per_page=20

// Estatísticas
GET /chat-sessions/?agent_id=75&min_messages=10
```

#### Chat Interface:
```javascript
// Carregar mensagens
GET /chat-sessions/174/messages?page=1&per_page=50

// Criar nova conversa
POST /chat-sessions/ { agent_id: 75, title: "Nova conversa" }
```

### 📊 ANALYTICS

#### Engajamento:
```javascript
// Conversas com muita interação
GET /chat-sessions/?min_messages=20&page=1&per_page=100

// Conversas por período (via created_at)
GET /chat-sessions/?page=1&per_page=50
```

## 🔧 CONFIGURAÇÃO

### Environment Variables:
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Pagination
MAX_SESSIONS_PER_PAGE=50
MAX_MESSAGES_PER_PAGE=100
DEFAULT_SESSIONS_PER_PAGE=20
DEFAULT_MESSAGES_PER_PAGE=20
```

### Docker Compose:
```yaml
services:
  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/agentapi
      - CELERY_BROKER_URL=redis://redis:6379/0
  
  worker:
    build: .
    command: celery -A agentgraph.tasks worker --loglevel=info --concurrency=4
  
  postgres:
    image: pgvector/pgvector:pg15
  
  redis:
    image: redis:7-alpine
```

## ✅ CHECKLIST DE DEPLOY

- ✅ **Migrations**: Tabelas criadas
- ✅ **Índices**: Performance otimizada
- ✅ **Workers**: Celery configurado
- ✅ **Monitoring**: Logs estruturados
- ✅ **Tests**: Cobertura completa
- ✅ **Documentation**: API docs geradas
- ✅ **Security**: JWT + validações
- ✅ **Backup**: Estratégia definida

## 🚀 STATUS

**SISTEMA PRONTO PARA PRODUÇÃO!** 🎉

Todos os testes passaram com sucesso:
- ✅ 8 mensagens corretas (sem duplicação)
- ✅ SQL queries nas mensagens do assistant
- ✅ Paginação funcionando perfeitamente
- ✅ Filtros por agente e status
- ✅ CRUD completo de sessões
- ✅ Processamento assíncrono via Celery
- ✅ Todos os endpoints validados
