# AgentGraph API

API multi-usuários que orquestra o AgentGraph via Celery/Redis, persiste metadados no Postgres e expõe endpoints REST.

## Endpoints

Veja a documentação interativa em:
- http://localhost:8000/docs

## Execução com Docker Compose

1. Build e up:

```
docker compose -f docker-compose.api.yml up --build
```

2. Criar tabelas e seed (opcional):

```
docker compose -f docker-compose.api.yml exec api python -m api.db.create_tables
docker compose -f docker-compose.api.yml exec api python -m api.db.seed
```

3. Testes rápidos:
- Login (crie admin via seed): POST /auth/login (username=admin@example.com, password=admin)
- Upload CSV: POST /datasets/upload
- Criar conexão (sqlite): POST /connections { tipo: "sqlite", dataset_id: <id> }
- Criar agente: POST /agents
- Executar run: POST /agents/{agent_id}/run { question }
- Acompanhar: GET /agents/{agent_id}/runs e GET /runs/{run_id}

## Observações
- A API salva a configuração do agente no Redis por agent_id e despacha a task process_sql_query.
- O worker atualiza a tabela runs (success/failure) usando PG_* do ambiente.
- CSVs são convertidos para SQLite e salvos no volume /shared-data para que o worker acesse.

