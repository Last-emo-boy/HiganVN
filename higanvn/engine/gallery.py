from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pygame
from pygame import Surface
from higanvn.engine.gallery_io import read_thumb, write_thumb, is_unlocked

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)
TABS = ["CG", "BGM"]


def _scan_cg_paths(resolve: Callable[[str, list[str]], str]) -> List[str]:
    candidates: List[str] = []
    # naive scan: look under assets/<ns>/cg if resolver maps a typical file
    # we can't inspect namespaces directly; rely on common files
    common = [
        "",  # allow passthrough if user uses absolute/relative
    ]
    seen = set()
    # In absence of a manifest, we scan known folders if exist
    for folder in ["assets/cg", "cg"]:
        p = Path(folder)
        if p.exists() and p.is_dir():
            for f in sorted(p.glob("**/*")):
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    rp = str(f)
                    if rp not in seen:
                        seen.add(rp)
                        candidates.append(rp)
    return candidates


def _scan_bgm_paths(resolve: Callable[[str, list[str]], str]) -> List[str]:
    out: List[str] = []
    for folder in ["assets/bgm", "bgm"]:
        p = Path(folder)
        if p.exists() and p.is_dir():
            for f in sorted(p.glob("**/*")):
                if f.suffix.lower() in (".mp3", ".ogg", ".wav"):
                    out.append(str(f))
    return out


def _cg_category_for(fp: str) -> str:
    p = Path(fp)
    # Prefer category by top-level folder under assets/cg or cg
    try_roots = [Path("assets/cg"), Path("cg")]
    for root in try_roots:
        try:
            rel = p.relative_to(root)
            parts = rel.parts
            if len(parts) > 1:
                return parts[0]
            else:
                return "未分类"
        except Exception:
            continue
    # Fallback to parent folder name
    return p.parent.name or "未分类"


def _thumb_for(img: Surface, size: Tuple[int, int]) -> Surface:
    w, h = img.get_size()
    tw, th = size
    # Fit preserving aspect
    ratio = min(tw / w, th / h)
    nw = max(1, int(w * ratio))
    nh = max(1, int(h * ratio))
    return pygame.transform.smoothscale(img, (nw, nh))


