from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class Op:
    kind: str
    payload: Dict[str, Any]


class Program:
    def __init__(self, ops: List[Op], labels: Optional[Dict[str, int]] = None) -> None:
        self.ops = ops
        self.labels = labels or {}
