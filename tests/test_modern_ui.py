"""
Tests for modern UI components.
"""
import pytest
from dataclasses import dataclass
from typing import Optional
import sys


class TestModernUIComponents:
    """测试现代UI组件"""
    
    def test_slots_ui_modern_import(self):
        """测试slots_ui_modern可以导入"""
        from higanvn.engine.slots_ui_modern import show_slots_menu, SlotCard
        assert show_slots_menu is not None
        assert SlotCard is not None
    
    def test_slot_card_creation(self):
        """测试SlotCard创建"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=1, rect=rect)
        
        assert card.slot_id == 1
        assert card.is_empty == True  # property
        assert card.hover_progress == 0.0
        assert card.meta is None
    
    def test_slot_card_with_data(self):
        """测试带数据的SlotCard"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=3, rect=rect)
        card.meta = {
            "timestamp": "2025-01-15 10:30",
            "label": "第一章 开始",
        }
        
        assert card.slot_id == 3
        assert card.is_empty == False  # has meta
        assert card.meta["timestamp"] == "2025-01-15 10:30"
        assert card.meta["label"] == "第一章 开始"
    
    def test_settings_menu_modern_import(self):
        """测试settings_menu_modern可以导入"""
        from higanvn.engine.settings_menu_modern import (
            ControlType, SettingItem, open_settings_menu
        )
        assert ControlType is not None
        assert SettingItem is not None
        assert open_settings_menu is not None
    
    def test_control_type_enum(self):
        """测试控件类型枚举"""
        from higanvn.engine.settings_menu_modern import ControlType
        
        assert ControlType.TOGGLE.value == "toggle"
        assert ControlType.SLIDER.value == "slider"
        assert ControlType.BUTTON.value == "button"
    
    def test_setting_item_toggle(self):
        """测试开关类型设置项"""
        from higanvn.engine.settings_menu_modern import SettingItem, ControlType
        
        item = SettingItem(
            key="auto_mode",
            label="自动播放",
            control_type=ControlType.TOGGLE,
            value=True,
        )
        
        assert item.key == "auto_mode"
        assert item.label == "自动播放"
        assert item.control_type == ControlType.TOGGLE
        assert item.value == True
        assert item.hover_progress == 0.0
        assert item.dragging == False
    
    def test_setting_item_slider(self):
        """测试滑块类型设置项"""
        from higanvn.engine.settings_menu_modern import SettingItem, ControlType
        
        item = SettingItem(
            key="volume",
            label="音量",
            control_type=ControlType.SLIDER,
            value=80.0,
            min_val=0.0,
            max_val=100.0,
            step=5.0,
        )
        
        assert item.key == "volume"
        assert item.value == 80.0
        assert item.min_val == 0.0
        assert item.max_val == 100.0
        assert item.step == 5.0


