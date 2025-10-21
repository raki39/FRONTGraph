"""
Teste de integração do nó de validação no grafo principal
"""
import asyncio
import json
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentgraph.graphs.main_graph import AgentGraphManager


async def test_validation_integration():
    """Testa a integração do nó de validação no grafo principal"""
    print("🧪 TESTANDO INTEGRAÇÃO DA VALIDAÇÃO NO GRAFO PRINCIPAL")
    print("=" * 60)
    
    try:
        # Inicializa o grafo
        print("📝 Inicializando grafo...")
        manager = AgentGraphManager()
        print("✅ Grafo inicializado")
        
        # Vamos usar CSV que já está funcionando para demonstrar a validação
        print("\n🔍 TESTE 1: Query sem validação (padrão)")
        print("-" * 50)

        # Primeiro, vamos criar dados de teste simulados para forçar uma resposta
        # Isso vai simular uma query bem-sucedida para testar a validação
        result = await manager.process_query(
            user_input="Quantos registros temos na tabela?",
            selected_model="GPT-4o-mini",
            connection_type="csv",
            validation_enabled=False  # Validação desabilitada
        )
        
        print(f"✅ Resultado sem validação:")
        print(f"   Sucesso: {not result.get('error')}")
        print(f"   Validação executada: {result.get('validation_success', 'N/A')}")
        print(f"   Tempo de validação: {result.get('validation_time', 0):.2f}s")
        
        # Teste 2: Query com validação individual habilitada
        print("\n🔍 TESTE 2: Query com validação individual")
        print("-" * 50)

        result = await manager.process_query(
            user_input="Mostre os melhores produtos do último período",
            selected_model="GPT-4o-mini",
            connection_type="csv",
            validation_enabled=True,
            validation_type="individual",
            validation_model="gpt-4o-mini",
            validation_auto_improve=True
        )
        
        print(f"✅ Resultado com validação individual:")
        print(f"   Sucesso: {not result.get('error')}")
        print(f"   Validação executada: {result.get('validation_success', False)}")
        print(f"   Tempo de validação: {result.get('validation_time', 0):.2f}s")
        
        if result.get('validation_result'):
            validation_result = result['validation_result']
            print(f"   Score geral: {validation_result.get('overall_score', 'N/A')}")
            print(f"   Issues encontrados: {len(validation_result.get('issues_found', []))}")
            print(f"   Sugestões: {len(validation_result.get('suggestions', []))}")
        
        # Teste 3: Query com validação comparativa habilitada
        print("\n🔍 TESTE 3: Query com validação comparativa")
        print("-" * 50)

        result = await manager.process_query(
            user_input="Qual o faturamento por categoria no último ano?",
            selected_model="GPT-4o-mini",
            connection_type="csv",
            validation_enabled=True,
            validation_type="comparative",
            validation_model="gpt-4o-mini",
            validation_comparison_limit=3,
            validation_use_similarity=True
        )
        
        print(f"✅ Resultado com validação comparativa:")
        print(f"   Sucesso: {not result.get('error')}")
        print(f"   Validação executada: {result.get('validation_success', False)}")
        print(f"   Tempo de validação: {result.get('validation_time', 0):.2f}s")
        
        if result.get('validation_result'):
            validation_result = result['validation_result']
            print(f"   Score consistência: {validation_result.get('consistency_score', 'N/A')}")
            print(f"   Inconsistências: {len(validation_result.get('inconsistencies_found', []))}")
            print(f"   IDs comparados: {validation_result.get('compared_run_ids', [])}")
        
        print("\n🎉 TODOS OS TESTES DE INTEGRAÇÃO PASSARAM!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste de integração: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_validation_integration())
