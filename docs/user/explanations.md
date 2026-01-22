# Explanations

This section explains the "why" behind key behaviors.

## Why there are two apps
- **BaramMesh** focuses on mesh preparation.
- **BaramFlow** focuses on solver setup and run management.

## UI resources generation (`convertUi.py`)
Some Python modules are generated from Qt inputs:
- `resource_rc.py` from `resource.qrc`
- `*_ui.py` from `.ui` files

These files are not committed, so builds that bundle the app (PyInstaller) generate them first.
