# AgentGraph - Dockerfile Simples
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar o pacote completo agentgraph para /app/agentgraph
COPY . /app/agentgraph

# Garantir CSV padrão disponível no diretório de trabalho e em uploaded_data
RUN mkdir -p /app/uploaded_data \
 && cp /app/agentgraph/tabela.csv /app/tabela.csv \
 && cp /app/agentgraph/tabela.csv /app/uploaded_data/tabela.csv

# Expor porta
EXPOSE 7860

# Executar como módulo de pacote para garantir imports absolutos
CMD ["python", "-m", "agentgraph.app"]
