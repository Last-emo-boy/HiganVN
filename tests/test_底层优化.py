"""Tests for enhanced bottom layer components."""
import pytest
import time
import threading


class TestImageCache:
    """Test enhanced image cache with LRU eviction."""
    
    def test_cache_stats_dataclass(self):
        """Test CacheStats dataclass."""
        from higanvn.engine.image_cache import CacheStats
        
        stats = CacheStats(entries=10, hits=80, misses=20, bytes_used=1024*1024)
        assert stats.hit_rate == 0.8
        assert stats.entries == 10
    
    def test_cache_entry_dataclass(self):
        """Test CacheEntry dataclass."""
        from higanvn.engine.image_cache import CacheEntry
        
        entry = CacheEntry(
            surface=None,
            path="test.png",
            width=100,
            height=100,
            bytes_estimate=40000,
        )
        assert entry.path == "test.png"
        assert entry.access_count == 0
    
    def test_image_cache_initialization(self):
        """Test ImageCache creation."""
        from higanvn.engine.image_cache import ImageCache
        
        cache = ImageCache(max_bytes=1024*1024)
        assert cache.max_bytes == 1024*1024
        assert cache.bytes_used == 0
    
    def test_cache_has_and_get(self):
        """Test has() and get() methods."""
        from higanvn.engine.image_cache import ImageCache
        
        cache = ImageCache()
        assert not cache.has("nonexistent.png")
        assert cache.get("nonexistent.png") is None
    
    def test_cache_evict(self):
        """Test manual eviction."""
        from higanvn.engine.image_cache import ImageCache
        
        cache = ImageCache()
        # Evicting non-existent should return False
        assert not cache.evict("nonexistent.png")
    
    def test_cache_clear(self):
        """Test cache clearing."""
        from higanvn.engine.image_cache import ImageCache
        
        cache = ImageCache()
        cache.clear()
        stats = cache.get_stats()
        assert stats.entries == 0
        assert stats.hits == 0
        assert stats.misses == 0
    
    def test_set_max_bytes(self):
        """Test changing memory limit."""
        from higanvn.engine.image_cache import ImageCache
        
        cache = ImageCache(max_bytes=1024)
        assert cache.max_bytes == 1024
        
        cache.set_max_bytes(2048)
        assert cache.max_bytes == 2048
    
    def test_legacy_api_functions(self):
        """Test legacy API compatibility."""
        from higanvn.engine.image_cache import get_stats, clear, get_cache
        
        clear()
        stats = get_stats()
        assert "images" in stats
        assert "cached" in stats["images"]
        assert "hits" in stats["images"]


