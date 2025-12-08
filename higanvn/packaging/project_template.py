"""
Project Template - 项目模板系统

用于创建标准化的 HiganVN 项目结构
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from higanvn.packaging.game_config import GameConfig, GameMetadata, ActorDefinition


# ============================================================================
# 目录结构模板
# ============================================================================

STANDARD_DIRS = [
    "assets",
    "assets/characters",
    "assets/backgrounds",
    "assets/cg",
    "assets/ui",
    "assets/ui/textbox",
    "assets/ui/buttons",
    "assets/ui/icons",
    "assets/audio",
    "assets/audio/bgm",
    "assets/audio/se",
    "assets/audio/voice",
    "assets/audio/ambient",
    "assets/fonts",
    "assets/video",
    "config",
    "scripts",
    "scripts/chapters",
    "saves",
    "build",
]

# 示例主脚本
SAMPLE_MAIN_SCRIPT = '''# {title}
# Version: {version}
# Author: {author}

*start
> TITLE "{title}"
> GOTO chapter1

# ============================================================================
# 第一章
# ============================================================================

*chapter1
> FADE out 500
> BG classroom_morning
> FADE in 500
♪ bgm/main_theme 0.6

: 这是一个新的故事的开始……

主角 (think)「终于开始了。」

? 继续 -> chapter1_continue
? 返回标题 -> start

*chapter1_continue
主角「让我们开始吧。」

> END
'''

# 示例角色配置
SAMPLE_ACTORS_CONFIG = {
    "protagonist": {
        "id": "protagonist",
        "name": "主角",
        "name_en": "Protagonist",
        "aliases": ["我", "主人公"],
        "name_color": "#FFFFFF",
        "is_protagonist": True,
        "default_expression": "normal",
    },
    "narrator": {
        "id": "narrator",
        "name": "",
        "is_narrator": True,
        "is_hidden": True,
    },
}


def create_project(
    project_dir: Path,
    title: str = "My Visual Novel",
    author: str = "",
    version: str = "1.0.0",
    include_samples: bool = True,
) -> Path:
    """
    创建新的 HiganVN 项目
    
    Args:
        project_dir: 项目目录
        title: 游戏标题
        author: 作者
        version: 版本号
        include_samples: 是否包含示例文件
    
    Returns:
        项目目录路径
    """
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建目录结构
    for subdir in STANDARD_DIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    # 创建游戏配置
    config = GameConfig()
    config.metadata = GameMetadata(
        title=title,
        author=author,
        version=version,
        main_script="scripts/main.vns",
        start_label="start",
    )
    
    # 添加角色
    for actor_id, actor_data in SAMPLE_ACTORS_CONFIG.items():
        config.actors[actor_id] = ActorDefinition(**actor_data)
    
    # 保存配置
    config.save(project_dir / "config" / "game.json")
    
    # 创建素材包清单
    pack_manifest = {
        "name": title,
        "version": version,
        "author": author,
        "description": f"{title} asset pack",
    }
    (project_dir / "assets" / "pack.json").write_text(
        json.dumps(pack_manifest, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # 创建示例脚本
    if include_samples:
        main_script = SAMPLE_MAIN_SCRIPT.format(
            title=title,
            version=version,
            author=author,
        )
        (project_dir / "scripts" / "main.vns").write_text(
            main_script,
            encoding='utf-8'
        )
    
    # 创建 .gitignore
    gitignore_content = """# HiganVN Project
saves/
build/
*.hap
*.pyc
__pycache__/
.DS_Store
Thumbs.db
"""
    (project_dir / ".gitignore").write_text(gitignore_content, encoding='utf-8')
    
    # 创建 README
    readme_content = f"""# {title}

A visual novel created with HiganVN.

## Project Structure

```
{project_dir.name}/
├── assets/                 # 素材目录
│   ├── characters/         # 角色立绘
│   ├── backgrounds/        # 背景
│   ├── cg/                 # CG
│   ├── ui/                 # UI 素材
│   ├── audio/              # 音频
│   │   ├── bgm/            # 背景音乐
│   │   ├── se/             # 音效
│   │   ├── voice/          # 语音
│   │   └── ambient/        # 环境音
│   ├── fonts/              # 字体
│   └── video/              # 视频
├── config/                 # 配置
│   └── game.json           # 游戏配置
├── scripts/                # 脚本
│   ├── main.vns            # 主脚本
│   └── chapters/           # 章节脚本
├── saves/                  # 存档目录
└── build/                  # 构建输出
```

## Running

```bash
higanvn run .
```

## Building

```bash
higanvn pack .
```

## Version

{version}

## Author

