from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from editor.ui.main_window import MainWindow


def run(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    app = QApplication(argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
