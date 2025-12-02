"""
Settings Menu - 现代风格设置界面

Features:
- 滑块控件
- 开关控件
- 分组布局
- 动画效果
"""
from __future__ import annotations

from typing import Tuple, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import math

import pygame
from pygame import Surface

from .ui_theme import (
    Theme, draw_gradient_rect, draw_rounded_panel, 
    draw_text_with_glow, draw_glow_border
)

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class ControlType(Enum):
    """控件类型"""
    TOGGLE = "toggle"
    SLIDER = "slider"
    BUTTON = "button"


@dataclass
class SettingItem:
    """设置项"""
    key: str
    label: str
    control_type: ControlType
    value: Any = None
    min_val: float = 0.0
    max_val: float = 100.0
    step: float = 1.0
    display_format: str = "{:.0f}"
    
    # UI状态
    hover: bool = False
    hover_progress: float = 0.0
    dragging: bool = False


def open_settings_menu(renderer) -> None:
    """
    打开现代风格设置菜单。
    """
    # 获取配置
    ui = (renderer._config.get("ui") if isinstance(renderer._config, dict) else {}) or {}
    
    # 定义设置项
    settings: List[SettingItem] = [
        SettingItem(
            key="toggle_auto",
            label="自动播放",
            control_type=ControlType.TOGGLE,
            value=renderer._auto_mode,
        ),
        SettingItem(
            key="typing_speed",
            label="文字速度",
            control_type=ControlType.SLIDER,
            value=renderer._typing_speed,
            min_val=0.0,
            max_val=120.0,
            step=5.0,
            display_format="{:.0f}",
        ),
        SettingItem(
            key="textbox_opacity",
            label="对话框透明度",
            control_type=ControlType.SLIDER,
            value=int(ui.get("textbox_opacity", 160)),
            min_val=50,
            max_val=255,
            step=5,
            display_format="{:.0f}",
        ),
        SettingItem(
            key="auto_delay",
            label="自动播放延迟",
            control_type=ControlType.SLIDER,
            value=getattr(renderer, '_auto_delay_line_ms', 1500),
            min_val=500,
            max_val=5000,
            step=100,
            display_format="{:.0f}ms",
        ),
        SettingItem(
            key="text_outline",
            label="文字描边",
            control_type=ControlType.TOGGLE,
            value=bool(ui.get("text_outline", False)),
        ),
        SettingItem(
            key="text_shadow",
            label="文字阴影",
            control_type=ControlType.TOGGLE,
            value=bool(ui.get("text_shadow", True)),
        ),
    ]
    
    selected_idx = 0
    last_time = pygame.time.get_ticks()
    
    # 面板尺寸
    panel_width = 600
    panel_height = 480
    panel_x = (LOGICAL_SIZE[0] - panel_width) // 2
    panel_y = (LOGICAL_SIZE[1] - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    # 设置项布局
    item_height = 60
    item_margin = 20
    items_start_y = panel_y + 80
    
    waiting = True
    while waiting:
        now = pygame.time.get_ticks()
        dt = (now - last_time) / 1000.0
        last_time = now
        
        # 更新动画
        for i, item in enumerate(settings):
            target = 1.0 if i == selected_idx else 0.0
            diff = target - item.hover_progress
            item.hover_progress += diff * 10.0 * dt
            item.hover_progress = max(0.0, min(1.0, item.hover_progress))
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _apply_settings(renderer, settings, ui)
                    waiting = False
                
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_idx = (selected_idx + 1) % len(settings)
                
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected_idx = (selected_idx - 1) % len(settings)
                
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    _adjust_value(settings[selected_idx], -1)
                
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    _adjust_value(settings[selected_idx], 1)
                
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    _toggle_value(settings[selected_idx])
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = _transform_mouse(event.pos, renderer)
                
                # 检查点击的设置项
                for i, item in enumerate(settings):
                    item_rect = pygame.Rect(
                        panel_x + item_margin,
                        items_start_y + i * item_height,
                        panel_width - item_margin * 2,
                        item_height - 8
                    )
                    if item_rect.collidepoint((mx, my)):
                        selected_idx = i
                        if item.control_type == ControlType.TOGGLE:
                            _toggle_value(item)
                        elif item.control_type == ControlType.SLIDER:
                            item.dragging = True
                            _update_slider_from_mouse(item, mx, item_rect)
            
            if event.type == pygame.MOUSEBUTTONUP:
                for item in settings:
                    item.dragging = False
            
            if event.type == pygame.MOUSEMOTION:
                mx, my = _transform_mouse(event.pos, renderer)
                for i, item in enumerate(settings):
                    if item.dragging:
                        item_rect = pygame.Rect(
                            panel_x + item_margin,
                            items_start_y + i * item_height,
                            panel_width - item_margin * 2,
                            item_height - 8
                        )
                        _update_slider_from_mouse(item, mx, item_rect)
        
        # 渲染
        renderer._render(flip=False, tick=False)
        canvas = renderer.canvas
        
        # 半透明遮罩
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        canvas.blit(overlay, (0, 0))
        
        # 面板背景
        draw_gradient_rect(
            canvas,
            panel_rect,
            (30, 40, 60, 240),
            (20, 25, 40, 250),
            border_radius=16
        )
        
        # 面板边框
        draw_glow_border(canvas, panel_rect, Theme.PRIMARY, glow_radius=4, border_radius=16)
        
        # 标题
        title_text = "设置"
        title_surf = renderer.font.render(title_text, True, Theme.TEXT_PRIMARY)
        canvas.blit(title_surf, (panel_rect.centerx - title_surf.get_width() // 2, panel_y + 24))
        
        # 分隔线
        line_y = panel_y + 64
        pygame.draw.line(canvas, Theme.PANEL_BORDER, 
                        (panel_x + 20, line_y), (panel_x + panel_width - 20, line_y), 2)
        
        # 绘制设置项
        for i, item in enumerate(settings):
            item_y = items_start_y + i * item_height
            item_rect = pygame.Rect(
                panel_x + item_margin,
                item_y,
                panel_width - item_margin * 2,
                item_height - 8
            )
            
            _draw_setting_item(canvas, renderer.font, item, item_rect, now)
        
        # 底部提示
        hint_text = "↑↓选择  ←→调节  回车确认  ESC返回"
        hint_font = pygame.font.Font(None, 20)  # 使用小号字体
        try:
            hint_surf = renderer.font.render(hint_text, True, Theme.TEXT_DIM)
            canvas.blit(hint_surf, (panel_rect.centerx - hint_surf.get_width() // 2, 
                                    panel_rect.bottom - 36))
        except:
            pass
        
        # 缩放到窗口
        _present(renderer)
        renderer.clock.tick(60)


def _transform_mouse(pos: Tuple[int, int], renderer) -> Tuple[int, int]:
    """将窗口坐标转换为canvas坐标"""
    mx, my = pos
    lt = getattr(renderer, '_last_transform', None)
    if lt:
        scale, offx, offy, dw, dh = lt
        if offx <= mx <= offx + dw and offy <= my <= offy + dh:
            return int((mx - offx) / scale), int((my - offy) / scale)
    return mx, my


def _present(renderer) -> None:
    """呈现画面到屏幕"""
    canvas = renderer.canvas
    screen = renderer.screen
    win_w, win_h = screen.get_size()
    cw, ch = canvas.get_size()
    scale = min(win_w / cw, win_h / ch)
    dst_w, dst_h = int(cw * scale), int(ch * scale)
    scaled = pygame.transform.smoothscale(canvas, (dst_w, dst_h))
    x = (win_w - dst_w) // 2
    y = (win_h - dst_h) // 2
    screen.fill((0, 0, 0))
    screen.blit(scaled, (x, y))
    pygame.display.flip()


def _adjust_value(item: SettingItem, direction: int) -> None:
    """调整设置值"""
    if item.control_type == ControlType.SLIDER:
        item.value = max(item.min_val, min(item.max_val, 
                        float(item.value) + direction * item.step))
    elif item.control_type == ControlType.TOGGLE:
        item.value = not item.value


def _toggle_value(item: SettingItem) -> None:
    """切换开关值"""
    if item.control_type == ControlType.TOGGLE:
        item.value = not item.value


def _update_slider_from_mouse(item: SettingItem, mx: int, rect: pygame.Rect) -> None:
    """从鼠标位置更新滑块值"""
    if item.control_type != ControlType.SLIDER:
        return
    
    slider_x = rect.x + 200
    slider_w = rect.width - 280
    
    t = (mx - slider_x) / slider_w
    t = max(0.0, min(1.0, t))
    
    item.value = item.min_val + t * (item.max_val - item.min_val)
    # 对齐到步长
    item.value = round(item.value / item.step) * item.step
    item.value = max(item.min_val, min(item.max_val, item.value))


def _apply_settings(renderer, settings: List[SettingItem], ui: dict) -> None:
    """应用设置到renderer"""
    for item in settings:
        if item.key == "toggle_auto":
            renderer._auto_mode = bool(item.value)
        elif item.key == "typing_speed":
            renderer._typing_speed = float(item.value)
            renderer._typing_enabled = float(item.value) > 0.0
        elif item.key == "textbox_opacity":
            ui["textbox_opacity"] = int(item.value)
        elif item.key == "auto_delay":
            renderer._auto_delay_line_ms = int(item.value)
        elif item.key == "text_outline":
            ui["text_outline"] = bool(item.value)
        elif item.key == "text_shadow":
            ui["text_shadow"] = bool(item.value)
    
    # 保存回配置
    try:
        if isinstance(renderer._config, dict):
            renderer._config["ui"] = ui
    except Exception:
        pass


def _draw_setting_item(
    canvas: Surface,
    font: pygame.font.Font,
    item: SettingItem,
    rect: pygame.Rect,
    time_ms: int,
) -> None:
    """绘制设置项"""
    hover_t = item.hover_progress
    
    # 背景
    if hover_t > 0.1:
        bg_alpha = int(40 * hover_t)
        bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (*Theme.PRIMARY, bg_alpha), 
                        (0, 0, rect.width, rect.height), border_radius=8)
        canvas.blit(bg_surf, rect.topleft)
    
    # 选中指示器
    if hover_t > 0.3:
        indicator_w = int(4 * hover_t)
        pygame.draw.rect(canvas, Theme.ACCENT, 
                        (rect.x - 8, rect.y + 8, indicator_w, rect.height - 16),
                        border_radius=2)
    
    # 标签
    label_color = Theme.TEXT_PRIMARY if hover_t > 0.5 else Theme.TEXT_SECONDARY
    label_surf = font.render(item.label, True, label_color)
    canvas.blit(label_surf, (rect.x + 12, rect.centery - label_surf.get_height() // 2))
    
    # 控件
    if item.control_type == ControlType.TOGGLE:
        _draw_toggle(canvas, item, rect, time_ms)
    elif item.control_type == ControlType.SLIDER:
        _draw_slider(canvas, font, item, rect, time_ms)


def _draw_toggle(canvas: Surface, item: SettingItem, rect: pygame.Rect, time_ms: int) -> None:
    """绘制开关控件"""
    toggle_w = 50
    toggle_h = 26
    toggle_x = rect.right - toggle_w - 20
    toggle_y = rect.centery - toggle_h // 2
    toggle_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
    
    is_on = bool(item.value)
    
    # 背景
    bg_color = Theme.PRIMARY if is_on else (60, 60, 70)
    pygame.draw.rect(canvas, bg_color, toggle_rect, border_radius=toggle_h // 2)
    pygame.draw.rect(canvas, Theme.PANEL_BORDER, toggle_rect, 2, border_radius=toggle_h // 2)
    
    # 滑块
    knob_radius = toggle_h // 2 - 3
    knob_x = toggle_x + toggle_w - knob_radius - 5 if is_on else toggle_x + knob_radius + 5
    pygame.draw.circle(canvas, (255, 255, 255), (knob_x, toggle_rect.centery), knob_radius)
    
    # 文字
    text = "开" if is_on else "关"
    text_x = toggle_x + 10 if is_on else toggle_x + toggle_w - 26
    try:
        small_font = pygame.font.Font(None, 18)
        text_surf = small_font.render(text, True, (255, 255, 255) if is_on else Theme.TEXT_DIM)
        canvas.blit(text_surf, (text_x, toggle_rect.centery - text_surf.get_height() // 2))
    except:
        pass


def _draw_slider(
    canvas: Surface,
    font: pygame.font.Font,
    item: SettingItem,
    rect: pygame.Rect,
    time_ms: int,
) -> None:
    """绘制滑块控件"""
    slider_x = rect.x + 200
    slider_w = rect.width - 280
    slider_h = 8
    slider_y = rect.centery - slider_h // 2
    slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
    
    # 计算进度
    t = (float(item.value) - item.min_val) / (item.max_val - item.min_val)
    t = max(0.0, min(1.0, t))
    
    # 背景轨道
    pygame.draw.rect(canvas, (50, 55, 70), slider_rect, border_radius=4)
    
    # 填充部分
    fill_w = int(slider_w * t)
    if fill_w > 0:
        fill_rect = pygame.Rect(slider_x, slider_y, fill_w, slider_h)
        pygame.draw.rect(canvas, Theme.PRIMARY, fill_rect, border_radius=4)
    
    # 滑块圆点
    knob_x = slider_x + int(slider_w * t)
    knob_radius = 10
    
    # 发光效果
    if item.dragging or item.hover_progress > 0.5:
        glow_surf = pygame.Surface((knob_radius * 4, knob_radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*Theme.PRIMARY_LIGHT, 60), 
                          (knob_radius * 2, knob_radius * 2), knob_radius * 2)
        canvas.blit(glow_surf, (knob_x - knob_radius * 2, slider_y + slider_h // 2 - knob_radius * 2))
    
    pygame.draw.circle(canvas, Theme.PRIMARY_LIGHT, (knob_x, slider_y + slider_h // 2), knob_radius)
    pygame.draw.circle(canvas, (255, 255, 255), (knob_x, slider_y + slider_h // 2), knob_radius - 3)
    
    # 数值显示
    if float(item.value) == 0 and item.key == "typing_speed":
        value_text = "瞬显"
    else:
        value_text = item.display_format.format(item.value)
    
    value_surf = font.render(value_text, True, Theme.TEXT_SECONDARY)
    canvas.blit(value_surf, (slider_x + slider_w + 20, rect.centery - value_surf.get_height() // 2))
