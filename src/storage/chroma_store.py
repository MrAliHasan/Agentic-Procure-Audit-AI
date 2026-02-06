"""
ChromaDB Vector Store - Local persistent vector database
"""
import asyncio
from typing import Optional, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.llm.embeddings import LocalEmbeddings, get_embeddings


class VectorStore:
    """
    ChromaDB-based vector store for semantic search.
    Persists data locally for AI sovereignty.
    """
    
    COLLECTIONS = {
        "vendors": "vendor_intelligence",
        "documents": "document_store", 
        "market_intel": "market_intelligence"
    }
    
    def __init__(self, persist_dir: str = None):
        """
        Initialize the vector store.
        
        Args:
            persist_dir: Directory for persistent storage
        """
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        self._client: Optional[chromadb.PersistentClient] = None
        self._embeddings = get_embeddings()
        self._collections: dict = {}
    
    def _get_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return self._client
    
    def _get_collection(self, name: str) -> chromadb.Collection:
        """Get or create a collection."""
        if name not in self._collections:
            client = self._get_client()
            collection_name = self.COLLECTIONS.get(name, name)
            self._collections[name] = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]
    
    async def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict] = None,
        ids: list[str] = None,
        collection: str = "vendors"
    ) -> list[str]:
        """
        Add documents to the vector store.
        
        Args:
            texts: Document texts to embed and store
            metadatas: Optional metadata for each document
            ids: Optional IDs (generated if not provided)
            collection: Which collection to add to
            
        Returns:
            List of document IDs
        """
        if not texts:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [f"{collection}_{uuid.uuid4().hex[:8]}" for _ in texts]
        
        # Generate embeddings
        embeddings = await self._embeddings.aembed_documents(texts)
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        # Add text to metadata for retrieval
        for i, meta in enumerate(metadatas):
            meta["text"] = texts[i]
        
        # Add to collection
        coll = self._get_collection(collection)
        
        # Run in executor since chromadb is sync
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: coll.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
        )
        
        return ids
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        collection: str = "vendors",
        filter_metadata: dict = None
    ) -> list[dict]:
        """
        Search for similar documents.
        
        Args:
            query: Query text
            k: Number of results to return
            collection: Which collection to search
            filter_metadata: Optional metadata filters
            
        Returns:
            List of results with text, metadata, and score
        """
        # Generate query embedding
        query_embedding = await self._embeddings.aembed_query(query)
        
        coll = self._get_collection(collection)
        
        # Build query kwargs
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": k,
            "include": ["documents", "metadatas", "distances"]
        }
        
        if filter_metadata:
            query_kwargs["where"] = filter_metadata
        
        # Run query
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: coll.query(**query_kwargs)
        )
        
        # Format results
        formatted = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity (cosine distance to similarity)
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # For cosine distance
                
                formatted.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": similarity
                })
        
        return formatted
    
    async def get_by_id(
        self,
        doc_id: str,
        collection: str = "vendors"
    ) -> Optional[dict]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID
            collection: Collection to search
            
        Returns:
            Document dict or None
        """
        coll = self._get_collection(collection)
        
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: coll.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
        )
        
        if results and results["ids"]:
            return {
                "id": results["ids"][0],
                "text": results["documents"][0] if results["documents"] else "",
                "metadata": results["metadatas"][0] if results["metadatas"] else {}
            }
        
        return None
    
    async def delete(
        self,
        ids: list[str],
        collection: str = "vendors"
    ) -> bool:
        """
        Delete documents by ID.
        
        Args:
            ids: Document IDs to delete
            collection: Collection to delete from
            
        Returns:
            True if successful
        """
        coll = self._get_collection(collection)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: coll.delete(ids=ids)
        )
        
        return True
    
    async def update(
        self,
        doc_id: str,
        text: str = None,
        metadata: dict = None,
        collection: str = "vendors"
    ) -> bool:
        """
        Update a document.
        
        Args:
            doc_id: Document ID
            text: New text (re-embeds if provided)
            metadata: New metadata
            collection: Collection
            
        Returns:
            True if successful
        """
        coll = self._get_collection(collection)
        
        update_kwargs = {"ids": [doc_id]}
        
        if text:
            embedding = await self._embeddings.aembed_query(text)
            update_kwargs["embeddings"] = [embedding]
            update_kwargs["documents"] = [text]
        
        if metadata:
            update_kwargs["metadatas"] = [metadata]
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: coll.update(**update_kwargs)
        )
        
        return True
    
    async def get_stats(self) -> dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dict with collection stats
        """
        client = self._get_client()
        collections = client.list_collections()
        
        stats = {}
        for coll in collections:
            stats[coll.name] = {
                "count": coll.count()
            }
        
        return stats
    
    async def reset(self, collection: str = None):
        """
        Reset (delete all data from) a collection or all collections.
        
        Args:
            collection: Specific collection to reset, or None for all
        """
        client = self._get_client()
        
        if collection:
            coll_name = self.COLLECTIONS.get(collection, collection)
            try:
                client.delete_collection(coll_name)
            except ValueError:
                pass  # Collection doesn't exist
            self._collections.pop(collection, None)
        else:
            # Reset all
            client.reset()
            self._collections.clear()


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
