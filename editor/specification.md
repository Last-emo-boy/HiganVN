# VNS Editor Specification

Updated: 2025-09-06

## Overview
A standalone Qt-based editor for the VNS DSL. It understands all current script ops using the existing parser/model, offers editing with validation, asset management, and optional preview. Exporting must not modify repository files outside the editor’s own directories.

## Goals
- Full syntax awareness via the existing parser/model
- Helpful editing UX (highlighting, outline, autocomplete for op names/args)
- Validation and diagnostics (strict mode, asset existence checks)
- Visual flow graph for labels/choices/jumps
- Asset browser scoped by metadata (assetsNamespace)
- Non-destructive export to a configurable output directory (default: `editor/out/`)

## Non-goals (initial)
- Advanced animation timelines
- In-Qt embedded pygame surface (Phase 3+ only)

## Architecture
- Frontend: PySide6 (Qt Widgets)
- Backend/Domain: Reuse engine’s script model/parser by importing the package
- IPC: Not required (single process)
- Packaging: PyInstaller for a single executable editor

### Modules
- app/ (Qt app bootstrap)
- core/
  - project.py – .higanproj schema load/save
  - parser_bridge.py – wraps engine’s parser & diagnostics
  - graph.py – builds flow graph from Program/Op
  - assets.py – assetsNamespace resolution, scanning, validation
  - export.py – writes outputs to `editor/out/` or user-chosen dir
- ui/
  - main_window.py – menus, tabs, statusbar
  - editor_widget.py – text editor with VNS highlighter
  - problems_panel.py – diagnostics list
  - outline_panel.py – scenes/labels/ops outline
  - graph_view.py – node/edge visualization
  - assets_panel.py – thumbnails, search, drag-drop
  - settings.py – preferences

## Data
### Editor Project (.higanproj)
JSON schema (draft):
{
  "version": 1,
  "name": "",
  "id": "",
  "scripts": ["scripts/demo.vns"],
  "assetsNamespace": "demo",
  "metadataPath": "scripts/demo.vns.meta.json",
  "outputDir": "editor/out",
  "settings": {
    "strict": true,
    "fontSize": 28
  }
}

### In-memory Model
- Program, Op, Labels, Choices (from engine)
- Graph nodes: labels; edges: jumps/choices/next
- Diagnostics: (path, line, column, severity, message)

## UX
- Main layout: Left (Project tree), Center (Editor), Right (Outline/Inspector), Bottom (Problems)
- Tabs: Script, Graph, Assets, Preview (later), Settings
- Commands: New Project, Open Project, Import Script, Validate, Export, Run in pygame (external), Generate Thumbnails

## Validation
- Parse with strict mode; surface errors live
- Asset checks: referenced files exist in assetsNamespace
- Save directory policy: editor never writes to existing repo files; all outputs go to outputDir or user-picked folder

## Exporting
- Copy scripts and metadata to `outputDir/`
- Do not overwrite original files; create new copies with timestamped backups if needed
- Optional: export a packaged zip for sharing

## Preview (Phase 2)
- Headless run to a given IP to produce state snapshot (text/bg/characters)
- Optional external run: start pygame renderer at current cursor position

## Telemetry & Logging
- Local-only logs for diagnostics; no network access

## Security
- No code execution from scripts beyond what the engine already performs; sandbox preview

## Test Plan
- Unit tests for parser bridge, project schema, graph builder
- E2E smoke: load project -> edit -> validate -> export -> external run

## Roadmap & Compatibility
- Ensure compatibility with future ops via a generic op registry rendered as key-value inspector
- Keep the editor versioned and independent from engine changes; feature flags if needed
