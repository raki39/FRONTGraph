#!/usr/bin/env python3
"""
Migração para adicionar tabelas do sistema de histórico
Inclui: ChatSession, Message, MessageEmbedding, ConversationSummary
"""

import logging
import time
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

class HistoryMigration:
    def __init__(self):
        self.engine = self._create_engine()
    
    def _create_engine(self):
        """Cria engine do banco com retry para aguardar PostgreSQL"""
        db_url = f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}"
        
        max_attempts = 30
        for attempt in range(1, max_attempts + 1):
            try:
                engine = create_engine(db_url)
                # Testa conexão
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("✅ Conexão com PostgreSQL estabelecida")
                return engine
            except OperationalError as e:
                if attempt == max_attempts:
                    logger.error(f"❌ Falha ao conectar após {max_attempts} tentativas: {e}")
                    raise
                logger.info(f"⏳ Aguardando PostgreSQL... (tentativa {attempt}/{max_attempts})")
                time.sleep(2)
        
        raise Exception("Não foi possível conectar ao PostgreSQL")
    
    def install_pgvector(self):
        """Instala extensão pgvector se não existir"""
        try:
            with self.engine.connect() as conn:
                # Verifica se pgvector já está instalado
                result = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = 'vector'
                    );
                """))
                
                if result.scalar():
                    logger.info("✅ pgvector já está instalado")
                    return True
                
                # Instala pgvector
                logger.info("📦 Instalando extensão pgvector...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("✅ pgvector instalado com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao instalar pgvector: {e}")
            logger.warning("⚠️ Continuando sem pgvector - busca semântica será desabilitada")
            return False
    
    def create_history_tables(self):
        """Cria tabelas do sistema de histórico"""
        try:
            with self.engine.connect() as conn:
                # 1. Tabela chat_sessions
                logger.info("📋 Criando tabela chat_sessions...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        total_messages INTEGER DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'active',
                        context_summary TEXT,
                        
                        -- Índices para performance
                        CONSTRAINT chat_sessions_status_check CHECK (status IN ('active', 'archived'))
                    );
                """))
                
                # 2. Tabela messages
                logger.info("📋 Criando tabela messages...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        chat_session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL,
                        role VARCHAR(20) NOT NULL,
                        content TEXT NOT NULL,
                        sql_query TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        sequence_order INTEGER NOT NULL,
                        metadata JSONB,
                        
                        -- Índices para performance
                        CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
                    );
                """))
                
                # 3. Tabela message_embeddings (só se pgvector estiver disponível)
                pgvector_available = self.install_pgvector()
                if pgvector_available:
                    logger.info("📋 Criando tabela message_embeddings...")
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS message_embeddings (
                            id SERIAL PRIMARY KEY,
                            message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                            embedding vector(1536),
                            model_version VARCHAR(50) DEFAULT 'text-embedding-3-small',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """))
                else:
                    logger.info("📋 Criando tabela message_embeddings (sem vector)...")
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS message_embeddings (
                            id SERIAL PRIMARY KEY,
                            message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                            embedding_text TEXT,  -- Fallback sem pgvector
                            model_version VARCHAR(50) DEFAULT 'text-embedding-3-small',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """))
                
                # 4. Tabela conversation_summaries
                logger.info("📋 Criando tabela conversation_summaries...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS conversation_summaries (
                        id SERIAL PRIMARY KEY,
                        chat_session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        up_to_message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                        summary TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
                
                conn.commit()
                logger.info("✅ Tabelas de histórico criadas com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")
            return False
    
    def create_indexes(self):
        """Cria índices para performance"""
        try:
            with self.engine.connect() as conn:
                logger.info("🔍 Criando índices de performance...")
                
                # Índices para chat_sessions
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id 
                    ON chat_sessions(user_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent_id 
                    ON chat_sessions(agent_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_activity 
                    ON chat_sessions(last_activity DESC);
                """))
                
                # Índices para messages
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_chat_session_id 
                    ON messages(chat_session_id);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_created_at 
                    ON messages(created_at DESC);
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_messages_sequence_order 
                    ON messages(chat_session_id, sequence_order);
                """))
                
                # Índice vetorial para message_embeddings (se pgvector disponível)
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_message_embeddings_vector 
                        ON message_embeddings USING ivfflat (embedding vector_l2_ops)
                        WITH (lists = 100);
                    """))
                    logger.info("✅ Índice vetorial criado")
                except Exception as e:
                    logger.warning(f"⚠️ Não foi possível criar índice vetorial: {e}")
                
                # Índices para message_embeddings
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_message_embeddings_message_id 
                    ON message_embeddings(message_id);
                """))
                
                # Índices para conversation_summaries
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_conversation_summaries_chat_session_id 
                    ON conversation_summaries(chat_session_id);
                """))
                
                conn.commit()
                logger.info("✅ Índices criados com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar índices: {e}")
            return False
    
    def run_migration(self):
        """Executa migração completa"""
        logger.info("🚀 Iniciando migração do sistema de histórico...")
        
        success = True
        success &= self.create_history_tables()
        success &= self.create_indexes()
        
        if success:
            logger.info("✅ Migração do sistema de histórico concluída com sucesso!")
        else:
            logger.error("❌ Migração falhou - verifique os logs acima")
        
        return success

def main():
    """Executa migração"""
    logging.basicConfig(level=logging.INFO)
    migration = HistoryMigration()
    return migration.run_migration()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
