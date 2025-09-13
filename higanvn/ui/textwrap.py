from __future__ import annotations

from typing import Callable, List


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def wrap_text_generic(text: str, measure: Callable[[str], int], max_width: int) -> List[str]:
    """Wrap text into lines that fit within max_width using a width measure.

    - For CJK text, wrap by character.
    - For non-CJK, wrap by words separated by spaces.

    Parameters:
        text: Full text containing optional newlines.
        measure: A function that returns pixel width for a given string.
        max_width: Maximum width in pixels for each line.
    Returns:
        List[str]: Wrapped lines preserving explicit newlines.
    """
    paragraphs = text.split("\n")
    out: List[str] = []
    for para in paragraphs:
        if para == "":
            out.append("")
            continue
        if _has_cjk(para):
            cur = ""
            for ch in para:
                test = cur + ch
                if measure(test) <= max_width:
                    cur = test
                else:
                    if cur:
                        out.append(cur)
                    cur = ch
            if cur:
                out.append(cur)
        else:
            words = para.split()
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if measure(test) <= max_width:
                    cur = test
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            if cur:
                out.append(cur)
    return out
