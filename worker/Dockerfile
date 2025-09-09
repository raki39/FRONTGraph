FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

COPY agentgraph/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia código do agente
COPY agentgraph /app/agentgraph

ENV PYTHONPATH=/app

CMD ["python", "-m", "celery", "-A", "agentgraph.tasks", "worker", "--loglevel=INFO"]

