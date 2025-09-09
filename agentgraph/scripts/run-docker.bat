@echo off
echo ========================================
echo AgentGraph - Docker com Link Publico
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

REM Criar arquivo .env se não existir
if not exist .env (
    echo 📝 Criando arquivo .env...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANTE: Configure suas API keys no arquivo .env
    echo    Abra o arquivo .env e adicione pelo menos uma chave de API:
    echo    - OPENAI_API_KEY
    echo    - ANTHROPIC_API_KEY  
    echo    - HUGGINGFACE_API_KEY
    echo.
    pause
)

REM Criar diretório para uploads
if not exist uploaded_data mkdir uploaded_data

echo 🚀 Iniciando AgentGraph com Docker...
echo    (Incluindo tabela.csv necessária para inicialização)
echo.

REM Parar containers existentes
docker-compose down >nul 2>&1

REM Iniciar aplicação com rebuild
echo 🔨 Construindo imagem Docker...
docker-compose up --build -d

if errorlevel 1 (
    echo ❌ Erro ao iniciar aplicação
    pause
    exit /b 1
)

echo ✅ AgentGraph iniciado com sucesso!
echo.
echo 🌐 Aguardando link público do Gradio...
echo    O link será exibido nos logs abaixo:
echo.

REM Aguardar alguns segundos
timeout /t 5 /nobreak >nul

REM Mostrar logs
echo 📊 Logs da aplicação (Ctrl+C para sair):
echo ==========================================
docker-compose logs -f agentgraph
