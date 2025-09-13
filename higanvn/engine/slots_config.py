from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any


def read_slots_config(asset_ns: Optional[str], logical_size: Tuple[int, int]) -> Dict[str, Any]:
    """Read UI slot positions/scale from config files, with namespace fallback.
    Returns a dict possibly containing keys: positions (list[tuple[int,int]]), scale (float).
    """
    candidates = []
    if asset_ns:
        candidates += [
            Path(asset_ns) / "config" / "ui.json",
            Path(asset_ns) / "config" / "slots.json",
        ]
    candidates += [
        Path("config") / "ui.json",
        Path("config") / "slots.json",
    ]
    for p in candidates:
        try:
            if p.exists():
                import json
                data = json.loads(p.read_text(encoding="utf-8"))
                out: Dict[str, Any] = {}
                if isinstance(data, dict):
                    pos = data.get("slots") or data.get("positions")
                    if isinstance(pos, list):
                        fixed = []
                        for it in pos:
                            if isinstance(it, (list, tuple)) and len(it) == 2:
                                x, y = it
                                if 0 < x <= 1 and 0 < y <= 1:
                                    fixed.append((int(logical_size[0] * x), int(logical_size[1] * y)))
                                else:
                                    fixed.append((int(x), int(y)))
                        if fixed:
                            out["positions"] = fixed
                    sc = data.get("scale")
                    if isinstance(sc, (int, float)) and sc > 0:
                        out["scale"] = float(sc)
                return out
        except Exception:
            continue
    return {}
