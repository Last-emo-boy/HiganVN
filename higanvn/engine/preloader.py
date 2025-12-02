"""
Asset Preloader - 资源预加载系统

Features:
- 异步资源加载 (使用线程池)
- 预加载队列管理
- 加载进度追踪
- 智能预测预加载
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Callable, Any
from pathlib import Path
from queue import Queue, Empty
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """资源类型"""
    BACKGROUND = "bg"
    CHARACTER = "ch"
    CG = "cg"
    BGM = "bgm"
    SE = "se"
    VOICE = "voice"


@dataclass
class AssetRequest:
    """资源请求"""
    asset_type: AssetType
    path: str
    priority: int = 0  # 更高的优先级先加载
    callback: Optional[Callable[[Any], None]] = None


@dataclass
class LoadProgress:
    """加载进度"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    
    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100.0
    
    @property
    def is_complete(self) -> bool:
        return self.completed + self.failed >= self.total


class AssetPreloader:
    """
    资源预加载器。
    
    使用线程池异步加载资源，支持优先级队列。
    
    Usage:
        preloader = AssetPreloader(max_workers=4)
        
        # 添加预加载任务
        preloader.preload(AssetType.BACKGROUND, "bg/school_day.jpg")
        preloader.preload(AssetType.CHARACTER, "ch/alice/normal.png")
        
        # 批量预加载
        preloader.preload_batch([
            (AssetType.BGM, "bgm/theme.ogg"),
            (AssetType.SE, "se/door.wav"),
        ])
        
        # 检查进度
        progress = preloader.get_progress()
        print(f"Loading: {progress.percent:.1f}%")
        
        # 等待全部完成
        preloader.wait_all(timeout=10.0)
        
        # 关闭
        preloader.shutdown()
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        image_loader: Optional[Callable[[str], Any]] = None,
        audio_loader: Optional[Callable[[str], Any]] = None,
    ):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        
        # 任务追踪
        self._pending: Dict[str, Future] = {}
        self._completed: Set[str] = set()
        self._failed: Set[str] = set()
        
        # 资源缓存引用
        self._loaded_assets: Dict[str, Any] = {}
        
        # 加载器
        self._image_loader = image_loader
        self._audio_loader = audio_loader
        
        # 统计
        self._total_requested = 0
        self._load_times: Dict[str, float] = {}
        
        # 是否已关闭
        self._shutdown = False
    
    def preload(
        self,
        asset_type: AssetType,
        path: str,
        priority: int = 0,
        callback: Optional[Callable[[Any], None]] = None,
    ) -> bool:
        """
        预加载单个资源。
        
        Returns:
            True 如果成功添加到队列，False 如果已存在或已关闭
        """
        if self._shutdown:
            return False
        
        key = f"{asset_type.value}:{path}"
        
        with self._lock:
            # 检查是否已经加载或正在加载
            if key in self._completed or key in self._pending:
                return False
            
            self._total_requested += 1
            
            # 提交加载任务
            future = self._executor.submit(
                self._load_asset, asset_type, path, key
            )
            
            if callback:
                future.add_done_callback(
                    lambda f: self._invoke_callback(callback, f)
                )
            
            self._pending[key] = future
            
        return True
    
    def preload_batch(
        self,
        assets: List[tuple],  # [(AssetType, path), ...]
        priority: int = 0,
    ) -> int:
        """
        批量预加载资源。
        
        Returns:
            成功添加到队列的数量
        """
        count = 0
        for item in assets:
            if len(item) == 2:
                asset_type, path = item
                if self.preload(asset_type, path, priority):
                    count += 1
            elif len(item) == 3:
                asset_type, path, callback = item
                if self.preload(asset_type, path, priority, callback):
                    count += 1
        return count
    
    def _load_asset(self, asset_type: AssetType, path: str, key: str) -> Any:
        """加载单个资源 (在工作线程中运行)"""
        start_time = time.time()
        result = None
        
        try:
            if asset_type in (AssetType.BACKGROUND, AssetType.CHARACTER, AssetType.CG):
                if self._image_loader:
                    result = self._image_loader(path)
                else:
                    # 默认图片加载
                    result = self._default_image_load(path)
            
            elif asset_type in (AssetType.BGM, AssetType.SE, AssetType.VOICE):
                if self._audio_loader:
                    result = self._audio_loader(path)
                else:
                    # 默认音频加载
                    result = self._default_audio_load(path)
            
            with self._lock:
                self._pending.pop(key, None)
                self._completed.add(key)
                if result is not None:
                    self._loaded_assets[key] = result
                self._load_times[key] = time.time() - start_time
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to preload {key}: {e}")
            with self._lock:
                self._pending.pop(key, None)
                self._failed.add(key)
            raise
    
    def _default_image_load(self, path: str) -> Any:
        """默认图片加载器"""
        try:
            import pygame
            full_path = Path(path)
            if full_path.exists():
                return pygame.image.load(str(full_path)).convert_alpha()
        except Exception:
            pass
        return None
    
    def _default_audio_load(self, path: str) -> Any:
        """默认音频加载器 (只验证存在)"""
        try:
            full_path = Path(path)
            return full_path.exists()
        except Exception:
            pass
        return None
    
    def _invoke_callback(self, callback: Callable, future: Future) -> None:
        """调用回调函数"""
        try:
            result = future.result()
            callback(result)
        except Exception as e:
            logger.warning(f"Preload callback error: {e}")
    
    def get_asset(self, asset_type: AssetType, path: str) -> Optional[Any]:
        """获取已加载的资源"""
        key = f"{asset_type.value}:{path}"
        with self._lock:
            return self._loaded_assets.get(key)
    
    def is_loaded(self, asset_type: AssetType, path: str) -> bool:
        """检查资源是否已加载"""
        key = f"{asset_type.value}:{path}"
        with self._lock:
            return key in self._completed
    
    def is_pending(self, asset_type: AssetType, path: str) -> bool:
        """检查资源是否正在加载"""
        key = f"{asset_type.value}:{path}"
        with self._lock:
            return key in self._pending
    
    def get_progress(self) -> LoadProgress:
        """获取加载进度"""
        with self._lock:
            return LoadProgress(
                total=self._total_requested,
                completed=len(self._completed),
                failed=len(self._failed),
                in_progress=len(self._pending),
            )
    
    def wait_all(self, timeout: Optional[float] = None) -> bool:
        """
        等待所有加载完成。
        
        Args:
            timeout: 超时时间(秒)，None表示无限等待
        
        Returns:
            True 如果全部完成，False 如果超时
        """
        start = time.time()
        
        while True:
            with self._lock:
                pending = list(self._pending.values())
            
            if not pending:
                return True
            
            if timeout is not None:
                remaining = timeout - (time.time() - start)
                if remaining <= 0:
                    return False
                
                # 等待第一个完成的任务
                try:
                    from concurrent.futures import wait, FIRST_COMPLETED
                    wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                except Exception:
                    pass
            else:
                time.sleep(0.1)
    
    def cancel_pending(self) -> int:
        """取消所有待处理的任务"""
        count = 0
        with self._lock:
            for future in self._pending.values():
                if future.cancel():
                    count += 1
            self._pending.clear()
        return count
    
    def clear_cache(self) -> None:
        """清空缓存"""
        with self._lock:
            self._loaded_assets.clear()
            self._completed.clear()
            self._failed.clear()
            self._load_times.clear()
            self._total_requested = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            avg_time = 0.0
            if self._load_times:
                avg_time = sum(self._load_times.values()) / len(self._load_times)
            
            return {
                "total_requested": self._total_requested,
                "completed": len(self._completed),
                "failed": len(self._failed),
                "pending": len(self._pending),
                "cached": len(self._loaded_assets),
                "avg_load_time_ms": avg_time * 1000,
            }
    
    def shutdown(self, wait: bool = True) -> None:
        """关闭预加载器"""
        self._shutdown = True
        self._executor.shutdown(wait=wait)


# ============================================================================
# 智能预加载分析器
# ============================================================================

class ScenePredictor:
    """
    场景预测器 - 分析脚本预测下一步需要的资源。
    """
    
    def __init__(self):
        # 缓存已分析的标签->资源映射
        self._label_assets: Dict[str, List[tuple]] = {}
    
    def analyze_script(self, program, current_ip: int, look_ahead: int = 20) -> List[tuple]:
        """
        分析脚本，预测接下来需要的资源。
        
        Args:
            program: 脚本程序对象
            current_ip: 当前指令指针
            look_ahead: 向前查看的指令数
        
        Returns:
            [(AssetType, path), ...] 列表
        """
        if not program or not hasattr(program, 'ops'):
            return []
        
        assets = []
        
        for i in range(current_ip, min(current_ip + look_ahead, len(program.ops))):
            op = program.ops[i]
            
            if op.kind == "command":
                name = (op.payload.get("name") or "").upper()
                args = op.payload.get("args") or ""
                
                if name in ("BG", "BACKGROUND"):
                    # 背景
                    bg_path = args.split()[0] if args else ""
                    if bg_path:
                        assets.append((AssetType.BACKGROUND, f"bg/{bg_path}"))
                
                elif name == "CG":
                    # CG
                    cg_path = args.split()[0] if args else ""
                    if cg_path:
                        assets.append((AssetType.CG, f"cg/{cg_path}"))
                
                elif name in ("BGM", "MUSIC"):
                    # 背景音乐
                    bgm_path = args.split()[0] if args else ""
                    if bgm_path:
                        assets.append((AssetType.BGM, f"bgm/{bgm_path}"))
                
                elif name in ("SE", "SOUND"):
                    # 音效
                    se_path = args.split()[0] if args else ""
                    if se_path:
                        assets.append((AssetType.SE, f"se/{se_path}"))
                
                elif name in ("SHOW", "CHAR", "CHARACTER"):
                    # 角色立绘
                    parts = args.split()
                    if parts:
                        char_name = parts[0]
                        # 简化路径，实际应该根据角色配置解析
                        assets.append((AssetType.CHARACTER, f"ch/{char_name}"))
            
            elif op.kind == "dialogue":
                # 检查语音
                actor = op.payload.get("actor")
                if actor:
                    # 假设有语音文件
                    # 实际实现需要根据命名规则生成路径
                    pass
            
            elif op.kind == "choice":
                # 选择支可能导致分支，停止预加载
                break
        
        return assets
    
    def get_label_assets(self, program, label: str) -> List[tuple]:
        """获取指定标签开始的资源列表"""
        if label in self._label_assets:
            return self._label_assets[label]
        
        if not program or not hasattr(program, 'labels'):
            return []
        
        ip = program.labels.get(label)
        if ip is None:
            return []
        
        assets = self.analyze_script(program, ip, look_ahead=50)
        self._label_assets[label] = assets
        return assets


# ============================================================================
# 全局预加载器实例
# ============================================================================

_global_preloader: Optional[AssetPreloader] = None


def get_preloader() -> AssetPreloader:
    """获取全局预加载器实例"""
    global _global_preloader
    if _global_preloader is None:
        _global_preloader = AssetPreloader(max_workers=2)
    return _global_preloader


def shutdown_preloader() -> None:
    """关闭全局预加载器"""
    global _global_preloader
    if _global_preloader:
        _global_preloader.shutdown()
        _global_preloader = None
