from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem

from higanvn.script.model import Program


class OutlinePanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Kind", "Name/Text", "Line"])
        layout.addWidget(self.tree)

    def setProgram(self, program: Program) -> None:  # noqa: N802
        self.tree.clear()
        labels_parent = QTreeWidgetItem(["labels", "", ""])  # root group
        ops_parent = QTreeWidgetItem(["ops", "", ""])  # root group
        self.tree.addTopLevelItem(labels_parent)
        self.tree.addTopLevelItem(ops_parent)

        # labels from program.labels
        for name, ip in program.labels.items():
            item = QTreeWidgetItem(["label", name, str(ip)])
            labels_parent.addChild(item)

        for op in program.ops:
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
            ops_parent.addChild(item)
