"""
Nó para captura e armazenamento de histórico
Executa dentro do Worker Celery após o processamento da query
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

async def history_capture_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para capturar e armazenar a conversa no histórico
    
    Args:
        state: Estado atual do LangGraph com resposta processada
        
    Returns:
        Estado atualizado com informações de captura
    """
    try:
        # Verifica se o histórico está habilitado
        from agentgraph.services.history_service import get_history_service
        
        history_service = get_history_service()
        
        if not history_service.is_enabled():
            # Histórico desabilitado
            state["history_captured"] = False
            return state
        
        # Extrai informações do state
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")
        user_input = state.get("user_input", "")
        response = state.get("response", "")
        sql_query = state.get("sql_query_extracted") or state.get("sql_query")
        run_id = state.get("run_id")
        
        if not user_id or not agent_id or not user_input:
            logger.warning("[HISTORY_CAPTURE] Informações insuficientes para capturar histórico")
            state["history_captured"] = False
            return state
        
        # Captura iniciada
        
        # Obtém ou cria sessão de chat
        chat_session_id = state.get("chat_session_id")
        if not chat_session_id:
            # Cria nova sessão baseada na pergunta
            title = user_input[:50] + "..." if len(user_input) > 50 else user_input
            chat_session_id = history_service.get_or_create_chat_session(
                user_id=user_id,
                agent_id=agent_id,
                title=title
            )
            state["chat_session_id"] = chat_session_id
        
        if not chat_session_id:
            logger.error("[HISTORY_CAPTURE] Falha ao obter/criar sessão de chat")
            state["history_captured"] = False
            return state
        
        # Salva mensagens no histórico
        success = await _save_conversation_to_history(
            history_service=history_service,
            chat_session_id=chat_session_id,
            user_input=user_input,
            response=response,
            sql_query=sql_query,
            run_id=run_id
        )
        
        if success:
            # Dispara task assíncrona para gerar embeddings
            await _dispatch_embedding_generation(
                user_input=user_input,
                response=response,
                chat_session_id=chat_session_id
            )
            
            logger.info("[HISTORY_CAPTURE] ✅ Capturada")
            state["history_captured"] = True
        else:
            logger.error("[HISTORY_CAPTURE] ❌ Falha")
            state["history_captured"] = False
        
        # Cleanup
        history_service.close()
        
        return state
        
    except Exception as e:
        error_msg = f"Erro na captura de histórico: {e}"
        logger.error(f"[HISTORY_CAPTURE] ❌ {error_msg}")
        
        state["history_captured"] = False
        state["history_capture_error"] = error_msg
        
        return state


