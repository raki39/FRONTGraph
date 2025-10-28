# 📖 Guia de Uso - ClickHouse + LangChain

## 🚀 Como Usar ClickHouse com o AgentGraph

### 1. Configuração Inicial

Certifique-se de que o ClickHouse está rodando:

```bash
# Docker
docker run -d --name clickhouse -p 8123:8123 clickhouse/clickhouse-server

# Ou localmente
clickhouse-server
```

### 2. Criar Conexão ClickHouse

Via API:

```bash
curl -X POST http://localhost:8000/api/connections \
  -H "Content-Type: application/json" \
  -d {
    "name": "Meu ClickHouse",
    "connection_type": "clickhouse",
    "clickhouse_config": {
      "host": "localhost",
      "port": 8123,
      "database": "default",
      "username": "default",
      "password": "",
      "secure": false
    }
  }
```

### 3. Usar com Agente

```python
from agentgraph.graphs.main_graph import AgentGraphManager

# Inicializar manager
manager = AgentGraphManager()

# Criar agente com ClickHouse
agent_id = manager.create_agent(
    name="Agente ClickHouse",
    connection_id=1,  # ID da conexão ClickHouse
    llm_provider="openai",
    model_name="gpt-4o-mini"
)

# Executar query
result = manager.run_agent(
    agent_id=agent_id,
    user_id=1,
    question="Quantos registros temos na tabela eventos?"
)

print(result)
```

### 4. Queries Suportadas

O agente suporta:

- ✅ SELECT simples
- ✅ Agregações (COUNT, SUM, AVG, etc)
- ✅ GROUP BY
- ✅ ORDER BY
- ✅ JOINs
- ✅ Subqueries
- ✅ Funções ClickHouse específicas

### 5. Exemplos de Perguntas

```
"Qual o total de vendas por categoria?"
"Quantos usuários ativos temos?"
"Qual é o produto mais vendido?"
"Mostre as vendas dos últimos 7 dias"
"Qual a receita média por cliente?"
```

## 🔧 Configuração Avançada

### Modo Tabela Única

Para restringir o agente a uma única tabela:

```python
agent_id = manager.create_agent(
    name="Agente ClickHouse - Vendas",
    connection_id=1,
    llm_provider="openai",
    model_name="gpt-4o-mini",
    single_table_mode=True,
    selected_table="vendas"
)
```

### Conexão Segura (HTTPS)

```python
clickhouse_config = {
    "host": "clickhouse.example.com",
    "port": 8443,
    "database": "analytics",
    "username": "user",
    "password": "password",
    "secure": True  # Usa HTTPS
}
```

### Pool de Conexões

A configuração padrão usa:
- `pool_timeout`: 30 segundos
- `pool_recycle`: 3600 segundos (1 hora)

Para customizar, edite `agentgraph/nodes/clickhouse_connection_node.py`:

```python
ch_engine = sa_create_engine(
    connection_uri,
    pool_timeout=60,  # Aumentar timeout
    pool_recycle=7200,  # Aumentar recycle
    echo=False
)
```

## 🧪 Teste de Conexão

```bash
cd agentgraph
python testes/test_clickhouse_integration.py
```

## 📊 Monitoramento

### Logs

Os logs mostram:
- ✅ Conexão estabelecida
- ✅ Tabelas detectadas
- ✅ Dialeto confirmado
- ✅ Queries executadas

### Exemplo de Log

```
[CLICKHOUSE_CONNECTION] SQLDatabase criado com sucesso
[CLICKHOUSE_CONNECTION] Tabelas encontradas: 5
[CLICKHOUSE_CONNECTION] Dialeto detectado: clickhouse
[SQL_AGENT] Criando agente em modo multi-tabela
[SQL_AGENT] Query executada com sucesso
```

## ⚠️ Troubleshooting

### Erro: "Authentication failed"

```
DB::Exception: default: Authentication failed
```

**Solução**: Verifique credenciais no `clickhouse_config`

### Erro: "Connection refused"

```
Connection refused at localhost:8123
```

**Solução**: Certifique-se de que ClickHouse está rodando

### Erro: "Unknown table"

```
DB::Exception: Unknown table expression identifier
```

**Solução**: Verifique se a tabela existe no banco

### Warnings sobre `information_schema`

**Não deve mais ocorrer** com a nova implementação usando `SQLDatabase(engine=...)`.

Se ainda ocorrer, verifique se está usando a versão corrigida dos arquivos.

## 🔄 Comparação: ClickHouse vs PostgreSQL

| Aspecto | ClickHouse | PostgreSQL |
|---------|-----------|-----------|
| Tipo | OLAP | OLTP |
| Melhor para | Análises | Transações |
| Agregações | Muito rápido | Rápido |
| Atualizações | Lento | Rápido |
| Compressão | Excelente | Boa |
| Integração | ✅ Funciona | ✅ Funciona |

## 📚 Recursos Adicionais

- [ClickHouse Docs](https://clickhouse.com/docs)
- [ClickHouse SQLAlchemy](https://github.com/ClickHouse/clickhouse-sqlalchemy)
- [LangChain SQLDatabase](https://python.langchain.com/docs/integrations/tools/sql_database)

## ✅ Checklist de Implementação

- [x] ClickHouse instalado e rodando
- [x] Credenciais configuradas
- [x] Conexão testada
- [x] Agente criado
- [x] Queries funcionando
- [x] Sem warnings sobre `information_schema`

## 🎉 Pronto!

Sua integração ClickHouse + LangChain está funcionando corretamente!

