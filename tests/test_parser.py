from __future__ import annotations

from higanvn.script.parser import parse_script


def test_parse_basic_dialogue_and_narration():
    src = """>
> BG 教室.png
张鹏: 你好
黄昏的风吹过
? 去天台 -> go
*go
""".strip()
    program = parse_script(src)
    kinds = [op.kind for op in program.ops]
    assert kinds[:3] == ["command", "dialogue", "narration"]
    assert any(op.kind == "choice" for op in program.ops)
    assert "go" in program.labels