{author}
"""
    (project_dir / "README.md").write_text(readme_content, encoding='utf-8')
    
    return project_dir


def create_character(
    project_dir: Path,
    actor_id: str,
    display_name: str,
    expressions: Optional[list] = None,
    outfits: Optional[list] = None,
) -> Path:
    """
    创建角色目录结构
    
    Args:
        project_dir: 项目目录
        actor_id: 角色ID
        display_name: 显示名称
        expressions: 表情列表
        outfits: 服装列表
    """
    project_dir = Path(project_dir)
    char_dir = project_dir / "assets" / "characters" / actor_id
    char_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建表情目录
    expr_dir = char_dir / "expressions"
    expr_dir.mkdir(exist_ok=True)
    
    # 创建默认表情占位
    expressions = expressions or ["normal", "happy", "sad", "angry", "surprised"]
    for expr in expressions:
        placeholder = expr_dir / f"{expr}.png"
        if not placeholder.exists():
            # 创建空占位文件说明
            (expr_dir / f"{expr}.txt").write_text(
                f"Place {expr} expression image here as {expr}.png",
                encoding='utf-8'
            )
    
    # 创建服装目录
    if outfits:
        outfits_dir = char_dir / "outfits"
        outfits_dir.mkdir(exist_ok=True)
        for outfit in outfits:
            outfit_dir = outfits_dir / outfit
            outfit_dir.mkdir(exist_ok=True)
            (outfit_dir / "expressions").mkdir(exist_ok=True)
    
    # 创建角色清单
    manifest = {
        "id": actor_id,
        "name": display_name,
        "expressions": expressions,
        "outfits": outfits or [],
        "default_expression": "normal",
    }
    (char_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # 更新游戏配置
    config_path = project_dir / "config" / "game.json"
    if config_path.exists():
        config = GameConfig.load(config_path)
        config.actors[actor_id] = ActorDefinition(
            id=actor_id,
            name=display_name,
            default_expression="normal",
        )
        config.save(config_path)
    
    return char_dir


def migrate_legacy_project(
    legacy_dir: Path,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    迁移旧版项目结构到新标准
    
    Args:
        legacy_dir: 旧项目目录 (assets/game 格式)
        output_dir: 输出目录，默认在旧目录旁创建
    
    Returns:
        新项目目录
    """
    legacy_dir = Path(legacy_dir)
    
    if output_dir is None:
        output_dir = legacy_dir.parent / f"{legacy_dir.name}_new"
    
    output_dir = Path(output_dir)
    
    # 创建新项目
    create_project(output_dir, include_samples=False)
    
    # 映射旧目录到新目录
    mappings = {
        "bg": "assets/backgrounds",
        "ch": "assets/characters",
        "cg": "assets/cg",
        "bgm": "assets/audio/bgm",
        "se": "assets/audio/se",
        "voice": "assets/audio/voice",
        "fonts": "assets/fonts",
        "config": "config",
    }
    
    for old_name, new_name in mappings.items():
        old_path = legacy_dir / old_name
        new_path = output_dir / new_name
        
        if old_path.exists():
            # 复制文件
            if old_path.is_dir():
                for item in old_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(old_path)
                        dest = new_path / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
    
    # 迁移角色配置
    actors_map = legacy_dir / "config" / "actors_map.json"
    if actors_map.exists():
        data = json.loads(actors_map.read_text(encoding='utf-8'))
        
        config = GameConfig.load(output_dir / "config" / "game.json")
        for display_name, folder_name in data.items():
            config.actors[folder_name] = ActorDefinition(
                id=folder_name,
                name=display_name,
            )
        config.save(output_dir / "config" / "game.json")
    
    return output_dir


def validate_project(project_dir: Path) -> Dict[str, Any]:
    """
    验证项目结构完整性
    
    Returns:
        验证结果字典
    """
    project_dir = Path(project_dir)
    
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {},
    }
    
    # 检查必需文件
    required_files = [
        "config/game.json",
        "scripts/main.vns",
    ]
    
    for req in required_files:
        if not (project_dir / req).exists():
            result["errors"].append(f"Missing required file: {req}")
            result["valid"] = False
    
    # 检查目录结构
    for subdir in STANDARD_DIRS[:10]:  # 检查主要目录
        if not (project_dir / subdir).exists():
            result["warnings"].append(f"Missing directory: {subdir}")
    
    # 统计素材
    if (project_dir / "assets").exists():
        stats = {
            "characters": 0,
            "backgrounds": 0,
            "cgs": 0,
            "bgm": 0,
            "se": 0,
        }
        
        char_dir = project_dir / "assets" / "characters"
        if char_dir.exists():
            stats["characters"] = len([d for d in char_dir.iterdir() if d.is_dir()])
        
        bg_dir = project_dir / "assets" / "backgrounds"
        if bg_dir.exists():
            stats["backgrounds"] = len([f for f in bg_dir.rglob('*') if f.is_file()])
        
        result["info"]["asset_stats"] = stats
    
    return result
