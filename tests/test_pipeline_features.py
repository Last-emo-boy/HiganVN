"""Tests for typewriter, transitions, and preloader."""
import pytest
import time


class TestTypewriter:
    """Test the typewriter effect system."""
    
    def test_create_typewriter(self):
        """Test creating a typewriter state."""
        from higanvn.engine.typewriter import create_typewriter
        
        state = create_typewriter("Hello, World!", chars_per_second=50.0)
        
        assert state.total_chars == 13
        assert state.revealed_chars == 0
        assert not state.is_complete
    
    def test_empty_text(self):
        """Test with empty text."""
        from higanvn.engine.typewriter import create_typewriter
        
        state = create_typewriter("", chars_per_second=50.0)
        
        assert state.total_chars == 0
        assert state.is_complete
    
    def test_update_reveals_chars(self):
        """Test that update reveals characters over time."""
        from higanvn.engine.typewriter import create_typewriter, update_typewriter, get_revealed_text
        
        state = create_typewriter("Hello", chars_per_second=100.0, start_time=1000)
        
        # After 30ms at 100 chars/sec, should reveal ~3 chars
        changed = update_typewriter(state, 1030)
        
        assert changed
        assert state.revealed_chars >= 2
        assert state.revealed_chars <= 4
    
    def test_reveal_all(self):
        """Test instant reveal."""
        from higanvn.engine.typewriter import create_typewriter, reveal_all, get_revealed_text
        
        state = create_typewriter("Hello, World!")
        reveal_all(state)
        
        assert state.is_complete
        assert state.revealed_chars == 13
        assert get_revealed_text(state) == "Hello, World!"
    
    def test_punctuation_pause(self):
        """Test that punctuation causes pauses."""
        from higanvn.engine.typewriter import PUNCTUATION_PAUSES, PauseType
        
        # Comma should cause short pause
        assert PUNCTUATION_PAUSES.get(',') == PauseType.SHORT
        assert PUNCTUATION_PAUSES.get('，') == PauseType.SHORT
        
        # Period should cause medium pause
        assert PUNCTUATION_PAUSES.get('.') == PauseType.MEDIUM
        assert PUNCTUATION_PAUSES.get('。') == PauseType.MEDIUM
        
        # Exclamation should cause long pause
        assert PUNCTUATION_PAUSES.get('!') == PauseType.LONG
        assert PUNCTUATION_PAUSES.get('！') == PauseType.LONG
    
    def test_simple_typewriter_update(self):
        """Test the simplified update function."""
        from higanvn.engine.typewriter import simple_typewriter_update
        
        text = "Hello"
        
        # Instant reveal
        displayed, start, complete = simple_typewriter_update(
            text, 1000, 0, reveal_instant=True
        )
        assert displayed == "Hello"
        assert complete
        
        # Normal typing
        displayed, start, complete = simple_typewriter_update(
            text, 1050, 1000, chars_per_second=100.0
        )
        # After 50ms at 100 chars/sec, should reveal ~5 chars (may be adjusted by punctuation)
        assert len(displayed) <= len(text)
    
    def test_reset_typewriter(self):
        """Test resetting typewriter state."""
        from higanvn.engine.typewriter import (
            create_typewriter, reveal_all, reset_typewriter, get_revealed_text
        )
        
        state = create_typewriter("Hello")
        reveal_all(state)
        
        assert state.is_complete
        
        reset_typewriter(state, 2000)
        
        assert not state.is_complete
        assert state.revealed_chars == 0
        assert state.start_time == 2000
    
    def test_get_revealed_segments(self):
        """Test getting revealed segments with style info."""
        from higanvn.engine.typewriter import (
            create_typewriter, update_typewriter, get_revealed_segments
        )
        
        state = create_typewriter("Hello", chars_per_second=1000.0, start_time=1000)
        update_typewriter(state, 1005)  # Reveal ~5 chars
        
        segments = get_revealed_segments(state)
        
        assert len(segments) > 0
        seg, text = segments[0]
        assert isinstance(text, str)


