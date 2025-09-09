# 📦 Instalação do Frontend AgentAPI

## 🔧 Pré-requisitos

- **Node.js**: 18.0.0 ou superior
- **npm**: 8.0.0 ou superior (ou yarn/pnpm)

### Verificar versões instaladas:
```bash
node --version
npm --version
```

## 🚀 Instalação Rápida

### Opção 1: Script Automático (Recomendado)

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### Opção 2: Manual

```bash
# 1. Navegar para a pasta do frontend
cd frontend

# 2. Instalar dependências
npm install

# 3. Configurar variáveis de ambiente
cp .env.example .env.local

# 4. Executar em modo desenvolvimento
npm run dev
```

## 📋 Dependências Principais

### Runtime Dependencies
```json
{
  "next": "14.0.4",           // Framework React
  "react": "^18.2.0",         // Biblioteca React
  "react-dom": "^18.2.0",     // React DOM
  "axios": "^1.6.2",          // Cliente HTTP
  "react-hook-form": "^7.48.2", // Formulários
  "zod": "^3.22.4",           // Validação
  "lucide-react": "^0.294.0", // Ícones
  "react-hot-toast": "^2.4.1", // Notificações
  "js-cookie": "^3.0.5",      // Cookies
  "clsx": "^2.0.0",           // Classes condicionais
  "tailwind-merge": "^2.2.0"  // Merge classes Tailwind
}
```

### Development Dependencies
```json
{
  "@types/node": "^20.10.0",
  "@types/react": "^18.2.45",
  "@types/react-dom": "^18.2.18",
  "@types/js-cookie": "^3.0.6",
  "typescript": "^5.3.3",
  "tailwindcss": "^3.3.6",
  "autoprefixer": "^10.4.16",
  "postcss": "^8.4.32",
  "eslint": "^8.56.0",
  "eslint-config-next": "14.0.4"
}
```

## ⚙️ Configuração

### Variáveis de Ambiente

Crie o arquivo `.env.local`:
```env
# URL da API do AgentAPI
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Scripts Disponíveis

```bash
# Desenvolvimento
npm run dev

# Build para produção
npm run build

# Executar build de produção
npm start

# Linting
npm run lint

# Verificação de tipos
npm run type-check
```

## 🔍 Verificação da Instalação

### 1. Verificar se as dependências foram instaladas:
```bash
ls node_modules
```

### 2. Verificar se o servidor inicia:
```bash
npm run dev
```

### 3. Acessar no navegador:
```
http://localhost:3000
```

## 🐛 Troubleshooting

### Erro: "Module not found"
```bash
# Limpar cache e reinstalar
rm -rf node_modules package-lock.json
npm install
```

### Erro: "Port 3000 already in use"
```bash
# Usar porta diferente
npm run dev -- -p 3001
```

### Erro: "TypeScript errors"
```bash
# Verificar tipos
npm run type-check
```

### Erro: "EACCES permission denied"
```bash
# Linux/Mac: Corrigir permissões npm
sudo chown -R $(whoami) ~/.npm
```

## 📊 Verificação de Saúde

Após a instalação, verifique se tudo está funcionando:

### ✅ Checklist
- [ ] Node.js 18+ instalado
- [ ] npm 8+ instalado
- [ ] Dependências instaladas sem erros
- [ ] Arquivo .env.local configurado
- [ ] Servidor inicia em http://localhost:3000
- [ ] Página de login carrega
- [ ] Console sem erros críticos

### 🔧 Comandos de Diagnóstico
```bash
# Verificar versões
node --version
npm --version

# Verificar dependências
npm list

# Verificar build
npm run build

# Verificar tipos
npm run type-check
```

## 🚀 Próximos Passos

Após a instalação bem-sucedida:

1. **Iniciar a API**: Certifique-se que o backend está rodando
2. **Acessar**: http://localhost:3000
3. **Criar conta**: Registrar um novo usuário
4. **Configurar**: Adicionar conexão PostgreSQL
5. **Testar**: Criar agente e fazer perguntas

## 📞 Suporte

Se encontrar problemas:

1. **Verificar logs**: Console do navegador e terminal
2. **Consultar documentação**: README.md
3. **Verificar API**: http://localhost:8000/docs
4. **Limpar cache**: `rm -rf .next node_modules && npm install`

---

**Tempo estimado de instalação**: 2-5 minutos
**Tamanho das dependências**: ~200MB
