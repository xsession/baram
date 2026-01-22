# Packaging

## PyInstaller
Specs:
- `packaging/pyinstaller/baramFlow.spec`
- `packaging/pyinstaller/baramMesh.spec`

Build helpers:
- `requirements-build.txt`
- `tools/build_binaries.py`
- `tools/make_binary_release.py`

## Notes
- The packaging scripts run `convertUi.py` first to generate `resource_rc.py` and `*_ui.py`.
