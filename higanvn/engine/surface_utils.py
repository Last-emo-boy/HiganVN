from __future__ import annotations

import pygame
from pygame import Surface


def scale_to_height(surf: Surface, target_h: int) -> Surface:
    if not isinstance(surf, Surface):
        return surf
    w, h = surf.get_size()
    if h <= 0:
        return surf
    ratio = float(target_h) / float(h)
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(target_h))
    return pygame.transform.smoothscale(surf, (new_w, new_h))
