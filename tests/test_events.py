"""Tests for the new event system."""
import pytest
from higanvn.engine.events import (
    EventSystem, Priority, Event, CancellableEvent,
    TextShowEvent, CommandEvent, EngineLoadEvent, EngineStepEvent,
    LabelEnterEvent, ChoiceSelectEvent, SaveEvent, LoadEvent,
    KeyDownEvent, AdvanceRequestEvent, LegacyEventBridge,
    TitleMenuEvent, GameStartEvent, GameQuitEvent
)


class TestEventSystem:
    """Test the typed event system."""
    
    def test_basic_subscribe_emit(self):
        """Test basic subscribe and emit."""
        events = EventSystem()
        received = []
        
        def handler(event: TextShowEvent):
            received.append(event)
        
        events.subscribe(TextShowEvent, handler)
        events.emit(TextShowEvent(speaker="Alice", text="Hello"))
        
        assert len(received) == 1
        assert received[0].speaker == "Alice"
        assert received[0].text == "Hello"
    
    def test_unsubscribe(self):
        """Test unsubscribe removes listener."""
        events = EventSystem()
        received = []
        
        def handler(event: TextShowEvent):
            received.append(event)
        
        events.subscribe(TextShowEvent, handler)
        events.emit(TextShowEvent(speaker="A", text="1"))
        
        events.unsubscribe(TextShowEvent, handler)
        events.emit(TextShowEvent(speaker="B", text="2"))
        
        assert len(received) == 1
        assert received[0].speaker == "A"
    
    def test_unsubscribe_via_returned_function(self):
        """Test the returned unsubscribe function works."""
        events = EventSystem()
        received = []
        
        def handler(event: TextShowEvent):
            received.append(event)
        
        unsub = events.subscribe(TextShowEvent, handler)
        events.emit(TextShowEvent(speaker="A", text="1"))
        
        unsub()
        events.emit(TextShowEvent(speaker="B", text="2"))
        
        assert len(received) == 1
    
    def test_priority_ordering(self):
        """Test that higher priority listeners are called first."""
        events = EventSystem()
        order = []
        
        def low_handler(event: TextShowEvent):
            order.append("low")
        
        def normal_handler(event: TextShowEvent):
            order.append("normal")
        
        def high_handler(event: TextShowEvent):
            order.append("high")
        
        events.subscribe(TextShowEvent, low_handler, priority=Priority.LOW)
        events.subscribe(TextShowEvent, normal_handler, priority=Priority.NORMAL)
        events.subscribe(TextShowEvent, high_handler, priority=Priority.HIGH)
        
        events.emit(TextShowEvent(speaker="X", text="Y"))
        
        assert order == ["high", "normal", "low"]
    
    def test_event_cancellation(self):
        """Test that cancellation stops propagation."""
        events = EventSystem()
        order = []
        
        def cancelling_handler(event: TextShowEvent):
            order.append("canceller")
            event.cancel()
        
        def low_handler(event: TextShowEvent):
            order.append("low")
        
        events.subscribe(TextShowEvent, cancelling_handler, priority=Priority.HIGH)
        events.subscribe(TextShowEvent, low_handler, priority=Priority.LOW)
        
        event = events.emit(TextShowEvent(speaker="X", text="Y"))
        
        assert order == ["canceller"]
        assert event.cancelled
    
    def test_monitor_priority_sees_cancelled(self):
        """Test that MONITOR priority still runs even after cancellation."""
        events = EventSystem()
        order = []
        
        def canceller(event: TextShowEvent):
            order.append("canceller")
            event.cancel()
        
        def low_handler(event: TextShowEvent):
            order.append("low")
        
        def monitor(event: TextShowEvent):
            order.append(f"monitor-cancelled={event.cancelled}")
        
        # MONITOR has highest priority value (200), so it runs first
        # But it's meant for observation only, so cancellation still affects lower priorities
        events.subscribe(TextShowEvent, canceller, priority=Priority.HIGH)
        events.subscribe(TextShowEvent, low_handler, priority=Priority.LOW)
        events.subscribe(TextShowEvent, monitor, priority=Priority.MONITOR)
        
        events.emit(TextShowEvent(speaker="X", text="Y"))
        
        # MONITOR runs first (highest priority), then canceller, then low is skipped
        assert "monitor-cancelled=False" in order  # Saw event before cancellation
        assert "canceller" in order
        assert "low" not in order  # Low was skipped due to cancellation
    
    def test_once_subscription(self):
        """Test that once subscriptions auto-unsubscribe."""
        events = EventSystem()
        received = []
        
        def handler(event: TextShowEvent):
            received.append(event.text)
        
        events.once(TextShowEvent, handler)
        
        events.emit(TextShowEvent(speaker="A", text="1"))
        events.emit(TextShowEvent(speaker="A", text="2"))
        events.emit(TextShowEvent(speaker="A", text="3"))
        
        assert received == ["1"]
    
    def test_decorator_syntax(self):
        """Test the @events.on decorator."""
        events = EventSystem()
        received = []
        
        @events.on(TextShowEvent, priority=Priority.HIGH)
        def handler(event: TextShowEvent):
            received.append(event.text)
        
        events.emit(TextShowEvent(speaker="A", text="decorated"))
        
        assert received == ["decorated"]
    
    def test_multiple_event_types(self):
        """Test handling different event types."""
        events = EventSystem()
        text_events = []
        command_events = []
        
        def text_handler(event: TextShowEvent):
            text_events.append(event.text)
        
        def command_handler(event: CommandEvent):
            command_events.append(event.name)
        
        events.subscribe(TextShowEvent, text_handler)
        events.subscribe(CommandEvent, command_handler)
        
        events.emit(TextShowEvent(speaker="A", text="hello"))
        events.emit(CommandEvent(name="BGM", args="music.mp3"))
        events.emit(TextShowEvent(speaker="B", text="world"))
        
        assert text_events == ["hello", "world"]
        assert command_events == ["BGM"]
    
    def test_event_timestamp(self):
        """Test that events have timestamps."""
        event = TextShowEvent(speaker="A", text="B")
        assert event.timestamp > 0
    
    def test_statistics(self):
        """Test event statistics tracking."""
        events = EventSystem()
        
        def dummy(event): pass
        events.subscribe(TextShowEvent, dummy)
        
        events.emit(TextShowEvent(speaker="A", text="1"))
        events.emit(TextShowEvent(speaker="A", text="2"))
        events.emit(CommandEvent(name="X", args="Y"))
        
        stats = events.get_stats()
        assert stats["total_emits"] == 3
        assert stats["emit_counts"]["TextShowEvent"] == 2
        assert stats["emit_counts"]["CommandEvent"] == 1
    
    def test_listener_count(self):
        """Test listener count methods."""
        events = EventSystem()
        
        def h1(e): pass
        def h2(e): pass
        def h3(e): pass
        
        events.subscribe(TextShowEvent, h1)
        events.subscribe(TextShowEvent, h2)
        events.subscribe(CommandEvent, h3)
        
        assert events.listener_count(TextShowEvent) == 2
        assert events.listener_count(CommandEvent) == 1
        assert events.listener_count() == 3
    
    def test_clear_specific_type(self):
        """Test clearing listeners for a specific event type."""
        events = EventSystem()
        
        def h1(e): pass
        def h2(e): pass
        
        events.subscribe(TextShowEvent, h1)
        events.subscribe(CommandEvent, h2)
        
        events.clear(TextShowEvent)
        
        assert events.listener_count(TextShowEvent) == 0
        assert events.listener_count(CommandEvent) == 1
    
    def test_clear_all(self):
        """Test clearing all listeners."""
        events = EventSystem()
        
        def h1(e): pass
        def h2(e): pass
        
        events.subscribe(TextShowEvent, h1)
        events.subscribe(CommandEvent, h2)
        
        events.clear()
        
        assert events.listener_count() == 0
    
    def test_exception_handling(self):
        """Test that exceptions in handlers don't crash the system."""
        events = EventSystem()
        received = []
        
        def bad_handler(event: TextShowEvent):
            raise ValueError("oops")
        
        def good_handler(event: TextShowEvent):
            received.append(event.text)
        
        events.subscribe(TextShowEvent, bad_handler, priority=Priority.HIGH)
        events.subscribe(TextShowEvent, good_handler, priority=Priority.LOW)
        
        # Should not raise
        events.emit(TextShowEvent(speaker="A", text="test"))
        
        # Good handler should still have been called
        assert received == ["test"]


