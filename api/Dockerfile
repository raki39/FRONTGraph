FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia projeto (API + agentgraph + tests + scripts para import)
COPY api /app/api
COPY agentgraph /app/agentgraph
COPY tests /app/tests
COPY scripts /app/scripts
COPY agentgraph/requirements.txt /app/agent-requirements.txt
RUN pip install --no-cache-dir -r /app/agent-requirements.txt

# Configurações do sistema de histórico
ENV HISTORY_ENABLED=true
ENV HISTORY_MAX_MESSAGES=15
ENV HISTORY_SIMILARITY_THRESHOLD=0.75

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

