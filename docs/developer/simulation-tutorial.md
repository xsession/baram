# BARAM Simulation Tutorial — Mesh to Flow (Developer Guide)

A step-by-step guide to running a complete CFD simulation using **BaramMesh** → **BaramFlow** from this development checkout.

---

## Prerequisites

### 1. Dev environment

```powershell
.\bootstrap-dev.ps1          # creates venv, installs deps, generates Qt resources
```

### 2. OpenFOAM solvers (required for mesh generation and solving)

The `solvers/` directory is **not included in the git repository**. BARAM expects NextFOAM-compiled OpenFOAM executables (`blockMesh.exe`, `snappyHexMesh.exe`, `checkMesh.exe`, solver binaries, etc.) in this layout:

```
<repo>/solvers/
    openfoam/
        bin/      ← solver and utility executables
        lib/      ← shared libraries
        lib/msmpi ← MS-MPI libraries (Windows only)
        etc/      ← OpenFOAM system config
    mingw64/      ← MinGW runtime (Windows only)
        bin/
        lib/
```

**Option A — Install the official BARAM release** (easiest):

1. Download the Windows installer from <https://baramcfd.org/download/>
2. Install it (e.g. to `C:\Program Files\BARAM`)
3. Copy (or symlink) the `solvers` folder into this repo:
   ```powershell
   # Example — adjust the source path to match your install location:
   New-Item -ItemType Junction -Path "C:\GIT\baram\solvers" `
            -Target "C:\Program Files\BARAM\solvers"
   ```

**Option B — Point to an existing install with env vars:**

```powershell
$env:BARAM_OPENFOAM_BIN = "C:\Program Files\BARAM\solvers\openfoam\bin"
# or
$env:BARAM_OPENFOAM_DIR = "C:\Program Files\BARAM\solvers\openfoam"
```

**Option C — Build NextFOAM from source** (Linux only):

See <https://github.com/nextfoam/nextfoam-cfd> for build instructions.

### 3. MS-MPI (Windows, required for parallel runs)

Install MS-MPI ≥ 10.0 from <https://docs.microsoft.com/en-us/message-passing-interface/microsoft-mpi>.

### 4. ParaView (optional, for post-processing)

Download from <https://www.paraview.org/download/>.  
Configure in BaramFlow via **Settings → ParaView**.

---

## Part 1 — Mesh Generation with BaramMesh

### Launch

```powershell
.\baramMesh.ps1
# or from VS Code: Run Task → "Run: baramMesh"
```

### Step 1: Create / Open Project

1. On the start screen, click **New Project**.
2. Choose a project name and location (creates a `.bm` folder).
3. The main window opens showing the **Geometry** step.

### Step 2: Geometry — Import your CAD/STL

1. Click **Import** in the geometry panel.
2. Select your geometry file(s):
   - **STL** files — imported directly; optionally set a **Feature Angle** to split surfaces at sharp edges
   - **STEP / IGES / BREP** files — auto-tessellated via `gmsh` (choose Coarse / Medium / Fine quality)
3. Each imported shape appears as **volumes** and **surfaces** in the geometry tree.
4. For each surface, set the **CFD Type**:
   | Type | Use |
   |------|-----|
   | **Boundary** | External wall, inlet, outlet |
   | **Interface** | Inter-region contact (for multi-region / CHT) |
   | **Cell Zone** | Marks a volume zone (porous, MRF, etc.) |
   | **None** | Ignore this surface |
5. Optionally **Add** primitive shapes (Hex, Cylinder, Sphere, Hex6) as bounding boxes or refinement regions.

> **Tip:** Use a **Hex6** shape as your mesh bounding box — it gives you full control over the domain extents.

### Step 3: Region — Define mesh regions

1. Click the **Region** step in the sidebar.
2. Add **region points** — each is an (x, y, z) coordinate inside the volume you want meshed.
   - **Single-region** (most cases): one point inside the flow domain.
   - **Multi-region** (conjugate heat transfer): one point per distinct solid/fluid region.
3. Validate: points must be inside the geometry bounding box; multi-region needs at least one interface.

### Step 4: Base Grid — Background hex mesh

1. Click the **Base Grid** step.
2. Set the **bounding box** (auto-fills from geometry, or use a Hex6 shape).
3. Set **number of cells** in X, Y, Z — watch the computed cell size.
   - Rule of thumb: start with cells ≈ 5–10× the smallest feature size.
4. Click **Generate**.

**What runs behind the scenes:**

| OpenFOAM Utility | Purpose |
|------------------|---------|
| `blockMesh` | Creates the structured background hex grid |
| `decomposePar` | Decomposes for parallel (if > 1 core) |
| `checkMesh` | Computes quality metrics |

The mesh appears in the 3D view. Inspect it before proceeding.

### Step 5: Castellation — Refine and carve

1. Click the **Castellation** step.
2. Configure:
   - **Number of cells between levels** — controls how gradually refinement transitions
   - **Feature angle** — edges sharper than this get refined
3. Add **Surface Refinement Groups** — set min/max refinement levels per surface group.
4. Add **Volume Refinement Groups** — refine inside specific volumes.
5. Click **Refine** (or use **Finish** to auto-run remaining steps).

**Runs:** `snappyHexMesh` (castellation phase) → `checkMesh`

### Step 6: Snap — Conform to geometry

1. Click the **Snap** step.
2. Configure snapping parameters (defaults are usually fine):
   - Smoothing iterations, relaxation factors
   - **Feature Snap Type**: Explicit (uses extracted feature edges) or Implicit
3. Optionally configure **Buffer Layers** for surface smoothing.
4. Click **Snap**.

**Runs:** `snappyHexMesh` (snap phase) → `checkMesh`

### Step 7: Boundary Layer — Add prism layers

1. Click the **Boundary Layer** step.
2. Add **Layer Groups** — assign wall surfaces to groups:
   - Set **number of layers** (e.g. 3–5 for RANS, more for wall-resolved LES)
   - Set **thickness specification** (final layer thickness, expansion ratio, etc.)
3. Click **Apply**.

**Runs:** `snappyHexMesh` (addLayers phase) → `checkMesh`

> **Tip:** Check mesh quality after each step. Look for low orthogonality, high skewness, and negative volumes in the console output.

### Step 8: Export — Send mesh to BaramFlow

1. Click the **Export** step.
2. Choose export type:
   - **3D Export** — standard (most common)
   - **2D Plane Export** — for planar 2D simulations
   - **2D Wedge Export** — for axisymmetric problems
3. Choose an output path (`.bf` suffix — this becomes a BaramFlow project).
4. Optionally check **"Open in BaramFlow"** to launch BaramFlow automatically.
5. Click **OK**.

**Runs (as needed):** `splitMeshRegions`, `topoSet`, `createPatch`, `reconstructPar`, `extrudeMesh`, `collapseEdges`

---

## Part 2 — Flow Simulation with BaramFlow

### Launch

```powershell
.\baramFlow.ps1
# or from VS Code: Run Task → "Run: baramFlow"
```

If you exported from BaramMesh with "Open in BaramFlow", it opens automatically.  
Otherwise: **Open** the `.bf` project folder, or run the **Case Wizard** for a new project.

### Case Wizard (new project)

| Step | What to set |
|------|-------------|
| **Workspace** | Project name and folder (mesh path pre-filled if from BaramMesh) |
| **Solver Type** | **Pressure-based** (incompressible / low-speed) or **Density-based** (transonic / supersonic) |
| **Multiphase** | Off (single phase) or Volume of Fluid (free surface / two-phase) |
| **Gravity** | Set gravity vector if multiphase is on |

### Step 1: Setup → General

- **Time**: Steady or Transient
- **Gravity**: Direction vector (x, y, z)
- **Operating Pressure**: Reference pressure in Pa

### Step 2: Setup → Models

Configure physics:

| Model | Typical choices |
|-------|----------------|
| **Turbulence** | k-ε (general), k-ω SST (wall-bounded), Spalart-Allmaras (external aero), Laminar (low Re) |
| **Energy** | Enable if temperature matters |
| **Multiphase** | Set during wizard |
| **Species** | Enable for mixing/combustion |

### Step 3: Setup → Materials

1. Click **Add** to import materials from the built-in database.
2. **Edit** material properties:
   - Density (constant, perfect gas, polynomial…)
   - Viscosity (constant, Sutherland, non-Newtonian…)
   - Thermal conductivity, specific heat, etc.

### Step 4: Setup → Cell Zone Conditions

For each cell zone in the mesh:
- Assign material (for multi-region / multi-material)
- Set special zone types: **MRF** (rotating), **Porous**, **Sliding Mesh**, source terms

### Step 5: Setup → Boundary Conditions

For **every boundary** in the mesh, set the type and values:

| Category | Common Types |
|----------|-------------|
| **Inlet** | Velocity Inlet (set U), Flow Rate Inlet, Pressure Inlet |
| **Outlet** | Pressure Outlet (set p), Outflow |
| **Wall** | Wall (no-slip, with/without heat flux) |
| **Symmetry** | Symmetry |
| **Other** | Cyclic, Empty (2D), Wedge (axisym) |

For each type, fill in velocity, pressure, temperature, turbulence values as prompted.

### Step 6: Setup → Reference Values

Set reference values for computing force/drag coefficients:
- Reference Area, Length, Velocity, Density, Pressure

### Step 7: Solution → Numerical Conditions

- **Pressure-Velocity Coupling**: SIMPLE (steady) or SIMPLEC
- **Discretization Schemes**: 1st order (stable) → 2nd order (accurate)
- **Under-Relaxation Factors**: lower = more stable, higher = faster convergence
- **Convergence Criteria**: residual targets (e.g. 1e-6 for steady)

### Step 8: Solution → Monitors (optional)

Add monitors to track convergence:
- **Force** monitor on an airfoil/body surface (lift, drag)
- **Point** monitor at a location (velocity, pressure)
- **Surface** monitor (averaged values on a plane)

### Step 9: Solution → Initialization

1. Set initial field values per region (velocity, pressure, temperature, turbulence).
2. Optionally add **Sections** for spatially varying initialization.
3. Click **Initialize** — this writes all OpenFOAM dictionaries and sets initial fields.

**Runs:** `setFields` (if sections are defined)

### Step 10: Solution → Run Conditions

| Setting | Steady | Transient |
|---------|--------|-----------|
| **Iterations / End Time** | Number of iterations (e.g. 1000–5000) | End time in seconds |
| **Time Step** | N/A | Fixed or Adaptive (set max Courant number) |
| **Report Interval** | Every N steps | Every N seconds |
| **Data Write** | Retain last N results | Retain last N results |

### Step 11: Solution → Run

1. Click **Start Calculation**.
2. Watch the **Residuals** chart — all residuals should decrease and flatten.
3. Watch **Monitor** plots — physical quantities should converge to steady values.
4. **Console** shows solver output in real-time.

**What runs:**
- OpenFOAM dictionaries are generated automatically
- If parallel: `decomposePar` splits the case
- The solver is launched (auto-selected based on your physics):

| Physics | Steady Solver | Transient Solver |
|---------|--------------|-----------------|
| Incompressible / general | `buoyantSimpleNFoam` | `buoyantPimpleNFoam` |
| Multi-region (CHT) | `chtMultiRegionSimpleNFoam` | `chtMultiRegionPimpleNFoam` |
| VOF (two-phase) | `interFoam` | `interFoam` |
| Density-based (supersonic) | `TSLAeroFoam` | `UTSLAeroFoam` |

### Step 12: Results → Post-processing

1. **Scaffolds**: Create visualization surfaces (planes, iso-surfaces, lines).
2. **Graphics**: Map field data onto surfaces with colormaps.
3. **Reports**: Extract quantitative data (forces, point/surface/volume averages).
4. **ParaView**: Use **External Tools → ParaView** for advanced visualization.

---

## Quick-Reference Checklist

```
□ bootstrap-dev.ps1 completed
□ OpenFOAM solvers available (solvers/ dir or BARAM_OPENFOAM_BIN set)
□ MS-MPI installed (for parallel)

BaramMesh:
  □ Geometry imported, CFD types assigned
  □ Region point(s) placed
  □ Base grid generated (blockMesh)
  □ Castellation refined (snappyHexMesh)
  □ Snap completed
  □ Boundary layers added
  □ Exported to .bf project

BaramFlow:
  □ Solver type & models configured
  □ Materials defined
  □ All boundaries have conditions set
  □ Numerical conditions reviewed
  □ Fields initialized
  □ Run conditions set (iterations/time)
  □ Calculation started & converged
  □ Results extracted
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `OpenFOAM executable not found: .../blockMesh.exe` | No solvers directory | Install BARAM or set `BARAM_OPENFOAM_BIN` env var |
| `MPI not available` | MS-MPI not installed | Install MS-MPI ≥ 10.0; or set cores to 1 |
| `checkMesh` reports negative volumes | Bad mesh quality | Reduce refinement levels, increase smoothing |
| Residuals diverge | Unstable numerics | Lower under-relaxation, switch to 1st-order schemes, check BCs |
| `Shiboken::Conversions` warnings | PySide6/VTK interop | Cosmetic; safe to ignore |