class TestLegacyEventBridge:
    """Test backward compatibility with old string-based events."""
    
    def test_legacy_subscribe_emit(self):
        """Test old-style subscribe and emit."""
        new_system = EventSystem()
        bridge = LegacyEventBridge(new_system)
        
        received = []
        
        def handler(data):
            received.append(data)
        
        bridge.subscribe("custom.event", handler)
        bridge.emit("custom.event", foo="bar", num=42)
        
        assert len(received) == 1
        assert received[0]["foo"] == "bar"
        assert received[0]["num"] == 42
    
    def test_legacy_unsubscribe(self):
        """Test old-style unsubscribe."""
        new_system = EventSystem()
        bridge = LegacyEventBridge(new_system)
        
        received = []
        
        def handler(data):
            received.append(data)
        
        bridge.subscribe("test", handler)
        bridge.emit("test", x=1)
        
        bridge.unsubscribe("test", handler)
        bridge.emit("test", x=2)
        
        assert len(received) == 1
    
    def test_bridge_converts_known_events(self):
        """Test that known events are converted to typed events."""
        new_system = EventSystem()
        bridge = LegacyEventBridge(new_system)
        
        typed_received = []
        
        def typed_handler(event: TextShowEvent):
            typed_received.append(event)
        
        new_system.subscribe(TextShowEvent, typed_handler)
        
        # Emit through legacy bridge with old field names
        bridge.emit("text.show", who="Alice", text="Hello")
        
        # Should have been converted
        assert len(typed_received) == 1
        assert typed_received[0].speaker == "Alice"
        assert typed_received[0].text == "Hello"


