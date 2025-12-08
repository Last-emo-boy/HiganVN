"""
Enhanced Character Layer - 增强角色图层

扩展原有 CharacterLayer，集成差分立绘渲染系统：
- 自动检测并使用差分立绘模式
- 兼容旧的简单立绘模式
- 统一的状态管理接口
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple, Callable, List, Any
from pathlib import Path

try:
    import pygame
    from pygame import Surface
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    Surface = Any

from higanvn.engine.animator import Animator
from higanvn.engine.surface_utils import scale_to_height
from higanvn.engine.image_cache import load_image
from higanvn.engine.layered_renderer import LayeredCharacterRenderer, AssetLoader

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class EnhancedCharacterLayer:
    """
    增强角色图层
    
    自动检测角色是否有差分立绘 manifest：
    - 有 manifest: 使用差分立绘合成
    - 无 manifest: 使用传统的 base.png + pose_*.png
    """
    
    def __init__(
        self,
        slots: dict,
        characters_dir: Optional[Path] = None,
        asset_loader: Optional[AssetLoader] = None,
    ) -> None:
        self._slots = slots or {}
        self.characters_dir = characters_dir
        self.asset_loader = asset_loader
        
        # 传统模式数据
        self.characters: Dict[str, Tuple[Optional[Surface], Optional[Surface]]] = {}
        self.active_actor: Optional[str] = None
        self._outfits: Dict[str, Optional[str]] = {}
        self._actions: Dict[str, Optional[Surface]] = {}
        self._pose_names: Dict[str, Optional[str]] = {}
        self._action_names: Dict[str, Optional[str]] = {}
        
        # 差分立绘渲染器
        self._layered_renderer: Optional[LayeredCharacterRenderer] = None
        if characters_dir:
            self._init_layered_renderer()
        
        # 模式标记（每个角色可能使用不同模式）
        self._use_layered: Dict[str, bool] = {}
        
        # 调试信息
        self._last_rects: Dict[str, Any] = {}
        self._last_centers: Dict[str, Tuple[int, int]] = {}
        
        # 严格模式
        self._strict_mode = False
    
    def _init_layered_renderer(self) -> None:
        """初始化差分立绘渲染器"""
        if not self.characters_dir:
            return
        
        def load_func(path: str) -> Optional[Surface]:
            if self.asset_loader:
                return self.asset_loader.load_image(path)
            try:
                return load_image(path, convert="alpha")
            except Exception:
                return None
        
        self._layered_renderer = LayeredCharacterRenderer(
            characters_dir=self.characters_dir,
            load_image_func=load_func,
        )
    
    def set_strict_mode(self, strict: bool) -> None:
        """设置严格模式"""
        self._strict_mode = bool(strict)
    
    def _is_layered(self, actor: str) -> bool:
        """检查角色是否使用差分立绘模式"""
        if actor in self._use_layered:
            return self._use_layered[actor]
        
        # 检查是否有 manifest
        if self._layered_renderer and self._layered_renderer.has_manifest(actor):
            self._use_layered[actor] = True
            return True
        
        self._use_layered[actor] = False
        return False
    
    def set_outfit(self, actor: str, outfit: Optional[str]) -> None:
        """设置服装"""
        self._outfits[actor] = outfit if outfit else None
        
        if self._is_layered(actor) and self._layered_renderer:
            self._layered_renderer.set_state(actor, outfit=outfit or "default")
            self._layered_renderer.invalidate_cache(actor)
        else:
            # 传统模式：清除缓存
            if actor in self.characters:
                self.characters.pop(actor, None)
            self._actions.pop(actor, None)
            self._pose_names.pop(actor, None)
            self._action_names.pop(actor, None)
    
    def ensure_loaded(
        self,
        actor: str,
        resolve_path: Callable[[str], str],
        make_placeholder: Callable[[str], Surface],
    ) -> None:
        """确保角色已加载"""
        if self._is_layered(actor):
            # 差分模式：初始化状态
            if self._layered_renderer:
                self._layered_renderer.set_state(actor)
            return
        
        # 传统模式
        if actor in self.characters:
            return
        
        outfit = self._outfits.get(actor)
        base: Optional[Surface] = None
        
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/base.png")
                base = load_image(p1, convert="alpha")
            except Exception:
                base = None
            if base is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/base.png")
                    base = load_image(p2, convert="alpha")
                except Exception:
                    base = None
        else:
            try:
                p = resolve_path(f"ch/{actor}/base.png")
                base = load_image(p, convert="alpha")
            except Exception:
                base = None
        
        if base is None:
            base = make_placeholder(actor)
        
        self.characters[actor] = (base, None)
    
    def set_pose(
        self,
        actor: str,
        emotion: str,
        resolve_path: Callable[[str], str],
        make_pose_ph: Callable[[str], Surface],
    ) -> None:
        """设置表情/姿势"""
        if self._is_layered(actor):
            # 差分模式：尝试解析为 pose:expression 格式
            if self._layered_renderer:
                # 检查是否是复合格式 "pose:expression:outfit"
                parts = emotion.split(":")
                pose = parts[0] if len(parts) > 0 else None
                expression = parts[1] if len(parts) > 1 else parts[0]
                outfit = parts[2] if len(parts) > 2 else None
                
                # 检查 pose 是否有效，否则作为 expression
                available_poses = self._layered_renderer.get_available_poses(actor)
                if pose and pose not in available_poses:
                    # pose 实际上是 expression
                    expression = pose
                    pose = None
                
                # 检查是否有特效 (用 + 分隔) - 在确定 expression 后再分离
                effects = []
                if "+" in (expression or ""):
                    effect_parts = expression.split("+")
                    expression = effect_parts[0]
                    effects = effect_parts[1:]
                
                self._layered_renderer.set_state(
                    actor,
                    pose=pose,
                    expression=expression,
                    outfit=outfit,
                    effects=effects if effects else None,
                )
            self._pose_names[actor] = emotion
            return
        
        # 传统模式
        base, _ = self.characters.get(actor, (None, None))
        outfit = self._outfits.get(actor)
        pose = None
        
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/pose_{emotion}.png")
                pose = load_image(p1, convert="alpha")
            except Exception:
                pose = None
            if pose is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/pose_{emotion}.png")
                    pose = load_image(p2, convert="alpha")
                except Exception:
                    pose = None
        else:
            try:
                p2 = resolve_path(f"ch/{actor}/pose_{emotion}.png")
                pose = load_image(p2, convert="alpha")
            except Exception:
                pose = None
        
        if pose is None:
            if self._strict_mode:
                pose = make_pose_ph(str(emotion))
            else:
                pose = None
        
        self.characters[actor] = (base, pose)
        self._pose_names[actor] = str(emotion)
    
    def set_action(
        self,
        actor: str,
        action: Optional[str],
        resolve_path: Callable[[str], str],
        make_pose_ph: Callable[[str], Surface],
    ) -> None:
        """设置动作"""
        if not action:
            self._actions[actor] = None
            self._action_names.pop(actor, None)
            return
        
        # 差分模式暂不支持 action，使用传统模式处理
        outfit = self._outfits.get(actor)
        img = None
        
        if outfit:
            try:
                p1 = resolve_path(f"ch/{actor}/{outfit}/action_{action}.png")
                img = load_image(p1, convert="alpha")
            except Exception:
                img = None
            if img is None and not self._strict_mode:
                try:
                    p2 = resolve_path(f"ch/{actor}/action_{action}.png")
                    img = load_image(p2, convert="alpha")
                except Exception:
                    img = None
        else:
            try:
                p2 = resolve_path(f"ch/{actor}/action_{action}.png")
                img = load_image(p2, convert="alpha")
            except Exception:
                img = None
        
        if img is None:
            if self._strict_mode:
                img = make_pose_ph(f"action:{action}")
            else:
                img = None
        
        self._actions[actor] = img
        self._action_names[actor] = str(action)
    
    def add_effect(self, actor: str, effect: str) -> None:
        """添加特效（仅差分模式）"""
        if self._is_layered(actor) and self._layered_renderer:
            self._layered_renderer.add_effect(actor, effect)
    
    def remove_effect(self, actor: str, effect: str) -> None:
        """移除特效（仅差分模式）"""
        if self._is_layered(actor) and self._layered_renderer:
            self._layered_renderer.remove_effect(actor, effect)
    
    def clear_effects(self, actor: str) -> None:
        """清除所有特效（仅差分模式）"""
        if self._is_layered(actor) and self._layered_renderer:
            self._layered_renderer.clear_effects(actor)
    
    def remove(self, actor: str) -> None:
        """移除角色"""
        self.characters.pop(actor, None)
        self._actions.pop(actor, None)
        self._pose_names.pop(actor, None)
        self._action_names.pop(actor, None)
        self._use_layered.pop(actor, None)
        
        if self._layered_renderer:
            self._layered_renderer.remove_character(actor)
        
        if self.active_actor == actor:
            self.active_actor = None
    
    def clear(self) -> None:
        """清除所有角色"""
        self.characters.clear()
        self._actions.clear()
        self._pose_names.clear()
        self._action_names.clear()
        self._use_layered.clear()
        self.active_actor = None
        self._last_rects.clear()
        self._last_centers.clear()
        
        if self._layered_renderer:
            self._layered_renderer.clear()
    
    def render(self, canvas: Surface, animator: Animator, now_ms: int) -> None:
        """渲染所有角色"""
        if not HAS_PYGAME:
            return
        
        # 收集所有要渲染的角色
        actors_to_render = set(self.characters.keys())
        if self._layered_renderer:
            for actor in list(self._layered_renderer._states.keys()):
                actors_to_render.add(actor)
        
        if not actors_to_render:
            return
        
        slot_positions = self._slots.get(
            "positions",
            [
                (int(LOGICAL_SIZE[0] * 0.2), int(LOGICAL_SIZE[1] * 0.64)),
                (int(LOGICAL_SIZE[0] * 0.5), int(LOGICAL_SIZE[1] * 0.64)),
                (int(LOGICAL_SIZE[0] * 0.8), int(LOGICAL_SIZE[1] * 0.64)),
            ],
        )
        slot_scale = float(self._slots.get("scale", 0.9))
        order = list(actors_to_render)
        eff_scale = slot_scale * (0.86 if len(order) >= 3 else 1.0)
        n = len(order)
        pos_count = max(1, len(slot_positions))
        
        if n == 1:
            mid = 1 if pos_count >= 3 else (pos_count // 2)
            slot_index_map = [mid]
        elif n == 2:
            if pos_count >= 3:
                slot_index_map = [0, 2]
            elif pos_count >= 2:
                slot_index_map = [0, 1]
            else:
                slot_index_map = [0, 0]
        else:
            slot_index_map = [i % pos_count for i in range(n)]
        
        # 活跃角色放最后（在最前面渲染）
        if self.active_actor in order:
            order = [a for a in order if a != self.active_actor] + [self.active_actor]
        
        self._last_rects.clear()
        self._last_centers.clear()
        
        for idx, actor in enumerate(order):
            si = slot_index_map[idx] if idx < len(slot_index_map) else (idx % pos_count)
            x, y = slot_positions[si]
            dx, dy = animator.offset(now_ms, actor, LOGICAL_SIZE[0], LOGICAL_SIZE[1])
            cx, cy = int(x + dx), int(y + dy)
            
            # 检查是否有 action（action 优先）
            act = self._actions.get(actor)
            if act is not None:
                a_s = scale_to_height(act, int(LOGICAL_SIZE[1] * eff_scale))
                recta = a_s.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim_a = a_s.copy()
                    dim_a.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim_a, recta)
                else:
                    canvas.blit(a_s, recta)
                self._last_rects[actor] = recta
                self._last_centers[actor] = (cx, cy)
                continue
            
            # 尝试差分模式
            if self._is_layered(actor) and self._layered_renderer:
                composed = self._layered_renderer.compose(actor)
                if composed:
                    scaled = scale_to_height(composed, int(LOGICAL_SIZE[1] * eff_scale))
                    rect = scaled.get_rect(center=(cx, cy))
                    if self.active_actor and actor != self.active_actor:
                        dim = scaled.copy()
                        dim.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                        canvas.blit(dim, rect)
                    else:
                        canvas.blit(scaled, rect)
                    self._last_rects[actor] = rect
                    self._last_centers[actor] = (cx, cy)
                    continue
            
            # 传统模式
            base, pose = self.characters.get(actor, (None, None))
            body = pose if pose is not None else base
            if body is not None:
                b = scale_to_height(body, int(LOGICAL_SIZE[1] * eff_scale))
                rect = b.get_rect(center=(cx, cy))
                if self.active_actor and actor != self.active_actor:
                    dim = b.copy()
                    dim.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_SUB)
                    canvas.blit(dim, rect)
                else:
                    canvas.blit(b, rect)
                self._last_rects[actor] = rect
                self._last_centers[actor] = (cx, cy)
    
    def last_rects(self) -> Dict[str, Any]:
        """获取角色渲染矩形"""
        return dict(self._last_rects)
    
    def last_centers(self) -> Dict[str, Tuple[int, int]]:
        """获取角色中心位置"""
        return dict(self._last_centers)
    
    def snapshot_characters(self) -> List[dict]:
        """获取角色快照（用于存档）"""
        data: List[dict] = []
        
        # 收集所有角色
        all_actors = set(self.characters.keys())
        if self._layered_renderer:
            all_actors.update(self._layered_renderer._states.keys())
        
        for actor in all_actors:
            entry = {
                "id": actor,
                "outfit": self._outfits.get(actor),
                "pose": self._pose_names.get(actor),
                "action": self._action_names.get(actor),
                "layered": self._is_layered(actor),
            }
            
            # 差分模式额外数据
            if self._is_layered(actor) and self._layered_renderer:
                state = self._layered_renderer.get_state(actor)
                if state:
                    entry["layered_state"] = {
                        "pose": state.pose,
                        "expression": state.expression,
                        "outfit": state.outfit,
                        "effects": state.active_effects,
                    }
            
            data.append(entry)
        
        return data
    
    def restore_from_snapshot(
        self,
        data: List[dict],
        resolve_path: Callable[[str], str],
        make_placeholder: Callable[[str], Surface],
        make_pose_ph: Callable[[str], Surface],
    ) -> None:
        """从快照恢复角色状态"""
        self.clear()
        
        for entry in data:
            actor = entry.get("id")
            if not actor:
                continue
            
            outfit = entry.get("outfit")
            pose = entry.get("pose")
            action = entry.get("action")
            
            # 设置服装
            if outfit:
                self.set_outfit(actor, outfit)
            
            # 加载角色
            self.ensure_loaded(actor, resolve_path, make_placeholder)
            
            # 差分模式恢复
            if entry.get("layered") and self._layered_renderer:
                layered_state = entry.get("layered_state", {})
                self._layered_renderer.set_state(
                    actor,
                    pose=layered_state.get("pose"),
                    expression=layered_state.get("expression"),
                    outfit=layered_state.get("outfit"),
                    effects=layered_state.get("effects"),
                )
            elif pose:
                self.set_pose(actor, pose, resolve_path, make_pose_ph)
            
            # 设置动作
            if action:
                self.set_action(actor, action, resolve_path, make_pose_ph)
    
    def get_available_expressions(self, actor: str) -> List[str]:
        """获取可用表情列表"""
        if self._is_layered(actor) and self._layered_renderer:
            return self._layered_renderer.get_available_expressions(actor)
        return []
    
    def get_available_outfits(self, actor: str) -> List[str]:
        """获取可用服装列表"""
        if self._is_layered(actor) and self._layered_renderer:
            return self._layered_renderer.get_available_outfits(actor)
        return []
    
    def cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        stats = {
            "traditional_characters": len(self.characters),
            "layered_mode": dict(self._use_layered),
        }
        if self._layered_renderer:
            stats["layered_renderer"] = self._layered_renderer.cache_stats()
        return stats
