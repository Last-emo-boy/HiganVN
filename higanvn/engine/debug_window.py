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

    def __init__(self, data_provider: Callable[[], Dict[str, object]], *, refresh_ms: int = 300) -> None:
        self._provider = data_provider
        self._refresh_ms = max(100, int(refresh_ms))
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._root = None
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
        # state/cache
        self._provider_names: List[str] = []
        self._data_cache: Dict[str, object] = {}

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

        self._build_ui()
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
        self._interval_var = tk.IntVar(value=self._refresh_ms)
        Spinbox = getattr(ttk, "Spinbox", None)
        spn = Spinbox(bar, from_=100, to=5000, increment=100, textvariable=self._interval_var, width=6) if Spinbox else tk.Spinbox(bar, from_=100, to=5000, increment=100, textvariable=self._interval_var, width=6)
        spn.pack(side="left")

        self._status_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self._status_var).pack(side="left", padx=(12, 0))

        ttk.Button(bar, text="Copy JSON", command=self._copy_json).pack(side="right", padx=8)

        # Notebook
        self._notebook = ttk.Notebook(self._root)
        self._notebook.pack(side="top", fill="both", expand=True)

        # Tabs
        frm_over = ttk.Frame(self._notebook)
        self._tv_overview = self._make_kv_tree(frm_over)
        self._notebook.add(frm_over, text="Overview")

        frm_chars = ttk.Frame(self._notebook)
        self._tv_chars = self._make_chars_tree(frm_chars)
        self._notebook.add(frm_chars, text="Characters")

        frm_anim = ttk.Frame(self._notebook)
        self._tv_anim = self._make_kv_tree(frm_anim)
        self._notebook.add(frm_anim, text="Animator")

        frm_back = ttk.Frame(self._notebook)
        self._tv_backlog = self._make_kv_tree(frm_back)
        self._notebook.add(frm_back, text="Backlog")

        frm_voice = ttk.Frame(self._notebook)
        self._tv_voice = self._make_kv_tree(frm_voice)
        self._notebook.add(frm_voice, text="Voice")

        frm_flow = ttk.Frame(self._notebook)
        self._tv_flow = self._make_kv_tree(frm_flow)
        self._notebook.add(frm_flow, text="Flow")

        frm_raw = ttk.Frame(self._notebook)
        self._txt_raw = tk.Text(frm_raw, wrap="none", font=("Consolas", 10))
        self._txt_raw.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm_raw, orient="vertical", command=self._txt_raw.yview)
        yscroll.pack(side="right", fill="y")
        self._txt_raw.configure(yscrollcommand=yscroll.set)
        self._notebook.add(frm_raw, text="Raw JSON")

    def _make_kv_tree(self, parent):
        frm = ttk.Frame(parent)
        frm.pack(fill="both", expand=True)
        cols = ("Key", "Value")
        tv = ttk.Treeview(frm, columns=cols, show="headings")
        tv.heading("Key", text="Key")
        tv.heading("Value", text="Value")
        tv.column("Key", width=260, anchor="w")
        tv.column("Value", width=520, anchor="w")
        tv.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        yscroll.pack(side="right", fill="y")
        tv.configure(yscrollcommand=yscroll.set)
        return tv

    def _make_chars_tree(self, parent):
        frm = ttk.Frame(parent)
        frm.pack(fill="both", expand=True)
        cols = ("Name", "Active", "Outfit", "Action", "Rect", "Center")
        tv = ttk.Treeview(frm, columns=cols, show="headings")
        for c in cols:
            tv.heading(c, text=c)
        tv.column("Name", width=180, anchor="w")
        tv.column("Active", width=60, anchor="center")
        tv.column("Outfit", width=140, anchor="w")
        tv.column("Action", width=70, anchor="center")
        tv.column("Rect", width=200, anchor="w")
        tv.column("Center", width=140, anchor="w")
        tv.pack(side="left", fill="both", expand=True)
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        yscroll.pack(side="right", fill="y")
        tv.configure(yscrollcommand=yscroll.set)
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

        self._render_overview(payload)
        self._render_chars(payload)
        self._render_anim(payload)
        self._render_backlog(payload)
        self._render_voice(payload)
        self._render_flow(payload)
        self._render_raw(payload)

        try:
            fps = payload.get("fps") if isinstance(payload, dict) else None
            prov = self._provider_var.get() if self._provider_var else ""
            auto = self._auto_var.get() if self._auto_var else False
            if self._status_var and hasattr(self._status_var, "set"):
                self._status_var.set(f"FPS: {fps if fps is not None else '-'} | Auto: {'On' if auto else 'Off'} | Provider: {prov}")
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
        for k, v in self._kv_rows(data):
            try:
                tv.insert("", "end", values=(k, v))
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
            for info in actors:
                try:
                    name = str(info.get("name"))
                    active = "Yes" if info.get("active") else ""
                    outfit = str(info.get("outfit") or "")
                    action = "Yes" if info.get("has_action") else ""
                    rect = str(tuple(info.get("rect"))) if info.get("rect") else ""
                    center = str(tuple(info.get("center"))) if info.get("center") else ""
                    tv.insert("", "end", values=(name, active, outfit, action, rect, center))
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
