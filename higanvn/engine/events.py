"""
Enhanced Event System for HiganVN

Features:
- Typed event definitions with dataclasses
- Priority-based listener ordering
- Event cancellation/propagation control
- One-shot subscriptions
- Async-ready event queue
- Debug logging support
- Weak references to prevent memory leaks
"""
from __future__ import annotations

import logging
import weakref
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, Type, TypeVar, Union
)
from collections import defaultdict
import threading
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Event Priority
# ============================================================================

class Priority(IntEnum):
    """Listener priority - higher values execute first."""
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100
    MONITOR = 200  # Read-only, cannot cancel events


# ============================================================================
# Base Event Classes
# ============================================================================

@dataclass
class Event:
    """Base class for all events."""
    _cancelled: bool = field(default=False, init=False, repr=False)
    _timestamp: float = field(default_factory=time.time, init=False, repr=False)
    
    @property
    def cancelled(self) -> bool:
        return self._cancelled
    
    def cancel(self) -> None:
        """Cancel the event, preventing further propagation to lower-priority listeners."""
        self._cancelled = True
    
    @property
    def timestamp(self) -> float:
        return self._timestamp


@dataclass
class CancellableEvent(Event):
    """Event that can be cancelled to prevent default behavior."""
    pass


# ============================================================================
# Engine Events
# ============================================================================

@dataclass
class EngineLoadEvent(Event):
    """Fired when a program is loaded into the engine."""
    op_count: int = 0


@dataclass
class EngineStepEvent(Event):
    """Fired before/after each engine step."""
    ip: int = 0
    op_kind: str = ""
    phase: str = "before"  # "before" or "after"


@dataclass
class TextShowEvent(CancellableEvent):
    """Fired when text is about to be displayed."""
    speaker: Optional[str] = None
    text: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandEvent(CancellableEvent):
    """Fired when a command is about to be executed."""
    name: str = ""
    args: str = ""
    line: Optional[int] = None


@dataclass
class LabelEnterEvent(Event):
    """Fired when execution enters a label."""
    name: str = ""


@dataclass
class ChoiceShowEvent(Event):
    """Fired when choices are about to be displayed."""
    choices: List[tuple] = field(default_factory=list)  # [(text, target), ...]


@dataclass 
class ChoiceSelectEvent(Event):
    """Fired when user selects a choice."""
    index: int = 0
    text: str = ""
    target: str = ""


# ============================================================================
# Input Events
# ============================================================================

@dataclass
class InputEvent(CancellableEvent):
    """Base class for input events."""
    pass


@dataclass
class KeyDownEvent(InputEvent):
    """Fired when a key is pressed."""
    key: int = 0
    mods: int = 0
    unicode: str = ""


@dataclass
class KeyUpEvent(InputEvent):
    """Fired when a key is released."""
    key: int = 0
    mods: int = 0


@dataclass
class MouseClickEvent(InputEvent):
    """Fired on mouse button press."""
    button: int = 1
    pos: tuple = (0, 0)
    canvas_pos: Optional[tuple] = None  # Transformed to canvas coordinates


@dataclass
class MouseWheelEvent(InputEvent):
    """Fired on mouse wheel scroll."""
    x: int = 0
    y: int = 0  # positive = up, negative = down


@dataclass
class AdvanceRequestEvent(CancellableEvent):
    """Fired when user requests to advance text."""
    source: str = "unknown"  # "keyboard", "mouse", "wheel", "auto"


@dataclass
class MouseMoveEvent(InputEvent):
    """Fired when mouse moves."""
    pos: tuple = (0, 0)
    rel: tuple = (0, 0)  # relative movement
    canvas_pos: Optional[tuple] = None


@dataclass
class MouseButtonUpEvent(InputEvent):
    """Fired on mouse button release."""
    button: int = 1
    pos: tuple = (0, 0)


@dataclass
class ControllerButtonEvent(InputEvent):
    """Fired for controller/gamepad button input."""
    button: int = 0
    pressed: bool = True
    controller_id: int = 0


@dataclass
class ControllerAxisEvent(InputEvent):
    """Fired for controller/gamepad axis input."""
    axis: int = 0
    value: float = 0.0
    controller_id: int = 0


@dataclass
class TouchEvent(InputEvent):
    """Fired for touch screen input."""
    touch_id: int = 0
    pos: tuple = (0, 0)
    touch_type: str = ""  # "down", "up", "move"


# ============================================================================
# UI Events
# ============================================================================

@dataclass
class UIEvent(Event):
    """Base class for UI-related events."""
    pass


@dataclass
class BacklogToggleEvent(UIEvent):
    """Fired when backlog visibility is toggled."""
    visible: bool = False


