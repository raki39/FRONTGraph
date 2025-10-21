#!/usr/bin/env python3
"""
Migração específica para adicionar coluna role na tabela users
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_user_role():
    """Adiciona coluna role na tabela users com tipo ENUM correto"""
    
    # Configurações do banco (Docker)
    db_url = "postgresql+psycopg2://agent:agent@postgres:5432/agentgraph"
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            logger.info("🔍 Verificando se tipo ENUM userrole existe...")
            
            # Verificar se o tipo ENUM já existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'userrole'
                );
            """))
            enum_exists = result.scalar()
            
            if not enum_exists:
                logger.info("📝 Criando tipo ENUM userrole...")
                conn.execute(text("""
                    CREATE TYPE userrole AS ENUM ('USER', 'ADMIN', 'SUPER_ADMIN');
                """))
                logger.info("✅ Tipo ENUM userrole criado")
            else:
                logger.info("✅ Tipo ENUM userrole já existe")
            
            # Verificar se a coluna role já existe
            logger.info("🔍 Verificando se coluna role existe...")
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'role'
                );
            """))
            column_exists = result.scalar()
            
            if not column_exists:
                logger.info("📝 Adicionando coluna role à tabela users...")
                conn.execute(text("""
                    ALTER TABLE users ADD COLUMN role userrole NOT NULL DEFAULT 'USER';
                """))
                logger.info("✅ Coluna role adicionada com sucesso")
            else:
                logger.info("✅ Coluna role já existe")
            
            # Commit das mudanças
            conn.commit()
            logger.info("🎉 Migração concluída com sucesso!")
            
    except Exception as e:
        logger.error(f"❌ Erro durante migração: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_user_role()
    sys.exit(0 if success else 1)
