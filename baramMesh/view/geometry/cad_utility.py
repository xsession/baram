#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CAD file (STEP/IGES/BREP) import utility for BaramMesh.

This module provides enterprise-grade STEP, IGES, and BREP file handling
by delegating tessellation to a **subprocess** running the ``_gmsh_worker``
module.  This architecture avoids native DLL conflicts between VTK's and
gmsh's bundled OpenCASCADE libraries which would otherwise cause access-
violation crashes when both are loaded in the same process.

Supported formats
-----------------
- STEP  (.step, .stp)         — ISO 10303 AP203/AP214
- IGES  (.iges, .igs)         — Initial Graphics Exchange Specification
- BREP  (.brep, .brp)         — OpenCascade native boundary representation

Architecture
------------
``CADImporter.load()`` spawns a child Python process
(``_gmsh_worker.py``) for each CAD file.  The worker imports gmsh in a
clean process (no VTK/PySide6 loaded), tessellates the geometry, and
writes one binary STL file per surface entity to a temporary directory.
The parent process then reads those STL files with ``vtkSTLReader`` and
builds ``StlSurface`` objects identical to those produced by
``StlImporter``.

Example
-------
>>> from baramMesh.view.geometry.cad_utility import CADImporter, CADImportError
>>> importer = CADImporter()
>>> importer.load([Path("housing.step")], params=TessellationParams.medium())
>>> volumes, surfaces = importer.identifyVolumes()

Dependencies
------------
- ``gmsh`` >= 4.11  (``pip install gmsh``) — loaded only in subprocess
- ``numpy``
- ``vtkmodules`` (provided by VTK) — used in the main process only
"""

from __future__ import annotations

import importlib.util
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from vtkmodules.vtkCommonCore import vtkIntArray
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import vtkCleanPolyData
from vtkmodules.vtkIOGeometry import vtkSTLReader

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

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON transport to the subprocess."""
        d: dict = {
            'deflection': self.deflection,
            'angle': self.angle,
            'curvature_elements': self.curvature_elements,
            'algorithm': self.algorithm,
        }
        if self.min_edge_length is not None:
            d['min_edge_length'] = self.min_edge_length
        if self.max_edge_length is not None:
            d['max_edge_length'] = self.max_edge_length
        return d


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

    def __init__(self, msg=None):
        super().__init__(
            msg or (
                "The 'gmsh' package is required for STEP/IGES/BREP import. "
                "Install it with:  pip install gmsh"
            )
        )


# ---------------------------------------------------------------------------
# Internal helpers
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


def _worker_module_path() -> str:
    """Return the absolute path to ``_gmsh_worker.py``."""
    return str(Path(__file__).with_name('_gmsh_worker.py'))


# ---------------------------------------------------------------------------
# CADImporter — the main public class
# ---------------------------------------------------------------------------