class TestSpecificEvents:
    """Test specific event types."""
    
    def test_engine_load_event(self):
        """Test EngineLoadEvent."""
        event = EngineLoadEvent(op_count=100)
        assert event.op_count == 100
        assert not event.cancelled
    
    def test_engine_step_event(self):
        """Test EngineStepEvent."""
        event = EngineStepEvent(ip=42, op_kind="dialogue", phase="before")
        assert event.ip == 42
        assert event.op_kind == "dialogue"
        assert event.phase == "before"
    
    def test_text_show_event_cancellable(self):
        """Test that TextShowEvent can be cancelled."""
        event = TextShowEvent(speaker="A", text="B")
        assert not event.cancelled
        event.cancel()
        assert event.cancelled
    
    def test_command_event_with_line(self):
        """Test CommandEvent with line number."""
        event = CommandEvent(name="BGM", args="music.mp3", line=42)
        assert event.name == "BGM"
        assert event.args == "music.mp3"
        assert event.line == 42
    
    def test_save_load_events(self):
        """Test SaveEvent and LoadEvent."""
        save = SaveEvent(slot=5, is_quicksave=False)
        assert save.slot == 5
        assert not save.is_quicksave
        
        load = LoadEvent(slot=3, is_quickload=True)
        assert load.slot == 3
        assert load.is_quickload
    
    def test_key_down_event(self):
        """Test KeyDownEvent."""
        event = KeyDownEvent(key=13, mods=1, unicode="\r")
        assert event.key == 13
        assert event.mods == 1
        assert event.unicode == "\r"
    
    def test_advance_request_event(self):
        """Test AdvanceRequestEvent."""
        event = AdvanceRequestEvent(source="keyboard")
        assert event.source == "keyboard"
        assert not event.cancelled
        event.cancel()
        assert event.cancelled

    def test_title_menu_event(self):
        """Test TitleMenuEvent for title menu interactions."""
        event = TitleMenuEvent(action="open")
        assert event.action == "open"
        assert event.selection == ""
        
        event2 = TitleMenuEvent(action="select", selection="start")
        assert event2.action == "select"
        assert event2.selection == "start"
        
        event3 = TitleMenuEvent(action="close")
        assert event3.action == "close"
    
    def test_game_start_event(self):
        """Test GameStartEvent for game start."""
        event = GameStartEvent(from_load=False)
        assert not event.from_load
        assert event.slot is None
        
        event2 = GameStartEvent(from_load=True, slot=3)
        assert event2.from_load
        assert event2.slot == 3
    
    def test_game_quit_event(self):
        """Test GameQuitEvent is cancellable."""
        event = GameQuitEvent(from_title=True)
        assert event.from_title
        assert not event.cancelled
        
        event.cancel()
        assert event.cancelled


class TestSceneEvents:
    """Test scene and visual events."""
    
    def test_background_change_event(self):
        """Test BackgroundChangeEvent."""
        from higanvn.engine.events import BackgroundChangeEvent
        
        event = BackgroundChangeEvent(
            path="bg/school.png",
            previous_path="bg/home.png",
            transition="fade"
        )
        assert event.path == "bg/school.png"
        assert event.previous_path == "bg/home.png"
        assert event.transition == "fade"
    
    def test_cg_events(self):
        """Test CGShowEvent and CGHideEvent."""
        from higanvn.engine.events import CGShowEvent, CGHideEvent
        
        show = CGShowEvent(path="cg/ending_01.png")
        assert show.path == "cg/ending_01.png"
        
        hide = CGHideEvent()
        assert isinstance(hide, CGHideEvent)
    
    def test_character_show_event(self):
        """Test CharacterShowEvent."""
        from higanvn.engine.events import CharacterShowEvent
        
        event = CharacterShowEvent(
            actor="alice",
            pose="happy",
            position="center",
            first_appearance=True
        )
        assert event.actor == "alice"
        assert event.pose == "happy"
        assert event.first_appearance
    
    def test_character_hide_event(self):
        """Test CharacterHideEvent."""
        from higanvn.engine.events import CharacterHideEvent
        
        event = CharacterHideEvent(actor="bob")
        assert event.actor == "bob"
    
    def test_character_pose_change_event(self):
        """Test CharacterPoseChangeEvent."""
        from higanvn.engine.events import CharacterPoseChangeEvent
        
        event = CharacterPoseChangeEvent(
            actor="alice",
            old_pose="normal",
            new_pose="angry"
        )
        assert event.old_pose == "normal"
        assert event.new_pose == "angry"
    
    def test_character_outfit_change_event(self):
        """Test CharacterOutfitChangeEvent."""
        from higanvn.engine.events import CharacterOutfitChangeEvent
        
        event = CharacterOutfitChangeEvent(
            actor="alice",
            old_outfit="uniform",
            new_outfit="casual"
        )
        assert event.old_outfit == "uniform"
        assert event.new_outfit == "casual"


class TestEffectEvents:
    """Test visual effect events."""
    
    def test_shake_effect_event(self):
        """Test ShakeEffectEvent."""
        from higanvn.engine.events import ShakeEffectEvent
        
        event = ShakeEffectEvent(
            target="alice",
            intensity=30,
            duration_ms=500,
            direction="x"
        )
        assert event.target == "alice"
        assert event.intensity == 30
        assert event.duration_ms == 500
    
    def test_slide_effect_event(self):
        """Test SlideEffectEvent."""
        from higanvn.engine.events import SlideEffectEvent
        
        event = SlideEffectEvent(
            target="bob",
            direction="in_left",
            duration_ms=400
        )
        assert event.direction == "in_left"
    
    def test_fade_effect_event(self):
        """Test FadeEffectEvent."""
        from higanvn.engine.events import FadeEffectEvent
        
        event = FadeEffectEvent(
            fade_type="out",
            duration_ms=1000,
            color=(0, 0, 0)
        )
        assert event.fade_type == "out"
        assert event.color == (0, 0, 0)


