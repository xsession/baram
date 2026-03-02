#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Parametric primitive shapes and boolean operations.

All primitives are tessellated entirely in VTK — no gmsh dependency.
Boolean operations use VTK's ``vtkBooleanOperationPolyDataFilter``.
"""

from __future__ import annotations

import math
import logging
from enum import Enum, auto
from typing import Optional, Tuple

import numpy as np

from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersCore import (
    vtkTriangleFilter,
    vtkCleanPolyData,
)
from vtkmodules.vtkFiltersSources import (
    vtkCubeSource,
    vtkCylinderSource,
    vtkSphereSource,
    vtkConeSource,
    vtkSuperquadricSource,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primitive type enum
# ---------------------------------------------------------------------------

class PrimitiveType(Enum):
    BOX = auto()
    CYLINDER = auto()
    SPHERE = auto()
    CONE = auto()
    TORUS = auto()
    WEDGE = auto()


# ---------------------------------------------------------------------------
# VTK polydata → numpy arrays
# ---------------------------------------------------------------------------

def polydata_to_numpy(pd: vtkPolyData) -> Tuple[np.ndarray, np.ndarray]:
    """Extract (vertices, faces) numpy arrays from VTK polydata.

    The polydata must consist of triangles (run through vtkTriangleFilter
    first if needed).
    """
    # Triangulate if needed
    tri = vtkTriangleFilter()
    tri.SetInputData(pd)
    tri.Update()
    pd = tri.GetOutput()

    npts = pd.GetNumberOfPoints()
    ncells = pd.GetNumberOfCells()

    verts = np.zeros((npts, 3), dtype=np.float64)
    for i in range(npts):
        verts[i] = pd.GetPoint(i)

    faces = np.zeros((ncells, 3), dtype=np.int32)
    for i in range(ncells):
        cell = pd.GetCell(i)
        if cell.GetNumberOfPoints() == 3:
            faces[i, 0] = cell.GetPointId(0)
            faces[i, 1] = cell.GetPointId(1)
            faces[i, 2] = cell.GetPointId(2)

    return verts, faces


def numpy_to_polydata(verts: np.ndarray, faces: np.ndarray) -> vtkPolyData:
    """Build VTK polydata from numpy arrays."""
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkTriangle

    points = vtkPoints()
    points.SetNumberOfPoints(verts.shape[0])
    for i in range(verts.shape[0]):
        points.SetPoint(i, float(verts[i, 0]), float(verts[i, 1]), float(verts[i, 2]))

    cells = vtkCellArray()
    for f in faces:
        t = vtkTriangle()
        t.GetPointIds().SetId(0, int(f[0]))
        t.GetPointIds().SetId(1, int(f[1]))
        t.GetPointIds().SetId(2, int(f[2]))
        cells.InsertNextCell(t)

    pd = vtkPolyData()
    pd.SetPoints(points)
    pd.SetPolys(cells)
    return pd


# ---------------------------------------------------------------------------
# Primitive generators
# ---------------------------------------------------------------------------

def make_box(
    x_len: float = 1.0,
    y_len: float = 1.0,
    z_len: float = 1.0,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Axis-aligned box.  Returns (vertices, faces)."""
    src = vtkCubeSource()
    src.SetXLength(x_len)
    src.SetYLength(y_len)
    src.SetZLength(z_len)
    src.SetCenter(*center)
    src.Update()
    return polydata_to_numpy(src.GetOutput())


