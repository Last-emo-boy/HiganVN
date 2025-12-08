"""
Text Panel - 现代视觉小说风格对话框
采用渐变背景、发光边框、精美排版
支持富文本标签渲染
"""
from __future__ import annotations

from typing import Optional, Tuple, List, Callable, Any
import math

import pygame
from pygame import Surface

from higanvn.ui.textwrap import wrap_text_generic
from higanvn.engine.rich_text import (
    RichTextParser, RichTextSegment, TextStyle, EffectType,
    parse_rich_text, strip_rich_tags, get_plain_length,
)

LOGICAL_SIZE: Tuple[int, int] = (1280, 720)

# 对话框布局常量
PANEL_MARGIN_X = 40
PANEL_MARGIN_BOTTOM = 30
PANEL_HEIGHT = 200
PANEL_BORDER_RADIUS = 16
NAME_BOX_HEIGHT = 38
NAME_BOX_OFFSET_Y = -32

# 主题色板
class Theme:
    PRIMARY = (100, 140, 220)
    PRIMARY_DARK = (60, 90, 160)
    PRIMARY_LIGHT = (140, 180, 255)
    ACCENT = (255, 200, 100)
    NAME_COLOR = (255, 235, 180)
    NAME_GLOW = (255, 200, 100)
    TEXT_PRIMARY = (255, 255, 255)
    PANEL_BG = (15, 20, 35)
    PANEL_BG_ALPHA = 220
    PANEL_BORDER = (80, 100, 140)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    def measure(s: str) -> int:
        try:
            return font.size(s)[0]
        except Exception:
            return 0
    return wrap_text_generic(text or "", measure, int(max_width))


def wrap_rich_text(
    text: str, 
    font: pygame.font.Font, 
    max_width: int,
    font_getter: Optional[Callable[[int, bool, bool], pygame.font.Font]] = None,
    default_size: int = 24,
) -> List[List[RichTextSegment]]:
    """
    将富文本换行为多行段落列表
    
    Args:
        text: 带富文本标签的原始文本
        font: 默认字体
        max_width: 最大宽度
        font_getter: 字体获取函数
        default_size: 默认字体大小
    
    Returns:
        List[List[RichTextSegment]] - 每行的段落列表
    """
    if not text:
        return []
    
    # 解析富文本
    segments = parse_rich_text(text)
    if not segments:
        return []
    
    lines: List[List[RichTextSegment]] = []
    current_line: List[RichTextSegment] = []
    current_width = 0
    
    for seg in segments:
        # 获取字体
        if font_getter:
            size = int(default_size * seg.style.size_scale)
            seg_font = font_getter(size, seg.style.bold, seg.style.italic)
        else:
            seg_font = font
        
        # 按单词/字符分割
        words = []
        current_word = ""
        for char in seg.text:
            if char in ' \t':
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)
            elif char == '\n':
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append('\n')
            else:
                current_word += char
        if current_word:
            words.append(current_word)
        
        for word in words:
            if word == '\n':
                # 强制换行
                if current_line:
                    lines.append(current_line)
                current_line = []
                current_width = 0
                continue
            
            try:
                word_width = seg_font.size(word)[0]
            except Exception:
                word_width = len(word) * 10
            
            # 检查是否需要换行
            if current_width + word_width > max_width and current_line:
                lines.append(current_line)
                current_line = []
                current_width = 0
                # 跳过行首空格
                if word.strip() == '':
                    continue
            
            # 添加到当前行
            if current_line and current_line[-1].style == seg.style:
                # 合并相同样式
                last_seg = current_line[-1]
                current_line[-1] = RichTextSegment(
                    text=last_seg.text + word,
                    style=last_seg.style,
                    pause_ms=last_seg.pause_ms,
                    speed_multiplier=last_seg.speed_multiplier,
                    instant=last_seg.instant,
                )
            else:
                # 新段落
                current_line.append(RichTextSegment(
                    text=word,
                    style=seg.style,
                    pause_ms=seg.pause_ms,
                    speed_multiplier=seg.speed_multiplier,
                    instant=seg.instant,
                ))
            current_width += word_width
    
    if current_line:
        lines.append(current_line)
    
    return lines


