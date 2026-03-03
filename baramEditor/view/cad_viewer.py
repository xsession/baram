#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VTK-based 3D viewer for the CAD document — Fusion 360 / Plasticity style.

Renders each :class:`Component` as a separate VTK actor. Includes:
- Floating viewport toolbar (fit, perspective, wireframe, axis views, grid)
- VTK orientation marker (axes widget)
- Optional ground-plane grid
- Per-component highlight on selection
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout

from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData, vtkTriangle
from vtkmodules.vtkFiltersSources import vtkPlaneSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkProperty

from widgets.rendering.rendering_widget import RenderingWidget
from libbaram.qt_utils import (
    apply_vtk_theme_defaults, LIGHT_BG1, LIGHT_BG2, DARK_BG1, DARK_BG2,
)

from baramEditor.cad_document import CADDocument, Component
from baramEditor.view.viewport_toolbar import ViewportToolbar

logger = logging.getLogger(__name__)

# ── Colours ────────────────────────────────────────────────────
_HIGHLIGHT_COLOR = (0.2, 0.7, 1.0)   # selection highlight
_GRID_COLOR = (0.35, 0.35, 0.35)
_GRID_OPACITY = 0.4


def _component_to_polydata(comp: Component) -> Optional[vtkPolyData]:
    """Convert a Component's mesh to VTK polydata."""
    mesh = comp.mesh
    if mesh is None or mesh.vertices.shape[0] == 0:
        return None

    points = vtkPoints()
    points.SetNumberOfPoints(mesh.vertices.shape[0])
    for i, (x, y, z) in enumerate(mesh.vertices):
        points.SetPoint(i, float(x), float(y), float(z))

    cells = vtkCellArray()
    for f in mesh.faces:
        tri = vtkTriangle()
        tri.GetPointIds().SetId(0, int(f[0]))
        tri.GetPointIds().SetId(1, int(f[1]))
        tri.GetPointIds().SetId(2, int(f[2]))
        cells.InsertNextCell(tri)

    pd = vtkPolyData()
    pd.SetPoints(points)
    pd.SetPolys(cells)
    return pd


def _make_grid_actor(size: float = 20.0, divisions: int = 40) -> vtkActor:
    """Create a ground-plane grid actor."""
    plane = vtkPlaneSource()
    plane.SetOrigin(-size, -size, 0)
    plane.SetPoint1(size, -size, 0)
    plane.SetPoint2(-size, size, 0)
    plane.SetXResolution(divisions)
    plane.SetYResolution(divisions)
    plane.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(plane.GetOutput())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetRepresentationToWireframe()
    actor.GetProperty().SetColor(*_GRID_COLOR)
    actor.GetProperty().SetOpacity(_GRID_OPACITY)
    actor.GetProperty().SetLineWidth(0.5)
    actor.GetProperty().LightingOff()
    actor.SetPickable(False)
    return actor