class TestEventBus:
    """Test enhanced EventBus."""
    
    def test_basic_subscribe_emit(self):
        """Test basic subscription and emit."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        received = []
        
        def handler(data):
            received.append(data)
        
        bus.subscribe("test", handler)
        bus.emit("test", value=42)
        
        assert len(received) == 1
        assert received[0]["value"] == 42
    
    def test_unsubscribe_via_return(self):
        """Test unsubscribe via returned function."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        received = []
        
        def handler(data):
            received.append(data)
        
        unsub = bus.subscribe("test", handler)
        bus.emit("test", a=1)
        
        unsub()
        bus.emit("test", a=2)
        
        assert len(received) == 1
    
    def test_has_listeners(self):
        """Test has_listeners method."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        assert not bus.has_listeners("test")
        
        bus.subscribe("test", lambda d: None)
        assert bus.has_listeners("test")
    
    def test_listener_count(self):
        """Test listener_count method."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        assert bus.listener_count("test") == 0
        
        bus.subscribe("test", lambda d: None)
        bus.subscribe("test", lambda d: None)
        assert bus.listener_count("test") == 2
    
    def test_get_stats(self):
        """Test get_stats method."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        bus.subscribe("a", lambda d: None)
        bus.emit("a")
        bus.emit("b")
        
        stats = bus.get_stats()
        assert stats["total_emits"] == 2
        assert "events" in stats
        assert "listeners" in stats
    
    def test_clear(self):
        """Test clear method."""
        from higanvn.engine.event_bus import EventBus
        
        bus = EventBus()
        bus.subscribe("test", lambda d: None)
        bus.emit("test")
        
        bus.clear()
        assert bus.listener_count("test") == 0
        assert bus.get_stats()["total_emits"] == 0


class TestResourceManager:
    """Test ResourceManager."""
    
    def test_resource_type_enum(self):
        """Test ResourceType enum."""
        from higanvn.engine.resource_manager import ResourceType
        
        assert ResourceType.BACKGROUND.value == "bg"
        assert ResourceType.CHARACTER.value == "ch"
        assert ResourceType.CG.value == "cg"
    
    def test_resource_stats_dataclass(self):
        """Test ResourceStats dataclass."""
        from higanvn.engine.resource_manager import ResourceStats
        
        stats = ResourceStats(
            images_cached=10,
            images_bytes=1024*1024,
            images_limit=256*1024*1024,
        )
        assert stats.images_usage_mb == 1.0
        assert stats.images_limit_mb == 256.0
    
    def test_manager_initialization(self):
        """Test ResourceManager creation."""
        from higanvn.engine.resource_manager import ResourceManager
        
        rm = ResourceManager()
        assert rm is not None
    
    def test_set_asset_root(self):
        """Test set_asset_root."""
        from higanvn.engine.resource_manager import ResourceManager
        
        rm = ResourceManager()
        rm.set_asset_root("assets")
        assert rm._asset_root is not None
    
    def test_get_stats(self):
        """Test get_stats method."""
        from higanvn.engine.resource_manager import ResourceManager
        
        rm = ResourceManager()
        stats = rm.get_stats()
        
        assert hasattr(stats, "images_cached")
        assert hasattr(stats, "preload_total")
    
    def test_get_load_counts(self):
        """Test get_load_counts method."""
        from higanvn.engine.resource_manager import ResourceManager
        
        rm = ResourceManager()
        counts = rm.get_load_counts()
        
        assert "bg" in counts
        assert "ch" in counts
    
    def test_global_singleton(self):
        """Test global resource manager singleton."""
        from higanvn.engine.resource_manager import get_resource_manager, init_resource_manager
        
        rm1 = get_resource_manager()
        rm2 = get_resource_manager()
        assert rm1 is rm2


class TestPerformanceMonitor:
    """Test PerformanceMonitor."""
    
    def test_frame_metrics_dataclass(self):
        """Test FrameMetrics dataclass."""
        from higanvn.engine.performance import FrameMetrics
        
        metrics = FrameMetrics(
            timestamp=time.time(),
            frame_time_ms=16.67,
            render_time_ms=8.0,
        )
        assert metrics.frame_time_ms == 16.67
        assert metrics.render_time_ms == 8.0
    
    def test_performance_stats_dataclass(self):
        """Test PerformanceStats dataclass."""
        from higanvn.engine.performance import PerformanceStats
        
        stats = PerformanceStats(fps=60.0, frame_time_avg=16.67)
        assert stats.fps == 60.0
    
    def test_monitor_initialization(self):
        """Test PerformanceMonitor creation."""
        from higanvn.engine.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        assert monitor is not None
    
    def test_frame_context_manager(self):
        """Test frame timing context manager."""
        from higanvn.engine.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        with monitor.frame():
            time.sleep(0.01)  # 10ms
        
        stats = monitor.get_stats()
        # Should have recorded at least one frame
        assert len(monitor._frames) == 1
        assert stats.frame_time_avg >= 10  # At least 10ms
    
    def test_section_context_manager(self):
        """Test section timing context manager."""
        from higanvn.engine.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        with monitor.frame():
            with monitor.section("render"):
                time.sleep(0.005)  # 5ms
        
        stats = monitor.get_stats()
        assert stats.render_time_avg >= 5  # At least 5ms
    
    def test_custom_metric(self):
        """Test custom metric recording."""
        from higanvn.engine.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        monitor.record_metric("test_metric", 10.0)
        monitor.record_metric("test_metric", 20.0)
        monitor.record_metric("test_metric", 30.0)
        
        avg = monitor.get_custom_metric_avg("test_metric")
        assert avg == 20.0
    
    def test_reset(self):
        """Test reset method."""
        from higanvn.engine.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        with monitor.frame():
            pass
        
        monitor.record_metric("test", 1.0)
        
        monitor.reset()
        
        assert len(monitor._frames) == 0
        assert len(monitor._custom_metrics) == 0
    
    def test_timer_class(self):
        """Test Timer utility class."""
        from higanvn.engine.performance import Timer
        
        timer = Timer()
        timer.start()
        time.sleep(0.01)
        elapsed = timer.stop()
        
        assert elapsed >= 10  # At least 10ms
    
    def test_timer_context_manager(self):
        """Test Timer as context manager."""
        from higanvn.engine.performance import Timer
        
        with Timer() as t:
            time.sleep(0.01)
        
        assert t.elapsed_ms() >= 10
    
    def test_global_monitor(self):
        """Test global monitor singleton."""
        from higanvn.engine.performance import get_monitor
        
        m1 = get_monitor()
        m2 = get_monitor()
        assert m1 is m2


class TestNewEventTypes:
    """Test new event types added to events.py."""
    
    def test_resource_load_event(self):
        """Test ResourceLoadEvent."""
        from higanvn.engine.events import ResourceLoadEvent
        
        event = ResourceLoadEvent(
            resource_type="bg",
            path="test.png",
            from_cache=True,
            load_time_ms=5.0,
        )
        assert event.resource_type == "bg"
        assert event.from_cache
    
    def test_cache_evict_event(self):
        """Test CacheEvictEvent."""
        from higanvn.engine.events import CacheEvictEvent
        
        event = CacheEvictEvent(path="old.png", bytes_freed=1024)
        assert event.path == "old.png"
        assert event.bytes_freed == 1024
    
    def test_debug_toggle_event(self):
        """Test DebugToggleEvent."""
        from higanvn.engine.events import DebugToggleEvent
        
        event = DebugToggleEvent(enabled=True, debug_type="hud")
        assert event.enabled
        assert event.debug_type == "hud"
    
    def test_screenshot_event(self):
        """Test ScreenshotEvent."""
        from higanvn.engine.events import ScreenshotEvent
        
        event = ScreenshotEvent(path="/tmp/screen.png", success=True)
        assert event.path == "/tmp/screen.png"
        assert event.success
    
    def test_flow_map_event(self):
        """Test FlowMapEvent."""
        from higanvn.engine.events import FlowMapEvent
        
        event = FlowMapEvent(action="open")
        assert event.action == "open"
    
    def test_auto_mode_event(self):
        """Test AutoModeEvent."""
        from higanvn.engine.events import AutoModeEvent
        
        event = AutoModeEvent(enabled=True)
        assert event.enabled
    
    def test_fast_forward_event(self):
        """Test FastForwardEvent."""
        from higanvn.engine.events import FastForwardEvent
        
        event = FastForwardEvent(enabled=True, held=True)
        assert event.enabled
        assert event.held