@dataclass
class UIHiddenEvent(UIEvent):
    """Fired when UI visibility is toggled."""
    hidden: bool = False


@dataclass
class BannerShowEvent(UIEvent):
    """Fired when a banner message is displayed."""
    message: str = ""
    color: tuple = (255, 255, 255)


@dataclass
class MenuOpenEvent(CancellableEvent):
    """Fired when a menu is about to open."""
    menu_type: str = ""  # "save", "load", "settings", "title"


@dataclass
class MenuCloseEvent(UIEvent):
    """Fired when a menu closes."""
    menu_type: str = ""
    result: Any = None


@dataclass
class TitleMenuEvent(UIEvent):
    """Fired for title menu interactions."""
    action: str = ""  # "open", "select", "close"
    selection: str = ""  # "start", "load", "settings", "gallery", "quit"


@dataclass
class GameStartEvent(Event):
    """Fired when game starts (from title menu or load)."""
    from_load: bool = False
    slot: Optional[int] = None


@dataclass
class GameQuitEvent(CancellableEvent):
    """Fired when user tries to quit the game."""
    from_title: bool = False


# ============================================================================
# Save/Load Events
# ============================================================================

@dataclass
class SaveEvent(CancellableEvent):
    """Fired before saving."""
    slot: int = 0
    is_quicksave: bool = False


@dataclass
class SaveCompleteEvent(Event):
    """Fired after successful save."""
    slot: int = 0
    success: bool = True


@dataclass
class LoadEvent(CancellableEvent):
    """Fired before loading."""
    slot: int = 0
    is_quickload: bool = False


@dataclass
class LoadCompleteEvent(Event):
    """Fired after successful load."""
    slot: int = 0
    success: bool = True


# ============================================================================
# Audio Events
# ============================================================================

@dataclass
class AudioEvent(Event):
    """Base class for audio events."""
    pass


@dataclass
class BGMPlayEvent(AudioEvent):
    """Fired when BGM starts playing."""
    path: str = ""
    loop: bool = True
    fade_in: float = 0.0


@dataclass
class BGMStopEvent(AudioEvent):
    """Fired when BGM stops."""
    fade_out: float = 0.0


@dataclass
class SEPlayEvent(AudioEvent):
    """Fired when a sound effect plays."""
    path: str = ""


@dataclass
class VoicePlayEvent(AudioEvent):
    """Fired when voice audio plays."""
    path: str = ""
    speaker: Optional[str] = None


# ============================================================================
# Transition Events  
# ============================================================================

@dataclass
class TransitionStartEvent(Event):
    """Fired when a visual transition starts."""
    transition_type: str = ""
    duration: float = 0.0


@dataclass
class TransitionEndEvent(Event):
    """Fired when a visual transition completes."""
    transition_type: str = ""


# ============================================================================
# Resource Events
# ============================================================================

@dataclass
class ResourceEvent(Event):
    """Base class for resource events."""
    pass


@dataclass
class ResourceLoadEvent(ResourceEvent):
    """Fired when a resource is loaded."""
    resource_type: str = ""  # "bg", "ch", "cg", "bgm", "se", "voice"
    path: str = ""
    from_cache: bool = False
    load_time_ms: float = 0.0


@dataclass
class ResourcePreloadEvent(ResourceEvent):
    """Fired during preloading."""
    total: int = 0
    completed: int = 0
    current_path: str = ""


@dataclass
class CacheEvictEvent(ResourceEvent):
    """Fired when a resource is evicted from cache."""
    path: str = ""
    bytes_freed: int = 0


# ============================================================================
# Debug Events
# ============================================================================

@dataclass
class DebugEvent(Event):
    """Base class for debug events."""
    pass


@dataclass
class DebugToggleEvent(DebugEvent):
    """Fired when debug mode is toggled."""
    enabled: bool = False
    debug_type: str = ""  # "hud", "window"


@dataclass
class ScreenshotEvent(Event):
    """Fired when a screenshot is taken."""
    path: str = ""
    success: bool = True


@dataclass
class FlowMapEvent(Event):
    """Fired for flow map interactions."""
    action: str = ""  # "open", "close", "select"
    selected_label: str = ""


# ============================================================================
# Mode Events
# ============================================================================

@dataclass
class AutoModeEvent(Event):
    """Fired when auto mode is toggled."""
    enabled: bool = False


@dataclass
class FastForwardEvent(Event):
    """Fired when fast forward mode changes."""
    enabled: bool = False
    held: bool = False  # True if held down, False if toggled


# ============================================================================
# Scene/Visual Events
# ============================================================================

@dataclass
class SceneEvent(Event):
    """Base class for scene-related events."""
    pass


