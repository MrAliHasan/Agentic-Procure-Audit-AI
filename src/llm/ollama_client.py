"""
Ollama Client - Async wrapper for local LLM inference
With OpenRouter fallback when Ollama is unavailable
"""
import asyncio
import json as json_module
import httpx
from typing import Optional, AsyncIterator
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings


class OllamaClient:
    """Async client for Ollama local LLM inference with OpenRouter fallback."""
    
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
        self._openrouter_client: Optional[httpx.AsyncClient] = None
        self._use_openrouter: bool = False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    async def _get_openrouter_client(self) -> httpx.AsyncClient:
        """Get or create OpenRouter async HTTP client."""
        if self._openrouter_client is None or self._openrouter_client.is_closed:
            self._openrouter_client = httpx.AsyncClient(
                base_url="https://openrouter.ai/api/v1",
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/MrAliHasan/Agentic-Procure-Audit-AI",
                    "X-Title": "Agentic Procure-Audit AI"
                }
            )
        return self._openrouter_client
    
    async def _openrouter_generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Generate using OpenRouter (OpenAI-compatible API)."""
        client = await self._get_openrouter_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # DeepSeek-R1 wraps reasoning in <think>...</think> tags — strip them
        if "<think>" in content:
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        return content
    
    async def _openrouter_chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Chat using OpenRouter (OpenAI-compatible API)."""
        client = await self._get_openrouter_client()
        
        payload = {
            "model": settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Strip DeepSeek-R1 thinking tags
        if "<think>" in content:
            import re
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        return content
    
    async def close(self):
        """Close the HTTP clients."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        if self._openrouter_client and not self._openrouter_client.is_closed:
            await self._openrouter_client.aclose()
            self._openrouter_client = None
    
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
        Generate a completion from the LLM.
        Tries Ollama first, falls back to OpenRouter if unavailable.
        """
        # Try Ollama first
        if not self._use_openrouter:
            try:
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
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
                # Ollama not available — try OpenRouter
                if settings.openrouter_api_key:
                    print(f"[LLM] Ollama unavailable, falling back to OpenRouter ({settings.openrouter_model})")
                    self._use_openrouter = True
                else:
                    raise
        
        # OpenRouter fallback
        if self._use_openrouter and settings.openrouter_api_key:
            return await self._openrouter_generate(prompt, system, temperature, max_tokens)
        
        raise Exception("No LLM provider available (Ollama offline, no OpenRouter key)")
    
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
        Tries Ollama first, falls back to OpenRouter if unavailable.
        """
        # Try Ollama first
        if not self._use_openrouter:
            try:
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
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
                if settings.openrouter_api_key:
                    print(f"[LLM] Ollama unavailable, falling back to OpenRouter ({settings.openrouter_model})")
                    self._use_openrouter = True
                else:
                    raise
        
        # OpenRouter fallback
        if self._use_openrouter and settings.openrouter_api_key:
            return await self._openrouter_chat(messages, temperature, max_tokens)
        
        raise Exception("No LLM provider available (Ollama offline, no OpenRouter key)")
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        Stream generation token by token.
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
                    data = json_module.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    async def embed(self, text: str) -> list[float]:
        """Generate embeddings for text (if model supports it)."""
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
        """Check if Ollama server is running and model is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            model_base = self.model.split(":")[0]
            return any(model_base in m for m in models)
        except Exception:
            # Check if OpenRouter is available as fallback
            if settings.openrouter_api_key:
                self._use_openrouter = True
                return True
            return False
    
    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            if settings.openrouter_api_key:
                return [f"openrouter:{settings.openrouter_model}"]
            return []


# Convenience function for simple queries
async def query_llm(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """Simple function to query the LLM (Ollama or OpenRouter fallback)."""
    client = OllamaClient()
    try:
        return await client.generate(prompt, system, temperature)
    finally:
        await client.close()
