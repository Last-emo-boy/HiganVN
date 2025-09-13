# Editor Project Status

Updated: 2025-09-06

## Vision
A standalone graphical editor for the VNS DSL used by this project. It must support the full syntax, provide validation and assistive tooling, and export outputs without modifying any files outside the editor’s own workspace/output.

## Constraints
- Non-destructive: generation/export must not modify repository files outside `editor/` unless exporting to a user-specified output directory.
- Full VNS compatibility: rely on the existing parser/model to understand all ops.
- Cross-platform, but prioritize Windows for initial milestones.

## Recommended Stack (initial)
- Language: Python 3.x
- UI Toolkit: PySide6 (Qt for Python)
- Syntax Editing: Qt text editor with custom VNS syntax highlighter
- Validation: use engine’s parser in strict mode
- Preview (Phase 2): run headless execution to compute state; optional external pygame preview
- Packaging: PyInstaller onefile app for the editor (separate from game packer)

Alternatives considered: Electron/Tauri (JS) – deferred to keep a single-language stack and reuse Python code.

## Current Status
- Project scaffolding to be created in `editor/` with specs and todo.
- No code yet. Planning & design in progress.

## Milestones
1. M0 – Foundations
   - Decide stack (PySide6) and project layout
   - Define `.higanproj` (editor project file) schema
   - Basic window: menu, tabs, status bar
   - VNS file open (read-only), file watcher
2. M1 – Editing & Validation
   - Syntax highlighter and basic editing
   - Invoke parser in strict mode; Problems panel
   - Outline/structure view (scenes, labels, jumps)
   - Export to `editor/out/` without touching repo files
3. M2 – Assets & Graph
   - Assets browser scoped by metadata assetsNamespace
   - Visual flow graph (labels/choices/jumps)
   - Inspector panels for ops
4. M3 – Preview & Tooling
   - Headless preview snapshots
   - External Run in pygame with current cursor
   - Slot thumbnails regeneration utility
5. M4 – Packaging & UX polish
   - PyInstaller packaging for the editor
   - Settings, themes, keybindings, docs

## Risks & Notes
- Embedding pygame preview into Qt can be tricky; prefer headless snapshot or external window first.
- Keep the editor independent: import engine modules but never write to them.
- Ensure export paths are configurable and default to `editor/out/`.
