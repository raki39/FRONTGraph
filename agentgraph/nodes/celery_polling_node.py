"""
Nó para polling de tasks do Celery
"""
import asyncio
import logging
import time
from typing import Dict, Any

async def celery_task_dispatch_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para disparar task do Celery para processamento SQL
    
    Args:
        state: Estado atual do LangGraph
        
    Returns:
        Estado atualizado com task_id
    """
    try:
        from tasks import process_sql_query_task, save_agent_config_to_redis
        
        user_input = state.get("user_input", "")
        agent_id = state.get("agent_id", "")
        
        if not user_input or not agent_id:
            raise ValueError("user_input e agent_id são obrigatórios")
        
        logging.info(f"[CELERY_DISPATCH] Disparando task para agent_id: {agent_id}")
        logging.info(f"[CELERY_DISPATCH] User input: {user_input[:100]}...")
        
        # Obter TOP_K atualizado do ObjectManager (se foi alterado via botão APLICAR)
        from agentgraph.utils.object_manager import get_object_manager
        object_manager = get_object_manager()
        state_top_k = state.get('top_k', 10)
        updated_top_k = object_manager.get_global_config('top_k', state_top_k)

        if updated_top_k != state_top_k:
            logging.info(f"[CELERY_DISPATCH] 📊 TOP_K atualizado via ObjectManager: {state_top_k} → {updated_top_k}")
        else:
            logging.info(f"[CELERY_DISPATCH] 📊 TOP_K do estado: {updated_top_k}")

        # Preparar configuração do agente para o Redis
        agent_config = {
            'tenant_id': state.get('tenant_id', 'default'),
            'connection_type': state.get('connection_type', 'csv'),
            'selected_model': state.get('selected_model', 'gpt-4o-mini'),
            'top_k': updated_top_k,  # Usa valor atualizado do ObjectManager
            'advanced_mode': state.get('advanced_mode', False),
            'processing_enabled': state.get('processing_enabled', False),
            'processing_model': state.get('processing_model', 'gpt-4o-mini'),
            # Adicionar contexto SQL
            'sql_context': state.get('sql_context', ''),
            'suggested_query': state.get('suggested_query', ''),
            'query_observations': state.get('query_observations', ''),
            'processing_result': state.get('processing_result', '')
        }

        # Log simplificado das configurações
        processing_status = "ATIVO" if agent_config['processing_enabled'] else "DESATIVO"
        refinement_status = "ATIVO" if agent_config['advanced_mode'] else "DESATIVO"

        logging.info(f"[CELERY_DISPATCH] Config: {agent_config['selected_model']} | {agent_config['connection_type']} | TOP_K={agent_config['top_k']} | Processing={processing_status} | Refinamento={refinement_status}")

        # Log do contexto apenas se houver
        sql_context = agent_config.get('sql_context', '')
        if sql_context:
            logging.info(f"[CELERY_DISPATCH] Contexto SQL: {len(str(sql_context))} chars")

        suggested_query = agent_config.get('suggested_query', '')
        if suggested_query:
            logging.info(f"[CELERY_DISPATCH] Query Sugerida: {str(suggested_query)[:80]}...")

        query_observations = agent_config.get('query_observations', '')
        if query_observations:
            logging.info(f"[CELERY_DISPATCH] Observacoes: {str(query_observations)[:80]}...")
        
        # Adicionar configurações específicas por tipo de conexão
        if agent_config['connection_type'] == 'csv':
            # Para CSV, usar SEMPRE o db_uri do SQLite já criado na ingestão
            from agentgraph.utils.config import SQL_DB_PATH
            agent_config['db_uri'] = f"sqlite:///{SQL_DB_PATH}"

        elif agent_config['connection_type'] == 'postgresql':
            # Para PostgreSQL, salvar configurações de conexão
            agent_config['postgresql_config'] = state.get('postgresql_config', {})
            agent_config['single_table_mode'] = state.get('single_table_mode', False)
            agent_config['selected_table'] = state.get('selected_table')

        elif agent_config['connection_type'] == 'clickhouse':
            # Para ClickHouse, salvar configurações de conexão
            agent_config['clickhouse_config'] = state.get('clickhouse_config', {})
            agent_config['single_table_mode'] = state.get('single_table_mode', False)
            agent_config['selected_table'] = state.get('selected_table')

        # Salvar configuração no Redis
        success = save_agent_config_to_redis(agent_id, agent_config)
        if not success:
            raise Exception("Falha ao salvar configuração do agente no Redis")
        
        logging.info(f"[CELERY_DISPATCH] Configuração salva no Redis para {agent_id}")
        
        # Disparar task do Celery e aguardar resultado
        logging.info(f"[CELERY_DISPATCH] Executando task síncrona...")

        task = process_sql_query_task.delay(agent_id, user_input)
        task_id = task.id

        logging.info(f"[CELERY_DISPATCH] Task {task_id} disparada, aguardando resultado...")

        # Aguardar resultado direto (timeout de 5 minutos)
        try:
            result = task.get(timeout=300)

            logging.info(f"[CELERY_DISPATCH] ✅ Task concluída com sucesso!")

            # Atualizar estado com resultado final
            state.update({
                'response': result.get('response', ''),
                'sql_query_extracted': result.get('sql_query'),
                'sql_result': {
                    'output': result.get('response', ''),
                    'success': result.get('status') == 'success',
                    'sql_query': result.get('sql_query'),
                    'intermediate_steps': result.get('intermediate_steps', [])
                },
                'execution_time': result.get('execution_time', 0),
                'error': None,
                'celery_task_id': task_id,
                'celery_task_status': 'SUCCESS'
            })

            if result.get('sql_query'):
                logging.info(f"[CELERY_DISPATCH] Query SQL extraída: {result.get('sql_query')}")

        except Exception as e:
            error_msg = f"Erro na task Celery: {e}"
            logging.error(f"[CELERY_DISPATCH] ❌ {error_msg}")

            state.update({
                'error': error_msg,
                'response': error_msg,
                'sql_result': {
                    'output': error_msg,
                    'success': False,
                    'sql_query': None,
                    'intermediate_steps': []
                },
                'celery_task_id': task_id,
                'celery_task_status': 'FAILURE'
            })

        return state
        
    except Exception as e:
        error_msg = f"Erro ao disparar task Celery: {e}"
        logging.error(f"[CELERY_DISPATCH] {error_msg}")
        
        state.update({
            'error': error_msg,
            'response': error_msg,
            'celery_task_id': None,
            'celery_task_status': 'ERROR'
        })
        
        return state

async def celery_task_polling_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para fazer polling do resultado da task Celery
    
    Args:
        state: Estado atual do LangGraph
        
    Returns:
        Estado atualizado com resultado da task
    """
    try:
        from tasks import get_task_status

        task_id = state.get('celery_task_id')
        if not task_id:
            raise ValueError("celery_task_id não encontrado no estado")

        # Controle de timeout e tentativas
        polling_count = state.get('celery_polling_count', 0) + 1
        dispatch_time = state.get('celery_dispatch_time', time.time())
        elapsed_time = time.time() - dispatch_time

        # Timeout de 2 minutos ou máximo 20 tentativas (com sleep de 3s = ~1 minuto)
        MAX_POLLING_ATTEMPTS = 20
        MAX_TIMEOUT_SECONDS = 120

        if polling_count > MAX_POLLING_ATTEMPTS or elapsed_time > MAX_TIMEOUT_SECONDS:
            timeout_msg = f"Timeout na task Celery após {polling_count} tentativas ({elapsed_time:.1f}s)"
            logging.error(f"[CELERY_POLLING] {timeout_msg}")

            state.update({
                'error': timeout_msg,
                'response': timeout_msg,
                'celery_task_status': 'TIMEOUT'
            })
            return state
        
        # Consultar status da task
        task_status = get_task_status(task_id)

        # Log apenas a cada 5 tentativas ou quando status muda
        current_status = task_status['state']
        previous_status = state.get('celery_task_status')

        if polling_count % 5 == 1 or current_status != previous_status:
            logging.info(f"[CELERY_POLLING] Tentativa {polling_count}: {current_status}")
            if task_status.get('progress'):
                logging.info(f"[CELERY_POLLING] Progresso: {task_status['progress']}")

        # Atualizar estado com status atual
        state.update({
            'celery_task_status': current_status,
            'celery_task_info': task_status,
            'celery_polling_count': polling_count
        })
        
        if task_status['state'] == 'SUCCESS':
            # Task concluída com sucesso
            result = task_status['result']
            
            logging.info(f"[CELERY_POLLING] Task concluída com sucesso")
            
            state.update({
                'response': result.get('response', ''),
                'sql_query_extracted': result.get('sql_query'),
                'sql_result': {
                    'output': result.get('response', ''),
                    'success': result.get('status') == 'success',
                    'sql_query': result.get('sql_query'),
                    'intermediate_steps': result.get('intermediate_steps', [])
                },
                'execution_time': result.get('execution_time', 0),
                'error': None
            })
            
        elif task_status['state'] == 'FAILURE':
            # Task falhou
            error_msg = task_status.get('error', 'Erro desconhecido na task')
            
            logging.error(f"[CELERY_POLLING] Task falhou: {error_msg}")
            
            state.update({
                'error': error_msg,
                'response': error_msg,
                'sql_result': {
                    'output': error_msg,
                    'success': False,
                    'sql_query': None,
                    'intermediate_steps': []
                }
            })
            
        elif task_status['state'] in ['PENDING', 'PROCESSING']:
            # Task ainda em processamento
            status_msg = task_status.get('status', 'Processando...')
            progress = task_status.get('progress', 0)

            # Log apenas a cada 5 tentativas
            if polling_count % 5 == 1:
                logging.info(f"[CELERY_POLLING] Aguardando task: {status_msg} ({progress}%)")

            # IMPORTANTE: Aguardar antes de retornar
            await asyncio.sleep(3)

            # Manter estado atual, será consultado novamente
            state.update({
                'celery_polling_status': status_msg,
                'celery_polling_progress': progress
            })
        
        return state
        
    except Exception as e:
        error_msg = f"Erro no polling da task Celery: {e}"
        logging.error(f"[CELERY_POLLING] {error_msg}")
        
        state.update({
            'error': error_msg,
            'response': error_msg,
            'celery_task_status': 'ERROR'
        })
        
        return state

