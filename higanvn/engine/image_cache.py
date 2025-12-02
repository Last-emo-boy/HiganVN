"""
Enhanced Image Cache with LRU eviction and memory limits.

Features:
- LRU (Least Recently Used) eviction policy
- Configurable memory limit
- Hit/miss statistics
- Thread-safe operations
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Callable
import time

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    surface: Any  # pygame.Surface or similar
    path: str
    width: int = 0
    height: int = 0
    bytes_estimate: int = 0
    load_time: float = 0.0
    last_access: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class CacheStats:
    """Cache statistics."""
    entries: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    bytes_used: int = 0
    bytes_limit: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def usage_percent(self) -> float:
        return (self.bytes_used / self.bytes_limit * 100) if self.bytes_limit > 0 else 0.0


class ImageCache:
    """
    LRU Image Cache with memory management.
    
    Usage:
        cache = ImageCache(max_bytes=256 * 1024 * 1024)  # 256MB limit
        
        # Load image (auto-caches)
        surf = cache.load("path/to/image.png")
        
        # Check if cached
        if cache.has("path/to/image.png"):
            ...
        
        # Get stats
        stats = cache.get_stats()
        print(f"Hit rate: {stats.hit_rate:.1%}")
    """
    
    # Default: 256MB
    DEFAULT_MAX_BYTES = 256 * 1024 * 1024
    
    def __init__(
        self,
        max_bytes: int = DEFAULT_MAX_BYTES,
        convert_mode: str = "alpha",
    ):
        self._max_bytes = max_bytes
        self._convert_mode = convert_mode
        
        # OrderedDict for LRU ordering (most recent at end)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._bytes_used = 0
        
        # Recent loads (for debugging)
        self._recent_loads: list[str] = []
        self._recent_max = 20
    
    def load(
        self,
        path: str,
        *,
        convert: Optional[str] = None,
        loader: Optional[Callable[[str], Any]] = None,
    ) -> Any:
        """Load image from cache or disk."""
        convert = convert or self._convert_mode
        
        with self._lock:
            # Check cache
            entry = self._cache.get(path)
            if entry is not None:
                self._hits += 1
                entry.last_access = time.time()
                entry.access_count += 1
                # Move to end (most recently used)
                self._cache.move_to_end(path)
                return entry.surface
        
        # Cache miss - load from disk
        start_time = time.time()
        
        if loader:
            surf = loader(path)
        else:
            surf = self._default_load(path, convert)
        
        load_time = time.time() - start_time
        
        # Calculate size
        try:
            w, h = surf.get_size()
            bytes_est = w * h * 4
        except Exception:
            w, h, bytes_est = 0, 0, 1024
        
        entry = CacheEntry(
            surface=surf,
            path=path,
            width=w,
            height=h,
            bytes_estimate=bytes_est,
            load_time=load_time,
        )
        
        with self._lock:
            self._misses += 1
            self._evict_if_needed(bytes_est)
            self._cache[path] = entry
            self._bytes_used += bytes_est
            self._record_recent(path)
        
        return surf
    
    def _default_load(self, path: str, convert: str) -> Any:
        """Default pygame image loader."""
        if not HAS_PYGAME:
            raise RuntimeError("pygame not available")
        
        raw = pygame.image.load(path)
        
        if convert == "alpha":
            return raw.convert_alpha()
        elif convert == "opaque":
            return raw.convert()
        else:
            return raw
    
    def _evict_if_needed(self, needed_bytes: int) -> None:
        """Evict LRU entries until we have enough space."""
        while self._bytes_used + needed_bytes > self._max_bytes and self._cache:
            oldest_path, oldest_entry = self._cache.popitem(last=False)
            self._bytes_used -= oldest_entry.bytes_estimate
            self._evictions += 1
    
    def _record_recent(self, path: str) -> None:
        """Record recent loads for debugging."""
        self._recent_loads.append(path)
        if len(self._recent_loads) > self._recent_max:
            del self._recent_loads[0]
    
    def has(self, path: str) -> bool:
        """Check if path is cached."""
        with self._lock:
            return path in self._cache
    
    def get(self, path: str) -> Optional[Any]:
        """Get cached surface without loading."""
        with self._lock:
            entry = self._cache.get(path)
            if entry:
                entry.last_access = time.time()
                entry.access_count += 1
                self._cache.move_to_end(path)
                return entry.surface
            return None
    
    def evict(self, path: str) -> bool:
        """Manually evict a path from cache."""
        with self._lock:
            entry = self._cache.pop(path, None)
            if entry:
                self._bytes_used -= entry.bytes_estimate
                self._evictions += 1
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._bytes_used = 0
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._recent_loads.clear()
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                entries=len(self._cache),
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                bytes_used=self._bytes_used,
                bytes_limit=self._max_bytes,
            )
    
    def set_max_bytes(self, max_bytes: int) -> None:
        """Update memory limit (may trigger evictions)."""
        with self._lock:
            self._max_bytes = max_bytes
            self._evict_if_needed(0)
    
    @property
    def max_bytes(self) -> int:
        return self._max_bytes
    
    @property
    def bytes_used(self) -> int:
        with self._lock:
            return self._bytes_used


# ============================================================================
# Global singleton for backwards compatibility
# ============================================================================

_global_cache: Optional[ImageCache] = None


def get_cache() -> ImageCache:
    """Get global image cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ImageCache()
    return _global_cache


# Legacy API functions (for backwards compatibility)
def load_image(path: str, *, convert: str = "alpha") -> Any:
    """Legacy: Load image through global cache."""
    return get_cache().load(path, convert=convert)


def get_stats() -> dict:
    """Legacy: Get stats as dict."""
    stats = get_cache().get_stats()
    cache = get_cache()
    return {
        "images": {
            "cached": stats.entries,
            "hits": stats.hits,
            "misses": stats.misses,
            "hit_rate": stats.hit_rate,
            "bytes": stats.bytes_used,
            "recent": list(cache._recent_loads),
        }
    }


def clear() -> None:
    """Legacy: Clear global cache."""
    get_cache().clear()

