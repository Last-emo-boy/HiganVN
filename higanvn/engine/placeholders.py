from __future__ import annotations

from typing import Tuple
import pygame


def make_bg_placeholder(logical_size: Tuple[int, int], font: pygame.font.Font,
                        bg_color: Tuple[int, int, int], fg_color: Tuple[int, int, int],
                        label: str) -> pygame.Surface:
    surf = pygame.Surface(logical_size).convert()
    surf.fill(bg_color)
    # draw grid
    step = 64
    for x in range(0, logical_size[0], step):
        pygame.draw.line(surf, fg_color, (x, 0), (x, logical_size[1]), 1)
    for y in range(0, logical_size[1], step):
        pygame.draw.line(surf, fg_color, (0, y), (logical_size[0], y), 1)
    # label
    try:
        txt = font.render(label, True, (255, 255, 255))
        surf.blit(txt, (16, 16))
    except Exception:
        pass
    return surf


def make_char_placeholder(actor: str, font: pygame.font.Font) -> pygame.Surface:
    w, h = 500, 900
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((80, 80, 120, 255))
    pygame.draw.rect(surf, (200, 200, 240, 255), surf.get_rect(), 4)
    try:
        txt = font.render(actor, True, (255, 255, 255))
        rect = txt.get_rect(center=(w // 2, 40))
        surf.blit(txt, rect)
    except Exception:
        pass
    return surf


def make_pose_placeholder(emotion: str, font: pygame.font.Font) -> pygame.Surface:
    w, h = 500, 900
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    banner = pygame.Surface((w, 60), pygame.SRCALPHA)
    banner.fill((0, 0, 0, 120))
    overlay.blit(banner, (0, 60))
    try:
        txt = font.render(f"{emotion}", True, (255, 255, 0))
        rect = txt.get_rect(center=(w // 2, 90))
        overlay.blit(txt, rect)
    except Exception:
        pass
    return overlay
