# STEP / IGES / BREP File Handling

## Overview

BARAM supports import of industry-standard CAD interchange formats:

| Format | Extensions | Standard |
|--------|-----------|----------|
| **STEP** | `.step`, `.stp` | ISO 10303 AP203/AP214 |
| **IGES** | `.iges`, `.igs` | ANSI Y14.26M |
| **BREP** | `.brep`, `.brp` | OpenCascade native |

CAD files contain exact (B-Rep) geometry — smooth curves and surfaces
represented mathematically.  For CFD meshing with snappyHexMesh, these
must be **tessellated** (approximated) into triangle meshes.  BARAM
automates this process using the [Gmsh](https://gmsh.info/) library.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  STEP / IGES │────▶│   Gmsh OCC   │────▶│  vtkPolyData     │
│  BREP file   │     │  Tessellator │     │  (tri surfaces)  │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │  StlSurface      │
                                          │  (compatible)     │
                                          └────────┬─────────┘
                                                   │
                           ┌───────────────────────┼───────────────┐
                           │                       │               │
                  ┌────────▼───────┐    ┌──────────▼──────┐   ┌────▼─────┐
                  │ Volume         │    │  VTK Rendering  │   │  HDF5    │
                  │ Identification │    │  Display        │   │  Storage │
                  └────────────────┘    └─────────────────┘   └──────────┘
```

### Key design decision

The CAD importer produces `StlSurface` objects — the same data structure
used by the STL importer.  This means **all downstream code works unchanged**:
database storage, VTK rendering, snappyHexMesh export, volume identification.

## Dependency

CAD import requires the `gmsh` Python package:

```bash
pip install gmsh
```

Gmsh is an **optional** dependency.  If not installed:
- The import dialog still opens and shows STL as the available format.
- Selecting a STEP/IGES/BREP file displays a clear error with install
  instructions.

## Tessellation Quality

Three quality presets are available in the import dialog:

| Preset | Deflection | Angle | Use case |
|--------|-----------|-------|----------|
| **Coarse** | 0.01 | 45° | Quick preview, early-stage design |
| **Medium** | 0.001 | 30° | Balanced quality / performance |
| **Fine** | 0.0001 | 15° | Production meshes, validation |

### Parameters explained

- **Deflection** (chord tolerance): Maximum distance between the true
  surface and the approximating triangle edge.  Smaller = finer mesh.
- **Angle**: Maximum angular deviation between adjacent facets.  Controls
  smoothness on curved regions.
- **Curvature elements**: Minimum number of mesh elements per 2π of
  curvature.  Higher = better circular arc approximation.

### Programmatic control

```python
from baramMesh.view.geometry.cad_utility import CADImporter, TessellationParams

params = TessellationParams(
    deflection=0.0005,
    angle=20.0,
    curvature_elements=18,
)

importer = CADImporter()
importer.load([Path("housing.step")], params=params)
volumes, surfaces = importer.identifyVolumes()
```

## Multi-body STEP files

STEP files often contain multiple solids (e.g., an assembly).  BARAM
handles this automatically:

1. Each solid in the STEP file becomes a separate volume group.
2. Surfaces belonging to the same solid share a common identifier.
3. Volume identification (closed surface detection) runs per-solid,
   then across all remaining surfaces.

## Error handling

| Error | Cause | User action |
|-------|-------|-------------|
| `GmshNotAvailableError` | `gmsh` not installed | `pip install gmsh` |
| `CADImportError` | Corrupt/unsupported file | Check file, try different format |
| Zero triangles | Degenerate geometry | Increase tessellation quality |

## Import statistics

Every CAD import generates detailed statistics (logged and optionally
displayed):

```
CAD Import: housing.step
  Format          : step
  Solids/Shells   : 3 / 42
  Faces           : 42
  Triangles       : 125,430
  Nodes           : 62,890
  Time            : 2.31s
  Bounding box    : (-0.1, -0.05, -0.2, 0.1, 0.05, 0.2)
```

## File format notes

### STEP (ISO 10303)
- Most widely supported CAD interchange format.
- Preserves topology, geometry, and product data.
- AP203: Configuration-controlled 3D design.
- AP214: Automotive design (more metadata).
- **Recommended** for BARAM import.

### IGES
- Legacy format, widely supported but less robust than STEP.
- No topology information — may produce disconnected surfaces.
- Surface trimming can cause gaps.
- Use STEP when possible.

### BREP
- OpenCascade native format.
- Compact and lossless for OCC geometry.
- Useful for CAD tools built on OpenCascade (FreeCAD, etc.).
