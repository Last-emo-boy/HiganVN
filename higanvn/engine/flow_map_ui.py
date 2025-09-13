from __future__ import annotations

from typing import Dict, Any, Callable, Optional, Tuple
import math
import pygame

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


def _compute_layers(flow: Dict[str, Any]) -> list[list[str]]:
    nodes: list[str] = list(flow.get("order") or flow.get("nodes") or [])
    edges = flow.get("edges") or []
    if not nodes:
        return []
    # Build adjacency from src->dst (ignore kind for layering)
    adj: Dict[str, list[str]] = {n: [] for n in nodes}
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    for e in edges:
        s = e.get("src")
        d = e.get("dst")
        if s == "__start__" and d in adj:
            indeg[d] = max(0, indeg.get(d, 0))
            continue
        if s in adj and d in adj:
            adj[s].append(d)
            indeg[d] = indeg.get(d, 0) + 1
    # BFS layering from nodes with indeg==0 (or the first node if all have indeg>0)
    frontier = [n for n in nodes if indeg.get(n, 0) == 0] or [nodes[0]]
    visited = set()
    layers: list[list[str]] = []
    while frontier:
        cur_layer: list[str] = []
        next_frontier: list[str] = []
        for n in frontier:
            if n in visited:
                continue
            visited.add(n)
            cur_layer.append(n)
            for m in adj.get(n, []):
                if m not in visited:
                    next_frontier.append(m)
        if cur_layer:
            layers.append(cur_layer)
        frontier = next_frontier
    # Append any isolated/unvisited nodes at the end
    rest = [n for n in nodes if n not in visited]
    if rest:
        layers.append(rest)
    return layers


def _layout_nodes(flow: Dict[str, Any]) -> dict[str, Tuple[int, int]]:
    layers = _compute_layers(flow)
    if not layers:
        return {}
    margin_x, margin_y = 140, 90
    usable_w = max(0, LOGICAL_SIZE[0] - margin_x * 2)
    usable_h = max(0, LOGICAL_SIZE[1] - margin_y * 2)
    L = max(1, len(layers))
    # Horizontal spacing by layers, left to right
    x_step = usable_w // max(1, L - 1) if L > 1 else 0
    pos: dict[str, Tuple[int, int]] = {}
    for li, layer in enumerate(layers):
        # Vertical positions within a layer (centered)
        count = max(1, len(layer))
        y_step = usable_h // max(1, count)
        x = margin_x + li * x_step
        # Center the group vertically
        base_y = margin_y + (usable_h - (y_step * (count - 1))) // 2
        for idx, name in enumerate(layer):
            y = base_y + idx * y_step
            pos[name] = (x, y)
    return pos


def show_flow_map(
    *,
    screen: pygame.Surface,
    canvas: pygame.Surface,
    clock: pygame.time.Clock,
    font: pygame.font.Font,
    error_font: pygame.font.Font,
    render_base: Callable[..., None],
    get_last_transform: Callable[[], Optional[tuple[float, int, int, int, int]]],
    flow: Dict[str, Any],
    visited_labels: set[str],
    slot_thumb_for_label: Callable[[str], Optional[pygame.Surface]],
) -> None:
    nodes = flow.get("order") or flow.get("nodes") or []
    edges = flow.get("edges") or []
    pos = _layout_nodes(flow)

    selected: Optional[str] = None
    running = True
    # Flush pending events so the key that opened the overlay doesn't close it immediately
    try:
        pygame.event.clear()
    except Exception:
        pass
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB, pygame.K_m):
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mp = _canvas_mouse(get_last_transform())
                if mp:
                    cx, cy = mp
                    for name, (nx, ny) in pos.items():
                        r = pygame.Rect(nx - 80, ny - 60, 160, 120)
                        if r.collidepoint((cx, cy)):
                            selected = name
                            break
        # draw the overlay frame
        render_base(flip=False, tick=False)
        # draw semi-transparent overlay
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        canvas.blit(overlay, (0, 0))
        _draw_grid(canvas)

        # edges with arrowheads (left-to-right)
        for e in edges:
            src = e.get("src")
            dst = e.get("dst")
            if not src or not dst or src not in pos or dst not in pos:
                continue
            sx, sy = pos[src]
            dx, dy = pos[dst]
            color = (120, 120, 120) if e.get("kind") == "next" else (90, 140, 200)
            _draw_curved_arrow(canvas, (sx, sy), (dx, dy), color)

        # nodes
        for name, (nx, ny) in pos.items():
            thumb = slot_thumb_for_label(name) if name in visited_labels else None
            rect = pygame.Rect(nx - 90, ny - 58, 180, 116)
            hovered = _is_hover(get_last_transform, rect)
            # shadow
            _rounded_rect(canvas, rect.move(4, 4), (0, 0, 0, 120), 10)
            # card background
            bg_col = (28, 32, 40) if not hovered else (36, 40, 50)
            _rounded_rect(canvas, rect, bg_col, 10, border=2, border_col=(70, 80, 96))
            # thumb or placeholder
            inner = rect.inflate(-10, -28)
            if thumb is not None:
                t = pygame.transform.smoothscale(thumb, (inner.width, inner.height))
                canvas.blit(t, inner)
            else:
                ph = font.render("?", True, (230, 230, 230))
                pr = ph.get_rect(center=inner.center)
                canvas.blit(ph, pr)
            # caption strip
            cap_bar = pygame.Surface((rect.width, 22), pygame.SRCALPHA)
            cap_bar.fill((0, 0, 0, 110))
            canvas.blit(cap_bar, (rect.x, rect.bottom - 22))
            cap = font.render(name, True, (240, 240, 240))
            canvas.blit(cap, (rect.x + 8, rect.bottom - 20))
            # state border
            border_col = (80, 140, 90) if name in visited_labels else (120, 120, 120)
            if selected == name:
                border_col = (255, 215, 0)
                glow = rect.inflate(10, 10)
                _rounded_rect(canvas, glow, (255, 215, 0, 30), 14)
            pygame.draw.rect(canvas, border_col, rect, 2, border_radius=10)

        # hint text
        hint = error_font.render("分支图（M 关闭 / 点击节点高亮）", True, (255, 255, 255))
        canvas.blit(hint, (16, 16))

        # present each frame
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


