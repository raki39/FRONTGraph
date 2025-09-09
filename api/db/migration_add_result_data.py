"""
Migração para adicionar campo result_data na tabela runs

Execute este script para adicionar a coluna result_data que armazena
a resposta textual do agente SQL.
"""

import os
from sqlalchemy import create_engine, text

def run_migration():
    """Executa a migração para adicionar result_data"""
    
    # Configuração do banco
    pg_host = os.getenv("PG_HOST", "localhost")
    pg_port = os.getenv("PG_PORT", "5432")
    pg_db = os.getenv("PG_DB", "agentgraph")
    pg_user = os.getenv("PG_USER", "agent")
    pg_password = os.getenv("PG_PASSWORD", "agent")
    
    db_url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Verifica se a coluna já existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'runs' AND column_name = 'result_data'
            """))
            
            if result.fetchone():
                print("✅ Coluna 'result_data' já existe na tabela 'runs'")
                return
            
            # Adiciona a coluna
            conn.execute(text("""
                ALTER TABLE runs 
                ADD COLUMN result_data TEXT
            """))
            
            conn.commit()
            print("✅ Coluna 'result_data' adicionada com sucesso à tabela 'runs'")
            
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        raise

if __name__ == "__main__":
    run_migration()
