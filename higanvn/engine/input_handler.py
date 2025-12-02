"""
Input Event Handler for HiganVN

Decouples input processing from renderer by using the typed event system.
"""
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING, Optional, Callable, Any

from .events import (
    EventSystem, Priority,
    KeyDownEvent, KeyUpEvent, MouseClickEvent, MouseWheelEvent,
    AdvanceRequestEvent, BacklogToggleEvent, UIHiddenEvent,
    MenuOpenEvent, ScreenshotEvent, FlowMapEvent, DebugToggleEvent,
    AutoModeEvent, FastForwardEvent
)

if TYPE_CHECKING:
    from .renderer_pygame import PygameRenderer


class InputHandler:
    """
    Handles input events and dispatches them through the event system.
    
    This decouples input handling from the renderer, allowing:
    - Custom key bindings
    - Input recording/playback
    - Accessibility features
    - Plugin input handling
    """
    
    # Default key bindings
    ADVANCE_KEYS = {pygame.K_RETURN, pygame.K_SPACE}
    SCROLL_UP_KEYS = {pygame.K_UP, pygame.K_PAGEUP}
    SCROLL_DOWN_KEYS = {pygame.K_DOWN, pygame.K_PAGEDOWN}
    BACKLOG_TOGGLE_KEY = pygame.K_TAB
    UI_HIDE_KEY = pygame.K_h
    SCREENSHOT_KEY = pygame.K_F12
    FLOW_MAP_KEY = pygame.K_m
    DEBUG_KEY = pygame.K_F3
    AUTO_MODE_KEY = pygame.K_a
    FAST_FORWARD_KEY = pygame.K_f
    QUICKSAVE_KEY = pygame.K_F5
    QUICKLOAD_KEY = pygame.K_F9
    SAVE_MENU_KEY = pygame.K_F7
    LOAD_MENU_KEY = pygame.K_F8
    
    def __init__(self, renderer: 'PygameRenderer', event_system: EventSystem):
        self.renderer = renderer
        self.events = event_system
        self._fast_forward_held = False
        
        # Subscribe to our own events for default handling
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Set up default event handlers with low priority (allow override)."""
        pass  # Handlers are in process_event for now; can be refactored
    
    def process_pygame_event(self, event: pygame.event.Event) -> bool:
        """
        Process a pygame event and dispatch typed events.
        
        Returns True if the event was consumed (should stop waiting loop).
        """
        if event.type == pygame.QUIT:
            raise SystemExit
        
        if event.type == pygame.VIDEORESIZE:
            self.renderer._render()
            return False
        
        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        
        if event.type == pygame.KEYUP:
            return self._handle_keyup(event)
        
        if event.type == pygame.MOUSEWHEEL:
            return self._handle_mousewheel(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouseclick(event)
        
        return False
    
    def _handle_keydown(self, event: pygame.event.Event) -> bool:
        """Handle key press events."""
        key = event.key
        mods = pygame.key.get_mods()
        unicode_char = getattr(event, 'unicode', '')
        
        # Emit typed key event
        key_event = KeyDownEvent(key=key, mods=mods, unicode=unicode_char)
        self.events.emit(key_event)
        
        if key_event.cancelled:
            return False
        
        # Dismiss overlays on any key
        self.renderer._overlay.dismiss_error()
        self.renderer._overlay.dismiss_banner()
        
        # Backlog mode - swallow navigation keys
        if self.renderer.show_backlog:
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.renderer.show_backlog = False
                self.events.emit(BacklogToggleEvent(visible=False))
                self.renderer._render()
                return False
        
        # Advance keys
        if key in self.ADVANCE_KEYS:
            return self._try_advance("keyboard")
        
        # Scroll keys
        if key == pygame.K_PAGEUP:
            self.renderer.textbox.scroll_up(3 if self.renderer.show_backlog else 1)
            return False
        if key == pygame.K_UP:
            self.renderer.textbox.scroll_up()
            return False
        if key == pygame.K_PAGEDOWN:
            self.renderer.textbox.scroll_down(3 if self.renderer.show_backlog else 1)
            return False
        if key == pygame.K_DOWN:
            self.renderer.textbox.scroll_down()
            return False
        
        # Backlog toggle
        if key == self.BACKLOG_TOGGLE_KEY:
            self.renderer.show_backlog = not self.renderer.show_backlog
            self.events.emit(BacklogToggleEvent(visible=self.renderer.show_backlog))
            self.renderer._render()
            return False
        
        # UI hide toggle
        if key == self.UI_HIDE_KEY:
            try:
                self.renderer._ui_hidden = not getattr(self.renderer, '_ui_hidden', False)
                self.events.emit(UIHiddenEvent(hidden=self.renderer._ui_hidden))
            except Exception:
                pass
            self.renderer._render()
            return False
        
        # Screenshot
        if key == self.SCREENSHOT_KEY:
            p = None
            try:
                p = self.renderer.capture_screenshot()
            except Exception:
                pass
            # Emit screenshot event
            self.events.emit(ScreenshotEvent(path=str(p) if p else "", success=bool(p)))
            self.renderer.show_banner("已保存截图" if p else "截图失败", 
                                       color=(60, 160, 60) if p else (200, 140, 40))
            return False
        
        # Flow map
        if key == self.FLOW_MAP_KEY:
            self.events.emit(FlowMapEvent(action="open"))
            self.renderer._show_flow_map()
            return False
        
        # Debug toggle
        if key == self.DEBUG_KEY:
            if mods & pygame.KMOD_SHIFT:
                self.renderer._debug.toggle()
                self.events.emit(DebugToggleEvent(enabled=self.renderer._debug.enabled, debug_type="hud"))
            else:
                try:
                    self.renderer._debug_win.toggle()
                    self.events.emit(DebugToggleEvent(enabled=getattr(self.renderer._debug_win, 'enabled', True), debug_type="window"))
                except Exception:
                    self.renderer._debug.toggle()
                    self.events.emit(DebugToggleEvent(enabled=self.renderer._debug.enabled, debug_type="hud"))
            return False
        
        # Auto mode toggle
        if key == self.AUTO_MODE_KEY:
            self.renderer._auto_mode = not self.renderer._auto_mode
            self.events.emit(AutoModeEvent(enabled=self.renderer._auto_mode))
            return False
        
        # Fast forward (hold key)
        if key == self.FAST_FORWARD_KEY:
            self.renderer._fast_forward = True
            self._fast_forward_held = True
            self.events.emit(FastForwardEvent(enabled=True, held=True))
            return False
        
        # Quick save
        if key == self.QUICKSAVE_KEY:
            if self.renderer._qs_hook:
                ok = False
                try:
                    ok = bool(self.renderer._qs_hook())
                except Exception:
                    ok = False
                self.renderer.show_banner("快速保存成功" if ok else "保存失败",
                                          color=(60, 160, 60) if ok else (200, 140, 40))
            return False
        
        # Quick load
        if key == self.QUICKLOAD_KEY:
            if self.renderer._ql_hook:
                ok = False
                try:
                    ok = bool(self.renderer._ql_hook())
                except Exception:
                    ok = False
                if ok:
                    self.renderer._fast_forward = False
                    self.renderer._suppress_auto_once = True
                    self.renderer.show_banner("快速读取成功")
                    self.renderer._render()
                else:
                    self.renderer.show_banner("读取失败", color=(200, 140, 40))
            return False
        
        # Save menu
        if key == self.SAVE_MENU_KEY:
            menu_event = MenuOpenEvent(menu_type="save")
            self.events.emit(menu_event)
            if not menu_event.cancelled:
                slot = self.renderer._show_slots_menu(mode="save")
                if slot is not None:
                    try:
                        self.renderer._capture_thumbnail(slot)
                    except Exception:
                        pass
                    ok = False
                    if self.renderer._save_slot_hook:
                        try:
                            ok = bool(self.renderer._save_slot_hook(int(slot)))
                        except Exception:
                            ok = False
                    self.renderer.show_banner(f"保存到槽位 {slot:02d}" if ok else "保存失败",
                                              color=(60, 160, 60) if ok else (200, 140, 40))
            return False
        
        # Load menu
        if key == self.LOAD_MENU_KEY:
            menu_event = MenuOpenEvent(menu_type="load")
            self.events.emit(menu_event)
            if not menu_event.cancelled:
                slot = self.renderer._show_slots_menu(mode="load")
                if slot is not None and self.renderer._load_slot_hook:
                    ok = False
                    try:
                        ok = bool(self.renderer._load_slot_hook(int(slot)))
                    except Exception:
                        ok = False
                    if ok:
                        self.renderer._fast_forward = False
                        self.renderer._suppress_auto_once = True
                        self.renderer.show_banner(f"读取槽位 {slot:02d} 成功")
                        self.renderer._render()
                    else:
                        self.renderer.show_banner("读取失败", color=(200, 140, 40))
            return False
        
        return False
    
    def _handle_keyup(self, event: pygame.event.Event) -> bool:
        """Handle key release events."""
        key = event.key
        
        # Emit typed event
        key_event = KeyUpEvent(key=key, mods=pygame.key.get_mods())
        self.events.emit(key_event)
        
        # Fast forward release
        if key == self.FAST_FORWARD_KEY and self._fast_forward_held:
            self.renderer._fast_forward = False
            self._fast_forward_held = False
            self.events.emit(FastForwardEvent(enabled=False, held=False))
        
        return False
    
    def _handle_mousewheel(self, event: pygame.event.Event) -> bool:
        """Handle mouse wheel events."""
        # Emit typed event
        wheel_event = MouseWheelEvent(x=event.x, y=event.y)
        self.events.emit(wheel_event)
        
        if wheel_event.cancelled:
            return False
        
        # Backlog scrolling
        if self.renderer.show_backlog and self.renderer.textbox.history:
            if event.y > 0:
                self.renderer.textbox.scroll_up(2)
            elif event.y < 0:
                self.renderer.textbox.scroll_down(2)
            self.renderer._render()
            return False
        
        # Story navigation
        if event.y > 0:
            # Scroll up = rewind
            ok = False
            if self.renderer._back_hook:
                try:
                    ok = bool(self.renderer._back_hook())
                except Exception:
                    ok = False
            if ok:
                self.renderer._fast_forward = False
                self.renderer._suppress_auto_once = True
                self.renderer.show_banner("回到上一句")
                self.renderer._render()
            return False
        
        elif event.y < 0:
            # Scroll down = advance
            return self._try_advance("wheel", suppress_anims=True)
        
        return False
    
    def _handle_mouseclick(self, event: pygame.event.Event) -> bool:
        """Handle mouse click events."""
        button = getattr(event, 'button', 1)
        
        # Only handle left click
        if button != 1:
            return False
        
        # Transform to canvas coordinates
        mx, my = event.pos
        canvas_pos = None
        
        if self.renderer._last_transform:
            scale, offx, offy, dst_w, dst_h = self.renderer._last_transform
            if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                cx = int((mx - offx) / scale)
                cy = int((my - offy) / scale)
                canvas_pos = (cx, cy)
        
        # Emit typed event
        click_event = MouseClickEvent(button=button, pos=event.pos, canvas_pos=canvas_pos)
        self.events.emit(click_event)
        
        if click_event.cancelled:
            return False
        
        # Close backlog on click
        if self.renderer.show_backlog:
            self.renderer.show_backlog = False
            self.events.emit(BacklogToggleEvent(visible=False))
            self.renderer._render()
            return False
        
        # Check button hits
        if canvas_pos:
            pos = canvas_pos
            
            if self.renderer._ui_rects.get("log") and self.renderer._ui_rects["log"].collidepoint(pos):
                self.renderer.show_backlog = not self.renderer.show_backlog
                self.events.emit(BacklogToggleEvent(visible=self.renderer.show_backlog))
                self.renderer._render()
                return False
            
            if self.renderer._ui_rects.get("back") and self.renderer._ui_rects["back"].collidepoint(pos):
                ok = False
                if self.renderer._back_hook:
                    try:
                        ok = bool(self.renderer._back_hook())
                    except Exception:
                        ok = False
                if ok:
                    self.renderer._fast_forward = False
                    self.renderer._suppress_auto_once = True
                    self.renderer.show_banner("回到上一句")
                    self.renderer._render()
                else:
                    self.renderer.textbox.scroll_up()
                return False
        
        # Default: try to advance
        return self._try_advance("mouse")
    
    def _try_advance(self, source: str, suppress_anims: bool = False) -> bool:
        """
        Try to advance text/reveal.
        
        Returns True if should exit waiting loop.
        """
        # Emit advance request event (can be cancelled)
        advance_event = AdvanceRequestEvent(source=source)
        self.events.emit(advance_event)
        
        if advance_event.cancelled:
            return False
        
        # Check if still typing
        cur = self.renderer.textbox.current()
        if (self.renderer._typing_enabled and cur and 
            not self.renderer._reveal_instant and 
            self.renderer._line_full_ts is None):
            # Reveal instantly first
            self.renderer._reveal_instant = True
            return False
        
        # Stop voice
        try:
            if self.renderer._voice_channel:
                self.renderer._voice_channel.stop()
        except Exception:
            pass
        
        # Clear animations if requested
        if suppress_anims:
            try:
                if self.renderer.animator:
                    self.renderer.animator.clear()
            except Exception:
                pass
            self.renderer._suppress_anims_once = True
            self.renderer._fast_forward = False
        
        return True  # Exit waiting loop


def wait_for_advance_v2(renderer: 'PygameRenderer', event_system: EventSystem) -> None:
    """
    Event loop that waits for reveal/advance using the new input handler.
    
    This is a drop-in replacement for the old wait_for_advance function.
    """
    handler = InputHandler(renderer, event_system)
    waiting = True
    
    while waiting:
        for event in pygame.event.get():
            if handler.process_pygame_event(event):
                waiting = False
                break
        
        renderer._render()
        
        # Auto-advance when fully revealed
        if (not renderer.show_backlog and 
            renderer._auto_mode and 
            renderer._typing_enabled and 
            renderer._line_full_ts is not None):
            if renderer._suppress_auto_once:
                renderer._suppress_auto_once = False
            elif pygame.time.get_ticks() - renderer._line_full_ts >= renderer._auto_delay_line_ms:
                waiting = False
        
        renderer.clock.tick(60)
