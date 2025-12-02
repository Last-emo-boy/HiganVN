"""
Title Menu - 现代视觉小说风格标题菜单
采用渐变背景、发光效果、优雅动画
"""
from __future__ import annotations

from typing import Optional
import math
import pygame
from higanvn.engine.placeholders import make_bg_placeholder

LOGICAL_SIZE = (1280, 720)

# 主题色板
class Theme:
    PRIMARY = (100, 140, 220)
    PRIMARY_DARK = (50, 70, 120)
    PRIMARY_LIGHT = (150, 190, 255)
    ACCENT = (255, 200, 100)
    ACCENT_GLOW = (255, 220, 150)
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (200, 200, 220)
    MENU_BG = (20, 25, 40)
    MENU_HOVER = (40, 55, 90)
    MENU_BORDER = (80, 100, 150)


def _draw_gradient_rect(surface, rect, color_top, color_bottom, border_radius=0):
    """绘制垂直渐变矩形"""
    temp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t) if len(color_top) > 3 else 255
        pygame.draw.line(temp, (r, g, b, a), (0, y), (rect.width, y))
    if border_radius > 0:
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=border_radius)
        temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(temp, rect.topleft)


def _create_title_font(renderer, size_multiplier=2.0):
    """创建标题专用大号字体"""
    try:
        from higanvn.engine.font_utils import init_font
        return init_font(renderer._font_path, int(renderer._font_size * size_multiplier), renderer._asset_ns)
    except Exception:
        return renderer.font


