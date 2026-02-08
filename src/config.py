"""
Sovereign Order Intelligence - Configuration
Centralized configuration using Pydantic Settings
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Sovereign Order Intelligence"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Ollama LLM Configuration
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=800, alias="OLLAMA_TIMEOUT")
    
    # Tavily Web Search
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
    tavily_max_results: int = Field(default=5, alias="TAVILY_MAX_RESULTS")
    
    # Serper.dev Google Search
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    
    # Groq LLM (Fast AI for intelligent search)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    
    # OpenAI LLM (GPT-4o-mini fallback)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    
    # ChromaDB Vector Store
    chroma_persist_dir: str = Field(default="./data/chroma_db", alias="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(default="vendor_intelligence", alias="CHROMA_COLLECTION_NAME")
    
    # Grading Thresholds
    relevance_threshold: float = Field(default=0.7, alias="RELEVANCE_THRESHOLD")
    confidence_threshold: float = Field(default=0.8, alias="CONFIDENCE_THRESHOLD")
    max_web_searches: int = Field(default=5, alias="MAX_WEB_SEARCHES")
    max_context_pages: int = Field(default=5, alias="MAX_CONTEXT_PAGES")  # Limit pages sent to LLM
    
    # Vendor Scoring Weights
    weight_price: float = Field(default=0.30, alias="WEIGHT_PRICE")
    weight_quality: float = Field(default=0.25, alias="WEIGHT_QUALITY")
    weight_reliability: float = Field(default=0.25, alias="WEIGHT_RELIABILITY")
    weight_risk: float = Field(default=0.20, alias="WEIGHT_RISK")
    
    # Document Processing
    max_document_size_mb: int = Field(default=50, alias="MAX_DOCUMENT_SIZE_MB")
    supported_formats: str = Field(default="pdf,png,jpg,jpeg,docx", alias="SUPPORTED_FORMATS")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    
    # Performance
    batch_size: int = Field(default=10, alias="BATCH_SIZE")
    max_concurrent_requests: int = Field(default=5, alias="MAX_CONCURRENT_REQUESTS")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def scoring_weights(self) -> dict:
        """Return vendor scoring weights as a dictionary."""
        return {
            "price": self.weight_price,
            "quality": self.weight_quality,
            "reliability": self.weight_reliability,
            "risk": self.weight_risk
        }
    
    @property
    def supported_formats_list(self) -> list[str]:
        """Return supported document formats as a list."""
        return [f.strip() for f in self.supported_formats.split(",")]
    
    @property
    def chroma_path(self) -> Path:
        """Return ChromaDB path as Path object."""
        path = Path(self.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection helper for FastAPI."""
    return settings
