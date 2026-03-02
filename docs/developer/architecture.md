# Architecture

## System Overview

BARAM is a GUI-driven CFD (Computational Fluid Dynamics) application built
on OpenFOAM solvers.  It consists of two main applications:

- **BaramMesh** — geometry import (STL, STEP, IGES, BREP), mesh generation
  via snappyHexMesh, and mesh export.
- **BaramFlow** — CFD case setup, solver execution, monitoring, and
  post-processing.

## Runtime Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Layer (PySide6 / Qt 6)                │
│  - Dialogs, widgets, rendering views (VTK)                  │
│  - Async event loop (qasync)                                │
├─────────────────────────────────────────────────────────────┤
│                   Domain Layer (Python)                      │
│  - Case configuration, geometry management                  │
│  - CAD import & tessellation (Gmsh)                         │
│  - Mesh quality analysis                                    │
│  - Enterprise: logging, configuration, validation           │
├─────────────────────────────────────────────────────────────┤
│                Integration Layer (OpenFOAM)                  │
│  - snappyHexMesh, blockMesh, checkMesh                      │
│  - Mesh converters (fluentToFoam, ccmToFoam, etc.)          │
│  - Solvers (simpleFoam, pimpleFoam, etc.)                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Subsystems

### Geometry Import Pipeline

Geometry files are imported through format-specific backends:

| Format | Backend | Output |
|--------|---------|--------|
| STL | `vtkSTLReader` | `vtkPolyData` → `StlSurface` |
| STEP/IGES/BREP | Gmsh + OCC | `vtkPolyData` → `StlSurface` |
| Primitives | VTK generators | `vtkPolyData` |

All formats produce the same `StlSurface` interface for downstream processing.

### Data / Config

- `coredb/` — BaramFlow case configuration state (CoreDB, schema-validated)
- `baramMesh/db/` — BaramMesh HDF5 project database (geometry polydata + YAML config)
- `libbaram/simple_db/` — Generic schema-validated database abstraction
- `libbaram/configuration.py` — Centralised application configuration

### Enterprise Infrastructure

- `libbaram/logging_config.py` — Structured logging with rotation and correlation IDs
- `libbaram/configuration.py` — Layered configuration (defaults → file → env vars)
- `libbaram/exception.py` — Structured exception hierarchy with error codes

### Rendering

VTK-based 3D rendering for geometry preview and mesh display.
Actors are managed per geometry entity with selection and visibility control.

## Data Flow

```
Geometry files  ──▶  Import pipeline  ──▶  HDF5 database
                                              │
                                              ▼
                                     snappyHexMesh config
                                              │
                                              ▼
                                     OpenFOAM case directory
                                              │
                                              ▼
                                     BaramFlow project
```

## Dependencies

### Runtime
- Python 3.11+, PySide6 (Qt 6), VTK 9.5, qasync
- h5py, numpy, pandas, matplotlib, lxml, xmlschema
- PyYAML, pyqtgraph, PySide6-QtAds

### Optional
- `gmsh` — STEP/IGES/BREP CAD file import

### Build
- PyInstaller 6.12 — binary distribution

![Data paths](../assets/diagrams/data-paths.svg)