@dataclass
class BackgroundChangeEvent(SceneEvent):
    """Fired when background changes."""
    path: Optional[str] = None
    previous_path: Optional[str] = None
    transition: str = ""


@dataclass
class CGShowEvent(SceneEvent):
    """Fired when CG is shown."""
    path: str = ""


@dataclass
class CGHideEvent(SceneEvent):
    """Fired when CG is hidden."""
    pass


@dataclass
class CharacterEvent(Event):
    """Base class for character-related events."""
    actor: str = ""


@dataclass
class CharacterShowEvent(CharacterEvent):
    """Fired when a character appears on screen."""
    pose: str = "base"
    position: Optional[str] = None  # "left", "center", "right"
    first_appearance: bool = False


@dataclass
class CharacterHideEvent(CharacterEvent):
    """Fired when a character is hidden."""
    pass


@dataclass
class CharacterPoseChangeEvent(CharacterEvent):
    """Fired when character pose/expression changes."""
    old_pose: str = ""
    new_pose: str = ""


@dataclass
class CharacterOutfitChangeEvent(CharacterEvent):
    """Fired when character outfit changes."""
    old_outfit: Optional[str] = None
    new_outfit: Optional[str] = None


@dataclass
class CharacterActionEvent(CharacterEvent):
    """Fired when character performs an action animation."""
    action: str = ""


# ============================================================================
# Effect Events
# ============================================================================

@dataclass
class EffectEvent(Event):
    """Base class for visual effects."""
    pass


@dataclass
class ShakeEffectEvent(EffectEvent):
    """Fired when shake effect is triggered."""
    target: str = ""  # actor name or "screen"
    intensity: int = 20
    duration_ms: int = 350
    direction: str = "x"  # "x", "y", "both"


@dataclass
class SlideEffectEvent(EffectEvent):
    """Fired when slide effect is triggered."""
    target: str = ""
    direction: str = ""  # "in_left", "in_right", "out_left", etc.
    duration_ms: int = 360
    distance: int = 120


@dataclass
class FadeEffectEvent(EffectEvent):
    """Fired for fade effects."""
    fade_type: str = ""  # "in", "out"
    duration_ms: int = 500
    color: tuple = (0, 0, 0)


# ============================================================================
# Navigation Events
# ============================================================================

@dataclass
class NavigationEvent(Event):
    """Base class for navigation events."""
    pass


@dataclass
class RewindEvent(NavigationEvent):
    """Fired when player rewinds to previous text."""
    from_ip: int = 0
    to_ip: int = 0
    success: bool = True


@dataclass
class HistoryScrollEvent(NavigationEvent):
    """Fired when scrolling through text history."""
    direction: str = ""  # "up", "down"
    lines: int = 1


@dataclass
class JumpToLabelEvent(CancellableEvent):
    """Fired when jumping to a label."""
    target_label: str = ""
    from_label: str = ""


# ============================================================================
# Typewriter Events
# ============================================================================

@dataclass
class TypewriterEvent(Event):
    """Base class for typewriter-related events."""
    pass


@dataclass
class TypewriterStartEvent(TypewriterEvent):
    """Fired when typewriter animation starts."""
    text: str = ""
    total_chars: int = 0


@dataclass
class TypewriterProgressEvent(TypewriterEvent):
    """Fired as typewriter progresses."""
    revealed_chars: int = 0
    total_chars: int = 0
    percent: float = 0.0


@dataclass
class TypewriterCompleteEvent(TypewriterEvent):
    """Fired when typewriter animation completes."""
    text: str = ""
    was_skipped: bool = False


@dataclass
class TypewriterSkipEvent(TypewriterEvent):
    """Fired when player skips typewriter animation."""
    pass


# ============================================================================
# Gallery Events
# ============================================================================

@dataclass
class GalleryEvent(Event):
    """Base class for gallery events."""
    pass


@dataclass
class GalleryOpenEvent(GalleryEvent):
    """Fired when gallery is opened."""
    pass


@dataclass
class GalleryCloseEvent(GalleryEvent):
    """Fired when gallery is closed."""
    pass


@dataclass
class GalleryUnlockEvent(GalleryEvent):
    """Fired when a new CG is unlocked."""
    cg_id: str = ""
    cg_path: str = ""


# ============================================================================
# Settings Events
# ============================================================================

@dataclass
class SettingsEvent(Event):
    """Base class for settings events."""
    pass


@dataclass
class SettingsOpenEvent(SettingsEvent):
    """Fired when settings menu opens."""
    pass


@dataclass
class SettingsCloseEvent(SettingsEvent):
    """Fired when settings menu closes."""
    pass


