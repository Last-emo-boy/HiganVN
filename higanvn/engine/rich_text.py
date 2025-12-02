"""
Rich Text Rendering System - 富文本渲染系统

支持的标签:
    [color=#RRGGBB]文本[/color]   - 文字颜色 (支持 #RGB, #RRGGBB, 颜色名)
    [size=1.5]文本[/size]         - 文字大小倍率 (0.5-3.0)
    [b]文本[/b]                   - 粗体
    [i]文本[/i]                   - 斜体
    [u]文本[/u]                   - 下划线
    [s]文本[/s]                   - 删除线
    [shake]文本[/shake]           - 抖动效果 (amplitude=3, speed=20)
    [shake=5,30]文本[/shake]      - 抖动效果 (自定义振幅和速度)
    [wave]文本[/wave]             - 波浪效果 (amplitude=3, speed=5)
    [wave=4,8]文本[/wave]         - 波浪效果 (自定义振幅和速度)
    [fade]文本[/fade]             - 渐变透明效果
    [rainbow]文本[/rainbow]       - 彩虹色效果
    [outline=#000000]文本[/outline] - 描边效果
    [shadow]文本[/shadow]         - 阴影效果
    [ruby=注音]文本[/ruby]        - 注音/振假名 (日语假名标注)

特殊标记:
    {pause=500}                   - 暂停500毫秒
    {speed=2.0}                   - 改变后续文本速度
    {instant}                     - 后续文本立即显示

Example:
    "[color=#FF0000]红色文字[/color]普通文字[shake]震动[/shake]"
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Callable
from enum import Enum, auto


# ============================================================================
# 颜色定义
# ============================================================================

NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    # 基础色
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    
    # 扩展色
    "orange": (255, 165, 0),
    "pink": (255, 192, 203),
    "purple": (128, 0, 128),
    "gold": (255, 215, 0),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    
    # 视觉小说常用色
    "anger": (255, 80, 80),       # 愤怒
    "sadness": (100, 150, 255),   # 悲伤
    "happy": (255, 230, 100),     # 开心
    "fear": (180, 100, 255),      # 恐惧
    "surprise": (255, 180, 100),  # 惊讶
    "whisper": (200, 200, 200),   # 低语
    "shout": (255, 100, 100),     # 大喊
    "thought": (180, 180, 220),   # 心声
    "narration": (220, 220, 220), # 旁白
    "system": (100, 200, 255),    # 系统提示
}


def parse_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    """
    解析颜色字符串。
    
    支持格式:
        - #RGB (如 #F00)
        - #RRGGBB (如 #FF0000)
        - #RRGGBBAA (如 #FF0000FF)
        - 颜色名 (如 red, blue)
        - rgb(r,g,b)
    """
    if not color_str:
        return None
    
    color_str = color_str.strip().lower()
    
    # 颜色名
    if color_str in NAMED_COLORS:
        return NAMED_COLORS[color_str]
    
    # Hex格式
    if color_str.startswith('#'):
        hex_val = color_str[1:]
        try:
            if len(hex_val) == 3:
                r = int(hex_val[0] * 2, 16)
                g = int(hex_val[1] * 2, 16)
                b = int(hex_val[2] * 2, 16)
                return (r, g, b)
            elif len(hex_val) >= 6:
                r = int(hex_val[0:2], 16)
                g = int(hex_val[2:4], 16)
                b = int(hex_val[4:6], 16)
                return (r, g, b)
        except ValueError:
            pass
    
    # rgb() 格式
    rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
    if rgb_match:
        r = min(255, max(0, int(rgb_match.group(1))))
        g = min(255, max(0, int(rgb_match.group(2))))
        b = min(255, max(0, int(rgb_match.group(3))))
        return (r, g, b)
    
    return None


# ============================================================================
# 文本效果类型
# ============================================================================

class EffectType(Enum):
    """文本效果类型"""
    NONE = auto()
    SHAKE = auto()
    WAVE = auto()
    FADE = auto()
    RAINBOW = auto()
    TYPEWRITER = auto()


@dataclass
class TextStyle:
    """文本样式"""
    color: Optional[Tuple[int, int, int]] = None
    size_scale: float = 1.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    outline_color: Optional[Tuple[int, int, int]] = None
    outline_width: int = 1
    shadow: bool = False
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_offset: Tuple[int, int] = (2, 2)
    
    # 效果
    effect: EffectType = EffectType.NONE
    effect_amplitude: float = 3.0
    effect_speed: float = 10.0
    
    # 注音
    ruby_text: Optional[str] = None
    
    def copy(self) -> 'TextStyle':
        """创建副本"""
        return TextStyle(
            color=self.color,
            size_scale=self.size_scale,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
            outline_color=self.outline_color,
            outline_width=self.outline_width,
            shadow=self.shadow,
            shadow_color=self.shadow_color,
            shadow_offset=self.shadow_offset,
            effect=self.effect,
            effect_amplitude=self.effect_amplitude,
            effect_speed=self.effect_speed,
            ruby_text=self.ruby_text,
        )


@dataclass
class RichTextSegment:
    """富文本段落"""
    text: str
    style: TextStyle = field(default_factory=TextStyle)
    
    # 控制指令
    pause_ms: int = 0
    speed_multiplier: float = 1.0
    instant: bool = False
    
    def __len__(self) -> int:
        return len(self.text)
    
    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass 
class RichTextLine:
    """富文本行"""
    segments: List[RichTextSegment] = field(default_factory=list)
    
    @property
    def text(self) -> str:
        return ''.join(seg.text for seg in self.segments)
    
    @property
    def char_count(self) -> int:
        return sum(len(seg) for seg in self.segments)


# ============================================================================
# 富文本解析器
# ============================================================================

class RichTextParser:
    """
    富文本解析器
    
    将带标签的文本解析为 RichTextSegment 列表
    """
    
    # 标签正则
    TAG_PATTERN = re.compile(
        r'\[(/?)(\w+)(?:=([^\]]*))?\]'
    )
    
    # 控制指令正则
    CONTROL_PATTERN = re.compile(
        r'\{(\w+)(?:=([^}]*))?\}'
    )
    
    def __init__(self, default_color: Tuple[int, int, int] = (255, 255, 255)):
        self.default_color = default_color
    
    def parse(self, text: str) -> List[RichTextSegment]:
        """解析富文本"""
        if not text:
            return []
        
        segments: List[RichTextSegment] = []
        style_stack: List[Tuple[str, TextStyle]] = []
        current_style = TextStyle(color=self.default_color)
        
        pos = 0
        current_text = ""
        current_pause = 0
        current_speed = 1.0
        current_instant = False
        
        while pos < len(text):
            # 检查标签
            tag_match = self.TAG_PATTERN.match(text, pos)
            if tag_match:
                # 保存当前文本段
                if current_text:
                    segments.append(RichTextSegment(
                        text=current_text,
                        style=current_style.copy(),
                        pause_ms=current_pause,
                        speed_multiplier=current_speed,
                        instant=current_instant,
                    ))
                    current_text = ""
                    current_pause = 0
                    current_instant = False
                
                is_closing = tag_match.group(1) == '/'
                tag_name = tag_match.group(2).lower()
                tag_value = tag_match.group(3)
                
                if is_closing:
                    # 关闭标签 - 从栈中弹出
                    for i in range(len(style_stack) - 1, -1, -1):
                        if style_stack[i][0] == tag_name:
                            # 恢复之前的样式
                            if i > 0:
                                current_style = style_stack[i - 1][1].copy()
                            else:
                                current_style = TextStyle(color=self.default_color)
                            style_stack = style_stack[:i]
                            break
                else:
                    # 开启标签 - 压入栈
                    style_stack.append((tag_name, current_style.copy()))
                    current_style = self._apply_tag(current_style.copy(), tag_name, tag_value)
                
                pos = tag_match.end()
                continue
            
            # 检查控制指令
            ctrl_match = self.CONTROL_PATTERN.match(text, pos)
            if ctrl_match:
                ctrl_name = ctrl_match.group(1).lower()
                ctrl_value = ctrl_match.group(2)
                
                # pause 指令: 附加到前一段文本上（表示读完后暂停）
                if ctrl_name == 'pause':
                    try:
                        pause_val = int(ctrl_value) if ctrl_value else 500
                    except ValueError:
                        pause_val = 500
                    
                    # 保存当前文本段并附加暂停
                    if current_text:
                        segments.append(RichTextSegment(
                            text=current_text,
                            style=current_style.copy(),
                            pause_ms=pause_val,  # 暂停附加到此段
                            speed_multiplier=current_speed,
                            instant=current_instant,
                        ))
                        current_text = ""
                        current_instant = False
                elif ctrl_name == 'speed':
                    # 保存当前文本段
                    if current_text:
                        segments.append(RichTextSegment(
                            text=current_text,
                            style=current_style.copy(),
                            pause_ms=0,
                            speed_multiplier=current_speed,
                            instant=current_instant,
                        ))
                        current_text = ""
                        current_instant = False
                    try:
                        current_speed = float(ctrl_value) if ctrl_value else 1.0
                    except ValueError:
                        current_speed = 1.0
                elif ctrl_name == 'instant':
                    # 保存当前文本段
                    if current_text:
                        segments.append(RichTextSegment(
                            text=current_text,
                            style=current_style.copy(),
                            pause_ms=0,
                            speed_multiplier=current_speed,
                            instant=current_instant,
                        ))
                        current_text = ""
                    current_instant = True
                
                pos = ctrl_match.end()
                continue
            
            # 普通字符
            current_text += text[pos]
            pos += 1
        
        # 保存剩余文本
        if current_text:
            segments.append(RichTextSegment(
                text=current_text,
                style=current_style.copy(),
                pause_ms=current_pause,
                speed_multiplier=current_speed,
                instant=current_instant,
            ))
        
        return segments
    
    def _apply_tag(self, style: TextStyle, tag_name: str, value: Optional[str]) -> TextStyle:
        """应用标签到样式"""
        
        if tag_name == 'color':
            color = parse_color(value) if value else None
            if color:
                style.color = color
        
        elif tag_name == 'size':
            try:
                scale = float(value) if value else 1.0
                style.size_scale = max(0.5, min(3.0, scale))
            except ValueError:
                pass
        
        elif tag_name == 'b':
            style.bold = True
        
        elif tag_name == 'i':
            style.italic = True
        
        elif tag_name == 'u':
            style.underline = True
        
        elif tag_name == 's':
            style.strikethrough = True
        
        elif tag_name == 'shake':
            style.effect = EffectType.SHAKE
            if value:
                try:
                    parts = value.split(',')
                    if len(parts) >= 1:
                        style.effect_amplitude = float(parts[0])
                    if len(parts) >= 2:
                        style.effect_speed = float(parts[1])
                except ValueError:
                    pass
        
        elif tag_name == 'wave':
            style.effect = EffectType.WAVE
            if value:
                try:
                    parts = value.split(',')
                    if len(parts) >= 1:
                        style.effect_amplitude = float(parts[0])
                    if len(parts) >= 2:
                        style.effect_speed = float(parts[1])
                except ValueError:
                    pass
        
        elif tag_name == 'fade':
            style.effect = EffectType.FADE
        
        elif tag_name == 'rainbow':
            style.effect = EffectType.RAINBOW
        
        elif tag_name == 'outline':
            color = parse_color(value) if value else (0, 0, 0)
            style.outline_color = color or (0, 0, 0)
        
        elif tag_name == 'shadow':
            style.shadow = True
            if value:
                color = parse_color(value)
                if color:
                    style.shadow_color = color
        
        elif tag_name == 'ruby':
            style.ruby_text = value
        
        return style
    
    def strip_tags(self, text: str) -> str:
        """移除所有标签，返回纯文本"""
        text = self.TAG_PATTERN.sub('', text)
        text = self.CONTROL_PATTERN.sub('', text)
        return text
    
    def get_plain_length(self, text: str) -> int:
        """获取纯文本长度"""
        return len(self.strip_tags(text))


# ============================================================================
# 富文本渲染器
# ============================================================================

class RichTextRenderer:
    """
    富文本渲染器
    
    将 RichTextSegment 渲染到 Pygame Surface
    """
    
    def __init__(
        self,
        font_getter: Callable[[int, bool, bool], Any],
        default_size: int = 24,
        default_color: Tuple[int, int, int] = (255, 255, 255),
    ):
        """
        Args:
            font_getter: 获取字体的函数 (size, bold, italic) -> Font
            default_size: 默认字体大小
            default_color: 默认文字颜色
        """
        self.font_getter = font_getter
        self.default_size = default_size
        self.default_color = default_color
        self.parser = RichTextParser(default_color)
    
    def measure_text(self, segments: List[RichTextSegment]) -> Tuple[int, int]:
        """测量文本尺寸"""
        total_width = 0
        max_height = 0
        
        for seg in segments:
            size = int(self.default_size * seg.style.size_scale)
            font = self.font_getter(size, seg.style.bold, seg.style.italic)
            
            try:
                w, h = font.size(seg.text)
            except Exception:
                w, h = len(seg.text) * size // 2, size
            
            total_width += w
            max_height = max(max_height, h)
            
            # 注音额外高度
            if seg.style.ruby_text:
                max_height += size // 2
        
        return total_width, max_height
    
    def render(
        self,
        segments: List[RichTextSegment],
        time_ms: int = 0,
        revealed_chars: Optional[int] = None,
    ) -> 'pygame.Surface':
        """
        渲染富文本段落到 Surface
        
        Args:
            segments: 富文本段列表
            time_ms: 当前时间（用于动画效果）
            revealed_chars: 已显示的字符数（用于打字机效果）
        
        Returns:
            渲染后的 Surface
        """
        import pygame
        
        if not segments:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        
        # 计算总尺寸
        width, height = self.measure_text(segments)
        if width <= 0:
            width = 1
        if height <= 0:
            height = self.default_size
        
        # 创建Surface（加上效果边距）
        margin = 10
        surface = pygame.Surface((width + margin * 2, height + margin * 2), pygame.SRCALPHA)
        
        x = margin
        char_index = 0
        
        for seg in segments:
            # 检查是否已超过显示字符数
            if revealed_chars is not None and char_index >= revealed_chars:
                break
            
            # 计算这个段落应该显示多少字符
            seg_chars = len(seg.text)
            if revealed_chars is not None:
                remaining = revealed_chars - char_index
                if remaining <= 0:
                    break
                visible_text = seg.text[:remaining]
            else:
                visible_text = seg.text
            
            if not visible_text:
                char_index += seg_chars
                continue
            
            # 获取字体
            size = int(self.default_size * seg.style.size_scale)
            font = self.font_getter(size, seg.style.bold, seg.style.italic)
            
            # 渲染每个字符（用于效果）
            for i, char in enumerate(visible_text):
                # 计算效果偏移
                dx, dy = 0, 0
                char_color = seg.style.color or self.default_color
                char_alpha = 255
                
                if seg.style.effect == EffectType.SHAKE:
                    amp = seg.style.effect_amplitude
                    spd = seg.style.effect_speed
                    dx = int(amp * math.sin(time_ms * spd / 1000 + i * 0.5))
                    dy = int(amp * math.cos(time_ms * spd / 1000 * 1.3 + i * 0.7))
                
                elif seg.style.effect == EffectType.WAVE:
                    amp = seg.style.effect_amplitude
                    spd = seg.style.effect_speed
                    dy = int(amp * math.sin(time_ms * spd / 1000 + i * 0.3))
                
                elif seg.style.effect == EffectType.RAINBOW:
                    hue = ((time_ms / 10) + i * 20) % 360
                    char_color = self._hue_to_rgb(hue)
                
                elif seg.style.effect == EffectType.FADE:
                    phase = math.sin(time_ms / 500 + i * 0.2)
                    char_alpha = int(128 + 127 * phase)
                
                # 渲染字符
                try:
                    char_width, _ = font.size(char)
                except Exception:
                    char_width = size // 2
                
                char_y = margin + (height - size) // 2
                
                # 阴影
                if seg.style.shadow:
                    shadow_surf = font.render(char, True, seg.style.shadow_color)
                    sox, soy = seg.style.shadow_offset
                    surface.blit(shadow_surf, (x + dx + sox, char_y + dy + soy))
                
                # 描边
                if seg.style.outline_color:
                    outline_surf = font.render(char, True, seg.style.outline_color)
                    for odx in range(-seg.style.outline_width, seg.style.outline_width + 1):
                        for ody in range(-seg.style.outline_width, seg.style.outline_width + 1):
                            if odx == 0 and ody == 0:
                                continue
                            surface.blit(outline_surf, (x + dx + odx, char_y + dy + ody))
                
                # 主文字
                char_surf = font.render(char, True, char_color)
                if char_alpha < 255:
                    char_surf.set_alpha(char_alpha)
                surface.blit(char_surf, (x + dx, char_y + dy))
                
                # 下划线
                if seg.style.underline:
                    underline_y = char_y + dy + size - 2
                    pygame.draw.line(surface, char_color, 
                                   (x + dx, underline_y), 
                                   (x + dx + char_width, underline_y), 1)
                
                # 删除线
                if seg.style.strikethrough:
                    strike_y = char_y + dy + size // 2
                    pygame.draw.line(surface, char_color,
                                   (x + dx, strike_y),
                                   (x + dx + char_width, strike_y), 1)
                
                x += char_width
            
            # 注音 (Ruby text)
            if seg.style.ruby_text and visible_text == seg.text:
                ruby_size = max(10, size // 2)
                ruby_font = self.font_getter(ruby_size, False, False)
                ruby_surf = ruby_font.render(seg.style.ruby_text, True, 
                                            seg.style.color or self.default_color)
                # 居中在文本上方
                seg_width, _ = font.size(seg.text)
                ruby_x = x - seg_width + (seg_width - ruby_surf.get_width()) // 2
                ruby_y = margin - ruby_size
                surface.blit(ruby_surf, (max(0, ruby_x), max(0, ruby_y)))
            
            char_index += seg_chars
        
        return surface
    
    def _hue_to_rgb(self, hue: float) -> Tuple[int, int, int]:
        """HSV转RGB (S=1, V=1)"""
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


# ============================================================================
# 便捷函数
# ============================================================================

_default_parser: Optional[RichTextParser] = None


def get_parser() -> RichTextParser:
    """获取默认解析器"""
    global _default_parser
    if _default_parser is None:
        _default_parser = RichTextParser()
    return _default_parser


def parse_rich_text(text: str) -> List[RichTextSegment]:
    """解析富文本"""
    return get_parser().parse(text)


def strip_rich_tags(text: str) -> str:
    """移除富文本标签"""
    return get_parser().strip_tags(text)


def get_plain_length(text: str) -> int:
    """获取纯文本长度"""
    return get_parser().get_plain_length(text)


def create_renderer(
    font_getter: Callable[[int, bool, bool], Any],
    default_size: int = 24,
    default_color: Tuple[int, int, int] = (255, 255, 255),
) -> RichTextRenderer:
    """创建渲染器"""
    return RichTextRenderer(font_getter, default_size, default_color)
