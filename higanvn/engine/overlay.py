from __future__ import annotations

from typing import Optional, Tuple

import pygame
from pygame import Surface


class Overlay:
    """Manages transient UI overlays: error banner and info banner with fade-out.

    Owns its own state (message, since timestamps, color) and draws onto a canvas.
    """

    def __init__(self) -> None:
        self.error_msg: Optional[str] = None
        self.error_since: Optional[int] = None
        self.banner_msg: Optional[str] = None
        self.banner_since: Optional[int] = None
        self.banner_color: Tuple[int, int, int] = (60, 160, 60)

    def reset(self) -> None:
        self.error_msg = None
        self.error_since = None
        self.banner_msg = None
        self.banner_since = None
        self.banner_color = (60, 160, 60)

    # state API
    def show_error(self, message: str) -> None:
        msg = str(message).strip()
        if len(msg) > 160:
            msg = msg[:157] + "..."
        self.error_msg = msg
        self.error_since = None

    def show_banner(self, message: str, color: Tuple[int, int, int] = (60, 160, 60)) -> None:
        msg = str(message).strip()
        if len(msg) > 160:
            msg = msg[:157] + "..."
        self.banner_msg = msg
        self.banner_color = color
        self.banner_since = None

    def dismiss_error(self) -> None:
        self.error_msg = None
        self.error_since = None

    def dismiss_banner(self) -> None:
        self.banner_msg = None
        self.banner_since = None

    # draw API
    def draw_error_banner(self, canvas: Surface, font: pygame.font.Font, now_ms: int, logical_size: Tuple[int, int]) -> None:
        if not self.error_msg:
            return
        if self.error_since is None:
            self.error_since = now_ms
        elapsed = now_ms - (self.error_since or now_ms)
        alpha = 220 if elapsed < 3500 else max(0, 220 - int((elapsed - 3500) / 4))
        if alpha <= 0:
            self.dismiss_error()
            return
        bar_h = 40
        bar = pygame.Surface((logical_size[0], bar_h), pygame.SRCALPHA)
        bar.fill((180, 40, 40, alpha))
        canvas.blit(bar, (0, 0))
        txt = font.render(self.error_msg, True, (255, 255, 255))
        canvas.blit(txt, (12, 8))

    def draw_banner(self, canvas: Surface, font: pygame.font.Font, now_ms: int, logical_size: Tuple[int, int]) -> None:
        if not self.banner_msg:
            return
        if self.banner_since is None:
            self.banner_since = now_ms
        elapsed = now_ms - (self.banner_since or now_ms)
        alpha = 220 if elapsed < 3500 else max(0, 220 - int((elapsed - 3500) / 4))
        if alpha <= 0:
            self.dismiss_banner()
            return
        bar_h = 40
        bar = pygame.Surface((logical_size[0], bar_h), pygame.SRCALPHA)
        r, g, b = self.banner_color
        bar.fill((r, g, b, alpha))
        canvas.blit(bar, (0, 0))
        txt = font.render(self.banner_msg, True, (255, 255, 255))
        canvas.blit(txt, (12, 8))
