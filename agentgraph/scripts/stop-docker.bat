@echo off
echo ========================================
echo AgentGraph - Parar Docker
echo ========================================

echo 🛑 Parando AgentGraph...

docker-compose down

if errorlevel 1 (
    echo ❌ Erro ao parar aplicação
    pause
    exit /b 1
)

echo ✅ AgentGraph parado com sucesso!
echo.
echo 📊 Para ver containers rodando:
echo    docker ps
echo.
echo 🚀 Para iniciar novamente:
echo    run-docker.bat
echo.
pause
