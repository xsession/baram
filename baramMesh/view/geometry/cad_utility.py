#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CAD file (STEP/IGES/BREP) import utility for BaramMesh.

This module provides enterprise-grade STEP, IGES, and BREP file handling
using the Gmsh meshing library as the CAD kernel. It tessellates CAD B-Rep
geometry into triangulated surface meshes (vtkPolyData) compatible with the
existing STL-based geometry pipeline.

Supported formats
-----------------
- STEP  (.step, .stp)         — ISO 10303 AP203/AP214
- IGES  (.iges, .igs)         — Initial Graphics Exchange Specification
- BREP  (.brep, .brp)         — OpenCascade native boundary representation

Architecture
------------
CADImporter produces ``StlSurface`` objects so that downstream code
(volume identification, database storage, VTK rendering) requires **zero**
changes.  The tessellation quality is controlled by *deflection* (chord
tolerance) and *angle* (angular tolerance) parameters that map directly to
the Gmsh meshing options.

Example
-------
>>> from baramMesh.view.geometry.cad_utility import CADImporter, CADImportError
>>> importer = CADImporter()
>>> importer.load([Path("housing.step")], deflection=0.001, angle=30.0)
>>> volumes, surfaces = importer.identifyVolumes()

Dependencies
------------
- ``gmsh`` >= 4.11  (``pip install gmsh``)
- ``numpy``
- ``vtkmodules`` (provided by VTK)

