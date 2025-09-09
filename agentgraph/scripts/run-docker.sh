#!/bin/bash

# ========================================
# AgentGraph - Docker com Link Público (Linux)
# ========================================

set -e

echo "========================================"
echo "AgentGraph - Docker com Link Público"
echo "========================================"

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Instale o Docker primeiro."
    echo "   Ubuntu/Debian: sudo apt install docker.io"
    echo "   CentOS/RHEL: sudo yum install docker"
    echo "   Ou visite: https://docs.docker.com/engine/install/"
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

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: Configure suas API keys no arquivo .env"
    echo "   Abra o arquivo .env e adicione pelo menos uma chave de API:"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - HUGGINGFACE_API_KEY"
    echo ""
    read -p "Pressione Enter após configurar as API keys..."
fi

# Criar diretório para uploads
mkdir -p uploaded_data

echo "🚀 Iniciando AgentGraph com Docker..."
echo "   (Incluindo tabela.csv necessária para inicialização)"
echo ""

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down &> /dev/null || true

# Iniciar aplicação com rebuild
echo "🔨 Construindo imagem Docker..."
docker-compose up --build -d

if [ $? -ne 0 ]; then
    echo "❌ Erro ao iniciar aplicação"
    exit 1
fi

echo "✅ AgentGraph iniciado com sucesso!"
echo ""
echo "🌐 Aguardando link público do Gradio..."
echo "   O link será exibido nos logs abaixo:"
echo ""

# Aguardar alguns segundos
sleep 5

# Mostrar logs
echo "📊 Logs da aplicação (Ctrl+C para sair):"
echo "=========================================="
docker-compose logs -f agentgraph
