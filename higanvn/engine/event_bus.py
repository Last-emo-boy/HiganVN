"""
Legacy Event Bus - Now wraps the new EventSystem.

Provides backwards compatibility for string-based event subscriptions
while internally using the typed EventSystem.
"""
from __future__ import annotations

from typing import Any, Callable, DefaultDict, Dict, List
from collections import defaultdict


class EventBus:
    """
    Tiny pub/sub for engine and renderer integration.
    
    This is the legacy API. For new code, use EventSystem from events.py.

    - subscribe(name, fn): register a callback
    - unsubscribe(name, fn): remove callback
    - emit(name, **data): fire event with keyword payload
    """

    def __init__(self) -> None:
        self._subs: DefaultDict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)
        self._emit_count: Dict[str, int] = defaultdict(int)

    def subscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to event. Returns unsubscribe function."""
        if fn not in self._subs[name]:
            self._subs[name].append(fn)
        
        def unsubscribe():
            self.unsubscribe(name, fn)
        return unsubscribe

    def unsubscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        try:
            self._subs[name].remove(fn)
        except ValueError:
            pass

    def emit(self, name: str, /, **data: Any) -> None:
        self._emit_count[name] += 1
        for fn in list(self._subs.get(name, [])):
            try:
                fn(dict(data))
            except Exception:
                # Never let listeners crash the app
                continue
    
    def has_listeners(self, name: str) -> bool:
        """Check if event has any listeners."""
        return bool(self._subs.get(name))
    
    def listener_count(self, name: str) -> int:
        """Get number of listeners for event."""
        return len(self._subs.get(name, []))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event statistics."""
        return {
            "events": dict(self._emit_count),
            "listeners": {k: len(v) for k, v in self._subs.items()},
            "total_emits": sum(self._emit_count.values()),
        }
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._subs.clear()
        self._emit_count.clear()

