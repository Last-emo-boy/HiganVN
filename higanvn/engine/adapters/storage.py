from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional
import json


class ISaveStore(ABC):
    """Abstract save store for engine state payloads.

    Implementations should store JSON-serializable dict payloads and retrieve them intact.
    """

    @abstractmethod
    def write_quick(self, payload: dict) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def read_quick(self) -> Optional[dict]:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def write_slot(self, slot: int, payload: dict) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    @abstractmethod
    def read_slot(self, slot: int) -> Optional[dict]:  # pragma: no cover - interface
        raise NotImplementedError

    # Optional extended APIs for UI and maintenance
    def list_slots(self) -> list[int]:  # pragma: no cover - interface
        return []

    def delete_slot(self, slot: int) -> bool:  # pragma: no cover - interface
        return False


class FileSaveStore(ISaveStore):
    """Filesystem-based save store compatible with current save file layout.

    Files:
    - quick.json
    - slot_XX.json
    """

    def __init__(self, get_base_dir: Callable[[], Path]) -> None:
        self._get_base = get_base_dir

    def _ensure_dir(self) -> Path:
        base = self._get_base()
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return base

    def _slot_path(self, slot: int) -> Path:
        base = self._ensure_dir()
        return base / f"slot_{int(slot):02d}.json"

    def _quick_path(self) -> Path:
        base = self._ensure_dir()
        return base / "quick.json"

    def write_quick(self, payload: dict) -> bool:
        try:
            p = self._quick_path()
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def read_quick(self) -> Optional[dict]:
        try:
            p = self._quick_path()
            if not p.exists():
                return None
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def write_slot(self, slot: int, payload: dict) -> bool:
        try:
            p = self._slot_path(int(slot))
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                # invalidate meta cache for this slot if present
                from ..save_io import invalidate_slot_cache
                invalidate_slot_cache(get_save_dir=self._get_base, slot=int(slot))
            except Exception:
                pass
            return True
        except Exception:
            return False

    def read_slot(self, slot: int) -> Optional[dict]:
        try:
            p = self._slot_path(int(slot))
            if not p.exists():
                return None
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    # --- extended helpers ---
    def list_slots(self) -> list[int]:
        base = self._ensure_dir()
        slots: list[int] = []
        try:
            for p in base.glob("slot_*.json"):
                name = p.stem  # slot_XX
                try:
                    n = int(name.split("_")[1])
                    slots.append(n)
                except Exception:
                    continue
            slots.sort()
        except Exception:
            return []
        return slots

    def delete_slot(self, slot: int) -> bool:
        ok = True
        try:
            p = self._slot_path(int(slot))
            if p.exists():
                p.unlink()
        except Exception:
            ok = False
        # try delete thumbnail if present
        try:
            from ..save_io import slot_thumb_path
            tp = slot_thumb_path(int(slot), get_save_dir=self._get_base)
            if tp.exists():
                tp.unlink()
        except Exception:
            pass
        # invalidate cache entry
        try:
            from ..save_io import invalidate_slot_cache
            invalidate_slot_cache(get_save_dir=self._get_base, slot=int(slot))
        except Exception:
            pass
        return ok
