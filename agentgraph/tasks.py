"""
Tasks do Celery para processamento de queries SQL
"""
import logging
import time
import json
import pandas as pd
from typing import Dict, Any, Optional
from celery import Celery
from sqlalchemy import create_engine, text

# Importa configurações
from agentgraph.utils.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, is_docker_environment, get_environment_info

# Log informações do ambiente no worker
env_info = get_environment_info()
logging.info(f"[CELERY_WORKER] Ambiente detectado: {env_info['environment']}")
logging.info(f"[CELERY_WORKER] Redis URL: {env_info['redis_url']}")
logging.info(f"[CELERY_WORKER] Concorrência esperada: {env_info['worker_concurrency']}")

# Configuração do Celery com logs
logging.info(f"[CELERY_CONFIG] Broker: {CELERY_BROKER_URL}")
logging.info(f"[CELERY_CONFIG] Backend: {CELERY_RESULT_BACKEND}")

celery_app = Celery(
    'agentgraph',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configurações do Celery (sem worker_pool - definido no comando)
if is_docker_environment():
    # Docker: Configurações permissivas para tabelas grandes
    celery_app.conf.update(
        # Serialização
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',

        # Timezone
        timezone='UTC',
        enable_utc=True,

        # Task tracking
        task_track_started=True,

        # Timeouts estendidos para tabelas grandes
        task_time_limit=120 * 60,  # 120 minutos (2 horas)
        task_soft_time_limit=110 * 60,  # 110 minutos

        # Worker configuration
        worker_prefetch_multiplier=1,  # Uma task por vez para evitar sobrecarga
        worker_max_tasks_per_child=50,  # Reinicia worker após 50 tasks
        worker_disable_rate_limits=True,

        # Task acknowledgment - configurações para reliability
        task_acks_late=True,  # Confirma apenas após conclusão
        task_acks_on_failure_or_timeout=True,  # Confirma mesmo em falha
        task_reject_on_worker_lost=True,  # Rejeita se worker morrer

        # Events (desabilitados para performance)
        worker_send_task_events=False,
        task_send_sent_event=False,

        # Result backend
        result_expires=24 * 60 * 60,  # Resultados expiram em 24h
        result_backend_always_retry=True,  # Retry em erros recuperáveis
        result_backend_max_retries=10,  # Máximo 10 retries
    )
    logging.info("[CELERY_CONFIG] Configuração Docker permissiva aplicada (120min timeout)")
else:
    # Windows: Configurações padrão
    celery_app.conf.update(
        # Serialização
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',

        # Timezone
        timezone='UTC',
        enable_utc=True,

        # Task tracking
        task_track_started=True,

        # Timeouts padrão
        task_time_limit=30 * 60,  # 30 minutos
        task_soft_time_limit=25 * 60,  # 25 minutos

        # Worker configuration
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_disable_rate_limits=True,

        # Events (desabilitados para performance)
        worker_send_task_events=False,
        task_send_sent_event=False,

        # Result backend
        result_expires=24 * 60 * 60,  # Resultados expiram em 24h
    )
    logging.info("[CELERY_CONFIG] Configuração Windows padrão aplicada (30min timeout)")

# Log configuração aplicada
env_info = get_environment_info()
logging.info(f"[CELERY_CONFIG] Configuração aplicada para {env_info['environment']}")
logging.info(f"[CELERY_CONFIG] Pool será definido pelo comando do worker")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Registries de cache por processo do worker
_AGENT_REGISTRY = {}
_DB_REGISTRY = {}

def _key_fingerprint(key_tuple: tuple) -> str:
    """Retorna um fingerprint seguro da chave de cache (SHA1) sem expor segredos."""
    try:
        import hashlib
        # Converte para string estável sem senhas explícitas: mascara db_uri
        parts = list(key_tuple)
        # parts[0] is literal "DB" or "AGENT"; the actual fields start at 1
        # Estrutura esperada: (LABEL, tenant_id, model, connection_type, db_uri_or_path, include_tables_key, top_k)
        if len(parts) >= 6:
            db_uri = str(parts[4])
            if db_uri.startswith("postgresql://") and '@' in db_uri:
                # mascara senha
                try:
                    prefix, rest = db_uri.split('://', 1)
                    creds, hostdb = rest.split('@', 1)
                    user, pwd = creds.split(':', 1)
                    masked = f"{prefix}://{user}:***@{hostdb}"
                    parts[4] = masked
                except Exception:
                    parts[4] = "***"
        key_str = '|'.join(map(str, parts))
        return hashlib.sha1(key_str.encode('utf-8')).hexdigest()[:12]
    except Exception:
        return "unknown"
def _sqlite_fingerprint(db_uri: str) -> str:
    """Gera fingerprint leve (tamanho-mtime) para arquivo SQLite do db_uri."""
    try:
        import re, os
        m = re.match(r"sqlite:///(.+)", db_uri)
        if not m:
            return "unknown"
        db_path = "/" + m.group(1)  # Adicionar barra inicial para caminho absoluto
        if not os.path.exists(db_path):
            return "missing"
        st = os.stat(db_path)
        return f"{st.st_size}-{int(st.st_mtime)}"
    except Exception:
        return "unknown"

        return "unknown"


def _build_db_uri_or_path(agent_config: Dict[str, Any]) -> str:
    """Monta db_uri_or_path a partir da configuração. Para CSV/SQLite espera 'db_uri' no config."""
    connection_type = agent_config.get('connection_type', 'csv')
    if connection_type == 'csv':
        db_uri = agent_config.get('db_uri')
        if not db_uri:
            # Falha explícita orientando ingestão primeiro
            raise Exception("db_uri ausente para conexão CSV. Realize a ingestão (CSV->SQLite) antes de executar no worker.")
        return db_uri
    elif connection_type == 'postgresql':
        # Usa config explícita ou string db_uri, se existir
        if agent_config.get('db_uri'):
            return agent_config['db_uri']
        pg = agent_config.get('postgresql_config', {})
        required = ['username', 'password', 'host', 'port', 'database']
        if not all(k in pg and pg[k] for k in required):
            raise Exception("Configuração PostgreSQL incompleta. Forneça username, password, host, port, database.")
        return f"postgresql://{pg['username']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"
    elif connection_type == 'clickhouse':
        # Usa config explícita ou string db_uri, se existir
        if agent_config.get('db_uri'):
            return agent_config['db_uri']
        ch = agent_config.get('clickhouse_config', {})
        required = ['host']
        if not all(k in ch and ch[k] for k in required):
            raise Exception("Configuração ClickHouse incompleta. Forneça pelo menos 'host'.")

        # Constrói URI do ClickHouse
        host = ch.get('host')
        port = ch.get('port', 8123)
        database = ch.get('database', 'default')
        username = ch.get('username', 'default')
        password = ch.get('password', '')
        secure = ch.get('secure', False)

        protocol = "https" if secure else "http"
        if password:
            return f"clickhouse+http://{username}:{password}@{host}:{port}/{database}?protocol={protocol}"
        else:
            return f"clickhouse+http://{username}@{host}:{port}/{database}?protocol={protocol}"
    else:
        raise Exception(f"Tipo de conexão não suportado: {connection_type}")


def _generate_cache_key(agent_config: Dict[str, Any]) -> tuple:
    tenant_id = agent_config.get('tenant_id', 'default')
    selected_model = agent_config.get('selected_model', 'gpt-4o-mini')
    connection_type = agent_config.get('connection_type', 'csv')
    db_uri_or_path = _build_db_uri_or_path(agent_config)
    # include_tables_key: '*' por padrão; se modo tabela única, usa nome da tabela
    if agent_config.get('single_table_mode') and agent_config.get('selected_table'):
        include_tables_key = agent_config['selected_table']
    else:
        include_tables_key = '*'
    # fingerprint de arquivo para SQLite para refletir mudanças após novo upload
    if connection_type == 'csv' and str(db_uri_or_path).startswith('sqlite'):
        sqlite_fp = _sqlite_fingerprint(str(db_uri_or_path))
    else:
        sqlite_fp = None
    top_k = agent_config.get('top_k', 10)
    # Flags que devem invalidar/recriar agente quando alteradas
    advanced_mode = bool(agent_config.get('advanced_mode', False))
    processing_enabled = bool(agent_config.get('processing_enabled', False))
    refinement_enabled = bool(agent_config.get('refinement_enabled', False))
    return (
        tenant_id,
        selected_model,
        connection_type,
        db_uri_or_path,
        include_tables_key,
        sqlite_fp,
        top_k,
        advanced_mode,
        processing_enabled,
        refinement_enabled,
    )


def _get_or_create_database(agent_config: Dict[str, Any]):
    """Obtém ou cria SQLDatabase usando db_uri, com cache por processo."""
    from agentgraph.utils.database import create_sql_database
    key = ("DB",) + _generate_cache_key(agent_config)
    if key in _DB_REGISTRY:
        logging.info(f"[CACHE] cache_hit DB para chave {_key_fingerprint(key)}")
        return _DB_REGISTRY[key]
    # cache miss
    db_uri = _build_db_uri_or_path(agent_config)
    logging.info(f"[DB_URI] Abrindo banco via db_uri: {db_uri}")
    # Se for SQLite local, garantir que o arquivo exista para não criar DB vazio
    if db_uri.startswith("sqlite"):
        try:
            import re, os
            m = re.match(r"sqlite:///(.+)", db_uri)
            if m:
                db_path = "/" + m.group(1)  # Adicionar barra inicial para caminho absoluto
                if not os.path.exists(db_path):
                    raise Exception(f"Arquivo SQLite não encontrado em '{db_path}'. Realize a ingestão antes de executar no worker.")
        except Exception as e:
            logging.error(f"[DB_URI] Validação SQLite falhou: {e}")
            raise
    engine = create_engine(db_uri)
    # Testar conexão rápida
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logging.error(f"[DB_URI] Falha ao conectar em {db_uri}: {e}")
        raise
    db = create_sql_database(engine)
    _DB_REGISTRY[key] = db
    logging.info(f"[CACHE] cache_miss DB; armazenado para chave {_key_fingerprint(key)}")
    return db


def _get_or_create_sql_agent(agent_config: Dict[str, Any]):
    """Obtém ou cria SQLAgentManager com cache por processo, preservando ciclo nativo."""
    from agentgraph.agents.sql_agent import SQLAgentManager
    key = ("AGENT",) + _generate_cache_key(agent_config)
    if key in _AGENT_REGISTRY:
        logging.info(f"[CACHE] cache_hit AGENT para chave {_key_fingerprint(key)}")
        return _AGENT_REGISTRY[key]
    # cache miss: cria DB (via cache) e agente
    db = _get_or_create_database(agent_config)
    single_table_mode = agent_config.get('single_table_mode', False)
    selected_table = agent_config.get('selected_table')
    selected_model = agent_config.get('selected_model', 'gpt-4o-mini')
    top_k = agent_config.get('top_k', 10)

    logging.info(f"[AGENT_CREATE] 📊 Criando agente com TOP_K: {top_k}")
    logging.info(f"[AGENT_CREATE] 🔧 Parâmetros: model={selected_model}, single_table={single_table_mode}, table={selected_table}")

    agent = SQLAgentManager(
        db=db,
        model_name=selected_model,
        single_table_mode=single_table_mode,
        selected_table=selected_table,
        top_k=top_k
    )

    logging.info(f"[AGENT_CREATE] ✅ Agente criado com TOP_K: {agent.top_k}")
    _AGENT_REGISTRY[key] = agent
    logging.info(f"[CACHE] cache_miss AGENT; agente criado e armazenado para chave {_key_fingerprint(key)}")
    return agent

@celery_app.task(bind=True, name='process_sql_query')
def process_sql_query_task(self, agent_id: str, user_input: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Task principal para processar queries SQL

    Args:
        agent_id: ID do agente para carregar configurações do Redis
        user_input: Pergunta do usuário

    Returns:
        Dicionário com resultado da execução
    """
    start_time = time.time()

    try:
        logging.info(f"[CELERY_TASK] ===== INICIANDO TASK =====")
        logging.info(f"[CELERY_TASK] Task ID: {self.request.id}")
        logging.info(f"[CELERY_TASK] Agent ID: {agent_id}")
        logging.info(f"[CELERY_TASK] User input: {user_input[:100]}...")
        logging.info(f"[CELERY_TASK] Timestamp: {time.time()}")

        # Atualiza status inicial
        logging.info(f"[CELERY_TASK] Atualizando estado inicial...")
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Carregando configurações do agente...',
                'progress': 10,
                'agent_id': agent_id
            }
        )
        logging.info(f"[CELERY_TASK] Estado inicial atualizado")

        # 0. Metadados de execução (opcional)
        run_id = None
        user_id_meta = None
        chat_session_id = None
        if meta and isinstance(meta, dict):
            run_id = meta.get('run_id')
            user_id_meta = meta.get('user_id')
            chat_session_id = meta.get('chat_session_id')
        # Fallback: se user_id/chat_session_id não vierem no meta, resolve via runs
        def _resolve_context_from_run(_run_id: Optional[int]):
            if not _run_id:
                return None, None
            try:
                import os
                from sqlalchemy import create_engine, text
                # Prioriza DATABASE_URL; se não houver, monta via PG_*
                database_url = os.getenv("DATABASE_URL")
                if not database_url or not database_url.startswith("postgresql"):
                    host = os.getenv("PG_HOST", "postgres")
                    port = os.getenv("PG_PORT", "5432")
                    db = os.getenv("PG_DB", "agentgraph")
                    user = os.getenv("PG_USER", "agent")
                    password = os.getenv("PG_PASSWORD", "agent")
                    database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
                engine = create_engine(database_url, pool_pre_ping=True)
                with engine.connect() as conn:
                    row = conn.execute(text(
                        "SELECT user_id, chat_session_id FROM runs WHERE id = :rid"
                    ), {"rid": _run_id}).fetchone()
                    if row:
                        return row[0], row[1]
                return None, None
            except Exception as e:
                logging.warning(f"[CELERY_TASK] Fallback via run_id falhou: {e}")
                return None, None

        if (not user_id_meta or not chat_session_id) and run_id:
            logging.info("[CELERY_TASK] ⚠️ user_id/chat_session_id ausentes no meta; resolvendo via run_id...")
            uid_fallback, cs_fallback = _resolve_context_from_run(run_id)
            if not user_id_meta and uid_fallback:
                user_id_meta = uid_fallback
            if not chat_session_id and cs_fallback:
                chat_session_id = cs_fallback
            logging.info(f"[CELERY_TASK] Contexto resolvido: user_id={user_id_meta}, chat_session_id={chat_session_id}")

        # 1. Carregar configurações do Redis
        logging.info(f"[CELERY_TASK] Carregando configurações do Redis para {agent_id}...")
        agent_config = load_agent_config_from_redis(agent_id)
        if not agent_config:
            logging.error(f"[CELERY_TASK] ❌ Configuração não encontrada no Redis!")
            raise Exception(f"Configuração do agente {agent_id} não encontrada no Redis")

        logging.info(f"[CELERY_TASK] ✅ Configurações carregadas com sucesso")

        logging.info(f"[CELERY_TASK] Configuração carregada: {agent_config['connection_type']}")

        # Atualiza status
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Preparando agente SQL (cache)...',
                'progress': 30,
                'connection_type': agent_config['connection_type']
            }
        )

        # 2. REMOVIDO: Não criar SQL Agent aqui, será criado no LangGraph
        # sql_agent = _get_or_create_sql_agent(agent_config)

        # Atualiza status
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Executando query SQL...',
                'progress': 60,
                'model': agent_config.get('selected_model', 'gpt-4o-mini')
            }
        )

        # 3. SEMPRE usar LangGraph (com todos os nós)
        # chat_session_id e user_id_meta já foram resolvidos acima (meta ou fallback)

        logging.info(f"[CELERY_TASK] 🚀 Usando LangGraph completo (todos os nós)")
        if chat_session_id:
            logging.info(f"[CELERY_TASK] 💬 Com histórico - Chat Session: {chat_session_id}")
        else:
            logging.info(f"[CELERY_TASK] 📝 Sem histórico (nova conversa)")

        result = execute_langgraph_pipeline(user_input, agent_config, chat_session_id, user_id_meta, run_id)

        # Atualiza status
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Finalizando processamento...',
                'progress': 90
            }
        )

        execution_time = time.time() - start_time

        # 4. CAPTURAR HISTÓRICO NO FINAL (com todos os dados disponíveis)
        if chat_session_id and user_id_meta and run_id:
            sql_query_to_save = result.get('sql_query')
            logging.info(f"[CELERY_TASK] 💾 Capturando histórico no final da task...")
            logging.info(f"[CELERY_TASK] 📊 SQL Query para salvar: {sql_query_to_save[:100] if sql_query_to_save else 'None'}...")
            try:
                _capture_history_final_sync(
                    user_id=user_id_meta,
                    agent_id=int(agent_id),
                    chat_session_id=chat_session_id,
                    user_input=user_input,
                    response=result.get('output', ''),
                    sql_query=sql_query_to_save,
                    run_id=run_id
                )
                logging.info(f"[CELERY_TASK] ✅ Histórico capturado com sucesso!")
            except Exception as e:
                logging.error(f"[CELERY_TASK] ❌ Erro ao capturar histórico: {e}")

        # 5. Preparar resultado final
        final_result = {
            'status': 'success',
            'sql_query': result.get('sql_query'),
            'response': result.get('output', ''),
            'execution_time': execution_time,
            'agent_id': agent_id,
            'connection_type': agent_config['connection_type'],
            'model_used': agent_config.get('selected_model', 'gpt-4o-mini'),
            'intermediate_steps': result.get('intermediate_steps', []),
            'run_id': run_id,
            'user_id': user_id_meta,
        }

        logging.info(f"[CELERY_TASK] Concluido em {execution_time:.2f}s | {agent_config.get('selected_model', 'gpt-4o-mini')}")
        if result.get('sql_query'):
            sql_query_str = str(result.get('sql_query'))
            logging.info(f"[CELERY_TASK] SQL: {sql_query_str[:80]}...")

        # Atualiza tabela runs se meta.run_id estiver presente
        try:
            if run_id:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                import os
                pg_host = os.getenv("PG_HOST", "localhost")
                pg_port = os.getenv("PG_PORT", "5432")
                pg_db = os.getenv("PG_DB", "agentgraph")
                pg_user = os.getenv("PG_USER", "agent")
                pg_password = os.getenv("PG_PASSWORD", "agent")
                db_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
                engine = create_engine(db_url)
                SessionLocal = sessionmaker(bind=engine)
                session = SessionLocal()
                try:
                    from sqlalchemy import text
                    session.execute(
                        text("""
                        UPDATE runs
                        SET status = 'success',
                            execution_ms = :ms,
                            sql_used = :sql,
                            result_data = :response,
                            result_rows_count = :rows,
                            finished_at = NOW()
                        WHERE id = :run_id
                        """),
                        {
                            "ms": int(execution_time * 1000),
                            "sql": result.get('sql_query'),
                            "response": result.get('output', ''),
                            "rows": result.get('rows_count'),
                            "run_id": int(run_id),
                        },
                    )
                    session.commit()
                finally:
                    session.close()
        except Exception as e:
            logging.error(f"[CELERY_TASK] Falha ao atualizar run_id={run_id}: {e}")

        return final_result

    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Erro no processamento SQL: {str(e)}"

        logging.error(f"[CELERY_TASK] {error_msg}")
        logging.error(f"[CELERY_TASK] Exception type: {type(e).__name__}")
        logging.error(f"[CELERY_TASK] Exception args: {e.args}")

        # Atualiza estado com mensagem de erro (sem usar estado FAILURE manualmente)
        # Deixe o Celery marcar como FAILURE automaticamente ao lançar a exceção
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Erro no processamento',
                'error': error_msg,
                'execution_time': execution_time,
                'agent_id': agent_id,
                'exception_type': type(e).__name__,
                'run_id': run_id,
                'user_id': user_id_meta,
            }
        )

        # Atualiza tabela runs em caso de erro
        try:
            if run_id:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                import os
                pg_host = os.getenv("PG_HOST", "localhost")
                pg_port = os.getenv("PG_PORT", "5432")
                pg_db = os.getenv("PG_DB", "agentgraph")
                pg_user = os.getenv("PG_USER", "agent")
                pg_password = os.getenv("PG_PASSWORD", "agent")
                db_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
                engine = create_engine(db_url)
                SessionLocal = sessionmaker(bind=engine)
                session = SessionLocal()
                try:
                    from sqlalchemy import text
                    session.execute(
                        text("""
                        UPDATE runs
                        SET status = 'failure',
                            execution_ms = :ms,
                            error_type = :err,
                            finished_at = NOW()
                        WHERE id = :run_id
                        """),
                        {
                            "ms": int(execution_time * 1000),
                            "err": type(e).__name__,
                            "run_id": int(run_id),
                        },
                    )
                    session.commit()
                finally:
                    session.close()
        except Exception as e2:
            logging.error(f"[CELERY_TASK] Falha ao atualizar run_id={run_id} em erro: {e2}")

        # Levanta a exceção corretamente para o Celery
        raise Exception(error_msg) from e

def load_agent_config_from_redis(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Carrega configuração do agente do Redis

    Args:
        agent_id: ID do agente

    Returns:
        Dicionário com configurações ou None se não encontrado
    """
    import redis
    from agentgraph.utils.config import REDIS_HOST, REDIS_PORT

    try:
        # Log informações de ambiente para debug
        env_info = get_environment_info()
        logging.info(f"[REDIS] Worker ambiente: {env_info['environment']}")
        logging.info(f"[REDIS] Conectando ao Redis para carregar {agent_id}...")
        logging.info(f"[REDIS] Host: {REDIS_HOST}, Port: {REDIS_PORT}")

        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

        # Testa conexão
        redis_client.ping()
        logging.info(f"[REDIS] Conexão com Redis estabelecida")

        # Busca configuração no Redis
        config_key = f"agent_config:{agent_id}"
        logging.info(f"[REDIS] Buscando chave: {config_key}")
        config_data = redis_client.get(config_key)

        if not config_data:
            logging.error(f"[REDIS] ❌ Configuração não encontrada para agent_id: {agent_id}")
            logging.error(f"[REDIS] Chave buscada: {config_key}")
            return None

        # Deserializa configuração
        logging.info(f"[REDIS] Dados encontrados, deserializando...")
        agent_config = json.loads(config_data)
        logging.info(f"[REDIS] ✅ Configuração carregada para {agent_id}: {list(agent_config.keys())}")

        return agent_config

    except Exception as e:
        logging.error(f"[REDIS] Erro ao carregar configuração: {e}")
        return None

def save_agent_config_to_redis(agent_id: str, config: Dict[str, Any]) -> bool:
    """
    Salva configuração do agente no Redis

    Args:
        agent_id: ID do agente
        config: Configurações a serem salvas

    Returns:
        True se salvou com sucesso, False caso contrário
    """
    import redis
    from agentgraph.utils.config import REDIS_HOST, REDIS_PORT

    try:
        # Log informações de ambiente para debug
        env_info = get_environment_info()
        logging.info(f"[REDIS] Worker ambiente: {env_info['environment']}")
        logging.info(f"[REDIS] Salvando configuração para {agent_id}...")
        logging.info(f"[REDIS] Host: {REDIS_HOST}, Port: {REDIS_PORT}")

        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

        # Serializa e salva configuração
        config_key = f"agent_config:{agent_id}"
        config_data = json.dumps(config, default=str)

        redis_client.set(config_key, config_data)
        logging.info(f"[REDIS] Configuração salva para {agent_id}")

        return True

    except Exception as e:
        logging.error(f"[REDIS] Erro ao salvar configuração: {e}")
        return False

# OBSOLETO: reconstrução por task foi substituída por cache por processo (_get_or_create_sql_agent)
# Mantido por compatibilidade mas não utilizado no fluxo principal.
def reconstruct_sql_agent(agent_config: Dict[str, Any]):
    logging.warning("[RECONSTRUCT] Função obsoleta chamada. Utilize o cache por processo.")
    return _get_or_create_sql_agent(agent_config)

# OBSOLETO: leitura de CSV no worker não é mais suportada. Utilize db_uri persistido.
def create_engine_from_csv(csv_path: str):
    """
    [OBSOLETO] Cria engine SQLite a partir de arquivo CSV. Não utilizar no worker.
    """
    raise RuntimeError("Leitura de CSV no worker desabilitada. Realize a ingestão (CSV->SQLite) no app e passe db_uri.")

def create_engine_from_postgresql(pg_config: Dict[str, Any]):
    """
    Cria engine PostgreSQL

    Args:
        pg_config: Configurações do PostgreSQL

    Returns:
        Engine SQLAlchemy
    """
    try:
        # Monta URL de conexão
        connection_url = (
            f"postgresql://{pg_config['username']}:{pg_config['password']}"
            f"@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
        )

        # Cria engine
        engine = create_engine(connection_url)

        # Testa conexão com text() para SQLAlchemy 2.0+
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        logging.info(f"[PG_ENGINE] Engine PostgreSQL criada com sucesso")
        return engine

    except Exception as e:
        logging.error(f"[PG_ENGINE] Erro ao criar engine: {e}")
        raise

def execute_langgraph_pipeline(user_input: str, agent_config: Dict[str, Any], chat_session_id: Optional[int], user_id: int, run_id: Optional[int] = None, api_agent_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Executa o pipeline usando LangGraph completo (todos os nós)

    Args:
        user_input: Pergunta do usuário
        agent_config: Configurações do agente
        chat_session_id: ID da sessão de chat para histórico (opcional)
        user_id: ID do usuário
        run_id: ID da run (opcional)

    Returns:
        Resultado da execução
    """
    import asyncio

    try:
        logging.info(f"[LANGGRAPH_PIPELINE] Executando LangGraph completo: {user_input[:80]}...")
        if chat_session_id:
            logging.info(f"[LANGGRAPH_PIPELINE] Com histórico - Chat Session: {chat_session_id}, User: {user_id}")
        else:
            logging.info(f"[LANGGRAPH_PIPELINE] Sem histórico - User: {user_id}")

        # IMPORTANTE: Criar engine e database ANTES do LangGraph (como no Gradio)
        logging.info(f"[LANGGRAPH_PIPELINE] Criando engine e database para db_uri: {agent_config.get('db_uri', 'N/A')}")

        # Criar engine e database usando o mesmo sistema do Gradio
        from agentgraph.utils.object_manager import get_object_manager
        from agentgraph.utils.database import create_sql_database
        from sqlalchemy import create_engine

        obj_manager = get_object_manager()

        # Criar engine
        db_uri = agent_config.get('db_uri')
        if not db_uri:
            raise Exception("db_uri não encontrado na configuração do agente")

        engine = create_engine(db_uri)
        engine_id = obj_manager.store_engine(engine)
        logging.info(f"[LANGGRAPH_PIPELINE] Engine criado e armazenado: {engine_id}")

        # Criar database
        database = create_sql_database(engine)
        db_id = obj_manager.store_database(database)
        logging.info(f"[LANGGRAPH_PIPELINE] Database criado e armazenado: {db_id}")

        # Importar LangGraph
        from agentgraph.graphs.main_graph import AgentGraphManager

        # Criar instância do LangGraph com objetos externos
        main_graph = AgentGraphManager(external_engine_id=engine_id, external_db_id=db_id)


        # Preparar parâmetros para process_query (apenas os aceitos)
        thread_id = f"chat_{chat_session_id}" if chat_session_id else f"user_{user_id}"

        process_query_params = {
            "user_input": user_input,
            "selected_model": agent_config.get('selected_model', 'gpt-4o-mini'),
            "advanced_mode": agent_config.get('advanced_mode', False),
            "processing_enabled": agent_config.get('processing_enabled', False),
            "question_refinement_enabled": agent_config.get('refinement_enabled', False),
            "connection_type": agent_config.get('connection_type', 'csv'),
            "selected_table": agent_config.get('selected_table'),
            "single_table_mode": agent_config.get('single_table_mode', False),
            "top_k": agent_config.get('top_k', 10),
            "use_celery": False,  # Já estamos no Celery
            "thread_id": thread_id,
            "engine_id": engine_id,  # NOVO: IDs dos objetos criados
            "db_id": db_id  # NOVO: IDs dos objetos criados
        }

        # Executar LangGraph de forma assíncrona
        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        try:
            # Adicionar user_id, chat_session_id e run_id aos parâmetros
            process_query_params["user_id"] = user_id
            if chat_session_id:
                process_query_params["chat_session_id"] = chat_session_id
            if run_id:
                process_query_params["run_id"] = run_id

            # Executar LangGraph com todos os parâmetros
            # IMPORTANTE: No worker (já estamos dentro do Celery), SEMPRE use_celery=False
            # para evitar "duplo Celery". A API é a única responsável por disparar a task.
            if "use_celery" in process_query_params:
                process_query_params["use_celery"] = False
            result = loop.run_until_complete(main_graph.process_query(**process_query_params))

        finally:
            loop.close()

        if result.get('error'):
            logging.error(f"[LANGGRAPH_PIPELINE] Erro: {result['error']}")
            return {
                'output': f"Erro: {result['error']}",
                'sql_query': None,
                'intermediate_steps': [],
                'success': False
            }
        else:
            logging.info(f"[LANGGRAPH_PIPELINE] Execução bem-sucedida (LangGraph completo)")

            # IMPORTANTE: O LangGraph retorna 'sql_query_extracted', não 'sql_query'
            sql_query = result.get('sql_query_extracted') or result.get('sql_query')

            if sql_query:
                logging.info(f"[LANGGRAPH_PIPELINE] ✅ SQL Query capturada: {sql_query[:100]}...")
            else:
                logging.warning(f"[LANGGRAPH_PIPELINE] ⚠️ Nenhuma SQL query encontrada no resultado")

            return {
                'output': result.get('response', ''),
                'sql_query': sql_query,
                'intermediate_steps': result.get('intermediate_steps', []),
                'success': True
            }

    except Exception as e:
        error_msg = f"Erro no pipeline LangGraph: {str(e)}"
        logging.error(f"[LANGGRAPH_PIPELINE] {error_msg}")
        return {
            'output': error_msg,
            'sql_query': None,
            'intermediate_steps': [],
            'success': False
        }


def execute_sql_pipeline(sql_agent, user_input: str, agent_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executa o pipeline do AgentSQL

    Args:
        sql_agent: Instância do SQLAgentManager
        user_input: Pergunta do usuário
        agent_config: Configurações do agente

    Returns:
        Resultado da execução
    """
    import asyncio

    try:
        logging.info(f"[SQL_PIPELINE] Executando: {user_input[:80]}...")

        # Log apenas se houver contexto
        sql_context = agent_config.get('sql_context', '')
        if sql_context:
            logging.info(f"[SQL_PIPELINE] Usando contexto SQL: {len(str(sql_context))} chars")

        # Executa query de forma assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Preparar instrução com contexto
            instruction = user_input

            # Adicionar contexto SQL se disponível
            sql_context = agent_config.get('sql_context', '')
            if sql_context:
                instruction = f"{sql_context}\n\nPergunta do usuário: {user_input}"

            # Adicionar query sugerida se disponível
            suggested_query = agent_config.get('suggested_query', '')
            if suggested_query:
                instruction += f"\n\nQuery sugerida: {suggested_query}"

            # Adicionar observações se disponíveis
            query_observations = agent_config.get('query_observations', '')
            if query_observations:
                instruction += f"\n\nObservações: {query_observations}"

            # Executar query
            result = loop.run_until_complete(sql_agent.execute_query(instruction))
        finally:
            loop.close()

        if result['success']:
            logging.info(f"[SQL_PIPELINE] Execução bem-sucedida")
            # Tentar contar linhas quando possível (heurística - não crítico)
            rows_count = None
            try:
                # output pode conter dados textuais; se houver df no futuro, ajustar aqui
                pass
            except Exception:
                pass
            return {
                'output': result['output'],
                'sql_query': result.get('sql_query'),
                'intermediate_steps': result.get('intermediate_steps', []),
                'rows_count': rows_count,
                'success': True
            }
        else:
            logging.error(f"[SQL_PIPELINE] Execução falhou: {result.get('output', 'Erro desconhecido')}")
            return {
                'output': result.get('output', 'Erro na execução SQL'),
                'sql_query': None,
                'intermediate_steps': [],
                'success': False
            }

    except Exception as e:
        error_msg = f"Erro no pipeline SQL: {str(e)}"
        logging.error(f"[SQL_PIPELINE] {error_msg}")
        return {
            'output': error_msg,
            'sql_query': None,
            'intermediate_steps': [],
            'success': False
        }

# Função auxiliar para obter status de task
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Obtém status de uma task do Celery

    Args:
        task_id: ID da task

    Returns:
        Dicionário com status da task
    """
    from celery.result import AsyncResult

    try:
        task_result = AsyncResult(task_id, app=celery_app)

        if task_result.state == 'PENDING':
            return {
                'state': 'PENDING',
                'status': 'Aguardando processamento...',
                'progress': 0,
                'task_id': task_id
            }
        elif task_result.state == 'PROCESSING':
            meta = task_result.info or {}
            return {
                'state': 'PROCESSING',
                'status': meta.get('status', 'Processando...'),
                'progress': meta.get('progress', 50),
                'task_id': task_id,
                **meta
            }
        elif task_result.state == 'SUCCESS':
            return {
                'state': 'SUCCESS',
                'result': task_result.result,
                'status': 'Concluído com sucesso',
                'progress': 100,
                'task_id': task_id
            }
        elif task_result.state == 'FAILURE':
            return {
                'state': 'FAILURE',
                'error': str(task_result.info),
                'status': 'Erro no processamento',
                'progress': 0,
                'task_id': task_id
            }
        else:
            return {
                'state': task_result.state,
                'status': f'Estado desconhecido: {task_result.state}',
                'progress': 0,
                'task_id': task_id
            }

    except Exception as e:
        return {
            'state': 'ERROR',
            'error': str(e),
            'status': 'Erro ao consultar status',
            'progress': 0,
            'task_id': task_id
        }


# ==========================================
# TASKS DE HISTÓRICO E EMBEDDINGS
# ==========================================

@celery_app.task(bind=True, max_retries=3)
def generate_message_embedding_task(self, message_content: str, chat_session_id: int, role: str = "user"):
    """
    Task para gerar embedding de uma mensagem e salvar no banco

    Args:
        message_content: Conteúdo da mensagem
        chat_session_id: ID da sessão de chat
        role: Papel da mensagem (user/assistant)
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[EMBEDDING_TASK] Iniciando geração de embedding para sessão {chat_session_id}")
        logger.info(f"[EMBEDDING_TASK] Conteúdo: '{message_content[:100]}...'")

        # Importa serviços necessários
        from agentgraph.services.embedding_service import get_embedding_service
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # Conecta ao banco usando as mesmas configurações da API
        import os
        host = os.getenv("PG_HOST", "postgres")
        port = os.getenv("PG_PORT", "5432")
        db = os.getenv("PG_DB", "agentgraph")
        user = os.getenv("PG_USER", "agent")
        password = os.getenv("PG_PASSWORD", "agent")

        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        engine = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db_session = Session()

        try:
            # Busca a mensagem mais recente da sessão com o conteúdo
            result = db_session.execute(text("""
                SELECT id FROM messages
                WHERE chat_session_id = :session_id
                AND content = :content
                AND role = :role
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                "session_id": chat_session_id,
                "content": message_content,
                "role": role
            })

            message_row = result.fetchone()
            if not message_row:
                logger.warning(f"[EMBEDDING_TASK] Mensagem não encontrada para sessão {chat_session_id}")
                return {"status": "error", "error": "Mensagem não encontrada"}

            message_id = message_row[0]
            logger.info(f"[EMBEDDING_TASK] Mensagem encontrada: ID {message_id}")

            # Verifica se embedding já existe
            existing = db_session.execute(text("""
                SELECT id FROM message_embeddings
                WHERE message_id = :message_id
            """), {"message_id": message_id}).fetchone()

            if existing:
                logger.info(f"[EMBEDDING_TASK] Embedding já existe para mensagem {message_id}")
                return {"status": "skipped", "message": "Embedding já existe"}

            # Gera embedding
            embedding_service = get_embedding_service()
            embedding = embedding_service.get_embedding(message_content)

            logger.info(f"[EMBEDDING_TASK] Embedding gerado: {len(embedding)} dimensões")

            # Salva embedding no banco
            db_session.execute(text("""
                INSERT INTO message_embeddings (message_id, embedding, model_version, created_at)
                VALUES (:message_id, :embedding, :model_version, NOW())
            """), {
                "message_id": message_id,
                "embedding": str(embedding),
                "model_version": embedding_service.model
            })

            db_session.commit()
            logger.info(f"[EMBEDDING_TASK] ✅ Embedding salvo para mensagem {message_id}")

            return {
                "status": "success",
                "message_id": message_id,
                "embedding_dimensions": len(embedding)
            }

        except Exception as e:
            logger.error(f"[EMBEDDING_TASK] Erro ao processar embedding: {e}")
            return {"status": "error", "error": str(e)}

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"[EMBEDDING_TASK] Erro geral: {e}")
        return {"status": "error", "error": str(e)}


def _capture_history_final_sync(user_id: int, agent_id: int, chat_session_id: int,
                                user_input: str, response: str, sql_query: str = None, run_id: int = None):
    """
    Captura o histórico no final da task com todos os dados disponíveis (versão síncrona)
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[HISTORY_FINAL] Capturando histórico: user_id={user_id}, agent_id={agent_id}, chat_session_id={chat_session_id}")

        # Importar serviços necessários
        from agentgraph.services.history_service import HistoryService
        from agentgraph.nodes.history_capture_node import _save_conversation_to_history_sync

        # Criar serviço de histórico
        history_service = HistoryService()

        # Usar a função existente do nó de histórico
        success = _save_conversation_to_history_sync(
            history_service=history_service,
            chat_session_id=chat_session_id,
            user_input=user_input,
            response=response,
            sql_query=sql_query,
            run_id=run_id
        )

        if success:
            logger.info(f"[HISTORY_FINAL] ✅ Conversa salva com sucesso!")

            # Disparar geração de embeddings
            try:
                logger.info(f"[HISTORY_FINAL] 🧠 Disparando geração de embeddings...")

                # Dispara task para mensagem do usuário
                generate_message_embedding_task.delay(user_input, chat_session_id, "user")
                logger.info(f"[HISTORY_FINAL] ✅ Task de embedding disparada para mensagem do usuário")

                # Dispara task para resposta do assistente
                generate_message_embedding_task.delay(response, chat_session_id, "assistant")
                logger.info(f"[HISTORY_FINAL] ✅ Task de embedding disparada para resposta do assistente")

            except Exception as e:
                logger.error(f"[HISTORY_FINAL] ❌ Erro ao disparar embeddings: {e}")
        else:
            logger.error(f"[HISTORY_FINAL] ❌ Erro ao salvar conversa")

        # Cleanup
        history_service.close()

        return True

    except Exception as e:
        logger.error(f"[HISTORY_FINAL] ❌ Erro ao capturar histórico: {e}")
        return False

    except Exception as e:
        error_msg = f"Erro ao gerar embedding: {e}"
        logger.error(f"[EMBEDDING_TASK] ❌ {error_msg}")

        # Retry com backoff exponencial
        try:
            raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"[EMBEDDING_TASK] Máximo de tentativas excedido para sessão {chat_session_id}")
            return {"status": "failed", "error": error_msg}
