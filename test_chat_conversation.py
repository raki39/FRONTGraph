#!/usr/bin/env python3
"""
Teste específico para fluxo de conversa completo com Chat Sessions
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"

class ChatConversationTester:
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
    
    def login(self):
        """Faz login e obtém token"""
        self.log("🔐 FAZENDO LOGIN", "HEADER")

        # Credenciais corretas
        login_data = {
            "username": "tiraramos@hotmail.com",
            "password": "tiago111"
        }

        # Usar session diretamente como no teste que funciona
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
            return False
    
    def setup_prerequisites(self):
        """Configura pré-requisitos"""
        self.log("🔧 CONFIGURANDO PRÉ-REQUISITOS", "HEADER")

        # Buscar datasets existentes
        response = self.make_request("GET", "/datasets/")
        if response.status_code != 200:
            self.log("❌ Erro ao buscar datasets", "ERROR")
            return False

        datasets = response.json()

        # Se não há datasets, criar um usando o CSV de exemplo
        if not datasets:
            self.log("📊 Nenhum dataset encontrado, criando um novo...")
            dataset_id = self.create_test_dataset()
            if not dataset_id:
                return False
        else:
            dataset_id = datasets[0]["id"]
            self.log(f"📊 Usando dataset existente: {dataset_id}")

        self.test_data["dataset_id"] = dataset_id
        
        # Criar conexão
        connection_data = {
            "tipo": "sqlite",
            "dataset_id": dataset_id
        }
        
        response = self.make_request("POST", "/connections/", json=connection_data)
        if response.status_code != 200:
            self.log("❌ Erro ao criar conexão", "ERROR")
            return False
        
        connection = response.json()
        self.test_data["connection_id"] = connection["id"]
        self.log(f"🔗 Conexão criada: {connection['id']}")
        
        # Criar agente
        agent_data = {
            "nome": "Agente Teste Conversa",
            "connection_id": connection["id"],
            "selected_model": "gpt-4o-mini",
            "top_k": 10,
            "description": "Agente para testar conversas"
        }
        
        response = self.make_request("POST", "/agents/", json=agent_data)
        if response.status_code != 200:
            self.log("❌ Erro ao criar agente", "ERROR")
            return False
        
        agent = response.json()
        self.test_data["agent_id"] = agent["id"]
        self.log(f"🤖 Agente criado: {agent['id']}")
        
        return True

    def create_test_dataset(self):
        """Cria um dataset de teste usando o arquivo CSV de exemplo"""
        try:
            self.log("📊 Criando dataset de teste...")

            # Ler o arquivo CSV de exemplo
            csv_file_path = "clinicas.csv"
            if not os.path.exists(csv_file_path):
                self.log("❌ Arquivo clinicas.csv não encontrado", "ERROR")
                return None

            # Fazer upload do CSV
            with open(csv_file_path, 'rb') as f:
                files = {'file': ('clinicas.csv', f, 'text/csv')}
                response = self.session.post(
                    f"{self.base_url}/datasets/upload",
                    files=files,
                    headers={"Authorization": f"Bearer {self.token}"}
                )

            if response.status_code == 200:
                dataset = response.json()
                dataset_id = dataset["id"]
                self.log(f"✅ Dataset criado com sucesso: {dataset_id} - '{dataset['nome']}'")
                return dataset_id
            else:
                self.log(f"❌ Erro ao criar dataset: {response.status_code} - {response.text}", "ERROR")
                return None

        except Exception as e:
            self.log(f"❌ Erro ao criar dataset: {e}", "ERROR")
            return None

    def create_chat_session(self):
        """Cria chat session"""
        self.log("💬 CRIANDO CHAT SESSION", "HEADER")
        
        session_data = {
            "agent_id": self.test_data["agent_id"],
            "title": "Conversa de Teste Completa"
        }
        
        response = self.make_request("POST", "/chat-sessions/", json=session_data)
        if response.status_code != 200:
            self.log("❌ Erro ao criar chat session", "ERROR")
            return False
        
        session = response.json()
        self.test_data["session_id"] = session["id"]
        self.log(f"💬 Chat session criada: {session['id']} - '{session['title']}'")
        
        return True
    
    def test_conversation(self):
        """Testa conversa completa com múltiplas perguntas"""
        self.log("🗣️ TESTANDO CONVERSA COMPLETA", "HEADER")
        
        session_id = self.test_data["session_id"]
        agent_id = self.test_data["agent_id"]
        
        questions = [
            "Quantos registros temos na tabela?",
            "Quais são as cidades disponíveis?", 
            "Qual é a idade média das pessoas?",
            "Mostre os 3 registros mais antigos"
        ]
        
        # Disparar todas as perguntas em paralelo
        run_ids = []
        self.log("🚀 Disparando 4 perguntas em paralelo...")

        for i, question in enumerate(questions, 1):
            run_data = {
                "question": question,
                "chat_session_id": session_id
            }

            response = self.make_request("POST", f"/agents/{agent_id}/run", json=run_data)
            if response.status_code == 200:
                run = response.json()
                run_ids.append(run['id'])
                self.log(f"   ✅ Run {i}: {question[:40]}...")
            else:
                self.log(f"   ❌ Erro na pergunta {i}", "ERROR")

            time.sleep(0.5)  # Pequena pausa

        # Aguardar processamento
        self.log("⏳ Aguardando processamento (15s)...")
        time.sleep(15)

        # Verificar resultados
        success_count = 0
        for i, run_id in enumerate(run_ids, 1):
            response = self.make_request("GET", f"/runs/{run_id}")
            if response.status_code == 200:
                run_data = response.json()
                status = run_data.get('status', 'unknown')
                if status == 'success':
                    success_count += 1
                    self.log(f"   ✅ Run {i}: {status}")
                else:
                    self.log(f"   ❌ Run {i}: {status}", "ERROR")

        self.log(f"📊 Resultado: {success_count}/{len(questions)} perguntas processadas")
        
        return success_count > 0
    
    def check_messages(self):
        """Verifica mensagens criadas"""
        self.log("📋 VERIFICANDO MENSAGENS", "HEADER")
        
        session_id = self.test_data["session_id"]
        
        # Buscar mensagens
        response = self.make_request("GET", f"/chat-sessions/{session_id}/messages?page=1&per_page=20")
        if response.status_code != 200:
            self.log("❌ Erro ao buscar mensagens", "ERROR")
            return False
        
        data = response.json()
        messages = data.get("messages", [])
        pagination = data.get("pagination", {})
        
        self.log(f"📋 Total de mensagens: {len(messages)}")
        self.log(f"📊 Paginação: {pagination}")
        
        # Mostrar estrutura JSON das mensagens (primeiras 4)
        limited_messages = messages[:4] if len(messages) > 4 else messages
        self.log(f"📊 JSON das mensagens (primeiras 4 de {len(messages)} total):")
        import json
        self.log(json.dumps(limited_messages, indent=2, ensure_ascii=False, default=str))
        
        # Verificar sessão atualizada
        session_response = self.make_request("GET", f"/chat-sessions/{session_id}")
        if session_response.status_code == 200:
            session = session_response.json()
            self.log(f"📊 Sessão - Total mensagens: {session.get('total_messages', 0)}")
        
        return True
    
    def check_runs_history(self):
        """Verifica histórico de runs"""
        self.log("🚀 VERIFICANDO HISTÓRICO DE RUNS", "HEADER")
        
        session_id = self.test_data["session_id"]
        agent_id = self.test_data["agent_id"]
        
        # Buscar runs da sessão
        response = self.make_request("GET", f"/agents/{agent_id}/runs", params={
            "chat_session_id": session_id,
            "page": 1,
            "per_page": 10
        })
        
        if response.status_code != 200:
            self.log("❌ Erro ao buscar runs", "ERROR")
            return False
        
        data = response.json()
        runs = data.get("runs", [])
        
        self.log(f"🚀 Total de runs: {len(runs)}")
        
        for i, run in enumerate(runs):
            question = run.get('question', '')[:50] + "..." if len(run.get('question', '')) > 50 else run.get('question', '')
            status = run.get('status', 'unknown')
            self.log(f"   🔍 Run {i+1}: {question} - Status: {status}")
        
        return True

    def test_all_chat_session_endpoints(self):
        """Testa todos os endpoints de chat sessions"""
        self.log("📋 TESTANDO TODOS OS ENDPOINTS DE CHAT SESSIONS", "HEADER")
        self.log("-" * 60)

        session_id = self.test_data.get("session_id")
        if not session_id:
            self.log("❌ Session ID não encontrado", "ERROR")
            self.log(f"🔍 Dados disponíveis: {list(self.test_data.keys())}")
            return False

        # 1. GET /chat-sessions/ - Listar todas as sessões (PAGINADO)
        self.log("🔍 1. LISTANDO CHAT SESSIONS (PAGINADO)")
        response = self.make_request("GET", "/chat-sessions/?page=1&per_page=5")
        if response.status_code != 200:
            self.log("❌ Erro ao listar chat sessions", "ERROR")
            return False

        sessions_response = response.json()
        self.log(f"📊 JSON Response (página 1, 5 por página):")
        import json
        self.log(json.dumps(sessions_response, indent=2, ensure_ascii=False, default=str))

        # 2. GET /chat-sessions/{id} - Detalhes da sessão
        self.log("")
        self.log("🔍 2. DETALHES DA CHAT SESSION")
        response = self.make_request("GET", f"/chat-sessions/{session_id}")
        if response.status_code != 200:
            self.log("❌ Erro ao buscar detalhes da sessão", "ERROR")
            return False

        session_details = response.json()
        self.log(f"📊 JSON Response:")
        self.log(json.dumps(session_details, indent=2, ensure_ascii=False, default=str))

        # 3. GET /chat-sessions/{id}/messages - Mensagens (já testado, mas vamos mostrar estrutura)
        self.log("")
        self.log("🔍 3. ESTRUTURA DAS MENSAGENS")
        response = self.make_request("GET", f"/chat-sessions/{session_id}/messages?page=1&per_page=3")
        if response.status_code != 200:
            self.log("❌ Erro ao buscar mensagens", "ERROR")
            return False

        messages_data = response.json()
        self.log(f"📊 JSON Response (primeiras 3 mensagens):")
        self.log(json.dumps(messages_data, indent=2, ensure_ascii=False, default=str))

        # 4. PUT /chat-sessions/{id} - Atualizar sessão
        self.log("")
        self.log("🔍 4. ATUALIZANDO TÍTULO DA SESSÃO")
        update_data = {
            "title": "Sessão de Teste Atualizada",
            "status": "active"
        }
        response = self.make_request("PUT", f"/chat-sessions/{session_id}", json=update_data)
        if response.status_code != 200:
            self.log("❌ Erro ao atualizar sessão", "ERROR")
            return False

        updated_session = response.json()
        self.log(f"✅ JSON Response da atualização:")
        self.log(json.dumps(updated_session, indent=2, ensure_ascii=False, default=str))

        # 5. Verificar se a atualização foi persistida
        self.log("")
        self.log("🔍 5. VERIFICANDO PERSISTÊNCIA DA ATUALIZAÇÃO")
        response = self.make_request("GET", f"/chat-sessions/{session_id}")
        if response.status_code != 200:
            self.log("❌ Erro ao verificar atualização", "ERROR")
            return False

        verified_session = response.json()
        if verified_session.get('title') == "Sessão de Teste Atualizada":
            self.log("✅ Atualização persistida corretamente")
        else:
            self.log("❌ Atualização não foi persistida", "ERROR")
            return False

        # 6. Criar uma segunda sessão para testar listagem
        self.log("")
        self.log("🔍 6. CRIANDO SEGUNDA SESSÃO PARA TESTE")
        new_session_data = {
            "title": "Segunda Sessão de Teste",
            "agent_id": self.test_data["agent_id"]
        }
        response = self.make_request("POST", "/chat-sessions/", json=new_session_data)
        if response.status_code not in [200, 201]:
            self.log(f"❌ Erro ao criar segunda sessão: {response.status_code} - {response.text}", "ERROR")
            return False

        second_session = response.json()
        second_session_id = second_session.get("id")
        self.log(f"✅ JSON Response da criação:")
        self.log(json.dumps(second_session, indent=2, ensure_ascii=False, default=str))

        # 7. Listar novamente para ver as duas sessões (PAGINADO)
        self.log("")
        self.log("🔍 7. LISTAGEM COM MÚLTIPLAS SESSÕES (PAGINADO)")
        response = self.make_request("GET", "/chat-sessions/?page=1&per_page=3")
        if response.status_code != 200:
            self.log("❌ Erro ao listar sessões", "ERROR")
            return False

        sessions_response = response.json()
        self.log(f"📊 JSON Response (página 1, 3 por página):")
        self.log(json.dumps(sessions_response, indent=2, ensure_ascii=False, default=str))

        # 7.1. Testar filtro por agente específico
        self.log("")
        self.log("🔍 7.1. FILTRO POR AGENTE ESPECÍFICO")
        agent_id = self.test_data["agent_id"]
        response = self.make_request("GET", f"/chat-sessions/?agent_id={agent_id}&page=1&per_page=5")
        if response.status_code != 200:
            self.log("❌ Erro ao filtrar por agente", "ERROR")
            return False

        agent_sessions = response.json()
        self.log(f"📊 Sessões do agente {agent_id}:")
        self.log(f"   • Total encontrado: {agent_sessions['pagination']['total_items']}")
        self.log(f"   • Página: {agent_sessions['pagination']['page']}/{agent_sessions['pagination']['total_pages']}")

        # Verificar se todas as sessões são do agente correto
        for session in agent_sessions['sessions']:
            if session['agent_id'] != agent_id:
                self.log(f"❌ Sessão {session['id']} não pertence ao agente {agent_id}", "ERROR")
                return False
        self.log(f"✅ Todas as {len(agent_sessions['sessions'])} sessões pertencem ao agente {agent_id}")

        # 7.2. Testar filtro por status
        self.log("")
        self.log("🔍 7.2. FILTRO POR STATUS")
        response = self.make_request("GET", "/chat-sessions/?status=active&page=1&per_page=5")
        if response.status_code != 200:
            self.log("❌ Erro ao filtrar por status", "ERROR")
            return False

        active_sessions = response.json()
        self.log(f"📊 Sessões ativas:")
        self.log(f"   • Total encontrado: {active_sessions['pagination']['total_items']}")
        self.log(f"   • Página: {active_sessions['pagination']['page']}/{active_sessions['pagination']['total_pages']}")

        # Verificar se todas as sessões são ativas
        for session in active_sessions['sessions']:
            if session['status'] != 'active':
                self.log(f"❌ Sessão {session['id']} não está ativa", "ERROR")
                return False
        self.log(f"✅ Todas as {len(active_sessions['sessions'])} sessões estão ativas")

        # 7.3. Testar combinação de filtros
        self.log("")
        self.log("🔍 7.3. COMBINAÇÃO DE FILTROS (AGENTE + STATUS)")
        response = self.make_request("GET", f"/chat-sessions/?agent_id={agent_id}&status=active&page=1&per_page=10")
        if response.status_code != 200:
            self.log("❌ Erro ao combinar filtros", "ERROR")
            return False

        filtered_sessions = response.json()
        self.log(f"📊 Sessões do agente {agent_id} que estão ativas:")
        self.log(f"   • Total encontrado: {filtered_sessions['pagination']['total_items']}")
        self.log(f"   • Página: {filtered_sessions['pagination']['page']}/{filtered_sessions['pagination']['total_pages']}")

        # Verificar se todas as sessões atendem aos critérios
        for session in filtered_sessions['sessions']:
            if session['agent_id'] != agent_id or session['status'] != 'active':
                self.log(f"❌ Sessão {session['id']} não atende aos filtros", "ERROR")
                return False
        self.log(f"✅ Todas as {len(filtered_sessions['sessions'])} sessões atendem aos filtros")

        # 7.4. Testar paginação (página 2)
        if filtered_sessions['pagination']['total_pages'] > 1:
            self.log("")
            self.log("🔍 7.4. TESTANDO PAGINAÇÃO (PÁGINA 2)")
            response = self.make_request("GET", f"/chat-sessions/?agent_id={agent_id}&status=active&page=2&per_page=10")
            if response.status_code != 200:
                self.log("❌ Erro ao acessar página 2", "ERROR")
                return False

            page2_sessions = response.json()
            self.log(f"📊 Página 2:")
            self.log(f"   • Sessões na página: {len(page2_sessions['sessions'])}")
            self.log(f"   • has_prev: {page2_sessions['pagination']['has_prev']}")
            self.log(f"   • has_next: {page2_sessions['pagination']['has_next']}")

            if not page2_sessions['pagination']['has_prev']:
                self.log("❌ Página 2 deveria ter has_prev=true", "ERROR")
                return False
            self.log("✅ Paginação funcionando corretamente")
        else:
            self.log("ℹ️ Apenas 1 página disponível - paginação não testada")

        # 8. DELETE /chat-sessions/{id} - Deletar segunda sessão
        self.log("")
        self.log("🔍 8. DELETANDO SEGUNDA SESSÃO")
        response = self.make_request("DELETE", f"/chat-sessions/{second_session_id}")
        if response.status_code != 200:
            self.log("❌ Erro ao deletar segunda sessão", "ERROR")
            return False

        self.log("✅ Segunda sessão deletada com sucesso")

        # 9. Verificar se a deleção funcionou
        self.log("")
        self.log("🔍 9. VERIFICANDO DELEÇÃO")
        response = self.make_request("GET", f"/chat-sessions/{second_session_id}")
        if response.status_code == 404:
            self.log("✅ Sessão deletada corretamente (404 esperado)", "SUCCESS")
        else:
            self.log(f"❌ Sessão ainda existe após deleção: {response.status_code}", "ERROR")
            return False

        # 10. Verificar se filtros ainda funcionam após deleção
        self.log("")
        self.log("🔍 10. VERIFICANDO FILTROS APÓS DELEÇÃO")
        response = self.make_request("GET", f"/chat-sessions/?agent_id={agent_id}&status=active&page=1&per_page=5")
        if response.status_code != 200:
            self.log("❌ Erro ao verificar filtros após deleção", "ERROR")
            return False

        final_sessions = response.json()
        self.log(f"📊 Sessões restantes do agente {agent_id}:")
        self.log(f"   • Total: {final_sessions['pagination']['total_items']}")

        # Verificar se a sessão deletada não aparece mais
        for session in final_sessions['sessions']:
            if session['id'] == second_session_id:
                self.log(f"❌ Sessão deletada {second_session_id} ainda aparece na listagem", "ERROR")
                return False
        self.log("✅ Sessão deletada não aparece mais na listagem filtrada")

        self.log("")
        self.log("🎉 TODOS OS ENDPOINTS DE CHAT SESSIONS TESTADOS COM SUCESSO!", "SUCCESS")
        return True

    def cleanup(self):
        """Limpa dados de teste"""
        self.log("🧹 LIMPANDO DADOS", "HEADER")
        
        # Deletar agente
        if "agent_id" in self.test_data:
            self.make_request("DELETE", f"/agents/{self.test_data['agent_id']}")
            self.log("✅ Agente deletado")
        
        # Deletar conexão
        if "connection_id" in self.test_data:
            self.make_request("DELETE", f"/connections/{self.test_data['connection_id']}")
            self.log("✅ Conexão deletada")
    
    def run_test(self):
        """Executa teste completo"""
        self.log("🧪 INICIANDO TESTE DE CONVERSA COMPLETA", "HEADER")
        self.log("=" * 60)
        
        try:
            if not self.login():
                return False
            
            if not self.setup_prerequisites():
                return False
            
            if not self.create_chat_session():
                return False
            
            if not self.test_conversation():
                return False
            
            if not self.check_messages():
                return False
            
            if not self.check_runs_history():
                return False

            if not self.test_all_chat_session_endpoints():
                return False

            self.log("🎉 TESTE COMPLETO REALIZADO COM SUCESSO!", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"❌ Erro durante teste: {str(e)}", "ERROR")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    tester = ChatConversationTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)
