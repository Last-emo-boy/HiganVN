from __future__ import annotations

import pygame
from typing import Tuple, List, Dict, Any, Optional
from higanvn.engine.ui_components import (
    ui_theme, draw_rounded_rect, draw_gradient_rect, 
    draw_glow_effect, UIButton
)

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)

class SettingsMenu:
    """现代化设置菜单"""
    def __init__(self, renderer):
        self.renderer = renderer
        self.font = renderer.font
        self.theme = ui_theme
        self.ui_config = (renderer._config.get("ui") if isinstance(renderer._config, dict) else {}) or {}
        
        self.visible = True
        self.panel_rect = pygame.Rect(
            LOGICAL_SIZE[0] // 2 - 300,
            LOGICAL_SIZE[1] // 2 - 250,
            600,
            500
        )
        
        self.items = [
            {"label": "自动播放", "key": "auto_mode", "type": "toggle"},
            {"label": "打字机速度", "key": "typing_speed", "type": "slider", "min": 0, "max": 120, "step": 10},
            {"label": "对话框不透明度", "key": "textbox_opacity", "type": "slider", "min": 0, "max": 255, "step": 10},
            {"label": "文字描边", "key": "text_outline", "type": "toggle"},
            {"label": "文字阴影", "key": "text_shadow", "type": "toggle"},
        ]
        
        self.selected_idx = 0
        self.buttons: List[UIButton] = []
        self._init_buttons()

    def _init_buttons(self):
        """初始化底部按钮"""
        btn_width = 120
        btn_height = 40
        x = self.panel_rect.centerx - btn_width // 2
        y = self.panel_rect.bottom - 60
        
        self.back_btn = UIButton(
            pygame.Rect(x, y, btn_width, btn_height),
            "返回",
            self.font,
            self.theme,
            on_click=self.close
        )

    def close(self):
        self.visible = False

    def handle_input(self, event: pygame.event.Event) -> bool:
        """处理输入，返回是否继续显示"""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_idx = (self.selected_idx - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_idx = (self.selected_idx + 1) % len(self.items)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_value(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_value(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._toggle_value()
            elif event.key == pygame.K_ESCAPE:
                self.close()
        
        # 鼠标处理
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了选项
            mx, my = event.pos
            item_h = 50
            start_y = self.panel_rect.top + 80
            
            for i, item in enumerate(self.items):
                rect = pygame.Rect(self.panel_rect.left + 40, start_y + i * item_h, self.panel_rect.width - 80, 40)
                if rect.collidepoint(mx, my):
                    self.selected_idx = i
                    if event.button == 1:
                        if item["type"] == "toggle":
                            self._toggle_value()
                        # 滑块可以通过点击左右区域调整，这里简化处理
        
        if self.back_btn.handle_event(event):
            return False
            
        return self.visible

    def _adjust_value(self, direction: int):
        item = self.items[self.selected_idx]
        key = item["key"]
        
        if item["type"] == "slider":
            if key == "typing_speed":
                val = self.renderer._typing_speed
                val = max(item["min"], min(item["max"], val + direction * item["step"]))
                self.renderer._typing_speed = val
                self.renderer._typing_enabled = val > 0
            elif key == "textbox_opacity":
                val = int(self.ui_config.get("textbox_opacity", 160))
                val = max(item["min"], min(item["max"], val + direction * item["step"]))
                self.ui_config["textbox_opacity"] = val

    def _toggle_value(self):
        item = self.items[self.selected_idx]
        key = item["key"]
        
        if item["type"] == "toggle":
            if key == "auto_mode":
                self.renderer._auto_mode = not self.renderer._auto_mode
            elif key == "text_outline":
                self.ui_config["text_outline"] = not bool(self.ui_config.get("text_outline", False))
            elif key == "text_shadow":
                self.ui_config["text_shadow"] = not bool(self.ui_config.get("text_shadow", True))

    def update(self, dt: float):
        mx, my = pygame.mouse.get_pos()
        # 转换坐标（如果需要）
        # 这里假设全屏坐标
        self.back_btn.update((mx, my), dt)

    def draw(self, surface: pygame.Surface):
        # 绘制半透明遮罩
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        
        # 绘制面板背景
        draw_rounded_rect(
            surface, self.panel_rect, self.theme.neutral_bg[:3],
            radius=self.theme.panel_corner_radius, alpha=self.theme.neutral_bg[3]
        )
        
        # 绘制面板边框发光
        draw_glow_effect(surface, self.panel_rect, self.theme.primary_light, intensity=0.3)
        pygame.draw.rect(surface, self.theme.neutral_border, self.panel_rect, width=2, border_radius=self.theme.panel_corner_radius)
        
        # 标题
        title_surf = self.font.render("系统设置", True, self.theme.text_primary)
        title_rect = title_surf.get_rect(centerx=self.panel_rect.centerx, top=self.panel_rect.top + 30)
        surface.blit(title_surf, title_rect)
        
        # 装饰线
        line_rect = pygame.Rect(self.panel_rect.left + 40, title_rect.bottom + 15, self.panel_rect.width - 80, 2)
        draw_gradient_rect(surface, line_rect, self.theme.accent, self.theme.primary_light, alpha=150)
        
        # 绘制选项
        start_y = self.panel_rect.top + 80
        item_h = 50
        
        for i, item in enumerate(self.items):
            y = start_y + i * item_h
            selected = (i == self.selected_idx)
            
            # 选中背景
            if selected:
                bg_rect = pygame.Rect(self.panel_rect.left + 30, y, self.panel_rect.width - 60, 40)
                draw_rounded_rect(surface, bg_rect, self.theme.primary_light, radius=8, alpha=100)
            
            # 标签
            color = self.theme.accent if selected else self.theme.text_primary
            label_surf = self.font.render(item["label"], True, color)
            surface.blit(label_surf, (self.panel_rect.left + 50, y + 5))
            
            # 值
            val_str = self._get_value_str(item)
            val_surf = self.font.render(val_str, True, self.theme.text_secondary)
            val_rect = val_surf.get_rect(right=self.panel_rect.right - 50, top=y + 5)
            surface.blit(val_surf, val_rect)
            
            # 如果是滑块，绘制简单的进度条
            if item["type"] == "slider":
                bar_w = 150
                bar_h = 4
                bar_rect = pygame.Rect(val_rect.left - bar_w - 20, y + 18, bar_w, bar_h)
                pygame.draw.rect(surface, self.theme.primary_dark, bar_rect, border_radius=2)
                
                # 计算进度
                val = self._get_value_raw(item)
                pct = (val - item["min"]) / (item["max"] - item["min"])
                fill_w = int(bar_w * pct)
                if fill_w > 0:
                    fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_h)
                    pygame.draw.rect(surface, self.theme.accent, fill_rect, border_radius=2)
                    
                # 滑块头
                knob_x = bar_rect.left + fill_w
                pygame.draw.circle(surface, self.theme.text_primary, (knob_x, bar_rect.centery), 6)

        # 绘制返回按钮
        self.back_btn.draw(surface)

    def _get_value_raw(self, item):
        key = item["key"]
        if key == "typing_speed":
            return self.renderer._typing_speed
        elif key == "textbox_opacity":
            return int(self.ui_config.get("textbox_opacity", 160))
        return 0

    def _get_value_str(self, item):
        key = item["key"]
        if key == "auto_mode":
            return "开启" if self.renderer._auto_mode else "关闭"
        elif key == "typing_speed":
            return "瞬显" if not self.renderer._typing_enabled else str(int(self.renderer._typing_speed))
        elif key == "textbox_opacity":
            return str(int(self.ui_config.get("textbox_opacity", 160)))
        elif key == "text_outline":
            return "开启" if bool(self.ui_config.get("text_outline", False)) else "关闭"
        elif key == "text_shadow":
            return "开启" if bool(self.ui_config.get("text_shadow", True)) else "关闭"
        return ""


def open_settings_menu(renderer) -> None:
    """Open the modern settings menu."""
    menu = SettingsMenu(renderer)
    clock = pygame.time.Clock()
    
    while menu.visible:
        dt = clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if not menu.handle_input(event):
                menu.visible = False
        
        # Render base scene
        renderer._render(flip=False, tick=False)
        
        # Update and draw menu
        menu.update(dt)
        menu.draw(renderer.canvas)
        
        # Present
        win_w, win_h = renderer.screen.get_size()
        canvas_w, canvas_h = LOGICAL_SIZE
        scale = min(win_w / canvas_w, win_h / canvas_h)
        dst_w, dst_h = int(canvas_w * scale), int(canvas_h * scale)
        scaled = pygame.transform.smoothscale(renderer.canvas, (dst_w, dst_h))
        x = (win_w - dst_w) // 2
        y = (win_h - dst_h) // 2
        renderer.screen.fill((0, 0, 0))
        renderer.screen.blit(scaled, (x, y))
        pygame.display.flip()
    
    # Save config on exit
    try:
        if isinstance(renderer._config, dict):
            renderer._config["ui"] = menu.ui_config
    except Exception:
        pass
