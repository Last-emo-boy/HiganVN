"""
Tests for Audio System
"""
import pytest
from unittest.mock import MagicMock, patch


class TestAudioManager:
    """Test AudioManager class."""
    
    def test_import(self):
        """Test that AudioManager can be imported."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        assert AudioManager is not None
        assert AudioChannel is not None
    
    def test_init(self):
        """Test AudioManager initialization."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        assert manager.master_volume == 1.0
        assert manager.volumes[AudioChannel.BGM] == 1.0
        assert manager.volumes[AudioChannel.SE] == 1.0
        assert manager.volumes[AudioChannel.VOICE] == 1.0
        assert manager.volumes[AudioChannel.AMBIENT] == 0.5
    
    def test_get_effective_volume(self):
        """Test effective volume calculation."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        # Default volumes
        assert manager.get_effective_volume(AudioChannel.BGM) == 1.0
        
        # With master volume
        manager.master_volume = 0.5
        assert manager.get_effective_volume(AudioChannel.BGM) == 0.5
        
        # With channel volume
        manager.volumes[AudioChannel.BGM] = 0.8
        assert manager.get_effective_volume(AudioChannel.BGM) == 0.4  # 0.5 * 0.8
    
    def test_set_volume(self):
        """Test setting channel volume."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        manager.set_volume(AudioChannel.SE, 0.7)
        assert manager.volumes[AudioChannel.SE] == 0.7
        
        # Clamp to range
        manager.set_volume(AudioChannel.SE, 1.5)
        assert manager.volumes[AudioChannel.SE] == 1.0
        
        manager.set_volume(AudioChannel.SE, -0.5)
        assert manager.volumes[AudioChannel.SE] == 0.0
    
    def test_set_master_volume(self):
        """Test setting master volume."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        manager.set_master_volume(0.6)
        assert manager.master_volume == 0.6
        
        # Clamp to range
        manager.set_master_volume(2.0)
        assert manager.master_volume == 1.0


class TestFadeTask:
    """Test FadeTask class."""
    
    def test_fade_task_creation(self):
        """Test FadeTask creation."""
        from higanvn.engine.audio_utils import FadeTask, AudioChannel
        
        task = FadeTask(
            channel=AudioChannel.BGM,
            start_volume=0.0,
            end_volume=1.0,
            duration_ms=1000,
            start_time=0,
        )
        
        assert task.channel == AudioChannel.BGM
        assert task.start_volume == 0.0
        assert task.end_volume == 1.0
        assert task.duration_ms == 1000
        assert task.callback is None


class TestAudioChannel:
    """Test AudioChannel enum."""
    
    def test_channels(self):
        """Test AudioChannel values."""
        from higanvn.engine.audio_utils import AudioChannel
        
        assert AudioChannel.BGM is not None
        assert AudioChannel.SE is not None
        assert AudioChannel.VOICE is not None
        assert AudioChannel.AMBIENT is not None
        
        # Ensure they are distinct
        channels = [AudioChannel.BGM, AudioChannel.SE, AudioChannel.VOICE, AudioChannel.AMBIENT]
        assert len(set(channels)) == 4


class TestGlobalFunctions:
    """Test global functions for backward compatibility."""
    
    def test_init_audio_manager(self):
        """Test init_audio_manager function."""
        from higanvn.engine.audio_utils import init_audio_manager, get_audio_manager
        
        resolve_path = lambda x: f"/path/{x}"
        manager = init_audio_manager(resolve_path)
        
        assert manager is not None
        assert get_audio_manager() is manager
    
    def test_legacy_play_bgm(self):
        """Test legacy play_bgm function signature."""
        from higanvn.engine.audio_utils import play_bgm
        import inspect
        
        sig = inspect.signature(play_bgm)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'resolve_path' in params
    
    def test_legacy_play_se(self):
        """Test legacy play_se function signature."""
        from higanvn.engine.audio_utils import play_se
        import inspect
        
        sig = inspect.signature(play_se)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'resolve_path' in params
    
    def test_legacy_load_voice(self):
        """Test legacy load_voice function signature."""
        from higanvn.engine.audio_utils import load_voice
        import inspect
        
        sig = inspect.signature(load_voice)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'resolve_path' in params


class TestAudioManagerMethods:
    """Test AudioManager method signatures."""
    
    def test_play_bgm_signature(self):
        """Test AudioManager.play_bgm signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.play_bgm)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'fade_in_ms' in params
        assert 'loops' in params
    
    def test_stop_bgm_signature(self):
        """Test AudioManager.stop_bgm signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.stop_bgm)
        params = list(sig.parameters.keys())
        
        assert 'fade_out_ms' in params
    
    def test_fade_bgm_signature(self):
        """Test AudioManager.fade_bgm signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.fade_bgm)
        params = list(sig.parameters.keys())
        
        assert 'target_volume' in params
        assert 'duration_ms' in params
        assert 'callback' in params
    
    def test_crossfade_bgm_signature(self):
        """Test AudioManager.crossfade_bgm signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.crossfade_bgm)
        params = list(sig.parameters.keys())
        
        assert 'new_path' in params
        assert 'duration_ms' in params
        assert 'new_volume' in params
    
    def test_play_se_signature(self):
        """Test AudioManager.play_se signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.play_se)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'fade_in_ms' in params
    
    def test_play_voice_signature(self):
        """Test AudioManager.play_voice signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.play_voice)
        params = list(sig.parameters.keys())
        
        assert 'path' in params
        assert 'volume' in params
        assert 'stop_current' in params
    
    def test_play_ambient_signature(self):
        """Test AudioManager.play_ambient signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.play_ambient)
        params = list(sig.parameters.keys())
        
        assert 'name' in params
        assert 'path' in params
        assert 'volume' in params
        assert 'fade_in_ms' in params
        assert 'loops' in params
    
    def test_stop_ambient_signature(self):
        """Test AudioManager.stop_ambient signature."""
        from higanvn.engine.audio_utils import AudioManager
        import inspect
        
        sig = inspect.signature(AudioManager.stop_ambient)
        params = list(sig.parameters.keys())
        
        assert 'name' in params
        assert 'fade_out_ms' in params
    
    def test_update_exists(self):
        """Test that update method exists."""
        from higanvn.engine.audio_utils import AudioManager
        
        assert hasattr(AudioManager, 'update')
        assert callable(getattr(AudioManager, 'update'))
    
    def test_stop_all_exists(self):
        """Test that stop_all method exists."""
        from higanvn.engine.audio_utils import AudioManager
        
        assert hasattr(AudioManager, 'stop_all')
        assert callable(getattr(AudioManager, 'stop_all'))


