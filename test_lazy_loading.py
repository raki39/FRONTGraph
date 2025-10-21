#!/usr/bin/env python3
"""
Script para testar o lazy loading no chat
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

def create_test_runs(token, agent_id, count=25):
    """Cria runs de teste para testar lazy loading"""
    console.print(f"\n📝 === CRIANDO {count} RUNS DE TESTE ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    created = 0
    
    for i in range(count):
        try:
            response = requests.post(
                f"{BASE_URL}/agents/{agent_id}/run",
                json={"question": f"Pergunta de teste {i+1} para lazy loading"},
                headers=headers
            )
            
            if response.status_code == 200:
                created += 1
                if (i + 1) % 5 == 0:
                    console.print(f"✅ Criadas {i+1} runs...")
            else:
                console.print(f"❌ Falha ao criar run {i+1}: {response.status_code}")
                
        except Exception as e:
            console.print(f"❌ Erro ao criar run {i+1}: {e}")
    
    console.print(f"🎉 Total de runs criadas: {created}/{count}")
    return created

def test_lazy_loading_behavior(token, agent_id):
    """Testa o comportamento do lazy loading"""
    console.print(f"\n🔄 === TESTANDO LAZY LOADING ===", style="cyan bold")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Teste 1: Primeira página (deve carregar 20 itens)
    console.print("1️⃣ Testando primeira página (20 itens)...")
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=20", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        console.print(f"✅ Primeira página:")
        console.print(f"   - Runs carregadas: {len(data['runs'])}")
        console.print(f"   - Total no sistema: {data['pagination']['total_items']}")
        console.print(f"   - Total de páginas: {data['pagination']['total_pages']}")
        console.print(f"   - Tem próxima: {data['pagination']['has_next']}")
        
        # Teste 2: Segunda página (lazy loading)
        if data['pagination']['has_next']:
            console.print("\n2️⃣ Testando segunda página (lazy loading)...")
            response2 = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=2&per_page=20", headers=headers)
            
            if response2.status_code == 200:
                data2 = response2.json()
                console.print(f"✅ Segunda página:")
                console.print(f"   - Runs carregadas: {len(data2['runs'])}")
                console.print(f"   - Tem próxima: {data2['pagination']['has_next']}")
                
                # Verificar se as runs são diferentes
                page1_ids = set(run['id'] for run in data['runs'])
                page2_ids = set(run['id'] for run in data2['runs'])
                overlap = page1_ids.intersection(page2_ids)
                
                if len(overlap) == 0:
                    console.print("✅ Páginas contêm runs diferentes (correto)")
                else:
                    console.print(f"⚠️ Sobreposição de {len(overlap)} runs entre páginas")
                
                return True
            else:
                console.print(f"❌ Falha na segunda página: {response2.status_code}")
                return False
        else:
            console.print("ℹ️ Não há segunda página para testar")
            return True
    else:
        console.print(f"❌ Falha na primeira página: {response.status_code}")
        return False

def test_pagination_limits(token, agent_id):
    """Testa os limites da paginação"""
    console.print(f"\n📊 === TESTANDO LIMITES DE PAGINAÇÃO ===", style="cyan bold")

    headers = {"Authorization": f"Bearer {token}"}

    # Testar com diferentes tamanhos de página
    page_sizes = [1, 5, 10, 20, 50]
    all_passed = True

    for size in page_sizes:
        console.print(f"📄 Testando per_page={size}...")
        response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page={size}", headers=headers)

        if response.status_code == 200:
            data = response.json()
            actual_size = len(data['runs'])
            expected_size = min(size, data['pagination']['total_items'])

            if actual_size == expected_size:
                console.print(f"   ✅ Retornou {actual_size} runs (correto)")
            else:
                console.print(f"   ❌ Esperado {expected_size}, recebido {actual_size}")
                all_passed = False
        else:
            console.print(f"   ❌ Falha: {response.status_code}")
            all_passed = False

    return all_passed

def main():
    """Função principal"""
    console.print(Panel.fit("🧪 === TESTE DE LAZY LOADING NO CHAT ===", style="bold blue"))
    
    # Login
    token = login_admin()
    if not token:
        return
    
    agent_id = 1  # ID do agente de teste
    
    # Verificar quantas runs já existem
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/runs?page=1&per_page=1", headers=headers)
    
    if response.status_code == 200:
        current_total = response.json()['pagination']['total_items']
        console.print(f"📊 Runs atuais no agente {agent_id}: {current_total}")
        
        # Se temos poucas runs, criar mais para testar lazy loading
        if current_total < 25:
            needed = 25 - current_total
            console.print(f"🔧 Criando {needed} runs adicionais para teste...")
            create_test_runs(token, agent_id, needed)
    
    # Executar testes
    tests = [
        ("Comportamento Lazy Loading", lambda: test_lazy_loading_behavior(token, agent_id)),
        ("Limites de Paginação", lambda: test_pagination_limits(token, agent_id)),
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
        console.print("🎉 Lazy loading está funcionando corretamente!", style="green bold")
        console.print("\n💡 Agora teste no frontend:", style="blue")
        console.print("1. Acesse http://localhost:3000/chat?agent=1")
        console.print("2. Verifique se carrega apenas 20 mensagens inicialmente")
        console.print("3. Clique em 'Carregar mais' para testar lazy loading")
    else:
        console.print("❌ Alguns testes falharam", style="red bold")

if __name__ == "__main__":
    main()
