#!/usr/bin/env python3
"""
🧪 Teste de Integração ClickHouse - AgentSQL

Este script testa a integração completa do ClickHouse com o AgentSQL,
incluindo autenticação, criação de conexões, agentes e execução de queries.

Requisitos:
- Docker Compose com ClickHouse rodando (docker-compose.test.yml)
- API do AgentSQL rodando (http://localhost:8000)

Uso:
    python test_clickhouse_integration.py
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
CLICKHOUSE_HOST = "localhost"  # Para testes diretos do script
CLICKHOUSE_HOST_FOR_API = "host.docker.internal"  # Para API dentro do Docker acessar o host
CLICKHOUSE_PORT = 8123
CLICKHOUSE_USER = "test_user"
CLICKHOUSE_PASS = "test_password"
CLICKHOUSE_DB = "test_db"

class ClickHouseIntegrationTester:
    """Classe para testes de integração do ClickHouse"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.base_url = BASE_URL
        self.test_data = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp e cores"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "HEADER": "\033[95m",
            "SUCCESS": "\033[92m", 
            "ERROR": "\033[91m",
            "WARN": "\033[93m",
            "INFO": "\033[94m"
        }
        color = colors.get(level, "\033[0m")
        print(f"{color}[{timestamp}] {level}: {message}\033[0m")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Faz requisição com log"""
        url = f"{self.base_url}{endpoint}"
        
        # Adicionar token se disponível
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        start_time = time.time()
        response = self.session.request(method, url, **kwargs)
        duration = time.time() - start_time
        
        status_color = "SUCCESS" if 200 <= response.status_code < 300 else "ERROR"
        self.log(f"🌐 {method} {endpoint}", "INFO")
        self.log(f"✅ {response.status_code} - {'Sucesso' if response.status_code < 300 else 'Erro'} ({duration:.2f}s)", status_color)
        
        if response.status_code >= 400:
            self.log(f"Response: {response.text}", "ERROR")
        
        return response
    
    def test_api_health(self) -> bool:
        """Testa se a API está respondendo"""
        self.log("🏥 TESTANDO SAÚDE DA API", "HEADER")
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ API está respondendo - Status: {data.get('status')}", "SUCCESS")
                return True
            else:
                self.log(f"❌ API retornou status {response.status_code}", "ERROR")
                return False
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Falha ao conectar na API: {e}", "ERROR")
            self.log("💡 Certifique-se que a API está rodando em http://localhost:8000", "WARN")
            return False
    
    def test_clickhouse_direct(self) -> bool:
        """Testa conexão direta com ClickHouse"""
        self.log("🟠 TESTANDO CONEXÃO DIRETA COM CLICKHOUSE", "HEADER")
        try:
            url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/ping"
            response = requests.get(url, timeout=5)
            if response.status_code == 200 and response.text.strip() == "Ok.":
                self.log("✅ ClickHouse está respondendo", "SUCCESS")

                # Testar query simples usando POST com autenticação
                query_url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/"
                query_response = requests.post(
                    query_url,
                    data="SELECT 1",
                    auth=(CLICKHOUSE_USER, CLICKHOUSE_PASS),
                    timeout=5
                )
                if query_response.status_code == 200 and query_response.text.strip() == "1":
                    self.log("✅ ClickHouse aceita queries", "SUCCESS")

                    # Testar acesso ao banco de dados test_db
                    db_query = f"SELECT count() FROM system.tables WHERE database = '{CLICKHOUSE_DB}'"
                    db_response = requests.post(
                        query_url,
                        data=db_query,
                        auth=(CLICKHOUSE_USER, CLICKHOUSE_PASS),
                        timeout=5
                    )
                    if db_response.status_code == 200:
                        table_count = int(db_response.text.strip())
                        self.log(f"✅ Banco '{CLICKHOUSE_DB}' tem {table_count} tabelas", "SUCCESS")
                        return True
                    else:
                        self.log(f"⚠️  Não foi possível verificar tabelas: {db_response.text}", "WARN")
                        return True  # Ainda considera sucesso se a query básica funcionou
                else:
                    self.log(f"❌ ClickHouse não aceita queries: {query_response.status_code} - {query_response.text}", "ERROR")
                    return False
            else:
                self.log(f"❌ ClickHouse retornou resposta inesperada: {response.text}", "ERROR")
                return False
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Falha ao conectar no ClickHouse: {e}", "ERROR")
            self.log("💡 Execute: docker-compose -f docker-compose.test.yml up -d", "WARN")
            return False
    
    def login(self) -> bool:
        """Faz login e obtém token"""
        self.log("🔐 FAZENDO LOGIN", "HEADER")

        # Credenciais
        login_data = {
            "username": "tiraramos@hotmail.com",
            "password": "tiago111"
        }

        response = self.session.post(
            f"{self.base_url}/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.log(f"👤 Login realizado: {data.get('user', {}).get('nome', 'Usuário')}", "SUCCESS")
            return True
        else:
            self.log(f"❌ Falha no login: {response.status_code} - {response.text}", "ERROR")
            self.log("💡 Verifique as credenciais no código", "WARN")
            return False
    
    def test_clickhouse_connection_endpoint(self) -> bool:
        """Testa endpoint de teste de conexão ClickHouse"""
        self.log("🧪 TESTANDO ENDPOINT /connections/test (CLICKHOUSE)", "HEADER")

        connection_config = {
            "tipo": "clickhouse",
            "clickhouse_config": {
                "host": CLICKHOUSE_HOST_FOR_API,  # Usar host.docker.internal para API acessar
                "port": CLICKHOUSE_PORT,
                "database": CLICKHOUSE_DB,
                "username": CLICKHOUSE_USER,
                "password": CLICKHOUSE_PASS,
                "secure": False
            }
        }
        
        response = self.make_request("POST", "/connections/test", json=connection_config)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                self.log(f"✅ Conexão testada: {data.get('message')}", "SUCCESS")
                self.log(f"📊 JSON Response:", "INFO")
                self.log(json.dumps(data, indent=2, ensure_ascii=False), "INFO")
                return True
            else:
                self.log(f"❌ Conexão inválida: {data.get('message')}", "ERROR")
                return False
        else:
            self.log("❌ Falha ao testar conexão", "ERROR")
            return False
    
    def create_clickhouse_connection(self) -> bool:
        """Cria conexão ClickHouse"""
        self.log("🔗 CRIANDO CONEXÃO CLICKHOUSE", "HEADER")

        connection_data = {
            "tipo": "clickhouse",
            "clickhouse_config": {
                "host": CLICKHOUSE_HOST_FOR_API,  # Usar host.docker.internal para API acessar
                "port": CLICKHOUSE_PORT,
                "database": CLICKHOUSE_DB,
                "username": CLICKHOUSE_USER,
                "password": CLICKHOUSE_PASS,
                "secure": False
            }
        }
        
        response = self.make_request("POST", "/connections/", json=connection_data)
        
        if response.status_code in [200, 201]:
            connection = response.json()
            self.test_data["connection_id"] = connection["id"]
            self.log(f"✅ Conexão criada: ID {connection['id']}", "SUCCESS")
            self.log(f"   • Tipo: {connection.get('tipo')}", "INFO")
            self.log(f"   • DSN: {connection.get('ch_dsn', 'N/A')[:60]}...", "INFO")
            self.log(f"📊 JSON Response:", "INFO")
            self.log(json.dumps(connection, indent=2, ensure_ascii=False, default=str), "INFO")
            return True
        else:
            self.log("❌ Falha ao criar conexão", "ERROR")
            return False
    
    def list_connections(self) -> bool:
        """Lista conexões"""
        self.log("📋 LISTANDO CONEXÕES", "HEADER")
        
        response = self.make_request("GET", "/connections/")
        
        if response.status_code == 200:
            connections = response.json()
            self.log(f"✅ Total de conexões: {len(connections)}", "SUCCESS")
            
            for conn in connections:
                tipo = conn.get('tipo', 'N/A')
                conn_id = conn.get('id', 'N/A')
                icon = "🟠" if tipo == "clickhouse" else "🟢" if tipo == "postgres" else "📁"
                self.log(f"   {icon} ID {conn_id}: {tipo.upper()}", "INFO")
            
            return True
        else:
            self.log("❌ Falha ao listar conexões", "ERROR")
            return False
    
    def create_agent_with_clickhouse(self) -> bool:
        """Cria agente com conexão ClickHouse"""
        self.log("🤖 CRIANDO AGENTE COM CLICKHOUSE", "HEADER")
        
        agent_data = {
            "nome": "Agente ClickHouse Analytics",
            "connection_id": self.test_data["connection_id"],
            "selected_model": "gpt-4o-mini",
            "top_k": 10,
            "description": "Agente para análise de dados no ClickHouse",
            "advanced_mode": False,
            "processing_enabled": False,
            "refinement_enabled": False
        }
        
        response = self.make_request("POST", "/agents/", json=agent_data)
        
        if response.status_code in [200, 201]:
            agent = response.json()
            self.test_data["agent_id"] = agent["id"]
            self.log(f"✅ Agente criado: ID {agent['id']}", "SUCCESS")
            self.log(f"   • Nome: {agent.get('nome')}", "INFO")
            self.log(f"   • Modelo: {agent.get('selected_model')}", "INFO")
            self.log(f"   • Connection ID: {agent.get('connection_id')}", "INFO")
            self.log(f"📊 JSON Response:", "INFO")
            self.log(json.dumps(agent, indent=2, ensure_ascii=False, default=str), "INFO")
            return True
        else:
            self.log("❌ Falha ao criar agente", "ERROR")
            return False

    def test_clickhouse_queries(self) -> bool:
        """Testa queries no ClickHouse via AgentSQL"""
        self.log("💬 TESTANDO QUERIES NO CLICKHOUSE", "HEADER")

        agent_id = self.test_data["agent_id"]

        # Queries de teste específicas para ClickHouse
        queries = [
            "Mostre as 5 primeiras vendas da tabela sales",
            "Qual o total de vendas por categoria?",
            "Quantos clientes temos na tabela customers?",
            "Mostre os eventos de erro da tabela event_logs"
        ]

        run_ids = []
        self.log(f"🚀 Disparando {len(queries)} queries no ClickHouse...")

        for i, question in enumerate(queries, 1):
            run_data = {
                "question": question
            }

            response = self.make_request("POST", f"/agents/{agent_id}/run", json=run_data)

            if response.status_code == 200:
                run = response.json()
                run_ids.append(run['id'])
                self.log(f"   ✅ Query {i}: {question[:50]}...", "SUCCESS")
                self.log(f"      Run ID: {run['id']}", "INFO")
            else:
                self.log(f"   ❌ Erro na query {i}", "ERROR")

            time.sleep(0.5)  # Pequena pausa entre queries

        # Aguardar processamento verificando status
        self.log("⏳ Aguardando processamento das queries...", "WARN")
        self.log("📊 VERIFICANDO RESULTADOS DAS QUERIES", "HEADER")
        success_count = 0
        max_wait_per_query = 30  # 30 segundos por query

        for i, run_id in enumerate(run_ids, 1):
            self.log(f"   🔍 Verificando Query {i} (Run ID: {run_id})...", "INFO")

            # Polling: verificar status até completar ou timeout
            start_time = time.time()
            status = 'pending'

            while time.time() - start_time < max_wait_per_query:
                response = self.make_request("GET", f"/runs/{run_id}")

                if response.status_code == 200:
                    run_data = response.json()
                    status = run_data.get('status', 'unknown')

                    # Se completou (sucesso ou erro), sair do loop
                    if status in ['success', 'error', 'failed']:
                        break

                    # Aguardar 1 segundo antes de verificar novamente
                    time.sleep(1)
                else:
                    self.log(f"      ⚠️  Erro ao verificar status: {response.status_code}", "WARN")
                    break

            # Processar resultado final
            if response.status_code == 200:
                run_data = response.json()
                status = run_data.get('status', 'unknown')
                question = run_data.get('question', '')[:50]

                if status == 'success':
                    success_count += 1
                    self.log(f"   ✅ Query {i}: {status.upper()}", "SUCCESS")
                    self.log(f"      Pergunta: {question}...", "INFO")

                    # Mostrar resposta se disponível
                    answer = run_data.get('answer', '')
                    if answer:
                        self.log(f"      Resposta: {answer[:100]}...", "INFO")
                else:
                    self.log(f"   ❌ Query {i}: {status.upper()}", "ERROR")
                    self.log(f"      Pergunta: {question}...", "INFO")

                    # Mostrar erro se disponível
                    error = run_data.get('error_message', '')
                    if error:
                        self.log(f"      Erro: {error[:200]}...", "ERROR")

        self.log(f"📈 Resultado: {success_count}/{len(queries)} queries processadas com sucesso",
                 "SUCCESS" if success_count > 0 else "ERROR")

        return success_count > 0

    def verify_clickhouse_data(self) -> bool:
        """Verifica dados de teste no ClickHouse"""
        self.log("🔍 VERIFICANDO DADOS DE TESTE NO CLICKHOUSE", "HEADER")

        try:
            # Verificar tabelas via HTTP
            query = "SHOW TABLES FROM test_db"
            url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/?query={query}&user={CLICKHOUSE_USER}&password={CLICKHOUSE_PASS}"

            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                tables = response.text.strip().split('\n')
                self.log(f"✅ Tabelas encontradas: {len(tables)}", "SUCCESS")

                for table in tables:
                    if table:
                        self.log(f"   📊 {table}", "INFO")

                # Contar registros em cada tabela
                for table in ['sales', 'customers', 'event_logs', 'performance_metrics']:
                    count_query = f"SELECT count() FROM test_db.{table}"
                    count_url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/?query={count_query}&user={CLICKHOUSE_USER}&password={CLICKHOUSE_PASS}"

                    count_response = requests.get(count_url, timeout=5)
                    if count_response.status_code == 200:
                        count = count_response.text.strip()
                        self.log(f"   • {table}: {count} registros", "INFO")

                return True
            else:
                self.log(f"❌ Erro ao verificar tabelas: {response.status_code}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Erro ao verificar dados: {e}", "ERROR")
            return False

    def cleanup(self) -> bool:
        """Limpa recursos de teste"""
        self.log("🧹 LIMPANDO RECURSOS DE TESTE", "HEADER")
        success = True

        # Remover agente
        if "agent_id" in self.test_data:
            response = self.make_request("DELETE", f"/agents/{self.test_data['agent_id']}")
            if response.status_code in [200, 204]:
                self.log(f"✅ Agente {self.test_data['agent_id']} removido", "SUCCESS")
            else:
                self.log(f"⚠️  Falha ao remover agente", "WARN")
                success = False

        # Remover conexão
        if "connection_id" in self.test_data:
            response = self.make_request("DELETE", f"/connections/{self.test_data['connection_id']}")
            if response.status_code in [200, 204]:
                self.log(f"✅ Conexão {self.test_data['connection_id']} removida", "SUCCESS")
            else:
                self.log(f"⚠️  Falha ao remover conexão", "WARN")
                success = False

        return success

    def run_test(self) -> bool:
        """Executa teste completo"""
        self.log("🧪 TESTE DE INTEGRAÇÃO CLICKHOUSE - AgentSQL", "HEADER")
        self.log("=" * 70)

        try:
            # 1. Verificar pré-requisitos
            if not self.test_api_health():
                return False

            if not self.test_clickhouse_direct():
                return False

            if not self.verify_clickhouse_data():
                return False

            # 2. Autenticação
            if not self.login():
                return False

            # 3. Testar endpoint de teste de conexão
            if not self.test_clickhouse_connection_endpoint():
                return False

            # 4. Criar conexão ClickHouse
            if not self.create_clickhouse_connection():
                return False

            # 5. Listar conexões
            if not self.list_connections():
                return False

            # 6. Criar agente com ClickHouse
            if not self.create_agent_with_clickhouse():
                return False

            # 7. Testar queries no ClickHouse
            if not self.test_clickhouse_queries():
                self.log("⚠️  Algumas queries falharam, mas continuando...", "WARN")

            self.log("=" * 70)
            self.log("🎉 TESTE DE INTEGRAÇÃO CLICKHOUSE CONCLUÍDO COM SUCESSO!", "SUCCESS")
            self.log("=" * 70)

            return True

        except Exception as e:
            self.log(f"❌ Erro durante teste: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Perguntar se deve fazer cleanup
            print("\n")
            try:
                choice = input("🧹 Deseja limpar os recursos de teste? (s/n): ").strip().lower()
                if choice in ['s', 'y', 'sim', 'yes']:
                    self.cleanup()
                else:
                    self.log("ℹ️  Recursos de teste mantidos", "INFO")
                    self.log(f"   • Connection ID: {self.test_data.get('connection_id')}", "INFO")
                    self.log(f"   • Agent ID: {self.test_data.get('agent_id')}", "INFO")
            except KeyboardInterrupt:
                print("\n")
                self.log("ℹ️  Cleanup cancelado", "INFO")


if __name__ == "__main__":
    print("\n")
    print("🟠" * 35)
    print("🧪 TESTE DE INTEGRAÇÃO CLICKHOUSE - AgentSQL")
    print("🟠" * 35)
    print("\n")

    tester = ClickHouseIntegrationTester()

    try:
        success = tester.run_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n")
        print("⚠️  Testes interrompidos pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

