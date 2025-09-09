#!/bin/bash

echo "🚀 Setup Completo do AgentAPI para Demonstração"
echo "=============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar pré-requisitos
echo -e "${BLUE}📋 Verificando pré-requisitos...${NC}"

if ! command_exists docker; then
    echo -e "${RED}❌ Docker não encontrado. Instale Docker primeiro.${NC}"
    exit 1
fi

if ! command_exists docker-compose; then
    echo -e "${RED}❌ Docker Compose não encontrado. Instale Docker Compose primeiro.${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}❌ Node.js não encontrado. Instale Node.js 18+ primeiro.${NC}"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}❌ Node.js 18+ é necessário. Versão atual: $(node -v)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Todos os pré-requisitos atendidos${NC}"

# Configurar variáveis de ambiente se necessário
echo -e "${BLUE}⚙️ Configurando variáveis de ambiente...${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 Arquivo .env criado a partir do .env.example${NC}"
        echo -e "${YELLOW}   Edite o arquivo .env com suas configurações antes de continuar${NC}"
    else
        echo -e "${RED}❌ Arquivo .env.example não encontrado${NC}"
        exit 1
    fi
fi

# Configurar frontend
echo -e "${BLUE}🌐 Configurando frontend...${NC}"

cd frontend

if [ ! -f ".env.local" ]; then
    cp .env.example .env.local
    echo -e "${GREEN}✅ Arquivo .env.local criado${NC}"
fi

if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Instalando dependências do frontend...${NC}"
    npm install
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
fi

cd ..

# Iniciar serviços
echo -e "${BLUE}🐳 Iniciando serviços com Docker...${NC}"

# Verificar se já está rodando
if docker-compose -f docker-compose.api.yml ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️ Alguns serviços já estão rodando. Reiniciando...${NC}"
    docker-compose -f docker-compose.api.yml down
fi

# Iniciar serviços
docker-compose -f docker-compose.api.yml up -d

# Aguardar serviços ficarem prontos
echo -e "${BLUE}⏳ Aguardando serviços ficarem prontos...${NC}"
sleep 10

# Verificar se API está respondendo
echo -e "${BLUE}🔍 Verificando API...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ API está respondendo${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API não está respondendo após 30 tentativas${NC}"
        echo -e "${YELLOW}   Verifique os logs: docker-compose -f docker-compose.api.yml logs${NC}"
        exit 1
    fi
    echo -e "${YELLOW}   Tentativa $i/30...${NC}"
    sleep 2
done

# Iniciar frontend em background
echo -e "${BLUE}🌐 Iniciando frontend...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Aguardar frontend ficar pronto
echo -e "${BLUE}⏳ Aguardando frontend ficar pronto...${NC}"
sleep 5

# Verificar se frontend está respondendo
for i in {1..15}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend está respondendo${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Frontend não está respondendo${NC}"
        kill $FRONTEND_PID 2>/dev/null
        exit 1
    fi
    echo -e "${YELLOW}   Tentativa $i/15...${NC}"
    sleep 2
done

# Sucesso!
echo ""
echo -e "${GREEN}🎉 Setup completo! Sistema pronto para demonstração${NC}"
echo ""
echo -e "${BLUE}📍 URLs de Acesso:${NC}"
echo -e "   🌐 Frontend: ${GREEN}http://localhost:3000${NC}"
echo -e "   🔧 API: ${GREEN}http://localhost:8000${NC}"
echo -e "   📚 Documentação: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}📋 Próximos passos:${NC}"
echo -e "   1. Acesse ${GREEN}http://localhost:3000${NC}"
echo -e "   2. Crie uma conta de usuário"
echo -e "   3. Configure uma conexão PostgreSQL"
echo -e "   4. Crie um agente"
echo -e "   5. Teste o chat!"
echo ""
echo -e "${BLUE}📖 Guia completo: ${GREEN}DEMO_INSTRUCTIONS.md${NC}"
echo ""
echo -e "${YELLOW}💡 Para parar os serviços:${NC}"
echo -e "   docker-compose -f docker-compose.api.yml down"
echo -e "   kill $FRONTEND_PID"
echo ""

# Salvar PID do frontend para facilitar o stop
echo $FRONTEND_PID > .frontend.pid

echo -e "${GREEN}✨ Demonstração pronta!${NC}"