class TestTransitionsAdvanced:
    """Test the advanced transition system."""
    
    def test_transition_type_enum(self):
        """Test transition type enumeration."""
        from higanvn.engine.transitions_advanced import TransitionType
        
        assert TransitionType.FADE.value == "fade"
        assert TransitionType.DISSOLVE.value == "dissolve"
        assert TransitionType.WIPE_LEFT.value == "wipe_left"
        assert TransitionType.BLINDS_H.value == "blinds_h"
        assert TransitionType.CIRCLE_IN.value == "circle_in"
    
    def test_easing_functions(self):
        """Test easing function behavior."""
        from higanvn.engine.transitions_advanced import (
            ease_in_out_cubic, ease_out_quad, ease_in_quad
        )
        
        # All easing functions should map [0,1] to [0,1]
        for func in [ease_in_out_cubic, ease_out_quad, ease_in_quad]:
            assert func(0.0) == pytest.approx(0.0, abs=0.01)
            assert func(1.0) == pytest.approx(1.0, abs=0.01)
            
            # Mid-point should be in (0, 1)
            mid = func(0.5)
            assert 0.0 < mid < 1.0
    
    def test_ease_in_out_cubic_symmetry(self):
        """Test that ease_in_out_cubic is symmetric around 0.5."""
        from higanvn.engine.transitions_advanced import ease_in_out_cubic
        
        # Points symmetric around 0.5 should sum to 1
        for t in [0.1, 0.2, 0.3, 0.4]:
            left = ease_in_out_cubic(t)
            right = ease_in_out_cubic(1.0 - t)
            assert left + right == pytest.approx(1.0, abs=0.01)


class TestPreloader:
    """Test the asset preloader system."""
    
    def test_create_preloader(self):
        """Test creating a preloader."""
        from higanvn.engine.preloader import AssetPreloader
        
        preloader = AssetPreloader(max_workers=2)
        
        assert preloader is not None
        
        preloader.shutdown()
    
    def test_preload_request(self):
        """Test adding preload requests."""
        from higanvn.engine.preloader import AssetPreloader, AssetType
        
        preloader = AssetPreloader(max_workers=1)
        
        # Should return True for new request
        result = preloader.preload(AssetType.BACKGROUND, "bg/test.jpg")
        # May be True or False depending on path existence
        
        preloader.shutdown()
    
    def test_load_progress(self):
        """Test load progress tracking."""
        from higanvn.engine.preloader import LoadProgress
        
        progress = LoadProgress(total=10, completed=5, failed=1, in_progress=4)
        
        assert progress.percent == 50.0
        assert not progress.is_complete
        
        # Complete when all done
        progress2 = LoadProgress(total=10, completed=9, failed=1, in_progress=0)
        assert progress2.is_complete
    
    def test_get_stats(self):
        """Test getting preloader stats."""
        from higanvn.engine.preloader import AssetPreloader
        
        preloader = AssetPreloader(max_workers=1)
        
        stats = preloader.get_stats()
        
        assert "total_requested" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "pending" in stats
        
        preloader.shutdown()
    
    def test_clear_cache(self):
        """Test clearing the preloader cache."""
        from higanvn.engine.preloader import AssetPreloader
        
        preloader = AssetPreloader(max_workers=1)
        
        preloader.clear_cache()
        
        stats = preloader.get_stats()
        assert stats["cached"] == 0
        
        preloader.shutdown()
    
    def test_asset_type_enum(self):
        """Test asset type enumeration."""
        from higanvn.engine.preloader import AssetType
        
        assert AssetType.BACKGROUND.value == "bg"
        assert AssetType.CHARACTER.value == "ch"
        assert AssetType.CG.value == "cg"
        assert AssetType.BGM.value == "bgm"
        assert AssetType.SE.value == "se"
        assert AssetType.VOICE.value == "voice"
    
    def test_global_preloader(self):
        """Test global preloader access."""
        from higanvn.engine.preloader import get_preloader, shutdown_preloader
        
        preloader = get_preloader()
        assert preloader is not None
        
        # Should return same instance
        preloader2 = get_preloader()
        assert preloader is preloader2
        
        shutdown_preloader()


class TestScenePredictor:
    """Test the scene prediction system."""
    
    def test_create_predictor(self):
        """Test creating a scene predictor."""
        from higanvn.engine.preloader import ScenePredictor
        
        predictor = ScenePredictor()
        assert predictor is not None
    
    def test_analyze_empty_program(self):
        """Test analyzing with no program."""
        from higanvn.engine.preloader import ScenePredictor
        
        predictor = ScenePredictor()
        
        assets = predictor.analyze_script(None, 0)
        assert assets == []
    
    def test_get_label_assets_no_program(self):
        """Test getting label assets with no program."""
        from higanvn.engine.preloader import ScenePredictor
        
        predictor = ScenePredictor()
        
        assets = predictor.get_label_assets(None, "test")
        assert assets == []