def open_gallery_ui(
    *,
    screen: Surface,
    canvas: Surface,
    clock: pygame.time.Clock,
    font: pygame.font.Font,
    resolve_path: Callable[[str, list[str]], str],
    get_save_dir: Optional[Callable[[], Path]] = None,
) -> None:
    """Simple CG gallery: grid of thumbnails, click to preview; Esc/Right/Left navigate; Esc to exit.
    Non-persistent unlock: shows everything in cg folder.
    """
    # Load lists
    cg_files = _scan_cg_paths(resolve_path)
    bgm_files = _scan_bgm_paths(resolve_path)
    thumbs: List[Tuple[str, Surface]] = []
    cg_cats: Dict[str, str] = {}
    for fp in cg_files:
        try:
            # use cached thumb if available
            th = read_thumb(fp, get_save_dir)
            if th is None:
                img = pygame.image.load(resolve_path(fp, ["cg"]))
                try:
                    img = img.convert_alpha()
                except Exception:
                    img = img.convert()
                th = _thumb_for(img, (280, 160))
                # best-effort write
                try:
                    write_thumb(th, fp, get_save_dir)
                except Exception:
                    pass
            thumbs.append((fp, th))
            cg_cats[fp] = _cg_category_for(fp)
        except Exception:
            continue
    # Build categories list (with "全部" first)
    cat_names = sorted({cg_cats.get(fp, "未分类") for fp, _ in thumbs})
    categories: List[str] = ["全部"] + cat_names
    current_cat = 0

    selected = 0  # index within current view (filtered by category)
    preview: Optional[Surface] = None

    def _ensure_preview(idx: int) -> Optional[Surface]:
        nonlocal preview
        if not (0 <= idx < len(thumbs)):
            preview = None
            return None
        fp, _ = thumbs[idx]
        try:
            img = pygame.image.load(resolve_path(fp, ["cg"]))
            try:
                img = img.convert_alpha()
            except Exception:
                img = img.convert()
            # Fit to screen
            ratio = min(LOGICAL_SIZE[0]/img.get_width(), LOGICAL_SIZE[1]/img.get_height())
            nw = max(1, int(img.get_width()*ratio))
            nh = max(1, int(img.get_height()*ratio))
            preview = pygame.transform.smoothscale(img, (nw, nh))
            return preview
        except Exception:
            preview = None
            return None

    # simple grid layout
    cols = 4
    pad = 18
    cell_w, cell_h = 300, 180
    grid_x = (LOGICAL_SIZE[0] - (cols*cell_w + (cols-1)*pad)) // 2
    grid_y = 80

    running = True
    tab_idx = 0  # 0: CG, 1: BGM
    bgm_playing: Optional[int] = None
    bgm_volume: float = 0.8

    def _view_indices() -> List[int]:
        if tab_idx != 0:
            return []
        if not thumbs:
            return []
        if categories[current_cat] == "全部":
            return list(range(len(thumbs)))
        cat = categories[current_cat]
        return [i for i, (fp, _) in enumerate(thumbs) if cg_cats.get(fp, "未分类") == cat]

    def _selected_global_index() -> Optional[int]:
        vis = _view_indices()
        if not vis:
            return None
        idx = selected % len(vis)
        return vis[idx]
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    running = False
                elif event.key in (pygame.K_TAB,):
                    tab_idx = (tab_idx + 1) % len(TABS)
                    preview = None
                    selected = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if tab_idx == 0:
                        vis = _view_indices()
                        if vis:
                            selected = (selected + 1) % len(vis)
                            gi = _selected_global_index()
                            if gi is not None:
                                _ensure_preview(gi)
                    else:
                        if bgm_files:
                            selected = (selected + 1) % len(bgm_files)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if tab_idx == 0:
                        vis = _view_indices()
                        if vis:
                            selected = (selected - 1) % len(vis)
                            gi = _selected_global_index()
                            if gi is not None:
                                _ensure_preview(gi)
                    else:
                        if bgm_files:
                            selected = (selected - 1) % len(bgm_files)
                elif event.key in (pygame.K_q,):
                    if tab_idx == 0 and len(categories) > 1:
                        current_cat = (current_cat - 1) % len(categories)
                        selected = 0
                        preview = None
                elif event.key in (pygame.K_e,):
                    if tab_idx == 0 and len(categories) > 1:
                        current_cat = (current_cat + 1) % len(categories)
                        selected = 0
                        preview = None
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if tab_idx == 0:
                        # toggle preview overlay
                        gi = _selected_global_index()
                        if gi is None:
                            preview = None
                        elif preview is None:
                            _ensure_preview(gi)
                        else:
                            preview = None
                    else:
                        # play/stop BGM
                        try:
                            if bgm_playing == selected:
                                pygame.mixer.music.fadeout(200)
                                bgm_playing = None
                            else:
                                pygame.mixer.music.load(resolve_path(bgm_files[selected], ["bgm"]))
                                pygame.mixer.music.set_volume(bgm_volume)
                                pygame.mixer.music.play(-1)
                                bgm_playing = selected
                        except Exception:
                            pass
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    if tab_idx == 1:
                        bgm_volume = min(1.0, bgm_volume + 0.1)
                        try:
                            pygame.mixer.music.set_volume(bgm_volume)
                        except Exception:
                            pass
                elif event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE:
                    if tab_idx == 1:
                        bgm_volume = max(0.0, bgm_volume - 0.1)
                        try:
                            pygame.mixer.music.set_volume(bgm_volume)
                        except Exception:
                            pass
            if event.type == pygame.MOUSEWHEEL:
                if tab_idx == 0:
                    vis = _view_indices()
                    if event.y < 0 and vis:
                        selected = (selected + 1) % len(vis)
                    elif event.y > 0 and vis:
                        selected = (selected - 1) % len(vis)
                else:
                    if event.y < 0 and bgm_files:
                        selected = (selected + 1) % len(bgm_files)
                    elif event.y > 0 and bgm_files:
                        selected = (selected - 1) % len(bgm_files)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # map to canvas space
                win_w, win_h = screen.get_size()
                scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
                dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
                offx = (win_w - dst_w) // 2
                offy = (win_h - dst_h) // 2
                if offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h:
                    cx = int((mx - offx) / scale)
                    cy = int((my - offy) / scale)
                    # Check clicks on CG category tabs
                    if tab_idx == 0:
                        # Category tabs are drawn at y=60
                        cat_y = 60
                        cat_x = 40
                        cat_h = 30
                        cat_pad = 8
                        cat_w = 120
                        for i, cname in enumerate(categories):
                            tr = pygame.Rect(cat_x + i*(cat_w+cat_pad), cat_y, cat_w, cat_h)
                            if tr.collidepoint((cx, cy)):
                                current_cat = i
                                selected = 0
                                preview = None
                                break
                    if tab_idx == 0:
                        # find CG cell
                        relx, rely = cx - grid_x, cy - grid_y
                        if relx >= 0 and rely >= 0:
                            col = relx // (cell_w + pad)
                            row = rely // (cell_h + pad)
                            if 0 <= col < cols:
                                idx = row * cols + col
                                vis = _view_indices()
                                if 0 <= idx < len(vis):
                                    selected = idx
                                    # toggle preview
                                    gi = _selected_global_index()
                                    if gi is not None and preview is None:
                                        _ensure_preview(gi)
                                    else:
                                        preview = None
                    else:
                        # click to play/stop BGM line
                        list_rect = pygame.Rect(60, 100, LOGICAL_SIZE[0]-120, 40*max(1, len(bgm_files)))
                        if list_rect.collidepoint((cx, cy)):
                            idx = (cy - list_rect.y) // 40
                            if 0 <= idx < len(bgm_files):
                                selected = idx
                                try:
                                    if bgm_playing == selected:
                                        pygame.mixer.music.fadeout(200)
                                        bgm_playing = None
                                    else:
                                        pygame.mixer.music.load(resolve_path(bgm_files[selected], ["bgm"]))
                                        pygame.mixer.music.set_volume(bgm_volume)
                                        pygame.mixer.music.play(-1)
                                        bgm_playing = selected
                                except Exception:
                                    pass

        # base render behind
        canvas.fill((0, 0, 0))
        # Tabs
        tab_w = 120
        for i, tname in enumerate(TABS):
            tr = pygame.Rect(40 + i*(tab_w+12), 20, tab_w, 34)
            color = (80, 120, 200, 160) if i == tab_idx else (60, 60, 60, 120)
            tab = pygame.Surface((tr.width, tr.height), pygame.SRCALPHA)
            tab.fill(color)
            canvas.blit(tab, (tr.x, tr.y))
            label = font.render(tname, True, (240, 240, 240))
            canvas.blit(label, (tr.x + (tr.width - label.get_width())//2, tr.y + (tr.height - label.get_height())//2))

        if tab_idx == 0:
            title = font.render("CG 画廊 (Esc返回, 回车预览) TAB切换", True, (240, 240, 240))
            canvas.blit(title, (LOGICAL_SIZE[0]//2 - title.get_width()//2, 24))
            # Category tabs
            cat_y = 60
            cat_x = 40
            cat_h = 30
            cat_pad = 8
            cat_w = 120
            for i, cname in enumerate(categories):
                tr = pygame.Rect(cat_x + i*(cat_w+cat_pad), cat_y, cat_w, cat_h)
                color = (120, 160, 220, 160) if i == current_cat else (60, 60, 60, 120)
                tab = pygame.Surface((tr.width, tr.height), pygame.SRCALPHA)
                tab.fill(color)
                canvas.blit(tab, (tr.x, tr.y))
                label = font.render(cname, True, (240, 240, 240))
                canvas.blit(label, (tr.x + (tr.width - label.get_width())//2, tr.y + (tr.height - label.get_height())//2))
        else:
            title = font.render("BGM 鉴赏 (Enter播放/停止, +/-音量) TAB切换", True, (240, 240, 240))
            canvas.blit(title, (LOGICAL_SIZE[0]//2 - title.get_width()//2, 24))

        vis = _view_indices() if tab_idx == 0 else []
        if tab_idx == 0 and not vis:
            msg = font.render("未找到任何 CG", True, (220, 200, 200))
            canvas.blit(msg, (LOGICAL_SIZE[0]//2 - msg.get_width()//2, LOGICAL_SIZE[1]//2 - msg.get_height()//2))
        elif tab_idx == 0:
            # draw grid
            for vi, gi in enumerate(vis):
                fp, th = thumbs[gi]
                row = vi // cols
                col = vi % cols
                rx = grid_x + col * (cell_w + pad)
                ry = grid_y + row * (cell_h + pad)
                cell = pygame.Rect(rx, ry, cell_w, cell_h)
                # panel
                panel = pygame.Surface((cell.width, cell.height), pygame.SRCALPHA)
                panel.fill((0, 0, 0, 150))
                canvas.blit(panel, (cell.x, cell.y))
                pygame.draw.rect(canvas, (255, 255, 255), cell, 2)
                # thumb
                tw, thh = th.get_size()
                canvas.blit(th, (cell.x + (cell.width - tw)//2, cell.y + (cell.height - thh)//2))
                # lock overlay if not unlocked yet
                if not is_unlocked(fp, get_save_dir):
                    ov = pygame.Surface((cell.width, cell.height), pygame.SRCALPHA)
                    ov.fill((0, 0, 0, 120))
                    canvas.blit(ov, (cell.x, cell.y))
                    lock = font.render("未解锁", True, (240, 200, 200))
                    canvas.blit(lock, (cell.x + (cell.width - lock.get_width())//2, cell.y + (cell.height - lock.get_height())//2))
                if vi == selected:
                    try:
                        pygame.draw.rect(canvas, (200, 220, 255), cell, 3)
                    except Exception:
                        pass
        elif tab_idx == 1:
            # BGM list view
            list_rect = pygame.Rect(60, 100, LOGICAL_SIZE[0]-120, 40*max(1, len(bgm_files)))
            pygame.draw.rect(canvas, (255,255,255), list_rect, 2)
            y = list_rect.y + 6
            for i, fp in enumerate(bgm_files):
                row = pygame.Rect(list_rect.x + 6, y, list_rect.width - 12, 30)
                if i == selected:
                    hi = pygame.Surface((row.width, row.height), pygame.SRCALPHA)
                    hi.fill((90, 140, 220, 140))
                    canvas.blit(hi, (row.x, row.y))
                base = Path(fp).name
                mark = "▶ " if bgm_playing == i else "   "
                label = font.render(mark + base, True, (240,240,240))
                canvas.blit(label, (row.x + 6, row.y + 4))
                y += 34

        # preview overlay for CG
        if tab_idx == 0 and preview is not None:
            ov = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
            ov.fill((0, 0, 0, 180))
            canvas.blit(ov, (0, 0))
            pw, ph = preview.get_size()
            canvas.blit(preview, (LOGICAL_SIZE[0]//2 - pw//2, LOGICAL_SIZE[1]//2 - ph//2))

        # Info bar at bottom
        info_bar = pygame.Surface((LOGICAL_SIZE[0], 36), pygame.SRCALPHA)
        info_bar.fill((0, 0, 0, 140))
        canvas.blit(info_bar, (0, LOGICAL_SIZE[1]-36))
        if tab_idx == 0:
            gi = _selected_global_index()
            if gi is not None:
                fp, _ = thumbs[gi]
                base = Path(fp).name
                cat = cg_cats.get(fp, "未分类")
                unlocked = is_unlocked(fp, get_save_dir)
                text = f"文件: {base} | 分组: {cat} | 状态: {'已解锁' if unlocked else '未解锁'} | Q/E切换分组"
            else:
                text = "没有可显示的CG。Q/E切换分组"
        else:
            if bgm_files:
                base = Path(bgm_files[selected % max(1, len(bgm_files))]).name
                state = "播放中" if bgm_playing == (selected % max(1, len(bgm_files))) else "已停止"
                vol = int(bgm_volume * 100)
                text = f"曲目: {base} | 状态: {state} | 音量: {vol}%"
            else:
                text = "未找到任何 BGM"
        info_label = font.render(text, True, (240, 240, 240))
        canvas.blit(info_label, (16, LOGICAL_SIZE[1]-36 + (36 - info_label.get_height())//2))

        # present
        win_w, win_h = screen.get_size()
        scale = min(win_w / LOGICAL_SIZE[0], win_h / LOGICAL_SIZE[1])
        dst_w, dst_h = int(LOGICAL_SIZE[0] * scale), int(LOGICAL_SIZE[1] * scale)
        scaled = pygame.transform.smoothscale(canvas, (dst_w, dst_h))
        x = (win_w - dst_w) // 2
        y = (win_h - dst_h) // 2
        screen.fill((0, 0, 0))
        screen.blit(scaled, (x, y))
        pygame.display.flip()
        clock.tick(60)
