"""
Nó para processamento de consultas SQL
"""
import time
import logging
import pandas as pd
from typing import Dict, Any, TypedDict

from agentgraph.agents.tools import is_greeting, detect_query_type, prepare_sql_context
from agentgraph.agents.sql_agent import SQLAgentManager
from agentgraph.utils.object_manager import get_object_manager

class QueryState(TypedDict):
    """Estado para processamento de consultas"""
    user_input: str
    selected_model: str
    response: str
    execution_time: float
    error: str
    intermediate_steps: list
    llama_instruction: str
    sql_result: dict

async def process_user_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó principal para processar consulta do usuário
    AGORA USA CELERY PARA TODAS AS QUERIES SQL

    Args:
        state: Estado atual com entrada do usuário

    Returns:
        Estado atualizado - dispara task Celery em vez de execução direta
    """
    start_time = time.time()
    user_input = state["user_input"]
    selected_model = state["selected_model"]

    logging.info(f"[QUERY] Processando: {user_input[:50]}...")

    try:
        # Verifica se é saudação
        if is_greeting(user_input):
            greeting_response = "Olá! Estou aqui para ajudar com suas consultas. Pergunte algo relacionado aos dados carregados no agente!"
            state.update({
                "response": greeting_response,
                "execution_time": time.time() - start_time,
                "error": None
            })
            return state
        
        # Recupera objetos necessários
        obj_manager = get_object_manager()
        
        # Recupera cache manager
        cache_id = state.get("cache_id")
        cache_manager = obj_manager.get_cache_manager(cache_id) if cache_id else None
        
        # CACHE TEMPORARIAMENTE DESATIVADO
        # Verifica cache se disponível
        if False:  # cache_manager:
            cached_response = cache_manager.get_cached_response(user_input)
            if cached_response:
                logging.info(f"[CACHE] Retornando resposta do cache")
                state.update({
                    "response": cached_response,
                    "execution_time": time.time() - start_time,
                    "error": None
                })
                return state
        
        # Converte amostra do banco para DataFrame
        db_sample_dict = state.get("db_sample_dict", {})
        if not db_sample_dict:
            raise ValueError("Amostra do banco não disponível")
        
        # Reconstrói DataFrame da amostra
        db_sample = pd.DataFrame(db_sample_dict.get("data", []))
        if db_sample.empty:
            raise ValueError("Dados de amostra vazios")
        
        # Detecta tipo de query e prepara contexto
        query_type = detect_query_type(user_input)
        state["query_type"] = query_type

        if query_type in ['sql_query', 'sql_query_graphic']:
            # Obtém sugestão de query e observações do Processing Agent (se disponível)
            suggested_query = state.get("suggested_query", "")
            query_observations = state.get("query_observations", "")

            # Obtém contexto histórico (se disponível)
            history_context = state.get("history_context", "")

            # LOG SEMPRE ATIVO PARA DEBUG (mesmo com histórico desativado)
            processing_enabled = state.get("processing_enabled", False)
            processing_status = "ATIVADO" if processing_enabled else "DESATIVADO"
            history_status = f"Histórico: {len(history_context)} chars" if history_context and history_context.strip() else "Sem histórico"

            # Verifica se histórico está habilitado globalmente
            import os
            history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"
            history_global_status = "HABILITADO" if history_enabled else "DESABILITADO"

            logging.info(f"[QUERY_NODE] ProcessingAgent: {processing_status} | Histórico Global: {history_global_status} | {history_status}")

            # Prepara contexto para envio direto ao agentSQL (agora com histórico)
            sql_context = prepare_sql_context(user_input, db_sample, suggested_query, query_observations, history_context)
            state["sql_context"] = sql_context

            logging.info(f"[QUERY_NODE] Tipo: {query_type} | Contexto preparado para AgentSQL")
        else:
            # Para tipos futuros (prediction)
            error_msg = f"Tipo de query '{query_type}' ainda não implementado."
            state.update({
                "error": error_msg,
                "response": error_msg,
                "execution_time": time.time() - start_time
            })
            return state
        
        # Recupera agente SQL
        agent_id = state.get("agent_id")
        if not agent_id:
            raise ValueError("ID do agente SQL não encontrado")

        sql_agent = obj_manager.get_sql_agent(agent_id)
        if not sql_agent:
            raise ValueError("Agente SQL não encontrado")

        # Verifica se precisa recriar o agente SQL para PostgreSQL/ClickHouse com configurações atuais
        connection_type = state.get("connection_type", "csv")
        if connection_type in ["postgresql", "clickhouse"]:
            single_table_mode = state.get("single_table_mode", False)
            selected_table = state.get("selected_table")
            selected_model = state.get("selected_model", "gpt-4o-mini")

            # Verifica se as configurações mudaram (incluindo TOP_K)
            current_single_mode = getattr(sql_agent, 'single_table_mode', False)
            current_table = getattr(sql_agent, 'selected_table', None)
            current_model = getattr(sql_agent, 'model_name', 'gpt-4o-mini')
            current_top_k = getattr(sql_agent, 'top_k', 10)
            new_top_k = state.get("top_k", 10)

            if (single_table_mode != current_single_mode or
                selected_table != current_table or
                selected_model != current_model or
                new_top_k != current_top_k):

                logging.info(f"[QUERY] Recriando agente SQL ({connection_type}) - Modo: {'único' if single_table_mode else 'multi'}, Tabela: {selected_table}, TOP_K: {current_top_k} → {new_top_k}")

                # Recria o agente com as novas configurações
                top_k = new_top_k
                sql_agent.recreate_agent(
                    single_table_mode=single_table_mode,
                    selected_table=selected_table,
                    new_model=selected_model,
                    top_k=top_k
                )

                # Atualiza no ObjectManager
                obj_manager.store_sql_agent(sql_agent, state.get("db_id"))

        # NOVA LÓGICA: VERIFICAR SE DEVE USAR CELERY
        use_celery = state.get("use_celery", False)

        # Log simples
        logging.info(f"[QUERY] use_celery: {use_celery}")

        if use_celery:
            # MODO CELERY: Preparar estado para dispatch
            logging.info(f"[QUERY] Modo Celery ativado - Preparando dispatch para Agent ID: {agent_id}")

            state.update({
                "ready_for_celery_dispatch": True,
                "celery_user_input": user_input,
                "celery_agent_id": agent_id,
                "execution_time": time.time() - start_time
            })

            logging.info(f"[QUERY] Estado preparado para dispatch Celery")
            return state

        # MODO TRADICIONAL: Execução direta (lógica original mantida)
        logging.info(f"[QUERY] Modo tradicional - Executando diretamente")

        # Executa query no agente SQL com contexto direto
        sql_result = await sql_agent.execute_query(state["sql_context"])

        # Log da resposta do agente SQL
        logging.info(f"[AGENT SQL] ===== RESPOSTA DO AGENTE SQL =====")
        logging.info(f"[AGENT SQL] Sucesso: {sql_result['success']}")
        logging.info(f"[AGENT SQL] Resposta completa:")
        logging.info(f"{sql_result.get('output', 'Sem resposta')}")
        if sql_result.get("sql_query"):
            logging.info(f"[AGENT SQL] Query SQL capturada: {sql_result['sql_query']}")
        logging.info(f"[AGENT SQL] ===== FIM DA RESPOSTA =====")

        if not sql_result["success"]:
            state.update({
                "error": sql_result["output"],
                "response": sql_result["output"],
                "sql_result": sql_result
            })
        else:
            # Captura query SQL do resultado do agente
            sql_query_captured = sql_result.get("sql_query")

            state.update({
                "response": sql_result["output"],
                "intermediate_steps": sql_result["intermediate_steps"],
                "sql_result": sql_result,
                "sql_query_extracted": sql_query_captured,  # ← Query SQL capturada
                "error": None
            })

            # Log apenas se não foi capturada (caso de erro)
            if not sql_query_captured:
                logging.warning("[QUERY] ⚠️ Nenhuma query SQL foi capturada pelo handler")

        # Armazena no cache se disponível
        if cache_manager and sql_result["success"]:
            cache_manager.cache_response(user_input, state["response"])

        state["execution_time"] = time.time() - start_time
        logging.info(f"[QUERY] Concluído em {state['execution_time']:.2f}s")

        
    except Exception as e:
        error_msg = f"Erro ao processar query: {e}"
        logging.error(f"[QUERY] {error_msg}")
        state.update({
            "error": error_msg,
            "response": error_msg,
            "execution_time": time.time() - start_time
        })
    
    return state

async def validate_query_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para validar entrada da consulta
    
    Args:
        state: Estado com entrada do usuário
        
    Returns:
        Estado atualizado com validação
    """
    user_input = state.get("user_input", "").strip()
    
    if not user_input:
        state.update({
            "error": "Entrada vazia",
            "response": "Por favor, digite uma pergunta.",
            "execution_time": 0.0
        })
        return state
    
    if len(user_input) > 1000:
        state.update({
            "error": "Entrada muito longa",
            "response": "Pergunta muito longa. Por favor, seja mais conciso.",
            "execution_time": 0.0
        })
        return state
    
    # Validação passou
    state["error"] = None
    logging.info(f"[VALIDATION] Entrada validada: {len(user_input)} caracteres")
    
    return state

