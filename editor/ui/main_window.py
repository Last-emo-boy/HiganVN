from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QLabel,
    QSplitter,
)

from editor.core.project import Project
from editor.core.parser_bridge import validate_files, validate_text
from editor.ui.problems_panel import ProblemsPanel
from editor.ui.script_editor import ScriptEditor
from editor.ui.outline_panel import OutlinePanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Higan VNS Editor (alpha)")
        self.resize(1000, 700)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(QLabel("Welcome. Use File > New Project or Open Project."), "Home")

        self._current_project = None  # type: ignore[assignment]
        self._problems = ProblemsPanel()
        self._editor = ScriptEditor()
        self._outline = OutlinePanel()

        self._editor_splitter = QSplitter()
        self._editor_splitter.addWidget(self._editor)
        self._editor_splitter.addWidget(self._outline)
        self._editor_splitter.setStretchFactor(0, 3)
        self._editor_splitter.setStretchFactor(1, 1)
        self.tabs.addTab(self._editor_splitter, "Editor")

        # Debounced validation timer and signals
        self._validate_timer = QTimer(self)
        self._validate_timer.setSingleShot(True)
        self._validate_timer.timeout.connect(self._validate_current_script)
        self._editor.textChanged.connect(self._on_editor_text_changed)
        self._outline.tree.itemActivated.connect(self._on_outline_item_activated)
        self._problems.navigateRequested.connect(self._on_problem_navigate)

        self._build_menu()

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("File")

        new_action = QAction("New Project", self)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("Open Project...", self)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        open_script_action = QAction("Open Script...", self)
        open_script_action.triggered.connect(self._open_script)
        file_menu.addAction(open_script_action)

        save_action = QAction("Save Project", self)
        save_action.triggered.connect(self._save_project)
        save_action.setEnabled(False)
        file_menu.addAction(save_action)
        self._save_action = save_action

        validate_action = QAction("Validate", self)
        validate_action.triggered.connect(self._validate_project)
        file_menu.addAction(validate_action)

        save_script_action = QAction("Save Script", self)
        save_script_action.triggered.connect(self._save_script)
        file_menu.addAction(save_script_action)

        save_script_as_action = QAction("Save Script As...", self)
        save_script_as_action.triggered.connect(self._save_script_as)
        file_menu.addAction(save_script_as_action)

    def _new_project(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Create Project",
            str(Path.cwd() / "editor" / "examples" / "example.higanproj"),
            "Higan Project (*.higanproj)",
        )
        if not path_str:
            return
        path = Path(path_str)
        project = Project.create(path)
        self._open_project_path(project.path)

    def _open_project(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open Project", str(Path.cwd()), "Higan Project (*.higanproj)"
        )
        if not path_str:
            return
        self._open_project_path(Path(path_str))

    def _open_script(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open Script", str(Path.cwd()), "VNS Script (*.vns)"
        )
        if not path_str:
            return
        p = Path(path_str)
        self._editor.load_file(p)
        from higanvn.script.parser import parse_script

        program = parse_script(self._editor.toPlainText())
        self._outline.setProgram(program)
        idx = self.tabs.indexOf(self._editor_splitter)
        if idx != -1:
            self.tabs.setCurrentIndex(idx)
        self._update_title()
        self._schedule_validate()

    def _open_project_path(self, path: Path) -> None:
        try:
            project = Project.load(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Failed to open", str(e))
            return
        self._current_project = project
        self._save_action.setEnabled(True)
        self._show_project_tab(project)
        if self.tabs.indexOf(self._problems) == -1:
            self.tabs.addTab(self._problems, "Problems")
        self._update_title()

    def _save_project(self) -> None:
        if not self._current_project:
            return
        try:
            self._current_project.save()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))
        else:
            QMessageBox.information(
                self, "Saved", f"Saved: {self._current_project.path}"
            )
        self._update_title()

    def _show_project_tab(self, project: Project) -> None:
        info = QLabel()
        try:
            flag = Qt.TextInteractionFlag.TextSelectableByMouse
        except AttributeError:
            flag = Qt.TextSelectableByMouse  # type: ignore[attr-defined]
        info.setTextInteractionFlags(info.textInteractionFlags() | flag)
        info.setText(
            f"<b>Project:</b> {project.path}<br>"
            f"<b>Scripts:</b> {', '.join(project.data.get('scripts', []))}<br>"
            f"<b>Assets Namespace:</b> {project.data.get('assetsNamespace', '')}<br>"
            f"<b>Output Dir:</b> {project.output_dir}"
        )
        self.tabs.addTab(info, "Project")
        self.tabs.setCurrentWidget(info)

    def _validate_project(self) -> None:
        if not self._current_project:
            QMessageBox.information(
                self, "No project", "Create or open a project first."
            )
            return
        files = [
            Path(self._current_project.root / p)
            for p in self._current_project.data.get("scripts", [])
        ]
        diags = validate_files(files)
        self._problems.setDiagnostics(diags)
        if self.tabs.indexOf(self._problems) == -1:
            self.tabs.addTab(self._problems, "Problems")
        self.tabs.setCurrentWidget(self._problems)

    # --- editor helpers ---
    def _on_editor_text_changed(self) -> None:
        self._schedule_validate()

    def _schedule_validate(self) -> None:
        self._validate_timer.start(300)

    def _validate_current_script(self) -> None:
        text = self._editor.toPlainText()
        fpath = self._editor.path if self._editor.path else Path("<editor>")
        diags = validate_text(fpath, text)
        self._problems.setDiagnostics(diags)
        if self.tabs.indexOf(self._problems) == -1:
            self.tabs.addTab(self._problems, "Problems")
        has_errors = any(d.severity == "error" for d in diags)
        if not has_errors:
            try:
                from higanvn.script.parser import parse_script

                program = parse_script(text)
            except Exception:
                return
            self._outline.setProgram(program)

    def _on_outline_item_activated(self, item, _column) -> None:
        try:
            line = int(item.text(2))
        except Exception:
            return
        self._editor.goto_line(line if line > 0 else 1)

    def _save_script(self) -> None:
        if not self._editor.path:
            QMessageBox.information(self, "No script", "Open a script first.")
            return
        try:
            self._editor.path.write_text(
                self._editor.toPlainText(), encoding="utf-8"
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))
        else:
            QMessageBox.information(self, "Saved", f"Saved: {self._editor.path}")
        self._update_title()

    def _save_script_as(self) -> None:
        default = str(self._editor.path) if self._editor.path else str(Path.cwd() / "script.vns")
        path_str, _ = QFileDialog.getSaveFileName(self, "Save Script As", default, "VNS Script (*.vns)")
        if not path_str:
            return
        try:
            Path(path_str).write_text(self._editor.toPlainText(), encoding="utf-8")
            self._editor.load_file(Path(path_str))
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save failed", str(e))
            return
        self._update_title()

    def _on_problem_navigate(self, file_str: str, line: int) -> None:
        # If the file matches current editor, just go; otherwise try to load it.
        try_path = Path(file_str)
        if self._editor.path and try_path.resolve() == self._editor.path.resolve():
            self._editor.goto_line(line)
        else:
            if try_path.exists():
                self._editor.load_file(try_path)
                idx = self.tabs.indexOf(self._editor_splitter)
                if idx != -1:
                    self.tabs.setCurrentIndex(idx)
                self._editor.goto_line(line)
        self._update_title()

    def _update_title(self) -> None:
        proj = f" - {self._current_project.path.name}" if self._current_project else ""
        script = f" [{self._editor.path.name}]" if self._editor.path else ""
        self.setWindowTitle(f"Higan VNS Editor (alpha){proj}{script}")
