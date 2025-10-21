#!/usr/bin/env python3
"""
Script de debug para testar especificamente o problema do chat
"""

import requests
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

# Configurações
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "tiraramos@hotmail.com"
ADMIN_PASSWORD = "tiago111"

def login_admin():
    """Faz login como administrador"""
    console.print("🔐 Fazendo login...", style="blue")
    
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
        console.print("✅ Login realizado com sucesso", style="green")
        return token
    else:
        console.print(f"❌ Falha no login: {response.status_code}", style="red")
        return None

def test_agent_endpoint(token):
    """Testa o endpoint do agente específico"""
    console.print("\n🤖 === TESTE: Endpoint do Agente ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    agent_id = 1
    
    # Testar endpoint do agente
    console.print(f"📞 Testando GET /agents/{agent_id}")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}", headers=headers)
    
    if response.status_code == 200:
        agent = response.json()
        console.print("✅ Agente carregado:", style="green")
        console.print(f"   - ID: {agent['id']}")
        console.print(f"   - Nome: {agent['nome']}")
        console.print(f"   - Modelo: {agent['selected_model']}")
        return True
    else:
        console.print(f"❌ Falha: {response.status_code}", style="red")
        console.print(response.text)
        return False

def test_runs_endpoint(token):
    """Testa o endpoint de runs do agente"""
    console.print("\n📋 === TESTE: Endpoint de Runs ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    agent_id = 1
    
    # Testar primeira página
    console.print(f"📞 Testando GET /agents/{agent_id}/runs?page=1&per_page=100")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=100", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print("✅ Runs carregadas:", style="green")
        console.print(f"   - Runs na página: {len(data['runs'])}")
        console.print(f"   - Total de itens: {data['pagination']['total_items']}")
        console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
        console.print(f"   - Tem próxima: {data['pagination']['has_next']}")
        
        # Mostrar algumas runs
        if data['runs']:
            console.print("\n📝 Primeiras runs:")
            for i, run in enumerate(data['runs'][:3]):
                console.print(f"   {i+1}. ID: {run['id']}, Status: {run['status']}, Pergunta: {run['question'][:50]}...")
        
        return data
    else:
        console.print(f"❌ Falha: {response.status_code}", style="red")
        console.print(response.text)
        return None

def test_multiple_pages(token):
    """Testa múltiplas páginas se existirem"""
    console.print("\n📄 === TESTE: Múltiplas Páginas ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    agent_id = 1
    
    # Testar com páginas pequenas para forçar paginação
    console.print(f"📞 Testando com per_page=1 para forçar paginação")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=1", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print("✅ Primeira página (per_page=1):", style="green")
        console.print(f"   - Runs na página: {len(data['runs'])}")
        console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
        console.print(f"   - Tem próxima: {data['pagination']['has_next']}")
        
        # Se tem próxima página, testar
        if data['pagination']['has_next']:
            console.print(f"📞 Testando página 2")
            response2 = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=2&per_page=1", headers=headers)
            if response2.status_code == 200:
                data2 = response2.json()
                console.print("✅ Segunda página carregada:", style="green")
                console.print(f"   - Runs na página: {len(data2['runs'])}")
            else:
                console.print(f"❌ Falha na página 2: {response2.status_code}", style="red")
        
        return True
    else:
        console.print(f"❌ Falha: {response.status_code}", style="red")
        return False

def main():
    """Função principal"""
    console.print(Panel.fit("🔍 === DEBUG DO CHAT - TESTE DE ENDPOINTS ===", style="bold blue"))
    
    # Login
    token = login_admin()
    if not token:
        return
    
    # Executar testes
    tests = [
        ("Endpoint do Agente", lambda: test_agent_endpoint(token)),
        ("Endpoint de Runs", lambda: test_runs_endpoint(token)),
        ("Múltiplas Páginas", lambda: test_multiple_pages(token)),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            console.print(f"\n🔍 Executando: {test_name}")
            result = test_func()
            results.append((test_name, bool(result)))
        except Exception as e:
            console.print(f"❌ Erro no teste {test_name}: {e}", style="red")
            results.append((test_name, False))
    
    # Resultado final
    console.print("\n🎯 === RESULTADO ===", style="bold")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        console.print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    console.print(f"\n✅ Testes bem-sucedidos: {passed}/{len(results)}")
    
    if passed == len(results):
        console.print("🎉 Todos os endpoints estão funcionando!", style="green bold")
        console.print("\n💡 Se o frontend ainda não carrega:", style="blue")
        console.print("1. Verifique o console do navegador (F12)")
        console.print("2. Verifique se há erros de CORS")
        console.print("3. Verifique se o frontend está rodando na porta 3000")
    else:
        console.print("❌ Alguns endpoints falharam", style="red bold")

if __name__ == "__main__":
    main()
