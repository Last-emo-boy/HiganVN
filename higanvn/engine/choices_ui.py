from __future__ import annotations

from typing import Callable, List, Tuple

import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def ask_choice(
    *,
    choices: List[Tuple[str, str]],
    screen: Surface,
    canvas: Surface,
    clock: pygame.time.Clock,
    font: pygame.font.Font,
    render_base: Callable[..., None],
) -> int:
    selected = 0
    while True:
        # compute transform from current window size
        win_w, win_h = screen.get_size()
        scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
        dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
        x_off = (win_w - dst_w) // 2
        y_off = (win_h - dst_h) // 2

        menu_rect = pygame.Rect(50, 100, LOGICAL_SIZE[0] - 100, 40 * len(choices) + 20)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(choices)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(choices)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return selected
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    num = event.key - pygame.K_0
                    if 1 <= num <= len(choices):
                        return num - 1
            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if x_off <= mx <= x_off + dst_w and y_off <= my <= y_off + dst_h:
                    cx = int((mx - x_off) / scale)
                    cy = int((my - y_off) / scale)
                    if menu_rect.collidepoint((cx, cy)):
                        idx = (cy - menu_rect.y - 10) // 40
                        if 0 <= idx < len(choices):
                            selected = idx
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if x_off <= mx <= x_off + dst_w and y_off <= my <= y_off + dst_h:
                    cx = int((mx - x_off) / scale)
                    cy = int((my - y_off) / scale)
                    if menu_rect.collidepoint((cx, cy)):
                        idx = (cy - menu_rect.y - 10) // 40
                        if 0 <= idx < len(choices):
                            return idx

        render_base(flip=False, tick=False)
        pygame.draw.rect(canvas, (0, 0, 0), menu_rect)
        pygame.draw.rect(canvas, (255, 255, 255), menu_rect, 2)
        y = menu_rect.y + 10
        for i, (txt, _tgt) in enumerate(choices):
            if i == selected:
                hi = pygame.Surface((menu_rect.width - 20, 36), pygame.SRCALPHA)
                hi.fill((70, 110, 180, 120))
                canvas.blit(hi, (menu_rect.x + 10, y))
            color = (0, 255, 0) if i == selected else (255, 255, 255)
            surf = font.render(f"{i+1}. {txt}", True, color)
            canvas.blit(surf, (menu_rect.x + 16, y + 4))
            y += 40

        scaled = pygame.transform.smoothscale(canvas, (dst_w, dst_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, (x_off, y_off))
        pygame.display.flip()
        clock.tick(60)
