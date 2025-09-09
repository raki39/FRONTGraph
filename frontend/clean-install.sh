#!/bin/bash

echo "========================================"
echo "   LIMPEZA E REINSTALACAO DO FRONTEND"
echo "========================================"
echo

echo "[1/5] Parando processos Node.js..."
pkill -f node 2>/dev/null || true
pkill -f npm 2>/dev/null || true
echo "✅ Processos Node.js finalizados"

echo
echo "[2/5] Removendo node_modules..."
if [ -d "node_modules" ]; then
    echo "Removendo node_modules... (pode demorar)"
    rm -rf node_modules
    echo "✅ node_modules removido"
else
    echo "ℹ️  node_modules não encontrado"
fi

echo
echo "[3/5] Removendo arquivos de lock..."
if [ -f "package-lock.json" ]; then
    rm package-lock.json
    echo "✅ package-lock.json removido"
else
    echo "ℹ️  package-lock.json não encontrado"
fi

if [ -f "yarn.lock" ]; then
    rm yarn.lock
    echo "✅ yarn.lock removido"
fi

echo
echo "[4/5] Limpando cache do npm (com timeout)..."
timeout 10s npm cache clean --force --silent 2>/dev/null || echo "⚠️  Cache não pode ser limpo (continuando...)"
echo "✅ Tentativa de limpeza de cache concluída"

echo
echo "[5/5] Instalando dependências..."
echo "Instalando... (pode demorar alguns minutos)"
npm install --no-audit --no-fund
if [ $? -eq 0 ]; then
    echo "✅ Dependências instaladas com sucesso"
else
    echo "❌ Erro na instalação das dependências"
    echo "Tentando novamente com cache limpo..."
    npm cache clean --force --silent 2>/dev/null || true
    npm install --no-audit --no-fund
fi

echo
echo "========================================"
echo "   INSTALAÇÃO CONCLUÍDA!"
echo "========================================"
echo
echo "Para iniciar o servidor de desenvolvimento:"
echo "npm run dev"
echo
