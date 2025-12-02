from __future__ import annotations

import pygame
from pygame import Surface
from typing import Dict, Tuple

# Cache for scaled surfaces: (id(surf), target_h) -> scaled_surface
_scale_cache: Dict[Tuple[int, int], Surface] = {}
_SCALE_CACHE_MAX = 64  # Limit cache size to avoid memory bloat


def scale_to_height(surf: Surface, target_h: int) -> Surface:
    """Scale a surface to a target height, maintaining aspect ratio.
    
    Uses an internal cache to avoid repeated smoothscale operations for the
    same surface and target height combination.
    """
    if not isinstance(surf, Surface):
        return surf
    w, h = surf.get_size()
    if h <= 0:
        return surf
    # Fast path: no scaling needed
    if h == target_h:
        return surf
    # Check cache
    cache_key = (id(surf), target_h)
    cached = _scale_cache.get(cache_key)
    if cached is not None:
        return cached
    # Perform scaling
    ratio = float(target_h) / float(h)
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(target_h))
    scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
    # Store in cache with simple LRU-like eviction
    if len(_scale_cache) >= _SCALE_CACHE_MAX:
        # Remove oldest entry (first key)
        try:
            oldest = next(iter(_scale_cache))
            del _scale_cache[oldest]
        except (StopIteration, KeyError):
            pass
    _scale_cache[cache_key] = scaled
    return scaled


def clear_scale_cache() -> None:
    """Clear the scale cache. Call when assets are reloaded."""
    _scale_cache.clear()
