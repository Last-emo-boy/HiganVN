from __future__ import annotations

from typing import Any, Dict, Optional


class IRenderer:
    """Abstract rendering/audio interface.

    Minimal subset for M0; pygame implementation can implement the same API later.
    """

    def set_background(self, path: Optional[str]) -> None:  # BG
        raise NotImplementedError

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:  # BGM
        raise NotImplementedError

    def play_se(self, path: str, volume: float | None = None) -> None:  # SE
        raise NotImplementedError

    # Voice (per-line voice-over). Renderer may start playback on the next dialogue line.
    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:  # VOICE
        pass

    def show_text(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        raise NotImplementedError

    def command(self, name: str, args: str) -> None:
        """Fallback for commands not explicitly modeled yet."""
        raise NotImplementedError

    # Interaction primitives
    def wait_for_advance(self) -> None:
        """Block until user input to advance a line (click/enter/etc.)."""
        raise NotImplementedError

    def ask_choice(self, choices: list[tuple[str, str]]) -> int:
        """Present choices and return selected index (0-based)."""
        raise NotImplementedError

    # Optional UI error banner (GUI renderers may override)
    def show_error(self, message: str) -> None:
        """Display a non-fatal error message to the user."""
        # Default headless behavior: print to console
        print(f"[ERROR] {message}")  # noqa: T201

    # Optional UI info banner (GUI renderers may override)
    def show_banner(self, message: str, color: tuple[int, int, int] | None = None) -> None:
        # Default headless behavior: print to console
        print(f"[INFO] {message}")  # noqa: T201

    # Optional hooks used by Engine for saves/back; GUI renderers may implement.
    def set_quicksave_hook(self, fn):
        pass

    def set_quickload_hook(self, fn):
        pass

    def set_back_hook(self, fn):
        pass

    def set_save_slot_hook(self, fn):
        pass

    def set_load_slot_hook(self, fn):
        pass

    def set_get_save_dir(self, fn):
        pass
    def set_list_slots_hook(self, fn):
        pass
    def set_delete_slot_hook(self, fn):
        pass
    def set_jump_to_label_hook(self, fn):
        """Optional: allow UI to request jumping to a given label."""
        pass

    # Optional: allow external modules (e.g., Engine) to add debug providers
    def add_debug_provider(self, name: str, fn):
        pass

    def reset_state(self) -> None:
        """Reset transient visual state; may be a no-op for headless implementations."""
        pass

    def begin_fast_replay(self) -> None:
        pass

    def end_fast_replay(self) -> None:
        pass

    def set_textbox(self, textbox, owned: bool = True) -> None:
        """Inject a Textbox-like model.

        owned=False means the renderer must not replace or mutate lifecycle
        (e.g., not recreate on reset_state); still can read/scroll.
        """
        pass

    # Optional: provide program graph for flow-map UI
    def set_program(self, program) -> None:
        pass

    # Optional: inform renderer current label for visited tracking
    def on_enter_label(self, label: str) -> None:
        pass

    def show_title_menu(self, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:
        """Show a title screen/menu and return one of: 'start','load','settings','gallery','quit', or None."""
        return None

    # --- Menus & system actions (optional) ---
    def open_slots_menu(self, mode: str = "load") -> Optional[int]:
        """Open built-in slot UI (mode: 'load' or 'save'). Returns selected slot or None.
        Implementations may also perform the save/load operation via installed hooks.
        """
        return None

    def open_settings_menu(self) -> None:
        """Open a small settings menu (typing speed, auto mode). Optional UI."""
        pass

    def open_gallery(self) -> None:
        """Open CG gallery (optional). Default may show a banner or no-op."""
        pass

    def quit(self) -> None:
        """Quit the game/application."""
        raise SystemExit


class DummyRenderer(IRenderer):
    """Headless renderer that prints actions; useful for tests and CLI."""

    def set_background(self, path: Optional[str]) -> None:
        if path:
            print(f"> BG {path}")  # noqa: T201
        else:
            print("> BG None")  # noqa: T201

    def play_bgm(self, path: Optional[str], volume: float | None = None) -> None:
        if path:
            vol = f" {volume}" if volume is not None else ""
            print(f"> BGM {path}{vol}")  # noqa: T201
        else:
            print("> BGM None")  # noqa: T201

    def play_se(self, path: str, volume: float | None = None) -> None:
        vol = f" {volume}" if volume is not None else ""
        print(f"> SE {path}{vol}")  # noqa: T201

    def prepare_voice(self, path: Optional[str], volume: float | None = None) -> None:
        if path:
            vol = f" {volume}" if volume is not None else ""
            print(f"> VOICE {path}{vol}")  # noqa: T201
        else:
            print("> VOICE None")  # noqa: T201

    def show_text(self, name: Optional[str], text: str, meta: Optional[dict] = None) -> None:
        suffix = ""
        if meta and (meta.get("emotion") or meta.get("effect")):
            emo = meta.get("emotion")
            eff = meta.get("effect")
            tags = [t for t in [emo, eff] if t]
            if tags:
                suffix = f" [{' '.join(tags)}]"
        if name:
            print(f"{name}{suffix}: {text}")  # noqa: T201
        else:
            print(text)  # noqa: T201

    def command(self, name: str, args: str) -> None:
        print(f"> {name} {args}".rstrip())  # noqa: T201

    def wait_for_advance(self) -> None:
        try:
            input("")
        except Exception:
            pass

    def ask_choice(self, choices: list[tuple[str, str]]) -> int:
        try:
            print("请选择：")  # noqa: T201
            for idx, (txt, tgt) in enumerate(choices, 1):
                print(f"  {idx}. {txt} -> {tgt}")  # noqa: T201
            raw = input("> ")
            sel = int(raw.strip())
            if 1 <= sel <= len(choices):
                return sel - 1
        except Exception:
            return 0
        return 0

    def show_error(self, message: str) -> None:
        print(f"[ERROR] {message}")  # noqa: T201

    def show_banner(self, message: str, color: tuple[int, int, int] | None = None) -> None:
        print(f"[INFO] {message}")  # noqa: T201

    def open_slots_menu(self, mode: str = "load") -> Optional[int]:
        try:
            print(f"[{mode.upper()}] 请输入槽位编号 (0-11)，留空取消：")  # noqa: T201
            raw = input("> ")
            if not raw.strip():
                return None
            slot = int(raw.strip())
            return slot
        except Exception:
            return None

    def open_settings_menu(self) -> None:
        print("[Settings] 暂无 GUI，在 pygame 版中可用。")  # noqa: T201

    def open_gallery(self) -> None:
        print("[Gallery] 暂未实装。")  # noqa: T201

    def show_title_menu(self, title: Optional[str] = None, bg_path: Optional[str] = None) -> Optional[str]:
        print(f"[TITLE] {title or 'Game'}")  # noqa: T201
        print("1. Start  2. Load  3. Settings  4. Gallery  5. Quit")  # noqa: T201
        try:
            raw = input("> ")
            m = {"1":"start","2":"load","3":"settings","4":"gallery","5":"quit"}
            return m.get(raw.strip(), "start")
        except Exception:
            return "start"
