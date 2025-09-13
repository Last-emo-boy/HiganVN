Higan VNS Editor (alpha)

A standalone graphical editor for the VNS DSL. Everything lives under `editor/` and the editor must not write outside this folder unless you explicitly export to another directory.

Dev run:
- Ensure Python 3.10+ is available.
- Install deps from `requirements.txt`.
- Launch with `python -m editor.app.main` from repo root.

Output policy:
- All outputs go to `editor/out/` by default.
- No modifications to engine/runtime files during export.
