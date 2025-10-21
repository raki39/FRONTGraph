"""
Migração para adicionar campos de UI/UX aos agentes
Adiciona: description, icon, color, features
"""

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade(engine):
    """Adiciona novos campos de UI/UX à tabela agents"""
    try:
        logger.info("🔄 Iniciando migração: Adicionando campos de UI/UX aos agentes")
        
        with engine.connect() as conn:
            # Verifica se as colunas já existem
            result = conn.execute(text("PRAGMA table_info(agents)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            # Adiciona description se não existir
            if 'description' not in existing_columns:
                logger.info("➕ Adicionando coluna 'description'")
                conn.execute(text("ALTER TABLE agents ADD COLUMN description TEXT"))
            else:
                logger.info("✅ Coluna 'description' já existe")
            
            # Adiciona icon se não existir
            if 'icon' not in existing_columns:
                logger.info("➕ Adicionando coluna 'icon'")
                conn.execute(text("ALTER TABLE agents ADD COLUMN icon VARCHAR(100) DEFAULT 'MessageSquare'"))
            else:
                logger.info("✅ Coluna 'icon' já existe")
            
            # Adiciona color se não existir
            if 'color' not in existing_columns:
                logger.info("➕ Adicionando coluna 'color'")
                conn.execute(text("ALTER TABLE agents ADD COLUMN color VARCHAR(100) DEFAULT 'from-blue-500 to-cyan-500'"))
            else:
                logger.info("✅ Coluna 'color' já existe")
            
            # Adiciona features se não existir
            if 'features' not in existing_columns:
                logger.info("➕ Adicionando coluna 'features'")
                conn.execute(text("ALTER TABLE agents ADD COLUMN features TEXT"))
            else:
                logger.info("✅ Coluna 'features' já existe")
            
            # Commit das alterações
            conn.commit()
            
        logger.info("✅ Migração concluída: Campos de UI/UX adicionados aos agentes")
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        raise

def downgrade(engine):
    """Remove os campos de UI/UX da tabela agents"""
    try:
        logger.info("🔄 Iniciando rollback: Removendo campos de UI/UX dos agentes")
        
        with engine.connect() as conn:
            # SQLite não suporta DROP COLUMN diretamente
            # Precisaríamos recriar a tabela, mas por segurança vamos apenas avisar
            logger.warning("⚠️ SQLite não suporta DROP COLUMN. Campos mantidos por segurança.")
            logger.info("💡 Para remover completamente, seria necessário recriar a tabela")
            
        logger.info("✅ Rollback concluído (campos mantidos por segurança)")
        
    except Exception as e:
        logger.error(f"❌ Erro no rollback: {e}")
        raise

if __name__ == "__main__":
    # Para teste direto
    from api.db.session import engine
    upgrade(engine)