def _canvas_mouse(last_transform: Optional[tuple[float, int, int, int, int]]) -> Optional[tuple[int, int]]:
    if not last_transform:
        return None
    mx, my = pygame.mouse.get_pos()
    scale, offx, offy, dst_w, dst_h = last_transform
    if not (offx <= mx <= offx + dst_w and offy <= my <= offy + dst_h):
        return None
    cx = int((mx - offx) / scale)
    cy = int((my - offy) / scale)
    return (cx, cy)


def _rounded_rect(surface: pygame.Surface, rect: pygame.Rect, color, radius: int, *, border: int = 0, border_col=None):
    pygame.draw.rect(surface, color, rect, 0, border_radius=radius)
    if border > 0:
        pygame.draw.rect(surface, border_col or (255, 255, 255), rect, border, border_radius=radius)


def _draw_arrow(surface: pygame.Surface, start: Tuple[int, int], end: Tuple[int, int], color):
    sx, sy = start
    ex, ey = end
    pygame.draw.line(surface, color, (sx, sy), (ex, ey), 2)
    # arrowhead
    ang = math.atan2(ey - sy, ex - sx)
    size = 10
    left = (ex - size * math.cos(ang) + size * 0.5 * math.sin(ang), ey - size * math.sin(ang) - size * 0.5 * math.cos(ang))
    right = (ex - size * math.cos(ang) - size * 0.5 * math.sin(ang), ey - size * math.sin(ang) + size * 0.5 * math.cos(ang))
    pygame.draw.polygon(surface, color, [(ex, ey), left, right])


def _draw_curved_arrow(surface: pygame.Surface, start: Tuple[int, int], end: Tuple[int, int], color):
    sx, sy = start
    ex, ey = end
    # Quadratic Bezier with a horizontal mid control
    mx = (sx + ex) / 2
    # Offset control point a bit vertically to create nice bend
    ctrl = (mx, sy + (ey - sy) * 0.2)
    points = []
    steps = 18
    for i in range(steps + 1):
        t = i / steps
        # Quadratic Bezier: B(t) = (1-t)^2 P0 + 2(1-t)t C + t^2 P1
        x = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * ctrl[0] + t * t * ex
        y = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * ctrl[1] + t * t * ey
        points.append((int(x), int(y)))
    # Draw the curve
    if len(points) >= 2:
        pygame.draw.aalines(surface, color, False, points, True)
        # Arrowhead angle from last segment
        (x1, y1), (x2, y2) = points[-2], points[-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        size = 10
        left = (x2 - size * math.cos(ang) + size * 0.5 * math.sin(ang), y2 - size * math.sin(ang) - size * 0.5 * math.cos(ang))
        right = (x2 - size * math.cos(ang) - size * 0.5 * math.sin(ang), y2 - size * math.sin(ang) + size * 0.5 * math.cos(ang))
        pygame.draw.polygon(surface, color, [(x2, y2), left, right])


def _draw_grid(surface: pygame.Surface):
    grid = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
    gap = 48
    col = (255, 255, 255, 14)
    for x in range(0, LOGICAL_SIZE[0], gap):
        pygame.draw.line(grid, col, (x, 0), (x, LOGICAL_SIZE[1]))
    for y in range(0, LOGICAL_SIZE[1], gap):
        pygame.draw.line(grid, col, (0, y), (LOGICAL_SIZE[0], y))
    surface.blit(grid, (0, 0))


def _is_hover(get_last_transform: Callable[[], Optional[tuple[float, int, int, int, int]]], rect: pygame.Rect) -> bool:
    mp = _canvas_mouse(get_last_transform())
    return bool(mp and rect.collidepoint(mp))
