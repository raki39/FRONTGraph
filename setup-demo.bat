@echo off
echo 🚀 Setup Completo do AgentAPI para Demonstração
echo ==============================================

REM Verificar pré-requisitos
echo 📋 Verificando pré-requisitos...

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker não encontrado. Instale Docker primeiro.
    pause
    exit /b 1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker Compose não encontrado. Instale Docker Compose primeiro.
    pause
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js não encontrado. Instale Node.js 18+ primeiro.
    pause
    exit /b 1
)

echo ✅ Todos os pré-requisitos atendidos

REM Configurar variáveis de ambiente
echo ⚙️ Configurando variáveis de ambiente...

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo 📝 Arquivo .env criado a partir do .env.example
        echo    Edite o arquivo .env com suas configurações antes de continuar
    ) else (
        echo ❌ Arquivo .env.example não encontrado
        pause
        exit /b 1
    )
)

REM Configurar frontend
echo 🌐 Configurando frontend...

cd frontend

if not exist ".env.local" (
    copy .env.example .env.local
    echo ✅ Arquivo .env.local criado
)

if not exist "node_modules" (
    echo 📦 Instalando dependências do frontend...
    npm install
    echo ✅ Dependências instaladas
)

cd ..

REM Iniciar serviços
echo 🐳 Iniciando serviços com Docker...

REM Parar serviços se estiverem rodando
docker-compose -f docker-compose.api.yml down >nul 2>nul

REM Iniciar serviços
docker-compose -f docker-compose.api.yml up -d

REM Aguardar serviços ficarem prontos
echo ⏳ Aguardando serviços ficarem prontos...
timeout /t 10 /nobreak >nul

REM Verificar se API está respondendo
echo 🔍 Verificando API...
for /l %%i in (1,1,30) do (
    curl -s http://localhost:8000/health >nul 2>nul
    if %errorlevel% equ 0 (
        echo ✅ API está respondendo
        goto api_ready
    )
    echo    Tentativa %%i/30...
    timeout /t 2 /nobreak >nul
)

echo ❌ API não está respondendo após 30 tentativas
echo    Verifique os logs: docker-compose -f docker-compose.api.yml logs
pause
exit /b 1

:api_ready

REM Iniciar frontend
echo 🌐 Iniciando frontend...
cd frontend
start /b npm run dev
cd ..

REM Aguardar frontend ficar pronto
echo ⏳ Aguardando frontend ficar pronto...
timeout /t 5 /nobreak >nul

REM Verificar se frontend está respondendo
for /l %%i in (1,1,15) do (
    curl -s http://localhost:3000 >nul 2>nul
    if %errorlevel% equ 0 (
        echo ✅ Frontend está respondendo
        goto frontend_ready
    )
    echo    Tentativa %%i/15...
    timeout /t 2 /nobreak >nul
)

echo ❌ Frontend não está respondendo
pause
exit /b 1

:frontend_ready

REM Sucesso!
echo.
echo 🎉 Setup completo! Sistema pronto para demonstração
echo.
echo 📍 URLs de Acesso:
echo    🌐 Frontend: http://localhost:3000
echo    🔧 API: http://localhost:8000
echo    📚 Documentação: http://localhost:8000/docs
echo.
echo 📋 Próximos passos:
echo    1. Acesse http://localhost:3000
echo    2. Crie uma conta de usuário
echo    3. Configure uma conexão PostgreSQL
echo    4. Crie um agente
echo    5. Teste o chat!
echo.
echo 📖 Guia completo: DEMO_INSTRUCTIONS.md
echo.
echo 💡 Para parar os serviços:
echo    docker-compose -f docker-compose.api.yml down
echo.
echo ✨ Demonstração pronta!
echo.
echo Pressione qualquer tecla para abrir o navegador...
pause >nul

REM Abrir navegador
start http://localhost:3000