def _draw_gradient_rect(
    surface: Surface,
    rect: pygame.Rect,
    color_top: Tuple[int, int, int, int],
    color_bottom: Tuple[int, int, int, int],
    border_radius: int = 0,
) -> None:
    """绘制垂直渐变矩形"""
    temp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        a = int(color_top[3] + (color_bottom[3] - color_top[3]) * t)
        pygame.draw.line(temp, (r, g, b, a), (0, y), (rect.width, y))
    if border_radius > 0:
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.width, rect.height), border_radius=border_radius)
        temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(temp, rect.topleft)


def render_rich_text_line(
    segments: List[RichTextSegment],
    font: pygame.font.Font,
    font_getter: Optional[Callable[[int, bool, bool], pygame.font.Font]],
    default_size: int,
    default_color: Tuple[int, int, int],
    time_ms: int,
    revealed_chars: Optional[int] = None,
    text_outline: bool = False,
    text_shadow: bool = False,
    shadow_offset: Tuple[int, int] = (2, 2),
) -> Tuple[Surface, int]:
    """
    渲染一行富文本
    
    Args:
        segments: 这一行的段落列表
        font: 默认字体
        font_getter: 字体获取函数
        default_size: 默认字体大小
        default_color: 默认颜色
        time_ms: 当前时间（用于动画）
        revealed_chars: 已显示字符数
        text_outline: 是否启用描边
        text_shadow: 是否启用阴影
        shadow_offset: 阴影偏移
    
    Returns:
        (渲染后的Surface, 总字符数)
    """
    if not segments:
        return pygame.Surface((1, 1), pygame.SRCALPHA), 0
    
    # 计算行尺寸
    total_width = 0
    max_height = 0
    total_chars = 0
    
    for seg in segments:
        if font_getter:
            size = int(default_size * seg.style.size_scale)
            seg_font = font_getter(size, seg.style.bold, seg.style.italic)
        else:
            seg_font = font
        
        try:
            w, h = seg_font.size(seg.text)
        except Exception:
            w, h = len(seg.text) * 10, default_size
        
        total_width += w
        max_height = max(max_height, h)
        total_chars += len(seg.text)
    
    if total_width <= 0:
        total_width = 1
    if max_height <= 0:
        max_height = default_size
    
    # 创建 Surface（加边距用于效果）
    margin = 8
    surface = pygame.Surface((total_width + margin * 2, max_height + margin * 2), pygame.SRCALPHA)
    
    x = margin
    char_index = 0
    
    for seg in segments:
        # 检查显示限制
        if revealed_chars is not None and char_index >= revealed_chars:
            break
        
        # 计算可见文本
        seg_len = len(seg.text)
        if revealed_chars is not None:
            remaining = revealed_chars - char_index
            if remaining <= 0:
                break
            visible_text = seg.text[:remaining]
        else:
            visible_text = seg.text
        
        if not visible_text:
            char_index += seg_len
            continue
        
        # 获取字体
        if font_getter:
            size = int(default_size * seg.style.size_scale)
            seg_font = font_getter(size, seg.style.bold, seg.style.italic)
        else:
            seg_font = font
            size = default_size
        
        style = seg.style
        
        # 逐字符渲染（用于动画效果）
        for i, char in enumerate(visible_text):
            dx, dy = 0, 0
            char_color = style.color or default_color
            char_alpha = 255
            
            # 抖动效果
            if style.effect == EffectType.SHAKE:
                amp = style.effect_amplitude
                spd = style.effect_speed
                dx = int(amp * math.sin(time_ms * spd / 1000 + i * 0.5))
                dy = int(amp * math.cos(time_ms * spd / 1000 * 1.3 + i * 0.7))
            
            # 波浪效果
            elif style.effect == EffectType.WAVE:
                amp = style.effect_amplitude
                spd = style.effect_speed
                dy = int(amp * math.sin(time_ms * spd / 1000 + i * 0.3))
            
            # 彩虹效果
            elif style.effect == EffectType.RAINBOW:
                hue = ((time_ms / 10) + i * 20) % 360
                char_color = _hue_to_rgb(hue)
            
            # 渐变透明效果
            elif style.effect == EffectType.FADE:
                phase = math.sin(time_ms / 500 + i * 0.2)
                char_alpha = int(128 + 127 * phase)
            
            try:
                char_width = seg_font.size(char)[0]
            except Exception:
                char_width = size // 2
            
            char_y = margin + (max_height - size) // 2
            
            # 阴影
            if text_shadow or style.shadow:
                shadow_color = style.shadow_color if style.shadow else (0, 0, 0)
                shadow_surf = seg_font.render(char, True, shadow_color)
                sox, soy = style.shadow_offset if style.shadow else shadow_offset
                surface.blit(shadow_surf, (x + dx + sox, char_y + dy + soy))
            
            # 描边
            if text_outline or style.outline_color:
                outline_color = style.outline_color or (0, 0, 0)
                outline_surf = seg_font.render(char, True, outline_color)
                width = style.outline_width if style.outline_color else 1
                for odx in range(-width, width + 1):
                    for ody in range(-width, width + 1):
                        if odx == 0 and ody == 0:
                            continue
                        surface.blit(outline_surf, (x + dx + odx, char_y + dy + ody))
            
            # 主文字
            char_surf = seg_font.render(char, True, char_color)
            if char_alpha < 255:
                char_surf.set_alpha(char_alpha)
            surface.blit(char_surf, (x + dx, char_y + dy))
            
            # 下划线
            if style.underline:
                underline_y = char_y + dy + size - 2
                pygame.draw.line(surface, char_color, 
                               (x + dx, underline_y), 
                               (x + dx + char_width, underline_y), 1)
            
            # 删除线
            if style.strikethrough:
                strike_y = char_y + dy + size // 2
                pygame.draw.line(surface, char_color,
                               (x + dx, strike_y),
                               (x + dx + char_width, strike_y), 1)
            
            x += char_width
        
        char_index += seg_len
    
    return surface, total_chars


