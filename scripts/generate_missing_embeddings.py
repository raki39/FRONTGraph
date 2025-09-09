#!/usr/bin/env python3
"""
Script para gerar embeddings para mensagens que não possuem
"""

import os
import sys
import logging
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Constrói URL do banco usando as mesmas configurações da API"""
    host = os.getenv("PG_HOST", "postgres")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB", "agentgraph")
    user = os.getenv("PG_USER", "agent")
    password = os.getenv("PG_PASSWORD", "agent")
    
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

def get_messages_without_embeddings(session):
    """Busca mensagens que não possuem embeddings"""
    result = session.execute(text("""
        SELECT m.id, m.content, m.role, m.chat_session_id
        FROM messages m
        LEFT JOIN message_embeddings me ON m.id = me.message_id
        WHERE me.id IS NULL
        ORDER BY m.id ASC
    """))
    
    return result.fetchall()

def generate_embedding_for_message(message_id, content, role, chat_session_id):
    """Dispara task de embedding para uma mensagem específica"""
    try:
        # Importa a task de embedding
        sys.path.append('/app')  # Para ambiente Docker
        from agentgraph.tasks import generate_message_embedding_task
        
        # Dispara task assíncrona
        task = generate_message_embedding_task.delay(content, chat_session_id, role)
        logger.info(f"✅ Task de embedding disparada para mensagem {message_id}: {task.id}")
        return task.id
        
    except Exception as e:
        logger.error(f"❌ Erro ao disparar embedding para mensagem {message_id}: {e}")
        return None

def main():
    """Função principal"""
    logger.info("🚀 Iniciando geração de embeddings para mensagens antigas...")
    
    try:
        # Conecta ao banco
        database_url = get_database_url()
        engine = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("✅ Conexão com banco estabelecida")
        
        # Busca mensagens sem embeddings
        messages = get_messages_without_embeddings(session)
        
        if not messages:
            logger.info("✅ Todas as mensagens já possuem embeddings!")
            return
        
        logger.info(f"📊 Encontradas {len(messages)} mensagens sem embeddings")
        
        # Processa cada mensagem
        tasks_dispatched = 0
        for message in messages:
            message_id, content, role, chat_session_id = message
            
            logger.info(f"🔄 Processando mensagem {message_id} ({role}): {content[:50]}...")
            
            task_id = generate_embedding_for_message(message_id, content, role, chat_session_id)
            
            if task_id:
                tasks_dispatched += 1
                # Pequena pausa para não sobrecarregar
                time.sleep(0.5)
        
        logger.info(f"✅ {tasks_dispatched} tasks de embedding disparadas!")
        logger.info("⏳ Aguarde alguns segundos para que os embeddings sejam processados...")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
