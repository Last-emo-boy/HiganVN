"""
Asset Pack System - 素材打包系统

功能：
- 素材包 (.hap / HiganVN Asset Pack) 格式
- 加密压缩支持
- 增量更新支持
- 资源索引和快速查找
- 多素材包叠加加载

目录结构规范:
    project/
    ├── assets/
    │   ├── pack.json           # 素材包清单
    │   ├── characters/         # 角色立绘
    │   │   └── {actor_id}/
    │   │       ├── manifest.json
    │   │       ├── base.png        # 基础立绘
    │   │       ├── expressions/    # 表情差分
    │   │       │   ├── normal.png
    │   │       │   ├── happy.png
    │   │       │   └── ...
    │   │       ├── outfits/        # 服装差分
    │   │       │   ├── school_summer/
    │   │       │   │   ├── base.png
    │   │       │   │   └── expressions/
    │   │       │   └── casual/
    │   │       └── poses/          # 姿势/动作
    │   │           ├── sit.png
    │   │           └── ...
    │   ├── backgrounds/        # 背景
    │   │   ├── manifest.json
    │   │   └── {bg_id}.{ext}
    │   ├── cg/                 # CG 事件图
    │   │   ├── manifest.json
    │   │   └── {cg_id}.{ext}
    │   ├── ui/                 # UI 素材
    │   │   ├── textbox/
    │   │   ├── buttons/
    │   │   ├── icons/
    │   │   └── cursors/
    │   ├── audio/
    │   │   ├── bgm/            # 背景音乐
    │   │   ├── se/             # 音效
    │   │   ├── voice/          # 语音
    │   │   │   └── {actor_id}/
    │   │   │       └── {scene_id}/
    │   │   └── ambient/        # 环境音
    │   ├── fonts/              # 字体
    │   ├── video/              # 视频（OP/ED等）
    │   └── scripts/            # 脚本
    │       ├── main.vns
    │       └── chapters/
    └── config/
        ├── game.json           # 游戏配置
        ├── actors.json         # 角色定义
        └── gallery.json        # CG 画廊配置
"""
from __future__ import annotations

import json
import hashlib
import struct
import zlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, BinaryIO, Iterator, Tuple
from enum import Enum, auto
import io
import os


# ============================================================================
# 常量定义
# ============================================================================

PACK_MAGIC = b'HGAP'  # HiGanvn Asset Pack
PACK_VERSION = 1

# 支持的图像格式
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}

# 支持的音频格式
AUDIO_EXTENSIONS = {'.ogg', '.mp3', '.wav', '.flac', '.m4a'}

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mkv'}

# 资源类型
class AssetType(Enum):
    UNKNOWN = 0
    CHARACTER = 1       # 角色立绘
    BACKGROUND = 2      # 背景
    CG = 3              # CG
    UI = 4              # UI 素材
    BGM = 5             # 背景音乐
    SE = 6              # 音效
    VOICE = 7           # 语音
    AMBIENT = 8         # 环境音
    FONT = 9            # 字体
    VIDEO = 10          # 视频
    SCRIPT = 11         # 脚本
    CONFIG = 12         # 配置
    

# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class AssetEntry:
    """素材条目"""
    path: str                           # 相对路径
    asset_type: AssetType               # 资源类型
    size: int = 0                       # 文件大小
    compressed_size: int = 0            # 压缩后大小
    offset: int = 0                     # 在包中的偏移
    hash_md5: str = ""                  # MD5 校验
    encrypted: bool = False             # 是否加密
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['asset_type'] = self.asset_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'AssetEntry':
        d = dict(d)
        d['asset_type'] = AssetType(d.get('asset_type', 0))
        return cls(**d)


@dataclass
class CharacterDefinition:
    """角色定义"""
    id: str                             # 角色ID (文件夹名)
    name: str                           # 显示名称
    aliases: List[str] = field(default_factory=list)  # 别名
    color: Optional[str] = None         # 对话框名字颜色
    voice_id: Optional[str] = None      # 语音文件夹ID
    default_outfit: str = "default"     # 默认服装
    default_expression: str = "normal"  # 默认表情
    
    # 可用资源
    expressions: List[str] = field(default_factory=list)
    outfits: List[str] = field(default_factory=list)
    poses: List[str] = field(default_factory=list)


