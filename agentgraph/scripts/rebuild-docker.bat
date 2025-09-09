@echo off
echo ========================================
echo AgentGraph - Rebuild Docker
echo ========================================

echo 🛑 Parando containers existentes...
docker-compose down

echo 🔨 Reconstruindo imagem Docker...
docker-compose build --no-cache

echo 🚀 Iniciando aplicação...
docker-compose up -d

if errorlevel 1 (
    echo ❌ Erro ao rebuild
    pause
    exit /b 1
)

echo ✅ Rebuild concluído com sucesso!
echo.
echo 🌐 Aguardando link público do Gradio...
echo.

REM Aguardar alguns segundos
timeout /t 5 /nobreak >nul

REM Mostrar logs
echo 📊 Logs da aplicação (Ctrl+C para sair):
echo ==========================================
docker-compose logs -f agentgraph
