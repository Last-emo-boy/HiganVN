from __future__ import annotations

from typing import Optional
import pygame

from higanvn.engine.placeholders import make_bg_placeholder


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
            img = pygame.image.load(resolved).convert()
            renderer.bg = pygame.transform.scale(img, size)
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
        renderer.cg = pygame.image.load(resolved).convert()
    except Exception:
        renderer.cg = make_bg_placeholder(size, renderer.font, getattr(renderer, "_ph_bg_color", (40,40,40)), getattr(renderer, "_ph_fg_color", (180,180,180)), f"CG missing: {path}")
