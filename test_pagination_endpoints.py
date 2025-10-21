#!/usr/bin/env python3
"""
Script de teste para verificar a paginação dos endpoints de RUNS
"""

import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

console = Console()

# Configurações
BASE_URL = "http://localhost:8000"
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

def test_user_runs_pagination(token):
    """Testa paginação do endpoint /runs/"""
    console.print("\n📋 === TESTE: Paginação /runs/ ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Teste 1: Primeira página
    console.print("1️⃣ Testando primeira página (page=1, per_page=5)...")
    response = requests.get(f"{BASE_URL}/runs/?page=1&per_page=5", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print(f"✅ Primeira página obtida:")
        console.print(f"   - Runs na página: {len(data['runs'])}")
        console.print(f"   - Total de itens: {data['pagination']['total_items']}")
        console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
        console.print(f"   - Tem próxima: {data['pagination']['has_next']}")
        console.print(f"   - Tem anterior: {data['pagination']['has_prev']}")
        
        # Teste 2: Segunda página se existir
        if data['pagination']['has_next']:
            console.print("2️⃣ Testando segunda página...")
            response2 = requests.get(f"{BASE_URL}/runs/?page=2&per_page=5", headers=headers)
            if response2.status_code == 200:
                data2 = response2.json()
                console.print(f"✅ Segunda página obtida: {len(data2['runs'])} runs")
            else:
                console.print(f"❌ Falha na segunda página: {response2.status_code}")
        
        return True
    else:
        console.print(f"❌ Falha ao testar paginação: {response.status_code}")
        return False

def test_agent_runs_pagination(token):
    """Testa paginação do endpoint /agents/{agent_id}/runs"""
    console.print("\n🤖 === TESTE: Paginação /agents/{agent_id}/runs ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Primeiro, obter lista de agentes para pegar um ID
    console.print("🔍 Obtendo lista de agentes...")
    response = requests.get(f"{BASE_URL}/agents/", headers=headers)
    
    if response.status_code == 200:
        agents = response.json()
        if agents:
            agent_id = agents[0]["id"]
            console.print(f"📌 Usando agente ID: {agent_id}")
            
            # Testar paginação das runs do agente
            console.print("1️⃣ Testando paginação das runs do agente...")
            response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=3", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"✅ Runs do agente obtidas:")
                console.print(f"   - Runs na página: {len(data['runs'])}")
                console.print(f"   - Total de itens: {data['pagination']['total_items']}")
                console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
                return True
            else:
                console.print(f"❌ Falha ao obter runs do agente: {response.status_code}")
                return False
        else:
            console.print("⚠️ Nenhum agente encontrado para testar")
            return True
    else:
        console.print(f"❌ Falha ao obter agentes: {response.status_code}")
        return False

def test_admin_runs_pagination(token):
    """Testa paginação do endpoint /admin/runs"""
    console.print("\n🔧 === TESTE: Paginação /admin/runs ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Teste paginação admin
    console.print("1️⃣ Testando paginação admin...")
    response = requests.get(f"{BASE_URL}/admin/runs?page=1&per_page=5", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print(f"✅ Runs admin obtidas:")
        console.print(f"   - Runs na página: {len(data['runs'])}")
        console.print(f"   - Total de itens: {data['pagination']['total_items']}")
        console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
        
        # Teste com filtros
        console.print("2️⃣ Testando com filtro de status...")
        response2 = requests.get(f"{BASE_URL}/admin/runs?page=1&per_page=5&status=success", headers=headers)
        if response2.status_code == 200:
            data2 = response2.json()
            console.print(f"✅ Runs filtradas por status: {len(data2['runs'])} runs")
        
        return True
    else:
        console.print(f"❌ Falha ao testar paginação admin: {response.status_code}")
        return False

def test_admin_agent_runs_pagination(token):
    """Testa paginação do novo endpoint /admin/agents/{agent_id}/runs"""
    console.print("\n🔧🤖 === TESTE: Paginação /admin/agents/{agent_id}/runs ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Obter lista de agentes admin
    console.print("🔍 Obtendo lista de agentes (admin)...")
    response = requests.get(f"{BASE_URL}/admin/agents?page=1&per_page=5", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        # A resposta admin de agentes é paginada, então acessamos data["agents"]
        if "agents" in data and data["agents"]:
            agent_id = data["agents"][0]["id"]
            console.print(f"📌 Usando agente ID: {agent_id}")
            
            # Testar novo endpoint admin
            console.print("1️⃣ Testando novo endpoint admin de runs por agente...")
            response = requests.get(f"{BASE_URL}/admin/agents/{agent_id}/runs?page=1&per_page=3", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"✅ Runs do agente (admin) obtidas:")
                console.print(f"   - Runs na página: {len(data['runs'])}")
                console.print(f"   - Total de itens: {data['pagination']['total_items']}")
                console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
                return True
            else:
                console.print(f"❌ Falha ao obter runs do agente (admin): {response.status_code}")
                console.print(response.text)
                return False
        else:
            console.print("⚠️ Nenhum agente encontrado para testar")
            return True
    else:
        console.print(f"❌ Falha ao obter agentes admin: {response.status_code}")
        return False

def main():
    """Função principal"""
    console.print(Panel.fit("🚀 === TESTE DE PAGINAÇÃO DOS ENDPOINTS DE RUNS ===", style="bold blue"))
    
    # Login
    token = login_admin()
    if not token:
        return
    
    # Executar testes
    tests = [
        ("Paginação /runs/", test_user_runs_pagination),
        ("Paginação /agents/{agent_id}/runs", test_agent_runs_pagination),
        ("Paginação /admin/runs", test_admin_runs_pagination),
        ("Paginação /admin/agents/{agent_id}/runs", test_admin_agent_runs_pagination),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func(token)
            results.append((test_name, result))
        except Exception as e:
            console.print(f"❌ Erro no teste {test_name}: {e}", style="red")
            results.append((test_name, False))
    
    # Resultado final
    console.print("\n🎯 === RESULTADO FINAL ===", style="bold")
    
    table = Table(title="Resultados dos Testes de Paginação")
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
        console.print("🎉 Todos os testes de paginação passaram!", style="green bold")
    else:
        console.print("❌ Alguns testes falharam", style="red bold")

if __name__ == "__main__":
    main()
