#!/usr/bin/env python3
"""
🧪 Teste de Integração ClickHouse - AgentSQL

Este script testa a integração completa do ClickHouse com o AgentSQL,
incluindo autenticação, criação de conexões, agentes e execução de queries.

Requisitos:
- Docker Compose com ClickHouse rodando (docker-compose.test.yml)
- API do AgentSQL rodando (http://localhost:8000)

Uso:
    python tests/test_clickhouse_integration.py
"""

import os
import sys
import time
import requests
from typing import Dict, Optional, Tuple
from datetime import datetime

# Configurações
API_URL = os.getenv("API_URL", "http://localhost:8000")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "test_user")
CLICKHOUSE_PASS = os.getenv("CLICKHOUSE_PASS", "test_password")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "test_db")

# Cores para output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class ClickHouseIntegrationTest:
    """Classe para testes de integração do ClickHouse"""
    
    def __init__(self):
        self.api_url = API_URL
        self.token: Optional[str] = None
        self.connection_id: Optional[int] = None
        self.agent_id: Optional[int] = None
        self.test_user_email = f"test_clickhouse_{int(time.time())}@test.com"
        self.test_user_password = "test123456"
        
    def log(self, message: str, color: str = Colors.NC):
        """Log com timestamp e cor"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.NC}")
    
    def log_success(self, message: str):
        """Log de sucesso"""
        self.log(f"✅ {message}", Colors.GREEN)
    
    def log_error(self, message: str):
        """Log de erro"""
        self.log(f"❌ {message}", Colors.RED)
    
    def log_info(self, message: str):
        """Log de informação"""
        self.log(f"ℹ️  {message}", Colors.BLUE)
    
    def log_warning(self, message: str):
        """Log de aviso"""
        self.log(f"⚠️  {message}", Colors.YELLOW)
    
    def test_api_health(self) -> bool:
        """Testa se a API está respondendo"""
        self.log_info("Testando saúde da API...")
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                self.log_success("API está respondendo")
                return True
            else:
                self.log_error(f"API retornou status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Falha ao conectar na API: {e}")
            return False
    
    def test_clickhouse_connection(self) -> bool:
        """Testa se o ClickHouse está respondendo"""
        self.log_info("Testando conexão direta com ClickHouse...")
        try:
            url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/ping"
            response = requests.get(url, timeout=5)
            if response.status_code == 200 and response.text.strip() == "Ok.":
                self.log_success("ClickHouse está respondendo")
                return True
            else:
                self.log_error(f"ClickHouse retornou resposta inesperada: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Falha ao conectar no ClickHouse: {e}")
            return False
    
    def register_user(self) -> bool:
        """Registra usuário de teste"""
        self.log_info(f"Registrando usuário de teste: {self.test_user_email}")
        try:
            response = requests.post(
                f"{self.api_url}/auth/register",
                json={
                    "email": self.test_user_email,
                    "password": self.test_user_password,
                    "nome": "Test User ClickHouse"
                }
            )
            if response.status_code in [200, 201]:
                self.log_success("Usuário registrado com sucesso")
                return True
            elif response.status_code == 400 and "já existe" in response.text.lower():
                self.log_warning("Usuário já existe, continuando...")
                return True
            else:
                self.log_error(f"Falha ao registrar usuário: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao registrar usuário: {e}")
            return False
    
    def login(self) -> bool:
        """Faz login e obtém token"""
        self.log_info("Fazendo login...")
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                data={
                    "username": self.test_user_email,
                    "password": self.test_user_password
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.log_success("Login realizado com sucesso")
                    return True
                else:
                    self.log_error("Token não encontrado na resposta")
                    return False
            else:
                self.log_error(f"Falha ao fazer login: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao fazer login: {e}")
            return False
    
    def test_connection_endpoint(self) -> bool:
        """Testa endpoint de teste de conexão"""
        self.log_info("Testando endpoint de teste de conexão ClickHouse...")
        try:
            response = requests.post(
                f"{self.api_url}/connections/test",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "tipo": "clickhouse",
                    "clickhouse_config": {
                        "host": CLICKHOUSE_HOST,
                        "port": CLICKHOUSE_PORT,
                        "database": CLICKHOUSE_DB,
                        "username": CLICKHOUSE_USER,
                        "password": CLICKHOUSE_PASS,
                        "secure": False
                    }
                }
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    self.log_success(f"Conexão testada com sucesso: {data.get('message')}")
                    return True
                else:
                    self.log_error(f"Conexão inválida: {data.get('message')}")
                    return False
            else:
                self.log_error(f"Falha ao testar conexão: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao testar conexão: {e}")
            return False
    
    def create_connection(self) -> bool:
        """Cria conexão ClickHouse"""
        self.log_info("Criando conexão ClickHouse...")
        try:
            response = requests.post(
                f"{self.api_url}/connections/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "tipo": "clickhouse",
                    "clickhouse_config": {
                        "host": CLICKHOUSE_HOST,
                        "port": CLICKHOUSE_PORT,
                        "database": CLICKHOUSE_DB,
                        "username": CLICKHOUSE_USER,
                        "password": CLICKHOUSE_PASS,
                        "secure": False
                    }
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.connection_id = data.get("id")
                self.log_success(f"Conexão criada com sucesso (ID: {self.connection_id})")
                self.log_info(f"  Tipo: {data.get('tipo')}")
                self.log_info(f"  DSN: {data.get('ch_dsn', 'N/A')[:50]}...")
                return True
            else:
                self.log_error(f"Falha ao criar conexão: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao criar conexão: {e}")
            return False
    
    def list_connections(self) -> bool:
        """Lista conexões"""
        self.log_info("Listando conexões...")
        try:
            response = requests.get(
                f"{self.api_url}/connections/",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                connections = response.json()
                self.log_success(f"Total de conexões: {len(connections)}")
                for conn in connections:
                    tipo = conn.get('tipo', 'N/A')
                    conn_id = conn.get('id', 'N/A')
                    self.log_info(f"  - ID {conn_id}: {tipo}")
                return True
            else:
                self.log_error(f"Falha ao listar conexões: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao listar conexões: {e}")
            return False
    
    def create_agent(self) -> bool:
        """Cria agente com conexão ClickHouse"""
        self.log_info("Criando agente com conexão ClickHouse...")
        try:
            response = requests.post(
                f"{self.api_url}/agents/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "nome": "Agente ClickHouse Test",
                    "connection_id": self.connection_id,
                    "selected_model": "gpt-4o-mini",
                    "top_k": 10,
                    "description": "Agente de teste para ClickHouse",
                    "advanced_mode": False,
                    "processing_enabled": False,
                    "refinement_enabled": False
                }
            )
            if response.status_code in [200, 201]:
                data = response.json()
                self.agent_id = data.get("id")
                self.log_success(f"Agente criado com sucesso (ID: {self.agent_id})")
                self.log_info(f"  Nome: {data.get('nome')}")
                self.log_info(f"  Modelo: {data.get('selected_model')}")
                return True
            else:
                self.log_error(f"Falha ao criar agente: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_error(f"Erro ao criar agente: {e}")
            return False

    def cleanup(self) -> bool:
        """Remove recursos de teste"""
        self.log_info("Limpando recursos de teste...")
        success = True

        # Remove agente
        if self.agent_id:
            try:
                response = requests.delete(
                    f"{self.api_url}/agents/{self.agent_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if response.status_code in [200, 204]:
                    self.log_success(f"Agente {self.agent_id} removido")
                else:
                    self.log_warning(f"Falha ao remover agente: {response.text}")
                    success = False
            except Exception as e:
                self.log_warning(f"Erro ao remover agente: {e}")
                success = False

        # Remove conexão
        if self.connection_id:
            try:
                response = requests.delete(
                    f"{self.api_url}/connections/{self.connection_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if response.status_code in [200, 204]:
                    self.log_success(f"Conexão {self.connection_id} removida")
                else:
                    self.log_warning(f"Falha ao remover conexão: {response.text}")
                    success = False
            except Exception as e:
                self.log_warning(f"Erro ao remover conexão: {e}")
                success = False

        return success

    def run_all_tests(self) -> bool:
        """Executa todos os testes"""
        print("\n" + "="*70)
        print(f"{Colors.CYAN}🧪 TESTE DE INTEGRAÇÃO CLICKHOUSE - AgentSQL{Colors.NC}")
        print("="*70 + "\n")

        print(f"{Colors.BLUE}📋 Configurações:{Colors.NC}")
        print(f"  API URL: {self.api_url}")
        print(f"  ClickHouse Host: {CLICKHOUSE_HOST}")
        print(f"  ClickHouse Port: {CLICKHOUSE_PORT}")
        print(f"  ClickHouse User: {CLICKHOUSE_USER}")
        print(f"  ClickHouse DB: {CLICKHOUSE_DB}")
        print()

        tests = [
            ("Saúde da API", self.test_api_health),
            ("Conexão ClickHouse", self.test_clickhouse_connection),
            ("Registro de Usuário", self.register_user),
            ("Login", self.login),
            ("Teste de Conexão (Endpoint)", self.test_connection_endpoint),
            ("Criação de Conexão", self.create_connection),
            ("Listagem de Conexões", self.list_connections),
            ("Criação de Agente", self.create_agent),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n{Colors.CYAN}{'─'*70}{Colors.NC}")
            print(f"{Colors.CYAN}🧪 Teste: {test_name}{Colors.NC}")
            print(f"{Colors.CYAN}{'─'*70}{Colors.NC}")

            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
                    self.log_error(f"Teste '{test_name}' falhou!")
                    # Não para nos primeiros erros, continua testando
            except Exception as e:
                failed += 1
                self.log_error(f"Exceção no teste '{test_name}': {e}")
                import traceback
                traceback.print_exc()

        # Resumo
        print("\n" + "="*70)
        print(f"{Colors.CYAN}📊 RESUMO DOS TESTES{Colors.NC}")
        print("="*70)
        print(f"{Colors.GREEN}✅ Testes Passados: {passed}{Colors.NC}")
        print(f"{Colors.RED}❌ Testes Falhados: {failed}{Colors.NC}")
        print(f"📈 Total: {passed + failed}")
        print(f"🎯 Taxa de Sucesso: {(passed / (passed + failed) * 100):.1f}%")
        print("="*70 + "\n")

        # Cleanup
        if self.connection_id or self.agent_id:
            print(f"{Colors.YELLOW}🧹 Deseja limpar os recursos de teste? (y/n): {Colors.NC}", end="")
            try:
                choice = input().strip().lower()
                if choice == 'y':
                    self.cleanup()
            except KeyboardInterrupt:
                print("\n")
                self.log_info("Cleanup cancelado")

        return failed == 0


def main():
    """Função principal"""
    test = ClickHouseIntegrationTest()

    try:
        success = test.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Testes interrompidos pelo usuário{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Erro fatal: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

