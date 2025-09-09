import os
import logging
import time
import requests
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='[TEST] %(message)s')
log = logging.getLogger("history_integration_test")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
AGENT_ID = int(os.getenv("AGENT_ID", "1"))


# Helpers to connect to Postgres used by the API
def _pg_url() -> str:
    host = os.getenv("PG_HOST", "localhost")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB", "agentgraph")
    user = os.getenv("PG_USER", "agent")
    password = os.getenv("PG_PASSWORD", "agent")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def login(email: str = "admin@example.com", password: str = "admin") -> str:
    """Perform login using API and return Bearer token."""
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": email,
        "password": password,
    })
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Token not found in login response")
    log.info("Autenticado com sucesso (token obtido)")
    return token


def run_question(token: str, agent_id: int, question: str, chat_session_id: int | None = None) -> dict:
    """Call /agents/{agent_id}/run with question (+ optional chat_session_id), poll /runs/{id} until done, return run record."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"question": question}
    if chat_session_id:
        payload["chat_session_id"] = chat_session_id
    res = requests.post(f"{BASE_URL}/agents/{agent_id}/run", headers=headers, json=payload)
    if res.status_code != 200:
        raise RuntimeError(f"run POST failed: {res.status_code} {res.text}")
    run = res.json()
    run_id = run["id"]
    log.info(f"Run criada: id={run_id} | chat_session_id={run.get('chat_session_id')}")

    # Poll status
    for _ in range(60):  # up to ~60s
        time.sleep(1)
        st = requests.get(f"{BASE_URL}/runs/{run_id}", headers=headers)
        if st.status_code != 200:
            continue
        rd = st.json()
        status = rd.get("status")
        log.info(f"Status da run {run_id}: {status}")
        if status in ("success", "failure"):
            return rd
    raise TimeoutError("Timeout aguardando conclusão da run")



def create_chat_session(session, user_id: int, agent_id: int) -> int:
    """Create a new chat_session and return its ID."""
    res = session.execute(text(
        """
        INSERT INTO chat_sessions (user_id, agent_id, title, created_at, last_activity, total_messages, status)
        VALUES (:user_id, :agent_id, :title, NOW(), NOW(), 0, 'active')
        RETURNING id
        """
    ), {"user_id": user_id, "agent_id": agent_id, "title": f"Teste {datetime.now().strftime('%d/%m %H:%M')}"})
    chat_session_id = res.fetchone()[0]
    session.commit()
    return chat_session_id


def insert_interaction(session, chat_session_id: int, user_text: str, assistant_text: str, sql_query: str | None, base_seq: int) -> None:
    """Insert a user+assistant pair with given sequence order start (base_seq, base_seq+1)."""
    msgs = [
        (chat_session_id, None, 'user', user_text, None, base_seq),
        (chat_session_id, None, 'assistant', assistant_text, sql_query, base_seq + 1),
    ]
    for (csid, run_id, role, content, sqlq, seq) in msgs:
        session.execute(text(
            """
            INSERT INTO messages (chat_session_id, run_id, role, content, sql_query, sequence_order, created_at)
            VALUES (:csid, :run_id, :role, :content, :sqlq, :seq, NOW())
            """
        ), {"csid": csid, "run_id": run_id, "role": role, "content": content, "sqlq": sqlq, "seq": seq})
    session.execute(text(
        "UPDATE chat_sessions SET total_messages = total_messages + 2, last_activity = NOW() WHERE id = :id"
    ), {"id": chat_session_id})
    session.commit()


def ensure_dummy_embeddings(session, chat_session_id: int) -> None:
    """Attempt to insert dummy embeddings if the fallback column exists."""
    try:
        col_query = text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'message_embeddings' AND column_name = 'embedding_text'
            """
        )
        has_text = session.execute(col_query).fetchone() is not None
        if not has_text:
            log.info("message_embeddings usa pgvector (sem embedding_text). Pulando embeddings simulados.")
            return
        # attach embeddings to the two latest messages
        msg_ids = session.execute(text(
            "SELECT id FROM messages WHERE chat_session_id = :cs ORDER BY id DESC LIMIT 2"
        ), {"cs": chat_session_id}).fetchall()
        for row in msg_ids:
            session.execute(text(
                """
                INSERT INTO message_embeddings (message_id, embedding_text, model_version, created_at)
                VALUES (:mid, :emb, :model, NOW())
                """
            ), {"mid": row[0], "emb": "[0.1, 0.1, 0.1]", "model": "text-embedding-3-small"})
        session.commit()
        log.info("Embeddings simulados inseridos para as mensagens mais recentes da sessão")
    except Exception as e:
        log.warning(f"Falha ao inserir embeddings simulados: {e}")



