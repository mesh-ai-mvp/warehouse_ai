"""
Cache Manager for Warehouse API

Implements in-memory caching with TTL for performance optimization
"""

from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """Simple in-memory cache with TTL support"""

    def __init__(self, default_ttl_seconds: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds

    def _generate_key(self, prefix: str, params: Any) -> str:
        """Generate cache key from prefix and parameters"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_digest = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_digest}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires_at"]:
                logger.debug(f"Cache hit for key: {key}")
                return entry["value"]
            else:
                # Remove expired entry
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.now() + timedelta(seconds=ttl),
            "created_at": datetime.now(),
        }
        logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries matching pattern or all if no pattern"""
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared entire cache ({count} entries)")
            return count

        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]

        logger.info(
            f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'"
        )
        return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        valid_entries = sum(
            1 for entry in self.cache.values() if now < entry["expires_at"]
        )
        expired_entries = len(self.cache) - valid_entries

        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "memory_keys": list(self.cache.keys())[:10],  # Show first 10 keys
        }


# Global cache instance
warehouse_cache = CacheManager(default_ttl_seconds=30)