def show_title_menu(renderer, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:
    # 预加载背景
    title_bg = None
    if bg_path:
        try:
            resolved = renderer._resolve_asset(bg_path, ["bg"])
            img = pygame.image.load(resolved).convert()
            title_bg = pygame.transform.smoothscale(img, LOGICAL_SIZE)
        except Exception:
            title_bg = make_bg_placeholder(LOGICAL_SIZE, renderer.font, (20, 25, 40), (100, 100, 120), f"BG: {bg_path}")
    
    # 创建标题大字体
    title_font = _create_title_font(renderer, 2.2)
    
    # 菜单项
    items = [
        ("开始游戏", "start", "▶"),
        ("读取进度", "load", "📁"),
        ("设置", "settings", "⚙"),
        ("CG 画廊", "gallery", "🖼"),
        ("退出", "quit", "✕"),
    ]
    sel = 0
    
    # 动画状态
    hover_anim = [0.0] * len(items)  # 每个菜单项的悬停动画进度
    start_time = pygame.time.get_ticks()
    
    while True:
        now = pygame.time.get_ticks()
        elapsed = now - start_time
        
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
                win_w, win_h = renderer.screen.get_size()
                scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
                dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
                offx = (win_w - dst_w) // 2
                offy = (win_h - dst_h) // 2
                if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                    cx = int((mx - offx) / scale)
                    cy = int((my - offy) / scale)
                    menu_start_y = LOGICAL_SIZE[1] // 2
                    for i in range(len(items)):
                        item_y = menu_start_y + i * 56
                        item_rect = pygame.Rect(LOGICAL_SIZE[0] // 2 - 160, item_y, 320, 48)
                        if item_rect.collidepoint((cx, cy)):
                            sel = i
                            break
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
                    menu_start_y = LOGICAL_SIZE[1] // 2
                    for i in range(len(items)):
                        item_y = menu_start_y + i * 56
                        item_rect = pygame.Rect(LOGICAL_SIZE[0] // 2 - 160, item_y, 320, 48)
                        if item_rect.collidepoint((cx, cy)):
                            return items[i][1]
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    sel = (sel - 1) % len(items)
                elif event.y < 0:
                    sel = (sel + 1) % len(items)
        
        # 更新悬停动画
        for i in range(len(items)):
            target = 1.0 if i == sel else 0.0
            hover_anim[i] += (target - hover_anim[i]) * 0.15
        
        # ====================================================================
        # 绘制背景
        # ====================================================================
        renderer.canvas.fill((10, 15, 25))
        
        if title_bg:
            # 添加轻微的明暗动画
            brightness = 0.85 + 0.05 * math.sin(elapsed * 0.001)
            bg_copy = title_bg.copy()
            dark_overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
            dark_alpha = int((1 - brightness) * 100)
            dark_overlay.fill((0, 0, 0, dark_alpha))
            bg_copy.blit(dark_overlay, (0, 0))
            renderer.canvas.blit(bg_copy, (0, 0))
        
        # 暗角效果
        vignette = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        for i in range(4):
            alpha = 40 - i * 10
            rect = pygame.Rect(i * 80, i * 45, LOGICAL_SIZE[0] - i * 160, LOGICAL_SIZE[1] - i * 90)
            pygame.draw.rect(vignette, (0, 0, 0, 0), rect)
        # 简化暗角 - 只画边缘
        edge_w = 200
        for x in range(edge_w):
            alpha = int(60 * (1 - x / edge_w))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (x, 0), (x, LOGICAL_SIZE[1]))
            pygame.draw.line(vignette, (0, 0, 0, alpha), (LOGICAL_SIZE[0] - x - 1, 0), (LOGICAL_SIZE[0] - x - 1, LOGICAL_SIZE[1]))
        renderer.canvas.blit(vignette, (0, 0))
        
        # 顶部渐变遮罩
        top_gradient = pygame.Surface((LOGICAL_SIZE[0], 150), pygame.SRCALPHA)
        for y in range(150):
            alpha = int(120 * (1 - y / 150))
            pygame.draw.line(top_gradient, (0, 0, 0, alpha), (0, y), (LOGICAL_SIZE[0], y))
        renderer.canvas.blit(top_gradient, (0, 0))
        
        # ====================================================================
        # 标题文字
        # ====================================================================
        title_text = str(title or "HiganVN")
        title_y = LOGICAL_SIZE[1] // 4
        
        # 标题发光效果
        glow_intensity = 0.7 + 0.3 * math.sin(elapsed * 0.002)
        
        # 绘制多层发光
        for radius in range(8, 0, -2):
            alpha = int(30 * glow_intensity * (1 - radius / 8))
            glow_color = (*Theme.PRIMARY_LIGHT, alpha)
            glow_surf = title_font.render(title_text, True, glow_color[:3])
            glow_alpha = pygame.Surface(glow_surf.get_size(), pygame.SRCALPHA)
            glow_alpha.fill((*glow_color[:3], alpha))
            glow_surf.blit(glow_alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            for dx, dy in [(-radius, 0), (radius, 0), (0, -radius), (0, radius)]:
                renderer.canvas.blit(glow_surf, (LOGICAL_SIZE[0] // 2 - glow_surf.get_width() // 2 + dx, title_y + dy))
        
        # 标题阴影
        shadow_surf = title_font.render(title_text, True, (0, 0, 0))
        renderer.canvas.blit(shadow_surf, (LOGICAL_SIZE[0] // 2 - shadow_surf.get_width() // 2 + 3, title_y + 3))
        
        # 标题主体
        title_surf = title_font.render(title_text, True, Theme.TEXT_PRIMARY)
        renderer.canvas.blit(title_surf, (LOGICAL_SIZE[0] // 2 - title_surf.get_width() // 2, title_y))
        
        # 标题下方装饰线
        line_width = min(400, title_surf.get_width() + 80)
        line_y = title_y + title_surf.get_height() + 20
        line_surf = pygame.Surface((line_width, 3), pygame.SRCALPHA)
        for x in range(line_width):
            t = 1 - abs(x - line_width / 2) / (line_width / 2)
            alpha = int(150 * t * t * glow_intensity)
            line_surf.set_at((x, 0), (*Theme.ACCENT, alpha))
            line_surf.set_at((x, 1), (*Theme.ACCENT, int(alpha * 0.7)))
            line_surf.set_at((x, 2), (*Theme.ACCENT, int(alpha * 0.3)))
        renderer.canvas.blit(line_surf, (LOGICAL_SIZE[0] // 2 - line_width // 2, line_y))
        
        # ====================================================================
        # 菜单项
        # ====================================================================
        menu_start_y = LOGICAL_SIZE[1] // 2
        
        for i, (txt, key, icon) in enumerate(items):
            item_y = menu_start_y + i * 56
            item_rect = pygame.Rect(LOGICAL_SIZE[0] // 2 - 160, item_y, 320, 48)
            
            anim = hover_anim[i]
            is_selected = (i == sel)
            
            # 菜单项背景
            item_bg = pygame.Surface((item_rect.width, item_rect.height), pygame.SRCALPHA)
            
            # 渐变背景 - 根据选中状态变化
            bg_alpha = int(120 + 80 * anim)
            top_color = (
                int(Theme.MENU_BG[0] + (Theme.MENU_HOVER[0] - Theme.MENU_BG[0]) * anim),
                int(Theme.MENU_BG[1] + (Theme.MENU_HOVER[1] - Theme.MENU_BG[1]) * anim),
                int(Theme.MENU_BG[2] + (Theme.MENU_HOVER[2] - Theme.MENU_BG[2]) * anim),
                bg_alpha
            )
            bottom_color = (
                top_color[0] + 10,
                top_color[1] + 15,
                top_color[2] + 25,
                bg_alpha
            )
            _draw_gradient_rect(item_bg, pygame.Rect(0, 0, item_rect.width, item_rect.height), 
                              top_color, bottom_color, border_radius=12)
            
            renderer.canvas.blit(item_bg, item_rect.topleft)
            
            # 边框 - 选中时发光
            if is_selected:
                # 发光边框
                glow_alpha = int(100 + 50 * math.sin(elapsed * 0.005))
                for r in range(3, 0, -1):
                    glow_rect = item_rect.inflate(r * 2, r * 2)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, (*Theme.PRIMARY_LIGHT, int(glow_alpha * (1 - r / 3))), 
                                   (0, 0, glow_rect.width, glow_rect.height), width=2, border_radius=14)
                    renderer.canvas.blit(glow_surf, glow_rect.topleft)
                
                pygame.draw.rect(renderer.canvas, Theme.PRIMARY_LIGHT, item_rect, width=2, border_radius=12)
                
                # 左侧指示条
                indicator_rect = pygame.Rect(item_rect.x + 6, item_rect.y + 10, 4, item_rect.height - 20)
                pygame.draw.rect(renderer.canvas, Theme.ACCENT, indicator_rect, border_radius=2)
            else:
                border_alpha = int(60 + 40 * anim)
                pygame.draw.rect(renderer.canvas, (*Theme.MENU_BORDER, border_alpha), item_rect, width=1, border_radius=12)
            
            # 文字
            text_color = Theme.ACCENT if is_selected else Theme.TEXT_PRIMARY
            # 阴影
            text_shadow = renderer.font.render(txt, True, (0, 0, 0))
            renderer.canvas.blit(text_shadow, (item_rect.x + 52, item_rect.y + 13))
            # 主文字
            text_surf = renderer.font.render(txt, True, text_color)
            renderer.canvas.blit(text_surf, (item_rect.x + 50, item_rect.y + 11))
        
        # ====================================================================
        # 底部提示
        # ====================================================================
        hint_text = "↑↓ 选择  Enter 确认  Esc 退出"
        hint_surf = renderer.font.render(hint_text, True, Theme.TEXT_SECONDARY)
        hint_bg = pygame.Surface((hint_surf.get_width() + 20, hint_surf.get_height() + 10), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 80))
        renderer.canvas.blit(hint_bg, (LOGICAL_SIZE[0] // 2 - hint_bg.get_width() // 2, LOGICAL_SIZE[1] - 70))
        renderer.canvas.blit(hint_surf, (LOGICAL_SIZE[0] // 2 - hint_surf.get_width() // 2, LOGICAL_SIZE[1] - 65))
        
        # 版本信息
        version_text = "HiganVN Engine v1.0"
        version_surf = renderer.font.render(version_text, True, (*Theme.TEXT_SECONDARY, 120))
        renderer.canvas.blit(version_surf, (20, LOGICAL_SIZE[1] - 40))
        
        # ====================================================================
        # 呈现
        # ====================================================================
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