@dataclass
class SettingsChangeEvent(SettingsEvent):
    """Fired when a setting value changes."""
    setting_name: str = ""
    old_value: Any = None
    new_value: Any = None


@dataclass
class VolumeChangeEvent(SettingsEvent):
    """Fired when volume setting changes."""
    channel: str = ""  # "master", "bgm", "se", "voice"
    old_value: float = 1.0
    new_value: float = 1.0


@dataclass
class TypewriterSpeedChangeEvent(SettingsEvent):
    """Fired when typewriter speed changes."""
    old_speed: float = 1.0
    new_speed: float = 1.0


# ============================================================================
# Window Events
# ============================================================================

@dataclass
class WindowEvent(Event):
    """Base class for window events."""
    pass


@dataclass
class WindowResizeEvent(WindowEvent):
    """Fired when window is resized."""
    old_size: tuple = (0, 0)
    new_size: tuple = (0, 0)


@dataclass
class WindowFocusEvent(WindowEvent):
    """Fired when window gains or loses focus."""
    focused: bool = True


@dataclass
class FullscreenToggleEvent(WindowEvent):
    """Fired when fullscreen mode is toggled."""
    fullscreen: bool = False


# ============================================================================
# Error Events
# ============================================================================

@dataclass
class ErrorEvent(Event):
    """Fired when an error occurs."""
    error_type: str = ""
    message: str = ""
    recoverable: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WarningEvent(Event):
    """Fired for non-critical warnings."""
    warning_type: str = ""
    message: str = ""


# ============================================================================
# Script/Flow Control Events
# ============================================================================

@dataclass
class ScriptEvent(Event):
    """Base class for script-related events."""
    pass


@dataclass
class ScriptLoadEvent(ScriptEvent):
    """Fired when a script file is loaded."""
    path: str = ""
    op_count: int = 0


@dataclass
class ScriptExecEvent(ScriptEvent):
    """Fired when SCRIPT command executes Python code."""
    code: str = ""
    result: Any = None


@dataclass
class VariableChangeEvent(ScriptEvent):
    """Fired when a script variable changes."""
    name: str = ""
    old_value: Any = None
    new_value: Any = None
    source: str = ""  # "SET", "SCRIPT", "CHOICE", etc.


@dataclass
class WaitEvent(ScriptEvent):
    """Fired when WAIT command pauses execution."""
    duration_ms: int = 0


@dataclass
class ConditionalEvent(ScriptEvent):
    """Fired for IF/ELSEIF/ELSE/SWITCH conditional execution."""
    condition_type: str = ""  # "IF", "ELSEIF", "ELSE", "SWITCH", "CASE"
    expression: str = ""
    result: bool = False


@dataclass
class GotoEvent(ScriptEvent):
    """Fired when GOTO command jumps to a label."""
    target_label: str = ""
    from_ip: int = 0


# ============================================================================
# Choice System Events
# ============================================================================

@dataclass
class ChoiceEvent(Event):
    """Base class for choice-related events."""
    pass


@dataclass
class ChoicePresentEvent(ChoiceEvent):
    """Fired before choices are presented to user."""
    choices: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)


@dataclass
class ChoiceHoverEvent(ChoiceEvent):
    """Fired when hovering over a choice option."""
    index: int = 0
    text: str = ""


@dataclass
class ChoiceTimeoutEvent(CancellableEvent):
    """Fired if choice times out (for timed choices)."""
    default_index: int = 0


# ============================================================================
# Slot/Save UI Events
# ============================================================================

@dataclass
class SlotUIEvent(UIEvent):
    """Base class for slot UI events."""
    pass


@dataclass
class SlotSelectEvent(SlotUIEvent):
    """Fired when a save slot is selected."""
    slot_id: int = 0
    mode: str = ""  # "save", "load"
    has_data: bool = False


@dataclass
class SlotHoverEvent(SlotUIEvent):
    """Fired when hovering over a save slot."""
    slot_id: int = 0
    has_data: bool = False


@dataclass
class SlotDeleteEvent(CancellableEvent):
    """Fired when a slot is about to be deleted."""
    slot_id: int = 0


@dataclass
class SlotDeleteCompleteEvent(Event):
    """Fired after a slot is deleted."""
    slot_id: int = 0
    success: bool = True


@dataclass
class SlotPageChangeEvent(SlotUIEvent):
    """Fired when changing pages in slot UI."""
    old_page: int = 0
    new_page: int = 1


# ============================================================================
# Animation Events
# ============================================================================

@dataclass
class AnimationEvent(Event):
    """Base class for animation events."""
    pass


@dataclass
class AnimationStartEvent(AnimationEvent):
    """Fired when an animation starts."""
    target: str = ""
    animation_type: str = ""
    duration_ms: int = 0


