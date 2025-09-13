from __future__ import annotations

from typing import Optional
import pygame


def trigger_effect(renderer, args: str) -> None:
    """Parse and trigger an EF effect on the active or named actor if not suppressed."""
    parts = args.split()
    if not parts:
        return
    kind = parts[0]
    actor = None
    dur = 400
    amp = 24
    if len(parts) >= 2:
        actor = parts[1]
    if len(parts) >= 3:
        try:
            dur = int(parts[2])
        except Exception:
            pass
    if len(parts) >= 4:
        try:
            amp = int(parts[3])
        except Exception:
            pass
    target = actor or renderer.char_layer.active_actor
    if target and not (renderer._suppress_anims_once or renderer._suppress_anims_replay):
        renderer.animator.start(pygame.time.get_ticks(), target, kind, dur, amp)
