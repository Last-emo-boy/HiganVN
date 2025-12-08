"""
Audio Utilities - 音频工具模块

Features:
- BGM 播放/停止/淡入淡出
- SE (音效) 播放
- Voice (语音) 加载和播放
- 全局音量控制
- 音频淡入淡出动画
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from enum import Enum, auto

import pygame


class AudioChannel(Enum):
    """音频通道类型"""
    BGM = auto()
    SE = auto()
    VOICE = auto()
    AMBIENT = auto()  # 环境音


@dataclass
class FadeTask:
    """音量淡入淡出任务"""
    channel: AudioChannel
    start_volume: float
    end_volume: float
    duration_ms: int
    start_time: int
    callback: Optional[Callable[[], None]] = None
    sound: Optional[pygame.mixer.Sound] = None  # 用于 SE/Voice


class AudioManager:
    """
    音频管理器
    
    统一管理 BGM, SE, Voice 的播放和淡入淡出效果
    """
    
    def __init__(self, resolve_path: Callable[[str], str]):
        """
        Args:
            resolve_path: 路径解析函数
        """
        self.resolve_path = resolve_path
        
        # 各通道音量
        self.volumes: Dict[AudioChannel, float] = {
            AudioChannel.BGM: 1.0,
            AudioChannel.SE: 1.0,
            AudioChannel.VOICE: 1.0,
            AudioChannel.AMBIENT: 0.5,
        }
        
        # 主音量
        self.master_volume: float = 1.0
        
        # 淡入淡出任务
        self._fade_tasks: List[FadeTask] = []
        
        # 当前播放的音效
        self._current_bgm_path: Optional[str] = None
        self._current_voice: Optional[pygame.mixer.Sound] = None
        self._ambient_sounds: Dict[str, pygame.mixer.Sound] = {}
        
        # 锁
        self._lock = threading.Lock()
    
    def get_effective_volume(self, channel: AudioChannel) -> float:
        """获取实际音量（考虑主音量）"""
        return self.master_volume * self.volumes.get(channel, 1.0)
    
    def set_volume(self, channel: AudioChannel, volume: float) -> None:
        """设置通道音量"""
        self.volumes[channel] = max(0.0, min(1.0, volume))
        self._apply_volume(channel)
    
    def set_master_volume(self, volume: float) -> None:
        """设置主音量"""
        self.master_volume = max(0.0, min(1.0, volume))
        for channel in AudioChannel:
            self._apply_volume(channel)
    
    def _apply_volume(self, channel: AudioChannel) -> None:
        """应用音量到对应通道"""
        vol = self.get_effective_volume(channel)
        
        if channel == AudioChannel.BGM:
            try:
                pygame.mixer.music.set_volume(vol)
            except Exception:
                pass
        elif channel == AudioChannel.VOICE and self._current_voice:
            try:
                self._current_voice.set_volume(vol)
            except Exception:
                pass
    
    # ========================================================================
    # BGM 控制
    # ========================================================================
    
    def play_bgm(
        self,
        path: Optional[str],
        volume: Optional[float] = None,
        fade_in_ms: int = 0,
        loops: int = -1,
    ) -> None:
        """
        播放背景音乐
        
        Args:
            path: 音乐文件路径，None 表示停止
            volume: 音量覆盖
            fade_in_ms: 淡入时间（毫秒）
            loops: 循环次数（-1 = 无限）
        """
        try:
            if path:
                resolved = self.resolve_path(path)
                pygame.mixer.music.load(resolved)
                
                if volume is not None:
                    self.volumes[AudioChannel.BGM] = max(0.0, min(1.0, volume))
                
                if fade_in_ms > 0:
                    pygame.mixer.music.set_volume(0)
                    pygame.mixer.music.play(loops)
                    self._start_fade(
                        AudioChannel.BGM,
                        start_volume=0,
                        end_volume=self.get_effective_volume(AudioChannel.BGM),
                        duration_ms=fade_in_ms,
                    )
                else:
                    pygame.mixer.music.set_volume(self.get_effective_volume(AudioChannel.BGM))
                    pygame.mixer.music.play(loops)
                
                self._current_bgm_path = path
            else:
                self.stop_bgm()
        except Exception:
            pass
    
    def stop_bgm(self, fade_out_ms: int = 0) -> None:
        """停止背景音乐"""
        try:
            if fade_out_ms > 0:
                pygame.mixer.music.fadeout(fade_out_ms)
            else:
                pygame.mixer.music.stop()
            self._current_bgm_path = None
        except Exception:
            pass
    
    def pause_bgm(self) -> None:
        """暂停背景音乐"""
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass
    
    def resume_bgm(self) -> None:
        """恢复背景音乐"""
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass
    
    def fade_bgm(
        self,
        target_volume: float,
        duration_ms: int,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        BGM 音量淡入淡出
        
        Args:
            target_volume: 目标音量
            duration_ms: 持续时间
            callback: 完成回调
        """
        try:
            current = pygame.mixer.music.get_volume()
            self._start_fade(
                AudioChannel.BGM,
                start_volume=current,
                end_volume=target_volume,
                duration_ms=duration_ms,
                callback=callback,
            )
        except Exception:
            if callback:
                callback()
    
    def crossfade_bgm(
        self,
        new_path: str,
        duration_ms: int = 1000,
        new_volume: Optional[float] = None,
    ) -> None:
        """
        交叉淡入淡出到新 BGM
        
        Args:
            new_path: 新音乐路径
            duration_ms: 淡入淡出时间
            new_volume: 新音乐音量
        """
        half_duration = duration_ms // 2
        
        def on_fadeout_complete():
            self.play_bgm(new_path, volume=new_volume, fade_in_ms=half_duration)
        
        self.fade_bgm(0, half_duration, callback=on_fadeout_complete)
    
    # ========================================================================
    # SE (音效) 控制
    # ========================================================================
    
    def play_se(
        self,
        path: str,
        volume: Optional[float] = None,
        fade_in_ms: int = 0,
    ) -> Optional[pygame.mixer.Sound]:
        """
        播放音效
        
        Args:
            path: 音效文件路径
            volume: 音量覆盖
            fade_in_ms: 淡入时间
        
        Returns:
            Sound 对象
        """
        try:
            resolved = self.resolve_path(path)
            se = pygame.mixer.Sound(resolved)
            
            if volume is not None:
                effective = max(0.0, min(1.0, volume)) * self.master_volume
            else:
                effective = self.get_effective_volume(AudioChannel.SE)
            
            if fade_in_ms > 0:
                se.set_volume(0)
                se.play()
                self._start_fade(
                    AudioChannel.SE,
                    start_volume=0,
                    end_volume=effective,
                    duration_ms=fade_in_ms,
                    sound=se,
                )
            else:
                se.set_volume(effective)
                se.play()
            
            return se
        except Exception:
            return None
    
    # ========================================================================
    # Voice (语音) 控制
    # ========================================================================
    
    def load_voice(
        self,
        path: str,
        volume: Optional[float] = None,
    ) -> Optional[pygame.mixer.Sound]:
        """
        加载语音
        
        Args:
            path: 语音文件路径
            volume: 音量覆盖
        
        Returns:
            Sound 对象
        """
        try:
            resolved = self.resolve_path(path)
            snd = pygame.mixer.Sound(resolved)
            
            if volume is not None:
                effective = max(0.0, min(1.0, volume)) * self.master_volume
            else:
                effective = self.get_effective_volume(AudioChannel.VOICE)
            
            snd.set_volume(effective)
            return snd
        except Exception:
            return None
    
    def play_voice(
        self,
        path: str,
        volume: Optional[float] = None,
        stop_current: bool = True,
    ) -> Optional[pygame.mixer.Sound]:
        """
        播放语音
        
        Args:
            path: 语音文件路径
            volume: 音量覆盖
            stop_current: 是否停止当前语音
        
        Returns:
            Sound 对象
        """
        if stop_current and self._current_voice:
            try:
                self._current_voice.stop()
            except Exception:
                pass
        
        voice = self.load_voice(path, volume)
        if voice:
            voice.play()
            self._current_voice = voice
        return voice
    
    def stop_voice(self) -> None:
        """停止语音"""
        if self._current_voice:
            try:
                self._current_voice.stop()
            except Exception:
                pass
            self._current_voice = None
    
    # ========================================================================
    # Ambient (环境音) 控制
    # ========================================================================
    
    def play_ambient(
        self,
        name: str,
        path: str,
        volume: Optional[float] = None,
        fade_in_ms: int = 0,
        loops: int = -1,
    ) -> None:
        """
        播放环境音
        
        Args:
            name: 环境音名称（用于管理）
            path: 文件路径
            volume: 音量
            fade_in_ms: 淡入时间
            loops: 循环次数
        """
        try:
            # 先停止同名的环境音
            if name in self._ambient_sounds:
                self._ambient_sounds[name].stop()
            
            resolved = self.resolve_path(path)
            snd = pygame.mixer.Sound(resolved)
            
            if volume is not None:
                effective = max(0.0, min(1.0, volume)) * self.master_volume
            else:
                effective = self.get_effective_volume(AudioChannel.AMBIENT)
            
            if fade_in_ms > 0:
                snd.set_volume(0)
                snd.play(loops)
                self._start_fade(
                    AudioChannel.AMBIENT,
                    start_volume=0,
                    end_volume=effective,
                    duration_ms=fade_in_ms,
                    sound=snd,
                )
            else:
                snd.set_volume(effective)
                snd.play(loops)
            
            self._ambient_sounds[name] = snd
        except Exception:
            pass
    
    def stop_ambient(self, name: str, fade_out_ms: int = 0) -> None:
        """停止环境音"""
        if name not in self._ambient_sounds:
            return
        
        snd = self._ambient_sounds[name]
        try:
            if fade_out_ms > 0:
                current_vol = snd.get_volume()
                self._start_fade(
                    AudioChannel.AMBIENT,
                    start_volume=current_vol,
                    end_volume=0,
                    duration_ms=fade_out_ms,
                    sound=snd,
                    callback=lambda: snd.stop(),
                )
            else:
                snd.stop()
        except Exception:
            pass
        
        del self._ambient_sounds[name]
    
    def stop_all_ambient(self, fade_out_ms: int = 0) -> None:
        """停止所有环境音"""
        names = list(self._ambient_sounds.keys())
        for name in names:
            self.stop_ambient(name, fade_out_ms)
    
    # ========================================================================
    # 淡入淡出管理
    # ========================================================================
    
    def _start_fade(
        self,
        channel: AudioChannel,
        start_volume: float,
        end_volume: float,
        duration_ms: int,
        callback: Optional[Callable[[], None]] = None,
        sound: Optional[pygame.mixer.Sound] = None,
    ) -> None:
        """启动淡入淡出任务"""
        task = FadeTask(
            channel=channel,
            start_volume=start_volume,
            end_volume=end_volume,
            duration_ms=max(1, duration_ms),
            start_time=pygame.time.get_ticks(),
            callback=callback,
            sound=sound,
        )
        
        with self._lock:
            # 移除同通道的旧任务
            self._fade_tasks = [t for t in self._fade_tasks 
                              if not (t.channel == channel and t.sound == sound)]
            self._fade_tasks.append(task)
    
    def update(self) -> None:
        """更新淡入淡出效果（应每帧调用）"""
        now = pygame.time.get_ticks()
        completed: List[FadeTask] = []
        
        with self._lock:
            for task in self._fade_tasks:
                elapsed = now - task.start_time
                progress = min(1.0, elapsed / task.duration_ms)
                
                # 计算当前音量
                current = task.start_volume + (task.end_volume - task.start_volume) * progress
                
                # 应用音量
                try:
                    if task.channel == AudioChannel.BGM and task.sound is None:
                        pygame.mixer.music.set_volume(current)
                    elif task.sound:
                        task.sound.set_volume(current)
                except Exception:
                    pass
                
                if progress >= 1.0:
                    completed.append(task)
            
            # 移除完成的任务
            for task in completed:
                self._fade_tasks.remove(task)
        
        # 在锁外调用回调
        for task in completed:
            if task.callback:
                try:
                    task.callback()
                except Exception:
                    pass
    
    def stop_all(self, fade_out_ms: int = 0) -> None:
        """停止所有音频"""
        self.stop_bgm(fade_out_ms)
        self.stop_voice()
        self.stop_all_ambient(fade_out_ms)


