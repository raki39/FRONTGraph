@echo off
echo ========================================
echo    REINSTALACAO FORCADA - FRONTEND
echo ========================================
echo.

echo Matando todos os processos Node.js...
taskkill /f /im node.exe 2>nul
taskkill /f /im npm.exe 2>nul
taskkill /f /im npx.exe 2>nul

echo.
echo Removendo TUDO...
if exist node_modules rmdir /s /q node_modules
if exist package-lock.json del package-lock.json
if exist yarn.lock del yarn.lock
if exist .next rmdir /s /q .next

echo.
echo Instalando sem cache...
npm install --no-cache --no-audit --no-fund --prefer-offline=false

echo.
echo ========================================
echo    PRONTO! Teste agora: npm run dev
echo ========================================
pause
