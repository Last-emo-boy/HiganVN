"""
Layered Sprite System - 差分立绘合成系统

功能：
- 身体底图 + 表情差分 + 服装差分
- 实时合成渲染
- 表情/姿势动态切换
- 支持部位级别的差分（眼睛、嘴巴、眉毛分离）

立绘结构:
    characters/{actor_id}/
    ├── manifest.json           # 角色配置
    ├── base/                   # 身体底图
    │   ├── normal.png          # 普通姿势
    │   ├── cross_arms.png      # 抱臂
    │   └── sit.png             # 坐姿
    ├── face/                   # 面部差分（可选细分）
    │   ├── normal/
    │   │   ├── eyes.png
    │   │   ├── mouth.png
    │   │   └── eyebrows.png
    │   ├── happy.png           # 或整体表情
    │   ├── sad.png
    │   └── angry.png
    ├── outfit/                 # 服装差分
    │   ├── school/
    │   │   ├── body.png        # 服装主体
    │   │   └── accessory.png   # 配饰（领带等）
    │   ├── casual/
    │   └── swimsuit/
    └── effects/                # 特效层（可选）
        ├── blush.png           # 脸红
        ├── sweat.png           # 汗滴
        └── shadow.png          # 阴影
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum, auto
import hashlib


# ============================================================================
# 图层类型
# ============================================================================

class LayerType(Enum):
    """图层类型"""
    BASE = 0            # 身体底图
    OUTFIT_UNDER = 1    # 服装底层（内衣等）
    OUTFIT = 2          # 主要服装
    OUTFIT_OVER = 3     # 服装覆盖层（外套等）
    FACE_BASE = 10      # 面部底图
    EYEBROWS = 11       # 眉毛
    EYES = 12           # 眼睛
    MOUTH = 13          # 嘴巴
    FACE_COMPOSITE = 14 # 整合表情（非分离式）
    EFFECT = 20         # 特效层
    ACCESSORY = 21      # 配饰
    OVERLAY = 30        # 覆盖层（光效等）


class BlendMode(Enum):
    """混合模式"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    ADD = "add"
    SUBTRACT = "subtract"


# ============================================================================
# 图层定义
# ============================================================================

@dataclass
class LayerDefinition:
    """单个图层定义"""
    id: str                             # 图层ID
    layer_type: LayerType               # 图层类型
    file: str                           # 相对文件路径
    offset_x: int = 0                   # X 偏移
    offset_y: int = 0                   # Y 偏移
    z_order: int = 0                    # Z 顺序（越大越靠前）
    blend_mode: BlendMode = BlendMode.NORMAL
    opacity: float = 1.0                # 不透明度
    visible: bool = True                # 默认可见性
    condition: Optional[str] = None     # 显示条件表达式
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'layer_type': self.layer_type.name,
            'file': self.file,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'z_order': self.z_order,
            'blend_mode': self.blend_mode.value,
            'opacity': self.opacity,
            'visible': self.visible,
            'condition': self.condition,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'LayerDefinition':
        return cls(
            id=d['id'],
            layer_type=LayerType[d.get('layer_type', 'BASE')],
            file=d['file'],
            offset_x=d.get('offset_x', 0),
            offset_y=d.get('offset_y', 0),
            z_order=d.get('z_order', 0),
            blend_mode=BlendMode(d.get('blend_mode', 'normal')),
            opacity=d.get('opacity', 1.0),
            visible=d.get('visible', True),
            condition=d.get('condition'),
        )


@dataclass
class PoseDefinition:
    """姿势定义"""
    id: str                             # 姿势ID (normal, sit, cross_arms)
    base_layer: str                     # 基础身体图层ID
    face_offset: Tuple[int, int] = (0, 0)  # 面部相对偏移
    compatible_outfits: List[str] = field(default_factory=list)  # 兼容的服装
    layers: List[LayerDefinition] = field(default_factory=list)  # 额外图层
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'base_layer': self.base_layer,
            'face_offset': list(self.face_offset),
            'compatible_outfits': self.compatible_outfits,
            'layers': [l.to_dict() for l in self.layers],
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'PoseDefinition':
        return cls(
            id=d['id'],
            base_layer=d['base_layer'],
            face_offset=tuple(d.get('face_offset', [0, 0])),
            compatible_outfits=d.get('compatible_outfits', []),
            layers=[LayerDefinition.from_dict(l) for l in d.get('layers', [])],
        )


