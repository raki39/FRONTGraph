#!/usr/bin/env python3
"""
Sistema de migração dinâmica para AgentAPI

Atualiza automaticamente as tabelas do PostgreSQL baseado nos modelos SQLAlchemy.
Detecta diferenças entre o schema atual e o definido nos models.py e aplica as mudanças.

Uso:
    python -m api.db.migrate
    docker compose -f docker-compose.api.yml exec api python -m api.db.migrate
"""

import os
import sys
import logging
import time
from typing import Dict, List, Set, Tuple
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.models import Base
from api.core.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.engine = self._create_engine()
        self.inspector = inspect(self.engine)
        
    def _create_engine(self) -> Engine:
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
    
    def get_existing_tables(self) -> Set[str]:
        """Retorna conjunto de tabelas existentes no banco"""
        return set(self.inspector.get_table_names())
    
    def get_model_tables(self) -> Dict[str, Table]:
        """Retorna dicionário de tabelas definidas nos modelos"""
        return {table.name: table for table in Base.metadata.tables.values()}
    
    def get_existing_columns(self, table_name: str) -> Dict[str, Dict]:
        """Retorna colunas existentes de uma tabela"""
        try:
            columns = self.inspector.get_columns(table_name)
            return {col['name']: col for col in columns}
        except Exception:
            return {}
    
    def get_model_columns(self, table: Table) -> Dict[str, Column]:
        """Retorna colunas definidas no modelo"""
        return {col.name: col for col in table.columns}
    
    def create_missing_tables(self) -> List[str]:
        """Cria tabelas que existem nos modelos mas não no banco"""
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        
        missing_tables = []
        for table_name, table in model_tables.items():
            if table_name not in existing_tables:
                missing_tables.append(table_name)
                logger.info(f"📝 Criando tabela: {table_name}")
                table.create(self.engine)
                logger.info(f"✅ Tabela {table_name} criada com sucesso")
        
        return missing_tables
    
    def add_missing_columns(self) -> List[Tuple[str, str]]:
        """Adiciona colunas que existem nos modelos mas não no banco"""
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        
        added_columns = []
        
        for table_name, table in model_tables.items():
            if table_name not in existing_tables:
                continue  # Tabela será criada por create_missing_tables
            
            existing_columns = self.get_existing_columns(table_name)
            model_columns = self.get_model_columns(table)
            
            for col_name, col in model_columns.items():
                if col_name not in existing_columns:
                    logger.info(f"📝 Adicionando coluna {col_name} à tabela {table_name}")
                    
                    # Construir comando ALTER TABLE
                    col_type = col.type.compile(self.engine.dialect)
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    
                    # Definir valor padrão se necessário
                    default_clause = ""
                    if col.default is not None:
                        if hasattr(col.default, 'arg'):
                            if callable(col.default.arg):
                                # Para funções como func.now()
                                default_clause = f" DEFAULT {col.default.arg.__name__}()"
                            else:
                                default_clause = f" DEFAULT '{col.default.arg}'"
                        else:
                            default_clause = f" DEFAULT '{col.default}'"
                    
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{default_clause}"
                    
                    try:
                        with self.engine.connect() as conn:
                            conn.execute(text(alter_sql))
                            conn.commit()
                        logger.info(f"✅ Coluna {col_name} adicionada à tabela {table_name}")
                        added_columns.append((table_name, col_name))
                    except Exception as e:
                        logger.error(f"❌ Erro ao adicionar coluna {col_name} à tabela {table_name}: {e}")
        
        return added_columns
    
    def verify_schema(self) -> bool:
        """Verifica se o schema atual está sincronizado com os modelos"""
        logger.info("🔍 Verificando sincronização do schema...")
        
        existing_tables = self.get_existing_tables()
        model_tables = self.get_model_tables()
        
        issues = []
        
        # Verificar tabelas faltantes
        missing_tables = set(model_tables.keys()) - existing_tables
        if missing_tables:
            issues.append(f"Tabelas faltantes: {', '.join(missing_tables)}")
        
        # Verificar colunas faltantes
        for table_name, table in model_tables.items():
            if table_name not in existing_tables:
                continue
            
            existing_columns = set(self.get_existing_columns(table_name).keys())
            model_columns = set(self.get_model_columns(table).keys())
            missing_columns = model_columns - existing_columns
            
            if missing_columns:
                issues.append(f"Colunas faltantes em {table_name}: {', '.join(missing_columns)}")
        
        if issues:
            logger.warning("⚠️ Schema não está sincronizado:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            return False
        else:
            logger.info("✅ Schema está sincronizado")
            return True
    
    def run_migration(self, verify_only: bool = False) -> bool:
        """Executa migração completa"""
        logger.info("🚀 INICIANDO MIGRAÇÃO DO BANCO DE DADOS")
        logger.info("=" * 60)
        
        try:
            if verify_only:
                return self.verify_schema()
            
            # 1. Verificar estado atual
            if self.verify_schema():
                logger.info("✅ Schema já está atualizado. Nenhuma migração necessária.")
                return True
            
            # 2. Criar tabelas faltantes
            logger.info("📋 Criando tabelas faltantes...")
            missing_tables = self.create_missing_tables()
            if missing_tables:
                logger.info(f"✅ {len(missing_tables)} tabelas criadas: {', '.join(missing_tables)}")
            else:
                logger.info("ℹ️ Nenhuma tabela faltante encontrada")
            
            # 3. Adicionar colunas faltantes
            logger.info("📋 Adicionando colunas faltantes...")
            added_columns = self.add_missing_columns()
            if added_columns:
                logger.info(f"✅ {len(added_columns)} colunas adicionadas")
                for table, column in added_columns:
                    logger.info(f"  - {table}.{column}")
            else:
                logger.info("ℹ️ Nenhuma coluna faltante encontrada")
            
            # 4. Executar migrações específicas
            logger.info("📋 Executando migrações específicas...")
            self._run_agent_ui_migration()

            # 5. Verificação final
            logger.info("🔍 Verificação final...")
            if self.verify_schema():
                logger.info("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
                return True
            else:
                logger.error("❌ Migração falhou na verificação final")
                return False
                
        except Exception as e:
            logger.error(f"💥 Erro durante migração: {e}")
            return False
        finally:
            logger.info("=" * 60)

    def _run_agent_ui_migration(self):
        """Executa migração específica para campos UI/UX dos agentes"""
        try:
            logger.info("🎨 Executando migração de campos UI/UX dos agentes...")

            with self.engine.connect() as conn:
                # Verifica se as colunas já existem
                existing_columns = set()
                try:
                    columns = self.inspector.get_columns('agents')
                    existing_columns = {col['name'] for col in columns}
                except Exception:
                    logger.warning("⚠️ Não foi possível verificar colunas existentes")
                    return

                # Lista de colunas para adicionar
                ui_columns = {
                    'description': 'TEXT',
                    'icon': "VARCHAR(100) DEFAULT 'MessageSquare'",
                    'color': "VARCHAR(100) DEFAULT 'from-blue-500 to-cyan-500'",
                    'features': 'TEXT'
                }

                # Adiciona colunas que não existem
                for column_name, column_def in ui_columns.items():
                    if column_name not in existing_columns:
                        logger.info(f"➕ Adicionando coluna 'agents.{column_name}'")
                        conn.execute(text(f"ALTER TABLE agents ADD COLUMN {column_name} {column_def}"))
                    else:
                        logger.info(f"✅ Coluna 'agents.{column_name}' já existe")

                conn.commit()
                logger.info("✅ Migração de campos UI/UX concluída")

        except Exception as e:
            logger.error(f"❌ Erro na migração de campos UI/UX: {e}")

    def create_seed_data(self):
        """Cria dados iniciais (admin user)"""
        logger.info("🌱 Criando dados iniciais...")
        
        try:
            from api.db.session import SessionLocal
            from api.models import User
            from api.core.security import get_password_hash
            from sqlalchemy import select
            
            db = SessionLocal()
            try:
                # Verificar se admin já existe
                existing_admin = db.execute(
                    select(User).where(User.email == "admin@example.com")
                ).scalar_one_or_none()
                
                if not existing_admin:
                    admin_user = User(
                        email="admin@example.com",
                        nome="Administrador",
                        senha_hash=get_password_hash("admin"),
                        ativo=True
                    )
                    db.add(admin_user)
                    db.commit()
                    logger.info("✅ Usuário admin criado: admin@example.com / admin")
                else:
                    logger.info("ℹ️ Usuário admin já existe")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar dados iniciais: {e}")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sistema de migração da AgentAPI")
    parser.add_argument(
        "--verify-only", 
        action="store_true", 
        help="Apenas verifica se o schema está sincronizado"
    )
    parser.add_argument(
        "--seed", 
        action="store_true", 
        help="Cria dados iniciais após migração"
    )
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator()
    
    success = migrator.run_migration(verify_only=args.verify_only)
    
    if success and args.seed and not args.verify_only:
        migrator.create_seed_data()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
