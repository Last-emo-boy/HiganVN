from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, Tuple

_RESOLVE_CACHE: dict[Tuple[Optional[str], str, Tuple[str, ...]], str] = {}


def resolve_asset(path: str, *, asset_namespace: Optional[str], prefixes: Optional[Iterable[str]] = None) -> str:
    # fast path: as-is exists
    p = Path(path)
    if p.exists():
        return str(p)
    # cached lookup key
    key = (asset_namespace, str(path), tuple(prefixes or ()))
    if key in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[key]
    candidates = []
    if asset_namespace:
        candidates.append(Path(asset_namespace) / path)
    for pre in (prefixes or []):
        if asset_namespace:
            candidates.append(Path(asset_namespace) / pre / path)
        candidates.append(Path(pre) / path)
    for q in candidates:
        if q.exists():
            res = str(q)
            _RESOLVE_CACHE[key] = res
            return res
    _RESOLVE_CACHE[key] = path
    return path