@dataclass
class ExpressionDefinition:
    """表情定义"""
    id: str                             # 表情ID (normal, happy, sad)
    
    # 整合模式：单个表情图
    composite_layer: Optional[str] = None
    
    # 分离模式：眼睛、嘴巴、眉毛分离
    eyes_layer: Optional[str] = None
    mouth_layer: Optional[str] = None
    eyebrows_layer: Optional[str] = None
    
    # 可选特效
    effects: List[str] = field(default_factory=list)  # 特效图层ID列表
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'composite_layer': self.composite_layer,
            'eyes_layer': self.eyes_layer,
            'mouth_layer': self.mouth_layer,
            'eyebrows_layer': self.eyebrows_layer,
            'effects': self.effects,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ExpressionDefinition':
        return cls(
            id=d['id'],
            composite_layer=d.get('composite_layer'),
            eyes_layer=d.get('eyes_layer'),
            mouth_layer=d.get('mouth_layer'),
            eyebrows_layer=d.get('eyebrows_layer'),
            effects=d.get('effects', []),
        )


@dataclass
class OutfitDefinition:
    """服装定义"""
    id: str                             # 服装ID (school, casual)
    name: str = ""                      # 显示名称
    layers: List[LayerDefinition] = field(default_factory=list)
    compatible_poses: List[str] = field(default_factory=list)  # 兼容的姿势
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'layers': [l.to_dict() for l in self.layers],
            'compatible_poses': self.compatible_poses,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'OutfitDefinition':
        return cls(
            id=d['id'],
            name=d.get('name', ''),
            layers=[LayerDefinition.from_dict(l) for l in d.get('layers', [])],
            compatible_poses=d.get('compatible_poses', []),
        )


# ============================================================================
# 角色立绘清单
# ============================================================================

@dataclass
class CharacterSpriteManifest:
    """
    角色立绘完整清单
    
    定义一个角色的所有差分组件
    """
    id: str                             # 角色ID
    name: str                           # 显示名称
    version: str = "1.0.0"              # 版本
    
    # 画布尺寸
    canvas_width: int = 1024
    canvas_height: int = 1536
    
    # 默认值
    default_pose: str = "normal"
    default_expression: str = "normal"
    default_outfit: str = "default"
    
    # 所有图层（资源池）
    layers: Dict[str, LayerDefinition] = field(default_factory=dict)
    
    # 姿势定义
    poses: Dict[str, PoseDefinition] = field(default_factory=dict)
    
    # 表情定义
    expressions: Dict[str, ExpressionDefinition] = field(default_factory=dict)
    
    # 服装定义
    outfits: Dict[str, OutfitDefinition] = field(default_factory=dict)
    
    # 特效定义
    effects: Dict[str, LayerDefinition] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        data = {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'canvas_width': self.canvas_width,
            'canvas_height': self.canvas_height,
            'default_pose': self.default_pose,
            'default_expression': self.default_expression,
            'default_outfit': self.default_outfit,
            'layers': {k: v.to_dict() for k, v in self.layers.items()},
            'poses': {k: v.to_dict() for k, v in self.poses.items()},
            'expressions': {k: v.to_dict() for k, v in self.expressions.items()},
            'outfits': {k: v.to_dict() for k, v in self.outfits.items()},
            'effects': {k: v.to_dict() for k, v in self.effects.items()},
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CharacterSpriteManifest':
        """从 JSON 反序列化"""
        data = json.loads(json_str)
        manifest = cls(
            id=data['id'],
            name=data.get('name', data['id']),
            version=data.get('version', '1.0.0'),
            canvas_width=data.get('canvas_width', 1024),
            canvas_height=data.get('canvas_height', 1536),
            default_pose=data.get('default_pose', 'normal'),
            default_expression=data.get('default_expression', 'normal'),
            default_outfit=data.get('default_outfit', 'default'),
        )
        
        # 解析图层
        for k, v in data.get('layers', {}).items():
            manifest.layers[k] = LayerDefinition.from_dict(v)
        
        # 解析姿势
        for k, v in data.get('poses', {}).items():
            manifest.poses[k] = PoseDefinition.from_dict(v)
        
        # 解析表情
        for k, v in data.get('expressions', {}).items():
            manifest.expressions[k] = ExpressionDefinition.from_dict(v)
        
        # 解析服装
        for k, v in data.get('outfits', {}).items():
            manifest.outfits[k] = OutfitDefinition.from_dict(v)
        
        # 解析特效
        for k, v in data.get('effects', {}).items():
            manifest.effects[k] = LayerDefinition.from_dict(v)
        
        return manifest
    
    @classmethod
    def load(cls, manifest_path: Path) -> 'CharacterSpriteManifest':
        """从文件加载"""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())
    
    def save(self, manifest_path: Path):
        """保存到文件"""
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


