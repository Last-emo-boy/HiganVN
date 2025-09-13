from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List


def _base_dir() -> Path:
    # When frozen by PyInstaller, sys._MEIPASS points to the temp extraction folder
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[attr-defined]
    # Fallback: use the directory of the executable or this file
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent  # higanvn/


def _read_default_script(base: Path) -> Path | None:
    marker = base / "DEFAULT_SCRIPT.txt"
    try:
        if marker.exists():
            rel = marker.read_text(encoding="utf-8").strip()
            if rel:
                # Ensure we point to a file inside bundle, not a directory
                p = (base / rel)
                if p.is_dir():
                    # if mistakenly pointed to directory, pick first .vns inside
                    cand = next((x for x in p.glob("*.vns")), None)
                    if cand:
                        return cand
                return p
    except Exception:
        pass
    # Fallback: try to find any .vns under scripts/
    cand_dir = base / "scripts"
    if cand_dir.exists():
        for p in cand_dir.glob("*.vns"):
            return p.resolve()
    return None


def _run() -> int:
    # Ensure audio driver is safe in frozen envs
    os.environ.setdefault("SDL_AUDIODRIVER", "directsound")
    # Defer heavy imports until runtime
    from higanvn.cli import main as higan_main

    base = _base_dir()
    script = _read_default_script(base)
    if not script or not script.exists():
        print("No script found to run. Expected DEFAULT_SCRIPT.txt or scripts/*.vns inside the bundle.")
        return 2
    assets = base / "assets"
    # Try reading metadata to customize window title and assets namespace
    argv: List[str] = [str(script), "--pygame", "--assets", str(assets)]
    meta = script.with_suffix('.meta.json')
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
            # title
            title = data.get('windowTitle') or data.get('title')
            if isinstance(title, str) and title.strip():
                argv += ["--font-size", "28"]  # keep default size; real title handled inside PygameRenderer
            # nothing else needed here, CLI will pick up meta for renderer title/namespace
        except Exception:
            pass
    return higan_main(argv)


if __name__ == "__main__":
    raise SystemExit(_run())
