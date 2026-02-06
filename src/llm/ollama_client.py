"""
Ollama Client - Async wrapper for local LLM inference
"""
import asyncio
import httpx
from typing import Optional, AsyncIterator
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings


class OllamaClient:
    """Async client for Ollama local LLM inference."""
    
    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate a completion from the local LLM.
        
        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", "")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Chat completion with message history.
        
        Args:
            messages: List of {"role": "user|assistant|system", "content": "..."}
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Assistant's response text
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("message", {}).get("content", "")
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        Stream generation token by token.
        
        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Sampling temperature
            
        Yields:
            Generated tokens one at a time
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature}
        }
        
        if system:
            payload["system"] = system
        
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    async def embed(self, text: str) -> list[float]:
        """
        Generate embeddings for text (if model supports it).
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        response = await client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("embedding", [])
    
    async def health_check(self) -> bool:
        """
        Check if Ollama server is running and model is available.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            # Check if our model is available
            model_base = self.model.split(":")[0]
            return any(model_base in m for m in models)
        except Exception:
            return False
    
    async def list_models(self) -> list[str]:
        """
        List available models on the Ollama server.
        
        Returns:
            List of model names
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []


# Convenience function for simple queries
async def query_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Simple function to query the local LLM.
    
    Args:
        prompt: User prompt
        system: Optional system prompt
        temperature: Sampling temperature
        
    Returns:
        LLM response text
    """
    client = OllamaClient()
    try:
        return await client.generate(prompt, system, temperature)
    finally:
        await client.close()
