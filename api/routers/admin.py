from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional, Dict, Any
import logging
import time
import json
import os
import math
from datetime import datetime, timedelta

from ..db.session import get_db
from ..core.security import get_current_admin_user, get_current_super_admin_user
from ..models import User, Agent, AgentConnection, Dataset, Run, Empresa, ChatSession, Message, UserRole
from ..schemas import (
    AdminUserCreate, AdminUserUpdate, AdminUserOut,
    AdminDatasetCreate, AdminDatasetUpdate, AdminDatasetOut,
    AdminConnectionCreate, AdminConnectionUpdate, AdminConnectionOut,
    AdminAgentCreate, AdminAgentUpdate, AdminAgentOut,
    AdminRunOut, AdminStatsOut, AdminSystemInfoOut,
    PaginatedAdminRunsResponse, PaginationInfo,
    UserRoleUpdate, UserRoleEnum
)
from ..core.security import get_password_hash
from ..services.ingestion import save_csv_and_get_db_uri

logger = logging.getLogger(__name__)
router = APIRouter()

# ==========================================
# ADMIN USER MANAGEMENT
# ==========================================

@router.get("/users", response_model=List[AdminUserOut])
def admin_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todos os usuários do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Listando usuários - Admin: {admin_user.email}")
    
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.nome.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    
    if active_only:
        query = query.filter(User.ativo == True)
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"✅ ADMIN: Encontrados {len(users)} usuários")
    
    return users

