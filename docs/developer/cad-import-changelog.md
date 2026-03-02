# CAD Import — Enterprise Upgrade Changelog

This document summarises the full series of changes made to add STEP/IGES/BREP file import to BARAM and bring the geometry pipeline up to production quality.

---

## 1. Objective

Make BARAM's geometry import pipeline **enterprise-grade** by adding:

- STEP (.step/.stp), IGES (.iges/.igs), and BREP (.brep/.brp) file support
- Responsive progress dialogs with real percentage tracking
- Robust error handling with structured logging
- Clean startup (no SyntaxWarnings)

## 2. Architecture — Subprocess Isolation

### Problem

Both VTK and gmsh bundle their own builds of **OpenCASCADE (OCC)** native libraries. When both are loaded in the same process, the symbol tables collide and `gmsh.model.occ.importShapes()` crashes with an **access violation**.

An earlier attempt to run gmsh on a `QThread` also failed because `gmsh.initialize()` calls `signal.signal()`, which is only allowed on the **main thread** in Python.

### Solution

Gmsh runs in a **separate subprocess** with no VTK or Qt loaded. The parent process reads the resulting STL files with VTK.

```
┌──────────────────────────┐       stdin (JSON job)        ┌──────────────────────┐
│  Parent Process          │ ──────────────────────────────▶│  _gmsh_worker.py     │
│  (Qt + VTK loaded)       │                                │  (gmsh only, no VTK) │
│                          │◀── stderr (PROGRESS lines) ───│                      │
│  CADImporter._run_worker │◀── stdout (JSON result)  ─────│  _run(job)           │
│  reads STL via vtkSTL... │       + per-surface .stl files │  writes binary STL   │
└──────────────────────────┘                                └──────────────────────┘
```

## 3. Files Created

| File | Purpose |
|------|---------|
| `baramMesh/view/geometry/_gmsh_worker.py` (~320 lines) | Standalone subprocess script. Imports gmsh, tessellates CAD, writes per-surface binary STL files, outputs JSON result on stdout, reports progress on stderr. |
| `libbaram/logging_config.py` (~370 lines) | Enterprise logging: rotating file logs, structured JSON output, correlation IDs, performance timing, env-var overrides. |
| `libbaram/configuration.py` (~270 lines) | Centralised configuration with layered resolution (defaults → config file → env vars), type-checked dataclasses. |

## 4. Files Modified

| File | Changes |
|------|---------|
| `baramMesh/view/geometry/cad_utility.py` | Complete rewrite (~750 lines). Uses `subprocess.Popen` + background thread to read stderr progress. No direct gmsh import. `check_gmsh_available()` uses `importlib.util.find_spec` + subprocess probe. Timeout raised to 3600s. |
| `baramMesh/view/geometry/geometry_page.py` | Dual STL + CAD pipeline with `QApplication.processEvents()` for UI responsiveness. Progress callbacks wired to `ProgressDialog.setPercent()`. |
| `baramMesh/view/geometry/geometry_import_dialog.py` | Multi-format file filter, CAD tessellation quality controls (Coarse/Medium/Fine presets), `stlFiles()`/`cadFiles()`/`tessellationParams()` API. |
| `baramMesh/view/geometry/stl_utility.py` | `StlImporter.load()` accepts optional `progress_callback`. |
| `widgets/progress_dialog.py` | Added `setRange()`, `setPercent()`, `setIndeterminate()` methods. |
| `libbaram/exception.py` | Added `CADImportError`, `GmshNotAvailableError`, `MeshQualityError` exception hierarchy. |
| `baramMesh/main.py`, `baramFlow/main.py` | Integrated `setup_logging()` for rotating file logs at startup. |
| `requirements.txt` | Added `gmsh>=4.11`. |
| `PyFoam/Infrastructure/Configuration.py` | Fixed SyntaxWarnings: replaced `eval()` on Windows paths with direct list literal; converted regex patterns to raw strings. |

## 5. Bugs Fixed

### 5.1 `check_gmsh_available()` — OSError on DLL Load

**Symptom:** App crashed on startup when gmsh's native DLL failed to load.  
**Root cause:** Only `ImportError` was caught, but gmsh raised `OSError: [WinError 1455]`.  
**Fix:** Changed to `importlib.util.find_spec()` + subprocess probe — gmsh is never imported in the main process.

### 5.2 QThread + `signal.signal()` Crash

**Symptom:** `ValueError: signal only works in main thread` when running gmsh on a QThread.  
**Root cause:** `gmsh.initialize()` registers signal handlers, forbidden on non-main threads.  
**Fix:** Abandoned QThread approach entirely. Used subprocess isolation instead.

### 5.3 Access Violation in `importShapes()`

**Symptom:** `EXCEPTION_ACCESS_VIOLATION` crash during `gmsh.model.occ.importShapes()`.  
**Root cause:** VTK and gmsh both bundle OpenCASCADE DLLs that conflict in the same process.  
**Fix:** Process isolation — gmsh runs in `_gmsh_worker.py` subprocess with no VTK loaded.

### 5.4 UI Freeze at 8% During Import

**Symptom:** Progress bar stuck at 8%, window unresponsive until subprocess finished.  
**Root cause:** `subprocess.run()` blocks the main thread entirely — no `processEvents()` calls.  
**Fix:** Replaced with `subprocess.Popen()` + polling loop. Worker writes `PROGRESS:` lines to stderr. Parent reads them via a background thread (Windows doesn't support `selectors` on pipes) and calls `progress_callback()` which pumps the Qt event loop every ~150ms.

### 5.5 600-Second Timeout Too Short

**Symptom:** `CADImportError: Tessellation of 'CN-06-13-00.stp' timed out after 600 seconds.`  
**Root cause:** Complex STEP assemblies can take 30+ minutes to tessellate.  
**Fix:** Timeout increased to 3600 seconds (1 hour).

### 5.6 SyntaxWarnings at Startup (`\c`, `\p`)

**Symptom:** `<string>:1: SyntaxWarning: invalid escape sequence '\c'` on every launch.  
**Root cause:** `PyFoam/Infrastructure/Configuration.py` line 85 used `eval()` to build a list from Windows paths containing backslashes (`C:\Users\...\caseBuilderDescriptions`).  
**Fix:** Replaced `eval('["'+...+'"]')` with a direct Python list `[path.curdir, path.join(...)]`. Also converted regex patterns at lines 48–50 and 692 to raw strings.

## 6. Progress Reporting Protocol

The worker reports progress to the parent via **stderr** using a simple line protocol:

```
PROGRESS:<phase>:<percent>:<detail>\n
```

| Phase | Percent | Description |
|-------|---------|-------------|
| `load` | 5 | Reading the CAD file |
| `sync` | 15 | Synchronising OCC model |
| `mesh` | 25 | Starting tessellation |
| `mesh` | 60 | Tessellation complete |
| `write` | 65–95 | Writing per-surface STL files |
| `done` | 100 | Complete |

The parent maps these to a 0–100% progress bar via the `cad_progress` callback in `geometry_page.py`.

## 7. Testing

Verified end-to-end:

1. **Syntax check:** All modified files pass `py_compile` with `-W error::SyntaxWarning`
2. **Runtime import:** `from baramMesh.view.geometry.cad_utility import CADImporter` succeeds
3. **Functional test:** Created a BREP box via gmsh → imported through `CADImporter` → subprocess tessellation → 6 faces, 540 triangles, 1 closed volume
4. **Progress callbacks:** 9 callbacks fired with real phase descriptions and monotonically increasing percentages
5. **gmsh availability:** `check_gmsh_available()` correctly detects gmsh via subprocess probe without loading DLLs
