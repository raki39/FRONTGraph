#!/usr/bin/env python3
"""
Teste COMPLETO da AgentAPI

Testa TODOS os endpoints da API de forma sequencial e organizada.
Usa o arquivo clinicas.csv e verifica se tudo está funcionando.

Fluxo completo:
1. 🔐 Autenticação (registro + login)
2. 📊 Datasets (upload + listagem)
3. 🔗 Conexões (criação + listagem)
4. 🤖 Agentes (criação + listagem + detalhes)
5. 🚀 Execuções (run + polling + listagem)
6. 📋 Consultas (runs específicas + todas as runs)

Uso: python test_api_complete.py [BASE_URL]
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional

class CompleteAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
        self.test_data = {}  # Armazenar IDs criados durante os testes
        self.tests_passed = 0
        self.tests_failed = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp e cores"""
        timestamp = time.strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[36m",    # Cyan
            "SUCCESS": "\033[32m", # Green
            "ERROR": "\033[31m",   # Red
            "WARN": "\033[33m",    # Yellow
            "HEADER": "\033[35m",  # Magenta
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Faz requisição com autenticação automática"""
        url = f"{self.base_url}{endpoint}"
        
        if self.token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.token:
            kwargs['headers']['Authorization'] = f"Bearer {self.token}"
            
        self.log(f"🌐 {method.upper()} {endpoint}")
        
        start_time = time.time()
        response = self.session.request(method, url, **kwargs)
        duration = time.time() - start_time
        
        if response.status_code < 400:
            self.log(f"✅ {response.status_code} - Sucesso ({duration:.2f}s)", "SUCCESS")
            self.tests_passed += 1
        else:
            self.log(f"❌ {response.status_code} - Erro ({duration:.2f}s): {response.text}", "ERROR")
            self.tests_failed += 1
            
        return response
    
    def test_health_check(self):
        """Testa se a API está funcionando"""
        self.log("🏥 TESTANDO HEALTH CHECK", "HEADER")
        response = self.make_request("GET", "/healthz")
        return response.status_code == 200
    
    def test_authentication(self):
        """Testa registro e login"""
        self.log("🔐 TESTANDO AUTENTICAÇÃO", "HEADER")
        
        # 1. Registro
        self.log("📝 Testando registro de usuário...")
        user_data = {
            "nome": "Teste Completo",
            "email": f"teste_completo_{int(time.time())}@example.com",
            "password": "senha123"
        }
        
        response = self.make_request("POST", "/auth/register", json=user_data)
        if response.status_code != 200:
            return False
        
        user_info = response.json()
        self.test_data['user_id'] = user_info['id']
        self.test_data['email'] = user_data['email']
        self.log(f"👤 Usuário criado: {user_info['nome']} (ID: {user_info['id']})")
        
        # 2. Login
        self.log("🔑 Testando login...")
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
            return False
            
        login_info = response.json()
        self.token = login_info['access_token']
        self.log(f"🎫 Token obtido: {self.token[:20]}...")
        
        # 3. Verificar /auth/me
        self.log("👤 Testando /auth/me...")
        response = self.make_request("GET", "/auth/me")
        if response.status_code == 200:
            me_info = response.json()
            self.log(f"✅ Usuário autenticado: {me_info['nome']}")
        
        return True
    
    def test_datasets(self):
        """Testa upload e listagem de datasets"""
        self.log("📊 TESTANDO DATASETS", "HEADER")
        
        # 1. Upload do arquivo clinicas.csv
        self.log("📁 Testando upload de dataset...")
        csv_file_path = "clinicas.csv"
        
        if not os.path.exists(csv_file_path):
            self.log(f"❌ Arquivo {csv_file_path} não encontrado!", "ERROR")
            return False
        
        with open(csv_file_path, 'rb') as f:
            files = {
                'file': ('clinicas.csv', f, 'text/csv')
            }
            data = {
                'nome': 'Clínicas para Teste Completo'
            }
            response = self.make_request("POST", "/datasets/upload", files=files, data=data)
        
        if response.status_code != 200:
            return False
            
        dataset_info = response.json()
        self.test_data['dataset_id'] = dataset_info['id']
        self.log(f"📊 Dataset criado: ID {dataset_info['id']}")
        self.log(f"🗄️ DB URI: {dataset_info['db_uri']}")
        
        # 2. Listar datasets
        self.log("📋 Testando listagem de datasets...")
        response = self.make_request("GET", "/datasets/")
        if response.status_code == 200:
            datasets = response.json()
            self.log(f"✅ Encontrados {len(datasets)} datasets")
        
        # 3. Obter dataset específico
        self.log("🔍 Testando consulta de dataset específico...")
        response = self.make_request("GET", f"/datasets/{self.test_data['dataset_id']}")
        if response.status_code == 200:
            dataset = response.json()
            self.log(f"✅ Dataset {dataset['id']}: {dataset['nome']}")
        
        return True
    
    def test_connections(self):
        """Testa criação e listagem de conexões"""
        self.log("🔗 TESTANDO CONEXÕES", "HEADER")
        
        # 1. Criar conexão
        self.log("🔌 Testando criação de conexão...")
        connection_data = {
            "tipo": "sqlite",
            "dataset_id": self.test_data['dataset_id']
        }
        
        response = self.make_request("POST", "/connections/", json=connection_data)
        if response.status_code != 200:
            return False
            
        connection_info = response.json()
        self.test_data['connection_id'] = connection_info['id']
        self.log(f"🔗 Conexão criada: ID {connection_info['id']}")
        self.log(f"🗄️ Tipo: {connection_info['tipo']}")
        
        # 2. Listar conexões
        self.log("📋 Testando listagem de conexões...")
        response = self.make_request("GET", "/connections/")
        if response.status_code == 200:
            connections = response.json()
            self.log(f"✅ Encontradas {len(connections)} conexões")
        
        # 3. Obter conexão específica
        self.log("🔍 Testando consulta de conexão específica...")
        response = self.make_request("GET", f"/connections/{self.test_data['connection_id']}")
        if response.status_code == 200:
            connection = response.json()
            self.log(f"✅ Conexão {connection['id']}: {connection['tipo']}")
        
        return True
    
    def test_agents(self):
        """Testa criação e listagem de agentes"""
        self.log("🤖 TESTANDO AGENTES", "HEADER")
        
        # 1. Criar agente
        self.log("🛠️ Testando criação de agente...")
        agent_data = {
            "nome": "Agente Teste Completo",
            "connection_id": self.test_data['connection_id'],
            "selected_model": "gpt-3.5-turbo",
            "top_k": 15,  # Testar com valor diferente do padrão
            "include_tables_key": "*",
            "advanced_mode": False,
            "processing_enabled": True,
            "refinement_enabled": False,
            "single_table_mode": False
        }
        
        response = self.make_request("POST", "/agents/", json=agent_data)
        if response.status_code != 200:
            return False
            
        agent_info = response.json()
        self.test_data['agent_id'] = agent_info['id']
        self.log(f"🤖 Agente criado: ID {agent_info['id']}")
        self.log(f"🧠 Modelo: {agent_info['selected_model']}")
        self.log(f"📊 TOP_K: {agent_info['top_k']}")
        
        # 2. Listar agentes
        self.log("📋 Testando listagem de agentes...")
        response = self.make_request("GET", "/agents/")
        if response.status_code == 200:
            agents = response.json()
            self.log(f"✅ Encontrados {len(agents)} agentes")
        
        # 3. Obter agente específico
        self.log("🔍 Testando consulta de agente específico...")
        response = self.make_request("GET", f"/agents/{self.test_data['agent_id']}")
        if response.status_code == 200:
            agent = response.json()
            self.log(f"✅ Agente {agent['id']}: {agent['nome']}")
        
        return True
    
    def test_runs_execution(self):
        """Testa execução de agentes e consulta de resultados"""
        self.log("🚀 TESTANDO EXECUÇÃO DE AGENTES", "HEADER")
        
        # Lista de perguntas para testar
        questions = [
            "Quantos estabelecimentos únicos existem na base?",
            "Qual é a taxa média de falta geral em 2023?",
            "Quais são os 5 horários com mais agendamentos confirmados?",
            "Qual estabelecimento tem a maior taxa de falta?",
            "Quantos agendamentos foram feitos por especialidade?"
        ]
        
        # Executar uma pergunta
        import random
        question = random.choice(questions)
        
        self.log(f"❓ Pergunta selecionada: '{question}'")
        
        # 1. Executar agente
        self.log("🎯 Testando execução de agente...")
        run_data = {
            "question": question
        }
        
        response = self.make_request("POST", f"/agents/{self.test_data['agent_id']}/run", json=run_data)
        if response.status_code != 200:
            return False
            
        run_info = response.json()
        self.test_data['run_id'] = run_info['id']
        self.log(f"🚀 Execução iniciada: Run ID {run_info['id']}")
        self.log(f"📋 Task ID: {run_info['task_id']}")
        
        # 2. Polling de resultado
        self.log("⏳ Aguardando resultado...")
        max_attempts = 30
        
        for attempt in range(1, max_attempts + 1):
            self.log(f"🔄 Tentativa {attempt}/{max_attempts}")
            
            response = self.make_request("GET", f"/runs/{self.test_data['run_id']}")
            if response.status_code != 200:
                return False
                
            run = response.json()
            status = run['status']
            
            if status == 'success':
                self.log("🎉 EXECUÇÃO CONCLUÍDA COM SUCESSO!", "SUCCESS")
                self.log(f"💬 Resposta: {run['result_data'][:100]}...")
                self.log(f"🗃️ SQL: {run['sql_used']}")
                self.log(f"⏱️ Tempo: {run['execution_ms']}ms")
                
                # Verificar se TOP_K foi aplicado corretamente
                if run['sql_used'] and 'LIMIT 15' in run['sql_used']:
                    self.log("✅ TOP_K (15) aplicado corretamente no SQL!", "SUCCESS")
                elif run['sql_used'] and 'LIMIT' in run['sql_used']:
                    self.log(f"⚠️ LIMIT encontrado mas não é 15: {run['sql_used']}", "WARN")
                
                break
                
            elif status == 'failure':
                self.log("❌ EXECUÇÃO FALHOU!", "ERROR")
                if run.get('error_type'):
                    self.log(f"🐛 Erro: {run['error_type']}", "ERROR")
                return False
                
            elif status in ['queued', 'running']:
                self.log(f"⏳ Status: {status}")
                time.sleep(2)
                
            else:
                self.log(f"❓ Status desconhecido: {status}", "WARN")
                time.sleep(2)
        else:
            self.log("⏰ TIMEOUT: Execução não finalizou no tempo esperado", "ERROR")
            return False
        
        return True
    
    def test_runs_listing(self):
        """Testa listagem de runs"""
        self.log("📋 TESTANDO LISTAGEM DE RUNS", "HEADER")
        
        # 1. Listar runs do agente
        self.log("📊 Testando listagem de runs do agente...")
        response = self.make_request("GET", f"/agents/{self.test_data['agent_id']}/runs")
        if response.status_code == 200:
            agent_runs = response.json()
            self.log(f"✅ Runs do agente: {len(agent_runs)} encontradas")
        
        # 2. Listar todas as runs do usuário
        self.log("📊 Testando listagem de todas as runs...")
        response = self.make_request("GET", "/runs/")
        if response.status_code == 200:
            all_runs = response.json()
            self.log(f"✅ Todas as runs: {len(all_runs)} encontradas")
        
        # 3. Consultar run específica
        self.log("🔍 Testando consulta de run específica...")
        response = self.make_request("GET", f"/runs/{self.test_data['run_id']}")
        if response.status_code == 200:
            run = response.json()
            self.log(f"✅ Run {run['id']}: {run['status']}")
        
        return True
    
    def run_complete_test(self):
        """Executa teste completo de todos os endpoints"""
        self.log("🧪 INICIANDO TESTE COMPLETO DA AGENTAPI", "HEADER")
        print("=" * 80)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Autenticação", self.test_authentication),
            ("Datasets", self.test_datasets),
            ("Conexões", self.test_connections),
            ("Agentes", self.test_agents),
            ("Execução", self.test_runs_execution),
            ("Listagem de Runs", self.test_runs_listing),
        ]
        
        for test_name, test_func in tests:
            self.log(f"🔄 Executando: {test_name}", "INFO")
            try:
                if not test_func():
                    self.log(f"❌ FALHA em: {test_name}", "ERROR")
                    return False
                self.log(f"✅ SUCESSO em: {test_name}", "SUCCESS")
            except Exception as e:
                self.log(f"💥 ERRO em {test_name}: {e}", "ERROR")
                return False
            
            print()  # Linha em branco entre testes
        
        return True

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 80)
    print("🧪 TESTE COMPLETO DA AGENTAPI")
    print("=" * 80)
    print(f"Base URL: {base_url}")
    print("Este teste verifica TODOS os endpoints da API")
    print("=" * 80)
    print()
    
    tester = CompleteAPITester(base_url)
    success = tester.run_complete_test()
    
    print()
    print("=" * 80)
    print("📊 RESUMO DOS TESTES:")
    print(f"✅ Testes passaram: {tester.tests_passed}")
    print(f"❌ Testes falharam: {tester.tests_failed}")
    print("=" * 80)
    
    if success:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("A API está funcionando corretamente.")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("Verifique os logs acima para detalhes.")
    
    print("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
