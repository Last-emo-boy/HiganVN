from __future__ import annotations

from pathlib import Path
from typing import Optional

from higanvn.engine.engine import Engine
from higanvn.engine.renderer import IRenderer

SCRIPT = "> VOICE voice1.ogg 0.8\n旁白：hello\n"


class FakeRenderer(IRenderer):
    def __init__(self) -> None:
        self._pending_voice = None  # tuple(path, vol)
        self._auto_mode = False
        self._typing_speed = 0.0

    def set_background(self, path: Optional[str]) -> None:
        pass

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:
        pass

    def play_se(self, path: str, volume: float | None = None) -> None:
        pass

    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:
        if path is None:
            self._pending_voice = None
        else:
            self._pending_voice = (path, volume)

    def show_text(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        pass

    def command(self, name: str, args: str) -> None:
        pass

    def wait_for_advance(self) -> None:
        pass

    def ask_choice(self, choices: list[tuple[str, str]]) -> int:
        return 0

    def reset_state(self) -> None:
        pass

    def get_snapshot(self) -> dict:
        return {
            "auto": self._auto_mode,
            "typing_speed": self._typing_speed,
            "voice": {
                "pending": {
                    "path": self._pending_voice[0] if self._pending_voice else None,
                    "volume": self._pending_voice[1] if self._pending_voice else None,
                }
            }
        }

    def apply_snapshot(self, snap: dict) -> None:
        v = snap.get("voice") or {}
        pen = v.get("pending") or {}
        p = pen.get("path")
        vol = pen.get("volume")
        if p is not None or vol is not None:
            self.prepare_voice(p, vol)


def test_snapshot_restores_voice_pending(tmp_path: Path) -> None:
    from higanvn.script.parser import parse_script

    sp = tmp_path / "demo.vns"
    sp.write_text(SCRIPT, encoding="utf-8")
    prog = parse_script(SCRIPT)

    r1 = FakeRenderer()
    eng = Engine(r1, interactive=False, strict=False)
    eng.set_script_path(sp)
    eng.load(prog)
    eng.run_headless()

    ok = eng.quicksave(tmp_path / "quick.json")
    assert ok

    # new engine/renderer
    r2 = FakeRenderer()
    eng2 = Engine(r2, interactive=False, strict=False)
    assert eng2.quickload(tmp_path / "quick.json")

    assert r2._pending_voice is not None
    assert r2._pending_voice[0] is not None
    assert r2._pending_voice[1] == 0.8