def should_continue_polling(state: Dict[str, Any]) -> str:
    """
    Função de roteamento para determinar se deve continuar polling

    Args:
        state: Estado atual

    Returns:
        Nome do próximo nó
    """
    task_status = state.get('celery_task_status', 'UNKNOWN')

    if task_status in ['SUCCESS', 'FAILURE', 'ERROR', 'TIMEOUT']:
        # Task finalizada, continuar fluxo normal
        logging.info(f"[POLLING_ROUTE] Task finalizada ({task_status}), continuando fluxo")

        # Verificar se deve gerar gráfico
        query_type = state.get("query_type", "")
        if query_type == "sql_query_graphic" and task_status == 'SUCCESS':
            return "graph_selection"
        elif state.get("advanced_mode", False) and task_status == 'SUCCESS':
            return "refine_response"
        else:
            return "cache_response"
    else:
        # Task ainda em processamento, continuar polling
        polling_count = state.get('celery_polling_count', 0)
        if polling_count % 10 == 1:  # Log apenas a cada 10 tentativas
            logging.info(f"[POLLING_ROUTE] Continuando polling (tentativa {polling_count})")
        return "celery_polling"

def is_task_completed(state: Dict[str, Any]) -> bool:
    """
    Verifica se a task do Celery foi concluída

    Args:
        state: Estado atual

    Returns:
        True se task foi concluída (sucesso ou falha)
    """
    task_status = state.get('celery_task_status', 'UNKNOWN')
    return task_status in ['SUCCESS', 'FAILURE', 'ERROR', 'TIMEOUT']