# ============================================================================
# 立绘状态
# ============================================================================

@dataclass
class SpriteState:
    """
    立绘当前状态
    
    记录当前显示的姿势、表情、服装组合
    """
    character_id: str
    pose: str = "normal"
    expression: str = "normal"
    outfit: str = "default"
    
    # 额外激活的特效
    active_effects: List[str] = field(default_factory=list)
    
    # 覆盖设置
    opacity: float = 1.0
    scale: float = 1.0
    flip_h: bool = False
    
    # 位置
    position_x: int = 0
    position_y: int = 0
    
    def get_cache_key(self) -> str:
        """生成缓存键"""
        effects_str = ','.join(sorted(self.active_effects))
        return f"{self.character_id}:{self.pose}:{self.expression}:{self.outfit}:{effects_str}"


# ============================================================================
# 立绘合成器
# ============================================================================

class SpriteCompositor:
    """
    立绘合成器
    
    根据 manifest 和 state 计算需要渲染的图层列表
    """
    
    def __init__(self, manifest: CharacterSpriteManifest):
        self.manifest = manifest
    
    def get_render_layers(self, state: SpriteState) -> List[Tuple[LayerDefinition, int, int]]:
        """
        获取需要渲染的图层列表
        
        返回: [(图层定义, x偏移, y偏移), ...]，按 z_order 排序
        """
        layers: List[Tuple[LayerDefinition, int, int, int]] = []  # (layer, x, y, z)
        
        # 1. 获取姿势
        pose = self.manifest.poses.get(state.pose)
        if not pose:
            pose = self.manifest.poses.get(self.manifest.default_pose)
        if not pose:
            return []
        
        # 2. 添加身体底图
        base_layer = self.manifest.layers.get(pose.base_layer)
        if base_layer:
            layers.append((base_layer, base_layer.offset_x, base_layer.offset_y, base_layer.z_order))
        
        # 3. 添加服装
        outfit = self.manifest.outfits.get(state.outfit)
        if not outfit:
            outfit = self.manifest.outfits.get(self.manifest.default_outfit)
        
        if outfit:
            for layer in outfit.layers:
                layers.append((layer, layer.offset_x, layer.offset_y, layer.z_order))
        
        # 4. 添加表情
        expression = self.manifest.expressions.get(state.expression)
        if not expression:
            expression = self.manifest.expressions.get(self.manifest.default_expression)
        
        if expression:
            face_offset_x, face_offset_y = pose.face_offset
            
            # 整合模式
            if expression.composite_layer:
                face_layer = self.manifest.layers.get(expression.composite_layer)
                if face_layer:
                    layers.append((
                        face_layer,
                        face_layer.offset_x + face_offset_x,
                        face_layer.offset_y + face_offset_y,
                        face_layer.z_order
                    ))
            
            # 分离模式
            else:
                for layer_id in [expression.eyebrows_layer, expression.eyes_layer, expression.mouth_layer]:
                    if layer_id:
                        layer = self.manifest.layers.get(layer_id)
                        if layer:
                            layers.append((
                                layer,
                                layer.offset_x + face_offset_x,
                                layer.offset_y + face_offset_y,
                                layer.z_order
                            ))
            
            # 表情自带特效
            for effect_id in expression.effects:
                effect = self.manifest.effects.get(effect_id)
                if effect:
                    layers.append((
                        effect,
                        effect.offset_x + face_offset_x,
                        effect.offset_y + face_offset_y,
                        effect.z_order
                    ))
        
        # 5. 添加激活的特效
        for effect_id in state.active_effects:
            effect = self.manifest.effects.get(effect_id)
            if effect:
                layers.append((effect, effect.offset_x, effect.offset_y, effect.z_order))
        
        # 按 z_order 排序
        layers.sort(key=lambda x: x[3])
        
        # 返回 (layer, x, y)
        return [(l[0], l[1], l[2]) for l in layers]
    
    def get_required_files(self, state: SpriteState) -> List[str]:
        """获取需要加载的文件列表"""
        layers = self.get_render_layers(state)
        return [layer.file for layer, _, _ in layers]


