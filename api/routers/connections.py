from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import List
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import AgentConnection, Dataset
from ..schemas import ConnectionCreate, ConnectionUpdate, ConnectionOut

router = APIRouter()

def test_connection(connection_string: str) -> tuple[bool, str]:
    """
    Testa se uma conexão é válida
    Retorna (sucesso, mensagem)
    """
    try:
        # Criar engine temporário para testar
        engine = create_engine(connection_string, pool_pre_ping=True)

        # Tentar conectar
        with engine.connect() as conn:
            # Executar uma query simples para verificar se funciona
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        # Fechar engine
        engine.dispose()

        return True, "Conexão testada com sucesso"

    except Exception as e:
        error_msg = str(e)

        # Mensagens de erro mais amigáveis
        if "Connection refused" in error_msg:
            return False, "Conexão recusada. Verifique se o PostgreSQL está rodando e acessível no host/porta especificados."
        elif "authentication failed" in error_msg:
            return False, "Falha na autenticação. Verifique o usuário e senha."
        elif "database" in error_msg and "does not exist" in error_msg:
            return False, "Banco de dados não encontrado. Verifique o nome do banco."
        elif "could not translate host name" in error_msg:
            return False, "Host não encontrado. Verifique o endereço do servidor."
        elif "timeout" in error_msg:
            return False, "Timeout na conexão. Verifique a conectividade de rede."
        else:
            return False, f"Erro na conexão: {error_msg}"

@router.post("/", response_model=ConnectionOut)
def create_connection(payload: ConnectionCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.tipo.lower() in ("sqlite", "duckdb"):
        if not payload.dataset_id:
            raise HTTPException(status_code=400, detail="dataset_id é obrigatório para conexões baseadas em arquivo")
        ds = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
        if not ds or not ds.db_uri:
            raise HTTPException(status_code=400, detail="Dataset inválido ou sem db_uri")
        conn = AgentConnection(owner_user_id=user.id, tipo=payload.tipo.lower(), db_uri=ds.db_uri)
    elif payload.tipo.lower() == "postgres":
        if not payload.pg_dsn:
            raise HTTPException(status_code=400, detail="pg_dsn é obrigatório para tipo postgres")

        # Testar a conexão antes de criar
        is_valid, error_message = test_connection(payload.pg_dsn)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn = AgentConnection(owner_user_id=user.id, tipo="postgres", pg_dsn=payload.pg_dsn)
    else:
        raise HTTPException(status_code=400, detail="tipo inválido: use sqlite/duckdb/postgres")

    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn

@router.get("/", response_model=List[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(AgentConnection).filter(AgentConnection.owner_user_id == user.id).order_by(AgentConnection.created_at.desc()).all()

@router.get("/{connection_id}", response_model=ConnectionOut)
def get_connection(connection_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Obter uma conexão específica por ID"""
    conn = db.query(AgentConnection).filter(
        AgentConnection.id == connection_id,
        AgentConnection.owner_user_id == user.id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="Conexão não encontrada")

    return conn

@router.post("/test")
def test_connection_endpoint(payload: ConnectionCreate, user=Depends(get_current_user)):
    """Testar uma conexão sem criar no banco"""
    if payload.tipo.lower() == "postgres":
        if not payload.pg_dsn:
            raise HTTPException(status_code=400, detail="pg_dsn é obrigatório para tipo postgres")

        is_valid, message = test_connection(payload.pg_dsn)
        return {
            "valid": is_valid,
            "message": message,
            "tipo": "postgres"
        }
    else:
        raise HTTPException(status_code=400, detail="Teste de conexão disponível apenas para PostgreSQL")

@router.patch("/{connection_id}", response_model=ConnectionOut)
def update_connection(connection_id: int, payload: ConnectionUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Atualizar uma conexão existente"""
    conn = db.query(AgentConnection).filter(
        AgentConnection.id == connection_id,
        AgentConnection.owner_user_id == user.id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="Conexão não encontrada")

    # Atualizar apenas campos fornecidos
    if payload.pg_dsn is not None:
        if conn.tipo != "postgres":
            raise HTTPException(status_code=400, detail="pg_dsn só pode ser atualizado para conexões PostgreSQL")

        # Testar a nova conexão antes de atualizar
        is_valid, error_message = test_connection(payload.pg_dsn)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn.pg_dsn = payload.pg_dsn

    db.commit()
    db.refresh(conn)
    return conn

@router.delete("/{connection_id}")
def delete_connection(connection_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from ..models import Agent, Run
    from sqlalchemy import text

    conn = db.query(AgentConnection).filter(AgentConnection.id == connection_id, AgentConnection.owner_user_id == user.id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Conexão não encontrada")

    # Verificar se há agentes usando esta conexão
    agents_using_connection = db.query(Agent).filter(Agent.connection_id == connection_id).all()

    if agents_using_connection:
        # Primeiro, deletar todos os embeddings das messages relacionadas aos agentes desta conexão
        for agent in agents_using_connection:
            db.execute(text("""
                DELETE FROM message_embeddings
                WHERE message_id IN (
                    SELECT m.id FROM messages m
                    JOIN runs r ON m.run_id = r.id
                    WHERE r.agent_id = :agent_id
                )
            """), {"agent_id": agent.id})

        # Segundo, deletar todas as messages relacionadas às runs dos agentes desta conexão
        for agent in agents_using_connection:
            db.execute(text("""
                DELETE FROM messages
                WHERE run_id IN (
                    SELECT id FROM runs WHERE agent_id = :agent_id
                )
            """), {"agent_id": agent.id})

        # Terceiro, deletar todas as runs dos agentes que usam esta conexão
        for agent in agents_using_connection:
            db.query(Run).filter(Run.agent_id == agent.id).delete()

        # Quarto, deletar todas as chat_sessions dos agentes que usam esta conexão
        for agent in agents_using_connection:
            db.execute(text("""
                DELETE FROM chat_sessions
                WHERE agent_id = :agent_id
            """), {"agent_id": agent.id})

        # Quinto, deletar todos os agentes que usam esta conexão
        db.query(Agent).filter(Agent.connection_id == connection_id).delete()

    # Finalmente deletar a conexão
    db.delete(conn)
    db.commit()
    return {"deleted": True}

