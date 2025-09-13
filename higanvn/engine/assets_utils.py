from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable


def resolve_asset(path: str, *, asset_namespace: Optional[str], prefixes: Optional[Iterable[str]] = None) -> str:
    p = Path(path)
    if p.exists():
        return str(p)
    candidates = []
    if asset_namespace:
        candidates.append(Path(asset_namespace) / path)
    for pre in (prefixes or []):
        if asset_namespace:
            candidates.append(Path(asset_namespace) / pre / path)
        candidates.append(Path(pre) / path)
    for q in candidates:
        if q.exists():
            return str(q)
    return path
