# ClickHouse + LangChain SQLDatabase Integration - Solução Correta

## 🎯 Problema Identificado

Quando usando `SQLDatabase.from_uri()` com ClickHouse, o LangChain tenta refletir metadados usando `information_schema` (padrão PostgreSQL), que **não existe no ClickHouse**. Isso causa warnings e erros:

```
[DATABASE] Erro ao verificar tabela COLUMNS: Unknown table expression identifier 'COLUMNS'
[DATABASE] Erro ao verificar tabela TABLES: Unknown table expression identifier 'TABLES'
[DATABASE] Erro ao verificar tabela VIEWS: Unknown table expression identifier 'VIEWS'
```

## ✅ Solução Implementada

**NÃO usar**: `SQLDatabase.from_uri(uri)`
**USAR**: `SQLDatabase(engine=engine)` com `create_engine()`

### Por quê?

- `SQLDatabase.from_uri()` automaticamente chama `metadata.reflect()` que tenta acessar `information_schema`
- `SQLDatabase(engine=engine)` cria a instância sem reflection automática
- ClickHouse usa `system.tables` para metadados, não `information_schema`

## 📝 Implementação

### ClickHouse Connection Node
```python
from sqlalchemy import create_engine as sa_create_engine
from langchain_community.utilities import SQLDatabase
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
    warnings.filterwarnings("ignore", category=Warning)
    
    ch_engine = sa_create_engine(
        connection_uri,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    
    # IMPORTANTE: Usar SQLDatabase(engine=...) e NÃO from_uri()
    db = SQLDatabase(engine=ch_engine)
```

### PostgreSQL Connection Node
```python
# Mesmo padrão para PostgreSQL
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
    
    pg_engine = sa_create_engine(
        connection_uri,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    
    db = SQLDatabase(engine=pg_engine)
```

### SQL Agent (Single Table Mode)
```python
# Para modo tabela única, usar include_tables
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
    warnings.filterwarnings("ignore", category=Warning)
    
    restricted_engine = sa_create_engine(
        str(db._engine.url),
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    
    restricted_db = SQLDatabase(
        engine=restricted_engine,
        include_tables=[selected_table]
    )
```

## 🔧 Arquivos Modificados

1. **agentgraph/nodes/clickhouse_connection_node.py** (linha 133-182)
   - Usa `SQLDatabase(engine=...)` ao invés de `from_uri()`
   - Filtra warnings sobre tipos desconhecidos

2. **agentgraph/nodes/postgresql_connection_node.py** (linha 108-149)
   - Usa `SQLDatabase(engine=...)` ao invés de `from_uri()`
   - Filtra warnings sobre pgvector type

3. **agentgraph/agents/sql_agent.py** (linha 145-176)
   - Usa `SQLDatabase(engine=...)` para modo tabela única
   - Usa `include_tables` para restringir tabelas

## 🧪 Teste

Execute o teste de integração:
```bash
python test_clickhouse_integration.py
```

Você deve ver:
- ✅ Sem warnings sobre `COLUMNS`, `TABLES`, `VIEWS`, etc
- ✅ Sem erros de `information_schema`
- ✅ Agente respondendo normalmente

## 🧪 Teste de Validação

Criamos um teste em `agentgraph/testes/test_clickhouse_integration.py` que valida:

1. ✅ Conexão com ClickHouse sem warnings sobre `information_schema`
2. ✅ Detecção correta de tabelas
3. ✅ Dialeto correto (clickhouse)
4. ✅ Comparação com PostgreSQL

Execute com:
```bash
cd agentgraph
python testes/test_clickhouse_integration.py
```

## 📚 Referência

- GitHub Issue: https://github.com/langchain-ai/langchain/issues/15584
- LangChain SQLDatabase: https://python.langchain.com/docs/integrations/tools/sql_database
- ClickHouse SQLAlchemy: https://github.com/ClickHouse/clickhouse-sqlalchemy

## ✅ Status

**RESOLVIDO**: A integração do ClickHouse com LangChain agora funciona corretamente sem warnings sobre `information_schema`. A solução usa `SQLDatabase(engine=...)` ao invés de `SQLDatabase.from_uri()` para evitar reflection automática de metadados.

