"""
Slots UI Modern - 现代风格存档/读取界面 v2

Features:
- 卡片式布局
- 缩略图预览
- 悬停/选中动画
- 渐变背景和发光效果
- 删除确认对话框
- 键盘导航支持
- 滚动支持（大量槽位时）
- 与 SaveManager 集成
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, List, Any, TYPE_CHECKING
import math

import pygame
from pygame import Surface

from .ui_theme import (
    Theme, draw_gradient_rect, draw_rounded_panel, 
    draw_text_with_glow, draw_glow_border
)

if TYPE_CHECKING:
    from .save_manager import SaveManager

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)


class SlotCard:
    """存档槽位卡片"""
    
    def __init__(self, slot_id: int, rect: pygame.Rect):
        self.slot_id = slot_id
        self.rect = rect
        self.hover = False
        self.selected = False
        self.hover_progress = 0.0
        self.select_progress = 0.0
        self.thumbnail: Optional[Surface] = None
        self.meta: Optional[dict] = None
        self.delete_confirm = False
        self.delete_progress = 0.0
    
    def update(self, dt: float):
        """更新动画状态"""
        # Hover animation
        target_hover = 1.0 if self.hover else 0.0
        self.hover_progress += (target_hover - self.hover_progress) * 10.0 * dt
        self.hover_progress = max(0.0, min(1.0, self.hover_progress))
        
        # Select animation
        target_select = 1.0 if self.selected else 0.0
        self.select_progress += (target_select - self.select_progress) * 8.0 * dt
        self.select_progress = max(0.0, min(1.0, self.select_progress))
        
        # Delete confirm animation
        target_delete = 1.0 if self.delete_confirm else 0.0
        self.delete_progress += (target_delete - self.delete_progress) * 12.0 * dt
        self.delete_progress = max(0.0, min(1.0, self.delete_progress))
    
    @property
    def is_empty(self) -> bool:
        return self.meta is None


class SlotsMenuState:
    """槽位菜单状态"""
    
    def __init__(self, mode: str, total: int, cols: int = 4):
        self.mode = mode
        self.total = total
        self.cols = cols
        self.selected_idx = 0
        self.scroll_offset = 0.0
        self.target_scroll = 0.0
        self.confirm_delete_id: Optional[int] = None
        self.page_size = 8  # 每页显示的槽位数
    
    def move_selection(self, dx: int, dy: int, cards: List[SlotCard]) -> None:
        """移动选择"""
        if not cards:
            return
        
        new_idx = self.selected_idx + dx + dy * self.cols
        if 0 <= new_idx < len(cards):
            self.selected_idx = new_idx
            self._ensure_visible(cards)
    
    def _ensure_visible(self, cards: List[SlotCard]) -> None:
        """确保选中项可见"""
        if not cards:
            return
        card = cards[self.selected_idx]
        # 简化：暂不实现滚动
        pass


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
    get_last_transform: Callable[[], Optional[Tuple[float, int, int, int, int]]],
    read_slot_meta: Callable[[int], Optional[dict]],
    slot_thumb_path: Callable[[int], Path],
    list_slots: Optional[Callable[[], List[int]]] = None,
    delete_slot: Optional[Callable[[int], bool]] = None,
    save_manager: Optional[Any] = None,  # SaveManager
) -> Optional[int]:
    """
    显示现代风格存档/读取界面。
    
    Args:
        mode: "save" 或 "load"
        total: 总槽位数
        canvas: 绘制目标 Surface
        screen: 屏幕 Surface
        clock: pygame Clock
        hint_font: 提示文字字体
        error_font: 标题字体
        render_base: 背景渲染函数
        get_last_transform: 获取坐标变换
        read_slot_meta: 读取槽位元数据
        slot_thumb_path: 获取缩略图路径
        list_slots: 列出有数据的槽位
        delete_slot: 删除槽位回调
        save_manager: SaveManager 实例（可选）
    
    Returns:
        选中的槽位号，或 None 表示取消
    """
    assert mode in ("save", "load")
    
    # 布局配置
    cols = 4
    rows = max(1, (total + cols - 1) // cols)
    margin_x = 60
    margin_y = 80
    gap_x = 20
    gap_y = 24
    
    # 计算卡片尺寸
    avail_w = LOGICAL_SIZE[0] - 2 * margin_x
    avail_h = LOGICAL_SIZE[1] - margin_y - 120
    cell_w = (avail_w - (cols - 1) * gap_x) // cols
    cell_h = (avail_h - (rows - 1) * gap_y) // rows
    cell_w = max(200, min(280, cell_w))
    cell_h = max(140, min(180, cell_h))
    
    # 创建卡片
    cards: List[SlotCard] = []
    start_x = (LOGICAL_SIZE[0] - (cols * cell_w + (cols - 1) * gap_x)) // 2
    start_y = margin_y + 60
    
    for i in range(total):
        row = i // cols
        col = i % cols
        x = start_x + col * (cell_w + gap_x)
        y = start_y + row * (cell_h + gap_y)
        card = SlotCard(i + 1, pygame.Rect(x, y, cell_w, cell_h))
        cards.append(card)
    
    # 加载槽位数据
    filled_slots: Optional[set] = None
    try:
        if list_slots:
            filled_slots = set(int(i) for i in list_slots())
    except Exception:
        filled_slots = None
    
    for card in cards:
        if filled_slots is not None and card.slot_id not in filled_slots:
            card.meta = None
            card.thumbnail = None
            continue
        
        # 优先使用 SaveManager
        if save_manager:
            try:
                meta_obj = save_manager.get_slot_meta(card.slot_id)
                if not meta_obj.is_empty:
                    card.meta = meta_obj.to_dict()
                    card.thumbnail = save_manager.get_thumbnail(card.slot_id)
                continue
            except Exception:
                pass
        
        # 回退到回调函数
        meta = read_slot_meta(card.slot_id)
        card.meta = meta
        
        if meta:
            tp = slot_thumb_path(card.slot_id)
            try:
                card.thumbnail = pygame.image.load(str(tp)).convert()
            except Exception:
                card.thumbnail = None
    
    # 状态
    state = SlotsMenuState(mode, total, cols)
    last_time = pygame.time.get_ticks()
    
    # 初始选择第一个有数据的槽位（读取模式）或第一个空槽位（保存模式）
    if mode == "load":
        for i, card in enumerate(cards):
            if not card.is_empty:
                state.selected_idx = i
                break
    else:
        for i, card in enumerate(cards):
            if card.is_empty:
                state.selected_idx = i
                break
    
    if cards:
        cards[state.selected_idx].selected = True
    
    while True:
        now = pygame.time.get_ticks()
        dt = (now - last_time) / 1000.0
        last_time = now
        
        # 获取鼠标位置
        mx, my = pygame.mouse.get_pos()
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
        
        # 更新卡片状态
        old_selected = state.selected_idx
        hovered_card: Optional[SlotCard] = None
        
        for i, card in enumerate(cards):
            card.hover = card.rect.collidepoint((cx, cy))
            card.selected = (i == state.selected_idx)
            if card.hover:
                hovered_card = card
            card.update(dt)
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            
            if event.type == pygame.KEYDOWN:
                if state.confirm_delete_id is not None:
                    # 删除确认模式
                    if event.key == pygame.K_y:
                        _do_delete(cards, state, delete_slot, save_manager, filled_slots)
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        _cancel_delete(cards, state)
                else:
                    # 正常导航模式
                    if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                        return None
                    
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        state.move_selection(-1, 0, cards)
                    
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        state.move_selection(1, 0, cards)
                    
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        state.move_selection(0, -1, cards)
                    
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state.move_selection(0, 1, cards)
                    
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        result = _handle_select(cards, state, mode)
                        if result is not None:
                            return result
                    
                    elif event.key == pygame.K_DELETE and delete_slot:
                        card = cards[state.selected_idx]
                        if not card.is_empty:
                            state.confirm_delete_id = card.slot_id
                            card.delete_confirm = True
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if state.confirm_delete_id is not None:
                    # 处理删除确认
                    confirm_card = next((c for c in cards if c.slot_id == state.confirm_delete_id), None)
                    if confirm_card:
                        result = _handle_delete_confirm_click(
                            confirm_card, cx, cy, cards, state, delete_slot, save_manager, filled_slots
                        )
                        if result == "done":
                            continue
                
                elif event.button == 1:  # 左键
                    if hovered_card:
                        # 更新选择
                        for i, card in enumerate(cards):
                            if card is hovered_card:
                                state.selected_idx = i
                                break
                        
                        result = _handle_select(cards, state, mode)
                        if result is not None:
                            return result
                
                elif event.button == 3:  # 右键删除
                    if hovered_card and not hovered_card.is_empty and delete_slot:
                        state.confirm_delete_id = hovered_card.slot_id
                        hovered_card.delete_confirm = True
        
        # 渲染
        render_base(flip=False, tick=False)
        
        # 半透明遮罩
        overlay = pygame.Surface(LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        canvas.blit(overlay, (0, 0))
        
        # 标题
        title_text = "保存进度" if mode == "save" else "读取进度"
        _draw_title(canvas, error_font, title_text, margin_y)
        
        # 绘制卡片
        for card in cards:
            _draw_slot_card(canvas, card, hint_font, now)
        
        # 底部提示
        if state.confirm_delete_id is not None:
            hint_text = "按 Y 确认删除，N 或 ESC 取消"
        else:
            hints = ["↑↓←→ 选择", "回车 确认"]
            if delete_slot:
                hints.append("Delete 删除")
            hints.append("ESC 返回")
            hint_text = "  |  ".join(hints)
        
        hint_surf = hint_font.render(hint_text, True, Theme.TEXT_DIM)
        canvas.blit(hint_surf, ((LOGICAL_SIZE[0] - hint_surf.get_width()) // 2, LOGICAL_SIZE[1] - 50))
        
        # 缩放到窗口
        _present(canvas, screen)
        clock.tick(60)


def _draw_title(canvas: Surface, font: pygame.font.Font, text: str, margin_y: int) -> None:
    """绘制标题"""
    title_surf = font.render(text, True, Theme.TEXT_PRIMARY)
    title_x = (LOGICAL_SIZE[0] - title_surf.get_width()) // 2
    title_y = margin_y // 2 - title_surf.get_height() // 2
    
    # 发光效果
    for i in range(3):
        glow = font.render(text, True, Theme.PRIMARY_LIGHT)
        glow.set_alpha(30 - i * 10)
        canvas.blit(glow, (title_x - i, title_y - i))
        canvas.blit(glow, (title_x + i, title_y + i))
    
    canvas.blit(title_surf, (title_x, title_y))


def _draw_slot_card(
    canvas: Surface,
    card: SlotCard,
    font: pygame.font.Font,
    time_ms: int,
) -> None:
    """绘制单个存档卡片"""
    rect = card.rect
    hover_t = card.hover_progress
    select_t = card.select_progress
    
    # 综合动画因子
    anim_t = max(hover_t, select_t)
    
    # 悬停时的缩放和偏移效果
    scale_factor = 1.0 + anim_t * 0.03
    offset_y = -anim_t * 5
    
    # 计算实际绘制矩形
    scaled_w = int(rect.width * scale_factor)
    scaled_h = int(rect.height * scale_factor)
    draw_rect = pygame.Rect(
        rect.centerx - scaled_w // 2,
        rect.centery - scaled_h // 2 + int(offset_y),
        scaled_w,
        scaled_h
    )
    
    # 卡片背景色
    if card.is_empty:
        bg_color = (30, 35, 50, 200)
        border_color = Theme.PANEL_BORDER
    else:
        bg_color = (40, 50, 70, 220)
        border_color = Theme.PRIMARY
    
    # 选中/悬停时的边框颜色
    if select_t > 0.3 or hover_t > 0.3:
        border_color = Theme.ACCENT
    
    # 发光效果
    if anim_t > 0.1:
        glow_alpha = int(80 * anim_t)
        glow_rect = draw_rect.inflate(12, 12)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        
        # 渐变发光
        glow_color = Theme.ACCENT if select_t > 0.3 else Theme.PRIMARY_LIGHT
        pygame.draw.rect(
            glow_surf, (*glow_color, glow_alpha), 
            (0, 0, glow_rect.width, glow_rect.height), 
            border_radius=14
        )
        canvas.blit(glow_surf, glow_rect.topleft)
    
    # 卡片主体
    draw_rounded_panel(
        canvas, draw_rect, bg_color,
        border_color=border_color,
        border_width=2 if anim_t < 0.3 else 3,
        border_radius=10
    )
    
    # 槽位号
    slot_text = f"{card.slot_id:02d}"
    slot_color = Theme.ACCENT if not card.is_empty else Theme.TEXT_DIM
    slot_surf = font.render(slot_text, True, slot_color)
    canvas.blit(slot_surf, (draw_rect.x + 10, draw_rect.y + 8))
    
    if card.is_empty:
        # 空槽位
        empty_text = "— 空 —"
        empty_surf = font.render(empty_text, True, Theme.TEXT_DIM)
        canvas.blit(empty_surf, (
            draw_rect.centerx - empty_surf.get_width() // 2,
            draw_rect.centery - empty_surf.get_height() // 2
        ))
    else:
        # 缩略图区域
        thumb_margin = 8
        thumb_top = draw_rect.y + 32
        thumb_w = draw_rect.width - thumb_margin * 2
        thumb_h = draw_rect.height - 60
        thumb_rect = pygame.Rect(draw_rect.x + thumb_margin, thumb_top, thumb_w, thumb_h)
        
        if card.thumbnail:
            try:
                scaled_thumb = pygame.transform.smoothscale(card.thumbnail, (thumb_w, thumb_h))
                canvas.blit(scaled_thumb, thumb_rect.topleft)
            except Exception:
                pygame.draw.rect(canvas, (50, 50, 60), thumb_rect)
        else:
            pygame.draw.rect(canvas, (50, 50, 60), thumb_rect)
            no_img = font.render("无预览", True, Theme.TEXT_DIM)
            canvas.blit(no_img, (
                thumb_rect.centerx - no_img.get_width() // 2,
                thumb_rect.centery - no_img.get_height() // 2
            ))
        
        # 缩略图边框
        pygame.draw.rect(canvas, Theme.PANEL_BORDER, thumb_rect, 1, border_radius=4)
        
        # 元数据
        if card.meta:
            # 时间戳
            ts = card.meta.get("ts", "")
            if ts:
                ts_short = str(ts)[:16] if len(str(ts)) > 16 else str(ts)
                ts_surf = font.render(ts_short, True, Theme.TEXT_SECONDARY)
                canvas.blit(ts_surf, (draw_rect.right - ts_surf.get_width() - 10, draw_rect.y + 8))
            
            # 标签名
            label = card.meta.get("label", "")
            if label:
                label_str = str(label)
                max_w = draw_rect.width - 20
                while font.size(label_str)[0] > max_w and len(label_str) > 1:
                    label_str = label_str[:-1]
                if label_str != str(label):
                    label_str = label_str[:-2] + "…"
                
                label_surf = font.render(label_str, True, Theme.PRIMARY_LIGHT)
                canvas.blit(label_surf, (draw_rect.x + 10, draw_rect.bottom - 24))
    
    # 删除确认覆盖层
    if card.delete_confirm and card.delete_progress > 0.1:
        _draw_delete_confirm(canvas, draw_rect, font, card.delete_progress)


def _draw_delete_confirm(
    canvas: Surface, 
    rect: pygame.Rect, 
    font: pygame.font.Font,
    progress: float
) -> None:
    """绘制删除确认覆盖层"""
    alpha = int(200 * progress)
    
    # 遮罩
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    overlay.fill((20, 20, 30, alpha))
    canvas.blit(overlay, rect.topleft)
    
    if progress < 0.5:
        return
    
    # 警告文字
    text_alpha = int(255 * (progress - 0.5) * 2)
    
    warn_text = "删除此存档?"
    warn_surf = font.render(warn_text, True, (255, 100, 100))
    warn_surf.set_alpha(text_alpha)
    canvas.blit(warn_surf, (
        rect.centerx - warn_surf.get_width() // 2,
        rect.centery - 25
    ))
    
    # 提示
    hint_text = "Y=是  N=否"
    hint_surf = font.render(hint_text, True, (200, 200, 200))
    hint_surf.set_alpha(text_alpha)
    canvas.blit(hint_surf, (
        rect.centerx - hint_surf.get_width() // 2,
        rect.centery + 5
    ))


def _handle_select(cards: List[SlotCard], state: SlotsMenuState, mode: str) -> Optional[int]:
    """处理选择操作"""
    if not cards or state.selected_idx >= len(cards):
        return None
    
    card = cards[state.selected_idx]
    
    if mode == "load" and card.is_empty:
        # 读取模式下不能选择空槽位
        return None
    
    return card.slot_id


def _handle_delete_confirm_click(
    card: SlotCard,
    cx: int, cy: int,
    cards: List[SlotCard],
    state: SlotsMenuState,
    delete_slot: Optional[Callable[[int], bool]],
    save_manager: Optional[Any],
    filled_slots: Optional[set],
) -> str:
    """处理删除确认点击"""
    rect = card.rect
    
    # 简化：点击卡片内部触发删除，外部取消
    if rect.collidepoint((cx, cy)):
        # 在卡片内点击 - 可以添加按钮检测
        # 暂时：点击确认删除
        pass
    else:
        # 卡片外点击 - 取消
        _cancel_delete(cards, state)
        return "done"
    
    return ""


def _do_delete(
    cards: List[SlotCard],
    state: SlotsMenuState,
    delete_slot: Optional[Callable[[int], bool]],
    save_manager: Optional[Any],
    filled_slots: Optional[set],
) -> None:
    """执行删除"""
    if state.confirm_delete_id is None:
        return
    
    card = next((c for c in cards if c.slot_id == state.confirm_delete_id), None)
    if not card:
        return
    
    success = False
    
    # 优先使用 SaveManager
    if save_manager:
        try:
            success = save_manager.delete_slot(state.confirm_delete_id)
        except Exception:
            pass
    elif delete_slot:
        try:
            success = delete_slot(state.confirm_delete_id)
        except Exception:
            pass
    
    if success:
        card.meta = None
        card.thumbnail = None
        if filled_slots is not None:
            filled_slots.discard(state.confirm_delete_id)
    
    _cancel_delete(cards, state)


def _cancel_delete(cards: List[SlotCard], state: SlotsMenuState) -> None:
    """取消删除"""
    if state.confirm_delete_id is not None:
        card = next((c for c in cards if c.slot_id == state.confirm_delete_id), None)
        if card:
            card.delete_confirm = False
    state.confirm_delete_id = None


def _present(canvas: Surface, screen: Surface) -> None:
    """呈现画面到屏幕"""
    win_w, win_h = screen.get_size()
    cw, ch = canvas.get_size()
    scale = min(win_w / cw, win_h / ch)
    dst_w, dst_h = int(cw * scale), int(ch * scale)
    scaled = pygame.transform.smoothscale(canvas, (dst_w, dst_h))
    x = (win_w - dst_w) // 2
    y = (win_h - dst_h) // 2
    screen.fill((0, 0, 0))
    screen.blit(scaled, (x, y))
    pygame.display.flip()
