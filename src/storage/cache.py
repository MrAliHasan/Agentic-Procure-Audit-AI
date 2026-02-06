"""
Query Cache - TTL-based caching for expensive operations
"""
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path

from src.config import settings


class QueryCache:
    """
    Simple file-based cache with TTL for query results.
    Avoids repeated LLM/API calls for identical queries.
    """
    
    def __init__(self, cache_dir: str = None, default_ttl: int = None):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds
        """
        self.cache_dir = Path(cache_dir or "./data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl or settings.cache_ttl_seconds
        
        # In-memory cache for hot data
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}
    
    def _get_cache_key(self, key: str) -> str:
        """Generate a hash-based cache key."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        cache_key = self._get_cache_key(key)
        return self.cache_dir / f"{cache_key}.json"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if datetime.utcnow() < expiry:
                return value
            else:
                del self._memory_cache[key]
        
        # Check file cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(
                    None,
                    lambda: json.loads(cache_path.read_text())
                )
                
                expiry = datetime.fromisoformat(data["expiry"])
                if datetime.utcnow() < expiry:
                    # Also store in memory for faster access
                    self._memory_cache[key] = (data["value"], expiry)
                    return data["value"]
                else:
                    # Expired, delete file
                    cache_path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, ValueError):
                cache_path.unlink(missing_ok=True)
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = None
    ) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: TTL in seconds (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Store in memory
        self._memory_cache[key] = (value, expiry)
        
        # Store on disk
        cache_path = self._get_cache_path(key)
        data = {
            "key": key,
            "value": value,
            "expiry": expiry.isoformat(),
            "created": datetime.utcnow().isoformat()
        }
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: cache_path.write_text(json.dumps(data, default=str))
        )
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        self._memory_cache.pop(key, None)
        
        # Remove from disk
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            return True
        
        return False
    
    async def invalidate(self, pattern: str = None) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Substring to match in keys (invalidates all if None)
            
        Returns:
            Number of entries invalidated
        """
        count = 0
        
        # Memory cache
        if pattern:
            keys_to_delete = [k for k in self._memory_cache if pattern in k]
        else:
            keys_to_delete = list(self._memory_cache.keys())
        
        for key in keys_to_delete:
            del self._memory_cache[key]
            count += 1
        
        # File cache - for simplicity, clear all if pattern matching files
        if pattern is None:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        
        return count
    
    async def get_or_compute(
        self,
        key: str,
        compute_fn,
        ttl: int = None
    ) -> Any:
        """
        Get from cache or compute if not found.
        
        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: TTL in seconds
            
        Returns:
            Cached or computed value
        """
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        value = await compute_fn()
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value
    
    async def stats(self) -> dict:
        """Get cache statistics."""
        memory_count = len(self._memory_cache)
        file_count = len(list(self.cache_dir.glob("*.json")))
        
        return {
            "memory_entries": memory_count,
            "file_entries": file_count,
            "cache_dir": str(self.cache_dir)
        }


# Singleton instance
_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
