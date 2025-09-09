from typing import Dict, Any
from api.config import settings

# Integra com a tasks existente do AgentGraph
# Nota: manter dependência mínima para não acoplar fortemente a API ao app gradio

def dispatch_agent_run(agent_config: Dict[str, Any], user_input: str) -> str:
    """
    Salva config no Redis e dispara task Celery usando o módulo tasks do AgentGraph.
    Retorna task_id.
    """
    from agentgraph.tasks import save_agent_config_to_redis, process_sql_query_task

    agent_id = agent_config["agent_id"]
    saved = save_agent_config_to_redis(agent_id, agent_config)
    if not saved:
        raise RuntimeError("Falha ao salvar configuração do agente no Redis")

    task = process_sql_query_task.delay(agent_id, user_input)
    return task.id

