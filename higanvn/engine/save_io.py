from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame


def slot_thumb_path(slot: int, *, get_save_dir) -> Path:
    base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
    base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
    return base / f"slot_{int(slot):02d}.png"


def slot_meta_path(slot: int, *, get_save_dir) -> Path:
    base_obj = get_save_dir() if callable(get_save_dir) else Path("save")
    base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
    return base / f"slot_{int(slot):02d}.json"


def read_slot_meta(slot: int, *, get_save_dir) -> Optional[dict]:
    p = slot_meta_path(slot, get_save_dir=get_save_dir)
    try:
        if p.exists():
            import json
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def capture_thumbnail(src_surface: pygame.Surface, slot: int, *, get_save_dir) -> None:
    thumb_path = slot_thumb_path(slot, get_save_dir=get_save_dir)
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 384, 216
    surf = pygame.transform.smoothscale(src_surface, (w, h))
    pygame.image.save(surf, str(thumb_path))
