"""
Nó para recuperação de histórico relevante
Executa dentro do Worker Celery com acesso ao PostgreSQL
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def history_retrieval_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para recuperar histórico relevante antes do processamento da query
    
    Args:
        state: Estado atual do LangGraph
        
    Returns:
        Estado atualizado com histórico relevante
    """
    try:
        # Verifica se o histórico está habilitado
        from agentgraph.services.history_service import get_history_service
        
        history_service = get_history_service()
        
        if not history_service.is_enabled():
            # Histórico desabilitado
            state["relevant_history"] = []
            state["has_history"] = False
            state["history_context"] = ""
            return state
        
        # Extrai informações do state
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")  # ATENÇÃO: aqui deve ser o agent_id da API
        user_input = state.get("user_input", "")
        chat_session_id = state.get("chat_session_id")
        run_id = state.get("run_id")

        # Fallbacks para garantir user_id/agent_id/chat_session_id
        try:
            from agentgraph.services.history_service import get_history_service
            _svc = get_history_service()
            if (not user_id or not agent_id or not chat_session_id) and run_id:
                row = _svc.db_session.execute(__import__("sqlalchemy").sql.text(
                    "SELECT user_id, agent_id, chat_session_id FROM runs WHERE id = :rid"
                ), {"rid": run_id}).fetchone()
                if row:
                    user_id = user_id or row[0]
                    agent_id = agent_id or row[1]
                    chat_session_id = chat_session_id or row[2]
                    # Contexto recuperado via run_id
            if (not user_id or not agent_id) and chat_session_id and not run_id:
                row2 = _svc.db_session.execute(__import__("sqlalchemy").sql.text(
                    "SELECT user_id, agent_id FROM chat_sessions WHERE id = :csid"
                ), {"csid": chat_session_id}).fetchone()
                if row2:
                    user_id = user_id or row2[0]
                    agent_id = agent_id or row2[1]
                    # Contexto recuperado via chat_session_id
            _svc.close()
        except Exception as e:
            logger.warning(f"[HISTORY_RETRIEVAL] Falha nos fallbacks de contexto: {e}")

        if not user_id or not agent_id or not user_input:
            logger.warning("[HISTORY_RETRIEVAL] Informações insuficientes para buscar histórico")
            state["relevant_history"] = []
            state["has_history"] = False
            state["history_context"] = ""
            return state
        
        # Busca histórico silenciosa
        
        # Busca histórico relevante (inclui busca semântica, mensagens recentes e última interação)
        relevant_messages = history_service.get_relevant_history(
            user_id=user_id,
            agent_id=agent_id,
            query_text=user_input,
            chat_session_id=chat_session_id,
            limit=15  # Máximo de mensagens
        )

        # Formata contexto para o AgentSQL / ProcessingAgent
        history_context = history_service.format_history_for_context(relevant_messages)

        # Atualiza state com histórico para uso a jusante
        state["relevant_history"] = relevant_messages
        state["has_history"] = len(relevant_messages) > 0
        state["history_context"] = history_context
        state["history_retrieved"] = True  # MARCA COMO RECUPERADO
        
        if relevant_messages:
            logger.info(f"[HISTORY_RETRIEVAL] ✅ {len(relevant_messages)} mensagens encontradas")
        else:
            logger.info("[HISTORY_RETRIEVAL] Nenhum histórico encontrado")
        
        # Cleanup
        history_service.close()
        
        return state
        
    except Exception as e:
        error_msg = f"Erro na recuperação de histórico: {e}"
        logger.error(f"[HISTORY_RETRIEVAL] ❌ {error_msg}")
        
        # Em caso de erro, continua sem histórico
        state["relevant_history"] = []
        state["has_history"] = False
        state["history_context"] = ""
        state["history_error"] = error_msg
        
        return state


