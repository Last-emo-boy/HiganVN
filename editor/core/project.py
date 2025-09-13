from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DEFAULT_PROJECT = {
    "version": 1,
    "name": "Untitled",
    "id": "",
    "scripts": ["scripts/demo.vns"],
    "assetsNamespace": "demo",
    "metadataPath": "scripts/demo.vns.meta.json",
    "outputDir": "editor/out",
    "settings": {"strict": True, "fontSize": 28},
}


@dataclass
class Project:
    path: Path
    data: dict

    @property
    def root(self) -> Path:
        return self.path.parent

    @property
    def output_dir(self) -> Path:
        out = self.data.get("outputDir", "editor/out")
        return (self.root / out).resolve()

    @staticmethod
    def load(path: Path) -> "Project":
        if not path.exists():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return Project(path=path, data=data)

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def create(path: Path, template: dict | None = None) -> "Project":
        template = template or DEFAULT_PROJECT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        return Project.load(path)
