#!/usr/bin/env python3
"""
Script de teste do sistema de testes massivos
"""
import sys
import os
import asyncio
import logging

# Adiciona path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Testa se todos os imports funcionam"""
    print("🔍 Testando imports...")
    
    try:
        from testes.test_runner import MassiveTestRunner
        print("  ✅ MassiveTestRunner")
        
        from testes.test_validator import TestValidator
        print("  ✅ TestValidator")
        
        from testes.report_generator import ReportGenerator
        print("  ✅ ReportGenerator")
        
        from utils.config import AVAILABLE_MODELS
        print("  ✅ AVAILABLE_MODELS")
        
        return True
    except Exception as e:
        print(f"  ❌ Erro no import: {e}")
        return False

def test_validator():
    """Testa o sistema de validação"""
    print("\n🔍 Testando validador...")
    
    try:
        from testes.test_validator import TestValidator
        
        validator = TestValidator()
        print("  ✅ Validator inicializado")
        
        # Teste de validação por keyword
        result = validator._validate_with_keyword(
            "A resposta contém 150 usuários no total",
            "150 usuários"
        )
        
        if result['valid'] and result['score'] == 100:
            print("  ✅ Validação por keyword funcionando")
        else:
            print(f"  ❌ Validação por keyword falhou: {result}")
            return False
        
        # Teste de sintaxe SQL
        sql_result = validator.validate_sql_syntax("SELECT * FROM usuarios WHERE idade > 18")
        
        if sql_result['valid']:
            print("  ✅ Validação de sintaxe SQL funcionando")
        else:
            print(f"  ❌ Validação SQL falhou: {sql_result}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Erro no validator: {e}")
        return False

def test_report_generator():
    """Testa o gerador de relatórios"""
    print("\n🔍 Testando gerador de relatórios...")
    
    try:
        from testes.report_generator import ReportGenerator
        
        generator = ReportGenerator()
        print("  ✅ ReportGenerator inicializado")
        
        # Dados de teste
        test_results = {
            'session_info': {
                'id': 'test_session',
                'question': 'Teste de pergunta',
                'validation_method': 'keyword'
            },
            'group_results': [
                {
                    'group_id': 1,
                    'group_config': {
                        'sql_model_name': 'GPT-4o-mini',
                        'processing_enabled': False,
                        'processing_model_name': None
                    },
                    'total_tests': 5,
                    'successful_tests': 4,
                    'valid_responses': 3,
                    'success_rate': 80.0,
                    'validation_rate': 60.0,
                    'response_consistency': 75.0,
                    'sql_consistency': 80.0,
                    'avg_execution_time': 5.2
                }
            ],
            'individual_results': [
                {
                    'group_id': 1,
                    'iteration': 1,
                    'sql_model': 'GPT-4o-mini',
                    'processing_enabled': False,
                    'success': True,
                    'validation': {'valid': True, 'score': 85}
                }
            ],
            'summary': {
                'total_groups': 1,
                'total_tests': 5,
                'overall_success_rate': 80.0,
                'overall_validation_rate': 60.0,
                'best_performing_group': {
                    'group_id': 1,
                    'group_config': {'sql_model_name': 'GPT-4o-mini'},
                    'validation_rate': 60.0
                },
                'most_consistent_group': {
                    'group_id': 1,
                    'group_config': {'sql_model_name': 'GPT-4o-mini'},
                    'response_consistency': 75.0
                }
            }
        }
        
        # Testa criação de DataFrames
        group_df = generator._create_group_summary_dataframe(test_results)
        individual_df = generator._create_individual_results_dataframe(test_results)
        general_df = generator._create_general_summary_dataframe(test_results)
        
        if len(group_df) > 0 and len(individual_df) > 0 and len(general_df) > 0:
            print("  ✅ DataFrames criados com sucesso")
        else:
            print("  ❌ Erro na criação de DataFrames")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Erro no report generator: {e}")
        return False

async def test_runner_basic():
    """Testa funcionalidades básicas do runner"""
    print("\n🔍 Testando runner básico...")
    
    try:
        from testes.test_runner import MassiveTestRunner
        
        runner = MassiveTestRunner(max_workers=2)
        print("  ✅ MassiveTestRunner inicializado")
        
        # Testa cálculo de consistência
        items = ["resposta A", "resposta A", "resposta B", "resposta A"]
        consistency = runner._calculate_consistency(items)
        
        expected = 3/4  # 3 "resposta A" de 4 total
        if abs(consistency - expected) < 0.01:
            print("  ✅ Cálculo de consistência funcionando")
        else:
            print(f"  ❌ Consistência incorreta: esperado {expected}, obtido {consistency}")
            return False
        
        # Testa status
        status = runner.get_status()
        if 'current_status' in status and status['current_status'] == 'idle':
            print("  ✅ Status funcionando")
        else:
            print(f"  ❌ Status incorreto: {status}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Erro no runner: {e}")
        return False

def test_flask_app():
    """Testa se o app Flask pode ser importado"""
    print("\n🔍 Testando Flask app...")
    
    try:
        from testes.app_teste import app
        print("  ✅ Flask app importado")
        
        # Testa se as rotas estão definidas
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/api/models', '/api/create_test_session']
        
        for route in expected_routes:
            if route in routes:
                print(f"  ✅ Rota {route} definida")
            else:
                print(f"  ❌ Rota {route} não encontrada")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ Erro no Flask app: {e}")
        return False

def test_agentgraph_integration():
    """Testa integração com AgentGraph"""
    print("\n🔍 Testando integração com AgentGraph...")
    
    try:
        from utils.config import AVAILABLE_MODELS, validate_config
        
        # Testa se modelos estão disponíveis
        if len(AVAILABLE_MODELS) > 0:
            print(f"  ✅ {len(AVAILABLE_MODELS)} modelos disponíveis")
        else:
            print("  ❌ Nenhum modelo disponível")
            return False
        
        # Testa validação de config (pode falhar se APIs não configuradas)
        try:
            validate_config()
            print("  ✅ Configuração válida")
        except Exception as e:
            print(f"  ⚠️ Configuração incompleta: {e}")
            print("  💡 Configure as APIs no .env para funcionalidade completa")
        
        return True
    except Exception as e:
        print(f"  ❌ Erro na integração: {e}")
        return False

async def main():
    """Função principal de teste"""
    print("🧪 TESTE DO SISTEMA DE TESTES MASSIVOS")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Validator", test_validator),
        ("Report Generator", test_report_generator),
        ("Runner Básico", test_runner_basic),
        ("Flask App", test_flask_app),
        ("Integração AgentGraph", test_agentgraph_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSOU")
            else:
                print(f"❌ {test_name} FALHOU")
        except Exception as e:
            print(f"❌ {test_name} ERRO: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTADO FINAL: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("🚀 Sistema pronto para uso!")
        print("💡 Execute: python testes/run_tests.py")
    else:
        print("⚠️ Alguns testes falharam")
        print("🔧 Verifique os erros acima")
    
    print("=" * 50)
    
    return passed == total

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
