#!/usr/bin/env python3
"""
Teste simples para verificar se o histórico está funcionando
"""

import requests
import time
import json

def test_simple():
    print("🧪 Teste simples do histórico...")
    
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
    
    # Enviar pergunta (nova sessão será criada)
    print("📝 Enviando pergunta (nova sessão)...")
    result = requests.post('http://localhost:8000/agents/1/run',
        headers=headers,
        json={
            'question': 'Quantos produtos temos?'
        }
    )
    
    if result.status_code != 200:
        print(f"❌ Erro ao enviar pergunta: {result.status_code}")
        print(result.text)
        return
    
    run_id = result.json()['id']
    print(f"✅ Run criada: {run_id}")
    
    # Aguardar conclusão
    print("⏳ Aguardando conclusão...")
    for i in range(20):  # 20 tentativas de 3 segundos = 60 segundos
        time.sleep(3)
        status_response = requests.get(f'http://localhost:8000/runs/{run_id}', headers=headers)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get('status', 'unknown')
            print(f"🔄 Status: {status}")
            
            if status in ['success', 'failure']:
                print(f"✅ Concluído com status: {status}")
                result_data = status_data.get('result_data', '')
                print(f"📊 Resultado: {result_data[:200]}...")
                return
        else:
            print(f"❌ Erro ao consultar status: {status_response.status_code}")
    
    print("⏰ Timeout - teste não concluído")

if __name__ == "__main__":
    test_simple()