@dataclass
class AnimationEndEvent(AnimationEvent):
    """Fired when an animation completes."""
    target: str = ""
    animation_type: str = ""
    completed: bool = True  # False if interrupted


@dataclass
class AnimationCancelEvent(AnimationEvent):
    """Fired when an animation is cancelled."""
    target: str = ""
    animation_type: str = ""


# ============================================================================
# Voice/Lip Sync Events
# ============================================================================

@dataclass
class VoiceEvent(AudioEvent):
    """Base class for voice-specific events."""
    pass


@dataclass
class VoiceStartEvent(VoiceEvent):
    """Fired when voice audio starts playing."""
    path: str = ""
    speaker: Optional[str] = None
    duration_ms: int = 0


@dataclass
class VoiceEndEvent(VoiceEvent):
    """Fired when voice audio finishes."""
    path: str = ""
    was_stopped: bool = False  # True if manually stopped


@dataclass
class VoiceVolumeChangeEvent(VoiceEvent):
    """Fired when voice volume changes."""
    old_volume: float = 1.0
    new_volume: float = 1.0


# ============================================================================
# Text Panel Events
# ============================================================================

@dataclass
class TextPanelEvent(UIEvent):
    """Base class for text panel events."""
    pass


@dataclass
class TextPanelShowEvent(TextPanelEvent):
    """Fired when text panel becomes visible."""
    pass


@dataclass
class TextPanelHideEvent(TextPanelEvent):
    """Fired when text panel is hidden."""
    pass


@dataclass
class TextClearEvent(TextPanelEvent):
    """Fired when text is cleared."""
    pass


@dataclass
class SpeakerChangeEvent(TextPanelEvent):
    """Fired when the speaking character changes."""
    old_speaker: Optional[str] = None
    new_speaker: Optional[str] = None


# ============================================================================
# Quick Save/Load Events
# ============================================================================

@dataclass
class QuickSaveEvent(CancellableEvent):
    """Fired when quick save is triggered."""
    pass


@dataclass
class QuickSaveCompleteEvent(Event):
    """Fired after quick save completes."""
    success: bool = True
    path: str = ""


@dataclass
class QuickLoadEvent(CancellableEvent):
    """Fired when quick load is triggered."""
    pass


@dataclass
class QuickLoadCompleteEvent(Event):
    """Fired after quick load completes."""
    success: bool = True
    path: str = ""


# ============================================================================
# Skip Mode Events
# ============================================================================

@dataclass
class SkipModeEvent(Event):
    """Base class for skip mode events."""
    pass


@dataclass
class SkipModeEnterEvent(SkipModeEvent):
    """Fired when skip mode is entered."""
    skip_type: str = ""  # "all", "read", "held"


@dataclass
class SkipModeExitEvent(SkipModeEvent):
    """Fired when skip mode is exited."""
    reason: str = ""  # "user", "choice", "unread"


# ============================================================================
# Backlog/History Events
# ============================================================================

@dataclass
class BacklogEvent(Event):
    """Base class for backlog events."""
    pass


@dataclass
class BacklogEntryAddEvent(BacklogEvent):
    """Fired when a new entry is added to backlog."""
    speaker: Optional[str] = None
    text: str = ""
    entry_index: int = 0


@dataclass
class BacklogJumpEvent(CancellableEvent):
    """Fired when user tries to jump from backlog."""
    target_index: int = 0


@dataclass
class BacklogVoiceReplayEvent(BacklogEvent):
    """Fired when replaying voice from backlog."""
    entry_index: int = 0
    voice_path: str = ""


# ============================================================================
# System Events
# ============================================================================

@dataclass
class SystemEvent(Event):
    """Base class for system events."""
    pass


@dataclass
class LanguageChangeEvent(SystemEvent):
    """Fired when language setting changes."""
    old_language: str = ""
    new_language: str = ""


@dataclass
class FontSizeChangeEvent(SystemEvent):
    """Fired when font size changes."""
    old_size: int = 24
    new_size: int = 24


@dataclass
class DisplayModeChangeEvent(SystemEvent):
    """Fired when display mode changes."""
    old_mode: str = ""  # "windowed", "fullscreen", "borderless"
    new_mode: str = ""


@dataclass
class VSyncChangeEvent(SystemEvent):
    """Fired when vsync setting changes."""
    enabled: bool = False


@dataclass
class FrameRateEvent(SystemEvent):
    """Fired for frame rate monitoring."""
    current_fps: float = 0.0
    avg_fps: float = 0.0


# ============================================================================
# Accessibility Events
# ============================================================================

@dataclass
class AccessibilityEvent(Event):
    """Base class for accessibility events."""
    pass


