"""
Patch Archive System - 分包加密系统

功能：
- 不同类型资源分开打包（图像/音频/语音/脚本）
- 可选加密保护
- 支持 DLC/补丁包叠加
- 版本管理和增量更新

分包结构：
    game/
    ├── data/
    │   ├── patch1.hgp         # 基础图形资源
    │   ├── patch2.hgp         # 语音资源
    │   ├── patch3.hgp         # BGM/SE
    │   ├── patch4.hgp         # 脚本/文本
    │   └── dlc01.hgp          # DLC 内容
    ├── game.exe
    └── patches.json           # 分包索引
"""
from __future__ import annotations

import json
import hashlib
import struct
import zlib
import io
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, BinaryIO, Iterator, Tuple, Callable
from enum import Enum, auto
import secrets


# ============================================================================
# 常量
# ============================================================================

PATCH_MAGIC = b'HGPK'  # HiGanvn Patch pacK
PATCH_VERSION = 1

# 加密相关
BLOCK_SIZE = 16
KEY_SIZE = 32  # AES-256


# ============================================================================
# 分包类型
# ============================================================================

class PatchType(Enum):
    """分包类型"""
    GRAPHICS = "graphics"       # 图形资源（立绘/背景/CG/UI）
    VOICE = "voice"             # 语音
    AUDIO = "audio"             # BGM/SE/环境音
    SCRIPT = "script"           # 脚本/文本
    VIDEO = "video"             # 视频（OP/ED）
    SYSTEM = "system"           # 系统资源（字体/配置）
    DLC = "dlc"                 # DLC 内容
    PATCH = "patch"             # 更新补丁


class CompressionType(Enum):
    """压缩类型"""
    NONE = 0
    ZLIB = 1
    LZ4 = 2  # 需要额外依赖


class EncryptionType(Enum):
    """加密类型"""
    NONE = 0
    XOR = 1         # 简单 XOR（轻度保护）
    AES = 2         # AES-256（需要 pycryptodome）
    CUSTOM = 3      # 自定义加密


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class PatchEntry:
    """分包内文件条目"""
    path: str                           # 相对路径
    size: int                           # 原始大小
    compressed_size: int                # 压缩后大小
    offset: int                         # 在文件中的偏移
    hash_md5: str                       # MD5 校验
    compression: CompressionType = CompressionType.ZLIB
    encrypted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': self.path,
            'size': self.size,
            'compressed_size': self.compressed_size,
            'offset': self.offset,
            'hash_md5': self.hash_md5,
            'compression': self.compression.value,
            'encrypted': self.encrypted,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'PatchEntry':
        return cls(
            path=d['path'],
            size=d['size'],
            compressed_size=d['compressed_size'],
            offset=d['offset'],
            hash_md5=d['hash_md5'],
            compression=CompressionType(d.get('compression', 1)),
            encrypted=d.get('encrypted', False),
        )


@dataclass
class PatchInfo:
    """分包信息"""
    name: str                           # 包名（patch1, dlc01）
    patch_type: PatchType               # 包类型
    version: str = "1.0.0"              # 版本
    priority: int = 0                   # 优先级（高优先覆盖低优先）
    description: str = ""
    author: str = ""
    
    # 依赖
    requires: List[str] = field(default_factory=list)  # 依赖的其他包
    
    # 加密
    encryption: EncryptionType = EncryptionType.NONE
    encryption_check: str = ""          # 加密校验（验证密钥）
    
    # 统计
    total_files: int = 0
    total_size: int = 0
    compressed_size: int = 0
    
    # 文件索引
    entries: Dict[str, PatchEntry] = field(default_factory=dict)
    
    def to_json(self) -> str:
        data = {
            'name': self.name,
            'patch_type': self.patch_type.value,
            'version': self.version,
            'priority': self.priority,
            'description': self.description,
            'author': self.author,
            'requires': self.requires,
            'encryption': self.encryption.value,
            'encryption_check': self.encryption_check,
            'total_files': self.total_files,
            'total_size': self.total_size,
            'compressed_size': self.compressed_size,
            'entries': {k: v.to_dict() for k, v in self.entries.items()},
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PatchInfo':
        data = json.loads(json_str)
        info = cls(
            name=data['name'],
            patch_type=PatchType(data.get('patch_type', 'graphics')),
            version=data.get('version', '1.0.0'),
            priority=data.get('priority', 0),
            description=data.get('description', ''),
            author=data.get('author', ''),
            requires=data.get('requires', []),
            encryption=EncryptionType(data.get('encryption', 0)),
            encryption_check=data.get('encryption_check', ''),
            total_files=data.get('total_files', 0),
            total_size=data.get('total_size', 0),
            compressed_size=data.get('compressed_size', 0),
        )
        
        for k, v in data.get('entries', {}).items():
            info.entries[k] = PatchEntry.from_dict(v)
        
        return info


# ============================================================================
# 简单 XOR 加密
# ============================================================================

def xor_encrypt(data: bytes, key: bytes) -> bytes:
    """简单 XOR 加密"""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))

