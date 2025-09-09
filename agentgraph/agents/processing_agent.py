"""
Agente de processamento de contexto inicial para sugestão de queries SQL
"""
import logging
import asyncio
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import HuggingFaceEndpoint
from langchain.schema import HumanMessage

from agentgraph.utils.config import (
    TEMPERATURE,
    AVAILABLE_MODELS,
    OPENAI_MODELS,
    ANTHROPIC_MODELS,
    GOOGLE_MODELS,
    REFINEMENT_MODELS
)


class ProcessingAgentManager:
    """
    Gerenciador do agente de processamento de contexto inicial
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Inicializa o modelo LLM baseado no nome fornecido"""
        try:
            # Obtém o ID real do modelo
            model_id = AVAILABLE_MODELS.get(self.model_name, self.model_name)
            
            # Verifica se é modelo de refinamento
            if model_id not in AVAILABLE_MODELS.values():
                model_id = REFINEMENT_MODELS.get(self.model_name, model_id)
            
            # Cria o modelo LLM baseado no provedor
            if model_id in OPENAI_MODELS:
                # Configurações específicas para modelos OpenAI
                if model_id == "o3-mini":
                    # o3-mini não suporta temperature
                    self.llm = ChatOpenAI(model=model_id)
                else:
                    # GPT-4o e GPT-4o-mini suportam temperature
                    self.llm = ChatOpenAI(model=model_id, temperature=TEMPERATURE)
                    
            elif model_id in ANTHROPIC_MODELS:
                # Claude com tool-calling e configurações para rate limiting
                self.llm = ChatAnthropic(
                    model=model_id,
                    temperature=TEMPERATURE,
                    max_tokens=4096,
                    max_retries=2,
                    timeout=60.0
                )

            elif model_id in GOOGLE_MODELS:
                # Gemini com configurações otimizadas
                self.llm = ChatGoogleGenerativeAI(
                    model=model_id,
                    temperature=TEMPERATURE,
                    max_tokens=4096,
                    max_retries=2,
                    timeout=60.0
                )

            else:
                # Modelos HuggingFace (refinement models)
                self.llm = HuggingFaceEndpoint(
                    endpoint_url=f"https://api-inference.huggingface.co/models/{model_id}",
                    temperature=TEMPERATURE,
                    max_new_tokens=1024,
                    timeout=120
                )
                
            logging.info(f"Processing Agent inicializado com modelo {model_id}")
            
        except Exception as e:
            logging.error(f"Erro ao inicializar Processing Agent: {e}")
            # Fallback para GPT-4o-mini
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=TEMPERATURE)
            logging.warning("Usando GPT-4o-mini como fallback")
    
    def recreate_llm(self, new_model: str):
        """
        Recria o LLM com novo modelo

        Args:
            new_model: Nome do novo modelo
        """
        old_model = self.model_name
        self.model_name = new_model
        self._initialize_llm()
        logging.info(f"[PROCESSING] Modelo alterado de '{old_model}' para '{new_model}'")
    
    async def process_context(self, context_prompt: str) -> Dict[str, Any]:
        """
        Processa o contexto inicial e retorna sugestão de query
        
        Args:
            context_prompt: Prompt com contexto e pergunta do usuário
            
        Returns:
            Resultado do processamento com pergunta e sugestão de query
        """
        try:
            logging.info(f"[PROCESSING] ===== INICIANDO PROCESSING AGENT =====")
            logging.info(f"[PROCESSING] Modelo utilizado: {self.model_name}")
            logging.info(f"[PROCESSING] Tamanho do contexto: {len(context_prompt)} caracteres")

            # Executa o processamento
            if hasattr(self.llm, 'ainvoke'):
                # Para modelos que suportam async
                logging.info(f"[PROCESSING] Executando chamada assíncrona para {self.model_name}")
                response = await self.llm.ainvoke([HumanMessage(content=context_prompt)])
                output = response.content
            else:
                # Para modelos síncronos, executa em thread
                logging.info(f"[PROCESSING] Executando chamada síncrona para {self.model_name}")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.llm.invoke([HumanMessage(content=context_prompt)])
                )
                output = response.content if hasattr(response, 'content') else str(response)

            logging.info(f"[PROCESSING] Resposta recebida do modelo ({len(output)} caracteres)")

            # Processa a resposta
            processed_result = self._parse_processing_response(output)

            result = {
                "success": True,
                "output": output,
                "processed_question": processed_result.get("question", ""),
                "suggested_query": processed_result.get("query", ""),
                "query_observations": processed_result.get("observations", ""),
                "model_used": self.model_name
            }

            # Log simples do resultado
            if result['suggested_query']:
                logging.info(f"[PROCESSING] ✅ Query SQL extraída com sucesso")
            else:
                logging.warning(f"[PROCESSING] ❌ Nenhuma query SQL foi extraída")

            logging.info(f"[PROCESSING] ===== PROCESSING AGENT CONCLUÍDO =====")
            return result
            
        except Exception as e:
            error_msg = f"Erro no Processing Agent: {e}"
            logging.error(error_msg)
            
            return {
                "success": False,
                "output": error_msg,
                "processed_question": "",
                "suggested_query": "",
                "model_used": self.model_name
            }
    
    def _parse_processing_response(self, response: str) -> Dict[str, str]:
        """
        Extrai query SQL e observações da resposta

        Args:
            response: Resposta do modelo

        Returns:
            Dicionário com query e observações extraídas
        """
        try:
            import re

            query = ""
            observations = ""

            # Primeiro, tenta extrair observações pelo formato esperado
            obs_match = re.search(r'Observações:\s*(.*?)(?:\n|$)', response, re.IGNORECASE)
            if obs_match:
                observations = obs_match.group(1).strip()

            # Agora extrai a query SQL - prioriza blocos de código SQL
            sql_patterns = [
                # Padrão principal: ```sql ... ```
                r'```sql\s*(.*?)\s*```',
                # Padrão alternativo: ``` ... ``` (assumindo que é SQL)
                r'```\s*(WITH.*?)\s*```',
                r'```\s*(SELECT.*?)\s*```',
                # Padrões sem backticks
                r'Opção de querySQL:\s*(WITH.*?)(?=Observações:|$)',
                r'Opção de querySQL:\s*(SELECT.*?)(?=Observações:|$)',
                # Padrões mais gerais
                r'(WITH\s+.*?;)',
                r'(SELECT\s+.*?;)'
            ]

            for pattern in sql_patterns:
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    query = match.group(1).strip()
                    break

            # Limpa a query final se encontrada
            if query:
                # Remove apenas backticks e mantém formatação original
                query = query.replace('```', '').replace('sql', '').strip()

                # Remove quebras de linha no início e fim, mas mantém formatação interna
                query = query.strip('\n').strip()

            # Se ainda não encontrou observações, tenta padrão mais flexível
            if not observations:
                obs_patterns = [
                    r'Observações:\s*(.*)',
                    r'Observacoes:\s*(.*)',
                ]
                for pattern in obs_patterns:
                    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                    if match:
                        observations = match.group(1).strip()
                        break

            return {
                "question": "",  # Não precisamos da pergunta processada
                "query": query,
                "observations": observations
            }

        except Exception as e:
            logging.error(f"Erro ao extrair query e observações: {e}")
            return {
                "question": "",
                "query": "",
                "observations": ""
            }


def get_default_processing_agent(model_name: str = "gpt-4o-mini") -> ProcessingAgentManager:
    """
    Cria um Processing Agent com configurações padrão
    
    Args:
        model_name: Nome do modelo a usar
        
    Returns:
        ProcessingAgentManager configurado
    """
    return ProcessingAgentManager(model_name)
