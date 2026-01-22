# Run & Debug

## VS Code
- Debug configs: `.vscode/launch.json` (modules `baramFlow.main` and `baramMesh.main`)
- Run tasks: `.vscode/tasks.json`

## Common debug checklist
- Confirm the selected interpreter matches your `venv`.
- Run `python -m compileall -q -x PyFoam .` to sanity-check syntax (the vendored `PyFoam` includes legacy Python 2 files).

![VS Code run/debug flow](../assets/diagrams/vscode-debug-flow.svg)
