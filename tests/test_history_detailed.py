#!/usr/bin/env python3
"""
Teste DETALHADO do sistema de histórico com logs técnicos
"""

import requests
import time
import json

class DetailedHistoryTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.agent_id = 1
        self.token = None
        self.chat_session_id = None
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def authenticate(self):
        """Autentica e obtém token"""
        self.log("🔐 Fazendo login...")
        
        response = requests.post(f"{self.base_url}/auth/login", data={
            "username": "admin@example.com",
            "password": "admin"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.log("✅ Login realizado com sucesso")
            return True
        else:
            self.log(f"❌ Erro no login: {response.status_code}", "ERROR")
            return False
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def send_question_and_wait(self, question: str, chat_session_id: int = None):
        """Envia pergunta e aguarda resposta completa"""
        self.log(f"📝 Enviando: '{question}'")
        
        payload = {"question": question}
        if chat_session_id:
            payload["chat_session_id"] = chat_session_id
            self.log(f"🔗 Usando sessão existente: {chat_session_id}")
        else:
            self.log("🆕 Criando nova sessão")
        
        # Envia pergunta
        response = requests.post(
            f"{self.base_url}/agents/{self.agent_id}/run",
            json=payload,
            headers=self.get_headers()
        )
        
        if response.status_code != 200:
            self.log(f"❌ Erro ao enviar: {response.status_code}", "ERROR")
            return None
        
        run_data = response.json()
        run_id = run_data["id"]
        self.chat_session_id = run_data.get("chat_session_id")
        
        self.log(f"🚀 Run iniciada: ID {run_id}, Sessão: {self.chat_session_id}")
        
        # Aguarda conclusão
        for attempt in range(30):
            time.sleep(2)
            
            status_response = requests.get(
                f"{self.base_url}/runs/{run_id}",
                headers=self.get_headers()
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data["status"]
                
                if status == "success":
                    self.log(f"✅ Resposta recebida (tentativa {attempt + 1})")
                    return {
                        "run_id": run_id,
                        "chat_session_id": self.chat_session_id,
                        "response": status_data.get("response", ""),
                        "sql_query": status_data.get("sql_query"),
                        "execution_time": status_data.get("execution_time", 0)
                    }
                elif status == "failed":
                    self.log(f"❌ Execução falhou: {status_data.get('error', 'Erro desconhecido')}", "ERROR")
                    return None
                else:
                    if attempt % 5 == 0:  # Log a cada 5 tentativas
                        self.log(f"⏳ Status: {status} (tentativa {attempt + 1}/30)")
        
        self.log("❌ Timeout na execução", "ERROR")
        return None
    
    def test_history_flow(self):
        """Testa fluxo completo de histórico"""
        self.log("🧪 INICIANDO TESTE DETALHADO DE HISTÓRICO", "HEADER")
        
        # 1. Primeira pergunta (estabelece contexto)
        self.log("\n" + "="*60)
        self.log("FASE 1: PRIMEIRA PERGUNTA (SEM HISTÓRICO)")
        self.log("="*60)
        
        result1 = self.send_question_and_wait("Quantos produtos únicos temos na tabela?")
        if not result1:
            return False
        
        self.log(f"📊 Resposta 1: {result1['response'][:100]}...")
        self.log(f"🔍 SQL gerado: {result1.get('sql_query', 'N/A')}")
        
        # Aguarda embeddings serem processados
        self.log("⏳ Aguardando processamento de embeddings...")
        time.sleep(5)
        
        # 2. Segunda pergunta (deveria usar histórico)
        self.log("\n" + "="*60)
        self.log("FASE 2: PERGUNTA SIMILAR (DEVERIA USAR HISTÓRICO)")
        self.log("="*60)
        
        result2 = self.send_question_and_wait(
            "Me lembre novamente: qual é o total de produtos diferentes?", 
            self.chat_session_id
        )
        if not result2:
            return False
        
        self.log(f"📊 Resposta 2: {result2['response'][:100]}...")
        self.log(f"🔍 SQL gerado: {result2.get('sql_query', 'N/A')}")
        
        # 3. Terceira pergunta (contexto diferente)
        self.log("\n" + "="*60)
        self.log("FASE 3: PERGUNTA DIFERENTE (NOVO CONTEXTO)")
        self.log("="*60)
        
        result3 = self.send_question_and_wait(
            "Qual é o valor médio dos produtos?", 
            self.chat_session_id
        )
        if not result3:
            return False
        
        self.log(f"📊 Resposta 3: {result3['response'][:100]}...")
        self.log(f"🔍 SQL gerado: {result3.get('sql_query', 'N/A')}")
        
        # 4. Quarta pergunta (referência explícita ao histórico)
        self.log("\n" + "="*60)
        self.log("FASE 4: REFERÊNCIA EXPLÍCITA AO HISTÓRICO")
        self.log("="*60)
        
        result4 = self.send_question_and_wait(
            "Baseado nas perguntas anteriores, você pode comparar o número de produtos com o valor médio?", 
            self.chat_session_id
        )
        if not result4:
            return False
        
        self.log(f"📊 Resposta 4: {result4['response'][:100]}...")
        self.log(f"🔍 SQL gerado: {result4.get('sql_query', 'N/A')}")
        
        # Resumo
        self.log("\n" + "="*60)
        self.log("RESUMO DO TESTE")
        self.log("="*60)
        self.log(f"✅ Chat Session ID: {self.chat_session_id}")
        self.log(f"✅ 4 perguntas processadas")
        self.log(f"✅ Runs: {result1['run_id']}, {result2['run_id']}, {result3['run_id']}, {result4['run_id']}")
        
        return True
    
    def run_test(self):
        """Executa teste completo"""
        if not self.authenticate():
            return False
        
        return self.test_history_flow()

def main():
    tester = DetailedHistoryTester()
    
    print("🧪 TESTE DETALHADO DO SISTEMA DE HISTÓRICO")
    print("=" * 80)
    print("Este teste vai:")
    print("1. Fazer 4 perguntas sequenciais")
    print("2. Verificar se o histórico está sendo capturado")
    print("3. Analisar logs técnicos detalhados")
    print("4. Testar referências ao histórico")
    print("=" * 80)
    
    success = tester.run_test()
    
    if success:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
        print("📋 Próximos passos:")
        print("   1. Verificar logs do worker para detalhes técnicos")
        print("   2. Consultar banco de dados para confirmar dados")
        print("   3. Analisar se histórico foi usado corretamente")
    else:
        print("\n❌ TESTE FALHOU!")
        print("📋 Verificar:")
        print("   1. Logs de erro no worker")
        print("   2. Conectividade com a API")
        print("   3. Configuração do sistema de histórico")

if __name__ == "__main__":
    main()
