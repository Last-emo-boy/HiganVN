"""
Text Panel - 现代视觉小说风格对话框
采用渐变背景、发光边框、精美排版
"""
from __future__ import annotations

from typing import Optional, Tuple
import math

import pygame
from pygame import Surface

from higanvn.ui.textwrap import wrap_text_generic

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)

# 对话框布局常量
PANEL_MARGIN_X = 40
PANEL_MARGIN_BOTTOM = 30
PANEL_HEIGHT = 200
PANEL_BORDER_RADIUS = 16
NAME_BOX_HEIGHT = 38
NAME_BOX_OFFSET_Y = -32

# 主题色板
class Theme:
    PRIMARY = (100, 140, 220)
    PRIMARY_DARK = (60, 90, 160)
    PRIMARY_LIGHT = (140, 180, 255)
    ACCENT = (255, 200, 100)
    NAME_COLOR = (255, 235, 180)
    NAME_GLOW = (255, 200, 100)
    TEXT_PRIMARY = (255, 255, 255)
    PANEL_BG = (15, 20, 35)
    PANEL_BG_ALPHA = 220
    PANEL_BORDER = (80, 100, 140)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    def measure(s: str) -> int:
        try:
            return font.size(s)[0]
        except Exception:
            return 0
    return wrap_text_generic(text or "", measure, int(max_width))


def _draw_gradient_rect(
    surface: Surface,
    rect: pygame.Rect,
    color_top: Tuple[int, int, int, int],
    color_bottom: Tuple[int, int, int, int],
    border_radius: int = 0,
) -> None:
    """绘制垂直渐变矩形"""
    temp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t)
        pygame.draw.line(temp, (r, g, b, a), (0, y), (rect.width, y))
    if border_radius > 0:
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=border_radius)
        temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(temp, rect.topleft)


