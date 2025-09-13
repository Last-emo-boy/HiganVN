from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu

from higanvn.script.model import Program


class OutlinePanel(QWidget):
    # Emitted when user requests running from a point in outline.
    # Payload dict includes keys: mode ('headless'|'pygame'), and either 'label' or 'line'.
    runRequested = Signal(dict)
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Kind", "Name/Text", "Line"])
        layout.addWidget(self.tree)
        # context menu for run actions
        # Be robust across PySide6 enum exposure differences
        try:
            policy = Qt.ContextMenuPolicy.CustomContextMenu  # type: ignore[attr-defined]
        except Exception:
            policy = getattr(Qt, "CustomContextMenu", None)  # type: ignore[attr-defined]
        if policy is not None:
            self.tree.setContextMenuPolicy(policy)  # type: ignore[arg-type]
        else:
            try:
                self.tree.setContextMenuPolicy(Qt.CustomContextMenu)  # type: ignore[attr-defined]
            except Exception:
                pass
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)

    def setProgram(self, program: Program) -> None:  # noqa: N802
        self.tree.clear()
        labels_parent = QTreeWidgetItem(["labels", "", ""])  # root group
        ops_parent = QTreeWidgetItem(["ops", "", ""])  # root group
        self.tree.addTopLevelItem(labels_parent)
        self.tree.addTopLevelItem(ops_parent)

        # labels from program.labels
        for name, ip in program.labels.items():
            # Prefer real source line if available on the label op's payload
            try:
                line = program.ops[ip].payload.get("line")
            except Exception:
                line = None
            item = QTreeWidgetItem(["label", name, str(line or "")])
            # tooltip with ip/line
            item.setToolTip(0, f"label {name}")
            item.setToolTip(1, f"ip={ip}")
            item.setToolTip(2, f"line={line}" if line else "line=?")
            # store metadata for context menu
            try:
                role = Qt.ItemDataRole.UserRole  # type: ignore[attr-defined]
            except Exception:
                role = getattr(Qt, "UserRole", 32)  # default UserRole int
            item.setData(0, role, {"type": "label", "name": name, "ip": int(ip), "line": int(line) if isinstance(line, int) else None})
            labels_parent.addChild(item)

        for idx, op in enumerate(program.ops):
            kind = op.kind
            line = op.payload.get("line") if op.payload else None
            if kind == "choice":
                text = op.payload.get("text", "")
            elif kind == "command":
                text = op.payload.get("name", "")
            elif kind == "dialogue":
                text = op.payload.get("actor", "")
            elif kind == "label":
                text = op.payload.get("name", "")
            else:
                text = op.payload.get("text", "")
            item = QTreeWidgetItem([kind, str(text), str(line or "")])
            # tooltip with ip/line
            item.setToolTip(0, f"{kind}")
            item.setToolTip(1, f"ip={idx}")
            item.setToolTip(2, f"line={line}" if line else "line=?")
            try:
                role = Qt.ItemDataRole.UserRole  # type: ignore[attr-defined]
            except Exception:
                role = getattr(Qt, "UserRole", 32)
            item.setData(0, role, {"type": kind, "ip": int(idx), "line": int(line) if isinstance(line, int) else None})
            ops_parent.addChild(item)

    def _on_tree_context_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        try:
            role = Qt.ItemDataRole.UserRole  # type: ignore[attr-defined]
        except Exception:
            role = getattr(Qt, "UserRole", 32)
        meta = item.data(0, role) or {}
        kind = meta.get("type")
        line = meta.get("line") if isinstance(meta.get("line"), int) else None
        label_name = meta.get("name") if kind == "label" else None
        menu = QMenu(self)
        act_head = menu.addAction("Run From Here (Headless)")
        act_pg = menu.addAction("Run From Here (Pygame)")
        global_pos = self.tree.viewport().mapToGlobal(pos)
        action = menu.exec(global_pos)
        if action == act_head:
            payload = {"mode": "headless"}
            if label_name:
                payload["label"] = label_name
            elif line:
                payload["line"] = str(int(line))
            self.runRequested.emit(payload)
        elif action == act_pg:
            payload = {"mode": "pygame"}
            if label_name:
                payload["label"] = label_name
            elif line:
                payload["line"] = str(int(line))
            self.runRequested.emit(payload)