# ============================================================================
# 全局单例和兼容函数
# ============================================================================

_audio_manager: Optional[AudioManager] = None


def get_audio_manager() -> Optional[AudioManager]:
    """获取全局音频管理器"""
    return _audio_manager


def init_audio_manager(resolve_path: Callable[[str], str]) -> AudioManager:
    """初始化全局音频管理器"""
    global _audio_manager
    _audio_manager = AudioManager(resolve_path)
    return _audio_manager


# 兼容旧 API
def play_bgm(path: Optional[str], *, volume: float | None, resolve_path) -> None:
    """兼容旧 API - 播放 BGM"""
    try:
        if path:
            resolved = resolve_path(path)
            pygame.mixer.music.load(resolved)
            if volume is not None:
                pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
            pygame.mixer.music.play(-1)
        else:
            try:
                pygame.mixer.music.fadeout(300)
            except Exception:
                pygame.mixer.music.stop()
    except Exception:
        pass


def play_se(path: str, *, volume: float | None, resolve_path) -> None:
    """兼容旧 API - 播放音效"""
    try:
        resolved = resolve_path(path)
        se = pygame.mixer.Sound(resolved)
        if volume is not None:
            se.set_volume(max(0.0, min(1.0, float(volume))))
        se.play()
    except Exception:
        pass


def load_voice(path: str, *, volume: float | None, resolve_path):
    """兼容旧 API - 加载语音"""
    try:
        resolved = resolve_path(path)
        snd = pygame.mixer.Sound(resolved)
        if volume is not None:
            snd.set_volume(max(0.0, min(1.0, float(volume))))
        return snd
    except Exception:
        return None