def history_retrieval_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Versão síncrona do nó de recuperação de histórico
    Para compatibilidade com LangGraph que pode não suportar async
    
    Args:
        state: Estado atual do LangGraph
        
    Returns:
        Estado atualizado com histórico relevante
    """
    try:
        # Verifica se o histórico está habilitado
        from agentgraph.services.history_service import get_history_service
        
        history_service = get_history_service()
        
        if not history_service.is_enabled():
            # Histórico desabilitado
            state["relevant_history"] = []
            state["has_history"] = False
            state["history_context"] = ""
            return state
        
        # Extrai informações do state
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")  # pode ser UUID interno; corrigiremos abaixo
        user_input = state.get("user_input", "")
        chat_session_id = state.get("chat_session_id")
        run_id = state.get("run_id")

        # Se temos chat_session_id, usar os valores do banco (sempre corretos: user_id e agent_id inteiros)
        try:
            if chat_session_id:
                from sqlalchemy import text
                from agentgraph.services.history_service import get_history_service
                _svc = get_history_service()
                row = _svc.db_session.execute(text(
                    "SELECT user_id, agent_id FROM chat_sessions WHERE id = :csid"
                ), {"csid": chat_session_id}).fetchone()
                if row:
                    user_id, agent_id = row[0], row[1]
                    # Contexto via chat_session_id
                _svc.close()
            elif run_id:
                from sqlalchemy import text
                from agentgraph.services.history_service import get_history_service
                _svc = get_history_service()
                row = _svc.db_session.execute(text(
                    "SELECT user_id, agent_id, chat_session_id FROM runs WHERE id = :rid"
                ), {"rid": run_id}).fetchone()
                if row:
                    user_id = row[0]
                    agent_id = row[1]
                    chat_session_id = row[2]
                    state["chat_session_id"] = chat_session_id
                    # Contexto via run_id
                _svc.close()
        except Exception as e:
            logger.warning(f"[HISTORY_RETRIEVAL] Falha ao resolver contexto: {e}")

        if not user_id or not agent_id or not user_input:
            logger.warning("[HISTORY_RETRIEVAL] Informações insuficientes para buscar histórico")
            state["relevant_history"] = []
            state["has_history"] = False
            state["history_context"] = ""
            return state
        
        # Busca histórico silenciosa
        
        # Busca histórico relevante (inclui busca semântica, mensagens recentes e última interação)
        relevant_messages = history_service.get_relevant_history(
            user_id=user_id,
            agent_id=agent_id,
            query_text=user_input,
            chat_session_id=chat_session_id,
            limit=15  # Máximo de mensagens
        )

        # Formata contexto para o AgentSQL / ProcessingAgent
        history_context = history_service.format_history_for_context(relevant_messages)

        # Atualiza state com histórico para uso a jusante
        state["relevant_history"] = relevant_messages
        state["has_history"] = len(relevant_messages) > 0
        state["history_context"] = history_context
        state["history_retrieved"] = True  # MARCA COMO RECUPERADO
        
        if relevant_messages:
            logger.info(f"[HISTORY_RETRIEVAL] ✅ {len(relevant_messages)} mensagens encontradas")
        else:
            logger.info("[HISTORY_RETRIEVAL] Nenhum histórico encontrado")
        
        # Cleanup
        history_service.close()
        
        return state
        
    except Exception as e:
        error_msg = f"Erro na recuperação de histórico: {e}"
        logger.error(f"[HISTORY_RETRIEVAL] ❌ {error_msg}")
        
        # Em caso de erro, continua sem histórico
        state["relevant_history"] = []
        state["has_history"] = False
        state["history_context"] = ""
        state["history_error"] = error_msg
        
        return state


def should_retrieve_history(state: Dict[str, Any]) -> str:
    """
    Função de roteamento para decidir se deve buscar histórico
    
    Args:
        state: Estado atual do LangGraph
        
    Returns:
        Nome do próximo nó
    """
    try:
        import os
        
        # Verifica se histórico está habilitado
        history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"
        
        if not history_enabled:
            return "skip_history"

        # Verifica se tem informações necessárias
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")
        user_input = state.get("user_input", "")

        if not user_id or not agent_id or not user_input.strip():
            return "skip_history"

        # Verifica se é uma query que se beneficia de histórico
        # (evita histórico para queries muito simples)
        if len(user_input.strip()) < 10:
            return "skip_history"
        return "retrieve_history"
        
    except Exception as e:
        logger.error(f"[HISTORY_ROUTING] Erro no roteamento: {e}")
        return "skip_history"
