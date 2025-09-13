from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem

from editor.core.parser_bridge import Diagnostic


class ProblemsPanel(QWidget):
    navigateRequested = Signal(str, int)  # file, line

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File", "Line", "Severity", "Message"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._on_cell_activated)
        layout.addWidget(self.table)

    def setDiagnostics(self, diags: list[Diagnostic]) -> None:  # noqa: N802
        self.table.setRowCount(0)
        for d in diags:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(d.file)))
            self.table.setItem(row, 1, QTableWidgetItem(str(d.line or "")))
            self.table.setItem(row, 2, QTableWidgetItem(d.severity))
            self.table.setItem(row, 3, QTableWidgetItem(d.message))

    def _on_cell_activated(self, row: int, _column: int) -> None:
        file_item = self.table.item(row, 0)
        line_item = self.table.item(row, 1)
        if not file_item:
            return
        file_str = file_item.text()
        try:
            line = int(line_item.text()) if line_item and line_item.text() else 1
        except Exception:
            line = 1
        self.navigateRequested.emit(file_str, line)
