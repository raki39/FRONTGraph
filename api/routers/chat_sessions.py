from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import List, Optional
from datetime import datetime

from ..db.session import get_db
from ..core.security import get_current_user
from ..models import ChatSession, Message, Agent, Run
from ..schemas import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionOut,
    ChatSessionListOut,
    ChatSessionListResponse,
    ChatSessionWithMessages,
    MessageOut,
    PaginationInfo
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=ChatSessionListResponse)
def list_user_chat_sessions(
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=50, description="Sessões por página"),
    agent_id: Optional[int] = Query(None, description="Filtrar por agente específico"),
    status: Optional[str] = Query("active", description="Filtrar por status (active, archived)"),
    search: Optional[str] = Query(None, description="Buscar por título da sessão"),
    min_messages: Optional[int] = Query(None, description="Mínimo de mensagens"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Lista sessões de chat do usuário com informações otimizadas para UI
    """
    logger.info(f"📋 Listando chat sessions - User: {user.id}, Agent: {agent_id}, Status: {status}")
    
    # Query base com subquery para última mensagem
    last_message_subquery = (
        db.query(
            Message.chat_session_id,
            Message.content.label('last_message_content'),
            func.row_number().over(
                partition_by=Message.chat_session_id,
                order_by=desc(Message.created_at)
            ).label('rn')
        )
        .filter(Message.role == 'assistant')  # Apenas respostas do agente
        .subquery()
    )
    
    # Query principal
    query = (
        db.query(
            ChatSession.id,
            ChatSession.title,
            ChatSession.last_activity.label('updated_at'),
            ChatSession.total_messages.label('messages_count'),
            ChatSession.status,
            ChatSession.agent_id,
            last_message_subquery.c.last_message_content.label('last_message')
        )
        .outerjoin(
            last_message_subquery,
            (ChatSession.id == last_message_subquery.c.chat_session_id) & 
            (last_message_subquery.c.rn == 1)
        )
        .filter(ChatSession.user_id == user.id)
    )
    
    # Filtros
    if agent_id:
        # Verificar se agente pertence ao usuário
        agent = db.query(Agent).filter(Agent.id == agent_id, Agent.owner_user_id == user.id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agente não encontrado")
        query = query.filter(ChatSession.agent_id == agent_id)
        logger.info(f"🔍 Filtrando por agent_id: {agent_id}")

    if status:
        query = query.filter(ChatSession.status == status)
        logger.info(f"🔍 Filtrando por status: {status}")

    if search:
        query = query.filter(ChatSession.title.ilike(f"%{search}%"))
        logger.info(f"🔍 Buscando por título: {search}")

    if min_messages:
        query = query.filter(ChatSession.total_messages >= min_messages)
        logger.info(f"🔍 Filtrando por mínimo de mensagens: {min_messages}")
    
    # Contar total de registros para paginação
    total_count = query.count()

    # Aplicar paginação
    offset = (page - 1) * per_page
    sessions = query.order_by(desc(ChatSession.last_activity)).offset(offset).limit(per_page).all()

    logger.info(f"✅ Encontradas {len(sessions)} chat sessions (página {page}/{(total_count + per_page - 1) // per_page})")

    # Converter para formato esperado
    sessions_list = []
    for session in sessions:
        sessions_list.append(ChatSessionListOut(
            id=session.id,
            title=session.title,
            last_message=session.last_message,
            messages_count=session.messages_count,  # Campo com label da query
            updated_at=session.updated_at,          # Campo com label da query
            status=session.status,
            agent_id=session.agent_id
        ))

    # Criar resposta paginada
    total_pages = (total_count + per_page - 1) // per_page
    pagination = PaginationInfo(
        page=page,
        per_page=per_page,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return ChatSessionListResponse(
        sessions=sessions_list,
        pagination=pagination
    )

@router.post("/", response_model=ChatSessionOut)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Cria nova sessão de chat
    """
    logger.info(f"💬 Criando nova chat session - User: {user.id}, Agent: {payload.agent_id}")
    
    # Verificar se agente existe e pertence ao usuário
    agent = db.query(Agent).filter(
        Agent.id == payload.agent_id, 
        Agent.owner_user_id == user.id
    ).first()
    
    if not agent:
        logger.error(f"❌ Agente {payload.agent_id} não encontrado para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    # Gerar título se não fornecido
    title = payload.title
    if not title:
        title = f"Conversa {datetime.now().strftime('%d/%m %H:%M')}"
    
    # Criar sessão
    session = ChatSession(
        user_id=user.id,
        agent_id=payload.agent_id,
        title=title,
        status="active",
        total_messages=0
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    logger.info(f"✅ Chat session criada: ID {session.id}, Título: '{session.title}'")
    return session

@router.get("/{session_id}", response_model=ChatSessionOut)
def get_chat_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém detalhes da sessão de chat (SEM mensagens para evitar sobrecarga)
    Use GET /chat-sessions/{id}/messages para obter mensagens paginadas
    """
    logger.info(f"🔍 Buscando chat session {session_id} - User: {user.id}")

    # Buscar sessão
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()

    if not session:
        logger.error(f"❌ Chat session {session_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")

    # Buscar última mensagem para contexto
    last_message_query = db.query(Message.content).filter(
        Message.chat_session_id == session_id,
        Message.role == "assistant"  # Última resposta do assistente
    ).order_by(Message.created_at.desc()).first()

    # Adicionar última mensagem ao objeto de resposta
    session_dict = {
        "id": session.id,
        "user_id": session.user_id,
        "agent_id": session.agent_id,
        "title": session.title,
        "created_at": session.created_at,
        "last_activity": session.last_activity,
        "total_messages": session.total_messages,
        "status": session.status,
        "context_summary": session.context_summary,
        "last_message": last_message_query[0] if last_message_query else None
    }

    logger.info(f"✅ Chat session encontrada: {session.total_messages} mensagens")

    return session_dict

@router.get("/{session_id}/messages")
def get_chat_session_messages(
    session_id: int,
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(20, ge=1, le=100, description="Mensagens por página"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Lista mensagens de uma sessão de chat com paginação
    """
    logger.info(f"📋 Listando mensagens da chat session {session_id} - User: {user.id}")

    # Verificar se sessão existe e pertence ao usuário
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()

    if not session:
        logger.error(f"❌ Chat session {session_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")

    # Query das mensagens
    query = db.query(Message).filter(Message.chat_session_id == session_id)

    # Paginação
    total_items = query.count()
    offset = (page - 1) * per_page
    messages = query.order_by(Message.sequence_order).offset(offset).limit(per_page).all()

    logger.info(f"✅ Encontradas {len(messages)} mensagens (total: {total_items})")

    return {
        "messages": [MessageOut(
            id=msg.id,
            chat_session_id=msg.chat_session_id,
            run_id=msg.run_id,
            role=msg.role,
            content=msg.content,
            sql_query=msg.sql_query,
            created_at=msg.created_at,
            sequence_order=msg.sequence_order,
            message_metadata=msg.message_metadata
        ) for msg in messages],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": (total_items + per_page - 1) // per_page
        },
        "session_info": {
            "id": session.id,
            "title": session.title,
            "total_messages": session.total_messages
        }
    }

@router.put("/{session_id}", response_model=ChatSessionOut)
def update_chat_session(
    session_id: int,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Atualiza sessão de chat (título, status)
    """
    logger.info(f"✏️ Atualizando chat session {session_id} - User: {user.id}")
    
    # Buscar sessão
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()
    
    if not session:
        logger.error(f"❌ Chat session {session_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    # Atualizar campos
    updated_fields = []
    if payload.title is not None:
        session.title = payload.title
        updated_fields.append(f"título: '{payload.title}'")
    
    if payload.status is not None:
        if payload.status not in ["active", "archived"]:
            raise HTTPException(status_code=400, detail="Status deve ser 'active' ou 'archived'")
        session.status = payload.status
        updated_fields.append(f"status: '{payload.status}'")
    
    if not updated_fields:
        logger.warning(f"⚠️ Nenhum campo para atualizar na chat session {session_id}")
        return session
    
    # Atualizar última atividade
    session.last_activity = datetime.utcnow()
    
    db.commit()
    db.refresh(session)
    
    logger.info(f"✅ Chat session {session_id} atualizada: {', '.join(updated_fields)}")
    return session

@router.delete("/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Deleta sessão de chat e todas as mensagens relacionadas
    """
    logger.info(f"🗑️ Deletando chat session {session_id} - User: {user.id}")
    
    # Buscar sessão
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()
    
    if not session:
        logger.error(f"❌ Chat session {session_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    # Contar mensagens e runs que serão afetadas
    messages_count = db.query(Message).filter(Message.chat_session_id == session_id).count()
    runs_count = db.query(Run).filter(Run.chat_session_id == session_id).count()
    
    # Deletar sessão (cascade deletará mensagens automaticamente)
    db.delete(session)
    db.commit()
    
    logger.info(f"✅ Chat session {session_id} deletada (afetou {messages_count} mensagens e {runs_count} runs)")
    
    return {
        "deleted": True, 
        "session_id": session_id,
        "affected_messages": messages_count,
        "affected_runs": runs_count
    }

@router.get("/{session_id}/runs")
def get_chat_session_runs(
    session_id: int,
    page: int = Query(1, ge=1, description="Número da página"),
    per_page: int = Query(10, ge=1, le=50, description="Itens por página"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Lista todas as runs de uma sessão de chat específica
    """
    logger.info(f"📋 Listando runs da chat session {session_id} - User: {user.id}")
    
    # Verificar se sessão existe e pertence ao usuário
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()
    
    if not session:
        logger.error(f"❌ Chat session {session_id} não encontrada para usuário {user.id}")
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    # Query das runs
    query = db.query(Run).filter(Run.chat_session_id == session_id)
    
    # Paginação
    total_items = query.count()
    offset = (page - 1) * per_page
    runs = query.order_by(desc(Run.created_at)).offset(offset).limit(per_page).all()
    
    logger.info(f"✅ Encontradas {len(runs)} runs (total: {total_items})")
    
    return {
        "runs": runs,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": (total_items + per_page - 1) // per_page
        },
        "session_info": {
            "id": session.id,
            "title": session.title,
            "total_messages": session.total_messages
        }
    }
