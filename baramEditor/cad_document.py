#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""CAD document model — loads STEP/IGES/BREP via gmsh, exposes a component
tree with visibility toggles, and tracks a linear modification history with
full undo/redo.

Design
------
* **Component** — one solid/shell from the CAD file.  Stores the gmsh
  entity tag, a user-facing name, visibility flag, a colour, and the
  tessellated triangle mesh (vertices + faces) used for VTK display.
* **Modification** — an undoable/redoable operation on a component
  (rename, hide/show, delete, transform, colour change …).
* **ModificationHistory** — ordered list of modifications with a cursor.
* **CADDocument** — top-level object owning the file path, component list,
  and modification history.  Provides ``load()``, ``save_as()``, and all
  edit operations.
"""

from __future__ import annotations

import copy
import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, IO

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Component
# ---------------------------------------------------------------------------

@dataclass
class ComponentMesh:
    """Tessellated triangle mesh for VTK display."""
    vertices: np.ndarray   # (N, 3) float64
    faces: np.ndarray      # (M, 3) int32 — indices into vertices

    def triangle_count(self) -> int:
        return self.faces.shape[0] if self.faces is not None else 0


@dataclass
class Component:
    """One solid / shell from the CAD file."""

    tag: int                          # gmsh entity tag (3-D volume or 2-D surface)
    dim: int                          # gmsh dimension (3 = solid, 2 = shell)
    name: str                         # user-facing name
    visible: bool = True
    colour: Tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)  # RGBA 0-1
    mesh: Optional[ComponentMesh] = None
    deleted: bool = False

    # Affine transform applied on top of the original geometry.
    transform: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))

    def bounding_box(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Axis-aligned bounding box of the tessellated mesh."""
        if self.mesh is None or self.mesh.vertices.shape[0] == 0:
            return None
        vmin = self.mesh.vertices.min(axis=0)
        vmax = self.mesh.vertices.max(axis=0)
        return vmin, vmax


# ---------------------------------------------------------------------------
# Modifications (undo / redo)
# ---------------------------------------------------------------------------

class ModificationType(Enum):
    RENAME = auto()
    SET_VISIBLE = auto()
    SET_COLOUR = auto()
    DELETE = auto()
    RESTORE = auto()      # un-delete
    TRANSFORM = auto()
    GROUP = auto()        # composite (groups several mods into one undo step)
    ADD_COMPONENT = auto()
    REMOVE_COMPONENT = auto()
    DUPLICATE = auto()
    SCALE = auto()
    ROTATE = auto()
    MIRROR = auto()
    BOOLEAN = auto()


@dataclass
class Modification:
    """A single undoable operation."""

    type: ModificationType
    component_tag: int                # which component (by tag)
    description: str                  # human-readable
    old_value: Any = None
    new_value: Any = None
    timestamp: float = 0.0           # time.time()
    children: List['Modification'] = field(default_factory=list)  # for GROUP

    def to_dict(self) -> dict:
        d = {
            'type': self.type.name,
            'tag': self.component_tag,
            'desc': self.description,
            'ts': self.timestamp,
        }
        if self.old_value is not None:
            d['old'] = _serialize_value(self.old_value)
        if self.new_value is not None:
            d['new'] = _serialize_value(self.new_value)
        if self.children:
            d['children'] = [c.to_dict() for c in self.children]
        return d


def _serialize_value(val):
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, tuple):
        return list(val)
    return val


class ModificationHistory:
    """Linear undo/redo stack."""

    def __init__(self):
        self._history: List[Modification] = []
        self._cursor: int = 0   # points to the *next* slot (== len when at head)

    @property
    def items(self) -> List[Modification]:
        """All modifications (including redo tail)."""
        return list(self._history)

    @property
    def modifications(self) -> List[Modification]:
        return self._history[:self._cursor]

    @property
    def all_modifications(self) -> List[Modification]:
        return list(self._history)

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._history)

    def push(self, mod: Modification):
        # Discard any redo tail.
        self._history = self._history[:self._cursor]
        self._history.append(mod)
        self._cursor += 1

    def undo_item(self) -> Optional[Modification]:
        if not self.can_undo:
            return None
        self._cursor -= 1
        return self._history[self._cursor]

    def redo_item(self) -> Optional[Modification]:
        if not self.can_redo:
            return None
        item = self._history[self._cursor]
        self._cursor += 1
        return item

    def clear(self):
        self._history.clear()
        self._cursor = 0

    def to_list(self) -> List[dict]:
        return [m.to_dict() for m in self._history]


