"""
Gerenciador de objetos não-serializáveis para LangGraph
Integrado com Redis para armazenamento de configurações de agentes
"""
import uuid
import json
from typing import Dict, Any, Optional
import logging

class ObjectManager:
    """
    Gerencia objetos não-serializáveis que não podem ser incluídos no estado do LangGraph
    """
    
    def __init__(self):
        self._objects: Dict[str, Any] = {}
        self._sql_agents: Dict[str, Any] = {}
        self._processing_agents: Dict[str, Any] = {}
        self._engines: Dict[str, Any] = {}
        self._databases: Dict[str, Any] = {}
        self._cache_managers: Dict[str, Any] = {}
        # Mapeamento para relacionar agentes com seus bancos
        self._agent_db_mapping: Dict[str, str] = {}
        # Metadados de conexões (CSV/PostgreSQL)
        self._connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    def store_sql_agent(self, agent: Any, db_id: str = None) -> str:
        """Armazena agente SQL e retorna ID"""
        agent_id = str(uuid.uuid4())
        self._sql_agents[agent_id] = agent

        # Mapeia agente com seu banco se fornecido
        if db_id:
            self._agent_db_mapping[agent_id] = db_id

        logging.info(f"Agente SQL armazenado com ID: {agent_id}")
        return agent_id

    def store_agent_config_redis(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        Armazena configuração do agente no Redis para uso pelo Celery

        Args:
            agent_id: ID do agente
            config: Configurações do agente

        Returns:
            True se salvou com sucesso
        """
        try:
            from tasks import save_agent_config_to_redis
            return save_agent_config_to_redis(agent_id, config)
        except Exception as e:
            logging.error(f"Erro ao salvar configuração no Redis: {e}")
            return False

    def load_agent_config_redis(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Carrega configuração do agente do Redis

        Args:
            agent_id: ID do agente

        Returns:
            Configurações do agente ou None se não encontrado
        """
        try:
            from tasks import load_agent_config_from_redis
            return load_agent_config_from_redis(agent_id)
        except Exception as e:
            logging.error(f"Erro ao carregar configuração do Redis: {e}")
            return None
    
    def get_sql_agent(self, agent_id: str) -> Optional[Any]:
        """Recupera agente SQL pelo ID"""
        return self._sql_agents.get(agent_id)

    def store_processing_agent(self, agent: Any) -> str:
        """Armazena Processing Agent e retorna ID"""
        agent_id = str(uuid.uuid4())
        self._processing_agents[agent_id] = agent
        logging.info(f"Processing Agent armazenado com ID: {agent_id}")
        return agent_id

    def get_processing_agent(self, agent_id: str) -> Optional[Any]:
        """Recupera Processing Agent pelo ID"""
        return self._processing_agents.get(agent_id)
    
    def store_engine(self, engine: Any) -> str:
        """Armazena engine e retorna ID"""
        engine_id = str(uuid.uuid4())
        self._engines[engine_id] = engine
        logging.info(f"Engine armazenada com ID: {engine_id}")
        return engine_id
    
    def get_engine(self, engine_id: str) -> Optional[Any]:
        """Recupera engine pelo ID"""
        return self._engines.get(engine_id)

    def store_database(self, database: Any) -> str:
        """Armazena banco de dados e retorna ID"""
        db_id = str(uuid.uuid4())
        self._databases[db_id] = database
        logging.info(f"Banco de dados armazenado com ID: {db_id}")
        return db_id

    def get_database(self, db_id: str) -> Optional[Any]:
        """Recupera banco de dados pelo ID"""
        return self._databases.get(db_id)

    def get_db_id_for_agent(self, agent_id: str) -> Optional[str]:
        """Recupera ID do banco associado ao agente"""
        return self._agent_db_mapping.get(agent_id)
    
    def store_cache_manager(self, cache_manager: Any) -> str:
        """Armazena cache manager e retorna ID"""
        cache_id = str(uuid.uuid4())
        self._cache_managers[cache_id] = cache_manager
        logging.info(f"Cache manager armazenado com ID: {cache_id}")
        return cache_id
    
    def get_cache_manager(self, cache_id: str) -> Optional[Any]:
        """Recupera cache manager pelo ID"""
        return self._cache_managers.get(cache_id)
    
    def store_object(self, obj: Any, category: str = "general") -> str:
        """Armazena objeto genérico e retorna ID"""
        obj_id = str(uuid.uuid4())
        self._objects[obj_id] = {"object": obj, "category": category}
        logging.info(f"Objeto {category} armazenado com ID: {obj_id}")
        return obj_id
    
    def get_object(self, obj_id: str) -> Optional[Any]:
        """Recupera objeto pelo ID"""
        obj_data = self._objects.get(obj_id)
        return obj_data["object"] if obj_data else None
    
    def update_sql_agent(self, agent_id: str, new_agent: Any) -> bool:
        """Atualiza agente SQL existente"""
        if agent_id in self._sql_agents:
            self._sql_agents[agent_id] = new_agent
            logging.info(f"Agente SQL atualizado: {agent_id}")
            return True
        return False
    
    def update_engine(self, engine_id: str, new_engine: Any) -> bool:
        """Atualiza engine existente"""
        if engine_id in self._engines:
            self._engines[engine_id] = new_engine
            logging.info(f"Engine atualizada: {engine_id}")
            return True
        return False
    
    def update_cache_manager(self, cache_id: str, new_cache_manager: Any) -> bool:
        """Atualiza cache manager existente"""
        if cache_id in self._cache_managers:
            self._cache_managers[cache_id] = new_cache_manager
            logging.info(f"Cache manager atualizado: {cache_id}")
            return True
        return False
    
    def clear_all(self):
        """Limpa todos os objetos armazenados"""
        self._objects.clear()
        self._sql_agents.clear()
        self._engines.clear()
        self._databases.clear()
        self._cache_managers.clear()
        self._agent_db_mapping.clear()
        self._connection_metadata.clear()
        logging.info("Todos os objetos foram limpos do gerenciador")

    def store_connection_metadata(self, connection_id: str, metadata: Dict[str, Any]) -> str:
        """
        Armazena metadados de conexão

        Args:
            connection_id: ID da conexão
            metadata: Metadados da conexão

        Returns:
            ID dos metadados armazenados
        """
        self._connection_metadata[connection_id] = metadata
        logging.info(f"Metadados de conexão armazenados com ID: {connection_id}")
        return connection_id

    def get_connection_metadata(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera metadados de conexão pelo ID

        Args:
            connection_id: ID da conexão

        Returns:
            Metadados da conexão ou None se não encontrado
        """
        return self._connection_metadata.get(connection_id)

    def get_all_connection_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Retorna todos os metadados de conexão

        Returns:
            Dicionário com todos os metadados
        """
        return self._connection_metadata.copy()

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas dos objetos armazenados"""
        return {
            "sql_agents": len(self._sql_agents),
            "engines": len(self._engines),
            "databases": len(self._databases),
            "cache_managers": len(self._cache_managers),
            "general_objects": len(self._objects),
            "agent_db_mappings": len(self._agent_db_mapping),
            "connection_metadata": len(self._connection_metadata)
        }

    def update_global_config(self, key: str, value: Any) -> bool:
        """
        Atualiza configuração global no Redis para uso pelo Celery

        Args:
            key: Chave da configuração (ex: 'top_k')
            value: Valor da configuração

        Returns:
            True se atualizou com sucesso
        """
        try:
            import redis
            from agentgraph.utils.config import REDIS_HOST, REDIS_PORT

            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

            # Salva configuração global
            config_key = f"global_config:{key}"
            redis_client.set(config_key, json.dumps(value))

            logging.info(f"[OBJECT_MANAGER] Configuração global atualizada: {key} = {value}")
            return True

        except Exception as e:
            logging.error(f"[OBJECT_MANAGER] Erro ao atualizar configuração global {key}: {e}")
            return False

    def get_global_config(self, key: str, default: Any = None) -> Any:
        """
        Obtém configuração global do Redis

        Args:
            key: Chave da configuração
            default: Valor padrão se não encontrar

        Returns:
            Valor da configuração ou default
        """
        try:
            import redis
            from agentgraph.utils.config import REDIS_HOST, REDIS_PORT

            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

            config_key = f"global_config:{key}"
            value = redis_client.get(config_key)

            if value is not None:
                return json.loads(value)
            else:
                return default

        except Exception as e:
            logging.error(f"[OBJECT_MANAGER] Erro ao obter configuração global {key}: {e}")
            return default

# Instância global do gerenciador
_object_manager: Optional[ObjectManager] = None

def get_object_manager() -> ObjectManager:
    """Retorna instância singleton do gerenciador de objetos"""
    global _object_manager
    if _object_manager is None:
        _object_manager = ObjectManager()
    return _object_manager

def reset_object_manager():
    """Reseta o gerenciador de objetos"""
    global _object_manager
    if _object_manager:
        _object_manager.clear_all()
    _object_manager = ObjectManager()