@dataclass  
class BackgroundDefinition:
    """背景定义"""
    id: str                             # 背景ID
    path: str                           # 文件路径
    display_name: Optional[str] = None  # 显示名称
    tags: List[str] = field(default_factory=list)  # 标签 (室内/室外/白天/夜晚)
    variants: Dict[str, str] = field(default_factory=dict)  # 变体 (day/night/rain)


@dataclass
class CGDefinition:
    """CG 定义"""
    id: str
    path: str
    unlock_condition: Optional[str] = None  # 解锁条件表达式
    gallery_group: Optional[str] = None     # 画廊分组
    variants: List[str] = field(default_factory=list)  # 变体列表


@dataclass
class PackManifest:
    """素材包清单"""
    name: str                           # 包名
    version: str = "1.0.0"              # 版本
    author: str = ""                    # 作者
    description: str = ""               # 描述
    
    # 素材统计
    total_files: int = 0
    total_size: int = 0
    
    # 索引
    characters: Dict[str, CharacterDefinition] = field(default_factory=dict)
    backgrounds: Dict[str, BackgroundDefinition] = field(default_factory=dict)
    cgs: Dict[str, CGDefinition] = field(default_factory=dict)
    
    # 文件索引
    entries: Dict[str, AssetEntry] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        data = {
            'name': self.name,
            'version': self.version,
            'author': self.author,
            'description': self.description,
            'total_files': self.total_files,
            'total_size': self.total_size,
            'characters': {k: asdict(v) for k, v in self.characters.items()},
            'backgrounds': {k: asdict(v) for k, v in self.backgrounds.items()},
            'cgs': {k: asdict(v) for k, v in self.cgs.items()},
            'entries': {k: v.to_dict() for k, v in self.entries.items()},
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PackManifest':
        """从 JSON 反序列化"""
        data = json.loads(json_str)
        manifest = cls(
            name=data.get('name', 'Unknown'),
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            description=data.get('description', ''),
            total_files=data.get('total_files', 0),
            total_size=data.get('total_size', 0),
        )
        
        # 解析角色
        for k, v in data.get('characters', {}).items():
            manifest.characters[k] = CharacterDefinition(**v)
        
        # 解析背景
        for k, v in data.get('backgrounds', {}).items():
            manifest.backgrounds[k] = BackgroundDefinition(**v)
        
        # 解析 CG
        for k, v in data.get('cgs', {}).items():
            manifest.cgs[k] = CGDefinition(**v)
        
        # 解析文件条目
        for k, v in data.get('entries', {}).items():
            manifest.entries[k] = AssetEntry.from_dict(v)
        
        return manifest


# ============================================================================
# 素材包构建器
# ============================================================================

class AssetPackBuilder:
    """
    素材包构建器
    
    扫描目录结构，生成打包清单和素材包文件
    """
    
    def __init__(self, source_dir: Path, pack_name: str = "game"):
        self.source_dir = Path(source_dir)
        self.pack_name = pack_name
        self.manifest = PackManifest(name=pack_name)
        
    def scan(self) -> PackManifest:
        """扫描源目录，构建清单"""
        self._scan_characters()
        self._scan_backgrounds()
        self._scan_cgs()
        self._scan_audio()
        self._scan_ui()
        self._scan_other()
        
        return self.manifest
    
    def _detect_asset_type(self, path: Path) -> AssetType:
        """检测资源类型"""
        rel_path = path.relative_to(self.source_dir).as_posix().lower()
        parts = rel_path.split('/')
        
        if parts[0] in ('characters', 'ch'):
            return AssetType.CHARACTER
        elif parts[0] in ('backgrounds', 'bg'):
            return AssetType.BACKGROUND
        elif parts[0] == 'cg':
            return AssetType.CG
        elif parts[0] == 'ui':
            return AssetType.UI
        elif parts[0] == 'audio':
            if len(parts) > 1:
                if parts[1] == 'bgm':
                    return AssetType.BGM
                elif parts[1] == 'se':
                    return AssetType.SE
                elif parts[1] == 'voice':
                    return AssetType.VOICE
                elif parts[1] == 'ambient':
                    return AssetType.AMBIENT
        elif parts[0] in ('bgm',):
            return AssetType.BGM
        elif parts[0] in ('se',):
            return AssetType.SE
        elif parts[0] in ('voice',):
            return AssetType.VOICE
        elif parts[0] == 'fonts':
            return AssetType.FONT
        elif parts[0] == 'video':
            return AssetType.VIDEO
        elif parts[0] == 'scripts':
            return AssetType.SCRIPT
        elif parts[0] == 'config':
            return AssetType.CONFIG
        
        return AssetType.UNKNOWN
    
    def _add_file(self, path: Path, asset_type: Optional[AssetType] = None) -> AssetEntry:
        """添加文件到清单"""
        rel_path = path.relative_to(self.source_dir).as_posix()
        
        if asset_type is None:
            asset_type = self._detect_asset_type(path)
        
        # 计算文件信息
        stat = path.stat()
        with open(path, 'rb') as f:
            content = f.read()
            hash_md5 = hashlib.md5(content).hexdigest()
        
        entry = AssetEntry(
            path=rel_path,
            asset_type=asset_type,
            size=stat.st_size,
            hash_md5=hash_md5,
        )
        
        self.manifest.entries[rel_path] = entry
        self.manifest.total_files += 1
        self.manifest.total_size += stat.st_size
        
        return entry
    
    def _scan_characters(self) -> None:
        """扫描角色目录"""
        for char_dir_name in ('characters', 'ch'):
            char_root = self.source_dir / char_dir_name
            if not char_root.exists():
                continue
            
            for actor_dir in char_root.iterdir():
                if not actor_dir.is_dir():
                    continue
                
                actor_id = actor_dir.name
                char_def = CharacterDefinition(
                    id=actor_id,
                    name=actor_id,
                )
                
                # 扫描基础立绘
                base_img = actor_dir / 'base.png'
                if base_img.exists():
                    self._add_file(base_img, AssetType.CHARACTER)
                
                # 扫描表情
                expr_dir = actor_dir / 'expressions'
                if expr_dir.exists():
                    for expr_file in expr_dir.iterdir():
                        if expr_file.suffix.lower() in IMAGE_EXTENSIONS:
                            self._add_file(expr_file, AssetType.CHARACTER)
                            char_def.expressions.append(expr_file.stem)
                
                # 兼容旧格式: pose_xxx.png
                for pose_file in actor_dir.glob('pose_*.png'):
                    self._add_file(pose_file, AssetType.CHARACTER)
                    expr_name = pose_file.stem.replace('pose_', '')
                    if expr_name not in char_def.expressions:
                        char_def.expressions.append(expr_name)
                
                # 扫描服装
                outfits_dir = actor_dir / 'outfits'
                if outfits_dir.exists():
                    for outfit_dir in outfits_dir.iterdir():
                        if outfit_dir.is_dir():
                            char_def.outfits.append(outfit_dir.name)
                            for img in outfit_dir.rglob('*'):
                                if img.suffix.lower() in IMAGE_EXTENSIONS:
                                    self._add_file(img, AssetType.CHARACTER)
                
                # 兼容旧格式: outfit_xxx/
                for outfit_dir in actor_dir.iterdir():
                    if outfit_dir.is_dir() and outfit_dir.name.startswith('outfit_'):
                        outfit_name = outfit_dir.name
                        if outfit_name not in char_def.outfits:
                            char_def.outfits.append(outfit_name)
                        for img in outfit_dir.rglob('*'):
                            if img.suffix.lower() in IMAGE_EXTENSIONS:
                                self._add_file(img, AssetType.CHARACTER)
                
                # 扫描姿势/动作
                poses_dir = actor_dir / 'poses'
                if poses_dir.exists():
                    for pose_file in poses_dir.iterdir():
                        if pose_file.suffix.lower() in IMAGE_EXTENSIONS:
                            self._add_file(pose_file, AssetType.CHARACTER)
                            char_def.poses.append(pose_file.stem)
                
                # 兼容旧格式: action_xxx.png
                for action_file in actor_dir.glob('action_*.png'):
                    self._add_file(action_file, AssetType.CHARACTER)
                    pose_name = action_file.stem.replace('action_', '')
                    if pose_name not in char_def.poses:
                        char_def.poses.append(pose_name)
                
                self.manifest.characters[actor_id] = char_def
    
    def _scan_backgrounds(self) -> None:
        """扫描背景目录"""
        for bg_dir_name in ('backgrounds', 'bg'):
            bg_root = self.source_dir / bg_dir_name
            if not bg_root.exists():
                continue
            
            for bg_file in bg_root.rglob('*'):
                if bg_file.is_file() and bg_file.suffix.lower() in IMAGE_EXTENSIONS:
                    self._add_file(bg_file, AssetType.BACKGROUND)
                    
                    bg_id = bg_file.stem
                    self.manifest.backgrounds[bg_id] = BackgroundDefinition(
                        id=bg_id,
                        path=bg_file.relative_to(self.source_dir).as_posix(),
                    )
    
    def _scan_cgs(self) -> None:
        """扫描 CG 目录"""
        cg_root = self.source_dir / 'cg'
        if not cg_root.exists():
            return
        
        for cg_file in cg_root.rglob('*'):
            if cg_file.is_file() and cg_file.suffix.lower() in IMAGE_EXTENSIONS:
                self._add_file(cg_file, AssetType.CG)
                
                cg_id = cg_file.stem
                self.manifest.cgs[cg_id] = CGDefinition(
                    id=cg_id,
                    path=cg_file.relative_to(self.source_dir).as_posix(),
                )
    
    def _scan_audio(self) -> None:
        """扫描音频目录"""
        for audio_dir in ('audio', 'bgm', 'se', 'voice', 'ambient'):
            audio_root = self.source_dir / audio_dir
            if not audio_root.exists():
                continue
            
            for audio_file in audio_root.rglob('*'):
                if audio_file.is_file() and audio_file.suffix.lower() in AUDIO_EXTENSIONS:
                    self._add_file(audio_file)
    
    def _scan_ui(self) -> None:
        """扫描 UI 目录"""
        ui_root = self.source_dir / 'ui'
        if not ui_root.exists():
            return
        
        for ui_file in ui_root.rglob('*'):
            if ui_file.is_file():
                self._add_file(ui_file, AssetType.UI)
    
    def _scan_other(self) -> None:
        """扫描其他目录"""
        for subdir in ('fonts', 'video', 'scripts', 'config'):
            root = self.source_dir / subdir
            if not root.exists():
                continue
            
            for f in root.rglob('*'):
                if f.is_file():
                    self._add_file(f)
    
    def build_pack(
        self,
        output_path: Path,
        compress: bool = True,
        encrypt: bool = False,
        encryption_key: Optional[bytes] = None,
    ) -> Path:
        """
        构建素材包文件
        
        格式:
            [4 bytes] Magic: 'HGAP'
            [4 bytes] Version
            [4 bytes] Manifest length
            [N bytes] Manifest JSON (可选压缩)
            [... ]    Asset data blocks
        """
        output_path = Path(output_path)
        
        with open(output_path, 'wb') as f:
            # 写入头部
            f.write(PACK_MAGIC)
            f.write(struct.pack('<I', PACK_VERSION))
            
            # 预留清单长度位置
            manifest_len_pos = f.tell()
            f.write(struct.pack('<I', 0))
            
            # 先跳过清单，写入资源数据
            data_start = f.tell() + 1024 * 1024  # 预留1MB给清单
            f.seek(data_start)
            
            for rel_path, entry in self.manifest.entries.items():
                file_path = self.source_dir / rel_path
                if not file_path.exists():
                    continue
                
                with open(file_path, 'rb') as src:
                    content = src.read()
                
                # 压缩
                if compress:
                    compressed = zlib.compress(content, level=6)
                    if len(compressed) < len(content):
                        content = compressed
                        entry.compressed_size = len(compressed)
                    else:
                        entry.compressed_size = entry.size
                else:
                    entry.compressed_size = entry.size
                
                # 记录偏移
                entry.offset = f.tell()
                
                # 写入数据
                f.write(content)
            
            # 回写清单
            manifest_json = self.manifest.to_json().encode('utf-8')
            if compress:
                manifest_data = zlib.compress(manifest_json)
            else:
                manifest_data = manifest_json
            
            f.seek(manifest_len_pos)
            f.write(struct.pack('<I', len(manifest_data)))
            f.write(manifest_data)
        
        return output_path


# ============================================================================
# 素材包加载器
# ============================================================================

class AssetPackLoader:
    """
    素材包加载器
    
    支持加载 .hap 文件或直接加载目录
    """
    
    def __init__(self):
        self.packs: List[Tuple[str, PackManifest, Optional[Path]]] = []
        self._cache: Dict[str, bytes] = {}
        self._file_handles: Dict[str, BinaryIO] = {}
    
    def load_directory(self, path: Path, pack_name: str = "game") -> PackManifest:
        """加载目录作为素材包"""
        path = Path(path)
        
        # 检查是否有 pack.json
        pack_json = path / 'pack.json'
        if pack_json.exists():
            manifest = PackManifest.from_json(pack_json.read_text(encoding='utf-8'))
        else:
            # 扫描目录
            builder = AssetPackBuilder(path, pack_name)
            manifest = builder.scan()
        
        self.packs.append((pack_name, manifest, path))
        return manifest
    
    def load_pack_file(self, path: Path) -> PackManifest:
        """加载 .hap 素材包文件"""
        path = Path(path)
        
        with open(path, 'rb') as f:
            # 读取头部
            magic = f.read(4)
            if magic != PACK_MAGIC:
                raise ValueError(f"Invalid pack file: {path}")
            
            version = struct.unpack('<I', f.read(4))[0]
            manifest_len = struct.unpack('<I', f.read(4))[0]
            
            # 读取清单
            manifest_data = f.read(manifest_len)
            try:
                manifest_json = zlib.decompress(manifest_data).decode('utf-8')
            except zlib.error:
                manifest_json = manifest_data.decode('utf-8')
            
            manifest = PackManifest.from_json(manifest_json)
        
        # 保持文件句柄打开
        self._file_handles[path.name] = open(path, 'rb')
        self.packs.append((manifest.name, manifest, path))
        
        return manifest
    
    def get_asset(self, rel_path: str) -> Optional[bytes]:
        """获取资源数据"""
        # 检查缓存
        if rel_path in self._cache:
            return self._cache[rel_path]
        
        # 搜索所有包（后加载的优先）
        for pack_name, manifest, pack_path in reversed(self.packs):
            if rel_path not in manifest.entries:
                continue
            
            entry = manifest.entries[rel_path]
            
            if pack_path and pack_path.is_dir():
                # 从目录加载
                file_path = pack_path / rel_path
                if file_path.exists():
                    data = file_path.read_bytes()
                    self._cache[rel_path] = data
                    return data
            elif pack_path and pack_path.is_file():
                # 从包文件加载
                handle = self._file_handles.get(pack_path.name)
                if handle:
                    handle.seek(entry.offset)
                    compressed = handle.read(entry.compressed_size)
                    
                    if entry.compressed_size < entry.size:
                        data = zlib.decompress(compressed)
                    else:
                        data = compressed
                    
                    self._cache[rel_path] = data
                    return data
        
        return None
    
    def get_asset_path(self, rel_path: str) -> Optional[Path]:
        """获取资源的实际路径（仅目录模式）"""
        for pack_name, manifest, pack_path in reversed(self.packs):
            if pack_path and pack_path.is_dir():
                file_path = pack_path / rel_path
                if file_path.exists():
                    return file_path
        return None
    
    def resolve_character_image(
        self,
        actor_id: str,
        expression: Optional[str] = None,
        outfit: Optional[str] = None,
        pose: Optional[str] = None,
    ) -> Optional[str]:
        """
        解析角色立绘路径
        
        Args:
            actor_id: 角色ID
            expression: 表情
            outfit: 服装
            pose: 姿势/动作
        
        Returns:
            资源相对路径
        """
        for pack_name, manifest, pack_path in reversed(self.packs):
            if actor_id not in manifest.characters:
                continue
            
            char_def = manifest.characters[actor_id]
            
            # 构建路径
            # 新格式: characters/{actor}/[outfits/{outfit}/][expressions/{expr}.png | base.png]
            # 旧格式: ch/{actor}/[outfit_{outfit}/][pose_{expr}.png | base.png]
            
            candidates = []
            
            # 检查服装
            if outfit:
                if outfit.startswith('outfit_'):
                    outfit_name = outfit
                else:
                    outfit_name = outfit
                
                base_paths = [
                    f"characters/{actor_id}/outfits/{outfit_name}",
                    f"ch/{actor_id}/outfits/{outfit_name}",
                    f"ch/{actor_id}/{outfit_name}",
                    f"ch/{actor_id}/outfit_{outfit_name}",
                ]
            else:
                base_paths = [
                    f"characters/{actor_id}",
                    f"ch/{actor_id}",
                ]
            
            # 添加表情/姿势候选
            for base in base_paths:
                if expression:
                    candidates.extend([
                        f"{base}/expressions/{expression}.png",
                        f"{base}/pose_{expression}.png",
                    ])
                if pose:
                    candidates.extend([
                        f"{base}/poses/{pose}.png",
                        f"{base}/action_{pose}.png",
                    ])
                candidates.append(f"{base}/base.png")
            
            # 查找存在的路径
            for cand in candidates:
                if cand in manifest.entries:
                    return cand
        
        return None
    
    def resolve_background(self, bg_id: str, variant: Optional[str] = None) -> Optional[str]:
        """解析背景路径"""
        for pack_name, manifest, pack_path in reversed(self.packs):
            # 直接匹配
            if bg_id in manifest.backgrounds:
                return manifest.backgrounds[bg_id].path
            
            # 尝试常见路径
            for ext in IMAGE_EXTENSIONS:
                for prefix in ('backgrounds/', 'bg/'):
                    path = f"{prefix}{bg_id}{ext}"
                    if path in manifest.entries:
                        return path
        
        return None
    
    def resolve_audio(
        self,
        audio_type: AssetType,
        audio_id: str,
    ) -> Optional[str]:
        """解析音频路径"""
        type_dirs = {
            AssetType.BGM: ['audio/bgm', 'bgm'],
            AssetType.SE: ['audio/se', 'se'],
            AssetType.VOICE: ['audio/voice', 'voice'],
            AssetType.AMBIENT: ['audio/ambient', 'ambient'],
        }
        
        dirs = type_dirs.get(audio_type, [])
        
        for pack_name, manifest, pack_path in reversed(self.packs):
            for dir_prefix in dirs:
                for ext in AUDIO_EXTENSIONS:
                    path = f"{dir_prefix}/{audio_id}{ext}"
                    if path in manifest.entries:
                        return path
                    
                    # 可能已经包含扩展名
                    if audio_id.endswith(ext):
                        path = f"{dir_prefix}/{audio_id}"
                        if path in manifest.entries:
                            return path
        
        return None
    
    def list_characters(self) -> Dict[str, CharacterDefinition]:
        """列出所有角色"""
        result: Dict[str, CharacterDefinition] = {}
        for pack_name, manifest, pack_path in self.packs:
            result.update(manifest.characters)
        return result
    
    def list_backgrounds(self) -> Dict[str, BackgroundDefinition]:
        """列出所有背景"""
        result: Dict[str, BackgroundDefinition] = {}
        for pack_name, manifest, pack_path in self.packs:
            result.update(manifest.backgrounds)
        return result
    
    def list_cgs(self) -> Dict[str, CGDefinition]:
        """列出所有 CG"""
        result: Dict[str, CGDefinition] = {}
        for pack_name, manifest, pack_path in self.packs:
            result.update(manifest.cgs)
        return result
    
    def close(self) -> None:
        """关闭所有文件句柄"""
        for handle in self._file_handles.values():
            try:
                handle.close()
            except Exception:
                pass
        self._file_handles.clear()
        self._cache.clear()


# ============================================================================
# 全局实例和便捷函数
# ============================================================================

_asset_loader: Optional[AssetPackLoader] = None


def get_asset_loader() -> Optional[AssetPackLoader]:
    """获取全局素材加载器"""
    return _asset_loader


def init_asset_loader() -> AssetPackLoader:
    """初始化全局素材加载器"""
    global _asset_loader
    if _asset_loader is None:
        _asset_loader = AssetPackLoader()
    return _asset_loader


def load_assets(path: Path, pack_name: str = "game") -> PackManifest:
    """加载素材包或目录"""
    loader = init_asset_loader()
    path = Path(path)
    
    if path.is_dir():
        return loader.load_directory(path, pack_name)
    elif path.suffix == '.hap':
        return loader.load_pack_file(path)
    else:
        raise ValueError(f"Unsupported asset source: {path}")
