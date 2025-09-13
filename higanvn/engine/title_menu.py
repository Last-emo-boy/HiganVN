from __future__ import annotations

from typing import Optional
import pygame
from higanvn.engine.placeholders import make_bg_placeholder

LOGICAL_SIZE = (1280, 720)


def show_title_menu(renderer, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:
    # Preload background if provided
    title_bg = None
    if bg_path:
        try:
            resolved = renderer._resolve_asset(bg_path, ["bg"])  # type: ignore[arg-type]
            img = pygame.image.load(resolved).convert()
            title_bg = pygame.transform.scale(img, LOGICAL_SIZE)
        except Exception:
            title_bg = make_bg_placeholder(LOGICAL_SIZE, renderer.font, (40,40,40), (180,180,180), f"BG missing: {bg_path}")
    items = [("开始游戏", "start"), ("读取进度", "load"), ("设置", "settings"), ("CG 画廊", "gallery"), ("退出", "quit")]
    sel = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % len(items)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % len(items)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return items[sel][1]
                elif event.key == pygame.K_ESCAPE:
                    return "quit"
            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                # Map to canvas space
                win_w, win_h = renderer.screen.get_size()
                scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
                dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
                offx = (win_w - dst_w) // 2
                offy = (win_h - dst_h) // 2
                if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                    cx = int((mx - offx) / scale)
                    cy = int((my - offy) / scale)
                    # Menu bounds
                    menu_rect = pygame.Rect(LOGICAL_SIZE[0]//2 - 140, LOGICAL_SIZE[1]//2 - 20, 280, 40 * len(items))
                    if menu_rect.collidepoint((cx, cy)):
                        idx = (cy - menu_rect.y) // 40
                        if 0 <= idx < len(items):
                            sel = idx
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                win_w, win_h = renderer.screen.get_size()
                scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
                dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
                offx = (win_w - dst_w) // 2
                offy = (win_h - dst_h) // 2
                if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                    cx = int((mx - offx) / scale)
                    cy = int((my - offy) / scale)
                    menu_rect = pygame.Rect(LOGICAL_SIZE[0]//2 - 140, LOGICAL_SIZE[1]//2 - 20, 280, 40 * len(items))
                    if menu_rect.collidepoint((cx, cy)):
                        idx = (cy - menu_rect.y) // 40
                        if 0 <= idx < len(items):
                            return items[idx][1]
        # Draw title screen
        renderer.canvas.fill((0,0,0))
        if title_bg:
            renderer.canvas.blit(title_bg, (0,0))
        # Title text
        t = str(title or "HiganVN")
        title_surf = renderer.font.render(t, True, (255,255,255))
        renderer.canvas.blit(title_surf, (LOGICAL_SIZE[0]//2 - title_surf.get_width()//2, LOGICAL_SIZE[1]//3 - title_surf.get_height()//2))
        # Menu
        menu_rect = pygame.Rect(LOGICAL_SIZE[0]//2 - 140, LOGICAL_SIZE[1]//2 - 20, 280, 40 * len(items))
        for i, (txt, _k) in enumerate(items):
            color = (0,255,0) if i == sel else (255,255,255)
            surf = renderer.font.render(txt, True, color)
            renderer.canvas.blit(surf, (menu_rect.x + 10, menu_rect.y + 40*i))
        # Present
        win_w, win_h = renderer.screen.get_size()
        scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
        dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
        scaled = pygame.transform.smoothscale(renderer.canvas, (dst_w, dst_h))
        x = (win_w - dst_w) // 2
        y = (win_h - dst_h) // 2
        renderer.screen.fill((0, 0, 0))
        renderer.screen.blit(scaled, (x, y))
        pygame.display.flip()
        renderer.clock.tick(60)
