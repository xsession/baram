#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""VTK-based 3D viewer for the CAD document.

Renders each :class:`Component` as a separate VTK actor so visibility
and colour can be toggled per-component without re-tessellating.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData, vtkTriangle
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from widgets.rendering.rendering_widget import RenderingWidget
from libbaram.qt_utils import (
    apply_vtk_theme_defaults, LIGHT_BG1, LIGHT_BG2, DARK_BG1, DARK_BG2,
)

from baramEditor.cad_document import CADDocument, Component

logger = logging.getLogger(__name__)


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


class CADViewer(QWidget):
    """3D rendering widget that displays a CADDocument's components."""

    componentPicked = Signal(int)  # tag of the picked component

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._view = RenderingWidget()
        self._layout.addWidget(self._view)

        self._actors: Dict[int, vtkActor] = {}   # tag → actor
        self._document: Optional[CADDocument] = None

    @property
    def rendering_widget(self) -> RenderingWidget:
        return self._view

    # -- Document binding ----------------------------------------------------

    def set_document(self, doc: CADDocument):
        """Bind a document and build actors for all components."""
        self.clear()
        self._document = doc
        for comp in doc.components:
            self._add_component_actor(comp)
        self._view.fitCamera()
        self._view.refresh()

    def clear(self):
        """Remove all actors."""
        for actor in self._actors.values():
            self._view.removeActor(actor)
        self._actors.clear()
        self._document = None
        self._view.refresh()

    # -- Per-component actor management --------------------------------------

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
        actor.GetProperty().SetAmbient(0.1)
        actor.GetProperty().SetDiffuse(0.7)
        actor.GetProperty().SetSpecular(0.3)

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
            # Component was added after initial set_document (e.g. primitive)
            if comp.visible and not comp.deleted:
                self._add_component_actor(comp)
            self._view.refresh()
            return

        actor.SetVisibility(comp.visible and not comp.deleted)
        actor.GetProperty().SetColor(*comp.colour[:3])
        actor.GetProperty().SetOpacity(comp.colour[3] if len(comp.colour) > 3 else 1.0)

        # Rebuild geometry when mesh vertices may have changed (scale/rotate/move)
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
            # Already present — just update
            self.update_component(comp)
            return
        self._add_component_actor(comp)
        self._view.refresh()

    def refresh_all(self):
        """Re-sync all actors with the document state."""
        if self._document is None:
            return
        # Handle components added/removed since last refresh
        doc_tags = {c.tag for c in self._document.components}
        # Remove actors for components no longer in document
        for tag in list(self._actors.keys()):
            if tag not in doc_tags:
                self._view.removeActor(self._actors.pop(tag))
        # Update or create actors for all document components
        for comp in self._document.components:
            if comp.tag in self._actors:
                actor = self._actors[comp.tag]
                actor.SetVisibility(comp.visible and not comp.deleted)
                actor.GetProperty().SetColor(*comp.colour[:3])
                actor.GetProperty().SetOpacity(comp.colour[3] if len(comp.colour) > 3 else 1.0)
                # Rebuild geometry
                pd = _component_to_polydata(comp)
                if pd is not None:
                    actor.GetMapper().SetInputData(pd)
                    actor.GetMapper().Update()
                # Transform
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
        """Apply light or dark VTK background gradient.

        Forces the correct gradient directly — the RenderingWidget's
        initial bg colours don't match the theme constants, so the
        conditional swap in ``apply_vtk_theme_defaults()`` would be a
        no-op on first call.
        """
        if dark_mode:
            self._view.setBackground1(*DARK_BG1)
            self._view.setBackground2(*DARK_BG2)
        else:
            self._view.setBackground1(*LIGHT_BG1)
            self._view.setBackground2(*LIGHT_BG2)
        self._view.refresh()

    def close(self):
        self._view.close()
        super().close()
