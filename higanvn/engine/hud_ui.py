from __future__ import annotations

from typing import Callable, Dict, Tuple, Optional

import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def draw_ui_buttons(
    canvas: Surface,
    font: pygame.font.Font,
    get_mouse_pos: Callable[[], Optional[tuple[int, int]]],
) -> Dict[str, pygame.Rect]:
    pad = 10
    btn_w, btn_h = 84, 32
    right = LOGICAL_SIZE[0] - pad
    top = pad
    back_rect = pygame.Rect(right - btn_w * 2 - pad, top, btn_w, btn_h)
    log_rect = pygame.Rect(right - btn_w, top, btn_w, btn_h)
    mouse = get_mouse_pos()
    for rect, label in ((back_rect, "Back"), (log_rect, "Log")):
        hovered = bool(mouse and rect.collidepoint(mouse))
        box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box.fill((30, 30, 30, 200) if hovered else (0, 0, 0, 140))
        canvas.blit(box, rect)
        pygame.draw.rect(canvas, (255, 255, 255), rect, 1)
        txt = font.render(label, True, (255, 255, 255))
        trect = txt.get_rect(center=rect.center)
        canvas.blit(txt, (trect.x, trect.y))
    return {"back": back_rect, "log": log_rect}


def draw_hints(
    canvas: Surface,
    hint_font: pygame.font.Font,
    auto_mode: bool,
) -> None:
    hint = "Tab:Backlog  M:分支图  ↑/↓:Scroll  Enter/Space:Adv  Click:Adv  A:Auto  F:Fast  F5/F9:快存/快读  F7/F8:存档/读档"
    surf = hint_font.render(hint, True, (210, 210, 210))
    margin = 10
    pos = (LOGICAL_SIZE[0] - surf.get_width() - margin, LOGICAL_SIZE[1] - surf.get_height() - margin)
    panel = pygame.Surface((surf.get_width() + 8, surf.get_height() + 4), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    canvas.blit(panel, (pos[0] - 4, pos[1] - 2))
    canvas.blit(surf, pos)
    if auto_mode:
        tag = hint_font.render("AUTO", True, (160, 255, 160))
        canvas.blit(tag, (pos[0] - tag.get_width() - 12, pos[1]))
