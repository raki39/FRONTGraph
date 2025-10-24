# 🧪 Testes de Integração ClickHouse

Este diretório contém testes de integração para validar a implementação do ClickHouse no AgentSQL.

## 📋 Estrutura

```
tests/
├── clickhouse/
│   └── init.sql              # Script de inicialização do ClickHouse com dados de teste
└── README.md                 # Este arquivo
```

**Nota:** O script de testes Python está na raiz do projeto: `test_clickhouse_integration.py`

## 🚀 Como Executar os Testes

### **Pré-requisitos**

1. **Docker e Docker Compose** instalados
2. **Python 3.8+** instalado
3. **API do AgentSQL** rodando em `http://localhost:8000`

### **Passo 1: Subir o ClickHouse de Teste**

```bash
# Na raiz do projeto
docker-compose -f docker-compose.test.yml up -d

# Verificar se está rodando
docker-compose -f docker-compose.test.yml ps

# Ver logs
docker-compose -f docker-compose.test.yml logs -f clickhouse-test
```

O ClickHouse estará disponível em:
- **HTTP Interface**: `http://localhost:8123`
- **Native Protocol**: `tcp://localhost:9000`

### **Passo 2: Verificar Dados de Teste**

```bash
# Conectar no ClickHouse e verificar tabelas
docker exec -it clickhouse-test clickhouse-client

# Dentro do ClickHouse client:
USE test_db;
SHOW TABLES;
SELECT count() FROM sales;
SELECT count() FROM customers;
SELECT count() FROM event_logs;
SELECT count() FROM performance_metrics;
SELECT count() FROM time_series_data;
```

### **Passo 3: Executar Testes Python**

```bash
# Instalar dependências (se necessário)
pip install requests

# Executar testes
python tests/test_clickhouse_integration.py

# Ou usar o script bash
chmod +x tests/run_tests.sh
./tests/run_tests.sh
```

### **Passo 4: Parar o ClickHouse**

```bash
# Parar e remover containers
docker-compose -f docker-compose.test.yml down

# Parar e remover containers + volumes (limpa dados)
docker-compose -f docker-compose.test.yml down -v
```

---

## 🧪 O Que os Testes Validam

### **1. Conectividade**
- ✅ API está respondendo
- ✅ ClickHouse está acessível
- ✅ Conexão direta com ClickHouse funciona

### **2. Autenticação**
- ✅ Registro de usuário
- ✅ Login e obtenção de token JWT
- ✅ Endpoints protegidos aceitam token

### **3. Endpoints de Conexão**
- ✅ `POST /connections/test` - Testa conexão ClickHouse
- ✅ `POST /connections/` - Cria conexão ClickHouse
- ✅ `GET /connections/` - Lista conexões
- ✅ `DELETE /connections/{id}` - Remove conexão

### **4. Endpoints de Agentes**
- ✅ `POST /agents/` - Cria agente com conexão ClickHouse
- ✅ `GET /agents/` - Lista agentes
- ✅ `DELETE /agents/{id}` - Remove agente

### **5. Validações**
- ✅ Configuração ClickHouse é validada corretamente
- ✅ Campos obrigatórios são verificados
- ✅ Erros de conexão são tratados adequadamente
- ✅ Mensagens de erro são amigáveis

---

## 📊 Dados de Teste Disponíveis

O script `init.sql` cria as seguintes tabelas com dados de exemplo:

### **1. sales** (15 registros)
Vendas de produtos com informações de categoria, quantidade, preço, data e região.

```sql
SELECT * FROM sales LIMIT 5;
```

### **2. customers** (10 registros)
Clientes com informações de contato, país e total de compras.

```sql
SELECT * FROM customers LIMIT 5;
```

### **3. event_logs** (10 registros)
Logs de eventos da aplicação com timestamps, duração e status.

```sql
SELECT * FROM event_logs WHERE status = 'error';
```

### **4. performance_metrics** (10 registros)
Métricas de performance de serviços com tags e valores.

```sql
SELECT service_name, avg(value) as avg_value 
FROM performance_metrics 
GROUP BY service_name;
```

### **5. time_series_data** (1000 registros)
Dados de série temporal de sensores (temperatura, umidade, pressão).