def xor_decrypt(data: bytes, key: bytes) -> bytes:
    """XOR 解密（与加密相同）"""
    return xor_encrypt(data, key)


def derive_key(password: str, salt: bytes = b'HiganVN_Salt') -> bytes:
    """从密码派生密钥"""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, KEY_SIZE)


def generate_encryption_check(key: bytes) -> str:
    """生成加密校验值"""
    check_data = b'HiganVN_EncryptionCheck'
    encrypted = xor_encrypt(check_data, key)
    return hashlib.md5(encrypted).hexdigest()


def verify_encryption_key(key: bytes, check: str) -> bool:
    """验证加密密钥"""
    return generate_encryption_check(key) == check


# ============================================================================
# 分包构建器
# ============================================================================

class PatchBuilder:
    """
    分包构建器
    
    将资源文件打包成加密分包
    """
    
    def __init__(
        self,
        name: str,
        patch_type: PatchType,
        output_path: Path,
        password: Optional[str] = None,
        compression: CompressionType = CompressionType.ZLIB,
    ):
        self.name = name
        self.patch_type = patch_type
        self.output_path = output_path
        self.compression = compression
        
        # 加密设置
        self.encryption = EncryptionType.NONE
        self.key: Optional[bytes] = None
        if password:
            self.encryption = EncryptionType.XOR
            self.key = derive_key(password)
        
        # 收集的文件
        self.files: List[Tuple[Path, str]] = []  # (源路径, 包内路径)
        
        # 信息
        self.info = PatchInfo(
            name=name,
            patch_type=patch_type,
            encryption=self.encryption,
        )
        if self.key:
            self.info.encryption_check = generate_encryption_check(self.key)
    
    def add_file(self, source_path: Path, archive_path: str):
        """添加单个文件"""
        self.files.append((source_path, archive_path))
    
    def add_directory(self, source_dir: Path, prefix: str = ""):
        """递归添加目录"""
        for path in source_dir.rglob('*'):
            if path.is_file():
                rel_path = path.relative_to(source_dir)
                archive_path = f"{prefix}/{rel_path}".lstrip('/') if prefix else str(rel_path)
                archive_path = archive_path.replace('\\', '/')
                self.files.append((path, archive_path))
    
    def build(self, version: str = "1.0.0", author: str = "", description: str = "") -> PatchInfo:
        """
        构建分包
        
        文件格式：
        [Header: 8 bytes]
            Magic: 4 bytes (HGPK)
            Version: 2 bytes
            Flags: 2 bytes
        [Index Offset: 8 bytes]
        [Data Section]
            File 1 data
            File 2 data
            ...
        [Index Section]
            JSON index (compressed)
        """
        self.info.version = version
        self.info.author = author
        self.info.description = description
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'wb') as f:
            # 写入头部
            f.write(PATCH_MAGIC)
            f.write(struct.pack('<H', PATCH_VERSION))
            flags = self.encryption.value
            f.write(struct.pack('<H', flags))
            
            # 预留索引偏移位置
            index_offset_pos = f.tell()
            f.write(struct.pack('<Q', 0))
            
            # 写入文件数据
            for source_path, archive_path in self.files:
                self._write_file(f, source_path, archive_path)
            
            # 记录索引位置
            index_offset = f.tell()
            
            # 写入索引
            index_json = self.info.to_json()
            index_data = index_json.encode('utf-8')
            compressed_index = zlib.compress(index_data, 9)
            f.write(compressed_index)
            
            # 回填索引偏移
            f.seek(index_offset_pos)
            f.write(struct.pack('<Q', index_offset))
        
        return self.info
    
    def _write_file(self, f: BinaryIO, source_path: Path, archive_path: str):
        """写入单个文件"""
        data = source_path.read_bytes()
        original_size = len(data)
        
        # 计算 MD5
        md5_hash = hashlib.md5(data).hexdigest()
        
        # 压缩
        if self.compression == CompressionType.ZLIB:
            compressed_data = zlib.compress(data, 6)
        else:
            compressed_data = data
        
        # 加密
        encrypted = self.encryption != EncryptionType.NONE
        if encrypted and self.key:
            compressed_data = xor_encrypt(compressed_data, self.key)
        
        # 记录偏移
        offset = f.tell()
        
        # 写入数据
        f.write(compressed_data)
        
        # 记录条目
        entry = PatchEntry(
            path=archive_path,
            size=original_size,
            compressed_size=len(compressed_data),
            offset=offset,
            hash_md5=md5_hash,
            compression=self.compression,
            encrypted=encrypted,
        )
        self.info.entries[archive_path] = entry
        self.info.total_files += 1
        self.info.total_size += original_size
        self.info.compressed_size += len(compressed_data)


