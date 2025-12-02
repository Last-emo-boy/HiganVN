"""
Tests for save/load system and modern slots UI.
"""
import pytest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import json


class TestSaveManager:
    """测试SaveManager"""
    
    def test_save_manager_import(self):
        """测试SaveManager可以导入"""
        from higanvn.engine.save_manager import (
            SaveManager, SlotMeta, create_save_manager, get_save_manager
        )
        assert SaveManager is not None
        assert SlotMeta is not None
    
    def test_slot_meta_empty(self):
        """测试空槽位元数据"""
        from higanvn.engine.save_manager import SlotMeta
        
        meta = SlotMeta(slot_id=1)
        assert meta.is_empty == True
        assert meta.display_time == ""
    
    def test_slot_meta_with_data(self):
        """测试有数据的槽位元数据"""
        from higanvn.engine.save_manager import SlotMeta
        
        meta = SlotMeta(
            slot_id=1,
            timestamp="2025-01-15T10:30:00",
            label="第一章",
        )
        assert meta.is_empty == False
        assert "2025-01-15" in meta.display_time
    
    def test_slot_meta_to_dict(self):
        """测试元数据转字典"""
        from higanvn.engine.save_manager import SlotMeta
        
        meta = SlotMeta(
            slot_id=3,
            timestamp="2025-01-15",
            label="测试",
        )
        d = meta.to_dict()
        
        assert d["slot"] == 3
        assert d["ts"] == "2025-01-15"
        assert d["label"] == "测试"
    
    def test_slot_meta_from_dict(self):
        """测试从字典创建元数据"""
        from higanvn.engine.save_manager import SlotMeta
        
        data = {
            "ts": "2025-01-15",
            "label": "第二章",
            "play_time": 3600,
        }
        meta = SlotMeta.from_dict(data, slot_id=5)
        
        assert meta.slot_id == 5
        assert meta.timestamp == "2025-01-15"
        assert meta.label == "第二章"
        assert meta.play_time == 3600
    
    def test_save_manager_creation(self):
        """测试SaveManager创建"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
                total_slots=6,
            )
            
            assert manager.total_slots == 6
            assert manager.save_dir == Path(tmpdir)
    
    def test_get_empty_slot_meta(self):
        """测试获取空槽位元数据"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            meta = manager.get_slot_meta(1)
            assert meta.is_empty == True
            assert meta.slot_id == 1
    
    def test_get_filled_slots_empty(self):
        """测试获取有数据槽位列表（空）"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            filled = manager.get_filled_slots()
            assert filled == []
    
    def test_get_slot_meta_with_file(self):
        """测试从文件读取槽位元数据"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            slot_path = Path(tmpdir) / "slot_01.json"
            slot_path.write_text(json.dumps({
                "ts": "2025-01-15",
                "label": "测试存档",
            }), encoding="utf-8")
            
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            meta = manager.get_slot_meta(1)
            assert meta.is_empty == False
            assert meta.label == "测试存档"
    
    def test_invalidate_cache(self):
        """测试缓存失效"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            # 第一次读取
            meta1 = manager.get_slot_meta(1)
            assert meta1.is_empty == True
            
            # 创建文件
            slot_path = Path(tmpdir) / "slot_01.json"
            slot_path.write_text(json.dumps({
                "ts": "2025-01-15",
                "label": "新存档",
            }), encoding="utf-8")
            
            # 不失效，仍然读取缓存
            meta2 = manager.get_slot_meta(1)
            assert meta2.is_empty == True  # 还是缓存的空值
            
            # 失效后重新读取
            manager.invalidate_slot(1)
            meta3 = manager.get_slot_meta(1)
            assert meta3.is_empty == False
            assert meta3.label == "新存档"


class TestSaveManagerEvents:
    """测试SaveManager事件"""
    
    def test_save_event_emitted(self):
        """测试保存时发送事件"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem, SaveEvent
        
        es = EventSystem()
        received = []
        
        @es.on(SaveEvent)
        def on_save(event):
            received.append(event)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            # 没有设置 hook，保存会失败，但事件会发送
            manager.save_to_slot(1)
            
            assert len(received) == 1
            assert received[0].slot == 1
    
    def test_save_event_cancellable(self):
        """测试保存事件可取消"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem, SaveEvent, SaveCompleteEvent
        
        es = EventSystem()
        complete_received = []
        
        @es.on(SaveEvent)
        def block_save(event):
            event.cancel()
        
        @es.on(SaveCompleteEvent)
        def on_complete(event):
            complete_received.append(event)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            result = manager.save_to_slot(1)
            
            # 被取消，返回 False
            assert result == False
            # 取消后不发送完成事件
            assert len(complete_received) == 0
    
    def test_delete_slot(self):
        """测试删除槽位"""
        from higanvn.engine.save_manager import SaveManager, SlotDeleteCompleteEvent
        from higanvn.engine.events import EventSystem
        
        es = EventSystem()
        delete_events = []
        
        @es.on(SlotDeleteCompleteEvent)
        def on_delete(event):
            delete_events.append(event)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            slot_path = Path(tmpdir) / "slot_01.json"
            slot_path.write_text('{"ts": "2025"}', encoding="utf-8")
            
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            result = manager.delete_slot(1)
            
            assert result == True
            assert not slot_path.exists()
            assert len(delete_events) == 1
            assert delete_events[0].success == True


class TestSlotsUIModernV2:
    """测试现代槽位UI v2"""
    
    def test_slot_card_import(self):
        """测试SlotCard导入"""
        from higanvn.engine.slots_ui_modern import SlotCard, SlotsMenuState
        assert SlotCard is not None
        assert SlotsMenuState is not None
    
    def test_slot_card_animations(self):
        """测试SlotCard动画"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=1, rect=rect)
        
        # 初始状态
        assert card.hover_progress == 0.0
        assert card.select_progress == 0.0
        assert card.delete_progress == 0.0
        
        # 设置 hover
        card.hover = True
        card.update(0.1)  # 100ms
        assert card.hover_progress > 0.0
        
        # 设置 selected
        card.selected = True
        card.update(0.1)
        assert card.select_progress > 0.0
    
    def test_slots_menu_state_navigation(self):
        """测试菜单状态导航"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard, SlotsMenuState
        
        # 创建4x3网格的卡片
        cards = []
        for i in range(12):
            rect = pygame.Rect((i % 4) * 100, (i // 4) * 100, 90, 90)
            cards.append(SlotCard(i + 1, rect))
        
        state = SlotsMenuState("load", 12, cols=4)
        assert state.selected_idx == 0
        
        # 向右移动
        state.move_selection(1, 0, cards)
        assert state.selected_idx == 1
        
        # 向下移动
        state.move_selection(0, 1, cards)
        assert state.selected_idx == 5  # 1 + 4
        
        # 边界检查 - 不能移动到负数
        state.selected_idx = 0
        state.move_selection(-1, 0, cards)
        assert state.selected_idx == 0  # 不变
    
    def test_slot_card_delete_confirm(self):
        """测试删除确认状态"""
        import pygame
        pygame.init()
        from higanvn.engine.slots_ui_modern import SlotCard
        
        rect = pygame.Rect(0, 0, 200, 150)
        card = SlotCard(slot_id=1, rect=rect)
        card.meta = {"ts": "2025-01-15"}  # 非空
        
        assert card.delete_confirm == False
        assert card.delete_progress == 0.0
        
        card.delete_confirm = True
        card.update(0.2)
        
        assert card.delete_progress > 0.0


class TestSaveLoadIntegration:
    """测试存档读取集成"""
    
    def test_events_import(self):
        """测试相关事件都可以导入"""
        from higanvn.engine.events import (
            SaveEvent, SaveCompleteEvent,
            LoadEvent, LoadCompleteEvent,
        )
        from higanvn.engine.save_manager import (
            SlotDeleteEvent, SlotDeleteCompleteEvent,
            SlotsMenuOpenEvent, SlotsMenuCloseEvent,
            SlotDataChangedEvent,
        )
        
        assert SaveEvent is not None
        assert LoadEvent is not None
        assert SlotDeleteEvent is not None
    
    def test_save_manager_with_hooks(self):
        """测试带钩子的SaveManager"""
        from higanvn.engine.save_manager import SaveManager
        from higanvn.engine.events import EventSystem, SaveCompleteEvent
        
        es = EventSystem()
        complete_events = []
        
        @es.on(SaveCompleteEvent)
        def on_complete(event):
            complete_events.append(event)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SaveManager(
                event_system=es,
                get_save_dir=lambda: Path(tmpdir),
            )
            
            # 设置保存钩子
            saved_slots = []
            def save_hook(slot):
                saved_slots.append(slot)
                # 写入文件
                path = Path(tmpdir) / f"slot_{slot:02d}.json"
                path.write_text(json.dumps({"ts": "2025-01-15", "label": f"Slot {slot}"}))
                return True
            
            manager.set_save_hook(save_hook)
            
            result = manager.save_to_slot(3)
            
            assert result == True
            assert 3 in saved_slots
            assert len(complete_events) == 1
            assert complete_events[0].success == True
