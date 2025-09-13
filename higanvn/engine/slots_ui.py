from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import pygame
from pygame import Surface

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def show_slots_menu(
    *,
    mode: str,
    total: int,
    canvas: Surface,
    screen: Surface,
    clock: pygame.time.Clock,
    hint_font: pygame.font.Font,
    error_font: pygame.font.Font,
    render_base: Callable[..., None],
    get_last_transform: Callable[[], Optional[tuple[float, int, int, int, int]]],
    read_slot_meta: Callable[[int], Optional[dict]],
    slot_thumb_path: Callable[[int], Path],
) -> Optional[int]:
    assert mode in ("save", "load")
    cols, rows = 3, max(1, (total + 2) // 3)
    margin_x, margin_y = 32, 64
    gap_x, gap_y = 16, 16
    avail_w = LOGICAL_SIZE[0] - 2 * margin_x - 40
    avail_h = LOGICAL_SIZE[1] - 2 * margin_y - 60
    cell_w = max(240, (avail_w - (cols - 1) * gap_x) // cols)
    cell_h = max(160, (avail_h - (rows - 1) * gap_y) // rows)
    panel_h = rows * cell_h + (rows - 1) * gap_y + 2 * margin_y
    panel = pygame.Rect(20, (LOGICAL_SIZE[1] - panel_h) // 2, LOGICAL_SIZE[0] - 40, panel_h)

    thumbs: Dict[int, Optional[Surface]] = {}
    metas: Dict[int, Optional[dict]] = {}
    for i in range(1, total + 1):
        metas[i] = read_slot_meta(i)
        tp = slot_thumb_path(i)
        try:
            thumbs[i] = pygame.image.load(str(tp)).convert()
        except Exception:
            thumbs[i] = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                lt = get_last_transform()
                if lt:
                    scale, offx, offy, dw, dh = lt
                    if offx <= mx <= offx + dw and offy <= my <= offy + dh:
                        cx = int((mx - offx) / scale)
                        cy = int((my - offy) / scale)
                    else:
                        cx, cy = -1, -1
                else:
                    cx, cy = mx, my
                if panel.collidepoint((cx, cy)):
                    gx = cx - panel.x - margin_x
                    gy = cy - panel.y - margin_y
                    if gx >= 0 and gy >= 0:
                        col = gx // (cell_w + gap_x)
                        row = gy // (cell_h + gap_y)
                        if 0 <= col < cols and 0 <= row < rows:
                            idx = row * cols + col + 1
                            if 1 <= idx <= total:
                                if mode == "load" and not metas.get(idx):
                                    continue
                                return idx
        # render base
        render_base(flip=False, tick=False)
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        canvas.blit(overlay, (0, 0))
        pygame.draw.rect(canvas, (10, 10, 10), panel)
        pygame.draw.rect(canvas, (255, 255, 255), panel, 2)
        title = error_font.render("存档槽位" if mode == "save" else "读取槽位", True, (255, 255, 255))
        canvas.blit(title, (panel.x + 12, panel.y + 10))

        y0 = panel.y + margin_y
        idx = 1
        for r in range(rows):
            x0 = panel.x + margin_x
            for c in range(cols):
                if idx > total:
                    break
                rect = pygame.Rect(x0, y0, cell_w, cell_h)
                pygame.draw.rect(canvas, (30, 30, 30), rect)
                pygame.draw.rect(canvas, (200, 200, 200), rect, 1)
                num_surf = hint_font.render(f"{idx:02d}", True, (200, 200, 200))
                canvas.blit(num_surf, (rect.x + 8, rect.y + 6))
                th = thumbs.get(idx)
                if th:
                    pad = 8
                    tgt_w = rect.width - 2 * pad
                    tgt_h = rect.height - 48
                    scaled = pygame.transform.smoothscale(th, (tgt_w, tgt_h))
                    canvas.blit(scaled, (rect.x + pad, rect.y + 28))
                else:
                    placeholder = hint_font.render("(空)", True, (100, 100, 100))
                    canvas.blit(placeholder, (rect.x + rect.width // 2 - placeholder.get_width() // 2, rect.y + rect.height // 2 - 10))
                meta = metas.get(idx)
                ts = meta.get("ts") if isinstance(meta, dict) else None
                label = meta.get("label") if isinstance(meta, dict) else None
                if ts:
                    ts_surf = hint_font.render(str(ts), True, (180, 180, 180))
                    canvas.blit(ts_surf, (rect.x + rect.width - ts_surf.get_width() - 8, rect.y + 6))
                if label:
                    # draw label under the slot number, trimmed if too long
                    lbl = str(label)
                    # simple trim: ensure it fits within rect width minus padding
                    maxw = rect.width - 16
                    trimmed = lbl
                    while hint_font.size(trimmed)[0] > maxw and len(trimmed) > 1:
                        trimmed = trimmed[:-1]
                    if trimmed != lbl and len(trimmed) > 1:
                        trimmed = trimmed[:-1] + "…"
                    lbl_surf = hint_font.render(trimmed, True, (200, 200, 220))
                    canvas.blit(lbl_surf, (rect.x + 8, rect.y + 6 + num_surf.get_height() + 2))
                x0 += cell_w + gap_x
                idx += 1
            y0 += cell_h + gap_y

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