@dataclass
class TextToSpeechEvent(AccessibilityEvent):
    """Fired when text-to-speech reads text."""
    text: str = ""
    speaker: Optional[str] = None


@dataclass
class HighContrastModeEvent(AccessibilityEvent):
    """Fired when high contrast mode changes."""
    enabled: bool = False


@dataclass
class LargeTextModeEvent(AccessibilityEvent):
    """Fired when large text mode changes."""
    enabled: bool = False
    scale: float = 1.0


# ============================================================================
# Game State Events
# ============================================================================

@dataclass
class GameStateEvent(Event):
    """Base class for game state events."""
    pass


@dataclass
class GamePauseEvent(GameStateEvent):
    """Fired when game is paused."""
    reason: str = ""  # "menu", "focus_lost", "manual"


@dataclass
class GameResumeEvent(GameStateEvent):
    """Fired when game is resumed from pause."""
    pass


@dataclass
class SceneTransitionEvent(GameStateEvent):
    """Fired when transitioning between scenes/chapters."""
    from_scene: str = ""
    to_scene: str = ""
    transition_type: str = ""


@dataclass
class ChapterStartEvent(GameStateEvent):
    """Fired when a new chapter begins."""
    chapter_id: str = ""
    chapter_name: str = ""


@dataclass
class ChapterEndEvent(GameStateEvent):
    """Fired when a chapter ends."""
    chapter_id: str = ""


@dataclass
class EndingReachEvent(GameStateEvent):
    """Fired when an ending is reached."""
    ending_id: str = ""
    ending_name: str = ""
    ending_type: str = ""  # "good", "bad", "neutral", "true"


@dataclass
class NewGamePlusEvent(GameStateEvent):
    """Fired when starting new game plus."""
    clear_count: int = 0
    unlocked_features: List[str] = field(default_factory=list)


# ============================================================================
# Plugin/Extension Events
# ============================================================================

@dataclass
class PluginEvent(Event):
    """Base class for plugin-related events."""
    pass


@dataclass
class PluginLoadEvent(PluginEvent):
    """Fired when a plugin is loaded."""
    plugin_id: str = ""
    plugin_name: str = ""
    version: str = ""


@dataclass
class PluginUnloadEvent(PluginEvent):
    """Fired when a plugin is unloaded."""
    plugin_id: str = ""


@dataclass
class PluginErrorEvent(PluginEvent):
    """Fired when a plugin encounters an error."""
    plugin_id: str = ""
    error: str = ""


@dataclass
class CustomCommandEvent(CancellableEvent):
    """Fired for custom/plugin-defined commands."""
    command_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Telemetry/Analytics Events (for optional analytics)
# ============================================================================

@dataclass
class TelemetryEvent(Event):
    """Base class for telemetry events."""
    pass


@dataclass
class SessionStartEvent(TelemetryEvent):
    """Fired when a game session starts."""
    session_id: str = ""


@dataclass
class SessionEndEvent(TelemetryEvent):
    """Fired when a game session ends."""
    session_id: str = ""
    play_time_seconds: float = 0.0


@dataclass
class MilestoneEvent(TelemetryEvent):
    """Fired when player reaches a milestone."""
    milestone_id: str = ""
    milestone_type: str = ""


# ============================================================================
# Hotkey Events
# ============================================================================

@dataclass
class HotkeyEvent(Event):
    """Base class for hotkey events."""
    pass


@dataclass
class HotkeyTriggerEvent(HotkeyEvent):
    """Fired when a hotkey combination is triggered."""
    action: str = ""  # "quicksave", "quickload", "screenshot", etc.
    key_combination: str = ""  # e.g., "Ctrl+S"


@dataclass
class HotkeyRegisterEvent(HotkeyEvent):
    """Fired when a new hotkey is registered."""
    action: str = ""
    key_combination: str = ""


# ============================================================================
# Localization Events
# ============================================================================

@dataclass
class LocalizationEvent(Event):
    """Base class for localization events."""
    pass


@dataclass
class LocaleLoadEvent(LocalizationEvent):
    """Fired when a locale is loaded."""
    locale_id: str = ""
    strings_count: int = 0


@dataclass
class MissingTranslationEvent(LocalizationEvent):
    """Fired when a translation is missing."""
    key: str = ""
    locale_id: str = ""


# ============================================================================
# Listener Registration
# ============================================================================

T = TypeVar('T', bound=Event)

