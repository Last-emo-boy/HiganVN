from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScriptError(Exception):
    message: str
    line: int | None = None
    context: str | None = None

    def __str__(self) -> str:  # pragma: no cover - formatting
        loc = f" (line {self.line})" if self.line else ""
        ctx = f"\n  >> {self.context}" if self.context else ""
        return f"{self.message}{loc}{ctx}"