class TestSettingsMenuLogic:
    """测试设置菜单逻辑"""
    
    def test_adjust_slider_up(self):
        """测试滑块增加"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _adjust_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.SLIDER,
            value=50.0,
            min_val=0.0,
            max_val=100.0,
            step=10.0,
        )
        
        _adjust_value(item, 1)
        assert item.value == 60.0
    
    def test_adjust_slider_down(self):
        """测试滑块减少"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _adjust_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.SLIDER,
            value=50.0,
            min_val=0.0,
            max_val=100.0,
            step=10.0,
        )
        
        _adjust_value(item, -1)
        assert item.value == 40.0
    
    def test_slider_clamp_max(self):
        """测试滑块不超过最大值"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _adjust_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.SLIDER,
            value=95.0,
            min_val=0.0,
            max_val=100.0,
            step=10.0,
        )
        
        _adjust_value(item, 1)
        assert item.value == 100.0
    
    def test_slider_clamp_min(self):
        """测试滑块不低于最小值"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _adjust_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.SLIDER,
            value=5.0,
            min_val=0.0,
            max_val=100.0,
            step=10.0,
        )
        
        _adjust_value(item, -1)
        assert item.value == 0.0
    
    def test_toggle_value(self):
        """测试开关切换"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _toggle_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.TOGGLE,
            value=False,
        )
        
        _toggle_value(item)
        assert item.value == True
        
        _toggle_value(item)
        assert item.value == False
    
    def test_toggle_via_adjust(self):
        """测试通过adjust也能切换开关"""
        from higanvn.engine.settings_menu_modern import (
            SettingItem, ControlType, _adjust_value
        )
        
        item = SettingItem(
            key="test",
            label="Test",
            control_type=ControlType.TOGGLE,
            value=False,
        )
        
        _adjust_value(item, 1)
        assert item.value == True


class TestUIThemeIntegration:
    """测试UI主题集成"""
    
    def test_theme_colors_exist(self):
        """测试主题颜色存在"""
        from higanvn.engine.ui_theme import Theme
        
        assert hasattr(Theme, 'PRIMARY')
        assert hasattr(Theme, 'ACCENT')
        assert hasattr(Theme, 'TEXT_PRIMARY')
        assert hasattr(Theme, 'PANEL_BG')
    
    def test_draw_functions_exist(self):
        """测试绘制函数存在"""
        from higanvn.engine.ui_theme import (
            draw_gradient_rect,
            draw_rounded_panel,
            draw_text_with_glow,
            draw_glow_border,
        )
        
        assert callable(draw_gradient_rect)
        assert callable(draw_rounded_panel)
        assert callable(draw_text_with_glow)
        assert callable(draw_glow_border)


class TestEventsCleanup:
    """测试事件系统清理"""
    
    def test_new_event_system_works(self):
        """测试新事件系统正常工作"""
        from higanvn.engine.events import EventSystem, Event, Priority
        
        es = EventSystem()
        received = []
        
        @dataclass
        class TestEvent(Event):
            message: str
        
        @es.on(TestEvent)
        def handler(event):
            received.append(event.message)
        
        es.emit(TestEvent(message="hello"))
        
        assert len(received) == 1
        assert received[0] == "hello"
    
    def test_legacy_bridge_works(self):
        """测试旧版兼容桥正常工作"""
        from higanvn.engine.events import EventSystem, LegacyEventBridge
        
        es = EventSystem()
        bridge = LegacyEventBridge(es)
        received = []
        
        bridge.subscribe("test.event", lambda data: received.append(data))
        # Use emit instead of publish (method name in LegacyEventBridge)
        bridge.emit("test.event", value=42)
        
        assert len(received) == 1
        assert received[0]["value"] == 42
    
    def test_engine_uses_new_system(self):
        """测试Engine使用新事件系统"""
        from higanvn.engine.engine import Engine
        from higanvn.engine.events import EventSystem, LegacyEventBridge
        
        engine = Engine()
        
        # 新系统可用
        assert hasattr(engine, '_event_system')
        assert isinstance(engine._event_system, EventSystem)
        assert hasattr(engine, 'event_system')
        
        # 旧版兼容桥可用
        assert hasattr(engine, 'events')
        assert isinstance(engine.events, LegacyEventBridge)


class TestModernSlotsCards:
    """测试现代存档槽卡片系统"""
    
    def test_card_hover_state(self):
        """测试卡片悬停状态"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=1, rect=rect)
        assert card.hover_progress == 0.0
        
        # 模拟动画更新
        card.hover_progress = 0.5
        assert card.hover_progress == 0.5
    
    def test_card_update_animation(self):
        """测试卡片动画更新"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=1, rect=rect)
        card.hover = True
        
        # Update a few times
        for _ in range(10):
            card.update(0.016)  # ~60fps
        
        # Progress should increase towards 1.0
        assert card.hover_progress > 0.5
    
    def test_multiple_cards(self):
        """测试多个卡片"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        cards = []
        for i in range(6):
            rect = pygame.Rect(i * 220, 0, 200, 150)
            card = SlotCard(slot_id=i, rect=rect)
            if i <= 3:
                card.meta = {"timestamp": f"2025-01-{i+1}"}
            cards.append(card)
        
        assert len(cards) == 6
        assert cards[0].is_empty == False  # slots 0-3 have meta
        assert cards[4].is_empty == True   # slots 4-5 are empty
