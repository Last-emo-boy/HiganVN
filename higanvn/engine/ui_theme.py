"""
UI Theme System - Modern Visual Novel Style
提供统一的视觉主题配置和渐变/阴影/发光效果绘制函数
"""
from __future__ import annotations

from typing import Tuple, Optional, List
import pygame
from pygame import Surface
import math

# ============================================================================
# 主题色板 - 现代视觉小说风格
# ============================================================================

class Theme:
    """主题配色方案"""
    # 主色调 - 优雅蓝紫渐变
    PRIMARY = (100, 140, 220)
    PRIMARY_DARK = (60, 90, 160)
    PRIMARY_LIGHT = (140, 180, 255)
    
    # 强调色 - 金色/琥珀色
    ACCENT = (255, 200, 100)
    ACCENT_GLOW = (255, 220, 150)
    
    # 角色名颜色
    NAME_COLOR = (255, 235, 180)
    NAME_GLOW = (255, 200, 100)
    
    # 文字颜色
    TEXT_PRIMARY = (255, 255, 255)
    TEXT_SECONDARY = (200, 200, 210)
    TEXT_DIM = (150, 150, 160)
    
    # 面板背景
    PANEL_BG = (15, 20, 35)
    PANEL_BG_ALPHA = 220
    PANEL_BORDER = (80, 100, 140)
    PANEL_BORDER_GLOW = (100, 140, 200)
    
    # 按钮
    BUTTON_BG = (40, 50, 70)
    BUTTON_HOVER = (60, 80, 120)
    BUTTON_ACTIVE = (80, 110, 160)
    BUTTON_BORDER = (100, 120, 160)
    
    # 标题菜单
    TITLE_GRADIENT_TOP = (20, 30, 50)
    TITLE_GRADIENT_BOTTOM = (10, 15, 30)
    MENU_ITEM_BG = (30, 40, 60)
    MENU_ITEM_HOVER = (50, 70, 110)
    MENU_ITEM_GLOW = (100, 150, 220)


# ============================================================================
# 绘制工具函数
# ============================================================================

def draw_gradient_rect(
    surface: Surface,
    rect: pygame.Rect,
    color_top: Tuple[int, int, int, int],
    color_bottom: Tuple[int, int, int, int],
    vertical: bool = True,
    border_radius: int = 0,
) -> None:
    """绘制带渐变的矩形"""
    temp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    
    if vertical:
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
            a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t)
            pygame.draw.line(temp, (r, g, b, a), (0, y), (rect.width, y))
    else:
        for x in range(rect.width):
            t = x / max(1, rect.width - 1)
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
            a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t)
            pygame.draw.line(temp, (r, g, b, a), (x, 0), (x, rect.height))
    
    if border_radius > 0:
        # 创建圆角遮罩
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=border_radius)
        temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    
    surface.blit(temp, rect.topleft)


def draw_glow_border(
    surface: Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    glow_radius: int = 3,
    border_width: int = 2,
    border_radius: int = 0,
) -> None:
    """绘制发光边框效果"""
    # 外发光层
    for i in range(glow_radius, 0, -1):
        alpha = int(60 * (1 - i / glow_radius))
        glow_rect = rect.inflate(i * 2, i * 2)
        glow_color = (*color, alpha)
        temp = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(temp, glow_color, (0, 0, glow_rect.width, glow_rect.height), 
                        width=2, border_radius=border_radius + i)
        surface.blit(temp, glow_rect.topleft)
    
    # 主边框
    pygame.draw.rect(surface, color, rect, width=border_width, border_radius=border_radius)


def draw_text_with_glow(
    surface: Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[int, int],
    color: Tuple[int, int, int] = (255, 255, 255),
    glow_color: Optional[Tuple[int, int, int]] = None,
    glow_radius: int = 2,
    shadow: bool = True,
    shadow_offset: Tuple[int, int] = (2, 2),
) -> pygame.Rect:
    """绘制带发光和阴影的文字"""
    x, y = pos
    
    # 阴影
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        shadow_alpha = pygame.Surface(shadow_surf.get_size(), pygame.SRCALPHA)
        shadow_alpha.fill((0, 0, 0, 100))
        shadow_surf.blit(shadow_alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(shadow_surf, (x + shadow_offset[0], y + shadow_offset[1]))
    
    # 发光效果
    if glow_color:
        glow_surf = font.render(text, True, glow_color)
        for i in range(glow_radius, 0, -1):
            alpha = int(80 * (1 - i / glow_radius))
            temp = pygame.Surface(glow_surf.get_size(), pygame.SRCALPHA)
            temp.fill((*glow_color, alpha))
            glow_surf_copy = glow_surf.copy()
            glow_surf_copy.blit(temp, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            for dx, dy in [(-i, 0), (i, 0), (0, -i), (0, i)]:
                surface.blit(glow_surf_copy, (x + dx, y + dy))
    
    # 主文字
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, pos)
    
    return text_surf.get_rect(topleft=pos)


def draw_rounded_panel(
    surface: Surface,
    rect: pygame.Rect,
    bg_color: Tuple[int, int, int, int],
    border_color: Optional[Tuple[int, int, int]] = None,
    border_width: int = 2,
    border_radius: int = 12,
    glow: bool = False,
    glow_color: Optional[Tuple[int, int, int]] = None,
) -> None:
    """绘制圆角面板"""
    # 面板背景
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, bg_color, (0, 0, rect.width, rect.height), border_radius=border_radius)
    surface.blit(panel, rect.topleft)
    
    # 发光边框
    if glow and glow_color:
        draw_glow_border(surface, rect, glow_color, glow_radius=4, border_width=border_width, border_radius=border_radius)
    elif border_color:
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=border_radius)


def create_vignette(size: Tuple[int, int], intensity: float = 0.4) -> Surface:
    """创建暗角效果"""
    w, h = size
    vignette = pygame.Surface(size, pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    
    # 简化版暗角 - 只绘制边缘
    for ring in range(0, int(max_dist), 4):
        if ring < max_dist * 0.5:
            continue
        t = (ring - max_dist * 0.5) / (max_dist * 0.5)
        alpha = int(255 * intensity * t * t)
        pygame.draw.circle(vignette, (0, 0, 0, alpha), (cx, cy), int(max_dist - ring), width=4)
    
    return vignette


def draw_decorative_line(
    surface: Surface,
    start: Tuple[int, int],
    end: Tuple[int, int],
    color: Tuple[int, int, int],
    width: int = 2,
    glow: bool = True,
) -> None:
    """绘制装饰性线条"""
    if glow:
        # 发光层
        for i in range(3, 0, -1):
            alpha = int(60 * (1 - i / 3))
            pygame.draw.line(surface, (*color, alpha), start, end, width + i * 2)
    pygame.draw.line(surface, color, start, end, width)


def animate_pulse(base_value: float, time_ms: int, speed: float = 0.003, amplitude: float = 0.1) -> float:
    """生成脉冲动画值"""
    return base_value + math.sin(time_ms * speed) * amplitude * base_value
