"""
Nó para gerenciamento de cache e histórico
"""
import logging
from typing import Dict, Any, List

from agentgraph.utils.object_manager import get_object_manager

async def update_history_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para atualizar histórico e logs
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado
    """
    try:
        obj_manager = get_object_manager()
        cache_id = state.get("cache_id")
        
        if not cache_id:
            logging.warning("[HISTORY] ID do cache não encontrado")
            return state
        
        cache_manager = obj_manager.get_cache_manager(cache_id)
        if not cache_manager:
            logging.warning("[HISTORY] Cache manager não encontrado")
            return state
        
        # Adiciona ao histórico de logs
        history_entry = {
            "Modelo AgentSQL": state.get("selected_model", ""),
            "Pergunta": state.get("user_input", ""),
            "Resposta": state.get("response", ""),
            "Tempo de Resposta (s)": round(state.get("execution_time", 0.0), 2),
            "Modo Avançado": state.get("advanced_mode", False),
            "Refinado": state.get("refined", False),
            "Erro": state.get("error"),
            "Tipo de Query": state.get("query_type", "sql_query")
        }
        cache_manager.add_to_history(history_entry)
        
        # Atualiza histórico recente
        cache_manager.update_recent_history(
            state.get("user_input", ""), 
            state.get("response", "")
        )
        
        state["history_updated"] = True
        logging.info("[HISTORY] Histórico atualizado")
        
    except Exception as e:
        error_msg = f"Erro ao atualizar histórico: {e}"
        logging.error(f"[HISTORY] {error_msg}")
        state["history_error"] = error_msg
    
    return state

async def cache_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para armazenar resposta no cache

    CACHE COMPLETAMENTE DESABILITADO - Não armazena nada

    Args:
        state: Estado com resposta a ser cacheada

    Returns:
        Estado atualizado
    """
    try:
        # CACHE DESABILITADO: Não armazena respostas
        logging.info(f"[CACHE] ❌ CACHE DESABILITADO - Não armazenando resposta")
        state["cached"] = False

    except Exception as e:
        error_msg = f"Erro ao cachear resposta: {e}"
        logging.error(f"[CACHE] {error_msg}")
        state["cache_error"] = error_msg

    return state

async def get_cache_stats_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para obter estatísticas do cache
    
    Args:
        state: Estado atual
        
    Returns:
        Estado com estatísticas do cache
    """
    try:
        obj_manager = get_object_manager()
        cache_id = state.get("cache_id")
        
        if not cache_id:
            state["cache_stats"] = {}
            return state
        
        cache_manager = obj_manager.get_cache_manager(cache_id)
        if not cache_manager:
            state["cache_stats"] = {}
            return state
        
        # Coleta estatísticas
        cache_stats = {
            "cached_queries": len(cache_manager.query_cache),
            "history_entries": len(cache_manager.history_log),
            "recent_history_size": len(cache_manager.recent_history),
            "cache_hit_rate": 0.0  # Seria calculado com mais dados históricos
        }
        
        # Calcula taxa de acerto aproximada
        if cache_stats["history_entries"] > 0:
            # Estimativa simples baseada em queries repetidas
            unique_queries = len(set(entry.get("Pergunta", "") for entry in cache_manager.history_log))
            if unique_queries > 0:
                cache_stats["cache_hit_rate"] = max(0, 1 - (unique_queries / cache_stats["history_entries"]))
        
        state["cache_stats"] = cache_stats
        logging.info(f"[CACHE] Estatísticas coletadas: {cache_stats}")
        
    except Exception as e:
        error_msg = f"Erro ao obter estatísticas do cache: {e}"
        logging.error(f"[CACHE] {error_msg}")
        state["cache_stats"] = {}
    
    return state

async def clear_cache_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para limpar cache
    
    Args:
        state: Estado atual
        
    Returns:
        Estado atualizado
    """
    try:
        obj_manager = get_object_manager()
        cache_id = state.get("cache_id")
        
        if not cache_id:
            state["cache_cleared"] = False
            return state
        
        cache_manager = obj_manager.get_cache_manager(cache_id)
        if not cache_manager:
            state["cache_cleared"] = False
            return state
        
        # Limpa cache
        cache_manager.clear_cache()
        state["cache_cleared"] = True
        
        logging.info("[CACHE] Cache limpo")
        
    except Exception as e:
        error_msg = f"Erro ao limpar cache: {e}"
        logging.error(f"[CACHE] {error_msg}")
        state["cache_cleared"] = False
        state["cache_error"] = error_msg
    
    return state

async def check_cache_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para verificar se existe resposta em cache

    CACHE COMPLETAMENTE DESABILITADO - Sempre retorna cache_hit=False

    Args:
        state: Estado com consulta do usuário

    Returns:
        Estado com resultado da verificação de cache
    """
    try:
        # CACHE DESABILITADO: Sempre retorna False para forçar nova execução
        logging.info(f"[CACHE] ❌ CACHE DESABILITADO - Forçando nova execução")
        state["cache_hit"] = False
        
    except Exception as e:
        error_msg = f"Erro ao verificar cache: {e}"
        logging.error(f"[CACHE] {error_msg}")
        state["cache_hit"] = False
        state["cache_error"] = error_msg
    
    return state


async def get_history_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para obter histórico de conversas

    Args:
        state: Estado atual do sistema

    Returns:
        Estado com histórico
    """
    try:
        obj_manager = get_object_manager()
        cache_id = state.get("cache_id")

        if not cache_id:
            logging.warning("[HISTORY] ID do cache não encontrado")
            state["history"] = []
            return state

        cache_manager = obj_manager.get_cache_manager(cache_id)
        if not cache_manager:
            logging.warning("[HISTORY] Cache manager não encontrado")
            state["history"] = []
            return state

        # Obtém histórico
        history = getattr(cache_manager, 'history_log', [])
        state["history"] = history

        logging.info(f"[HISTORY] Histórico obtido: {len(history)} entradas")

    except Exception as e:
        error_msg = f"Erro ao obter histórico: {e}"
        logging.error(f"[HISTORY] {error_msg}")
        state["history"] = []
        state["error"] = error_msg

    return state


async def clear_cache_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para limpar cache do sistema

    Args:
        state: Estado atual do sistema

    Returns:
        Estado atualizado
    """
    try:
        obj_manager = get_object_manager()
        cache_id = state.get("cache_id")

        if not cache_id:
            logging.warning("[CACHE] ID do cache não encontrado")
            state.update({
                "success": False,
                "message": "ID do cache não encontrado"
            })
            return state

        cache_manager = obj_manager.get_cache_manager(cache_id)
        if not cache_manager:
            logging.warning("[CACHE] Cache manager não encontrado")
            state.update({
                "success": False,
                "message": "Cache manager não encontrado"
            })
            return state

        # Limpa cache
        if hasattr(cache_manager, 'clear_cache'):
            cache_manager.clear_cache()
        else:
            # Limpa manualmente se não tem método
            if hasattr(cache_manager, 'query_cache'):
                cache_manager.query_cache.clear()
            if hasattr(cache_manager, 'history_log'):
                cache_manager.history_log.clear()
            if hasattr(cache_manager, 'recent_history'):
                cache_manager.recent_history.clear()

        state.update({
            "success": True,
            "message": "Cache limpo com sucesso"
        })

        logging.info("[CACHE] Cache limpo com sucesso")

    except Exception as e:
        error_msg = f"Erro ao limpar cache: {e}"
        logging.error(f"[CACHE] {error_msg}")
        state.update({
            "success": False,
            "message": error_msg
        })

    return state
