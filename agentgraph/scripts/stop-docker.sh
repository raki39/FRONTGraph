#!/bin/bash

# ========================================
# AgentGraph - Parar Docker (Linux)
# ========================================

echo "========================================"
echo "AgentGraph - Parar Docker"
echo "========================================"

echo "🛑 Parando AgentGraph..."

docker-compose down

if [ $? -ne 0 ]; then
    echo "❌ Erro ao parar aplicação"
    exit 1
fi

echo "✅ AgentGraph parado com sucesso!"
echo ""
echo "📊 Para ver containers rodando:"
echo "   docker ps"
echo ""
echo "🚀 Para iniciar novamente:"
echo "   ./run-docker.sh"
echo ""
