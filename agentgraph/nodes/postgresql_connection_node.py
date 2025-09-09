"""
Nó para conexão com PostgreSQL
"""
import logging
import time
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase

from agentgraph.utils.database import create_sql_database
from agentgraph.utils.object_manager import get_object_manager
from agentgraph.utils.validation import (
    validate_postgresql_config,
    sanitize_postgresql_config,
    get_connection_error_message
)


async def postgresql_connection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para estabelecer conexão com PostgreSQL
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com conexão PostgreSQL estabelecida
    """
    try:
        logging.info("[POSTGRESQL_CONNECTION] Iniciando conexão com PostgreSQL")
        
        # Recupera e valida configuração PostgreSQL
        postgresql_config = state.get("postgresql_config", {})

        if not postgresql_config:
            error_msg = "Configuração PostgreSQL não encontrada"
            logging.error(f"[POSTGRESQL_CONNECTION] {error_msg}")
            state.update({
                "success": False,
                "message": f"❌ {error_msg}",
                "connection_error": error_msg,
                "connection_success": False
            })
            return state

        # Sanitiza e valida configuração
        postgresql_config = sanitize_postgresql_config(postgresql_config)
        is_valid, validation_error = validate_postgresql_config(postgresql_config)

        if not is_valid:
            error_msg = f"Configuração PostgreSQL inválida: {validation_error}"
            logging.error(f"[POSTGRESQL_CONNECTION] {error_msg}")
            state.update({
                "success": False,
                "message": f"❌ {validation_error}",
                "connection_error": error_msg,
                "connection_success": False
            })
            return state
        
        # Extrai credenciais
        host = postgresql_config.get("host")
        port = postgresql_config.get("port", 5432)
        database = postgresql_config.get("database")
        username = postgresql_config.get("username")
        password = postgresql_config.get("password")
        
        # Constrói URI de conexão
        connection_uri = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        
        logging.info(f"[POSTGRESQL_CONNECTION] Conectando a: {host}:{port}/{database}")
        
        # Tenta estabelecer conexão
        start_time = time.time()
        
        try:
            # Cria engine SQLAlchemy
            engine = create_engine(
                connection_uri,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False  # Não mostrar SQL queries no log
            )
            
            # Testa conexão
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            connection_time = time.time() - start_time
            logging.info(f"[POSTGRESQL_CONNECTION] Conexão estabelecida em {connection_time:.2f}s")
            
        except Exception as conn_error:
            error_msg = f"Falha na conexão PostgreSQL: {str(conn_error)}"
            logging.error(f"[POSTGRESQL_CONNECTION] {error_msg}")

            # Usa função de tratamento de erro amigável
            user_error = get_connection_error_message(conn_error)
            
            state.update({
                "success": False,
                "message": user_error,
                "connection_error": error_msg,
                "connection_success": False
            })
            return state
        
        # Cria objeto SQLDatabase do LangChain (sempre com todas as tabelas para amostra)
        try:
            db = SQLDatabase.from_uri(connection_uri)
            logging.info("[POSTGRESQL_CONNECTION] SQLDatabase criado com sucesso")

            # Obtém informações do banco
            table_names = db.get_usable_table_names()
            logging.info(f"[POSTGRESQL_CONNECTION] Tabelas encontradas: {table_names}")

            if not table_names:
                warning_msg = "⚠️ Nenhuma tabela encontrada no banco de dados"
                logging.warning(f"[POSTGRESQL_CONNECTION] {warning_msg}")
                # Não é um erro fatal, mas avisa o usuário
            
        except Exception as db_error:
            error_msg = f"Erro ao criar SQLDatabase: {str(db_error)}"
            logging.error(f"[POSTGRESQL_CONNECTION] {error_msg}")
            state.update({
                "success": False,
                "message": f"❌ {error_msg}",
                "connection_error": error_msg,
                "connection_success": False
            })
            return state
        
        # Armazena objetos no ObjectManager
        obj_manager = get_object_manager()
        engine_id = obj_manager.store_engine(engine)
        db_id = obj_manager.store_database(db)
        
        # Informações da conexão
        connection_info = {
            "type": "postgresql",
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "table_count": len(table_names),
            "tables": table_names[:1000],  # Primeiras 10 tabelas
            "connection_time": connection_time,
            "engine_id": engine_id,
            "db_id": db_id
        }
        
        # Atualiza estado com sucesso
        state.update({
            "success": True,
            "message": f"✅ Conectado ao PostgreSQL: {len(table_names)} tabelas encontradas",
            "connection_info": connection_info,
            "connection_error": None,
            "connection_success": True,
            "engine_id": engine_id,
            "db_id": db_id
        })
        
        logging.info(f"[POSTGRESQL_CONNECTION] Conexão PostgreSQL estabelecida com sucesso")
        logging.info(f"[POSTGRESQL_CONNECTION] Informações: {connection_info}")
        
        return state
        
    except Exception as e:
        error_msg = f"Erro inesperado na conexão PostgreSQL: {e}"
        logging.error(f"[POSTGRESQL_CONNECTION] {error_msg}")
        
        state.update({
            "success": False,
            "message": f"❌ {error_msg}",
            "connection_error": error_msg,
            "connection_success": False
        })
        
        return state


def validate_postgresql_credentials(postgresql_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valida credenciais PostgreSQL sem estabelecer conexão completa
    
    Args:
        postgresql_config: Configuração PostgreSQL
        
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        required_fields = ["host", "port", "database", "username", "password"]
        
        for field in required_fields:
            if not postgresql_config.get(field):
                return False, f"Campo obrigatório ausente: {field}"
        
        # Validações básicas
        port = postgresql_config.get("port")
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                return False, "Porta deve estar entre 1 e 65535"
        except (ValueError, TypeError):
            return False, "Porta deve ser um número válido"
        
        host = postgresql_config.get("host", "").strip()
        if not host:
            return False, "Host não pode estar vazio"
        
        database = postgresql_config.get("database", "").strip()
        if not database:
            return False, "Nome do banco não pode estar vazio"
        
        username = postgresql_config.get("username", "").strip()
        if not username:
            return False, "Nome de usuário não pode estar vazio"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro na validação: {e}"


async def test_postgresql_connection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para testar conexão PostgreSQL sem armazenar
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com resultado do teste
    """
    try:
        logging.info("[POSTGRESQL_TEST] Testando conexão PostgreSQL")
        
        postgresql_config = state.get("postgresql_config", {})
        
        # Valida credenciais
        is_valid, error_msg = validate_postgresql_credentials(postgresql_config)
        if not is_valid:
            state.update({
                "test_success": False,
                "test_message": f"❌ {error_msg}",
                "test_error": error_msg
            })
            return state
        
        # Testa conexão rápida
        host = postgresql_config.get("host")
        port = postgresql_config.get("port", 5432)
        database = postgresql_config.get("database")
        username = postgresql_config.get("username")
        password = postgresql_config.get("password")
        
        connection_uri = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        
        try:
            engine = create_engine(connection_uri, pool_timeout=10)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            state.update({
                "test_success": True,
                "test_message": "✅ Conexão PostgreSQL testada com sucesso",
                "test_error": None
            })
            
        except Exception as e:
            error_msg = f"Falha no teste de conexão: {str(e)}"
            state.update({
                "test_success": False,
                "test_message": f"❌ {error_msg}",
                "test_error": error_msg
            })
        
        return state
        
    except Exception as e:
        error_msg = f"Erro no teste de conexão: {e}"
        logging.error(f"[POSTGRESQL_TEST] {error_msg}")
        
        state.update({
            "test_success": False,
            "test_message": f"❌ {error_msg}",
            "test_error": error_msg
        })
        
        return state


