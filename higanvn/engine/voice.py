from __future__ import annotations

import pygame


def prepare_voice(renderer, path: str | None, volume: float | None = None) -> None:
    """Queue a voice clip on the renderer; None or 'none' stops current voice.

    Uses renderer's asset resolution and voice channel/sound fields.
    """
    if not path or (isinstance(path, str) and path.lower() == "none"):
        # stop current voice
        try:
            if renderer._voice_channel:
                renderer._voice_channel.stop()
        except Exception:
            pass
        renderer._pending_voice = None
        renderer._voice_sound = None
        return
    # resolve and preload Sound (do not play yet)
    try:
        resolved = renderer._resolve_asset(path, ["voice", "vo", "voices"])  # allow multiple folder names
        snd = pygame.mixer.Sound(resolved)
        if volume is not None:
            snd.set_volume(max(0.0, min(1.0, float(volume))))
        renderer._pending_voice = (resolved, float(volume) if volume is not None else None)
        renderer._voice_sound = snd
    except Exception:
        # show non-fatal banner
        try:
            renderer.show_banner(f"未找到配音: {path}", color=(200,140,40))
        except Exception:
            pass
