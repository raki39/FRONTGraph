# 🔧 Resumo das Correções - Integração ClickHouse

## 📋 Problemas Identificados e Corrigidos

### **Problema 1: ClickHouse não era tratado em `celery_polling_node.py`**
**Arquivo:** `agentgraph/nodes/celery_polling_node.py` (linhas 77-93)

**Problema:** O nó de dispatch do Celery tinha lógica para CSV e PostgreSQL, mas não para ClickHouse. Isso causava que a configuração do ClickHouse não fosse salva corretamente no Redis.

**Solução:** Adicionado `elif` para ClickHouse:
```python
elif agent_config['connection_type'] == 'clickhouse':
    # Para ClickHouse, salvar configurações de conexão
    agent_config['clickhouse_config'] = state.get('clickhouse_config', {})
    agent_config['single_table_mode'] = state.get('single_table_mode', False)
    agent_config['selected_table'] = state.get('selected_table')
```

---

### **Problema 2: ClickHouse não era tratado em `database_node.py`**
**Arquivo:** `agentgraph/nodes/database_node.py` (linhas 277-319)

**Problema:** O nó `get_database_sample_node` só tratava PostgreSQL e CSV/SQLite. Quando ClickHouse era usado, o código caía no `else` e tentava usar SQLite, causando erro.

**Solução:** Adicionado bloco `elif` para ClickHouse com query específica:
```python
elif connection_type == "clickhouse":
    # Obtém lista de tabelas do ClickHouse usando system.tables
    tables_result = conn.execute(sa.text("""
        SELECT name
        FROM system.tables
        WHERE database != 'system'
        ORDER BY name
    """))
```

---

### **Problema 3: ClickHouse não era tratado em `processing_node.py`**
**Arquivo:** `agentgraph/nodes/processing_node.py` (linhas 85-152)

**Problema:** O nó de processamento só tratava PostgreSQL e SQLite. ClickHouse caía no `else` e tentava usar tabela padrão "tabela".

**Solução:** 
1. Adicionada validação de dialeto para ClickHouse (linha 89-91)
2. Adicionado bloco `elif` para ClickHouse com lógica similar ao PostgreSQL (linhas 123-147)
3. Atualizada lógica de `available_tables` para incluir ClickHouse (linha 185)

---

### **Problema 4: ClickHouse não era tratado em `query_node.py`**
**Arquivo:** `agentgraph/nodes/query_node.py` (linhas 130-160)

**Problema:** O nó de query só recriava o agente SQL para PostgreSQL. ClickHouse não era tratado.

**Solução:** Alterado `if connection_type == "postgresql"` para `if connection_type in ["postgresql", "clickhouse"]`

---

### **Problema 5: ClickHouse não era tratado em `tasks.py`**
**Arquivo:** `agentgraph/tasks.py` (linhas 161-202)

**Problema:** A função `_build_db_uri_or_path` não construía URI para ClickHouse.

**Solução:** Adicionado `elif` para ClickHouse que constrói URI no formato:
```python
clickhouse+http://username:password@host:port/database?protocol=http
```

---

## ✅ Arquivos Modificados

### Correções de Integração ClickHouse
1. ✅ `agentgraph/nodes/celery_polling_node.py` - Adicionado suporte ClickHouse
2. ✅ `agentgraph/nodes/database_node.py` - Adicionado suporte ClickHouse
3. ✅ `agentgraph/nodes/processing_node.py` - Adicionado suporte ClickHouse
4. ✅ `agentgraph/nodes/query_node.py` - Adicionado suporte ClickHouse
5. ✅ `agentgraph/tasks.py` - Adicionado suporte ClickHouse

### Correções de Warnings (information_schema)
6. ✅ `agentgraph/nodes/clickhouse_connection_node.py` - Substituído `SQLDatabase.from_uri()` por `create_engine() + SQLDatabase()` com warnings filtrados
7. ✅ `agentgraph/nodes/postgresql_connection_node.py` - Substituído `SQLDatabase.from_uri()` por `create_engine() + SQLDatabase()` com warnings filtrados
8. ✅ `agentgraph/agents/sql_agent.py` - Substituído `SQLDatabase.from_uri()` por `create_engine() + SQLDatabase()` com warnings filtrados

