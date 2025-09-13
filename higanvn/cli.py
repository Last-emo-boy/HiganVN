from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
from typing import List, Optional
import subprocess
import sys

from .engine.engine import Engine
from .script.parser import parse_script


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="higanvn", description="HiganVN engine runner")
    sub = parser.add_subparsers(dest="cmd")

    # run subcommand (default behavior)
    p_run = sub.add_parser("run", help="Run a .vns script")
    p_run.add_argument("script", type=str, help="Path to .vns script to run")
    p_run.add_argument("--assets", type=str, default="assets", help="Assets base directory")
    p_run.add_argument("--pygame", action="store_true", help="Use pygame renderer (interactive)")
    p_run.add_argument("--strict", action="store_true", help="Enable strict script errors")
    p_run.add_argument("--font", type=str, default=None, help="Path to TTF/OTF font for CJK text")
    p_run.add_argument("--font-size", type=int, default=28, help="Font size for UI text")

    # pack subcommand: build a standalone app with PyInstaller (per-OS)
    p_pack = sub.add_parser("pack", help="Pack a script and assets into a distributable app/binary")
    p_pack.add_argument("script", type=str, help="Path to .vns script to pack")
    p_pack.add_argument("--assets", type=str, default="assets", help="Assets directory to include")
    p_pack.add_argument("--name", type=str, default="HiganVN-Game", help="Application name")
    p_pack.add_argument("--icon", type=str, default=None, help="Optional icon file (.ico on Windows, .icns on macOS, .png on Linux)")
    p_pack.add_argument("--onefile", action="store_true", help="Build as one-file bundle (slower start)")
    p_pack.add_argument("--output", type=str, default="dist", help="Output directory for the build")
    p_pack.add_argument("--target", type=str, choices=["auto","win","mac","linux"], default="auto", help="Target platform (run on that OS)")
    p_pack.add_argument("--format", type=str, choices=["auto","exe","app","dmg","appimage","deb"], default="auto", help="Packaging format (varies by OS)")
    p_pack.add_argument("--extra-data", action="append", default=[], help="Extra data files or folders to include 'src;dest'")
    # optimization flags
    p_pack.add_argument("--version", type=str, default="auto", help="Version string to embed (auto = git describe or 0.1.0)")
    p_pack.add_argument("--upx-dir", type=str, default=None, help="Path to UPX for executable compression")
    p_pack.add_argument("--strip", action="store_true", help="Strip symbols (non-Windows)")
    p_pack.add_argument("--console", action="store_true", help="Build with console (omit --windowed)")
    p_pack.add_argument("--prune-unused-assets", action="store_true", help="Only include assets referenced by the script (experimental)")

    # Back-compat: if user didn't specify a subcommand, treat as 'run'
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    if not argv_list or argv_list[0] not in {"run", "pack"}:
        args = p_run.parse_args(argv_list)
        args.cmd = "run"  # type: ignore[attr-defined]
    else:
        args = parser.parse_args(argv_list)

    if args.cmd == "run":
        script_path = Path(args.script)
        if not script_path.exists():
            print(f"Script not found: {script_path}")
            return 2

        source = script_path.read_text(encoding="utf-8")
        program = parse_script(source)

        if args.pygame:
            # Resolve script path to absolute so save files store a stable path
            abs_script = script_path.resolve()
            # load optional metadata from <script>.meta.json
            meta: dict = {}
            try:
                mfile = script_path.with_suffix('.meta.json')
                if mfile.exists():
                    meta = json.loads(mfile.read_text(encoding='utf-8'))
            except Exception:
                meta = {}
            # make paths relative to assets dir by chdir
            assets_dir = Path(args.assets)
            if assets_dir.exists():
                os.chdir(assets_dir)
            from .engine.renderer_pygame import PygameRenderer  # local import to avoid test deps
            # Use per-script asset namespace: assets/<script-stem>/...
            ns = (
                (meta.get('assetsNamespace') or meta.get('assetNamespace') or meta.get('id'))
                if isinstance(meta, dict) else None
            ) or script_path.stem
            title = (
                (meta.get('windowTitle') or meta.get('title'))
                if isinstance(meta, dict) else None
            ) or "HiganVN"
            renderer = PygameRenderer(title=title, font_path=args.font, font_size=args.font_size, asset_namespace=ns)
            engine = Engine(renderer=renderer, interactive=True, strict=args.strict)
            engine.set_script_path(abs_script)
            # wire quick save/load hooks for F5/F9
            try:
                renderer.set_quicksave_hook(lambda: engine.quicksave())
                renderer.set_quickload_hook(lambda: engine.quickload())
                # wire multi-slot hooks (F7 save, F8 load -> open UI in renderer)
                renderer.set_save_slot_hook(lambda slot: engine.save_to_slot(int(slot)))
                renderer.set_load_slot_hook(lambda slot: engine.load_from_slot(int(slot)))
                # let renderer know where saves live (Documents/HiganVN/<game-id>) for thumbs/metas
                renderer.set_get_save_dir(lambda: engine.get_save_dir())
                # back/rewind one visible line
                renderer.set_back_hook(lambda: engine.back_one_line())
            except Exception:
                pass
        else:
            engine = Engine(strict=args.strict)
            engine.set_script_path(script_path)

        engine.load(program)
        # For MVP in headless mode, just iterate and print
        engine.run_headless()
        return 0

    if args.cmd == "pack":
        return _cmd_pack(
            script=args.script,
            assets=args.assets,
            name=args.name,
            icon=args.icon,
            onefile=bool(args.onefile),
            output=args.output,
            target=args.target,
            fmt=args.format,
            extra_data=args.extra_data,
            version=args.version,
            upx_dir=args.upx_dir,
            strip=args.strip,
            console=bool(args.console),
            prune=bool(args.prune_unused_assets),
        )

    return 0


