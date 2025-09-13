from __future__ import annotations

import json
from pathlib import Path

from higanvn.engine.engine import Engine
from higanvn.script.parser import parse_script


class FakeRenderer:
    """Minimal renderer stub with snapshot support for headless tests."""

    def __init__(self):
        self._auto_mode = False
        self._current_label = None
        self._bg_path = None
        self._cg_path = None
        self.char_layer = type("CL", (), {"snapshot_characters": lambda self: []})()  # type: ignore

    def set_textbox(self, tb, owned=False):
        self.textbox = tb

    def set_program(self, program):
        self._program = program

    def on_enter_label(self, name: str):
        self._current_label = name

    def show_text(self, name, text, meta=None):
        # push into textbox like real renderer does
        self.textbox.push(name, text, meta)

    def wait_for_advance(self):
        # no-op for tests
        pass

    def command(self, name: str, args: str):
        if name.upper() == "CG":
            self._cg_path = args if args != "None" else None

    def set_background(self, path: str | None):
        self._bg_path = path

    def reset_state(self):
        self._bg_path = None
        self._cg_path = None
        self.char_layer = type("CL", (), {"snapshot_characters": lambda self: []})()  # type: ignore

    def get_snapshot(self) -> dict:
        return {"bg": self._bg_path, "cg": self._cg_path, "characters": []}

    def apply_snapshot(self, snap: dict) -> None:
        self._bg_path = snap.get("bg")
        self._cg_path = snap.get("cg")


def test_snapshot_roundtrip_quick(tmp_path: Path):
    # simple script: set bg, a line, then set cg to ensure snapshot captures both
    src = "> BG bg/title.jpg\n黄昏\n> CG cg/scene01.jpg\n"
    program = parse_script(src)
    r = FakeRenderer()
    # type: ignore to satisfy type checker in tests; Engine accepts any object duck-typing IRenderer
    e = Engine(renderer=r)  # type: ignore[arg-type]
    # write script to disk so quickload can reload by path
    script_path = tmp_path / "demo.vns"
    script_path.write_text(src, encoding="utf-8")
    e.set_script_path(script_path)
    e.load(program)
    e.run_headless()
    # sanity: renderer saw both
    assert r._bg_path == "bg/title.jpg"
    assert r._cg_path == "cg/scene01.jpg"
    # write quick save into tmp
    sp = tmp_path / "quick.json"
    assert e.quicksave(sp)
    # wipe state
    r.reset_state()
    assert r._bg_path is None and r._cg_path is None
    # load via snapshot path
    assert e.quickload(sp)
    assert r._bg_path == "bg/title.jpg"
    assert r._cg_path == "cg/scene01.jpg"
