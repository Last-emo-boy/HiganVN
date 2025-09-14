from __future__ import annotations

from typing import Dict, Tuple, Callable, List, Optional
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


def make_system_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider for system/window/frame timing stats independent of game state."""
    def provider() -> Dict[str, object]:
        try:
            size = renderer.screen.get_size() if getattr(renderer, 'screen', None) else (0, 0)
        except Exception:
            size = (0, 0)
        try:
            vsync = bool(getattr(renderer, '_vsync', False))
        except Exception:
            vsync = False
        try:
            target = int(getattr(renderer, '_target_fps', 60))
        except Exception:
            target = 60
        try:
            frame_ms = int(getattr(renderer, '_frame_time_ms', 0))
        except Exception:
            frame_ms = 0
        try:
            last_tf = getattr(renderer, '_last_transform', None)
            scale = last_tf[0] if isinstance(last_tf, tuple) and last_tf else None
        except Exception:
            scale = None
        return {
            'window': {
                'size': size,
                'vsync': vsync,
                'target_fps': target,
            },
            'frame': {
                'last_ms': frame_ms,
                'scale': scale,
            },
        }
    return provider


def make_audio_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider for audio snapshot: BGM, SE (basic), Voice state."""
    def provider() -> Dict[str, object]:
        try:
            bgm_path: Optional[str] = getattr(renderer, '_bgm_path', None)
            bgm_vol: Optional[float] = getattr(renderer, '_bgm_vol', None)
        except Exception:
            bgm_path, bgm_vol = None, None
        try:
            ch = getattr(renderer, '_voice_channel', None)
            voice_playing = bool(ch.get_busy()) if ch else False
        except Exception:
            voice_playing = False
        try:
            pending = getattr(renderer, '_pending_voice', None)
            pending_path = pending[0] if isinstance(pending, tuple) else None
            pending_vol = pending[1] if isinstance(pending, tuple) else None
        except Exception:
            pending_path, pending_vol = None, None
        return {
            'bgm': {
                'path': bgm_path,
                'volume': bgm_vol,
            },
            'voice': {
                'playing': voice_playing,
                'pending_path': pending_path,
                'pending_volume': pending_vol,
            },
        }
    return provider


def make_config_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider for renderer configuration and UI settings snapshot."""
    def provider() -> Dict[str, object]:
        try:
            ui = dict(getattr(renderer, '_config', {}).get('ui', {})) if isinstance(getattr(renderer, '_config', {}), dict) else {}
        except Exception:
            ui = {}
        try:
            typing_speed = float(getattr(renderer, '_typing_speed', 0.0))
            auto_mode = bool(getattr(renderer, '_auto_mode', False))
        except Exception:
            typing_speed, auto_mode = 0.0, False
        return {
            'typing_speed': typing_speed,
            'auto_mode': auto_mode,
            'ui': ui,
        }
    return provider


def make_slots_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider summarizing save slots metadata availability (count and quick hooks)."""
    def provider() -> Dict[str, object]:
        try:
            slots = getattr(renderer, '_slots', {}) or {}
            total = int(slots.get('total', 12)) if isinstance(slots, dict) else 12
            positions = len(slots.get('positions', []) or []) if isinstance(slots, dict) else 0
        except Exception:
            total, positions = 12, 0
        try:
            has_list = getattr(renderer, '_list_slots_hook', None) is not None
            has_delete = getattr(renderer, '_delete_slot_hook', None) is not None
            has_save = getattr(renderer, '_save_slot_hook', None) is not None
            has_load = getattr(renderer, '_load_slot_hook', None) is not None
        except Exception:
            has_list = has_delete = has_save = has_load = False
        return {
            'config': {
                'total': total,
                'positions_defined': positions,
            },
            'hooks': {
                'list': has_list,
                'delete': has_delete,
                'save': has_save,
                'load': has_load,
            }
        }
    return provider


