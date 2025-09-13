from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from higanvn.script.parser import parse_script


@dataclass
class Diagnostic:
    file: Path
    line: int | None
    column: int | None
    severity: str  # "error" | "warning" | "info"
    message: str


def validate_text(file: Path, text: str) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    try:
        program = parse_script(text)
    except Exception as e:  # noqa: BLE001
        diags.append(Diagnostic(file=file, line=None, column=None, severity="error", message=str(e)))
        return diags

    # Check choice targets exist
    labels = program.labels
    for op in program.ops:
        kind = op.kind
        payload = op.payload
        raw_line = payload.get("line") if payload else None
        line = int(raw_line) if isinstance(raw_line, (int, str)) and str(raw_line).isdigit() else None
        if kind == "choice":
            target = str(payload.get("target", "")).strip()
            if target and target not in labels:
                diags.append(
                    Diagnostic(
                        file=file,
                        line=line,
                        column=None,
                        severity="error",
                        message=f"Choice target label not found: '{target}'",
                    )
                )
        elif kind == "command":
            name = str(payload.get("name", "")).strip()
            if not name:
                diags.append(Diagnostic(file=file, line=line, column=None, severity="warning", message="Empty command name"))
        elif kind == "dialogue":
            actor = str(payload.get("actor", "")).strip()
            if not actor:
                diags.append(Diagnostic(file=file, line=line, column=None, severity="warning", message="Dialogue missing actor"))

    return diags


def validate_files(files: Iterable[Path]) -> list[Diagnostic]:
    all_diags: list[Diagnostic] = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            all_diags.append(Diagnostic(file=file, line=None, column=None, severity="error", message=f"Failed to read: {e}"))
            continue
        all_diags.extend(validate_text(file, text))
    return all_diags
