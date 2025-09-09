"""
Nó para refinamento de perguntas usando GPT-4o
"""
import logging
import re
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from agentgraph.utils.config import OPENAI_API_KEY
from agentgraph.utils.object_manager import get_object_manager


async def question_refinement_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para refinar perguntas usando GPT-4o para melhorar clareza sem alterar lógica
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com pergunta refinada
    """
    try:
        logging.info("[QUESTION_REFINEMENT] Iniciando refinamento de pergunta")

        # Verifica se refinamento já foi aplicado (evita loop infinito)
        if state.get("question_refinement_applied", False):
            logging.info("[QUESTION_REFINEMENT] Refinamento já aplicado, pulando")
            return state

        # Verifica se refinamento está habilitado
        question_refinement_enabled = state.get("question_refinement_enabled", False)
        if not question_refinement_enabled:
            logging.info("[QUESTION_REFINEMENT] Refinamento desabilitado, mantendo pergunta original")
            state.update({
                "refined_question": state.get("user_input", ""),
                "question_refinement_applied": False,
                "question_refinement_changes": [],
                "question_refinement_success": True
            })
            return state
        
        # Recupera pergunta original
        original_question = state.get("user_input", "")
        if not original_question or not original_question.strip():
            error_msg = "Pergunta original não encontrada ou vazia"
            logging.error(f"[QUESTION_REFINEMENT] {error_msg}")
            state.update({
                "refined_question": original_question,
                "question_refinement_applied": False,
                "question_refinement_error": error_msg,
                "question_refinement_success": False
            })
            return state
        
        # Verifica se OpenAI API está disponível
        if not OPENAI_API_KEY:
            error_msg = "OpenAI API Key não configurada para Question Refinement"
            logging.error(f"[QUESTION_REFINEMENT] {error_msg}")
            state.update({
                "refined_question": original_question,
                "question_refinement_applied": False,
                "question_refinement_error": error_msg,
                "question_refinement_success": False
            })
            return state
        
        # Obtém informações de contexto dos dados
        db_sample_dict = state.get("db_sample_dict", {})
        context_info = _build_context_info(db_sample_dict)
        
        # Executa refinamento
        refinement_result = await _refine_question_with_gpt4o(original_question, context_info)
        
        if refinement_result["success"]:
            # Atualiza estado com pergunta refinada
            refined_question = refinement_result["refined_question"]
            
            # Atualiza user_input para que toda a pipeline use a pergunta refinada
            state.update({
                "user_input": refined_question,  # ← Substitui a pergunta original
                "original_user_input": original_question,  # ← Preserva a original
                "refined_question": refined_question,
                "question_refinement_applied": True,
                "question_refinement_changes": refinement_result.get("changes_made", []),
                "question_refinement_justification": refinement_result.get("justification", ""),
                "question_refinement_success": True,
                "question_refinement_has_significant_change": refinement_result.get("has_significant_change", False)
            })
            
            logging.info(f"[QUESTION_REFINEMENT] Pergunta refinada com sucesso")
            logging.info(f"[QUESTION_REFINEMENT] Original: {original_question}")
            logging.info(f"[QUESTION_REFINEMENT] Refinada: {refined_question}")
            
        else:
            # Falha no refinamento, mantém pergunta original
            error_msg = refinement_result.get("reason", "Erro desconhecido no refinamento")
            logging.error(f"[QUESTION_REFINEMENT] {error_msg}")
            state.update({
                "refined_question": original_question,
                "question_refinement_applied": False,
                "question_refinement_error": error_msg,
                "question_refinement_success": False
            })
        
        return state
        
    except Exception as e:
        error_msg = f"Erro no nó de refinamento de pergunta: {e}"
        logging.error(f"[QUESTION_REFINEMENT] {error_msg}")
        
        # Em caso de erro, mantém pergunta original
        original_question = state.get("user_input", "")
        state.update({
            "refined_question": original_question,
            "question_refinement_applied": False,
            "question_refinement_error": error_msg,
            "question_refinement_success": False
        })
        return state


def _build_context_info(db_sample_dict: Dict[str, Any]) -> str:
    """
    Constrói informações de contexto sobre os dados para o refinamento
    
    Args:
        db_sample_dict: Dicionário com amostra dos dados
        
    Returns:
        String com informações de contexto
    """
    try:
        if not db_sample_dict or not db_sample_dict.get("data"):
            return "Dados tabulares genéricos"
        
        # Obtém informações básicas dos dados
        data = db_sample_dict.get("data", [])
        if not data:
            return "Dados tabulares genéricos"
        
        # Obtém colunas disponíveis
        columns = list(data[0].keys()) if data else []
        num_records = len(data)
        
        # Constrói contexto
        context_parts = [
            f"Tabela com {num_records} registros de amostra",
            f"Colunas disponíveis: {', '.join(columns[:10])}"  # Limita a 10 colunas
        ]
        
        if len(columns) > 10:
            context_parts.append(f"(e mais {len(columns) - 10} colunas)")
        
        return ". ".join(context_parts)
        
    except Exception as e:
        logging.warning(f"Erro ao construir contexto dos dados: {e}")
        return "Dados tabulares genéricos"


async def _refine_question_with_gpt4o(original_question: str, context_info: str) -> Dict[str, Any]:
    """
    Refina pergunta usando GPT-4o
    
    Args:
        original_question: Pergunta original
        context_info: Informações de contexto
        
    Returns:
        Resultado do refinamento
    """
    try:
        # Inicializa LLM
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,  # Baixa temperatura para consistência
            max_tokens=500,   # Perguntas refinadas devem ser concisas
            api_key=OPENAI_API_KEY
        )
        
        # Prompt especializado para refinamento
        refinement_prompt = f"""
