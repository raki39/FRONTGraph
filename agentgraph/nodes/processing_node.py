"""
Nó para processamento de contexto inicial usando Processing Agent
"""
import logging
import pandas as pd
from typing import Dict, Any

from agentgraph.agents.processing_agent import ProcessingAgentManager
from agentgraph.agents.tools import prepare_processing_context
from agentgraph.utils.object_manager import get_object_manager


async def process_initial_context_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para processar contexto inicial com Processing Agent (opcional)
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com contexto processado
    """
    # Verifica se o processing está habilitado
    processing_enabled = state.get("processing_enabled", False)
    logging.info(f"[PROCESSING NODE] Processing enabled: {processing_enabled}")

    if not processing_enabled:
        logging.info("[PROCESSING NODE] Processing Agent desabilitado - pulando nó")
        return state

    logging.info("[PROCESSING NODE] ===== INICIANDO NÓ DE PROCESSAMENTO =====")
    
    try:
        user_input = state.get("user_input", "")
        processing_model = state.get("processing_model", "gpt-4o-mini")

        logging.info(f"[PROCESSING NODE] Entrada do usuário: {user_input[:100]}...")
        logging.info(f"[PROCESSING NODE] Modelo selecionado: {processing_model}")

        if not user_input:
            logging.warning("[PROCESSING NODE] Entrada do usuário não disponível")
            return state
        
        # Acessa o banco de dados correto baseado no estado atual
        obj_manager = get_object_manager()

        try:
            # Usa os IDs específicos do estado atual (não o primeiro disponível)
            engine_id = state.get("engine_id")
            db_id = state.get("db_id")

            logging.info(f"[PROCESSING NODE] ===== DEBUG ESTADO =====")
            logging.info(f"[PROCESSING NODE] engine_id do estado: {engine_id}")
            logging.info(f"[PROCESSING NODE] db_id do estado: {db_id}")
            logging.info(f"[PROCESSING NODE] connection_type do estado: {state.get('connection_type')}")
            logging.info(f"[PROCESSING NODE] Chaves disponíveis no estado: {list(state.keys())}")
            logging.info(f"[PROCESSING NODE] ===== FIM DEBUG =====")

            if not engine_id or not db_id:
                logging.error("[PROCESSING NODE] IDs de engine ou database não encontrados no estado")
                logging.error(f"[PROCESSING NODE] engine_id: {engine_id}, db_id: {db_id}")

                # Fallback: tenta usar os IDs disponíveis no ObjectManager
                logging.info("[PROCESSING NODE] Tentando fallback para IDs disponíveis...")
                engines = obj_manager._engines
                databases = obj_manager._databases

                if engines and databases:
                    engine_id = list(engines.keys())[-1]  # Pega o último (mais recente)
                    db_id = list(databases.keys())[-1]    # Pega o último (mais recente)
                    logging.info(f"[PROCESSING NODE] Fallback: usando engine_id={engine_id}, db_id={db_id}")
                else:
                    logging.error("[PROCESSING NODE] Nenhum engine ou database disponível no ObjectManager")
                    return state

            # Obtém engine e database específicos do estado atual
            engine = obj_manager.get_engine(engine_id)
            database = obj_manager.get_database(db_id)

            logging.info(f"[PROCESSING NODE] Engine obtido: {engine is not None}")
            logging.info(f"[PROCESSING NODE] Database obtido: {database is not None}")

            if not engine or not database:
                logging.error("[PROCESSING NODE] Engine ou database não encontrados no ObjectManager")
                logging.error(f"[PROCESSING NODE] engine: {engine}, database: {database}")
                logging.error(f"[PROCESSING NODE] Engines disponíveis: {list(obj_manager._engines.keys())}")
                logging.error(f"[PROCESSING NODE] Databases disponíveis: {list(obj_manager._databases.keys())}")
                return state

            logging.info(f"[PROCESSING NODE] Usando engine {engine_id} e database {db_id} do estado atual")

            # Detecta o tipo de engine baseado no dialect
            engine_dialect = str(engine.dialect.name).lower()
            connection_type = state.get("connection_type", "csv")
            single_table_mode = state.get("single_table_mode", False)
            selected_table = state.get("selected_table")

            logging.info(f"[PROCESSING NODE] ===== DETECÇÃO DE CONEXÃO =====")
            logging.info(f"[PROCESSING NODE] Engine dialect detectado: {engine_dialect}")
            logging.info(f"[PROCESSING NODE] Connection type do estado: {connection_type}")
            logging.info(f"[PROCESSING NODE] Single table mode: {single_table_mode}")
            logging.info(f"[PROCESSING NODE] Selected table: {selected_table}")
            logging.info(f"[PROCESSING NODE] Engine URL: {str(engine.url)}")
            logging.info(f"[PROCESSING NODE] ===== FIM DETECÇÃO =====")

            # Validação: engine dialect deve corresponder ao connection_type
            if connection_type.lower() == "postgresql" and engine_dialect != "postgresql":
                logging.error(f"[PROCESSING NODE] INCONSISTÊNCIA: connection_type={connection_type} mas engine_dialect={engine_dialect}")
                logging.error(f"[PROCESSING NODE] Isso indica que está usando o engine errado!")
            elif connection_type.lower() == "csv" and engine_dialect != "sqlite":
                logging.error(f"[PROCESSING NODE] INCONSISTÊNCIA: connection_type={connection_type} mas engine_dialect={engine_dialect}")
                logging.error(f"[PROCESSING NODE] Isso indica que está usando o engine errado!")

            # NOVA IMPLEMENTAÇÃO: Cria dados das colunas baseado no tipo de conexão
            columns_data = {}
            import sqlalchemy as sa

            if engine_dialect == "postgresql":
                # Para PostgreSQL, processa baseado no modo
                if single_table_mode and selected_table:
                    # Modo tabela única - processa APENAS a tabela selecionada
                    logging.info(f"[PROCESSING NODE] PostgreSQL - Modo tabela única: {selected_table}")
                    columns_data[selected_table] = _extract_table_columns_info(engine, selected_table)

                else:
                    # Modo multi-tabela - processa TODAS as tabelas disponíveis
                    logging.info(f"[PROCESSING NODE] PostgreSQL - Modo multi-tabela")

                    # Obtém lista de todas as tabelas
                    with engine.connect() as conn:
                        tables_result = conn.execute(sa.text("""
                            SELECT table_name
                            FROM information_schema.tables
                            WHERE table_schema = 'public'
                            ORDER BY table_name
                        """))
                        available_tables = [row[0] for row in tables_result.fetchall()]

                    logging.info(f"[PROCESSING NODE] Tabelas encontradas: {available_tables}")

                    # Processa cada tabela (máximo 5 para performance)
                    for table_name in available_tables[:20]:
                        columns_data[table_name] = _extract_table_columns_info(engine, table_name)

            else:
                # Para SQLite (CSV convertido), processa tabela padrão
                logging.info(f"[PROCESSING NODE] SQLite - processando tabela padrão")
                columns_data["tabela"] = _extract_table_columns_info(engine, "tabela")

            logging.info(f"[PROCESSING NODE] ✅ Dados das colunas extraídos para {len(columns_data)} tabela(s)")

        except Exception as e:
            logging.error(f"[PROCESSING NODE] ❌ Erro ao acessar banco de dados: {e}")
            logging.error(f"[PROCESSING NODE] Detalhes do erro: {str(e)}")
            logging.error(f"[PROCESSING NODE] Tipo do erro: {type(e)}")
            import traceback
            logging.error(f"[PROCESSING NODE] Traceback: {traceback.format_exc()}")
            return state
        
        # Recupera ou cria Processing Agent
        processing_agent_id = state.get("processing_agent_id")
        
        if processing_agent_id:
            processing_agent = obj_manager.get_processing_agent(processing_agent_id)
            # Verifica se precisa recriar com modelo diferente
            if processing_agent and processing_agent.model_name != processing_model:
                logging.info(f"[PROCESSING NODE] Recriando Processing Agent com modelo {processing_model}")
                processing_agent.recreate_llm(processing_model)
            else:
                logging.info(f"[PROCESSING NODE] Reutilizando Processing Agent existente com modelo {processing_agent.model_name}")
        else:
            # Cria novo Processing Agent
            logging.info(f"[PROCESSING NODE] Criando novo Processing Agent com modelo {processing_model}")
            processing_agent = ProcessingAgentManager(processing_model)
            processing_agent_id = obj_manager.store_processing_agent(processing_agent)
            state["processing_agent_id"] = processing_agent_id
            logging.info(f"[PROCESSING NODE] Novo Processing Agent criado e armazenado com ID: {processing_agent_id}")
        
        # Prepara contexto para o Processing Agent com dados já processados
        connection_type = state.get("connection_type", "csv")
        single_table_mode = state.get("single_table_mode", False)
        selected_table = state.get("selected_table")

        # Obtém lista de tabelas disponíveis se for PostgreSQL
        available_tables = None
        if engine_dialect == "postgresql":
            available_tables = list(columns_data.keys())
            logging.info(f"[PROCESSING NODE] Tabelas disponíveis para contexto: {available_tables}")

        # Obtém contexto histórico (se disponível)
        history_context = state.get("history_context", "")
        try:
            logging.info("[PROCESSING NODE] Inspecting history context in state...")
            logging.info(f"[PROCESSING NODE] history flags: enabled={state.get('history_enabled')}, retrieved={state.get('history_retrieved')}, has_history={state.get('has_history')}")
            hlen = len(history_context) if history_context is not None else 0
            logging.info(f"[PROCESSING NODE] history_context len={hlen}")
            if history_context and history_context.strip():
                # Preview das primeiras linhas
                preview_lines = [ln for ln in history_context.split('\n') if ln.strip()][:6]
                logging.info("[PROCESSING NODE] PREVIEW DO HISTORICO NO STATE:")
                for ln in preview_lines:
                    logging.info(f"[PROCESSING NODE]    {ln}")
            else:
                logging.info("[PROCESSING NODE] history_context esta vazio/branco no state")
        except Exception:
            logging.info("[PROCESSING NODE] erro ao inspecionar history_context no state")

        # NOVA CHAMADA: Passa dados já processados em vez de fazer consultas redundantes
        processing_context = prepare_processing_context(
            user_input,
            columns_data,  # Dados já processados das colunas
            connection_type,
            single_table_mode,
            selected_table,
            available_tables,
            history_context  # NOVO: Inclui histórico
        )

        logging.info(f"[PROCESSING NODE] ===== CONTEXTO PARA PRIMEIRA LLM =====")
        logging.info(f"{processing_context}")
        logging.info(f"[PROCESSING NODE] ===== FIM DO CONTEXTO =====")

        # DEBUG: Verificar se há histórico no estado e no contexto
        chat_session_id = state.get("chat_session_id")
        user_id = state.get("user_id")
        logging.info(f"[PROCESSING NODE] 🔍 VERIFICANDO HISTÓRICO - chat_session_id: {chat_session_id}, user_id: {user_id}")

        if chat_session_id and user_id:
            logging.info(f"[PROCESSING NODE] 📚 HISTÓRICO DISPONÍVEL - Deveria estar no contexto!")
            # Verificar se o histórico está realmente no contexto
            if "HISTÓRICO" in processing_context or "histórico" in processing_context:
                logging.info(f"[PROCESSING NODE] ✅ HISTÓRICO ENCONTRADO NO CONTEXTO!")
            else:
                logging.info(f"[PROCESSING NODE] ❌ HISTÓRICO NÃO ENCONTRADO NO CONTEXTO!")
        else:
            logging.info(f"[PROCESSING NODE] ❌ SEM DADOS DE HISTÓRICO - chat_session_id ou user_id ausentes")

        # Executa processamento
        logging.info(f"[PROCESSING NODE] 🚀 Iniciando execução do Processing Agent...")
        logging.info(f"[PROCESSING NODE] Processing Agent: {processing_agent}")
        logging.info(f"[PROCESSING NODE] Modelo: {processing_agent.model_name if processing_agent else 'N/A'}")

        try:
            processing_result = await processing_agent.process_context(processing_context)
            logging.info(f"[PROCESSING NODE] ✅ Processing Agent executado com sucesso")
        except Exception as e:
            logging.error(f"[PROCESSING NODE] ❌ Erro na execução do Processing Agent: {e}")
            import traceback
            logging.error(f"[PROCESSING NODE] Traceback: {traceback.format_exc()}")
            return state

        # Log da resposta da primeira LLM
        logging.info(f"[PROCESSING NODE] ===== RESPOSTA DA PRIMEIRA LLM =====")
        logging.info(f"{processing_result.get('output', 'Sem resposta')}")
        logging.info(f"[PROCESSING NODE] ===== FIM DA RESPOSTA =====")

        if processing_result["success"]:
            # Extrai query sugerida e observações
            suggested_query = processing_result.get("suggested_query", "")
            query_observations = processing_result.get("query_observations", "")

            # Atualiza estado com resultados do processamento
            state.update({
                "suggested_query": suggested_query,
                "query_observations": query_observations,
                "processing_result": processing_result,
                "processing_success": True
            })
            
            # Log simples do resultado
            if suggested_query:
                logging.info(f"[PROCESSING NODE] ✅ Query SQL extraída com sucesso")
                logging.info(f"[PROCESSING NODE] ✅ Observações extraídas: {len(query_observations)} caracteres")
                logging.info(f"[PROCESSING NODE] 🎯 Query será incluída no contexto do SQL Agent")
            else:
                logging.warning(f"[PROCESSING NODE] ❌ Nenhuma query foi extraída - agente SQL funcionará normalmente")
            
        else:
            # Em caso de erro, continua sem processamento
            error_msg = processing_result.get("output", "Erro desconhecido")
            logging.error(f"[PROCESSING] Erro no processamento: {error_msg}")

            state.update({
                "suggested_query": "",
                "query_observations": "",
                "processing_result": processing_result,
                "processing_success": False,
                "processing_error": error_msg
            })
        
    except Exception as e:
        error_msg = f"Erro no nó de processamento: {e}"
        logging.error(f"[PROCESSING] {error_msg}")
        
        # Em caso de erro, continua sem processamento
        state.update({
            "suggested_query": "",
            "query_observations": "",
            "processing_success": False,
            "processing_error": error_msg
        })
    
    return state


def should_use_processing(state: Dict[str, Any]) -> str:
    """
    Determina se deve usar o Processing Agent
    
    Args:
        state: Estado atual
        
    Returns:
        Nome do próximo nó
    """
    if state.get("processing_enabled", False):
        return "process_initial_context"
    else:
        return "prepare_context"


async def validate_processing_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida entrada para o Processing Agent

    Args:
        state: Estado atual

    Returns:
        Estado validado
    """
    try:
        logging.info("[PROCESSING VALIDATION] ===== VALIDANDO ENTRADA PARA PROCESSING AGENT =====")

        # Verifica se processing está habilitado
        processing_enabled = state.get("processing_enabled", False)
        logging.info(f"[PROCESSING VALIDATION] Processing habilitado: {processing_enabled}")

        if not processing_enabled:
            logging.info("[PROCESSING VALIDATION] Processing desabilitado - pulando validação")
            return state

        # Valida modelo de processamento
        processing_model = state.get("processing_model", "")
        logging.info(f"[PROCESSING VALIDATION] Modelo especificado: '{processing_model}'")

        if not processing_model:
            logging.warning("[PROCESSING VALIDATION] Modelo de processamento não especificado, usando padrão")
            state["processing_model"] = "gpt-4o-mini"
            logging.info(f"[PROCESSING VALIDATION] Modelo padrão definido: gpt-4o-mini")

        # Valida entrada do usuário
        user_input = state.get("user_input", "")
        if not user_input or not user_input.strip():
            logging.error("[PROCESSING VALIDATION] Entrada do usuário vazia - desabilitando processing")
            state["processing_enabled"] = False
            return state

        logging.info(f"[PROCESSING VALIDATION] Validação concluída com sucesso")
        logging.info(f"[PROCESSING VALIDATION] Modelo final: {state['processing_model']}")
        logging.info(f"[PROCESSING VALIDATION] Entrada: {user_input[:100]}...")

    except Exception as e:
        logging.error(f"[PROCESSING VALIDATION] Erro na validação: {e}")
        state["processing_enabled"] = False

    return state


