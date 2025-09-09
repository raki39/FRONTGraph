#!/usr/bin/env node

/**
 * Script para verificar dependências do frontend
 * Equivalente a um requirements checker para Node.js
 */

const fs = require('fs');
const { execSync } = require('child_process');

console.log('🔍 Verificando dependências do Frontend AgentAPI...\n');

// Cores para output
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// Verificar se Node.js está na versão correta
function checkNodeVersion() {
  const nodeVersion = process.version;
  const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
  
  if (majorVersion >= 18) {
    log('green', `✅ Node.js ${nodeVersion} (OK)`);
    return true;
  } else {
    log('red', `❌ Node.js ${nodeVersion} (Necessário: 18+)`);
    return false;
  }
}

// Verificar se npm está na versão correta
function checkNpmVersion() {
  try {
    const npmVersion = execSync('npm --version', { encoding: 'utf8' }).trim();
    const majorVersion = parseInt(npmVersion.split('.')[0]);
    
    if (majorVersion >= 8) {
      log('green', `✅ npm ${npmVersion} (OK)`);
      return true;
    } else {
      log('red', `❌ npm ${npmVersion} (Necessário: 8+)`);
      return false;
    }
  } catch (error) {
    log('red', '❌ npm não encontrado');
    return false;
  }
}

// Verificar se package.json existe
function checkPackageJson() {
  if (fs.existsSync('package.json')) {
    log('green', '✅ package.json encontrado');
    return true;
  } else {
    log('red', '❌ package.json não encontrado');
    return false;
  }
}

// Verificar se node_modules existe
function checkNodeModules() {
  if (fs.existsSync('node_modules')) {
    log('green', '✅ node_modules encontrado');
    return true;
  } else {
    log('yellow', '⚠️ node_modules não encontrado (execute: npm install)');
    return false;
  }
}

// Verificar dependências específicas
function checkSpecificDependencies() {
  const requiredDeps = [
    'next',
    'react',
    'react-dom',
    'axios',
    'react-hook-form',
    'tailwindcss',
    'typescript'
  ];

  let allFound = true;

  for (const dep of requiredDeps) {
    try {
      require.resolve(dep);
      log('green', `✅ ${dep}`);
    } catch (error) {
      log('red', `❌ ${dep} não encontrado`);
      allFound = false;
    }
  }

  return allFound;
}

// Verificar arquivos de configuração
function checkConfigFiles() {
  const configFiles = [
    'next.config.js',
    'tailwind.config.js',
    'tsconfig.json',
    '.env.example'
  ];

  let allFound = true;

  for (const file of configFiles) {
    if (fs.existsSync(file)) {
      log('green', `✅ ${file}`);
    } else {
      log('red', `❌ ${file} não encontrado`);
      allFound = false;
    }
  }

  return allFound;
}

// Verificar se pode fazer build
function checkBuild() {
  try {
    log('blue', '🔨 Testando build...');
    execSync('npm run type-check', { stdio: 'pipe' });
    log('green', '✅ TypeScript check passou');
    return true;
  } catch (error) {
    log('red', '❌ Erro no TypeScript check');
    console.log(error.stdout?.toString() || error.message);
    return false;
  }
}

// Função principal
function main() {
  let allChecksPass = true;

  console.log('📋 Verificando pré-requisitos...');
  allChecksPass &= checkNodeVersion();
  allChecksPass &= checkNpmVersion();
  
  console.log('\n📦 Verificando arquivos do projeto...');
  allChecksPass &= checkPackageJson();
  allChecksPass &= checkNodeModules();
  
  console.log('\n🔧 Verificando arquivos de configuração...');
  allChecksPass &= checkConfigFiles();
  
  if (fs.existsSync('node_modules')) {
    console.log('\n📚 Verificando dependências...');
    allChecksPass &= checkSpecificDependencies();
    
    console.log('\n🔨 Verificando build...');
    allChecksPass &= checkBuild();
  }

  console.log('\n' + '='.repeat(50));
  
  if (allChecksPass) {
    log('green', '🎉 Todas as verificações passaram!');
    log('blue', '🚀 Pronto para executar: npm run dev');
  } else {
    log('red', '❌ Algumas verificações falharam');
    log('yellow', '💡 Execute: npm install');
  }
  
  console.log('');
}

// Executar se chamado diretamente
if (require.main === module) {
  main();
}

module.exports = {
  checkNodeVersion,
  checkNpmVersion,
  checkPackageJson,
  checkNodeModules,
  checkSpecificDependencies,
  checkConfigFiles
};
