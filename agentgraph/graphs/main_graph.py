"""
Grafo principal do LangGraph para o AgentGraph
"""
import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agentgraph.nodes.agent_node import (
    AgentState,
    should_refine_response,
    should_generate_graph,
    should_use_processing_agent,
    should_refine_question,
    route_after_cache_check
)
from agentgraph.nodes.csv_processing_node import csv_processing_node
from agentgraph.nodes.database_node import (
    create_database_from_dataframe_node,
    load_existing_database_node,
    get_database_sample_node
)
from agentgraph.nodes.query_node import (
    validate_query_input_node,
    prepare_query_context_node,
    process_user_query_node,
    should_use_celery_routing
)
from agentgraph.nodes.refinement_node import (
    refine_response_node,
    format_final_response_node
)
from agentgraph.nodes.processing_node import (
    process_initial_context_node,
    validate_processing_input_node
)
from agentgraph.nodes.cache_node import (
    check_cache_node,
    cache_response_node,
    update_history_node
)
from agentgraph.nodes.graph_selection_node import graph_selection_node
from agentgraph.nodes.graph_generation_node import graph_generation_node
from agentgraph.nodes.custom_nodes import CustomNodeManager
from agentgraph.nodes.connection_selection_node import (
    connection_selection_node,
    validate_connection_input_node,
    route_by_connection_type
)
from agentgraph.nodes.history_retrieval_node import (
    history_retrieval_node_sync,
    should_retrieve_history
)
from agentgraph.nodes.history_capture_node import (
    history_capture_node,  # ASYNC - CORRETO PARA APIs
    should_capture_history
)
from agentgraph.nodes.celery_polling_node import (
    celery_task_dispatch_node
)
from agentgraph.nodes.postgresql_connection_node import postgresql_connection_node
from agentgraph.nodes.clickhouse_connection_node import clickhouse_connection_node
from agentgraph.nodes.question_refinement_node import question_refinement_node, route_after_question_refinement
from agentgraph.agents.sql_agent import SQLAgentManager
from agentgraph.agents.tools import CacheManager
from agentgraph.utils.database import create_sql_database
from agentgraph.utils.config import get_active_csv_path, SQL_DB_PATH
from agentgraph.utils.object_manager import get_object_manager

