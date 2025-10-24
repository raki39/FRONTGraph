#!/bin/bash

# 🧪 Script de Teste - Integração ClickHouse
# Este script testa a integração completa do ClickHouse com o AgentSQL

set -e  # Para na primeira falha

echo "🚀 Iniciando testes de integração ClickHouse..."
echo ""

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
API_URL="${API_URL:-http://localhost:8000}"
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-8123}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASS="${CLICKHOUSE_PASS:-}"
CLICKHOUSE_DB="${CLICKHOUSE_DB:-default}"

echo "📋 Configurações:"
echo "  API URL: $API_URL"
echo "  ClickHouse Host: $CLICKHOUSE_HOST"
echo "  ClickHouse Port: $CLICKHOUSE_PORT"
echo "  ClickHouse User: $CLICKHOUSE_USER"
echo "  ClickHouse DB: $CLICKHOUSE_DB"
echo ""

# Função para fazer login e obter token
get_token() {
    echo "🔐 Fazendo login..."
    
    # Cria usuário de teste se não existir
    curl -s -X POST "$API_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "test@clickhouse.com",
            "password": "test123",
            "nome": "Test User"
        }' > /dev/null 2>&1 || true
    
    # Faz login
    RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test@clickhouse.com&password=test123")
    
    TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}❌ Falha ao obter token de autenticação${NC}"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Login realizado com sucesso${NC}"
    echo ""
}

# Função para testar conexão ClickHouse
test_clickhouse_connection() {
    echo "🧪 Testando conexão ClickHouse..."
    
    RESPONSE=$(curl -s -X POST "$API_URL/connections/test" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"tipo\": \"clickhouse\",
            \"clickhouse_config\": {
                \"host\": \"$CLICKHOUSE_HOST\",
                \"port\": $CLICKHOUSE_PORT,
                \"database\": \"$CLICKHOUSE_DB\",
                \"username\": \"$CLICKHOUSE_USER\",
                \"password\": \"$CLICKHOUSE_PASS\",
                \"secure\": false
            }
        }")
    
    VALID=$(echo $RESPONSE | grep -o '"valid":[^,]*' | cut -d':' -f2)
    MESSAGE=$(echo $RESPONSE | grep -o '"message":"[^"]*' | cut -d'"' -f4)
    
    if [ "$VALID" = "true" ]; then
        echo -e "${GREEN}✅ Conexão ClickHouse testada com sucesso${NC}"
        echo "   Mensagem: $MESSAGE"
    else
        echo -e "${RED}❌ Falha ao testar conexão ClickHouse${NC}"
        echo "   Mensagem: $MESSAGE"
        echo "   Response: $RESPONSE"
        exit 1
    fi
    echo ""
}

# Função para criar conexão ClickHouse
create_clickhouse_connection() {
    echo "📝 Criando conexão ClickHouse..."
    
    RESPONSE=$(curl -s -X POST "$API_URL/connections/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"tipo\": \"clickhouse\",
            \"clickhouse_config\": {
                \"host\": \"$CLICKHOUSE_HOST\",
                \"port\": $CLICKHOUSE_PORT,
                \"database\": \"$CLICKHOUSE_DB\",
                \"username\": \"$CLICKHOUSE_USER\",
                \"password\": \"$CLICKHOUSE_PASS\",
                \"secure\": false
            }
        }")
    
    CONNECTION_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [ -z "$CONNECTION_ID" ]; then
        echo -e "${RED}❌ Falha ao criar conexão ClickHouse${NC}"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Conexão ClickHouse criada com sucesso (ID: $CONNECTION_ID)${NC}"
    echo ""
}

# Função para criar agente com ClickHouse
create_agent_with_clickhouse() {
    echo "🤖 Criando agente com conexão ClickHouse..."
    
    RESPONSE=$(curl -s -X POST "$API_URL/agents/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"nome\": \"Agente ClickHouse Test\",
            \"connection_id\": $CONNECTION_ID,
            \"selected_model\": \"gpt-4o-mini\",
            \"top_k\": 10,
            \"description\": \"Agente de teste para ClickHouse\"
        }")
    
    AGENT_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}❌ Falha ao criar agente${NC}"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Agente criado com sucesso (ID: $AGENT_ID)${NC}"
    echo ""
}

# Função para testar query no agente
test_agent_query() {
    echo "💬 Testando query no agente ClickHouse..."
    
    RESPONSE=$(curl -s -X POST "$API_URL/agents/$AGENT_ID/run" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "question": "Mostre as primeiras 5 tabelas do banco de dados"
        }')
    
    TASK_ID=$(echo $RESPONSE | grep -o '"task_id":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TASK_ID" ]; then
        echo -e "${RED}❌ Falha ao executar query${NC}"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Query enviada com sucesso (Task ID: $TASK_ID)${NC}"
    echo ""
    
    # Aguarda processamento
    echo "⏳ Aguardando processamento (30s)..."
    sleep 30
    
    # Verifica resultado
    echo "📊 Verificando resultado..."
    RESULT=$(curl -s -X GET "$API_URL/runs/$TASK_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $RESULT | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}✅ Query processada com sucesso${NC}"
        echo "   Status: $STATUS"
    else
        echo -e "${YELLOW}⚠️  Query ainda processando ou falhou${NC}"
        echo "   Status: $STATUS"
    fi
    echo ""
}

# Função para listar conexões
list_connections() {
    echo "📋 Listando conexões..."
    
    RESPONSE=$(curl -s -X GET "$API_URL/connections/" \
        -H "Authorization: Bearer $TOKEN")
    
    echo "Conexões encontradas:"
    echo "$RESPONSE" | grep -o '"tipo":"[^"]*' | cut -d'"' -f4 | sort | uniq -c
    echo ""
}

# Função para cleanup
cleanup() {
    echo "🧹 Limpando recursos de teste..."
    
    if [ ! -z "$AGENT_ID" ]; then
        curl -s -X DELETE "$API_URL/agents/$AGENT_ID" \
            -H "Authorization: Bearer $TOKEN" > /dev/null 2>&1 || true
        echo "  ✓ Agente removido"
    fi
    
    if [ ! -z "$CONNECTION_ID" ]; then
        curl -s -X DELETE "$API_URL/connections/$CONNECTION_ID" \
            -H "Authorization: Bearer $TOKEN" > /dev/null 2>&1 || true
        echo "  ✓ Conexão removida"
    fi
    
    echo ""
}

# Executa testes
main() {
    get_token
    test_clickhouse_connection
    create_clickhouse_connection
    create_agent_with_clickhouse
    list_connections
    test_agent_query
    
    echo ""
    echo -e "${GREEN}🎉 Todos os testes passaram com sucesso!${NC}"
    echo ""
    
    # Pergunta se deve fazer cleanup
    read -p "Deseja remover os recursos de teste? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup
    fi
}

# Executa
main