def make_scene_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider for scene/script context: current label, bg/cg, and current line summary."""
    def provider() -> Dict[str, object]:
        try:
            label = getattr(renderer, '_current_label', None)
        except Exception:
            label = None
        try:
            visited = len(getattr(renderer, '_visited_labels', set()) or set())
        except Exception:
            visited = 0
        try:
            bgp: Optional[str] = getattr(renderer, '_bg_path', None)
            cgp: Optional[str] = getattr(renderer, '_cg_path', None)
        except Exception:
            bgp, cgp = None, None
        # current line brief
        try:
            cur = renderer.textbox.current() if getattr(renderer, 'textbox', None) else None
            name = getattr(cur, 'name', None) if cur else None
            text = getattr(cur, 'text', '') if cur else ''
            line = {
                'name': name,
                'len': len(text or ''),
            }
        except Exception:
            line = {'name': None, 'len': 0}
        return {
            'label': label,
            'visited_labels': visited,
            'background': bgp,
            'cg': cgp,
            'line': line,
        }
    return provider


def make_engine_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider exposing script VM state via renderer-injected hooks, if available.

    Expects renderer to expose optional attributes set by Engine:
      - _engine_script_path: pathlib.Path or str
      - _engine_ip: int
      - _engine_call_stack_depth: int
      - _engine_vars_snapshot: dict
    """
    def provider() -> Dict[str, object]:
        try:
            sp = getattr(renderer, '_engine_script_path', None)
            script_file = str(sp) if sp is not None else None
        except Exception:
            script_file = None
        try:
            ip = int(getattr(renderer, '_engine_ip', 0))
        except Exception:
            ip = 0
        try:
            cdepth = int(getattr(renderer, '_engine_call_stack_depth', 0))
        except Exception:
            cdepth = 0
        try:
            vars_snapshot = dict(getattr(renderer, '_engine_vars_snapshot', {}))
        except Exception:
            vars_snapshot = {}
        return {
            'script_file': script_file,
            'ip': ip,
            'call_stack_depth': cdepth,
            'vars': vars_snapshot,
        }
    return provider


def make_cache_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider exposing resource cache stats (images, etc.).

    Currently surfaces image cache metrics from higanvn.engine.image_cache.
    """
    def provider() -> Dict[str, object]:
        try:
            # Lazy import to avoid hard dependency at import time
            from .image_cache import get_stats as _img_stats  # type: ignore
            istats = _img_stats() or {}
        except Exception:
            istats = {}
        return {
            'images': istats.get('images', istats) if isinstance(istats, dict) else {},
        }
    return provider


def make_perf_provider(renderer) -> Callable[[], Dict[str, object]]:
    """Provider for per-frame timing breakdown collected by the renderer.

    Expects renderer to expose:
      - _perf_last: dict(stage->ms)
      - _perf_avg: dict(stage->ms)
      - _perf_frames: int
      - _target_fps, _vsync, clock.get_fps()
    """
    def provider() -> Dict[str, object]:
        try:
            clock = getattr(renderer, 'clock', None)
            fps = int(clock.get_fps()) if clock else 0
        except Exception:
            fps = 0
        try:
            target = int(getattr(renderer, '_target_fps', 60))
        except Exception:
            target = 60
        try:
            vsync = bool(getattr(renderer, '_vsync', False))
        except Exception:
            vsync = False
        try:
            last = dict(getattr(renderer, '_perf_last', {}) or {})
            avg = dict(getattr(renderer, '_perf_avg', {}) or {})
            frames = int(getattr(renderer, '_perf_frames', 0))
        except Exception:
            last, avg, frames = {}, {}, 0
        # Compute simple totals if not provided
        try:
            total_last = sum(float(v) for v in last.values()) if last else None
        except Exception:
            total_last = None
        try:
            total_avg = sum(float(v) for v in avg.values()) if avg else None
        except Exception:
            total_avg = None
        return {
            'fps': fps,
            'target_fps': target,
            'vsync': vsync,
            'frames': frames,
            'last_ms_total': total_last,
            'avg_ms_total': total_avg,
            'stages_last_ms': last,
            'stages_avg_ms': avg,
        }
    return provider

