#!/usr/bin/env python3
"""
Script específico para testar endpoints de runs com logs detalhados

Foca especificamente no fluxo de execução de agentes e consulta de resultados.
Mostra logs detalhados tanto do cliente quanto do servidor.

Uso: python test_runs_detailed.py [BASE_URL]
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional

class RunsTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
        
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp e cores"""
        timestamp = time.strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[36m",    # Cyan
            "SUCCESS": "\033[32m", # Green
            "ERROR": "\033[31m",   # Red
            "WARN": "\033[33m",    # Yellow
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Faz requisição com logs detalhados"""
        url = f"{self.base_url}{endpoint}"
        
        if self.token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.token:
            kwargs['headers']['Authorization'] = f"Bearer {self.token}"
            
        self.log(f"🌐 {method.upper()} {endpoint}")
        if 'json' in kwargs:
            self.log(f"📤 Payload: {json.dumps(kwargs['json'], indent=2)}")
        
        start_time = time.time()
        response = self.session.request(method, url, **kwargs)
        duration = time.time() - start_time
        
        if response.status_code < 400:
            self.log(f"✅ {response.status_code} - Sucesso ({duration:.2f}s)", "SUCCESS")
            try:
                data = response.json()
                self.log(f"📥 Response: {json.dumps(data, indent=2, default=str)}")
            except:
                self.log(f"📥 Response: {response.text}")
        else:
            self.log(f"❌ {response.status_code} - Erro ({duration:.2f}s): {response.text}", "ERROR")
            
        return response
    
    def setup_test_environment(self) -> Dict[str, Any]:
        """Configura ambiente de teste (usuário, dataset, conexão, agente)"""
        self.log("🔧 CONFIGURANDO AMBIENTE DE TESTE", "INFO")
        
        # 1. Registro
        user_data = {
            "nome": "Teste Runs",
            "email": f"teste_runs_{int(time.time())}@example.com",
            "password": "senha123"
        }
        
        response = self.make_request("POST", "/auth/register", json=user_data)
        if response.status_code != 200:
            raise Exception("Falha no registro")
        
        # 2. Login
        login_data = {
            "username": user_data['email'],
            "password": "senha123"
        }
        
        response = self.make_request(
            "POST", 
            "/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception("Falha no login")
            
        self.token = response.json()['access_token']
        self.log(f"🔑 Token obtido: {self.token[:20]}...", "SUCCESS")
        
        # 3. Upload dataset - usar arquivo clinicas.csv existente
        csv_file_path = "clinicas.csv"

        # Verificar se arquivo existe
        if not os.path.exists(csv_file_path):
            raise Exception(f"Arquivo {csv_file_path} não encontrado na raiz do projeto")

        with open(csv_file_path, 'rb') as f:
            files = {
                'file': ('clinicas.csv', f, 'text/csv')
            }
            data = {
                'nome': 'Clínicas para Teste de Runs'
            }
            response = self.make_request("POST", "/datasets/upload", files=files, data=data)
        if response.status_code != 200:
            raise Exception("Falha no upload")
            
        dataset_id = response.json()['id']
        
        # 4. Criar conexão
        connection_data = {
            "tipo": "sqlite",
            "dataset_id": dataset_id
        }
        
        response = self.make_request("POST", "/connections/", json=connection_data)
        if response.status_code != 200:
            raise Exception("Falha na criação da conexão")
            
        connection_id = response.json()['id']
        
        # 5. Criar agente
        agent_data = {
            "nome": "Agente Teste Runs",
            "connection_id": connection_id,
            "selected_model": "gpt-3.5-turbo",
            "top_k": 10,
            "include_tables_key": "*",
            "advanced_mode": False,
            "processing_enabled": True,
            "refinement_enabled": False,
            "single_table_mode": False
        }
        
        response = self.make_request("POST", "/agents/", json=agent_data)
        if response.status_code != 200:
            raise Exception("Falha na criação do agente")
            
        agent_id = response.json()['id']
        
        self.log("✅ AMBIENTE CONFIGURADO COM SUCESSO", "SUCCESS")
        return {
            "agent_id": agent_id,
            "connection_id": connection_id,
            "dataset_id": dataset_id
        }
    
    def test_run_execution(self, agent_id: int) -> int:
        """Testa execução de agente com pergunta complexa"""
        self.log("🚀 TESTANDO EXECUÇÃO DE AGENTE", "INFO")
        
        questions = [
            "Quantos estabelecimentos únicos existem na base?",
            "Qual é a taxa média de falta geral em 2023?",
            "Quais são os 5 horários com mais agendamentos confirmados?",
            "Qual estabelecimento tem a maior taxa de falta?",
            "Quantos agendamentos foram feitos por especialidade?"
        ]
        
        # Escolher uma pergunta aleatória
        import random
        question = random.choice(questions)
        
        run_data = {
            "question": question
        }
        
        self.log(f"❓ Pergunta selecionada: '{question}'")
        
        response = self.make_request(f"POST", f"/agents/{agent_id}/run", json=run_data)
        
        if response.status_code != 200:
            raise Exception("Falha na execução do agente")
            
        run = response.json()
        run_id = run['id']
        
        self.log(f"✅ Execução iniciada: Run ID {run_id}", "SUCCESS")
        return run_id
    
    def test_run_polling(self, run_id: int, max_attempts: int = 60) -> bool:
        """Testa polling de resultado com logs detalhados"""
        self.log(f"⏳ INICIANDO POLLING - Run ID: {run_id}", "INFO")
        
        for attempt in range(1, max_attempts + 1):
            self.log(f"🔄 Tentativa {attempt}/{max_attempts}")
            
            response = self.make_request("GET", f"/runs/{run_id}")
            
            if response.status_code != 200:
                self.log("❌ Erro ao consultar run", "ERROR")
                return False
                
            run = response.json()
            status = run['status']
            
            self.log(f"📊 Status atual: {status}")
            
            if status == 'success':
                self.log("🎉 EXECUÇÃO CONCLUÍDA COM SUCESSO!", "SUCCESS")
                
                if run.get('result_data'):
                    self.log(f"💬 Resposta do agente:")
                    print("=" * 60)
                    print(run['result_data'])
                    print("=" * 60)
                else:
                    self.log("⚠️ Resposta vazia", "WARN")
                
                if run.get('sql_used'):
                    self.log(f"🗃️ SQL executado: {run['sql_used']}")
                
                if run.get('execution_ms'):
                    self.log(f"⏱️ Tempo de execução: {run['execution_ms']}ms")
                
                if run.get('result_rows_count'):
                    self.log(f"📊 Linhas retornadas: {run['result_rows_count']}")
                
                return True
                
            elif status == 'failure':
                self.log("❌ EXECUÇÃO FALHOU!", "ERROR")
                if run.get('error_type'):
                    self.log(f"🐛 Tipo de erro: {run['error_type']}", "ERROR")
                return False
                
            elif status in ['queued', 'running']:
                self.log(f"⏳ Aguardando... ({status})")
                time.sleep(2)
                
            else:
                self.log(f"❓ Status desconhecido: {status}", "WARN")
                time.sleep(2)
        
        self.log("⏰ TIMEOUT: Execução não finalizou no tempo esperado", "ERROR")
        return False
    
    def test_list_runs(self, agent_id: int):
        """Testa listagem de runs"""
        self.log("📋 TESTANDO LISTAGEM DE RUNS", "INFO")
        
        # Listar runs do agente
        response = self.make_request("GET", f"/agents/{agent_id}/runs")
        if response.status_code == 200:
            runs = response.json()
            self.log(f"✅ Runs do agente: {len(runs)} encontradas", "SUCCESS")
        
        # Listar todas as runs do usuário
        response = self.make_request("GET", "/runs/")
        if response.status_code == 200:
            runs = response.json()
            self.log(f"✅ Todas as runs: {len(runs)} encontradas", "SUCCESS")
    
    def run_complete_test(self):
        """Executa teste completo de runs"""
        try:
            self.log("🧪 INICIANDO TESTE COMPLETO DE RUNS", "INFO")
            
            # 1. Configurar ambiente
            env = self.setup_test_environment()
            agent_id = env['agent_id']
            
            # 2. Executar agente
            run_id = self.test_run_execution(agent_id)
            
            # 3. Polling de resultado
            success = self.test_run_polling(run_id)
            
            # 4. Testar listagens
            self.test_list_runs(agent_id)
            
            if success:
                self.log("🎉 TESTE COMPLETO CONCLUÍDO COM SUCESSO!", "SUCCESS")
                return True
            else:
                self.log("❌ TESTE FALHOU", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"💥 Erro inesperado: {str(e)}", "ERROR")
            return False

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 80)
    print("🧪 TESTE DETALHADO DE RUNS - AGENTAPI")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print("Este teste foca especificamente no fluxo de execução de agentes")
    print("e mostra logs detalhados tanto do cliente quanto do servidor.")
    print("=" * 80)
    print()
    
    tester = RunsTester(base_url)
    success = tester.run_complete_test()
    
    print()
    print("=" * 80)
    if success:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("O sistema de runs está funcionando corretamente.")
    else:
        print("❌ TESTE FALHOU!")
        print("Verifique os logs acima e os logs do servidor.")
    print("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
