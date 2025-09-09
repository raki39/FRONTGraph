#!/bin/bash

echo "🚀 Iniciando AgentAPI Frontend..."

# Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não encontrado. Instale Node.js 18+ primeiro."
    exit 1
fi

# Verificar versão do Node.js
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ é necessário. Versão atual: $(node -v)"
    exit 1
fi

# Instalar dependências se necessário
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependências..."
    npm install
fi

# Verificar se .env.local existe
if [ ! -f ".env.local" ]; then
    echo "⚙️ Criando arquivo de configuração..."
    cp .env.example .env.local
fi

# Iniciar servidor de desenvolvimento
echo "🌐 Iniciando servidor em http://localhost:3000"
npm run dev
