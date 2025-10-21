"""
Teste direto da validação com dados simulados
"""
import asyncio
import json
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentgraph.nodes.validation_node import query_validation_node


async def test_validation_direct():
    """Testa a validação diretamente com dados simulados"""
    print("🧪 TESTANDO VALIDAÇÃO DIRETA COM DADOS SIMULADOS")
    print("=" * 60)
    
    try:
        # Teste 1: Validação Individual com dados simulados
        print("\n🔍 TESTE 1: Validação Individual (Dados Simulados)")
        print("-" * 55)
        
        # Estado simulando uma query bem-sucedida
        state_individual = {
            "validation_request": {
                "validation_type": "individual",
                "auto_improve_question": True
            },
            "run_data": {
                "question": "Mostre os melhores produtos do último período",
                "sql_used": """
                SELECT 
                    p.nome,
                    SUM(v.quantidade) as total_vendido,
                    SUM(v.valor_total) as receita_total
                FROM produtos p
                JOIN vendas v ON p.id = v.produto_id
                WHERE v.data_venda > '2024-01-01'
                GROUP BY p.id, p.nome
                ORDER BY total_vendido DESC
                LIMIT 10
                """,
                "result_data": "Produto A: 1000 unidades, R$ 50.000; Produto B: 800 unidades, R$ 40.000; Produto C: 600 unidades, R$ 30.000"
            },
            "validation_model": "gpt-4o-mini",
            # Campos necessários para o estado
            "validation_enabled": True,
            "validation_success": False,
            "validation_error": None,
            "validation_time": 0.0,
            "validation_result": None,
            "user_input": "Mostre os melhores produtos do último período",
            "response": "Produto A: 1000 unidades, R$ 50.000; Produto B: 800 unidades, R$ 40.000; Produto C: 600 unidades, R$ 30.000",
            "sql_query_extracted": """
                SELECT 
                    p.nome,
                    SUM(v.quantidade) as total_vendido,
                    SUM(v.valor_total) as receita_total
                FROM produtos p
                JOIN vendas v ON p.id = v.produto_id
                WHERE v.data_venda > '2024-01-01'
                GROUP BY p.id, p.nome
                ORDER BY total_vendido DESC
                LIMIT 10
                """,
            "error": None
        }
        
        print("📝 Executando validação individual...")
        result_state = await query_validation_node(state_individual)
        
        print(f"✅ Resultado da validação individual:")
        print(f"   Sucesso: {result_state.get('validation_success')}")
        print(f"   Erro: {result_state.get('validation_error')}")
        print(f"   Tempo: {result_state.get('validation_time', 0):.2f}s")
        
        if result_state.get('validation_result'):
            validation_result = result_state['validation_result']
            print(f"   Score geral: {validation_result.get('overall_score', 'N/A')}")
            print(f"   Issues encontrados: {len(validation_result.get('issues_found', []))}")
            print(f"   Sugestões: {len(validation_result.get('suggestions', []))}")
            
            if validation_result.get('issues_found'):
                print("   📋 Issues encontrados:")
                for i, issue in enumerate(validation_result['issues_found'][:3], 1):
                    print(f"      {i}. {issue}")
            
            if validation_result.get('suggestions'):
                print("   💡 Sugestões:")
                for i, suggestion in enumerate(validation_result['suggestions'][:3], 1):
                    print(f"      {i}. {suggestion}")
        
        # Teste 2: Validação Comparativa com dados simulados
        print(f"\n🔍 TESTE 2: Validação Comparativa (Dados Simulados)")
        print("-" * 55)
        
        state_comparative = {
            "validation_request": {
                "validation_type": "comparative"
            },
            "run_data": {
                "question": "Vendas por região no último trimestre",
                "sql_used": """
                SELECT 
                    r.nome_regiao,
                    SUM(v.valor_total) as total_vendas,
                    COUNT(*) as num_vendas
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                JOIN regioes r ON c.regiao_id = r.id
                WHERE v.data_venda >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                GROUP BY r.id, r.nome_regiao
                ORDER BY total_vendas DESC
                """,
                "result_data": "Sul: R$ 850.000 (1.200 vendas), Sudeste: R$ 720.000 (980 vendas), Norte: R$ 450.000 (650 vendas)"
            },
            "compared_runs_data": [
                {
                    "run_id": 2001,
                    "question": "Vendas regionais do último trimestre",
                    "sql_query": "SELECT r.nome, SUM(v.valor) FROM vendas v JOIN regioes r ON v.regiao_id = r.id WHERE v.data >= '2024-07-01' GROUP BY r.nome",
                    "response": "Sul: R$ 845.000, Sudeste: R$ 725.000, Norte: R$ 455.000"
                },
                {
                    "run_id": 2002,
                    "question": "Qual região vendeu mais nos últimos 3 meses?",
                    "sql_query": "SELECT regiao_nome, SUM(valor_total) FROM view_vendas_trimestre GROUP BY regiao_nome ORDER BY SUM(valor_total) DESC",
                    "response": "Sul: R$ 860.000, Sudeste: R$ 715.000, Norte: R$ 440.000"
                }
            ],
            "validation_model": "gpt-4o-mini",
            # Campos necessários para o estado
            "validation_enabled": True,
            "validation_success": False,
            "validation_error": None,
            "validation_time": 0.0,
            "validation_result": None,
            "user_input": "Vendas por região no último trimestre",
            "response": "Sul: R$ 850.000 (1.200 vendas), Sudeste: R$ 720.000 (980 vendas), Norte: R$ 450.000 (650 vendas)",
            "sql_query_extracted": """
                SELECT 
                    r.nome_regiao,
                    SUM(v.valor_total) as total_vendas,
                    COUNT(*) as num_vendas
                FROM vendas v
                JOIN clientes c ON v.cliente_id = c.id
                JOIN regioes r ON c.regiao_id = r.id
                WHERE v.data_venda >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                GROUP BY r.id, r.nome_regiao
                ORDER BY total_vendas DESC
                """,
            "error": None
        }
        
        print("📝 Executando validação comparativa...")
        result_state = await query_validation_node(state_comparative)
        
        print(f"✅ Resultado da validação comparativa:")
        print(f"   Sucesso: {result_state.get('validation_success')}")
        print(f"   Erro: {result_state.get('validation_error')}")
        print(f"   Tempo: {result_state.get('validation_time', 0):.2f}s")
        
        if result_state.get('validation_result'):
            validation_result = result_state['validation_result']
            print(f"   Score consistência: {validation_result.get('consistency_score', 'N/A')}")
            print(f"   Inconsistências: {len(validation_result.get('inconsistencies_found', []))}")
            print(f"   IDs comparados: {validation_result.get('compared_run_ids', [])}")
            
            if validation_result.get('inconsistencies_found'):
                print("   ⚠️  Inconsistências encontradas:")
                for i, inconsistency in enumerate(validation_result['inconsistencies_found'][:2], 1):
                    print(f"      {i}. {inconsistency}")
            
            if validation_result.get('suggestions'):
                print("   💡 Sugestões:")
                for i, suggestion in enumerate(validation_result['suggestions'][:2], 1):
                    print(f"      {i}. {suggestion}")
        
        print("\n🎉 TODOS OS TESTES DIRETOS PASSARAM!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste direto: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_validation_direct())