@dataclass
class Listener(Generic[T]):
    """Wrapper for event listener with metadata."""
    callback: Callable[[T], None]
    priority: Priority = Priority.NORMAL
    once: bool = False
    weak: bool = False
    _ref: Optional[weakref.ref] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        if self.weak and hasattr(self.callback, '__self__'):
            # Create weak reference for bound methods
            obj = self.callback.__self__
            method_name = self.callback.__name__
            self._ref = weakref.ref(obj)
            self._method_name = method_name
    
    def invoke(self, event: T) -> bool:
        """Invoke the callback. Returns False if listener is dead (weak ref expired)."""
        if self.weak and self._ref is not None:
            obj = self._ref()
            if obj is None:
                return False
            method = getattr(obj, self._method_name, None)
            if method:
                method(event)
        else:
            self.callback(event)
        return True


# ============================================================================
# Event Bus
# ============================================================================

class EventSystem:
    """
    Enhanced event system with typed events, priorities, and cancellation.
    
    Usage:
        events = EventSystem()
        
        # Subscribe to typed events
        @events.on(TextShowEvent)
        def on_text(event: TextShowEvent):
            print(f"{event.speaker}: {event.text}")
        
        # Subscribe with priority
        events.subscribe(TextShowEvent, handler, priority=Priority.HIGH)
        
        # One-shot subscription
        events.once(LoadCompleteEvent, on_load_done)
        
        # Emit events
        events.emit(TextShowEvent(speaker="Alice", text="Hello!"))
        
        # Check if cancelled
        event = CommandEvent(name="BGM", args="music.mp3")
        events.emit(event)
        if not event.cancelled:
            # Execute default behavior
            pass
    """
    
    def __init__(self, debug: bool = False):
        self._listeners: Dict[Type[Event], List[Listener]] = defaultdict(list)
        self._lock = threading.RLock()
        self._debug = debug
        self._queue: Queue[Event] = Queue()
        self._processing = False
        
        # Statistics
        self._emit_count: Dict[Type[Event], int] = defaultdict(int)
        self._total_emits = 0
    
    def subscribe(
        self,
        event_type: Type[T],
        callback: Callable[[T], None],
        priority: Priority = Priority.NORMAL,
        once: bool = False,
        weak: bool = False
    ) -> Callable[[], None]:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event class to listen for
            callback: Function to call when event fires
            priority: Listener priority (higher = called first)
            once: If True, automatically unsubscribe after first call
            weak: If True, use weak reference (auto-cleanup when object is GC'd)
        
        Returns:
            Unsubscribe function
        """
        listener = Listener(
            callback=callback,
            priority=priority,
            once=once,
            weak=weak
        )
        
        with self._lock:
            listeners = self._listeners[event_type]
            listeners.append(listener)
            # Sort by priority (highest first)
            listeners.sort(key=lambda l: l.priority, reverse=True)
        
        if self._debug:
            logger.debug(f"Subscribed to {event_type.__name__} with priority {priority.name}")
        
        # Return unsubscribe function
        def unsubscribe():
            self.unsubscribe(event_type, callback)
        return unsubscribe
    
    def unsubscribe(self, event_type: Type[T], callback: Callable[[T], None]) -> bool:
        """Remove a listener. Returns True if found and removed."""
        with self._lock:
            listeners = self._listeners.get(event_type, [])
            for i, listener in enumerate(listeners):
                if listener.callback == callback:
                    listeners.pop(i)
                    if self._debug:
                        logger.debug(f"Unsubscribed from {event_type.__name__}")
                    return True
        return False
    
    def on(
        self, 
        event_type: Type[T], 
        priority: Priority = Priority.NORMAL
    ) -> Callable[[Callable[[T], None]], Callable[[T], None]]:
        """Decorator for subscribing to events."""
        def decorator(fn: Callable[[T], None]) -> Callable[[T], None]:
            self.subscribe(event_type, fn, priority=priority)
            return fn
        return decorator
    
    def once(
        self,
        event_type: Type[T],
        callback: Callable[[T], None],
        priority: Priority = Priority.NORMAL
    ) -> Callable[[], None]:
        """Subscribe to an event for a single invocation only."""
        return self.subscribe(event_type, callback, priority=priority, once=True)
    
    def emit(self, event: Event) -> Event:
        """
        Emit an event to all listeners.
        
        Returns the event (useful for checking if cancelled).
        """
        event_type = type(event)
        
        self._total_emits += 1
        self._emit_count[event_type] += 1
        
        if self._debug:
            logger.debug(f"Emitting {event_type.__name__}: {event}")
        
        with self._lock:
            listeners = list(self._listeners.get(event_type, []))
        
        to_remove: List[Listener] = []
        
        for listener in listeners:
            # Skip if cancelled (unless MONITOR priority)
            if event.cancelled and listener.priority != Priority.MONITOR:
                continue
            
            try:
                alive = listener.invoke(event)
                if not alive:
                    to_remove.append(listener)
                elif listener.once:
                    to_remove.append(listener)
            except Exception as e:
                logger.error(f"Error in listener for {event_type.__name__}: {e}", exc_info=True)
                if self._debug:
                    raise  # Re-raise in debug mode
        
        # Cleanup dead/once listeners
        if to_remove:
            with self._lock:
                for listener in to_remove:
                    try:
                        self._listeners[event_type].remove(listener)
                    except ValueError:
                        pass
        
        return event
    
    def emit_async(self, event: Event) -> None:
        """Queue an event for deferred processing."""
        self._queue.put(event)
    
    def process_queue(self, max_events: int = 100) -> int:
        """Process queued events. Returns number of events processed."""
        if self._processing:
            return 0
        
        self._processing = True
        count = 0
        
        try:
            while count < max_events:
                try:
                    event = self._queue.get_nowait()
                    self.emit(event)
                    count += 1
                except Empty:
                    break
        finally:
            self._processing = False
        
        return count
    
    def clear(self, event_type: Optional[Type[Event]] = None) -> None:
        """Clear all listeners, or listeners for a specific event type."""
        with self._lock:
            if event_type:
                self._listeners[event_type].clear()
            else:
                self._listeners.clear()
    
    def listener_count(self, event_type: Optional[Type[Event]] = None) -> int:
        """Get number of listeners for an event type, or total listeners."""
        with self._lock:
            if event_type:
                return len(self._listeners.get(event_type, []))
            return sum(len(l) for l in self._listeners.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event system statistics."""
        return {
            "total_emits": self._total_emits,
            "emit_counts": {
                k.__name__: v for k, v in self._emit_count.items()
            },
            "listener_counts": {
                k.__name__: len(v) for k, v in self._listeners.items() if v
            },
            "queue_size": self._queue.qsize()
        }


# ============================================================================
# Global Instance (optional convenience)
# ============================================================================

_global_events: Optional[EventSystem] = None

def get_event_system() -> EventSystem:
    """Get or create the global event system instance."""
    global _global_events
    if _global_events is None:
        _global_events = EventSystem()
    return _global_events

def reset_event_system() -> None:
    """Reset the global event system (mainly for testing)."""
    global _global_events
    if _global_events:
        _global_events.clear()
    _global_events = None


# ============================================================================
# Compatibility Layer - Maps old string-based events to new typed events
# ============================================================================

class LegacyEventBridge:
    """
    Bridge between old string-based EventBus and new typed EventSystem.
    
    Provides backward compatibility while allowing gradual migration.
    """
    
    # Mapping from old event names to new event types
    EVENT_MAP = {
        "engine.load": EngineLoadEvent,
        "engine.before_op": EngineStepEvent,
        "engine.after_op": EngineStepEvent,
        "text.show": TextShowEvent,
        "command": CommandEvent,
        "label.enter": LabelEnterEvent,
        "choice.select": ChoiceSelectEvent,
    }
    
    def __init__(self, new_system: EventSystem):
        self._new = new_system
        self._old_listeners: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        """Legacy subscribe - wraps old-style dict callbacks."""
        if fn not in self._old_listeners[name]:
            self._old_listeners[name].append(fn)
            
            # If we have a typed event for this, also subscribe there
            event_type = self.EVENT_MAP.get(name)
            if event_type:
                def wrapper(event):
                    # Convert typed event back to dict for old listeners
                    data = {k: v for k, v in event.__dict__.items() 
                            if not k.startswith('_')}
                    fn(data)
                self._new.subscribe(event_type, wrapper)
    
    def unsubscribe(self, name: str, fn: Callable[[Dict[str, Any]], None]) -> None:
        """Legacy unsubscribe."""
        try:
            self._old_listeners[name].remove(fn)
        except ValueError:
            pass
    
    def emit(self, name: str, /, **data: Any) -> None:
        """Legacy emit - converts to typed event if possible."""
        event_type = self.EVENT_MAP.get(name)
        
        if event_type:
            # Build typed event from kwargs
            try:
                # Map old field names to new ones
                if name == "engine.before_op":
                    data["phase"] = "before"
                    data["op_kind"] = data.pop("kind", "")
                elif name == "engine.after_op":
                    data["phase"] = "after"
                elif name == "text.show":
                    data["speaker"] = data.pop("who", None)
                
                event = event_type(**{
                    k: v for k, v in data.items()
                    if k in event_type.__dataclass_fields__
                })
                self._new.emit(event)
            except Exception as e:
                logger.warning(f"Failed to create typed event for {name}: {e}")
                # Fall through to legacy handling
        
        # Also call old-style listeners directly
        for fn in list(self._old_listeners.get(name, [])):
            try:
                fn(dict(data))
            except Exception:
                continue
