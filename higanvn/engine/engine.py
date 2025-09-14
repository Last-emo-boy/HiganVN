from __future__ import annotations

from typing import Iterable, List, Optional, Dict, Any, Tuple

from .renderer import IRenderer, DummyRenderer
from .adapters.storage import ISaveStore, FileSaveStore
from .event_bus import EventBus
from ..script.parser import parse_script
from ..script.model import Op, Program
from pathlib import Path
import json
from ..script.errors import ScriptError
from datetime import datetime
import os
from ..ui.textbox import Textbox
from .expr import safe_eval
import time
from .sandbox import safe_exec
import re
import hashlib


 


class Engine:
    def __init__(self, renderer: Optional[IRenderer] = None, interactive: bool = False, strict: bool = False,
                 save_store: Optional[ISaveStore] = None) -> None:
        self.program = None
        self.ip = 0
        self.renderer = renderer or DummyRenderer()
        self.interactive = interactive
        self.strict = strict
        self.script_path = None
        # event bus (pub/sub)
        self.events = EventBus()
        # record of choices taken so far (indices in each choice block)
        self.choice_trace = []
        # choices to replay on load (set temporarily during reconstruction)
        self._replay_choices = None
        # record of op indices that produced visible text (for back/rewind)
        self.line_ip_trace = []
        # return addresses for CALL/RETURN
        self.call_stack = []
        # shared textbox model
        self.textbox = Textbox()
        # inject textbox and hooks into renderer if supported
        self._install_renderer_hooks()
        # simple variable store for SET/IF
        self.vars = {}
        # conditional chain state for IF/ELSEIF/ELSE
        self._cond_chain_active = False
        self._cond_chain_taken = False
        # switch-case state
        self._switch_active = False
        self._switch_value = None
        self._switch_matched = False
        # pluggable save store (defaults to file-based under Documents/HiganVN/<game>)
        try:
            self._save_store = save_store or FileSaveStore(lambda: self.get_save_dir())
        except Exception:
            self._save_store = None

    def load(self, program: Program) -> None:
        self.program = program
        self.ip = 0
        # reset choice history when loading a program
        self.choice_trace = []
        # reset line trace on program load
        self.line_ip_trace = []
        # reset call stack
        self.call_stack = []
        # reset variables for new program
        self.vars = {}
        # clear textbox content
        try:
            self.textbox.clear()
        except Exception:
            pass
        # provide program to renderer for flow map
        try:
            if hasattr(self.renderer, "set_program"):
                self.renderer.set_program(program)  # type: ignore[attr-defined]
        except Exception:
            pass
        # notify listeners
        try:
            self.events.emit("engine.load", count=len(program.ops) if program else 0)
        except Exception:
            pass

    def set_script_path(self, path: Path) -> None:
        # store absolute path to avoid issues after chdir (e.g., pygame changes CWD to assets)
        try:
            self.script_path = Path(path).resolve()
        except Exception:
            self.script_path = Path(path)
        # inform renderer for debug provider
        try:
            if hasattr(self.renderer, "_engine_script_path"):
                setattr(self.renderer, "_engine_script_path", self.script_path)
        except Exception:
            pass

    def _install_renderer_hooks(self) -> None:
        try:
            if hasattr(self.renderer, "set_textbox") and callable(getattr(self.renderer, "set_textbox")):
                # engine owns the model lifecycle; renderer should not replace it
                self.renderer.set_textbox(self.textbox, owned=False)  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_quicksave_hook"):
                self.renderer.set_quicksave_hook(lambda: self.quicksave())  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_quickload_hook"):
                self.renderer.set_quickload_hook(lambda: self.quickload())  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_back_hook"):
                self.renderer.set_back_hook(lambda: self.back_one_line())  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_save_slot_hook"):
                self.renderer.set_save_slot_hook(lambda slot: self.save_to_slot(int(slot)))  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_load_slot_hook"):
                self.renderer.set_load_slot_hook(lambda slot: self.load_from_slot(int(slot)))  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_get_save_dir"):
                self.renderer.set_get_save_dir(lambda: self.get_save_dir())  # type: ignore[attr-defined]
        except Exception:
            pass
        # optional: list/delete hooks for slots UI
        try:
            if hasattr(self.renderer, "set_list_slots_hook") and self._save_store and hasattr(self._save_store, "list_slots"):
                self.renderer.set_list_slots_hook(lambda: list(self._save_store.list_slots()))  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if hasattr(self.renderer, "set_delete_slot_hook") and self._save_store and hasattr(self._save_store, "delete_slot"):
                self.renderer.set_delete_slot_hook(lambda slot: bool(self._save_store.delete_slot(int(slot))))  # type: ignore[attr-defined]
        except Exception:
            pass

    # --- save directory helpers ---
    def _load_metadata(self) -> dict:
        # Optional metadata file next to the script: <script>.meta.json
        try:
            if not self.script_path:
                return {}
            meta_file = Path(str(self.script_path)).with_suffix('.meta.json')
            if meta_file.exists():
                return json.loads(meta_file.read_text(encoding='utf-8'))
        except Exception:
            return {}
        return {}

    def _sanitize_name(self, name: str) -> str:
        # Remove characters not friendly for filesystem
        bad = '<>:"/\\|?*'
        out = ''.join('_' if ch in bad else ch for ch in str(name))
        out = out.strip().strip('.')
        return out or 'Game'

    def _resolve_save_dir(self) -> Path:
        # Prefer Documents/HiganVN/<game-id>
        home = Path.home()
        docs = home / 'Documents'
        base = docs if docs.exists() else home
        game_id = None
        meta = self._load_metadata()
        if isinstance(meta, dict):
            # allow multiple keys: saveId > id > title > name
            game_id = meta.get('saveId') or meta.get('id') or meta.get('title') or meta.get('name')
        if not game_id and self.script_path:
            game_id = Path(self.script_path).stem
        folder = self._sanitize_name(str(game_id or 'Game'))
        return base / 'HiganVN' / folder

    def get_save_dir(self) -> Path:
        p = self._resolve_save_dir()
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p

    def step(self) -> bool:
        if not self.program:
            return False
        if self.ip >= len(self.program.ops):
            return False
        op = self.program.ops[self.ip]
        # update renderer debug hooks
        try:
            setattr(self.renderer, "_engine_ip", int(self.ip))
            setattr(self.renderer, "_engine_call_stack_depth", int(len(self.call_stack)))
            # snapshot public vars shallowly (avoid large objects)
            if isinstance(self.vars, dict):
                snap = {k: v for k, v in self.vars.items() if isinstance(k, str) and (isinstance(v, (int, float, str, bool)) or v is None)}
                setattr(self.renderer, "_engine_vars_snapshot", snap)
        except Exception:
            pass
        # pre-op event
        try:
            self.events.emit("engine.before_op", ip=int(self.ip), kind=str(op.kind))
        except Exception:
            pass
        self._execute(op)
        self.ip += 1
        # post-op event
        try:
            self.events.emit("engine.after_op", ip=int(self.ip))
        except Exception:
            pass
        return True

    def run_headless(self) -> None:
        while True:
            try:
                if not self.step():
                    break
            except ScriptError as e:
                # In interactive mode, show on renderer; otherwise raise
                if self.interactive:
                    self.renderer.show_error(str(e))
                    # continue attempting to run (skip this op)
                    self.ip += 1
                    continue
                else:
                    raise

    # Minimal execution for MVP: print actions
    def _execute(self, op: Op) -> None:
        k = op.kind
        p = op.payload
        # Reset IF chain when encountering non-conditional commands
        if k != "command" or str(p.get("name", "")).upper() not in {"IF", "ELSEIF", "ELSE", "SWITCH", "CASE", "DEFAULT", "ENDSWITCH"}:
            self._cond_chain_active = False
            self._cond_chain_taken = False
            # Optionally auto-end switch on unrelated op
            if k != "command" or str(p.get("name", "")).upper() not in {"SWITCH", "CASE", "DEFAULT", "ENDSWITCH"}:
                self._switch_active = False
                self._switch_value = None
                self._switch_matched = False

        def _interp(txt: str | None) -> str:
            if not isinstance(txt, str):
                return ""
            # Replace {var} with value from self.vars; keep unknown placeholders unchanged
            def repl(m: re.Match[str]) -> str:
                name = m.group(1)
                return str(self.vars.get(name, m.group(0)))
            return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, txt)
        if k == "narration":
            # record the op index for this visible line
            try:
                self.line_ip_trace.append(int(self.ip))
            except Exception:
                pass
            try:
                self.events.emit("text.show", who=None, text=str(_interp(p.get("text"))))
            except Exception:
                pass
            self.renderer.show_text(None, _interp(p.get("text")), None)
            if self.interactive:
                self.renderer.wait_for_advance()
        elif k == "dialogue":
            who = p.get("actor", "?")
            alias = p.get("alias")
            display = f"{who}|{alias}" if alias else who
            meta = {"emotion": p.get("emotion"), "effect": p.get("effect")}
            try:
                self.line_ip_trace.append(int(self.ip))
            except Exception:
                pass
            try:
                self.events.emit("text.show", who=str(display), text=str(_interp(p.get("text"))), meta=dict(meta))
            except Exception:
                pass
            self.renderer.show_text(display, _interp(p.get("text")), meta)
            if self.interactive:
                self.renderer.wait_for_advance()
        elif k == "command":
            try:
                self.events.emit("command", name=str(p.get("name") or ""), args=str(p.get("args") or ""))
            except Exception:
                pass
            self._execute_command(p.get("name") or "", p.get("args") or "", p.get("line"))
        elif k == "label":
            # no-op in headless
            try:
                name = p.get("name")
                if name and hasattr(self.renderer, "on_enter_label"):
                    self.renderer.on_enter_label(str(name))  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                if name:
                    self.events.emit("label.enter", name=str(name))
            except Exception:
                pass
        elif k == "choice":
            # gather contiguous choices
            start = self.ip
            choices: List[Tuple[str, str]] = []  # (text, target)
            if not self.program:
                return
            i = start
            while i < len(self.program.ops) and self.program.ops[i].kind == "choice":
                ch = self.program.ops[i].payload
                choices.append((ch.get("text", ""), ch.get("target", "")))
                i += 1
            # select
            sel_idx = 0
            if self.interactive and choices:
                sel_idx = self.renderer.ask_choice(choices)
                # record user choice
                self.choice_trace.append(int(sel_idx))
                try:
                    self.events.emit("choice.select", index=int(sel_idx), text=str(choices[sel_idx][0]))
                except Exception:
                    pass
            elif self._replay_choices is not None and choices:
                # consume recorded choice for deterministic replay
                if self._replay_choices:
                    try:
                        sel_idx = int(self._replay_choices.pop(0))
                    except Exception:
                        sel_idx = 0
                else:
                    sel_idx = 0
            target = choices[sel_idx][1] if choices else None
            if target and target in self.program.labels:
                self.ip = self.program.labels[target]
            else:
                # if no valid target, just skip the choice block
                if self.strict and target:
                    raise ScriptError(f"Unknown target label: {target}", p.get("line"))
                self.ip = i - 1  # -1 because step() will +1
        else:
            self.renderer.command(k, str(p))
        # SCRIPT op (safe_exec block)
        if k == "script":
            try:
                code = p.get("code") or ""
                safe_exec(str(code), self.vars)
            except Exception:
                if self.strict:
                    raise
            return

    def _execute_command(self, name: str, args: str, line: Optional[int]) -> None:
        parts = args.split()
        # Variable system
        if name.upper() == "SET":
            # Syntax: SET var = expr
            try:
                if '=' not in args:
                    if self.strict:
                        raise ScriptError("SET missing '='", line)
                    return
                left, right = args.split('=', 1)
                var = left.strip()
                expr = right.strip()
                val = safe_eval(expr, self.vars)
                self.vars[var] = val
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"SET error: {e}", line)
            return
        if name.upper() == "IF":
            # Syntax: IF expr -> label
            try:
                if '->' not in args:
                    if self.strict:
                        raise ScriptError("IF missing '->'", line)
                    return
                cond, target = args.split('->', 1)
                cond = cond.strip()
                target = target.strip()
                ok = bool(safe_eval(cond, self.vars))
                # begin conditional chain
                self._cond_chain_active = True
                self._cond_chain_taken = False
                if ok and self.program and target in self.program.labels:
                    # jump by setting ip to label index - 1 (step() will +1)
                    self.ip = self.program.labels[target] - 1
                    self._cond_chain_taken = True
                elif ok and self.strict:
                    raise ScriptError(f"Unknown target label: {target}", line)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"IF error: {e}", line)
            return
        if name.upper() == "ELSEIF":
            # Syntax: ELSEIF expr -> label (valid only after IF)
            try:
                if not self._cond_chain_active or self._cond_chain_taken:
                    return
                if '->' not in args:
                    if self.strict:
                        raise ScriptError("ELSEIF missing '->'", line)
                    return
                cond, target = args.split('->', 1)
                cond = cond.strip()
                target = target.strip()
                ok = bool(safe_eval(cond, self.vars))
                if ok and self.program and target in self.program.labels:
                    self.ip = self.program.labels[target] - 1
                    self._cond_chain_taken = True
                elif ok and self.strict:
                    raise ScriptError(f"Unknown target label: {target}", line)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"ELSEIF error: {e}", line)
            return
        if name.upper() == "ELSE":
            # Syntax: ELSE -> label (valid only after IF/ELSEIF)
            try:
                if not self._cond_chain_active or self._cond_chain_taken:
                    return
                target = args.split('->', 1)[1].strip() if '->' in args else args.strip()
                if target and self.program and target in self.program.labels:
                    self.ip = self.program.labels[target] - 1
                    self._cond_chain_taken = True
                elif target and self.strict:
                    raise ScriptError(f"Unknown target label: {target}", line)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"ELSE error: {e}", line)
            return
        if name.upper() == "SWITCH":
            # Syntax: SWITCH expr
            try:
                expr = args.strip()
                self._switch_value = safe_eval(expr, self.vars)
                self._switch_active = True
                self._switch_matched = False
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"SWITCH error: {e}", line)
            return
        if name.upper() == "CASE":
            # Syntax: CASE value -> label (valid only after SWITCH)
            try:
                if not self._switch_active or self._switch_matched:
                    return
                if '->' not in args:
                    if self.strict:
                        raise ScriptError("CASE missing '->'", line)
                    return
                val_s, target = args.split('->', 1)
                val = safe_eval(val_s.strip(), self.vars)
                target = target.strip()
                if val == self._switch_value:
                    if target and self.program and target in self.program.labels:
                        self.ip = self.program.labels[target] - 1
                        self._switch_matched = True
                    elif target and self.strict:
                        raise ScriptError(f"Unknown target label: {target}", line)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"CASE error: {e}", line)
            return
        if name.upper() == "DEFAULT":
            # Syntax: DEFAULT -> label (valid only after SWITCH)
            try:
                if not self._switch_active or self._switch_matched:
                    return
                target = args.split('->', 1)[1].strip() if '->' in args else args.strip()
                if target and self.program and target in self.program.labels:
                    self.ip = self.program.labels[target] - 1
                    self._switch_matched = True
                elif target and self.strict:
                    raise ScriptError(f"Unknown target label: {target}", line)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"DEFAULT error: {e}", line)
            return
        if name.upper() == "ENDSWITCH":
            # Syntax: ENDSWITCH
            self._switch_active = False
            self._switch_value = None
            self._switch_matched = False
            return
        if name.upper() == "GOTO":
            # Syntax: GOTO label
            target = parts[0] if parts else None
            if target and self.program and target in self.program.labels:
                self.ip = self.program.labels[target] - 1
            elif self.strict and target:
                raise ScriptError(f"Unknown target label: {target}", line)
            return
        if name.upper() == "SCRIPT":
            # Syntax: SCRIPT <inline...> or multiline via parser support
            # Execute a tiny safe subset of Python statements against self.vars
            try:
                safe_exec(args, self.vars)
            except Exception as e:
                if self.strict:
                    raise ScriptError(f"SCRIPT error: {e}", line)
            return
        if name.upper() == "CALL":
            # Syntax: CALL label
            target = parts[0] if parts else None
            if target and self.program and target in self.program.labels:
                # push current ip as return address
                self.call_stack.append(self.ip)
                self.ip = self.program.labels[target] - 1
            elif self.strict and target:
                raise ScriptError(f"Unknown target label: {target}", line)
            return
        if name.upper() == "RETURN":
            # Syntax: RETURN
            if not self.call_stack:
                if self.strict:
                    raise ScriptError("RETURN with empty call stack", line)
                return
            ret = self.call_stack.pop()
            # step() will +1 after this instruction; set ip to ret to resume next op
            self.ip = ret
            return
        if name.upper() == "WAIT":
            # Syntax: WAIT <ms>
            try:
                ms = int(parts[0]) if parts else 0
            except Exception:
                ms = 0
            if ms > 0:
                try:
                    if hasattr(self.renderer, "wait_ms") and callable(getattr(self.renderer, "wait_ms")):
                        self.renderer.wait_ms(ms)  # type: ignore[attr-defined]
                    else:
                        # Fallback: sleep without UI pumping
                        time.sleep(ms / 1000.0)
                except Exception:
                    pass
            return
        if name.upper() == "AUTO":
            # Syntax: AUTO on|off|toggle
            mode = (parts[0].lower() if parts else "toggle")
            try:
                if hasattr(self.renderer, "set_auto_mode") and callable(getattr(self.renderer, "set_auto_mode")):
                    if mode == "on":
                        self.renderer.set_auto_mode(True)  # type: ignore[attr-defined]
                    elif mode == "off":
                        self.renderer.set_auto_mode(False)  # type: ignore[attr-defined]
                    else:
                        self.renderer.set_auto_mode(not bool(getattr(self.renderer, "_auto_mode", False)))  # type: ignore[attr-defined]
                else:
                    # Best effort direct toggle
                    cur = bool(getattr(self.renderer, "_auto_mode", False))
                    if mode == "on":
                        setattr(self.renderer, "_auto_mode", True)
                    elif mode == "off":
                        setattr(self.renderer, "_auto_mode", False)
                    else:
                        setattr(self.renderer, "_auto_mode", not cur)
            except Exception:
                pass
            return
        if name.upper() == "TITLE":
            # Syntax: TITLE ["标题"] [bg_path]
            # Shows a title menu; returns only when user chooses Start (continue), or quits.
            raw = args.strip()
            title = None
            bgp = None
            try:
                if raw.startswith('"') and '"' in raw[1:]:
                    i = raw.find('"', 1)
                    j = raw.rfind('"')
                    if j > 0 and j > i:
                        title = raw[1:j]
                        rest = raw[j+1:].strip()
                    else:
                        title = raw.strip('"')
                        rest = ''
                elif (raw.startswith('“') and '”' in raw) or (raw.startswith('「') and '」' in raw):
                    if raw.startswith('“'):
                        close = raw.rfind('”')
                        title = raw[1:close] if close > 0 else raw.strip('“”')
                        rest = raw[close+1:].strip() if close > 0 else ''
                    else:
                        close = raw.rfind('」')
                        title = raw[1:close] if close > 0 else raw.strip('「」')
                        rest = raw[close+1:].strip() if close > 0 else ''
                else:
                    rest = raw
                parts2 = rest.split()
                if parts2:
                    bgp = parts2[0]
            except Exception:
                pass
            # Loop menu until start or quit
            while True:
                try:
                    choice = None
                    if hasattr(self.renderer, 'show_title_menu'):
                        # type: ignore[attr-defined]
                        choice = self.renderer.show_title_menu(title, bgp)
                except Exception:
                    choice = 'start'
                if not choice or choice == 'start':
                    break
                if choice == 'load':
                    try:
                        if hasattr(self.renderer, 'open_slots_menu'):
                            self.renderer.open_slots_menu('load')  # type: ignore[attr-defined]
                    except Exception:
                        pass
                elif choice == 'settings':
                    try:
                        if hasattr(self.renderer, 'open_settings_menu'):
                            self.renderer.open_settings_menu()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                elif choice == 'gallery':
                    try:
                        if hasattr(self.renderer, 'open_gallery'):
                            self.renderer.open_gallery()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                elif choice == 'quit':
                    try:
                        if hasattr(self.renderer, 'quit'):
                            self.renderer.quit()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    raise SystemExit
            return
        if name.upper() == "BG":
            path = None if not parts or parts[0] == "None" else parts[0]
            self.renderer.set_background(path)
            return
        if name.upper() == "BGM":
            path = None if not parts or parts[0] == "None" else parts[0]
            vol = float(parts[1]) if len(parts) > 1 else None
            self.renderer.play_bgm(path, vol)
            return
        if name.upper() == "SE":
            if not parts:
                return
            vol = float(parts[1]) if len(parts) > 1 else None
            self.renderer.play_se(parts[0], vol)
            return
        if name.upper() == "OUTFIT":
            # Syntax: OUTFIT <actor> <folder|None>
            if len(parts) >= 1:
                actor = parts[0]
                folder = parts[1] if len(parts) > 1 else None
                try:
                    # route to renderer via generic command (pygame handles it)
                    self.renderer.command("OUTFIT", f"{actor} {folder or ''}".strip())
                except Exception:
                    pass
            return
        if name.upper() == "ACTION":
            # Syntax: ACTION <actor> <name|None>
            if len(parts) >= 1:
                actor = parts[0]
                act = parts[1] if len(parts) > 1 else None
                try:
                    self.renderer.command("ACTION", f"{actor} {act or ''}".strip())
                except Exception:
                    pass
            return
        if name.upper() == "HIDE":
            # Syntax: HIDE <actor>
            if len(parts) >= 1:
                actor = parts[0]
                try:
                    self.renderer.command("HIDE", actor)
                except Exception:
                    pass
            return
        if name.upper() == "CLEAR_STAGE":
            # Syntax: CLEAR_STAGE (remove all characters)
            try:
                self.renderer.command("CLEAR_STAGE", "")
            except Exception:
                pass
            return
        if name.upper() == "VOICE":
            # Syntax: VOICE <path|None> [volume]
            path = None if not parts or parts[0].lower() == "none" else parts[0]
            vol = float(parts[1]) if len(parts) > 1 else None
            try:
                if hasattr(self.renderer, "prepare_voice"):
                    # type: ignore[attr-defined]
                    self.renderer.prepare_voice(path, vol)
            except Exception:
                pass
            return
        # Fallback
        if self.strict:
            raise ScriptError(f"Unknown command: {name}", line)
        self.renderer.command(name, args)

    # --- quick save/load ---
    def quicksave(self, save_path: Path | None = None) -> bool:
        try:
            if not self.program:
                return False
            # try to infer current label name from last label entered
            try:
                cur_label = getattr(self.renderer, "_current_label", None)
            except Exception:
                cur_label = None
            # collect renderer snapshot if available
            snapshot = None
            try:
                if hasattr(self.renderer, "get_snapshot") and callable(getattr(self.renderer, "get_snapshot")):
                    snapshot = self.renderer.get_snapshot()  # type: ignore[attr-defined]
            except Exception:
                snapshot = None
            # compute script content hash for mismatch detection on load
            try:
                script_hash = None
                if self.script_path and Path(self.script_path).exists():
                    data = Path(self.script_path).read_bytes()
                    script_hash = hashlib.sha256(data).hexdigest()
            except Exception:
                script_hash = None
            payload = {
                "script": str(self.script_path) if self.script_path else None,
                "ip": self.ip,
                "ts": datetime.now().isoformat(timespec="seconds"),
                # include choice path for deterministic replay
                "choices": list(self.choice_trace),
                # include variable store
                "vars": self.vars,
                "label": cur_label,
                # optional snapshot for fast restore
                "snapshot": snapshot,
                # textbox view state
                "textbox": {"view_idx": getattr(self.textbox, "view_idx", -1)},
                # script hash for mismatch detection
                "script_hash": script_hash,
                "version": 2,
            }
            # Prefer injected save store; fall back to legacy file path when explicit path provided
            if self._save_store and save_path is None:
                return bool(self._save_store.write_quick(payload))
            else:
                sp = save_path or (self.get_save_dir() / "quick.json")
                sp.parent.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                return True
        except Exception:
            return False

    def quickload(self, save_path: Path | None = None) -> bool:
        try:
            # Prefer injected save store; fall back to legacy file
            if self._save_store and save_path is None:
                data = self._save_store.read_quick()
                if not data:
                    return False
            else:
                sp = save_path or (self.get_save_dir() / "quick.json")
                if not sp.exists():
                    return False
                data = json.loads(sp.read_text(encoding="utf-8"))
            script = data.get("script")
            ip = int(data.get("ip", 0))
            choices = data.get("choices") or []
            snapshot = data.get("snapshot") or None
            saved_hash = data.get("script_hash")
            if not script:
                return False
            p = Path(script)
            if not p.exists():
                # allow relative to current cwd
                p = Path(str(script))
            # reload program
            source = p.read_text(encoding="utf-8")
            prog = parse_script(source)
            self.load(prog)
            self.script_path = p
            # Check if script changed; if changed, do not trust snapshot
            changed = False
            try:
                cur_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                changed = bool(saved_hash) and saved_hash != cur_hash
            except Exception:
                changed = False
            # Apply snapshot if available and script unchanged, else fast-replay deterministically to rebuild state
            try:
                if (not changed) and snapshot and hasattr(self.renderer, "apply_snapshot") and callable(getattr(self.renderer, "apply_snapshot")):
                    # reset renderer to a clean state first
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                    self.renderer.apply_snapshot(snapshot)  # type: ignore[attr-defined]
                    # adopt saved variable store and set ip so the saved line will be executed next
                    try:
                        self.vars = dict(data.get("vars") or {})
                    except Exception:
                        self.vars = {}
                    self.ip = max(0, int(ip) - 1)
                else:
                    # Reset renderer state then fast-replay deterministically
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                    self._replay_choices = list(choices)
                    # Rewind target by one so the saved line will be executed next
                    target = max(0, min(max(0, ip - 1), (len(self.program.ops) - 1) if self.program else 0))
                    self._fast_replay_to(target)
                if changed:
                    try:
                        self.renderer.show_banner("脚本已变更，使用快速重放恢复状态", (200,140,40))
                    except Exception:
                        pass
            except Exception:
                # Snapshot failed -> fall back to fast replay
                try:
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                except Exception:
                    pass
                self._replay_choices = list(choices)
                target = max(0, min(max(0, ip - 1), (len(self.program.ops) - 1) if self.program else 0))
                self._fast_replay_to(target)
            # adopt saved trace so future saves continue from here
            self.choice_trace = list(choices)
            # restore textbox view state
            try:
                tb = data.get("textbox") or {}
                vi = int(tb.get("view_idx", -1))
                self.textbox.view_idx = vi
            except Exception:
                pass
            # line trace rebuilt during replay; keep as-is
            self._replay_choices = None
            return True
        except Exception:
            return False

    # --- multi-slot save/load ---
    def _slot_json_path(self, slot: int, base: Path | None = None) -> Path:
        b = base or self.get_save_dir()
        return b / f"slot_{slot:02d}.json"

    def save_to_slot(self, slot: int, base: Path | None = None) -> bool:
        try:
            if not self.program:
                return False
            try:
                cur_label = getattr(self.renderer, "_current_label", None)
            except Exception:
                cur_label = None
            snapshot = None
            try:
                if hasattr(self.renderer, "get_snapshot") and callable(getattr(self.renderer, "get_snapshot")):
                    snapshot = self.renderer.get_snapshot()  # type: ignore[attr-defined]
            except Exception:
                snapshot = None
            try:
                script_hash = None
                if self.script_path and Path(self.script_path).exists():
                    data = Path(self.script_path).read_bytes()
                    script_hash = hashlib.sha256(data).hexdigest()
            except Exception:
                script_hash = None
            payload = {
                "script": str(self.script_path) if self.script_path else None,
                "ip": self.ip,
                "ts": datetime.now().isoformat(timespec="seconds"),
                "choices": list(self.choice_trace),
                "vars": self.vars,
                "label": cur_label,
                "snapshot": snapshot,
                "textbox": {"view_idx": getattr(self.textbox, "view_idx", -1)},
                "script_hash": script_hash,
                "version": 2,
            }
            if self._save_store and base is None:
                return bool(self._save_store.write_slot(int(slot), payload))
            else:
                sp = self._slot_json_path(int(slot), base)
                sp.parent.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                return True
        except Exception:
            return False

    def load_from_slot(self, slot: int, base: Path | None = None) -> bool:
        try:
            if self._save_store and base is None:
                data = self._save_store.read_slot(int(slot))
                if not data:
                    return False
            else:
                sp = self._slot_json_path(int(slot), base)
                if not sp.exists():
                    return False
                data = json.loads(sp.read_text(encoding="utf-8"))
            script = data.get("script")
            ip = int(data.get("ip", 0))
            choices = data.get("choices") or []
            snapshot = data.get("snapshot") or None
            saved_hash = data.get("script_hash")
            if not script:
                return False
            p = Path(script)
            if not p.exists():
                p = Path(str(script))
            source = p.read_text(encoding="utf-8")
            prog = parse_script(source)
            self.load(prog)
            self.script_path = p
            # Apply snapshot if available and script unchanged; otherwise fast replay
            try:
                changed = False
                try:
                    cur_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                    changed = bool(saved_hash) and saved_hash != cur_hash
                except Exception:
                    changed = False
                if (not changed) and snapshot and hasattr(self.renderer, "apply_snapshot") and callable(getattr(self.renderer, "apply_snapshot")):
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                    self.renderer.apply_snapshot(snapshot)  # type: ignore[attr-defined]
                    try:
                        self.vars = dict(data.get("vars") or {})
                    except Exception:
                        self.vars = {}
                    self.ip = max(0, int(ip) - 1)
                else:
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                    self._replay_choices = list(choices)
                    target = max(0, min(max(0, ip - 1), (len(self.program.ops) - 1) if self.program else 0))
                    self._fast_replay_to(target)
                if changed:
                    try:
                        self.renderer.show_banner("脚本已变更，使用快速重放恢复状态", (200,140,40))
                    except Exception:
                        pass
            except Exception:
                try:
                    if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                        self.renderer.reset_state()  # type: ignore[attr-defined]
                except Exception:
                    pass
                self._replay_choices = list(choices)
                target = max(0, min(max(0, ip - 1), (len(self.program.ops) - 1) if self.program else 0))
                self._fast_replay_to(target)
            self.choice_trace = list(choices)
            try:
                tb = data.get("textbox") or {}
                vi = int(tb.get("view_idx", -1))
                self.textbox.view_idx = vi
            except Exception:
                pass
            # line trace rebuilt during replay; keep as-is
            self._replay_choices = None
            return True
        except Exception:
            return False

    # --- helpers ---
    def _fast_replay_to(self, target_ip: int) -> None:
        """Rebuild renderer state up to target_ip without interactive waits.

        Temporarily disables interactive waiting and typing effects if supported by renderer.
        """
        target = max(0, target_ip)
        # temporarily disable interactive waits
        was_interactive = self.interactive
        self.interactive = False
        # hint renderer to speed up (optional)
        try:
            if hasattr(self.renderer, "begin_fast_replay") and callable(getattr(self.renderer, "begin_fast_replay")):
                self.renderer.begin_fast_replay()  # type: ignore[attr-defined]
        except Exception:
            pass
        self.ip = 0
        # Clear variable store; during reconstruction variables will be re-applied by SET ops
        try:
            self.vars = {}
        except Exception:
            pass
        # reset line trace as we'll rebuild deterministically
        try:
            self.line_ip_trace = []
        except Exception:
            pass
        while self.ip < target:
            try:
                if not self.step():
                    break
            except Exception:
                # ignore errors during reconstruction
                break
        # end fast replay
        try:
            if hasattr(self.renderer, "end_fast_replay") and callable(getattr(self.renderer, "end_fast_replay")):
                self.renderer.end_fast_replay()  # type: ignore[attr-defined]
        except Exception:
            pass
        self.interactive = was_interactive

    # --- back/rewind one visible line ---
    def back_one_line(self) -> bool:
        try:
            if not self.program:
                return False
            if len(self.line_ip_trace) < 2:
                return False
            prev_ip = int(self.line_ip_trace[-2])
            # Reset renderer state then fast-replay up to just before prev line,
            # so that prev line will be executed next in interactive flow.
            try:
                if hasattr(self.renderer, "reset_state") and callable(getattr(self.renderer, "reset_state")):
                    self.renderer.reset_state()  # type: ignore[attr-defined]
            except Exception:
                pass
            # Reset variables; will be rebuilt during fast replay
            try:
                self.vars = {}
            except Exception:
                pass
            # Feed choices taken so far; consume as needed
            original_choices = list(self.choice_trace)
            self._replay_choices = list(original_choices)
            # target to rebuild state so next step executes prev_ip
            target = max(0, prev_ip)
            self._fast_replay_to(target)
            # Trim choice_trace to the number consumed during replay
            try:
                consumed = max(0, len(original_choices) - len(self._replay_choices or []))
                self.choice_trace = original_choices[:consumed]
            except Exception:
                pass
            self._replay_choices = None
            return True
        except Exception:
            return False
