"""
Criação e configuração do agente SQL
"""
import logging
import time
import asyncio
from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish


from agentgraph.utils.config import (
    MAX_ITERATIONS,
    TEMPERATURE,
    AVAILABLE_MODELS,
    OPENAI_MODELS,
    ANTHROPIC_MODELS,
    GOOGLE_MODELS
)

class SQLQueryCaptureHandler(BaseCallbackHandler):
    """
    Handler para capturar queries SQL executadas pelo agente
    """

    def __init__(self):
        super().__init__()
        self.sql_queries: List[str] = []
        self.agent_actions: List[Dict[str, Any]] = []
        self.step_count = 0

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """
        Captura ações do agente, especialmente queries SQL

        Args:
            action: Ação do agente
        """
        try:
            self.step_count += 1
            tool_name = action.tool
            tool_input = action.tool_input

            # Capturar SQL especificamente (sem log de cada passo)
            if tool_name == 'sql_db_query' and isinstance(tool_input, dict):
                sql_query = tool_input.get('query', '')
                if sql_query and sql_query.strip():
                    clean_query = sql_query.strip()
                    self.sql_queries.append(clean_query)

                    # Log apenas uma vez com query completa
                    logging.info(f"[SQL_HANDLER] 🔍 Query SQL capturada:\n{clean_query}")

            # Armazenar todas as ações para debug
            self.agent_actions.append({
                "step": self.step_count,
                "tool": tool_name,
                "input": tool_input,
                "timestamp": time.time()
            })

        except Exception as e:
            logging.error(f"[SQL_HANDLER] Erro ao capturar ação: {e}")

    def get_last_sql_query(self) -> Optional[str]:
        """
        Retorna a última query SQL capturada

        Returns:
            Última query SQL ou None se não houver
        """
        return self.sql_queries[-1] if self.sql_queries else None

    def get_all_sql_queries(self) -> List[str]:
        """
        Retorna todas as queries SQL capturadas

        Returns:
            Lista de queries SQL
        """
        return self.sql_queries.copy()

    def reset(self):
        """Reseta o handler para nova execução"""
        self.sql_queries.clear()
        self.agent_actions.clear()
        self.step_count = 0

