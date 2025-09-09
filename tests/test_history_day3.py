#!/usr/bin/env python3
"""
Teste das implementações do Dia 3 - Sistema de Histórico
Valida: PostgreSQL + pgvector, tabelas, modelos, schemas, embedding service
"""

import os
import sys
import logging
import asyncio
from datetime import datetime

# Adiciona paths para imports
sys.path.append('.')
sys.path.append('./api')
sys.path.append('./agentgraph')

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoryDay3Tester:
    """Testa todas as implementações do Dia 3"""
    
    def __init__(self):
        self.results = {
            "pgvector_installation": False,
            "tables_creation": False,
            "models_import": False,
            "schemas_import": False,
            "embedding_service": False,
            "database_connection": False,
            "basic_crud": False
        }
    
    def test_pgvector_installation(self):
        """Testa instalação do pgvector"""
        logger.info("🔍 Testando instalação do pgvector...")
        
        try:
            from api.db.migration_add_history_tables import HistoryMigration
            migration = HistoryMigration()
            
            # Testa instalação do pgvector
            pgvector_ok = migration.install_pgvector()
            
            if pgvector_ok:
                logger.info("✅ pgvector instalado e funcionando")
                self.results["pgvector_installation"] = True
            else:
                logger.warning("⚠️ pgvector não disponível - continuando sem busca vetorial")
                self.results["pgvector_installation"] = False
                
        except Exception as e:
            logger.error(f"❌ Erro ao testar pgvector: {e}")
            self.results["pgvector_installation"] = False
    
    def test_tables_creation(self):
        """Testa criação das tabelas"""
        logger.info("🔍 Testando criação das tabelas...")
        
        try:
            from api.db.migration_add_history_tables import HistoryMigration
            migration = HistoryMigration()
            
            # Executa migração completa
            success = migration.run_migration()
            
            if success:
                logger.info("✅ Tabelas de histórico criadas com sucesso")
                self.results["tables_creation"] = True
            else:
                logger.error("❌ Falha ao criar tabelas")
                self.results["tables_creation"] = False
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar tabelas: {e}")
            self.results["tables_creation"] = False
    
    def test_models_import(self):
        """Testa importação dos modelos SQLAlchemy"""
        logger.info("🔍 Testando importação dos modelos...")
        
        try:
            from api.models import ChatSession, Message, MessageEmbedding, ConversationSummary
            
            # Verifica se os modelos têm os atributos esperados
            assert hasattr(ChatSession, 'id')
            assert hasattr(ChatSession, 'user_id')
            assert hasattr(ChatSession, 'agent_id')
            assert hasattr(ChatSession, 'title')
            assert hasattr(ChatSession, 'messages')
            
            assert hasattr(Message, 'id')
            assert hasattr(Message, 'chat_session_id')
            assert hasattr(Message, 'role')
            assert hasattr(Message, 'content')
            assert hasattr(Message, 'embedding')
            
            assert hasattr(MessageEmbedding, 'id')
            assert hasattr(MessageEmbedding, 'message_id')
            
            assert hasattr(ConversationSummary, 'id')
            assert hasattr(ConversationSummary, 'chat_session_id')
            
            logger.info("✅ Modelos SQLAlchemy importados e validados")
            self.results["models_import"] = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar modelos: {e}")
            self.results["models_import"] = False
    
    def test_schemas_import(self):
        """Testa importação dos schemas Pydantic"""
        logger.info("🔍 Testando importação dos schemas...")
        
        try:
            from api.schemas import (
                ChatSessionCreate, ChatSessionOut, ChatSessionUpdate,
                MessageCreate, MessageOut, MessageEmbeddingOut,
                ConversationSummaryOut, ChatSessionWithMessages
            )
            
            # Testa criação de schemas
            chat_create = ChatSessionCreate(agent_id=1, title="Teste")
            assert chat_create.agent_id == 1
            assert chat_create.title == "Teste"
            
            message_create = MessageCreate(
                role="user",
                content="Teste de mensagem"
            )
            assert message_create.role == "user"
            assert message_create.content == "Teste de mensagem"
            
            logger.info("✅ Schemas Pydantic importados e validados")
            self.results["schemas_import"] = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar schemas: {e}")
            self.results["schemas_import"] = False
    
    def test_embedding_service(self):
        """Testa serviço de embedding"""
        logger.info("🔍 Testando serviço de embedding...")
        
        try:
            from agentgraph.services.embedding_service import EmbeddingService, get_embedding_service
            
            # Verifica se OpenAI API key está configurada
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                logger.warning("⚠️ OPENAI_API_KEY não configurada - pulando teste de embedding")
                self.results["embedding_service"] = False
                return
            
            # Testa criação do serviço
            service = EmbeddingService(model="text-embedding-3-small")
            
            # Testa geração de embedding (com texto pequeno para economizar)
            test_text = "Teste de embedding"
            embedding = service.get_embedding(test_text)
            
            # Valida embedding
            assert isinstance(embedding, list)
            assert len(embedding) == 1536  # Dimensões do text-embedding-3-small
            assert all(isinstance(x, float) for x in embedding)
            
            # Testa função singleton
            service2 = get_embedding_service()
            assert service2 is not None
            
            # Testa informações do modelo
            info = service.get_model_info()
            assert info["model"] == "text-embedding-3-small"
            assert info["dimensions"] == 1536
            
            logger.info("✅ Serviço de embedding funcionando")
            self.results["embedding_service"] = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao testar embedding service: {e}")
            self.results["embedding_service"] = False
    
    def test_database_connection(self):
        """Testa conexão com banco de dados"""
        logger.info("🔍 Testando conexão com banco de dados...")
        
        try:
            from api.db.session import engine
            from sqlalchemy import text
            
            # Testa conexão
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            
            logger.info("✅ Conexão com PostgreSQL funcionando")
            self.results["database_connection"] = True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com banco: {e}")
            self.results["database_connection"] = False
    
    def test_basic_crud(self):
        """Testa operações CRUD básicas"""
        logger.info("🔍 Testando operações CRUD básicas...")
        
        try:
            from api.db.session import SessionLocal
            from api.models import ChatSession, Message, User, Agent, AgentConnection
            from sqlalchemy import text
            
            db = SessionLocal()
            
            try:
                # Verifica se as tabelas existem
                tables_to_check = [
                    'chat_sessions', 'messages', 'message_embeddings', 'conversation_summaries'
                ]
                
                for table in tables_to_check:
                    result = db.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table}'
                        );
                    """))
                    
                    if not result.scalar():
                        raise Exception(f"Tabela {table} não encontrada")
                
                logger.info("✅ Todas as tabelas de histórico existem")
                
                # Testa se consegue fazer query básica (sem inserir dados)
                result = db.execute(text("SELECT COUNT(*) FROM chat_sessions"))
                count = result.scalar()
                logger.info(f"✅ Query básica funcionando - {count} sessões de chat")
                
                self.results["basic_crud"] = True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Erro ao testar CRUD: {e}")
            self.results["basic_crud"] = False
    
    def run_all_tests(self):
        """Executa todos os testes"""
        logger.info("🚀 Iniciando testes do Dia 3 - Sistema de Histórico")
        logger.info("=" * 60)
        
        # Executa testes em ordem
        self.test_database_connection()
        self.test_pgvector_installation()
        self.test_tables_creation()
        self.test_models_import()
        self.test_schemas_import()
        self.test_embedding_service()
        self.test_basic_crud()
        
        # Relatório final
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO FINAL - DIA 3")
        logger.info("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(self.results.values())
        
        for test_name, result in self.results.items():
            status = "✅ PASSOU" if result else "❌ FALHOU"
            logger.info(f"{test_name:25} | {status}")
        
        logger.info("-" * 60)
        logger.info(f"TOTAL: {passed_tests}/{total_tests} testes passaram")
        
        if passed_tests == total_tests:
            logger.info("🎉 TODOS OS TESTES PASSARAM - DIA 3 COMPLETO!")
            return True
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} testes falharam")
            return False

def main():
    """Função principal"""
    tester = HistoryDay3Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 DIA 3 CONCLUÍDO COM SUCESSO!")
        print("✅ PostgreSQL + pgvector funcionando")
        print("✅ Tabelas criadas e testadas")
        print("✅ Modelos SQLAlchemy + Schemas operacionais")
        print("✅ Embedding service básico funcionando")
        print("\n🚀 Pronto para continuar com o Dia 4!")
    else:
        print("\n❌ DIA 3 INCOMPLETO - Verifique os erros acima")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
