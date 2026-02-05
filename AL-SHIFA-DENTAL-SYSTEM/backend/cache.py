"""
Simple in-memory cache for agent responses to improve performance.
Caches responses for frequently asked questions.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

class ResponseCache:
    def __init__(self, ttl_minutes: int = 30, max_size: int = 100):
        """
        Args:
            ttl_minutes: Time-to-live for cached responses in minutes
            max_size: Maximum number of cached items
        """
        self.cache: Dict[str, tuple[str, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
    
    def _get_key(self, query: str, user_id: int) -> str:
        """Generate cache key from query and user"""
        combined = f"{user_id}:{query.lower().strip()}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, query: str, user_id: int) -> Optional[str]:
        """Retrieve cached response if available and valid"""
        key = self._get_key(query, user_id)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            
            # Check if expired
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, query: str, user_id: int, response: str):
        """Cache a response"""
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
            del self.cache[oldest_key]
        
        key = self._get_key(query, user_id)
        self.cache[key] = (response, datetime.now())
    
    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_minutes": self.ttl.total_seconds() / 60
        }

# Global cache instance
response_cache = ResponseCache(ttl_minutes=30, max_size=100)