Você é um especialista em SQL e análise de dados. Sua tarefa é refinar uma pergunta para torná-la mais clara e precisa para um agente SQL, SEM ALTERAR a lógica ou intenção original.

PERGUNTA ORIGINAL:
{original_question}

CONTEXTO DOS DADOS:
{context_info}

OBJETIVOS DO REFINAMENTO:
1. Remover ambiguidades que possam gerar interpretações diferentes
2. Tornar a pergunta mais específica e clara
3. Usar terminologia mais precisa para consultas SQL
4. Manter EXATAMENTE a mesma intenção e lógica original
5. Não adicionar filtros ou condições que não estavam implícitos

REGRAS IMPORTANTES:
- NÃO altere o escopo ou objetivo da pergunta
- NÃO adicione filtros temporais se não estavam na pergunta original
- NÃO assuma colunas específicas que não foram mencionadas
- NÃO mude o tipo de análise solicitada
- MANTENHA a linguagem natural e compreensível
- Se a pergunta já está clara, retorne ela praticamente igual

EXEMPLOS DE REFINAMENTO:
Original: "Mostre os dados"
Refinado: "Mostre todos os registros da tabela principal"

Original: "Qual o maior valor?"
Refinado: "Qual é o maior valor numérico encontrado nos dados?"

Original: "Produtos com problema"
Refinado: "Quais produtos apresentam algum tipo de problema ou irregularidade?"