async def prepare_query_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para preparar contexto da consulta
    
    Args:
        state: Estado atual
        
    Returns:
        Estado com contexto preparado
    """
    try:
        # Verifica se todos os componentes necessários estão disponíveis
        required_ids = ["agent_id", "engine_id", "cache_id"]
        missing_ids = [id_name for id_name in required_ids if not state.get(id_name)]
        
        if missing_ids:
            raise ValueError(f"IDs necessários não encontrados: {missing_ids}")
        
        obj_manager = get_object_manager()
        
        # Verifica se objetos existem
        for id_name in required_ids:
            obj_id = state[id_name]
            if id_name == "agent_id":
                obj = obj_manager.get_sql_agent(obj_id)
            elif id_name == "engine_id":
                obj = obj_manager.get_engine(obj_id)
            elif id_name == "cache_id":
                obj = obj_manager.get_cache_manager(obj_id)
            
            if obj is None:
                raise ValueError(f"Objeto não encontrado para {id_name}: {obj_id}")
        
        # Contexto preparado com sucesso
        state["context_ready"] = True
        logging.info("[CONTEXT] Contexto da consulta preparado")
        
    except Exception as e:
        error_msg = f"Erro ao preparar contexto: {e}"
        logging.error(f"[CONTEXT] {error_msg}")
        state.update({
            "error": error_msg,
            "context_ready": False
        })
    
    return state

def should_use_celery_routing(state: Dict[str, Any]) -> str:
    """
    Função de roteamento para decidir se deve usar Celery ou execução direta

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    # Verifica se Celery está habilitado
    use_celery = state.get("use_celery", False)

    # Verifica se está pronto para dispatch Celery
    ready_for_celery = state.get("ready_for_celery_dispatch", False)

    # Log simples
    logging.info(f"[ROUTING] use_celery: {use_celery}, ready: {ready_for_celery}")

    if use_celery and ready_for_celery:
        logging.info("[ROUTING] ✅ Redirecionando para Celery dispatch")
        return "celery_dispatch"
    else:
        logging.info(f"[ROUTING] ❌ Continuando fluxo tradicional (use_celery={use_celery}, ready={ready_for_celery})")
        # Verificar se deve gerar gráfico
        query_type = state.get("query_type", "")
        if query_type == "sql_query_graphic":
            return "graph_selection"
        elif state.get("advanced_mode", False):
            return "refine_response"
        else:
            return "format_response"  # Sempre formatar antes do cache
