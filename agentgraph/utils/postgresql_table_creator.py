"""
Utilitário para criar tabelas no PostgreSQL baseadas em queries SQL
"""
import logging
import re
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
import pandas as pd


def remove_limit_from_query(sql_query: str) -> str:
    """
    Remove LIMIT da query SQL
    
    Args:
        sql_query: Query SQL original
        
    Returns:
        Query SQL sem LIMIT
    """
    try:
        # Remove LIMIT e tudo que vem depois (case insensitive)
        cleaned_query = re.sub(r'\s+LIMIT\s+\d+.*$', '', sql_query, flags=re.IGNORECASE)
        
        # Remove ponto e vírgula final se existir
        cleaned_query = cleaned_query.rstrip(';').strip()
        
        logging.info(f"[TABLE_CREATOR] Query original: {sql_query[:100]}...")
        logging.info(f"[TABLE_CREATOR] Query sem LIMIT: {cleaned_query[:100]}...")
        
        return cleaned_query
        
    except Exception as e:
        logging.error(f"[TABLE_CREATOR] Erro ao remover LIMIT: {e}")
        return sql_query


def validate_table_name(table_name: str) -> bool:
    """
    Valida nome da tabela PostgreSQL
    
    Args:
        table_name: Nome da tabela
        
    Returns:
        True se válido, False caso contrário
    """
    # Verifica se não está vazio
    if not table_name or not table_name.strip():
        return False
    
    # Verifica padrão: letras, números, underscore, começando com letra ou underscore
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    
    # Verifica se não é palavra reservada do PostgreSQL
    reserved_words = {
        'select', 'from', 'where', 'insert', 'update', 'delete', 'create', 'drop',
        'table', 'index', 'view', 'database', 'schema', 'user', 'group', 'order',
        'by', 'group', 'having', 'limit', 'offset', 'union', 'join', 'inner',
        'outer', 'left', 'right', 'on', 'as', 'and', 'or', 'not', 'null', 'true',
        'false', 'primary', 'key', 'foreign', 'references', 'constraint', 'unique'
    }
    
    return (
        re.match(pattern, table_name.strip()) and 
        table_name.lower() not in reserved_words and
        len(table_name.strip()) <= 63  # Limite do PostgreSQL
    )


async def create_table_from_query(
    table_name: str,
    sql_query: str,
    postgresql_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Cria nova tabela no PostgreSQL baseada em query SQL
    
    Args:
        table_name: Nome da nova tabela
        sql_query: Query SQL para extrair dados
        postgresql_config: Configurações de conexão PostgreSQL
        
    Returns:
        Dicionário com resultado da operação
    """
    try:
        logging.info(f"[TABLE_CREATOR] Iniciando criação da tabela '{table_name}'")
        
        # Valida nome da tabela
        if not validate_table_name(table_name):
            return {
                "success": False,
                "message": "❌ Nome da tabela inválido. Use apenas letras, números e underscore, começando com letra."
            }
        
        # Remove LIMIT da query
        clean_query = remove_limit_from_query(sql_query)
        
        # Cria conexão PostgreSQL
        connection_uri = f"postgresql://{postgresql_config['username']}:{postgresql_config['password']}@{postgresql_config['host']}:{postgresql_config['port']}/{postgresql_config['database']}"
        
        engine = create_engine(connection_uri)
        
        # Testa conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logging.info(f"[TABLE_CREATOR] Conexão PostgreSQL estabelecida")
        
        # Executa query original para obter dados
        logging.info(f"[TABLE_CREATOR] Executando query para obter dados...")
        df = pd.read_sql_query(clean_query, engine)
        
        if df.empty:
            return {
                "success": False,
                "message": "❌ A query não retornou dados para criar a tabela."
            }
        
        logging.info(f"[TABLE_CREATOR] Query executada: {len(df)} registros obtidos")
        
        # Verifica se tabela já existe
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = :table_name
        );
        """
        
        with engine.connect() as conn:
            table_exists = conn.execute(
                text(check_table_query), 
                {"table_name": table_name}
            ).scalar()
        
        if table_exists:
            return {
                "success": False,
                "message": f"❌ Tabela '{table_name}' já existe no banco de dados."
            }
        
        # Cria a nova tabela
        logging.info(f"[TABLE_CREATOR] Criando tabela '{table_name}' com {len(df)} registros...")
        
        df.to_sql(
            table_name,
            engine,
            if_exists='fail',  # Falha se tabela já existir
            index=False,
            method='multi'  # Inserção em lote para performance
        )
        
        # Verifica se tabela foi criada com sucesso
        with engine.connect() as conn:
            count_result = conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()
        
        logging.info(f"[TABLE_CREATOR] ✅ Tabela '{table_name}' criada com {count_result} registros")
        
        return {
            "success": True,
            "message": f"✅ Tabela '{table_name}' criada com sucesso! {count_result} registros inseridos.",
            "records_count": count_result
        }
        
    except Exception as e:
        error_msg = f"Erro ao criar tabela: {str(e)}"
        logging.error(f"[TABLE_CREATOR] {error_msg}")
        
        return {
            "success": False,
            "message": f"❌ {error_msg}"
        }


def get_current_sql_query() -> Optional[str]:
    """
    Recupera a SQL query atual do estado global
    
    Returns:
        SQL query atual ou None se não encontrada
    """
    try:
        # Implementação temporária - será integrada com o estado global
        # Por enquanto retorna None para indicar que precisa ser implementado
        return None
        
    except Exception as e:
        logging.error(f"[TABLE_CREATOR] Erro ao recuperar SQL query: {e}")
        return None
