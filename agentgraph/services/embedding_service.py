"""
Serviço de Embedding para o sistema de histórico
Gera embeddings usando OpenAI API com cache e retry
"""

import os
import json
import time
import logging
import hashlib
from typing import List, Optional, Union
from openai import OpenAI
import redis
from tenacity import retry, stop_after_attempt, wait_exponential

from agentgraph.utils.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Serviço para gerar e gerenciar embeddings"""
    
    def __init__(self, 
                 model: str = "text-embedding-3-small",
                 cache_ttl: int = 3600,
                 redis_url: Optional[str] = None):
        """
        Inicializa o serviço de embedding
        
        Args:
            model: Modelo OpenAI para embeddings
            cache_ttl: TTL do cache em segundos
            redis_url: URL do Redis para cache
        """
        self.model = model
        self.cache_ttl = cache_ttl
        
        # Cliente OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Cache Redis (opcional)
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("✅ Cache Redis conectado para embeddings")
            except Exception as e:
                logger.warning(f"⚠️ Falha ao conectar Redis: {e}")
                self.redis_client = None
    
    def _generate_cache_key(self, text: str) -> str:
        """Gera chave de cache baseada no texto e modelo"""
        content = f"{self.model}:{text}"
        return f"embedding:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """Recupera embedding do cache"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, embedding: List[float]) -> None:
        """Salva embedding no cache"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(embedding)
            )
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _call_openai_api(self, text: str) -> List[float]:
        """Chama API OpenAI com retry automático"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Embedding gerado: {len(embedding)} dimensões")
            return embedding
            
        except Exception as e:
            logger.error(f"Erro na API OpenAI: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um texto
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            Lista de floats representando o embedding
        """
        if not text or not text.strip():
            raise ValueError("Texto não pode estar vazio")
        
        # Limita tamanho do texto (OpenAI tem limite de tokens)
        text = text.strip()[:8000]  # ~8k chars = ~2k tokens
        
        # Verifica cache primeiro
        cache_key = self._generate_cache_key(text)
        cached_embedding = self._get_from_cache(cache_key)
        
        if cached_embedding:
            logger.debug("Cache hit para embedding")
            return cached_embedding
        
        # Gera embedding via API
        start_time = time.time()
        embedding = self._call_openai_api(text)
        duration = time.time() - start_time
        
        logger.info(f"Embedding gerado em {duration:.2f}s")
        
        # Salva no cache
        self._save_to_cache(cache_key, embedding)
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em lotes
        
        Args:
            texts: Lista de textos
            batch_size: Tamanho do lote para API
            
        Returns:
            Lista de embeddings
        """
        if not texts:
            return []
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                try:
                    embedding = self.get_embedding(text)
                    batch_embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Erro ao gerar embedding para texto: {e}")
                    # Embedding zero como fallback
                    batch_embeddings.append([0.0] * 1536)
            
            embeddings.extend(batch_embeddings)
            
            # Rate limiting - pausa entre lotes
            if i + batch_size < len(texts):
                time.sleep(0.1)
        
        logger.info(f"Gerados {len(embeddings)} embeddings em lotes")
        return embeddings
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcula similaridade coseno entre dois embeddings
        
        Args:
            embedding1: Primeiro embedding
            embedding2: Segundo embedding
            
        Returns:
            Similaridade coseno (0-1)
        """
        import numpy as np
        
        # Converte para numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calcula similaridade coseno
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def get_model_info(self) -> dict:
        """Retorna informações sobre o modelo de embedding"""
        return {
            "model": self.model,
            "dimensions": 1536,  # text-embedding-3-small
            "cache_enabled": self.redis_client is not None,
            "cache_ttl": self.cache_ttl
        }

# Instância global do serviço
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Retorna instância singleton do serviço de embedding"""
    global _embedding_service
    
    if _embedding_service is None:
        # Configurações do ambiente
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        cache_ttl = int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        _embedding_service = EmbeddingService(
            model=model,
            cache_ttl=cache_ttl,
            redis_url=redis_url
        )
    
    return _embedding_service

# Funções de conveniência
def generate_embedding(text: str) -> List[float]:
    """Função de conveniência para gerar embedding"""
    service = get_embedding_service()
    return service.get_embedding(text)

def calculate_text_similarity(text1: str, text2: str) -> float:
    """Função de conveniência para calcular similaridade entre textos"""
    service = get_embedding_service()
    embedding1 = service.get_embedding(text1)
    embedding2 = service.get_embedding(text2)
    return service.calculate_similarity(embedding1, embedding2)
