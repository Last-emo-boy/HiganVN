from __future__ import annotations

from typing import Tuple

import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def fade(
    *,
    screen: Surface,
    clock: pygame.time.Clock,
    render_base,
    direction: str,
    duration_ms: int,
) -> None:
    start = pygame.time.get_ticks()
    size = screen.get_size()
    fade_surf = pygame.Surface(size, pygame.SRCALPHA)
    while True:
        # handle basic events and window resize to keep transition stable
        cancel = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                size = screen.get_size()
                fade_surf = pygame.Surface(size, pygame.SRCALPHA)
            # If user scrolls wheel or clicks to back/advance, cancel the transition immediately
            if event.type == pygame.MOUSEWHEEL:
                cancel = True
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) in (1, 4, 5):
                cancel = True
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN, pygame.K_SPACE, pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_UP, pygame.K_DOWN,
            ):
                cancel = True
        if cancel:
            # draw base once and exit without completing fade
            render_base()
            pygame.display.flip()
            break
        now = pygame.time.get_ticks()
        t = (now - start) / max(1, duration_ms)
        t = max(0.0, min(1.0, t))
        alpha = int(255 * (t if direction == "out" else (1 - t)))
        # draw the base scene without presenting
        render_base()
        # overlay the fade surface once and present
        fade_surf.fill((0, 0, 0, alpha))
        screen.blit(fade_surf, (0, 0))
        pygame.display.flip()
        if t >= 1.0:
            break
        clock.tick(60)
