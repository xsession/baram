## BARAM
*BARAM* is a Free Open Source Computational Fluid Dynamics (CFD) software package.
*BARAM* is developed to mitigate the steep learning curve of Text-based Solvers.
*BARAM* helps you focus on a problem itself with intuitive graphical user interface.
For now, *OpenFOAM®* solvers modified by *NEXTFOAM* are integrated into *BARAM*.
*NEXTFOAM* develops and releases it under GNU Public License (GPL).


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