RESPONDA EXATAMENTE NESTE FORMATO:
PERGUNTA_REFINADA: [pergunta melhorada]
MUDANÇAS: [lista das principais mudanças feitas, ou "Nenhuma mudança significativa"]
JUSTIFICATIVA: [breve explicação do refinamento]
"""
        
        # Executa refinamento
        message = HumanMessage(content=refinement_prompt)
        response_llm = await llm.ainvoke([message])
        
        # Extrai e valida resultado
        return _parse_refinement_result(response_llm.content, original_question)
        
    except Exception as e:
        logging.error(f"Erro no refinamento com GPT-4o: {e}")
        return {
            'success': False,
            'refined_question': original_question,
            'reason': f'Erro no refinamento: {e}'
        }


def _parse_refinement_result(llm_response: str, original_question: str) -> Dict[str, Any]:
    """
    Extrai resultado do refinamento da resposta do LLM
    
    Args:
        llm_response: Resposta do LLM
        original_question: Pergunta original para fallback
        
    Returns:
        Resultado parseado do refinamento
    """
    try:
        # Padrões para extrair informações
        question_pattern = r'PERGUNTA_REFINADA:\s*(.+?)(?:\n|MUDANÇAS:|$)'
        changes_pattern = r'MUDANÇAS:\s*(.+?)(?:\n|JUSTIFICATIVA:|$)'
        justification_pattern = r'JUSTIFICATIVA:\s*(.+?)(?:\n|$)'
        
        # Extrai pergunta refinada
        question_match = re.search(question_pattern, llm_response, re.IGNORECASE | re.DOTALL)
        refined_question = question_match.group(1).strip() if question_match else original_question
        
        # Remove possíveis aspas ou formatação extra
        refined_question = refined_question.strip('"\'[]')
        
        # Extrai mudanças
        changes_match = re.search(changes_pattern, llm_response, re.IGNORECASE | re.DOTALL)
        changes_text = changes_match.group(1).strip() if changes_match else "Não especificado"
        
        # Extrai justificativa
        justification_match = re.search(justification_pattern, llm_response, re.IGNORECASE | re.DOTALL)
        justification = justification_match.group(1).strip() if justification_match else "Não especificado"
        
        # Processa mudanças em lista
        changes_made = []
        if changes_text and changes_text.lower() not in ['nenhuma mudança significativa', 'nenhuma', 'não especificado']:
            changes_made = [change.strip() for change in changes_text.split(',') if change.strip()]
        
        # Verifica se houve mudança real
        has_significant_change = (
            refined_question.lower().strip() != original_question.lower().strip() and
            len(changes_made) > 0
        )
        
        # Valida refinamento
        validation = _validate_refinement(original_question, refined_question)
        
        if not validation['valid']:
            logging.warning(f"Refinamento inválido: {validation['reason']}")
            return {
                'success': False,
                'refined_question': original_question,
                'reason': f'Refinamento inválido: {validation["reason"]}'
            }
        
        return {
            'success': True,
            'refined_question': refined_question,
            'original_question': original_question,
            'changes_made': changes_made,
            'justification': justification,
            'has_significant_change': has_significant_change,
            'raw_response': llm_response
        }
        
    except Exception as e:
        logging.error(f"Erro ao parsear resultado do refinamento: {e}")
        return {
            'success': False,
            'refined_question': original_question,
            'reason': f'Erro ao parsear resposta: {e}'
        }


def _validate_refinement(original: str, refined: str) -> Dict[str, Any]:
    """
    Valida se o refinamento mantém a intenção original

    Args:
        original: Pergunta original
        refined: Pergunta refinada

    Returns:
        Resultado da validação
    """
    try:
        # Verificações básicas de qualidade (muito permissivas)
        checks = {
            'not_empty': bool(refined and refined.strip()),
            'reasonable_length': 3 <= len(refined) <= 2000,  # Muito flexível
            'has_content': len(refined.strip()) >= 3,  # Pelo menos 3 caracteres
            'no_obvious_errors': not any(error in refined.lower() for error in ['erro', 'error', 'desculpe', 'não posso', 'não é possível'])
        }

        all_valid = all(checks.values())

        # Se a pergunta refinada é igual à original, também é válido
        if refined.strip().lower() == original.strip().lower():
            all_valid = True

        return {
            'valid': all_valid,
            'checks': checks,
            'reason': 'Refinamento válido' if all_valid else f'Problemas detectados: {[k for k, v in checks.items() if not v]}'
        }

    except Exception as e:
        return {
            'valid': False,
            'reason': f'Erro na validação: {e}'
        }


def route_after_question_refinement(state: Dict[str, Any]) -> str:
    """
    Roteamento após refinamento de pergunta

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    # Após refinamento, sempre vai para validação de processing
    return "validate_processing"
