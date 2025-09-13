from __future__ import annotations

from typing import Dict, Tuple, Callable, List
import pygame


def draw_debug_hud(surface: pygame.Surface, font: pygame.font.Font, data: Dict[str, object], *, pos: Tuple[int,int]=(12,12)) -> None:
    """Draw a compact diagnostics overlay.

    data: flat dict of simple values; nested dicts are flattened with 'a.b' keys.
    """
    def flatten(prefix: str, obj: object, out: Dict[str, str]):
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else str(k)
                flatten(key, v, out)
        else:
            try:
                out[prefix] = str(obj)
            except Exception:
                out[prefix] = repr(obj)

    flat: Dict[str, str] = {}
    flatten("", data, flat)

    # Build lines and background rect
    lines = [f"{k}: {v}" for k, v in flat.items()]
    if not lines:
        return

    # Measure box
    pad_x, pad_y = 10, 8
    w = 0
    h = pad_y
    for line in lines:
        surf = font.render(line, True, (240, 240, 240))
        w = max(w, surf.get_width())
        h += surf.get_height() + 2
    w += pad_x * 2
    h += pad_y

    # Background with slight transparency
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 170))
    surface.blit(bg, pos)

    # Draw lines
    x = pos[0] + pad_x
    y = pos[1] + pad_y
    for line in lines:
        surf = font.render(line, True, (240, 240, 240))
        surface.blit(surf, (x, y))
        y += surf.get_height() + 2


class DebugHUD:
    """Modular debug HUD manager. Collects metrics from providers and renders them.

    Providers are registered with a root name and a zero-arg callable returning a dict.
    """
    def __init__(self) -> None:
        self.enabled: bool = False
        self._providers: List[Tuple[str, Callable[[], Dict[str, object]]]] = []

    def toggle(self) -> None:
        self.enabled = not self.enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def add_provider(self, name: str, fn: Callable[[], Dict[str, object]]) -> None:
        self._providers.append((str(name or 'core'), fn))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, *, pos: Tuple[int,int]=(12,12)) -> None:
        if not self.enabled:
            return
        data = self.collect()
        draw_debug_hud(surface, font, data, pos=pos)

    def collect(self) -> Dict[str, object]:
        """Collect metrics from providers into a nested dict.

        Safe to call from other threads for read-only debug purposes.
        """
        data: Dict[str, object] = {}
        for root, fn in list(self._providers):
            try:
                payload = fn() or {}
            except Exception:
                payload = {'error': 'provider failed'}
            data[root] = payload
        return data


def make_renderer_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Create a provider that extracts common renderer metrics without hard dependency on types."""
    def provider() -> Dict[str, object]:
        try:
            clock = getattr(renderer, 'clock', None)
            fps = int(clock.get_fps()) if clock else 0
        except Exception:
            fps = 0
        try:
            cur = renderer.textbox.current() if getattr(renderer, 'textbox', None) else None
            line_len = len(cur.text) if cur and getattr(cur, 'text', None) else 0
        except Exception:
            line_len = 0
        try:
            animator = getattr(renderer, 'animator', None)
            counts = getattr(animator, 'counts', None)
            anim_counts = counts() if callable(counts) else {}
        except Exception:
            anim_counts = {}
        # character snapshot
        try:
            chars = getattr(renderer, 'char_layer', None)
            active = getattr(chars, 'active_actor', None)
            char_dict = getattr(chars, 'characters', {}) if chars else {}
            ccount = len(char_dict)
            actors = list(char_dict.keys())
            # debug rects/centers
            rects = chars.last_rects() if chars and hasattr(chars, 'last_rects') else {}
            centers = chars.last_centers() if chars and hasattr(chars, 'last_centers') else {}
            # outfit/action state (if available)
            outfits = getattr(chars, '_outfits', {}) if chars else {}
            actions = getattr(chars, '_actions', {}) if chars else {}
            actors_info = []
            for a in actors:
                info = {
                    'name': a,
                    'active': a == active,
                    'outfit': outfits.get(a),
                    'has_action': actions.get(a) is not None,
                }
                try:
                    r = rects.get(a)
                    if r:
                        info['rect'] = (r.x, r.y, r.w, r.h)
                except Exception:
                    pass
                try:
                    c = centers.get(a)
                    if c:
                        info['center'] = c
                except Exception:
                    pass
                actors_info.append(info)
        except Exception:
            active, ccount, actors_info = None, 0, []

        # backlog snapshot
        try:
            backlog_len = len(getattr(renderer.textbox, 'history', []) or []) if getattr(renderer, 'textbox', None) else 0
        except Exception:
            backlog_len = 0

        # voice snapshot
        try:
            ch = getattr(renderer, '_voice_channel', None)
            voice_playing = bool(ch.get_busy()) if ch else False
            pending_voice = getattr(renderer, '_pending_voice', None)
        except Exception:
            voice_playing, pending_voice = False, None

        # flow snapshot
        try:
            visited = len(getattr(renderer, '_visited_labels', set()) or set())
            has_flow = getattr(renderer, '_flow_graph', None) is not None
        except Exception:
            visited, has_flow = 0, False
        return {
            'fps': fps,
            'typing_enabled': getattr(renderer, '_typing_enabled', False),
            'fast_forward': getattr(renderer, '_fast_forward', False),
            'auto_mode': getattr(renderer, '_auto_mode', False),
            'auto_delay_ms(line)': getattr(renderer, '_auto_delay_line_ms', 0),
            'line': {
                'revealed': getattr(renderer, '_reveal_instant', False),
                'start_ts': getattr(renderer, '_line_start_ts', 0),
                'full_ts': getattr(renderer, '_line_full_ts', None),
                'len': line_len,
            },
            'suppression': {
                'once': getattr(renderer, '_suppress_anims_once', False),
                'replay': getattr(renderer, '_suppress_anims_replay', False),
            },
            'animator': anim_counts,
            'backlog': {
                'visible': getattr(renderer, 'show_backlog', False),
                'len': backlog_len,
            },
            'voice': {
                'playing': voice_playing,
                'pending': bool(pending_voice),
            },
            'flow': {
                'has_graph': has_flow,
                'visited_labels': visited,
            },
            'chars': {
                'active': active,
                'count': ccount,
                'actors': actors_info,
            },
        }

    return provider
