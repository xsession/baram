#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Boundary-condition color coding — FlowEFD-style visual mapping.

Each boundary type gets a distinct color so users can instantly identify
inlet / outlet / wall / symmetry / interface regions in the 3D viewport.
Colors are chosen to mirror industry-standard CFD tools (FloEFD, STAR-CCM+,
Fluent) where convention is:
  - Blue tones  → inlets
  - Red/orange  → outlets
  - Gray        → walls
  - Green       → symmetry / periodic
  - Yellow      → special (fans, porous jump)
"""

from __future__ import annotations

from baramFlow.coredb.boundary_db import BoundaryType


# RGB colors (0-1 float) for each boundary type category
# Format: (R, G, B)

# ── Inlets: blue family ──
_INLET_BLUE = (0.2, 0.5, 0.9)
_INLET_LIGHT = (0.3, 0.6, 1.0)
_INLET_DARK = (0.15, 0.35, 0.75)

# ── Outlets: red/orange family ──
_OUTLET_RED = (0.9, 0.3, 0.2)
_OUTLET_ORANGE = (0.95, 0.55, 0.2)
_OUTLET_LIGHT = (1.0, 0.4, 0.3)

# ── Walls: gray family ──
_WALL_GRAY = (0.7, 0.7, 0.7)
_WALL_WARM = (0.75, 0.65, 0.6)

# ── Symmetry / periodic: green family ──
_SYMMETRY_GREEN = (0.3, 0.8, 0.4)
_CYCLIC_TEAL = (0.2, 0.7, 0.7)

# ── Special: yellow/purple ──
_FAN_YELLOW = (0.9, 0.85, 0.3)
_INTERFACE_PURPLE = (0.7, 0.4, 0.9)
_POROUS_AMBER = (0.85, 0.7, 0.2)

# ── Empty / wedge: dim ──
_EMPTY_DIM = (0.5, 0.5, 0.5)


BC_TYPE_COLORS: dict[BoundaryType, tuple[float, float, float]] = {
    # Inlets
    BoundaryType.VELOCITY_INLET:      _INLET_BLUE,
    BoundaryType.FLOW_RATE_INLET:     _INLET_BLUE,
    BoundaryType.PRESSURE_INLET:      _INLET_LIGHT,
    BoundaryType.INTAKE_FAN:          _INLET_DARK,
    BoundaryType.ABL_INLET:           _INLET_DARK,
    BoundaryType.OPEN_CHANNEL_INLET:  _INLET_LIGHT,
    BoundaryType.FREE_STREAM:         _INLET_BLUE,
    BoundaryType.FAR_FIELD_RIEMANN:   _INLET_DARK,
    BoundaryType.SUBSONIC_INLET:      _INLET_BLUE,
    BoundaryType.SUPERSONIC_INFLOW:   _INLET_DARK,

    # Outlets
    BoundaryType.FLOW_RATE_OUTLET:    _OUTLET_RED,
    BoundaryType.PRESSURE_OUTLET:     _OUTLET_RED,
    BoundaryType.EXHAUST_FAN:         _OUTLET_ORANGE,
    BoundaryType.OPEN_CHANNEL_OUTLET: _OUTLET_LIGHT,
    BoundaryType.OUTFLOW:             _OUTLET_ORANGE,
    BoundaryType.SUBSONIC_OUTFLOW:    _OUTLET_RED,
    BoundaryType.SUPERSONIC_OUTFLOW:  _OUTLET_RED,

    # Walls
    BoundaryType.WALL:                _WALL_GRAY,
    BoundaryType.THERMO_COUPLED_WALL: _WALL_WARM,

    # Special
    BoundaryType.POROUS_JUMP:         _POROUS_AMBER,
    BoundaryType.FAN:                 _FAN_YELLOW,

    # Symmetry / internal
    BoundaryType.SYMMETRY:            _SYMMETRY_GREEN,
    BoundaryType.INTERFACE:           _INTERFACE_PURPLE,
    BoundaryType.EMPTY:               _EMPTY_DIM,
    BoundaryType.CYCLIC:              _CYCLIC_TEAL,
    BoundaryType.WEDGE:               _EMPTY_DIM,
}

# Friendly category names for the legend
BC_CATEGORY_COLORS: list[tuple[str, tuple[float, float, float]]] = [
    ('Inlet',          _INLET_BLUE),
    ('Outlet',         _OUTLET_RED),
    ('Wall',           _WALL_GRAY),
    ('Symmetry',       _SYMMETRY_GREEN),
    ('Interface',      _INTERFACE_PURPLE),
    ('Fan / Porous',   _FAN_YELLOW),
    ('Cyclic',         _CYCLIC_TEAL),
    ('Empty / Wedge',  _EMPTY_DIM),
]


def get_bc_color(bctype: BoundaryType) -> tuple[float, float, float]:
    """Return the RGB color for a boundary type."""
    return BC_TYPE_COLORS.get(bctype, _WALL_GRAY)