def _extract_table_columns_info(engine, table_name: str) -> list:
    """
    Extrai informações das colunas de uma tabela específica

    Args:
        engine: Engine SQLAlchemy
        table_name: Nome da tabela

    Returns:
        Lista de dicionários com informações das colunas
    """
    import sqlalchemy as sa
    import pandas as pd

    try:
        logging.info(f"[PROCESSING NODE] Extraindo informações da tabela: {table_name}")

        with engine.connect() as conn:
            # Primeiro, tenta obter dados da tabela (máximo 5 linhas)
            try:
                result = conn.execute(sa.text(f"SELECT * FROM {table_name} LIMIT 5"))
                columns = result.keys()
                rows = result.fetchall()

                if rows:
                    # Tabela com dados - processa normalmente
                    table_df = pd.DataFrame(rows, columns=columns)
                    columns_info = []

                    for col in table_df.columns:
                        col_data = table_df[col].dropna()

                        col_info = {
                            "column": col,
                            "type": str(col_data.dtype) if len(col_data) > 0 else "object",
                            "examples": "",
                            "stats": ""
                        }

                        if len(col_data) > 0:
                            # Adiciona exemplos de valores
                            unique_values = col_data.unique()[:3]
                            col_info["examples"] = ", ".join([str(v) for v in unique_values])

                            # Adiciona estatísticas para colunas numéricas
                            if col_data.dtype in ['int64', 'float64']:
                                try:
                                    min_val = col_data.min()
                                    max_val = col_data.max()
                                    col_info["stats"] = f" | Min: {min_val}, Max: {max_val}"
                                except:
                                    pass

                        columns_info.append(col_info)

                    logging.info(f"[PROCESSING NODE] ✅ Tabela {table_name}: {len(columns_info)} colunas com dados")
                    return columns_info

                else:
                    # Tabela sem dados - obtém apenas estrutura das colunas
                    logging.info(f"[PROCESSING NODE] ⚠️ Tabela {table_name} sem dados - obtendo apenas estrutura")

                    # Para PostgreSQL, obtém informações das colunas do schema
                    if str(engine.dialect.name).lower() == "postgresql":
                        schema_result = conn.execute(sa.text(f"""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = '{table_name}'
                            ORDER BY ordinal_position
                        """))

                        columns_info = []
                        for row in schema_result.fetchall():
                            col_info = {
                                "column": row[0],
                                "type": row[1],
                                "examples": "(sem dados)",
                                "stats": ""
                            }
                            columns_info.append(col_info)
                    else:
                        # Para SQLite, usa PRAGMA
                        pragma_result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
                        columns_info = []
                        for row in pragma_result.fetchall():
                            col_info = {
                                "column": row[1],  # column name
                                "type": row[2],    # column type
                                "examples": "(sem dados)",
                                "stats": ""
                            }
                            columns_info.append(col_info)

                    logging.info(f"[PROCESSING NODE] ✅ Tabela {table_name}: {len(columns_info)} colunas (estrutura apenas)")
                    return columns_info

            except Exception as e:
                # Se falhar ao acessar a tabela, tenta obter pelo menos a estrutura
                logging.warning(f"[PROCESSING NODE] Erro ao acessar dados da tabela {table_name}: {e}")

                try:
                    # Fallback: obtém estrutura das colunas
                    if str(engine.dialect.name).lower() == "postgresql":
                        schema_result = conn.execute(sa.text(f"""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_name = '{table_name}'
                            ORDER BY ordinal_position
                        """))

                        columns_info = []
                        for row in schema_result.fetchall():
                            col_info = {
                                "column": row[0],
                                "type": row[1],
                                "examples": "(erro ao acessar dados)",
                                "stats": ""
                            }
                            columns_info.append(col_info)
                    else:
                        # Para SQLite
                        pragma_result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
                        columns_info = []
                        for row in pragma_result.fetchall():
                            col_info = {
                                "column": row[1],
                                "type": row[2],
                                "examples": "(erro ao acessar dados)",
                                "stats": ""
                            }
                            columns_info.append(col_info)

                    logging.info(f"[PROCESSING NODE] ⚠️ Tabela {table_name}: {len(columns_info)} colunas (fallback)")
                    return columns_info

                except Exception as e2:
                    logging.error(f"[PROCESSING NODE] ❌ Erro total ao processar tabela {table_name}: {e2}")
                    return []

    except Exception as e:
        logging.error(f"[PROCESSING NODE] ❌ Erro ao extrair informações da tabela {table_name}: {e}")
        return []
