#!/bin/bash

echo "========================================"
echo "AgentGraph - Docker Production Mode"
echo "========================================"

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado."
    echo "   Ubuntu/Debian: sudo apt install docker.io"
    echo "   CentOS/RHEL: sudo yum install docker"
    echo "   Ou visite: https://docs.docker.com/install/"
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado."
    echo "   Instale com: sudo apt install docker-compose"
    echo "   Ou visite: https://docs.docker.com/compose/install/"
    exit 1
fi

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    echo "❌ Docker não está rodando. Inicie o serviço Docker:"
    echo "   sudo systemctl start docker"
    echo "   sudo systemctl enable docker"
    exit 1
fi

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "⚠️ Arquivo .env não encontrado"
    echo "💡 Crie um arquivo .env com suas API keys:"
    echo "   OPENAI_API_KEY=sua_chave_aqui"
    echo "   ANTHROPIC_API_KEY=sua_chave_aqui"
    echo "   HUGGINGFACE_API_KEY=sua_chave_aqui"
    echo ""
    read -p "Pressione Enter para continuar..."
fi

echo "🧹 Parando containers existentes..."
docker-compose down

echo "🔨 Construindo imagem Docker..."
docker-compose build

echo "🚀 Iniciando AgentGraph com Redis + Celery (2 workers x 4 concurrency = 8 processos)..."
echo "🔥 Gradio sem fila - Concorrência ilimitada para múltiplos usuários"
echo "⏱️ Celery configurado para tabelas grandes (120min timeout)"
echo "🛡️ Configurações de reliability e fault tolerance habilitadas"
echo ""
echo "📊 Serviços disponíveis:"
echo "   - AgentGraph: http://localhost:7860 (sem fila)"
echo "   - Flower Dashboard: http://localhost:5555 (admin/admin)"
echo "   - Redis: localhost:6379"
echo ""
echo "🛑 Para parar: Ctrl+C"
echo ""

# Captura Ctrl+C para cleanup
trap 'echo ""; echo "🧹 Limpando containers..."; docker-compose down; echo "✅ AgentGraph Docker finalizado"; exit 0' INT

docker-compose up

echo ""
echo "🧹 Limpando containers..."
docker-compose down

echo "✅ AgentGraph Docker finalizado"
