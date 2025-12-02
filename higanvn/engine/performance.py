"""
Performance Monitor for HiganVN.

Tracks:
- Frame rate (FPS)
- Frame times
- Memory usage
- Resource loading times
- Event processing times
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from collections import deque
import gc


@dataclass
class FrameMetrics:
    """Single frame metrics."""
    timestamp: float
    frame_time_ms: float
    render_time_ms: float = 0.0
    update_time_ms: float = 0.0
    event_time_ms: float = 0.0


@dataclass 
class PerformanceStats:
    """Performance statistics snapshot."""
    # FPS
    fps: float = 0.0
    fps_avg: float = 0.0
    fps_min: float = 0.0
    fps_max: float = 0.0
    
    # Frame times (ms)
    frame_time_avg: float = 0.0
    frame_time_max: float = 0.0
    frame_time_p95: float = 0.0
    
    # Memory (bytes)
    memory_used: int = 0
    memory_peak: int = 0
    gc_collections: int = 0
    
    # Timing breakdown
    render_time_avg: float = 0.0
    update_time_avg: float = 0.0
    event_time_avg: float = 0.0


class PerformanceMonitor:
    """
    Performance monitoring system.
    
    Usage:
        monitor = PerformanceMonitor()
        
        # In game loop
        with monitor.frame():
            with monitor.section("render"):
                render()
            with monitor.section("update"):
                update()
        
        # Get stats
        stats = monitor.get_stats()
        print(f"FPS: {stats.fps:.1f}")
    """
    
    def __init__(self, history_size: int = 120):  # 2 seconds at 60fps
        self._history_size = history_size
        self._frames: deque[FrameMetrics] = deque(maxlen=history_size)
        self._lock = threading.RLock()
        
        # Current frame tracking
        self._frame_start: Optional[float] = None
        self._section_times: Dict[str, float] = {}
        self._current_sections: Dict[str, float] = {}
        
        # Memory tracking
        self._memory_peak = 0
        self._gc_count = 0
        
        # Custom metrics
        self._custom_metrics: Dict[str, deque] = {}
    
    def frame(self) -> 'FrameContext':
        """Start timing a frame. Use as context manager."""
        return FrameContext(self)
    
    def section(self, name: str) -> 'SectionContext':
        """Start timing a section. Use as context manager."""
        return SectionContext(self, name)
    
    def _begin_frame(self) -> None:
        """Begin frame timing."""
        self._frame_start = time.perf_counter()
        self._section_times.clear()
        self._current_sections.clear()
    
    def _end_frame(self) -> None:
        """End frame timing and record metrics."""
        if self._frame_start is None:
            return
        
        end_time = time.perf_counter()
        frame_time = (end_time - self._frame_start) * 1000  # ms
        
        metrics = FrameMetrics(
            timestamp=end_time,
            frame_time_ms=frame_time,
            render_time_ms=self._section_times.get("render", 0.0),
            update_time_ms=self._section_times.get("update", 0.0),
            event_time_ms=self._section_times.get("event", 0.0),
        )
        
        with self._lock:
            self._frames.append(metrics)
        
        self._frame_start = None
    
    def _begin_section(self, name: str) -> None:
        """Begin section timing."""
        self._current_sections[name] = time.perf_counter()
    
    def _end_section(self, name: str) -> None:
        """End section timing."""
        if name in self._current_sections:
            elapsed = (time.perf_counter() - self._current_sections[name]) * 1000
            self._section_times[name] = elapsed
            del self._current_sections[name]
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a custom metric."""
        with self._lock:
            if name not in self._custom_metrics:
                self._custom_metrics[name] = deque(maxlen=self._history_size)
            self._custom_metrics[name].append(value)
    
    def get_stats(self) -> PerformanceStats:
        """Get current performance statistics."""
        with self._lock:
            frames = list(self._frames)
        
        if not frames:
            return PerformanceStats()
        
        # Calculate FPS
        if len(frames) >= 2:
            time_span = frames[-1].timestamp - frames[0].timestamp
            fps = len(frames) / time_span if time_span > 0 else 0
        else:
            fps = 0
        
        # Frame times
        frame_times = [f.frame_time_ms for f in frames]
        frame_times_sorted = sorted(frame_times)
        
        avg_frame = sum(frame_times) / len(frame_times)
        max_frame = max(frame_times)
        p95_idx = int(len(frame_times_sorted) * 0.95)
        p95_frame = frame_times_sorted[p95_idx] if p95_idx < len(frame_times_sorted) else max_frame
        
        # FPS from frame times
        fps_values = [1000 / ft if ft > 0 else 0 for ft in frame_times]
        fps_avg = sum(fps_values) / len(fps_values) if fps_values else 0
        fps_min = min(fps_values) if fps_values else 0
        fps_max = max(fps_values) if fps_values else 0
        
        # Section times
        render_times = [f.render_time_ms for f in frames if f.render_time_ms > 0]
        update_times = [f.update_time_ms for f in frames if f.update_time_ms > 0]
        event_times = [f.event_time_ms for f in frames if f.event_time_ms > 0]
        
        render_avg = sum(render_times) / len(render_times) if render_times else 0
        update_avg = sum(update_times) / len(update_times) if update_times else 0
        event_avg = sum(event_times) / len(event_times) if event_times else 0
        
        # Memory
        try:
            import psutil
            process = psutil.Process()
            memory_used = process.memory_info().rss
        except Exception:
            memory_used = 0
        
        if memory_used > self._memory_peak:
            self._memory_peak = memory_used
        
        gc_stats = gc.get_stats()
        gc_collections = sum(s.get('collections', 0) for s in gc_stats)
        
        return PerformanceStats(
            fps=fps,
            fps_avg=fps_avg,
            fps_min=fps_min,
            fps_max=fps_max,
            frame_time_avg=avg_frame,
            frame_time_max=max_frame,
            frame_time_p95=p95_frame,
            memory_used=memory_used,
            memory_peak=self._memory_peak,
            gc_collections=gc_collections,
            render_time_avg=render_avg,
            update_time_avg=update_avg,
            event_time_avg=event_avg,
        )
    
    def get_custom_metric_avg(self, name: str) -> float:
        """Get average of a custom metric."""
        with self._lock:
            values = list(self._custom_metrics.get(name, []))
        return sum(values) / len(values) if values else 0.0
    
    def reset(self) -> None:
        """Reset all tracking data."""
        with self._lock:
            self._frames.clear()
            self._custom_metrics.clear()
            self._memory_peak = 0