class TestFadeLogic:
    """Test fade in/out logic."""
    
    def test_start_fade(self):
        """Test starting a fade task."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        # Start a fade
        manager._start_fade(
            channel=AudioChannel.BGM,
            start_volume=0.0,
            end_volume=1.0,
            duration_ms=1000,
        )
        
        assert len(manager._fade_tasks) == 1
        task = manager._fade_tasks[0]
        assert task.channel == AudioChannel.BGM
        assert task.start_volume == 0.0
        assert task.end_volume == 1.0
    
    def test_fade_replaces_same_channel(self):
        """Test that new fade replaces existing one for same channel."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        # Start first fade
        manager._start_fade(
            channel=AudioChannel.BGM,
            start_volume=0.0,
            end_volume=0.5,
            duration_ms=1000,
        )
        
        # Start second fade on same channel
        manager._start_fade(
            channel=AudioChannel.BGM,
            start_volume=0.5,
            end_volume=1.0,
            duration_ms=1000,
        )
        
        # Should only have the second task
        assert len(manager._fade_tasks) == 1
        assert manager._fade_tasks[0].end_volume == 1.0
    
    def test_fade_different_channels(self):
        """Test fades on different channels are independent."""
        from higanvn.engine.audio_utils import AudioManager, AudioChannel
        
        resolve_path = lambda x: f"/path/{x}"
        manager = AudioManager(resolve_path)
        
        # Start fades on different channels
        manager._start_fade(
            channel=AudioChannel.BGM,
            start_volume=0.0,
            end_volume=1.0,
            duration_ms=1000,
        )
        
        manager._start_fade(
            channel=AudioChannel.SE,
            start_volume=0.5,
            end_volume=0.0,
            duration_ms=500,
        )
        
        # Should have both tasks
        assert len(manager._fade_tasks) == 2
