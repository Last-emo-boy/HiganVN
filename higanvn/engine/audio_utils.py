from __future__ import annotations

from typing import Optional

import pygame


def play_bgm(path: Optional[str], *, volume: float | None, resolve_path) -> None:
    try:
        if path:
            resolved = resolve_path(path)
            pygame.mixer.music.load(resolved)
            if volume is not None:
                pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
            pygame.mixer.music.play(-1)
        else:
            try:
                pygame.mixer.music.fadeout(300)
            except Exception:
                pygame.mixer.music.stop()
    except Exception:
        pass


def play_se(path: str, *, volume: float | None, resolve_path) -> None:
    try:
        resolved = resolve_path(path)
        se = pygame.mixer.Sound(resolved)
        if volume is not None:
            se.set_volume(max(0.0, min(1.0, float(volume))))
        se.play()
    except Exception:
        pass


def load_voice(path: str, *, volume: float | None, resolve_path):
    """Load a voice Sound for later playback; returns pygame.mixer.Sound or None."""
    try:
        resolved = resolve_path(path)
        snd = pygame.mixer.Sound(resolved)
        if volume is not None:
            snd.set_volume(max(0.0, min(1.0, float(volume))))
        return snd
    except Exception:
        return None
