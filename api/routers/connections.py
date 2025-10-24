from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import List
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import AgentConnection, Dataset
from ..schemas import ConnectionCreate, ConnectionUpdate, ConnectionOut, PostgreSQLConfig, ClickHouseConfig

router = APIRouter()

def test_connection(connection_string: str, db_type: str = "postgres") -> tuple[bool, str]:
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
            if db_type == "clickhouse":
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0] if result else "unknown"
                message = f"Conexão ClickHouse testada com sucesso (versão: {version})"
            else:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                message = "Conexão testada com sucesso"

        # Fechar engine
        engine.dispose()

        return True, message

    except Exception as e:
        error_msg = str(e).lower()

        # Mensagens de erro mais amigáveis
        if "connection refused" in error_msg or "failed to connect" in error_msg:
            db_name = "ClickHouse" if db_type == "clickhouse" else "PostgreSQL"
            return False, f"Conexão recusada. Verifique se o {db_name} está rodando e acessível no host/porta especificados."
        elif "authentication failed" in error_msg or "access denied" in error_msg:
            return False, "Falha na autenticação. Verifique o usuário e senha."
        elif "database" in error_msg and "does not exist" in error_msg:
            return False, "Banco de dados não encontrado. Verifique o nome do banco."
        elif "could not translate host name" in error_msg or "name or service not known" in error_msg:
            return False, "Host não encontrado. Verifique o endereço do servidor."
        elif "timeout" in error_msg or "timed out" in error_msg:
            return False, "Timeout na conexão. Verifique a conectividade de rede."
        elif "ssl" in error_msg or "certificate" in error_msg:
            return False, "Erro SSL/TLS. Verifique as configurações de segurança."
        else:
            return False, f"Erro na conexão: {str(e)}"


def build_clickhouse_uri(config: ClickHouseConfig) -> str:
    """
    Constrói URI de conexão ClickHouse a partir da configuração
    """
    protocol = "https" if config.secure else "http"
    if config.password:
        return f"clickhouse+http://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}?protocol={protocol}"
    else:
        return f"clickhouse+http://{config.username}@{config.host}:{config.port}/{config.database}?protocol={protocol}"


def build_postgresql_uri(config: PostgreSQLConfig) -> str:
    """
    Constrói URI de conexão PostgreSQL a partir da configuração
    """
    return f"postgresql+psycopg2://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"

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
        # Suporta tanto pg_dsn (legacy) quanto postgresql_config (novo)
        if payload.postgresql_config:
            pg_dsn = build_postgresql_uri(payload.postgresql_config)
        elif payload.pg_dsn:
            pg_dsn = payload.pg_dsn
        else:
            raise HTTPException(status_code=400, detail="pg_dsn ou postgresql_config é obrigatório para tipo postgres")

        # Testar a conexão antes de criar
        is_valid, error_message = test_connection(pg_dsn, "postgres")
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn = AgentConnection(owner_user_id=user.id, tipo="postgres", pg_dsn=pg_dsn)

    elif payload.tipo.lower() == "clickhouse":
        if not payload.clickhouse_config:
            raise HTTPException(status_code=400, detail="clickhouse_config é obrigatório para tipo clickhouse")

        # Construir URI de conexão
        ch_dsn = build_clickhouse_uri(payload.clickhouse_config)

        # Testar a conexão antes de criar
        is_valid, error_message = test_connection(ch_dsn, "clickhouse")
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn = AgentConnection(owner_user_id=user.id, tipo="clickhouse", ch_dsn=ch_dsn)

    else:
        raise HTTPException(status_code=400, detail="tipo inválido: use sqlite/duckdb/postgres/clickhouse")

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
        # Suporta tanto pg_dsn (legacy) quanto postgresql_config (novo)
        if payload.postgresql_config:
            pg_dsn = build_postgresql_uri(payload.postgresql_config)
        elif payload.pg_dsn:
            pg_dsn = payload.pg_dsn
        else:
            raise HTTPException(status_code=400, detail="pg_dsn ou postgresql_config é obrigatório para tipo postgres")

        is_valid, message = test_connection(pg_dsn, "postgres")
        return {
            "valid": is_valid,
            "message": message,
            "tipo": "postgres"
        }

    elif payload.tipo.lower() == "clickhouse":
        if not payload.clickhouse_config:
            raise HTTPException(status_code=400, detail="clickhouse_config é obrigatório para tipo clickhouse")

        ch_dsn = build_clickhouse_uri(payload.clickhouse_config)
        is_valid, message = test_connection(ch_dsn, "clickhouse")
        return {
            "valid": is_valid,
            "message": message,
            "tipo": "clickhouse"
        }

    else:
        raise HTTPException(status_code=400, detail="Teste de conexão disponível apenas para PostgreSQL e ClickHouse")

@router.patch("/{connection_id}", response_model=ConnectionOut)
def update_connection(connection_id: int, payload: ConnectionUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Atualizar uma conexão existente"""
    conn = db.query(AgentConnection).filter(
        AgentConnection.id == connection_id,
        AgentConnection.owner_user_id == user.id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="Conexão não encontrada")

    # Atualizar PostgreSQL
    if payload.pg_dsn is not None or payload.postgresql_config is not None:
        if conn.tipo != "postgres":
            raise HTTPException(status_code=400, detail="Configuração PostgreSQL só pode ser atualizada para conexões PostgreSQL")

        # Construir URI
        if payload.postgresql_config:
            pg_dsn = build_postgresql_uri(payload.postgresql_config)
        elif payload.pg_dsn:
            pg_dsn = payload.pg_dsn
        else:
            raise HTTPException(status_code=400, detail="pg_dsn ou postgresql_config é obrigatório")

        # Testar a nova conexão antes de atualizar
        is_valid, error_message = test_connection(pg_dsn, "postgres")
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn.pg_dsn = pg_dsn

    # Atualizar ClickHouse
    if payload.clickhouse_config is not None:
        if conn.tipo != "clickhouse":
            raise HTTPException(status_code=400, detail="Configuração ClickHouse só pode ser atualizada para conexões ClickHouse")

        # Construir URI
        ch_dsn = build_clickhouse_uri(payload.clickhouse_config)

        # Testar a nova conexão antes de atualizar
        is_valid, error_message = test_connection(ch_dsn, "clickhouse")
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn.ch_dsn = ch_dsn

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

