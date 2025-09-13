# SEU-monogatari

HiganVN 最小可行版本（MVP）脚手架（初期支持无图形 headless），目标是迭代成为一个具备自然 DSL 的 Python 面向对象 Galgame 引擎。

入门请阅读《脚本编写与素材指南.md》。

## 运行 (Run)

基础运行（终端打印）：
```
python -m higanvn run scripts/demo.vns
```

交互模式（pygame 渲染，素材路径相对于 `--assets` 指定目录）：
```
python -m higanvn run scripts/demo.vns --assets assets --pygame
```

指定字体（CJK 渲染/中文断行更稳定）：
```
python -m higanvn run scripts/demo.vns --assets assets --pygame --font assets/fonts/NotoSansCJK-Regular.otf --font-size 28
```

## 打包 Windows 可执行文件 (.exe)

需要预先安装 PyInstaller：
```
pip install pyinstaller
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --onefile
```
完成后双击 `dist/SEU-Monogatari.exe` 启动。

更多跨平台打包（macOS / Linux AppImage / DEB / DMG 等）详见 `higanvn/packaging/README.md`。

## 开发 (Dev)
```
pip install -e .[dev]
pytest -q
```

说明：后续可插拔渲染 / 音频后端（当前使用 pygame）。

## GUI 动效 (Effects)

在 pygame 模式下支持基础立绘/角色动画：
- 指令：`> EF shake_x 张鹏 350 20`  
	支持类型：`shake_x`, `shake_y`, `slide_in_{l|r|u|d}`, `slide_out_{l|r|u|d}`
- 隐式触发：对白中 `[effect]` 标签触发动画，如 `[惊]` → shake_x。

## 功能概要
- 自然 DSL 脚本：`*label`、`? 选项 -> label`、`♪ BGM`、`> BG 背景.png`、`> CG xxx.png` 等。
- 回退（Back）与快速存取（F5/F9）
- 多槽位存读档（F7/F8）& 缩略图捕获
- Flow Map 分支图（M 键）
- 自动播放 / 快进 / 打字机速度控制
- 中日韩文本换行 & 字体自定义
- 角色立绘管理：base + pose_表情

## 目录约定
```
assets/
	bg/      背景
	cg/      CG 全屏图
	bgm/     背景音乐
	se/      音效
	ch/<actor>/base.png / pose_xxx.png  立绘
	fonts/   字体文件
	config/  actors_map.json 等
scripts/   .vns 剧本
```

## 常用快捷键
- Enter / Space：推进
- F5 / F9：快速存 / 快速读
- F7 / F8：槽位存 / 槽位读
- M：分支图 Flow Map
- Tab：日志 / 回放
- A：自动播放切换
- F：按住快进
- PageUp / Back 按钮：回到上一句

## 未来计划（摘要）
- 交互式脚本编辑器增强（实时预览 / 断点）
- 可点击 Flow Map 跳转
- 保存文件压缩与校验
- 资源子集打包 / 增量补丁
- 国际化（i18n）与多语言文本表导入

---
欢迎继续反馈与提出新需求。

