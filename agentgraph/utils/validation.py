"""
Utilitários de validação para o sistema AgentGraph
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional


def validate_postgresql_config(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Valida configuração postgresql completa
    
    Args:
        config: Dicionário com configuração postgresql
        
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        # Campos obrigatórios
        required_fields = ["host", "port", "database", "username", "password"]
        
        for field in required_fields:
            if field not in config or not config[field]:
                return False, f"Campo obrigatório ausente ou vazio: {field}"
        
        # Validação específica do host
        host = str(config["host"]).strip()
        if not host:
            return False, "Host não pode estar vazio"
        
        # Validação básica de formato de host
        if not _is_valid_host(host):
            return False, "Formato de host inválido"
        
        # Validação da porta
        try:
            port = int(config["port"])
            if port < 1 or port > 65535:
                return False, "Porta deve estar entre 1 e 65535"
        except (ValueError, TypeError):
            return False, "Porta deve ser um número válido"
        
        # Validação do nome do banco
        database = str(config["database"]).strip()
        if not database:
            return False, "Nome do banco não pode estar vazio"
        
        if not _is_valid_database_name(database):
            return False, "Nome do banco contém caracteres inválidos"
        
        # Validação do usuário
        username = str(config["username"]).strip()
        if not username:
            return False, "Nome de usuário não pode estar vazio"
        
        if not _is_valid_username(username):
            return False, "Nome de usuário contém caracteres inválidos"
        
        # Validação da senha (básica)
        password = str(config["password"])
        if not password:
            return False, "Senha não pode estar vazia"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro na validação: {e}"


def _is_valid_host(host: str) -> bool:
    """
    Valida formato de host (IP ou hostname)
    
    Args:
        host: Host a validar
        
    Returns:
        True se válido
    """
    # Regex para IPv4
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    # Regex para hostname/FQDN
    hostname_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    
    # Permite localhost
    if host.lower() == 'localhost':
        return True
    
    # Valida IPv4
    if re.match(ipv4_pattern, host):
        return True
    
    # Valida hostname
    if re.match(hostname_pattern, host):
        return True
    
    return False


def _is_valid_database_name(database: str) -> bool:
    """
    Valida nome de banco postgresql
    
    Args:
        database: Nome do banco
        
    Returns:
        True se válido
    """
    # postgresql: deve começar com letra ou underscore, 
    # pode conter letras, números, underscores e hífens
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
    
    # Comprimento máximo típico
    if len(database) > 63:
        return False
    
    return bool(re.match(pattern, database))


def _is_valid_username(username: str) -> bool:
    """
    Valida nome de usuário postgresql
    
    Args:
        username: Nome de usuário
        
    Returns:
        True se válido
    """
    # Similar ao nome do banco
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_-]*$'
    
    # Comprimento máximo típico
    if len(username) > 63:
        return False
    
    return bool(re.match(pattern, username))


def validate_csv_file_path(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Valida caminho de arquivo csv
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        import os
        
        if not file_path:
            return False, "Caminho do arquivo não pode estar vazio"
        
        if not os.path.exists(file_path):
            return False, f"Arquivo não encontrado: {file_path}"
        
        if not file_path.lower().endswith('.csv'):
            return False, "Arquivo deve ter extensão .csv"
        
        # Verifica se é um arquivo (não diretório)
        if not os.path.isfile(file_path):
            return False, "Caminho deve apontar para um arquivo"
        
        # Verifica tamanho do arquivo
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Arquivo csv está vazio"
        
        # Limite de 5GB
        if file_size > 5 * 1024 * 1024 * 1024:
            return False, "Arquivo muito grande (máximo 5GB)"
        
        return True, None
        
    except Exception as e:
        return False, f"Erro na validação do arquivo: {e}"


def validate_connection_state(state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Valida estado de conexão completo

    Args:
        state: Estado da conexão

    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        connection_type = state.get("connection_type", "csv")

        if connection_type.lower() not in ["csv", "postgresql", "clickhouse"]:
            return False, f"Tipo de conexão inválido: {connection_type}"

        if connection_type.lower() == "postgresql":
            postgresql_config = state.get("postgresql_config")
            if not postgresql_config:
                return False, "Configuração postgresql ausente"

            return validate_postgresql_config(postgresql_config)

        elif connection_type.lower() == "clickhouse":
            clickhouse_config = state.get("clickhouse_config")
            if not clickhouse_config:
                return False, "Configuração clickhouse ausente"

            # Validação básica de ClickHouse
            from agentgraph.nodes.clickhouse_connection_node import validate_clickhouse_config
            return validate_clickhouse_config(clickhouse_config)

        elif connection_type.lower() == "csv":
            file_path = state.get("file_path")
            if file_path:
                return validate_csv_file_path(file_path)
            else:
                # Verifica se há banco existente
                import os
                from agentgraph.utils.config import SQL_DB_PATH

                if not os.path.exists(SQL_DB_PATH):
                    return False, "Nenhum arquivo csv fornecido e nenhum banco existente"

                return True, None

        return True, None

    except Exception as e:
        return False, f"Erro na validação do estado: {e}"


def sanitize_postgresql_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitiza configuração postgresql removendo espaços e normalizando
    
    Args:
        config: Configuração original
        
    Returns:
        Configuração sanitizada
    """
    try:
        sanitized = {}
        
        # Host
        sanitized["host"] = str(config.get("host", "")).strip()
        
        # Porta
        try:
            sanitized["port"] = int(config.get("port", 5432))
        except (ValueError, TypeError):
            sanitized["port"] = 5432
        
        # Database
        sanitized["database"] = str(config.get("database", "")).strip()
        
        # Username
        sanitized["username"] = str(config.get("username", "")).strip()
        
        # Password (não remove espaços - pode ser intencional)
        sanitized["password"] = str(config.get("password", ""))
        
        return sanitized
        
    except Exception as e:
        logging.error(f"Erro ao sanitizar configuração postgresql: {e}")
        return config


def get_connection_error_message(error: Exception) -> str:
    """
    Converte erro de conexão em mensagem amigável
    
    Args:
        error: Exceção capturada
        
    Returns:
        Mensagem de erro amigável
    """
    error_str = str(error).lower()
    
    if "password authentication failed" in error_str:
        return "❌ Falha na autenticação: Usuário ou senha incorretos"
    
    elif "could not connect to server" in error_str:
        return "❌ Não foi possível conectar ao servidor: Verifique host e porta"
    
    elif "database" in error_str and "does not exist" in error_str:
        return "❌ Banco de dados não existe: Verifique o nome do banco"
    
    elif "connection refused" in error_str:
        return "❌ Conexão recusada: Servidor postgresql pode estar desligado"
    
    elif "timeout" in error_str:
        return "❌ Timeout na conexão: Servidor demorou muito para responder"
    
    elif "permission denied" in error_str:
        return "❌ Permissão negada: Usuário não tem acesso ao banco"
    
    elif "too many connections" in error_str:
        return "❌ Muitas conexões: Servidor postgresql está sobrecarregado"
    
    else:
        return f"❌ Erro de conexão: {str(error)}"