class CADImporter:
    """Enterprise-grade CAD file importer for BaramMesh.

    Converts STEP / IGES / BREP geometry into triangulated ``StlSurface``
    objects that seamlessly integrate with the existing BaramMesh geometry
    pipeline.

    The tessellation runs in a **subprocess** to avoid native DLL conflicts
    between VTK and gmsh's OpenCASCADE libraries.

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

            stat = self._import_cad_file(Path(f), params, progress_callback)
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
    # Internals — subprocess-based tessellation
    # ------------------------------------------------------------------

    def _import_cad_file(
        self,
        path: Path,
        params: TessellationParams,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> CADImportStats:
        """Import a single CAD file via subprocess tessellation.

        The workflow is:
        1. Validate the file format.
        2. Spawn ``_gmsh_worker.py`` in a child process, supplying a JSON
           job on stdin.
        3. The worker tessellates with gmsh and writes per-surface binary
           STL files into a temporary directory.
        4. Read the STL files back with ``vtkSTLReader`` and populate
           ``_surfaceList``.
        """

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

        # Create a temporary directory for the STL outputs
        tmp_dir = tempfile.mkdtemp(prefix='baram_cad_')
        try:
            result = self._run_worker(path, params, tmp_dir, progress_callback)
            self._process_result(result, path, stat, tmp_dir)
        finally:
            # Clean up temporary files
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

        stat.elapsed_seconds = time.perf_counter() - t0
        return stat

    def _run_worker(
        self,
        path: Path,
        params: TessellationParams,
        tmp_dir: str,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> dict:
        """Spawn the gmsh worker subprocess and return its JSON result."""

        worker_script = _worker_module_path()
        if not Path(worker_script).is_file():
            raise CADImportError(
                f"Internal error: gmsh worker script not found at {worker_script}"
            )

        job = {
            'file': str(path),
            'out_dir': tmp_dir,
            'params': params.to_dict(),
        }
        job_json = json.dumps(job)

        if progress_callback:
            progress_callback(f"Tessellating {path.name}…", 0.05)

        python_exe = sys.executable
        # 1 hour timeout — complex STEP assemblies can take 30+ minutes
        timeout_secs = 3600

        try:
            proc = subprocess.Popen(
                [python_exe, worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
            raise CADImportError(
                f"Failed to launch gmsh subprocess for '{path.name}': {exc}"
            ) from exc

        # Write the job JSON to stdin, then close stdin so the worker starts
        try:
            proc.stdin.write(job_json)
            proc.stdin.close()
        except Exception as exc:
            proc.kill()
            raise CADImportError(
                f"Failed to send job to gmsh subprocess: {exc}"
            ) from exc

        # Poll the subprocess while keeping the UI responsive.
        # The worker writes PROGRESS:<phase>:<pct>:<detail> lines to
        # stderr.  We use a background thread to read them (Windows does
        # not support select() on pipes).
        import time as _time
        import threading
        import queue

        deadline = _time.monotonic() + timeout_secs
        poll_interval = 0.15  # seconds between UI pumps
        last_pct = 0.05
        last_msg = f"Tessellating {path.name}…"
        stderr_lines: list[str] = []  # collect non-progress stderr
        line_queue: queue.Queue[str] = queue.Queue()

        def _stderr_reader():
            """Read stderr line-by-line in a background thread."""
            try:
                for raw in proc.stderr:
                    line_queue.put(raw.rstrip('\n\r'))
            except (ValueError, OSError):
                pass  # pipe closed

        reader_thread = threading.Thread(target=_stderr_reader, daemon=True)
        reader_thread.start()

        while proc.poll() is None:
            if _time.monotonic() > deadline:
                proc.kill()
                proc.wait()
                raise CADImportError(
                    f"Tessellation of '{path.name}' timed out "
                    f"after {timeout_secs} seconds."
                )

            # Drain any lines the reader thread has collected
            while not line_queue.empty():
                try:
                    line = line_queue.get_nowait()
                except queue.Empty:
                    break
                if line.startswith('PROGRESS:'):
                    # Format: PROGRESS:<phase>:<pct>:<detail>
                    parts = line.split(':', 3)
                    if len(parts) >= 3:
                        try:
                            pct_int = int(parts[2])
                            last_pct = max(last_pct, pct_int / 100.0)
                        except ValueError:
                            pass
                        detail = parts[3] if len(parts) > 3 else ''
                        if detail:
                            last_msg = f"{path.name}: {detail}"
                else:
                    stderr_lines.append(line)

            if progress_callback:
                progress_callback(last_msg, last_pct)

            _time.sleep(poll_interval)

        # Wait for the reader thread to finish draining
        reader_thread.join(timeout=5.0)

        # Drain any remaining lines
        while not line_queue.empty():
            try:
                line = line_queue.get_nowait()
                if line.startswith('PROGRESS:'):
                    pass
                else:
                    stderr_lines.append(line)
            except queue.Empty:
                break

        # Read stdout
        stdout_data = proc.stdout.read()
        proc.stdout.close()
        proc.stderr.close()

        if proc.returncode != 0:
            stderr = '\n'.join(stderr_lines).strip() or '(no output)'
            raise CADImportError(
                f"Gmsh subprocess failed for '{path.name}' "
                f"(exit code {proc.returncode}):\n{stderr}"
            )

        # Parse JSON result from stdout
        stdout = stdout_data.strip()
        if not stdout:
            raise CADImportError(
                f"Gmsh subprocess produced no output for '{path.name}'.\n"
                f"stderr: {'  '.join(stderr_lines) if stderr_lines else '(empty)'}"
            )

        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise CADImportError(
                f"Invalid JSON from gmsh subprocess for '{path.name}': {exc}\n"
                f"stdout (first 500 chars): {stdout[:500]}"
            ) from exc

        if progress_callback:
            progress_callback(f"Reading tessellation for {path.name}…", 0.90)

        return result

    def _process_result(
        self,
        result: dict,
        path: Path,
        stat: CADImportStats,
        tmp_dir: str,
    ) -> None:
        """Read STL files produced by the worker and populate surfaces."""

        # Check for errors reported by the worker
        if 'error' in result:
            raise CADImportError(result['error'])

        # Populate statistics
        stat.num_solids = result.get('num_solids', 0)
        stat.num_shells = result.get('num_shells', 0)
        stat.num_faces = result.get('num_faces', 0)
        stat.total_triangles = result.get('total_triangles', 0)
        stat.total_nodes = result.get('total_nodes', 0)
        stat.warnings = result.get('warnings', [])
        bb = result.get('bounding_box', [])
        stat.bounding_box = tuple(bb) if bb else ()

        fName = _sanitize_name(path.stem)
        stl_files = result.get('stl_files', [])

        if not stl_files:
            stat.warnings.append("No surfaces were extracted from the CAD file.")
            logger.warning("No surfaces extracted from '%s'", path.name)
            return

        total_tris = 0
        total_nodes = 0

        for entry in stl_files:
            stl_path = Path(entry['path'])
            solid_name = _sanitize_name(entry.get('solid_name', ''))
            surface_name = _sanitize_name(entry.get('surface_name', ''))

            if not stl_path.is_file():
                logger.warning("Expected STL file not found: %s", stl_path)
                continue

            poly = self._read_stl_file(stl_path)
            if poly is None or poly.GetNumberOfCells() == 0:
                continue

            n_cells = poly.GetNumberOfCells()

            # Add fIndex cell data — file name index
            self._add_index_array(poly, 'fIndex', fName, n_cells)

            # Add sIndex cell data — solid (volume group) index
            if solid_name:
                sIndex = self._stringIndices.putString(solid_name)
                self._add_index_array_with_index(poly, 'sIndex', sIndex, n_cells)
            else:
                sIndex = self._add_index_array(poly, 'sIndex', surface_name, n_cells)

            sName = solid_name or surface_name
            self._surfaceList.append(StlSurface(poly, fName, sName, sIndex))

            total_tris += n_cells
            total_nodes += poly.GetNumberOfPoints()

        # Update stats with VTK-side counts (may differ slightly from gmsh)
        stat.total_triangles = total_tris
        stat.total_nodes = total_nodes

    @staticmethod
    def _read_stl_file(path: Path) -> Optional[vtkPolyData]:
        """Read a binary STL file and return a cleaned vtkPolyData."""
        try:
            reader = vtkSTLReader()
            reader.SetFileName(str(path))
            reader.Update()

            clean = vtkCleanPolyData()
            clean.SetInputData(reader.GetOutput())
            clean.Update()

            return clean.GetOutput()
        except Exception as exc:
            logger.warning("Failed to read STL file '%s': %s", path, exc)
            return None

    def _add_index_array(self, polyData: vtkPolyData, arrayName: str,
                         value: str, count: int) -> int:
        """Add a cell-data integer array mapping to a StringIndex entry."""
        index = self._stringIndices.putString(value)
        array = vtkIntArray()
        array.SetName(arrayName)
        for _ in range(count):
            array.InsertNextValue(index)
        polyData.GetCellData().AddArray(array)
        return index

    def _add_index_array_with_index(self, polyData: vtkPolyData, arrayName: str,
                                    index: int, count: int) -> None:
        """Add a cell-data integer array using an existing StringIndex entry."""
        array = vtkIntArray()
        array.SetName(arrayName)
        for _ in range(count):
            array.InsertNextValue(index)
        polyData.GetCellData().AddArray(array)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

# Cached result of gmsh availability check
_gmsh_available: Optional[bool] = None


def check_gmsh_available() -> bool:
    """Return *True* if the ``gmsh`` package is installed and can be loaded.

    Uses ``importlib.util.find_spec`` to avoid actually importing gmsh (and
    loading its native DLLs) in the main process.  Falls back to a
    subprocess probe if ``find_spec`` succeeds but a previous attempt to
    load gmsh failed.
    """
    global _gmsh_available
    if _gmsh_available is not None:
        return _gmsh_available

    # Quick check: can Python find the gmsh package at all?
    spec = importlib.util.find_spec('gmsh')
    if spec is None:
        _gmsh_available = False
        return False

    # Verify the native library actually loads by asking a subprocess
    try:
        proc = subprocess.run(
            [sys.executable, '-c', 'import gmsh; print("ok")'],
            capture_output=True, text=True, timeout=30,
        )
        _gmsh_available = (proc.returncode == 0 and 'ok' in proc.stdout)
    except Exception:
        _gmsh_available = False

    return _gmsh_available


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
