"""
Nó para gerenciamento de sistema e configurações
"""
import logging
from typing import Dict, Any, TypedDict

from agentgraph.agents.sql_agent import SQLAgentManager
from agentgraph.utils.object_manager import get_object_manager


class SystemManagementState(TypedDict):
    """Estado para operações de gerenciamento do sistema"""
    success: bool
    message: str
    enabled: bool
    top_k: int
    agent_id: str
    db_id: str
    cache_id: str


async def toggle_advanced_mode_node(state: SystemManagementState) -> SystemManagementState:
    """
    Nó para alternar modo avançado
    
    Args:
        state: Estado contendo configuração do modo avançado
        
    Returns:
        Estado atualizado
    """
    try:
        enabled = state.get("enabled", False)
        message = "Modo avançado ativado." if enabled else "Modo avançado desativado."
        logging.info(f"[MODO AVANÇADO] {'Ativado' if enabled else 'Desativado'}")
        
        state.update({
            "success": True,
            "message": message
        })
        
    except Exception as e:
        error_msg = f"Erro ao alternar modo avançado: {e}"
        logging.error(error_msg)
        state.update({
            "success": False,
            "message": error_msg
        })
    
    return state


async def force_recreate_sql_agent_node(state: SystemManagementState) -> SystemManagementState:
    """
    Nó para forçar recriação do agente SQL com novo TOP_K
    
    Args:
        state: Estado contendo configurações do agente
        
    Returns:
        Estado atualizado
    """
    try:
        top_k = state.get("top_k", 10)
        agent_id = state.get("agent_id")
        
        if not agent_id:
            raise ValueError("ID do agente não fornecido")
        
        logging.info(f"[FORCE_RECREATE] Forçando recriação do agente SQL com TOP_K={top_k}")
        
        obj_manager = get_object_manager()
        
        # Recupera banco de dados atual
        db_id = obj_manager.get_db_id_for_agent(agent_id)
        if not db_id:
            raise ValueError("Banco de dados não encontrado")
        
        db = obj_manager.get_database(db_id)
        if not db:
            raise ValueError("Objeto de banco de dados não encontrado")
        
        # Recupera agente atual para manter configurações
        current_agent = obj_manager.get_sql_agent(agent_id)
        if current_agent:
            model_name = current_agent.model_name
            single_table_mode = current_agent.single_table_mode
            selected_table = current_agent.selected_table
        else:
            model_name = "gpt-4o-mini"
            single_table_mode = False
            selected_table = None
        
        # Cria novo agente SQL com TOP_K atualizado
        new_sql_agent = SQLAgentManager(
            db=db,
            model_name=model_name,
            single_table_mode=single_table_mode,
            selected_table=selected_table,
            top_k=top_k
        )
        
        # Atualiza no ObjectManager
        new_agent_id = obj_manager.store_sql_agent(new_sql_agent, db_id)
        
        logging.info(f"[FORCE_RECREATE] Agente SQL recriado com sucesso - Modelo: {model_name}, TOP_K: {top_k}")
        
        state.update({
            "success": True,
            "message": f"Agente SQL recriado com TOP_K={top_k}",
            "agent_id": new_agent_id,
            "top_k": top_k,
            "model": model_name
        })
        
    except Exception as e:
        error_msg = f"Erro ao forçar recriação do agente SQL: {e}"
        logging.error(error_msg)
        state.update({
            "success": False,
            "message": error_msg
        })
    
    return state


async def get_system_info_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para obter informações detalhadas do sistema
    
    Args:
        state: Estado atual do sistema
        
    Returns:
        Estado com informações do sistema
    """
    try:
        from agentgraph.utils.config import get_active_csv_path, SQL_DB_PATH

        obj_manager = get_object_manager()
        
        system_info = {
            "csv_active": get_active_csv_path(),
            "database_path": SQL_DB_PATH,
            "agent_info": None,
            "cache_stats": None,
            "object_manager_stats": obj_manager.get_stats() if hasattr(obj_manager, 'get_stats') else {}
        }
        
        # Informações do agente SQL
        agent_id = state.get("agent_id")
        if agent_id:
            sql_agent = obj_manager.get_sql_agent(agent_id)
            if sql_agent and hasattr(sql_agent, 'get_agent_info'):
                system_info["agent_info"] = sql_agent.get_agent_info()
        
        # Estatísticas do cache
        cache_id = state.get("cache_id")
        if cache_id:
            cache_manager = obj_manager.get_cache_manager(cache_id)
            if cache_manager:
                system_info["cache_stats"] = {
                    "cached_queries": len(getattr(cache_manager, 'query_cache', {})),
                    "history_entries": len(getattr(cache_manager, 'history_log', [])),
                    "recent_history_size": len(getattr(cache_manager, 'recent_history', []))
                }
        
        state["system_info"] = system_info
        logging.info("[SYSTEM_INFO] Informações do sistema coletadas")
        
    except Exception as e:
        logging.error(f"[SYSTEM_INFO] Erro ao coletar informações: {e}")
        state["system_info"] = {
            "error": str(e),
            "csv_active": None,
            "database_path": None,
            "agent_info": None,
            "cache_stats": None
        }
    
    return state


async def validate_system_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para validar o estado completo do sistema
    
    Args:
        state: Estado atual do sistema
        
    Returns:
        Estado com informações de validação
    """
    validation_results = {
        "database_valid": False,
        "agent_valid": False,
        "cache_valid": False,
        "object_manager_valid": False,
        "overall_valid": False
    }
    
    try:
        obj_manager = get_object_manager()
        
        # Valida banco de dados
        engine_id = state.get("engine_id")
        if engine_id:
            engine = obj_manager.get_engine(engine_id)
            if engine:
                try:
                    # Testa conexão básica
                    with engine.connect() as conn:
                        conn.execute("SELECT 1")
                    validation_results["database_valid"] = True
                except Exception as e:
                    logging.warning(f"Validação do banco falhou: {e}")
        
        # Valida agente SQL
        agent_id = state.get("agent_id")
        if agent_id:
            sql_agent = obj_manager.get_sql_agent(agent_id)
            if sql_agent and hasattr(sql_agent, 'validate_agent'):
                validation_results["agent_valid"] = sql_agent.validate_agent()
            elif sql_agent:
                validation_results["agent_valid"] = True  # Existe mas não tem método de validação
        
        # Valida cache
        cache_id = state.get("cache_id")
        if cache_id:
            cache_manager = obj_manager.get_cache_manager(cache_id)
            validation_results["cache_valid"] = cache_manager is not None
        
        # Valida object manager
        validation_results["object_manager_valid"] = obj_manager is not None
        
        # Validação geral
        validation_results["overall_valid"] = all([
            validation_results["database_valid"],
            validation_results["agent_valid"],
            validation_results["cache_valid"],
            validation_results["object_manager_valid"]
        ])
        
        state["validation"] = validation_results
        logging.info(f"[VALIDATION] Sistema válido: {validation_results['overall_valid']}")
        
    except Exception as e:
        logging.error(f"[VALIDATION] Erro na validação: {e}")
        validation_results["error"] = str(e)
        state["validation"] = validation_results
    
    return state
