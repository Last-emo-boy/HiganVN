from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame


def init_font(font_path: Optional[str], size: int, asset_namespace: Optional[str] = None) -> pygame.font.Font:
    # 1) Explicit path
    if font_path:
        try:
            p = Path(font_path)
            if p.exists():
                return pygame.font.Font(str(p), size)
        except Exception:
            pass
    # 2) Common bundled fonts in assets/fonts (try namespaced first)
    candidates = [
        "fonts/NotoSansSC-Regular.otf",
        "fonts/NotoSansSC-Regular.ttf",
        "fonts/SourceHanSansSC-Regular.otf",
        "fonts/MicrosoftYaHei.ttf",
        "fonts/SimHei.ttf",
    ]
    for rel in candidates:
        try:
            ns = asset_namespace
            if ns:
                p = Path(str(ns)) / rel
                if p.exists():
                    return pygame.font.Font(str(p), size)
        except Exception:
            continue
    for rel in candidates:
        try:
            p = Path(rel)
            if p.exists():
                return pygame.font.Font(str(p), size)
        except Exception:
            continue
    # 3) System fonts
    cjk_families = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "PingFang SC",
    ]
    try:
        return pygame.font.SysFont(cjk_families, size)
    except Exception:
        return pygame.font.SysFont(None, size)
