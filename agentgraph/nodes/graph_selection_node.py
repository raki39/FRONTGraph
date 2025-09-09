"""
Nó para seleção do tipo de gráfico usando LLM - REFATORADO COMPLETO
"""
import logging
import re
import pandas as pd
from typing import Dict, Any, Optional

from agentgraph.agents.tools import (
    generate_graph_type_context,
    extract_sql_query_from_response
)
from agentgraph.utils.config import OPENAI_API_KEY
from langchain_openai import ChatOpenAI
from agentgraph.utils.object_manager import get_object_manager

# Mapeamento DIRETO no arquivo para evitar problemas externos
GRAPH_TYPE_MAPPING = {
    "1": "line_simple",
    "2": "multiline",
    "3": "area",
    "4": "bar_vertical",
    "5": "bar_horizontal",
    "6": "bar_grouped",
    "7": "bar_stacked",
    "8": "pie",
    "9": "donut",
    "10": "pie_multiple"
}

async def graph_selection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó REFATORADO para seleção do tipo de gráfico usando LLM
    """
    logging.info("[GRAPH_SELECTION_NEW] 🚀 Iniciando seleção REFATORADA")

    try:
        # 1. Verificações básicas
        if state.get("query_type") != "sql_query_graphic":
            logging.info("[GRAPH_SELECTION_NEW] Query não requer gráfico")
            return state

        # 2. Obter SQL query
        sql_query = state.get("sql_query_extracted")
        if not sql_query:
            sql_query = extract_sql_query_from_response(state.get("response", ""))

        if not sql_query:
            logging.error("[GRAPH_SELECTION_NEW] ❌ SQL query não encontrada")
            state.update({"graph_error": "SQL query não encontrada", "graph_generated": False})
            return state

        # 3. Obter dados
        obj_manager = get_object_manager()
        engine = obj_manager.get_engine(state.get("engine_id"))
        if not engine:
            logging.error("[GRAPH_SELECTION_NEW] ❌ Engine não encontrada")
            state.update({"graph_error": "Engine não encontrada", "graph_generated": False})
            return state

        # 4. Executar query
        try:
            df_result = pd.read_sql_query(sql_query, engine)
            if df_result.empty:
                logging.error("[GRAPH_SELECTION_NEW] ❌ Dados vazios")
                state.update({"graph_error": "Dados vazios", "graph_generated": False})
                return state
        except Exception as e:
            logging.error(f"[GRAPH_SELECTION_NEW] ❌ Erro na query: {e}")
            state.update({"graph_error": f"Erro na query: {e}", "graph_generated": False})
            return state

        # 5. Preparar contexto
        user_query = state.get("user_input", "")
        df_sample = df_result.head(3)
        graph_context = generate_graph_type_context(user_query, sql_query, df_result.columns.tolist(), df_sample)

        # 6. Chamar LLM de forma LIMPA
        graph_type = await call_llm_for_graph_selection(graph_context, user_query)

        logging.error(f"🎯 [RESULTADO_FINAL] Tipo selecionado: '{graph_type}'")

        # 7. Armazenar resultado
        graph_data_id = obj_manager.store_object(df_result, "graph_data")
        state.update({
            "graph_type": graph_type,
            "graph_data": {
                "data_id": graph_data_id,
                "columns": df_result.columns.tolist(),
                "rows": len(df_result),
                "sample": df_sample.to_dict()
            },
            "graph_error": None
        })

        return state

    except Exception as e:
        logging.error(f"[GRAPH_SELECTION_NEW] ❌ Erro geral: {e}")
        state.update({"graph_error": f"Erro geral: {e}", "graph_generated": False})
        return state

async def call_llm_for_graph_selection(graph_context: str, user_query: str) -> str:
    """
    Função NOVA e LIMPA para chamar LLM sem interferências
    """
    logging.error("🔥 [LLM_CALL] Iniciando chamada LIMPA da LLM")

    # Verificação básica
    if not OPENAI_API_KEY:
        logging.error("🔥 [LLM_CALL] OpenAI não configurada")
        return "line_simple"

    try:
        # Criar LLM com configuração limpa
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_tokens=5,
            timeout=30
        )

        # Log do contexto
        logging.error("🔥 [LLM_CALL] Contexto enviado:")
        logging.error(f"'{graph_context}...'")

        # Agora a pergunta real
        real_response = llm.invoke(graph_context)
        real_content = real_response.content.strip()

        logging.error(f"🔥 [LLM_CALL] Resposta REAL: '{real_content}'")

        # Extrair número da resposta
        number_match = re.search(r'\b([1-9]|10)\b', real_content)
        if number_match:
            number = number_match.group(0)
            graph_type = GRAPH_TYPE_MAPPING.get(number, "line_simple")
            logging.error(f"🔥 [LLM_CALL] Número: {number} → Tipo: {graph_type}")
            return graph_type
        else:
            logging.error(f"🔥 [LLM_CALL] Número não encontrado em: '{real_content}'")
            return "line_simple"

    except Exception as e:
        logging.error(f"🔥 [LLM_CALL] ERRO: {e}")
        return "line_simple"

