from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import pygame
from pygame import Surface

from higanvn.engine.renderer import IRenderer
from higanvn.engine.animator import Animator
from higanvn.ui.textwrap import wrap_text_generic
from higanvn.assets.actors import load_actor_mapping, resolve_actor_folder
from higanvn.ui.textbox import Textbox
from higanvn.engine.overlay import Overlay
from higanvn.engine.surface_utils import scale_to_height
from higanvn.engine.characters import CharacterLayer
from higanvn.engine.endcard import draw_end_card
from higanvn.engine.slots_ui import show_slots_menu
from higanvn.engine.hud_ui import draw_ui_buttons, draw_hints
from higanvn.engine.text_panel import draw_text_panel
from higanvn.engine.backlog_view import draw_backlog
from higanvn.engine.choices_ui import ask_choice as ask_choice_ui
from higanvn.engine.transitions import fade as fade_transition
from higanvn.engine.transition_runner import run_fade
from higanvn.engine.assets_utils import resolve_asset as resolve_asset_util
from higanvn.engine.font_utils import init_font
from higanvn.engine.audio_utils import play_bgm as play_bgm_util, play_se as play_se_util
from higanvn.engine.save_io import slot_thumb_path as io_slot_thumb_path, slot_meta_path as io_slot_meta_path, read_slot_meta as io_read_slot_meta, capture_thumbnail as io_capture_thumbnail, list_slot_metas as io_list_slot_metas
from higanvn.engine.placeholders import make_bg_placeholder, make_char_placeholder, make_pose_placeholder
from higanvn.engine.slots_config import read_slots_config
from higanvn.engine.flow_map import build_flow_graph
from higanvn.engine.flow_map_ui import show_flow_map
from higanvn.engine.debug_hud import DebugHUD, make_renderer_provider, make_system_provider, make_audio_provider, make_config_provider, make_slots_provider, make_scene_provider, make_engine_provider, make_cache_provider, make_perf_provider
from higanvn.engine.debug_window import DebugWindow
from higanvn.engine.settings_menu import open_settings_menu as settings_open
from higanvn.engine.title_menu import show_title_menu as title_show
from higanvn.engine.input_loop import wait_for_advance as input_wait_for_advance
from higanvn.engine.voice import prepare_voice as voice_prepare
from higanvn.engine.backgrounds import set_background as bg_set, set_cg as cg_set
from higanvn.engine.effects import trigger_effect as ef_trigger
from higanvn.engine.stage import set_outfit as stage_set_outfit, set_action as stage_set_action, hide_actor as stage_hide_actor, clear_stage as stage_clear
from higanvn.engine.config_io import load_config, save_config
from higanvn.engine.gallery import open_gallery_ui


# Logical canvas size (16:9)
LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """CJK-aware word/char wrapping using generic utility and pygame font metrics."""
    def measure(s: str) -> int:
        try:
            return font.size(s)[0]
        except Exception:
            return 0

    return wrap_text_generic(text or "", measure, int(max_width))


# moved to higanvn.engine.surface_utils


