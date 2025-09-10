"""
Nó para seleção do tipo de conexão (csv ou postgresql)
"""
import logging
from typing import Dict, Any
from agentgraph.utils.validation import validate_connection_state


async def connection_selection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para determinar o tipo de conexão baseado na entrada do usuário
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com tipo de conexão definido
    """
    try:
        # Seleção de conexão iniciada
        
        # Verifica se o tipo de conexão já foi definido
        connection_type = state.get("connection_type")
        
        if not connection_type:
            # Se não foi definido, assume csv como padrão (compatibilidade)
            connection_type = "csv"
            # Usando csv como padrão
        
        # Valida tipo de conexão
        valid_types = ["csv", "postgresql"]
        if connection_type.upper() not in [t.upper() for t in valid_types]:
            error_msg = f"Tipo de conexão inválido: {connection_type}. Tipos válidos: {valid_types}"
            logging.error(f"[CONNECTION_SELECTION] {error_msg}")
            state.update({
                "connection_type": "csv",  # Fallback para csv
                "connection_error": error_msg,
                "connection_success": False
            })
            return state
        
        # Atualiza estado com tipo de conexão validado
        state.update({
            "connection_type": connection_type,
            "connection_error": None,
            "connection_success": True
        })
        
        logging.info(f"[CONNECTION_SELECTION] Selecionado: {connection_type}")
        
        return state
        
    except Exception as e:
        error_msg = f"Erro na seleção de tipo de conexão: {e}"
        logging.error(f"[CONNECTION_SELECTION] {error_msg}")
        
        # Fallback para csv em caso de erro
        state.update({
            "connection_type": "csv",
            "connection_error": error_msg,
            "connection_success": False
        })
        
        return state


def route_by_connection_type(state: Dict[str, Any]) -> str:
    """
    Função de roteamento baseada no tipo de conexão

    Args:
        state: Estado atual do agente

    Returns:
        Nome do próximo nó baseado no tipo de conexão
    """
    connection_type = state.get("connection_type", "csv")
    file_path = state.get("file_path")
    db_id = state.get("db_id")
    engine_id = state.get("engine_id")

    # Roteamento de conexão

    # Se já tem conexão estabelecida, pula para get_db_sample
    # Verifica se o sistema já foi inicializado
    from agentgraph.utils.object_manager import get_object_manager
    obj_manager = get_object_manager()

    # Verifica se há agentes SQL já criados (indicando sistema inicializado)
    stats = obj_manager.get_stats()
    has_sql_agents = stats.get("sql_agents", 0) > 0
    has_databases = stats.get("databases", 0) > 0

    if has_sql_agents and has_databases:
        return "get_db_sample"

    # Fallback: verifica IDs específicos
    if db_id and engine_id:
        return "get_db_sample"

    if connection_type.upper() == "POSTGRESQL":
        return "postgresql_connection"
    elif file_path:
        # Há arquivo csv para processar
        return "csv_processing"
    else:
        # Usar banco existente
        return "load_database"


async def validate_connection_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para validar entrada de conexão antes do processamento
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com validação
    """
    try:
        logging.info("[CONNECTION_VALIDATION] Validando entrada de conexão")
        
        connection_type = state.get("connection_type", "csv")
        
        # Usa validação centralizada
        is_valid, validation_error = validate_connection_state(state)

        if not is_valid:
            logging.error(f"[CONNECTION_VALIDATION] {validation_error}")
            state.update({
                "connection_error": validation_error,
                "connection_success": False
            })
            return state
            
        logging.info(f"[CONNECTION_VALIDATION] Validação de conexão {connection_type} bem-sucedida")
        
        # Validação bem-sucedida
        state.update({
            "connection_error": None,
            "connection_success": True
        })
        
        logging.info("[CONNECTION_VALIDATION] Validação de conexão concluída com sucesso")
        return state
        
    except Exception as e:
        error_msg = f"Erro na validação de conexão: {e}"
        logging.error(f"[CONNECTION_VALIDATION] {error_msg}")
        
        state.update({
            "connection_error": error_msg,
            "connection_success": False
        })
        
        return state
