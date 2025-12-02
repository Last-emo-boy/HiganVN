"""
Typewriter Effect System - 增强的打字机效果

Features:
- 逐字符显示动画
- 标点符号自动停顿
- 富文本标签支持 (颜色、大小、效果)
- 打字音效支持
- 可配置的速度和停顿时间
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

# 导入富文本解析器
from higanvn.engine.rich_text import (
    RichTextParser, RichTextSegment, TextStyle, EffectType,
    parse_rich_text as rt_parse, strip_rich_tags, get_plain_length,
)


class PauseType(Enum):
    """停顿类型"""
    NONE = 0
    SHORT = 1   # 逗号等
    MEDIUM = 2  # 句号等
    LONG = 3    # 省略号、感叹号等


@dataclass
class TextSegment:
    """文本段，包含样式信息 (兼容旧接口)"""
    text: str
    color: Optional[Tuple[int, int, int]] = None
    size_scale: float = 1.0
    bold: bool = False
    italic: bool = False
    shake: bool = False
    wave: bool = False
    
    # 扩展样式
    underline: bool = False
    strikethrough: bool = False
    outline_color: Optional[Tuple[int, int, int]] = None
    shadow: bool = False
    rainbow: bool = False
    fade: bool = False
    ruby_text: Optional[str] = None
    
    def __len__(self) -> int:
        return len(self.text)
    
    @classmethod
    def from_rich_segment(cls, seg: RichTextSegment) -> 'TextSegment':
        """从 RichTextSegment 转换"""
        style = seg.style
        return cls(
            text=seg.text,
            color=style.color,
            size_scale=style.size_scale,
            bold=style.bold,
            italic=style.italic,
            shake=style.effect == EffectType.SHAKE,
            wave=style.effect == EffectType.WAVE,
            underline=style.underline,
            strikethrough=style.strikethrough,
            outline_color=style.outline_color,
            shadow=style.shadow,
            rainbow=style.effect == EffectType.RAINBOW,
            fade=style.effect == EffectType.FADE,
            ruby_text=style.ruby_text,
        )


@dataclass
class TypewriterState:
    """打字机状态"""
    segments: List[TextSegment] = field(default_factory=list)
    total_chars: int = 0
    revealed_chars: int = 0
    start_time: int = 0
    pause_until: int = 0
    is_complete: bool = False
    
    # 配置
    chars_per_second: float = 45.0
    pause_short_ms: int = 100
    pause_medium_ms: int = 200
    pause_long_ms: int = 400
    
    # 音效
    type_sound_enabled: bool = False
    type_sound_interval: int = 2  # 每N个字符播放一次


# 标点符号停顿映射
PUNCTUATION_PAUSES: Dict[str, PauseType] = {
    # 短停顿 - 逗号、顿号
    ',': PauseType.SHORT,
    '，': PauseType.SHORT,
    '、': PauseType.SHORT,
    ';': PauseType.SHORT,
    '；': PauseType.SHORT,
    ':': PauseType.SHORT,
    '：': PauseType.SHORT,
    
    # 中等停顿 - 句号
    '.': PauseType.MEDIUM,
    '。': PauseType.MEDIUM,
    
    # 长停顿 - 感叹号、问号、省略号
    '!': PauseType.LONG,
    '！': PauseType.LONG,
    '?': PauseType.LONG,
    '？': PauseType.LONG,
    '…': PauseType.LONG,
    '~': PauseType.SHORT,
    '～': PauseType.SHORT,
}


def parse_rich_text(text: str) -> List[TextSegment]:
    """
    解析富文本标签，返回文本段列表。
    
    支持的标签:
        [color=#RRGGBB]文本[/color]  - 文字颜色
        [size=1.5]文本[/size]        - 文字大小倍率
        [b]文本[/b]                  - 粗体
        [i]文本[/i]                  - 斜体
        [u]文本[/u]                  - 下划线
        [s]文本[/s]                  - 删除线
        [shake]文本[/shake]          - 抖动效果
        [wave]文本[/wave]            - 波浪效果
        [fade]文本[/fade]            - 渐变透明
        [rainbow]文本[/rainbow]      - 彩虹色
        [outline=#000000]文本[/outline] - 描边
        [shadow]文本[/shadow]        - 阴影
        [ruby=注音]文本[/ruby]       - 注音
    
    控制指令:
        {pause=500}                  - 暂停500毫秒
        {speed=2.0}                  - 改变速度
        {instant}                    - 立即显示
    """
    if not text:
        return []
    
    # 使用新的富文本解析器
    rich_segments = rt_parse(text)
    
    # 转换为旧格式以保持兼容性
    segments = [TextSegment.from_rich_segment(seg) for seg in rich_segments]
    
    return segments


def get_rich_segments(text: str) -> List[RichTextSegment]:
    """获取完整的富文本段落列表（包含所有样式信息）"""
    if not text:
        return []
    return rt_parse(text)


def create_typewriter(
    text: str,
    chars_per_second: float = 45.0,
    start_time: int = 0,
    pause_short_ms: int = 100,
    pause_medium_ms: int = 200,
    pause_long_ms: int = 400,
) -> TypewriterState:
    """
    创建打字机状态。
    
    Args:
        text: 要显示的文本
        chars_per_second: 每秒显示的字符数
        start_time: 开始时间 (毫秒)
        pause_short_ms: 短停顿时长
        pause_medium_ms: 中等停顿时长
        pause_long_ms: 长停顿时长
    
    Returns:
        TypewriterState 对象
    """
    segments = parse_rich_text(text)
    total_chars = sum(len(seg) for seg in segments)
    
    return TypewriterState(
        segments=segments,
        total_chars=total_chars,
        revealed_chars=0,
        start_time=start_time,
        pause_until=0,
        is_complete=total_chars == 0,
        chars_per_second=chars_per_second,
        pause_short_ms=pause_short_ms,
        pause_medium_ms=pause_medium_ms,
        pause_long_ms=pause_long_ms,
    )


def update_typewriter(state: TypewriterState, current_time: int, speed_multiplier: float = 1.0) -> bool:
    """
    更新打字机状态。
    
    Args:
        state: 打字机状态
        current_time: 当前时间 (毫秒)
        speed_multiplier: 速度倍率 (如快进时为3.0)
    
    Returns:
        True 如果有变化，False 如果无变化
    """
    if state.is_complete:
        return False
    
    # 检查是否在停顿中
    if current_time < state.pause_until:
        return False
    
    # 初始化开始时间
    if state.start_time == 0:
        state.start_time = current_time
    
    # 计算应该显示的字符数
    elapsed_ms = current_time - state.start_time
    effective_speed = state.chars_per_second * speed_multiplier
    target_chars = int(elapsed_ms / 1000.0 * effective_speed)
    
    if target_chars <= state.revealed_chars:
        return False
    
    old_revealed = state.revealed_chars
    
    # 逐字符检查停顿
    while state.revealed_chars < min(target_chars, state.total_chars):
        char = get_char_at(state, state.revealed_chars)
        state.revealed_chars += 1
        
        # 检查标点停顿
        pause_type = PUNCTUATION_PAUSES.get(char, PauseType.NONE)
        if pause_type != PauseType.NONE:
            pause_ms = {
                PauseType.SHORT: state.pause_short_ms,
                PauseType.MEDIUM: state.pause_medium_ms,
                PauseType.LONG: state.pause_long_ms,
            }.get(pause_type, 0)
            
            # 应用速度倍率到停顿时间
            pause_ms = int(pause_ms / speed_multiplier)
            
            if pause_ms > 0:
                state.pause_until = current_time + pause_ms
                # 重置开始时间以便暂停后继续
                state.start_time = state.pause_until - int(state.revealed_chars / effective_speed * 1000)
                break
    
    # 检查是否完成
    if state.revealed_chars >= state.total_chars:
        state.is_complete = True
    
    return state.revealed_chars != old_revealed


def get_char_at(state: TypewriterState, index: int) -> str:
    """获取指定位置的字符"""
    current = 0
    for seg in state.segments:
        if current + len(seg) > index:
            return seg.text[index - current]
        current += len(seg)
    return ''


def get_revealed_text(state: TypewriterState) -> str:
    """获取当前已显示的文本"""
    if state.revealed_chars >= state.total_chars:
        return ''.join(seg.text for seg in state.segments)
    
    result = []
    remaining = state.revealed_chars
    
    for seg in state.segments:
        if remaining <= 0:
            break
        if len(seg) <= remaining:
            result.append(seg.text)
            remaining -= len(seg)
        else:
            result.append(seg.text[:remaining])
            remaining = 0
    
    return ''.join(result)


def get_revealed_segments(state: TypewriterState) -> List[Tuple[TextSegment, str]]:
    """
    获取已显示的文本段，保留样式信息。
    
    Returns:
        List of (segment, visible_text) tuples
    """
    result = []
    remaining = state.revealed_chars
    
    for seg in state.segments:
        if remaining <= 0:
            break
        if len(seg) <= remaining:
            result.append((seg, seg.text))
            remaining -= len(seg)
        else:
            result.append((seg, seg.text[:remaining]))
            remaining = 0
    
    return result


def reveal_all(state: TypewriterState) -> None:
    """立即显示所有文本"""
    state.revealed_chars = state.total_chars
    state.is_complete = True
    state.pause_until = 0


def reset_typewriter(state: TypewriterState, current_time: int = 0) -> None:
    """重置打字机状态"""
    state.revealed_chars = 0
    state.start_time = current_time
    state.pause_until = 0
    state.is_complete = state.total_chars == 0


# ============================================================================
# 光标/指示器效果
# ============================================================================

@dataclass
class CursorState:
    """光标状态"""
    visible: bool = True
    blink_interval_ms: int = 500
    last_toggle_time: int = 0
    style: str = "triangle"  # "triangle", "line", "block"


def update_cursor(cursor: CursorState, current_time: int, text_complete: bool) -> bool:
    """
    更新光标状态。
    
    Args:
        cursor: 光标状态
        current_time: 当前时间
        text_complete: 文本是否显示完成
    
    Returns:
        当前光标是否可见
    """
    if not text_complete:
        cursor.visible = True
        return True
    
    # 文本完成后闪烁
    if current_time - cursor.last_toggle_time >= cursor.blink_interval_ms:
        cursor.visible = not cursor.visible
        cursor.last_toggle_time = current_time
    
    return cursor.visible


# ============================================================================
# 便捷函数
# ============================================================================

def simple_typewriter_update(
    text: str,
    current_time: int,
    start_time: int,
    chars_per_second: float = 45.0,
    fast_forward: bool = False,
    reveal_instant: bool = False,
) -> Tuple[str, int, bool]:
    """
    简化版打字机更新，用于向后兼容。
    
    Args:
        text: 完整文本
        current_time: 当前时间 (毫秒)
        start_time: 开始时间 (毫秒)
        chars_per_second: 每秒字符数
        fast_forward: 是否快进
        reveal_instant: 是否立即显示
    
    Returns:
        (displayed_text, new_start_time, is_complete)
    """
    if reveal_instant or not text:
        return text, start_time, True
    
    if start_time == 0:
        start_time = current_time
    
    speed = chars_per_second * (3.0 if fast_forward else 1.0)
    elapsed = max(0, current_time - start_time)
    char_count = int(elapsed / 1000.0 * speed)
    
    # 添加标点停顿逻辑
    actual_chars = 0
    accumulated_pause = 0
    
    for i, char in enumerate(text):
        if i >= char_count:
            break
        
        pause_type = PUNCTUATION_PAUSES.get(char, PauseType.NONE)
        if pause_type != PauseType.NONE:
            pause_ms = {
                PauseType.SHORT: 80,
                PauseType.MEDIUM: 150,
                PauseType.LONG: 250,
            }.get(pause_type, 0)
            
            if fast_forward:
                pause_ms //= 3
            
            accumulated_pause += pause_ms
        
        # 检查加上停顿后是否还应该显示这个字符
        effective_elapsed = elapsed - accumulated_pause
        chars_at_this_point = int(effective_elapsed / 1000.0 * speed)
        
        if i < chars_at_this_point:
            actual_chars = i + 1
    
    displayed = text[:actual_chars]
    is_complete = actual_chars >= len(text)
    
    return displayed, start_time, is_complete