```sql
SELECT sensor_id, avg(temperature) as avg_temp 
FROM time_series_data 
GROUP BY sensor_id;
```

### **Views Criadas**

- **sales_by_category**: Agregação de vendas por categoria
- **performance_by_minute**: Métricas agregadas por minuto

---

## 🔧 Configuração Personalizada

Você pode personalizar as configurações através de variáveis de ambiente:

```bash
# Configurar variáveis
export API_URL=http://localhost:8000
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=8123
export CLICKHOUSE_USER=test_user
export CLICKHOUSE_PASS=test_password
export CLICKHOUSE_DB=test_db

# Executar testes
python tests/test_clickhouse_integration.py
```

---

## 🐛 Troubleshooting

### **Problema: ClickHouse não inicia**

```bash
# Ver logs detalhados
docker-compose -f docker-compose.test.yml logs clickhouse-test

# Verificar se a porta está em uso
netstat -an | grep 8123

# Remover volumes antigos e reiniciar
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
```

### **Problema: Testes falham na autenticação**

```bash
# Verificar se a API está rodando
curl http://localhost:8000/health

# Verificar logs da API
docker-compose logs api
```

### **Problema: Conexão ClickHouse falha**

```bash
# Testar conexão direta
curl http://localhost:8123/ping

# Testar query simples
curl "http://localhost:8123/?query=SELECT%201"

# Verificar credenciais
docker exec -it clickhouse-test clickhouse-client \
  --user test_user \
  --password test_password \
  --database test_db \
  --query "SELECT 1"
```

### **Problema: Dados de teste não foram criados**

```bash
# Verificar se o script de inicialização foi executado
docker exec -it clickhouse-test clickhouse-client --query "SHOW DATABASES"

# Recriar dados manualmente
docker exec -i clickhouse-test clickhouse-client < tests/clickhouse/init.sql
```

---

## 📝 Exemplos de Queries para Testar

Após criar um agente com ClickHouse, você pode testar com estas perguntas:

### **Queries Simples**
```
"Mostre as 5 primeiras vendas"
"Quantos clientes temos no total?"
"Liste todas as tabelas disponíveis"
```

### **Agregações**
```
"Qual o total de vendas por categoria?"
"Qual a média de temperatura por sensor?"
"Quantos eventos de erro temos nos logs?"
```

### **Queries Analíticas (ClickHouse específicas)**
```
"Qual o percentil 95 de latência do api-gateway?"
"Mostre a média de temperatura por hora nas últimas 24h"
"Qual a taxa de hit do cache ao longo do tempo?"
```

### **Queries com Funções ClickHouse**
```
"Use a função quantile para calcular o percentil 95 de duration_ms nos event_logs"
"Agrupe as métricas por minuto usando toStartOfMinute"
"Mostre os sensores com temperatura acima da média usando subqueries"
```

---

## 🎯 Checklist de Validação

Antes de considerar a integração completa, valide:

- [ ] ClickHouse sobe corretamente com docker-compose.test.yml
- [ ] Dados de teste são criados automaticamente
- [ ] Endpoint `/connections/test` valida conexão ClickHouse
- [ ] Endpoint `/connections/` cria conexão ClickHouse
- [ ] Campo `ch_dsn` é salvo corretamente no banco
- [ ] Agente pode ser criado com conexão ClickHouse
- [ ] LangChain detecta dialeto ClickHouse automaticamente
- [ ] Queries simples funcionam
- [ ] Queries com agregações funcionam
- [ ] Queries com funções específicas do ClickHouse funcionam
- [ ] Erros de conexão são tratados adequadamente
- [ ] Cleanup de recursos funciona

---

## 📚 Recursos Adicionais

- [Documentação ClickHouse](https://clickhouse.com/docs)
- [ClickHouse SQL Reference](https://clickhouse.com/docs/en/sql-reference)
- [clickhouse-sqlalchemy](https://github.com/cloudflare/sqlalchemy-clickhouse)
- [LangChain SQL Agent](https://python.langchain.com/docs/integrations/toolkits/sql_database)

---

**Desenvolvido com ❤️ para AgentSQL**

