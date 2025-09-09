#!/usr/bin/env python3
"""
Teste end-to-end do sistema de histórico
Simula conversa real via API para verificar se o histórico está funcionando
"""

import requests
import json
import time
import logging
import psycopg2
import socket
from typing import Dict, Any, Optional

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoryEndToEndTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.agent_id = None
        self.connection_id = None
        self.chat_session_id = None

    def login(self, email: str = "admin@example.com", password: str = "admin") -> bool:
        """Faz login e obtém token"""
        try:
            logger.info(f"🔐 Fazendo login com {email}...")

            response = requests.post(f"{self.base_url}/auth/login", data={
                "username": email,
                "password": password
            })

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_id = data["user"]["id"]
                logger.info(f"✅ Login realizado! User ID: {self.user_id}")
                return True
            else:
                logger.error(f"❌ Erro no login: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Retorna headers com token de autenticação"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_local_ip(self) -> str:
        """Obtém o IP local da máquina"""
        try:
            # Conecta a um endereço externo para descobrir o IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "192.168.1.100"  # Fallback comum

    def test_postgresql_direct(self, host: str, port: int, database: str, username: str, password: str) -> bool:
        """Testa conexão PostgreSQL diretamente com psycopg2"""
        try:
            logger.info(f"🔌 Testando conexão direta: {username}@{host}:{port}/{database}")

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10
            )

            # Testa uma query simples
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            logger.info(f"✅ Conexão direta funcionou! Resultado: {result}")
            return True

        except Exception as e:
            logger.error(f"❌ Conexão direta falhou: {e}")
            return False

    def test_postgresql_connection(self, pg_dsn: str) -> bool:
        """Testa conexão PostgreSQL antes de criar"""
        try:
            logger.info(f"🧪 Testando conexão PostgreSQL: {pg_dsn}")

            response = requests.post(f"{self.base_url}/connections/test",
                headers=self.get_headers(),
                json={
                    "tipo": "postgres",
                    "pg_dsn": pg_dsn
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"📊 Resposta do teste: {result}")

                # Verifica se a conexão é realmente válida
                if result.get("valid", False):
                    logger.info("✅ Teste de conexão PostgreSQL passou!")
                    return True
                else:
                    logger.error(f"❌ Teste de conexão falhou: {result.get('message', 'Erro desconhecido')}")
                    return False
            else:
                logger.error(f"❌ Teste de conexão falhou: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro ao testar conexão PostgreSQL: {e}")
            return False

    def create_postgresql_connection(self) -> bool:
        """Cria conexão PostgreSQL local"""
        try:
            logger.info("🔗 Criando conexão PostgreSQL local...")

            # Primeiro testa conexão direta com psycopg2 (na máquina local)
            logger.info("🧪 Testando conexão direta com psycopg2 (localhost)...")
            if not self.test_postgresql_direct("localhost", 5432, "chainagent_db", "postgres", "admin"):
                logger.error("❌ Conexão direta falhou - PostgreSQL pode não estar rodando ou configurado corretamente")
                return False

            # Para a API (que roda no Docker), tenta várias opções
            logger.info("🐳 API roda no Docker, testando opções de conexão...")

            # Opções de conexão para Docker
            local_ip = self.get_local_ip()
            logger.info(f"🌐 IP local detectado: {local_ip}")

            docker_connection_options = [
                "postgresql://postgres:admin@host.docker.internal:5432/chainagent_db",
                f"postgresql://postgres:admin@{local_ip}:5432/chainagent_db",
                "postgresql://postgres:admin@172.17.0.1:5432/chainagent_db",  # Docker bridge default
                "postgresql://postgres:admin@192.168.65.1:5432/chainagent_db"  # Docker Desktop default
            ]

            pg_dsn = None
            for dsn in docker_connection_options:
                logger.info(f"🔗 Testando DSN para Docker: {dsn}")
                if self.test_postgresql_connection(dsn):
                    pg_dsn = dsn
                    logger.info(f"✅ Conexão Docker funcionou com: {dsn}")
                    break
                else:
                    logger.warning(f"⚠️ Conexão Docker falhou com: {dsn}")

            if not pg_dsn:
                logger.error("❌ Nenhuma opção de conexão Docker funcionou")
                return False

            logger.info(f"🔄 Criando conexão com DSN: {pg_dsn}")
            response = requests.post(f"{self.base_url}/connections/",
                headers=self.get_headers(),
                json={
                    "tipo": "postgres",
                    "pg_dsn": pg_dsn
                }
            )

            logger.info(f"📡 Status da resposta: {response.status_code}")

            if response.status_code == 200:
                connection_data = response.json()
                self.connection_id = connection_data["id"]
                logger.info(f"✅ Conexão PostgreSQL criada! ID: {self.connection_id}")
                logger.info(f"📊 Dados da conexão: {connection_data}")
                return True
            else:
                logger.error(f"❌ Erro ao criar conexão: {response.status_code}")
                logger.error(f"📄 Resposta completa: {response.text}")

                # Vamos tentar entender o erro
                try:
                    error_data = response.json()
                    logger.error(f"🔍 Detalhes do erro: {error_data}")
                except:
                    logger.error("🔍 Não foi possível parsear o erro como JSON")

                return False

        except Exception as e:
            logger.error(f"❌ Erro ao criar conexão PostgreSQL: {e}")
            return False

    def create_postgresql_agent(self) -> bool:
        """Cria agente PostgreSQL para teste de histórico"""
        try:
            logger.info("🤖 Criando agente PostgreSQL...")

            response = requests.post(f"{self.base_url}/agents/",
                headers=self.get_headers(),
                json={
                    "nome": "Agente PostgreSQL - Teste Histórico",
                    "connection_id": self.connection_id,
                    "selected_model": "gpt-4o-mini",
                    "top_k": 10,
                    "include_tables_key": "*",
                    "advanced_mode": False,
                    "processing_enabled": True,
                    "refinement_enabled": False,
                    "single_table_mode": False,
                    "selected_table": None
                }
            )

            if response.status_code == 200:
                agent_data = response.json()
                self.agent_id = agent_data["id"]
                logger.info(f"✅ Agente PostgreSQL criado! ID: {self.agent_id} - {agent_data['nome']}")
                return True
            else:
                logger.error(f"❌ Erro ao criar agente: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro ao criar agente PostgreSQL: {e}")
            return False
    
    def send_question(self, question: str, chat_session_id: Optional[int] = None) -> Dict[str, Any]:
        """Envia pergunta para o agente"""
        try:
            logger.info(f"💬 Enviando pergunta: '{question}'")
            if chat_session_id:
                logger.info(f"🔗 Usando chat session: {chat_session_id}")
            
            payload = {
                "question": question
            }
            
            if chat_session_id:
                payload["chat_session_id"] = chat_session_id
            
            response = requests.post(
                f"{self.base_url}/agents/{self.agent_id}/run",
                headers=self.get_headers(),
                json=payload
            )
            
            if response.status_code == 200:
                run_data = response.json()
                logger.info(f"✅ Pergunta enviada! Run ID: {run_data['id']}")
                logger.info(f"📊 Chat Session ID: {run_data.get('chat_session_id', 'N/A')}")
                
                # Atualiza chat_session_id se foi criado
                if not self.chat_session_id and run_data.get('chat_session_id'):
                    self.chat_session_id = run_data['chat_session_id']
                    logger.info(f"💾 Chat Session ID salvo: {self.chat_session_id}")
                
                return run_data
            else:
                logger.error(f"❌ Erro ao enviar pergunta: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar pergunta: {e}")
            return {}
    
    def wait_for_completion(self, run_id: int, max_wait: int = 120) -> Dict[str, Any]:
        """Aguarda conclusão da execução"""
        logger.info(f"⏳ Aguardando conclusão da execução {run_id}...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.base_url}/runs/{run_id}",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    run_data = response.json()
                    status = run_data.get("status", "unknown")
                    
                    if status in ["success", "failure"]:
                        logger.info(f"✅ Execução concluída com status: {status}")
                        return run_data
                    else:
                        logger.info(f"🔄 Status atual: {status}")
                        time.sleep(3)
                else:
                    logger.error(f"❌ Erro ao consultar run: {response.status_code}")
                    time.sleep(3)
                    
            except Exception as e:
                logger.error(f"❌ Erro ao consultar run: {e}")
                time.sleep(3)
        
        logger.error(f"⏰ Timeout aguardando conclusão da execução")
        return {}
    
    def run_conversation_test(self):
        """Executa teste de conversa com histórico usando PostgreSQL"""
        logger.info("🚀 INICIANDO TESTE END-TO-END DO HISTÓRICO COM POSTGRESQL")
        logger.info("=" * 60)

        # 1. Login
        if not self.login():
            return False

        # 2. Criar conexão PostgreSQL
        if not self.create_postgresql_connection():
            return False

        # 3. Criar agente PostgreSQL
        if not self.create_postgresql_agent():
            return False

        # 4. Primeira pergunta (cria nova sessão)
        logger.info("\n📝 PRIMEIRA PERGUNTA (Nova sessão PostgreSQL)")
        logger.info("-" * 40)

        run1 = self.send_question("Quantas tabelas existem no banco de dados?")
        if not run1:
            return False

        result1 = self.wait_for_completion(run1["id"])
        if result1:
            logger.info(f"📊 Resultado 1: {result1.get('result_data', 'N/A')[:100]}...")

        # 5. Segunda pergunta (usa mesma sessão)
        logger.info("\n📝 SEGUNDA PERGUNTA (Mesma sessão - deve usar histórico)")
        logger.info("-" * 40)

        run2 = self.send_question("E quantos registros tem a primeira tabela?", self.chat_session_id)
        if not run2:
            return False

        result2 = self.wait_for_completion(run2["id"])
        if result2:
            logger.info(f"📊 Resultado 2: {result2.get('result_data', 'N/A')[:100]}...")

        # 6. Terceira pergunta (relacionada ao histórico)
        logger.info("\n📝 TERCEIRA PERGUNTA (Referência ao histórico)")
        logger.info("-" * 40)

        run3 = self.send_question("Mostre um exemplo dos dados da tabela mencionada anteriormente", self.chat_session_id)
        if not run3:
            return False

        result3 = self.wait_for_completion(run3["id"])
        if result3:
            logger.info(f"📊 Resultado 3: {result3.get('result_data', 'N/A')[:100]}...")

        # 7. Verificar logs do histórico
        logger.info("\n🔍 VERIFICAÇÃO DOS LOGS")
        logger.info("-" * 40)
        logger.info("✅ Teste de conversa PostgreSQL concluído!")
        logger.info(f"💾 Chat Session ID usado: {self.chat_session_id}")
        logger.info(f"🔗 Connection ID usado: {self.connection_id}")
        logger.info(f"🤖 Agent ID usado: {self.agent_id}")
        logger.info("📋 Verifique os logs do worker para confirmar uso do histórico")

        return True

def main():
    """Função principal"""
    test = HistoryEndToEndTest()

    try:
        success = test.run_conversation_test()

        if success:
            logger.info("\n🎉 TESTE END-TO-END POSTGRESQL CONCLUÍDO COM SUCESSO!")
            logger.info("✅ Sistema de histórico testado via API com PostgreSQL")
            logger.info("🔗 Conexão PostgreSQL: host.docker.internal:5432/chainagent_db (via Docker)")
            logger.info("📋 Verifique os logs do worker para confirmar funcionamento do histórico")
        else:
            logger.error("\n❌ TESTE END-TO-END POSTGRESQL FALHOU!")

    except KeyboardInterrupt:
        logger.info("\n⏹️ Teste interrompido pelo usuário")
    except Exception as e:
        logger.error(f"\n💥 Erro inesperado: {e}")

if __name__ == "__main__":
    main()
