# HiganVN 打包系统

本文档说明如何打包游戏资源。

## 分包结构

```
game/
├── game.exe                # 游戏主程序
├── data/
│   ├── patches.json        # 分包注册表
│   ├── patch1.hgp          # 图形资源（立绘/背景/CG/UI）
│   ├── patch2.hgp          # 语音资源
│   ├── patch3.hgp          # 音频（BGM/SE）
│   ├── patch4.hgp          # 脚本/文本
│   └── dlc01.hgp           # DLC 内容（可选）
└── saves/                  # 存档目录
```

## 使用方式

### 1. 完整打包

```python
from higanvn.packaging import package_game
from pathlib import Path

# 打包整个游戏项目
patches = package_game(
    project_dir=Path("my_project"),
    output_dir=Path("build/data"),
    password="optional_encryption_key",  # 可选加密
    version="1.0.0"
)

print(f"打包完成，共 {len(patches)} 个分包")
```

### 2. 单独打包特定资源

```python
from higanvn.packaging import (
    PatchBuilder,
    PatchType,
    create_graphics_patch,
    create_voice_patch,
)
from pathlib import Path

# 打包图形资源
graphics_patch = create_graphics_patch(
    source_dir=Path("assets/characters"),
    output_path=Path("build/patch1.hgp"),
    password="secret123",
    version="1.0.0"
)

# 自定义打包
builder = PatchBuilder(
    name="dlc01",
    patch_type=PatchType.DLC,
    output_path=Path("build/dlc01.hgp"),
    password="dlc_key",
)
builder.add_directory(Path("dlc/chapter_ex"))
builder.build(version="1.0.0", description="追加章节 DLC")
```

### 3. 加载资源

```python
from higanvn.packaging import PatchRegistry, PatchLoader
from pathlib import Path

# 使用注册表（推荐）
registry = PatchRegistry(Path("data"))
registry.load_all(passwords={"patch1": "secret123"})

# 读取资源
image_data = registry.read("characters/alice/base/normal.png")
script_data = registry.read("scripts/main.vns")

# 单独加载分包
loader = PatchLoader(Path("data/patch1.hgp"), password="secret123")
with loader:
    files = loader.list_files()
    data = loader.read("some/file.png")
```

## 分包类型说明

| 类型 | 后缀 | 内容 | 压缩 |
|------|------|------|------|
| GRAPHICS | .hgp | 立绘/背景/CG/UI | ZLIB |
| VOICE | .hgp | 语音文件 | 无（已压缩） |
| AUDIO | .hgp | BGM/SE/环境音 | 无（已压缩） |
| SCRIPT | .hgp | 脚本/配置/文本 | ZLIB |
| VIDEO | .hgp | OP/ED 视频 | 无 |
| DLC | .hgp | DLC 追加内容 | ZLIB |
| PATCH | .hgp | 更新补丁 | ZLIB |

## 加密说明

- 使用 XOR 加密（轻量级保护）
- 密钥通过 PBKDF2-SHA256 派生
- 每个分包可使用不同密码
- `encryption_check` 用于验证密钥正确性

## 优先级机制

- 高优先级分包的文件会覆盖低优先级
- 用于实现补丁/DLC 覆盖基础资源
- 在 `patches.json` 中配置优先级

```json
{
  "game_version": "1.0.0",
  "patches": [
    {"name": "patch1", "priority": 0, "enabled": true},
    {"name": "update1", "priority": 10, "enabled": true},
    {"name": "dlc01", "priority": 5, "enabled": true}
  ]
}
```

## 差分立绘系统

见 [LAYERED_SPRITE.md](LAYERED_SPRITE.md) 了解如何组织角色差分立绘。
