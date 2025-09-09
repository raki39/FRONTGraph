#!/usr/bin/env python3
"""
Script de inicialização do Sistema de Testes Massivos - AgentGraph
Execute este arquivo na raiz do projeto para ter acesso a todos os módulos
"""
import os
import sys
import subprocess
import logging

def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    try:
        import flask
        import pandas
        import openpyxl
        print("✅ Dependências Flask/Pandas verificadas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("💡 Execute: pip install flask pandas openpyxl")
        return False

def check_agentgraph_setup():
    """Verifica se o AgentGraph está configurado"""
    try:
        from utils.config import AVAILABLE_MODELS, validate_config
        validate_config()
        print("✅ AgentGraph configurado corretamente")
        print(f"📊 {len(AVAILABLE_MODELS)} modelos disponíveis")
        return True
    except Exception as e:
        print(f"❌ Erro na configuração do AgentGraph: {e}")
        print("💡 Verifique se as APIs estão configuradas no .env")
        return False

def check_cache_disabled():
    """Verifica se o cache foi desativado conforme solicitado"""
    try:
        from nodes.agent_node import route_after_cache_check
        
        # Testa se o cache está desativado
        test_state = {"cache_hit": True, "processing_enabled": False}
        result = route_after_cache_check(test_state)
        
        if result != "update_history":  # Se não vai para cache, está desativado
            print("✅ Cache desativado conforme solicitado")
            return True
        else:
            print("⚠️ Cache ainda ativo - pode afetar testes de consistência")
            return True  # Não é erro fatal
    except Exception as e:
        print(f"⚠️ Erro ao verificar cache: {e}")
        return True  # Não é erro fatal

def check_test_modules():
    """Verifica se os módulos de teste estão funcionando"""
    try:
        from testes.test_runner import MassiveTestRunner
        from testes.test_validator import TestValidator
        from testes.report_generator import ReportGenerator
        
        print("✅ Módulos de teste carregados com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro nos módulos de teste: {e}")
        return False

def main():
    """Função principal"""
    print("🧪 Sistema de Testes Massivos - AgentGraph")
    print("=" * 60)
    print("📍 Executando da raiz do projeto para acesso completo aos módulos")
    print("=" * 60)
    
    # Verificações pré-execução
    checks = [
        ("Dependências", check_dependencies),
        ("Configuração AgentGraph", check_agentgraph_setup),
        ("Status do Cache", check_cache_disabled),
        ("Módulos de Teste", check_test_modules)
    ]
    
    print("\n🔍 Verificações pré-execução:")
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_passed = False
    
    if not all_passed:
        print("\n❌ Algumas verificações falharam")
        print("🔧 Corrija os problemas acima antes de continuar")
        return False
    
    print("\n" + "=" * 60)
    print("🚀 Todas as verificações passaram!")
    print("🌐 Iniciando servidor de testes...")
    print("📊 Interface disponível em: http://localhost:5001")
    print("🔄 Pressione Ctrl+C para parar")
    print("=" * 60)
    
    # Inicia o servidor
    try:
        from testes.app_teste import app

        # Configura logging para Flask
        import logging
        logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduz logs do Flask

        app.run(
            host='0.0.0.0',
            port=5001,
            debug=True,  # Habilita debug para ver logs
            threaded=True,
            use_reloader=False  # Evita restart duplo
        )
    except KeyboardInterrupt:
        print("\n👋 Sistema de testes encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        print("💡 Verifique se a porta 5001 está disponível")
        return False
    
    return True

if __name__ == '__main__':
    print("🎯 SISTEMA DE TESTES MASSIVOS PARA AGENTGRAPH")
    print("=" * 60)
    print("📝 FUNCIONALIDADES:")
    print("• Testes paralelos com até 8 workers simultâneos")
    print("• Comparação de modelos SQL (GPT, Claude, Gemini)")
    print("• Teste com/sem Processing Agent")
    print("• Validação automática por LLM ou palavra-chave")
    print("• Relatórios detalhados em Excel/CSV")
    print("• Interface HTML intuitiva")
    print("• Métricas de consistência e performance")
    print("=" * 60)
    
    success = main()
    
    if success:
        print("\n🎉 Sistema executado com sucesso!")
    else:
        print("\n❌ Erro na execução do sistema")
        print("💡 Verifique os logs acima para detalhes")
    
    sys.exit(0 if success else 1)
