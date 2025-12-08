"""
Tests for modern UI components.
"""
import pytest
from unittest.mock import Mock
import pygame

from higanvn.engine.ui_components import (
    UITheme, UIButton, UIMenuBar, UIQuickMenu, UIStatusIndicator,
    create_bottom_menu_bar, create_quick_menu
)


class TestModernUIComponents:
    """测试现代UI组件"""

    def test_ui_theme_creation(self):
        """测试UI主题创建"""
        theme = UITheme()
        assert theme.primary == (100, 140, 220)
        assert theme.accent == (255, 200, 100)
        assert theme.neutral_bg == (15, 20, 35, 220)

    @pytest.fixture
    def pygame_init(self):
        """初始化Pygame"""
        pygame.init()
        yield
        pygame.quit()

    def test_ui_button_creation(self, pygame_init):
        """测试UI按钮创建"""
        font = pygame.font.SysFont("arial", 24)
        theme = UITheme()
        rect = pygame.Rect(0, 0, 100, 40)
        button = UIButton(rect, "测试", font, theme)

        assert button.text == "测试"
        assert button.rect == rect
        assert not button.hovered
        assert not button.pressed

    def test_ui_button_update_hover(self, pygame_init):
        """测试按钮悬停状态"""
        font = pygame.font.SysFont("arial", 24)
        theme = UITheme()
        rect = pygame.Rect(0, 0, 100, 40)
        button = UIButton(rect, "测试", font, theme)

        # 鼠标在按钮内
        mouse_pos = (50, 20)
        button.update(mouse_pos, 0.016)
        assert button.hovered

        # 鼠标在按钮外
        mouse_pos = (200, 200)
        button.update(mouse_pos, 0.016)
        assert not button.hovered

    def test_ui_menu_bar_creation(self, pygame_init):
        """测试菜单栏创建"""
        font = pygame.font.SysFont("arial", 20)
        theme = UITheme()
        items = [
            {"text": "自动", "on_click": Mock()},
            {"text": "快进", "on_click": Mock()},
        ]
        menu_bar = UIMenuBar(font, theme, items)

        assert len(menu_bar.buttons) == 2
        assert menu_bar.buttons[0].text == "自动"
        assert menu_bar.buttons[1].text == "快进"

    def test_ui_quick_menu_creation(self, pygame_init):
        """测试快捷菜单创建"""
        font = pygame.font.SysFont("arial", 20)
        theme = UITheme()
        quick_menu = UIQuickMenu(font, theme)

        assert len(quick_menu.items) == 6  # 默认6个项目
        assert quick_menu.items[0]["text"] == "自动"
        assert quick_menu.items[0]["key"] == "A"

    def test_ui_quick_menu_show_hide(self, pygame_init):
        """测试快捷菜单显示隐藏"""
        font = pygame.font.SysFont("arial", 20)
        theme = UITheme()
        quick_menu = UIQuickMenu(font, theme)

        assert not quick_menu.visible

        quick_menu.show_at((100, 100))
        assert quick_menu.visible
        assert quick_menu.position == (100, 100)

        quick_menu.hide()
        assert not quick_menu.visible

    def test_ui_status_indicator(self, pygame_init):
        """测试状态指示器"""
        font = pygame.font.SysFont("arial", 20)
        theme = UITheme()
        indicator = UIStatusIndicator(font, theme)

        assert not indicator.auto_mode
        assert not indicator.skip_mode
        assert not indicator.voice_playing

        indicator.set_auto_mode(True)
        assert indicator.auto_mode

        indicator.set_skip_mode(True)
        assert indicator.skip_mode

        indicator.set_voice_playing(True)
        assert indicator.voice_playing

    def test_create_bottom_menu_bar(self, pygame_init):
        """测试底部菜单栏创建函数"""
        font = pygame.font.SysFont("arial", 20)
        actions = {
            "auto": Mock(),
            "skip": Mock(),
            "backlog": Mock(),
        }
        menu_bar = create_bottom_menu_bar(font, actions=actions)

        assert isinstance(menu_bar, UIMenuBar)
        assert len(menu_bar.buttons) == 6  # 自动、快进、记录、保存、读取、设置

    def test_create_quick_menu(self, pygame_init):
        """测试快捷菜单创建函数"""
        font = pygame.font.SysFont("arial", 20)
        actions = {
            "auto": Mock(),
            "skip": Mock(),
        }
        quick_menu = create_quick_menu(font, actions=actions)

        assert isinstance(quick_menu, UIQuickMenu)
        assert len(quick_menu.items) == 6

    def test_ui_button_event_handling(self, pygame_init):
        """测试按钮事件处理"""
        font = pygame.font.SysFont("arial", 24)
        theme = UITheme()
        rect = pygame.Rect(0, 0, 100, 40)
        on_click = Mock()
        button = UIButton(rect, "测试", font, theme, on_click)

        # 鼠标按下事件
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 20))
        result = button.handle_event(event)
        assert result  # 应该返回True表示点击开始
        assert button.pressed

        # 鼠标释放事件
        event = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 20))
        result = button.handle_event(event)
        assert result  # 应该返回True表示点击完成
        assert not button.pressed
        on_click.assert_called_once()

    def test_ui_quick_menu_event_handling(self, pygame_init):
        """测试快捷菜单事件处理"""
        font = pygame.font.SysFont("arial", 20)
        theme = UITheme()
        quick_menu = UIQuickMenu(font, theme)

        # 模拟右键显示菜单
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(200, 200))
        result = quick_menu.handle_event(event)
        assert result == "quick_menu_shown"

        # 菜单已显示，点击外部应该隐藏
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
        result = quick_menu.handle_event(event)
        assert result is None
        assert not quick_menu.visible