"""
Script para teste manual do sistema de validação
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentgraph.agents.validation_agent import ValidationAgentManager
from agentgraph.nodes.validation_node import query_validation_node, validate_validation_state

async def test_validation_agent():
    """Testa o ValidationAgentManager diretamente"""
    print("🧪 TESTANDO VALIDATION AGENT MANAGER")
    print("=" * 50)

    try:
        # Inicializa agente
        print("📝 Inicializando agente...")
        agent = ValidationAgentManager(model="gpt-4o-mini")
        print(f"✅ Agente inicializado com modelo: {agent.model}")

        # TESTE 1: Validação Individual com pergunta problemática
        print(f"\n🔍 TESTE 1: Validação Individual (Pergunta com Problemas)")
        print("-" * 60)

        question = "Mostre os melhores produtos do último período"
        sql_query = """
        SELECT
            p.nome,
            SUM(v.quantidade) as total,
            SUM(v.valor) as valor
        FROM produtos p
        JOIN vendas v ON p.id = v.produto_id
        WHERE v.data > '2024-01-01'
        GROUP BY p.nome
        ORDER BY total DESC
        LIMIT 10
        """
        response = "Produto A: 1000 unidades, R$ 50.000; Produto B: 800 unidades, R$ 40.000; Produto C: 600 unidades, R$ 30.000"

        print(f"Pergunta: {question}")
        print(f"Query: {sql_query.strip()}")
        print(f"Resposta: {response}")

        result = await agent.validate_individual(
            question=question,
            sql_query=sql_query,
            response=response,
            auto_improve=True
        )

        print("\n✅ Resultado da validação individual:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # TESTE 2: Validação Comparativa com IDs reais
        print(f"\n🔍 TESTE 2: Validação Comparativa (Perguntas Similares com IDs)")
        print("-" * 65)

        current_run = {
            "question": "Qual o faturamento por categoria no último ano?",
            "sql_query": "SELECT categoria, SUM(valor_total) FROM vendas WHERE YEAR(data) = 2024 GROUP BY categoria",
            "response": "Eletrônicos: R$ 2.500.000, Roupas: R$ 1.800.000, Casa: R$ 1.200.000"
        }

        # Runs com IDs reais definidos
        compared_runs = [
            {
                "run_id": 1001,  # ID real definido
                "question": "Faturamento por categoria no último ano",
                "sql_query": "SELECT cat.nome, SUM(v.valor) FROM vendas v JOIN categorias cat ON v.categoria_id = cat.id WHERE v.data >= '2024-01-01' GROUP BY cat.nome",
                "response": "Eletrônicos: R$ 2.480.000, Roupas: R$ 1.820.000, Casa: R$ 1.190.000"
            },
            {
                "run_id": 1002,  # ID real definido
                "question": "Qual o total de vendas por categoria em 2024?",
                "sql_query": "SELECT categoria_nome, SUM(valor_vendas) FROM view_vendas_2024 GROUP BY categoria_nome",
                "response": "Eletrônicos: R$ 2.520.000, Roupas: R$ 1.780.000, Casa: R$ 1.210.000"
            }
        ]

        result = await agent.validate_comparative(current_run, compared_runs)

        print("✅ Resultado da validação comparativa:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return True

    except Exception as e:
        print(f"❌ Erro no teste do agente: {e}")
        return False

async def test_validation_node():
    """Testa o nodo de validação"""
    print("\n🧪 TESTANDO VALIDATION NODE")
    print("=" * 50)

    try:
        # TESTE 1: Validação Individual com pergunta problemática
        print("🔍 TESTE 1: Nodo - Validação Individual (Pergunta Problemática)")
        print("-" * 65)

        state_individual = {
            "validation_request": {
                "validation_type": "individual",
                "auto_improve_question": True
            },
            "run_data": {
                "question": "Quais são os melhores clientes do último período?",
                "sql_used": """
                SELECT
                    cliente_nome,
                    total_compras,
                    valor_gasto
                FROM clientes
                WHERE ativo = 1
                ORDER BY valor_gasto DESC
                """,
                "result_data": "Cliente A: 15 compras, R$ 5.000; Cliente B: 12 compras, R$ 4.500; Cliente C: 10 compras, R$ 3.800"
            },
            "validation_model": "gpt-4o-mini"
        }

        result_state = await query_validation_node(state_individual)

        print(f"✅ Sucesso: {result_state.get('validation_success')}")
        print(f"Erro: {result_state.get('validation_error')}")
        print(f"Tempo: {result_state.get('validation_time'):.2f}s")

        if result_state.get('validation_result'):
            print("Resultado da validação:")
            print(json.dumps(result_state['validation_result'], indent=2, ensure_ascii=False))

        # TESTE 2: Validação Comparativa com IDs reais
        print(f"\n🔍 TESTE 2: Nodo - Validação Comparativa (IDs Reais)")
        print("-" * 55)

        state_comparative = {
            "validation_request": {
                "validation_type": "comparative"
            },
            "run_data": {
                "question": "Vendas por região no último trimestre",
                "sql_used": """
                SELECT
                    regiao,
                    SUM(valor_vendas) as total_vendas,
                    COUNT(*) as num_vendas
                FROM vendas
                WHERE data_venda >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                GROUP BY regiao
                ORDER BY total_vendas DESC
                """,
                "result_data": "Sul: R$ 850.000 (1.200 vendas), Sudeste: R$ 720.000 (980 vendas), Norte: R$ 450.000 (650 vendas)"
            },
            "compared_runs_data": [
                {
                    "run_id": 2001,  # ID real
                    "question": "Vendas regionais do último trimestre",
                    "sql_query": "SELECT r.nome, SUM(v.valor) FROM vendas v JOIN regioes r ON v.regiao_id = r.id WHERE v.data >= '2024-07-01' GROUP BY r.nome",
                    "response": "Sul: R$ 845.000, Sudeste: R$ 725.000, Norte: R$ 455.000"
                },
                {
                    "run_id": 2002,  # ID real
                    "question": "Qual região vendeu mais nos últimos 3 meses?",
                    "sql_query": "SELECT regiao_nome, SUM(valor_total) FROM view_vendas_trimestre GROUP BY regiao_nome ORDER BY SUM(valor_total) DESC",
                    "response": "Sul: R$ 860.000, Sudeste: R$ 715.000, Norte: R$ 440.000"
                }
            ],
            "validation_model": "gpt-4o-mini"
        }

        result_state = await query_validation_node(state_comparative)

        print(f"✅ Sucesso: {result_state.get('validation_success')}")
        print(f"Erro: {result_state.get('validation_error')}")
        print(f"Tempo: {result_state.get('validation_time'):.2f}s")

        if result_state.get('validation_result'):
            print("Resultado da validação:")
            print(json.dumps(result_state['validation_result'], indent=2, ensure_ascii=False))

        return True

    except Exception as e:
        print(f"❌ Erro no teste do nodo: {e}")
        return False

def test_state_validation():
    """Testa validação de state"""
    print("\n🧪 TESTANDO VALIDAÇÃO DE STATE")
    print("=" * 50)

    test_results = []

    # Teste 1: State válido individual
    print("🔍 TESTE 1: State válido (individual)")
    valid_state = {
        "validation_request": {
            "validation_type": "individual"
        },
        "run_data": {
            "question": "Teste",
            "sql_used": "SELECT 1",
            "result_data": "Resultado"
        }
    }

    is_valid = validate_validation_state(valid_state)
    print(f"✅ State individual válido: {is_valid}")
    test_results.append(("State individual válido", is_valid == True))

    # Teste 2: State válido comparativo
    print("\n🔍 TESTE 2: State válido (comparativo)")
    valid_comparative_state = {
        "validation_request": {
            "validation_type": "comparative"
        },
        "run_data": {
            "question": "Teste comparativo",
            "sql_used": "SELECT COUNT(*) FROM tabela",
            "result_data": "Total: 100"
        },
        "compared_runs_data": [
            {
                "run_id": 123,
                "question": "Teste similar",
                "sql_query": "SELECT COUNT(1) FROM tabela",
                "response": "Total: 98"
            }
        ]
    }

    is_valid = validate_validation_state(valid_comparative_state)
    print(f"✅ State comparativo válido: {is_valid}")
    test_results.append(("State comparativo válido", is_valid == True))

    # Teste 3: State inválido (dados ausentes em run_data) - DEVE FALHAR
    print("\n🔍 TESTE 3: State inválido (dados ausentes em run_data) - DEVE FALHAR")
    invalid_state = {
        "validation_request": {
            "validation_type": "individual"
        },
        "run_data": {
            "question": "Teste"
            # sql_used e result_data ausentes
        }
    }

    is_valid = validate_validation_state(invalid_state)
    print(f"✅ Validação funcionou corretamente (rejeitou state inválido): {not is_valid}")
    test_results.append(("Rejeição de state inválido", is_valid == False))

    # Teste 4: State comparativo sem runs de comparação - DEVE FALHAR
    print("\n🔍 TESTE 4: State comparativo sem runs de comparação - DEVE FALHAR")
    comparative_invalid = {
        "validation_request": {
            "validation_type": "comparative"
        },
        "run_data": {
            "question": "Teste",
            "sql_used": "SELECT 1",
            "result_data": "Resultado"
        }
        # compared_runs_data ausente
    }

    is_valid = validate_validation_state(comparative_invalid)
    print(f"✅ Validação funcionou corretamente (rejeitou state sem runs): {not is_valid}")
    test_results.append(("Rejeição de state sem runs", is_valid == False))

    # Teste 5: State comparativo com runs malformados - DEVE FALHAR
    print("\n🔍 TESTE 5: State comparativo com runs malformados - DEVE FALHAR")
    comparative_malformed = {
        "validation_request": {
            "validation_type": "comparative"
        },
        "run_data": {
            "question": "Teste",
            "sql_used": "SELECT 1",
            "result_data": "Resultado"
        },
        "compared_runs_data": [
            {
                "question": "Teste similar"
                # sql_query e response ausentes
            }
        ]
    }

    is_valid = validate_validation_state(comparative_malformed)
    print(f"✅ Validação funcionou corretamente (rejeitou runs malformados): {not is_valid}")
    test_results.append(("Rejeição de runs malformados", is_valid == False))

    # Teste 6: State sem validation_request - DEVE FALHAR
    print("\n🔍 TESTE 6: State sem validation_request - DEVE FALHAR")
    no_request_state = {
        "run_data": {
            "question": "Teste",
            "sql_used": "SELECT 1",
            "result_data": "Resultado"
        }
    }

    is_valid = validate_validation_state(no_request_state)
    print(f"✅ Validação funcionou corretamente (rejeitou state sem request): {not is_valid}")
    test_results.append(("Rejeição de state sem request", is_valid == False))

    # Resumo dos testes de validação
    print(f"\n📊 RESUMO DOS TESTES DE VALIDAÇÃO:")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"  {test_name}: {status}")

    print(f"\nResultado: {passed}/{total} testes de validação passaram")

    return passed == total

async def run_all_tests():
    """Executa todos os testes"""
    print("🚀 INICIANDO TESTES DO SISTEMA DE VALIDAÇÃO")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Teste 1: Validation Agent
    try:
        result = await test_validation_agent()
        results.append(("Validation Agent", result))
    except Exception as e:
        print(f"❌ Erro crítico no teste do agente: {e}")
        results.append(("Validation Agent", False))
    
    # Teste 2: Validation Node
    try:
        result = await test_validation_node()
        results.append(("Validation Node", result))
    except Exception as e:
        print(f"❌ Erro crítico no teste do nodo: {e}")
        results.append(("Validation Node", False))
    
    # Teste 3: State Validation
    try:
        result = test_state_validation()
        results.append(("State Validation", result))
    except Exception as e:
        print(f"❌ Erro crítico no teste de state: {e}")
        results.append(("State Validation", False))
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    print(f"\nResultado geral: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("🎉 TODOS OS TESTES PASSARAM!")
        return True
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        return False

if __name__ == "__main__":
    # Executa os testes
    success = asyncio.run(run_all_tests())
    
    # Exit code baseado no resultado
    sys.exit(0 if success else 1)
