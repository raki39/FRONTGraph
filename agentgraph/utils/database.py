"""
Funções para gerenciamento de banco de dados e processamento de CSV
"""
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import DateTime, Integer, Float
from langchain_community.utilities import SQLDatabase
import logging
from typing import Optional

from agentgraph.utils.config import SQL_DB_PATH

# FUNÇÃO REMOVIDA: create_engine_and_load_db
# Esta função foi substituída pela nova arquitetura de nós
# Use: csv_processing_node.py + database_node.py

def create_engine_from_processed_dataframe(processed_df: pd.DataFrame, sql_types: dict, sql_db_path: str = SQL_DB_PATH):
    """
    Cria engine SQLAlchemy a partir de DataFrame já processado
    NOVA VERSÃO - usa processamento genérico

    Args:
        processed_df: DataFrame já processado
        sql_types: Dicionário com tipos SQL para as colunas
        sql_db_path: Caminho para o banco SQLite

    Returns:
        SQLAlchemy Engine
    """
    logging.info("Criando banco de dados a partir de DataFrame processado...")
    engine = create_engine(f"sqlite:///{sql_db_path}")

    logging.info("[DEBUG] Tipos das colunas processadas:")
    logging.info(processed_df.dtypes)

    # Salva no banco SQLite
    processed_df.to_sql("tabela", engine, index=False, if_exists="replace", dtype=sql_types)
    logging.info(f"Banco de dados SQL criado com sucesso! {len(processed_df)} registros salvos")
    return engine

def create_sql_database(engine) -> SQLDatabase:
    """
    Cria objeto SQLDatabase do LangChain a partir de uma engine

    Args:
        engine: SQLAlchemy Engine

    Returns:
        SQLDatabase do LangChain
    """
    # Ignora tipos desconhecidos como 'vector' do pgvector
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
        return SQLDatabase(engine=engine)

def get_sample_data(engine, limit: int = 10) -> pd.DataFrame:
    """
    Obtém dados de amostra do banco para contexto
    
    Args:
        engine: SQLAlchemy Engine
        limit: Número de linhas para retornar
        
    Returns:
        DataFrame com dados de amostra
    """
    try:
        return pd.read_sql_query(f"SELECT * FROM tabela LIMIT {limit}", engine)
    except Exception as e:
        logging.error(f"Erro ao obter dados de amostra: {e}")
        return pd.DataFrame()

def validate_database(engine) -> bool:
    """
    Valida se o banco de dados está funcionando corretamente
    
    Args:
        engine: SQLAlchemy Engine
        
    Returns:
        True se válido, False caso contrário
    """
    try:
        # Testa uma query simples
        result = pd.read_sql_query("SELECT COUNT(*) as count FROM tabela", engine)
        count = result.iloc[0]['count']
        logging.info(f"Banco validado: {count} registros encontrados")
        return count > 0
    except Exception as e:
        logging.error(f"Erro na validação do banco: {e}")
        return False

