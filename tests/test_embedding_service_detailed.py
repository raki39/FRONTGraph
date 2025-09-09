#!/usr/bin/env python3
"""
Teste DETALHADO do Embedding Service
Mostra exatamente como funciona o serviço de embeddings para o sistema de histórico
"""

import os
import sys
import json
import time
import logging
from typing import List

# Adiciona paths para imports
sys.path.append('.')
sys.path.append('./agentgraph')

# Configuração de logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingServiceDetailedTester:
    """Testa o embedding service com logs detalhados"""
    
    def __init__(self):
        self.results = []
        
    def log_step(self, step: str, details: str = ""):
        """Log detalhado de cada passo"""
        logger.info(f"🔍 {step}")
        if details:
            logger.info(f"   📝 {details}")
    
    def test_1_import_and_setup(self):
        """Teste 1: Importação e configuração inicial"""
        self.log_step("TESTE 1: Importação e configuração do embedding service")
        
        try:
            from agentgraph.services.embedding_service import EmbeddingService, get_embedding_service
            self.log_step("✅ Importação bem-sucedida", "Módulo embedding_service importado")
            
            # Verifica se OpenAI API key está configurada
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                self.log_step("✅ OpenAI API Key encontrada", f"Key: {openai_key[:10]}...{openai_key[-4:]}")
            else:
                self.log_step("❌ OpenAI API Key não encontrada", "Defina OPENAI_API_KEY")
                return False
            
            # Cria instância do serviço
            service = EmbeddingService(
                model="text-embedding-3-small",
                cache_ttl=3600,
                redis_url="redis://redis:6379/0"
            )
            
            self.log_step("✅ Serviço criado", f"Modelo: {service.model}, Cache TTL: {service.cache_ttl}s")
            
            # Verifica informações do modelo
            info = service.get_model_info()
            self.log_step("📊 Informações do modelo:", json.dumps(info, indent=2))
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro na importação", str(e))
            return False
    
    def test_2_single_embedding(self):
        """Teste 2: Geração de embedding único"""
        self.log_step("TESTE 2: Geração de embedding único")
        
        try:
            from agentgraph.services.embedding_service import get_embedding_service
            
            service = get_embedding_service()
            
            # Texto de teste
            test_text = "Quantos clientes temos na base de dados?"
            self.log_step("📝 Texto de entrada", f"'{test_text}' ({len(test_text)} caracteres)")
            
            # Gera embedding
            start_time = time.time()
            embedding = service.get_embedding(test_text)
            duration = time.time() - start_time
            
            self.log_step("⏱️ Tempo de geração", f"{duration:.3f} segundos")
            self.log_step("📊 Embedding gerado", f"{len(embedding)} dimensões")
            self.log_step("🔢 Primeiros 5 valores", str(embedding[:5]))
            self.log_step("🔢 Últimos 5 valores", str(embedding[-5:]))
            
            # Verifica se é um embedding válido
            assert isinstance(embedding, list), "Embedding deve ser uma lista"
            assert len(embedding) == 1536, f"Embedding deve ter 1536 dimensões, tem {len(embedding)}"
            assert all(isinstance(x, float) for x in embedding), "Todos os valores devem ser float"
            
            # Calcula estatísticas
            import numpy as np
            arr = np.array(embedding)
            self.log_step("📈 Estatísticas do embedding:")
            self.log_step("   📊 Média", f"{arr.mean():.6f}")
            self.log_step("   📊 Desvio padrão", f"{arr.std():.6f}")
            self.log_step("   📊 Valor mínimo", f"{arr.min():.6f}")
            self.log_step("   📊 Valor máximo", f"{arr.max():.6f}")
            self.log_step("   📊 Norma L2", f"{np.linalg.norm(arr):.6f}")
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro na geração de embedding", str(e))
            return False
    
    def test_3_cache_functionality(self):
        """Teste 3: Funcionalidade de cache"""
        self.log_step("TESTE 3: Funcionalidade de cache")
        
        try:
            from agentgraph.services.embedding_service import get_embedding_service
            
            service = get_embedding_service()
            test_text = "SELECT COUNT(*) FROM usuarios WHERE ativo = true"
            
            # Primeira chamada (sem cache)
            self.log_step("🔄 Primeira chamada (sem cache)")
            start_time = time.time()
            embedding1 = service.get_embedding(test_text)
            duration1 = time.time() - start_time
            self.log_step("⏱️ Tempo primeira chamada", f"{duration1:.3f} segundos")
            
            # Segunda chamada (com cache)
            self.log_step("🔄 Segunda chamada (com cache)")
            start_time = time.time()
            embedding2 = service.get_embedding(test_text)
            duration2 = time.time() - start_time
            self.log_step("⏱️ Tempo segunda chamada", f"{duration2:.3f} segundos")
            
            # Verifica se são idênticos
            if embedding1 == embedding2:
                self.log_step("✅ Cache funcionando", "Embeddings idênticos")
            else:
                self.log_step("❌ Cache não funcionando", "Embeddings diferentes")
                return False
            
            # Verifica melhoria de performance
            speedup = duration1 / duration2 if duration2 > 0 else float('inf')
            self.log_step("🚀 Melhoria de performance", f"{speedup:.1f}x mais rápido com cache")
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro no teste de cache", str(e))
            return False
    
    def test_4_similarity_calculation(self):
        """Teste 4: Cálculo de similaridade"""
        self.log_step("TESTE 4: Cálculo de similaridade entre textos")
        
        try:
            from agentgraph.services.embedding_service import get_embedding_service
            
            service = get_embedding_service()
            
            # Textos de teste
            texts = [
                "Quantos clientes temos?",
                "Qual o número total de usuários?",  # Similar ao primeiro
                "Mostre as vendas do mês",           # Diferente
                "SELECT COUNT(*) FROM clientes"      # SQL relacionado ao primeiro
            ]
            
            self.log_step("📝 Textos de teste:", "\n".join([f"   {i+1}. '{text}'" for i, text in enumerate(texts)]))
            
            # Gera embeddings
            embeddings = []
            for i, text in enumerate(texts):
                embedding = service.get_embedding(text)
                embeddings.append(embedding)
                self.log_step(f"✅ Embedding {i+1} gerado", f"{len(embedding)} dimensões")
            
            # Calcula similaridades
            self.log_step("🔍 Matriz de similaridades:")
            for i in range(len(texts)):
                for j in range(i+1, len(texts)):
                    similarity = service.calculate_similarity(embeddings[i], embeddings[j])
                    self.log_step(f"   📊 Texto {i+1} ↔ Texto {j+1}", f"Similaridade: {similarity:.4f}")
                    
                    # Interpreta similaridade
                    if similarity > 0.8:
                        interpretation = "Muito similar"
                    elif similarity > 0.6:
                        interpretation = "Similar"
                    elif similarity > 0.4:
                        interpretation = "Pouco similar"
                    else:
                        interpretation = "Muito diferente"
                    
                    self.log_step(f"      🎯 Interpretação", interpretation)
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro no cálculo de similaridade", str(e))
            return False
    
    def test_5_batch_processing(self):
        """Teste 5: Processamento em lote"""
        self.log_step("TESTE 5: Processamento em lote")
        
        try:
            from agentgraph.services.embedding_service import get_embedding_service
            
            service = get_embedding_service()
            
            # Lista de textos para processar
            batch_texts = [
                "Quantos produtos temos em estoque?",
                "Qual o faturamento total do ano?",
                "Mostre os clientes mais ativos",
                "SELECT * FROM vendas WHERE data > '2024-01-01'",
                "Relatório de performance mensal"
            ]
            
            self.log_step("📝 Processamento em lote", f"{len(batch_texts)} textos")
            for i, text in enumerate(batch_texts):
                self.log_step(f"   {i+1}. '{text}'")
            
            # Processa em lote
            start_time = time.time()
            batch_embeddings = service.get_embeddings_batch(batch_texts, batch_size=3)
            duration = time.time() - start_time
            
            self.log_step("⏱️ Tempo total do lote", f"{duration:.3f} segundos")
            self.log_step("📊 Embeddings gerados", f"{len(batch_embeddings)} embeddings")
            self.log_step("⚡ Velocidade média", f"{duration/len(batch_texts):.3f} segundos por embedding")
            
            # Verifica se todos foram gerados
            assert len(batch_embeddings) == len(batch_texts), "Número de embeddings deve ser igual ao número de textos"
            
            for i, embedding in enumerate(batch_embeddings):
                assert len(embedding) == 1536, f"Embedding {i+1} deve ter 1536 dimensões"
                self.log_step(f"✅ Embedding {i+1} válido", f"{len(embedding)} dimensões")
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro no processamento em lote", str(e))
            return False
    
    def test_6_error_handling(self):
        """Teste 6: Tratamento de erros"""
        self.log_step("TESTE 6: Tratamento de erros")
        
        try:
            from agentgraph.services.embedding_service import get_embedding_service
            
            service = get_embedding_service()
            
            # Teste com texto vazio
            try:
                service.get_embedding("")
                self.log_step("❌ Deveria ter falhado com texto vazio")
                return False
            except ValueError as e:
                self.log_step("✅ Erro tratado corretamente", f"Texto vazio: {e}")
            
            # Teste com texto muito longo (simulação)
            long_text = "A" * 10000  # 10k caracteres
            embedding = service.get_embedding(long_text)
            self.log_step("✅ Texto longo processado", f"Texto de {len(long_text)} chars → embedding de {len(embedding)} dims")
            
            return True
            
        except Exception as e:
            self.log_step("❌ Erro no tratamento de erros", str(e))
            return False
    
    def run_all_tests(self):
        """Executa todos os testes detalhados"""
        logger.info("🚀 INICIANDO TESTES DETALHADOS DO EMBEDDING SERVICE")
        logger.info("=" * 80)
        
        tests = [
            ("Importação e Setup", self.test_1_import_and_setup),
            ("Embedding Único", self.test_2_single_embedding),
            ("Cache", self.test_3_cache_functionality),
            ("Similaridade", self.test_4_similarity_calculation),
            ("Processamento em Lote", self.test_5_batch_processing),
            ("Tratamento de Erros", self.test_6_error_handling)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info("-" * 80)
            logger.info(f"🧪 EXECUTANDO: {test_name}")
            logger.info("-" * 80)
            
            try:
                result = test_func()
                results.append((test_name, result))
                
                if result:
                    logger.info(f"✅ {test_name}: PASSOU")
                else:
                    logger.info(f"❌ {test_name}: FALHOU")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: ERRO CRÍTICO - {e}")
                results.append((test_name, False))
        
        # Relatório final
        logger.info("=" * 80)
        logger.info("📊 RELATÓRIO FINAL - EMBEDDING SERVICE DETALHADO")
        logger.info("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSOU" if result else "❌ FALHOU"
            logger.info(f"{test_name:25} | {status}")
        
        logger.info("-" * 80)
        logger.info(f"TOTAL: {passed}/{total} testes passaram ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 TODOS OS TESTES PASSARAM - EMBEDDING SERVICE FUNCIONANDO PERFEITAMENTE!")
            logger.info("")
            logger.info("🎯 O QUE O EMBEDDING SERVICE FAZ:")
            logger.info("   1. Converte texto em vetores numéricos (1536 dimensões)")
            logger.info("   2. Usa OpenAI API (text-embedding-3-small)")
            logger.info("   3. Cache Redis para performance")
            logger.info("   4. Calcula similaridade semântica entre textos")
            logger.info("   5. Processa em lote para eficiência")
            logger.info("   6. Tratamento robusto de erros")
            logger.info("")
            logger.info("🚀 PRONTO PARA O SISTEMA DE HISTÓRICO!")
        else:
            logger.warning(f"⚠️ {total - passed} testes falharam - verifique os logs acima")
        
        return passed == total

def main():
    """Função principal"""
    tester = EmbeddingServiceDetailedTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
