#!/usr/bin/env python3
"""
Migração para adicionar chat_session_id à tabela runs
Conecta runs ao sistema de histórico
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Adiciona paths para imports
sys.path.append('.')
sys.path.append('./api')

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Obtém URL do banco de dados"""
    # Tenta variáveis de ambiente primeiro
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    
    # Fallback para configuração padrão
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "agent")
    password = os.getenv("POSTGRES_PASSWORD", "agent123")
    database = os.getenv("POSTGRES_DB", "agentgraph")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def add_chat_session_id_to_runs(engine):
    """Adiciona campo chat_session_id à tabela runs"""
    try:
        with engine.connect() as conn:
            # Verifica se a coluna já existe
            logger.info("🔍 Verificando se chat_session_id já existe na tabela runs...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'runs' 
                AND column_name = 'chat_session_id'
            """))
            
            if result.fetchone():
                logger.info("✅ Campo chat_session_id já existe na tabela runs")
                return True
            
            # Adiciona a coluna
            logger.info("📋 Adicionando campo chat_session_id à tabela runs...")
            conn.execute(text("""
                ALTER TABLE runs 
                ADD COLUMN chat_session_id INTEGER REFERENCES chat_sessions(id) ON DELETE SET NULL
            """))
            
            # Cria índice para performance
            logger.info("📊 Criando índice para chat_session_id...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_runs_chat_session_id 
                ON runs(chat_session_id)
            """))
            
            conn.commit()
            logger.info("✅ Campo chat_session_id adicionado com sucesso!")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"❌ Erro ao adicionar chat_session_id: {e}")
        return False

def verify_migration(engine):
    """Verifica se a migração foi aplicada corretamente"""
    try:
        with engine.connect() as conn:
            # Verifica estrutura da tabela runs
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'runs' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            logger.info("📋 Estrutura atual da tabela runs:")
            for col in columns:
                logger.info(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
            
            # Verifica se chat_session_id existe
            chat_session_col = [col for col in columns if col[0] == 'chat_session_id']
            if chat_session_col:
                logger.info("✅ Campo chat_session_id encontrado!")
                return True
            else:
                logger.error("❌ Campo chat_session_id não encontrado!")
                return False
                
    except SQLAlchemyError as e:
        logger.error(f"❌ Erro na verificação: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Iniciando migração: Adicionar chat_session_id à tabela runs")
    logger.info("=" * 70)
    
    # Conecta ao banco
    try:
        db_url = get_database_url()
        logger.info(f"🔗 Conectando ao banco: {db_url.split('@')[1] if '@' in db_url else db_url}")
        engine = create_engine(db_url)
        
        # Testa conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Conectado ao PostgreSQL: {version}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
        return 1
    
    # Executa migração
    logger.info("\n📋 Executando migração...")
    success = add_chat_session_id_to_runs(engine)
    
    if not success:
        logger.error("❌ Migração falhou!")
        return 1
    
    # Verifica migração
    logger.info("\n🔍 Verificando migração...")
    verified = verify_migration(engine)
    
    if verified:
        logger.info("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("✅ Campo chat_session_id adicionado à tabela runs")
        logger.info("✅ Índice criado para performance")
        logger.info("✅ Foreign key configurada para chat_sessions")
        return 0
    else:
        logger.error("\n❌ MIGRAÇÃO FALHOU NA VERIFICAÇÃO!")
        return 1

if __name__ == "__main__":
    exit(main())
