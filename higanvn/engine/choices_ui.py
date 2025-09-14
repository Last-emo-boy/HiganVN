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

        # dynamic menu width based on content
        max_w = 0
        for i, (txt, _tgt) in enumerate(choices):
            w, _ = font.size(f"{i+1}. {txt}")
            if w > max_w:
                max_w = w
        menu_w = min(LOGICAL_SIZE[0] - 100, max_w + 60)
        menu_h = 44 * len(choices) + 20
        menu_x = (LOGICAL_SIZE[0] - menu_w) // 2
        menu_y = max(80, (LOGICAL_SIZE[1] - menu_h) // 3)
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)

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
            if event.type == pygame.MOUSEWHEEL:
                # scroll wheel to navigate
                if event.y > 0:
                    selected = (selected - 1) % len(choices)
                elif event.y < 0:
                    selected = (selected + 1) % len(choices)

        render_base(flip=False, tick=False)
        # darken background for readability
        ov = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        ov.fill((0, 0, 0, 100))
        canvas.blit(ov, (0, 0))
        # menu panel
        panel = pygame.Surface((menu_rect.width, menu_rect.height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        canvas.blit(panel, (menu_rect.x, menu_rect.y))
        pygame.draw.rect(canvas, (255, 255, 255), menu_rect, 2)
        y = menu_rect.y + 10
        for i, (txt, _tgt) in enumerate(choices):
            row_rect = pygame.Rect(menu_rect.x + 10, y, menu_rect.width - 20, 40)
            if i == selected:
                hi = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
                hi.fill((90, 140, 220, 140))
                canvas.blit(hi, (row_rect.x, row_rect.y))
                try:
                    pygame.draw.rect(canvas, (200, 220, 255), row_rect, 2)
                except Exception:
                    pass
            color = (0, 255, 0) if i == selected else (240, 240, 240)
            arrow = "▶" if i == selected else "  "
            label_surf = font.render(arrow, True, color)
            canvas.blit(label_surf, (row_rect.x + 6, row_rect.y + 6))
            surf = font.render(f"{i+1}. {txt}", True, color)
            canvas.blit(surf, (row_rect.x + 28, row_rect.y + 6))
            y += 44

        scaled = pygame.transform.smoothscale(canvas, (dst_w, dst_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled, (x_off, y_off))
        pygame.display.flip()
        clock.tick(60)