# ============================================================================
# 辅助函数：创建角色模板
# ============================================================================

def create_character_template(
    character_id: str,
    name: str,
    output_dir: Path,
    expressions: List[str] = None,
    outfits: List[str] = None,
    poses: List[str] = None,
) -> CharacterSpriteManifest:
    """
    创建角色差分模板
    
    生成标准目录结构和 manifest
    """
    if expressions is None:
        expressions = ['normal', 'happy', 'sad', 'angry', 'surprise', 'shy']
    if outfits is None:
        outfits = ['default', 'school', 'casual']
    if poses is None:
        poses = ['normal']
    
    char_dir = output_dir / character_id
    
    # 创建目录结构
    dirs = [
        char_dir / 'base',
        char_dir / 'face',
        char_dir / 'outfit',
        char_dir / 'effects',
    ]
    for outfit in outfits:
        dirs.append(char_dir / 'outfit' / outfit)
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    
    # 创建 manifest
    manifest = CharacterSpriteManifest(
        id=character_id,
        name=name,
    )
    
    # 添加身体底图层
    for pose_id in poses:
        layer_id = f"base_{pose_id}"
        manifest.layers[layer_id] = LayerDefinition(
            id=layer_id,
            layer_type=LayerType.BASE,
            file=f"base/{pose_id}.png",
            z_order=0,
        )
        
        manifest.poses[pose_id] = PoseDefinition(
            id=pose_id,
            base_layer=layer_id,
            compatible_outfits=outfits,
        )
    
    # 添加表情图层
    for expr_id in expressions:
        layer_id = f"face_{expr_id}"
        manifest.layers[layer_id] = LayerDefinition(
            id=layer_id,
            layer_type=LayerType.FACE_COMPOSITE,
            file=f"face/{expr_id}.png",
            z_order=100,
        )
        
        manifest.expressions[expr_id] = ExpressionDefinition(
            id=expr_id,
            composite_layer=layer_id,
        )
    
    # 添加服装
    for outfit_id in outfits:
        layer_id = f"outfit_{outfit_id}"
        manifest.layers[layer_id] = LayerDefinition(
            id=layer_id,
            layer_type=LayerType.OUTFIT,
            file=f"outfit/{outfit_id}/body.png",
            z_order=50,
        )
        
        manifest.outfits[outfit_id] = OutfitDefinition(
            id=outfit_id,
            name=outfit_id.replace('_', ' ').title(),
            layers=[manifest.layers[layer_id]],
            compatible_poses=poses,
        )
    
    # 添加常用特效
    effects = ['blush', 'sweat', 'tears', 'shadow']
    for effect_id in effects:
        manifest.effects[effect_id] = LayerDefinition(
            id=effect_id,
            layer_type=LayerType.EFFECT,
            file=f"effects/{effect_id}.png",
            z_order=150,
        )
    
    # 保存 manifest
    manifest.save(char_dir / 'manifest.json')
    
    return manifest


# ============================================================================
# 批量扫描角色目录
# ============================================================================

def scan_characters_directory(characters_dir: Path) -> Dict[str, CharacterSpriteManifest]:
    """
    扫描角色目录，加载所有角色 manifest
    """
    manifests = {}
    
    if not characters_dir.exists():
        return manifests
    
    for char_dir in characters_dir.iterdir():
        if not char_dir.is_dir():
            continue
        
        manifest_path = char_dir / 'manifest.json'
        if manifest_path.exists():
            try:
                manifest = CharacterSpriteManifest.load(manifest_path)
                manifests[manifest.id] = manifest
            except Exception as e:
                print(f"Warning: Failed to load manifest for {char_dir.name}: {e}")
    
    return manifests