def history_capture_node_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Versão síncrona do nó de captura de histórico
    Para compatibilidade com LangGraph que pode não suportar async
    
    Args:
        state: Estado atual do LangGraph com resposta processada
        
    Returns:
        Estado atualizado com informações de captura
    """
    try:
        # Verifica se o histórico está habilitado
        from agentgraph.services.history_service import get_history_service
        
        history_service = get_history_service()
        
        if not history_service.is_enabled():
            # Histórico desabilitado
            state["history_captured"] = False
            return state
        
        # Extrai informações do state
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")
        user_input = state.get("user_input", "")
        response = state.get("response", "")
        sql_query = state.get("sql_query_extracted") or state.get("sql_query")
        run_id = state.get("run_id")

        # FALLBACK: Se user_id não está no estado, obter do banco de dados
        if not user_id:
            try:
                # Obter user_id da run atual usando run_id
                if run_id:
                    from sqlalchemy import text
                    result = history_service.db_session.execute(text("""
                        SELECT user_id FROM runs WHERE id = :run_id
                    """), {"run_id": run_id})

                    row = result.fetchone()
                    if row:
                        user_id = row[0]
                        logger.info(f"[HISTORY_CAPTURE] FALLBACK - user_id obtido do banco via run_id: {user_id}")
                    else:
                        logger.warning(f"[HISTORY_CAPTURE] Run {run_id} não encontrada no banco")

                # Se ainda não tem user_id, tentar obter da task Celery
                if not user_id:
                    from celery import current_task
                    if current_task and hasattr(current_task, 'request') and current_task.request:
                        task_kwargs = getattr(current_task.request, 'kwargs', {})
                        meta = task_kwargs.get('meta', {})
                        user_id = meta.get('user_id')
                        logger.info(f"[HISTORY_CAPTURE] FALLBACK - user_id obtido da task: {user_id}")

            except Exception as e:
                logger.warning(f"[HISTORY_CAPTURE] Erro ao obter user_id: {e}")

        # DEBUG: Log dos valores recebidos e campos disponíveis
        logger.info(f"[HISTORY_CAPTURE] DEBUG - user_id: {user_id}, agent_id: {agent_id}, user_input: {bool(user_input)}")
        logger.info(f"[HISTORY_CAPTURE] DEBUG - Campos disponíveis no estado: {list(state.keys())}")

        if not user_id or not agent_id or not user_input:
            logger.warning(f"[HISTORY_CAPTURE] Informações insuficientes - user_id: {user_id}, agent_id: {agent_id}, user_input: {bool(user_input)}")
            state["history_captured"] = False
            return state
        
        # Captura iniciada
        
        # Obtém ou cria sessão de chat
        chat_session_id = state.get("chat_session_id")
        if not chat_session_id:
            # Cria nova sessão baseada na pergunta
            title = user_input[:50] + "..." if len(user_input) > 50 else user_input
            chat_session_id = history_service.get_or_create_chat_session(
                user_id=user_id,
                agent_id=agent_id,
                title=title
            )
            state["chat_session_id"] = chat_session_id
        
        if not chat_session_id:
            logger.error("[HISTORY_CAPTURE] Falha ao obter/criar sessão de chat")
            state["history_captured"] = False
            return state
        
        # Salva mensagens no histórico
        success = _save_conversation_to_history_sync(
            history_service=history_service,
            chat_session_id=chat_session_id,
            user_input=user_input,
            response=response,
            sql_query=sql_query,
            run_id=run_id
        )
        
        if success:
            # Dispara task assíncrona para gerar embeddings
            _dispatch_embedding_generation_sync(
                user_input=user_input,
                response=response,
                chat_session_id=chat_session_id
            )
            
            logger.info("[HISTORY_CAPTURE] ✅ Capturada")
            state["history_captured"] = True
        else:
            logger.error("[HISTORY_CAPTURE] ❌ Falha")
            state["history_captured"] = False
        
        # Cleanup
        history_service.close()
        
        return state
        
    except Exception as e:
        error_msg = f"Erro na captura de histórico: {e}"
        logger.error(f"[HISTORY_CAPTURE] ❌ {error_msg}")
        
        state["history_captured"] = False
        state["history_capture_error"] = error_msg
        
        return state


async def _save_conversation_to_history(history_service, chat_session_id: int, 
                                      user_input: str, response: str, 
                                      sql_query: str = None, run_id: int = None) -> bool:
    """Salva conversa no histórico (versão async)"""
    try:
        from sqlalchemy import text
        
        # Obtém próximo sequence_order
        result = history_service.db_session.execute(text("""
            SELECT COALESCE(MAX(sequence_order), 0) + 1 
            FROM messages 
            WHERE chat_session_id = :session_id
        """), {"session_id": chat_session_id})
        
        next_sequence = result.fetchone()[0]
        
        # Salva mensagem do usuário
        user_message_result = history_service.db_session.execute(text("""
            INSERT INTO messages (chat_session_id, run_id, role, content, sql_query, sequence_order, created_at)
            VALUES (:session_id, :run_id, 'user', :content, NULL, :sequence, NOW())
            RETURNING id
        """), {
            "session_id": chat_session_id,
            "run_id": run_id,
            "content": user_input,
            "sequence": next_sequence
        })
        
        user_message_id = user_message_result.fetchone()[0]
        
        # Salva resposta do assistente
        assistant_message_result = history_service.db_session.execute(text("""
            INSERT INTO messages (chat_session_id, run_id, role, content, sql_query, sequence_order, created_at)
            VALUES (:session_id, :run_id, 'assistant', :content, :sql_query, :sequence, NOW())
            RETURNING id
        """), {
            "session_id": chat_session_id,
            "run_id": run_id,
            "content": response,
            "sql_query": sql_query,
            "sequence": next_sequence + 1
        })
        
        assistant_message_id = assistant_message_result.fetchone()[0]
        
        # Atualiza estatísticas da sessão
        history_service.db_session.execute(text("""
            UPDATE chat_sessions 
            SET last_activity = NOW(), 
                total_messages = total_messages + 2
            WHERE id = :session_id
        """), {"session_id": chat_session_id})
        
        history_service.db_session.commit()
        
        # Mensagens salvas
        return True
        
    except Exception as e:
        logger.error(f"[HISTORY_CAPTURE] Erro ao salvar conversa: {e}")
        history_service.db_session.rollback()
        return False


def _save_conversation_to_history_sync(history_service, chat_session_id: int, 
                                     user_input: str, response: str, 
                                     sql_query: str = None, run_id: int = None) -> bool:
    """Salva conversa no histórico (versão sync)"""
    try:
        from sqlalchemy import text
        
        # Obtém próximo sequence_order
        result = history_service.db_session.execute(text("""
            SELECT COALESCE(MAX(sequence_order), 0) + 1 
            FROM messages 
            WHERE chat_session_id = :session_id
        """), {"session_id": chat_session_id})
        
        next_sequence = result.fetchone()[0]
        
        # Salva mensagem do usuário
        user_message_result = history_service.db_session.execute(text("""
            INSERT INTO messages (chat_session_id, run_id, role, content, sql_query, sequence_order, created_at)
            VALUES (:session_id, :run_id, 'user', :content, NULL, :sequence, NOW())
            RETURNING id
        """), {
            "session_id": chat_session_id,
            "run_id": run_id,
            "content": user_input,
            "sequence": next_sequence
        })
        
        user_message_id = user_message_result.fetchone()[0]
        
        # Salva resposta do assistente
        assistant_message_result = history_service.db_session.execute(text("""
            INSERT INTO messages (chat_session_id, run_id, role, content, sql_query, sequence_order, created_at)
            VALUES (:session_id, :run_id, 'assistant', :content, :sql_query, :sequence, NOW())
            RETURNING id
        """), {
            "session_id": chat_session_id,
            "run_id": run_id,
            "content": response,
            "sql_query": sql_query,
            "sequence": next_sequence + 1
        })
        
        assistant_message_id = assistant_message_result.fetchone()[0]
        
        # Atualiza estatísticas da sessão
        history_service.db_session.execute(text("""
            UPDATE chat_sessions 
            SET last_activity = NOW(), 
                total_messages = total_messages + 2
            WHERE id = :session_id
        """), {"session_id": chat_session_id})
        
        history_service.db_session.commit()
        
        # Mensagens salvas
        return True
        
    except Exception as e:
        logger.error(f"[HISTORY_CAPTURE] Erro ao salvar conversa: {e}")
        history_service.db_session.rollback()
        return False


async def _dispatch_embedding_generation(user_input: str, response: str, chat_session_id: int):
    """Dispara task assíncrona para gerar embeddings"""
    try:
        # Importa task de embedding
        from agentgraph.tasks import generate_message_embedding_task
        
        # Dispara task para mensagem do usuário
        generate_message_embedding_task.delay(user_input, chat_session_id, "user")
        
        logger.info("[HISTORY_CAPTURE] Task de embedding disparada para mensagem do usuário")
        
    except Exception as e:
        logger.error(f"[HISTORY_CAPTURE] Erro ao disparar task de embedding: {e}")


def _dispatch_embedding_generation_sync(user_input: str, response: str, chat_session_id: int):
    """Dispara task assíncrona para gerar embeddings (versão sync)"""
    try:
        # Importa task de embedding
        from agentgraph.tasks import generate_message_embedding_task
        
        # Dispara task para mensagem do usuário
        generate_message_embedding_task.delay(user_input, chat_session_id, "user")
        
        logger.info("[HISTORY_CAPTURE] Task de embedding disparada para mensagem do usuário")
        
    except Exception as e:
        logger.error(f"[HISTORY_CAPTURE] Erro ao disparar task de embedding: {e}")


def should_capture_history(state: Dict[str, Any]) -> str:
    """
    Função de roteamento para decidir se deve capturar histórico
    
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
            return "skip_capture"

        # Verifica se tem resposta para capturar
        response = state.get("response", "")
        user_input = state.get("user_input", "")

        if not response.strip() or not user_input.strip():
            return "skip_capture"

        # Verifica se houve erro
        error = state.get("error")
        if error:
            return "skip_capture"
        
        logger.info("[HISTORY_CAPTURE_ROUTING] Condições atendidas - capturando histórico")
        return "capture_history"
        
    except Exception as e:
        logger.error(f"[HISTORY_CAPTURE_ROUTING] Erro no roteamento: {e}")
        return "skip_capture"