class AgentGraphManager:
    """
    Gerenciador principal do grafo LangGraph
    """
    
    def __init__(self, external_engine_id=None, external_db_id=None):
        self.graph = None
        self.app = None
        self.cache_manager = CacheManager()
        self.custom_node_manager = CustomNodeManager()
        self.object_manager = get_object_manager()
        self.engine = None
        self.sql_agent = None
        self.db = None
        # IDs para objetos não-serializáveis
        self.agent_id = None
        self.engine_id = external_engine_id  # Pode usar engine externo
        self.db_id = external_db_id  # Pode usar database externo
        self.cache_id = None

        # Se não há objetos externos, inicializar sistema padrão
        if not external_engine_id or not external_db_id:
            self._initialize_system()
        else:
            # Usar objetos externos
            self._use_external_objects()

        self._build_graph()

    def _use_external_objects(self):
        """Usa objetos externos (engine e database) fornecidos pela API"""
        try:
            logging.info(f"[GRAPH_MANAGER] Usando objetos externos: engine_id={self.engine_id}, db_id={self.db_id}")

            # Recuperar objetos do ObjectManager
            self.engine = self.object_manager.get_engine(self.engine_id)
            self.db = self.object_manager.get_database(self.db_id)

            if not self.engine or not self.db:
                raise Exception(f"Objetos externos não encontrados: engine={self.engine}, db={self.db}")

            # Criar SQL Agent usando o database externo
            from agentgraph.utils.config import DEFAULT_TOP_K
            from agentgraph.agents.sql_agent import SQLAgentManager

            self.sql_agent = SQLAgentManager(self.db, single_table_mode=False, selected_table=None, top_k=DEFAULT_TOP_K)

            # Armazenar SQL Agent
            self.agent_id = self.object_manager.store_sql_agent(self.sql_agent, self.db_id)
            self.cache_id = self.object_manager.store_cache_manager(self.cache_manager)

            logging.info(f"[GRAPH_MANAGER] Objetos externos configurados com sucesso")

        except Exception as e:
            logging.error(f"[GRAPH_MANAGER] Erro ao usar objetos externos: {e}")
            # Fallback para inicialização padrão
            logging.info("[GRAPH_MANAGER] Fazendo fallback para inicialização padrão")
            self._initialize_system()

    def _initialize_system(self):
        """Inicializa o sistema com banco e agente padrão"""
        try:
            # Para inicialização síncrona, vamos usar load_existing_database_node de forma síncrona
            # ou criar uma versão síncrona temporária
            import os
            from sqlalchemy import create_engine

            # Verifica se banco existe
            if os.path.exists(SQL_DB_PATH):
                # Carrega banco existente
                self.engine = create_engine(f"sqlite:///{SQL_DB_PATH}")
                db = create_sql_database(self.engine)
                logging.info("Banco existente carregado")
            else:
                # Cria novo banco usando função síncrona temporária
                csv_path = get_active_csv_path()
                self.engine = self._create_engine_sync(csv_path)
                db = create_sql_database(self.engine)
                logging.info("Novo banco criado")

            # Armazena banco de dados
            self.db = db
            self.db_id = self.object_manager.store_database(db)

            # Cria agente SQL (modo padrão multi-tabela)
            from agentgraph.utils.config import DEFAULT_TOP_K
            self.sql_agent = SQLAgentManager(db, single_table_mode=False, selected_table=None, top_k=DEFAULT_TOP_K)

            # Armazena objetos no gerenciador
            self.agent_id = self.object_manager.store_sql_agent(self.sql_agent, self.db_id)
            self.engine_id = self.object_manager.store_engine(self.engine)
            self.cache_id = self.object_manager.store_cache_manager(self.cache_manager)

            logging.info("Sistema inicializado com sucesso")

        except Exception as e:
            logging.error(f"Erro ao inicializar sistema: {e}")
            raise

    def _create_engine_sync(self, csv_path: str):
        """
        Cria engine de forma síncrona para inicialização
        NOTA: Esta função será removida em favor dos nós específicos
        """
        import asyncio
        from sqlalchemy import create_engine

        # Usa nós específicos para processamento
        async def process_csv_sync():
            # Processa CSV usando nó específico
            csv_state = {
                "file_path": csv_path,
                "success": False,
                "message": "",
                "csv_data_sample": {},
                "column_info": {},
                "processing_stats": {}
            }

            csv_result = await csv_processing_node(csv_state)
            if not csv_result["success"]:
                raise Exception(csv_result["message"])

            # Cria banco usando nó específico
            db_result = await create_database_from_dataframe_node(csv_result)
            if not db_result["success"]:
                raise Exception(db_result["message"])

            # Recupera engine criada
            engine_id = db_result["engine_id"]
            engine = self.object_manager.get_engine(engine_id)

            return engine, engine_id, db_result["db_id"]

        # Executa de forma síncrona com verificação de event loop
        try:
            # Verifica se já existe um event loop rodando
            try:
                loop = asyncio.get_running_loop()
                # Se chegou aqui, há um loop rodando - não pode usar asyncio.run
                logging.warning("Event loop já rodando - usando fallback síncrono")
                raise Exception("Event loop conflict")
            except RuntimeError:
                # Não há event loop rodando - pode usar asyncio.run
                engine, engine_id, db_id = asyncio.run(process_csv_sync())
                self.engine_id = engine_id
                self.db_id = db_id
                logging.info("Banco criado usando nós específicos")
                return engine
        except Exception as e:
            logging.error(f"Erro ao criar engine usando nós: {e}")
            # Fallback síncrono simples
            logging.info("Usando fallback síncrono para criação do banco")
            engine = create_engine(f"sqlite:///{SQL_DB_PATH}")
            return engine
    
    def _build_graph(self):
        """Constrói o grafo LangGraph com nova arquitetura"""
        try:
            # Cria o StateGraph
            workflow = StateGraph(AgentState)

            # Adiciona nós de validação e preparação
            workflow.add_node("validate_input", validate_query_input_node)
            workflow.add_node("check_cache", check_cache_node)

            # Adiciona nó de refinamento de pergunta
            workflow.add_node("question_refinement", question_refinement_node)

            # Adiciona nós de conexão
            workflow.add_node("connection_selection", connection_selection_node)
            workflow.add_node("validate_connection", validate_connection_input_node)
            workflow.add_node("postgresql_connection", postgresql_connection_node)
            workflow.add_node("clickhouse_connection", clickhouse_connection_node)
            workflow.add_node("csv_processing", csv_processing_node)
            workflow.add_node("create_database", create_database_from_dataframe_node)
            workflow.add_node("load_database", load_existing_database_node)

            workflow.add_node("validate_processing", validate_processing_input_node)
            workflow.add_node("process_initial_context", process_initial_context_node)
            workflow.add_node("prepare_context", prepare_query_context_node)
            workflow.add_node("get_db_sample", get_database_sample_node)

            # Adiciona nós de processamento
            workflow.add_node("process_query", process_user_query_node)

            # Adiciona nó do Celery (apenas dispatch)
            workflow.add_node("celery_dispatch", celery_task_dispatch_node)

            # Adiciona nós de gráficos
            workflow.add_node("graph_selection", graph_selection_node)
            workflow.add_node("graph_generation", graph_generation_node)

            # Adiciona nós de refinamento
            workflow.add_node("refine_response", refine_response_node)
            workflow.add_node("format_response", format_final_response_node)

            # Adiciona nós de histórico
            workflow.add_node("history_retrieval", history_retrieval_node_sync)
            workflow.add_node("history_capture", history_capture_node)  # ASYNC - CORRETO

            # Adiciona nós de cache e histórico
            workflow.add_node("cache_response", cache_response_node)
            workflow.add_node("update_history", update_history_node)

            # Define ponto de entrada
            workflow.set_entry_point("validate_input")

            # Fluxo principal
            workflow.add_edge("validate_input", "check_cache")

            # Condicional para cache hit ou recuperação de histórico
            workflow.add_conditional_edges(
                "check_cache",
                route_after_cache_check,
                {
                    "update_history": "update_history",
                    "history_retrieval": "history_retrieval",  # Novo: busca histórico
                    "question_refinement": "question_refinement",
                    "validate_processing": "validate_processing",
                    "connection_selection": "connection_selection"
                }
            )

            # Condicional para decidir se busca histórico ou pula
            workflow.add_conditional_edges(
                "history_retrieval",
                should_retrieve_history,
                {
                    # Após a recuperação (ou decisão de pular), sempre continuamos o fluxo
                    # O nó de recuperação já preenche state["history_context"] quando aplicável
                    "retrieve_history": "question_refinement",
                    "skip_history": "question_refinement"
                }
            )

            # Fluxo do refinamento de pergunta
            workflow.add_edge("question_refinement", "validate_processing")

            # Fluxo do Processing Agent
            workflow.add_edge("validate_processing", "process_initial_context")
            workflow.add_edge("process_initial_context", "prepare_context")
            workflow.add_edge("prepare_context", "connection_selection")

            # Fluxo de seleção de conexão
            workflow.add_edge("connection_selection", "validate_connection")

            # Roteamento por tipo de conexão (apenas se necessário)
            workflow.add_conditional_edges(
                "validate_connection",
                route_by_connection_type,
                {
                    "postgresql_connection": "postgresql_connection",
                    "clickhouse_connection": "clickhouse_connection",
                    "csv_processing": "csv_processing",
                    "load_database": "load_database",
                    "get_db_sample": "get_db_sample"  # Pula conexão se já existe
                }
            )

            # Fluxos específicos de conexão (apenas quando necessário)
            workflow.add_edge("postgresql_connection", "get_db_sample")
            workflow.add_edge("clickhouse_connection", "get_db_sample")
            workflow.add_edge("csv_processing", "create_database")
            workflow.add_edge("create_database", "get_db_sample")
            workflow.add_edge("load_database", "get_db_sample")
            workflow.add_edge("get_db_sample", "process_query")

            # Condicional para Celery ou fluxo tradicional (após process_query)
            workflow.add_conditional_edges(
                "process_query",
                should_use_celery_routing,
                {
                    "celery_dispatch": "celery_dispatch",
                    "graph_selection": "graph_selection",
                    "refine_response": "refine_response",
                    "format_response": "format_response"  # Sempre formatar antes do cache
                }
            )

            # Fluxo do Celery - direto para próximo passo após dispatch
            workflow.add_conditional_edges(
                "celery_dispatch",
                should_generate_graph,
                {
                    "graph_selection": "graph_selection",
                    "refine_response": "refine_response",
                    "format_response": "format_response"  # Sempre formatar antes do cache
                }
            )

            # Fluxo dos gráficos
            workflow.add_edge("graph_selection", "graph_generation")

            # Após geração de gráfico, vai para refinamento ou formatação
            workflow.add_conditional_edges(
                "graph_generation",
                should_refine_response,
                {
                    "refine_response": "refine_response",
                    "format_response": "format_response"  # Sempre formatar antes do cache
                }
            )

            workflow.add_edge("refine_response", "format_response")

            # Condicional para capturar histórico antes do cache
            workflow.add_conditional_edges(
                "format_response",
                should_capture_history,
                {
                    "capture_history": "history_capture",
                    "skip_capture": "cache_response"
                }
            )

            workflow.add_edge("history_capture", "cache_response")
            workflow.add_edge("cache_response", "update_history")
            workflow.add_edge("update_history", END)

            # Compila o grafo
            memory = MemorySaver()
            self.app = workflow.compile(checkpointer=memory)

            logging.info("Grafo LangGraph construído com sucesso")

        except Exception as e:
            logging.error(f"Erro ao construir grafo: {e}")
            raise
    
    async def process_query(
        self,
        user_input: str,
        selected_model: str = "GPT-4o-mini",
        advanced_mode: bool = False,
        processing_enabled: bool = False,
        processing_model: str = "GPT-4o-mini",
        question_refinement_enabled: bool = False,
        connection_type: str = "csv",
        postgresql_config: Optional[Dict] = None,
        selected_table: str = None,
        single_table_mode: bool = False,
        top_k: int = 10,
        use_celery: bool = False,
        thread_id: str = "default",
        user_id: Optional[int] = None,
        chat_session_id: Optional[int] = None,
        engine_id: Optional[str] = None,
        db_id: Optional[str] = None,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processa uma query do usuário através do grafo

        Args:
            user_input: Entrada do usuário
            selected_model: Modelo LLM selecionado
            advanced_mode: Se deve usar refinamento avançado
            processing_enabled: Se deve usar o Processing Agent
            processing_model: Modelo para o Processing Agent
            question_refinement_enabled: Se deve usar refinamento de perguntas
            connection_type: Tipo de conexão (csv, postgresql)
            postgresql_config: Configuração PostgreSQL (se aplicável)
            selected_table: Tabela selecionada (se aplicável)
            single_table_mode: Se está em modo de tabela única
            top_k: Número máximo de resultados
            use_celery: Se deve usar Celery para processamento
            thread_id: ID da thread para checkpointing
            user_id: ID do usuário (para histórico)
            chat_session_id: ID da sessão de chat (para histórico)
            engine_id: ID do engine SQLAlchemy (para API)
            db_id: ID do database (para API)
            run_id: ID da run (para histórico)
            processing_model: Modelo para o Processing Agent
            connection_type: Tipo de conexão ("csv" ou "postgresql")
            postgresql_config: Configuração PostgreSQL (se aplicável)
            selected_table: Tabela selecionada (para PostgreSQL)
            single_table_mode: Se deve usar apenas uma tabela (PostgreSQL)
            top_k: Número máximo de resultados (LIMIT) para queries SQL
            use_celery: Se deve usar Celery para processamento assíncrono
            thread_id: ID da thread para checkpoint

        Returns:
            Resultado do processamento
        """
        try:
            # Log simples
            logging.info(f"[MAIN_GRAPH] Celery: {use_celery}")

            # Verifica se precisa recriar agente SQL com modelo diferente
            current_sql_agent = self.object_manager.get_sql_agent(self.agent_id)
            if current_sql_agent and current_sql_agent.model_name != selected_model:
                logging.info(f"Recriando agente SQL com modelo {selected_model}")

                # Recupera banco de dados associado ao agente
                db_id = self.object_manager.get_db_id_for_agent(self.agent_id)
                if db_id:
                    db = self.object_manager.get_database(db_id)
                    if db:
                        new_sql_agent = SQLAgentManager(db, selected_model, single_table_mode=False, selected_table=None, top_k=top_k)
                        self.agent_id = self.object_manager.store_sql_agent(new_sql_agent, db_id)
                        logging.info(f"Agente SQL recriado com sucesso para modelo {selected_model}")
                    else:
                        logging.error("Banco de dados não encontrado para recriar agente")
                else:
                    logging.error("ID do banco de dados não encontrado para o agente")

            # Log simplificado
            logging.info(f"[MAIN_GRAPH] Processando: {user_input[:50]}...")
            logging.info(f"[MAIN GRAPH] Single table mode: {single_table_mode}")

            # Prepara estado inicial com IDs serializáveis
            import os
            history_enabled_flag = os.getenv("HISTORY_ENABLED", "true").lower() == "true"

            initial_state = {
                "user_input": user_input,
                "selected_model": selected_model,
                "response": "",
                "advanced_mode": advanced_mode,
                "execution_time": 0.0,
                "error": None,
                "intermediate_steps": [],
                "db_sample_dict": {},
                # IDs para recuperar objetos não-serializáveis
                "agent_id": self.agent_id,
                "engine_id": engine_id or self.engine_id,  # Usar engine_id passado ou o padrão
                "db_id": db_id or self.db_id,  # Usar db_id passado ou o padrão
                "cache_id": self.cache_id,
                # Campos relacionados ao histórico/conversa
                "user_id": user_id,
                "chat_session_id": chat_session_id,
                "run_id": run_id,
                # Campos relacionados a gráficos
                "query_type": "sql_query",  # Será atualizado pela detecção
                "sql_query_extracted": None,
                "graph_type": None,
                "graph_data": None,
                "graph_image_id": None,
                "graph_generated": False,
                "graph_error": None,
                # Campos relacionados ao cache
                "cache_hit": False,
                # Campos relacionados ao Processing Agent
                "processing_enabled": processing_enabled,
                "processing_model": processing_model,
                "processing_agent_id": None,
                "suggested_query": None,
                "query_observations": None,
                "processing_result": None,
                "processing_success": False,
                "processing_error": None,
                # Campos relacionados ao Question Refinement
                "question_refinement_enabled": question_refinement_enabled,
                "original_user_input": None,
                "refined_question": None,
                "question_refinement_applied": False,
                "question_refinement_changes": [],
                "question_refinement_justification": None,
                "question_refinement_success": False,
                "question_refinement_error": None,
                "question_refinement_has_significant_change": False,
                # Campos relacionados ao refinamento
                "refined": False,
                "refinement_error": None,
                "refinement_quality": None,
                "quality_metrics": None,
                # Campos relacionados ao contexto SQL
                "sql_context": None,
                "sql_result": None,
                # Campos relacionados ao tipo de conexão
                "connection_type": connection_type,
                "postgresql_config": postgresql_config,
                "selected_table": selected_table,
                "single_table_mode": single_table_mode,
                "connection_success": self.db_id is not None,  # True se já tem conexão
                "connection_error": None,
                "connection_info": None,
                # Configuração do agente SQL
                "top_k": top_k,
                # Configuração do Celery
                "use_celery": use_celery,
                "ready_for_celery_dispatch": False,
                "celery_task_id": None,
                "celery_task_status": None,
                # Campos relacionados ao histórico (IDs)
                "user_id": user_id,
                "chat_session_id": chat_session_id,
                "run_id": run_id,
                # Campos relacionados ao histórico (conteúdo/flags)
                "history_enabled": history_enabled_flag,
                "history_retrieved": False,
                "history_context": "",
                "relevant_history": [],
                "has_history": False,
                "history_error": None,
            }

            # DEBUG: Log dos valores de histórico
            logging.info(f"[MAIN_GRAPH] DEBUG - Estado inicial: user_id={user_id}, chat_session_id={chat_session_id}, run_id={run_id}")
            logging.info(f"[MAIN_GRAPH] DEBUG - Campos no estado inicial: {list(initial_state.keys())}")
            logging.info(f"[MAIN_GRAPH] DEBUG - user_id no estado: {initial_state.get('user_id')}")
            logging.info(f"[MAIN_GRAPH] DEBUG - chat_session_id no estado: {initial_state.get('chat_session_id')}")
            logging.info(f"[MAIN_GRAPH] DEBUG - run_id no estado: {initial_state.get('run_id')}")
        
            # Executa o grafo com limite de recursão aumentado
            config = {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 100  # Aumenta limite para polling do Celery
            }
            result = await self.app.ainvoke(initial_state, config=config)
            
            logging.info(f"[MAIN_GRAPH] ✅ Processada: {user_input[:50]}...")
            return result
            
        except Exception as e:
            error_msg = f"Erro ao processar query: {e}"
            logging.error(error_msg)
            return {
                "user_input": user_input,
                "response": error_msg,
                "error": error_msg,
                "execution_time": 0.0
            }

# Instância global do gerenciador
_graph_manager: Optional[AgentGraphManager] = None

def get_graph_manager() -> AgentGraphManager:
    """
    Retorna instância singleton do gerenciador de grafo
    
    Returns:
        AgentGraphManager
    """
    global _graph_manager
    if _graph_manager is None:
        _graph_manager = AgentGraphManager()
    return _graph_manager

async def initialize_graph() -> AgentGraphManager:
    """
    Inicializa o grafo principal
    
    Returns:
        AgentGraphManager inicializado
    """
    try:
        manager = get_graph_manager()
        
        # Valida sistema usando CustomNodeManager
        validation = await manager.custom_node_manager.validate_system(
            manager.agent_id,
            manager.engine_id,
            manager.cache_id
        )
        if not validation.get("overall_valid", False):
            logging.warning("Sistema não passou na validação completa")
        
        logging.info("Grafo principal inicializado e validado")
        return manager
        
    except Exception as e:
        logging.error(f"Erro ao inicializar grafo: {e}")
        raise

# Classe GraphManager removida - funcionalidade movida para AgentGraphManager
