"""
Simple in-memory cache for Copilot responses.
Reduces latency for repeated queries.
"""

import hashlib
import time
from typing import Dict, Any, Optional
from collections import OrderedDict


class ResponseCache:
    """LRU cache for Copilot responses with TTL."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time to live for cached items (default 1 hour)
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _hash_key(self, message: str, model: Optional[str] = None) -> str:
        """Generate cache key from message and model."""
        key_str = f"{message.lower().strip()}|{model or 'default'}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, message: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response.
        
        Args:
            message: User message
            model: Model ID
            
        Returns:
            Cached response or None if not found/expired
        """
        key = self._hash_key(message, model)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check TTL
        if time.time() - entry['timestamp'] > self.ttl_seconds:
            # Expired, remove from cache
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        
        return entry['response']
    
    def set(self, message: str, response: Dict[str, Any], model: Optional[str] = None):
        """
        Cache a response.
        
        Args:
            message: User message
            response: Agent response
            model: Model ID
        """
        key = self._hash_key(message, model)
        
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)
        
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Move to end
        self.cache.move_to_end(key)
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'ttl_seconds': self.ttl_seconds
        }


# Global cache instance
_global_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache(max_size=100, ttl_seconds=3600)
    return _global_cache
