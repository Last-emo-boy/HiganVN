"""
Game Configuration System - 游戏配置系统

统一管理游戏元数据、角色定义、画廊配置等
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class GameMetadata:
    """游戏元数据"""
    title: str = "Untitled Game"
    title_jp: Optional[str] = None          # 日文标题
    title_en: Optional[str] = None          # 英文标题
    version: str = "1.0.0"
    author: str = ""
    developer: str = ""
    publisher: str = ""
    release_date: Optional[str] = None
    description: str = ""
    
    # 分辨率
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    resizable: bool = True
    
    # 入口脚本
    main_script: str = "scripts/main.vns"
    start_label: str = "start"
    
    # 功能开关
    enable_gallery: bool = True
    enable_backlog: bool = True
    enable_skip: bool = True
    enable_auto: bool = True
    enable_save: bool = True
    
    # 存档槽位
    save_slots: int = 20
    quicksave_slots: int = 3
    autosave_enabled: bool = True


@dataclass
class ActorDefinition:
    """角色定义（完整版）"""
    id: str                                 # 内部ID（文件夹名）
    name: str                               # 显示名称
    name_jp: Optional[str] = None           # 日文名
    name_en: Optional[str] = None           # 英文名
    
    # 别名（脚本中可用的其他名称）
    aliases: List[str] = field(default_factory=list)
    
    # 显示设置
    name_color: str = "#FFFFFF"             # 名字颜色
    text_color: Optional[str] = None        # 对话文字颜色（可选）
    
    # 语音设置
    voice_folder: Optional[str] = None      # 语音文件夹
    voice_enabled: bool = True
    
    # 默认值
    default_outfit: str = "default"
    default_expression: str = "normal"
    default_position: str = "center"        # left/center/right
    
    # 立绘设置
    base_scale: float = 1.0                 # 基础缩放
    base_offset_y: int = 0                  # Y轴偏移
    
    # 角色类型
    is_protagonist: bool = False            # 是否主角
    is_narrator: bool = False               # 是否旁白
    is_hidden: bool = False                 # 是否隐藏（系统角色）


@dataclass
class GalleryCategory:
    """画廊分类"""
    id: str
    name: str
    name_jp: Optional[str] = None
    description: str = ""
    items: List[str] = field(default_factory=list)  # CG/背景 ID 列表


@dataclass
class GalleryConfig:
    """画廊配置"""
    enabled: bool = True
    categories: List[GalleryCategory] = field(default_factory=list)
    unlock_all_in_debug: bool = True
    show_locked_as_silhouette: bool = True
    columns: int = 4
    thumbnail_size: Tuple[int, int] = (200, 150)


@dataclass
class GameConfig:
    """完整游戏配置"""
    metadata: GameMetadata = field(default_factory=GameMetadata)
    actors: Dict[str, ActorDefinition] = field(default_factory=dict)
    gallery: GalleryConfig = field(default_factory=GalleryConfig)
    
    # 额外配置
    ui_config: Dict[str, Any] = field(default_factory=dict)
    audio_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        data = {
            'metadata': asdict(self.metadata),
            'actors': {k: asdict(v) for k, v in self.actors.items()},
            'gallery': asdict(self.gallery),
            'ui_config': self.ui_config,
            'audio_config': self.audio_config,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def save(self, path: Path) -> None:
        """保存到文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding='utf-8')
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GameConfig':
        """从 JSON 反序列化"""
        data = json.loads(json_str)
        
        config = cls()
        
        # 元数据
        if 'metadata' in data:
            config.metadata = GameMetadata(**data['metadata'])
        
        # 角色
        for k, v in data.get('actors', {}).items():
            config.actors[k] = ActorDefinition(**v)
        
        # 画廊
        if 'gallery' in data:
            gdata = data['gallery']
            config.gallery = GalleryConfig(
                enabled=gdata.get('enabled', True),
                unlock_all_in_debug=gdata.get('unlock_all_in_debug', True),
                show_locked_as_silhouette=gdata.get('show_locked_as_silhouette', True),
                columns=gdata.get('columns', 4),
                thumbnail_size=tuple(gdata.get('thumbnail_size', [200, 150])),
            )
            for cat in gdata.get('categories', []):
                config.gallery.categories.append(GalleryCategory(**cat))
        
        config.ui_config = data.get('ui_config', {})
        config.audio_config = data.get('audio_config', {})
        
        return config
    
    @classmethod
    def load(cls, path: Path) -> 'GameConfig':
        """从文件加载"""
        path = Path(path)
        return cls.from_json(path.read_text(encoding='utf-8'))
    
    @classmethod
    def load_from_directory(cls, config_dir: Path) -> 'GameConfig':
        """从目录加载（兼容多文件格式）"""
        config_dir = Path(config_dir)
        config = cls()
        
        # 尝试加载单一配置文件
        game_json = config_dir / 'game.json'
        if game_json.exists():
            return cls.load(game_json)
        
        # 分别加载各配置文件
        
        # 元数据
        meta_json = config_dir / 'metadata.json'
        if meta_json.exists():
            config.metadata = GameMetadata(**json.loads(meta_json.read_text(encoding='utf-8')))
        
        # 角色 - 兼容旧格式
        actors_json = config_dir / 'actors.json'
        actors_map_json = config_dir / 'actors_map.json'
        
        if actors_json.exists():
            data = json.loads(actors_json.read_text(encoding='utf-8'))
            for k, v in data.items():
                if isinstance(v, dict):
                    config.actors[k] = ActorDefinition(**v)
                else:
                    # 简单映射格式
                    config.actors[k] = ActorDefinition(id=str(v), name=k)
        elif actors_map_json.exists():
            # 旧格式：{ "显示名": "文件夹名" }
            data = json.loads(actors_map_json.read_text(encoding='utf-8'))
            for display_name, folder_name in data.items():
                config.actors[folder_name] = ActorDefinition(
                    id=folder_name,
                    name=display_name,
                )
        
        # 画廊
        gallery_json = config_dir / 'gallery.json'
        if gallery_json.exists():
            gdata = json.loads(gallery_json.read_text(encoding='utf-8'))
            config.gallery = GalleryConfig(**gdata)
        
        # UI 配置
        ui_json = config_dir / 'ui.json'
        if ui_json.exists():
            config.ui_config = json.loads(ui_json.read_text(encoding='utf-8'))
        
        return config
    
    def get_actor_by_name(self, name: str) -> Optional[ActorDefinition]:
        """通过名称查找角色"""
        # 直接匹配 ID
        if name in self.actors:
            return self.actors[name]
        
        # 匹配显示名称
        for actor in self.actors.values():
            if actor.name == name:
                return actor
            if name in actor.aliases:
                return actor
        
        return None
    
    def resolve_actor_folder(self, name: str) -> str:
        """解析角色文件夹名"""
        actor = self.get_actor_by_name(name)
        if actor:
            return actor.id
        return name


# ============================================================================
# 全局实例
# ============================================================================

_game_config: Optional[GameConfig] = None


def get_game_config() -> Optional[GameConfig]:
    """获取全局游戏配置"""
    return _game_config


def load_game_config(path: Path) -> GameConfig:
    """加载游戏配置"""
    global _game_config
    path = Path(path)
    
    if path.is_dir():
        _game_config = GameConfig.load_from_directory(path)
    else:
        _game_config = GameConfig.load(path)
    
    return _game_config


def create_default_config(
    title: str = "My Visual Novel",
    author: str = "",
) -> GameConfig:
    """创建默认配置"""
    config = GameConfig()
    config.metadata.title = title
    config.metadata.author = author
    
    # 添加默认系统角色
    config.actors['narrator'] = ActorDefinition(
        id='narrator',
        name='',
        is_narrator=True,
        is_hidden=True,
    )
    
    return config
