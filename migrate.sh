#!/bin/bash

# Script de migração para AgentAPI via Docker Compose
# Executa migração das tabelas baseado nos modelos SQLAlchemy

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar se Docker Compose está disponível
if ! command -v docker &> /dev/null; then
    error "Docker não encontrado. Instale Docker primeiro."
fi

# Verificar se o arquivo docker-compose.yml existe
if [ ! -f "docker-compose.yml" ]; then
    error "Arquivo docker-compose.yml não encontrado. Execute este script na raiz do projeto."
fi

echo "=========================================="
echo "🗄️  MIGRAÇÃO DO BANCO DE DADOS - AGENTAPI"
echo "=========================================="
echo ""

# Verificar se os serviços estão rodando
log "Verificando status dos serviços..."

if ! docker compose ps postgres | grep -q "Up"; then
    warning "PostgreSQL não está rodando. Iniciando serviços..."
    docker compose up -d postgres redis
    log "Aguardando PostgreSQL inicializar..."
    sleep 10
else
    success "PostgreSQL está rodando"
fi

# Opções de migração
VERIFY_ONLY=false
SEED_DATA=false

# Processar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        --seed)
            SEED_DATA=true
            shift
            ;;
        --help)
            echo "Uso: $0 [opções]"
            echo ""
            echo "Opções:"
            echo "  --verify-only    Apenas verifica se o schema está sincronizado"
            echo "  --seed          Cria dados iniciais após migração"
            echo "  --help          Mostra esta ajuda"
            echo ""
            exit 0
            ;;
        *)
            error "Opção desconhecida: $1. Use --help para ver as opções disponíveis."
            ;;
    esac
done

# Construir argumentos para o comando de migração
MIGRATE_ARGS=""
if [ "$VERIFY_ONLY" = true ]; then
    MIGRATE_ARGS="$MIGRATE_ARGS --verify-only"
fi
if [ "$SEED_DATA" = true ]; then
    MIGRATE_ARGS="$MIGRATE_ARGS --seed"
fi

# Executar migração
log "Executando migração..."

if [ "$VERIFY_ONLY" = true ]; then
    log "Modo verificação: apenas checando sincronização do schema"
else
    log "Aplicando migrações necessárias..."
fi

# Executar comando de migração no container da API
if docker compose exec api python -m api.db.migrate $MIGRATE_ARGS; then
    if [ "$VERIFY_ONLY" = true ]; then
        success "Verificação concluída"
    else
        success "Migração concluída com sucesso!"
    fi
else
    error "Falha na migração"
fi

echo ""
echo "=========================================="
echo "📋 COMANDOS ÚTEIS:"
echo "=========================================="
echo ""
echo "# Verificar apenas (sem aplicar mudanças):"
echo "  ./migrate.sh --verify-only"
echo ""
echo "# Migração completa com dados iniciais:"
echo "  ./migrate.sh --seed"
echo ""
echo "# Conectar ao PostgreSQL:"
echo "  docker compose exec postgres psql -U agent -d agentgraph"
echo ""
echo "# Ver logs da API:"
echo "  docker compose logs -f api"
echo ""
echo "# Reiniciar serviços:"
echo "  docker compose restart"
echo ""
echo "=========================================="
