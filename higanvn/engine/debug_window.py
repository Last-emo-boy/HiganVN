from __future__ import annotations

import json
import threading
from typing import Any, Callable, Dict, List, Optional, cast

try:
    import tkinter as tk_rt
    from tkinter import ttk as ttk_rt
except Exception:  # pragma: no cover - tkinter may be unavailable
    tk_rt = None
    ttk_rt = None

# Provide safe module aliases (tk/ttk). When tkinter isn't available, use stubs
if tk_rt is None or ttk_rt is None:
    class _Stub:
        def __getattr__(self, name):
            return self

        def __call__(self, *args, **kwargs):
            return self

    tk = cast(Any, _Stub())
    ttk = cast(Any, _Stub())
else:
    tk = cast(Any, tk_rt)
    ttk = cast(Any, ttk_rt)


class DebugWindow:
    """Detached debug window using Tkinter with a tabbed, data-driven UI.

    Tabs: Overview, Characters, Animator, Backlog, Voice, Flow, Raw JSON
    Controls: Provider select, Auto refresh, Interval, Refresh, Copy JSON
    """

    def __init__(
        self,
        data_provider: Callable[[], Dict[str, object]],
        *,
        refresh_ms: int = 300,
        actions: Optional[Dict[str, Callable[[], object]]] = None,
        prefs: Optional[Dict[str, object]] = None,
        on_prefs_save: Optional[Callable[[Dict[str, object]], None]] = None,
    ) -> None:
        self._provider = data_provider
        self._refresh_ms = max(100, int(refresh_ms))
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._root = None
        # prefs
        self._prefs = dict(prefs or {})
        self._on_prefs_save = on_prefs_save
        # tk variables/widgets (created in UI thread)
        self._provider_var = None
        self._auto_var = None
        self._interval_var = None
        self._status_var = None
        self._provider_combo = None
        self._notebook = None
        self._tv_overview = None
        self._tv_chars = None
        self._tv_anim = None
        self._tv_backlog = None
        self._tv_voice = None
        self._tv_flow = None
        self._txt_raw = None
        self._filter_var = None
        self._filter_entry = None
        self._theme_var = None
        self._ontop_var = None
        self._actions = actions or {}
        self._actions_frame = None
        # state/cache
        self._provider_names: List[str] = []
        self._data_cache: Dict[str, object] = {}
        self._last_refresh_ts: Optional[float] = None
        self._sort_state: Dict[int, tuple[str, bool]] = {}  # id(tv) -> (column, reverse)
        # dynamic tabs state
        self._tab_frames = {}
        self._current_tab_keys = []

    # lifecycle
    def open(self) -> None:
        if tk_rt is None or not hasattr(tk_rt, "Tk"):
            return
        if self.is_open():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="DebugWindow", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        try:
            if self._root:
                self._root.after(0, self._root.destroy)
        except Exception:
            pass
        self._root = None

    def toggle(self) -> None:
        if self.is_open():
            self.close()
        else:
            self.open()

    def is_open(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # thread entry
    def _run(self) -> None:
        try:
            self._root = tk.Tk()
        except Exception:
            return
        self._root.title("HiganVN Debug")
        self._root.geometry("960x720")
        self._root.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self._install_style()
        except Exception:
            pass
        self._build_ui()
        try:
            # keyboard shortcuts
            self._root.bind("<F5>", lambda e: self._refresh_once())
            self._root.bind("<Control-f>", lambda e: (self._filter_entry.focus_set() if self._filter_entry else None))
            self._root.bind("<Control-s>", lambda e: self._save_json())
            self._root.bind("<Control-c>", lambda e: self._copy_selection())
        except Exception:
            pass
        self._refresh_once()
        self._schedule_refresh()
        try:
            self._root.mainloop()
        except Exception:
            pass
        finally:
            self._root = None

    # UI
    def _build_ui(self) -> None:
        bar = ttk.Frame(self._root)
        bar.pack(side="top", fill="x")

        ttk.Label(bar, text="Provider:").pack(side="left", padx=(8, 2), pady=6)
        self._provider_var = tk.StringVar(value="renderer")
        self._provider_combo = ttk.Combobox(bar, textvariable=self._provider_var, width=22, state="readonly")
        self._provider_combo.pack(side="left", padx=(0, 8))
        self._provider_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_once())

        ttk.Button(bar, text="Refresh", command=self._refresh_once).pack(side="left", padx=4)

        self._auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Auto", variable=self._auto_var, command=self._on_auto_changed).pack(side="left", padx=(10, 2))

        ttk.Label(bar, text="Interval(ms):").pack(side="left", padx=(10, 2))
        # initial interval from prefs if provided
        try:
            raw_iv = self._prefs.get("interval_ms", self._refresh_ms)
            pref_iv = int(str(raw_iv))
            self._refresh_ms = max(100, pref_iv)
        except Exception:
            pass
        self._interval_var = tk.IntVar(value=self._refresh_ms)
        Spinbox = getattr(ttk, "Spinbox", None)
        spn = Spinbox(bar, from_=100, to=5000, increment=100, textvariable=self._interval_var, width=6) if Spinbox else tk.Spinbox(bar, from_=100, to=5000, increment=100, textvariable=self._interval_var, width=6)
        spn.pack(side="left")
        # persist interval on change
        try:
            self._interval_var.trace_add("write", lambda *_: self._persist_prefs())
        except Exception:
            pass

        # Theme & OnTop
        # theme from prefs
        init_theme = str(self._prefs.get("theme", "Dark"))
        self._theme_var = tk.StringVar(value=init_theme)
        ttk.Label(bar, text="Theme:").pack(side="left", padx=(10, 2))
        cmb_theme = ttk.Combobox(bar, textvariable=self._theme_var, width=8, state="readonly", values=["Dark", "Light"])
        cmb_theme.pack(side="left")
        cmb_theme.bind("<<ComboboxSelected>>", lambda e: (self._apply_theme(self._theme_var.get() if self._theme_var else "Dark"), self._persist_prefs()))
        self._ontop_var = tk.BooleanVar(value=bool(self._prefs.get("ontop", False)))
        ttk.Checkbutton(bar, text="Always on top", variable=self._ontop_var, command=lambda: (self._apply_ontop(), self._persist_prefs())).pack(side="left", padx=(10, 2))

        self._status_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self._status_var).pack(side="left", padx=(12, 0))

        ttk.Button(bar, text="Export CSV", command=self._export_csv_current).pack(side="right", padx=(8, 2))
        ttk.Button(bar, text="Save JSON", command=self._save_json).pack(side="right", padx=(8, 2))
        ttk.Button(bar, text="Copy JSON", command=self._copy_json).pack(side="right", padx=(2, 8))

        # Filter row
        filter_bar = ttk.Frame(self._root)
        filter_bar.pack(side="top", fill="x")
        ttk.Label(filter_bar, text="Filter:").pack(side="left", padx=(8, 2), pady=(0, 6))
        self._filter_var = tk.StringVar(value="")
        self._filter_entry = ttk.Entry(filter_bar, textvariable=self._filter_var, width=40)
        self._filter_entry.pack(side="left", padx=(0, 8))
        try:
            self._filter_var.trace_add("write", lambda *_: self._refresh_once())
        except Exception:
            # older tkinter
            self._filter_entry.bind("<KeyRelease>", lambda e: self._refresh_once())
        # Notebook
        self._notebook = ttk.Notebook(self._root)
        self._notebook.pack(side="top", fill="both", expand=True)

        # Build frames/widgets once; add to notebook dynamically per provider
        self._tab_frames = {}

        frm_over = ttk.Frame(self._notebook)
        self._tv_overview = self._make_kv_tree(frm_over)
        self._tab_frames["overview"] = (frm_over, "Overview")

        frm_chars = ttk.Frame(self._notebook)
        self._tv_chars = self._make_chars_tree(frm_chars)
        self._tab_frames["characters"] = (frm_chars, "Characters")

        frm_anim = ttk.Frame(self._notebook)
        self._tv_anim = self._make_kv_tree(frm_anim)
        self._tab_frames["animator"] = (frm_anim, "Animator")

        frm_back = ttk.Frame(self._notebook)
        self._tv_backlog = self._make_kv_tree(frm_back)
        self._tab_frames["backlog"] = (frm_back, "Backlog")

        frm_voice = ttk.Frame(self._notebook)
        self._tv_voice = self._make_kv_tree(frm_voice)
        self._tab_frames["voice"] = (frm_voice, "Voice")

        frm_flow = ttk.Frame(self._notebook)
        self._tv_flow = self._make_kv_tree(frm_flow)
        self._tab_frames["flow"] = (frm_flow, "Flow")

        frm_raw = ttk.Frame(self._notebook)
        self._txt_raw = tk.Text(frm_raw, wrap="none", font=("Consolas", 10))
        self._txt_raw.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm_raw, orient="vertical", command=self._txt_raw.yview)
        yscroll.pack(side="right", fill="y")
        self._txt_raw.configure(yscrollcommand=yscroll.set)
        self._tab_frames["raw"] = (frm_raw, "Raw JSON")

        # Actions tab (if any actions provided)
        self._actions_frame = None
        if self._actions:
            frm_actions = ttk.Frame(self._notebook)
            grid = ttk.Frame(frm_actions)
            grid.pack(side="top", fill="x", padx=12, pady=12)
            row, col = 0, 0
            for name in sorted(self._actions.keys()):
                try:
                    btn = ttk.Button(grid, text=name, command=lambda n=name: self._run_action(n))
                    btn.grid(row=row, column=col, padx=6, pady=6, sticky="w")
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
                except Exception:
                    continue
            self._actions_frame = frm_actions

        # initial tabs based on provider
        try:
            prov = self._provider_var.get() if self._provider_var else "renderer"
        except Exception:
            prov = "renderer"
        self._current_tab_keys = []  # type: List[str]
        self._rebuild_tabs(self._desired_tabs_for_provider(prov))
        # apply initial theme/ontop
        try:
            self._apply_theme(self._theme_var.get() if self._theme_var else "Dark")
            self._apply_ontop()
        except Exception:
            pass

    def _persist_prefs(self) -> None:
        try:
            prefs = {
                "theme": (self._theme_var.get() if self._theme_var else "Dark"),
                "ontop": bool(self._ontop_var.get() if self._ontop_var else False),
                "interval_ms": int(self._interval_var.get() if self._interval_var else self._refresh_ms),
            }
            if callable(self._on_prefs_save):
                try:
                    self._on_prefs_save(prefs)
                except Exception:
                    pass
            # also keep local copy
            self._prefs.update(prefs)
        except Exception:
            pass

    def _desired_tabs_for_provider(self, name: str) -> List[str]:
        n = str(name or "").lower()
        mapping = {
            "renderer": ["overview", "characters", "animator", "backlog", "voice", "flow", "raw"],
            "system": ["overview", "raw"],
            "audio": ["overview", "raw"],
            "config": ["overview", "raw"],
            "slots": ["overview", "raw"],
            "scene": ["overview", "characters", "flow", "raw"],
        }
        return mapping.get(n, ["overview", "raw"])

    def _rebuild_tabs(self, keys: List[str]) -> None:
        if not self._notebook:
            return
        try:
            # remove all tabs first
            for tab in list(self._notebook.tabs()):
                try:
                    self._notebook.forget(tab)
                except Exception:
                    continue
            # add requested tabs
            for k in keys:
                item = self._tab_frames.get(k)
                if not item:
                    continue
                frame, title = item
                try:
                    self._notebook.add(frame, text=title)
                except Exception:
                    pass
            # actions tab at end
            if self._actions_frame is not None:
                try:
                    self._notebook.add(self._actions_frame, text="Actions")
                except Exception:
                    pass
            self._current_tab_keys = list(keys)
        except Exception:
            pass

    def _make_kv_tree(self, parent):
        frm = ttk.Frame(parent)
        frm.pack(fill="both", expand=True)
        cols = ("Key", "Value")
        tv = ttk.Treeview(frm, columns=cols, show="headings")
        for c in cols:
            tv.heading(c, text=c, command=lambda col=c, _tv=tv: self._sort_treeview(_tv, col))
            tv.column(c, width=260 if c == "Key" else 520, anchor="w", stretch=True)
        tv.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        yscroll.pack(side="right", fill="y")
        tv.configure(yscrollcommand=yscroll.set)
        self._install_tree_tags(tv)
        return tv

    def _make_chars_tree(self, parent):
        frm = ttk.Frame(parent)
        frm.pack(fill="both", expand=True)
        cols = ("Name", "Active", "Outfit", "Action", "Rect", "Center")
        tv = ttk.Treeview(frm, columns=cols, show="headings")
        for c in cols:
            tv.heading(c, text=c, command=lambda col=c, _tv=tv: self._sort_treeview(_tv, col))
        tv.column("Name", width=180, anchor="w", stretch=True)
        tv.column("Active", width=60, anchor="center", stretch=False)
        tv.column("Outfit", width=140, anchor="w", stretch=True)
        tv.column("Action", width=70, anchor="center", stretch=False)
        tv.column("Rect", width=200, anchor="w", stretch=True)
        tv.column("Center", width=140, anchor="w", stretch=True)
        tv.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        yscroll.pack(side="right", fill="y")
        tv.configure(yscrollcommand=yscroll.set)
        self._install_tree_tags(tv)
        # Right-click copy
        try:
            tv.bind("<Button-3>", lambda e, _tv=tv: self._copy_selection_from(_tv))
        except Exception:
            pass
        return tv

    # actions
    def _on_auto_changed(self) -> None:
        if self._root and not self._stop.is_set():
            self._root.after(0, self._schedule_refresh)

    def _schedule_refresh(self) -> None:
        if not self._root or self._stop.is_set():
            return
        if self._auto_var and self._auto_var.get():
            self._refresh_once()
            try:
                iv = max(100, int(self._interval_var.get())) if self._interval_var else self._refresh_ms
            except Exception:
                iv = self._refresh_ms
            try:
                self._root.after(iv, self._schedule_refresh)
            except Exception:
                pass

    def _copy_json(self) -> None:
        if not self._root:
            return
        try:
            js = self._txt_raw.get("1.0", "end") if self._txt_raw else json.dumps(self._data_cache, ensure_ascii=False, indent=2)
            self._root.clipboard_clear()
            self._root.clipboard_append(js)
        except Exception:
            pass

    def _copy_selection(self) -> None:
        # Copy from current tab's primary treeview if possible, else fallback to JSON
        cur = None
        cur = self._get_current_treeview()
        if cur is None:
            return self._copy_json()
        self._copy_selection_from(cur)

    def _copy_selection_from(self, tv) -> None:
        try:
            sel = tv.selection()
            if not sel:
                return self._copy_json()
            lines: List[str] = []
            cols = tv.cget("columns") or []
            for i in sel:
                vals = tv.item(i, "values")
                if isinstance(cols, (list, tuple)) and len(cols) == 2:
                    lines.append(f"{vals[0]}: {vals[1]}")
                else:
                    lines.append("\t".join(str(v) for v in vals))
            text = "\n".join(lines)
            if self._root and hasattr(self._root, "clipboard_clear") and hasattr(self._root, "clipboard_append"):
                self._root.clipboard_clear()
                self._root.clipboard_append(text)
        except Exception:
            pass

    def _save_json(self) -> None:
        if not self._root:
            return
        try:
            from tkinter import filedialog
        except Exception:
            return
        try:
            payload = self._current_payload()
            js = json.dumps(payload, ensure_ascii=False, indent=2)
            path = filedialog.asksaveasfilename(title="Save JSON Snapshot", defaultextension=".json", filetypes=[("JSON","*.json"), ("All Files","*.*")])
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(js)
        except Exception:
            pass

    def _export_csv_current(self) -> None:
        if not self._root:
            return
        try:
            from tkinter import filedialog
        except Exception:
            return
        # pick a treeview based on current tab
        tv = self._get_current_treeview()
        if tv is None:
            return
        try:
            path = filedialog.asksaveasfilename(title="Export CSV", defaultextension=".csv", filetypes=[("CSV","*.csv"), ("All Files","*.*")])
            if not path:
                return
            import csv
            cols = list(tv.cget("columns") or [])
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if cols:
                    writer.writerow(cols)
                for iid in tv.get_children(""):
                    vals = tv.item(iid, "values")
                    writer.writerow(list(vals))
        except Exception:
            pass

    def _get_current_treeview(self):
        try:
            if not self._notebook:
                return None
            cur_tab = self._notebook.select()
            if not cur_tab:
                return None
            # find first Treeview child in the selected tab/frame
            # Tk returns tab id; use nametowidget to access frame
            frame = self._root.nametowidget(cur_tab) if (self._root and hasattr(self._root, 'nametowidget')) else None
            if not frame:
                return None
            # breadth-first search for ttk.Treeview
            q = [frame]
            while q:
                node = q.pop(0)
                try:
                    for child in list(node.winfo_children()):
                        try:
                            if str(child.winfo_class()).lower() == 'treeview':
                                return child
                        except Exception:
                            pass
                        q.append(child)
                except Exception:
                    break
        except Exception:
            return None
        return None

    # data render
    def _refresh_once(self) -> None:
        if not self._root or self._stop.is_set():
            return
        try:
            self._data_cache = self._provider() or {}
        except Exception as e:
            self._data_cache = {"error": str(e)}

        try:
            names = list(self._data_cache.keys()) if isinstance(self._data_cache, dict) else ["root"]
        except Exception:
            names = ["root"]
        if names and names != self._provider_names:
            self._provider_names = names
            try:
                if self._provider_combo:
                    self._provider_combo.configure(values=names)
                if self._provider_var and self._provider_var.get() not in names:
                    self._provider_var.set(names[0])
            except Exception:
                pass

        cur = self._provider_var.get() if self._provider_var else None
        if isinstance(self._data_cache, dict):
            payload = self._data_cache.get(cur) if cur in self._data_cache else (self._data_cache.get(names[0]) if names else {})
        else:
            payload = self._data_cache
        if not isinstance(payload, dict):
            payload = {"value": payload}

        # Rebuild tabs if provider's desired layout changed
        try:
            prov = self._provider_var.get() if self._provider_var else "renderer"
        except Exception:
            prov = "renderer"
        desired = self._desired_tabs_for_provider(prov)
        if desired != self._current_tab_keys:
            self._rebuild_tabs(desired)

        self._render_overview(payload)
        self._render_chars(payload)
        self._render_anim(payload)
        self._render_backlog(payload)
        self._render_voice(payload)
        self._render_flow(payload)
        self._render_raw(payload)

        try:
            import time
            self._last_refresh_ts = time.time()
            fps = payload.get("fps") if isinstance(payload, dict) else None
            prov = self._provider_var.get() if self._provider_var else ""
            auto = self._auto_var.get() if self._auto_var else False
            fil = self._filter_var.get() if self._filter_var else ""
            if self._status_var and hasattr(self._status_var, "set"):
                self._status_var.set(
                    f"FPS: {fps if fps is not None else '-'} | Auto: {'On' if auto else 'Off'} | Provider: {prov} | Filter: {'on' if fil else 'off'}"
                )
        except Exception:
            pass

    def _clear_tv(self, tv) -> None:
        try:
            for i in tv.get_children():
                tv.delete(i)
        except Exception:
            pass

    def _kv_rows(self, d: Dict[str, object], prefix: str = "") -> List[tuple[str, str]]:
        rows: List[tuple[str, str]] = []
        try:
            def flatten(pfx: str, obj: Any) -> None:
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        flatten(f"{pfx}.{k}" if pfx else str(k), v)
                else:
                    rows.append((pfx, str(obj) if isinstance(obj, (str, int, float, bool)) or obj is None else json.dumps(obj, ensure_ascii=False)))
            flatten(prefix, d or {})
        except Exception:
            rows = [("error", "failed to build")]
        return rows

    def _populate_kv_tree(self, tv, data: Dict[str, object]) -> None:
        self._clear_tv(tv)
        filt = (self._filter_var.get().strip().lower() if self._filter_var else "")
        idx = 0
        for k, v in self._kv_rows(data):
            if filt and (filt not in str(k).lower() and filt not in str(v).lower()):
                continue
            try:
                tag = "odd" if (idx % 2) else "even"
                tv.insert("", "end", values=(k, v), tags=(tag,))
                idx += 1
            except Exception:
                pass

    def _render_overview(self, payload: Dict[str, object]) -> None:
        keys = [
            "fps", "typing_enabled", "fast_forward", "auto_mode", "auto_delay_ms(line)",
            "line", "suppression",
        ]
        data: Dict[str, object] = {}
        for k in keys:
            if k in payload:
                data[k] = payload[k]
        if not data:
            data = payload
        self._populate_kv_tree(self._tv_overview, data)

    def _render_chars(self, payload: Dict[str, object]) -> None:
        tv = self._tv_chars
        if not tv:
            return
        self._clear_tv(tv)
        try:
            chars = payload.get("chars", {}) if isinstance(payload, dict) else {}
            actors = chars.get("actors", []) if isinstance(chars, dict) else []
            filt = (self._filter_var.get().strip().lower() if self._filter_var else "")
            idx = 0
            for info in actors:
                try:
                    name = str(info.get("name"))
                    active = "Yes" if info.get("active") else ""
                    outfit = str(info.get("outfit") or "")
                    action = "Yes" if info.get("has_action") else ""
                    rect = str(tuple(info.get("rect"))) if info.get("rect") else ""
                    center = str(tuple(info.get("center"))) if info.get("center") else ""
                    row = (name, active, outfit, action, rect, center)
                    if filt and all(filt not in str(x).lower() for x in row):
                        continue
                    tag = "odd" if (idx % 2) else "even"
                    tv.insert("", "end", values=row, tags=(tag,))
                    idx += 1
                except Exception:
                    continue
        except Exception:
            pass

    def _render_anim(self, payload: Dict[str, object]) -> None:
        d = payload.get("animator", {}) if isinstance(payload, dict) else {}
        self._populate_kv_tree(self._tv_anim, d if isinstance(d, dict) else {})

    def _render_backlog(self, payload: Dict[str, object]) -> None:
        d = payload.get("backlog", {}) if isinstance(payload, dict) else {}
        self._populate_kv_tree(self._tv_backlog, d if isinstance(d, dict) else {})

    def _render_voice(self, payload: Dict[str, object]) -> None:
        d = payload.get("voice", {}) if isinstance(payload, dict) else {}
        self._populate_kv_tree(self._tv_voice, d if isinstance(d, dict) else {})

    def _render_flow(self, payload: Dict[str, object]) -> None:
        d = payload.get("flow", {}) if isinstance(payload, dict) else {}
        self._populate_kv_tree(self._tv_flow, d if isinstance(d, dict) else {})

    def _render_raw(self, payload: Dict[str, object]) -> None:
        try:
            js = json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception:
            js = str(payload)
        try:
            if self._txt_raw is not None:
                self._txt_raw.delete("1.0", "end")
                self._txt_raw.insert("1.0", js)
        except Exception:
            pass

    def _run_action(self, name: str) -> None:
        fn = self._actions.get(name) if isinstance(self._actions, dict) else None
        if not callable(fn):
            return
        try:
            res = fn()
            if self._status_var and hasattr(self._status_var, "set"):
                self._status_var.set(f"Action '{name}' -> {res}")
        except Exception as e:
            try:
                if self._status_var and hasattr(self._status_var, "set"):
                    self._status_var.set(f"Action '{name}' failed: {e}")
            except Exception:
                pass

    # helpers: style/theme/sort/filter
    def _install_style(self) -> None:
        try:
            style = ttk.Style()
            # Prefer 'clam' for better ttk styling consistency
            try:
                style.theme_use("clam")
            except Exception:
                pass
            # define dark bg/fg
            self._apply_theme("Dark")
        except Exception:
            pass

    def _apply_theme(self, which: str) -> None:
        try:
            style = ttk.Style()
            dark = (str(which).lower() == "dark")
            if dark:
                bg = "#1e1f22"
                fg = "#e6e6e6"
                acc = "#2b2d31"
                sel = "#3a3d41"
                alt = "#24262a"
            else:
                bg = "#f4f4f4"
                fg = "#202020"
                acc = "#e8e8e8"
                sel = "#dcdcdc"
                alt = "#f9f9f9"
            # general
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg)
            style.configure("TCheckbutton", background=bg, foreground=fg)
            style.configure("TNotebook", background=bg)
            style.configure("TNotebook.Tab", background=acc, foreground=fg)
            style.map("TNotebook.Tab", background=[("selected", sel)])
            style.configure("TButton", background=acc, foreground=fg)
            style.configure("TCombobox", fieldbackground=acc, foreground=fg)
            style.configure("TEntry", fieldbackground=acc, foreground=fg)
            # Treeview
            style.configure("Treeview", background=bg, fieldbackground=bg, foreground=fg)
            style.map("Treeview", background=[("selected", sel)])
            # odd/even tags use tag_configure at runtime
            if self._root:
                self._root.configure(bg=bg)
        except Exception:
            pass

    def _apply_ontop(self) -> None:
        try:
            if self._root and hasattr(self._root, "attributes"):
                self._root.attributes("-topmost", bool(self._ontop_var.get() if self._ontop_var else False))
        except Exception:
            pass

    def _install_tree_tags(self, tv) -> None:
        try:
            tv.tag_configure("odd", background="#23262b")
            tv.tag_configure("even", background="#1e1f22")
        except Exception:
            try:
                tv.tag_configure("odd", background="#f4f8ff")
                tv.tag_configure("even", background="#ffffff")
            except Exception:
                pass

    def _sort_treeview(self, tv, column: str) -> None:
        try:
            items = [(tv.set(k, column), k) for k in tv.get_children("")]
        except Exception:
            return
        # attempt numeric conversion
        def coerce(v: str):
            try:
                if v is None:
                    return ""
                s = str(v)
                if s.isdigit():
                    return int(s)
                return float(s)
            except Exception:
                return str(v or "")
        items2 = []
        for val, iid in items:
            try:
                items2.append((coerce(val), iid))
            except Exception:
                items2.append((val, iid))
        tv_id = id(tv)
        prev = self._sort_state.get(tv_id)
        reverse = not prev[1] if prev and prev[0] == column else False
        items2.sort(key=lambda x: x[0], reverse=reverse)
        try:
            for idx, (_, iid) in enumerate(items2):
                tv.move(iid, "", idx)
        except Exception:
            pass
        self._sort_state[tv_id] = (column, reverse)

    def _current_payload(self) -> Dict[str, object]:
        names = []
        try:
            names = list(self._data_cache.keys()) if isinstance(self._data_cache, dict) else []
        except Exception:
            names = []
        cur = self._provider_var.get() if self._provider_var else None
        if isinstance(self._data_cache, dict):
            payload = self._data_cache.get(cur) if cur in self._data_cache else (self._data_cache.get(names[0]) if names else {})
        else:
            payload = self._data_cache
        if not isinstance(payload, dict):
            payload = {"value": payload}
        return payload