@router.post("/users", response_model=AdminUserOut)
def admin_create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Cria novo usuário (admin only)"""
    logger.info(f"🔧 ADMIN: Criando usuário - Admin: {admin_user.email}, Email: {payload.email}")
    
    # Verifica se o email já existe
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Cria novo usuário
    hashed_password = get_password_hash(payload.password)
    new_user = User(
        nome=payload.nome,
        email=payload.email,
        senha_hash=hashed_password,
        ativo=payload.ativo
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"✅ ADMIN: Usuário criado - ID: {new_user.id}")
    return new_user

@router.get("/users/{user_id}", response_model=AdminUserOut)
def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Obtém usuário específico (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return user

@router.patch("/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Atualiza usuário (admin only)"""
    logger.info(f"🔧 ADMIN: Atualizando usuário {user_id} - Admin: {admin_user.email}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Atualiza campos fornecidos
    if payload.nome is not None:
        user.nome = payload.nome
    if payload.email is not None:
        # Verifica se novo email já existe
        existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email já está em uso")
        user.email = payload.email
    if payload.password is not None:
        user.senha_hash = get_password_hash(payload.password)
    if payload.ativo is not None:
        user.ativo = payload.ativo
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ ADMIN: Usuário {user_id} atualizado")
    return user

@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    force: bool = Query(False, description="Força deleção mesmo com dados relacionados"),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Deleta usuário (admin only)"""
    logger.info(f"🔧 ADMIN: Deletando usuário {user_id} - Admin: {admin_user.email}, Force: {force}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verifica se usuário tem dados relacionados
    agent_count = db.query(Agent).filter(Agent.owner_user_id == user_id).count()
    run_count = db.query(Run).filter(Run.user_id == user_id).count()
    
    if (agent_count > 0 or run_count > 0) and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Usuário possui {agent_count} agentes e {run_count} execuções. Use force=true para deletar."
        )
    
    if force:
        # Deletar em cascata (similar ao delete de agente)
        logger.info(f"🗑️ ADMIN: Deletando dados relacionados do usuário {user_id}")
        
        # Deletar embeddings das mensagens
        db.execute(text("""
            DELETE FROM message_embeddings
            WHERE message_id IN (
                SELECT m.id FROM messages m
                JOIN runs r ON m.run_id = r.id
                WHERE r.user_id = :user_id
            )
        """), {"user_id": user_id})
        
        # Deletar mensagens
        db.execute(text("""
            DELETE FROM messages
            WHERE run_id IN (
                SELECT id FROM runs WHERE user_id = :user_id
            )
        """), {"user_id": user_id})
        
        # Deletar runs
        db.query(Run).filter(Run.user_id == user_id).delete()
        
        # Deletar chat sessions
        db.query(ChatSession).filter(ChatSession.user_id == user_id).delete()
        
        # Deletar agentes
        db.query(Agent).filter(Agent.owner_user_id == user_id).delete()
        
        # Deletar conexões
        db.query(AgentConnection).filter(AgentConnection.owner_user_id == user_id).delete()
        
        # Deletar datasets
        db.query(Dataset).filter(Dataset.owner_user_id == user_id).delete()
    
    # Deletar usuário
    db.delete(user)
    db.commit()
    
    logger.info(f"✅ ADMIN: Usuário {user_id} deletado")
    return {"deleted": True, "user_id": user_id}

# ==========================================
# ADMIN ROLE MANAGEMENT
# ==========================================

@router.put("/users/{user_id}/role", response_model=AdminUserOut)
def admin_update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_super_admin_user)
):
    """Atualiza role de usuário (super admin only)"""
    logger.info(f"🔧 ADMIN: Atualizando role do usuário {user_id} para {role_update.role.value} - Super Admin: {admin_user.email}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Não permitir que super admin remova seu próprio privilégio
    if user.id == admin_user.id and role_update.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=400,
            detail="Super administrador não pode remover seus próprios privilégios"
        )

    old_role = user.role
    user.role = UserRole(role_update.role.value)
    db.commit()
    db.refresh(user)

    logger.info(f"✅ ADMIN: Role do usuário {user_id} alterada de {old_role.value} para {role_update.role.value}")
    return user

@router.get("/users/roles/stats")
def admin_get_role_stats(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Estatísticas de roles no sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Obtendo estatísticas de roles - Admin: {admin_user.email}")

    stats = {}
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        stats[role.value] = count

    total_users = db.query(User).count()

    result = {
        "total_users": total_users,
        "role_distribution": stats,
        "admin_count": stats.get("admin", 0) + stats.get("super_admin", 0),
        "regular_users": stats.get("user", 0)
    }

    logger.info(f"✅ ADMIN: Estatísticas de roles obtidas: {result}")
    return result

@router.get("/users/admins", response_model=List[AdminUserOut])
def admin_list_admin_users(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todos os usuários com privilégios admin (admin only)"""
    logger.info(f"🔧 ADMIN: Listando usuários admin - Admin: {admin_user.email}")

    admin_users = db.query(User).filter(
        User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ).order_by(User.created_at.desc()).all()

    logger.info(f"✅ ADMIN: Encontrados {len(admin_users)} usuários admin")
    return admin_users

# ==========================================
# ADMIN DATASET MANAGEMENT
# ==========================================

@router.get("/datasets", response_model=List[AdminDatasetOut])
def admin_list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    owner_user_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todos os datasets do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Listando datasets - Admin: {admin_user.email}")
    
    query = db.query(Dataset)
    
    if owner_user_id:
        query = query.filter(Dataset.owner_user_id == owner_user_id)
    
    if tipo:
        query = query.filter(Dataset.tipo == tipo)
    
    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"✅ ADMIN: Encontrados {len(datasets)} datasets")
    
    return datasets

