
import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings

logger = logging.getLogger(__name__)

class OpenAIEmbedder:

    def __init__(self):
        
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries
        )
        self.model = settings.openai_embedding_model
        
        # Rate limiter (token bucket)
        self.rate_limit = settings.embedding_rate_limit
        self.rate_period = settings.embedding_rate_period
        self.semaphore = asyncio.Semaphore(self.rate_limit)
        self.last_request_time = 0
        
        # Redis cache
        try:
            self.cache = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=False
            )
            self.cache.ping()
            self.cache_enabled = True
            logger.info("Redis cache enabled for embeddings")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            self.cache_enabled = False
    
    async def embed_text(self, text: str) -> List[float]:
        
        embeddings = await self.embed_batch([text])
        return embeddings[0]
    
    async def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[List[float]]:
        
        if not texts:
            return []
        
        embeddings = []
        texts_to_embed = []
        cache_keys = []
        indices_to_embed = []
        
        # Check cache
        if use_cache and self.cache_enabled:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                cache_keys.append(cache_key)
                
                cached = self._get_from_cache(cache_key)
                if cached is not None:
                    embeddings.append(cached)
                else:
                    embeddings.append(None)
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
        else:
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Generate embeddings for cache misses
        if texts_to_embed:
            logger.info(f"Generating embeddings for {len(texts_to_embed)} texts (cache hits: {len(texts) - len(texts_to_embed)})")
            
            new_embeddings = await self._generate_embeddings(texts_to_embed)
            
            # Store in cache and update results
            for i, embedding in zip(indices_to_embed, new_embeddings):
                embeddings[i] = embedding
                if use_cache and self.cache_enabled:
                    self._store_in_cache(cache_keys[i], embedding)
        
        return embeddings
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        
        # Rate limiting
        async with self.semaphore:
            # Ensure minimum time between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < (1.0 / self.rate_limit):
                await asyncio.sleep((1.0 / self.rate_limit) - time_since_last)
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    encoding_format="float"
                )
                
                self.last_request_time = time.time()
                
                # Extract embeddings in order
                embeddings = [item.embedding for item in response.data]
                
                logger.debug(f"Generated {len(embeddings)} embeddings")
                return embeddings
                
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise
    
    def _get_cache_key(self, text: str) -> str:
        
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.model}:{text_hash}"
    
    def _get_from_cache(self, key: str) -> Optional[List[float]]:
        
        try:
            cached = self.cache.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None
    
    def _store_in_cache(self, key: str, embedding: List[float]) -> None:
        
        try:
            self.cache.setex(
                key,
                settings.cache_ttl,
                json.dumps(embedding)
            )
        except Exception as e:
            logger.debug(f"Cache write error: {e}")
    
    async def embed_documents(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "content"
    ) -> List[Dict[str, Any]]:
        
        texts = [doc[text_field] for doc in documents]
        embeddings = await self.embed_batch(texts)
        
        for doc, embedding in zip(documents, embeddings):
            doc["vector"] = embedding
        
        return documents

# Global embedder instance
openai_embedder = OpenAIEmbedder()


# Synchronous wrapper for tests
class OpenAIEmbedder:
    """Synchronous wrapper for OpenAI embeddings (for tests)"""
    
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries
        )
        self.model = settings.openai_embedding_model
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        Returns list of embedding vectors.
        """
        if not texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
