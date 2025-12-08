"""
Layered Character Renderer - 差分立绘渲染器

将差分立绘系统 (layered_sprite) 集成到渲染器中：
- 支持差分立绘实时合成
- 图层缓存优化
- 兼容旧的简单立绘模式
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Callable, Any
from collections import OrderedDict

try:
    import pygame
    from pygame import Surface
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    Surface = Any

from higanvn.packaging.layered_sprite import (
    CharacterSpriteManifest,
    SpriteState,
    SpriteCompositor,
    LayerDefinition,
    scan_characters_directory,
)


# ============================================================================
# 合成缓存
# ============================================================================

@dataclass
class CompositeEntry:
    """合成图像缓存条目"""
    surface: Surface
    cache_key: str
    width: int
    height: int
    bytes_estimate: int
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    access_count: int = 0


class CompositeCache:
    """
    合成图像缓存
    
    缓存已合成的立绘，避免重复合成
    """
    
    def __init__(self, max_entries: int = 50, max_bytes: int = 256 * 1024 * 1024):
        self._cache: OrderedDict[str, CompositeEntry] = OrderedDict()
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._current_bytes = 0
        
        # 统计
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, cache_key: str) -> Optional[Surface]:
        """获取缓存的合成图像"""
        entry = self._cache.get(cache_key)
        if entry:
            entry.last_access = time.time()
            entry.access_count += 1
            # 移动到末尾（最近使用）
            self._cache.move_to_end(cache_key)
            self.hits += 1
            return entry.surface
        self.misses += 1
        return None
    
    def put(self, cache_key: str, surface: Surface) -> None:
        """缓存合成图像"""
        if not HAS_PYGAME:
            return
        
        # 估算内存
        try:
            w, h = surface.get_size()
            bpp = surface.get_bytesize()
            bytes_estimate = w * h * bpp
        except Exception:
            bytes_estimate = 1024 * 1024  # 默认 1MB
        
        # 检查是否需要腾出空间
        while (len(self._cache) >= self._max_entries or 
               self._current_bytes + bytes_estimate > self._max_bytes):
            if not self._cache:
                break
            self._evict_oldest()
        
        # 添加新条目
        entry = CompositeEntry(
            surface=surface,
            cache_key=cache_key,
            width=surface.get_width(),
            height=surface.get_height(),
            bytes_estimate=bytes_estimate,
        )
        self._cache[cache_key] = entry
        self._current_bytes += bytes_estimate
    
    def _evict_oldest(self) -> None:
        """淘汰最旧的条目"""
        if not self._cache:
            return
        oldest_key = next(iter(self._cache))
        entry = self._cache.pop(oldest_key)
        self._current_bytes -= entry.bytes_estimate
        self.evictions += 1
    
    def invalidate(self, character_id: str) -> int:
        """使指定角色的所有缓存失效"""
        prefix = f"{character_id}:"
        to_remove = [k for k in self._cache if k.startswith(prefix)]
        for k in to_remove:
            entry = self._cache.pop(k)
            self._current_bytes -= entry.bytes_estimate
        return len(to_remove)
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._current_bytes = 0
    
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.hits + self.misses
        return {
            "entries": len(self._cache),
            "bytes_used": self._current_bytes,
            "bytes_limit": self._max_bytes,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hits / total if total > 0 else 0.0,
        }


# ============================================================================
# 差分立绘渲染器
# ============================================================================

class LayeredCharacterRenderer:
    """
    差分立绘渲染器
    
    支持两种模式：
    1. 差分模式：使用 manifest.json 定义的图层合成
    2. 简单模式：兼容旧的 base.png + pose_*.png 结构
    """
    
    def __init__(
        self,
        characters_dir: Optional[Path] = None,
        load_image_func: Optional[Callable[[str], Surface]] = None,
        make_placeholder_func: Optional[Callable[[str], Surface]] = None,
    ):
        self.characters_dir = characters_dir
        self._load_image = load_image_func
        self._make_placeholder = make_placeholder_func
        
        # 角色 manifest 缓存
        self._manifests: Dict[str, CharacterSpriteManifest] = {}
        
        # 合成器缓存
        self._compositors: Dict[str, SpriteCompositor] = {}
        
        # 当前角色状态
        self._states: Dict[str, SpriteState] = {}
        
        # 合成图像缓存
        self._composite_cache = CompositeCache()
        
        # 单层图像缓存（避免重复加载）
        self._layer_cache: Dict[str, Surface] = {}
        
        # 是否使用差分模式
        self._layered_mode: Dict[str, bool] = {}
        
        # 扫描并加载所有 manifest
        if characters_dir:
            self._scan_manifests()
    
    def _scan_manifests(self) -> None:
        """扫描并加载所有角色 manifest"""
        if not self.characters_dir or not self.characters_dir.exists():
            return
        
        self._manifests = scan_characters_directory(self.characters_dir)
        
        for char_id, manifest in self._manifests.items():
            self._compositors[char_id] = SpriteCompositor(manifest)
            self._layered_mode[char_id] = True
    
    def has_manifest(self, character_id: str) -> bool:
        """检查角色是否有 manifest"""
        return character_id in self._manifests
    
    def get_state(self, character_id: str) -> Optional[SpriteState]:
        """获取角色当前状态"""
        return self._states.get(character_id)
    
    def set_state(
        self,
        character_id: str,
        pose: Optional[str] = None,
        expression: Optional[str] = None,
        outfit: Optional[str] = None,
        effects: Optional[List[str]] = None,
    ) -> SpriteState:
        """设置角色状态"""
        # 获取或创建状态
        state = self._states.get(character_id)
        if state is None:
            manifest = self._manifests.get(character_id)
            state = SpriteState(
                character_id=character_id,
                pose=manifest.default_pose if manifest else "normal",
                expression=manifest.default_expression if manifest else "normal",
                outfit=manifest.default_outfit if manifest else "default",
            )
            self._states[character_id] = state
        
        # 更新状态
        if pose is not None:
            state.pose = pose
        if expression is not None:
            state.expression = expression
        if outfit is not None:
            state.outfit = outfit
        if effects is not None:
            state.active_effects = effects
        
        return state
    
    def add_effect(self, character_id: str, effect: str) -> None:
        """添加特效"""
        state = self._states.get(character_id)
        if state and effect not in state.active_effects:
            state.active_effects.append(effect)
    
    def remove_effect(self, character_id: str, effect: str) -> None:
        """移除特效"""
        state = self._states.get(character_id)
        if state and effect in state.active_effects:
            state.active_effects.remove(effect)
    
    def clear_effects(self, character_id: str) -> None:
        """清除所有特效"""
        state = self._states.get(character_id)
        if state:
            state.active_effects.clear()
    
    def _load_layer_image(self, character_id: str, layer_file: str) -> Optional[Surface]:
        """加载单个图层图像"""
        if not self._load_image:
            return None
        
        cache_key = f"{character_id}/{layer_file}"
        
        # 检查缓存
        if cache_key in self._layer_cache:
            return self._layer_cache[cache_key]
        
        # 加载图像
        try:
            if self.characters_dir:
                full_path = str(self.characters_dir / character_id / layer_file)
            else:
                full_path = f"ch/{character_id}/{layer_file}"
            
            surface = self._load_image(full_path)
            if surface:
                self._layer_cache[cache_key] = surface
            return surface
        except Exception:
            return None
    
    def compose(self, character_id: str) -> Optional[Surface]:
        """
        合成角色立绘
        
        返回合成后的 Surface
        """
        if not HAS_PYGAME:
            return None
        
        state = self._states.get(character_id)
        if not state:
            return None
        
        # 检查是否使用差分模式
        if not self._layered_mode.get(character_id, False):
            return None  # 不使用差分模式，返回 None 让调用者使用旧逻辑
        
        manifest = self._manifests.get(character_id)
        compositor = self._compositors.get(character_id)
        if not manifest or not compositor:
            return None
        
        # 检查缓存
        cache_key = state.get_cache_key()
        cached = self._composite_cache.get(cache_key)
        if cached:
            return cached
        
        # 获取需要渲染的图层
        layers = compositor.get_render_layers(state)
        if not layers:
            return None
        
        # 创建画布
        canvas = pygame.Surface(
            (manifest.canvas_width, manifest.canvas_height),
            pygame.SRCALPHA
        )
        
        # 逐层渲染
        for layer_def, offset_x, offset_y in layers:
            layer_surface = self._load_layer_image(character_id, layer_def.file)
            if layer_surface is None:
                continue
            
            # 应用透明度
            if layer_def.opacity < 1.0:
                layer_surface = layer_surface.copy()
                alpha = int(255 * layer_def.opacity)
                layer_surface.set_alpha(alpha)
            
            # 绘制到画布
            canvas.blit(layer_surface, (offset_x, offset_y))
        
        # 缓存合成结果
        self._composite_cache.put(cache_key, canvas)
        
        return canvas
    
    def remove_character(self, character_id: str) -> None:
        """移除角色"""
        self._states.pop(character_id, None)
        self._composite_cache.invalidate(character_id)
    
    def clear(self) -> None:
        """清除所有角色"""
        self._states.clear()
        self._composite_cache.clear()
    
    def invalidate_cache(self, character_id: Optional[str] = None) -> None:
        """使缓存失效"""
        if character_id:
            self._composite_cache.invalidate(character_id)
            # 清除图层缓存
            prefix = f"{character_id}/"
            to_remove = [k for k in self._layer_cache if k.startswith(prefix)]
            for k in to_remove:
                del self._layer_cache[k]
        else:
            self._composite_cache.clear()
            self._layer_cache.clear()
    
    def reload_manifest(self, character_id: str) -> bool:
        """重新加载角色 manifest"""
        if not self.characters_dir:
            return False
        
        manifest_path = self.characters_dir / character_id / "manifest.json"
        if not manifest_path.exists():
            return False
        
        try:
            manifest = CharacterSpriteManifest.load(manifest_path)
            self._manifests[character_id] = manifest
            self._compositors[character_id] = SpriteCompositor(manifest)
            self._layered_mode[character_id] = True
            self.invalidate_cache(character_id)
            return True
        except Exception:
            return False
    
    def get_available_poses(self, character_id: str) -> List[str]:
        """获取可用的姿势列表"""
        manifest = self._manifests.get(character_id)
        return list(manifest.poses.keys()) if manifest else []
    
    def get_available_expressions(self, character_id: str) -> List[str]:
        """获取可用的表情列表"""
        manifest = self._manifests.get(character_id)
        return list(manifest.expressions.keys()) if manifest else []
    
    def get_available_outfits(self, character_id: str) -> List[str]:
        """获取可用的服装列表"""
        manifest = self._manifests.get(character_id)
        return list(manifest.outfits.keys()) if manifest else []
    
    def get_available_effects(self, character_id: str) -> List[str]:
        """获取可用的特效列表"""
        manifest = self._manifests.get(character_id)
        return list(manifest.effects.keys()) if manifest else []
    
    def cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "composite_cache": self._composite_cache.stats(),
            "layer_cache_entries": len(self._layer_cache),
            "manifests_loaded": len(self._manifests),
            "active_characters": len(self._states),
        }


# ============================================================================
# 资源加载器（集成分包系统）
# ============================================================================

class AssetLoader:
    """
    统一资源加载器
    
    支持从以下来源加载资源：
    1. 本地文件系统
    2. 分包 (.hgp) 文件
    3. 内存缓存
    """
    
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        patch_registry: Optional[Any] = None,  # PatchRegistry
    ):
        self.base_dir = base_dir
        self.patch_registry = patch_registry
        
        # 图像缓存
        self._image_cache: Dict[str, Surface] = {}
        
        # 统计
        self.loads = 0
        self.cache_hits = 0
    
    def load_image(self, path: str, convert: str = "alpha") -> Optional[Surface]:
        """
        加载图像
        
        Args:
            path: 资源路径
            convert: 转换模式 ("alpha", "convert", None)
        """
        if not HAS_PYGAME:
            return None
        
        # 检查缓存
        cache_key = f"{path}:{convert}"
        if cache_key in self._image_cache:
            self.cache_hits += 1
            return self._image_cache[cache_key]
        
        self.loads += 1
        surface = None
        
        # 尝试从分包加载
        if self.patch_registry:
            try:
                data = self.patch_registry.read(path)
                import io
                surface = pygame.image.load(io.BytesIO(data))
            except Exception:
                pass
        
        # 尝试从文件系统加载
        if surface is None and self.base_dir:
            try:
                full_path = self.base_dir / path
                if full_path.exists():
                    surface = pygame.image.load(str(full_path))
            except Exception:
                pass
        
        # 尝试直接加载路径
        if surface is None:
            try:
                surface = pygame.image.load(path)
            except Exception:
                pass
        
        # 转换
        if surface is not None:
            if convert == "alpha":
                surface = surface.convert_alpha()
            elif convert == "convert":
                surface = surface.convert()
        
        # 缓存
        if surface is not None:
            self._image_cache[cache_key] = surface
        
        return surface
    
    def load_bytes(self, path: str) -> Optional[bytes]:
        """加载原始字节"""
        # 尝试从分包加载
        if self.patch_registry:
            try:
                return self.patch_registry.read(path)
            except Exception:
                pass
        
        # 尝试从文件系统加载
        if self.base_dir:
            try:
                full_path = self.base_dir / path
                if full_path.exists():
                    return full_path.read_bytes()
            except Exception:
                pass
        
        # 尝试直接加载路径
        try:
            return Path(path).read_bytes()
        except Exception:
            pass
        
        return None
    
    def exists(self, path: str) -> bool:
        """检查资源是否存在"""
        # 检查分包
        if self.patch_registry and self.patch_registry.exists(path):
            return True
        
        # 检查文件系统
        if self.base_dir:
            full_path = self.base_dir / path
            if full_path.exists():
                return True
        
        # 检查直接路径
        return Path(path).exists()
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._image_cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "loads": self.loads,
            "cache_hits": self.cache_hits,
            "cache_entries": len(self._image_cache),
            "hit_rate": self.cache_hits / self.loads if self.loads > 0 else 0.0,
        }
