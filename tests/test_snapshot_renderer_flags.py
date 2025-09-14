from __future__ import annotations

from pathlib import Path
from typing import Optional

from higanvn.engine.engine import Engine
from higanvn.engine.renderer import IRenderer

SCRIPT = "> BG bg1.png\n> BGM bgm1.ogg 0.6\n旁白：test\n"


class FakeRenderer(IRenderer):
    def __init__(self) -> None:
        self.bg = None
        self.bgm = (None, None)  # (path, vol)
        self._auto_mode = True
        self._typing_speed = 0.0
        self._applied_snapshot = None

    def set_background(self, path: Optional[str]) -> None:
        self.bg = path

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:
        self.bgm = (path, volume)

    def play_se(self, path: str, volume: float | None = None) -> None:
        pass

    def show_text(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        pass

    def command(self, name: str, args: str) -> None:
        if name.upper() == "CG":
            pass

    def wait_for_advance(self) -> None:
        pass

    def ask_choice(self, choices: list[tuple[str, str]]) -> int:
        return 0

    def reset_state(self) -> None:
        pass

    def get_snapshot(self) -> dict:
        return {
            "bg": self.bg,
            "cg": None,
            "characters": [],
            "auto": self._auto_mode,
            "typing_speed": self._typing_speed,
            "bgm": {"path": self.bgm[0], "volume": self.bgm[1]},
        }

    def apply_snapshot(self, snap: dict) -> None:
        self._applied_snapshot = snap
        self._auto_mode = bool(snap.get("auto"))
        self._typing_speed = float(snap.get("typing_speed") or 0.0)
        self.set_background(snap.get("bg"))
        bgm = snap.get("bgm") or {}
        self.play_bgm(bgm.get("path"), bgm.get("volume"))


def test_quicksave_quickload_preserves_flags(tmp_path: Path) -> None:
    from higanvn.script.parser import parse_script

    prog = parse_script(SCRIPT)
    r1 = FakeRenderer()
    eng = Engine(r1, interactive=False, strict=False)
    sp = tmp_path / "demo.vns"
    sp.write_text(SCRIPT, encoding="utf-8")
    eng.set_script_path(sp)
    eng.load(prog)
    eng.run_headless()

    # initial flags snapshot should record auto/typing/bgm/bg
    assert r1.get_snapshot()["auto"] is True

    ok = eng.quicksave(tmp_path / "quick.json")
    assert ok

    # load into a fresh renderer
    r2 = FakeRenderer()
    eng2 = Engine(r2, interactive=False, strict=False)
    eng2.quickload(tmp_path / "quick.json")

    snap = r2._applied_snapshot
    assert snap is not None
    assert snap.get("auto") is True
    assert float(snap.get("typing_speed") or 0.0) == 0.0
    bgm = snap.get("bgm")
    assert isinstance(bgm, dict)
    # ensure bgm path/volume passed through
    assert bgm.get("path") is not None
    assert bgm.get("volume") == 0.6