def ensure_user_and_agent(session) -> tuple[int, int]:
    """Ensure a test user, connection, and agent exist. Returns (user_id, agent_id)."""
    # Create user
    user_id = session.execute(text(
        "INSERT INTO users (email, senha_hash, nome, ativo, created_at) VALUES (:e, :p, :n, true, NOW()) RETURNING id"
    ), {"e": f"test_{int(datetime.now().timestamp())}@example.com", "p": "x", "n": "Test User"}).fetchone()[0]

    # Create connection (sqlite) and agent
    conn_id = session.execute(text(
        "INSERT INTO agent_connections (owner_user_id, tipo, db_uri, created_at) VALUES (:u, 'sqlite', :db, NOW()) RETURNING id"
    ), {"u": user_id, "db": "sqlite:///./test_history.db"}).fetchone()[0]

    agent_id = session.execute(text(
        """
        INSERT INTO agents (
            owner_user_id, nome, connection_id, selected_model, top_k, include_tables_key,
            advanced_mode, processing_enabled, refinement_enabled, single_table_mode, selected_table,
            version, created_at, updated_at
        ) VALUES (
            :u, :name, :cid, 'GPT-4o-mini', 10, '*', false, false, false, false, NULL, 1, NOW(), NOW()
        ) RETURNING id
        """
    ), {"u": user_id, "name": f"Agent Test {datetime.now().strftime('%H%M%S')}", "cid": conn_id}).fetchone()[0]

    session.commit()
    return user_id, agent_id


def test_history_retrieval_and_context(session, chat_session_id: int, user_id: int, agent_id: int, query_text: str):
    """Retrieve history and format context. Validate Pergunta/Resposta appear and log concise summary."""
    from agentgraph.services.history_service import HistoryService

    svc = HistoryService()
    try:
        relevant = svc.get_relevant_history(user_id=user_id, agent_id=agent_id, query_text=query_text, chat_session_id=chat_session_id, limit=15)
        context = svc.format_history_for_context(relevant)

        log.info(f"[CTX] msgs={len(relevant)} | chars={len(context)} | query='{query_text}'")
        has_q = "Pergunta" in context
        has_a = "Resposta" in context
        if has_q and has_a:
            log.info("[CTX] OK: Contexto contém Pergunta e Resposta")
        else:
            log.error("[CTX] FALHA: Contexto não contém Pergunta/Resposta")

        preview = "\n".join(context.splitlines()[:10])
        log.info("[CTX] Preview:\n" + preview)
    finally:
        svc.close()


def test_worker_sets_use_celery_false():
    """Patch AgentGraphManager.process_query to assert use_celery=False inside the worker pipeline.
    We call tasks.execute_langgraph_pipeline, which will set use_celery=False by design.
    """
    import agentgraph.tasks as tasks
    from agentgraph.graphs import main_graph as mg

    # Prepare SQLite db for the AgentGraphManager to accept
    sqlite_uri = "sqlite:///./test_history.db"
    _ensure_sqlite_db(sqlite_uri)

    # Prepare a fake process_query to capture kwargs
    captured = {"called": False, "use_celery": None}

    async def fake_process_query(self, **kwargs):
        captured["called"] = True
        captured["use_celery"] = kwargs.get("use_celery")
        # Minimal result structure expected by pipeline
        return {"response": "ok", "intermediate_steps": [], "sql_query": None}

    # Patch
    original = mg.AgentGraphManager.process_query
    mg.AgentGraphManager.process_query = fake_process_query

    try:
        agent_config = {
            "tenant_id": "test",
            "connection_type": "csv",
            "db_uri": sqlite_uri,
            "selected_model": "gpt-4o-mini",
            "advanced_mode": False,
            "processing_enabled": False,
            "refinement_enabled": False,
            "single_table_mode": False,
            "top_k": 5,
        }
        result = tasks.execute_langgraph_pipeline(
            user_input="Teste pipeline",
            agent_config=agent_config,
            chat_session_id=None,
            user_id=9999,
            run_id=None,
        )
        # execute_langgraph_pipeline returns a dict, not raising if patched function returned ok
        assert isinstance(result, dict)
        # Validate the flag
        if captured["called"] and captured["use_celery"] is False:
            log.info("OK: Worker forçou use_celery=False ao chamar process_query")
        else:
            log.error(f"FALHA: Esperado use_celery=False no worker | captured={captured}")
    finally:
        mg.AgentGraphManager.process_query = original


def main():
    # 1) Login
    token = login()

    # 2) Rodar 3 perguntas na API usando o agente existente
    log.info("Iniciando trilha de 3 perguntas usando API (criando e reutilizando chat_session)")

    # Pergunta 1 - nova sessão será criada pelo endpoint automaticamente
    r1 = run_question(token, AGENT_ID, "Quais são os top 5 produtos por vendas?")
    csid = r1.get("chat_session_id")
    log.info(f"P1 concluída | chat_session_id={csid}")

    # Pergunta 2 - mesma sessão
    r2 = run_question(token, AGENT_ID, "E no último mês, houve queda?", chat_session_id=csid)
    log.info("P2 concluída")

    # Pergunta 3 - mesma sessão
    r3 = run_question(token, AGENT_ID, "Quais categorias cresceram mais?", chat_session_id=csid)
    log.info("P3 concluída")

    # 3) Verificações no Postgres: recuperar e validar contexto gerado via HistoryService
    pg_url = _pg_url()
    engine = create_engine(pg_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Validar contexto após 3 perguntas, cada uma com uma consulta diferente
        test_history_retrieval_and_context(session, csid, r1["user_id"], r1["agent_id"], query_text="top 5")
        test_history_retrieval_and_context(session, csid, r1["user_id"], r1["agent_id"], query_text="queda")
        test_history_retrieval_and_context(session, csid, r1["user_id"], r1["agent_id"], query_text="categorias")

        # 4) Validar que o worker forçou use_celery=False
        test_worker_sets_use_celery_false()

        log.info("\n===== RESULTADO DOS TESTES =====")
        log.info("- Deve haver 'OK' nos três contextos e no worker.")
    finally:
        session.close()


if __name__ == "__main__":
    main()

