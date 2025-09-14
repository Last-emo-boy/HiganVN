from __future__ import annotations

import pygame


def open_settings_menu(renderer) -> None:
    """Simple settings menu: toggle auto mode and adjust typing speed.

    Draws on renderer.canvas and presents to renderer.screen.
    """
    ui = (renderer._config.get("ui") if isinstance(renderer._config, dict) else {}) or {}
    options = [
        ("自动播放", "toggle_auto"),
        ("打字机速度", "typing_speed"),
        ("对话框不透明度", "textbox_opacity"),
        ("文字描边", "text_outline"),
        ("文字阴影", "text_shadow"),
        ("返回", "back"),
    ]
    sel = 0
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % len(options)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % len(options)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if options[sel][1] == "typing_speed":
                        renderer._typing_speed = max(0.0, renderer._typing_speed - 10.0)
                        renderer._typing_enabled = renderer._typing_speed > 0.0
                    elif options[sel][1] == "textbox_opacity":
                        val = int(ui.get("textbox_opacity", 160))
                        val = max(0, min(255, val - 10))
                        ui["textbox_opacity"] = val
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if options[sel][1] == "typing_speed":
                        renderer._typing_speed = min(120.0, renderer._typing_speed + 10.0)
                        renderer._typing_enabled = renderer._typing_speed > 0.0
                    elif options[sel][1] == "textbox_opacity":
                        val = int(ui.get("textbox_opacity", 160))
                        val = max(0, min(255, val + 10))
                        ui["textbox_opacity"] = val
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if options[sel][1] == "toggle_auto":
                        renderer._auto_mode = not renderer._auto_mode
                    elif options[sel][1] == "text_outline":
                        ui["text_outline"] = not bool(ui.get("text_outline", False))
                    elif options[sel][1] == "text_shadow":
                        ui["text_shadow"] = not bool(ui.get("text_shadow", True))
                    elif options[sel][1] == "back":
                        # write-back ui dict
                        try:
                            if isinstance(renderer._config, dict):
                                renderer._config["ui"] = ui
                        except Exception:
                            pass
                        waiting = False
                elif event.key == pygame.K_ESCAPE:
                    try:
                        if isinstance(renderer._config, dict):
                            renderer._config["ui"] = ui
                    except Exception:
                        pass
                    waiting = False
        # Render base scene behind
        renderer._render(flip=False, tick=False)
        # Panel
        canvas_w, canvas_h = renderer.canvas.get_size()
        panel = pygame.Rect(int(canvas_w*0.15625), int(canvas_h*0.2083), int(canvas_w*0.6875), int(canvas_h*0.3333))
        pygame.draw.rect(renderer.canvas, (0, 0, 0), panel)
        pygame.draw.rect(renderer.canvas, (255, 255, 255), panel, 2)
        y = panel.y + 20
        for i, (txt, kind) in enumerate(options):
            show = txt
            if kind == "toggle_auto":
                show = f"{txt}: {'开' if renderer._auto_mode else '关'}"
            if kind == "typing_speed":
                show = f"{txt}: {'瞬显' if not renderer._typing_enabled else int(renderer._typing_speed)}"
            if kind == "textbox_opacity":
                show = f"{txt}: {int(ui.get('textbox_opacity', 160))}"
            if kind == "text_outline":
                show = f"{txt}: {'开' if bool(ui.get('text_outline', False)) else '关'}"
            if kind == "text_shadow":
                show = f"{txt}: {'开' if bool(ui.get('text_shadow', True)) else '关'}"
            color = (0, 255, 0) if i == sel else (255, 255, 255)
            surf = renderer.font.render(show, True, color)
            renderer.canvas.blit(surf, (panel.x + 24, y))
            y += 60
        # Present
        win_w, win_h = renderer.screen.get_size()
        scale = min(win_w / canvas_w, win_h / canvas_h)
        dst_w, dst_h = int(canvas_w * scale), int(canvas_h * scale)
        scaled = pygame.transform.smoothscale(renderer.canvas, (dst_w, dst_h))
        x = (win_w - dst_w) // 2
        y2 = (win_h - dst_h) // 2
        renderer.screen.fill((0, 0, 0))
        renderer.screen.blit(scaled, (x, y2))
        pygame.display.flip()
        renderer.clock.tick(60)
