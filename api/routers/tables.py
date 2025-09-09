from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import logging
from ..db.session import get_db
from ..core.security import get_current_user
from ..models import Agent, AgentConnection

router = APIRouter()

class CreateTableRequest(BaseModel):
    table_name: str
    sql_query: str
    agent_id: int

class CreateTableResponse(BaseModel):
    success: bool
    message: str
    records_count: int = None

def parse_pg_dsn(pg_dsn: str) -> Dict[str, Any]:
    """
    Parse PostgreSQL DSN para extrair configurações
    Formato: postgresql://username:password@host:port/database
    """
    try:
        # Remove o prefixo postgresql://
        if pg_dsn.startswith('postgresql://'):
            dsn_part = pg_dsn[13:]  # Remove 'postgresql://'
        else:
            raise ValueError("DSN deve começar com 'postgresql://'")
        
        # Separa credenciais do resto
        if '@' in dsn_part:
            credentials, host_part = dsn_part.split('@', 1)
            if ':' in credentials:
                username, password = credentials.split(':', 1)
            else:
                username = credentials
                password = ''
        else:
            raise ValueError("DSN deve conter credenciais")
        
        # Separa host:port/database
        if '/' in host_part:
            host_port, database = host_part.split('/', 1)
        else:
            raise ValueError("DSN deve conter nome do banco")
        
        # Separa host e port
        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 5432  # Porta padrão PostgreSQL
        
        return {
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": password
        }
    except Exception as e:
        raise ValueError(f"Erro ao fazer parse do DSN: {str(e)}")

@router.post("/create", response_model=CreateTableResponse)
async def create_table_from_query(
    payload: CreateTableRequest, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    """
    Cria uma nova tabela PostgreSQL baseada em uma query SQL
    """
    try:
        # Verificar se o agente existe e pertence ao usuário
        agent = db.query(Agent).filter(
            Agent.id == payload.agent_id,
            Agent.owner_user_id == user.id
        ).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agente não encontrado")
        
        # Verificar se a conexão é PostgreSQL
        connection = db.query(AgentConnection).filter(
            AgentConnection.id == agent.connection_id
        ).first()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Conexão do agente não encontrada")
        
        if connection.tipo != "postgres":
            raise HTTPException(
                status_code=400, 
                detail="Criação de tabela disponível apenas para conexões PostgreSQL"
            )
        
        if not connection.pg_dsn:
            raise HTTPException(status_code=400, detail="DSN PostgreSQL não configurado")
        
        # Parse do DSN para obter configurações
        try:
            postgresql_config = parse_pg_dsn(connection.pg_dsn)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Importar e executar a função de criação de tabela
        try:
            # Importar diretamente do agentgraph
            from agentgraph.utils.postgresql_table_creator import create_table_from_query

            # Executar a criação da tabela
            result = await create_table_from_query(
                payload.table_name,
                payload.sql_query,
                postgresql_config
            )

            return CreateTableResponse(
                success=result["success"],
                message=result["message"],
                records_count=result.get("records_count")
            )

        except ImportError as e:
            logging.error(f"Erro ao importar postgresql_table_creator: {e}")
            raise HTTPException(
                status_code=500,
                detail="Módulo de criação de tabela não disponível"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erro ao criar tabela: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
