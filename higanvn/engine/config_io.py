from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import json


DEFAULTS = {
    "ui": {
        "textbox_opacity": 160,
        "text_outline": False,
        "text_shadow": True,
        "text_shadow_offset": [1, 1],
    },
    "debug": {
        "theme": "Dark",
        "ontop": False,
        "interval_ms": 300,
    },
}


def _config_path(get_save_dir: Optional[Callable[[], Path]] = None) -> Path:
    base: Path
    try:
        if callable(get_save_dir):
            base_obj = get_save_dir()  # type: ignore[misc]
            base = base_obj if isinstance(base_obj, Path) else Path(str(base_obj))
        else:
            base = Path("save")
    except Exception:
        base = Path("save")
    return base / "config.json"


def load_config(get_save_dir: Optional[Callable[[], Path]] = None) -> dict:
    p = _config_path(get_save_dir)
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            # merge defaults (shallow)
            ui = dict(DEFAULTS.get("ui", {}))
            ui.update(dict((data.get("ui") or {})))
            dbg = dict(DEFAULTS.get("debug", {}))
            dbg.update(dict((data.get("debug") or {})))
            out = {"ui": ui, "debug": dbg}
            return out
    except Exception:
        pass
    return {"ui": dict(DEFAULTS.get("ui", {})), "debug": dict(DEFAULTS.get("debug", {}))}


def save_config(cfg: dict, get_save_dir: Optional[Callable[[], Path]] = None) -> bool:
    p = _config_path(get_save_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # Keep only known keys (avoid bloating)
        ui = dict(DEFAULTS.get("ui", {}))
        ui.update(dict((cfg.get("ui") or {})))
        dbg = dict(DEFAULTS.get("debug", {}))
        dbg.update(dict((cfg.get("debug") or {})))
        data = {"ui": ui, "debug": dbg}
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
