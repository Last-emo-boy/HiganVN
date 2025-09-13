from __future__ import annotations

from higanvn.engine.engine import Engine
from higanvn.script.parser import parse_script


def test_engine_runs_headless_and_jumps_label():
    src = """
? go -> lab
黄昏
*lab
张鹏: 到了
"""
    program = parse_script(src)
    e = Engine()
    e.load(program)
    # Should not raise
    e.run_headless()