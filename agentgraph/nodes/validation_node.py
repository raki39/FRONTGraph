"""
Nó para validação de queries SQL e respostas do AgentSQL
"""
import logging
import time
from typing import Dict, Any, List, Optional

from agentgraph.agents.validation_agent import ValidationAgentManager
from agentgraph.utils.object_manager import get_object_manager
from agentgraph.services.validation_history import (
    get_recent_runs_for_comparison,
    get_similar_runs_for_comparison,
    get_run_by_id
)

logger = logging.getLogger(__name__)

async def query_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para validação de queries SQL e respostas
    
    Args:
        state: Estado do AgentGraph contendo:
            - validation_request: Dados da requisição de validação
            - run_data: Dados da run principal
            - compared_runs_data: Dados das runs para comparação (opcional)
            - validation_model: Modelo LLM para validação
    
    Returns:
        Estado atualizado com resultado da validação
    """
    start_time = time.time()
    logger.info("[VALIDATION_NODE] Iniciando validação")
    
    try:
        # Extrai dados do state
        validation_request = state.get("validation_request")
        if not validation_request:
            raise ValueError("validation_request não encontrado no state")
        
        run_data = state.get("run_data")
        if not run_data:
            raise ValueError("run_data não encontrado no state")
        
        # Valida dados obrigatórios
        question = run_data.get("question", "").strip()
        sql_query = run_data.get("sql_used", "").strip()
        response = run_data.get("result_data", "").strip()

        # Apenas question é obrigatória
        if not question:
            raise ValueError("Dados incompletos: question ausente")
        
        # Inicializa agente de validação
        validation_model = state.get("validation_model", "gpt-4o-mini")
        validation_agent = ValidationAgentManager(model=validation_model)
        
        logger.info(f"[VALIDATION_NODE] Tipo de validação: {validation_request['validation_type']}")
        
        # Executa validação baseada no tipo
        if validation_request["validation_type"] == "individual":
            result = await _execute_individual_validation(
                validation_agent, question, sql_query, response, validation_request
            )
        elif validation_request["validation_type"] == "comparative":
            # Busca runs para comparação automaticamente se não fornecidas
            compared_runs = state.get("compared_runs_data", [])

            if not compared_runs:
                compared_runs = await _get_runs_for_comparison(state)
                logger.info(f"[VALIDATION_NODE] Buscadas automaticamente {len(compared_runs)} runs para comparação")

            result = await _execute_comparative_validation(
                validation_agent, question, sql_query, response, compared_runs
            )
        else:
            raise ValueError(f"Tipo de validação inválido: {validation_request['validation_type']}")
        
        # Calcula tempo de processamento
        processing_time = time.time() - start_time
        
        # Atualiza state com resultado
        state.update({
            "validation_result": result,
            "validation_success": True,
            "validation_time": processing_time,
            "validation_error": None
        })
        
        logger.info(f"[VALIDATION_NODE] Validação concluída em {processing_time:.2f}s")
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error(f"[VALIDATION_NODE] Erro na validação: {error_msg}")
        
        state.update({
            "validation_result": None,
            "validation_success": False,
            "validation_error": error_msg,
            "validation_time": processing_time
        })
    
    return state

async def _get_runs_for_comparison(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Busca runs automaticamente para comparação

    Args:
        state: Estado contendo informações para busca

    Returns:
        Lista de runs para comparação
    """
    try:
        # Extrai informações necessárias
        db_session = state.get("db_session")
        user_id = state.get("user_id")
        agent_id = state.get("agent_id")
        run_id = state.get("run_id")

        # Configurações de busca
        comparison_limit = state.get("comparison_limit", 3)
        use_similarity = state.get("use_similarity_search", True)

        if not db_session or not user_id:
            logger.warning("[VALIDATION_NODE] db_session ou user_id não fornecidos para busca automática")
            return []

        run_data = state.get("run_data", {})
        current_question = run_data.get("question", "")

        # Busca runs similares ou recentes
        if use_similarity and current_question:
            logger.info("[VALIDATION_NODE] Buscando runs similares baseado na pergunta")
            compared_runs = get_similar_runs_for_comparison(
                db=db_session,
                current_run_id=run_id or 0,
                current_question=current_question,
                user_id=user_id,
                agent_id=agent_id,
                limit=comparison_limit
            )
        else:
            logger.info("[VALIDATION_NODE] Buscando runs recentes")
            compared_runs = get_recent_runs_for_comparison(
                db=db_session,
                current_run_id=run_id or 0,
                user_id=user_id,
                agent_id=agent_id,
                limit=comparison_limit
            )

        logger.info(f"[VALIDATION_NODE] Encontradas {len(compared_runs)} runs para comparação automática")
        return compared_runs

    except Exception as e:
        logger.error(f"[VALIDATION_NODE] Erro na busca automática de runs: {e}")
        return []

