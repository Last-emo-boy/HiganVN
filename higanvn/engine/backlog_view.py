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
    # content area margin and width limit
    margin_x = 60
    y = 60
    max_lines = 18
    hist = history
    if view_idx == -1:
        start = max(0, len(hist) - max_lines)
    else:
        start = max(0, min(view_idx, len(hist) - 1) - max_lines + 1)
    end = min(len(hist), start + max_lines)
    # header with underline
    title = font.render("Backlog", True, (240, 240, 240))
    canvas.blit(title, (margin_x, 24))
    try:
        pygame.draw.line(canvas, (220, 220, 220), (margin_x, 52), (LOGICAL_SIZE[0]-margin_x, 52), 1)
    except Exception:
        pass
    for i in range(start, end):
        line = hist[i]
        name = line.name or ""
        text = f"{name}: {line.text}" if name else line.text
        color = (255, 255, 160) if (view_idx == -1 and i == len(hist) - 1) or (view_idx == i) else (230, 230, 230)
        # draw each entry block with a subtle separator
        lines = wrap_text(text, font, LOGICAL_SIZE[0] - 2*margin_x)
        for wrapped in lines:
            surf = font.render(wrapped, True, color)
            canvas.blit(surf, (margin_x, y))
            y += 28
        # extra spacing between entries
        y += 10
        try:
            pygame.draw.line(canvas, (80, 80, 80), (margin_x, y), (LOGICAL_SIZE[0]-margin_x, y), 1)
        except Exception:
            pass
        y += 6
