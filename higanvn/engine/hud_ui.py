"""
HUD UI - 现代视觉小说风格界面按钮和提示
采用精致的按钮样式、优雅的提示条
集成新的UI组件库，支持底部菜单栏和快捷菜单
"""
from __future__ import annotations

from typing import Callable, Dict, Tuple, Optional
import math

import pygame
from pygame import Surface

from higanvn.engine.ui_components import (
    UITheme, UIMenuBar, UIQuickMenu, UIStatusIndicator,
    create_bottom_menu_bar, create_quick_menu
)

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


class ModernHUD:
    """现代化HUD界面"""
    def __init__(
        self,
        font: pygame.font.Font,
        hint_font: pygame.font.Font,
        on_auto_toggle: Optional[Callable] = None,
        on_skip_toggle: Optional[Callable] = None,
        on_backlog: Optional[Callable] = None,
        on_save: Optional[Callable] = None,
        on_load: Optional[Callable] = None,
        on_config: Optional[Callable] = None,
    ):
        self.font = font
        self.hint_font = hint_font

        # UI组件
        self.theme = UITheme()
        self.menu_bar = create_bottom_menu_bar(
            font,
            self.theme,
            auto=on_auto_toggle,
            skip=on_skip_toggle,
            backlog=on_backlog,
            save=on_save,
            load=on_load,
            config=on_config,
        )
        self.quick_menu = create_quick_menu(
            font,
            self.theme,
            auto=on_auto_toggle,
            skip=on_skip_toggle,
            backlog=on_backlog,
            save=on_save,
            load=on_load,
            config=on_config,
        )
        self.status_indicator = UIStatusIndicator(font, self.theme)

        # 状态
        self.auto_mode = False
        self.skip_mode = False
        self.voice_playing = False

    def update(self, mouse_pos: Optional[Tuple[int, int]], dt: float) -> None:
        """更新HUD"""
        self.menu_bar.update(mouse_pos, dt)
        self.quick_menu.update(mouse_pos, dt)
        self.status_indicator.update(dt)

        # 更新状态指示器
        self.status_indicator.auto_mode = self.auto_mode
        self.status_indicator.skip_mode = self.skip_mode
        self.status_indicator.voice_playing = self.voice_playing

    def draw(self, canvas: Surface) -> None:
        """绘制HUD"""
        # 绘制底部菜单栏
        self.menu_bar.draw(canvas)

        # 绘制快捷菜单（如果可见）
        self.quick_menu.draw(canvas)

        # 绘制状态指示器
        self.status_indicator.draw(canvas)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """处理事件，返回触发的动作"""
        # 快捷菜单事件
        action = self.quick_menu.handle_event(event)
        if action:
            return action

        # 菜单栏事件
        if self.menu_bar.handle_event(event):
            return "menu_action"  # 菜单栏点击已通过回调处理

        # 右键显示快捷菜单
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:  # 右键
            self.quick_menu.show_at(event.pos)
            return "quick_menu_shown"

        # 中键显示快捷菜单
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:  # 中键
            self.quick_menu.show_at(event.pos)
            return "quick_menu_shown"

        return None

    def set_auto_mode(self, enabled: bool) -> None:
        """设置自动模式"""
        self.auto_mode = enabled

    def set_skip_mode(self, enabled: bool) -> None:
        """设置快进模式"""
        self.skip_mode = enabled

    def set_voice_playing(self, playing: bool) -> None:
        """设置语音播放状态"""
        self.voice_playing = playing


def draw_ui_buttons(
    canvas: Surface,
    font: pygame.font.Font,
    get_mouse_pos: Callable[[], Optional[tuple[int, int]]],
) -> Dict[str, pygame.Rect]:
    """兼容性函数 - 绘制现代风格的UI按钮（已废弃，请使用ModernHUD）"""
    # 创建一个临时的HUD实例用于兼容性
    hud = ModernHUD(font, font)  # hint_font使用font
    mouse_pos = get_mouse_pos()
    hud.update(mouse_pos, 0)
    hud.draw(canvas)

    # 返回空的rect字典以保持兼容性
    return {}


def draw_hints(
    canvas: Surface,
    hint_font: pygame.font.Font,
    auto_mode: bool,
) -> None:
    """兼容性函数 - 绘制底部操作提示（已废弃，请使用ModernHUD）"""
    # 提示功能已集成到ModernHUD中
    pass
