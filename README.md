## BARAM

## OpenCL (v2512) heterogeneous backend

Important: upstream OpenFOAM solvers are C++ CPU solvers; “refactoring OpenFOAM solvers to OpenCL” generally means using a separate GPU/OpenCL-enabled fork/solver implementation. BaramFlow can:
- generate standard OpenFOAM cases,
- choose which solver executable to launch, and
- pass environment variables/device selections to that solver.

BaramFlow can run calculations via either:
- the bundled OpenFOAM backend (`calculation_backend: openfoam`, default), or
- an external solver backend (`calculation_backend: external`).

If you want to keep using OpenFOAM case setup but run a custom solver binary (for example, an OpenCL/GPU-enabled OpenFOAM fork that ships different executable names), configure `openfoam_solver_overrides`.

Example `~/.BaramFlow/baram.cfg.yaml`:

```yaml
calculation_backend: openfoam

openfoam_solver_overrides:
	buoyantSimpleNFoam: buoyantSimpleNFoamOpenCL
	buoyantPimpleNFoam: buoyantPimpleNFoamOpenCL

opencl_devices: "0,1,2"
solver_env:
	# Optional: map Baram's device string to env vars your fork expects
	OPENCL_DEVICES: "{BARAM_OPENCL_DEVICES}"
```

For **CPU+iGPU+dGPU** heterogeneous compute, the **external solver** must implement multi-device OpenCL itself (FluidX3D-style). BaramFlow will pass your device selection to the external solver via environment variables.

### 1) List OpenCL devices

```powershell
\.\venv\Scripts\python.exe .\tools\opencl_info.py
```

### 1b) Try to detect your solver's CLI

If you don’t know which flags your external solver uses for device selection:

```powershell
\.\venv\Scripts\python.exe .\tools\detect_external_solver_cli.py -- C:\\Path\\To\\YourOpenCLSolver.exe
```

### 2) Configure BaramFlow

Edit `~/.BaramFlow/baram.cfg.yaml` and add:

```yaml
calculation_backend: external
external_solver_command:
	- C:\\Path\\To\\YourOpenCLSolver.exe
	# You can use placeholders in args:
	# {BARAM_CASE_PATH}, {BARAM_PROJECT_UUID}, {BARAM_RUN_MODE}, {BARAM_OPENCL_DEVICES}
	- --case={BARAM_CASE_PATH}
	- --devices={BARAM_OPENCL_DEVICES}
opencl_devices: "0,1,2"  # external solver decides what this means
solver_env:
	# Optional extra knobs your solver expects
	# BARAM_OPENCL_DEVICES: "0,1,2"  # overrides opencl_devices if set
```

### 3) Dry-run the wiring

You can validate that Baram passes env vars/logs correctly by setting:

```yaml
external_solver_command:
	- C:\\GIT\\baram\\venv\\Scripts\\python.exe
	- C:\\GIT\\baram\\tools\\external_backend_echo.py
```
*BARAM* is a Free Open Source Computational Fluid Dynamics (CFD) software package.
*BARAM* is developed to mitigate the steep learning curve of Text-based Solvers.
*BARAM* helps you focus on a problem itself with intuitive graphical user interface.
For now, *OpenFOAM®* solvers modified by *NEXTFOAM* are integrated into *BARAM*.
*NEXTFOAM* develops and releases it under GNU Public License (GPL).

### Key Features
- **Multi-format geometry import** — STL, STEP (.step/.stp), IGES (.iges/.igs), BREP (.brep/.brp)
- **Automated mesh generation** — snappyHexMesh with GUI-driven configuration
- **Enterprise logging** — rotating file logs, structured JSON, correlation IDs
- **Centralised configuration** — environment variables, YAML config files, sensible defaults
- **Structured error handling** — typed exception hierarchy with error codes


### Supported Platforms
- Ubuntu 20.04 or later
- CentOS 8.2 or alternatives ( Rocky Linux, AlmaLinux, ... )
- OpenSUSE Leap 15.4
- Linux Mint 21 "Vanessa"
- Windows 10 or later
- macOS 10.14 or later

### Note
BARAM is not approved or endorsed by OpenCFD Limited,
producer and distributor of the OpenFOAM software
and owner of the OPENFOAM® and OpenCFD® trademarks.


### Documentation (local)
This repo includes an offline documentation site under `docs/` (MkDocs).

Build and serve locally:
```powershell
python -m pip install -r requirements-docs.txt
mkdocs serve
```


### VS Code
- Debug: use `.vscode/launch.json` (`baramFlow`, `baramMesh`).
- Run tasks: `Run: baramFlow` / `Run: baramMesh` in `.vscode/tasks.json` (uses the selected VS Code Python interpreter).

Python note:
- The runtime dependencies in `requirements.txt` target Python 3.11+.
- If you change versions/pins and see build-from-source failures on Windows, prefer packages with prebuilt wheels for your Python version.

Recommended first-time setup:
- Run the VS Code task `Setup: dev venv + deps` (or run `./bootstrap-dev.ps1`).
- In VS Code, select the interpreter from `./venv`.


### Windows quick start
- `./baramFlow.ps1` and `./baramMesh.ps1` run the apps using `./venv`.


### Releases (GitHub + GitLab)
- Create a version tag like `v1.2.3` and push it.
- GitHub: `.github/workflows/release.yml` creates a GitHub Release and uploads `baram-<tag>-windows.zip`, `baram-<tag>-linux.tar.gz`, `baram-<tag>-macos.tar.gz`, and `SHA256SUMS`.
- GitLab: `.gitlab-ci.yml` creates a GitLab Release on tags and links the same artifacts from the `package` job.


### Local release artifacts
- Create the archives locally (requires `git`): `python tools/make_release.py --version v1.2.3` (writes to `dist/`).
- VS Code task: `Release: local archives`.


### Installable binaries (PyInstaller)
- Build requirements: install runtime deps plus `requirements-build.txt`. The build also runs `convertUi.py`, which needs Qt tools like `pyside6-rcc`/`pyside6-uic`.
- Local build (current OS):
	- `python -m pip install -r requirements.txt -r requirements-build.txt`
	- `python tools/make_binary_release.py --version v1.2.3`
	- Output: `dist/baram-v1.2.3-<platform>-binaries.zip`