class TestNavigationEvents:
    """Test navigation events."""
    
    def test_rewind_event(self):
        """Test RewindEvent."""
        from higanvn.engine.events import RewindEvent
        
        event = RewindEvent(from_ip=100, to_ip=95, success=True)
        assert event.from_ip == 100
        assert event.to_ip == 95
        assert event.success
    
    def test_history_scroll_event(self):
        """Test HistoryScrollEvent."""
        from higanvn.engine.events import HistoryScrollEvent
        
        event = HistoryScrollEvent(direction="up", lines=3)
        assert event.direction == "up"
        assert event.lines == 3
    
    def test_jump_to_label_event(self):
        """Test JumpToLabelEvent is cancellable."""
        from higanvn.engine.events import JumpToLabelEvent
        
        event = JumpToLabelEvent(target_label="ending_a", from_label="chapter_1")
        assert event.target_label == "ending_a"
        assert not event.cancelled
        
        event.cancel()
        assert event.cancelled


class TestTypewriterEvents:
    """Test typewriter events."""
    
    def test_typewriter_start_event(self):
        """Test TypewriterStartEvent."""
        from higanvn.engine.events import TypewriterStartEvent
        
        event = TypewriterStartEvent(text="Hello world", total_chars=11)
        assert event.text == "Hello world"
        assert event.total_chars == 11
    
    def test_typewriter_progress_event(self):
        """Test TypewriterProgressEvent."""
        from higanvn.engine.events import TypewriterProgressEvent
        
        event = TypewriterProgressEvent(
            revealed_chars=5,
            total_chars=10,
            percent=50.0
        )
        assert event.revealed_chars == 5
        assert event.percent == 50.0
    
    def test_typewriter_complete_event(self):
        """Test TypewriterCompleteEvent."""
        from higanvn.engine.events import TypewriterCompleteEvent
        
        event = TypewriterCompleteEvent(text="Hello", was_skipped=True)
        assert event.was_skipped
    
    def test_typewriter_skip_event(self):
        """Test TypewriterSkipEvent."""
        from higanvn.engine.events import TypewriterSkipEvent
        
        event = TypewriterSkipEvent()
        assert isinstance(event, TypewriterSkipEvent)


class TestGalleryEvents:
    """Test gallery events."""
    
    def test_gallery_open_close_events(self):
        """Test GalleryOpenEvent and GalleryCloseEvent."""
        from higanvn.engine.events import GalleryOpenEvent, GalleryCloseEvent
        
        open_event = GalleryOpenEvent()
        close_event = GalleryCloseEvent()
        
        assert isinstance(open_event, GalleryOpenEvent)
        assert isinstance(close_event, GalleryCloseEvent)
    
    def test_gallery_unlock_event(self):
        """Test GalleryUnlockEvent."""
        from higanvn.engine.events import GalleryUnlockEvent
        
        event = GalleryUnlockEvent(cg_id="cg_001", cg_path="cg/ending.png")
        assert event.cg_id == "cg_001"
        assert event.cg_path == "cg/ending.png"


class TestSettingsEvents:
    """Test settings events."""
    
    def test_settings_open_close_events(self):
        """Test SettingsOpenEvent and SettingsCloseEvent."""
        from higanvn.engine.events import SettingsOpenEvent, SettingsCloseEvent
        
        open_event = SettingsOpenEvent()
        close_event = SettingsCloseEvent()
        
        assert isinstance(open_event, SettingsOpenEvent)
        assert isinstance(close_event, SettingsCloseEvent)
    
    def test_settings_change_event(self):
        """Test SettingsChangeEvent."""
        from higanvn.engine.events import SettingsChangeEvent
        
        event = SettingsChangeEvent(
            setting_name="language",
            old_value="en",
            new_value="zh"
        )
        assert event.setting_name == "language"
        assert event.old_value == "en"
        assert event.new_value == "zh"
    
    def test_volume_change_event(self):
        """Test VolumeChangeEvent."""
        from higanvn.engine.events import VolumeChangeEvent
        
        event = VolumeChangeEvent(
            channel="bgm",
            old_value=1.0,
            new_value=0.7
        )
        assert event.channel == "bgm"
        assert event.new_value == 0.7
    
    def test_typewriter_speed_change_event(self):
        """Test TypewriterSpeedChangeEvent."""
        from higanvn.engine.events import TypewriterSpeedChangeEvent
        
        event = TypewriterSpeedChangeEvent(old_speed=1.0, new_speed=2.0)
        assert event.new_speed == 2.0


class TestWindowEvents:
    """Test window events."""
    
    def test_window_resize_event(self):
        """Test WindowResizeEvent."""
        from higanvn.engine.events import WindowResizeEvent
        
        event = WindowResizeEvent(
            old_size=(1280, 720),
            new_size=(1920, 1080)
        )
        assert event.old_size == (1280, 720)
        assert event.new_size == (1920, 1080)
    
    def test_window_focus_event(self):
        """Test WindowFocusEvent."""
        from higanvn.engine.events import WindowFocusEvent
        
        event = WindowFocusEvent(focused=False)
        assert not event.focused
    
    def test_fullscreen_toggle_event(self):
        """Test FullscreenToggleEvent."""
        from higanvn.engine.events import FullscreenToggleEvent
        
        event = FullscreenToggleEvent(fullscreen=True)
        assert event.fullscreen


