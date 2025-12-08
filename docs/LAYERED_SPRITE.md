# HiganVN 差分立绘系统

差分立绘合成系统，支持图层叠加渲染。

## 核心概念

### 图层叠加

立绘由多个图层叠加而成：

```
        ┌─────────────┐
        │  特效层     │  z=150 (脸红/汗滴)
        ├─────────────┤
        │  表情层     │  z=100 (整合表情或分离部件)
        │ ┌─────────┐ │
        │ │ 眉毛    │ │  z=103
        │ ├─────────┤ │
        │ │ 眼睛    │ │  z=102
        │ ├─────────┤ │
        │ │ 嘴巴    │ │  z=101
        │ └─────────┘ │
        ├─────────────┤
        │  配饰层     │  z=55 (领带/蝴蝶结)
        ├─────────────┤
        │  服装层     │  z=50
        ├─────────────┤
        │  身体底图   │  z=0
        └─────────────┘
```

### 两种表情模式

#### 1. 整合模式（简单）

一个表情一张图，适合简单项目：

```
face/
├── normal.png
├── happy.png
├── sad.png
└── angry.png
```

#### 2. 分离模式（高级）

眼睛、嘴巴、眉毛分开，可自由组合：

```
face/parts/
├── eyes_normal.png
├── eyes_closed.png
├── eyes_half.png
├── mouth_normal.png
├── mouth_smile.png
├── mouth_open.png
├── brows_normal.png
└── brows_angry.png
```

## 目录结构

```
characters/{角色ID}/
├── manifest.json           # 角色配置
├── base/                   # 身体底图
│   ├── normal.png          # 普通站姿
│   ├── sit.png             # 坐姿
│   └── cross_arms.png      # 抱臂
├── face/                   # 表情
│   ├── normal.png          # 整合表情
│   ├── happy.png
│   └── parts/              # 分离部件
│       ├── eyes_*.png
│       ├── mouth_*.png
│       └── brows_*.png
├── outfit/                 # 服装
│   ├── school/
│   │   ├── body.png
│   │   └── ribbon.png
│   └── casual/
│       └── body.png
└── effects/                # 特效
    ├── blush.png           # 脸红
    ├── sweat.png           # 汗滴
    └── tears.png           # 眼泪
```

## manifest.json 配置

```json
{
  "id": "alice",
  "name": "爱丽丝",
  "canvas_width": 1024,
  "canvas_height": 1536,
  "default_pose": "normal",
  "default_expression": "normal",
  "default_outfit": "school",
  
  "layers": {
    "base_normal": {
      "id": "base_normal",
      "layer_type": "BASE",
      "file": "base/normal.png",
      "z_order": 0
    },
    "face_happy": {
      "id": "face_happy",
      "layer_type": "FACE_COMPOSITE",
      "file": "face/happy.png",
      "z_order": 100
    }
  },
  
  "poses": {
    "normal": {
      "id": "normal",
      "base_layer": "base_normal",
      "face_offset": [256, 80]
    }
  },
  
  "expressions": {
    "happy": {
      "id": "happy",
      "composite_layer": "face_happy"
    },
    "custom_smile": {
      "id": "custom_smile",
      "eyes_layer": "eyes_normal",
      "mouth_layer": "mouth_smile",
      "eyebrows_layer": "eyebrows_normal"
    }
  },
  
  "outfits": {
    "school": {
      "id": "school",
      "name": "制服",
      "layers": [...]
    }
  }
}
```

## 代码使用

### 合成立绘

```python
from higanvn.packaging import (
    CharacterSpriteManifest,
    SpriteState,
    SpriteCompositor,
)

# 加载角色 manifest
manifest = CharacterSpriteManifest.load(Path("characters/alice/manifest.json"))

# 创建合成器
compositor = SpriteCompositor(manifest)

# 设置状态
state = SpriteState(
    character_id="alice",
    pose="normal",
    expression="happy",
    outfit="school",
    active_effects=["blush"],  # 添加脸红特效
)

# 获取需要渲染的图层
layers = compositor.get_render_layers(state)
# 返回: [(LayerDefinition, x_offset, y_offset), ...]

# 获取需要加载的文件列表
files = compositor.get_required_files(state)
# 返回: ["base/normal.png", "outfit/school/body.png", "face/happy.png", "effects/blush.png"]
```

### 创建角色模板

```python
from higanvn.packaging import create_character_template

# 快速创建角色目录结构
manifest = create_character_template(
    character_id="alice",
    name="爱丽丝",
    output_dir=Path("characters"),
    expressions=["normal", "happy", "sad", "angry", "shy"],
    outfits=["default", "school", "casual"],
    poses=["normal", "sit"],
)
```

### 扫描所有角色

```python
from higanvn.packaging import scan_characters_directory

# 加载所有角色 manifest
manifests = scan_characters_directory(Path("characters"))
# 返回: {"alice": CharacterSpriteManifest, "bob": ...}
```

## 脚本调用语法

```
# 基本显示
爱丽丝 "你好！"

# 指定表情
爱丽丝 (happy) "开心~"

# 完整指定：姿势:表情:服装
爱丽丝 (normal:happy:school) "穿着制服呢！"

# 切换服装
爱丽丝 (casual) "换上便服了"

# 添加特效（用 + 号）
爱丽丝 (shy+blush) "好害羞..."

# 多个特效
爱丽丝 (sad+tears+sweat) "呜呜..."

# 自定义组合表情
爱丽丝 (custom_smile) "自定义的微笑"
```

## 最佳实践

1. **统一画布尺寸**: 所有素材使用相同的画布尺寸（如 1024x1536）
2. **正确设置偏移**: `face_offset` 确保表情对齐面部
3. **分层导出**: 从 PSD 分层导出，保持透明度
4. **命名规范**: 使用英文小写 + 下划线命名
5. **预览测试**: 使用合成器预览确认效果
