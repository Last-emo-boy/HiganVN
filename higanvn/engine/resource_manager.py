"""
Unified Resource Manager for HiganVN.

Integrates:
- Image caching (with LRU eviction)
- Asset preloading
- Audio resource management
- Path resolution

Provides a single point of access for all resource operations.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List, Set
from pathlib import Path
from enum import Enum
import time
import logging

from .image_cache import ImageCache, CacheStats
from .preloader import AssetPreloader, AssetType, LoadProgress

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Resource types."""
    BACKGROUND = "bg"
    CHARACTER = "ch"
    CG = "cg"
    BGM = "bgm"
    SE = "se"
    VOICE = "voice"
    FONT = "fonts"
    CONFIG = "config"


@dataclass
class ResourceStats:
    """Combined resource statistics."""
    # Image cache stats
    images_cached: int = 0
    images_hits: int = 0
    images_misses: int = 0
    images_hit_rate: float = 0.0
    images_bytes: int = 0
    images_limit: int = 0
    
    # Preloader stats
    preload_total: int = 0
    preload_completed: int = 0
    preload_failed: int = 0
    preload_pending: int = 0
    
    # Audio stats
    audio_loaded: int = 0
    
    @property
    def images_usage_mb(self) -> float:
        return self.images_bytes / (1024 * 1024)
    
    @property
    def images_limit_mb(self) -> float:
        return self.images_limit / (1024 * 1024)