def _hue_to_rgb(hue: float) -> Tuple[int, int, int]:
    """HSV 转 RGB (S=1, V=1)"""
    h = hue / 60.0
    i = int(h) % 6
    f = h - int(h)
    
    if i == 0:
        return (255, int(255 * f), 0)
    elif i == 1:
        return (int(255 * (1 - f)), 255, 0)
    elif i == 2:
        return (0, 255, int(255 * f))
    elif i == 3:
        return (0, int(255 * (1 - f)), 255)
    elif i == 4:
        return (int(255 * f), 0, 255)
    else:
        return (255, 0, int(255 * (1 - f)))


def draw_text_panel(
    canvas: Surface,
    font: pygame.font.Font,
    hint_font: pygame.font.Font,
    name: Optional[str],
    text: str,
    effect: Optional[str],
    typing_enabled: bool,
    fast_forward: bool,
    line_start_ts: int,
    line_full_ts: Optional[int],
    reveal_instant: bool,
    panel_alpha: Optional[int] = None,
    text_outline: Optional[bool] = None,
    text_shadow: Optional[bool] = None,
    text_shadow_offset: Optional[Tuple[int, int]] = None,
    rich_text_enabled: bool = True,
    font_getter: Optional[Callable[[int, bool, bool], pygame.font.Font]] = None,
    default_font_size: int = 24,
) -> tuple[bool, int, Optional[int]]:
    """绘制现代风格对话框（支持富文本）"""
    
    now = pygame.time.get_ticks()
    
    # ========================================================================
    # 主面板
    # ========================================================================
    panel_rect = pygame.Rect(
        PANEL_MARGIN_X,
        LOGICAL_SIZE[1] - PANEL_HEIGHT - PANEL_MARGIN_BOTTOM,
        LOGICAL_SIZE[0] - PANEL_MARGIN_X * 2,
        PANEL_HEIGHT
    )
    
    alpha = min(255, max(0, panel_alpha if panel_alpha is not None else Theme.PANEL_BG_ALPHA))
    
    # 创建渐变面板
    panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    _draw_gradient_rect(
        panel_surf,
        pygame.Rect(0, 0, panel_rect.width, panel_rect.height),
        (*Theme.PANEL_BG, alpha),
        (Theme.PANEL_BG[0] + 15, Theme.PANEL_BG[1] + 20, Theme.PANEL_BG[2] + 30, alpha),
        border_radius=PANEL_BORDER_RADIUS
    )
    
    # 顶部高光线
    highlight = pygame.Surface((panel_rect.width - 40, 2), pygame.SRCALPHA)
    for x in range(highlight.get_width()):
        t = 1 - abs(x - highlight.get_width() / 2) / (highlight.get_width() / 2)
        a = int(80 * t * t)
        highlight.set_at((x, 0), (*Theme.PRIMARY_LIGHT, a))
        highlight.set_at((x, 1), (*Theme.PRIMARY_LIGHT, a // 2))
    panel_surf.blit(highlight, (20, 4))
    
    # 底部装饰线
    bottom_line = pygame.Surface((panel_rect.width - 80, 1), pygame.SRCALPHA)
    for x in range(bottom_line.get_width()):
        t = 1 - abs(x - bottom_line.get_width() / 2) / (bottom_line.get_width() / 2)
        a = int(40 * t)
        bottom_line.set_at((x, 0), (*Theme.PANEL_BORDER, a))
    panel_surf.blit(bottom_line, (40, panel_rect.height - 8))
    
    canvas.blit(panel_surf, panel_rect.topleft)
    
    # 面板边框 - 带微光动画
    border_alpha = int(80 + 30 * (0.5 + 0.5 * math.sin(now * 0.002)))
    pygame.draw.rect(canvas, (*Theme.PANEL_BORDER, border_alpha), panel_rect, 
                    width=2, border_radius=PANEL_BORDER_RADIUS)
    
    # ========================================================================
    # 角色名框
    # ========================================================================
    text_start_y = panel_rect.y + 20
    
    if name:
        nstr = str(name)
        if '|' in nstr:
            base, alias = nstr.split('|', 1)
            disp_name = f"{base}（{alias}）"
        else:
            disp_name = nstr
        
        name_surf_temp = font.render(disp_name, True, Theme.NAME_COLOR)
        name_width = name_surf_temp.get_width() + 40
        
        name_rect = pygame.Rect(
            panel_rect.x + 20,
            panel_rect.y + NAME_BOX_OFFSET_Y,
            name_width,
            NAME_BOX_HEIGHT
        )
        
        # 名字框渐变背景
        name_bg = pygame.Surface((name_rect.width, name_rect.height), pygame.SRCALPHA)
        _draw_gradient_rect(
            name_bg,
            pygame.Rect(0, 0, name_rect.width, name_rect.height),
            (*Theme.PRIMARY_DARK, 240),
            (*Theme.PRIMARY, 220),
            border_radius=8
        )
        canvas.blit(name_bg, name_rect.topleft)
        
        # 名字框边框
        pygame.draw.rect(canvas, Theme.PRIMARY_LIGHT, name_rect, width=2, border_radius=8)
        
        # 左侧装饰条
        deco_rect = pygame.Rect(name_rect.x + 8, name_rect.y + 8, 3, name_rect.height - 16)
        pygame.draw.rect(canvas, Theme.ACCENT, deco_rect, border_radius=2)
        
        # 角色名文字 - 带阴影和发光
        nx = name_rect.x + 20
        ny = name_rect.y + (NAME_BOX_HEIGHT - name_surf_temp.get_height()) // 2
        # 阴影
        shadow = font.render(disp_name, True, (0, 0, 0))
        canvas.blit(shadow, (nx + 2, ny + 2))
        # 发光
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            glow = font.render(disp_name, True, (*Theme.NAME_GLOW, 60))
            canvas.blit(glow, (nx + dx, ny + dy))
        # 主文字
        canvas.blit(name_surf_temp, (nx, ny))
        
        # 效果标签
        if effect:
            eff_txt = f"[{effect}]"
            eff_surf = hint_font.render(eff_txt, True, (180, 180, 255))
            eff_x = name_rect.right + 10
            eff_y = name_rect.y + (NAME_BOX_HEIGHT - eff_surf.get_height()) // 2
            canvas.blit(eff_surf, (eff_x, eff_y))
        
        text_start_y = panel_rect.y + 24
    
    # ========================================================================
    # 对话文本
    # ========================================================================
    line_start_ts_out = line_start_ts
    line_full_ts_out = line_full_ts
    reveal = reveal_instant
    
    text_margin_x = 24
    text_max_width = panel_rect.width - text_margin_x * 2
    line_height = 32
    
    # 获取纯文本长度（用于打字机效果）
    plain_length = get_plain_length(text) if rich_text_enabled else len(text)
    
    # 计算已显示字符数
    revealed_chars: Optional[int] = None
    if typing_enabled and not reveal_instant:
        if line_start_ts_out == 0:
            line_start_ts_out = now
        speed = 50.0 * (3.0 if fast_forward else 1.0)
        allow = int(max(0, (now - line_start_ts_out) / 1000.0) * speed)
        if allow < plain_length:
            revealed_chars = allow
            line_full_ts_out = None
        else:
            revealed_chars = None  # 显示全部
            if line_full_ts_out is None:
                line_full_ts_out = now
    
    y = text_start_y
    
    if rich_text_enabled:
        # 使用富文本渲染
        lines = wrap_rich_text(text, font, text_max_width, font_getter, default_font_size)
        
        char_offset = 0
        for line_segments in lines:
            # 计算这行的字符数
            line_chars = sum(len(seg.text) for seg in line_segments)
            
            # 计算这行应该显示多少字符
            line_revealed: Optional[int] = None
            if revealed_chars is not None:
                if char_offset >= revealed_chars:
                    # 这行还不该显示
                    break
                remaining = revealed_chars - char_offset
                if remaining < line_chars:
                    line_revealed = remaining
            
            # 渲染这行
            line_surf, _ = render_rich_text_line(
                segments=line_segments,
                font=font,
                font_getter=font_getter,
                default_size=default_font_size,
                default_color=Theme.TEXT_PRIMARY,
                time_ms=now,
                revealed_chars=line_revealed,
                text_outline=text_outline or False,
                text_shadow=text_shadow or False,
                shadow_offset=text_shadow_offset or (2, 2),
            )
            
            # 绘制到画布（去掉边距偏移）
            canvas.blit(line_surf, (panel_rect.x + text_margin_x - 8, y - 8))
            y += line_height
            char_offset += line_chars
    else:
        # 传统纯文本渲染
        disp_text = text
        if revealed_chars is not None:
            disp_text = text[:revealed_chars]
        
        for line in wrap_text(disp_text, font, text_max_width):
            # 文字阴影
            if text_shadow:
                ox, oy = text_shadow_offset or (2, 2)
                shadow_surf = font.render(line, True, (0, 0, 0))
                canvas.blit(shadow_surf, (panel_rect.x + text_margin_x + ox, y + oy))
            
            # 文字轮廓
            if text_outline:
                outline_surf = font.render(line, True, (0, 0, 0))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    canvas.blit(outline_surf, (panel_rect.x + text_margin_x + dx, y + dy))
            
            # 主文字
            text_surf = font.render(line, True, Theme.TEXT_PRIMARY)
            canvas.blit(text_surf, (panel_rect.x + text_margin_x, y))
            y += line_height
    
    # ========================================================================
    # 继续指示器
    # ========================================================================
    if line_full_ts_out is not None:
        indicator_alpha = int(128 + 127 * math.sin(now * 0.005))
        indicator_x = panel_rect.right - 40
        indicator_y = panel_rect.bottom - 30
        
        points = [
            (indicator_x, indicator_y),
            (indicator_x + 12, indicator_y + 6),
            (indicator_x, indicator_y + 12)
        ]
        indicator_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(indicator_surf, (*Theme.ACCENT, indicator_alpha), 
                          [(p[0] - indicator_x + 4, p[1] - indicator_y + 4) for p in points])
        canvas.blit(indicator_surf, (indicator_x - 4, indicator_y - 4))
    
    return reveal, line_start_ts_out, line_full_ts_out
