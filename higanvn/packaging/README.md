# HiganVN 跨平台打包指南 (Windows / macOS / Linux)

使用 `python -m higanvn pack` 将一个 `.vns` 剧本与其 `assets/` 素材打包为可分发的应用或二进制。支持多平台与多格式输出。

## 前置依赖 (Prerequisites)

- Python 3.9+
- 已安装 PyInstaller：`pip install pyinstaller`
- 可选平台工具：
	- macOS 生成 DMG：`hdiutil`（Xcode Command Line Tools）
	- Linux 生成 AppImage：`appimagetool` 在 PATH 中
	- Linux 生成 DEB：`dpkg-deb`（Debian/Ubuntu 系列）

## 快速开始 (Windows .exe)

在仓库根目录执行：

```powershell
# Packs scripts/demo.vns and assets/ into dist/ as a single .exe
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --onefile --format exe
```

可选参数：
- `--icon path\game.ico` 设置图标（macOS 用 `.icns`，Linux 用 `.png`）
- `--extra-data src;dest` 追加自定义文件/目录（可重复）
- 去掉 `--onefile` 使用目录模式（启动更快 / 便于调试）

## macOS 打包

生成 `.app`（默认）或 `.dmg`：

```bash
# 生成 .app （需在 macOS 上）
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --format app

# 由已有 .app 生成 DMG（需 hdiutil）
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --format dmg
```

## Linux 打包

生成 AppImage（默认）或 DEB 包：

```bash
# AppImage（需 appimagetool）
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --format appimage

# DEB（需 dpkg-deb）
python -m higanvn pack scripts/demo.vns --assets assets --name SEU-Monogatari --output dist --format deb
```

## 推荐素材目录布局

脚本中引用的相对路径按以下结构放置：
- `assets/bg/`   背景
- `assets/cg/`   CG 全屏图
- `assets/bgm/`  背景音乐
- `assets/se/`   音效
- `assets/ch/<actor>/base.png` 与 `pose_*.png` 角色立绘与表情
- `assets/config/actors_map.json` 角色显示名 → 目录映射

脚本引用示例：
- `> CG school.png` 会尝试加载 `assets/cg/school.png`
- `♪ theme.ogg` 会尝试加载 `assets/bgm/theme.ogg`

## 运行打包产物

双击 `dist/` 下生成的文件（Windows: `SEU-Monogatari.exe`，macOS: `SEU-Monogatari.app`，Linux: `SEU-Monogatari.AppImage`）。

启动引导（bootstrap）会读取 `DEFAULT_SCRIPT.txt`（打包时写入），否则回退到 `scripts/` 中第一个 `.vns`。

## 按脚本命名空间隔离素材

若一个仓库里有多份独立剧本，可根据脚本文件名建立命名空间：脚本 `scripts/demo.vns` 的专属资源放在 `assets/demo/` 下，对应子目录仍保持 `bg/`, `cg/`, `bgm/`, `se/`, `ch/`, `fonts/`, `config/`。

运行时素材查找优先级：
1. `assets/<脚本stem>/<relative>`
2. `assets/<脚本stem>/<子目录>/<relative>`（子目录限定：bg, cg, bgm, se, ch）
3. `assets/<子目录>/<relative>`
4. 原始传入路径

角色映射文件优先：`assets/<脚本stem>/config/actors_map.json` → 否则回退到 `assets/config/actors_map.json`。

## 体积与元数据优化 (Optimization)

使用高级参数减小体积、写入版本信息：

```bash
python -m higanvn pack scripts/demo.vns \
	--assets assets \
	--name SEU-Monogatari \
	--output dist \
	--onefile \
	--version auto \
	--strip \
	--upx-dir /path/to/upx
```

参数说明：
- `--version auto`：写入 `git describe` 结果（失败回退 0.1.0）到 `VERSION.txt`
- `--strip`：Unix 系统去符号缩小体积
- `--upx-dir`：指定 UPX 目录以压缩可执行文件
- `--console`：保留控制台窗口（调试崩溃 / 日志）
- 额外剔除：`tkinter`, `unittest`, `distutils`, `OpenGL*`, `numpy`, `pygame.sndarray` 等

### 可复现构建 (Reproducible Builds)
- 固定 Python 版本与依赖（生成 `requirements.txt`）
- 使用干净虚拟环境构建
- 设定 `PYTHONHASHSEED=0` 保证哈希顺序稳定

### 多格式产物
可多次执行 `pack` 使用不同 `--format`，产物集中于 `dist/`。

### 资源裁剪 (实验特性)
`--prune-unused-assets`：仅打包脚本静态解析到的资源（外加 fonts/config），并输出 `asset_manifest.json`。若脚本运行时需动态资源丢失，可关闭此参数重试。

### 常见问题 (Troubleshooting)
- 字体缺失：确认放在 `assets/fonts/` 或运行时通过 `--font` 指定
- Windows 杀软误报：可用目录模式（去掉 `--onefile`）或禁用 UPX，并考虑代码签名
- AppImage 失败：确认 `appimagetool` 可执行，并检查大小写敏感路径

### 可能的后续增强 (Ideas)
- 嵌入游戏元数据 manifest（About 界面）
- 增量补丁打包（区分程序与资源）
- 导出符号表辅助崩溃分析