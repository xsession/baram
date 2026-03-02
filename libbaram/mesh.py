#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Mesh geometry utilities.

Provides the :class:`Bounds` dataclass for bounding-box operations and
helper functions for mesh validation and analysis.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Bounds:
    """Axis-aligned bounding box.

    Attributes
    ----------
    xMin, xMax, yMin, yMax, zMin, zMax : float
        Extents along each axis.
    """
    xMin: float
    xMax: float
    yMin: float
    yMax: float
    zMin: float
    zMax: float

    def merge(self, bounds: 'Bounds') -> None:
        """Expand this box to encompass *bounds*."""
        self.xMin = min(self.xMin, bounds.xMin)
        self.xMax = max(self.xMax, bounds.xMax)
        self.yMin = min(self.yMin, bounds.yMin)
        self.yMax = max(self.yMax, bounds.yMax)
        self.zMin = min(self.zMin, bounds.zMin)
        self.zMax = max(self.zMax, bounds.zMax)

    def size(self) -> Tuple[float, float, float]:
        """Return ``(dx, dy, dz)`` extents."""
        return self.xMax - self.xMin, self.yMax - self.yMin, self.zMax - self.zMin

    def diagonal(self) -> float:
        """Return the diagonal length of the bounding box."""
        dx, dy, dz = self.size()
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def volume(self) -> float:
        """Return the volume of the bounding box."""
        dx, dy, dz = self.size()
        return dx * dy * dz

    def includes(self, point: Sequence[float]) -> bool:
        """Return *True* if *point* ``(x, y, z)`` is strictly inside."""
        x, y, z = point
        return (self.xMin < x < self.xMax
                and self.yMin < y < self.yMax
                and self.zMin < z < self.zMax)

    def toTuple(self) -> Tuple[float, float, float, float, float, float]:
        """Return ``(xMin, xMax, yMin, yMax, zMin, zMax)``."""
        return self.xMin, self.xMax, self.yMin, self.yMax, self.zMin, self.zMax

    def center(self) -> Tuple[float, float, float]:
        """Return the centroid ``(cx, cy, cz)``."""
        def mid(a, b):
            return (a + b) / 2
        return mid(self.xMin, self.xMax), mid(self.yMin, self.yMax), mid(self.zMin, self.zMax)

    def toInsidePoint(self, point: Sequence[float]) -> Tuple[float, float, float]:
        """Clamp *point* to lie inside (or on the boundary of) this box."""
        x, y, z = point
        return (self.xMin if x < self.xMin else self.xMax if x > self.xMax else x,
                self.yMin if y < self.yMin else self.yMax if y > self.yMax else y,
                self.zMin if z < self.zMin else self.zMax if z > self.zMax else z)

    def isValid(self) -> bool:
        """Return *True* if the box has positive extents on all axes."""
        return self.xMax > self.xMin and self.yMax > self.yMin and self.zMax > self.zMin

    def expandBy(self, fraction: float = 0.05) -> 'Bounds':
        """Return a new box expanded by *fraction* of the diagonal.

        Useful for adding padding around tight geometry.
        """
        d = self.diagonal() * fraction
        return Bounds(
            self.xMin - d, self.xMax + d,
            self.yMin - d, self.yMax + d,
            self.zMin - d, self.zMax + d,
        )

    def __repr__(self) -> str:
        return (
            f'Bounds(x=[{self.xMin:.4g}, {self.xMax:.4g}], '
            f'y=[{self.yMin:.4g}, {self.yMax:.4g}], '
            f'z=[{self.zMin:.4g}, {self.zMax:.4g}])'
        )


# ---------------------------------------------------------------------------
# Mesh quality validation
# ---------------------------------------------------------------------------

def validate_polydata(polyData, context: str = '') -> bool:
    """Perform basic sanity checks on a vtkPolyData surface.

    Parameters
    ----------
    polyData : vtkPolyData
        Surface mesh to validate.
    context : str
        Description for log messages.

    Returns
    -------
    bool
        *True* if the mesh passes all checks.
    """
    prefix = f"[{context}] " if context else ""

    if polyData is None:
        logger.warning("%sPolyData is None", prefix)
        return False

    n_points = polyData.GetNumberOfPoints()
    n_cells = polyData.GetNumberOfCells()

    if n_points < 3:
        logger.warning("%sInsufficient points: %d (need ≥ 3)", prefix, n_points)
        return False

    if n_cells < 1:
        logger.warning("%sNo cells in mesh", prefix)
        return False

    # Check for degenerate (zero-area) bounds
    bounds = polyData.GetBounds()  # (xmin, xmax, ymin, ymax, zmin, zmax)
    dx = bounds[1] - bounds[0]
    dy = bounds[3] - bounds[2]
    dz = bounds[5] - bounds[4]

    # At most one dimension can be zero (planar surface)
    zero_count = sum(1 for d in (dx, dy, dz) if abs(d) < 1e-30)
    if zero_count >= 2:
        logger.warning(
            "%sDegenerate geometry: bounds are nearly zero in %d dimensions",
            prefix, zero_count,
        )
        return False

    logger.debug(
        "%sValidation passed: %d points, %d cells, bounds=[%.4g..%.4g, %.4g..%.4g, %.4g..%.4g]",
        prefix, n_points, n_cells, *bounds,
    )
    return True


def estimate_mesh_quality(polyData) -> Optional[dict]:
    """Compute basic mesh quality metrics for a triangulated surface.

    Returns
    -------
    dict or None
        Dictionary with keys ``min_area``, ``max_area``, ``mean_area``,
        ``aspect_ratio_mean``, ``num_triangles``.  *None* if input is
        invalid.
    """
    if polyData is None or polyData.GetNumberOfCells() == 0:
        return None

    try:
        from vtkmodules.vtkFiltersVerdict import vtkCellSizeFilter
        sizeFilter = vtkCellSizeFilter()
        sizeFilter.SetInputData(polyData)
        sizeFilter.Update()
        output = sizeFilter.GetOutput()
        areas = output.GetCellData().GetArray('Area')
        if areas is None:
            return None

        n = areas.GetNumberOfTuples()
        vals = [areas.GetValue(i) for i in range(n)]
        return {
            'num_triangles': n,
            'min_area': min(vals),
            'max_area': max(vals),
            'mean_area': sum(vals) / n if n > 0 else 0,
        }
    except Exception:
        logger.debug("Could not compute mesh quality metrics", exc_info=True)
        return None
