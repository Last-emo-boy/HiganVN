"""
HiganVN Packaging Module
专业的素材打包与项目管理系统

包含:
- asset_pack: 素材包系统 (.hap 格式)
- game_config: 游戏配置管理
- project_template: 项目模板生成
- layered_sprite: 差分立绘合成系统
- patch_archive: 分包加密系统
- asset_scan: 素材扫描工具
- bootstrap: 初始化工具
"""

from .asset_pack import (
    AssetType,
    AssetEntry,
    PackManifest,
    CharacterDefinition as AssetCharacterDefinition,
    BackgroundDefinition,
    CGDefinition,
    AssetPackBuilder,
    AssetPackLoader,
)

from .game_config import (
    GameMetadata,
    ActorDefinition,
    GalleryCategory,
    GalleryConfig,
    GameConfig,
)

from .project_template import (
    create_project,
    create_character,
    migrate_legacy_project,
    validate_project,
)

from .layered_sprite import (
    LayerType,
    BlendMode,
    LayerDefinition,
    PoseDefinition,
    ExpressionDefinition,
    OutfitDefinition,
    CharacterSpriteManifest,
    SpriteState,
    SpriteCompositor,
    create_character_template,
    scan_characters_directory,
)

from .patch_archive import (
    PatchType,
    CompressionType,
    EncryptionType,
    PatchEntry,
    PatchInfo,
    PatchBuilder,
    PatchLoader,
    PatchRegistry,
    create_graphics_patch,
    create_voice_patch,
    create_audio_patch,
    create_script_patch,
    package_game,
)

__all__ = [
    # Asset Pack
    'AssetType',
    'AssetEntry', 
    'PackManifest',
    'AssetCharacterDefinition',
    'BackgroundDefinition',
    'CGDefinition',
    'AssetPackBuilder',
    'AssetPackLoader',
    # Game Config
    'GameMetadata',
    'ActorDefinition',
    'GalleryCategory',
    'GalleryConfig',
    'GameConfig',
    # Project Template
    'create_project',
    'create_character',
    'migrate_legacy_project',
    'validate_project',
    # Layered Sprite
    'LayerType',
    'BlendMode',
    'LayerDefinition',
    'PoseDefinition',
    'ExpressionDefinition',
    'OutfitDefinition',
    'CharacterSpriteManifest',
    'SpriteState',
    'SpriteCompositor',
    'create_character_template',
    'scan_characters_directory',
    # Patch Archive
    'PatchType',
    'CompressionType',
    'EncryptionType',
    'PatchEntry',
    'PatchInfo',
    'PatchBuilder',
    'PatchLoader',
    'PatchRegistry',
    'create_graphics_patch',
    'create_voice_patch',
    'create_audio_patch',
    'create_script_patch',
    'package_game',
]