# ---------------------------------------------------------------------------
# gmsh worker  (subprocess isolation — same pattern as cad_utility.py)
# ---------------------------------------------------------------------------

_GMSH_WORKER_SCRIPT = r'''
"""gmsh subprocess worker -- reads a JSON job on stdin, tessellates the CAD
file, and writes per-entity numpy arrays to the given output directory.
Outputs a JSON result on stdout.  Progress is written to stderr as:
  PROGRESS:<percent>:<message>

Uses ALL available CPU cores for meshing via gmsh threading and
parallel numpy extraction with concurrent.futures.
"""
import json, sys, pathlib, math, traceback, os

def _progress(pct, msg):
    sys.stderr.write(f"PROGRESS:{pct}:{msg}\n")
    sys.stderr.flush()

def _extract_entity(args):
    """Extract mesh for one entity — runs in a ThreadPoolExecutor."""
    import gmsh
    import numpy as _np
    dim, tag, out_dir = args
    out_dir = pathlib.Path(out_dir)

    label = ""
    try:
        label = gmsh.model.getEntityName(dim, tag)
    except Exception:
        pass
    if not label:
        kind = "Solid" if dim == 3 else "Surface"
        label = f"{kind}_{tag}"
    label = label.rsplit("/", 1)[-1] if "/" in label else label

    if dim == 3:
        try:
            bnd = gmsh.model.getBoundary([(dim, tag)],
                                          oriented=False, recursive=False)
            surf_tags = [abs(t) for _, t in bnd]
        except Exception:
            surf_tags = []
    else:
        surf_tags = [tag]

    all_coords = []
    all_faces = []
    vert_offset = 0

    for stag in surf_tags:
        try:
            node_tags, coords, _ = gmsh.model.mesh.getNodes(
                dim=2, tag=stag, includeBoundary=True)
        except Exception:
            continue
        if len(coords) == 0:
            continue

        # Vectorized vertex extraction using numpy
        n_nodes = len(coords) // 3
        verts = _np.array(coords, dtype=_np.float64).reshape(n_nodes, 3)
        tag_to_idx = {}
        for i, t in enumerate(node_tags):
            tag_to_idx[int(t)] = i

        try:
            elem_types, _, elem_nodes = gmsh.model.mesh.getElements(
                dim=2, tag=stag)
        except Exception:
            continue

        for et, enodes in zip(elem_types, elem_nodes):
            enodes_int = _np.array(enodes, dtype=_np.int64)
            if et == 2:  # 3-node triangle
                tri_nodes = enodes_int.reshape(-1, 3)
                for tri in tri_nodes:
                    idx = [tag_to_idx.get(int(n)) for n in tri]
                    if all(x is not None for x in idx):
                        all_faces.append([idx[0]+vert_offset,
                                          idx[1]+vert_offset,
                                          idx[2]+vert_offset])
            elif et == 3:  # 4-node quad -> 2 triangles
                quad_nodes = enodes_int.reshape(-1, 4)
                for quad in quad_nodes:
                    idx = [tag_to_idx.get(int(n)) for n in quad]
                    if all(x is not None for x in idx):
                        all_faces.append([idx[0]+vert_offset,
                                          idx[1]+vert_offset,
                                          idx[2]+vert_offset])
                        all_faces.append([idx[0]+vert_offset,
                                          idx[2]+vert_offset,
                                          idx[3]+vert_offset])

        all_coords.append(verts)
        vert_offset += n_nodes

    if all_coords:
        v = _np.concatenate(all_coords, axis=0)
        f = (_np.array(all_faces, dtype=_np.int32)
             if all_faces
             else _np.zeros((0, 3), dtype=_np.int32))
        _np.save(str(out_dir / f"verts_{dim}_{tag}.npy"), v)
        _np.save(str(out_dir / f"faces_{dim}_{tag}.npy"), f)
        return {"dim": dim, "tag": tag, "name": label,
                "nverts": int(v.shape[0]), "nfaces": len(all_faces)}
    return None


def _main():
    job = json.loads(sys.stdin.read())
    file_path = job["file"]
    out_dir    = pathlib.Path(job["out_dir"])
    deflection = job.get("deflection", 0.001)
    angle      = job.get("angle", 30.0)

    # Detect available CPU cores
    ncpus = os.cpu_count() or 1

    _progress(0, f"Initializing gmsh ({ncpus} cores)")
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)

    # ═══ Enable multi-threaded meshing on ALL available cores ═══
    gmsh.option.setNumber("General.NumThreads", ncpus)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", ncpus)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", ncpus)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", ncpus)

    try:
        _progress(5, "Importing CAD geometry")
        gmsh.model.occ.importShapes(file_path)
        gmsh.model.occ.synchronize()

        # Collect entities
        volumes = gmsh.model.getEntities(dim=3)
        surfaces = gmsh.model.getEntities(dim=2)
        entities = volumes if volumes else surfaces

        # Bounding-box-relative sizing
        try:
            bb = gmsh.model.getBoundingBox(-1, -1)
            diag = math.sqrt((bb[3]-bb[0])**2 + (bb[4]-bb[1])**2 + (bb[5]-bb[2])**2)
            if diag > 0:
                auto_max = diag * deflection * 100
                auto_min = auto_max * 0.01
                gmsh.option.setNumber("Mesh.MeshSizeMax", auto_max)
                gmsh.option.setNumber("Mesh.MeshSizeMin", auto_min)
        except Exception:
            gmsh.option.setNumber("Mesh.MeshSizeMin", deflection * 0.5)
            gmsh.option.setNumber("Mesh.MeshSizeMax", deflection * 50)

        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap",
                              angle / 57.2958)

        _progress(15, f"Meshing {len(entities)} entities on {ncpus} threads")

        # Multi-threaded mesh generation
        gmsh.model.mesh.generate(2)

        _progress(50, "Mesh generated, extracting surfaces in parallel")

        # ═══ Parallel entity extraction using thread pool ═══
        from concurrent.futures import ThreadPoolExecutor, as_completed

        extract_args = [(dim, tag, str(out_dir)) for dim, tag in entities]
        results = []
        total_entities = len(entities)

        # Use threads (not processes) since gmsh state is shared
        # but numpy I/O benefits from parallelism
        n_workers = min(ncpus, total_entities, 8)
        done_count = 0

        with ThreadPoolExecutor(max_workers=max(n_workers, 1)) as pool:
            futures = {pool.submit(_extract_entity, a): a for a in extract_args}
            for future in as_completed(futures):
                done_count += 1
                ent_pct = 50 + int(40 * done_count / max(total_entities, 1))
                _progress(ent_pct, f"Extracted {done_count}/{total_entities}")
                r = future.result()
                if r is not None:
                    results.append(r)

        _progress(95, "Finalizing")
        gmsh.finalize()
        _progress(100, "Done")
        print(json.dumps(results))

    except Exception:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        try:
            gmsh.finalize()
        except Exception:
            pass
        sys.exit(1)


try:
    _main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
'''


