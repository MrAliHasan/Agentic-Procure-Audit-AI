"""
Base Agent - Foundation for all specialized agents
"""
from abc import ABC, abstractmethod
from typing import Optional, Any

from src.llm.ollama_client import OllamaClient


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides common functionality:
    - LLM client management
    - Prompt formatting
    - Error handling
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        temperature: float = 0.7
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent name for logging/identification
            system_prompt: System prompt defining agent behavior
            temperature: LLM temperature (0.0-1.0)
        """
        self.name = name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self._client: Optional[OllamaClient] = None
    
    async def _get_client(self) -> OllamaClient:
        """Get or create LLM client."""
        if self._client is None:
            self._client = OllamaClient()
        return self._client
    
    async def close(self):
        """Close the LLM client."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def think(self, prompt: str) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt: User/task prompt
            
        Returns:
            LLM response
        """
        client = await self._get_client()
        return await client.generate(
            prompt,
            system=self.system_prompt,
            temperature=self.temperature
        )
    
    async def chat(self, messages: list[dict]) -> str:
        """
        Multi-turn chat with context.
        
        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            
        Returns:
            Assistant response
        """
        client = await self._get_client()
        
        # Prepend system message if not present
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        return await client.chat(messages, temperature=self.temperature)
    
    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """
        Execute the agent's main task.
        
        Args:
            input_data: Task-specific input
            
        Returns:
            Task-specific output
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