class TestErrorEvents:
    """Test error events."""
    
    def test_error_event(self):
        """Test ErrorEvent."""
        from higanvn.engine.events import ErrorEvent
        
        event = ErrorEvent(
            error_type="script_error",
            message="Undefined label",
            recoverable=True,
            details={"label": "missing_label"}
        )
        assert event.error_type == "script_error"
        assert event.recoverable
        assert event.details["label"] == "missing_label"
    
    def test_warning_event(self):
        """Test WarningEvent."""
        from higanvn.engine.events import WarningEvent
        
        event = WarningEvent(
            warning_type="missing_asset",
            message="Could not find bg/test.png"
        )
        assert event.warning_type == "missing_asset"


class TestScriptEvents:
    """Test script/flow control events."""
    
    def test_script_load_event(self):
        """Test ScriptLoadEvent."""
        from higanvn.engine.events import ScriptLoadEvent
        
        event = ScriptLoadEvent(path="scripts/game.vns", op_count=150)
        assert event.path == "scripts/game.vns"
        assert event.op_count == 150
    
    def test_script_exec_event(self):
        """Test ScriptExecEvent."""
        from higanvn.engine.events import ScriptExecEvent
        
        event = ScriptExecEvent(code="x = x + 1", result=5)
        assert event.code == "x = x + 1"
        assert event.result == 5
    
    def test_variable_change_event(self):
        """Test VariableChangeEvent."""
        from higanvn.engine.events import VariableChangeEvent
        
        event = VariableChangeEvent(
            name="mood",
            old_value="neutral",
            new_value="happy",
            source="SET"
        )
        assert event.name == "mood"
        assert event.old_value == "neutral"
        assert event.new_value == "happy"
        assert event.source == "SET"
    
    def test_wait_event(self):
        """Test WaitEvent."""
        from higanvn.engine.events import WaitEvent
        
        event = WaitEvent(duration_ms=500)
        assert event.duration_ms == 500
    
    def test_conditional_event(self):
        """Test ConditionalEvent."""
        from higanvn.engine.events import ConditionalEvent
        
        event = ConditionalEvent(
            condition_type="IF",
            expression="mood == 'happy'",
            result=True
        )
        assert event.condition_type == "IF"
        assert event.expression == "mood == 'happy'"
        assert event.result
    
    def test_goto_event(self):
        """Test GotoEvent."""
        from higanvn.engine.events import GotoEvent
        
        event = GotoEvent(target_label="ending_1", from_ip=42)
        assert event.target_label == "ending_1"
        assert event.from_ip == 42


class TestChoiceSystemEvents:
    """Test choice system events."""
    
    def test_choice_present_event(self):
        """Test ChoicePresentEvent."""
        from higanvn.engine.events import ChoicePresentEvent
        
        event = ChoicePresentEvent(
            choices=["Go left", "Go right"],
            targets=["left_path", "right_path"]
        )
        assert len(event.choices) == 2
        assert event.choices[0] == "Go left"
        assert event.targets[1] == "right_path"
    
    def test_choice_hover_event(self):
        """Test ChoiceHoverEvent."""
        from higanvn.engine.events import ChoiceHoverEvent
        
        event = ChoiceHoverEvent(index=1, text="Go right")
        assert event.index == 1
        assert event.text == "Go right"
    
    def test_choice_timeout_event(self):
        """Test ChoiceTimeoutEvent."""
        from higanvn.engine.events import ChoiceTimeoutEvent
        
        event = ChoiceTimeoutEvent(default_index=0)
        assert event.default_index == 0
        # Should be cancellable
        event.cancel()
        assert event.cancelled


class TestSlotUIEvents:
    """Test slot UI events."""
    
    def test_slot_select_event(self):
        """Test SlotSelectEvent."""
        from higanvn.engine.events import SlotSelectEvent
        
        event = SlotSelectEvent(slot_id=3, mode="save", has_data=True)
        assert event.slot_id == 3
        assert event.mode == "save"
        assert event.has_data
    
    def test_slot_hover_event(self):
        """Test SlotHoverEvent."""
        from higanvn.engine.events import SlotHoverEvent
        
        event = SlotHoverEvent(slot_id=5, has_data=False)
        assert event.slot_id == 5
        assert not event.has_data
    
    def test_slot_delete_event(self):
        """Test SlotDeleteEvent."""
        from higanvn.engine.events import SlotDeleteEvent
        
        event = SlotDeleteEvent(slot_id=2)
        assert event.slot_id == 2
        # Should be cancellable
        event.cancel()
        assert event.cancelled
    
    def test_slot_delete_complete_event(self):
        """Test SlotDeleteCompleteEvent."""
        from higanvn.engine.events import SlotDeleteCompleteEvent
        
        event = SlotDeleteCompleteEvent(slot_id=2, success=True)
        assert event.slot_id == 2
        assert event.success
    
    def test_slot_page_change_event(self):
        """Test SlotPageChangeEvent."""
        from higanvn.engine.events import SlotPageChangeEvent
        
        event = SlotPageChangeEvent(old_page=1, new_page=2)
        assert event.old_page == 1
        assert event.new_page == 2


