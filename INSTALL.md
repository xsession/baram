# Installation

See also the [online installation page](https://baramcfd.org/docs/installation/) for
end-user binary packages.

This guide covers **developer / from-source** setup.

---

## Prerequisites

| Requirement        | Notes |
|--------------------|-------|
| **Python 3.11 – 3.13** | 3.13 recommended. Must be a CPython build with `venv` support. |
| **Git**            | To clone the repository. |
| **MS-MPI** (Windows) | Required by the parallel OpenFOAM solver. Download from [Microsoft MPI](https://learn.microsoft.com/en-us/message-passing-interface/microsoft-mpi). |
| **OpenFOAM / NextFOAM** (optional) | Solver binaries are **not** included in the repository. See [Solver binaries](#solver-binaries) below. |

### Installing Python

=== "Windows — py launcher (recommended)"

    Download from <https://www.python.org/downloads/> and check
    **"Add python.exe to PATH"** + **"Install launcher for all users"**
    during the installer.

    Verify:

    ```powershell
    py -3.13 --version
    ```

=== "Windows — uv (alternative)"

    If you use [**uv**](https://docs.astral.sh/uv/) for Python management:

    ```powershell
    uv python install 3.13
    uv python find 3.13          # should print the installed path
    ```

    The bootstrap script will auto-detect uv-managed Pythons when the
    `py` launcher does not have 3.11+ registered.

=== "Linux / macOS"

    Use your package manager or [pyenv](https://github.com/pyenv/pyenv):

    ```bash
    # Ubuntu / Debian
    sudo apt install python3.13 python3.13-venv

    # macOS (Homebrew)
    brew install python@3.13
    ```

---

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/nextfoam/baram.git
cd baram
```

### 2. Bootstrap the dev environment

The bootstrap script creates a `./venv`, installs all dependencies, and
generates the Qt resource / UI files.

=== "Windows (PowerShell)"

    ```powershell
    .\bootstrap-dev.ps1
    ```

    Optional flags:

    | Flag | Effect |
    |------|--------|
    | `-PythonExe C:\path\to\python.exe` | Use a specific interpreter |
    | `-RecreateVenv` | Delete and recreate `./venv` |
    | `-SkipDocs` | Skip `requirements-docs.txt` |
    | `-SkipBuild` | Skip `requirements-build.txt` (PyInstaller) |

=== "Linux / macOS"

    ```bash
    ./bootstrap-dev.sh
    ```

### 3. Run the applications

=== "Windows"

    ```powershell
    .\baramMesh.ps1      # mesh generation GUI
    .\baramFlow.ps1      # CFD solver GUI
    ```

    Or use the VS Code tasks **Run: baramMesh** / **Run: baramFlow**.

=== "Linux / macOS"

    ```bash
    ./baramMesh.sh
    ./baramFlow.sh
    ```

### 4. Select the interpreter in VS Code

After bootstrapping, point VS Code at the venv interpreter:

1. **Ctrl+Shift+P** → *Python: Select Interpreter*
2. Choose `./venv/Scripts/python.exe` (Windows) or `./venv/bin/python` (Linux/macOS)

---

## Solver binaries

BaramMesh and BaramFlow need **NextFOAM / OpenFOAM** executables to run
mesh utilities (`blockMesh`, `snappyHexMesh`, …) and solvers
(`buoyantSimpleNFoam`, etc.).  These are **not** shipped in the git
repository.

### Option A — Use the official BARAM installer

Install BARAM from <https://baramcfd.org>, then point the dev checkout at
its solver directory:

```powershell
# Example (adjust the path to your BARAM installation)
$env:BARAM_OPENFOAM_DIR = "C:\Program Files\BARAM\solvers"
```

Or create a symlink:

```powershell
# Run as Administrator
New-Item -ItemType Junction -Path solvers -Target "C:\Program Files\BARAM\solvers"
```

### Option B — Set environment variables

| Variable | Purpose |
|----------|---------|
| `BARAM_OPENFOAM_DIR` | Directory containing the OpenFOAM `bin/`, `etc/`, `lib/` tree |
| `BARAM_OPENFOAM_BIN` | Direct path to the `bin/` folder with solver executables |

### Option C — Build from source

Build NextFOAM following the instructions at
<https://github.com/nextfoam/nextfoam-cfd> and set the environment
variables above.

---

## Build & release

### PyInstaller binaries

```powershell
# Install build deps
python -m pip install -r requirements-build.txt

# Build
python tools/build_binaries.py --clean

# Create release zip
python tools/make_binary_release.py --version v1.2.3 --clean
```

Or use the VS Code tasks:

- **Build: binaries (PyInstaller)**
- **Release: local binaries (zip)**

### Source archives

```powershell
python tools/make_release.py --version v1.2.3 --out dist
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `py` launcher doesn't find 3.13 | Install from python.org **or** use `uv python install 3.13` — the bootstrap script handles both. |
| `SyntaxWarning: invalid escape sequence` | Make sure you are on the latest commit; these were fixed with raw strings. |
| `blockMesh.exe` not found | See [Solver binaries](#solver-binaries) — the solvers directory is not in the git repo. |
| `MS-MPI` errors on Windows | Install MS-MPI from Microsoft and restart your terminal. |
| Venv uses wrong Python version | Re-run `.\bootstrap-dev.ps1 -RecreateVenv`. |
| Qt resources out of date | Run `python convertUi.py` or the VS Code task **Generate: Qt resources**. |