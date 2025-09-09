#!/bin/bash

# ========================================
# AgentGraph - Rebuild Docker (Linux)
# ========================================

set -e

echo "========================================"
echo "AgentGraph - Rebuild Docker"
echo "========================================"

echo "🛑 Parando containers existentes..."
docker-compose down

echo "🔨 Reconstruindo imagem Docker..."
docker-compose build --no-cache

echo "🚀 Iniciando aplicação..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Erro ao rebuild"
    exit 1
fi

echo "✅ Rebuild concluído com sucesso!"
echo ""
echo "🌐 Aguardando link público do Gradio..."
echo ""

# Aguardar alguns segundos
sleep 5

# Mostrar logs
echo "📊 Logs da aplicação (Ctrl+C para sair):"
echo "=========================================="
docker-compose logs -f agentgraph
