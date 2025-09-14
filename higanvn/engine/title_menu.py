from __future__ import annotations

from typing import Optional
import pygame
from higanvn.engine.placeholders import make_bg_placeholder

LOGICAL_SIZE = (1280, 720)


def show_title_menu(renderer, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:
    # Preload background if provided (smoothscale to logical size)
    title_bg = None
    if bg_path:
        try:
            resolved = renderer._resolve_asset(bg_path, ["bg"])  # type: ignore[arg-type]
            img = pygame.image.load(resolved).convert()
            title_bg = pygame.transform.smoothscale(img, LOGICAL_SIZE)
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
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    sel = (sel - 1) % len(items)
                elif event.y < 0:
                    sel = (sel + 1) % len(items)
        # Draw title screen
        renderer.canvas.fill((0,0,0))
        if title_bg:
            renderer.canvas.blit(title_bg, (0,0))
        # dim overlay for contrast
        ov = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        ov.fill((0, 0, 0, 80))
        renderer.canvas.blit(ov, (0, 0))
        # Title text
        t = str(title or "HiganVN")
        # subtle shadow
        try:
            shadow = renderer.font.render(t, True, (0,0,0))
            renderer.canvas.blit(shadow, (LOGICAL_SIZE[0]//2 - shadow.get_width()//2 + 2, LOGICAL_SIZE[1]//3 - shadow.get_height()//2 + 2))
        except Exception:
            pass
        title_surf = renderer.font.render(t, True, (255,255,255))
        renderer.canvas.blit(title_surf, (LOGICAL_SIZE[0]//2 - title_surf.get_width()//2, LOGICAL_SIZE[1]//3 - title_surf.get_height()//2))
        # Menu
        menu_rect = pygame.Rect(LOGICAL_SIZE[0]//2 - 140, LOGICAL_SIZE[1]//2 - 20, 280, 40 * len(items))
        for i, (txt, _k) in enumerate(items):
            row = pygame.Rect(menu_rect.x + 8, menu_rect.y + 40*i, menu_rect.width - 16, 36)
            if i == sel:
                hi = pygame.Surface((row.width, row.height), pygame.SRCALPHA)
                hi.fill((80, 120, 200, 140))
                renderer.canvas.blit(hi, (row.x, row.y))
                try:
                    pygame.draw.rect(renderer.canvas, (200, 220, 255), row, 2)
                except Exception:
                    pass
            color = (0,255,0) if i == sel else (240,240,240)
            surf = renderer.font.render(f"{i+1}. {txt}", True, color)
            renderer.canvas.blit(surf, (row.x + 10, row.y + 5))
        # hint
        hint = renderer.font.render("上下选择，回车确认，Esc退出", True, (230,230,230))
        renderer.canvas.blit(hint, (LOGICAL_SIZE[0]//2 - hint.get_width()//2, LOGICAL_SIZE[1] - 80))
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
