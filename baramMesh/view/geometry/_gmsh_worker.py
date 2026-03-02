#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Isolated gmsh worker — runs in a **subprocess** to avoid DLL conflicts.

Both VTK and gmsh bundle their own builds of the OpenCASCADE (OCC) native
libraries.  When both are loaded in the same process the symbol tables
collide and gmsh's ``importShapes`` crashes with an access-violation.

This script is therefore executed as a standalone Python process by
:class:`CADImporter`.  It:

1. Receives a JSON job description on **stdin**.
2. Imports the CAD file with gmsh.
3. Tessellates (meshes to 2-D surface triangles).
4. Writes one ``.stl`` file per gmsh surface entity into a temporary
   directory.
5. Writes a JSON result (file list + statistics) to **stdout**.

The parent process reads the STL files using VTK and discards the
temporary directory.

Usage (called by CADImporter, not directly)::

    python -m baramMesh.view.geometry._gmsh_worker  < job.json  > result.json
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path


def _progress(phase: str, pct: int, detail: str = '') -> None:
    """Write a machine-readable progress line to stderr.

    Format::  PROGRESS:<phase>:<percent>:<detail>\n

    The parent process (CADImporter) reads stderr line-by-line in its
    poll loop to update the UI progress bar.
    """
    line = f'PROGRESS:{phase}:{pct}:{detail}\n'
    sys.stderr.write(line)
    sys.stderr.flush()


