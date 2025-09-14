from __future__ import annotations

from typing import Dict, Tuple, Optional
import pygame

# Simple global image cache with basic stats
_cache: Dict[str, pygame.Surface] = {}
_meta: Dict[str, Tuple[int,int,int]] = {}  # path -> (w, h, bytes)
_hits = 0
_misses = 0
_recent: list[str] = []  # most recent loaded paths (misses only)
_RECENT_MAX = 20


def load_image(path: str, *, convert: str = "alpha") -> pygame.Surface:
    global _hits, _misses
    surf = _cache.get(path)
    if surf is not None:
        _hits += 1
        return surf
    try:
        raw = pygame.image.load(path)
        if convert == "alpha":
            surf = raw.convert_alpha()
        elif convert == "opaque":
            surf = raw.convert()
        else:
            surf = raw
    except Exception:
        # Let caller handle None by falling back to placeholders
        raise
    _cache[path] = surf
    try:
        w, h = surf.get_size()
        _meta[path] = (w, h, w * h * 4)
    except Exception:
        _meta[path] = (0, 0, 0)
    _record_recent(path)
    _misses += 1
    return surf


def _record_recent(path: str) -> None:
    try:
        _recent.append(path)
        if len(_recent) > _RECENT_MAX:
            del _recent[0: len(_recent) - _RECENT_MAX]
    except Exception:
        pass


def get_stats() -> dict:
    total_bytes = 0
    try:
        total_bytes = sum(b for (_, _, b) in _meta.values())
    except Exception:
        total_bytes = 0
    return {
        "images": {
            "cached": len(_cache),
            "hits": _hits,
            "misses": _misses,
            "hit_rate": (float(_hits) / float(max(1, _hits + _misses))),
            "bytes": total_bytes,
            "recent": list(_recent),
        }
    }


def clear() -> None:
    global _hits, _misses
    _cache.clear()
    _meta.clear()
    _hits = 0
    _misses = 0
    _recent.clear()
