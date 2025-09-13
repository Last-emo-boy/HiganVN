from __future__ import annotations

from higanvn.ui.textwrap import wrap_text_generic


def fake_measure_factory(char_widths: dict[str, int], default: int = 10):
    def measure(s: str) -> int:
        w = 0
        for ch in s:
            w += char_widths.get(ch, default)
        return w
    return measure


def test_wrap_cjk_char_based():
    # Each Chinese char = 12px, max_width 36 -> 3 chars per line
    measure = fake_measure_factory({}, default=12)
    text = "你好世界再见"  # 6 chars
    lines = wrap_text_generic(text, measure, 36)
    assert lines == ["你好世", "界再见"]


def test_wrap_word_based():
    # Letters 5px each, space counts as 5px, max_width 15 -> roughly 3 letters per line sans spaces
    measure = fake_measure_factory({" ": 5}, default=5)
    text = "hello world test"
    # Wrap by words: "hello" (25px) exceeds 15 -> each word alone in a line
    lines = wrap_text_generic(text, measure, 15)
    assert lines == ["hello", "world", "test"]


def test_wrap_mixed_newlines():
    measure = fake_measure_factory({}, default=10)
    text = "第一行\n\nthird line"
    lines = wrap_text_generic(text, measure, 100)
    # Large width -> no wrapping; preserve blank line
    assert lines == ["第一行", "", "third line"]
