@echo off
echo ========================================
echo AgentGraph - Docker Production Mode
echo ========================================

REM Verificar se Docker está instalado
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker não está instalado. Instale o Docker Desktop primeiro.
    echo Download: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM Verificar se Docker Compose está instalado
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose não está instalado.
    pause
    exit /b 1
)

REM Verificar se Docker está rodando
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker não está rodando. Inicie o Docker Desktop primeiro.
    pause
    exit /b 1
)

REM Verificar se .env existe
if not exist .env (
    echo ⚠️ Arquivo .env não encontrado
    echo 💡 Crie um arquivo .env com suas API keys:
    echo    OPENAI_API_KEY=sua_chave_aqui
    echo    ANTHROPIC_API_KEY=sua_chave_aqui
    echo    HUGGINGFACE_API_KEY=sua_chave_aqui
    echo.
    pause
)

echo 🧹 Parando containers existentes...
docker-compose down

echo 🔨 Construindo imagem Docker...
docker-compose build

echo 🚀 Iniciando AgentGraph com Redis + Celery (2 workers x 4 concurrency = 8 processos)...
echo 🔥 Gradio sem fila - Concorrência ilimitada para múltiplos usuários
echo ⏱️ Celery configurado para tabelas grandes (120min timeout)
echo 🛡️ Configurações de reliability e fault tolerance habilitadas
echo.
echo 📊 Serviços disponíveis:
echo    - AgentGraph: http://localhost:7860 (sem fila)
echo    - Flower Dashboard: http://localhost:5555 (admin/admin)
echo    - Redis: localhost:6379
echo.
echo 🛑 Para parar: Ctrl+C
echo.

docker-compose up

echo.
echo 🧹 Limpando containers...
docker-compose down

echo ✅ AgentGraph Docker finalizado
pause
