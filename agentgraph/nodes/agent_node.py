"""
Definições do estado do agente e funções de coordenação geral
"""
from typing import Dict, Any, Optional, TypedDict


class AgentState(TypedDict):
    """Estado do agente LangGraph - apenas dados serializáveis"""
    user_input: str
    selected_model: str
    response: str
    advanced_mode: bool
    execution_time: float
    error: Optional[str]
    intermediate_steps: list

    # Dados serializáveis do banco
    db_sample_dict: dict

    # IDs para recuperar objetos não-serializáveis
    agent_id: str
    engine_id: str
    cache_id: str

    # Campos relacionados ao refinamento de pergunta
    question_refinement_enabled: bool  # Se o refinamento está habilitado
    original_user_input: Optional[str]  # Pergunta original antes do refinamento
    refined_question: Optional[str]  # Pergunta refinada pelo GPT-4o
    question_refinement_applied: bool  # Se o refinamento foi aplicado
    question_refinement_changes: list  # Lista de mudanças feitas
    question_refinement_justification: Optional[str]  # Justificativa do refinamento
    question_refinement_success: bool  # Se o refinamento foi bem-sucedido
    question_refinement_error: Optional[str]  # Erro no refinamento
    question_refinement_has_significant_change: bool  # Se houve mudança significativa
    
    # Campos relacionados a gráficos
    query_type: str  # 'sql_query', 'sql_query_graphic', 'prediction'
    sql_query_extracted: Optional[str]  # Query SQL extraída da resposta do agente
    graph_type: Optional[str]  # Tipo de gráfico escolhido pela LLM
    graph_data: Optional[dict]  # Dados preparados para o gráfico (serializável)
    graph_image_id: Optional[str]  # ID da imagem do gráfico no ObjectManager
    graph_generated: bool  # Se o gráfico foi gerado com sucesso
    graph_error: Optional[str]  # Erro na geração de gráfico
    
    # Campos relacionados ao cache
    cache_hit: bool  # Se houve hit no cache
    
    # Campos relacionados ao Processing Agent
    processing_enabled: bool  # Se o Processing Agent está habilitado
    processing_model: str  # Modelo usado no Processing Agent
    processing_agent_id: Optional[str]  # ID do Processing Agent no ObjectManager
    suggested_query: Optional[str]  # Query SQL sugerida pelo Processing Agent
    query_observations: Optional[str]  # Observações sobre a query sugerida
    processing_result: Optional[dict]  # Resultado completo do Processing Agent
    processing_success: bool  # Se o processamento foi bem-sucedido
    processing_error: Optional[str]  # Erro no processamento
    
    # Campos relacionados ao refinamento
    refined: bool  # Se a resposta foi refinada
    refinement_error: Optional[str]  # Erro no refinamento
    refinement_quality: Optional[str]  # Qualidade do refinamento
    quality_metrics: Optional[dict]  # Métricas de qualidade
    
    # Campos relacionados ao contexto SQL
    sql_context: Optional[str]  # Contexto preparado para o agente SQL
    sql_result: Optional[dict]  # Resultado do agente SQL

    # Campos relacionados ao tipo de conexão
    connection_type: str  # "csv" | "postgresql"
    postgresql_config: Optional[dict]  # Configuração PostgreSQL
    selected_table: Optional[str]  # Tabela selecionada (para PostgreSQL)
    single_table_mode: bool  # Se deve usar apenas uma tabela (PostgreSQL)
    connection_success: bool  # Se a conexão foi estabelecida com sucesso
    connection_error: Optional[str]  # Erro na conexão
    connection_info: Optional[dict]  # Informações da conexão estabelecida

    # Campos relacionados ao Celery
    use_celery: bool  # Se deve usar Celery para processamento assíncrono
    ready_for_celery_dispatch: Optional[bool]  # Se está pronto para dispatch Celery
    celery_task_id: Optional[str]  # ID da task Celery disparada
    celery_task_status: Optional[str]  # Status da task Celery

    # Campos relacionados ao histórico/conversa (precisam estar no estado inicial)
    user_id: Optional[int]  # ID do usuário autenticado
    chat_session_id: Optional[int]  # ID da sessão de chat criada/fornecida
    run_id: Optional[int]  # ID da run atual (para auditoria)

    # Campos de histórico (conteúdo e flags) — devem persistir entre os nós
    history_enabled: bool
    history_retrieved: bool
    history_context: Optional[str]
    relevant_history: list
    has_history: bool
    history_error: Optional[str]


