from __future__ import annotations

from typing import Tuple, Optional

import pygame

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def draw_end_card(canvas: pygame.Surface, title_text: str, hint_font: pygame.font.Font, base_font: pygame.font.Font,
                  font_path: Optional[str], font_size: int) -> None:
    overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    canvas.blit(overlay, (0, 0))
    if "：" in title_text:
        title, subtitle = title_text.split("：", 1)
    else:
        title, subtitle = title_text, ""
    big = pygame.font.Font(font_path or None, max(28, int(font_size * 1.6))) if font_path else pygame.font.SysFont(None, max(28, int(font_size * 1.6)))
    mid = pygame.font.Font(font_path or None, max(24, int(font_size * 1.1))) if font_path else pygame.font.SysFont(None, max(24, int(font_size * 1.1)))
    t_surf = big.render(title, True, (255, 235, 130))
    s_surf = mid.render(subtitle, True, (235, 235, 235)) if subtitle else None
    t_rect = t_surf.get_rect(center=(LOGICAL_SIZE[0] // 2, LOGICAL_SIZE[1] // 2 - (24 if s_surf else 0)))
    canvas.blit(t_surf, t_rect)
    if s_surf:
        s_rect = s_surf.get_rect(center=(LOGICAL_SIZE[0] // 2, LOGICAL_SIZE[1] // 2 + 24))
        canvas.blit(s_surf, s_rect)
    hint = "按任意键继续"
    hsurf = hint_font.render(hint, True, (230, 230, 230))
    hrect = hsurf.get_rect(center=(LOGICAL_SIZE[0] // 2, LOGICAL_SIZE[1] // 2 + 80))
    canvas.blit(hsurf, hrect)
