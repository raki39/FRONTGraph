#!/usr/bin/env python3
"""
Teste rápido do histórico - 2 perguntas na mesma sessão
"""

import requests
import time

def test_history():
    print("🧪 Teste rápido do histórico...")
    
    # Login
    response = requests.post('http://localhost:8000/auth/login', data={
        'username': 'admin@example.com', 
        'password': 'admin'
    })
    
    if response.status_code != 200:
        print(f"❌ Erro no login: {response.status_code}")
        return
    
    token = response.json()['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # PERGUNTA 1: Primeira pergunta (sem histórico)
    print("📝 PERGUNTA 1: Quantos produtos temos?")
    result1 = requests.post('http://localhost:8000/agents/1/run',
        headers=headers,
        json={'question': 'Quantos produtos temos?'}
    )
    
    if result1.status_code != 200:
        print(f"❌ Erro na pergunta 1: {result1.status_code}")
        return
    
    run1_data = result1.json()
    run1_id = run1_data['id']
    chat_session_id = run1_data.get('chat_session_id')
    
    print(f"🚀 Run 1: {run1_id}, Sessão: {chat_session_id}")
    
    # Aguarda conclusão
    for i in range(30):
        time.sleep(2)
        status = requests.get(f'http://localhost:8000/runs/{run1_id}', headers=headers)
        if status.status_code == 200 and status.json()['status'] == 'success':
            print("✅ Pergunta 1 concluída")
            break
    
    # Aguarda embeddings
    print("⏳ Aguardando embeddings...")
    time.sleep(5)
    
    # PERGUNTA 2: Segunda pergunta (DEVERIA usar histórico)
    print("📝 PERGUNTA 2: Me lembre novamente quantos produtos temos?")
    result2 = requests.post('http://localhost:8000/agents/1/run',
        headers=headers,
        json={
            'question': 'Me lembre novamente quantos produtos temos?',
            'chat_session_id': chat_session_id
        }
    )
    
    if result2.status_code != 200:
        print(f"❌ Erro na pergunta 2: {result2.status_code}")
        return
    
    run2_data = result2.json()
    run2_id = run2_data['id']
    
    print(f"🚀 Run 2: {run2_id}, Sessão: {chat_session_id}")
    
    # Aguarda conclusão
    for i in range(30):
        time.sleep(2)
        status = requests.get(f'http://localhost:8000/runs/{run2_id}', headers=headers)
        if status.status_code == 200 and status.json()['status'] == 'success':
            print("✅ Pergunta 2 concluída")
            break
    
    print(f"🎯 TESTE CONCLUÍDO - Sessão: {chat_session_id}, Runs: {run1_id}, {run2_id}")
    print("📋 Verificar logs do worker para ver se histórico foi usado!")

if __name__ == "__main__":
    test_history()
