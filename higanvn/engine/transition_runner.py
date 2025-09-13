from __future__ import annotations

import pygame
from higanvn.engine.transitions import fade as fade_transition


def run_fade(renderer, direction: str, duration_ms: int) -> None:
    """Run a fade transition respecting renderer suppression flags.

    Skips entirely when animations are suppressed (scroll/fast-replay),
    otherwise uses transitions.fade with renderer's screen/clock and a base render callback.
    """
    # Skip transition entirely if animations are suppressed (scroll/fast-replay)
    if getattr(renderer, '_suppress_anims_once', False) or getattr(renderer, '_suppress_anims_replay', False):
        renderer._render()
        return
    fade_transition(
        screen=renderer.screen,
        clock=renderer.clock,
        render_base=lambda: renderer._render(flip=False, tick=False),
        direction=direction,
        duration_ms=duration_ms,
    )
