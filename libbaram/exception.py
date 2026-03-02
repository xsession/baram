#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""BARAM exception hierarchy.

Provides a structured, enterprise-grade exception tree so that callers
can catch errors at the appropriate granularity:

.. code-block:: text

    BaramError
    ├── CanceledException        — user-initiated cancellation
    ├── ConfigurationError       — invalid or missing configuration
    ├── GeometryError            — geometry import / processing failures
    │   ├── CADImportError       — STEP/IGES/BREP specific
    │   ├── STLImportError       — STL-specific
    │   └── TessellationError    — surface mesh generation failure
    ├── MeshError                — mesh generation / conversion failures
    │   ├── SnappyHexMeshError
    │   └── MeshConversionError
    ├── SolverError              — OpenFOAM solver failures
    ├── DatabaseError            — project database failures
    └── DependencyError          — missing optional dependency

Design principles
-----------------
* Every custom exception carries a *user_message* suitable for display
  in a Qt ``QMessageBox`` and a *technical_detail* for log files.
* The ``error_code`` attribute is a short machine-readable string for
  reliable programmatic handling and i18n lookup.
"""

from __future__ import annotations

from typing import Optional


class BaramError(Exception):
    """Base exception for all BARAM application errors.

    Parameters
    ----------
    message : str
        Human-readable error description.
    error_code : str, optional
        Short machine-readable code (e.g. ``'GEOM_001'``).
    technical_detail : str, optional
        Additional context for log files (file paths, stack details).
    """

    def __init__(
        self,
        message: str = '',
        error_code: Optional[str] = None,
        technical_detail: Optional[str] = None,
    ):
        super().__init__(message)
        self.user_message = message
        self.error_code = error_code or ''
        self.technical_detail = technical_detail or ''

    def __str__(self):
        parts = [self.user_message]
        if self.error_code:
            parts.append(f'[{self.error_code}]')
        return ' '.join(parts)


# ── Cancellation ──────────────────────────────────────────────────────

class CanceledException(BaramError):
    """Raised when the user cancels a long-running operation."""

    def __init__(self, message: str = 'Operation cancelled by user'):
        super().__init__(message, error_code='CANCEL')


# ── Configuration ─────────────────────────────────────────────────────

class ConfigurationError(BaramError):
    """Raised for invalid or missing configuration."""

    def __init__(self, message: str, key: str = ''):
        super().__init__(
            message,
            error_code='CFG_001',
            technical_detail=f'config_key={key}' if key else '',
        )


# ── Geometry ──────────────────────────────────────────────────────────

class GeometryError(BaramError):
    """Base for geometry import / processing errors."""

    def __init__(self, message: str, error_code: str = 'GEOM_000', **kw):
        super().__init__(message, error_code=error_code, **kw)


class CADImportError(GeometryError):
    """Raised when a STEP/IGES/BREP file cannot be imported."""

    def __init__(self, message: str, file_path: str = ''):
        super().__init__(
            message,
            error_code='GEOM_CAD_001',
            technical_detail=f'file={file_path}',
        )


class STLImportError(GeometryError):
    """Raised when an STL file cannot be imported."""

    def __init__(self, message: str, file_path: str = ''):
        super().__init__(
            message,
            error_code='GEOM_STL_001',
            technical_detail=f'file={file_path}',
        )


class TessellationError(GeometryError):
    """Raised when surface tessellation fails."""

    def __init__(self, message: str):
        super().__init__(message, error_code='GEOM_TESS_001')


# ── Mesh ──────────────────────────────────────────────────────────────

class MeshError(BaramError):
    """Base for mesh generation / conversion errors."""

    def __init__(self, message: str, error_code: str = 'MESH_000', **kw):
        super().__init__(message, error_code=error_code, **kw)


class SnappyHexMeshError(MeshError):
    """Raised when snappyHexMesh fails."""

    def __init__(self, message: str, stage: str = ''):
        super().__init__(
            message,
            error_code='MESH_SNAPPY_001',
            technical_detail=f'stage={stage}',
        )


class MeshConversionError(MeshError):
    """Raised when mesh format conversion fails."""

    def __init__(self, message: str, converter: str = ''):
        super().__init__(
            message,
            error_code='MESH_CONV_001',
            technical_detail=f'converter={converter}',
        )


# ── Solver ────────────────────────────────────────────────────────────

class SolverError(BaramError):
    """Raised when an OpenFOAM solver fails."""

    def __init__(self, message: str, solver: str = '', returncode: int = -1):
        super().__init__(
            message,
            error_code='SOLVER_001',
            technical_detail=f'solver={solver} rc={returncode}',
        )
        self.returncode = returncode


# ── Database ──────────────────────────────────────────────────────────

class DatabaseError(BaramError):
    """Raised for project database (HDF5) failures."""

    def __init__(self, message: str):
        super().__init__(message, error_code='DB_001')


# ── Dependencies ──────────────────────────────────────────────────────

class DependencyError(BaramError):
    """Raised when a required optional dependency is missing."""

    def __init__(self, package: str, purpose: str = '', install_cmd: str = ''):
        msg = f"Required package '{package}' is not installed."
        if purpose:
            msg += f" It is needed for {purpose}."
        if install_cmd:
            msg += f"\nInstall with: {install_cmd}"
        super().__init__(
            msg,
            error_code='DEP_001',
            technical_detail=f'package={package}',
        )
        self.package = package
        self.install_cmd = install_cmd