async def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """
    Executa função com retry e backoff exponencial para lidar com rate limiting

    Args:
        func: Função a ser executada
        max_retries: Número máximo de tentativas
        base_delay: Delay base em segundos

    Returns:
        Resultado da função ou levanta exceção após esgotar tentativas
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_str = str(e)

            # Verifica se é erro de rate limiting ou overload
            if any(keyword in error_str.lower() for keyword in ['overloaded', 'rate_limit', 'too_many_requests', 'quota']):
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Backoff exponencial
                    logging.warning(f"API sobrecarregada (tentativa {attempt + 1}/{max_retries + 1}). Aguardando {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"API continua sobrecarregada após {max_retries + 1} tentativas")
                    raise Exception(f"API da Anthropic sobrecarregada. Tente novamente em alguns minutos. Erro original: {e}")
            else:
                # Se não é erro de rate limiting, levanta imediatamente
                raise e

    # Não deveria chegar aqui, mas por segurança
    raise Exception("Número máximo de tentativas excedido")



def create_sql_agent_executor(db: SQLDatabase, model_name: str = "gpt-4o-mini", single_table_mode: bool = False, selected_table: str = None, top_k: int = 10):
    """
    Cria um agente SQL usando LangChain com suporte a diferentes provedores

    Args:
        db: Objeto SQLDatabase do LangChain
        model_name: Nome do modelo a usar (OpenAI, Anthropic)
        single_table_mode: Se deve restringir a uma única tabela
        selected_table: Tabela específica para modo único
        top_k: Número máximo de resultados (LIMIT) para queries SQL

    Returns:
        Agente SQL configurado
    """
    try:
        # Se modo tabela única, cria SQLDatabase restrito
        if single_table_mode and selected_table:
            # Cria uma nova instância do SQLDatabase restrita à tabela selecionada
            restricted_db = SQLDatabase.from_uri(
                db._engine.url,
                include_tables=[selected_table]
            )
            logging.info(f"[SQL_AGENT] Criando agente em modo tabela única: {selected_table}")
            db_to_use = restricted_db
        else:
            # Usa o SQLDatabase original (modo multi-tabela)
            logging.info("[SQL_AGENT] Criando agente em modo multi-tabela")
            db_to_use = db

        # Obtém o ID real do modelo
        model_id = AVAILABLE_MODELS.get(model_name, model_name)

        # Cria o modelo LLM baseado no provedor
        if model_id in OPENAI_MODELS:
            # Configurações específicas para modelos OpenAI
            if model_id == "o3-mini":
                # o3-mini não suporta temperature
                llm = ChatOpenAI(model=model_id)
            else:
                # GPT-4o e GPT-4o-mini suportam temperature
                llm = ChatOpenAI(model=model_id, temperature=TEMPERATURE)

            agent_type = "openai-tools"

        elif model_id in ANTHROPIC_MODELS:
            # Claude com tool-calling e configurações para rate limiting
            llm = ChatAnthropic(
                model=model_id,
                temperature=TEMPERATURE,
                max_tokens=4096,
                max_retries=2,  # Retry interno do cliente
                timeout=60.0    # Timeout mais longo
            )
            agent_type = "tool-calling"  # Claude usa tool-calling

        elif model_id in GOOGLE_MODELS:
            # Gemini com tool-calling e configurações otimizadas
            llm = ChatGoogleGenerativeAI(
                model=model_id,
                temperature=TEMPERATURE,
                max_tokens=4096,
                max_retries=2,
                timeout=60.0
            )
            agent_type = "tool-calling"  # Gemini usa tool-calling

        else:
            # Fallback para OpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=TEMPERATURE
            )
            agent_type = "openai-tools"
            logging.warning(f"Modelo {model_name} não reconhecido, usando gpt-4o-mini como fallback")

        # Cria o agente SQL
        sql_agent = create_sql_agent(
            llm=llm,
            db=db_to_use,  # Usa o SQLDatabase apropriado (restrito ou completo)
            agent_type=agent_type,
            verbose=True,
            max_iterations=MAX_ITERATIONS,
            return_intermediate_steps=True,
            top_k=top_k  # Usa o valor dinâmico configurado pelo usuário
        )

        logging.info(f"Agente SQL criado com sucesso usando modelo {model_name} ({model_id}) com agent_type={agent_type}")
        return sql_agent

    except Exception as e:
        logging.error(f"Erro ao criar agente SQL: {e}")
        raise

class SQLAgentManager:
    """
    Gerenciador do agente SQL com funcionalidades avançadas
    """

    def __init__(self, db: SQLDatabase, model_name: str = "gpt-4o-mini", single_table_mode: bool = False, selected_table: str = None, top_k: int = 10):
        self.db = db
        self.model_name = model_name
        self.single_table_mode = single_table_mode
        self.selected_table = selected_table
        self.top_k = top_k
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Inicializa o agente SQL"""
        self.agent = create_sql_agent_executor(self.db, self.model_name, self.single_table_mode, self.selected_table, self.top_k)
    
    def recreate_agent(self, new_db: SQLDatabase = None, new_model: str = None, single_table_mode: bool = None, selected_table: str = None, top_k: int = None):
        """
        Recria o agente com novos parâmetros

        Args:
            new_db: Novo banco de dados (opcional)
            new_model: Novo modelo (opcional)
            single_table_mode: Novo modo de tabela (opcional)
            selected_table: Nova tabela selecionada (opcional)
            top_k: Novo valor de TOP_K para LIMIT (opcional)
        """
        if new_db:
            self.db = new_db
        if new_model:
            self.model_name = new_model
        if single_table_mode is not None:
            self.single_table_mode = single_table_mode
        if selected_table is not None:
            self.selected_table = selected_table
        if top_k is not None:
            self.top_k = top_k

        self._initialize_agent()
        mode_info = f"modo {'tabela única' if self.single_table_mode else 'multi-tabela'}"
        logging.info(f"Agente SQL recriado com modelo {self.model_name} em {mode_info}, TOP_K={self.top_k}")
    
    def _extract_text_from_claude_response(self, output) -> str:
        """
        Extrai texto limpo da resposta do Claude que pode vir em formato complexo

        Args:
            output: Resposta do agente (pode ser string, lista ou dict)

        Returns:
            String limpa com o texto da resposta
        """
        try:
            # Se já é string, retorna diretamente
            if isinstance(output, str):
                return output

            # Se é lista, procura por dicionários com 'text'
            if isinstance(output, list):
                text_parts = []
                for item in output:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)

                if text_parts:
                    return '\n'.join(text_parts)

            # Se é dict, procura por 'text' ou converte para string
            if isinstance(output, dict):
                if 'text' in output:
                    return output['text']
                elif 'content' in output:
                    return str(output['content'])

            # Fallback: converte para string
            return str(output)

        except Exception as e:
            logging.warning(f"Erro ao extrair texto da resposta: {e}")
            return str(output)

    async def execute_query(self, instruction: str) -> dict:
        """
        Executa uma query através do agente SQL com retry para rate limiting

        Args:
            instruction: Instrução para o agente

        Returns:
            Resultado da execução
        """
        try:
            logging.info("------- Agent SQL: Executando query -------")

            # Criar handler para capturar SQL
            sql_handler = SQLQueryCaptureHandler()

            # Verifica se é agente Claude ou Gemini para aplicar retry
            model_id = getattr(self, 'model_name', '')
            is_claude = any(claude_model in model_id for claude_model in ANTHROPIC_MODELS)
            is_gemini = any(gemini_model in model_id for gemini_model in GOOGLE_MODELS)

            if is_claude or is_gemini:
                # Usa retry com backoff para Claude e Gemini
                response = await retry_with_backoff(
                    lambda: self.agent.invoke(
                        {"input": instruction},
                        {"callbacks": [sql_handler]}
                    ),
                    max_retries=3,
                    base_delay=2.0
                )
            else:
                # Execução normal para outros modelos
                response = self.agent.invoke(
                    {"input": instruction},
                    {"callbacks": [sql_handler]}
                )

            # Extrai e limpa a resposta
            raw_output = response.get("output", "Erro ao obter a resposta do agente.")
            clean_output = self._extract_text_from_claude_response(raw_output)

            # Captura a última query SQL executada
            sql_query = sql_handler.get_last_sql_query()

            result = {
                "output": clean_output,
                "intermediate_steps": response.get("intermediate_steps", []),
                "success": True,
                "sql_query": sql_query,  # ← Query SQL capturada
                "all_sql_queries": sql_handler.get_all_sql_queries()
            }

            logging.info(f"Query executada com sucesso: {result['output'][:100]}...")
            return result

        except Exception as e:
            error_str = str(e)

            # Mensagem mais amigável para problemas de rate limiting
            if any(keyword in error_str.lower() for keyword in ['overloaded', 'rate_limit', 'too_many_requests', 'quota']):
                error_msg = (
                    "🚫 **API da Anthropic temporariamente sobrecarregada**\n\n"
                    "A API do Claude está com muitas solicitações no momento. "
                    "Por favor, aguarde alguns minutos e tente novamente.\n\n"
                    "**Sugestões:**\n"
                    "- Aguarde 2-3 minutos antes de tentar novamente\n"
                    "- Considere usar um modelo OpenAI temporariamente\n"
                    "- Tente novamente em horários de menor movimento\n\n"
                    f"*Erro técnico: {e}*"
                )
            else:
                error_msg = f"Erro ao consultar o agente SQL: {e}"

            logging.error(error_msg)
            return {
                "output": error_msg,
                "intermediate_steps": [],
                "success": False
            }

    def get_agent_info(self) -> dict:
        """
        Retorna informações sobre o agente atual
        
        Returns:
            Dicionário com informações do agente
        """
        return {
            "model_name": self.model_name,
            "max_iterations": MAX_ITERATIONS,
            "temperature": TEMPERATURE,
            "database_tables": self.db.get_usable_table_names() if self.db else [],
            "agent_type": "openai-tools"
        }
    
    def validate_agent(self) -> bool:
        """
        Valida se o agente está funcionando corretamente
        
        Returns:
            True se válido, False caso contrário
        """
        try:
            # Testa com uma query simples
            test_result = self.agent.invoke({
                "input": "Quantas linhas existem na tabela?"
            })
            
            success = "output" in test_result and test_result["output"]
            logging.info(f"Validação do agente: {'Sucesso' if success else 'Falha'}")
            return success
            
        except Exception as e:
            logging.error(f"Erro na validação do agente: {e}")
            return False

def get_default_sql_agent(db: SQLDatabase) -> SQLAgentManager:
    """
    Cria um agente SQL com configurações padrão
    
    Args:
        db: Objeto SQLDatabase
        
    Returns:
        SQLAgentManager configurado
    """
    return SQLAgentManager(db)