def _cmd_pack(
    *,
    script: str,
    assets: str,
    name: str,
    icon: Optional[str],
    onefile: bool,
    output: str,
    target: str,
    fmt: str,
    extra_data: list[str],
    version: str,
    upx_dir: Optional[str],
    strip: bool,
    console: bool,
    prune: bool,
) -> int:
    script_path = Path(script).resolve()
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return 2
    assets_dir = Path(assets).resolve()
    if not assets_dir.exists():
        print(f"Assets dir not found: {assets_dir}")
        return 2

    # Determine platform/format
    plat = target
    if plat == "auto":
        if sys.platform.startswith("win"):
            plat = "win"
        elif sys.platform == "darwin":
            plat = "mac"
        else:
            plat = "linux"
    if fmt == "auto":
        fmt = {
            "win": "exe",
            "mac": "app",
            "linux": "appimage",
        }.get(plat, "exe")

    out_dir = Path(output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optionally build a pruned asset directory (only referenced files)
    if prune:
        pruned_dir = out_dir / f"_pruned_assets_{script_path.stem}"
        if pruned_dir.exists():
            import shutil as _shutil
            try:
                _shutil.rmtree(pruned_dir)
            except Exception:
                pass
        pruned_dir.mkdir(parents=True, exist_ok=True)
        try:
            from .packaging.asset_scan import build_asset_manifest
            manifest = build_asset_manifest(script_path, assets_dir, namespace=script_path.stem)
            import shutil
            def safe_copy(rel_path: str):
                if rel_path.startswith("MISSING:"):
                    return
                src = assets_dir / rel_path
                if not src.exists():
                    return
                dst = pruned_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass
            for cat in ("backgrounds", "cgs", "bgm", "se"):
                for rel in manifest.get(cat, []):
                    safe_copy(rel)
            for actor, info in (manifest.get("characters", {}) or {}).items():
                base_rel = info.get("base")
                if base_rel:
                    safe_copy(base_rel)
                for pose_rel in (info.get("poses") or {}).values():
                    safe_copy(pose_rel)
            for extra_folder in ("fonts", "config"):
                src_dir = assets_dir / extra_folder
                if src_dir.exists():
                    for p in src_dir.rglob("*"):
                        if p.is_file():
                            rel = p.relative_to(assets_dir).as_posix()
                            safe_copy(rel)
            assets_dir = pruned_dir
            (pruned_dir / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Pruned assets written: {pruned_dir}")
        except Exception as e:
            print(f"Asset pruning failed, falling back to full assets: {e}")

    # Write DEFAULT_SCRIPT marker (will be added to bundle)
    default_script_file = out_dir / "DEFAULT_SCRIPT.txt"
    default_script_file.write_text(f"scripts/{script_path.name}", encoding="utf-8")

    # Resolve version
    ver = version
    if ver == "auto":
        ver = _detect_version() or "0.1.0"
    version_file = out_dir / "VERSION.txt"
    version_file.write_text(ver, encoding="utf-8")

    # Build PyInstaller base
    data_sep = ";" if sys.platform.startswith("win") else ":"

    def add_data_arg(src: Path, dest_rel: str) -> list[str]:
        return ["--add-data", f"{src}{data_sep}{dest_rel}"]

    py_cmd = [
        sys.executable, "-m", "PyInstaller",
        str(Path(__file__).resolve().parent / "packaging" / "bootstrap.py"),
        "--name", name,
        "--distpath", str(out_dir),
        "--noconfirm",
    ]
    if not console:
        py_cmd.append("--windowed")
    if strip and not sys.platform.startswith("win"):
        py_cmd.append("--strip")
    if upx_dir:
        py_cmd += ["--upx-dir", str(Path(upx_dir).resolve())]
    if icon:
        py_cmd += ["--icon", str(Path(icon).resolve())]
    if onefile:
        py_cmd.append("--onefile")
    py_cmd += [
        "--exclude-module", "numpy",
        "--exclude-module", "pygame.sndarray",
        "--exclude-module", "OpenGL",
        "--exclude-module", "OpenGL_accelerate",
    "--exclude-module", "tkinter",
    "--exclude-module", "unittest",
    "--exclude-module", "distutils",
    ]
    py_cmd += add_data_arg(assets_dir, "assets")
    py_cmd += add_data_arg(script_path, "scripts")
    meta_path = script_path.with_suffix('.meta.json')
    if meta_path.exists():
        py_cmd += add_data_arg(meta_path, "scripts")
    py_cmd += add_data_arg(default_script_file, "DEFAULT_SCRIPT.txt")
    py_cmd += add_data_arg(version_file, "VERSION.txt")
    for item in extra_data:
        try:
            src, dest = item.split(";", 1)
        except ValueError:
            print(f"Invalid --extra-data format: {item}, expected src;dest")
            return 2
        py_cmd += ["--add-data", f"{Path(src).resolve()}{data_sep}{dest}"]

    print("Running:", " ".join(py_cmd))
    try:
        res = subprocess.run(py_cmd, check=False)
    except FileNotFoundError:
        print("PyInstaller not found. Please install it: pip install pyinstaller")
        return 2
    if res.returncode != 0:
        return res.returncode

    # Post-process per target format
    if plat == "mac" and fmt == "dmg":
        return _mac_make_dmg(out_dir, name)
    if plat == "linux" and fmt == "appimage":
        return _linux_make_appimage(out_dir, name)
    if plat == "linux" and fmt == "deb":
        return _linux_make_deb(out_dir, name)

    print(f"Build complete. See: {out_dir}")
    return 0


def _mac_make_dmg(out_dir: Path, name: str) -> int:
    app = (out_dir / f"{name}.app")
    if not app.exists():
        # PyInstaller may place app in a subfolder when onefile=0; try locate
        cand = next(out_dir.glob(f"**/{name}.app"), None)
        if cand:
            app = cand
    if not app.exists():
        print(f".app not found under {out_dir}")
        return 2
    dmg_path = out_dir / f"{name}.dmg"
    cmd = [
        "hdiutil", "create", "-volname", name, "-srcfolder", str(app), "-ov", "-format", "UDZO", str(dmg_path)
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        print("hdiutil failed. Install Xcode command line tools and try again.")
        return res.returncode
    print(f"DMG created: {dmg_path}")
    return 0


def _linux_make_appimage(out_dir: Path, name: str) -> int:
    # Requires appimagetool in PATH
    exe = next(out_dir.glob(f"**/{name}"), None)
    if not exe:
        exe = next(out_dir.glob(f"**/{name}.bin"), None)
    if not exe:
        print(f"Executable not found under {out_dir}; skipping AppImage")
        return 2
    appdir = out_dir / f"{name}.AppDir"
    (appdir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
    # Copy executable
    target_exe = appdir / "usr" / "bin" / name
    try:
        import shutil
        shutil.copy2(exe, target_exe)
        os.chmod(target_exe, 0o755)
    except Exception as e:
        print(f"Copy failed: {e}")
        return 2
    # desktop file
    desktop = appdir / f"{name}.desktop"
    desktop.write_text(
        f"""[Desktop Entry]\nType=Application\nName={name}\nExec={name}\nIcon={name}\nCategories=Game;\n""",
        encoding="utf-8",
    )
    # minimal AppRun
    apprun = appdir / "AppRun"
    apprun.write_text("#!/bin/sh\nexec \"$APPDIR/usr/bin/%s\" \"$@\"\n" % name, encoding="utf-8")
    os.chmod(apprun, 0o755)
    # icon if present
    icon_src = next(out_dir.glob("**/*.png"), None)
    if icon_src:
        (appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_src, appdir / f"{name}.png")

    # Run appimagetool
    cmd = ["appimagetool", str(appdir), str(out_dir / f"{name}.AppImage")]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        print("appimagetool failed. Install it from https://github.com/AppImage/appimagetool/releases")
        return res.returncode
    print(f"AppImage created: {out_dir / f'{name}.AppImage'}")
    return 0


def _linux_make_deb(out_dir: Path, name: str) -> int:
    # Requires dpkg-deb
    exe = next(out_dir.glob(f"**/{name}"), None)
    if not exe:
        exe = next(out_dir.glob(f"**/{name}.bin"), None)
    if not exe:
        print(f"Executable not found under {out_dir}; skipping DEB")
        return 2
    debdir = out_dir / f"{name}-deb"
    bindir = debdir / "usr" / "bin"
    desktopdir = debdir / "usr" / "share" / "applications"
    controldir = debdir / "DEBIAN"
    bindir.mkdir(parents=True, exist_ok=True)
    desktopdir.mkdir(parents=True, exist_ok=True)
    controldir.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(exe, bindir / name)
    os.chmod(bindir / name, 0o755)
    (debdir / "usr" / "share" / name).mkdir(parents=True, exist_ok=True)
    # .desktop
    (desktopdir / f"{name}.desktop").write_text(
        f"""[Desktop Entry]\nType=Application\nName={name}\nExec=/usr/bin/{name}\nIcon=/usr/share/{name}/icon.png\nCategories=Game;\n""",
        encoding="utf-8",
    )
    # control file (minimal)
    (controldir / "control").write_text(
        f"""Package: {name}\nVersion: 1.0\nSection: games\nPriority: optional\nArchitecture: amd64\nMaintainer: {name} <noreply@example.com>\nDescription: Visual novel built with HiganVN\n""",
        encoding="utf-8",
    )
    deb_path = out_dir / f"{name}_1.0_amd64.deb"
    cmd = ["dpkg-deb", "--build", str(debdir), str(deb_path)]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        print("dpkg-deb failed. Ensure you run this on Debian/Ubuntu with dpkg-deb installed.")
        return res.returncode
    print(f"DEB created: {deb_path}")
    return 0


def _detect_version() -> Optional[str]:
    try:
        import subprocess
        res = subprocess.run(["git", "describe", "--tags", "--dirty", "--always"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        return None
    return None


if __name__ == "__main__":
    raise SystemExit(main())