class ResourceManager:
    """
    Unified resource manager.
    
    Usage:
        rm = ResourceManager(asset_root="assets")
        
        # Load resources
        bg = rm.load_background("school_day.jpg")
        ch = rm.load_character("alice", "normal")
        
        # Preload for next scene
        rm.preload_scene(["bg/night.jpg", "ch/bob/base.png"])
        
        # Get stats
        stats = rm.get_stats()
    """
    
    def __init__(
        self,
        asset_root: Optional[str] = None,
        image_cache_bytes: int = 256 * 1024 * 1024,  # 256MB
        preload_workers: int = 4,
    ):
        self._asset_root = Path(asset_root) if asset_root else None
        self._lock = threading.RLock()
        
        # Image cache
        self._image_cache = ImageCache(max_bytes=image_cache_bytes)
        
        # Preloader
        self._preloader = AssetPreloader(
            max_workers=preload_workers,
            image_loader=self._load_image_raw,
        )
        
        # Audio tracking
        self._loaded_audio: Set[str] = set()
        
        # Path resolvers for different asset types
        self._resolvers: Dict[ResourceType, Callable[[str], str]] = {}
        
        # Statistics
        self._load_counts: Dict[ResourceType, int] = {t: 0 for t in ResourceType}
    
    def set_asset_root(self, path: str) -> None:
        """Set the asset root directory."""
        self._asset_root = Path(path)
    
    def set_resolver(self, resource_type: ResourceType, resolver: Callable[[str], str]) -> None:
        """Set custom path resolver for a resource type."""
        self._resolvers[resource_type] = resolver
    
    def resolve_path(self, resource_type: ResourceType, name: str) -> str:
        """Resolve resource path."""
        # Use custom resolver if set
        if resource_type in self._resolvers:
            return self._resolvers[resource_type](name)
        
        # Default resolution
        if self._asset_root:
            base = self._asset_root / resource_type.value
            full = base / name
            if full.exists():
                return str(full)
            # Try with common extensions
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".ogg", ".mp3", ".wav"]:
                with_ext = base / (name + ext)
                if with_ext.exists():
                    return str(with_ext)
        
        return name
    
    def _load_image_raw(self, path: str) -> Any:
        """Raw image load (for preloader)."""
        return self._image_cache._default_load(path, "alpha")
    
    # ========================================================================
    # Image Loading
    # ========================================================================
    
    def load_background(self, name: str) -> Any:
        """Load a background image."""
        path = self.resolve_path(ResourceType.BACKGROUND, name)
        with self._lock:
            self._load_counts[ResourceType.BACKGROUND] += 1
        return self._image_cache.load(path)
    
    def load_cg(self, name: str) -> Any:
        """Load a CG image."""
        path = self.resolve_path(ResourceType.CG, name)
        with self._lock:
            self._load_counts[ResourceType.CG] += 1
        return self._image_cache.load(path)
    
    def load_character(self, actor: str, pose: str = "base") -> Any:
        """Load a character sprite."""
        # Try pose file first, then base
        if pose and pose != "base":
            name = f"{actor}/pose_{pose}.png"
        else:
            name = f"{actor}/base.png"
        
        path = self.resolve_path(ResourceType.CHARACTER, name)
        with self._lock:
            self._load_counts[ResourceType.CHARACTER] += 1
        return self._image_cache.load(path)
    
    def load_image(self, path: str, convert: str = "alpha") -> Any:
        """Load any image by path."""
        return self._image_cache.load(path, convert=convert)
    
    # ========================================================================
    # Preloading
    # ========================================================================
    
    def preload(self, resource_type: ResourceType, name: str, priority: int = 0) -> bool:
        """Preload a single resource."""
        path = self.resolve_path(resource_type, name)
        asset_type = self._to_asset_type(resource_type)
        if asset_type:
            return self._preloader.preload(asset_type, path, priority)
        return False
    
    def preload_scene(
        self,
        resources: List[tuple],  # [(ResourceType, name), ...]
        priority: int = 0,
    ) -> int:
        """Preload resources for a scene."""
        count = 0
        for item in resources:
            if len(item) >= 2:
                rtype, name = item[0], item[1]
                if self.preload(rtype, name, priority):
                    count += 1
        return count
    
    def preload_backgrounds(self, names: List[str], priority: int = 0) -> int:
        """Preload multiple backgrounds."""
        return self.preload_scene(
            [(ResourceType.BACKGROUND, n) for n in names],
            priority
        )
    
    def preload_characters(self, actors: List[str], priority: int = 0) -> int:
        """Preload character base sprites."""
        return self.preload_scene(
            [(ResourceType.CHARACTER, f"{a}/base.png") for a in actors],
            priority
        )
    
    def _to_asset_type(self, resource_type: ResourceType) -> Optional[AssetType]:
        """Convert ResourceType to AssetType."""
        mapping = {
            ResourceType.BACKGROUND: AssetType.BACKGROUND,
            ResourceType.CHARACTER: AssetType.CHARACTER,
            ResourceType.CG: AssetType.CG,
            ResourceType.BGM: AssetType.BGM,
            ResourceType.SE: AssetType.SE,
            ResourceType.VOICE: AssetType.VOICE,
        }
        return mapping.get(resource_type)
    
    def get_preload_progress(self) -> LoadProgress:
        """Get preloading progress."""
        return self._preloader.get_progress()
    
    def wait_preload(self, timeout: Optional[float] = None) -> bool:
        """Wait for all preloading to complete."""
        return self._preloader.wait_all(timeout)
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def is_cached(self, resource_type: ResourceType, name: str) -> bool:
        """Check if resource is cached."""
        path = self.resolve_path(resource_type, name)
        return self._image_cache.has(path)
    
    def evict(self, resource_type: ResourceType, name: str) -> bool:
        """Evict resource from cache."""
        path = self.resolve_path(resource_type, name)
        return self._image_cache.evict(path)
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._image_cache.clear()
        self._loaded_audio.clear()
    
    def set_cache_limit(self, bytes_limit: int) -> None:
        """Set image cache memory limit."""
        self._image_cache.set_max_bytes(bytes_limit)
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    def get_stats(self) -> ResourceStats:
        """Get combined resource statistics."""
        cache_stats = self._image_cache.get_stats()
        preload_progress = self._preloader.get_progress()
        
        return ResourceStats(
            images_cached=cache_stats.entries,
            images_hits=cache_stats.hits,
            images_misses=cache_stats.misses,
            images_hit_rate=cache_stats.hit_rate,
            images_bytes=cache_stats.bytes_used,
            images_limit=cache_stats.bytes_limit,
            preload_total=preload_progress.total,
            preload_completed=preload_progress.completed,
            preload_failed=preload_progress.failed,
            preload_pending=preload_progress.in_progress,
            audio_loaded=len(self._loaded_audio),
        )
    
    def get_load_counts(self) -> Dict[str, int]:
        """Get load counts by resource type."""
        with self._lock:
            return {t.value: c for t, c in self._load_counts.items()}
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    def shutdown(self) -> None:
        """Shutdown resource manager."""
        self._preloader.shutdown()
        self._image_cache.clear()


# ============================================================================
# Global singleton
# ============================================================================

_global_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ResourceManager()
    return _global_manager


def init_resource_manager(
    asset_root: Optional[str] = None,
    image_cache_bytes: int = 256 * 1024 * 1024,
) -> ResourceManager:
    """Initialize global resource manager."""
    global _global_manager
    _global_manager = ResourceManager(
        asset_root=asset_root,
        image_cache_bytes=image_cache_bytes,
    )
    return _global_manager
