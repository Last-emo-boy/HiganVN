from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_actor_mapping(base_dir: str | Path = ".") -> Dict[str, str]:
    """Load mapping from actor display names to asset folder keys.

    Looks for an `actors_map.json` file in base_dir with structure:
      { "张鹏": "zhangpeng", "小马": "xiaoma" }

    Returns empty mapping if not found or invalid.
    """
    try:
        base = Path(base_dir)
        candidates = [
            base / "config" / "actors_map.json",  # preferred new location
            base / "actors_map.json",              # backward compatible
        ]
        p = next((c for c in candidates if c.exists()), None)
        if not p:
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def resolve_actor_folder(name: str, mapping: Dict[str, str]) -> str:
    """Resolve actor folder name from display name using mapping.

    Fallback to the original name if no mapping is present.
    """
    return mapping.get(name, name)
