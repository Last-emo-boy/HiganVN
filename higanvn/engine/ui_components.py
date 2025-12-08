"""
UI Components Library - Modern Visual Novel Interface
基于现代风格的低阻力阅读UI组件库

核心理念：
- 低阻力阅读：文本框靠下，快捷功能围绕边缘
- 双层菜单：小窗快捷菜单 + 全屏系统菜单
- 可定制主题：主色+角色主题色+中性底色
- 多输入支持：鼠标、键盘、触控
"""
from __future__ import annotations

from typing import Callable, Dict, Tuple, Optional, List, Any
import math
import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)

# ============================================================================
# 主题系统 - 参数化配置
# ============================================================================

class UITheme:
    """可定制UI主题"""
    def __init__(self):
        # 主色调（现代深色玻璃风）
        self.primary = (40, 45, 60)
        self.primary_dark = (30, 35, 50)
        self.primary_light = (60, 70, 90)

        # 角色主题色（樱花粉/活力橙）
        self.accent = (255, 140, 160)  # 柔和的粉色
        self.accent_glow = (255, 180, 200)

        # 中性底色（深色半透明）
        self.neutral_bg = (10, 12, 18, 230)
        self.neutral_border = (100, 110, 130)

        # 文字颜色层级
        self.text_primary = (240, 240, 245)
        self.text_secondary = (180, 185, 195)
        self.text_dim = (120, 125, 135)

        # 按钮样式参数
        self.button_corner_radius = 12
        self.button_shadow_offset = 3
        self.button_glow_intensity = 0.8

        # 面板样式参数
        self.panel_corner_radius = 20
        self.panel_shadow_alpha = 100

        # 字体配置（支持中日韩等宽组合）
        self.font_family = "msyh"  # 微软雅黑作为默认
        self.font_fallback = ["simsun", "arial"]  # 宋体、Arial作为后备

# 全局主题实例
ui_theme = UITheme()

# ============================================================================
# 基础绘制函数
# ============================================================================

def draw_gradient_rect(
    surface: Surface,
    rect: pygame.Rect,
    color_top: Tuple[int, int, int],
    color_bottom: Tuple[int, int, int],
    alpha: int = 255
) -> None:
    """绘制渐变矩形"""
    width, height = rect.size
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        color = (r, g, b, alpha) if alpha < 255 else (r, g, b)
        pygame.draw.line(surface, color, (0, y), (width, y))

def draw_rounded_rect(
    surface: Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    radius: int = 8,
    alpha: int = 255
) -> None:
    """绘制圆角矩形"""
    if alpha < 255:
        temp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(temp, (*color, alpha), (0, 0, *rect.size), border_radius=radius)
        surface.blit(temp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_glow_effect(
    surface: Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    intensity: float = 0.6,
    radius: int = 12
) -> None:
    """绘制发光效果 (优化版)"""
    # 简单的高性能发光：绘制几个不同透明度的扩充矩形
    steps = 3
    base_alpha = int(100 * intensity / steps)
    
    for i in range(steps):
        inflate = radius * (i + 1) // steps
        glow_rect = rect.inflate(inflate * 2, inflate * 2)
        
        # 使用圆角矩形模拟柔和边缘
        s = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, base_alpha), s.get_rect(), border_radius=radius + inflate)
        surface.blit(s, glow_rect.topleft)

# ============================================================================
# UI组件类
# ============================================================================