class TestAnimationEvents:
    """Test animation events."""
    
    def test_animation_start_event(self):
        """Test AnimationStartEvent."""
        from higanvn.engine.events import AnimationStartEvent
        
        event = AnimationStartEvent(
            target="character_1",
            animation_type="slide_in_left",
            duration_ms=300
        )
        assert event.target == "character_1"
        assert event.animation_type == "slide_in_left"
        assert event.duration_ms == 300
    
    def test_animation_end_event(self):
        """Test AnimationEndEvent."""
        from higanvn.engine.events import AnimationEndEvent
        
        event = AnimationEndEvent(
            target="character_1",
            animation_type="slide_in_left",
            completed=True
        )
        assert event.completed
    
    def test_animation_cancel_event(self):
        """Test AnimationCancelEvent."""
        from higanvn.engine.events import AnimationCancelEvent
        
        event = AnimationCancelEvent(
            target="character_1",
            animation_type="shake_x"
        )
        assert event.target == "character_1"


class TestVoiceEvents:
    """Test voice-specific events."""
    
    def test_voice_start_event(self):
        """Test VoiceStartEvent."""
        from higanvn.engine.events import VoiceStartEvent
        
        event = VoiceStartEvent(
            path="voice/ch01_001.ogg",
            speaker="Alice",
            duration_ms=5000
        )
        assert event.path == "voice/ch01_001.ogg"
        assert event.speaker == "Alice"
        assert event.duration_ms == 5000
    
    def test_voice_end_event(self):
        """Test VoiceEndEvent."""
        from higanvn.engine.events import VoiceEndEvent
        
        event = VoiceEndEvent(path="voice/ch01_001.ogg", was_stopped=False)
        assert not event.was_stopped
    
    def test_voice_volume_change_event(self):
        """Test VoiceVolumeChangeEvent."""
        from higanvn.engine.events import VoiceVolumeChangeEvent
        
        event = VoiceVolumeChangeEvent(old_volume=1.0, new_volume=0.5)
        assert event.old_volume == 1.0
        assert event.new_volume == 0.5


class TestTextPanelEvents:
    """Test text panel events."""
    
    def test_text_panel_show_hide_events(self):
        """Test TextPanelShowEvent and TextPanelHideEvent."""
        from higanvn.engine.events import TextPanelShowEvent, TextPanelHideEvent
        
        show_event = TextPanelShowEvent()
        hide_event = TextPanelHideEvent()
        
        assert isinstance(show_event, TextPanelShowEvent)
        assert isinstance(hide_event, TextPanelHideEvent)
    
    def test_text_clear_event(self):
        """Test TextClearEvent."""
        from higanvn.engine.events import TextClearEvent
        
        event = TextClearEvent()
        assert isinstance(event, TextClearEvent)
    
    def test_speaker_change_event(self):
        """Test SpeakerChangeEvent."""
        from higanvn.engine.events import SpeakerChangeEvent
        
        event = SpeakerChangeEvent(
            old_speaker="Alice",
            new_speaker="Bob"
        )
        assert event.old_speaker == "Alice"
        assert event.new_speaker == "Bob"


class TestQuickSaveLoadEvents:
    """Test quick save/load events."""
    
    def test_quick_save_event(self):
        """Test QuickSaveEvent."""
        from higanvn.engine.events import QuickSaveEvent
        
        event = QuickSaveEvent()
        assert not event.cancelled
        event.cancel()
        assert event.cancelled
    
    def test_quick_save_complete_event(self):
        """Test QuickSaveCompleteEvent."""
        from higanvn.engine.events import QuickSaveCompleteEvent
        
        event = QuickSaveCompleteEvent(success=True, path="save/quick.json")
        assert event.success
        assert event.path == "save/quick.json"
    
    def test_quick_load_event(self):
        """Test QuickLoadEvent."""
        from higanvn.engine.events import QuickLoadEvent
        
        event = QuickLoadEvent()
        event.cancel()
        assert event.cancelled
    
    def test_quick_load_complete_event(self):
        """Test QuickLoadCompleteEvent."""
        from higanvn.engine.events import QuickLoadCompleteEvent
        
        event = QuickLoadCompleteEvent(success=True, path="save/quick.json")
        assert event.success


class TestSkipModeEvents:
    """Test skip mode events."""
    
    def test_skip_mode_enter_event(self):
        """Test SkipModeEnterEvent."""
        from higanvn.engine.events import SkipModeEnterEvent
        
        event = SkipModeEnterEvent(skip_type="read")
        assert event.skip_type == "read"
    
    def test_skip_mode_exit_event(self):
        """Test SkipModeExitEvent."""
        from higanvn.engine.events import SkipModeExitEvent
        
        event = SkipModeExitEvent(reason="choice")
        assert event.reason == "choice"


