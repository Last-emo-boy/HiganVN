# HiganVN Demo Project

官方演示项目，展示 HiganVN 引擎的核心功能。

## 项目结构

```
demo/
├── assets/                     # 素材目录
│   ├── pack.json               # 素材包清单
│   ├── characters/             # 角色立绘
│   │   ├── alice/
│   │   │   ├── manifest.json   # 角色清单
│   │   │   ├── base.png        # 基础立绘
│   │   │   └── expressions/    # 表情差分
│   │   │       ├── normal.png
│   │   │       ├── happy.png
│   │   │       └── ...
│   │   └── bob/
│   │       └── ...
│   ├── backgrounds/            # 背景图片
│   │   ├── title_bg.jpg
│   │   ├── classroom.jpg
│   │   ├── park_day.jpg
│   │   ├── cafe.jpg
│   │   └── park_sunset.jpg
│   ├── cg/                     # CG 事件图
│   ├── ui/                     # UI 素材
│   │   └── textbox/
│   ├── audio/                  # 音频
│   │   ├── bgm/                # 背景音乐
│   │   │   ├── title_theme.ogg
│   │   │   ├── school_day.ogg
│   │   │   └── ...
│   │   ├── se/                 # 音效
│   │   │   └── whoosh.wav
│   │   └── voice/              # 语音
│   └── fonts/                  # 字体
├── config/                     # 配置
│   └── game.json               # 游戏主配置
├── scripts/                    # 脚本
│   ├── main.vns                # 主脚本
│   └── chapters/               # 章节脚本
└── saves/                      # 存档目录
```

## 素材规范

### 角色立绘 (characters/)

每个角色一个文件夹，文件夹名为角色 ID：

```
characters/{actor_id}/
├── manifest.json       # 角色配置
├── base.png            # 基础立绘 (可选)
├── expressions/        # 表情差分
│   ├── normal.png
│   ├── happy.png
│   ├── sad.png
│   ├── angry.png
│   ├── surprised.png
│   └── think.png
├── outfits/            # 服装 (可选)
│   ├── casual/
│   │   ├── base.png
│   │   └── expressions/
│   └── school/
│       └── ...
└── poses/              # 姿势/动作 (可选)
    ├── sit.png
    └── wave.png
```

### 背景 (backgrounds/)

直接放置图片文件，文件名即为背景 ID：

```
backgrounds/
├── classroom.jpg       # 使用: > BG classroom
├── park_day.jpg        # 使用: > BG park_day
└── cafe.webp           # 使用: > BG cafe
```

### 音频 (audio/)

```
audio/
├── bgm/                # 背景音乐 (循环)
│   └── title_theme.ogg # 使用: ♪ bgm/title_theme 0.6
├── se/                 # 音效 (单次)
│   └── whoosh.wav      # 使用: > SE se/whoosh 0.8
├── voice/              # 语音
│   └── alice/          # 按角色分文件夹
│       └── ch1_001.ogg
└── ambient/            # 环境音 (循环)
    └── rain.ogg
```

## 运行方式

```bash
# 从项目根目录运行
higanvn run demo

# 或进入 demo 目录运行
cd demo
higanvn run .
```

## 打包

```bash
# 打包为 .hap 文件
higanvn pack demo -o demo.hap
```

## 演示功能

1. **富文本渲染** - 颜色、大小、粗体、斜体、特效
2. **场景切换** - 淡入淡出、背景切换
3. **音频系统** - BGM、音效
4. **选项系统** - 分支选择
5. **角色对话** - 带表情的对话显示

## 注意事项

- 此 demo 项目中的素材文件为占位符
- 运行前需要添加实际的图片和音频文件
- 或使用 `--placeholder` 模式运行（自动生成占位符）