# Type alias for the progress callback:  callback(percent: int, message: str)
ProgressCallback = Callable[[int, str], None]


def _load_step_via_subprocess(
    file_path: Path,
    deflection: float = 0.001,
    angle: float = 30.0,
    progress: Optional[ProgressCallback] = None,
) -> List[Component]:
    """Load a STEP/IGES/BREP file in a subprocess and return Components.

    The *progress* callback receives ``(percent, message)`` as the
    gmsh worker emits ``PROGRESS:<pct>:<msg>`` lines on stderr.
    """

    with tempfile.TemporaryDirectory(prefix='baramEditor_') as tmp:
        tmp_path = Path(tmp)
        job = json.dumps({
            'file': str(file_path),
            'out_dir': str(tmp_path),
            'deflection': deflection,
            'angle': angle,
        })

        proc = subprocess.Popen(
            [sys.executable, '-c', _GMSH_WORKER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send job on stdin then close it so the worker can start
        proc.stdin.write(job)
        proc.stdin.close()

        # Stream stderr for PROGRESS lines while process runs.
        # Use a background thread to read stderr so we never deadlock
        # even if the child writes a lot and the pipe buffer fills.
        import threading

        stderr_lines: List[str] = []

        def _drain_stderr():
            for line in proc.stderr:
                line = line.rstrip()
                if line.startswith('PROGRESS:'):
                    parts = line.split(':', 2)
                    if len(parts) >= 3 and progress is not None:
                        try:
                            pct = int(parts[1])
                        except ValueError:
                            pct = -1
                        progress(pct, parts[2])
                elif line:
                    stderr_lines.append(line)

        reader = threading.Thread(target=_drain_stderr, daemon=True)
        reader.start()

        # 1-hour timeout for very large STEP files
        proc.wait(timeout=3600)
        reader.join(timeout=10)

        if proc.returncode != 0:
            err_detail = '\n'.join(stderr_lines).strip() or '(no error output captured)'
            raise RuntimeError(
                f'gmsh worker failed (exit {proc.returncode}):\n{err_detail}'
            )

        stdout = proc.stdout.read()
        results = json.loads(stdout.strip())
        components: List[Component] = []

        # ═══ Parallel .npy file loading ═══
        import os
        from concurrent.futures import ThreadPoolExecutor

        total = len(results)

        def _load_entry(i_entry):
            i, entry = i_entry
            dim = entry['dim']
            tag = entry['tag']
            name = entry['name']
            verts_file = tmp_path / f'verts_{dim}_{tag}.npy'
            faces_file = tmp_path / f'faces_{dim}_{tag}.npy'
            if verts_file.exists() and faces_file.exists():
                vertices = np.load(str(verts_file))
                faces = np.load(str(faces_file))
                mesh = ComponentMesh(vertices=vertices, faces=faces)
            else:
                mesh = None
            return i, Component(tag=tag, dim=dim, name=name, mesh=mesh)

        n_workers = min(os.cpu_count() or 1, total, 8)
        loaded = [None] * total
        with ThreadPoolExecutor(max_workers=max(n_workers, 1)) as pool:
            for i, comp in pool.map(_load_entry, enumerate(results)):
                loaded[i] = comp
                if progress:
                    progress(95 + int(5 * (i + 1) / max(total, 1)),
                             f'Reading mesh {i+1}/{total}…')

        components = [c for c in loaded if c is not None]

        return components


# ---------------------------------------------------------------------------
# STL loader  (no gmsh needed — pure Python / numpy)
# ---------------------------------------------------------------------------

def _load_stl(
    file_path: Path,
    progress: Optional[ProgressCallback] = None,
) -> List[Component]:
    """Load a binary or ASCII STL file and return a single Component.

    Binary STL format:
      - 80 bytes header
      - 4 bytes uint32 triangle count
      - per triangle: 12 floats (normal + 3 vertices) + 2 bytes attribute

    If the file doesn't look like valid binary STL, falls back to ASCII.
    """
    import struct as _struct

    raw = file_path.read_bytes()
    name = file_path.stem

    if progress:
        progress(5, f'Reading {name}…')

    vertices, faces = _try_parse_binary_stl(raw, progress)
    if vertices is None:
        vertices, faces = _try_parse_ascii_stl(raw.decode('utf-8', errors='replace'), progress)

    if vertices is None or len(vertices) == 0:
        raise RuntimeError(f'Could not parse STL file: {file_path.name}')

    mesh = ComponentMesh(
        vertices=np.array(vertices, dtype=np.float64),
        faces=np.array(faces, dtype=np.int32),
    )

    comp = Component(
        tag=1,
        dim=2,
        name=name,
        mesh=mesh,
    )

    if progress:
        progress(100, 'Done')

    return [comp]


def _try_parse_binary_stl(
    raw: bytes,
    progress: Optional[ProgressCallback] = None,
) -> tuple:
    """Try to parse as binary STL.  Returns (vertices, faces) or (None, None).

    Uses fully vectorized numpy operations for maximum throughput on
    multi-million triangle files — no Python per-triangle loop.
    """
    if len(raw) < 84:
        return None, None

    ntri = np.frombuffer(raw, dtype=np.uint32, count=1, offset=80)[0]
    expected = 84 + ntri * 50
    if len(raw) < expected:
        return None, None

    # Quick sanity: ASCII STL starts with 'solid'
    if raw[:6] == b'solid ' and ntri > 0x10000000:
        return None, None

    if progress:
        progress(10, f'Parsing {ntri:,} triangles (binary STL, vectorized)…')

    # ═══ Fully vectorized: parse all triangles at once ═══
    # Each triangle record is 50 bytes:
    #   12 bytes normal (3 floats) + 36 bytes vertices (9 floats) + 2 bytes attr
    # We use a structured dtype to read all at once
    tri_dtype = np.dtype([
        ('normal', '<f4', (3,)),
        ('v0', '<f4', (3,)),
        ('v1', '<f4', (3,)),
        ('v2', '<f4', (3,)),
        ('attr', '<u2'),
    ])
    tri_data = np.frombuffer(raw, dtype=tri_dtype, count=ntri, offset=84)

    if progress:
        progress(40, f'Extracting {ntri:,} x 3 vertices…')

    # Stack all vertices: (ntri, 3, 3) -> (ntri*3, 3)
    all_verts = np.stack([tri_data['v0'], tri_data['v1'], tri_data['v2']], axis=1)
    all_verts = all_verts.reshape(-1, 3).astype(np.float64)

    if progress:
        progress(60, 'De-duplicating vertices…')

    # De-duplicate vertices
    unique_verts, inverse = np.unique(all_verts, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3).astype(np.int32)

    if progress:
        progress(95, f'{len(unique_verts):,} unique vertices, {ntri:,} triangles')

    return unique_verts.tolist(), faces.tolist()


def _try_parse_ascii_stl(
    text: str,
    progress: Optional[ProgressCallback] = None,
) -> tuple:
    """Parse an ASCII STL.  Returns (vertices, faces) or (None, None)."""
    import re as _re

    if not text.lstrip().lower().startswith('solid'):
        return None, None

    if progress:
        progress(10, 'Parsing ASCII STL…')

    vertex_re = _re.compile(r'vertex\s+([\deE.+-]+)\s+([\deE.+-]+)\s+([\deE.+-]+)', _re.IGNORECASE)
    matches = vertex_re.findall(text)

    if len(matches) < 3 or len(matches) % 3 != 0:
        return None, None

    vertices = [(float(x), float(y), float(z)) for x, y, z in matches]
    ntri = len(vertices) // 3
    faces = [(i * 3, i * 3 + 1, i * 3 + 2) for i in range(ntri)]

    if progress:
        progress(80, 'De-duplicating vertices…')

    verts_arr = np.array(vertices, dtype=np.float64)
    unique_verts, inverse = np.unique(verts_arr, axis=0, return_inverse=True)
    new_faces = inverse[np.array(faces, dtype=np.int32).ravel()].reshape(-1, 3)

    if progress:
        progress(95, f'{len(unique_verts):,} unique vertices, {ntri:,} triangles')

    return unique_verts.tolist(), new_faces.tolist()


# ---------------------------------------------------------------------------
# Predefined colour palette for auto-colouring components
# ---------------------------------------------------------------------------

_PALETTE = [
    (0.545, 0.678, 0.788, 1.0),   # steel blue
    (0.788, 0.545, 0.545, 1.0),   # rosewood
    (0.545, 0.788, 0.545, 1.0),   # sage green
    (0.788, 0.745, 0.545, 1.0),   # sand
    (0.678, 0.545, 0.788, 1.0),   # lavender
    (0.545, 0.788, 0.745, 1.0),   # teal
    (0.788, 0.620, 0.545, 1.0),   # salmon
    (0.620, 0.788, 0.545, 1.0),   # lime
    (0.788, 0.545, 0.678, 1.0),   # pink
    (0.545, 0.620, 0.788, 1.0),   # periwinkle
]


# ---------------------------------------------------------------------------
# CAD Document
# ---------------------------------------------------------------------------

class CADDocument:
    """Top-level document owning file, components, and history."""

    def __init__(self):
        self._file_path: Optional[Path] = None
        self._components: List[Component] = []
        self._history = ModificationHistory()
        self._modified = False

    # -- Properties ----------------------------------------------------------

    @property
    def file_path(self) -> Optional[Path]:
        return self._file_path

    @property
    def components(self) -> List[Component]:
        return self._components

    @property
    def visible_components(self) -> List[Component]:
        return [c for c in self._components if c.visible and not c.deleted]

    @property
    def history(self) -> ModificationHistory:
        return self._history

    @property
    def is_modified(self) -> bool:
        return self._modified

    # -- Load / Save ---------------------------------------------------------

    def load(
        self,
        file_path,
        deflection: float = 0.001,
        angle: float = 30.0,
        progress: Optional[ProgressCallback] = None,
    ):
        """Load a STEP / IGES / BREP / STL file.

        *progress* is an optional ``(percent, message)`` callback.
        """
        file_path = Path(file_path)
        self._file_path = file_path

        suffix = file_path.suffix.lower()
        if suffix in ('.stl',):
            self._components = _load_stl(file_path, progress=progress)
        else:
            self._components = _load_step_via_subprocess(
                file_path, deflection, angle, progress=progress,
            )

        self._history.clear()
        self._modified = False

        # Auto-assign colours
        for i, comp in enumerate(self._components):
            comp.colour = _PALETTE[i % len(_PALETTE)]

        logger.info('Loaded %d components from %s', len(self._components), file_path.name)

    def save_project(self, project_path: Path):
        """Save the document state (component metadata + history) as JSON."""
        data = {
            'version': 1,
            'source_file': str(self._file_path) if self._file_path else None,
            'components': [
                {
                    'tag': c.tag,
                    'dim': c.dim,
                    'name': c.name,
                    'visible': c.visible,
                    'colour': list(c.colour),
                    'deleted': c.deleted,
                    'transform': c.transform.tolist(),
                }
                for c in self._components
            ],
            'history': self._history.to_list(),
            'history_cursor': self._history.cursor,
        }
        project_path.parent.mkdir(parents=True, exist_ok=True)
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        self._modified = False
        logger.info('Project saved to %s', project_path)

    def open_project(self, project_path: Path, deflection: float = 0.001, angle: float = 30.0):
        """Open a saved project — reloads the CAD file and applies stored state."""
        with open(project_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        source = data.get('source_file')
        if source and Path(source).is_file():
            self.load(Path(source), deflection, angle)
        else:
            raise FileNotFoundError(
                f'Source CAD file not found: {source}'
            )

        # Restore component state
        comp_by_tag = {c.tag: c for c in self._components}
        for cdata in data.get('components', []):
            comp = comp_by_tag.get(cdata['tag'])
            if comp is None:
                continue
            comp.name = cdata.get('name', comp.name)
            comp.visible = cdata.get('visible', True)
            comp.colour = tuple(cdata.get('colour', list(comp.colour)))
            comp.deleted = cdata.get('deleted', False)
            tf = cdata.get('transform')
            if tf:
                comp.transform = np.array(tf, dtype=np.float64)

        self._modified = False
        logger.info('Project opened from %s', project_path)

    # -- Component lookup ----------------------------------------------------

    def component_by_tag(self, tag: int) -> Optional[Component]:
        for c in self._components:
            if c.tag == tag:
                return c
        return None

    # -- Edit operations (all create Modifications) --------------------------

    def _push_mod(self, mod: Modification):
        import time
        mod.timestamp = time.time()
        self._history.push(mod)
        self._modified = True

    def rename_component(self, tag: int, new_name: str) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None:
            return None
        old = comp.name
        comp.name = new_name
        mod = Modification(
            type=ModificationType.RENAME,
            component_tag=tag,
            description=f'Rename "{old}" → "{new_name}"',
            old_value=old,
            new_value=new_name,
        )
        self._push_mod(mod)
        return mod

    def set_visible(self, tag: int, visible: bool) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None:
            return None
        old = comp.visible
        comp.visible = visible
        action = 'Show' if visible else 'Hide'
        mod = Modification(
            type=ModificationType.SET_VISIBLE,
            component_tag=tag,
            description=f'{action} "{comp.name}"',
            old_value=old,
            new_value=visible,
        )
        self._push_mod(mod)
        return mod

    def set_colour(self, tag: int, colour: Tuple[float, float, float, float]) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None:
            return None
        old = comp.colour
        comp.colour = colour
        mod = Modification(
            type=ModificationType.SET_COLOUR,
            component_tag=tag,
            description=f'Colour "{comp.name}"',
            old_value=old,
            new_value=colour,
        )
        self._push_mod(mod)
        return mod

    def delete_component(self, tag: int) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None or comp.deleted:
            return None
        comp.deleted = True
        comp.visible = False
        mod = Modification(
            type=ModificationType.DELETE,
            component_tag=tag,
            description=f'Delete "{comp.name}"',
            old_value=False,
            new_value=True,
        )
        self._push_mod(mod)
        return mod

    def restore_component(self, tag: int) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None or not comp.deleted:
            return None
        comp.deleted = False
        comp.visible = True
        mod = Modification(
            type=ModificationType.RESTORE,
            component_tag=tag,
            description=f'Restore "{comp.name}"',
            old_value=True,
            new_value=False,
        )
        self._push_mod(mod)
        return mod

    def translate_component(self, tag: int, dx: float, dy: float, dz: float) -> Optional[Modification]:
        comp = self.component_by_tag(tag)
        if comp is None:
            return None
        old_tf = comp.transform.copy()
        t = np.eye(4, dtype=np.float64)
        t[0, 3] = dx
        t[1, 3] = dy
        t[2, 3] = dz
        comp.transform = t @ comp.transform
        mod = Modification(
            type=ModificationType.TRANSFORM,
            component_tag=tag,
            description=f'Translate "{comp.name}" by ({dx:.3f}, {dy:.3f}, {dz:.3f})',
            old_value=old_tf,
            new_value=comp.transform.copy(),
        )
        self._push_mod(mod)
        return mod

    # -- Utility -------------------------------------------------------------

    def _next_tag(self) -> int:
        """Return a tag value not yet used by any component."""
        used = {c.tag for c in self._components}
        t = 1
        while t in used:
            t += 1
        return t

    # -- Primitive / editing operations --------------------------------------

    def add_component(
        self,
        name: str,
        dim: int,
        mesh: 'ComponentMesh',
        colour: Tuple[float, float, float, float] = None,
    ) -> Tuple[Optional[Component], Optional[Modification]]:
        """Add a brand-new component.  Returns (component, modification)."""
        tag = self._next_tag()
        if colour is None:
            colour = _PALETTE[len(self._components) % len(_PALETTE)]
        comp = Component(tag=tag, dim=dim, name=name, mesh=mesh, colour=colour)
        self._components.append(comp)
        mod = Modification(
            type=ModificationType.ADD_COMPONENT,
            component_tag=tag,
            description=f'Add "{name}"',
            old_value=None,
            new_value=tag,
        )
        self._push_mod(mod)
        return comp, mod

    def duplicate_component(self, tag: int) -> Tuple[Optional[Component], Optional[Modification]]:
        """Duplicate an existing component.  Returns (new_comp, modification)."""
        src = self.component_by_tag(tag)
        if src is None:
            return None, None
        import copy as _copy
        new_tag = self._next_tag()
        new_mesh = ComponentMesh(
            vertices=src.mesh.vertices.copy(),
            faces=src.mesh.faces.copy(),
        ) if src.mesh else None
        new_comp = Component(
            tag=new_tag,
            dim=src.dim,
            name=f'{src.name} (copy)',
            visible=True,
            colour=src.colour,
            mesh=new_mesh,
            deleted=False,
            transform=src.transform.copy(),
        )
        self._components.append(new_comp)
        mod = Modification(
            type=ModificationType.DUPLICATE,
            component_tag=new_tag,
            description=f'Duplicate "{src.name}"',
            old_value=tag,       # source tag
            new_value=new_tag,   # new tag
        )
        self._push_mod(mod)
        return new_comp, mod

    def scale_component(
        self, tag: int, sx: float, sy: float, sz: float,
    ) -> Optional[Modification]:
        """Scale a component's mesh vertices in-place."""
        comp = self.component_by_tag(tag)
        if comp is None or comp.mesh is None:
            return None
        from baramEditor.primitives import scale_mesh
        old_verts = comp.mesh.vertices.copy()
        comp.mesh.vertices = scale_mesh(comp.mesh.vertices, sx, sy, sz)
        mod = Modification(
            type=ModificationType.SCALE,
            component_tag=tag,
            description=f'Scale "{comp.name}" ({sx:.2f}, {sy:.2f}, {sz:.2f})',
            old_value=old_verts,
            new_value=comp.mesh.vertices.copy(),
        )
        self._push_mod(mod)
        return mod

    def rotate_component(
        self, tag: int, angle_deg: float, axis: str = 'z',
    ) -> Optional[Modification]:
        """Rotate a component's mesh vertices in-place."""
        comp = self.component_by_tag(tag)
        if comp is None or comp.mesh is None:
            return None
        from baramEditor.primitives import rotate_mesh
        old_verts = comp.mesh.vertices.copy()
        comp.mesh.vertices = rotate_mesh(comp.mesh.vertices, angle_deg, axis)
        mod = Modification(
            type=ModificationType.ROTATE,
            component_tag=tag,
            description=f'Rotate "{comp.name}" {angle_deg:.1f}° around {axis.upper()}',
            old_value=old_verts,
            new_value=comp.mesh.vertices.copy(),
        )
        self._push_mod(mod)
        return mod

    def mirror_component(
        self, tag: int, plane: str = 'xy',
    ) -> Tuple[Optional[Component], Optional[Modification]]:
        """Mirror a component, creating a new mirrored copy."""
        comp = self.component_by_tag(tag)
        if comp is None or comp.mesh is None:
            return None, None
        from baramEditor.primitives import mirror_mesh
        new_verts, new_faces = mirror_mesh(
            comp.mesh.vertices, comp.mesh.faces, plane,
        )
        new_mesh = ComponentMesh(
            vertices=new_verts,
            faces=new_faces,
        )
        return self.add_component(
            name=f'{comp.name} (mirror {plane.upper()})',
            dim=comp.dim,
            mesh=new_mesh,
            colour=comp.colour,
        )

    def boolean_operation(
        self, tag_a: int, tag_b: int, op_index: int,
    ) -> Tuple[Optional[Component], Optional[Modification]]:
        """Perform a boolean operation between two components.

        *op_index*: 0 = union, 1 = subtract (A-B), 2 = intersect.
        Returns the resulting new component and modification.
        """
        comp_a = self.component_by_tag(tag_a)
        comp_b = self.component_by_tag(tag_b)
        if comp_a is None or comp_b is None:
            return None, None
        if comp_a.mesh is None or comp_b.mesh is None:
            return None, None

        from baramEditor.primitives import boolean_operation as _bool_op, BooleanOp
        ops = [BooleanOp.UNION, BooleanOp.DIFFERENCE, BooleanOp.INTERSECTION]
        op = ops[op_index]
        op_names = ['Union', 'Subtract', 'Intersect']

        result_verts, result_faces = _bool_op(
            comp_a.mesh.vertices, comp_a.mesh.faces,
            comp_b.mesh.vertices, comp_b.mesh.faces,
            op,
        )
        result_mesh = ComponentMesh(vertices=result_verts, faces=result_faces)
        name = f'{op_names[op_index]}({comp_a.name}, {comp_b.name})'
        return self.add_component(name=name, dim=comp_a.dim, mesh=result_mesh)

    def move_component_mesh(
        self, tag: int, dx: float, dy: float, dz: float,
    ) -> Optional[Modification]:
        """Translate a component's mesh vertices directly (not the 4x4 transform)."""
        comp = self.component_by_tag(tag)
        if comp is None or comp.mesh is None:
            return None
        from baramEditor.primitives import translate_mesh
        old_verts = comp.mesh.vertices.copy()
        comp.mesh.vertices = translate_mesh(comp.mesh.vertices, dx, dy, dz)
        mod = Modification(
            type=ModificationType.TRANSFORM,
            component_tag=tag,
            description=f'Move "{comp.name}" by ({dx:.3f}, {dy:.3f}, {dz:.3f})',
            old_value=old_verts,
            new_value=comp.mesh.vertices.copy(),
        )
        self._push_mod(mod)
        return mod

    def undo(self) -> Optional[Modification]:
        mod = self._history.undo_item()
        if mod is None:
            return None
        self._apply_undo(mod)
        self._modified = True
        return mod

    def redo(self) -> Optional[Modification]:
        mod = self._history.redo_item()
        if mod is None:
            return None
        self._apply_redo(mod)
        self._modified = True
        return mod

    def _apply_undo(self, mod: Modification):
        comp = self.component_by_tag(mod.component_tag)
        if mod.type in (ModificationType.ADD_COMPONENT, ModificationType.DUPLICATE):
            # Soft-delete: mark as deleted so redo can restore it
            if comp is not None:
                comp.deleted = True
                comp.visible = False
            return
        if comp is None:
            return
        if mod.type == ModificationType.RENAME:
            comp.name = mod.old_value
        elif mod.type == ModificationType.SET_VISIBLE:
            comp.visible = mod.old_value
        elif mod.type == ModificationType.SET_COLOUR:
            comp.colour = mod.old_value
        elif mod.type in (ModificationType.DELETE, ModificationType.RESTORE):
            comp.deleted = mod.old_value
            comp.visible = not mod.old_value
        elif mod.type == ModificationType.TRANSFORM:
            arr = np.asarray(mod.old_value, dtype=np.float64)
            if arr.shape == (4, 4):
                comp.transform = arr
            elif comp.mesh is not None:
                comp.mesh.vertices = arr
        elif mod.type in (ModificationType.SCALE, ModificationType.ROTATE):
            if comp.mesh is not None:
                comp.mesh.vertices = np.array(mod.old_value, dtype=np.float64)
        elif mod.type == ModificationType.GROUP:
            for child in reversed(mod.children):
                self._apply_undo(child)

    def _apply_redo(self, mod: Modification):
        comp = self.component_by_tag(mod.component_tag)
        if mod.type in (ModificationType.ADD_COMPONENT, ModificationType.DUPLICATE):
            # For redo of add/duplicate we store the component in mod.new_value
            # but we only stored the tag — we can't fully reconstruct.
            # So we keep deleted components in a stash instead.
            # For now, this is a simplified approach: we mark as not-deleted
            # if the component still exists in the list.
            if comp is not None:
                comp.deleted = False
                comp.visible = True
            return
        if comp is None:
            return
        if mod.type == ModificationType.RENAME:
            comp.name = mod.new_value
        elif mod.type == ModificationType.SET_VISIBLE:
            comp.visible = mod.new_value
        elif mod.type == ModificationType.SET_COLOUR:
            comp.colour = mod.new_value
        elif mod.type in (ModificationType.DELETE, ModificationType.RESTORE):
            comp.deleted = mod.new_value
            comp.visible = not mod.new_value
        elif mod.type == ModificationType.TRANSFORM:
            arr = np.array(mod.new_value, dtype=np.float64)
            if arr.shape == (4, 4):
                comp.transform = arr
            elif comp.mesh is not None:
                comp.mesh.vertices = arr
        elif mod.type in (ModificationType.SCALE, ModificationType.ROTATE):
            if comp.mesh is not None:
                comp.mesh.vertices = np.array(mod.new_value, dtype=np.float64)
        elif mod.type == ModificationType.GROUP:
            for child in mod.children:
                self._apply_redo(child)
