"""
Nó para refinamento de respostas
"""
import logging
from typing import Dict, Any

from agentgraph.agents.tools import refine_response_with_llm

async def refine_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para refinar a resposta usando LLM adicional
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com resposta refinada
    """
    if not state.get("advanced_mode", False) or state.get("error"):
        # Pula refinamento se modo avançado desabilitado ou há erro
        logging.info("[REFINE] Pulando refinamento - modo avançado desabilitado ou erro presente")
        return state
    
    logging.info("[REFINE] Iniciando refinamento da resposta")
    
    try:
        original_response = state.get("response", "")
        user_input = state.get("user_input", "")
        
        if not original_response or not user_input:
            logging.warning("[REFINE] Resposta ou entrada do usuário não disponível")
            return state
        
        # Refina resposta com LLM adicional
        refined_response = await refine_response_with_llm(
            user_input,
            original_response
        )
        
        # Atualiza estado com resposta refinada
        state["response"] = refined_response
        state["refined"] = True
        
        logging.info("[REFINE] Resposta refinada com sucesso")
        
    except Exception as e:
        error_msg = f"Erro ao refinar resposta: {e}"
        logging.error(f"[REFINE] {error_msg}")
        # Mantém resposta original em caso de erro
        state["refinement_error"] = error_msg
    
    return state

async def check_refinement_quality_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para verificar qualidade do refinamento
    
    Args:
        state: Estado com resposta refinada
        
    Returns:
        Estado com avaliação da qualidade
    """
    try:
        original_response = state.get("sql_result", {}).get("output", "")
        refined_response = state.get("response", "")
        
        if not state.get("refined", False):
            state["refinement_quality"] = "not_refined"
            return state
        
        # Métricas simples de qualidade
        quality_metrics = {
            "length_increase": len(refined_response) - len(original_response),
            "has_insights": any(word in refined_response.lower() for word in [
                "insight", "análise", "interpretação", "conclusão", "tendência"
            ]),
            "has_statistics": any(word in refined_response.lower() for word in [
                "média", "total", "percentual", "proporção", "estatística"
            ]),
            "improved": len(refined_response) > len(original_response) * 1.1
        }
        
        # Determina qualidade geral
        if quality_metrics["improved"] and (quality_metrics["has_insights"] or quality_metrics["has_statistics"]):
            quality_score = "high"
        elif quality_metrics["length_increase"] > 0:
            quality_score = "medium"
        else:
            quality_score = "low"
        
        state["refinement_quality"] = quality_score
        state["quality_metrics"] = quality_metrics
        
        logging.info(f"[REFINE] Qualidade avaliada: {quality_score}")
        
    except Exception as e:
        logging.error(f"[REFINE] Erro ao avaliar qualidade: {e}")
        state["refinement_quality"] = "error"
    
    return state

async def format_final_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para formatação final da resposta

    Args:
        state: Estado com resposta processada

    Returns:
        Estado com resposta formatada
    """
    try:
        logging.info("[FORMAT] 🎨 Iniciando formatação final da resposta")

        response = state.get("response", "")
        execution_time = state.get("execution_time", 0.0)
        advanced_mode = state.get("advanced_mode", False)
        refined = state.get("refined", False)

        logging.info(f"[FORMAT] Estado inicial - Response: {len(response)} chars, Advanced: {advanced_mode}, Refined: {refined}")

        # Adiciona informações de contexto se necessário
        if advanced_mode and refined:
            quality = state.get("refinement_quality", "unknown")
            if quality == "high":
                response += "\n\n💡 *Resposta aprimorada com análise avançada*"
            elif quality == "medium":
                response += "\n\n🔍 *Resposta complementada*"

        # Adiciona tempo de execução se significativo
        if execution_time > 2.0:
            response += f"\n\n⏱️ *Processado em {execution_time:.1f}s*"

        # Adiciona SQL query utilizada se disponível
        sql_query = state.get("sql_query_extracted") or state.get("sql_query")
        connection_type = state.get("connection_type", "")
        logging.info(f"[FORMAT] SQL query encontrada: {sql_query}")
        logging.info(f"[FORMAT] Connection type: {connection_type}")

        if sql_query:
            # Limpa e formata a SQL query
            sql_query_str = str(sql_query).strip()
            logging.info(f"[FORMAT] SQL query processada: {sql_query_str[:100]}...")

            if sql_query_str and sql_query_str.lower() != 'none':
                response += f"\n\n---\n\n**Query SQL utilizada:**\n\n```sql\n{sql_query_str}\n```"

                # Adiciona indicação para criar tabela apenas para PostgreSQL
                if connection_type == "postgresql":
                    # Armazena a SQL query no estado para uso posterior
                    state["create_table_sql"] = sql_query_str
                    state["show_create_table_option"] = True
                    response += f"\n\n💡 *Você pode criar uma nova tabela no PostgreSQL com estes dados. Use o botão 'Criar Tabela' abaixo do chat.*"
                    logging.info("[FORMAT] ✅ Opção de criar tabela habilitada (PostgreSQL)")

                logging.info(f"[FORMAT] ✅ SQL query adicionada à resposta: {sql_query_str[:50]}...")
            else:
                logging.info("[FORMAT] ❌ SQL query vazia ou 'none', não adicionada")
        else:
            logging.info("[FORMAT] ❌ Nenhuma SQL query encontrada no estado")

        # Formatação final
        state["response"] = response.strip()
        state["formatted"] = True

        logging.info(f"[FORMAT] ✅ Resposta formatada - {len(response)} caracteres")

    except Exception as e:
        logging.error(f"[FORMAT] Erro na formatação: {e}")
        # Mantém resposta original se houver erro na formatação

    return state