---

## 🐛 Problema dos Warnings (RESOLVIDO)

### **O Problema**
Quando o ClickHouse era usado, o SQLAlchemy tentava refletir metadados usando tabelas do `information_schema` (padrão do PostgreSQL), causando erros como:

```
[DATABASE] Erro ao verificar tabela COLUMNS: Unknown table expression identifier 'COLUMNS'
[DATABASE] Erro ao verificar tabela TABLES: Unknown table expression identifier 'TABLES'
[DATABASE] Erro ao verificar tabela VIEWS: Unknown table expression identifier 'VIEWS'
```

### **Causa Raiz**
O método `SQLDatabase.from_uri()` do LangChain automaticamente tenta refletir todas as tabelas do banco usando `metadata.reflect()`, que no ClickHouse tenta acessar tabelas do `information_schema` que não existem.

### **Solução**
Substituir `SQLDatabase.from_uri()` por:
1. `create_engine()` - cria a engine SQLAlchemy
2. `SQLDatabase(engine=...)` - cria o SQLDatabase sem reflection automática
3. Filtrar warnings com `warnings.filterwarnings("ignore", category=Warning)`

**Arquivos corrigidos:**
- `agentgraph/nodes/clickhouse_connection_node.py` (linha 135)
- `agentgraph/nodes/postgresql_connection_node.py` (linha 110)
- `agentgraph/agents/sql_agent.py` (linha 149)

---

## 🧪 Como Testar

### **Pré-requisitos**
- Docker e Docker Compose instalados
- API do AgentSQL rodando em `http://localhost:8000`
- Python 3.8+ instalado

### **Passo 1: Subir o ClickHouse de Teste**
```bash
docker-compose -f docker-compose.test.yml up -d
```

### **Passo 2: Verificar Dados de Teste**
```bash
# Testar conexão
curl http://localhost:8123/ping
# Deve retornar: Ok.

# Testar query
curl "http://localhost:8123/?query=SELECT%201"
# Deve retornar: 1
```

### **Passo 3: Executar Testes Automatizados**
```bash
python test_clickhouse_integration.py
```

### **Passo 4: Testar Manualmente (Opcional)**
```bash
# Conectar no ClickHouse
docker exec -it clickhouse-test clickhouse-client \
  --user test_user \
  --password test_password \
  --database test_db

# Dentro do ClickHouse client:
SHOW TABLES;
SELECT count() FROM sales;
```

---

## 🎯 Queries de Teste Sugeridas

Após criar um agente com ClickHouse, teste com:

### **Simples**
- "Mostre as 5 primeiras vendas"
- "Quantos clientes temos?"

### **Agregações**
- "Qual o total de vendas por categoria?"
- "Qual a média de temperatura por sensor?"

### **ClickHouse Específicas**
- "Qual o percentil 95 de latência?"
- "Mostre a média de temperatura por hora"

---

## 🐛 Troubleshooting

Se ainda houver problemas:

1. **Verificar logs do worker:**
   ```bash
   docker-compose logs inter-worker-1
   ```

2. **Verificar se ClickHouse está rodando:**
   ```bash
   docker-compose -f docker-compose.test.yml ps
   ```

3. **Limpar e reiniciar:**
   ```bash
   docker-compose -f docker-compose.test.yml down -v
   docker-compose -f docker-compose.test.yml up -d
   ```

---

## 📝 Notas Importantes

- ClickHouse usa `system.tables` para listar tabelas (não `sqlite_master`)
- URI do ClickHouse: `clickhouse+http://user:pass@host:port/database`
- Dialeto detectado automaticamente como "clickhouse" pelo SQLAlchemy
- Suporta modo tabela única e multi-tabela como PostgreSQL