async def _execute_individual_validation(
    validation_agent: ValidationAgentManager,
    question: str,
    sql_query: str,
    response: str,
    validation_request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executa validação individual
    
    Args:
        validation_agent: Instância do agente de validação
        question: Pergunta do usuário
        sql_query: Query SQL gerada
        response: Resposta do AgentSQL
        validation_request: Dados da requisição
    
    Returns:
        Resultado da validação individual
    """
    logger.info("[VALIDATION_NODE] Executando validação individual")
    
    auto_improve = validation_request.get("auto_improve_question", False)
    
    result = await validation_agent.validate_individual(
        question=question,
        sql_query=sql_query,
        response=response,
        auto_improve=auto_improve
    )
    
    # Valida resultado
    if not isinstance(result, dict):
        raise ValueError("Resultado da validação individual inválido")
    
    # Garante que scores estão no range correto
    for score_field in ["question_clarity_score", "query_correctness_score", 
                       "response_accuracy_score", "overall_score"]:
        if score_field in result:
            score = result[score_field]
            if score is not None and (score < 0 or score > 1):
                logger.warning(f"Score {score_field} fora do range [0,1]: {score}")
                result[score_field] = max(0, min(1, score))
    
    return result

async def _execute_comparative_validation(
    validation_agent: ValidationAgentManager,
    question: str,
    sql_query: str,
    response: str,
    compared_runs: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Executa validação comparativa
    
    Args:
        validation_agent: Instância do agente de validação
        question: Pergunta atual
        sql_query: Query SQL atual
        response: Resposta atual
        compared_runs: Lista de runs para comparação
    
    Returns:
        Resultado da validação comparativa
    """
    logger.info(f"[VALIDATION_NODE] Executando validação comparativa com {len(compared_runs)} runs")
    
    if not compared_runs:
        raise ValueError("Nenhuma run fornecida para comparação")
    
    # Valida dados das runs de comparação
    for i, run in enumerate(compared_runs):
        if not all(key in run for key in ["question", "sql_query", "response"]):
            raise ValueError(f"Run {i} incompleta para comparação")

    current_run = {
        "question": question,
        "sql_query": sql_query,
        "response": response
    }

    result = await validation_agent.validate_comparative(
        current_run=current_run,
        compared_runs=compared_runs
    )
    
    # Valida resultado
    if not isinstance(result, dict):
        raise ValueError("Resultado da validação comparativa inválido")
    
    # Garante que consistency_score está no range correto
    if "consistency_score" in result:
        score = result["consistency_score"]
        if score is not None and (score < 0 or score > 1):
            logger.warning(f"Consistency score fora do range [0,1]: {score}")
            result["consistency_score"] = max(0, min(1, score))
    
    return result

def validate_validation_state(state: Dict[str, Any]) -> bool:
    """
    Valida se o state contém os dados necessários para validação

    Args:
        state: Estado do AgentGraph

    Returns:
        True se válido, False caso contrário
    """
    try:
        # Verifica validation_request
        validation_request = state.get("validation_request")
        if not validation_request:
            logger.error("validation_request ausente no state")
            return False

        required_fields = ["validation_type"]
        for field in required_fields:
            if field not in validation_request:
                logger.error(f"Campo obrigatório ausente em validation_request: {field}")
                return False

        # Verifica run_data
        run_data = state.get("run_data")
        if not run_data:
            logger.error("run_data ausente no state")
            return False

        required_run_fields = ["question", "sql_used", "result_data"]
        for field in required_run_fields:
            if not run_data.get(field):
                logger.error(f"Campo obrigatório ausente em run_data: {field}")
                return False

        # Validação específica para tipo comparativo
        if validation_request["validation_type"] == "comparative":
            compared_runs = state.get("compared_runs_data", [])
            if not compared_runs:
                logger.error("compared_runs_data ausente para validação comparativa")
                return False

            # Verifica se há pelo menos 1 run para comparação
            if len(compared_runs) < 1:
                logger.error("Validação comparativa requer pelo menos 1 run para comparação")
                return False

            # Valida estrutura dos runs de comparação
            for i, run in enumerate(compared_runs):
                required_compare_fields = ["question", "sql_query", "response"]
                for field in required_compare_fields:
                    if not run.get(field):
                        logger.error(f"Campo obrigatório ausente em compared_runs_data[{i}]: {field}")
                        return False

        return True

    except Exception as e:
        logger.error(f"Erro na validação do state: {e}")
        return False

# Função de roteamento para integração com o grafo principal
def should_execute_validation(state: Dict[str, Any]) -> str:
    """
    Determina se deve executar validação baseado no state
    
    Args:
        state: Estado atual
    
    Returns:
        Nome do próximo nó
    """
    if validate_validation_state(state):
        return "query_validation"
    else:
        return "validation_error"
