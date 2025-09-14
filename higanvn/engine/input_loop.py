from __future__ import annotations

import pygame
from typing import Optional


def wait_for_advance(renderer) -> None:
    """Event loop that waits for reveal/advance with proper wheel/backlog behavior.

    This function mutates the provided renderer's state and calls its helpers.
    """
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                # re-render on resize
                renderer._render()
            if event.type == pygame.KEYDOWN:
                renderer._overlay.dismiss_error()
                renderer._overlay.dismiss_banner()
                # When backlog is visible, swallow advance keys and close backlog instead
                if renderer.show_backlog:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                        renderer.show_backlog = False
                        renderer._render()
                        continue
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # if typing not finished, reveal instantly instead of advancing
                cur = renderer.textbox.current()
                if renderer._typing_enabled and cur and not renderer._reveal_instant and renderer._line_full_ts is None:
                    renderer._reveal_instant = True
                else:
                    # stop voice when advancing to next line
                    try:
                        if renderer._voice_channel:
                            renderer._voice_channel.stop()
                    except Exception:
                        pass
                    waiting = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEUP:
                # faster scroll in backlog view
                renderer.textbox.scroll_up(3 if renderer.show_backlog else 1)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
                renderer.textbox.scroll_up()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEDOWN:
                renderer.textbox.scroll_down(3 if renderer.show_backlog else 1)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
                renderer.textbox.scroll_down()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
                renderer.show_backlog = not renderer.show_backlog
                # Do not advance when toggling backlog
                renderer._render()
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                # Toggle UI visibility (hide overlays and textbox)
                try:
                    renderer._ui_hidden = not getattr(renderer, '_ui_hidden', False)
                except Exception:
                    pass
                renderer._render()
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
                # Capture a screenshot to save/screenshots
                p = None
                try:
                    p = renderer.capture_screenshot()
                except Exception:
                    p = None
                if p:
                    renderer.show_banner("已保存截图")
                else:
                    renderer.show_banner("截图失败", color=(200,140,40))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                renderer._show_flow_map()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                # F3 toggles external debug window; Shift+F3 toggles overlay HUD
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    renderer._debug.toggle()
                else:
                    try:
                        renderer._debug_win.toggle()
                    except Exception:
                        # If window isn't available, fallback to overlay HUD
                        renderer._debug.toggle()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                renderer._auto_mode = not renderer._auto_mode
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                renderer._fast_forward = True
            if event.type == pygame.KEYUP and event.key == pygame.K_f:
                renderer._fast_forward = False
            # quick save/load
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                if renderer._qs_hook:
                    ok = False
                    try:
                        ok = bool(renderer._qs_hook())
                    except Exception:
                        ok = False
                    if ok:
                        renderer.show_banner("快速保存成功")
                    else:
                        renderer.show_banner("保存失败", color=(200, 140, 40))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                if renderer._ql_hook:
                    ok = False
                    try:
                        ok = bool(renderer._ql_hook())
                    except Exception:
                        ok = False
                    if ok:
                        # On successful quickload, cancel fast-forward and suppress auto once.
                        renderer._fast_forward = False
                        renderer._suppress_auto_once = True
                        renderer.show_banner("快速读取成功")
                        # Stay in waiting loop and refresh the newly loaded frame.
                        renderer._render()
                    else:
                        renderer.show_banner("读取失败", color=(200, 140, 40))
            # open save/load slot menus
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
                slot = renderer._show_slots_menu(mode="save")
                if slot is not None:
                    # capture thumbnail first
                    try:
                        renderer._capture_thumbnail(slot)
                    except Exception:
                        pass
                    ok = False
                    if renderer._save_slot_hook:
                        try:
                            ok = bool(renderer._save_slot_hook(int(slot)))
                        except Exception:
                            ok = False
                    renderer.show_banner(f"保存到槽位 {slot:02d}" if ok else "保存失败", color=(60,160,60) if ok else (200,140,40))
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                slot = renderer._show_slots_menu(mode="load")
                if slot is not None and renderer._load_slot_hook:
                    ok = False
                    try:
                        ok = bool(renderer._load_slot_hook(int(slot)))
                    except Exception:
                        ok = False
                    if ok:
                        # After loading from slot, cancel fast-forward and suppress auto once.
                        renderer._fast_forward = False
                        renderer._suppress_auto_once = True
                        renderer.show_banner(f"读取槽位 {slot:02d} 成功")
                        # Keep waiting and refresh frame so user can read the loaded line.
                        renderer._render()
                    else:
                        renderer.show_banner("读取失败", color=(200, 140, 40))
            if event.type == pygame.MOUSEWHEEL:
                # If backlog is visible, wheel scrolls the backlog only
                if renderer.show_backlog and renderer.textbox.history:
                    if event.y > 0:
                        renderer.textbox.scroll_up(2)
                    elif event.y < 0:
                        renderer.textbox.scroll_down(2)
                    # stay in backlog mode and refresh
                    renderer._render()
                    continue
                else:
                    # Backlog hidden: wheel navigates story statefully
                    if event.y > 0:
                        # Rewind one visible line with engine hook if available
                        ok = False
                        if renderer._back_hook:
                            try:
                                ok = bool(renderer._back_hook())
                            except Exception:
                                ok = False
                        if ok:
                            # cancel fast-forward and suppress auto once; refresh frame
                            renderer._fast_forward = False
                            renderer._suppress_auto_once = True
                            renderer.show_banner("回到上一句")
                            renderer._render()
                        else:
                            # no-op if cannot rewind further
                            pass
                    elif event.y < 0:
                        # Scroll down: act like a gentle advance
                        cur = renderer.textbox.current()
                        if renderer._typing_enabled and cur and not renderer._reveal_instant and renderer._line_full_ts is None:
                            # first reveal current line fully
                            renderer._reveal_instant = True
                        else:
                            # then advance to next line
                            try:
                                if renderer._voice_channel:
                                    renderer._voice_channel.stop()
                            except Exception:
                                pass
                            # clear any running animations and suppress entrance/effects for next line
                            try:
                                if renderer.animator:
                                    renderer.animator.clear()
                            except Exception:
                                pass
                            renderer._suppress_anims_once = True
                            # cancel fast-forward once the user manually advances
                            renderer._fast_forward = False
                            waiting = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Only left-click (button 1) should reveal/advance; ignore wheel buttons (4/5)
                if getattr(event, 'button', None) != 1:
                    # let MOUSEWHEEL handler manage scrolling; do nothing here for other buttons
                    continue
                # If backlog is visible, left-click closes backlog without advancing
                if renderer.show_backlog:
                    renderer.show_backlog = False
                    renderer._render()
                    continue
                # Map window coords to canvas coords for button hit-test
                mx, my = event.pos
                if renderer._last_transform:
                    scale, offx, offy, dst_w, dst_h = renderer._last_transform
                    # ignore clicks outside the scaled canvas
                    if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                        cx = int((mx - offx) / scale)
                        cy = int((my - offy) / scale)
                        pos = (cx, cy)
                        if renderer._ui_rects.get("log") and renderer._ui_rects["log"].collidepoint(pos):
                            renderer.show_backlog = not renderer.show_backlog
                            # don't advance
                        elif renderer._ui_rects.get("back") and renderer._ui_rects["back"].collidepoint(pos):
                            # try engine-level rewind if available
                            ok = False
                            if renderer._back_hook:
                                try:
                                    ok = bool(renderer._back_hook())
                                except Exception:
                                    ok = False
                            if ok:
                                # stay in waiting loop so user can read the rewound line
                                # cancel fast-forward and suppress auto once
                                renderer._fast_forward = False
                                renderer._suppress_auto_once = True
                                renderer.show_banner("回到上一句")
                                # force a refresh of the rewound frame
                                renderer._render()
                            else:
                                # fallback: only scroll backlog view
                                renderer.textbox.scroll_up()
                        else:
                            # click: reveal first, then advance
                            cur = renderer.textbox.current()
                            if renderer._typing_enabled and cur and not renderer._reveal_instant and renderer._line_full_ts is None:
                                renderer._reveal_instant = True
                            else:
                                try:
                                    if renderer._voice_channel:
                                        renderer._voice_channel.stop()
                                except Exception:
                                    pass
                                waiting = False
                    else:
                        # click outside canvas advances
                        cur = renderer.textbox.current()
                        if renderer._typing_enabled and cur and not renderer._reveal_instant and renderer._line_full_ts is None:
                            renderer._reveal_instant = True
                        else:
                            try:
                                if renderer._voice_channel:
                                    renderer._voice_channel.stop()
                            except Exception:
                                pass
                            waiting = False
        renderer._render()
        # auto-advance when fully revealed (skip once if just rewound)
        if (not renderer.show_backlog) and renderer._auto_mode and renderer._typing_enabled and renderer._line_full_ts is not None:
            if renderer._suppress_auto_once:
                # consume the suppression and do not advance this cycle
                renderer._suppress_auto_once = False
            elif pygame.time.get_ticks() - renderer._line_full_ts >= renderer._auto_delay_line_ms:
                # exit wait loop
                waiting = False
        renderer.clock.tick(60)
