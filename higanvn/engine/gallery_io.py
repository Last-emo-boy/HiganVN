from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import json
import pygame

DEFAULTS = {
    "unlocked": []  # list of relative CG paths
}


def _gallery_dir(get_save_dir: Optional[Callable[[], Path]] = None) -> Path:
    base: Path
    try:
        if callable(get_save_dir):
            b = get_save_dir()  # type: ignore[misc]
            base = b if isinstance(b, Path) else Path(str(b))
        else:
            base = Path("save")
    except Exception:
        base = Path("save")
    d = base / "gallery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def manifest_path(get_save_dir: Optional[Callable[[], Path]] = None) -> Path:
    return _gallery_dir(get_save_dir) / "gallery.json"


def thumbs_dir(get_save_dir: Optional[Callable[[], Path]] = None) -> Path:
    d = _gallery_dir(get_save_dir) / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_manifest(get_save_dir: Optional[Callable[[], Path]] = None) -> Dict:
    p = manifest_path(get_save_dir)
    if not p.exists():
        return {"unlocked": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"unlocked": []}


def save_manifest(data: Dict, get_save_dir: Optional[Callable[[], Path]] = None) -> bool:
    p = manifest_path(get_save_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        base = {"unlocked": []}
        base["unlocked"].extend(data.get("unlocked", []))
        p.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def is_unlocked(path: str, get_save_dir: Optional[Callable[[], Path]] = None) -> bool:
    m = load_manifest(get_save_dir)
    return str(path) in set(m.get("unlocked", []))


def unlock(path: str, get_save_dir: Optional[Callable[[], Path]] = None) -> None:
    try:
        m = load_manifest(get_save_dir)
        u = set(m.get("unlocked", []))
        u.add(str(path))
        save_manifest({"unlocked": sorted(u)}, get_save_dir)
    except Exception:
        pass


def cache_thumb_key(path: str) -> str:
    # simple filename-based key; could include hash later
    p = Path(path)
    return p.stem + ".png"


def read_thumb(path: str, get_save_dir: Optional[Callable[[], Path]] = None) -> Optional[pygame.Surface]:
    tp = thumbs_dir(get_save_dir) / cache_thumb_key(path)
    if not tp.exists():
        return None
    try:
        img = pygame.image.load(str(tp))
        return img.convert_alpha()
    except Exception:
        return None


def write_thumb(surf: pygame.Surface, path: str, get_save_dir: Optional[Callable[[], Path]] = None) -> bool:
    tp = thumbs_dir(get_save_dir) / cache_thumb_key(path)
    try:
        pygame.image.save(surf, str(tp))
        return True
    except Exception:
        return False