class FrameContext:
    """Context manager for frame timing."""
    
    def __init__(self, monitor: PerformanceMonitor):
        self._monitor = monitor
    
    def __enter__(self):
        self._monitor._begin_frame()
        return self
    
    def __exit__(self, *args):
        self._monitor._end_frame()


class SectionContext:
    """Context manager for section timing."""
    
    def __init__(self, monitor: PerformanceMonitor, name: str):
        self._monitor = monitor
        self._name = name
    
    def __enter__(self):
        self._monitor._begin_section(self._name)
        return self
    
    def __exit__(self, *args):
        self._monitor._end_section(self._name)


# ============================================================================
# Timer utilities
# ============================================================================

class Timer:
    """Simple timer for measuring durations."""
    
    def __init__(self):
        self._start: Optional[float] = None
        self._elapsed: float = 0.0
    
    def start(self) -> 'Timer':
        """Start the timer."""
        self._start = time.perf_counter()
        return self
    
    def stop(self) -> float:
        """Stop the timer and return elapsed time in ms."""
        if self._start is not None:
            self._elapsed = (time.perf_counter() - self._start) * 1000
            self._start = None
        return self._elapsed
    
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self._start is not None:
            return (time.perf_counter() - self._start) * 1000
        return self._elapsed
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


def time_function(func: Callable) -> Callable:
    """Decorator to time function execution."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"{func.__name__}: {elapsed:.2f}ms")
        return result
    return wrapper


# ============================================================================
# Global instance
# ============================================================================

_global_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor
