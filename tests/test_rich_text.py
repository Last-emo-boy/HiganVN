"""
Tests for Rich Text Rendering System
"""
import pytest


class TestColorParsing:
    """测试颜色解析"""
    
    def test_parse_hex_color_short(self):
        """Test short hex color parsing."""
        from higanvn.engine.rich_text import parse_color
        
        assert parse_color("#F00") == (255, 0, 0)
        assert parse_color("#0F0") == (0, 255, 0)
        assert parse_color("#00F") == (0, 0, 255)
        assert parse_color("#FFF") == (255, 255, 255)
    
    def test_parse_hex_color_long(self):
        """Test long hex color parsing."""
        from higanvn.engine.rich_text import parse_color
        
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#00FF00") == (0, 255, 0)
        assert parse_color("#0000FF") == (0, 0, 255)
        assert parse_color("#FFFFFF") == (255, 255, 255)
        assert parse_color("#808080") == (128, 128, 128)
    
    def test_parse_named_colors(self):
        """Test named color parsing."""
        from higanvn.engine.rich_text import parse_color
        
        assert parse_color("red") == (255, 0, 0)
        assert parse_color("green") == (0, 255, 0)
        assert parse_color("blue") == (0, 0, 255)
        assert parse_color("WHITE") == (255, 255, 255)
        assert parse_color("Orange") == (255, 165, 0)
    
    def test_parse_rgb_format(self):
        """Test rgb() format parsing."""
        from higanvn.engine.rich_text import parse_color
        
        assert parse_color("rgb(255, 0, 0)") == (255, 0, 0)
        assert parse_color("rgb(128,128,128)") == (128, 128, 128)
        assert parse_color("rgb( 0, 255, 0 )") == (0, 255, 0)
    
    def test_parse_invalid_color(self):
        """Test invalid color returns None."""
        from higanvn.engine.rich_text import parse_color
        
        assert parse_color("invalid") is None
        assert parse_color("#GGG") is None
        assert parse_color("") is None
        assert parse_color(None) is None


class TestTextStyle:
    """测试文本样式"""
    
    def test_text_style_defaults(self):
        """Test TextStyle default values."""
        from higanvn.engine.rich_text import TextStyle, EffectType
        
        style = TextStyle()
        assert style.color is None
        assert style.size_scale == 1.0
        assert style.bold is False
        assert style.italic is False
        assert style.effect == EffectType.NONE
    
    def test_text_style_copy(self):
        """Test TextStyle copy."""
        from higanvn.engine.rich_text import TextStyle, EffectType
        
        style = TextStyle(
            color=(255, 0, 0),
            bold=True,
            effect=EffectType.SHAKE,
        )
        copy = style.copy()
        
        assert copy.color == (255, 0, 0)
        assert copy.bold is True
        assert copy.effect == EffectType.SHAKE
        
        # Modifying copy shouldn't affect original
        copy.color = (0, 255, 0)
        assert style.color == (255, 0, 0)


class TestRichTextParser:
    """测试富文本解析器"""
    
    def test_parse_plain_text(self):
        """Test parsing plain text."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("Hello, World!")
        
        assert len(segments) == 1
        assert segments[0].text == "Hello, World!"
    
    def test_parse_color_tag(self):
        """Test parsing color tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[color=#FF0000]Red Text[/color]")
        
        assert len(segments) == 1
        assert segments[0].text == "Red Text"
        assert segments[0].style.color == (255, 0, 0)
    
    def test_parse_named_color_tag(self):
        """Test parsing named color tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[color=blue]Blue Text[/color]")
        
        assert len(segments) == 1
        assert segments[0].style.color == (0, 0, 255)
    
    def test_parse_size_tag(self):
        """Test parsing size tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[size=1.5]Big Text[/size]")
        
        assert len(segments) == 1
        assert segments[0].text == "Big Text"
        assert segments[0].style.size_scale == 1.5
    
    def test_parse_bold_tag(self):
        """Test parsing bold tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[b]Bold Text[/b]")
        
        assert len(segments) == 1
        assert segments[0].style.bold is True
    
    def test_parse_italic_tag(self):
        """Test parsing italic tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[i]Italic Text[/i]")
        
        assert len(segments) == 1
        assert segments[0].style.italic is True
    
    def test_parse_underline_tag(self):
        """Test parsing underline tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[u]Underlined[/u]")
        
        assert len(segments) == 1
        assert segments[0].style.underline is True
    
    def test_parse_strikethrough_tag(self):
        """Test parsing strikethrough tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[s]Strikethrough[/s]")
        
        assert len(segments) == 1
        assert segments[0].style.strikethrough is True
    
    def test_parse_shake_tag(self):
        """Test parsing shake effect tag."""
        from higanvn.engine.rich_text import RichTextParser, EffectType
        
        parser = RichTextParser()
        segments = parser.parse("[shake]Shaky[/shake]")
        
        assert len(segments) == 1
        assert segments[0].style.effect == EffectType.SHAKE
    
    def test_parse_shake_with_params(self):
        """Test parsing shake tag with parameters."""
        from higanvn.engine.rich_text import RichTextParser, EffectType
        
        parser = RichTextParser()
        segments = parser.parse("[shake=5,30]Shaky[/shake]")
        
        assert len(segments) == 1
        assert segments[0].style.effect == EffectType.SHAKE
        assert segments[0].style.effect_amplitude == 5.0
        assert segments[0].style.effect_speed == 30.0
    
    def test_parse_wave_tag(self):
        """Test parsing wave effect tag."""
        from higanvn.engine.rich_text import RichTextParser, EffectType
        
        parser = RichTextParser()
        segments = parser.parse("[wave]Wavy[/wave]")
        
        assert len(segments) == 1
        assert segments[0].style.effect == EffectType.WAVE
    
    def test_parse_rainbow_tag(self):
        """Test parsing rainbow effect tag."""
        from higanvn.engine.rich_text import RichTextParser, EffectType
        
        parser = RichTextParser()
        segments = parser.parse("[rainbow]Rainbow[/rainbow]")
        
        assert len(segments) == 1
        assert segments[0].style.effect == EffectType.RAINBOW
    
    def test_parse_fade_tag(self):
        """Test parsing fade effect tag."""
        from higanvn.engine.rich_text import RichTextParser, EffectType
        
        parser = RichTextParser()
        segments = parser.parse("[fade]Fading[/fade]")
        
        assert len(segments) == 1
        assert segments[0].style.effect == EffectType.FADE
    
    def test_parse_outline_tag(self):
        """Test parsing outline tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[outline=#000000]Outlined[/outline]")
        
        assert len(segments) == 1
        assert segments[0].style.outline_color == (0, 0, 0)
    
    def test_parse_shadow_tag(self):
        """Test parsing shadow tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[shadow]Shadowed[/shadow]")
        
        assert len(segments) == 1
        assert segments[0].style.shadow is True
    
    def test_parse_ruby_tag(self):
        """Test parsing ruby (furigana) tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[ruby=かんじ]漢字[/ruby]")
        
        assert len(segments) == 1
        assert segments[0].text == "漢字"
        assert segments[0].style.ruby_text == "かんじ"
    
    def test_parse_mixed_text(self):
        """Test parsing mixed plain and tagged text."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("Hello [color=#FF0000]Red[/color] World")
        
        assert len(segments) == 3
        assert segments[0].text == "Hello "
        assert segments[0].style.color is None or segments[0].style.color == parser.default_color
        assert segments[1].text == "Red"
        assert segments[1].style.color == (255, 0, 0)
        assert segments[2].text == " World"
    
    def test_parse_nested_tags(self):
        """Test parsing nested tags."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[color=#FF0000][b]Bold Red[/b][/color]")
        
        assert len(segments) == 1
        assert segments[0].text == "Bold Red"
        assert segments[0].style.color == (255, 0, 0)
        assert segments[0].style.bold is True
    
    def test_parse_pause_control(self):
        """Test parsing pause control directive."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("Hello{pause=500} World")
        
        assert len(segments) == 2
        assert segments[0].text == "Hello"
        assert segments[0].pause_ms == 500
        assert segments[1].text == " World"
    
    def test_parse_speed_control(self):
        """Test parsing speed control directive."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("Normal{speed=2.0}Fast")
        
        assert len(segments) == 2
        assert segments[0].speed_multiplier == 1.0
        assert segments[1].speed_multiplier == 2.0
    
    def test_parse_instant_control(self):
        """Test parsing instant control directive."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("Slow{instant}Fast")
        
        assert len(segments) == 2
        assert segments[0].instant is False
        assert segments[1].instant is True
    
    def test_strip_tags(self):
        """Test stripping tags from text."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        plain = parser.strip_tags("[color=#FF0000]Red[/color] and [b]Bold[/b]{pause=100}")
        
        assert plain == "Red and Bold"
    
    def test_get_plain_length(self):
        """Test getting plain text length."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        length = parser.get_plain_length("[color=#FF0000]Hello[/color]")
        
        assert length == 5


class TestRichTextSegment:
    """测试 RichTextSegment"""
    
    def test_segment_char_count(self):
        """Test segment character count."""
        from higanvn.engine.rich_text import RichTextSegment
        
        seg = RichTextSegment(text="Hello")
        assert len(seg) == 5
        assert seg.char_count == 5
    
    def test_segment_default_style(self):
        """Test segment default style."""
        from higanvn.engine.rich_text import RichTextSegment, EffectType
        
        seg = RichTextSegment(text="Test")
        assert seg.style.bold is False
        assert seg.style.effect == EffectType.NONE
        assert seg.pause_ms == 0
        assert seg.speed_multiplier == 1.0


class TestRichTextLine:
    """测试 RichTextLine"""
    
    def test_line_text(self):
        """Test line text property."""
        from higanvn.engine.rich_text import RichTextLine, RichTextSegment
        
        line = RichTextLine(segments=[
            RichTextSegment(text="Hello "),
            RichTextSegment(text="World"),
        ])
        
        assert line.text == "Hello World"
    
    def test_line_char_count(self):
        """Test line character count."""
        from higanvn.engine.rich_text import RichTextLine, RichTextSegment
        
        line = RichTextLine(segments=[
            RichTextSegment(text="Hello "),
            RichTextSegment(text="World"),
        ])
        
        assert line.char_count == 11


class TestTypewriterIntegration:
    """测试与打字机系统的集成"""
    
    def test_parse_rich_text_function(self):
        """Test parse_rich_text function from typewriter module."""
        from higanvn.engine.typewriter import parse_rich_text
        
        segments = parse_rich_text("[color=#FF0000]Red[/color] Normal")
        
        assert len(segments) == 2
        assert segments[0].text == "Red"
        assert segments[0].color == (255, 0, 0)
        assert segments[1].text == " Normal"
    
    def test_get_rich_segments_function(self):
        """Test get_rich_segments function."""
        from higanvn.engine.typewriter import get_rich_segments
        
        segments = get_rich_segments("[b]Bold[/b]")
        
        assert len(segments) == 1
        assert segments[0].style.bold is True
    
    def test_text_segment_from_rich_segment(self):
        """Test TextSegment.from_rich_segment conversion."""
        from higanvn.engine.typewriter import TextSegment
        from higanvn.engine.rich_text import RichTextSegment, TextStyle, EffectType
        
        rich_seg = RichTextSegment(
            text="Test",
            style=TextStyle(
                color=(255, 0, 0),
                bold=True,
                effect=EffectType.SHAKE,
            )
        )
        
        text_seg = TextSegment.from_rich_segment(rich_seg)
        
        assert text_seg.text == "Test"
        assert text_seg.color == (255, 0, 0)
        assert text_seg.bold is True
        assert text_seg.shake is True


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_module_parse_rich_text(self):
        """Test module-level parse_rich_text."""
        from higanvn.engine.rich_text import parse_rich_text
        
        segments = parse_rich_text("[b]Bold[/b]")
        assert len(segments) == 1
        assert segments[0].style.bold is True
    
    def test_module_strip_rich_tags(self):
        """Test module-level strip_rich_tags."""
        from higanvn.engine.rich_text import strip_rich_tags
        
        plain = strip_rich_tags("[color=red]Hello[/color]")
        assert plain == "Hello"
    
    def test_module_get_plain_length(self):
        """Test module-level get_plain_length."""
        from higanvn.engine.rich_text import get_plain_length
        
        length = get_plain_length("[b]Test[/b]{pause=100}")
        assert length == 4


class TestNamedColors:
    """测试命名颜色"""
    
    def test_emotion_colors(self):
        """Test emotion-related named colors."""
        from higanvn.engine.rich_text import NAMED_COLORS
        
        assert "anger" in NAMED_COLORS
        assert "sadness" in NAMED_COLORS
        assert "happy" in NAMED_COLORS
        assert "fear" in NAMED_COLORS
        assert "surprise" in NAMED_COLORS
    
    def test_vn_specific_colors(self):
        """Test VN-specific named colors."""
        from higanvn.engine.rich_text import NAMED_COLORS
        
        assert "whisper" in NAMED_COLORS
        assert "shout" in NAMED_COLORS
        assert "thought" in NAMED_COLORS
        assert "narration" in NAMED_COLORS
        assert "system" in NAMED_COLORS


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_text(self):
        """Test parsing empty text."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("")
        
        assert len(segments) == 0
    
    def test_only_tags(self):
        """Test parsing text with only tags (no content)."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[b][/b]")
        
        assert len(segments) == 0
    
    def test_unclosed_tag(self):
        """Test parsing unclosed tag."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[b]Bold text")
        
        # Should still parse, treating rest as styled text
        assert len(segments) >= 1
        assert segments[0].style.bold is True
    
    def test_mismatched_tags(self):
        """Test parsing mismatched tags."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[b]Bold[/i]text[/b]")
        
        # Should handle gracefully
        assert len(segments) >= 1
    
    def test_invalid_size_value(self):
        """Test parsing invalid size value."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[size=invalid]Text[/size]")
        
        assert len(segments) == 1
        assert segments[0].style.size_scale == 1.0  # Default
    
    def test_size_clamping(self):
        """Test size value clamping."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        
        # Too small
        segments = parser.parse("[size=0.1]Small[/size]")
        assert segments[0].style.size_scale >= 0.5
        
        # Too large
        segments = parser.parse("[size=10]Large[/size]")
        assert segments[0].style.size_scale <= 3.0
    
    def test_unicode_text(self):
        """Test parsing Unicode text."""
        from higanvn.engine.rich_text import RichTextParser
        
        parser = RichTextParser()
        segments = parser.parse("[color=red]你好世界[/color] 🎮 [b]ゲーム[/b]")
        
        assert len(segments) == 3
        assert "你好世界" in segments[0].text
        assert "🎮" in segments[1].text
        assert "ゲーム" in segments[2].text


class TestTextPanelRichTextIntegration:
    """Test rich text integration with text_panel module."""
    
    def test_wrap_rich_text_import(self):
        """Test that wrap_rich_text can be imported."""
        from higanvn.engine.text_panel import wrap_rich_text
        assert callable(wrap_rich_text)
    
    def test_render_rich_text_line_import(self):
        """Test that render_rich_text_line can be imported."""
        from higanvn.engine.text_panel import render_rich_text_line
        assert callable(render_rich_text_line)
    
    def test_wrap_rich_text_basic(self):
        """Test basic rich text wrapping."""
        from higanvn.engine.text_panel import wrap_rich_text
        import pygame
        pygame.font.init()
        
        font = pygame.font.SysFont("arial", 24)
        text = "[color=red]Hello[/color] World"
        
        lines = wrap_rich_text(text, font, 500)
        assert len(lines) >= 1
        
        # 验证所有段落加起来是完整文本
        all_text = ""
        for line in lines:
            for seg in line:
                all_text += seg.text
        assert all_text == "Hello World"
    
    def test_wrap_rich_text_long_text(self):
        """Test wrapping long rich text with spaces."""
        from higanvn.engine.text_panel import wrap_rich_text
        import pygame
        pygame.font.init()
        
        font = pygame.font.SysFont("arial", 24)
        # 使用带空格的英文，确保能换行
        text = "[b]This is a very long long long long long text that should wrap to multiple lines.[/b]"
        
        lines = wrap_rich_text(text, font, 200)
        assert len(lines) >= 2  # 应该换行
    
    def test_wrap_rich_text_newline(self):
        """Test explicit newline in rich text."""
        from higanvn.engine.text_panel import wrap_rich_text
        import pygame
        pygame.font.init()
        
        font = pygame.font.SysFont("arial", 24)
        text = "Line1\nLine2"
        
        lines = wrap_rich_text(text, font, 500)
        assert len(lines) == 2
    
    def test_draw_text_panel_signature(self):
        """Test that draw_text_panel has rich_text_enabled parameter."""
        from higanvn.engine.text_panel import draw_text_panel
        import inspect
        
        sig = inspect.signature(draw_text_panel)
        params = list(sig.parameters.keys())
        
        assert 'rich_text_enabled' in params
        assert 'font_getter' in params
        assert 'default_font_size' in params
    
    def test_wrap_rich_text_empty(self):
        """Test wrapping empty text."""
        from higanvn.engine.text_panel import wrap_rich_text
        import pygame
        pygame.font.init()
        
        font = pygame.font.SysFont("arial", 24)
        lines = wrap_rich_text("", font, 500)
        assert len(lines) == 0
    
    def test_wrap_rich_text_preserves_style(self):
        """Test that wrapping preserves text styles."""
        from higanvn.engine.text_panel import wrap_rich_text
        from higanvn.engine.rich_text import EffectType
        import pygame
        pygame.font.init()
        
        font = pygame.font.SysFont("arial", 24)
        text = "[b]Bold[/b] [i]Italic[/i] [shake]Shake[/shake]"
        
        lines = wrap_rich_text(text, font, 500)
        assert len(lines) >= 1
        
        # 验证样式保留
        all_segments = [seg for line in lines for seg in line]
        bold_segs = [s for s in all_segments if s.style.bold and "Bold" in s.text]
        italic_segs = [s for s in all_segments if s.style.italic and "Italic" in s.text]
        shake_segs = [s for s in all_segments if s.style.effect == EffectType.SHAKE and "Shake" in s.text]
        
        assert len(bold_segs) >= 1
        assert len(italic_segs) >= 1
        assert len(shake_segs) >= 1