# AgentAPI Frontend

Interface web moderna para o AgentAPI, construída com Next.js 14, TypeScript e Tailwind CSS.

## 🚀 Funcionalidades

- **Autenticação JWT**: Login/registro seguro
- **Dashboard**: Visão geral de agentes e atividades
- **Gerenciamento de Conexões**: Configure conexões PostgreSQL
- **Gerenciamento de Agentes**: Crie e configure agentes de IA
- **Chat em Tempo Real**: Interface conversacional com polling automático
- **Design Responsivo**: Funciona em desktop e mobile

## 🛠️ Tecnologias

- **Next.js 14**: Framework React com App Router
- **TypeScript**: Tipagem estática
- **Tailwind CSS**: Estilização utilitária
- **Axios**: Cliente HTTP
- **React Hook Form**: Gerenciamento de formulários
- **Lucide React**: Ícones modernos
- **React Hot Toast**: Notificações

## 📦 Instalação

1. **Instalar dependências**:
```bash
cd frontend
npm install
```

2. **Configurar variáveis de ambiente**:
```bash
cp .env.example .env.local
```

3. **Executar em desenvolvimento**:
```bash
npm run dev
```

4. **Acessar**: http://localhost:3000

## 🔧 Configuração

### Variáveis de Ambiente

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
```

## 🏗️ Estrutura do Projeto

```
frontend/
├── app/                    # App Router (Next.js 14)
│   ├── globals.css        # Estilos globais
│   ├── layout.tsx         # Layout raiz
│   ├── page.tsx           # Página inicial (redirect)
│   ├── login/             # Página de login
│   ├── register/          # Página de registro
│   ├── dashboard/         # Dashboard principal
│   ├── connections/       # Gerenciamento de conexões
│   ├── agents/           # Gerenciamento de agentes
│   └── chat/             # Interface de chat
├── components/            # Componentes reutilizáveis
│   ├── ui/               # Componentes de UI base
│   └── layout/           # Componentes de layout
├── lib/                  # Utilitários e configurações
│   ├── api.ts           # Cliente API e tipos
│   ├── auth-context.tsx # Context de autenticação
│   └── utils.ts         # Funções utilitárias
└── public/              # Arquivos estáticos
```

## 🎨 Design System

### Cores Principais
- **Primary**: Azul (#3b82f6)
- **Success**: Verde (#10b981)
- **Warning**: Amarelo (#f59e0b)
- **Error**: Vermelho (#ef4444)

### Componentes Base
- **Buttons**: `.btn-primary`, `.btn-secondary`
- **Inputs**: `.input-field`
- **Cards**: `.card`
- **Chat**: `.chat-message`

## 🔐 Autenticação

O sistema usa JWT tokens armazenados em cookies:

- **Login**: POST `/auth/login`
- **Registro**: POST `/auth/register`
- **Verificação**: GET `/users/me`
- **Logout**: Remove cookies localmente

## 📡 Integração com API

### Cliente HTTP (Axios)

```typescript
// Configuração automática de headers
api.interceptors.request.use((config) => {
  const token = Cookies.get('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Polling de Status

O chat implementa polling automático para runs em execução:

```typescript
// Verifica status a cada 2 segundos
useEffect(() => {
  if (pollingRuns.size > 0) {
    intervalRef.current = setInterval(checkRunStatus, 2000)
  }
}, [pollingRuns])
```

## 🚀 Deploy

### Vercel (Recomendado)

1. **Conectar repositório** no Vercel
2. **Configurar variável de ambiente**:
   - `NEXT_PUBLIC_API_BASE_URL`: URL da sua API
3. **Deploy automático** a cada push

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Build Manual

```bash
npm run build
npm start
```

## 🔍 Funcionalidades Detalhadas

### Dashboard
- Estatísticas de agentes, conexões e runs
- Atividade recente
- Links rápidos para principais funcionalidades

### Conexões
- Formulário para PostgreSQL
- Validação de campos obrigatórios
- Listagem com informações de conexão

### Agentes
- Seleção de modelo de IA (GPT-4o, Claude, Gemini)
- Configurações avançadas (top_k, tabelas, etc.)
- Link direto para chat

### Chat
- Interface conversacional intuitiva
- Polling automático para status de runs
- Exibição de SQL executado
- Métricas de performance (tempo, linhas)
- Status visual das mensagens

## 🐛 Troubleshooting

### Erro de CORS
Certifique-se que a API está configurada para aceitar requests do frontend:

```python
# Na API FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erro de Conexão
Verifique se:
1. A API está rodando na porta 8000
2. A variável `NEXT_PUBLIC_API_BASE_URL` está correta
3. Não há firewall bloqueando a conexão

### Problemas de Build
```bash
# Limpar cache
rm -rf .next node_modules
npm install
npm run build
```

## 📝 Próximos Passos

- [ ] Implementar sistema de sessões de chat
- [ ] Adicionar suporte a upload de CSV
- [ ] Implementar visualizações de dados
- [ ] Adicionar temas dark/light
- [ ] Implementar notificações em tempo real (WebSocket)
- [ ] Adicionar testes automatizados

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request
