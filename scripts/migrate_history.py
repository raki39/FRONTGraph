#!/usr/bin/env python3
"""
Migração para adicionar tabelas do sistema de histórico
Versão incluída na imagem Docker
"""

import os
import logging
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Constrói URL do banco usando as mesmas configurações da API"""
    host = os.getenv("PG_HOST", "postgres")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB", "agentgraph")
    user = os.getenv("PG_USER", "agent")
    password = os.getenv("PG_PASSWORD", "agent")
    
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

def create_engine_with_retry():
    """Cria engine do banco com retry"""
    db_url = get_database_url()
    logger.info(f"Conectando ao banco: {db_url.replace(os.getenv('PG_PASSWORD', 'agent'), '***')}")
    
    max_attempts = 10
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

def install_pgvector(engine):
    """Instala extensão pgvector se não existir"""
    try:
        with engine.connect() as conn:
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

def create_history_tables(engine):
    """Cria tabelas do sistema de histórico"""
    try:
        with engine.connect() as conn:
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
                    message_metadata JSONB,
                    
                    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
                );
            """))
            
            # 3. Verifica se pgvector está disponível
            pgvector_available = install_pgvector(engine)
            
            # 4. Tabela message_embeddings - DROP e recria com pgvector
            logger.info("📋 Recriando tabela message_embeddings com pgvector...")
            conn.execute(text("DROP TABLE IF EXISTS message_embeddings CASCADE;"))
            
            if pgvector_available:
                conn.execute(text("""
                    CREATE TABLE message_embeddings (
                        id SERIAL PRIMARY KEY,
                        message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                        embedding vector(1536),
                        model_version VARCHAR(50) DEFAULT 'text-embedding-3-small',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
                logger.info("✅ Tabela message_embeddings criada com pgvector")
            else:
                conn.execute(text("""
                    CREATE TABLE message_embeddings (
                        id SERIAL PRIMARY KEY,
                        message_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
                        embedding_text TEXT,
                        model_version VARCHAR(50) DEFAULT 'text-embedding-3-small',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
                logger.info("✅ Tabela message_embeddings criada sem pgvector")
            
            # 5. Tabela conversation_summaries
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
            
            # 6. Adiciona coluna chat_session_id na tabela runs se não existir
            logger.info("📋 Adicionando chat_session_id na tabela runs...")
            try:
                conn.execute(text("""
                    ALTER TABLE runs 
                    ADD COLUMN IF NOT EXISTS chat_session_id INTEGER 
                    REFERENCES chat_sessions(id) ON DELETE SET NULL;
                """))
            except Exception as e:
                logger.warning(f"⚠️ Coluna chat_session_id pode já existir: {e}")
            
            conn.commit()
            logger.info("✅ Tabelas de histórico criadas com sucesso")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        return False

def create_indexes(engine):
    """Cria índices para performance"""
    try:
        with engine.connect() as conn:
            logger.info("🔍 Criando índices de performance...")
            
            # Índices para chat_sessions
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent_id ON chat_sessions(agent_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_activity ON chat_sessions(last_activity DESC);"))
            
            # Índices para messages
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_chat_session_id ON messages(chat_session_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_sequence_order ON messages(chat_session_id, sequence_order);"))
            
            # Índice vetorial para message_embeddings (só se coluna embedding existir)
            try:
                # Verifica se coluna embedding existe
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'message_embeddings' AND column_name = 'embedding';
                """))
                
                if result.fetchone():
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_message_embeddings_vector 
                        ON message_embeddings USING ivfflat (embedding vector_l2_ops)
                        WITH (lists = 100);
                    """))
                    logger.info("✅ Índice vetorial criado")
                else:
                    logger.info("ℹ️ Coluna embedding não existe - pulando índice vetorial")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível criar índice vetorial: {e}")
            
            # Índices para message_embeddings
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_message_embeddings_message_id ON message_embeddings(message_id);"))
            
            # Índices para conversation_summaries
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversation_summaries_chat_session_id ON conversation_summaries(chat_session_id);"))
            
            # Índice para runs.chat_session_id
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_chat_session_id ON runs(chat_session_id);"))
            
            conn.commit()
            logger.info("✅ Índices criados com sucesso")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar índices: {e}")
        return False

def main():
    """Executa migração completa"""
    logger.info("🚀 Iniciando migração do sistema de histórico...")
    
    try:
        engine = create_engine_with_retry()
        
        success = True
        success &= create_history_tables(engine)
        success &= create_indexes(engine)
        
        if success:
            logger.info("✅ Migração do sistema de histórico concluída com sucesso!")
            logger.info("🎯 Tabelas criadas:")
            logger.info("   - chat_sessions")
            logger.info("   - messages") 
            logger.info("   - message_embeddings")
            logger.info("   - conversation_summaries")
            logger.info("   - runs (coluna chat_session_id adicionada)")
        else:
            logger.error("❌ Migração falhou - verifique os logs acima")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na migração: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
