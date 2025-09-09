@echo off
echo 🚀 Iniciando AgentAPI Frontend...

REM Verificar se Node.js está instalado
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js não encontrado. Instale Node.js 18+ primeiro.
    pause
    exit /b 1
)

REM Instalar dependências se necessário
if not exist "node_modules" (
    echo 📦 Instalando dependências...
    npm install
)

REM Verificar se .env.local existe
if not exist ".env.local" (
    echo ⚙️ Criando arquivo de configuração...
    copy .env.example .env.local
)

REM Iniciar servidor de desenvolvimento
echo 🌐 Iniciando servidor em http://localhost:3000
npm run dev