def should_refine_response(state: Dict[str, Any]) -> str:
    """
    Determina se deve refinar a resposta

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    if state.get("advanced_mode", False) and not state.get("error"):
        return "refine_response"
    else:
        return "format_response"  # Sempre formatar antes do cache


def should_generate_graph(state: Dict[str, Any]) -> str:
    """
    Determina se deve gerar gráfico

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    query_type = state.get("query_type", "")

    if query_type == "sql_query_graphic" and not state.get("error"):
        return "graph_selection"
    elif state.get("advanced_mode", False) and not state.get("error"):
        return "refine_response"
    else:
        return "format_response"  # Sempre formatar antes do cache


def should_use_processing_agent(state: Dict[str, Any]) -> str:
    """
    Determina se deve usar o Processing Agent

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    if state.get("processing_enabled", False):
        return "validate_processing"
    else:
        return "prepare_context"


def should_refine_question(state: Dict[str, Any]) -> str:
    """
    Determina se deve refinar a pergunta

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    if state.get("question_refinement_enabled", False):
        return "question_refinement"
    else:
        # Pula refinamento e vai para validação de processing
        return "validate_processing"


def route_after_cache_check(state: Dict[str, Any]) -> str:
    """
    Roteamento após verificação de cache

    CACHE TEMPORARIAMENTE DESATIVADO - Sempre ignora cache hit

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    import logging

    cache_hit = state.get("cache_hit", False)
    processing_enabled = state.get("processing_enabled", False)
    question_refinement_enabled = state.get("question_refinement_enabled", False)

    # DESATIVAÇÃO TEMPORÁRIA DO CACHE
    # Força cache_hit = False para sempre processar queries
    cache_hit = False

    logging.info(f"[ROUTING] ===== ROTEAMENTO APÓS CACHE =====")
    logging.info(f"[ROUTING] Cache hit: {cache_hit} (CACHE DESATIVADO TEMPORARIAMENTE)")
    logging.info(f"[ROUTING] Processing enabled: {processing_enabled}")
    logging.info(f"[ROUTING] Question refinement enabled: {question_refinement_enabled}")

    # DEBUG: Log completo do estado
    user_id = state.get("user_id")
    agent_id = state.get("agent_id")
    chat_session_id = state.get("chat_session_id")
    logging.info(f"[ROUTING] 🔍 ESTADO ATUAL - user_id: {user_id}, agent_id: {agent_id}, chat_session_id: {chat_session_id}")

    if cache_hit:
        logging.info("[ROUTING] Direcionando para update_history (cache hit)")
        return "update_history"

    # Verifica se deve buscar histórico primeiro
    import os
    history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() == "true"
    history_retrieved = state.get("history_retrieved", False)

    logging.info(f"[ROUTING] 🔍 VERIFICANDO HISTÓRICO - enabled: {history_enabled}, retrieved: {history_retrieved}")

    if history_enabled and not history_retrieved:
        logging.info("[ROUTING] 📚 DIRECIONANDO PARA HISTORY_RETRIEVAL!")
        return "history_retrieval"

    # Se histórico já foi recuperado ou está desabilitado, continua fluxo normal
    logging.info("[ROUTING] ✅ Histórico processado - continuando fluxo")

    # Se não tem conexão, vai para seleção de conexão
    if not state.get("agent_id") or not state.get("engine_id"):
        logging.info("[ROUTING] Direcionando para connection_selection (sem conexão)")
        return "connection_selection"

    # Se refinamento está habilitado E ainda não foi aplicado, vai para refinamento primeiro
    if question_refinement_enabled and not state.get("question_refinement_applied", False):
        logging.info("[ROUTING] Direcionando para question_refinement (refinamento habilitado)")
        return "question_refinement"
    elif processing_enabled:
        logging.info("[ROUTING] Direcionando para validate_processing (processing habilitado)")
        return "validate_processing"
    else:
        logging.info("[ROUTING] Direcionando para connection_selection (fluxo direto)")
        return "connection_selection"
