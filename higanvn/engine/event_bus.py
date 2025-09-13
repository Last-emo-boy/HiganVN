from __future__ import annotations

from typing import Any, Callable, DefaultDict, Dict, List
from collections import defaultdict


class EventBus:
    """Tiny pub/sub for engine and renderer integration.

    - subscribe(name, fn): register a callback
    - unsubscribe(name, fn): remove callback
    - emit(name, **data): fire event with keyword payload
    """

    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        if fn not in self._subs[name]:
            self._subs[name].append(fn)

    def unsubscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        try:
            self._subs[name].remove(fn)
        except ValueError:
            pass

    def emit(self, name: str, /, **data: Any) -> None:
        for fn in list(self._subs.get(name, [])):
            try:
                fn(dict(data))
            except Exception:
                # Never let listeners crash the app
                continue
