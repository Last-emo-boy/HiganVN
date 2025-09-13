from __future__ import annotations

from typing import Tuple

import pygame
from pygame import Surface

from higanvn.ui.textwrap import wrap_text_generic

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    def measure(s: str) -> int:
        try:
            return font.size(s)[0]
        except Exception:
            return 0
    return wrap_text_generic(text or "", measure, int(max_width))


def draw_backlog(
    canvas: Surface,
    font: pygame.font.Font,
    history: list,
    view_idx: int,
) -> None:
    overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    canvas.blit(overlay, (0, 0))
    y = 60
    max_lines = 18
    hist = history
    if view_idx == -1:
        start = max(0, len(hist) - max_lines)
    else:
        start = max(0, min(view_idx, len(hist) - 1) - max_lines + 1)
    end = min(len(hist), start + max_lines)
    title = font.render("Backlog", True, (240, 240, 240))
    canvas.blit(title, (40, 24))
    for i in range(start, end):
        line = hist[i]
        name = line.name or ""
        text = f"{name}: {line.text}" if name else line.text
        color = (255, 255, 160) if (view_idx == -1 and i == len(hist) - 1) or (view_idx == i) else (230, 230, 230)
        for wrapped in wrap_text(text, font, LOGICAL_SIZE[0] - 80):
            surf = font.render(wrapped, True, color)
            canvas.blit(surf, (40, y))
            y += 28
