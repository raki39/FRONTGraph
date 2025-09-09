# 🚀 **Configuração do Celery + Redis + Flower**

Este documento explica como configurar e usar o sistema de processamento assíncrono com Celery no AgentGraph.

## 📋 **Pré-requisitos**

### **1. Redis Local (Automático)**
O Redis será baixado e iniciado automaticamente:

```bash
# Opção 1: Configuração automática
python setup_redis.py

# Opção 2: O app.py tentará iniciar Redis automaticamente
python app.py
```

### **1.1. Redis Manual (se necessário)**
Se a configuração automática falhar:

```bash
# Baixar Redis para Windows
# https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip

# Extrair na pasta do projeto como "redis-windows/"
# Executar: redis-windows/redis-server.exe
```

### **2. Dependências Python**
As dependências já estão no `requirements.txt`:
- `celery>=5.3.0`
- `redis>=5.0.0`
- `flower>=2.0.0`

## ⚙️ **Configuração**

### **1. Variáveis de Ambiente**
Configure no arquivo `.env`:

```env
# Habilitar/Desabilitar Celery
CELERY_ENABLED=true

# Configurações do Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Configurações do Worker (Windows)
CELERY_WORKER_CONCURRENCY=1

# Porta do Flower (monitoramento)
FLOWER_PORT=5555
```

### **2. Inicialização Automática**
O sistema Celery é inicializado automaticamente quando você roda `python app.py`:

1. **Verifica Redis**: Testa conexão com Redis
2. **Inicia Worker**: Celery worker em background
3. **Inicia Flower**: Dashboard de monitoramento
4. **Configura Cleanup**: Encerra processos ao fechar app

## 🔄 **Como Funciona**

### **Fluxo Tradicional (sem Celery)**
```
User Input → LangGraph → SQL Agent → Response
```

### **Fluxo com Celery**
```
User Input → LangGraph → Celery Task → Worker → Response
                ↓
            Task Polling ← Redis ← Worker
```

### **Quando Usar Celery**
- **Automático**: Baseado na configuração `CELERY_ENABLED=true`
- **Todas as queries SQL**: Sem exceção, independente da complexidade
- **Isolamento**: Cada query roda em worker separado
- **Não-bloqueante**: Interface responde imediatamente

## 🖥️ **Monitoramento**

### **Flower Dashboard**
Acesse: `http://localhost:5555`

**Funcionalidades:**
- ✅ Workers ativos/inativos
- 📊 Tasks em execução, concluídas, falhadas
- ⏱️ Tempos de execução
- 📈 Estatísticas de performance
- 🔄 Controle de workers

### **Logs**
```bash
# Logs do Worker
[CELERY] Worker Celery iniciado com sucesso

# Logs das Tasks
[CELERY_TASK] Iniciando processamento para agent_id: abc123
[CELERY_TASK] User input: Como estão as vendas...
[CELERY_TASK] Configuração carregada: csv
[CELERY_TASK] Processamento concluído em 3.45s
```

## 🛠️ **Comandos Manuais**

### **Testar Celery (Recomendado)**
```bash
python test_celery.py
```

### **Iniciar Worker Manualmente**
```bash
# Opção 1: Comando direto (se disponível)
celery -A tasks worker --concurrency=1 --loglevel=INFO --pool=solo

# Opção 2: Via módulo Python (mais compatível no Windows)
python -m celery -A tasks worker --concurrency=1 --loglevel=INFO --pool=solo
```

### **Iniciar Flower Manualmente**
```bash
# Opção 1: Comando direto
celery -A tasks flower --port=5555

# Opção 2: Via módulo Python
python -m celery -A tasks flower --port=5555
```

### **Verificar Status**
```bash
python -m celery -A tasks status
```

### **Limpar Tasks**
```bash
python -m celery -A tasks purge
```

## 🔧 **Configurações Avançadas**

### **Redis em Porta Diferente**
```env
CELERY_BROKER_URL=redis://localhost:6380/0
CELERY_RESULT_BACKEND=redis://localhost:6380/0
```

### **Redis Remoto**
```env
CELERY_BROKER_URL=redis://192.168.1.100:6379/0
CELERY_RESULT_BACKEND=redis://192.168.1.100:6379/0
```

### **Múltiplos Workers**
```env
CELERY_WORKER_CONCURRENCY=4
```

### **Flower em Porta Diferente**
```env
FLOWER_PORT=8080
```

## 🚨 **Troubleshooting**

### **Redis não conecta (Windows Local)**
```bash
# 1. Finalizar processos Redis existentes
taskkill /F /IM redis-server.exe

# 2. Executar configuração automática
python setup_redis.py

# 3. Verificar se Redis existe na pasta
dir redis-windows\redis-server.exe
dir redis-windows\redis.windows.conf

# 4. Iniciar Redis manualmente (com configuração)
redis-windows\redis-server.exe redis-windows\redis.windows.conf

# 5. Ou sem configuração (se arquivo não existir)
redis-windows\redis-server.exe

# 6. Verificar porta (em outro terminal)
netstat -an | findstr 6379

# 7. Testar conexão
python -c "import redis; redis.Redis().ping(); print('OK')"
```

### **Worker não inicia (Windows)**
```bash
# 1. Executar teste completo
python test_celery.py

# 2. Verificar dependências
pip install celery redis flower

# 3. Testar comando manual (opção 1)
celery -A tasks worker --loglevel=DEBUG --pool=solo

# 4. Testar comando manual (opção 2 - mais compatível)
python -m celery -A tasks worker --loglevel=DEBUG --pool=solo

# 5. Verificar se tasks.py existe
dir tasks.py

# 6. Verificar versão do Celery
python -c "import celery; print(celery.__version__)"
```

### **Flower não abre**
```bash
# Verificar se porta está livre
netstat -an | findstr 5555

# Testar comando manual
celery -A tasks flower --port=5555
```

### **Tasks ficam pendentes**
```bash
# Verificar workers ativos
celery -A tasks status

# Limpar fila
celery -A tasks purge
```

## 🔄 **Desabilitar Celery**

Para voltar ao modo tradicional:

```env
CELERY_ENABLED=false
```

O sistema funcionará normalmente sem Celery, executando queries diretamente.

## 📊 **Performance**

### **Vantagens do Celery**
- ✅ **Interface responsiva**: Não trava durante queries pesadas
- ✅ **Isolamento**: Falhas em queries não afetam a aplicação
- ✅ **Escalabilidade**: Múltiplos workers para alta demanda
- ✅ **Monitoramento**: Flower dashboard completo
- ✅ **Retry automático**: Tasks falhas são reprocessadas

### **Overhead**
- ⚠️ **Latência adicional**: ~100-200ms para dispatch/polling
- ⚠️ **Memória**: Redis + Workers consomem RAM adicional
- ⚠️ **Complexidade**: Mais componentes para gerenciar

## 🎯 **Recomendações**

### **Desenvolvimento**
```env
CELERY_ENABLED=false  # Mais simples para debug
```

### **Produção**
```env
CELERY_ENABLED=true   # Melhor performance e escalabilidade
```

### **Múltiplos Usuários**
```env
CELERY_ENABLED=true
CELERY_WORKER_CONCURRENCY=4  # Ou mais, dependendo do hardware
```