@router.post("/datasets/upload", response_model=AdminDatasetOut)
async def admin_upload_dataset(
    file: UploadFile = File(...),
    owner_user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Upload de dataset como admin (admin only)"""
    logger.info(f"🔧 ADMIN: Upload de dataset - Admin: {admin_user.email}, File: {file.filename}")
    
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas CSV é suportado")
    
    # Criar registro de dataset
    ds = Dataset(
        owner_user_id=owner_user_id,
        nome=file.filename,
        tipo="csv",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    
    # Processar arquivo
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(await file.read())
    tmp.flush()
    tmp.close()
    
    db_uri = save_csv_and_get_db_uri(tmp.name, ds.id)
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    
    ds.source_path = f"dataset_{ds.id}/{file.filename}"
    ds.db_uri = db_uri
    db.commit()
    db.refresh(ds)
    
    logger.info(f"✅ ADMIN: Dataset criado - ID: {ds.id}")
    return ds

@router.delete("/datasets/{dataset_id}")
def admin_delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Deleta dataset (admin only)"""
    logger.info(f"🔧 ADMIN: Deletando dataset {dataset_id} - Admin: {admin_user.email}")

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")

    # Verificar se há conexões usando este dataset
    connections_using = db.query(AgentConnection).filter(
        AgentConnection.db_uri.like(f"%dataset_{dataset_id}%")
    ).count()

    if connections_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset está sendo usado por {connections_using} conexões. Delete as conexões primeiro."
        )

    db.delete(dataset)
    db.commit()

    logger.info(f"✅ ADMIN: Dataset {dataset_id} deletado")
    return {"deleted": True, "dataset_id": dataset_id}

# ==========================================
# ADMIN CONNECTION MANAGEMENT
# ==========================================

@router.get("/connections", response_model=List[AdminConnectionOut])
def admin_list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    owner_user_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todas as conexões do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Listando conexões - Admin: {admin_user.email}")

    query = db.query(AgentConnection)

    if owner_user_id:
        query = query.filter(AgentConnection.owner_user_id == owner_user_id)

    if tipo:
        query = query.filter(AgentConnection.tipo == tipo)

    connections = query.order_by(AgentConnection.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"✅ ADMIN: Encontradas {len(connections)} conexões")

    return connections