def make_cylinder(
    radius: float = 0.5,
    height: float = 1.0,
    resolution: int = 32,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Cylinder along Y axis.  Returns (vertices, faces)."""
    src = vtkCylinderSource()
    src.SetRadius(radius)
    src.SetHeight(height)
    src.SetResolution(resolution)
    src.SetCenter(*center)
    src.CappingOn()
    src.Update()
    return polydata_to_numpy(src.GetOutput())


def make_sphere(
    radius: float = 0.5,
    theta_res: int = 24,
    phi_res: int = 24,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """UV sphere.  Returns (vertices, faces)."""
    src = vtkSphereSource()
    src.SetRadius(radius)
    src.SetThetaResolution(theta_res)
    src.SetPhiResolution(phi_res)
    src.SetCenter(*center)
    src.Update()
    return polydata_to_numpy(src.GetOutput())


def make_cone(
    radius: float = 0.5,
    height: float = 1.0,
    resolution: int = 32,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Cone pointing along +X.  Returns (vertices, faces)."""
    src = vtkConeSource()
    src.SetRadius(radius)
    src.SetHeight(height)
    src.SetResolution(resolution)
    src.SetCenter(*center)
    src.CappingOn()
    src.Update()
    return polydata_to_numpy(src.GetOutput())


def make_torus(
    ring_radius: float = 0.5,
    cross_section_radius: float = 0.15,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Torus (via superquadric).  Returns (vertices, faces)."""
    src = vtkSuperquadricSource()
    src.SetToroidal(True)
    src.SetSize(ring_radius)
    src.SetThickness(cross_section_radius / ring_radius)
    src.SetThetaResolution(48)
    src.SetPhiResolution(24)
    src.SetCenter(*center)
    src.Update()
    return polydata_to_numpy(src.GetOutput())


def make_wedge(
    x_len: float = 1.0,
    y_len: float = 1.0,
    z_len: float = 1.0,
    center: Tuple[float, float, float] = (0, 0, 0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Triangular wedge / prism.  Built from raw verts + faces.

    The wedge is a right triangular prism extruded along Z.
    """
    cx, cy, cz = center
    hx, hy, hz = x_len / 2, y_len / 2, z_len / 2

    verts = np.array([
        # bottom triangle (z = cz - hz)
        [cx - hx, cy - hy, cz - hz],
        [cx + hx, cy - hy, cz - hz],
        [cx,      cy + hy, cz - hz],
        # top triangle (z = cz + hz)
        [cx - hx, cy - hy, cz + hz],
        [cx + hx, cy - hy, cz + hz],
        [cx,      cy + hy, cz + hz],
    ], dtype=np.float64)

    faces = np.array([
        # bottom
        [0, 2, 1],
        # top
        [3, 4, 5],
        # front (bottom edge)
        [0, 1, 4], [0, 4, 3],
        # right slope
        [1, 2, 5], [1, 5, 4],
        # left slope
        [2, 0, 3], [2, 3, 5],
    ], dtype=np.int32)

    return verts, faces


# Map PrimitiveType → factory function (with default params)
PRIMITIVE_FACTORIES = {
    PrimitiveType.BOX:      make_box,
    PrimitiveType.CYLINDER: make_cylinder,
    PrimitiveType.SPHERE:   make_sphere,
    PrimitiveType.CONE:     make_cone,
    PrimitiveType.TORUS:    make_torus,
    PrimitiveType.WEDGE:    make_wedge,
}


# ---------------------------------------------------------------------------
# Boolean operations via VTK
# ---------------------------------------------------------------------------

class BooleanOp(Enum):
    UNION = 0
    INTERSECTION = 1
    DIFFERENCE = 2       # A minus B


def boolean_operation(
    verts_a: np.ndarray, faces_a: np.ndarray,
    verts_b: np.ndarray, faces_b: np.ndarray,
    operation: BooleanOp,
) -> Tuple[np.ndarray, np.ndarray]:
    """Perform a boolean operation on two triangle meshes.

    Returns the resulting (vertices, faces) arrays.
    Uses ``vtkBooleanOperationPolyDataFilter``.
    """
    from vtkmodules.vtkFiltersGeneral import vtkBooleanOperationPolyDataFilter

    pd_a = numpy_to_polydata(verts_a, faces_a)
    pd_b = numpy_to_polydata(verts_b, faces_b)

    boolean_filter = vtkBooleanOperationPolyDataFilter()
    boolean_filter.SetOperation(operation.value)
    boolean_filter.SetInputData(0, pd_a)
    boolean_filter.SetInputData(1, pd_b)
    boolean_filter.Update()

    # Clean up result
    clean = vtkCleanPolyData()
    clean.SetInputData(boolean_filter.GetOutput())
    clean.Update()

    return polydata_to_numpy(clean.GetOutput())


# ---------------------------------------------------------------------------
# Mesh transforms (applied to vertex data directly)
# ---------------------------------------------------------------------------

def translate_mesh(verts: np.ndarray, dx: float, dy: float, dz: float) -> np.ndarray:
    """Return a translated copy of the vertices."""
    out = verts.copy()
    out[:, 0] += dx
    out[:, 1] += dy
    out[:, 2] += dz
    return out


def scale_mesh(
    verts: np.ndarray,
    sx: float, sy: float, sz: float,
    center: Optional[Tuple[float, float, float]] = None,
) -> np.ndarray:
    """Scale vertices about a centre point."""
    out = verts.copy()
    if center is None:
        center = out.mean(axis=0)
    cx, cy, cz = center
    out[:, 0] = (out[:, 0] - cx) * sx + cx
    out[:, 1] = (out[:, 1] - cy) * sy + cy
    out[:, 2] = (out[:, 2] - cz) * sz + cz
    return out


def rotate_mesh(
    verts: np.ndarray,
    angle_deg: float,
    axis: str = 'z',
    center: Optional[Tuple[float, float, float]] = None,
) -> np.ndarray:
    """Rotate vertices about an axis through centre.

    *axis* is one of ``'x'``, ``'y'``, ``'z'``.
    """
    out = verts.copy()
    if center is None:
        center = out.mean(axis=0)
    cx, cy, cz = center
    out -= [cx, cy, cz]

    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)

    if axis.lower() == 'x':
        r = np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    elif axis.lower() == 'y':
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    else:
        r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)

    out = out @ r.T
    out += [cx, cy, cz]
    return out


def mirror_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    plane: str = 'xy',
    center: Optional[Tuple[float, float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Mirror vertices across a plane and flip face winding.

    *plane* is ``'xy'`` (mirror Z), ``'xz'`` (mirror Y), or ``'yz'`` (mirror X).
    """
    out = verts.copy()
    if center is None:
        center = out.mean(axis=0)
    cx, cy, cz = center

    if plane == 'yz':
        out[:, 0] = 2 * cx - out[:, 0]
    elif plane == 'xz':
        out[:, 1] = 2 * cy - out[:, 1]
    else:  # 'xy'
        out[:, 2] = 2 * cz - out[:, 2]

    # Flip winding
    mirrored_faces = faces[:, ::-1].copy()
    return out, mirrored_faces


# ---------------------------------------------------------------------------
# Export to STL
# ---------------------------------------------------------------------------

def export_stl(
    file_path: str,
    verts: np.ndarray,
    faces: np.ndarray,
    binary: bool = True,
):
    """Write a triangle mesh to an STL file (binary or ASCII)."""
    from vtkmodules.vtkIOGeometry import vtkSTLWriter

    pd = numpy_to_polydata(verts, faces)

    writer = vtkSTLWriter()
    writer.SetFileName(str(file_path))
    writer.SetInputData(pd)
    if binary:
        writer.SetFileTypeToBinary()
    else:
        writer.SetFileTypeToASCII()
    writer.Write()
    logger.info('Exported STL to %s (%d triangles)', file_path, faces.shape[0])
