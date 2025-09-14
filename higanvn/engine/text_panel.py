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
    panel_alpha: Optional[int] = None,
    text_outline: Optional[bool] = None,
    text_shadow: Optional[bool] = None,
    text_shadow_offset: Optional[Tuple[int, int]] = None,
) -> tuple[bool, int, Optional[int]]:
    def _blit_text(s: str, pos: Tuple[int, int], color: Tuple[int, int, int] = (255, 255, 255)) -> None:
        ox, oy = (text_shadow_offset or (1, 1))
        if text_outline:
            try:
                out = font.render(s, True, (0, 0, 0))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                    canvas.blit(out, (pos[0] + dx, pos[1] + dy))
            except Exception:
                pass
        if text_shadow:
            try:
                sh = font.render(s, True, (0, 0, 0))
                canvas.blit(sh, (pos[0] + ox, pos[1] + oy))
            except Exception:
                pass
        try:
            surf = font.render(s, True, color)
            canvas.blit(surf, pos)
        except Exception:
            pass
    box_rect = pygame.Rect(0, LOGICAL_SIZE[1] - 200, LOGICAL_SIZE[0], 200)
    ui_panel = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
    try:
        alpha = int(panel_alpha if panel_alpha is not None else 160)
        alpha = 0 if alpha < 0 else (255 if alpha > 255 else alpha)
    except Exception:
        alpha = 160
    ui_panel.fill((0, 0, 0, alpha))
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
        try:
            name_surf = font.render(disp, True, name_color)
        except Exception:
            name_surf = None
        _blit_text(disp, (box_rect.x + 16, y), name_color)
        if effect:
            eff_txt = f"[{effect}]"
            x0 = box_rect.x + 16 + (name_surf.get_width() if name_surf else 0) + 10
            _blit_text(eff_txt, (x0, y), (150, 150, 255))
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
        _blit_text(line, (box_rect.x + 16, y), (255, 255, 255))
        y += 28
    return reveal, line_start_ts_out, line_full_ts_out
