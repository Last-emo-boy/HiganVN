from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit


def _color_format(color_name: str, bold: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    color = {
        "darkBlue": Qt.GlobalColor.darkBlue,
        "darkMagenta": Qt.GlobalColor.darkMagenta,
        "darkGreen": Qt.GlobalColor.darkGreen,
        "darkCyan": Qt.GlobalColor.darkCyan,
        "gray": Qt.GlobalColor.gray,
        "darkRed": Qt.GlobalColor.darkRed,
        "black": Qt.GlobalColor.black,
    }.get(color_name, Qt.GlobalColor.black)
    fmt.setForeground(color)
    if bold:
        fmt.setFontWeight(75)  # Bold
    return fmt


class VnsHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:  # type: ignore[override]
        super().__init__(document)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Simple patterns
        self.rules.append((QRegularExpression(r"^\s*>.*"), _color_format("darkBlue", True)))  # commands
        self.rules.append((QRegularExpression(r"^\s*♪.*"), _color_format("darkMagenta", True)))  # BGM shorthand
        self.rules.append((QRegularExpression(r"^\s*\*\w+.*"), _color_format("darkGreen", True)))  # labels
        self.rules.append((QRegularExpression(r"^\s*\?.*"), _color_format("darkCyan", True)))  # choices
        self.rules.append((QRegularExpression(r"#.*$"), _color_format("gray")))  # comments
        # quoted text using Chinese/English quotes or double quotes
        self.rules.append((QRegularExpression(r"[“\"].*[”\"]"), _color_format("darkRed")))

    def highlightBlock(self, text: str) -> None:  # type: ignore[override]
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

    # no duplicate helpers below


class ScriptEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self._path: Path | None = None
        self._highlighter = VnsHighlighter(self.document())

    @property
    def path(self) -> Path | None:
        return self._path

    def load_file(self, path: Path) -> None:
        self._path = Path(path)
        text = self._path.read_text(encoding="utf-8")
        self.setPlainText(text)

    def goto_line(self, line: int) -> None:
        if line <= 0:
            line = 1
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line - 1):
            cursor.movePosition(cursor.MoveOperation.Down)
        self.setTextCursor(cursor)
        self.centerCursor()

    def current_line(self) -> int:
        try:
            cursor = self.textCursor()
            # blockNumber is 0-indexed; return 1-indexed
            return int(cursor.blockNumber()) + 1
        except Exception:
            return 1
