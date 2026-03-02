# Geometry Import Guide

## Supported Formats

BaramMesh supports importing geometry from multiple file formats:

### Native Mesh Formats
| Format | Extensions | Notes |
|--------|-----------|-------|
| **STL** | `.stl` | Binary and ASCII. Most common for CFD. |

### CAD Interchange Formats (requires `gmsh`)
| Format | Extensions | Notes |
|--------|-----------|-------|
| **STEP** | `.step`, `.stp` | **Recommended.** ISO 10303. Best topology preservation. |
| **IGES** | `.iges`, `.igs` | Legacy format. Less robust than STEP. |
| **BREP** | `.brep`, `.brp` | OpenCascade native. Useful for FreeCAD exports. |

### Primitive Shapes (built-in)
| Shape | Use case |
|-------|----------|
| **Hexahedron** | Box-shaped refinement zones |
| **Cylinder** | Pipe / bore refinement |
| **Sphere** | Point-source refinement |
| **Hex6** | Bounding box with named faces |

## Importing Geometry

### Step 1: Open the Import Dialog

Click the **Import** button on the Geometry page. The file selection
dialog supports multi-select — you can import several files at once.

### Step 2: Select Files

The dialog shows all supported formats by default:

```
All Supported Geometry (*.stl *.step *.stp *.iges *.igs *.brep *.brp)
```

You can filter by specific format using the dropdown.

> **Tip**: You can mix STL and STEP files in a single import. Each file
> is processed by the appropriate backend automatically.

### Step 3: Configure Import Options

#### For STL files
- **Split Surface**: Check to split the surface by feature angle.
  Default angle: 60°. Useful for separating distinct faces of a geometry.

#### For CAD files (STEP/IGES/BREP)
When CAD files are selected, a **CAD Tessellation Quality** panel appears:

| Preset | Speed | Quality | Use case |
|--------|-------|---------|----------|
| Coarse | Fast | Low | Quick preview, design exploration |
| Medium | Moderate | Good | **Default.** Balanced for most workflows. |
| Fine | Slow | High | Production meshes, validation studies |

### Step 4: Import

Click **OK** to begin import. For large files, a progress indicator shows
the current stage.

After import, the geometry appears in the 3D viewport and the geometry
tree. Each solid body from a STEP file becomes a separate volume group.

## Volume Identification

BARAM automatically identifies closed volumes:

1. Each solid within a file is checked individually.
2. If all surfaces of a solid form a closed shell → it's a **volume**.
3. Remaining open surfaces are checked as a group.
4. If all remaining surfaces form a closed shell → grouped as a volume.
5. Otherwise, they remain as independent **boundary** surfaces.

## Working with STEP Files

### Multi-body STEP files

STEP files from CAD assemblies often contain multiple solid bodies.
BARAM imports each body as a separate volume with named surfaces:

```
housing                    (volume)
├── housing_face1          (surface)
├── housing_face2          (surface)
└── housing_face3          (surface)
impeller                   (volume)
├── impeller_face1         (surface)
└── impeller_face2         (surface)
```

### Tips for best results

1. **Use STEP over IGES** when possible — better topology preservation.
2. **Simplify geometry** in your CAD tool before export — remove small
   fillets, chamfers, and bolt holes if they're not relevant to the flow.
3. **Check units** — BARAM uses metres. If your STEP file uses millimetres,
   you may need to apply a scale factor.
4. **Start with Medium quality** — increase to Fine only if needed.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "gmsh package not installed" | Run `pip install gmsh` |
| Import takes very long | Use Coarse preset, simplify geometry |
| Missing surfaces | Try Fine preset, check CAD file in viewer |
| Disconnected surfaces | Typical with IGES — use STEP instead |
| Zero triangles warning | Degenerate face in CAD — edit in CAD tool |

## Installing CAD Support

CAD file support requires the `gmsh` package:

```bash
pip install gmsh
```

This installs the Gmsh meshing library with OpenCascade backend, adding
STEP/IGES/BREP reading capability. The package is approximately 150 MB.

If `gmsh` is not installed, STL import works normally and the import
dialog only shows STL as an available format.

## Import Statistics

After importing CAD files, statistics are logged:

```
CAD Import: housing.step
  Format          : step
  Solids/Shells   : 3 / 42
  Faces           : 42
  Triangles       : 125,430
  Nodes           : 62,890
  Time            : 2.31s
```

Enable `show_import_statistics` in the configuration to display these
in the UI after import.
