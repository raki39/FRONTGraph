# Use Node.js 18 Alpine como base
FROM node:18-alpine

# Instalar libc6-compat para compatibilidade
RUN apk add --no-cache libc6-compat

# Definir diretório de trabalho
WORKDIR /app

# Copiar package.json e package-lock.json
COPY package*.json ./

# Instalar dependências com cache limpo e sem cache npm
RUN npm ci --no-audit --no-fund --cache /tmp/.npm

# Copiar código fonte
COPY . .

# Expor porta 3000
EXPOSE 3000

# Comando para iniciar em modo desenvolvimento
CMD ["npm", "run", "dev"]
