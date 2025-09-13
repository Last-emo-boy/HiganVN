from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from pathlib import Path


class IAssets(ABC):
    @abstractmethod
    def resolve(self, path: str, *, prefixes: Optional[list[str]] = None, namespace: Optional[str] = None) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def exists(self, rel_or_uri: str, *, namespace: Optional[str] = None) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class FileSystemAssets(IAssets):
    """Simple filesystem-based asset resolver.

    This mirrors current resolve behavior; detailed logic still lives in engine.assets_utils.
    """

    def __init__(self, base: Path | None = None) -> None:
        self._base = base or Path.cwd()

    def resolve(self, path: str, *, prefixes: Optional[list[str]] = None, namespace: Optional[str] = None) -> str:
        # Defer to existing centralized resolver to keep parity; local fallback is simple join
        try:
            from higanvn.engine.assets_utils import resolve_asset
            return resolve_asset(path, asset_namespace=namespace, prefixes=prefixes or [])
        except Exception:
            p = Path(path)
            if p.is_absolute():
                return str(p)
            base = self._base
            if namespace:
                base = base / namespace
            if prefixes:
                for pref in prefixes:
                    cand = base / pref / path
                    if cand.exists():
                        return str(cand)
            return str((base / path))

    def exists(self, rel_or_uri: str, *, namespace: Optional[str] = None) -> bool:
        try:
            p = Path(rel_or_uri)
            if p.is_absolute():
                return p.exists()
            base = self._base
            if namespace:
                base = base / namespace
            return (base / rel_or_uri).exists()
        except Exception:
            return False
