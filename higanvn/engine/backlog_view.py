"""
Backlog View - 现代视觉小说风格文本回看界面
支持语音重放、收藏功能，作为"二级中枢"
"""
from __future__ import annotations

from typing import Tuple, Optional, Callable, List

import pygame
from pygame import Surface

from higanvn.ui.textwrap import wrap_text_generic
from higanvn.engine.ui_components import UITheme, UIButton

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class BacklogEntry:
    """Backlog条目"""
    def __init__(self, name: str, text: str, voice_file: Optional[str] = None):
        self.name = name
        self.text = text
        self.voice_file = voice_file
        self.favorited = False

class ModernBacklogView:
    """现代化Backlog界面，支持语音重放"""
    def __init__(
        self,
        font: pygame.font.Font,
        theme: Optional[UITheme] = None,
        on_voice_replay: Optional[Callable[[str], None]] = None,
        on_favorite_toggle: Optional[Callable[[int], None]] = None,
    ):
        self.font = font
        self.theme = theme or UITheme()
        self.on_voice_replay = on_voice_replay
        self.on_favorite_toggle = on_favorite_toggle

        self.entries: List[BacklogEntry] = []
        self.view_start = 0
        self.selected_index = -1
        self.max_visible_entries = 12

        # UI组件
        self.voice_buttons: List[UIButton] = []
        self.favorite_buttons: List[UIButton] = []

        # 布局参数
        self.margin_x = 60
        self.margin_y = 80
        self.entry_height = 60
        self.button_size = 24

    def set_entries(self, entries: List[BacklogEntry]) -> None:
        """设置Backlog条目"""
        self.entries = entries
        self.view_start = max(0, len(entries) - self.max_visible_entries)

    def update(self, mouse_pos: Optional[Tuple[int, int]], dt: float) -> None:
        """更新界面"""
        self._layout_buttons()
        for button in self.voice_buttons + self.favorite_buttons:
            button.update(mouse_pos, dt)

    def draw(self, canvas: Surface) -> None:
        """绘制Backlog界面"""
        theme = self.theme

        # 半透明遮罩
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((*theme.neutral_bg[:3], 160))
        canvas.blit(overlay, (0, 0))

        # 标题
        title = self.font.render("文本记录", True, theme.text_primary)
        title_rect = title.get_rect(centerx=LOGICAL_SIZE[0] // 2, y=30)
        canvas.blit(title, title_rect)

        # 标题下划线
        pygame.draw.line(
            canvas, theme.neutral_border,
            (self.margin_x, 60), (LOGICAL_SIZE[0] - self.margin_x, 60), 2
        )

        # 绘制条目
        y = self.margin_y
        visible_entries = self.entries[self.view_start:self.view_start + self.max_visible_entries]

        for i, entry in enumerate(visible_entries):
            global_index = self.view_start + i
            is_selected = global_index == self.selected_index

            # 条目背景
            entry_rect = pygame.Rect(
                self.margin_x, y,
                LOGICAL_SIZE[0] - 2 * self.margin_x,
                self.entry_height
            )

            if is_selected:
                # 选中状态背景
                pygame.draw.rect(
                    canvas, (*theme.accent, 100), entry_rect,
                    border_radius=theme.button_corner_radius
                )
                pygame.draw.rect(
                    canvas, theme.accent, entry_rect, width=2,
                    border_radius=theme.button_corner_radius
                )

            # 角色名
            if entry.name:
                name_text = f"{entry.name}:"
                name_surf = self.font.render(name_text, True, theme.accent)
                canvas.blit(name_surf, (entry_rect.x + 10, y + 8))

                # 台词文本
                text_x = entry_rect.x + 10 + name_surf.get_width() + 10
                text_surf = self.font.render(entry.text, True, theme.text_primary)
                canvas.blit(text_surf, (text_x, y + 8))
            else:
                # 无角色名的情况
                text_surf = self.font.render(entry.text, True, theme.text_primary)
                canvas.blit(text_surf, (entry_rect.x + 10, y + 8))

            # 语音重放按钮
            if entry.voice_file and self.voice_buttons:
                voice_button = self.voice_buttons[i]
                voice_button.draw(canvas)

            # 收藏按钮
            if self.favorite_buttons:
                fav_button = self.favorite_buttons[i]
                fav_button.draw(canvas)

            # 分隔线
            if i < len(visible_entries) - 1:
                sep_y = y + self.entry_height + 2
                pygame.draw.line(
                    canvas, (*theme.neutral_border, 100),
                    (self.margin_x, sep_y), (LOGICAL_SIZE[0] - self.margin_x, sep_y), 1
                )

            y += self.entry_height + 8

        # 滚动指示器
        if len(self.entries) > self.max_visible_entries:
            self._draw_scroll_indicator(canvas)

    def _layout_buttons(self) -> None:
        """布局按钮"""
        self.voice_buttons.clear()
        self.favorite_buttons.clear()

        y = self.margin_y
        visible_entries = self.entries[self.view_start:self.view_start + self.max_visible_entries]

        for entry in visible_entries:
            # 语音按钮
            if entry.voice_file:
                button_rect = pygame.Rect(
                    LOGICAL_SIZE[0] - self.margin_x - self.button_size - 10,
                    y + (self.entry_height - self.button_size) // 2,
                    self.button_size, self.button_size
                )
                voice_button = UIButton(button_rect, "🔊", self.font, self.theme)
                self.voice_buttons.append(voice_button)

            # 收藏按钮
            fav_rect = pygame.Rect(
                LOGICAL_SIZE[0] - self.margin_x - self.button_size * 2 - 20,
                y + (self.entry_height - self.button_size) // 2,
                self.button_size, self.button_size
            )
            fav_text = "★" if entry.favorited else "☆"
            fav_button = UIButton(fav_rect, fav_text, self.font, self.theme)
            self.favorite_buttons.append(fav_button)

            y += self.entry_height + 8

    def _draw_scroll_indicator(self, canvas: Surface) -> None:
        """绘制滚动指示器"""
        bar_width = 8
        bar_height = 200
        bar_x = LOGICAL_SIZE[0] - 20
        bar_y = (LOGICAL_SIZE[1] - bar_height) // 2

        # 背景条
        pygame.draw.rect(
            canvas, (*self.theme.neutral_border, 100),
            (bar_x, bar_y, bar_width, bar_height), border_radius=4
        )

        # 滚动位置指示器
        total_entries = len(self.entries)
        visible_ratio = self.max_visible_entries / total_entries
        scroll_ratio = self.view_start / max(1, total_entries - self.max_visible_entries)

        indicator_height = max(20, bar_height * visible_ratio)
        indicator_y = bar_y + (bar_height - indicator_height) * scroll_ratio

        pygame.draw.rect(
            canvas, self.theme.accent,
            (bar_x, indicator_y, bar_width, indicator_height), border_radius=4
        )

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """处理事件"""
        # 处理语音按钮点击
        for i, button in enumerate(self.voice_buttons):
            if button.handle_event(event):
                entry_index = self.view_start + i
                if entry_index < len(self.entries) and self.on_voice_replay:
                    entry = self.entries[entry_index]
                    if entry.voice_file:
                        self.on_voice_replay(entry.voice_file)
                return "voice_replay"

        # 处理收藏按钮点击
        for i, button in enumerate(self.favorite_buttons):
            if button.handle_event(event):
                entry_index = self.view_start + i
                if entry_index < len(self.entries):
                    entry = self.entries[entry_index]
                    entry.favorited = not entry.favorited
                    if self.on_favorite_toggle:
                        self.on_favorite_toggle(entry_index)
                return "favorite_toggle"

        # 鼠标滚轮滚动
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:  # 向上滚动
                self.view_start = max(0, self.view_start - 1)
            elif event.y < 0:  # 向下滚动
                max_start = max(0, len(self.entries) - self.max_visible_entries)
                self.view_start = min(max_start, self.view_start + 1)
            return "scroll"

        # 键盘导航
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.view_start = max(0, self.view_start - 1)
                return "navigate"
            elif event.key == pygame.K_DOWN:
                max_start = max(0, len(self.entries) - self.max_visible_entries)
                self.view_start = min(max_start, self.view_start + 1)
                return "navigate"
            elif event.key == pygame.K_PAGEUP:
                self.view_start = max(0, self.view_start - self.max_visible_entries)
                return "navigate"
            elif event.key == pygame.K_PAGEDOWN:
                max_start = max(0, len(self.entries) - self.max_visible_entries)
                self.view_start = min(max_start, self.view_start + self.max_visible_entries)
                return "navigate"

        return None

    def scroll_to_entry(self, index: int) -> None:
        """滚动到指定条目"""
        if 0 <= index < len(self.entries):
            self.view_start = max(0, min(index, len(self.entries) - self.max_visible_entries))


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    def measure(s: str) -> int:
        try:
            return font.size(s)[0]
        except Exception:
            return 0
    return wrap_text_generic(text or "", measure, int(max_width))


def draw_backlog(
    canvas: Surface,
    font: pygame.font.Font,
    history: list,
    view_idx: int,
) -> None:
    """兼容性函数 - 绘制Backlog（已废弃，请使用ModernBacklogView）"""
    # 转换历史记录为BacklogEntry
    entries = []
    for line in history:
        entry = BacklogEntry(
            name=line.name or "",
            text=line.text,
            voice_file=getattr(line, 'voice_file', None)
        )
        entries.append(entry)

    # 创建现代Backlog视图
    backlog_view = ModernBacklogView(font)
    backlog_view.set_entries(entries)
    backlog_view.selected_index = view_idx if view_idx >= 0 else len(entries) - 1
    backlog_view.update(None, 0)
    backlog_view.draw(canvas)
