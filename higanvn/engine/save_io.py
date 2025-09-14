from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Tuple

import pygame
_META_CACHE: Dict[Path, Dict[int, Tuple[float, Optional[dict]]]] = {}



def slot_thumb_path(slot: int, *, get_save_dir) -> Path:
    base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
    base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
    return base / f"slot_{int(slot):02d}.png"


def slot_meta_path(slot: int, *, get_save_dir) -> Path:
    base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
    base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
    return base / f"slot_{int(slot):02d}.json"


def slot_json_path(slot: int, *, get_save_dir) -> Path:
    """Return path of the main slot JSON payload written by the Engine.

    This can be used as a fallback to obtain ts/label when separate meta files
    are not present (e.g., after centralizing metadata in engine saves).
    """
    return slot_meta_path(slot, get_save_dir=get_save_dir)


def read_slot_meta(slot: int, *, get_save_dir) -> Optional[dict]:
    # normalize base dir key
    base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
    base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
    p = slot_meta_path(slot, get_save_dir=lambda: base)
    try:
        import json, os
        # init cache bucket
        bucket = _META_CACHE.setdefault(base, {})
        # handle delete case: file missing -> drop cache and return None
        if not p.exists():
            if slot in bucket:
                try:
                    del bucket[slot]
                except Exception:
                    pass
            # Fallback to main JSON (same path here) no longer exists either
            return None
        mtime = p.stat().st_mtime
        cached = bucket.get(slot)
        if cached and abs(cached[0] - mtime) < 1e-6:
            return cached[1]
        # read fresh
        data = json.loads(p.read_text(encoding="utf-8"))
        meta = {"ts": data.get("ts"), "label": data.get("label")}
        # store to cache
        bucket[slot] = (mtime, meta)
        return meta
    except Exception:
        return None


def invalidate_slot_cache(*, get_save_dir, slot: int) -> None:
    """Invalidate cached meta for a given slot under the provided save dir."""
    try:
        base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
        base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
        bucket = _META_CACHE.get(base)
        if bucket and slot in bucket:
            del bucket[slot]
    except Exception:
        pass


def list_slot_metas(*, get_save_dir) -> dict[int, dict]:
    """Return a dictionary of slot->meta using cached mtimes.

    Only reads files whose mtime changed since last call for the same save_dir.
    """
    result: dict[int, dict] = {}
    try:
        import json
        base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
        base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
        bucket = _META_CACHE.setdefault(base, {})
        # scan files
        for p in base.glob("slot_*.json"):
            try:
                stem = p.stem  # slot_XX
                n = int(stem.split("_")[1])
            except Exception:
                continue
            try:
                mt = p.stat().st_mtime
            except Exception:
                continue
            cached = bucket.get(n)
            if not cached or abs(cached[0] - mt) >= 1e-6:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    meta = {"ts": data.get("ts"), "label": data.get("label")}
                except Exception:
                    meta = None
                bucket[n] = (mt, meta)
            # collect if has meta
            meta = bucket.get(n, (0.0, None))[1]
            if isinstance(meta, dict) and (meta.get("ts") or meta.get("label")):
                result[n] = meta
        # prune cache entries for non-existing files
        existing = {int(p.stem.split("_")[1]) for p in base.glob("slot_*.json") if p.stem.split("_")[1].isdigit()}
        for k in list(bucket.keys()):
            if k not in existing:
                try:
                    del bucket[k]
                except Exception:
                    pass
    except Exception:
        return {}
    return result


def capture_thumbnail(src_surface: pygame.Surface, slot: int, *, get_save_dir) -> None:
    thumb_path = slot_thumb_path(slot, get_save_dir=get_save_dir)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 384, 216
    surf = pygame.transform.smoothscale(src_surface, (w, h))
    pygame.image.save(surf, str(thumb_path))
