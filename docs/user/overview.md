# User overview

Baram provides a GUI-driven workflow for CFD and mesh preparation:
- **BaramMesh**: mesh creation / import / export
- **BaramFlow**: case setup, solving, and post-processing

## What you need
- Python environment with dependencies installed (see repository `INSTALL.md` and the online installation page linked there)
- OpenFOAM environment as required by your workflow

## App startup
- From the repo root:
  - `python -m baramMesh.main`
  - `python -m baramFlow.main`
- Windows convenience scripts:
  - `./baramMesh.ps1`
  - `./baramFlow.ps1`

## First-time setup (Windows)
1. Run `./bootstrap-dev.ps1` to create `./venv`, install dependencies, and generate Qt resources.
2. In VS Code, select the interpreter from `./venv`.

## Typical workflow

![Runtime flow](../assets/diagrams/runtime-flow.svg)
