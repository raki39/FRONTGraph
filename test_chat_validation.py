#!/usr/bin/env python3
"""
Teste dos novos endpoints de validação por chat session
"""

import requests
import json
import time
from rich.console import Console
from rich.table import Table

console = Console()

# Configurações
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "tiraramos@hotmail.com"
ADMIN_PASSWORD = "tiago111"

class ChatValidationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.token = None
        
    def login_admin(self):
        """Faz login como administrador"""
        console.print("🔐 Fazendo login como administrador...", style="blue")
        
        response = self.session.post(
            f"{self.base_url}/auth/login",
            data={
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            console.print(f"👤 Login realizado: {data['user']['nome']}", style="green")
            return True
        else:
            console.print(f"❌ Falha no login: {response.status_code} - {response.text}", style="red")
            return False

    def create_test_dataset(self):
        """Cria um dataset de teste usando o arquivo CSV de exemplo"""
        console.print("📊 Verificando datasets...", style="blue")
        
        # Verificar se já existe dataset
        response = self.session.get(f"{self.base_url}/datasets/")
        if response.status_code == 200:
            datasets = response.json()
            if datasets:
                dataset_id = datasets[0]["id"]
                console.print(f"📊 Usando dataset existente: {dataset_id}", style="green")
                return dataset_id
        
        # Criar novo dataset
        csv_file_path = "clinicas.csv"
        try:
            with open(csv_file_path, 'rb') as f:
                files = {'file': ('clinicas.csv', f, 'text/csv')}
                response = self.session.post(
                    f"{self.base_url}/datasets/upload",
                    files=files,
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                
            if response.status_code == 200:
                dataset_id = response.json()["dataset_id"]
                console.print(f"📊 Dataset criado: {dataset_id}", style="green")
                return dataset_id
            else:
                console.print(f"❌ Erro ao criar dataset: {response.text}", style="red")
                return None
        except FileNotFoundError:
            console.print(f"❌ Arquivo {csv_file_path} não encontrado", style="red")
            return None

    def setup_prerequisites(self):
        """Configura pré-requisitos para o teste"""
        console.print("🔧 Configurando pré-requisitos...", style="blue")
        
        # Criar dataset
        dataset_id = self.create_test_dataset()
        if not dataset_id:
            return None, None, None
        
        # Criar conexão
        connection_data = {
            "nome": "Conexão de Teste Validação",
            "tipo": "postgres",
            "pg_dsn": "postgresql://agent:agent@postgres:5432/agentgraph",
            "dataset_id": dataset_id
        }
        
        response = self.session.post(f"{self.base_url}/connections/", json=connection_data)
        if response.status_code != 200:
            console.print(f"❌ Erro ao criar conexão: {response.text}", style="red")
            return None, None, None
        
        connection_id = response.json()["id"]
        console.print(f"🔗 Conexão criada: {connection_id}", style="green")
        
        # Criar agente
        agent_data = {
            "nome": "Agente de Teste Validação",
            "descricao": "Agente para testar validação por chat session",
            "selected_model": "gpt-4o-mini",
            "connection_id": connection_id
        }
        
        response = self.session.post(f"{self.base_url}/agents/", json=agent_data)
        if response.status_code != 200:
            console.print(f"❌ Erro ao criar agente: {response.text}", style="red")
            return None, None, None
        
        agent_id = response.json()["id"]
        console.print(f"🤖 Agente criado: {agent_id}", style="green")
        
        return dataset_id, connection_id, agent_id

    def create_chat_session_with_conversation(self, agent_id):
        """Cria uma sessão de chat com algumas perguntas"""
        console.print("💬 Criando sessão de chat com conversa...", style="blue")
        
        # Criar sessão
        session_data = {
            "agent_id": agent_id,
            "title": "Sessão de Teste para Validação"
        }
        
        response = self.session.post(f"{self.base_url}/chat-sessions/", json=session_data)
        if response.status_code != 200:
            console.print(f"❌ Erro ao criar sessão: {response.text}", style="red")
            return None
        
        session_id = response.json()["id"]
        console.print(f"💬 Sessão criada: {session_id}", style="green")
        
        # Fazer algumas perguntas
        questions = [
            "Quantos registros temos na tabela?",
            "Quais são as especialidades disponíveis?",
            "Mostre os 5 primeiros registros"
        ]
        
        run_ids = []
        for i, question in enumerate(questions, 1):
            console.print(f"❓ Pergunta {i}: {question}", style="cyan")
            
            response = self.session.post(
                f"{self.base_url}/agents/{agent_id}/run",
                json={
                    "question": question,
                    "chat_session_id": session_id
                }
            )
            
            if response.status_code == 200:
                run_id = response.json()["id"]
                run_ids.append(run_id)
                console.print(f"✅ Run criada: {run_id}", style="green")
            else:
                console.print(f"❌ Erro na pergunta {i}: {response.text}", style="red")
        
        # Aguardar processamento com polling
        console.print("⏳ Aguardando processamento das runs...", style="yellow")
        successful_runs = self.wait_for_runs_completion(run_ids)

        console.print(f"📊 {successful_runs}/{len(questions)} runs processadas com sucesso", style="blue")
        return session_id if successful_runs > 0 else None

    def wait_for_runs_completion(self, run_ids, max_wait_minutes=10):
        """Aguarda até que todas as runs sejam processadas ou timeout"""
        console.print(f"⏳ Aguardando {len(run_ids)} runs completarem (máximo {max_wait_minutes} minutos)...", style="yellow")

        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        successful_runs = 0

        while time.time() - start_time < max_wait_seconds:
            all_completed = True
            current_successful = 0

            for run_id in run_ids:
                try:
                    response = self.session.get(f"{self.base_url}/runs/{run_id}")
                    if response.status_code == 200:
                        run_data = response.json()
                        status = run_data["status"]

                        if status == "success":
                            current_successful += 1
                        elif status in ["running", "pending"]:
                            all_completed = False
                        # Se status é "error" ou "failed", consideramos como completado mas não bem-sucedido

                except Exception as e:
                    console.print(f"⚠️ Erro ao verificar run {run_id}: {e}", style="red")
                    all_completed = False

            successful_runs = current_successful

            # Mostrar progresso
            elapsed = int(time.time() - start_time)
            console.print(f"⏱️ {elapsed}s - {successful_runs}/{len(run_ids)} runs concluídas com sucesso", style="blue")

            if all_completed:
                console.print("✅ Todas as runs foram processadas!", style="green")
                break

            time.sleep(10)  # Aguardar 10 segundos antes de verificar novamente

        if time.time() - start_time >= max_wait_seconds:
            console.print(f"⚠️ Timeout após {max_wait_minutes} minutos", style="yellow")

        return successful_runs

    def test_chat_session_validation(self, session_id):
        """Testa a validação de uma sessão de chat"""
        console.print("🔍 Testando validação da sessão de chat...", style="blue")
        
        # Testar validação individual
        console.print("📋 1. Validação Individual da Sessão", style="cyan")
        validation_data = {
            "validation_type": "individual",
            "validation_model": "gpt-4o-mini"
        }
        
        response = self.session.post(
            f"{self.base_url}/validation/chat-sessions/{session_id}/validate",
            json=validation_data
        )
        
        if response.status_code == 200:
            result = response.json()
            console.print("✅ Validação individual concluída!", style="green")
            
            # Mostrar resultados
            table = Table(title="Resultados da Validação Individual")
            table.add_column("Métrica", style="cyan")
            table.add_column("Score", style="green")
            table.add_column("Detalhes", style="yellow")
            
            validation_result = result["validation_result"]
            table.add_row("Score Geral", f"{validation_result['overall_score']:.2f}/10", "")
            table.add_row("Clareza das Perguntas", f"{validation_result['question_clarity']:.2f}/10", "")
            table.add_row("Correção das Queries", f"{validation_result['query_correctness']:.2f}/10", "")
            table.add_row("Precisão das Respostas", f"{validation_result['response_accuracy']:.2f}/10", "")
            
            console.print(table)
            
            # Mostrar metadados da sessão
            metadata = result["metadata"]
            console.print(f"📊 Total de runs validadas: {metadata['total_runs']}", style="blue")
            console.print(f"📊 Score médio da sessão: {metadata['average_score']:.2f}", style="blue")
            console.print(f"📊 Consistência: {metadata['consistency_analysis']['consistency_score']:.2f}/10", style="blue")
            
            # Mostrar sugestões
            console.print("💡 Sugestões:", style="cyan")
            for suggestion in validation_result["suggestions"]:
                console.print(f"  • {suggestion}", style="white")
            
        else:
            console.print(f"❌ Erro na validação individual: {response.text}", style="red")
            return False
        
        # Testar validação comparativa
        console.print("\n📋 2. Validação Comparativa da Sessão", style="cyan")
        validation_data["validation_type"] = "comparative"
        
        response = self.session.post(
            f"{self.base_url}/validation/chat-sessions/{session_id}/validate",
            json=validation_data
        )
        
        if response.status_code == 200:
            result = response.json()
            console.print("✅ Validação comparativa concluída!", style="green")
            console.print(f"📊 Score geral: {result['validation_result']['overall_score']:.2f}/10", style="blue")
        else:
            console.print(f"❌ Erro na validação comparativa: {response.text}", style="red")
        
        return True

    def test_get_session_validations(self, session_id):
        """Testa a obtenção do histórico de validações"""
        console.print("📋 Testando histórico de validações...", style="blue")
        
        response = self.session.get(f"{self.base_url}/validation/chat-sessions/{session_id}/validations")
        
        if response.status_code == 200:
            data = response.json()
            console.print("✅ Histórico obtido com sucesso!", style="green")
            
            # Mostrar estatísticas
            console.print(f"📊 Total de validações: {data['total_validations']}", style="blue")
            console.print(f"📊 Score médio: {data['average_score']}", style="blue")
            console.print(f"📊 Runs validadas: {data['session_stats']['successful_runs']}", style="blue")
            console.print(f"📊 Taxa de sucesso: {data['session_stats']['success_rate']}%", style="blue")
            
            return True
        else:
            console.print(f"❌ Erro ao obter histórico: {response.text}", style="red")
            return False

    def cleanup(self, agent_id, connection_id):
        """NÃO limpa os dados de teste para evitar problemas de foreign key"""
        console.print("🧹 Mantendo dados de teste para evitar problemas...", style="blue")
        console.print(f"📝 Agent ID criado: {agent_id}", style="cyan")
        console.print(f"📝 Connection ID criado: {connection_id}", style="cyan")
        console.print("💡 Os dados podem ser limpos manualmente depois se necessário", style="yellow")

        # NÃO DELETAR NADA - deixar os dados persistirem
        # Isso evita problemas de foreign key com mensagens sendo salvas assincronamente

    def run_test(self):
        """Executa o teste completo"""
        console.print("🧪 INICIANDO TESTE DE VALIDAÇÃO POR CHAT SESSION", style="bold blue")
        console.print("=" * 60, style="blue")
        
        # Login
        if not self.login_admin():
            return False
        
        # Setup
        dataset_id, connection_id, agent_id = self.setup_prerequisites()
        if not agent_id:
            return False
        
        try:
            # Criar sessão com conversa
            session_id = self.create_chat_session_with_conversation(agent_id)
            if not session_id:
                return False
            
            # Testar validação
            if not self.test_chat_session_validation(session_id):
                return False
            
            # Testar histórico
            if not self.test_get_session_validations(session_id):
                return False
            
            console.print("🎉 TESTE DE VALIDAÇÃO CONCLUÍDO COM SUCESSO!", style="bold green")
            return True
            
        finally:
            # Cleanup
            self.cleanup(agent_id, connection_id)

if __name__ == "__main__":
    tester = ChatValidationTester()
    success = tester.run_test()
    exit(0 if success else 1)
