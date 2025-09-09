from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Agent, AgentConnection
from ..schemas import AgentCreate, AgentUpdate, AgentOut

router = APIRouter()

@router.post("/", response_model=AgentOut)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Verifica se a conexão existe
    conn = db.query(AgentConnection).filter(AgentConnection.id == payload.connection_id).first()
    if not conn:
        raise HTTPException(status_code=400, detail="Conexão informada não existe")

    ag = Agent(
        owner_user_id=user.id,
        nome=payload.nome,
        connection_id=payload.connection_id,
        selected_model=payload.selected_model,
        top_k=payload.top_k,
        include_tables_key=payload.include_tables_key,
        advanced_mode=payload.advanced_mode,
        processing_enabled=payload.processing_enabled,
        refinement_enabled=payload.refinement_enabled,
        single_table_mode=payload.single_table_mode,
        selected_table=payload.selected_table,
    )
    db.add(ag)
    db.commit()
    db.refresh(ag)
    return ag

@router.get("/", response_model=List[AgentOut])
def list_agents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Agent).filter(Agent.owner_user_id == user.id).order_by(Agent.created_at.desc()).all()

@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ag = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    # Carregar a conexão relacionada
    connection = db.query(AgentConnection).filter(AgentConnection.id == ag.connection_id).first()

    # Criar resposta com conexão incluída
    agent_dict = {
        "id": ag.id,
        "owner_user_id": ag.owner_user_id,
        "nome": ag.nome,
        "connection_id": ag.connection_id,
        "selected_model": ag.selected_model,
        "top_k": ag.top_k,
        "include_tables_key": ag.include_tables_key,
        "advanced_mode": ag.advanced_mode,
        "processing_enabled": ag.processing_enabled,
        "refinement_enabled": ag.refinement_enabled,
        "single_table_mode": ag.single_table_mode,
        "selected_table": ag.selected_table,
        "version": ag.version,
        "created_at": ag.created_at,
        "updated_at": ag.updated_at,
        "connection": {
            "id": connection.id,
            "owner_user_id": connection.owner_user_id,
            "tipo": connection.tipo,
            "db_uri": connection.db_uri,
            "pg_dsn": connection.pg_dsn,
            "created_at": connection.created_at
        } if connection else None
    }

    return agent_dict

@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: int, payload: AgentUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ag = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    changed = False
    if payload.selected_model is not None:
        ag.selected_model = payload.selected_model
        changed = True
    if payload.top_k is not None:
        ag.top_k = payload.top_k
        changed = True
    if payload.include_tables_key is not None:
        ag.include_tables_key = payload.include_tables_key
        changed = True
    # Novos campos que impactam versão
    for field in [
        "advanced_mode",
        "processing_enabled",
        "refinement_enabled",
        "single_table_mode",
        "selected_table",
    ]:
        val = getattr(payload, field, None)
        if val is not None:
            setattr(ag, field, val)
            changed = True

    if changed:
        ag.version = ag.version + 1
    db.commit()
    db.refresh(ag)
    return ag

@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from ..models import Run
    from sqlalchemy import text

    ag = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    # Primeiro, deletar todos os embeddings das messages relacionadas às runs deste agente
    db.execute(text("""
        DELETE FROM message_embeddings
        WHERE message_id IN (
            SELECT m.id FROM messages m
            JOIN runs r ON m.run_id = r.id
            WHERE r.agent_id = :agent_id
        )
    """), {"agent_id": agent_id})

    # Segundo, deletar todas as messages relacionadas às runs deste agente
    db.execute(text("""
        DELETE FROM messages
        WHERE run_id IN (
            SELECT id FROM runs WHERE agent_id = :agent_id
        )
    """), {"agent_id": agent_id})

    # Terceiro, deletar todas as runs relacionadas
    db.query(Run).filter(Run.agent_id == agent_id).delete()

    # Quarto, deletar todas as chat_sessions relacionadas
    db.execute(text("""
        DELETE FROM chat_sessions
        WHERE agent_id = :agent_id
    """), {"agent_id": agent_id})

    # Quinto, deletar o agente
    db.delete(ag)
    db.commit()
    return {"deleted": True}

