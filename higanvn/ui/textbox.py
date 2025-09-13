from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class Line:
    name: Optional[str]
    text: str
    emotion: Optional[str] = None
    effect: Optional[str] = None


class Textbox:
    def __init__(self, capacity: int = 500) -> None:
        self.capacity = capacity
        self.history: List[Line] = []
        self.view_idx: int = -1  # -1 means latest

    def push(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        line = Line(name=name, text=text,
                    emotion=(meta or {}).get("emotion"),
                    effect=(meta or {}).get("effect"))
        self.history.append(line)
        if len(self.history) > self.capacity:
            self.history.pop(0)
        self.view_idx = -1

    def current(self) -> Optional[Line]:
        if not self.history:
            return None
        if self.view_idx == -1:
            return self.history[-1]
        i = max(0, min(self.view_idx, len(self.history) - 1))
        return self.history[i]

    def scroll_up(self, n: int = 1) -> None:
        if not self.history:
            return
        if self.view_idx == -1:
            self.view_idx = len(self.history) - 1
        self.view_idx = max(0, self.view_idx - n)

    def scroll_down(self, n: int = 1) -> None:
        if not self.history:
            return
        if self.view_idx == -1:
            return
        self.view_idx += n
        if self.view_idx >= len(self.history) - 1:
            self.view_idx = -1

    def clear(self) -> None:
        self.history.clear()
        self.view_idx = -1