class CADViewer(QWidget):
    """3D rendering widget that displays a CADDocument's components.

    Includes a floating ViewportToolbar overlaid on the viewport.
    """

    componentPicked = Signal(int)  # tag of the picked component

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._view = RenderingWidget()
        self._layout.addWidget(self._view)

        # Floating viewport toolbar
        self._vpToolbar = ViewportToolbar(self._view)
        self._vpToolbar.move(8, 8)
        self._vpToolbar.raise_()

        self._actors: Dict[int, vtkActor] = {}   # tag → actor
        self._document: Optional[CADDocument] = None
        self._selectedTag: Optional[int] = None
        self._wireframeMode = False

        # Grid
        self._gridActor: Optional[vtkActor] = None
        self._gridVisible = True
        self._setup_grid()

        # Axis widget
        self._view.setAxisVisible(True)

        # Connect viewport toolbar signals
        self._vpToolbar.fitAllClicked.connect(self.fit_camera)
        self._vpToolbar.perspectiveToggled.connect(self._onPerspectiveToggle)
        self._vpToolbar.wireframeToggled.connect(self._onWireframeToggle)
        self._vpToolbar.gridToggled.connect(self._onGridToggle)
        self._vpToolbar.axesToggled.connect(self._onAxesToggle)
        self._vpToolbar.cubeAxesToggled.connect(self._onCubeAxesToggle)

        self._vpToolbar.viewFront.connect(lambda: self._set_camera_preset(( 0,  0,  1), (0, 1, 0)))
        self._vpToolbar.viewBack.connect( lambda: self._set_camera_preset(( 0,  0, -1), (0, 1, 0)))
        self._vpToolbar.viewTop.connect(  lambda: self._set_camera_preset(( 0,  1,  0), (0, 0, -1)))
        self._vpToolbar.viewBottom.connect(lambda: self._set_camera_preset(( 0, -1,  0), (0, 0, 1)))
        self._vpToolbar.viewLeft.connect( lambda: self._set_camera_preset((-1,  0,  0), (0, 1, 0)))
        self._vpToolbar.viewRight.connect(lambda: self._set_camera_preset(( 1,  0,  0), (0, 1, 0)))

    @property
    def rendering_widget(self) -> RenderingWidget:
        return self._view

    # ── Grid ───────────────────────────────────────────────────────

    def _setup_grid(self):
        self._gridActor = _make_grid_actor()
        self._view.addActor(self._gridActor)

    def _update_grid_size(self):
        """Resize grid to match the scene bounding box."""
        if self._gridActor is None or self._document is None:
            return
        bounds = self._view.getBounds()
        if bounds is None:
            return
        extent = max(abs(bounds[1] - bounds[0]),
                     abs(bounds[3] - bounds[2]),
                     abs(bounds[5] - bounds[4]), 10.0)
        self._view.removeActor(self._gridActor)
        self._gridActor = _make_grid_actor(size=extent * 1.5, divisions=40)
        self._gridActor.SetVisibility(self._gridVisible)
        self._view.addActor(self._gridActor)

    # ── Document binding ───────────────────────────────────────────

    def set_document(self, doc: CADDocument):
        """Bind a document and build actors for all components."""
        self.clear()
        self._document = doc
        for comp in doc.components:
            self._add_component_actor(comp)
        self._update_grid_size()
        self._view.fitCamera()
        self._view.refresh()

    def clear(self):
        """Remove all component actors (keep grid and axes)."""
        for actor in self._actors.values():
            self._view.removeActor(actor)
        self._actors.clear()
        self._document = None
        self._selectedTag = None
        self._view.refresh()

    # ── Selection / highlight ──────────────────────────────────────

    def select_component(self, tag: Optional[int]):
        """Highlight the selected component, de-highlight the previous."""
        # Restore previous
        if self._selectedTag is not None and self._selectedTag in self._actors:
            prev_comp = self._document.component_by_tag(self._selectedTag) if self._document else None
            if prev_comp:
                actor = self._actors[self._selectedTag]
                actor.GetProperty().SetColor(*prev_comp.colour[:3])
                actor.GetProperty().EdgeVisibilityOff()

        self._selectedTag = tag

        # Highlight new
        if tag is not None and tag in self._actors:
            actor = self._actors[tag]
            # Subtle highlight: edge visibility + slight colour shift
            actor.GetProperty().SetEdgeVisibility(True)
            actor.GetProperty().SetEdgeColor(*_HIGHLIGHT_COLOR)
            actor.GetProperty().SetLineWidth(1.5)

        self._view.refresh()

    # ── Per-component actor management ─────────────────────────────

    def _add_component_actor(self, comp: Component):
        pd = _component_to_polydata(comp)
        if pd is None:
            return

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(pd)

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*comp.colour[:3])
        actor.GetProperty().SetOpacity(comp.colour[3] if len(comp.colour) > 3 else 1.0)
        actor.GetProperty().SetInterpolationToPhong()
        actor.GetProperty().SetAmbient(0.15)
        actor.GetProperty().SetDiffuse(0.65)
        actor.GetProperty().SetSpecular(0.35)
        actor.GetProperty().SetSpecularPower(32)

        if self._wireframeMode:
            actor.GetProperty().SetRepresentationToWireframe()
        else:
            actor.GetProperty().SetRepresentationToSurface()

        # Apply transform
        if not np.allclose(comp.transform, np.eye(4)):
            from vtkmodules.vtkCommonTransforms import vtkTransform
            t = vtkTransform()
            t.SetMatrix(comp.transform.flatten().tolist())
            actor.SetUserTransform(t)

        actor.SetVisibility(comp.visible and not comp.deleted)

        self._actors[comp.tag] = actor
        self._view.addActor(actor)

    def update_component(self, comp: Component):
        """Update the actor for a single component after a modification."""
        actor = self._actors.get(comp.tag)
        if actor is None:
            if comp.visible and not comp.deleted:
                self._add_component_actor(comp)
            self._view.refresh()
            return

        actor.SetVisibility(comp.visible and not comp.deleted)
        actor.GetProperty().SetColor(*comp.colour[:3])
        actor.GetProperty().SetOpacity(comp.colour[3] if len(comp.colour) > 3 else 1.0)

        # Rebuild geometry when mesh vertices may have changed
        pd = _component_to_polydata(comp)
        if pd is not None:
            actor.GetMapper().SetInputData(pd)
            actor.GetMapper().Update()

        # Update transform
        if not np.allclose(comp.transform, np.eye(4)):
            from vtkmodules.vtkCommonTransforms import vtkTransform
            t = vtkTransform()
            t.SetMatrix(comp.transform.flatten().tolist())
            actor.SetUserTransform(t)
        else:
            actor.SetUserTransform(None)

        self._view.refresh()

    def add_new_component(self, comp: Component):
        """Add a new actor for a freshly-created component."""
        if comp.tag in self._actors:
            self.update_component(comp)
            return
        self._add_component_actor(comp)
        self._view.refresh()

    def refresh_all(self):
        """Re-sync all actors with the document state."""
        if self._document is None:
            return
        doc_tags = {c.tag for c in self._document.components}
        for tag in list(self._actors.keys()):
            if tag not in doc_tags:
                self._view.removeActor(self._actors.pop(tag))
        for comp in self._document.components:
            if comp.tag in self._actors:
                actor = self._actors[comp.tag]
                actor.SetVisibility(comp.visible and not comp.deleted)
                actor.GetProperty().SetColor(*comp.colour[:3])
                actor.GetProperty().SetOpacity(comp.colour[3] if len(comp.colour) > 3 else 1.0)
                pd = _component_to_polydata(comp)
                if pd is not None:
                    actor.GetMapper().SetInputData(pd)
                    actor.GetMapper().Update()
                if not np.allclose(comp.transform, np.eye(4)):
                    from vtkmodules.vtkCommonTransforms import vtkTransform
                    t = vtkTransform()
                    t.SetMatrix(comp.transform.flatten().tolist())
                    actor.SetUserTransform(t)
                else:
                    actor.SetUserTransform(None)
            else:
                self._add_component_actor(comp)
        self._view.refresh()

    def fit_camera(self):
        self._view.fitCamera()

    def apply_theme(self, dark_mode: bool):
        """Apply light or dark VTK background gradient."""
        if dark_mode:
            self._view.setBackground1(*DARK_BG1)
            self._view.setBackground2(*DARK_BG2)
        else:
            self._view.setBackground1(*LIGHT_BG1)
            self._view.setBackground2(*LIGHT_BG2)
        self._view.refresh()

    # ── Viewport toolbar callbacks ─────────────────────────────────

    def _onPerspectiveToggle(self, perspective: bool):
        self._view.setParallelProjection(not perspective)

    def _onWireframeToggle(self, wireframe: bool):
        self._wireframeMode = wireframe
        for actor in self._actors.values():
            if wireframe:
                actor.GetProperty().SetRepresentationToWireframe()
            else:
                actor.GetProperty().SetRepresentationToSurface()
        self._view.refresh()

    def _onGridToggle(self, visible: bool):
        self._gridVisible = visible
        if self._gridActor:
            self._gridActor.SetVisibility(visible)
        self._view.refresh()

    def _onAxesToggle(self, visible: bool):
        self._view.setAxisVisible(visible)

    def _onCubeAxesToggle(self, visible: bool):
        self._view.setCubeAxisVisible(visible)

    def _set_camera_preset(self, direction: tuple, up: tuple):
        """Set the camera to a predefined orientation."""
        cam = self._view.renderer().GetActiveCamera()
        d = cam.GetDistance()
        fx, fy, fz = cam.GetFocalPoint()
        cam.SetPosition(
            fx - direction[0] * d,
            fy - direction[1] * d,
            fz - direction[2] * d,
        )
        cam.SetViewUp(*up)
        self._view.renderer().ResetCamera()
        self._view.refresh()

    def close(self):
        self._view.close()
        super().close()