class PygameRenderer(IRenderer):
    def __init__(self, title: str = "HiganVN", font_path: Optional[str] = None, font_size: int = 28,
                 typing_speed: float = 45.0, auto_mode: bool = False, auto_delay_ms: int = 900,
                 asset_namespace: Optional[str] = None, target_fps: int = 60, vsync: bool = False) -> None:
        pygame.init()
        self.clock = pygame.time.Clock()
        # display options
        self._target_fps = max(10, int(target_fps))
        self._vsync = bool(vsync)
        try:
            # vsync supported on pygame 2.0+
            self.screen = pygame.display.set_mode(LOGICAL_SIZE, pygame.RESIZABLE, vsync=1 if self._vsync else 0)
        except TypeError:
            # fallback if vsync kw not supported by backend
            self.screen = pygame.display.set_mode(LOGICAL_SIZE, pygame.RESIZABLE)
        pygame.display.set_caption(title)
        self.canvas = pygame.Surface(LOGICAL_SIZE).convert_alpha()
        self.bg = None
        # track last background path (for future timeline snapshots)
        self._bg_path = None  # type: Optional[str]

        # asset namespace for asset resolution (needed before font init)
        self._asset_ns = asset_namespace.strip() if isinstance(asset_namespace, str) and asset_namespace.strip() else None

        # keep font config for scaled variants
        self._font_path = font_path
        self._font_size = font_size
        # Prefer a good CJK font if available
        self.font = init_font(font_path, font_size, self._asset_ns)
        self._textbox_owned = True
        self.textbox = Textbox()

        # characters and assets
        self.actor_map = load_actor_mapping(self._asset_ns or ".") or load_actor_mapping(".")
        self.cg = None  # full-screen CG overlay
        # track last CG path (for future timeline snapshots)
        self._cg_path = None  # type: Optional[str]
        self.show_backlog = False

        # UI state
        self._ui_rects = {}
        self._last_transform = None

        # placeholder colors
        self._ph_bg_color = (40, 40, 40)
        self._ph_fg_color = (180, 180, 180)
        # ui fonts (hint)
        self._hint_font = init_font(self._font_path, max(16, int(self._font_size * 0.8)), self._asset_ns)
        # overlay UI (error/info banners)
        self._error_font = init_font(self._font_path, max(18, int(self._font_size)), self._asset_ns)
        self._overlay = Overlay()
        # debug HUD
        self._debug = DebugHUD()
        self._debug.add_provider('renderer', make_renderer_provider(self))
        self._debug.add_provider('system', make_system_provider(self))
        self._debug.add_provider('audio', make_audio_provider(self))
        self._debug.add_provider('config', make_config_provider(self))
        self._debug.add_provider('slots', make_slots_provider(self))
        self._debug.add_provider('scene', make_scene_provider(self))
        self._debug.add_provider('engine', make_engine_provider(self))
        # resource cache & performance providers (added later after fields are initialized)
        # external debug window actions (safe toggles)
        def _dbg_toggle_auto():
            self._auto_mode = not bool(getattr(self, '_auto_mode', False))
            return f"auto={'on' if self._auto_mode else 'off'}"

        def _dbg_toggle_typing():
            cur = bool(getattr(self, '_typing_enabled', False))
            self._typing_enabled = not cur
            return f"typing={'on' if self._typing_enabled else 'off'}"

        def _dbg_stop_voice():
            try:
                ch = getattr(self, '_voice_channel', None)
                if ch is not None and hasattr(ch, 'stop'):
                    ch.stop()
                return 'voice: stopped'
            except Exception:
                return 'voice: failed'

        def _dbg_hide_ui():
            self._ui_hidden = not bool(getattr(self, '_ui_hidden', False))
            return f"ui_hidden={self._ui_hidden}"

        def _dbg_clear_stage():
            try:
                stage_clear(self)
                return 'stage: cleared'
            except Exception:
                return 'stage: failed'

        def _dbg_screenshot():
            try:
                p = self.capture_screenshot()
                if p:
                    self.show_banner(f"已截图: {p}")
                    return str(p)
            except Exception:
                pass
            return "screenshot failed"

        def _dbg_quicksave():
            try:
                if callable(self._qs_hook):
                    self._qs_hook()
                    return "quicksave ok"
            except Exception:
                pass
            return "quicksave n/a"

        def _dbg_quickload():
            try:
                if callable(self._ql_hook):
                    self._ql_hook()
                    return "quickload ok"
            except Exception:
                pass
            return "quickload n/a"

        def _dbg_open_flow_map():
            try:
                self._show_flow_map()
                return "flow map opened"
            except Exception:
                return "flow map failed"

        actions = {
            'Toggle Auto': _dbg_toggle_auto,
            'Toggle Typing': _dbg_toggle_typing,
            'Stop Voice': _dbg_stop_voice,
            'Hide/Show UI': _dbg_hide_ui,
            'Clear Stage': _dbg_clear_stage,
            'Screenshot': _dbg_screenshot,
            'Quick Save': _dbg_quicksave,
            'Quick Load': _dbg_quickload,
            'Open Flow Map': _dbg_open_flow_map,
        }
        # external debug window with persisted preferences
        def _load_prefs():
            try:
                dbg = (self._config.get("debug") if isinstance(self._config, dict) else {}) or {}
                return dict(dbg)
            except Exception:
                return {"theme": "Dark", "ontop": False, "interval_ms": 300}

        def _save_prefs(prefs: Dict[str, object]):
            try:
                if isinstance(self._config, dict):
                    cur = dict(self._config.get("debug", {}))
                    cur.update(dict(prefs))
                    self._config["debug"] = cur
                    save_config(self._config, lambda: self._get_save_dir() if callable(self._get_save_dir) else Path("save"))
            except Exception:
                pass

        self._debug_win = DebugWindow(lambda: self._debug.collect(), actions=actions, prefs=_load_prefs(), on_prefs_save=_save_prefs)
        # UI visibility
        self._ui_hidden = False

        # simple animation registry via helper
        self.animator = Animator()

        # typewriter/auto
        self._typing_speed = max(0.0, float(typing_speed))
        self._typing_enabled = self._typing_speed > 0.0
        self._fast_forward = False
        self._auto_mode = bool(auto_mode)
        # Auto-advance timing
        self._auto_delay_ms = max(0, int(auto_delay_ms))
        self._auto_delay_per_char_ms = 35  # extra ms per character
        self._auto_delay_min_ms = 700      # minimum total delay per line
        self._auto_delay_max_ms = 6000     # maximum total delay per line
        self._auto_delay_line_ms = self._auto_delay_ms
        self._line_start_ts = 0
        self._line_full_ts = None
        self._reveal_instant = False

        # audio fades
        self._bgm_fade_ms = 300
        self._bgm_path = None  # type: Optional[str]
        self._bgm_vol = None   # type: Optional[float]
        # voice channel
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self._voice_channel = None
        try:
            self._voice_channel = pygame.mixer.Channel(7)
        except Exception:
            self._voice_channel = None
        self._pending_voice = None  # tuple(path, volume)
        self._voice_sound = None

        # ui slots & scale (from optional config)
        self._slots = read_slots_config(self._asset_ns, LOGICAL_SIZE)
        # character layer manages characters and active actor
        self.char_layer = CharacterLayer(self._slots)
        try:
            # ensure char layer inherits current strict flag
            if hasattr(self.char_layer, 'set_strict_mode'):
                self.char_layer.set_strict_mode(getattr(self, '_strict_mode', False))  # type: ignore[attr-defined]
        except Exception:
            pass
        # ui config
        try:
            self._config = load_config(lambda: self._get_save_dir() if callable(self._get_save_dir) else Path("save"))
        except Exception:
            self._config = {"ui": {}}

        # hooks for quick save/load (set by Engine/CLI)
        self._qs_hook = None
        self._ql_hook = None
        # hooks for slot save/load
        self._save_slot_hook = None
        self._load_slot_hook = None
        # hooks for listing/deleting slots (optional)
        self._list_slots_hook = None
        self._delete_slot_hook = None
        # hook for back/rewind one line
        self._back_hook = None
        # callback to get save dir from engine (optional)
        self._get_save_dir = None
        # keep a copy of last fully rendered canvas for proper thumbnail capture
        self._last_frame = None
        self._frame_time_ms = 0
        # performance counters
        self._perf_last = {}
        self._perf_avg = {}
        self._perf_frames = 0
        # now that timing fields exist, register providers
        try:
            self._debug.add_provider('cache', make_cache_provider(self))
            self._debug.add_provider('perf', make_perf_provider(self))
        except Exception:
            pass
        # fast replay mode (engine reconstruction): no flip/tick and no typewriter
        self._fast_replay_mode = False
        self._typing_enabled_prev = self._typing_enabled
        # flow map context
        self._program = None
        self._flow_graph = None
        self._visited_labels = set()
        self._label_thumbs = {}
        self._current_label = None
        # one-shot suppression of auto-advance after a back/rewind action
        self._suppress_auto_once = False
        # animation suppression flags
        self._suppress_anims_once = False   # consume on next show_text/command
        self._suppress_anims_replay = False # active during fast replay
        # external debug providers and jump hook placeholders
        self._ext_debug_providers = {}
        self._jump_to_label_hook = None
    

    # --- asset path helpers (prefer standardized folders and per-script namespace) ---
    def _resolve_asset(self, path: str, prefixes: Optional[list[str]] = None) -> str:
        return resolve_asset_util(path, asset_namespace=self._asset_ns, prefixes=prefixes or [])

    # font init moved to font_utils.init_font

    def _pump(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit

    def _render(self, flip: bool = True, tick: bool = True) -> None:
        import time as _t
        t0 = _t.perf_counter()
        # suppress present/sleep in fast replay mode
        if self._fast_replay_mode:
            flip = False
            tick = False
        self.canvas.fill((0, 0, 0, 255))
        t_bg_begin = _t.perf_counter()
        if self.bg:
            self.canvas.blit(self.bg, (0, 0))
        if self.cg:
            # CG is pre-scaled when set; blit directly
            self.canvas.blit(self.cg, (0, 0))
        t_bg = (_t.perf_counter() - t_bg_begin) * 1000.0
        # characters and overlays
        t_char_begin = _t.perf_counter()
        now = pygame.time.get_ticks()
        self.char_layer.render(self.canvas, self.animator, now)
        t_char = (_t.perf_counter() - t_char_begin) * 1000.0
        # debug overlays (character bounds/centers)
        try:
            t_dbg_begin = _t.perf_counter()
            self._draw_debug_overlays()
            t_dbg = (_t.perf_counter() - t_dbg_begin) * 1000.0
        except Exception:
            t_dbg = 0.0
        # overlays
        t_ui_begin = _t.perf_counter()
        if not self._ui_hidden:
            self._overlay.draw_error_banner(self.canvas, self._error_font, now, LOGICAL_SIZE)
            self._overlay.draw_banner(self.canvas, self._error_font, now, LOGICAL_SIZE)
        cur = self.textbox.current()
        if cur and not self._ui_hidden:
            name, text = cur.name, cur.text
            if (isinstance(name, str) and name.strip().startswith("结局")) or (
                (name is None) and isinstance(text, str) and text.strip().startswith("结局")
            ):
                draw_end_card(self.canvas, text, self._hint_font, self.font, self._font_path, self._font_size)
            else:
                # ui config for textbox and text effects
                ui_cfg = (self._config.get("ui") if isinstance(self._config, dict) else {}) or {}
                self._reveal_instant, self._line_start_ts, self._line_full_ts = draw_text_panel(
                    self.canvas,
                    self.font,
                    self._hint_font,
                    name,
                    text,
                    getattr(cur, 'effect', None),
                    self._typing_enabled,
                    self._fast_forward,
                    self._line_start_ts,
                    self._line_full_ts,
                    self._reveal_instant,
                    panel_alpha=int(ui_cfg.get("textbox_opacity", 160)),
                    text_outline=bool(ui_cfg.get("text_outline", False)),
                    text_shadow=bool(ui_cfg.get("text_shadow", True)),
                    text_shadow_offset=tuple(ui_cfg.get("text_shadow_offset", [1, 1])),
                )
        if (not self._ui_hidden) and self.show_backlog and self.textbox.history:
            draw_backlog(self.canvas, self.font, self.textbox.history, self.textbox.view_idx)
        self._ui_rects = draw_ui_buttons(self.canvas, self.font, self._canvas_mouse_pos) if not self._ui_hidden else {}
        t_ui = (_t.perf_counter() - t_ui_begin) * 1000.0
        # Optional debug HUD
        t_hud_begin = _t.perf_counter()
        if not self._ui_hidden:
            try:
                self._debug.draw(self.canvas, self._hint_font)
            except Exception:
                pass
            draw_hints(self.canvas, self._hint_font, self._auto_mode)
        t_hud = (_t.perf_counter() - t_hud_begin) * 1000.0

        t_scale_begin = _t.perf_counter()
        win_w, win_h = self.screen.get_size()
        scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
        dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
        scaled = pygame.transform.smoothscale(self.canvas, (dst_w, dst_h))
        x = (win_w - dst_w) // 2
        y = (win_h - dst_h) // 2
        self._last_transform = (scale, x, y, dst_w, dst_h)
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, (x, y))
        t_scale = (_t.perf_counter() - t_scale_begin) * 1000.0
        if flip:
            t_flip_begin = _t.perf_counter()
            pygame.display.flip()
            t_flip = (_t.perf_counter() - t_flip_begin) * 1000.0
        else:
            t_flip = 0.0
        if tick:
            t_tick_begin = _t.perf_counter()
            self.clock.tick(self._target_fps)
            t_tick = (_t.perf_counter() - t_tick_begin) * 1000.0
            try:
                self._frame_time_ms = int(self.clock.get_time())
            except Exception:
                self._frame_time_ms = 0
        else:
            t_tick = 0.0
        # store last frame after presenting
        self._last_frame = self.canvas.copy()
        # update perf counters
        t_total = (_t.perf_counter() - t0) * 1000.0
        stages = {
            'bg_cg': round(t_bg, 3),
            'characters': round(t_char, 3),
            'overlays_ui': round(t_ui, 3),
            'debug_overlay': round(t_dbg, 3),
            'hud': round(t_hud, 3),
            'scale_blit': round(t_scale, 3),
            'flip': round(t_flip, 3),
            'tick': round(t_tick, 3),
            'total': round(t_total, 3),
        }
        self._perf_last = stages
        # Exponential moving average
        alpha = 0.2
        if not self._perf_avg:
            self._perf_avg = dict(stages)
        else:
            for k, v in stages.items():
                try:
                    prev = float(self._perf_avg.get(k, v))
                    self._perf_avg[k] = round((1 - alpha) * prev + alpha * float(v), 3)
                except Exception:
                    self._perf_avg[k] = round(float(v), 3)
        try:
            self._perf_frames = int(self._perf_frames) + 1
        except Exception:
            self._perf_frames = 1

    # --- snapshot helpers ---
    def get_snapshot(self) -> dict:
        """Collect a minimal renderer snapshot for deterministic restoration.

        Returns:
            dict with keys: bg, cg, characters (list of logical states), auto, typing_speed
        """
        try:
            chars = []
            if hasattr(self, 'char_layer') and hasattr(self.char_layer, 'snapshot_characters'):
                chars = list(self.char_layer.snapshot_characters())  # type: ignore[attr-defined]
        except Exception:
            chars = []
        return {
            "bg": getattr(self, "_bg_path", None),
            "cg": getattr(self, "_cg_path", None),
            "characters": chars,
            "auto": bool(getattr(self, "_auto_mode", False)),
            "typing_speed": float(getattr(self, "_typing_speed", 0.0)),
            "bgm": {"path": getattr(self, "_bgm_path", None), "volume": getattr(self, "_bgm_vol", None)},
            "voice": {
                "pending": {
                    "path": (self._pending_voice[0] if isinstance(self._pending_voice, tuple) else None) if self._pending_voice else None,
                    "volume": (self._pending_voice[1] if isinstance(self._pending_voice, tuple) else None) if self._pending_voice else None,
                },
            },
        }

    def apply_snapshot(self, snap: dict) -> None:
        """Apply a renderer snapshot captured by get_snapshot().

        Safe best-effort; missing assets fall back to placeholders.
        """
        # restore simple playback flags first
        try:
            ts = snap.get("typing_speed")
            if ts is not None:
                self._typing_speed = max(0.0, float(ts))
                self._typing_enabled = self._typing_speed > 0.0
        except Exception:
            pass
        try:
            auto = snap.get("auto")
            if auto is not None:
                self._auto_mode = bool(auto)
        except Exception:
            pass
        try:
            bgp = snap.get("bg")
            self.set_background(bgp if bgp else None)
        except Exception:
            pass
        # restore bgm (best effort)
        try:
            bgm = snap.get("bgm") or {}
            p = bgm.get("path")
            v = bgm.get("volume")
            if p is not None or v is not None:
                self.play_bgm(p, v)
        except Exception:
            pass
        try:
            cgp = snap.get("cg")
            # route through command path for CG to ensure consistency
            self.command("CG", str(cgp or "None"))
        except Exception:
            pass
        # restore voice pending (best effort)
        try:
            v = snap.get("voice") or {}
            pen = v.get("pending") or {}
            vp = pen.get("path")
            vv = pen.get("volume")
            if vp is not None or vv is not None:
                self.prepare_voice(vp, vv)
        except Exception:
            pass
        try:
            chars = snap.get("characters") or []
            for ch in chars:
                actor = ch.get("id")
                outfit = ch.get("outfit")
                pose = ch.get("pose")
                action = ch.get("action")
                if not actor:
                    continue
                # ensure actor present
                try:
                    stage_set_outfit(self, actor, outfit)
                except Exception:
                    pass
                # set pose if provided
                try:
                    if pose:
                        self.char_layer.ensure_loaded(actor, self._resolve_asset, lambda lbl: make_char_placeholder(lbl, self.font))
                        self.char_layer.set_pose(actor, str(pose), self._resolve_asset, lambda emo: make_pose_placeholder(emo, self.font))
                except Exception:
                    pass
                # set action if provided
                try:
                    stage_set_action(self, actor, action)
                except Exception:
                    pass
        except Exception:
            pass

    # --- timing/display config ---
    def set_frame_rate(self, fps: int) -> None:
        try:
            self._target_fps = max(10, int(fps))
        except Exception:
            self._target_fps = 60

    def set_vsync(self, enabled: bool) -> None:
        flag = bool(enabled)
        if flag == self._vsync:
            return
        self._vsync = flag
        try:
            # Recreate display with current size and flags
            sz = self.screen.get_size()
            self.screen = pygame.display.set_mode(sz, pygame.RESIZABLE, vsync=1 if self._vsync else 0)
        except Exception:
            # backend may not support toggling; ignore
            pass

    # old UI drawing helpers removed; now provided by hud_ui module

    def set_background(self, path: Optional[str]) -> None:
        self._pump()
        bg_set(self, path)
        try:
            self._bg_path = str(path) if path is not None else None
        except Exception:
            self._bg_path = None
        self._render()

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:
        self._pump()
        play_bgm_util(path, volume=volume, resolve_path=lambda p: self._resolve_asset(p, ["bgm"]))
        try:
            self._bgm_path = path if path else None
            self._bgm_vol = float(volume) if volume is not None else None
        except Exception:
            self._bgm_path, self._bgm_vol = None, None

    def play_se(self, path: str, volume: float | None = None) -> None:
        self._pump()
        play_se_util(path, volume=volume, resolve_path=lambda p: self._resolve_asset(p, ["se"]))

    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:
        """Queue a voice clip to play with the next dialogue line, or None to stop current voice."""
        self._pump()
        voice_prepare(self, path, volume)

    def show_text(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        self._pump()
        self.textbox.push(name, text, meta)
        # reset typewriter state for new line
        self._line_start_ts = 0
        self._line_full_ts = None
        self._reveal_instant = False
        # compute per-line auto delay based on content length (independent of typewriter speed)
        try:
            txt = str(text or "")
            # basic length; future: could weight punctuation/newlines differently
            n = len(txt)
            total = int(self._auto_delay_ms + self._auto_delay_per_char_ms * n)
            # clamp to sane bounds
            if total < self._auto_delay_min_ms:
                total = self._auto_delay_min_ms
            if total > self._auto_delay_max_ms:
                total = self._auto_delay_max_ms
            self._auto_delay_line_ms = total
        except Exception:
            # fallback to base if anything goes wrong
            self._auto_delay_line_ms = self._auto_delay_ms
        # start pending voice if any
        try:
            if self._voice_sound and self._voice_channel:
                self._voice_channel.stop()
                self._voice_channel.play(self._voice_sound)
                # clear pending so it won't repeat next lines unless re-prepared
                self._pending_voice = None
                self._voice_sound = None
        except Exception:
            pass
        if name:
            actor_disp = name.split('|', 1)[0]
            folder = resolve_actor_folder(actor_disp, self.actor_map)
            self.char_layer.active_actor = folder
            # ensure character assets
            # Detect first-time appearance: if not loaded yet, ensure then trigger entrance anim
            first_appear = folder not in self.char_layer.characters
            self.char_layer.ensure_loaded(folder, self._resolve_asset, lambda lbl: make_char_placeholder(lbl, self.font))
            if first_appear and folder and not (self._suppress_anims_once or self._suppress_anims_replay):
                # short, subtle slide-in from bottom; 360ms, 120px
                try:
                    self.animator.start(pygame.time.get_ticks(), folder, "slide_in_d", 360, 120)
                except Exception:
                    pass
            if meta and meta.get("emotion"):
                self.char_layer.set_pose(folder, str(meta["emotion"]), self._resolve_asset, lambda emo: make_pose_placeholder(emo, self.font))
            # trigger simple animations based on effect tags
            if meta and meta.get("effect") and not (self._suppress_anims_once or self._suppress_anims_replay):
                self.animator.trigger_by_effect(pygame.time.get_ticks(), folder, str(meta.get("effect")))
        self._render()
        # consume one-shot animation suppression after rendering this line
        if self._suppress_anims_once:
            self._suppress_anims_once = False

    def command(self, name: str, args: str) -> None:
        self._pump()
        up = name.upper()
        if up == "CG":
            arg = args.strip()
            cg_set(self, arg)
            try:
                self._cg_path = arg if arg else None
            except Exception:
                self._cg_path = None
        elif up == "FADE":
            # Syntax: > FADE [in|out] [duration_ms]
            parts = args.split()
            direction = parts[0].lower() if parts else "in"
            try:
                duration = int(parts[1]) if len(parts) > 1 else 400
            except Exception:
                duration = 400
            self._fade(direction, duration)
        elif up == "EF":
            ef_trigger(self, args)
        elif up == "OUTFIT":
            # Syntax: > OUTFIT <actor_display_name> <folder|None>
            parts = args.split()
            if parts:
                display = parts[0]
                outfit = parts[1] if len(parts) > 1 else None
                stage_set_outfit(self, display, outfit)
        elif up == "ACTION":
            # Syntax: > ACTION <actor_display_name> <name|None>
            parts = args.split()
            if parts:
                display = parts[0]
                action = parts[1] if len(parts) > 1 else None
                stage_set_action(self, display, action)
        elif up == "HIDE":
            # Syntax: > HIDE <actor_display_name>
            display = args.strip()
            if display:
                stage_hide_actor(self, display)
        elif up == "CLEAR_STAGE":
            # Syntax: > CLEAR_STAGE
            stage_clear(self)
        # EF or others are ignored for now
        self._render()

    def _fade(self, direction: str, duration_ms: int) -> None:
        run_fade(self, direction, duration_ms)

    def wait_for_advance(self) -> None:
        input_wait_for_advance(self)

    def ask_choice(self, choices: list[tuple[str, str]]) -> int:
        return ask_choice_ui(
            choices=choices,
            screen=self.screen,
            canvas=self.canvas,
            clock=self.clock,
            font=self.font,
            render_base=lambda flip=False, tick=False: self._render(flip=flip, tick=tick),
        )

    def _render_ending_banner(self, text: str) -> None:
        # backward-compat wrapper; prefer draw_end_card
        draw_end_card(self.canvas, text, self._hint_font, self.font, self._font_path, self._font_size)

    def _canvas_mouse_pos(self) -> Optional[tuple[int, int]]:
        if not self._last_transform:
            return None
        mx, my = pygame.mouse.get_pos()
        scale, offx, offy, dst_w, dst_h = self._last_transform
        if not (offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h):
            return None
        cx = int((mx - offx) / scale)
        cy = int((my - offy) / scale)
        return (cx, cy)

    def _draw_debug_overlays(self) -> None:
        if not getattr(self._debug, 'enabled', False):
            return
        chars = getattr(self, 'char_layer', None)
        if not chars:
            return
        try:
            rects = chars.last_rects()
            centers = chars.last_centers()
        except Exception:
            rects, centers = {}, {}
        for actor, rect in rects.items():
            color = (0, 220, 90) if actor == getattr(chars, 'active_actor', None) else (255, 215, 0)
            try:
                pygame.draw.rect(self.canvas, color, rect, width=2)
            except Exception:
                continue
            cx, cy = centers.get(actor, rect.center)
            try:
                pygame.draw.line(self.canvas, color, (cx - 6, cy), (cx + 6, cy), 2)
                pygame.draw.line(self.canvas, color, (cx, cy - 6), (cx, cy + 6), 2)
            except Exception:
                pass
            # actor label
            try:
                label = str(actor)
                ts = self._hint_font.render(label, True, (255, 255, 255))
                bg = pygame.Surface((ts.get_width() + 6, ts.get_height() + 2), pygame.SRCALPHA)
                bg.fill((0, 0, 0, 160))
                lx = max(0, min(rect.left, LOGICAL_SIZE[0] - bg.get_width()))
                ly = max(0, rect.top - bg.get_height() - 2)
                self.canvas.blit(bg, (lx, ly))
                self.canvas.blit(ts, (lx + 3, ly + 1))
            except Exception:
                pass

        # slot position guides
        try:
            slots = getattr(self, '_slots', {}) or {}
            pos_list = slots.get('positions') or []
            for i, (sx, sy) in enumerate(pos_list):
                try:
                    pygame.draw.circle(self.canvas, (80, 200, 250), (int(sx), int(sy)), 8, 2)
                    lbl = self._hint_font.render(str(i), True, (255, 255, 255))
                    self.canvas.blit(lbl, (int(sx) + 10, int(sy) - 10))
                except Exception:
                    continue
        except Exception:
            pass

    # character helpers moved to CharacterLayer

    # --- simple animations ---
    # removed in favor of Animator helper

    # --- placeholders ---
    # moved to slots_config.read_slots_config

    # exposed for Engine strict-mode errors
    def show_error(self, message: str) -> None:
        self._overlay.show_error(message)
    
    def show_banner(self, message: str, color: Tuple[int, int, int] = (60, 160, 60)) -> None:
        self._overlay.show_banner(message, color)

    def capture_screenshot(self) -> Optional[Path]:
        """Capture the current canvas to save/screenshots with a timestamped filename.

        Returns the saved path on success, else None.
        """
        try:
            base_dir = (self._get_save_dir or (lambda: Path("save")))()
            out_dir = Path(base_dir) / "screenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            p = out_dir / f"shot_{ts}.png"
            src = self._last_frame if isinstance(self._last_frame, pygame.Surface) else self.canvas
            pygame.image.save(src, str(p))
            return p
        except Exception:
            return None
    # removed: _draw_banner/_draw_error_banner (now in Overlay)

    # hooks setters
    def set_quicksave_hook(self, fn: Callable[[], bool]) -> None:
        self._qs_hook = fn

    def set_quickload_hook(self, fn: Callable[[], bool]) -> None:
        self._ql_hook = fn

    def set_back_hook(self, fn: Callable[[], bool]) -> None:
        self._back_hook = fn
    def set_save_slot_hook(self, fn: Callable[[int], bool]) -> None:
        self._save_slot_hook = fn
    def set_load_slot_hook(self, fn: Callable[[int], bool]) -> None:
        self._load_slot_hook = fn
    def set_get_save_dir(self, fn: Callable[[], Path]) -> None:
        self._get_save_dir = fn
    def set_list_slots_hook(self, fn: Callable[[], list[int]]) -> None:
        self._list_slots_hook = fn
    def set_delete_slot_hook(self, fn: Callable[[int], bool]) -> None:
        self._delete_slot_hook = fn

    # --- load/rollback helpers ---
    def begin_fast_replay(self) -> None:
        """Enter fast replay mode: disable typewriter and skip flips to speed reconstruction."""
        self._fast_replay_mode = True
        self._typing_enabled_prev = self._typing_enabled
        # During fast replay, suppress animations and typing to avoid delays
        self._suppress_anims_replay = True
        self._typing_enabled = False

    def end_fast_replay(self) -> None:
        """Exit fast replay mode and restore UI behavior."""
        self._fast_replay_mode = False
        self._typing_enabled = self._typing_enabled_prev
        self._suppress_anims_replay = False

    def reset_state(self) -> None:
        """Clear visual state so the engine can deterministically rebuild prior frames.

        Intentionally does not clear the shared Textbox model (owned by the Engine).
        """
        # Clear background and CG overlay
        self.bg = None
        self.cg = None
        # Clear tracked asset paths
        try:
            self._bg_path = None
            self._cg_path = None
        except Exception:
            pass
        # Reset character layer and animations
        self.char_layer = CharacterLayer(self._slots)
        self.animator = Animator()
        # Reset typing/reveal state
        self._line_start_ts = 0
        self._line_full_ts = None
        self._reveal_instant = False
        # Reset playback flags
        self._auto_mode = False
        self._fast_forward = False
        self._suppress_auto_once = False
        self._suppress_anims_once = False
        self._suppress_anims_replay = False
        # Drop last frame so thumbnails don't show stale visuals
        self._last_frame = None
        # Clear transient overlays
        try:
            self._overlay.dismiss_error()
            self._overlay.dismiss_banner()
        except Exception:
            pass
        # stop any voice
        try:
            if self._voice_channel:
                self._voice_channel.stop()
        except Exception:
            pass
        # stop BGM if playing
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        # ensure backlog view follows current
        try:
            if hasattr(self, "textbox") and self.textbox:
                self.textbox.view_idx = -1
        except Exception:
            pass

    # --- flow map integration ---
    def set_program(self, program) -> None:
        self._program = program
        try:
            self._flow_graph = build_flow_graph(program)
        except Exception:
            self._flow_graph = None

    def on_enter_label(self, label: str) -> None:
        try:
            name = str(label)
            # track current label so saves can record it
            self._current_label = name
            self._visited_labels.add(name)
            # capture a small thumb for this label if possible
            if isinstance(self._last_frame, pygame.Surface):
                self._label_thumbs[name] = self._last_frame.copy()
        except Exception:
            pass

    def _label_thumbnail(self, label: str) -> Optional[pygame.Surface]:
        # Prefer cached per-label thumbnail
        surf = self._label_thumbs.get(label)
        if isinstance(surf, pygame.Surface):
            return surf
        # fallback: last frame
        return self._last_frame if isinstance(self._last_frame, pygame.Surface) else None

    def _show_flow_map(self) -> None:
        if not self._flow_graph:
            return
        show_flow_map(
            screen=self.screen,
            canvas=self.canvas,  
            clock=self.clock,
            font=self.font,
            error_font=self._error_font,
            render_base=lambda flip=False, tick=False: self._render(flip=flip, tick=tick),
            get_last_transform=lambda: self._last_transform,
            flow=self._flow_graph,
            visited_labels=self._visited_labels,
            slot_thumb_for_label=lambda name: self._label_thumbnail(name),
        )
    # (duplicate methods removed below)

    # --- slot UI & thumbnails ---
    def _slot_thumb_path(self, slot: int) -> Path:
        return io_slot_thumb_path(slot, get_save_dir=self._get_save_dir or (lambda: Path("save")))

    def _slot_meta_path(self, slot: int) -> Path:
        return io_slot_meta_path(slot, get_save_dir=self._get_save_dir or (lambda: Path("save")))

    def _read_slot_meta(self, slot: int) -> Optional[dict]:
        return io_read_slot_meta(slot, get_save_dir=self._get_save_dir or (lambda: Path("save")))

    def _capture_thumbnail(self, slot: int) -> None:
        src = self._last_frame if isinstance(self._last_frame, pygame.Surface) else self.canvas
        io_capture_thumbnail(src, slot, get_save_dir=self._get_save_dir or (lambda: Path("save")))

    def _show_slots_menu(self, mode: str = "save", total: int = 12) -> Optional[int]:
        # preload metas for performance
        pre = {}
        try:
            pre = io_list_slot_metas(get_save_dir=self._get_save_dir or (lambda: Path("save")))
        except Exception:
            pre = {}
        return show_slots_menu(
            mode=mode,
            total=total,
            canvas=self.canvas,
            screen=self.screen,
            clock=self.clock,
            hint_font=self._hint_font,
            error_font=self._error_font,
            render_base=lambda flip=False, tick=False: self._render(flip=flip, tick=tick),
            get_last_transform=lambda: self._last_transform,
            read_slot_meta=lambda i: pre.get(int(i)) if pre else self._read_slot_meta(i),
            slot_thumb_path=self._slot_thumb_path,
            list_slots=self._list_slots_hook,
            delete_slot=self._delete_slot_hook,
        )
    # moved to placeholders module: make_bg_placeholder, make_char_placeholder, make_pose_placeholder

    # --- Menus & system actions ---
    def open_slots_menu(self, mode: str = "load") -> Optional[int]:  # type: ignore[override]
        slot = self._show_slots_menu(mode)
        if slot is None:
            return None
        ok = False
        try:
            if mode == "save" and self._save_slot_hook:
                # capture thumbnail first on save
                try:
                    self._capture_thumbnail(int(slot))
                except Exception:
                    pass
                ok = bool(self._save_slot_hook(int(slot)))
            if mode == "load" and self._load_slot_hook:
                ok = bool(self._load_slot_hook(int(slot)))
        except Exception:
            ok = False
        if ok:
            self.show_banner(("保存到槽位 %02d" if mode == "save" else "读取槽位 %02d 成功") % int(slot))
            # If loaded, leave to caller to continue
        else:
            self.show_banner("操作失败", color=(200,140,40))
        return int(slot)

    # --- interface additions ---
    def add_debug_provider(self, name: str, fn) -> None:  # type: ignore[override]
        try:
            self._ext_debug_providers[str(name)] = fn
            self._debug.add_provider(str(name), fn)
        except Exception:
            pass

    def set_jump_to_label_hook(self, fn) -> None:  # type: ignore[override]
        self._jump_to_label_hook = fn

    def open_settings_menu(self) -> None:  # type: ignore[override]
        before = dict(self._config)
        settings_open(self)
        # persist ui-related config changes from renderer fields
        try:
            # collect current ui options
            ui = dict(self._config.get("ui", {}))
            # typing speed/auto are already in renderer fields; textbox opacity & effects in config only
            self._config["ui"] = ui
            save_config(self._config, lambda: self._get_save_dir() if callable(self._get_save_dir) else Path("save"))
        except Exception:
            pass

    def open_gallery(self) -> None:  # type: ignore[override]
        try:
            open_gallery_ui(
                screen=self.screen,
                canvas=self.canvas,
                clock=self.clock,
                font=self.font,
                resolve_path=lambda p, prefs=None: self._resolve_asset(p, (prefs or ["cg"])) ,
                get_save_dir=self._get_save_dir if callable(self._get_save_dir) else (lambda: Path("save"))
            )
        except Exception:
            self.show_banner("CG 画廊打开失败", color=(200,140,40))

    def quit(self) -> None:  # type: ignore[override]
        pygame.quit()
        raise SystemExit

    def show_title_menu(self, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:  # type: ignore[override]
        return title_show(self, title, bg_path)

    # --- engine-managed flags ---
    def set_strict_mode(self, strict: bool) -> None:  # type: ignore[override]
        self._strict_mode = bool(strict)
        try:
            if hasattr(self, 'char_layer') and hasattr(self.char_layer, 'set_strict_mode'):
                self.char_layer.set_strict_mode(self._strict_mode)  # type: ignore[attr-defined]
        except Exception:
            pass
