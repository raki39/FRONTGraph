#!/usr/bin/env python3
"""
Script de teste para verificar se o frontend está funcionando corretamente
com a nova implementação de paginação
"""

import requests
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Configurações
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
ADMIN_EMAIL = "tiraramos@hotmail.com"
ADMIN_PASSWORD = "tiago111"

def login_admin():
    """Faz login como administrador"""
    console.print("🔐 Fazendo login como administrador...", style="blue")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        console.print("✅ Login admin realizado com sucesso", style="green")
        return token
    else:
        console.print(f"❌ Falha no login: {response.status_code}", style="red")
        console.print(response.text)
        return None

def test_api_pagination_structure(token):
    """Testa se a API está retornando a estrutura de paginação correta"""
    console.print("\n📋 === TESTE: Estrutura de Paginação da API ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Teste endpoint /runs/
    console.print("1️⃣ Testando estrutura /runs/...")
    response = requests.get(f"{BASE_URL}/runs/?page=1&per_page=5", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Verificar estrutura esperada
        required_keys = ['runs', 'pagination']
        pagination_keys = ['page', 'per_page', 'total_items', 'total_pages', 'has_next', 'has_prev']
        
        if all(key in data for key in required_keys):
            console.print("✅ Estrutura principal correta", style="green")
            
            if all(key in data['pagination'] for key in pagination_keys):
                console.print("✅ Estrutura de paginação correta", style="green")
                console.print(f"   - Runs: {len(data['runs'])}")
                console.print(f"   - Total: {data['pagination']['total_items']}")
                console.print(f"   - Páginas: {data['pagination']['total_pages']}")
                return True
            else:
                console.print("❌ Estrutura de paginação incorreta", style="red")
                console.print(f"   Esperado: {pagination_keys}")
                console.print(f"   Recebido: {list(data['pagination'].keys())}")
                return False
        else:
            console.print("❌ Estrutura principal incorreta", style="red")
            console.print(f"   Esperado: {required_keys}")
            console.print(f"   Recebido: {list(data.keys())}")
            return False
    else:
        console.print(f"❌ Falha na API: {response.status_code}", style="red")
        return False

def test_agent_runs_pagination(token):
    """Testa paginação de runs por agente"""
    console.print("\n🤖 === TESTE: Paginação Runs por Agente ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Obter agentes
    response = requests.get(f"{BASE_URL}/agents/", headers=headers)
    if response.status_code != 200:
        console.print("❌ Falha ao obter agentes", style="red")
        return False
    
    agents = response.json()
    if not agents:
        console.print("⚠️ Nenhum agente encontrado", style="yellow")
        return True
    
    agent_id = agents[0]["id"]
    console.print(f"📌 Testando com agente ID: {agent_id}")
    
    # Testar paginação
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=3", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print("✅ Paginação de runs por agente funcionando", style="green")
        console.print(f"   - Runs: {len(data['runs'])}")
        console.print(f"   - Total: {data['pagination']['total_items']}")
        return True
    else:
        console.print(f"❌ Falha: {response.status_code}", style="red")
        return False

def check_frontend_running():
    """Verifica se o frontend está rodando"""
    console.print("\n🌐 === TESTE: Frontend Rodando ===", style="cyan bold")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            console.print("✅ Frontend está rodando", style="green")
            return True
        else:
            console.print(f"⚠️ Frontend respondeu com status: {response.status_code}", style="yellow")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"❌ Frontend não está rodando: {e}", style="red")
        console.print("💡 Execute: cd frontend && npm run dev", style="blue")
        return False

def test_api_compatibility():
    """Testa compatibilidade da API com o frontend"""
    console.print("\n🔗 === TESTE: Compatibilidade API-Frontend ===", style="cyan bold")
    
    # Simular chamadas que o frontend faria
    test_cases = [
        {
            "name": "Dashboard - Estatísticas",
            "url": f"{BASE_URL}/runs/?page=1&per_page=5",
            "description": "Primeira página com 5 itens para dashboard"
        },
        {
            "name": "Chat - Todas as mensagens",
            "url": f"{BASE_URL}/runs/?page=1&per_page=100",
            "description": "Muitas mensagens para chat completo"
        }
    ]
    
    token = login_admin()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    all_passed = True
    
    for test_case in test_cases:
        console.print(f"🧪 {test_case['name']}...")
        response = requests.get(test_case['url'], headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'runs' in data and 'pagination' in data:
                console.print(f"   ✅ {test_case['description']}", style="green")
            else:
                console.print(f"   ❌ Estrutura incorreta", style="red")
                all_passed = False
        else:
            console.print(f"   ❌ Falha: {response.status_code}", style="red")
            all_passed = False
    
    return all_passed

def main():
    """Função principal"""
    console.print(Panel.fit("🧪 === TESTE DE INTEGRAÇÃO FRONTEND-PAGINAÇÃO ===", style="bold blue"))
    
    # Executar testes
    tests = [
        ("Frontend Rodando", check_frontend_running),
        ("Estrutura API", lambda: test_api_pagination_structure(login_admin())),
        ("Paginação por Agente", lambda: test_agent_runs_pagination(login_admin())),
        ("Compatibilidade API-Frontend", test_api_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            console.print(f"\n🔍 Executando: {test_name}")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ Erro no teste {test_name}: {e}", style="red")
            results.append((test_name, False))
    
    # Resultado final
    console.print("\n🎯 === RESULTADO FINAL ===", style="bold")
    
    table = Table(title="Resultados dos Testes de Integração")
    table.add_column("Teste", style="cyan")
    table.add_column("Status", style="bold")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        table.add_row(test_name, status)
        if result:
            passed += 1
    
    console.print(table)
    console.print(f"\n✅ Testes bem-sucedidos: {passed}/{len(results)}")
    
    if passed == len(results):
        console.print("🎉 Todos os testes passaram! Frontend pronto para uso.", style="green bold")
        console.print("\n📋 Próximos passos:", style="blue")
        console.print("1. Acesse http://localhost:3000")
        console.print("2. Faça login")
        console.print("3. Teste o dashboard e chat")
        console.print("4. Verifique se as mensagens carregam corretamente")
    else:
        console.print("❌ Alguns testes falharam", style="red bold")
        console.print("\n🔧 Verifique:", style="yellow")
        console.print("1. Se a API está rodando (http://localhost:8000)")
        console.print("2. Se o frontend está rodando (http://localhost:3000)")
        console.print("3. Se há dados de teste no banco")

if __name__ == "__main__":
    main()