@router.post("/connections", response_model=AdminConnectionOut)
def admin_create_connection(
    payload: AdminConnectionCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Cria nova conexão como admin (admin only)"""
    logger.info(f"🔧 ADMIN: Criando conexão - Admin: {admin_user.email}, Tipo: {payload.tipo}")

    if payload.tipo.lower() in ("sqlite", "duckdb"):
        if not payload.dataset_id:
            raise HTTPException(status_code=400, detail="dataset_id é obrigatório para conexões baseadas em arquivo")
        ds = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
        if not ds or not ds.db_uri:
            raise HTTPException(status_code=400, detail="Dataset inválido ou sem db_uri")
        conn = AgentConnection(
            owner_user_id=payload.owner_user_id,
            tipo=payload.tipo.lower(),
            db_uri=ds.db_uri
        )
    elif payload.tipo.lower() == "postgres":
        if not payload.pg_dsn:
            raise HTTPException(status_code=400, detail="pg_dsn é obrigatório para tipo postgres")

        # Testar a conexão antes de criar
        from ..routers.connections import test_connection
        is_valid, error_message = test_connection(payload.pg_dsn)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Falha ao conectar: {error_message}")

        conn = AgentConnection(
            owner_user_id=payload.owner_user_id,
            tipo="postgres",
            pg_dsn=payload.pg_dsn
        )
    else:
        raise HTTPException(status_code=400, detail="tipo inválido: use sqlite/duckdb/postgres")

    db.add(conn)
    db.commit()
    db.refresh(conn)

    logger.info(f"✅ ADMIN: Conexão criada - ID: {conn.id}")
    return conn

@router.delete("/connections/{connection_id}")
def admin_delete_connection(
    connection_id: int,
    force: bool = Query(False, description="Força deleção mesmo com agentes relacionados"),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Deleta conexão (admin only)"""
    logger.info(f"🔧 ADMIN: Deletando conexão {connection_id} - Admin: {admin_user.email}, Force: {force}")

    conn = db.query(AgentConnection).filter(AgentConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Conexão não encontrada")

    # Verificar se há agentes usando esta conexão
    agents_using_connection = db.query(Agent).filter(Agent.connection_id == connection_id).all()

    if agents_using_connection and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Conexão está sendo usada por {len(agents_using_connection)} agentes. Use force=true para deletar."
        )

    if force and agents_using_connection:
        # Deletar em cascata (similar ao delete de conexão normal)
        for agent in agents_using_connection:
            db.execute(text("""
                DELETE FROM message_embeddings
                WHERE message_id IN (
                    SELECT m.id FROM messages m
                    JOIN runs r ON m.run_id = r.id
                    WHERE r.agent_id = :agent_id
                )
            """), {"agent_id": agent.id})

        for agent in agents_using_connection:
            db.execute(text("""
                DELETE FROM messages
                WHERE run_id IN (
                    SELECT id FROM runs WHERE agent_id = :agent_id
                )
            """), {"agent_id": agent.id})

        # Deletar runs dos agentes
        for agent in agents_using_connection:
            db.query(Run).filter(Run.agent_id == agent.id).delete()

        # Deletar chat sessions dos agentes
        for agent in agents_using_connection:
            db.query(ChatSession).filter(ChatSession.agent_id == agent.id).delete()

        # Deletar agentes
        db.query(Agent).filter(Agent.connection_id == connection_id).delete()

    # Deletar conexão
    db.delete(conn)
    db.commit()

    logger.info(f"✅ ADMIN: Conexão {connection_id} deletada")
    return {"deleted": True, "connection_id": connection_id}

# ==========================================
# ADMIN AGENT MANAGEMENT
# ==========================================

@router.get("/agents", response_model=List[AdminAgentOut])
def admin_list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    owner_user_id: Optional[int] = Query(None),
    connection_id: Optional[int] = Query(None),
    selected_model: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todos os agentes do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Listando agentes - Admin: {admin_user.email}")

    query = db.query(Agent)

    if owner_user_id:
        query = query.filter(Agent.owner_user_id == owner_user_id)

    if connection_id:
        query = query.filter(Agent.connection_id == connection_id)

    if selected_model:
        query = query.filter(Agent.selected_model == selected_model)

    agents = query.order_by(Agent.created_at.desc()).offset(skip).limit(limit).all()
    logger.info(f"✅ ADMIN: Encontrados {len(agents)} agentes")

    return agents

@router.post("/agents", response_model=AdminAgentOut)
def admin_create_agent(
    payload: AdminAgentCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Cria novo agente como admin (admin only)"""
    logger.info(f"🔧 ADMIN: Criando agente - Admin: {admin_user.email}, Nome: {payload.nome}")

    # Verifica se a conexão existe
    conn = db.query(AgentConnection).filter(AgentConnection.id == payload.connection_id).first()
    if not conn:
        raise HTTPException(status_code=400, detail="Conexão informada não existe")

    # Converte features para JSON string se fornecido
    features_json = None
    if payload.features:
        features_json = json.dumps(payload.features)

    ag = Agent(
        owner_user_id=payload.owner_user_id,
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
        description=payload.description,
        icon=payload.icon,
        color=payload.color,
        features=features_json,
        version=1
    )

    db.add(ag)
    db.commit()
    db.refresh(ag)

    logger.info(f"✅ ADMIN: Agente criado - ID: {ag.id}")
    return ag

@router.patch("/agents/{agent_id}", response_model=AdminAgentOut)
def admin_update_agent(
    agent_id: int,
    payload: AdminAgentUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Atualiza agente (admin only)"""
    logger.info(f"🔧 ADMIN: Atualizando agente {agent_id} - Admin: {admin_user.email}")

    ag = db.query(Agent).filter(Agent.id == agent_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    # Verifica se nova conexão existe (se fornecida)
    if payload.connection_id is not None:
        conn = db.query(AgentConnection).filter(AgentConnection.id == payload.connection_id).first()
        if not conn:
            raise HTTPException(status_code=400, detail="Conexão informada não existe")

    # Atualiza campos fornecidos
    updated = False
    if payload.nome is not None:
        ag.nome = payload.nome
        updated = True
    if payload.connection_id is not None:
        ag.connection_id = payload.connection_id
        updated = True
    if payload.selected_model is not None:
        ag.selected_model = payload.selected_model
        updated = True
    if payload.top_k is not None:
        ag.top_k = payload.top_k
        updated = True
    if payload.include_tables_key is not None:
        ag.include_tables_key = payload.include_tables_key
        updated = True
    if payload.advanced_mode is not None:
        ag.advanced_mode = payload.advanced_mode
        updated = True
    if payload.processing_enabled is not None:
        ag.processing_enabled = payload.processing_enabled
        updated = True
    if payload.refinement_enabled is not None:
        ag.refinement_enabled = payload.refinement_enabled
        updated = True
    if payload.single_table_mode is not None:
        ag.single_table_mode = payload.single_table_mode
        updated = True
    if payload.selected_table is not None:
        ag.selected_table = payload.selected_table
        updated = True
    if payload.description is not None:
        ag.description = payload.description
        updated = True
    if payload.icon is not None:
        ag.icon = payload.icon
        updated = True
    if payload.color is not None:
        ag.color = payload.color
        updated = True
    if payload.features is not None:
        ag.features = json.dumps(payload.features) if payload.features else None
        updated = True
    if payload.owner_user_id is not None:
        ag.owner_user_id = payload.owner_user_id
        updated = True

    # Incrementa versão se houve mudanças técnicas
    if updated:
        ag.version += 1

    db.commit()
    db.refresh(ag)

    logger.info(f"✅ ADMIN: Agente {agent_id} atualizado")
    return ag

@router.delete("/agents/{agent_id}")
def admin_delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Deleta agente (admin only)"""
    logger.info(f"🔧 ADMIN: Deletando agente {agent_id} - Admin: {admin_user.email}")

    ag = db.query(Agent).filter(Agent.id == agent_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    # Deletar em cascata completa (similar ao delete normal)
    logger.info(f"🗑️ ADMIN: Deletando dados relacionados do agente {agent_id}")

    # Deletar embeddings das mensagens
    db.execute(text("""
        DELETE FROM message_embeddings
        WHERE message_id IN (
            SELECT m.id FROM messages m
            JOIN runs r ON m.run_id = r.id
            WHERE r.agent_id = :agent_id
        )
    """), {"agent_id": agent_id})

    # Deletar mensagens
    db.execute(text("""
        DELETE FROM messages
        WHERE run_id IN (
            SELECT id FROM runs WHERE agent_id = :agent_id
        )
    """), {"agent_id": agent_id})

    # Deletar runs
    db.query(Run).filter(Run.agent_id == agent_id).delete()

    # Deletar chat sessions
    db.query(ChatSession).filter(ChatSession.agent_id == agent_id).delete()

    # Deletar agente
    db.delete(ag)
    db.commit()

    logger.info(f"✅ ADMIN: Agente {agent_id} deletado")
    return {"deleted": True, "agent_id": agent_id}

# ==========================================
# ADMIN RUN MANAGEMENT
# ==========================================

@router.get("/runs", response_model=PaginatedAdminRunsResponse)
def admin_list_runs(
    page: int = Query(1, ge=1, description="Número da página (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    user_id: Optional[int] = Query(None, description="Filtrar por usuário"),
    agent_id: Optional[int] = Query(None, description="Filtrar por agente"),
    chat_session_id: Optional[int] = Query(None, description="Filtrar por sessão de chat"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todas as execuções do sistema com paginação (admin only)"""
    logger.info(f"🔧 ADMIN: Listando runs - Admin: {admin_user.email}, Page: {page}, Per Page: {per_page}")

    # Query base
    query = db.query(Run)

    # Filtros opcionais
    if user_id:
        query = query.filter(Run.user_id == user_id)
        logger.info(f"🔍 ADMIN: Filtrando por user_id: {user_id}")

    if agent_id:
        query = query.filter(Run.agent_id == agent_id)
        logger.info(f"🔍 ADMIN: Filtrando por agent_id: {agent_id}")

    if chat_session_id:
        query = query.filter(Run.chat_session_id == chat_session_id)
        logger.info(f"🔍 ADMIN: Filtrando por chat_session_id: {chat_session_id}")

    if status:
        query = query.filter(Run.status == status)
        logger.info(f"🔍 ADMIN: Filtrando por status: {status}")

    # Contar total de itens
    total_items = query.count()

    # Calcular paginação
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    offset = (page - 1) * per_page

    # Buscar runs paginadas
    runs = query.order_by(Run.created_at.desc()).offset(offset).limit(per_page).all()

    logger.info(f"✅ ADMIN: Encontradas {len(runs)} execuções (página {page}/{total_pages})")

    # Criar resposta paginada
    pagination_info = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return PaginatedAdminRunsResponse(runs=runs, pagination=pagination_info)

@router.get("/agents/{agent_id}/runs", response_model=PaginatedAdminRunsResponse)
def admin_list_agent_runs(
    agent_id: int,
    page: int = Query(1, ge=1, description="Número da página (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Itens por página"),
    user_id: Optional[int] = Query(None, description="Filtrar por usuário"),
    chat_session_id: Optional[int] = Query(None, description="Filtrar por sessão de chat"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Lista todas as execuções de um agente específico com paginação (admin only)"""
    logger.info(f"🔧 ADMIN: Listando runs do agente {agent_id} - Admin: {admin_user.email}, Page: {page}, Per Page: {per_page}")

    # Verificar se o agente existe
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    # Query base filtrada por agente
    query = db.query(Run).filter(Run.agent_id == agent_id)

    # Filtros opcionais
    if user_id:
        query = query.filter(Run.user_id == user_id)
        logger.info(f"🔍 ADMIN: Filtrando por user_id: {user_id}")

    if chat_session_id:
        query = query.filter(Run.chat_session_id == chat_session_id)
        logger.info(f"🔍 ADMIN: Filtrando por chat_session_id: {chat_session_id}")

    if status:
        query = query.filter(Run.status == status)
        logger.info(f"🔍 ADMIN: Filtrando por status: {status}")

    # Contar total de itens
    total_items = query.count()

    # Calcular paginação
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    offset = (page - 1) * per_page

    # Buscar runs paginadas
    runs = query.order_by(Run.created_at.desc()).offset(offset).limit(per_page).all()

    logger.info(f"✅ ADMIN: Encontradas {len(runs)} execuções para agente {agent_id} (página {page}/{total_pages})")

    # Criar resposta paginada
    pagination_info = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return PaginatedAdminRunsResponse(runs=runs, pagination=pagination_info)

@router.delete("/runs/{run_id}")
def admin_delete_run(
    run_id: int,
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Deleta execução específica (admin only)"""
    logger.info(f"🔧 ADMIN: Deletando run {run_id} - Admin: {admin_user.email}")

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    # Deletar embeddings das mensagens relacionadas
    db.execute(text("""
        DELETE FROM message_embeddings
        WHERE message_id IN (
            SELECT id FROM messages WHERE run_id = :run_id
        )
    """), {"run_id": run_id})

    # Deletar mensagens relacionadas
    db.query(Message).filter(Message.run_id == run_id).delete()

    # Deletar run
    db.delete(run)
    db.commit()

    logger.info(f"✅ ADMIN: Run {run_id} deletada")
    return {"deleted": True, "run_id": run_id}

# ==========================================
# ADMIN STATISTICS & MONITORING
# ==========================================

@router.get("/stats", response_model=AdminStatsOut)
def admin_get_stats(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Obtém estatísticas do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Obtendo estatísticas - Admin: {admin_user.email}")

    # Contadores básicos
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.ativo == True).count()
    total_agents = db.query(Agent).count()
    total_connections = db.query(AgentConnection).count()
    total_datasets = db.query(Dataset).count()
    total_runs = db.query(Run).count()

    # Runs por status
    runs_by_status = {}
    status_results = db.query(Run.status, func.count(Run.id)).group_by(Run.status).all()
    for status, count in status_results:
        runs_by_status[status] = count

    # Atividade recente (últimas 24h)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_activity = []

    # Usuários criados recentemente
    recent_users = db.query(User).filter(User.created_at >= yesterday).count()
    if recent_users > 0:
        recent_activity.append({
            "type": "users_created",
            "count": recent_users,
            "description": f"{recent_users} novos usuários"
        })

    # Agentes criados recentemente
    recent_agents = db.query(Agent).filter(Agent.created_at >= yesterday).count()
    if recent_agents > 0:
        recent_activity.append({
            "type": "agents_created",
            "count": recent_agents,
            "description": f"{recent_agents} novos agentes"
        })

    # Runs executadas recentemente
    recent_runs = db.query(Run).filter(Run.created_at >= yesterday).count()
    if recent_runs > 0:
        recent_activity.append({
            "type": "runs_executed",
            "count": recent_runs,
            "description": f"{recent_runs} execuções"
        })

    stats = AdminStatsOut(
        total_users=total_users,
        active_users=active_users,
        total_agents=total_agents,
        total_connections=total_connections,
        total_datasets=total_datasets,
        total_runs=total_runs,
        runs_by_status=runs_by_status,
        recent_activity=recent_activity
    )

    logger.info(f"✅ ADMIN: Estatísticas obtidas")
    return stats

@router.get("/system-info", response_model=AdminSystemInfoOut)
def admin_get_system_info(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Obtém informações do sistema (admin only)"""
    logger.info(f"🔧 ADMIN: Obtendo informações do sistema - Admin: {admin_user.email}")

    from ..core.settings import settings

    # Status do banco de dados
    database_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "disconnected"

    # Status do Redis
    redis_status = "connected"
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
    except Exception:
        redis_status = "disconnected"

    # Status do Celery (simplificado)
    celery_status = "unknown"
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        # Verificar se há workers ativos através de chaves do Celery
        worker_keys = r.keys('celery-task-meta-*')
        celery_status = "active" if worker_keys else "inactive"
    except Exception:
        celery_status = "disconnected"

    # Informações de armazenamento (simplificado sem psutil)
    total_storage_mb = None
    try:
        if hasattr(settings, 'DATA_DIR'):
            import os
            # Método alternativo sem psutil
            if os.path.exists(settings.DATA_DIR):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(settings.DATA_DIR):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
                total_storage_mb = total_size / (1024 * 1024)  # MB
    except Exception:
        pass

    # Uptime (simplificado sem psutil)
    uptime_seconds = None
    try:
        # Usar tempo desde que o processo Python iniciou (aproximação)
        import os
        uptime_seconds = time.time() - os.path.getctime('/proc/1/stat') if os.path.exists('/proc/1/stat') else None
    except Exception:
        pass

    system_info = AdminSystemInfoOut(
        version="0.1.0",  # Versão da API
        environment=settings.ENV,
        database_status=database_status,
        redis_status=redis_status,
        celery_status=celery_status,
        total_storage_mb=total_storage_mb,
        uptime_seconds=uptime_seconds
    )

    logger.info(f"✅ ADMIN: Informações do sistema obtidas")
    return system_info

# ==========================================
# ADMIN BULK OPERATIONS
# ==========================================

@router.post("/bulk/cleanup-failed-runs")
def admin_cleanup_failed_runs(
    older_than_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    """Remove runs falhadas antigas (admin only)"""
    logger.info(f"🔧 ADMIN: Limpeza de runs falhadas - Admin: {admin_user.email}, Dias: {older_than_days}")

    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

    # Buscar runs falhadas antigas
    failed_runs = db.query(Run).filter(
        Run.status.in_(["failure", "timeout"]),
        Run.created_at < cutoff_date
    ).all()

    deleted_count = 0
    for run in failed_runs:
        # Deletar embeddings das mensagens
        db.execute(text("""
            DELETE FROM message_embeddings
            WHERE message_id IN (
                SELECT id FROM messages WHERE run_id = :run_id
            )
        """), {"run_id": run.id})

        # Deletar mensagens
        db.query(Message).filter(Message.run_id == run.id).delete()

        # Deletar run
        db.delete(run)
        deleted_count += 1

    db.commit()

    logger.info(f"✅ ADMIN: {deleted_count} runs falhadas removidas")
    return {
        "deleted_runs": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
        "criteria": f"status in [failure, timeout] and older than {older_than_days} days"
    }
