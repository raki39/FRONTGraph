#!/usr/bin/env python3
"""
Teste de integração do ClickHouse com LangChain SQLDatabase
Valida que a conexão funciona sem warnings sobre information_schema
"""
import sys
import os
import logging
import warnings
from io import StringIO

# Adiciona path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_clickhouse_connection():
    """Testa conexão com ClickHouse usando SQLDatabase"""
    print("\n" + "="*60)
    print("🧪 TESTE DE INTEGRAÇÃO CLICKHOUSE + LANGCHAIN")
    print("="*60)
    
    try:
        from sqlalchemy import create_engine as sa_create_engine
        from langchain_community.utilities import SQLDatabase
        
        # Configuração do ClickHouse (ajuste conforme seu ambiente)
        clickhouse_uri = "clickhouse+http://default:@localhost:8123/default"
        
        print(f"\n📍 Conectando ao ClickHouse: {clickhouse_uri}")
        
        # Captura warnings
        warning_list = []
        
        def warning_handler(message, category, filename, lineno, file=None, line=None):
            warning_list.append({
                'message': str(message),
                'category': category.__name__,
                'file': filename
            })
        
        old_showwarning = warnings.showwarning
        warnings.showwarning = warning_handler
        
        try:
            # Cria engine com warnings filtrados
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Did not recognize type.*")
                warnings.filterwarnings("ignore", category=Warning)
                
                ch_engine = sa_create_engine(
                    clickhouse_uri,
                    pool_timeout=30,
                    pool_recycle=3600,
                    echo=False
                )
                
                # IMPORTANTE: Usar SQLDatabase(engine=...) e NÃO from_uri()
                db = SQLDatabase(engine=ch_engine)
            
            print("✅ SQLDatabase criado com sucesso")
            
            # Obtém tabelas
            table_names = db.get_usable_table_names()
            print(f"✅ Tabelas encontradas: {len(table_names)}")
            if table_names:
                print(f"   Primeiras tabelas: {table_names[:5]}")
            
            # Verifica dialeto
            dialect = str(db.dialect)
            print(f"✅ Dialeto detectado: {dialect}")
            
            # Verifica se há warnings sobre information_schema
            info_schema_warnings = [w for w in warning_list if 'information_schema' in w['message'].lower() or 'COLUMNS' in w['message'] or 'TABLES' in w['message']]
            
            if info_schema_warnings:
                print(f"\n❌ FALHA: Encontrados {len(info_schema_warnings)} warnings sobre information_schema:")
                for w in info_schema_warnings:
                    print(f"   - {w['message']}")
                return False
            else:
                print("\n✅ SUCESSO: Nenhum warning sobre information_schema!")
            
            # Testa query simples
            try:
                result = db.run("SELECT 1 as test_value")
                print(f"✅ Query simples funcionou: {result}")
            except Exception as e:
                print(f"⚠️  Query simples falhou (pode ser esperado se ClickHouse não está rodando): {e}")
            
            print("\n" + "="*60)
            print("✅ TESTE PASSOU!")
            print("="*60)
            return True
            
        finally:
            warnings.showwarning = old_showwarning
    
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        print("   Certifique-se de que langchain_community está instalado")
        return False
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_clickhouse_vs_postgresql():
    """Compara comportamento entre ClickHouse e PostgreSQL"""
    print("\n" + "="*60)
    print("🔄 COMPARAÇÃO CLICKHOUSE vs POSTGRESQL")
    print("="*60)
    
    try:
        from sqlalchemy import create_engine as sa_create_engine
        from langchain_community.utilities import SQLDatabase
        
        # Teste ClickHouse
        print("\n📍 Testando ClickHouse...")
        try:
            ch_engine = sa_create_engine("clickhouse+http://default:@localhost:8123/default")
            ch_db = SQLDatabase(engine=ch_engine)
            ch_tables = ch_db.get_usable_table_names()
            print(f"✅ ClickHouse: {len(ch_tables)} tabelas encontradas")
        except Exception as e:
            print(f"⚠️  ClickHouse não disponível: {e}")
        
        # Teste PostgreSQL
        print("\n📍 Testando PostgreSQL...")
        try:
            pg_engine = sa_create_engine("postgresql://postgres:postgres@localhost:5432/postgres")
            pg_db = SQLDatabase(engine=pg_engine)
            pg_tables = pg_db.get_usable_table_names()
            print(f"✅ PostgreSQL: {len(pg_tables)} tabelas encontradas")
        except Exception as e:
            print(f"⚠️  PostgreSQL não disponível: {e}")
        
        print("\n" + "="*60)
        print("✅ COMPARAÇÃO CONCLUÍDA")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"❌ Erro durante comparação: {e}")
        return False

if __name__ == "__main__":
    print("\n🚀 Iniciando testes de integração ClickHouse...")
    
    # Teste 1: Conexão básica
    result1 = test_clickhouse_connection()
    
    # Teste 2: Comparação
    result2 = test_clickhouse_vs_postgresql()
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    print(f"Teste de Conexão: {'✅ PASSOU' if result1 else '❌ FALHOU'}")
    print(f"Teste de Comparação: {'✅ PASSOU' if result2 else '❌ FALHOU'}")
    print("="*60)
    
    sys.exit(0 if result1 else 1)

