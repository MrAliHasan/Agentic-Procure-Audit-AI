"""
Local Embeddings - Using Sentence Transformers for vector embeddings
"""
import asyncio
from typing import Optional
from functools import lru_cache
import numpy as np

from src.config import settings


class LocalEmbeddings:
    """
    Local embedding model using Sentence Transformers.
    Runs entirely on local hardware - no API calls needed.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            model_name: HuggingFace model name. Options:
                - all-MiniLM-L6-v2 (default): Fast, 384 dimensions
                - all-mpnet-base-v2: Higher quality, 768 dimensions
                - paraphrase-MiniLM-L6-v2: Good for paraphrasing
        """
        self.model_name = model_name
        self._model = None
    
    def _load_model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = self._load_model()
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32
        )
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single query.
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector
        """
        if not text:
            return []
        
        model = self._load_model()
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embedding.tolist()
    
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Async wrapper for embed_documents."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_documents, texts)
    
    async def aembed_query(self, text: str) -> list[float]:
        """Async wrapper for embed_query."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_query, text)
    
    @property
    def dimension(self) -> int:
        """Return the embedding dimension for this model."""
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384,
            "all-distilroberta-v1": 768
        }
        return dimensions.get(self.model_name, 384)


# Cached singleton instance
@lru_cache(maxsize=1)
def get_embeddings(model_name: str = "all-MiniLM-L6-v2") -> LocalEmbeddings:
    """
    Get a cached embedding model instance.
    
    Args:
        model_name: Model to use
        
    Returns:
        LocalEmbeddings instance
    """
    return LocalEmbeddings(model_name)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Similarity score between -1 and 1
    """
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def batch_cosine_similarity(query: list[float], documents: list[list[float]]) -> list[float]:
    """
    Calculate cosine similarity between a query and multiple documents.
    
    Args:
        query: Query embedding vector
        documents: List of document embedding vectors
        
    Returns:
        List of similarity scores
    """
    query = np.array(query)
    documents = np.array(documents)
    
    # Normalize
    query_norm = query / np.linalg.norm(query)
    doc_norms = documents / np.linalg.norm(documents, axis=1, keepdims=True)
    
    # Dot product for similarity
    similarities = np.dot(doc_norms, query_norm)
    return similarities.tolist()