class UIButton:
    """现代化按钮组件"""
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        theme: Optional[UITheme] = None,
        on_click: Optional[Callable] = None
    ):
        self.rect = rect
        self.text = text
        self.font = font
        self.theme = theme or ui_theme
        self.on_click = on_click

        self.hovered = False
        self.pressed = False
        self.glow_phase = 0.0

    def update(self, mouse_pos: Optional[Tuple[int, int]], dt: float) -> None:
        """更新按钮状态"""
        self.hovered = self.rect.collidepoint(mouse_pos) if mouse_pos else False
        if self.hovered:
            self.glow_phase = (self.glow_phase + dt * 0.005) % (2 * math.pi)

    def draw(self, surface: Surface) -> None:
        """绘制按钮"""
        theme = self.theme

        # 状态颜色计算
        if self.pressed:
            bg_color = theme.primary_dark
            offset = 2
        elif self.hovered:
            bg_color = theme.primary_light
            offset = 0
        else:
            bg_color = theme.primary
            offset = 0

        # 阴影 (仅在未按下时显示)
        if not self.pressed:
            shadow_rect = self.rect.move(theme.button_shadow_offset, theme.button_shadow_offset)
            draw_rounded_rect(
                surface, shadow_rect, (0, 0, 0),
                radius=theme.button_corner_radius, alpha=80
            )

        # 发光效果（悬停时）
        if self.hovered:
            pulse = 0.8 + 0.2 * math.sin(self.glow_phase)
            draw_glow_effect(surface, self.rect, theme.accent, intensity=theme.button_glow_intensity * pulse, radius=8)

        # 按钮主体
        draw_rect = self.rect.move(offset, offset)
        draw_rounded_rect(
            surface, draw_rect, bg_color,
            radius=theme.button_corner_radius
        )

        # 边框
        border_color = theme.accent if self.hovered else theme.neutral_border
        pygame.draw.rect(surface, border_color, draw_rect, width=1 if not self.hovered else 2, border_radius=theme.button_corner_radius)

        # 文字
        text_color = theme.text_primary if not self.hovered else theme.accent_glow
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=draw_rect.center)

        # 文字阴影
        if not self.pressed:
            shadow_surf = self.font.render(self.text, True, (0, 0, 0))
            surface.blit(shadow_surf, text_rect.move(1, 1))
        
        surface.blit(text_surf, text_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件，返回是否点击"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self.pressed = False
        return False

class UIMenuBar:
    """底部功能带菜单栏"""
    def __init__(
        self,
        font: pygame.font.Font,
        theme: UITheme = None,
        items: List[Dict[str, Any]] = None
    ):
        self.font = font
        self.theme = theme or ui_theme
        self.items = items or []

        # 布局参数
        self.margin_bottom = 20
        self.button_height = 36
        self.button_spacing = 8
        self.bar_height = self.button_height + 2 * self.margin_bottom

        self.buttons: List[UIButton] = []
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        """布局按钮"""
        if not self.items:
            return

        total_width = sum(
            self.font.size(item.get("text", ""))[0] + 40  # 文字宽度 + 内边距
            for item in self.items
        ) + (len(self.items) - 1) * self.button_spacing

        start_x = (LOGICAL_SIZE[0] - total_width) // 2
        y = LOGICAL_SIZE[1] - self.bar_height + self.margin_bottom

        self.buttons.clear()
        for item in self.items:
            text = item.get("text", "")
            text_width = self.font.size(text)[0]
            button_width = text_width + 40

            rect = pygame.Rect(start_x, y, button_width, self.button_height)
            button = UIButton(rect, text, self.font, self.theme, item.get("on_click"))
            self.buttons.append(button)

            start_x += button_width + self.button_spacing

    def update(self, mouse_pos: Optional[Tuple[int, int]], dt: float) -> None:
        """更新菜单栏"""
        for button in self.buttons:
            button.update(mouse_pos, dt)

    def draw(self, surface: Surface) -> None:
        """绘制菜单栏"""
        if not self.buttons:
            return

        theme = self.theme

        # 菜单栏背景面板
        bar_rect = pygame.Rect(
            0,
            LOGICAL_SIZE[1] - self.bar_height,
            LOGICAL_SIZE[0],
            self.bar_height
        )

        # 使用悬浮条样式而不是贴底样式
        margin_side = 40
        float_rect = bar_rect.inflate(-margin_side * 2, -10)
        float_rect.bottom = LOGICAL_SIZE[1] - 10
        
        draw_rounded_rect(
            surface, float_rect, theme.neutral_bg[:3],
            radius=theme.panel_corner_radius, alpha=theme.neutral_bg[3]
        )
        
        # 装饰线
        line_rect = pygame.Rect(float_rect.centerx - 100, float_rect.top + 5, 200, 2)
        draw_rounded_rect(surface, line_rect, theme.accent, radius=1, alpha=100)

        # 绘制按钮
        for button in self.buttons:
            button.draw(surface)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件"""
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False

class UIQuickMenu:
    """快捷菜单（右键/中键弹出）"""
    def __init__(
        self,
        font: pygame.font.Font,
        theme: Optional[UITheme] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ):
        self.font = font
        self.theme = theme or ui_theme
        self.items = items or self._default_items()

        self.visible = False
        self.position = (0, 0)
        self.buttons: List[UIButton] = []

        # 布局参数
        self.item_height = 32
        self.item_width = 120
        self.padding = 8

    def _default_items(self) -> List[Dict[str, Any]]:
        """默认快捷菜单项"""
        return [
            {"text": "自动", "action": "auto", "key": "A"},
            {"text": "快进", "action": "skip", "key": "F"},
            {"text": "记录", "action": "backlog", "key": "Tab"},
            {"text": "保存", "action": "save", "key": "F5"},
            {"text": "读取", "action": "load", "key": "F9"},
            {"text": "设置", "action": "config", "key": "C"},
        ]

    def show_at(self, position: Tuple[int, int]) -> None:
        """在指定位置显示菜单"""
        self.position = position
        self.visible = True
        self._layout_buttons()

    def hide(self) -> None:
        """隐藏菜单"""
        self.visible = False

    def _layout_buttons(self) -> None:
        """布局按钮"""
        self.buttons.clear()

        menu_width = self.item_width + 2 * self.padding
        menu_height = len(self.items) * self.item_height + 2 * self.padding

        # 确保菜单不超出屏幕
        x = min(self.position[0], LOGICAL_SIZE[0] - menu_width)
        y = min(self.position[1], LOGICAL_SIZE[1] - menu_height)

        for i, item in enumerate(self.items):
            button_rect = pygame.Rect(
                x + self.padding,
                y + self.padding + i * self.item_height,
                self.item_width,
                self.item_height
            )
            button = UIButton(
                button_rect,
                item["text"],
                self.font,
                self.theme,
                on_click=item.get("on_click")
            )
            self.buttons.append(button)

    def update(self, mouse_pos: Optional[Tuple[int, int]], dt: float) -> None:
        """更新菜单"""
        if not self.visible:
            return

        for button in self.buttons:
            button.update(mouse_pos, dt)

    def draw(self, surface: Surface) -> None:
        """绘制菜单"""
        if not self.visible:
            return

        theme = self.theme

        # 计算菜单尺寸
        menu_width = self.item_width + 2 * self.padding
        menu_height = len(self.items) * self.item_height + 2 * self.padding

        menu_rect = pygame.Rect(
            self.position[0] - self.padding,
            self.position[1] - self.padding,
            menu_width,
            menu_height
        )

        # 菜单背景
        draw_rounded_rect(
            surface, menu_rect, theme.neutral_bg[:3],
            radius=theme.panel_corner_radius, alpha=240
        )

        # 边框
        pygame.draw.rect(
            surface, theme.neutral_border, menu_rect,
            width=2, border_radius=theme.panel_corner_radius
        )

        # 绘制按钮
        for button in self.buttons:
            button.draw(surface)

        # 绘制快捷键提示
        for i, (button, item) in enumerate(zip(self.buttons, self.items)):
            key_text = item.get("key", "")
            if key_text:
                key_surf = self.font.render(key_text, True, theme.text_dim)
                key_rect = key_surf.get_rect(
                    right=button.rect.right - 8,
                    centery=button.rect.centery
                )
                surface.blit(key_surf, key_rect)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """处理事件，返回触发的动作"""
        # 右键显示菜单
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not self.visible:
                self.show_at(event.pos)
                return "quick_menu_shown"
            else:
                self.hide()
                return "quick_menu_hidden"

        if not self.visible:
            return None

        # 点击外部隐藏菜单
        if event.type == pygame.MOUSEBUTTONDOWN:
            menu_rect = pygame.Rect(
                self.position[0] - self.padding,
                self.position[1] - self.padding,
                self.item_width + 2 * self.padding,
                len(self.items) * self.item_height + 2 * self.padding
            )
            if not menu_rect.collidepoint(event.pos):
                self.hide()
                return None

        # 处理按钮点击
        for button, item in zip(self.buttons, self.items):
            if button.handle_event(event):
                self.hide()
                return item.get("action")

        return None

class UIStatusIndicator:
    """状态指示器（自动模式、快进模式等）"""
    def __init__(
        self,
        font: pygame.font.Font,
        theme: Optional[UITheme] = None
    ):
        self.font = font
        self.theme = theme or ui_theme

        self.auto_mode = False
        self.skip_mode = False
        self.voice_playing = False

        self.animation_phase = 0.0

    def set_auto_mode(self, enabled: bool) -> None:
        """设置自动模式"""
        self.auto_mode = enabled

    def set_skip_mode(self, enabled: bool) -> None:
        """设置快进模式"""
        self.skip_mode = enabled

    def set_voice_playing(self, playing: bool) -> None:
        """设置语音播放状态"""
        self.voice_playing = playing

    def update(self, dt: float) -> None:
        """更新动画"""
        self.animation_phase = (self.animation_phase + dt * 0.004) % (2 * math.pi)

    def draw(self, surface: Surface) -> None:
        """绘制状态指示器"""
        theme = self.theme
        indicators = []

        if self.auto_mode:
            indicators.append(("AUTO", theme.accent))
        if self.skip_mode:
            indicators.append(("SKIP", theme.primary_light))
        if self.voice_playing:
            indicators.append(("🔊", theme.accent_glow))

        if not indicators:
            return

        # 布局在右上角
        x = LOGICAL_SIZE[0] - 20
        y = 20

        for text, color in reversed(indicators):
            text_surf = self.font.render(text, True, color)
            text_rect = text_surf.get_rect(topright=(x, y))

            # 背景框
            bg_rect = text_rect.inflate(16, 8)
            draw_rounded_rect(
                surface, bg_rect, theme.neutral_bg[:3],
                radius=theme.button_corner_radius, alpha=200
            )

            # 发光效果
            if text in ["AUTO", "SKIP"]:
                pulse = 0.6 + 0.4 * math.sin(self.animation_phase)
                draw_glow_effect(surface, bg_rect, color, pulse * 0.3)

            # 文字
            surface.blit(text_surf, text_rect)
            x -= bg_rect.width + 10

# ============================================================================
# 便捷函数
# ============================================================================

def create_bottom_menu_bar(
    font: pygame.font.Font,
    theme: Optional[UITheme] = None,
    **actions
) -> UIMenuBar:
    """创建底部菜单栏"""
    items = [
        {"text": "自动", "on_click": actions.get("auto")},
        {"text": "快进", "on_click": actions.get("skip")},
        {"text": "记录", "on_click": actions.get("backlog")},
        {"text": "保存", "on_click": actions.get("save")},
        {"text": "读取", "on_click": actions.get("load")},
        {"text": "设置", "on_click": actions.get("config")},
    ]
    return UIMenuBar(font, theme, items)

def create_quick_menu(
    font: pygame.font.Font,
    theme: Optional[UITheme] = None,
    **actions
) -> UIQuickMenu:
    """创建快捷菜单"""
    items = [
        {"text": "自动", "action": "auto", "key": "A", "on_click": actions.get("auto")},
        {"text": "快进", "action": "skip", "key": "F", "on_click": actions.get("skip")},
        {"text": "记录", "action": "backlog", "key": "Tab", "on_click": actions.get("backlog")},
        {"text": "保存", "action": "save", "key": "F5", "on_click": actions.get("save")},
        {"text": "读取", "action": "load", "key": "F9", "on_click": actions.get("load")},
        {"text": "设置", "action": "config", "key": "C", "on_click": actions.get("config")},
    ]
    menu = UIQuickMenu(font, theme, items)
    return menu