def _run(job: dict) -> dict:
    """Execute a single CAD import job and return a result dict."""

    # Import gmsh only here — the whole point is that this process has no
    # VTK / PySide6 loaded, so no DLL conflicts.
    import gmsh

    cad_path = Path(job['file'])
    out_dir = Path(job['out_dir'])
    params = job.get('params', {})

    deflection = params.get('deflection', 0.001)
    angle = params.get('angle', 30.0)
    min_edge = params.get('min_edge_length')
    max_edge = params.get('max_edge_length')
    curvature_elements = params.get('curvature_elements', 12)
    algorithm = params.get('algorithm', 6)

    result: dict = {
        'file': str(cad_path),
        'format': cad_path.suffix.lower().lstrip('.'),
        'stl_files': [],      # list of {path, solid_name, surface_name}
        'num_solids': 0,
        'num_shells': 0,
        'num_faces': 0,
        'total_triangles': 0,
        'total_nodes': 0,
        'bounding_box': [],
        'warnings': [],
        'elapsed': 0.0,
    }

    t0 = time.perf_counter()

    gmsh.initialize()
    gmsh.option.setNumber("General.Verbosity", 1)

    try:
        # ── Configure meshing parameters ─────────────────────────────
        gmsh.option.setNumber("Mesh.Algorithm", algorithm)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", curvature_elements)
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", angle / 57.2958)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvatureIsotropic", 1)

        if min_edge is not None:
            gmsh.option.setNumber("Mesh.MeshSizeMin", min_edge)
        if max_edge is not None:
            gmsh.option.setNumber("Mesh.MeshSizeMax", max_edge)

        # ── Load CAD ─────────────────────────────────────────────────
        _progress('load', 5, f'Reading {cad_path.name}')
        try:
            gmsh.model.occ.importShapes(str(cad_path))
        except Exception as exc:
            return {**result, 'error': f"Gmsh failed to read '{cad_path.name}': {exc}"}

        _progress('sync', 15, 'Synchronising OCC model')
        gmsh.model.occ.synchronize()

        # ── Bounding-box-relative auto-sizing ────────────────────────
        try:
            bb = gmsh.model.getBoundingBox(-1, -1)
            result['bounding_box'] = list(bb)
            if max_edge is None:
                diag = math.sqrt(
                    (bb[3] - bb[0]) ** 2 +
                    (bb[4] - bb[1]) ** 2 +
                    (bb[5] - bb[2]) ** 2
                )
                if diag > 0:
                    auto_max = diag * deflection * 100
                    auto_min = auto_max * 0.01
                    gmsh.option.setNumber("Mesh.MeshSizeMax", auto_max)
                    if min_edge is None:
                        gmsh.option.setNumber("Mesh.MeshSizeMin", auto_min)
        except Exception:
            pass

        # ── Entity counts ────────────────────────────────────────────
        volumes_3d = gmsh.model.getEntities(3)
        surfaces_2d = gmsh.model.getEntities(2)
        result['num_solids'] = len(volumes_3d)
        result['num_shells'] = len(surfaces_2d)
        result['num_faces'] = len(surfaces_2d)

        _progress('mesh', 25, f'Tessellating {len(surfaces_2d)} faces')

        # ── Generate 2-D surface mesh ────────────────────────────────
        try:
            gmsh.model.mesh.generate(2)
        except Exception as exc:
            result['warnings'].append(f"Meshing warning: {exc}")

        _progress('mesh', 60, 'Tessellation complete')

        # ── Build surface→volume mapping ─────────────────────────────
        surface_to_volume: dict[int, int] = {}
        for _, vol_tag in volumes_3d:
            try:
                boundaries = gmsh.model.getBoundary(
                    [(3, vol_tag)], oriented=False
                )
                for _, stag in boundaries:
                    surface_to_volume[abs(stag)] = vol_tag
            except Exception:
                pass

        volume_groups: dict[int, list[int]] = {}
        unattached: list[int] = []
        for _, stag in surfaces_2d:
            if stag in surface_to_volume:
                vtag = surface_to_volume[stag]
                volume_groups.setdefault(vtag, []).append(stag)
            else:
                unattached.append(stag)

        # ── Helper: entity name ──────────────────────────────────────
        def _entity_name(dim: int, tag: int) -> str:
            try:
                n = gmsh.model.getEntityName(dim, tag)
                return n.strip() if n else ''
            except Exception:
                return ''

        stem = cad_path.stem

        _progress('write', 65, 'Writing STL surfaces')

        # ── Write per-surface STL files ──────────────────────────────
        total_tris = 0
        total_nodes = 0
        file_idx = 0
        total_surfs = len(surfaces_2d) or 1

        def _write_surface(stag: int, solid_name: str, surf_name: str):
            nonlocal total_tris, total_nodes, file_idx

            node_tags, coords, _ = gmsh.model.mesh.getNodes(
                2, stag, includeBoundary=True
            )
            if len(node_tags) == 0:
                return

            etypes, _, enodes = gmsh.model.mesh.getElements(2, stag)
            tri_count = 0
            for etype, en in zip(etypes, enodes):
                if etype == 2:
                    tri_count += len(en) // 3
                elif etype == 3:
                    tri_count += (len(en) // 4) * 2
            if tri_count == 0:
                return

            stl_name = f"{file_idx:04d}_{solid_name}_{surf_name}.stl"
            stl_path = out_dir / stl_name

            # Use gmsh's built-in STL writer for this surface
            # Create a temporary view of just this physical group
            # Simpler: write the whole model once, or write per-entity
            # via direct binary STL construction.
            _write_binary_stl(
                gmsh.model, stag, str(stl_path), solid_name
            )

            n_nodes = len(node_tags)
            total_tris += tri_count
            total_nodes += n_nodes
            file_idx += 1

            result['stl_files'].append({
                'path': str(stl_path),
                'solid_name': solid_name,
                'surface_name': surf_name,
            })

            # Report per-surface progress (65 → 95 range)
            pct = 65 + int(30 * file_idx / total_surfs)
            _progress('write', min(pct, 95), f'Surface {file_idx}/{total_surfs}')

        # Volume-grouped surfaces
        for vtag, stags in volume_groups.items():
            vol_name = _entity_name(3, vtag) or f"{stem}_solid{vtag}"
            for stag in stags:
                sname = _entity_name(2, stag) or f"{vol_name}_face{stag}"
                _write_surface(stag, vol_name, sname)

        # Unattached surfaces
        for stag in unattached:
            sname = _entity_name(2, stag) or f"{stem}_face{stag}"
            _write_surface(stag, sname, sname)

        result['total_triangles'] = total_tris
        result['total_nodes'] = total_nodes

    except Exception as exc:
        result['error'] = str(exc)
    finally:
        try:
            gmsh.finalize()
        except Exception:
            pass

    result['elapsed'] = time.perf_counter() - t0
    _progress('done', 100, 'Complete')
    return result


# ---------------------------------------------------------------------------
# Binary STL writer (avoids gmsh's global write which merges everything)
# ---------------------------------------------------------------------------

import struct
import numpy as np_compat  # numpy is a gmsh dependency, always available


def _write_binary_stl(gmsh_model, surface_tag: int, out_path: str,
                       solid_name: str = '') -> None:
    """Write a single gmsh surface entity as a binary STL file."""

    node_tags, node_coords, _ = gmsh_model.mesh.getNodes(
        2, surface_tag, includeBoundary=True
    )
    coords = np_compat.asarray(node_coords, dtype=np_compat.float64).reshape(-1, 3)
    tag_map = {int(t): i for i, t in enumerate(node_tags)}

    etypes, _, enodes = gmsh_model.mesh.getElements(2, surface_tag)

    triangles: list[tuple[int, int, int]] = []
    for etype, en in zip(etypes, enodes):
        if etype == 2:  # tri
            for i in range(0, len(en), 3):
                n = [tag_map.get(int(en[i + j])) for j in range(3)]
                if all(x is not None for x in n):
                    triangles.append(tuple(n))
        elif etype == 3:  # quad → 2 tris
            for i in range(0, len(en), 4):
                n = [tag_map.get(int(en[i + j])) for j in range(4)]
                if all(x is not None for x in n):
                    triangles.append((n[0], n[1], n[2]))
                    triangles.append((n[0], n[2], n[3]))

    num_tris = len(triangles)

    with open(out_path, 'wb') as f:
        # 80-byte header — embed solid name
        header = solid_name.encode('ascii', errors='replace')[:80]
        header = header.ljust(80, b'\x00')
        f.write(header)

        # Triangle count
        f.write(struct.pack('<I', num_tris))

        for i0, i1, i2 in triangles:
            v0 = coords[i0]
            v1 = coords[i1]
            v2 = coords[i2]
            # Normal (cross product)
            e1 = v1 - v0
            e2 = v2 - v0
            normal = np_compat.cross(e1, e2)
            norm_len = np_compat.linalg.norm(normal)
            if norm_len > 0:
                normal /= norm_len

            f.write(struct.pack('<3f', *normal.astype(np_compat.float32)))
            f.write(struct.pack('<3f', *v0.astype(np_compat.float32)))
            f.write(struct.pack('<3f', *v1.astype(np_compat.float32)))
            f.write(struct.pack('<3f', *v2.astype(np_compat.float32)))
            f.write(struct.pack('<H', 0))  # attribute byte count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Read a JSON job from stdin, process it, write JSON result to stdout."""
    raw = sys.stdin.read()
    job = json.loads(raw)
    result = _run(job)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == '__main__':
    main()