class TestBacklogEvents:
    """Test backlog events."""
    
    def test_backlog_entry_add_event(self):
        """Test BacklogEntryAddEvent."""
        from higanvn.engine.events import BacklogEntryAddEvent
        
        event = BacklogEntryAddEvent(
            speaker="Alice",
            text="Hello, world!",
            entry_index=42
        )
        assert event.speaker == "Alice"
        assert event.text == "Hello, world!"
        assert event.entry_index == 42
    
    def test_backlog_jump_event(self):
        """Test BacklogJumpEvent."""
        from higanvn.engine.events import BacklogJumpEvent
        
        event = BacklogJumpEvent(target_index=10)
        assert event.target_index == 10
        event.cancel()
        assert event.cancelled
    
    def test_backlog_voice_replay_event(self):
        """Test BacklogVoiceReplayEvent."""
        from higanvn.engine.events import BacklogVoiceReplayEvent
        
        event = BacklogVoiceReplayEvent(
            entry_index=5,
            voice_path="voice/ch01_005.ogg"
        )
        assert event.entry_index == 5
        assert event.voice_path == "voice/ch01_005.ogg"


class TestSystemEvents:
    """Test system events."""
    
    def test_language_change_event(self):
        """Test LanguageChangeEvent."""
        from higanvn.engine.events import LanguageChangeEvent
        
        event = LanguageChangeEvent(old_language="en", new_language="ja")
        assert event.old_language == "en"
        assert event.new_language == "ja"
    
    def test_font_size_change_event(self):
        """Test FontSizeChangeEvent."""
        from higanvn.engine.events import FontSizeChangeEvent
        
        event = FontSizeChangeEvent(old_size=24, new_size=28)
        assert event.old_size == 24
        assert event.new_size == 28
    
    def test_display_mode_change_event(self):
        """Test DisplayModeChangeEvent."""
        from higanvn.engine.events import DisplayModeChangeEvent
        
        event = DisplayModeChangeEvent(
            old_mode="windowed",
            new_mode="fullscreen"
        )
        assert event.old_mode == "windowed"
        assert event.new_mode == "fullscreen"
    
    def test_vsync_change_event(self):
        """Test VSyncChangeEvent."""
        from higanvn.engine.events import VSyncChangeEvent
        
        event = VSyncChangeEvent(enabled=True)
        assert event.enabled
    
    def test_frame_rate_event(self):
        """Test FrameRateEvent."""
        from higanvn.engine.events import FrameRateEvent
        
        event = FrameRateEvent(current_fps=59.5, avg_fps=60.0)
        assert event.current_fps == 59.5
        assert event.avg_fps == 60.0


class TestAccessibilityEvents:
    """Test accessibility events."""
    
    def test_text_to_speech_event(self):
        """Test TextToSpeechEvent."""
        from higanvn.engine.events import TextToSpeechEvent
        
        event = TextToSpeechEvent(text="Hello", speaker="Alice")
        assert event.text == "Hello"
        assert event.speaker == "Alice"
    
    def test_high_contrast_mode_event(self):
        """Test HighContrastModeEvent."""
        from higanvn.engine.events import HighContrastModeEvent
        
        event = HighContrastModeEvent(enabled=True)
        assert event.enabled
    
    def test_large_text_mode_event(self):
        """Test LargeTextModeEvent."""
        from higanvn.engine.events import LargeTextModeEvent
        
        event = LargeTextModeEvent(enabled=True, scale=1.5)
        assert event.enabled
        assert event.scale == 1.5


class TestInputEventsExtended:
    """Test extended input events."""
    
    def test_mouse_move_event(self):
        """Test MouseMoveEvent."""
        from higanvn.engine.events import MouseMoveEvent
        
        event = MouseMoveEvent(
            pos=(100, 200),
            rel=(5, -3),
            canvas_pos=(100, 200)
        )
        assert event.pos == (100, 200)
        assert event.rel == (5, -3)
    
    def test_mouse_button_up_event(self):
        """Test MouseButtonUpEvent."""
        from higanvn.engine.events import MouseButtonUpEvent
        
        event = MouseButtonUpEvent(button=1, pos=(50, 50))
        assert event.button == 1
        assert event.pos == (50, 50)
    
    def test_controller_button_event(self):
        """Test ControllerButtonEvent."""
        from higanvn.engine.events import ControllerButtonEvent
        
        event = ControllerButtonEvent(
            button=0,
            pressed=True,
            controller_id=0
        )
        assert event.button == 0
        assert event.pressed
        assert event.controller_id == 0
    
    def test_controller_axis_event(self):
        """Test ControllerAxisEvent."""
        from higanvn.engine.events import ControllerAxisEvent
        
        event = ControllerAxisEvent(axis=0, value=0.75, controller_id=0)
        assert event.axis == 0
        assert event.value == 0.75
    
    def test_touch_event(self):
        """Test TouchEvent."""
        from higanvn.engine.events import TouchEvent
        
        event = TouchEvent(touch_id=0, pos=(100, 200), touch_type="down")
        assert event.touch_id == 0
        assert event.touch_type == "down"


