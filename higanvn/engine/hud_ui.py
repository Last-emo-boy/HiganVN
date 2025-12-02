"""
HUD UI - 现代视觉小说风格界面按钮和提示
采用精致的按钮样式、优雅的提示条
"""
from __future__ import annotations

from typing import Callable, Dict, Tuple, Optional
import math

import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)

# 主题色
class Theme:
    BUTTON_BG = (25, 30, 45)
    BUTTON_HOVER = (45, 55, 80)
    BUTTON_BORDER = (80, 100, 140)
    BUTTON_GLOW = (100, 140, 200)
    TEXT_PRIMARY = (220, 225, 235)
    TEXT_ACCENT = (255, 200, 100)
    HINT_BG = (15, 20, 30)
    AUTO_COLOR = (100, 220, 140)


def draw_ui_buttons(
    canvas: Surface,
    font: pygame.font.Font,
    get_mouse_pos: Callable[[], Optional[tuple[int, int]]],
) -> Dict[str, pygame.Rect]:
    """绘制现代风格的UI按钮"""
    pad = 12
    btn_w, btn_h = 72, 34
    right = LOGICAL_SIZE[0] - pad
    top = pad
    
    back_rect = pygame.Rect(right - btn_w * 2 - pad - 8, top, btn_w, btn_h)
    log_rect = pygame.Rect(right - btn_w, top, btn_w, btn_h)
    
    mouse = get_mouse_pos()
    now = pygame.time.get_ticks()
    
    for rect, label in ((back_rect, "◀ 返回"), (log_rect, "📜 记录")):
        hovered = bool(mouse and rect.collidepoint(mouse))
        
        # 按钮背景
        btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # 渐变背景
        bg_color = Theme.BUTTON_HOVER if hovered else Theme.BUTTON_BG
        alpha = 200 if hovered else 160
        
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            r = int(bg_color[0] + 10 * t)
            g = int(bg_color[1] + 15 * t)
            b = int(bg_color[2] + 20 * t)
            pygame.draw.line(btn_surf, (r, g, b, alpha), (0, y), (rect.width, y))
        
        # 圆角遮罩
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=8)
        btn_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        
        canvas.blit(btn_surf, rect.topleft)
        
        # 边框
        if hovered:
            # 发光效果
            glow_alpha = int(60 + 30 * math.sin(now * 0.005))
            pygame.draw.rect(canvas, (*Theme.BUTTON_GLOW, glow_alpha), rect.inflate(4, 4), width=2, border_radius=10)
            pygame.draw.rect(canvas, Theme.BUTTON_GLOW, rect, width=2, border_radius=8)
        else:
            pygame.draw.rect(canvas, (*Theme.BUTTON_BORDER, 100), rect, width=1, border_radius=8)
        
        # 文字
        text_color = Theme.TEXT_ACCENT if hovered else Theme.TEXT_PRIMARY
        txt_surf = font.render(label, True, text_color)
        txt_rect = txt_surf.get_rect(center=rect.center)
        
        # 文字阴影
        shadow = font.render(label, True, (0, 0, 0))
        canvas.blit(shadow, (txt_rect.x + 1, txt_rect.y + 1))
        canvas.blit(txt_surf, txt_rect)
    
    return {"back": back_rect, "log": log_rect}


def draw_hints(
    canvas: Surface,
    hint_font: pygame.font.Font,
    auto_mode: bool,
) -> None:
    """绘制底部操作提示"""
    # 简化的提示文字
    hints = [
        ("Tab", "记录"),
        ("M", "分支"),
        ("A", "自动"),
        ("F", "快进"),
        ("F5/F9", "快存/读"),
    ]
    
    margin = 12
    hint_height = 26
    hint_y = LOGICAL_SIZE[1] - hint_height - margin
    
    # 计算总宽度
    total_width = 0
    for key, desc in hints:
        key_surf = hint_font.render(key, True, (255, 255, 255))
        desc_surf = hint_font.render(desc, True, (255, 255, 255))
        total_width += key_surf.get_width() + desc_surf.get_width() + 24
    total_width += 20  # 额外边距
    
    # 背景面板
    panel_rect = pygame.Rect(LOGICAL_SIZE[0] - total_width - margin, hint_y - 4, total_width, hint_height + 8)
    panel = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    
    # 渐变背景
    for y in range(panel_rect.height):
        alpha = int(100 + 20 * (y / panel_rect.height))
        pygame.draw.line(panel, (*Theme.HINT_BG, alpha), (0, y), (panel_rect.width, y))
    
    # 圆角
    mask = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, panel_rect.width, panel_rect.height), border_radius=6)
    panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    
    canvas.blit(panel, panel_rect.topleft)
    
    # 绘制提示项
    x = panel_rect.x + 10
    for key, desc in hints:
        # 按键背景
        key_surf = hint_font.render(key, True, Theme.TEXT_ACCENT)
        key_bg_rect = pygame.Rect(x, hint_y, key_surf.get_width() + 8, hint_height)
        key_bg = pygame.Surface((key_bg_rect.width, key_bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(key_bg, (60, 70, 90, 150), (0, 0, key_bg_rect.width, key_bg_rect.height), border_radius=4)
        canvas.blit(key_bg, key_bg_rect.topleft)
        
        # 按键文字
        canvas.blit(key_surf, (x + 4, hint_y + (hint_height - key_surf.get_height()) // 2))
        x += key_surf.get_width() + 12
        
        # 描述文字
        desc_surf = hint_font.render(desc, True, (180, 185, 195))
        canvas.blit(desc_surf, (x, hint_y + (hint_height - desc_surf.get_height()) // 2))
        x += desc_surf.get_width() + 16
    
    # AUTO 模式指示器
    if auto_mode:
        now = pygame.time.get_ticks()
        pulse = 0.7 + 0.3 * math.sin(now * 0.004)
        
        auto_text = "● AUTO"
        auto_surf = hint_font.render(auto_text, True, Theme.AUTO_COLOR)
        
        # 发光效果
        glow_surf = hint_font.render(auto_text, True, Theme.AUTO_COLOR)
        glow_alpha = pygame.Surface(glow_surf.get_size(), pygame.SRCALPHA)
        glow_alpha.fill((*Theme.AUTO_COLOR, int(100 * pulse)))
        glow_surf.blit(glow_alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        auto_x = panel_rect.x - auto_surf.get_width() - 20
        auto_y = hint_y + (hint_height - auto_surf.get_height()) // 2
        
        # 背景
        auto_bg = pygame.Surface((auto_surf.get_width() + 16, hint_height), pygame.SRCALPHA)
        pygame.draw.rect(auto_bg, (20, 40, 30, 180), (0, 0, auto_bg.get_width(), auto_bg.get_height()), border_radius=6)
        pygame.draw.rect(auto_bg, (*Theme.AUTO_COLOR, 100), (0, 0, auto_bg.get_width(), auto_bg.get_height()), width=1, border_radius=6)
        canvas.blit(auto_bg, (auto_x - 8, hint_y - 1))
        
        canvas.blit(auto_surf, (auto_x, auto_y))
