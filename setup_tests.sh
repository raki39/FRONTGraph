#!/bin/bash

# Script para configurar ambiente de testes da AgentAPI
# Instala todas as dependências necessárias

set -e

echo "🔧 Configurando ambiente de testes da AgentAPI"
echo "=============================================="

# Verificar se Python está instalado
if command -v python3 &> /dev/null; then
    echo "✅ Python3 encontrado: $(python3 --version)"
else
    echo "❌ Python3 não encontrado. Instale Python 3.7+ primeiro."
    exit 1
fi

# Verificar se Node.js está instalado
if command -v node &> /dev/null; then
    echo "✅ Node.js encontrado: $(node --version)"
    NODE_AVAILABLE=true
else
    echo "⚠️  Node.js não encontrado. Scripts JavaScript não funcionarão."
    NODE_AVAILABLE=false
fi

# Verificar se curl está instalado
if command -v curl &> /dev/null; then
    echo "✅ curl encontrado: $(curl --version | head -n1)"
else
    echo "❌ curl não encontrado. Instale curl primeiro."
    exit 1
fi

# Verificar se jq está instalado
if command -v jq &> /dev/null; then
    echo "✅ jq encontrado: $(jq --version)"
else
    echo "⚠️  jq não encontrado. Instalando..."
    
    # Tentar instalar jq baseado no sistema
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        elif command -v pacman &> /dev/null; then
            sudo pacman -S jq
        else
            echo "❌ Não foi possível instalar jq automaticamente."
            echo "   Instale manualmente: https://stedolan.github.io/jq/download/"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install jq
        else
            echo "❌ Homebrew não encontrado. Instale jq manualmente."
            exit 1
        fi
    else
        echo "❌ Sistema não suportado para instalação automática do jq."
        echo "   Instale manualmente: https://stedolan.github.io/jq/download/"
        exit 1
    fi
fi

echo ""
echo "📦 Instalando dependências Python..."

# Instalar dependências Python
pip3 install requests

echo "✅ Dependências Python instaladas"

# Instalar dependências Node.js se disponível
if [ "$NODE_AVAILABLE" = true ]; then
    echo ""
    echo "📦 Instalando dependências Node.js..."
    
    # Verificar se npm está disponível
    if command -v npm &> /dev/null; then
        npm install axios form-data
        echo "✅ Dependências Node.js instaladas"
    else
        echo "⚠️  npm não encontrado. Dependências Node.js não foram instaladas."
    fi
fi

echo ""
echo "🔧 Configurando permissões..."

# Tornar scripts executáveis
chmod +x test_api_quick.sh
chmod +x setup_tests.sh

echo "✅ Permissões configuradas"

echo ""
echo "🧪 Testando configuração..."

# Testar se tudo está funcionando
echo "Testando Python..."
python3 -c "import requests; print('✅ requests OK')"

if [ "$NODE_AVAILABLE" = true ]; then
    echo "Testando Node.js..."
    node -e "require('axios'); require('form-data'); console.log('✅ axios e form-data OK')"
fi

echo "Testando jq..."
echo '{"test": "ok"}' | jq '.test' > /dev/null && echo "✅ jq OK"

echo ""
echo "🎉 Configuração concluída!"
echo "=============================================="
echo ""
echo "📋 Scripts disponíveis:"
echo "  🐍 Python:  python3 test_api_endpoints.py"
echo "  🐚 Bash:    ./test_api_quick.sh"
if [ "$NODE_AVAILABLE" = true ]; then
echo "  🟨 Node.js:  node test_api_endpoints.js"
fi
echo ""
echo "📖 Para mais informações, consulte: README_TESTS.md"
echo ""
echo "🚀 Exemplo de uso:"
echo "   ./test_api_quick.sh http://localhost:8000"
echo ""