class TestGameStateEvents:
    """Test game state events."""
    
    def test_game_pause_event(self):
        """Test GamePauseEvent."""
        from higanvn.engine.events import GamePauseEvent
        
        event = GamePauseEvent(reason="menu")
        assert event.reason == "menu"
    
    def test_game_resume_event(self):
        """Test GameResumeEvent."""
        from higanvn.engine.events import GameResumeEvent
        
        event = GameResumeEvent()
        assert isinstance(event, GameResumeEvent)
    
    def test_scene_transition_event(self):
        """Test SceneTransitionEvent."""
        from higanvn.engine.events import SceneTransitionEvent
        
        event = SceneTransitionEvent(
            from_scene="prologue",
            to_scene="chapter_1",
            transition_type="fade"
        )
        assert event.from_scene == "prologue"
        assert event.to_scene == "chapter_1"
    
    def test_chapter_start_event(self):
        """Test ChapterStartEvent."""
        from higanvn.engine.events import ChapterStartEvent
        
        event = ChapterStartEvent(
            chapter_id="ch01",
            chapter_name="The Beginning"
        )
        assert event.chapter_id == "ch01"
        assert event.chapter_name == "The Beginning"
    
    def test_chapter_end_event(self):
        """Test ChapterEndEvent."""
        from higanvn.engine.events import ChapterEndEvent
        
        event = ChapterEndEvent(chapter_id="ch01")
        assert event.chapter_id == "ch01"
    
    def test_ending_reach_event(self):
        """Test EndingReachEvent."""
        from higanvn.engine.events import EndingReachEvent
        
        event = EndingReachEvent(
            ending_id="end_true",
            ending_name="True Ending",
            ending_type="true"
        )
        assert event.ending_id == "end_true"
        assert event.ending_type == "true"
    
    def test_new_game_plus_event(self):
        """Test NewGamePlusEvent."""
        from higanvn.engine.events import NewGamePlusEvent
        
        event = NewGamePlusEvent(
            clear_count=1,
            unlocked_features=["gallery", "skip_all"]
        )
        assert event.clear_count == 1
        assert "gallery" in event.unlocked_features


class TestPluginEvents:
    """Test plugin-related events."""
    
    def test_plugin_load_event(self):
        """Test PluginLoadEvent."""
        from higanvn.engine.events import PluginLoadEvent
        
        event = PluginLoadEvent(
            plugin_id="my_plugin",
            plugin_name="My Plugin",
            version="1.0.0"
        )
        assert event.plugin_id == "my_plugin"
        assert event.version == "1.0.0"
    
    def test_plugin_unload_event(self):
        """Test PluginUnloadEvent."""
        from higanvn.engine.events import PluginUnloadEvent
        
        event = PluginUnloadEvent(plugin_id="my_plugin")
        assert event.plugin_id == "my_plugin"
    
    def test_plugin_error_event(self):
        """Test PluginErrorEvent."""
        from higanvn.engine.events import PluginErrorEvent
        
        event = PluginErrorEvent(
            plugin_id="my_plugin",
            error="Failed to initialize"
        )
        assert event.error == "Failed to initialize"
    
    def test_custom_command_event(self):
        """Test CustomCommandEvent."""
        from higanvn.engine.events import CustomCommandEvent
        
        event = CustomCommandEvent(
            command_name="my_command",
            args={"param1": "value1"}
        )
        assert event.command_name == "my_command"
        assert event.args["param1"] == "value1"
        # Should be cancellable
        event.cancel()
        assert event.cancelled


class TestTelemetryEvents:
    """Test telemetry events."""
    
    def test_session_start_event(self):
        """Test SessionStartEvent."""
        from higanvn.engine.events import SessionStartEvent
        
        event = SessionStartEvent(session_id="abc123")
        assert event.session_id == "abc123"
    
    def test_session_end_event(self):
        """Test SessionEndEvent."""
        from higanvn.engine.events import SessionEndEvent
        
        event = SessionEndEvent(
            session_id="abc123",
            play_time_seconds=3600.0
        )
        assert event.play_time_seconds == 3600.0
    
    def test_milestone_event(self):
        """Test MilestoneEvent."""
        from higanvn.engine.events import MilestoneEvent
        
        event = MilestoneEvent(
            milestone_id="first_choice",
            milestone_type="story_progress"
        )
        assert event.milestone_id == "first_choice"


class TestHotkeyEvents:
    """Test hotkey events."""
    
    def test_hotkey_trigger_event(self):
        """Test HotkeyTriggerEvent."""
        from higanvn.engine.events import HotkeyTriggerEvent
        
        event = HotkeyTriggerEvent(
            action="quicksave",
            key_combination="Ctrl+S"
        )
        assert event.action == "quicksave"
        assert event.key_combination == "Ctrl+S"
    
    def test_hotkey_register_event(self):
        """Test HotkeyRegisterEvent."""
        from higanvn.engine.events import HotkeyRegisterEvent
        
        event = HotkeyRegisterEvent(
            action="screenshot",
            key_combination="F12"
        )
        assert event.action == "screenshot"


class TestLocalizationEvents:
    """Test localization events."""
    
    def test_locale_load_event(self):
        """Test LocaleLoadEvent."""
        from higanvn.engine.events import LocaleLoadEvent
        
        event = LocaleLoadEvent(locale_id="ja_JP", strings_count=500)
        assert event.locale_id == "ja_JP"
        assert event.strings_count == 500
    
    def test_missing_translation_event(self):
        """Test MissingTranslationEvent."""
        from higanvn.engine.events import MissingTranslationEvent
        
        event = MissingTranslationEvent(
            key="ui.button.start",
            locale_id="fr_FR"
        )
        assert event.key == "ui.button.start"
        assert event.locale_id == "fr_FR"