# ============================================================================
# 分包加载器
# ============================================================================

class PatchLoader:
    """
    分包加载器
    
    加载和读取分包内的资源
    """
    
    def __init__(self, patch_path: Path, password: Optional[str] = None):
        self.patch_path = patch_path
        self.key: Optional[bytes] = None
        if password:
            self.key = derive_key(password)
        
        self.info: Optional[PatchInfo] = None
        self._file: Optional[BinaryIO] = None
        
        self._load_index()
    
    def _load_index(self):
        """加载索引"""
        with open(self.patch_path, 'rb') as f:
            # 读取头部
            magic = f.read(4)
            if magic != PATCH_MAGIC:
                raise ValueError(f"Invalid patch file: {self.patch_path}")
            
            version = struct.unpack('<H', f.read(2))[0]
            flags = struct.unpack('<H', f.read(2))[0]
            
            # 读取索引偏移
            index_offset = struct.unpack('<Q', f.read(8))[0]
            
            # 读取索引
            f.seek(index_offset)
            compressed_index = f.read()
            index_data = zlib.decompress(compressed_index)
            index_json = index_data.decode('utf-8')
            
            self.info = PatchInfo.from_json(index_json)
        
        # 验证密钥
        if self.info.encryption != EncryptionType.NONE:
            if not self.key:
                raise ValueError("Patch is encrypted but no password provided")
            if not verify_encryption_key(self.key, self.info.encryption_check):
                raise ValueError("Invalid encryption password")
    
    def open(self):
        """打开文件句柄"""
        if self._file is None:
            self._file = open(self.patch_path, 'rb')
    
    def close(self):
        """关闭文件句柄"""
        if self._file:
            self._file.close()
            self._file = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def list_files(self) -> List[str]:
        """列出所有文件"""
        return list(self.info.entries.keys()) if self.info else []
    
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return path in self.info.entries if self.info else False
    
    def read(self, path: str) -> bytes:
        """读取文件内容"""
        if not self.info:
            raise RuntimeError("Patch not loaded")
        
        entry = self.info.entries.get(path)
        if not entry:
            raise FileNotFoundError(f"File not found in patch: {path}")
        
        # 确保文件打开
        was_closed = self._file is None
        if was_closed:
            self.open()
        
        try:
            self._file.seek(entry.offset)
            data = self._file.read(entry.compressed_size)
            
            # 解密
            if entry.encrypted and self.key:
                data = xor_decrypt(data, self.key)
            
            # 解压
            if entry.compression == CompressionType.ZLIB:
                data = zlib.decompress(data)
            
            # 验证
            if hashlib.md5(data).hexdigest() != entry.hash_md5:
                raise ValueError(f"Data corruption detected: {path}")
            
            return data
        finally:
            if was_closed:
                self.close()
    
    def extract(self, path: str, output_path: Path):
        """提取文件到磁盘"""
        data = self.read(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
    
    def extract_all(self, output_dir: Path):
        """提取所有文件"""
        for path in self.list_files():
            output_path = output_dir / path
            self.extract(path, output_path)


# ============================================================================
# 多分包管理器
# ============================================================================

@dataclass
class PatchRegistryEntry:
    """分包注册条目"""
    name: str
    path: str
    patch_type: str
    version: str
    priority: int
    enabled: bool = True


class PatchRegistry:
    """
    分包注册表
    
    管理多个分包的加载顺序和文件查找
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.patches: Dict[str, PatchLoader] = {}
        self.registry: List[PatchRegistryEntry] = []
        self.file_index: Dict[str, str] = {}  # path -> patch_name
        
        self._load_registry()
    
    def _load_registry(self):
        """加载分包注册表"""
        registry_path = self.data_dir / 'patches.json'
        if registry_path.exists():
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for entry_data in data.get('patches', []):
                self.registry.append(PatchRegistryEntry(**entry_data))
        else:
            # 自动扫描
            self._scan_patches()
    
    def _scan_patches(self):
        """扫描分包目录"""
        if not self.data_dir.exists():
            return
        
        for path in self.data_dir.glob('*.hgp'):
            try:
                loader = PatchLoader(path)
                if loader.info:
                    self.registry.append(PatchRegistryEntry(
                        name=loader.info.name,
                        path=path.name,
                        patch_type=loader.info.patch_type.value,
                        version=loader.info.version,
                        priority=loader.info.priority,
                    ))
            except Exception as e:
                print(f"Warning: Failed to scan patch {path}: {e}")
        
        # 按优先级排序
        self.registry.sort(key=lambda x: x.priority, reverse=True)
    
    def save_registry(self):
        """保存注册表"""
        registry_path = self.data_dir / 'patches.json'
        data = {
            'patches': [asdict(e) for e in self.registry]
        }
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_patch(self, name: str, password: Optional[str] = None) -> PatchLoader:
        """加载指定分包"""
        if name in self.patches:
            return self.patches[name]
        
        entry = next((e for e in self.registry if e.name == name), None)
        if not entry:
            raise ValueError(f"Patch not found: {name}")
        
        patch_path = self.data_dir / entry.path
        loader = PatchLoader(patch_path, password)
        self.patches[name] = loader
        
        # 更新文件索引
        for path in loader.list_files():
            # 高优先级覆盖低优先级
            if path not in self.file_index:
                self.file_index[path] = name
        
        return loader
    
    def load_all(self, passwords: Dict[str, str] = None):
        """加载所有分包"""
        passwords = passwords or {}
        for entry in self.registry:
            if entry.enabled:
                try:
                    self.load_patch(entry.name, passwords.get(entry.name))
                except Exception as e:
                    print(f"Warning: Failed to load patch {entry.name}: {e}")
    
    def read(self, path: str) -> bytes:
        """从合适的分包读取文件"""
        patch_name = self.file_index.get(path)
        if not patch_name:
            raise FileNotFoundError(f"File not found in any patch: {path}")
        
        loader = self.patches.get(patch_name)
        if not loader:
            raise RuntimeError(f"Patch not loaded: {patch_name}")
        
        return loader.read(path)
    
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return path in self.file_index
    
    def close_all(self):
        """关闭所有分包"""
        for loader in self.patches.values():
            loader.close()
        self.patches.clear()


# ============================================================================
# 便捷函数
# ============================================================================

def create_graphics_patch(
    source_dir: Path,
    output_path: Path,
    password: Optional[str] = None,
    version: str = "1.0.0",
) -> PatchInfo:
    """创建图形资源分包"""
    builder = PatchBuilder(
        name="graphics",
        patch_type=PatchType.GRAPHICS,
        output_path=output_path,
        password=password,
    )
    builder.add_directory(source_dir)
    return builder.build(version=version)


def create_voice_patch(
    source_dir: Path,
    output_path: Path,
    password: Optional[str] = None,
    version: str = "1.0.0",
) -> PatchInfo:
    """创建语音分包"""
    builder = PatchBuilder(
        name="voice",
        patch_type=PatchType.VOICE,
        output_path=output_path,
        password=password,
        compression=CompressionType.NONE,  # 音频一般已压缩
    )
    builder.add_directory(source_dir)
    return builder.build(version=version)


def create_audio_patch(
    source_dir: Path,
    output_path: Path,
    password: Optional[str] = None,
    version: str = "1.0.0",
) -> PatchInfo:
    """创建音频分包（BGM/SE）"""
    builder = PatchBuilder(
        name="audio",
        patch_type=PatchType.AUDIO,
        output_path=output_path,
        password=password,
        compression=CompressionType.NONE,
    )
    builder.add_directory(source_dir)
    return builder.build(version=version)


def create_script_patch(
    source_dir: Path,
    output_path: Path,
    password: Optional[str] = None,
    version: str = "1.0.0",
) -> PatchInfo:
    """创建脚本分包"""
    builder = PatchBuilder(
        name="script",
        patch_type=PatchType.SCRIPT,
        output_path=output_path,
        password=password,
    )
    builder.add_directory(source_dir)
    return builder.build(version=version)


# ============================================================================
# 完整游戏打包
# ============================================================================

def package_game(
    project_dir: Path,
    output_dir: Path,
    password: Optional[str] = None,
    version: str = "1.0.0",
) -> Dict[str, PatchInfo]:
    """
    打包完整游戏
    
    将项目目录打包成多个分包
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    patches = {}
    
    # 图形资源
    graphics_sources = ['characters', 'backgrounds', 'cg', 'ui']
    graphics_builder = PatchBuilder(
        name="patch1",
        patch_type=PatchType.GRAPHICS,
        output_path=output_dir / "patch1.hgp",
        password=password,
    )
    for src in graphics_sources:
        src_dir = project_dir / 'assets' / src
        if src_dir.exists():
            graphics_builder.add_directory(src_dir, src)
    if graphics_builder.files:
        patches['patch1'] = graphics_builder.build(version=version)
    
    # 语音
    voice_dir = project_dir / 'assets' / 'audio' / 'voice'
    if voice_dir.exists():
        patches['patch2'] = create_voice_patch(
            voice_dir,
            output_dir / "patch2.hgp",
            password,
            version,
        )
    
    # BGM/SE
    audio_builder = PatchBuilder(
        name="patch3",
        patch_type=PatchType.AUDIO,
        output_path=output_dir / "patch3.hgp",
        password=password,
        compression=CompressionType.NONE,
    )
    for src in ['bgm', 'se', 'ambient']:
        src_dir = project_dir / 'assets' / 'audio' / src
        if src_dir.exists():
            audio_builder.add_directory(src_dir, src)
    if audio_builder.files:
        patches['patch3'] = audio_builder.build(version=version)
    
    # 脚本
    scripts_dir = project_dir / 'scripts'
    if scripts_dir.exists():
        patches['patch4'] = create_script_patch(
            scripts_dir,
            output_dir / "patch4.hgp",
            password,
            version,
        )
    
    # 创建注册表
    registry_data = {
        'game_version': version,
        'patches': [
            {
                'name': name,
                'path': f"{name}.hgp",
                'patch_type': info.patch_type.value,
                'version': info.version,
                'priority': i,
                'enabled': True,
            }
            for i, (name, info) in enumerate(patches.items())
        ]
    }
    
    with open(output_dir / 'patches.json', 'w', encoding='utf-8') as f:
        json.dump(registry_data, f, ensure_ascii=False, indent=2)
    
    return patches
