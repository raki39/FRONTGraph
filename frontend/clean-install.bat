@echo off
echo ========================================
echo    LIMPEZA E REINSTALACAO DO FRONTEND
echo ========================================
echo.

echo [1/5] Parando processos Node.js...
taskkill /f /im node.exe 2>nul
taskkill /f /im npm.exe 2>nul
echo ✅ Processos Node.js finalizados

echo.
echo [2/5] Removendo node_modules...
if exist node_modules (
    echo Removendo node_modules... (pode demorar)
    rmdir /s /q node_modules
    echo ✅ node_modules removido
) else (
    echo ℹ️  node_modules nao encontrado
)

echo.
echo [3/5] Removendo arquivos de lock...
if exist package-lock.json (
    del package-lock.json
    echo ✅ package-lock.json removido
) else (
    echo ℹ️  package-lock.json nao encontrado
)

if exist yarn.lock (
    del yarn.lock
    echo ✅ yarn.lock removido
)

echo.
echo [4/5] Limpando cache do npm (com timeout)...
timeout /t 2 /nobreak >nul
npm cache clean --force --silent 2>nul || echo ⚠️  Cache nao pode ser limpo (continuando...)
echo ✅ Tentativa de limpeza de cache concluida

echo.
echo [5/5] Instalando dependencias...
echo Instalando... (pode demorar alguns minutos)
npm install --no-audit --no-fund
if %errorlevel% equ 0 (
    echo ✅ Dependencias instaladas com sucesso
) else (
    echo ❌ Erro na instalacao das dependencias
    echo Tentando novamente com cache limpo...
    npm cache clean --force --silent 2>nul
    npm install --no-audit --no-fund
)

echo.
echo ========================================
echo    INSTALACAO CONCLUIDA!
echo ========================================
echo.
echo Para iniciar o servidor de desenvolvimento:
echo npm run dev
echo.
pause
