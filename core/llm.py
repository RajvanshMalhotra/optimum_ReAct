"""Optimized LLM client with caching and parallel requests."""
import asyncio
import hashlib
from typing import List, Dict, Optional
from functools import lru_cache
import httpx
from config import (
    GROQ_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT
)


class ResponseCache:
    """Simple in-memory cache for LLM responses."""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, str] = {}
        self.max_size = max_size
        
    def _hash(self, messages: List[Dict]) -> str:
        """Create hash of messages for caching."""
        content = str(messages)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, messages: List[Dict]) -> Optional[str]:
        """Get cached response."""
        key = self._hash(messages)
        return self.cache.get(key)
    
    def set(self, messages: List[Dict], response: str):
        """Cache response with LRU eviction."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            self.cache.pop(next(iter(self.cache)))
        
        key = self._hash(messages)
        self.cache[key] = response


class LLMClient:
    """Optimized LLM client with caching and batching."""
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL
        self.cache = ResponseCache()
        self._client = None
        
    async def _get_client(self):
        """Get persistent HTTP client for connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=LLM_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
        
    async def chat(
        self, 
        messages: List[Dict], 
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = LLM_TEMPERATURE,
        use_cache: bool = True
    ) -> str:
        """Call LLM with caching."""
        
        # Check cache first
        if use_cache:
            cached = self.cache.get(messages)
            if cached:
                return cached
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            
            if response.status_code == 429:
                await asyncio.sleep(2)  # Reduced from 5s
                return await self.chat(messages, max_tokens, temperature, use_cache)
            
            if response.status_code != 200:
                return f"ERROR: API {response.status_code}"
            
            data = response.json()
            result = data["choices"][0]["message"]["content"].strip()
            
            # Cache successful response
            if use_cache:
                self.cache.set(messages, result)
            
            return result
                
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    async def batch_chat(self, prompts: List[str], max_tokens: int = 500) -> List[str]:
        """Execute multiple prompts in parallel."""
        tasks = [
            self.chat([{"role": "user", "content": p}], max_tokens)
            for p in prompts
        ]
        return await asyncio.gather(*tasks)
    
    async def simple_prompt(self, prompt: str, max_tokens: int = LLM_MAX_TOKENS) -> str:
        """Simple single prompt call."""
        return await self.chat([{"role": "user", "content": prompt}], max_tokens)
    
    async def close(self):
        """Close persistent client."""
        if self._client:
            await self._client.aclose()


# Global instance
llm_client = LLMClient()