def draw_text_panel(
    canvas: Surface,
    font: pygame.font.Font,
    hint_font: pygame.font.Font,
    name: Optional[str],
    text: str,
    effect: Optional[str],
    typing_enabled: bool,
    fast_forward: bool,
    line_start_ts: int,
    line_full_ts: Optional[int],
    reveal_instant: bool,
    panel_alpha: Optional[int] = None,
    text_outline: Optional[bool] = None,
    text_shadow: Optional[bool] = None,
    text_shadow_offset: Optional[Tuple[int, int]] = None,
) -> tuple[bool, int, Optional[int]]:
    """绘制现代风格对话框"""
    
    now = pygame.time.get_ticks()
    
    # ========================================================================
    # 主面板
    # ========================================================================
    panel_rect = pygame.Rect(
        PANEL_MARGIN_X,
        LOGICAL_SIZE[1] - PANEL_HEIGHT - PANEL_MARGIN_BOTTOM,
        LOGICAL_SIZE[0] - PANEL_MARGIN_X * 2,
        PANEL_HEIGHT
    )
    
    alpha = min(255, max(0, panel_alpha if panel_alpha is not None else Theme.PANEL_BG_ALPHA))
    
    # 创建渐变面板
    panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    _draw_gradient_rect(
        panel_surf,
        pygame.Rect(0, 0, panel_rect.width, panel_rect.height),
        (*Theme.PANEL_BG, alpha),
        (Theme.PANEL_BG[0] + 15, Theme.PANEL_BG[1] + 20, Theme.PANEL_BG[2] + 30, alpha),
        border_radius=PANEL_BORDER_RADIUS
    )
    
    # 顶部高光线
    highlight = pygame.Surface((panel_rect.width - 40, 2), pygame.SRCALPHA)
    for x in range(highlight.get_width()):
        t = 1 - abs(x - highlight.get_width() / 2) / (highlight.get_width() / 2)
        a = int(80 * t * t)
        highlight.set_at((x, 0), (*Theme.PRIMARY_LIGHT, a))
        highlight.set_at((x, 1), (*Theme.PRIMARY_LIGHT, a // 2))
    panel_surf.blit(highlight, (20, 4))
    
    # 底部装饰线
    bottom_line = pygame.Surface((panel_rect.width - 80, 1), pygame.SRCALPHA)
    for x in range(bottom_line.get_width()):
        t = 1 - abs(x - bottom_line.get_width() / 2) / (bottom_line.get_width() / 2)
        a = int(40 * t)
        bottom_line.set_at((x, 0), (*Theme.PANEL_BORDER, a))
    panel_surf.blit(bottom_line, (40, panel_rect.height - 8))
    
    canvas.blit(panel_surf, panel_rect.topleft)
    
    # 面板边框 - 带微光动画
    border_alpha = int(80 + 30 * (0.5 + 0.5 * math.sin(now * 0.002)))
    pygame.draw.rect(canvas, (*Theme.PANEL_BORDER, border_alpha), panel_rect, 
                    width=2, border_radius=PANEL_BORDER_RADIUS)
    
    # ========================================================================
    # 角色名框
    # ========================================================================
    text_start_y = panel_rect.y + 20
    
    if name:
        nstr = str(name)
        if '|' in nstr:
            base, alias = nstr.split('|', 1)
            disp_name = f"{base}（{alias}）"
        else:
            disp_name = nstr
        
        name_surf_temp = font.render(disp_name, True, Theme.NAME_COLOR)
        name_width = name_surf_temp.get_width() + 40
        
        name_rect = pygame.Rect(
            panel_rect.x + 20,
            panel_rect.y + NAME_BOX_OFFSET_Y,
            name_width,
            NAME_BOX_HEIGHT
        )
        
        # 名字框渐变背景
        name_bg = pygame.Surface((name_rect.width, name_rect.height), pygame.SRCALPHA)
        _draw_gradient_rect(
            name_bg,
            pygame.Rect(0, 0, name_rect.width, name_rect.height),
            (*Theme.PRIMARY_DARK, 240),
            (*Theme.PRIMARY, 220),
            border_radius=8
        )
        canvas.blit(name_bg, name_rect.topleft)
        
        # 名字框边框
        pygame.draw.rect(canvas, Theme.PRIMARY_LIGHT, name_rect, width=2, border_radius=8)
        
        # 左侧装饰条
        deco_rect = pygame.Rect(name_rect.x + 8, name_rect.y + 8, 3, name_rect.height - 16)
        pygame.draw.rect(canvas, Theme.ACCENT, deco_rect, border_radius=2)
        
        # 角色名文字 - 带阴影和发光
        nx = name_rect.x + 20
        ny = name_rect.y + (NAME_BOX_HEIGHT - name_surf_temp.get_height()) // 2
        # 阴影
        shadow = font.render(disp_name, True, (0, 0, 0))
        canvas.blit(shadow, (nx + 2, ny + 2))
        # 发光
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            glow = font.render(disp_name, True, (*Theme.NAME_GLOW, 60))
            canvas.blit(glow, (nx + dx, ny + dy))
        # 主文字
        canvas.blit(name_surf_temp, (nx, ny))
        
        # 效果标签
        if effect:
            eff_txt = f"[{effect}]"
            eff_surf = hint_font.render(eff_txt, True, (180, 180, 255))
            eff_x = name_rect.right + 10
            eff_y = name_rect.y + (NAME_BOX_HEIGHT - eff_surf.get_height()) // 2
            canvas.blit(eff_surf, (eff_x, eff_y))
        
        text_start_y = panel_rect.y + 24
    
    # ========================================================================
    # 对话文本
    # ========================================================================
    disp_text = text
    line_start_ts_out = line_start_ts
    line_full_ts_out = line_full_ts
    reveal = reveal_instant
    
    if typing_enabled and not reveal_instant:
        if line_start_ts_out == 0:
            line_start_ts_out = now
        speed = 50.0 * (3.0 if fast_forward else 1.0)
        allow = int(max(0, (now - line_start_ts_out) / 1000.0) * speed)
        if allow < len(text):
            disp_text = text[:allow]
            line_full_ts_out = None
        else:
            disp_text = text
            if line_full_ts_out is None:
                line_full_ts_out = now
    
    text_margin_x = 24
    text_max_width = panel_rect.width - text_margin_x * 2
    line_height = 32
    
    y = text_start_y
    for line in wrap_text(disp_text, font, text_max_width):
        # 文字阴影
        if text_shadow:
            ox, oy = text_shadow_offset or (2, 2)
            shadow_surf = font.render(line, True, (0, 0, 0))
            canvas.blit(shadow_surf, (panel_rect.x + text_margin_x + ox, y + oy))
        
        # 文字轮廓
        if text_outline:
            outline_surf = font.render(line, True, (0, 0, 0))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                canvas.blit(outline_surf, (panel_rect.x + text_margin_x + dx, y + dy))
        
        # 主文字
        text_surf = font.render(line, True, Theme.TEXT_PRIMARY)
        canvas.blit(text_surf, (panel_rect.x + text_margin_x, y))
        y += line_height
    
    # ========================================================================
    # 继续指示器
    # ========================================================================
    if line_full_ts_out is not None:
        indicator_alpha = int(128 + 127 * math.sin(now * 0.005))
        indicator_x = panel_rect.right - 40
        indicator_y = panel_rect.bottom - 30
        
        points = [
            (indicator_x, indicator_y),
            (indicator_x + 12, indicator_y + 6),
            (indicator_x, indicator_y + 12)
        ]
        indicator_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(indicator_surf, (*Theme.ACCENT, indicator_alpha), 
                          [(p[0] - indicator_x + 4, p[1] - indicator_y + 4) for p in points])
        canvas.blit(indicator_surf, (indicator_x - 4, indicator_y - 4))
    
    return reveal, line_start_ts_out, line_full_ts_out
