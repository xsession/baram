# How-to guides

These are **task-oriented** instructions.

## Run from VS Code
- Debug: `.vscode/launch.json`
- Run tasks: `.vscode/tasks.json`

## Generate local release archives
- `python tools/make_release.py --version v1.2.3`

## Generate local binary bundle (current OS)
- Install build requirements: `pip install -r requirements.txt -r requirements-build.txt`
- Build & package: `python tools/make_binary_release.py --version v1.2.3 --clean`
