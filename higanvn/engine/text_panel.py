from __future__ import annotations

from typing import Optional, Tuple

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


def draw_text_panel(
    canvas: Surface,
    font: pygame.font.Font,
    hint_font: pygame.font.Font,
    name: Optional[str],
    text: str,
    effect: Optional[str],
    typing_enabled: bool,
    fast_forward: bool,
    line_start_ts: int,
    line_full_ts: Optional[int],
    reveal_instant: bool,
) -> tuple[bool, int, Optional[int]]:
    box_rect = pygame.Rect(0, LOGICAL_SIZE[1] - 200, LOGICAL_SIZE[0], 200)
    ui_panel = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
    ui_panel.fill((0, 0, 0, 160))
    canvas.blit(ui_panel, (box_rect.x, box_rect.y))
    pygame.draw.rect(canvas, (255, 255, 255), box_rect, 2)
    y = box_rect.y + 16
    if name:
        name_color = (255, 255, 0)
        nstr = str(name)
        if '|' in nstr:
            base, alias = nstr.split('|', 1)
            disp = f"{base}（{alias}）"
        else:
            disp = nstr
        pygame.draw.rect(canvas, (255, 255, 0), pygame.Rect(box_rect.x + 10, y + 4, 4, 22))
        name_surf = font.render(disp, True, name_color)
        canvas.blit(name_surf, (box_rect.x + 16, y))
        if effect:
            eff_surf = font.render(f"[{effect}]", True, (150, 150, 255))
            canvas.blit(eff_surf, (box_rect.x + 16 + name_surf.get_width() + 10, y))
        y += 30
    disp_text = text
    line_start_ts_out = line_start_ts
    line_full_ts_out = line_full_ts
    reveal = reveal_instant
    if typing_enabled and not reveal_instant:
        now = pygame.time.get_ticks()
        if line_start_ts_out == 0:
            line_start_ts_out = now
        speed = 45.0 * (3.0 if fast_forward else 1.0)
        allow = int(max(0, (now - line_start_ts_out) / 1000.0) * speed)
        if allow < len(text):
            disp_text = text[:allow]
            line_full_ts_out = None
        else:
            disp_text = text
            if line_full_ts_out is None:
                line_full_ts_out = now
    for line in wrap_text(disp_text, font, box_rect.width - 32):
        surf = font.render(line, True, (255, 255, 255))
        canvas.blit(surf, (box_rect.x + 16, y))
        y += 28
    return reveal, line_start_ts_out, line_full_ts_out
