"""
Save/Load Manager - 统一的存档管理系统

整合了：
- 事件系统（SaveEvent/LoadEvent/DeleteEvent）
- 现代UI界面
- 缓存管理
- 缩略图处理
- 槽位状态管理
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any, TYPE_CHECKING
from datetime import datetime
import json
import logging
import threading
import hashlib

if TYPE_CHECKING:
    import pygame

from .events import (
    EventSystem, Event, CancellableEvent, Priority,
    SaveEvent, SaveCompleteEvent, LoadEvent, LoadCompleteEvent
)

logger = logging.getLogger(__name__)


# ============================================================================
# Additional Events for Save/Load System
# ============================================================================

@dataclass
class SlotDeleteEvent(CancellableEvent):
    """Fired before a slot is deleted."""
    slot: int = 0


@dataclass
class SlotDeleteCompleteEvent(Event):
    """Fired after a slot deletion attempt."""
    slot: int = 0
    success: bool = False


@dataclass
class SlotsMenuOpenEvent(Event):
    """Fired when slots menu is opened."""
    mode: str = "load"  # "save" or "load"


@dataclass
class SlotsMenuCloseEvent(Event):
    """Fired when slots menu is closed."""
    mode: str = "load"
    selected_slot: Optional[int] = None


@dataclass
class SlotDataChangedEvent(Event):
    """Fired when slot data changes (save/delete)."""
    slot: int = 0
    action: str = ""  # "save", "delete", "update"


# ============================================================================
# Slot Metadata
# ============================================================================

@dataclass
class SlotMeta:
    """存档槽位元数据"""
    slot_id: int
    timestamp: Optional[str] = None
    label: Optional[str] = None
    play_time: Optional[int] = None  # seconds
    chapter: Optional[str] = None
    script_hash: Optional[str] = None
    version: int = 1
    
    @property
    def is_empty(self) -> bool:
        return self.timestamp is None
    
    @property
    def display_time(self) -> str:
        if not self.timestamp:
            return ""
        try:
            dt = datetime.fromisoformat(self.timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(self.timestamp)[:16]
    
    def to_dict(self) -> dict:
        return {
            "slot": self.slot_id,
            "ts": self.timestamp,
            "label": self.label,
            "play_time": self.play_time,
            "chapter": self.chapter,
            "script_hash": self.script_hash,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: dict, slot_id: int) -> "SlotMeta":
        return cls(
            slot_id=slot_id,
            timestamp=data.get("ts"),
            label=data.get("label"),
            play_time=data.get("play_time"),
            chapter=data.get("chapter"),
            script_hash=data.get("script_hash"),
            version=data.get("version", 1),
        )


# ============================================================================
# Save Manager
# ============================================================================

class SaveManager:
    """
    统一的存档管理器
    
    负责:
    - 槽位元数据缓存和刷新
    - 事件触发和处理
    - 缩略图管理
    - 与Engine和Renderer的协调
    """
    
    def __init__(
        self,
        event_system: EventSystem,
        get_save_dir: Callable[[], Path],
        total_slots: int = 12,
    ):
        self._events = event_system
        self._get_save_dir = get_save_dir
        self._total_slots = total_slots
        
        # 缓存
        self._meta_cache: Dict[int, SlotMeta] = {}
        self._thumb_cache: Dict[int, Any] = {}  # pygame.Surface
        self._cache_valid = False
        self._cache_lock = threading.Lock()
        
        # 回调钩子
        self._save_hook: Optional[Callable[[int], bool]] = None
        self._load_hook: Optional[Callable[[int], bool]] = None
        self._delete_hook: Optional[Callable[[int], bool]] = None
        
        # 注册事件处理
        self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """注册内部事件处理器"""
        @self._events.on(SaveCompleteEvent, priority=Priority.LOW)
        def on_save_complete(event: SaveCompleteEvent):
            if event.success:
                self.invalidate_slot(event.slot)
                self._events.emit(SlotDataChangedEvent(slot=event.slot, action="save"))
        
        @self._events.on(LoadCompleteEvent, priority=Priority.LOW)
        def on_load_complete(event: LoadCompleteEvent):
            pass  # 读取不改变槽位数据
        
        @self._events.on(SlotDeleteCompleteEvent, priority=Priority.LOW)
        def on_delete_complete(event: SlotDeleteCompleteEvent):
            if event.success:
                self.invalidate_slot(event.slot)
                self._events.emit(SlotDataChangedEvent(slot=event.slot, action="delete"))
    
    @property
    def save_dir(self) -> Path:
        return self._get_save_dir()
    
    @property
    def total_slots(self) -> int:
        return self._total_slots
    
    # =========================================
    # Hooks
    # =========================================
    
    def set_save_hook(self, fn: Callable[[int], bool]) -> None:
        """设置保存回调"""
        self._save_hook = fn
    
    def set_load_hook(self, fn: Callable[[int], bool]) -> None:
        """设置读取回调"""
        self._load_hook = fn
    
    def set_delete_hook(self, fn: Callable[[int], bool]) -> None:
        """设置删除回调"""
        self._delete_hook = fn
    
    # =========================================
    # Slot Operations
    # =========================================
    
    def save_to_slot(self, slot: int) -> bool:
        """
        保存到指定槽位
        
        触发事件链:
        1. SaveEvent (可取消)
        2. 执行保存
        3. SaveCompleteEvent
        4. SlotDataChangedEvent
        """
        # 发送可取消事件
        save_event = SaveEvent(slot=slot, is_quicksave=False)
        self._events.emit(save_event)
        
        if save_event.cancelled:
            logger.debug(f"Save to slot {slot} cancelled by event handler")
            return False
        
        success = False
        try:
            if self._save_hook:
                success = self._save_hook(slot)
        except Exception as e:
            logger.error(f"Save hook failed: {e}")
            success = False
        
        # 发送完成事件
        self._events.emit(SaveCompleteEvent(slot=slot, success=success))
        
        return success
    
    def load_from_slot(self, slot: int) -> bool:
        """
        从指定槽位读取
        
        触发事件链:
        1. LoadEvent (可取消)
        2. 执行读取
        3. LoadCompleteEvent
        """
        # 检查槽位是否有数据
        meta = self.get_slot_meta(slot)
        if meta.is_empty:
            logger.warning(f"Cannot load from empty slot {slot}")
            return False
        
        # 发送可取消事件
        load_event = LoadEvent(slot=slot, is_quickload=False)
        self._events.emit(load_event)
        
        if load_event.cancelled:
            logger.debug(f"Load from slot {slot} cancelled by event handler")
            return False
        
        success = False
        try:
            if self._load_hook:
                success = self._load_hook(slot)
        except Exception as e:
            logger.error(f"Load hook failed: {e}")
            success = False
        
        # 发送完成事件
        self._events.emit(LoadCompleteEvent(slot=slot, success=success))
        
        return success
    
    def delete_slot(self, slot: int) -> bool:
        """
        删除指定槽位
        
        触发事件链:
        1. SlotDeleteEvent (可取消)
        2. 删除文件
        3. SlotDeleteCompleteEvent
        4. SlotDataChangedEvent
        """
        # 发送可取消事件
        delete_event = SlotDeleteEvent(slot=slot)
        self._events.emit(delete_event)
        
        if delete_event.cancelled:
            logger.debug(f"Delete slot {slot} cancelled by event handler")
            return False
        
        success = False
        try:
            if self._delete_hook:
                success = self._delete_hook(slot)
            else:
                # 默认删除逻辑
                success = self._default_delete(slot)
        except Exception as e:
            logger.error(f"Delete hook failed: {e}")
            success = False
        
        # 发送完成事件
        self._events.emit(SlotDeleteCompleteEvent(slot=slot, success=success))
        
        return success
    
    def _default_delete(self, slot: int) -> bool:
        """默认删除实现"""
        try:
            meta_path = self.save_dir / f"slot_{slot:02d}.json"
            thumb_path = self.save_dir / f"slot_{slot:02d}.png"
            
            deleted = False
            if meta_path.exists():
                meta_path.unlink()
                deleted = True
            if thumb_path.exists():
                thumb_path.unlink()
                deleted = True
            
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete slot {slot}: {e}")
            return False
    
    # =========================================
    # Metadata & Cache
    # =========================================
    
    def get_slot_meta(self, slot: int) -> SlotMeta:
        """获取槽位元数据（带缓存）"""
        with self._cache_lock:
            if slot in self._meta_cache:
                return self._meta_cache[slot]
        
        # 从文件读取
        meta = self._read_meta_from_disk(slot)
        
        with self._cache_lock:
            self._meta_cache[slot] = meta
        
        return meta
    
    def get_all_metas(self) -> Dict[int, SlotMeta]:
        """获取所有槽位元数据"""
        result = {}
        for i in range(1, self._total_slots + 1):
            result[i] = self.get_slot_meta(i)
        return result
    
    def get_filled_slots(self) -> List[int]:
        """获取有数据的槽位列表"""
        filled = []
        for i in range(1, self._total_slots + 1):
            if not self.get_slot_meta(i).is_empty:
                filled.append(i)
        return filled
    
    def invalidate_slot(self, slot: int) -> None:
        """使单个槽位缓存失效"""
        with self._cache_lock:
            self._meta_cache.pop(slot, None)
            self._thumb_cache.pop(slot, None)
    
    def invalidate_all(self) -> None:
        """使所有缓存失效"""
        with self._cache_lock:
            self._meta_cache.clear()
            self._thumb_cache.clear()
            self._cache_valid = False
    
    def refresh_cache(self) -> None:
        """刷新所有槽位缓存"""
        self.invalidate_all()
        for i in range(1, self._total_slots + 1):
            self.get_slot_meta(i)
        self._cache_valid = True
    
    def _read_meta_from_disk(self, slot: int) -> SlotMeta:
        """从磁盘读取元数据"""
        try:
            meta_path = self.save_dir / f"slot_{slot:02d}.json"
            if not meta_path.exists():
                return SlotMeta(slot_id=slot)
            
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return SlotMeta.from_dict(data, slot)
        except Exception as e:
            logger.warning(f"Failed to read meta for slot {slot}: {e}")
            return SlotMeta(slot_id=slot)
    
    # =========================================
    # Thumbnails
    # =========================================
    
    def get_thumbnail_path(self, slot: int) -> Path:
        """获取缩略图路径"""
        return self.save_dir / f"slot_{slot:02d}.png"
    
    def get_thumbnail(self, slot: int) -> Optional[Any]:
        """获取缩略图 Surface（带缓存）"""
        with self._cache_lock:
            if slot in self._thumb_cache:
                return self._thumb_cache[slot]
        
        thumb = self._load_thumbnail(slot)
        
        with self._cache_lock:
            self._thumb_cache[slot] = thumb
        
        return thumb
    
    def _load_thumbnail(self, slot: int) -> Optional[Any]:
        """从磁盘加载缩略图"""
        try:
            import pygame
            path = self.get_thumbnail_path(slot)
            if path.exists():
                return pygame.image.load(str(path)).convert()
        except Exception as e:
            logger.warning(f"Failed to load thumbnail for slot {slot}: {e}")
        return None
    
    def capture_thumbnail(self, slot: int, surface: Any, size: tuple = (240, 135)) -> bool:
        """
        从 Surface 捕获缩略图并保存
        
        Args:
            slot: 槽位号
            surface: pygame.Surface 源
            size: 缩略图尺寸
        """
        try:
            import pygame
            
            # 确保目录存在
            self.save_dir.mkdir(parents=True, exist_ok=True)
            
            # 缩放
            thumb = pygame.transform.smoothscale(surface, size)
            
            # 保存
            path = self.get_thumbnail_path(slot)
            pygame.image.save(thumb, str(path))
            
            # 更新缓存
            with self._cache_lock:
                self._thumb_cache[slot] = thumb
            
            return True
        except Exception as e:
            logger.error(f"Failed to capture thumbnail for slot {slot}: {e}")
            return False
    
    # =========================================
    # Quick Save/Load
    # =========================================
    
    def quicksave(self) -> bool:
        """快速保存（使用槽位0）"""
        event = SaveEvent(slot=0, is_quicksave=True)
        self._events.emit(event)
        
        if event.cancelled:
            return False
        
        success = False
        if self._save_hook:
            try:
                # Quick save uses special handling
                success = self._save_hook(0)
            except Exception:
                pass
        
        self._events.emit(SaveCompleteEvent(slot=0, success=success))
        return success
    
    def quickload(self) -> bool:
        """快速读取（使用槽位0）"""
        event = LoadEvent(slot=0, is_quickload=True)
        self._events.emit(event)
        
        if event.cancelled:
            return False
        
        success = False
        if self._load_hook:
            try:
                success = self._load_hook(0)
            except Exception:
                pass
        
        self._events.emit(LoadCompleteEvent(slot=0, success=success))
        return success


# ============================================================================
# Factory Function
# ============================================================================

_manager_instance: Optional[SaveManager] = None


def get_save_manager() -> Optional[SaveManager]:
    """获取全局 SaveManager 实例"""
    return _manager_instance


def create_save_manager(
    event_system: EventSystem,
    get_save_dir: Callable[[], Path],
    total_slots: int = 12,
) -> SaveManager:
    """创建并设置全局 SaveManager"""
    global _manager_instance
    _manager_instance = SaveManager(event_system, get_save_dir, total_slots)
    return _manager_instance
