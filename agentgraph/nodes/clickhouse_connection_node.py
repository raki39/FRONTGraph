"""
Nó para conexão com ClickHouse
"""
import logging
import time
from typing import Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase

from agentgraph.utils.object_manager import get_object_manager


async def clickhouse_connection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para estabelecer conexão com ClickHouse

    Args:
        state: Estado atual do agente

    Returns:
        Estado atualizado com conexão ClickHouse estabelecida
    """
    try:
        logging.info("[CLICKHOUSE_CONNECTION] Iniciando conexão com ClickHouse")

        # DEBUG: Log completo do state
        logging.info(f"[CLICKHOUSE_CONNECTION] DEBUG - Keys no state: {list(state.keys())}")
        logging.info(f"[CLICKHOUSE_CONNECTION] DEBUG - connection_type: {state.get('connection_type')}")
        logging.info(f"[CLICKHOUSE_CONNECTION] DEBUG - db_uri: {state.get('db_uri')}")
        logging.info(f"[CLICKHOUSE_CONNECTION] DEBUG - clickhouse_config: {state.get('clickhouse_config')}")

        # Recupera configuração ClickHouse (pode vir como config ou db_uri)
        clickhouse_config = state.get("clickhouse_config", {})
        db_uri = state.get("db_uri")

        # Se db_uri foi fornecido diretamente (vindo da API), usar ele
        if db_uri and not clickhouse_config:
            logging.info(f"[CLICKHOUSE_CONNECTION] Usando db_uri diretamente: {db_uri}")
            connection_uri = db_uri

            # Extrai informações do URI para logging
            # Formato: clickhouse+http://user:password@host:port/database?protocol=http
            try:
                from urllib.parse import urlparse
                parsed = urlparse(connection_uri)
                host = parsed.hostname or "unknown"
                port = parsed.port or 8123
                database = parsed.path.lstrip('/') or "default"
            except:
                host = "unknown"
                port = 8123
                database = "unknown"

        elif clickhouse_config:
            # Valida configuração
            is_valid, validation_error = validate_clickhouse_config(clickhouse_config)

            if not is_valid:
                error_msg = f"Configuração ClickHouse inválida: {validation_error}"
                logging.error(f"[CLICKHOUSE_CONNECTION] {error_msg}")
                state.update({
                    "success": False,
                    "message": f"❌ {validation_error}",
                    "connection_error": error_msg,
                    "connection_success": False
                })
                return state

            # Extrai credenciais
            host = clickhouse_config.get("host")
            port = clickhouse_config.get("port", 8123)  # HTTP port padrão
            database = clickhouse_config.get("database", "default")
            username = clickhouse_config.get("username", "default")
            password = clickhouse_config.get("password", "")
            secure = clickhouse_config.get("secure", False)

            # Constrói URI de conexão
            # Formato: clickhouse+http://user:password@host:port/database?protocol=https
            protocol = "https" if secure else "http"
            if password:
                connection_uri = f"clickhouse+http://{username}:{password}@{host}:{port}/{database}?protocol={protocol}"
            else:
                connection_uri = f"clickhouse+http://{username}@{host}:{port}/{database}?protocol={protocol}"

        else:
            error_msg = "Configuração ClickHouse ou db_uri não encontrada"
            logging.error(f"[CLICKHOUSE_CONNECTION] {error_msg}")
            state.update({
                "success": False,
                "message": f"❌ {error_msg}",
                "connection_error": error_msg,
                "connection_success": False
            })
            return state

        logging.info(f"[CLICKHOUSE_CONNECTION] Conectando a: {host}:{port}/{database}")
        
        # Tenta estabelecer conexão
        start_time = time.time()
        
        try:
            # Cria engine SQLAlchemy com clickhouse-sqlalchemy
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
            logging.info(f"[CLICKHOUSE_CONNECTION] Conexão estabelecida em {connection_time:.2f}s")
            
        except Exception as conn_error:
            error_msg = f"Falha na conexão ClickHouse: {str(conn_error)}"
            logging.error(f"[CLICKHOUSE_CONNECTION] {error_msg}")

            # Usa função de tratamento de erro amigável
            user_error = get_clickhouse_connection_error_message(conn_error)
            
            state.update({
                "success": False,
                "message": user_error,
                "connection_error": error_msg,
                "connection_success": False
            })
            return state
        
        # Cria objeto SQLDatabase do LangChain
        try:
            # Para ClickHouse, NUNCA usar SQLDatabase.from_uri() pois tenta refletir information_schema
            # Usar create_engine + SQLDatabase(engine=...) com warnings filtrados
            import warnings
            from sqlalchemy import create_engine as sa_create_engine
            from langchain_community.utilities import SQLDatabase

            # Cria engine com warnings filtrados
            with warnings.catch_warnings():
                # Ignora warnings sobre tipos desconhecidos (pgvector, etc)
                warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
                warnings.filterwarnings("ignore", category=Warning)

                ch_engine = sa_create_engine(
                    connection_uri,
                    pool_timeout=30,
                    pool_recycle=3600,
                    echo=False
                )

                # IMPORTANTE: Usar SQLDatabase(engine=...) e NÃO SQLDatabase.from_uri()
                # from_uri() tenta refletir metadados usando information_schema que não existe no ClickHouse
                db = SQLDatabase(engine=ch_engine)

            logging.info("[CLICKHOUSE_CONNECTION] SQLDatabase criado com sucesso (sem reflection de information_schema)")

            # Obtém informações do banco
            # IMPORTANTE: Para ClickHouse, NÃO usar db.get_usable_table_names() pois tenta refletir information_schema
            # Usar query direta ao system.tables
            try:
                with ch_engine.connect() as conn:
                    tables_result = conn.execute(text("""
                        SELECT name
                        FROM system.tables
                        WHERE database != 'system'
                        ORDER BY name
                    """))
                    table_names = [row[0] for row in tables_result.fetchall()]
            except Exception as e:
                logging.warning(f"[CLICKHOUSE_CONNECTION] Erro ao obter tabelas: {e}")
                table_names = []

            logging.info(f"[CLICKHOUSE_CONNECTION] Tabelas encontradas: {table_names}")

            # Verifica o dialeto (deve ser 'clickhouse')
            dialect = str(db.dialect)
            logging.info(f"[CLICKHOUSE_CONNECTION] Dialeto detectado: {dialect}")

            if not table_names:
                warning_msg = "⚠️ Nenhuma tabela encontrada no banco de dados"
                logging.warning(f"[CLICKHOUSE_CONNECTION] {warning_msg}")
                # Não é um erro fatal, mas avisa o usuário

        except Exception as db_error:
            error_msg = f"Erro ao criar SQLDatabase: {str(db_error)}"
            logging.error(f"[CLICKHOUSE_CONNECTION] {error_msg}")
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
            "type": "clickhouse",
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "table_count": len(table_names),
            "tables": table_names[:1000],  # Primeiras 1000 tabelas
            "connection_time": connection_time,
            "engine_id": engine_id,
            "db_id": db_id,
            "dialect": dialect  # ← IMPORTANTE: LangChain usa isso para selecionar o prompt
        }
        
        # Atualiza estado com sucesso
        state.update({
            "success": True,
            "message": f"✅ Conectado ao ClickHouse: {len(table_names)} tabelas encontradas",
            "connection_info": connection_info,
            "connection_error": None,
            "connection_success": True,
            "engine_id": engine_id,
            "db_id": db_id,
            "database_dialect": dialect  # ← Para referência futura
        })
        
        logging.info(f"[CLICKHOUSE_CONNECTION] Conexão ClickHouse estabelecida com sucesso")
        logging.info(f"[CLICKHOUSE_CONNECTION] Informações: {connection_info}")
        
        return state
        
    except Exception as e:
        error_msg = f"Erro inesperado na conexão ClickHouse: {e}"
        logging.error(f"[CLICKHOUSE_CONNECTION] {error_msg}")
        
        state.update({
            "success": False,
            "message": f"❌ {error_msg}",
            "connection_error": error_msg,
            "connection_success": False
        })
        
        return state


def validate_clickhouse_config(clickhouse_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Valida configuração ClickHouse
    
    Args:
        clickhouse_config: Configuração ClickHouse
        
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        required_fields = ["host"]
        
        for field in required_fields:
            if not clickhouse_config.get(field):
                return False, f"Campo obrigatório ausente: {field}"
        
        # Validações básicas
        port = clickhouse_config.get("port", 8123)
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                return False, "Porta deve estar entre 1 e 65535"
        except (ValueError, TypeError):
            return False, "Porta deve ser um número válido"
        
        host = clickhouse_config.get("host", "").strip()
        if not host:
            return False, "Host não pode estar vazio"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro na validação: {e}"


def get_clickhouse_connection_error_message(error: Exception) -> str:
    """
    Retorna mensagem de erro amigável para erros de conexão ClickHouse
    
    Args:
        error: Exceção capturada
        
    Returns:
        Mensagem de erro amigável
    """
    error_str = str(error).lower()
    
    if "connection refused" in error_str or "failed to connect" in error_str:
        return "❌ Conexão recusada. Verifique se o ClickHouse está rodando e acessível no host/porta especificados."
    elif "authentication failed" in error_str or "access denied" in error_str:
        return "❌ Falha na autenticação. Verifique o usuário e senha."
    elif "database" in error_str and "does not exist" in error_str:
        return "❌ Banco de dados não encontrado. Verifique o nome do banco."
    elif "could not translate host name" in error_str or "name or service not known" in error_str:
        return "❌ Host não encontrado. Verifique o endereço do servidor."
    elif "timeout" in error_str or "timed out" in error_str:
        return "❌ Timeout na conexão. Verifique a conectividade de rede e firewall."
    elif "ssl" in error_str or "certificate" in error_str:
        return "❌ Erro SSL/TLS. Verifique se a opção 'secure' está configurada corretamente."
    else:
        return f"❌ Erro na conexão ClickHouse: {str(error)}"


async def test_clickhouse_connection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nó para testar conexão ClickHouse sem armazenar
    
    Args:
        state: Estado atual do agente
        
    Returns:
        Estado atualizado com resultado do teste
    """
    try:
        logging.info("[CLICKHOUSE_TEST] Testando conexão ClickHouse")
        
        clickhouse_config = state.get("clickhouse_config", {})
        
        # Valida credenciais
        is_valid, error_msg = validate_clickhouse_config(clickhouse_config)
        if not is_valid:
            state.update({
                "test_success": False,
                "test_message": f"❌ {error_msg}",
                "test_error": error_msg
            })
            return state
        
        # Testa conexão rápida
        host = clickhouse_config.get("host")
        port = clickhouse_config.get("port", 8123)
        database = clickhouse_config.get("database", "default")
        username = clickhouse_config.get("username", "default")
        password = clickhouse_config.get("password", "")
        secure = clickhouse_config.get("secure", False)
        
        protocol = "https" if secure else "http"
        if password:
            connection_uri = f"clickhouse+http://{username}:{password}@{host}:{port}/{database}?protocol={protocol}"
        else:
            connection_uri = f"clickhouse+http://{username}@{host}:{port}/{database}?protocol={protocol}"
        
        try:
            engine = create_engine(connection_uri, pool_timeout=10)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0] if result else "unknown"
            
            state.update({
                "test_success": True,
                "test_message": f"✅ Conexão ClickHouse testada com sucesso (versão: {version})",
                "test_error": None,
                "clickhouse_version": version
            })
            
        except Exception as e:
            error_msg = get_clickhouse_connection_error_message(e)
            state.update({
                "test_success": False,
                "test_message": error_msg,
                "test_error": str(e)
            })
        
        return state
        
    except Exception as e:
        error_msg = f"Erro no teste de conexão: {e}"
        logging.error(f"[CLICKHOUSE_TEST] {error_msg}")
        
        state.update({
            "test_success": False,
            "test_message": f"❌ {error_msg}",
            "test_error": error_msg
        })
        
        return state

