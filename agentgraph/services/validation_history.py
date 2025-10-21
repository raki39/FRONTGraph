"""
Serviço para buscar histórico de runs para validação comparativa
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

logger = logging.getLogger(__name__)

class ValidationHistoryService:
    """
    Serviço para buscar histórico de runs para validação comparativa
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def get_recent_runs_for_comparison(
        self,
        user_id: int,
        limit: int = 3,
        exclude_run_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        exclude_chat_session_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca runs recentes para comparação (versão async)
        Agora com suporte para excluir runs da mesma sessão de chat
        """
        try:
            # Importa aqui para evitar circular import
            from api.db.session import SessionLocal

            db = SessionLocal()
            try:
                return get_recent_runs_for_comparison(
                    db=db,
                    current_run_id=exclude_run_id or 0,
                    user_id=user_id,
                    agent_id=agent_id,
                    limit=limit,
                    exclude_chat_session_id=exclude_chat_session_id
                )
            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Erro ao buscar runs recentes: {e}")
            return []

    async def get_session_runs_for_comparison(
        self,
        chat_session_id: int,
        user_id: int,
        exclude_run_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca runs da mesma sessão de chat para comparação de consistência
        """
        try:
            from api.db.session import SessionLocal
            from api.models import Run

            db = SessionLocal()
            try:
                query = db.query(Run).filter(
                    and_(
                        Run.chat_session_id == chat_session_id,
                        Run.user_id == user_id,
                        Run.status == "success"
                    )
                )

                if exclude_run_id:
                    query = query.filter(Run.id != exclude_run_id)

                runs = query.order_by(desc(Run.created_at)).limit(limit).all()

                return [
                    {
                        "id": run.id,
                        "question": run.question,
                        "sql_query": run.sql_used or "",
                        "response": run.result_data or "",
                        "created_at": run.created_at.isoformat(),
                        "chat_session_id": run.chat_session_id,
                        "execution_ms": run.execution_ms,
                        "result_rows_count": run.result_rows_count
                    }
                    for run in runs
                ]

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Erro ao buscar runs da sessão {chat_session_id}: {e}")
            return []

    async def get_similar_runs_for_comparison(
        self,
        question: str,
        user_id: int,
        limit: int = 3,
        exclude_run_id: Optional[int] = None,
        agent_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca runs similares para comparação (versão async)
        """
        try:
            from api.db.session import SessionLocal

            db = SessionLocal()
            try:
                return get_similar_runs_for_comparison(
                    db=db,
                    current_run_id=exclude_run_id or 0,
                    current_question=question,
                    user_id=user_id,
                    agent_id=agent_id,
                    limit=limit
                )
            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Erro ao buscar runs similares: {e}")
            return []

def get_recent_runs_for_comparison(
    db: Session,
    current_run_id: int,
    user_id: int,
    agent_id: Optional[int] = None,
    limit: int = 3,
    exclude_current: bool = True,
    exclude_chat_session_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Busca runs recentes para comparação

    Args:
        db: Sessão do banco de dados
        current_run_id: ID da run atual (para excluir)
        user_id: ID do usuário
        agent_id: ID do agente (opcional, se None busca de todos os agentes)
        limit: Número máximo de runs para retornar
        exclude_current: Se deve excluir a run atual
        exclude_chat_session_id: ID da sessão de chat para excluir (opcional)

    Returns:
        Lista de runs formatadas para comparação
    """
    try:
        # Importa aqui para evitar circular import
        from api.models import Run
        
        logger.info(f"[VALIDATION_HISTORY] Buscando {limit} runs recentes para comparação")
        logger.info(f"[VALIDATION_HISTORY] User: {user_id}, Agent: {agent_id}, Exclude: {current_run_id}")
        
        # Query base
        query = db.query(Run).filter(
            Run.user_id == user_id,
            Run.status == "success",  # Apenas runs bem-sucedidas
            Run.sql_used.isnot(None),  # Que tenham SQL
            Run.result_data.isnot(None)  # E resultado
        )
        
        # Filtrar por agente se especificado
        if agent_id:
            query = query.filter(Run.agent_id == agent_id)
        
        # Excluir run atual se solicitado
        if exclude_current:
            query = query.filter(Run.id != current_run_id)

        # Excluir runs da mesma sessão de chat se solicitado
        if exclude_chat_session_id:
            query = query.filter(
                (Run.chat_session_id != exclude_chat_session_id) |
                (Run.chat_session_id.is_(None))
            )
        
        # Ordenar por data (mais recentes primeiro) e limitar
        runs = query.order_by(desc(Run.created_at)).limit(limit).all()
        
        logger.info(f"[VALIDATION_HISTORY] Encontradas {len(runs)} runs para comparação")
        
        # Formatar runs para validação
        formatted_runs = []
        for run in runs:
            formatted_run = {
                "run_id": run.id,
                "question": run.question,
                "sql_query": run.sql_used,
                "response": run.result_data,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "agent_id": run.agent_id
            }
            formatted_runs.append(formatted_run)
            
            logger.debug(f"[VALIDATION_HISTORY] Run {run.id}: '{run.question[:50]}...'")
        
        return formatted_runs
        
    except Exception as e:
        logger.error(f"[VALIDATION_HISTORY] Erro ao buscar runs: {e}")
        return []

def get_similar_runs_for_comparison(
    db: Session,
    current_run_id: int,
    current_question: str,
    user_id: int,
    agent_id: Optional[int] = None,
    limit: int = 3,
    similarity_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Busca runs similares baseado na pergunta para comparação mais inteligente
    
    Args:
        db: Sessão do banco de dados
        current_run_id: ID da run atual
        current_question: Pergunta atual para comparação
        user_id: ID do usuário
        agent_id: ID do agente (opcional)
        limit: Número máximo de runs
        similarity_threshold: Threshold de similaridade (não implementado ainda)
        
    Returns:
        Lista de runs similares
    """
    try:
        from api.models import Run
        
        logger.info(f"[VALIDATION_HISTORY] Buscando runs similares para: '{current_question[:50]}...'")
        
        # Por enquanto, busca runs que contenham palavras-chave similares
        # TODO: Implementar similaridade semântica com embeddings
        
        # Extrair palavras-chave da pergunta atual
        keywords = extract_keywords_from_question(current_question)
        logger.info(f"[VALIDATION_HISTORY] Palavras-chave extraídas: {keywords}")
        
        # Query base
        query = db.query(Run).filter(
            Run.user_id == user_id,
            Run.status == "success",
            Run.sql_used.isnot(None),
            Run.result_data.isnot(None),
            Run.id != current_run_id
        )
        
        if agent_id:
            query = query.filter(Run.agent_id == agent_id)
        
        # Filtrar por palavras-chave (busca simples por enquanto)
        if keywords:
            # Criar condições OR para cada palavra-chave
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(Run.question.ilike(f"%{keyword}%"))
            
            if keyword_conditions:
                query = query.filter(db.query(Run).filter(*keyword_conditions).exists())
        
        # Ordenar por data e limitar
        runs = query.order_by(desc(Run.created_at)).limit(limit * 2).all()  # Busca mais para filtrar
        
        # Filtrar manualmente por similaridade (implementação simples)
        similar_runs = []
        for run in runs:
            if is_question_similar(current_question, run.question, keywords):
                similar_runs.append({
                    "run_id": run.id,
                    "question": run.question,
                    "sql_query": run.sql_used,
                    "response": run.result_data,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "agent_id": run.agent_id,
                    "similarity_reason": f"Contém palavras-chave: {keywords}"
                })
                
                if len(similar_runs) >= limit:
                    break
        
        logger.info(f"[VALIDATION_HISTORY] Encontradas {len(similar_runs)} runs similares")
        return similar_runs
        
    except Exception as e:
        logger.error(f"[VALIDATION_HISTORY] Erro ao buscar runs similares: {e}")
        # Fallback para busca recente
        return get_recent_runs_for_comparison(db, current_run_id, user_id, agent_id, limit)

def extract_keywords_from_question(question: str) -> List[str]:
    """
    Extrai palavras-chave relevantes de uma pergunta
    
    Args:
        question: Pergunta para extrair palavras-chave
        
    Returns:
        Lista de palavras-chave
    """
    import re
    
    # Palavras irrelevantes (stop words)
    stop_words = {
        'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 'dos', 'das',
        'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com', 'sem', 'sob', 'sobre',
        'que', 'qual', 'quais', 'quando', 'onde', 'como', 'por que', 'porque',
        'e', 'ou', 'mas', 'se', 'então', 'é', 'são', 'foi', 'foram', 'será', 'serão',
        'tem', 'têm', 'teve', 'tiveram', 'terá', 'terão', 'há', 'houve', 'haverá'
    }
    
    # Limpar e dividir a pergunta
    words = re.findall(r'\b\w+\b', question.lower())
    
    # Filtrar palavras relevantes
    keywords = []
    for word in words:
        if len(word) > 2 and word not in stop_words:
            keywords.append(word)
    
    # Retornar palavras únicas
    return list(set(keywords))

def is_question_similar(question1: str, question2: str, keywords: List[str]) -> bool:
    """
    Verifica se duas perguntas são similares baseado em palavras-chave
    
    Args:
        question1: Primeira pergunta
        question2: Segunda pergunta
        keywords: Palavras-chave da primeira pergunta
        
    Returns:
        True se similares, False caso contrário
    """
    if not keywords:
        return False
    
    question2_lower = question2.lower()
    
    # Conta quantas palavras-chave aparecem na segunda pergunta
    matches = sum(1 for keyword in keywords if keyword in question2_lower)
    
    # Considera similar se pelo menos 30% das palavras-chave aparecem
    similarity_ratio = matches / len(keywords)
    return similarity_ratio >= 0.3

def get_run_by_id(db: Session, run_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca uma run específica por ID
    
    Args:
        db: Sessão do banco
        run_id: ID da run
        user_id: ID do usuário (para segurança)
        
    Returns:
        Dados da run ou None se não encontrada
    """
    try:
        from api.models import Run
        
        run = db.query(Run).filter(
            Run.id == run_id,
            Run.user_id == user_id
        ).first()
        
        if not run:
            logger.warning(f"[VALIDATION_HISTORY] Run {run_id} não encontrada para usuário {user_id}")
            return None
        
        return {
            "run_id": run.id,
            "question": run.question,
            "sql_query": run.sql_used,
            "response": run.result_data,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "agent_id": run.agent_id,
            "status": run.status
        }
        
    except Exception as e:
        logger.error(f"[VALIDATION_HISTORY] Erro ao buscar run {run_id}: {e}")
        return None