Notes
-----
Gmsh is initialised and finalised per-file to guarantee clean state and
prevent memory leaks in long-running sessions.
"""

from __future__ import annotations

import logging
import re
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkIdList, vtkIntArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkAppendPolyData, vtkCleanPolyData
from vtkmodules.vtkFiltersModeling import vtkSelectEnclosedPoints

from .stl_utility import StlSurface, StringIndex, isClosed, composeVolume

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

# Supported CAD file extensions (lower-cased, with leading dot)
CAD_EXTENSIONS = frozenset({'.step', '.stp', '.iges', '.igs', '.brep', '.brp'})
STL_EXTENSIONS = frozenset({'.stl'})


def is_cad_file(path: Path) -> bool:
    """Return *True* if *path* has a recognised CAD extension."""
    return path.suffix.lower() in CAD_EXTENSIONS


def is_stl_file(path: Path) -> bool:
    """Return *True* if *path* has an STL extension."""
    return path.suffix.lower() in STL_EXTENSIONS


class CADFormat(Enum):
    """Enumeration of supported CAD interchange formats."""
    STEP = 'step'
    IGES = 'iges'
    BREP = 'brep'
    UNKNOWN = 'unknown'

    @classmethod
    def from_path(cls, path: Path) -> 'CADFormat':
        ext = path.suffix.lower()
        if ext in ('.step', '.stp'):
            return cls.STEP
        if ext in ('.iges', '.igs'):
            return cls.IGES
        if ext in ('.brep', '.brp'):
            return cls.BREP
        return cls.UNKNOWN


# ---------------------------------------------------------------------------
# Tessellation parameters
# ---------------------------------------------------------------------------

@dataclass
class TessellationParams:
    """Parameters controlling CAD-to-mesh tessellation quality.

    Attributes
    ----------
    deflection : float
        Maximum chord deviation (distance between the true surface and the
        approximating triangle edge).  Smaller values yield finer meshes.
        A reasonable default for millimetre-scale parts is 0.001.
    angle : float
        Maximum angular deviation in degrees between adjacent facets.
        Controls smoothness on curved regions.  Default 30°.
    min_edge_length : float or None
        Hard lower bound on triangle edge length.  Set to *None* to let Gmsh
        decide automatically based on *deflection*.
    max_edge_length : float or None
        Hard upper bound on triangle edge length.  Set to *None* for
        automatic sizing.
    curvature_elements : int
        Minimum number of mesh elements per 2π of curvature.
        Higher values better capture circular arcs.  Default 12.
    algorithm : int
        Gmsh 2-D meshing algorithm. ``6`` = Frontal-Delaunay (recommended
        for surface tessellation).
    """
    deflection: float = 0.001
    angle: float = 30.0
    min_edge_length: Optional[float] = None
    max_edge_length: Optional[float] = None
    curvature_elements: int = 12
    algorithm: int = 6

    # ------------------------------------------------------------------
    # Enterprise presets
    # ------------------------------------------------------------------
    @classmethod
    def coarse(cls) -> 'TessellationParams':
        """Fast preview quality."""
        return cls(deflection=0.01, angle=45.0, curvature_elements=6)

    @classmethod
    def medium(cls) -> 'TessellationParams':
        """Balanced quality / performance (default)."""
        return cls()

    @classmethod
    def fine(cls) -> 'TessellationParams':
        """High quality for production meshes."""
        return cls(deflection=0.0001, angle=15.0, curvature_elements=24)


# ---------------------------------------------------------------------------
# Import statistics
# ---------------------------------------------------------------------------

@dataclass
class CADImportStats:
    """Statistics collected during a CAD import operation.

    Useful for logging, auditing, and quality assurance.
    """
    file_path: str = ''
    format: str = ''
    num_solids: int = 0
    num_shells: int = 0
    num_faces: int = 0
    total_triangles: int = 0
    total_nodes: int = 0
    elapsed_seconds: float = 0.0
    bounding_box: Tuple[float, ...] = ()
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            f"CAD Import: {self.file_path}",
            f"  Format          : {self.format}",
            f"  Solids/Shells   : {self.num_solids} / {self.num_shells}",
            f"  Faces           : {self.num_faces}",
            f"  Triangles       : {self.total_triangles:,}",
            f"  Nodes           : {self.total_nodes:,}",
            f"  Time            : {self.elapsed_seconds:.2f}s",
        ]
        if self.bounding_box:
            lines.append(f"  Bounding box    : {self.bounding_box}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CADImportError(Exception):
    """Raised when a CAD file cannot be imported or tessellated."""
    pass


class GmshNotAvailableError(CADImportError):
    """Raised when the ``gmsh`` Python package is not installed."""

    def __init__(self):
        super().__init__(
            "The 'gmsh' package is required for STEP/IGES/BREP import. "
            "Install it with:  pip install gmsh"
        )


# ---------------------------------------------------------------------------
# Internal: gmsh ↔ VTK conversion
# ---------------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """Sanitise a CAD entity name for OpenFOAM compatibility.

    Replaces non-alphanumeric characters with underscores and ensures the
    name does not start with a digit.
    """
    if not name:
        return name
    sanitized = re.sub(r'\W+', '_', name, flags=re.ASCII)
    if sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized


def _gmsh_surface_to_polydata(gmsh_mod, surface_tag: int) -> Optional[vtkPolyData]:
    """Convert a single Gmsh surface entity to a *vtkPolyData*.

    Parameters
    ----------
    gmsh_mod
        Reference to the ``gmsh.model`` module.
    surface_tag : int
        Gmsh entity tag (dimension 2).

    Returns
    -------
    vtkPolyData or None
        Triangulated surface, or *None* if the surface has no mesh.
    """
    try:
        node_tags, node_coords, _ = gmsh_mod.mesh.getNodes(2, surface_tag, includeBoundary=True)
    except Exception:
        return None

    if len(node_tags) == 0:
        return None

    coords = np.asarray(node_coords, dtype=np.float64).reshape(-1, 3)
    tag_to_local = {int(t): i for i, t in enumerate(node_tags)}

    elem_types, _, elem_node_tags = gmsh_mod.mesh.getElements(2, surface_tag)

    # Collect only triangles (type 2) and quads (type 3); quads are split.
    all_tris: List[Tuple[int, int, int]] = []
    for etype, enodes in zip(elem_types, elem_node_tags):
        if etype == 2:  # 3-node triangle
            for i in range(0, len(enodes), 3):
                n0 = tag_to_local.get(int(enodes[i]))
                n1 = tag_to_local.get(int(enodes[i + 1]))
                n2 = tag_to_local.get(int(enodes[i + 2]))
                if n0 is not None and n1 is not None and n2 is not None:
                    all_tris.append((n0, n1, n2))
        elif etype == 3:  # 4-node quad → split into 2 triangles
            for i in range(0, len(enodes), 4):
                ns = [tag_to_local.get(int(enodes[i + j])) for j in range(4)]
                if all(n is not None for n in ns):
                    all_tris.append((ns[0], ns[1], ns[2]))
                    all_tris.append((ns[0], ns[2], ns[3]))

    if not all_tris:
        return None

    # Build VTK structures
    points = vtkPoints()
    points.SetNumberOfPoints(len(coords))
    for idx, (x, y, z) in enumerate(coords):
        points.SetPoint(idx, x, y, z)

    triangles = vtkCellArray()
    id_list = vtkIdList()
    id_list.SetNumberOfIds(3)
    for t in all_tris:
        id_list.SetId(0, t[0])
        id_list.SetId(1, t[1])
        id_list.SetId(2, t[2])
        triangles.InsertNextCell(id_list)

    poly = vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(triangles)

    return poly


def _get_entity_name(gmsh_mod, dim: int, tag: int) -> str:
    """Retrieve the name assigned to a Gmsh entity, if any."""
    try:
        name = gmsh_mod.getEntityName(dim, tag)
        return _sanitize_name(name.strip()) if name else ''
    except Exception:
        return ''


def _compute_bounding_box(gmsh_mod) -> Tuple[float, ...]:
    """Return the (xmin, ymin, zmin, xmax, ymax, zmax) bounding box."""
    try:
        bb = gmsh_mod.getBoundingBox(-1, -1)
        return tuple(bb)
    except Exception:
        return ()


# ---------------------------------------------------------------------------
# CADImporter — the main public class
# ---------------------------------------------------------------------------

class CADImporter:
    """Enterprise-grade CAD file importer for BaramMesh.

    Converts STEP / IGES / BREP geometry into triangulated ``StlSurface``
    objects that seamlessly integrate with the existing BaramMesh geometry
    pipeline.

    Typical usage
    -------------
    >>> importer = CADImporter()
    >>> importer.load(files, params=TessellationParams.medium())
    >>> volumes, surfaces = importer.identifyVolumes()

    The resulting ``volumes`` and ``surfaces`` are identical in structure
    to those produced by ``StlImporter``, so all downstream code (database
    storage, VTK rendering, snappyHexMesh export) works unchanged.
    """

    def __init__(self):
        self._stringIndices = StringIndex()
        self._surfaceList: List[StlSurface] = []
        self._stats: List[CADImportStats] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def stats(self) -> List[CADImportStats]:
        """Import statistics for the most recent :meth:`load` call."""
        return list(self._stats)

    def load(
        self,
        files: Sequence[Path],
        params: Optional[TessellationParams] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[CADImportStats]:
        """Load and tessellate one or more CAD files.

        Parameters
        ----------
        files : sequence of Path
            CAD file paths to import.
        params : TessellationParams, optional
            Tessellation quality parameters.  Defaults to
            ``TessellationParams.medium()``.
        progress_callback : callable, optional
            ``callback(message: str, fraction: float)`` called to report
            progress.  *fraction* ranges from 0.0 to 1.0.

        Returns
        -------
        list of CADImportStats
            Per-file import statistics.

        Raises
        ------
        GmshNotAvailableError
            If the ``gmsh`` package is not installed.
        CADImportError
            If any file fails to load or tessellate.
        """
        if params is None:
            params = TessellationParams.medium()

        self._stringIndices.clear()
        self._surfaceList.clear()
        self._stats.clear()

        total = len(files)
        for idx, f in enumerate(files):
            if progress_callback:
                progress_callback(f"Importing {f.name}…", idx / total)

            stat = self._import_cad_file(Path(f), params)
            self._stats.append(stat)
            logger.info(stat.summary())

        if progress_callback:
            progress_callback("Import complete.", 1.0)

        return list(self._stats)

    def identifyVolumes(self):
        """Identify closed volumes and open surfaces.

        Delegates to the same algorithm used for STL surfaces, ensuring
        consistent behaviour across all geometry formats.

        Returns
        -------
        volumes : list[list[StlSurface]]
            Groups of surfaces that form closed volumes.
        surfaces : list[StlSurface]
            Open (non-closed) surfaces.
        """
        volumes: List[List[StlSurface]] = []
        surfaces: List[StlSurface] = []

        file_names = set(s.fName for s in self._surfaceList)
        for fName in file_names:
            file_surfaces = [s for s in self._surfaceList if s.fName == fName]
            s_indices = set(s.sIndex for s in file_surfaces)

            remains: List[StlSurface] = []
            for sIndex in s_indices:
                solid_surfaces = [s for s in file_surfaces if s.sIndex == sIndex]
                v_list, s_list = composeVolume(solid_surfaces)
                volumes.extend(v_list)
                remains.extend(s_list)

            if isClosed(remains):
                volumes.append(remains)
            else:
                surfaces.extend(remains)

        # Check if all remaining surfaces form a closed volume
        if isClosed(surfaces):
            volumes.append(surfaces)
            surfaces = []

        return volumes, surfaces

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _import_cad_file(
        self,
        path: Path,
        params: TessellationParams,
    ) -> CADImportStats:
        """Import a single CAD file and populate ``_surfaceList``."""

        try:
            import gmsh
        except ImportError:
            raise GmshNotAvailableError()

        cad_format = CADFormat.from_path(path)
        if cad_format == CADFormat.UNKNOWN:
            raise CADImportError(
                f"Unsupported CAD format: {path.suffix}. "
                f"Supported: .step/.stp, .iges/.igs, .brep/.brp"
            )

        if not path.is_file():
            raise CADImportError(f"File not found: {path}")

        stat = CADImportStats(file_path=str(path), format=cad_format.value)
        t0 = time.perf_counter()

        # Gmsh initialisation — one instance per file for clean state
        gmsh.initialize()
        gmsh.option.setNumber("General.Verbosity", 1)  # Warnings only

        try:
            self._configure_gmsh(gmsh, params)
            self._load_and_mesh(gmsh, path, params, stat)
            self._extract_surfaces(gmsh, path, stat)
        except CADImportError:
            raise
        except Exception as exc:
            raise CADImportError(
                f"Failed to import '{path.name}': {exc}"
            ) from exc
        finally:
            try:
                gmsh.finalize()
            except Exception:
                pass

        stat.elapsed_seconds = time.perf_counter() - t0
        return stat

    @staticmethod
    def _configure_gmsh(gmsh, params: TessellationParams) -> None:
        """Apply tessellation parameters to Gmsh global options."""
        gmsh.option.setNumber("Mesh.Algorithm", params.algorithm)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", params.curvature_elements)
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", params.angle / 57.2958)

        if params.min_edge_length is not None:
            gmsh.option.setNumber("Mesh.MeshSizeMin", params.min_edge_length)
        if params.max_edge_length is not None:
            gmsh.option.setNumber("Mesh.MeshSizeMax", params.max_edge_length)

        # Enable adaptive meshing based on curvature
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvatureIsotropic", 1)

    @staticmethod
    def _load_and_mesh(gmsh, path: Path, params: TessellationParams, stat: CADImportStats) -> None:
        """Load CAD file into Gmsh and generate 2-D surface mesh."""
        try:
            gmsh.model.occ.importShapes(str(path))
        except Exception as exc:
            raise CADImportError(f"Gmsh failed to read '{path.name}': {exc}") from exc

        gmsh.model.occ.synchronize()

        # Compute bounding-box-relative mesh sizing if no explicit limits
        stat.bounding_box = _compute_bounding_box(gmsh.model)
        if stat.bounding_box and params.max_edge_length is None:
            bb = stat.bounding_box
            diag = ((bb[3] - bb[0]) ** 2 + (bb[4] - bb[1]) ** 2 + (bb[5] - bb[2]) ** 2) ** 0.5
            if diag > 0:
                auto_max = diag * params.deflection * 100
                auto_min = auto_max * 0.01
                gmsh.option.setNumber("Mesh.MeshSizeMax", auto_max)
                if params.min_edge_length is None:
                    gmsh.option.setNumber("Mesh.MeshSizeMin", auto_min)

        # Collect entity counts
        stat.num_solids = len(gmsh.model.getEntities(3))
        stat.num_shells = len(gmsh.model.getEntities(2))
        stat.num_faces = stat.num_shells

        # Generate 2-D surface mesh
        try:
            gmsh.model.mesh.generate(2)
        except Exception as exc:
            stat.warnings.append(f"Meshing warning: {exc}")
            logger.warning("Gmsh meshing produced warnings for '%s': %s", path.name, exc)

    def _extract_surfaces(self, gmsh, path: Path, stat: CADImportStats) -> None:
        """Extract meshed surfaces from Gmsh model into StlSurface objects."""
        fName = _sanitize_name(path.stem)

        # Get all 2-D entities (surfaces)
        surfaces_2d = gmsh.model.getEntities(2)
        volumes_3d = gmsh.model.getEntities(3)

        # Build mapping: surface_tag → volume_tag (if any)
        surface_to_volume: Dict[int, int] = {}
        for _, vol_tag in volumes_3d:
            try:
                boundaries = gmsh.model.getBoundary([(3, vol_tag)], oriented=False)
                for _, surf_tag in boundaries:
                    surface_to_volume[abs(surf_tag)] = vol_tag
            except Exception:
                pass

        # Group surfaces by their parent volume (or 'unattached')
        volume_groups: Dict[int, List[int]] = {}
        unattached: List[int] = []

        for _, surf_tag in surfaces_2d:
            if surf_tag in surface_to_volume:
                vol_tag = surface_to_volume[surf_tag]
                volume_groups.setdefault(vol_tag, []).append(surf_tag)
            else:
                unattached.append(surf_tag)

        total_tris = 0
        total_nodes = 0

        # Process volume-grouped surfaces: each surface → one StlSurface,
        # sharing a common solid index per volume
        for vol_tag, surf_tags in volume_groups.items():
            vol_name = _get_entity_name(gmsh.model, 3, vol_tag)
            if not vol_name:
                vol_name = f"{fName}_solid{vol_tag}"
            sIndex = self._stringIndices.putString(vol_name)

            for surf_tag in surf_tags:
                poly = _gmsh_surface_to_polydata(gmsh.model, surf_tag)
                if poly is None or poly.GetNumberOfCells() == 0:
                    continue

                surf_name = _get_entity_name(gmsh.model, 2, surf_tag)
                if not surf_name:
                    surf_name = f"{vol_name}_face{surf_tag}"

                n_cells = poly.GetNumberOfCells()
                self._add_index_array(poly, 'fIndex', fName, n_cells)
                self._add_index_array_with_index(poly, 'sIndex', sIndex, n_cells)

                self._surfaceList.append(StlSurface(poly, fName, vol_name, sIndex))

                total_tris += n_cells
                total_nodes += poly.GetNumberOfPoints()

        # Process unattached surfaces
        for surf_tag in unattached:
            poly = _gmsh_surface_to_polydata(gmsh.model, surf_tag)
            if poly is None or poly.GetNumberOfCells() == 0:
                continue

            surf_name = _get_entity_name(gmsh.model, 2, surf_tag)
            if not surf_name:
                surf_name = f"{fName}_face{surf_tag}"

            n_cells = poly.GetNumberOfCells()
            self._add_index_array(poly, 'fIndex', fName, n_cells)
            sIndex = self._add_index_array(poly, 'sIndex', surf_name, n_cells)

            self._surfaceList.append(StlSurface(poly, fName, surf_name, sIndex))

            total_tris += n_cells
            total_nodes += poly.GetNumberOfPoints()

        stat.total_triangles = total_tris
        stat.total_nodes = total_nodes

    def _add_index_array(self, polyData: vtkPolyData, arrayName: str, value: str, count: int) -> int:
        """Add a cell-data integer array mapping to a StringIndex entry."""
        index = self._stringIndices.putString(value)
        array = vtkIntArray()
        array.SetName(arrayName)
        for _ in range(count):
            array.InsertNextValue(index)
        polyData.GetCellData().AddArray(array)
        return index

    def _add_index_array_with_index(self, polyData: vtkPolyData, arrayName: str, index: int, count: int) -> None:
        """Add a cell-data integer array using an existing StringIndex entry."""
        array = vtkIntArray()
        array.SetName(arrayName)
        for _ in range(count):
            array.InsertNextValue(index)
        polyData.GetCellData().AddArray(array)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def check_gmsh_available() -> bool:
    """Return *True* if the ``gmsh`` package can be imported."""
    try:
        import gmsh  # noqa: F401
        return True
    except ImportError:
        return False


def get_supported_formats_filter() -> str:
    """Return a combined file-dialog filter string for all supported formats.

    Includes STL, STEP, IGES, and BREP.
    """
    parts = [
        "All Supported Geometry (*.stl *.step *.stp *.iges *.igs *.brep *.brp)",
        "STL (*.stl)",
    ]
    if check_gmsh_available():
        parts.extend([
            "STEP (*.step *.stp)",
            "IGES (*.iges *.igs)",
            "BREP (*.brep *.brp)",
        ])
    parts.append("All Files (*)")
    return ";;".join(parts)
