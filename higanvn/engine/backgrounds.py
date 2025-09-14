from __future__ import annotations

from typing import Optional
from pathlib import Path
import pygame

from higanvn.engine.placeholders import make_bg_placeholder
from higanvn.engine.image_cache import load_image
from higanvn.engine.gallery_io import unlock as gallery_unlock


def _logical_size(renderer) -> tuple[int, int]:
    try:
        return renderer.canvas.get_size()
    except Exception:
        return (1280, 720)


def set_background(renderer, path: Optional[str]) -> None:
    """Set or clear background using renderer's asset resolver and fonts for placeholders."""
    size = _logical_size(renderer)
    if path:
        try:
            resolved = renderer._resolve_asset(path, ["bg"])  # prefer assets/<ns>/bg then assets/bg
            img = load_image(resolved, convert="opaque")
            renderer.bg = pygame.transform.smoothscale(img, size)
        except Exception:
            renderer.bg = make_bg_placeholder(size, renderer.font, getattr(renderer, "_ph_bg_color", (40,40,40)), getattr(renderer, "_ph_fg_color", (180,180,180)), f"BG missing: {path}")
    else:
        renderer.bg = make_bg_placeholder(size, renderer.font, getattr(renderer, "_ph_bg_color", (40,40,40)), getattr(renderer, "_ph_fg_color", (180,180,180)), "BG: None")


def set_cg(renderer, path: Optional[str]) -> None:
    """Set or clear full-screen CG overlay using renderer's asset resolver."""
    size = _logical_size(renderer)
    if not path or (isinstance(path, str) and path.lower() == "none"):
        renderer.cg = None
        return
    try:
        resolved = renderer._resolve_asset(path, ["cg"])  # prefer assets/<ns>/cg then assets/cg
        img = load_image(resolved, convert="alpha")
        renderer.cg = pygame.transform.smoothscale(img, size)
        # Mark unlocked in gallery manifest (best effort)
        try:
            def _gsd() -> Path:
                try:
                    get_dir = getattr(renderer, "_get_save_dir", None)
                    if callable(get_dir):
                        res = get_dir()
                        return res if isinstance(res, Path) else Path(str(res))
                except Exception:
                    pass
                return Path("save")
            gallery_unlock(str(path), _gsd)
        except Exception:
            pass
    except Exception:
        renderer.cg = make_bg_placeholder(size, renderer.font, getattr(renderer, "_ph_bg_color", (40,40,40)), getattr(renderer, "_ph_fg_color", (180,180,180)), f"CG missing: {path}")
