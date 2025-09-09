from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging
import time
import json
from datetime import datetime

from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Run, Agent, AgentConnection
from ..schemas import RunCreate, RunOut
from ..services.runs import create_run
from agentgraph.tasks import save_agent_config_to_redis, process_sql_query_task, get_task_status

# Configurar logging detalhado
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter()

@router.post("/agents/{agent_id}/run", response_model=RunOut)
def run_agent(agent_id: int, payload: RunCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    start_time = time.time()
    logger.info(f"🚀 INICIANDO EXECUÇÃO - Agent ID: {agent_id}, User ID: {user.id}")
    logger.info(f"📝 Pergunta recebida: '{payload.question}'")

    # Verificar se agente existe e pertence ao usuário
    logger.info(f"🔍 Buscando agente {agent_id} para usuário {user.id}")
    ag = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
    if not ag:
        logger.error(f"❌ Agente {agent_id} não encontrado para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    logger.info(f"✅ Agente encontrado: '{ag.nome}' (Connection ID: {ag.connection_id})")

    # Gerenciar chat_session_id
    chat_session_id = payload.chat_session_id
    if not chat_session_id:
        # Criar nova sessão de chat
        logger.info(f"💬 Criando nova sessão de chat...")
        from api.models import ChatSession
        from datetime import datetime

        chat_session = ChatSession(
            user_id=user.id,
            agent_id=ag.id,
            title=f"Conversa {datetime.now().strftime('%d/%m %H:%M')}"
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        chat_session_id = chat_session.id
        logger.info(f"✅ Nova sessão criada: ID {chat_session_id}")
    else:
        logger.info(f"🔄 Usando sessão existente: ID {chat_session_id}")

    # cria run (queued) com chat_session_id
    logger.info(f"📝 Criando run no banco de dados...")
    run = create_run(db=db, agent_id=agent_id, user_id=user.id, question=payload.question, chat_session_id=chat_session_id)
    logger.info(f"✅ Run criada: ID {run.id}, Status: {run.status}, Chat Session: {chat_session_id}")

    # carrega connection
    logger.info(f"🔗 Carregando conexão ID: {ag.connection_id}")
    conn = db.query(AgentConnection).filter(AgentConnection.id == ag.connection_id).first()
    if not conn:
        logger.error(f"❌ Conexão {ag.connection_id} inválida")
        raise HTTPException(status_code=400, detail="Conexão do agente inválida")

    logger.info(f"✅ Conexão carregada: Tipo '{conn.tipo}', URI: {conn.db_uri or conn.pg_dsn}")

    # Monta agent_config para o worker (cache key do worker inclui: user/empresa, agent_id, model, tipo, db_uri/pg_dsn, include_tables_key, top_k, version)
    logger.info(f"⚙️ Montando configuração do agente...")
    tenant_id = str(ag.owner_empresa_id or ag.owner_user_id or user.id)
    agent_config = {
        "tenant_id": tenant_id,
        "agent_id": ag.id,
        "selected_model": ag.selected_model,
        "top_k": ag.top_k,
        "include_tables_key": ag.include_tables_key or "*",
        # flags e modos do agente
        "advanced_mode": bool(getattr(ag, "advanced_mode", False)),
        "processing_enabled": bool(getattr(ag, "processing_enabled", False)),
        "refinement_enabled": bool(getattr(ag, "refinement_enabled", False)),
        "single_table_mode": bool(getattr(ag, "single_table_mode", False)),
        "selected_table": getattr(ag, "selected_table", None),
        "version": ag.version,
    }
    logger.info(f"📊 Config base: Tenant {tenant_id}, Model {ag.selected_model}, Top-K {ag.top_k}")
    if conn.tipo == "postgres":
        logger.info(f"🐘 Configurando conexão PostgreSQL: {conn.pg_dsn}")
        agent_config.update({
            "connection_type": "postgresql",
            "db_uri": conn.pg_dsn,  # usa DSN diretamente
        })
    else:
        # MAPEAMENTO CORRETO: sqlite/duckdb da API → csv do LangGraph
        logger.info(f"📁 Configurando conexão {conn.tipo.upper()}: {conn.db_uri}")
        agent_config.update({
            "connection_type": "csv",  # LangGraph usa 'csv' para SQLite
            "db_uri": conn.db_uri,  # sqlite/duckdb
        })

    logger.info(f"✅ Configuração final: {json.dumps(agent_config, indent=2, default=str)}")

    # Dispara task do agente: usamos a task existente, salvando a config no Redis do módulo do agente
    logger.info(f"💾 Preparando configuração para Redis...")
    agent_cfg_to_save = {
        "tenant_id": agent_config["tenant_id"],
        "connection_type": agent_config["connection_type"],
        "selected_model": agent_config["selected_model"],
        "top_k": agent_config["top_k"],
        "include_tables_key": agent_config.get("include_tables_key", "*"),
        "version": agent_config["version"],
        # Flags do agente também vão para o Redis para participarem da cache key do worker
        "advanced_mode": agent_config.get("advanced_mode", False),
        "processing_enabled": agent_config.get("processing_enabled", False),
        "refinement_enabled": agent_config.get("refinement_enabled", False),
        "single_table_mode": agent_config.get("single_table_mode", False),
        "selected_table": agent_config.get("selected_table"),
    }
    # Para postgres, enviamos db_uri com o DSN; o worker monta a engine a partir dele
    agent_cfg_to_save["db_uri"] = agent_config["db_uri"]

    logger.info(f"💾 Salvando configuração no Redis para agent_id: {ag.id}")
    if not save_agent_config_to_redis(str(ag.id), agent_cfg_to_save):
        logger.error(f"❌ Falha ao salvar configuração no Redis para agent_id: {ag.id}")
        raise HTTPException(status_code=500, detail="Falha ao salvar configuração no Redis")

    logger.info(f"✅ Configuração salva no Redis com sucesso")

    # Dispara task Celery via assinatura direta
    logger.info(f"🚀 Disparando task Celery...")
    task_metadata = {"run_id": run.id, "user_id": user.id, "chat_session_id": chat_session_id}  # NOVO: chat_session_id
    logger.info(f"📋 Metadata da task: {task_metadata}")

    task = process_sql_query_task.delay(str(ag.id), payload.question, task_metadata)
    logger.info(f"✅ Task Celery disparada: ID {task.id}")

    # Atualiza status localmente como running e salva task_id
    logger.info(f"📝 Atualizando run no banco: Status -> running, Task ID -> {task.id}")
    run.status = "running"
    run.task_id = task.id
    db.commit()
    db.refresh(run)

    execution_time = time.time() - start_time
    logger.info(f"🎉 EXECUÇÃO INICIADA COM SUCESSO em {execution_time:.2f}s")
    logger.info(f"📊 Run ID: {run.id}, Task ID: {task.id}, Status: {run.status}")

    return run

@router.get("/agents/{agent_id}/runs", response_model=List[RunOut])
def list_agent_runs(agent_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    logger.info(f"📋 LISTANDO RUNS - Agent ID: {agent_id}, User ID: {user.id}")

    # Primeiro verifica se o agente pertence ao usuário
    ag = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
    if not ag:
        logger.error(f"❌ Agente {agent_id} não encontrado para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    runs = db.query(Run).filter(Run.agent_id == agent_id, Run.user_id == user.id).order_by(Run.created_at.desc()).all()
    logger.info(f"✅ Encontradas {len(runs)} execuções para agente {agent_id}")

    return runs

@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    logger.info(f"🔍 CONSULTANDO RUN - Run ID: {run_id}, User ID: {user.id}")

    run = db.query(Run).filter(Run.id == run_id, Run.user_id == user.id).first()
    if not run:
        logger.error(f"❌ Run {run_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Run não encontrada")

    logger.info(f"📊 Run encontrada: Status '{run.status}', Task ID: {run.task_id}")

    # Se ainda não temos finalização, consultar status dinâmico no Celery
    if run.status in ("queued", "running") and run.task_id:
        logger.info(f"⏳ Consultando status da task no Celery: {run.task_id}")
        status_info = get_task_status(run.task_id)
        state = status_info.get("state")
        logger.info(f"📡 Status Celery: {state}")

        if state == "SUCCESS":
            logger.info(f"✅ Task concluída com sucesso (worker deve ter atualizado o banco)")
        elif state == "FAILURE":
            logger.info(f"❌ Task falhou (worker deve ter atualizado o banco)")
        elif state in ["PENDING", "RETRY"]:
            logger.info(f"⏳ Task ainda em processamento: {state}")
    else:
        logger.info(f"📋 Run finalizada: Status '{run.status}'")
        if run.result_data:
            logger.info(f"💬 Resposta disponível: {len(run.result_data)} caracteres")

    return run

@router.get("/runs/", response_model=List[RunOut])
def list_user_runs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Lista todas as execuções do usuário logado"""
    logger.info(f"📋 LISTANDO TODAS AS RUNS - User ID: {user.id}")

    runs = db.query(Run).filter(Run.user_id == user.id).order_by(Run.created_at.desc()).all()
    logger.info(f"✅ Encontradas {len(runs)} execuções para usuário {user.id}")

    # Log de estatísticas
    if runs:
        status_counts = {}
        for run in runs:
            status_counts[run.status] = status_counts.get(run.status, 0) + 1
        logger.info(f"📊 Estatísticas: {status_counts}")

    return runs

