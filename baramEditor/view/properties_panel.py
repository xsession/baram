#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Properties / Inspector panel — shows selected component info, transform,
appearance, and mesh statistics.  Fusion 360 / Plasticity style.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton, QCheckBox,
    QColorDialog, QScrollArea, QFrame, QSizePolicy, QSlider,
)

from baramEditor.cad_document import Component

logger = logging.getLogger(__name__)


def _section_label(text: str) -> QLabel:
    """Create a styled section header label."""
    lbl = QLabel(text)
    lbl.setObjectName('sectionLabel')
    lbl.setStyleSheet(
        'color: #888; font-size: 10px; font-weight: bold; '
        'padding: 10px 0 2px 0; text-transform: uppercase;'
    )
    return lbl


def _info_label(text: str = '') -> QLabel:
    """Create a dim read-only info label."""
    lbl = QLabel(text)
    lbl.setObjectName('dimLabel')
    lbl.setStyleSheet('color: #888; font-size: 10px;')
    return lbl


def _h_line() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet('color: #484848;')
    return line


class PropertiesPanel(QWidget):
    """Right-side inspector panel for the selected component."""

    renameRequested = Signal(int, str)       # tag, new_name
    colourRequested = Signal(int, tuple)     # tag, (r,g,b,a)
    opacityChanged = Signal(int, float)      # tag, alpha 0-1
    translateRequested = Signal(int, float, float, float)  # tag, dx, dy, dz
    rotateRequested = Signal(int, float, str)   # tag, angle, axis
    scaleRequested = Signal(int, float, float, float)   # tag, sx, sy, sz

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName('cadPanel')
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)

        self._component: Optional[Component] = None

        # --- Scroll area wrapping ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(2)
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ═══ Title ═══
        self._titleLabel = QLabel('Properties')
        self._titleLabel.setObjectName('panelTitle')
        self._titleLabel.setStyleSheet(
            'color: white; font-size: 13px; font-weight: bold; padding: 2px 0;'
        )
        self._layout.addWidget(self._titleLabel)
        self._layout.addWidget(_h_line())

        # ═══ No selection placeholder ═══
        self._placeholder = QLabel('Select a component\nto see its properties')
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet('color: #666; font-size: 11px; padding: 40px 0;')
        self._layout.addWidget(self._placeholder)

        # ═══ Content (hidden until selection) ═══
        self._content = QWidget()
        self._contentLayout = QVBoxLayout(self._content)
        self._contentLayout.setContentsMargins(0, 0, 0, 0)
        self._contentLayout.setSpacing(4)
        self._layout.addWidget(self._content)
        self._content.setVisible(False)

        # --- Identity section ---
        self._contentLayout.addWidget(_section_label('IDENTITY'))
        ident_form = QFormLayout()
        ident_form.setContentsMargins(0, 0, 0, 0)
        ident_form.setSpacing(4)

        self._nameEdit = QLineEdit()
        self._nameEdit.setPlaceholderText('Component name')
        self._nameEdit.editingFinished.connect(self._onNameChanged)
        ident_form.addRow('Name', self._nameEdit)

        self._tagLabel = _info_label()
        ident_form.addRow('Tag', self._tagLabel)

        self._dimLabel = _info_label()
        ident_form.addRow('Dim', self._dimLabel)

        self._contentLayout.addLayout(ident_form)
        self._contentLayout.addWidget(_h_line())

        # --- Appearance section ---
        self._contentLayout.addWidget(_section_label('APPEARANCE'))
        appear_form = QFormLayout()
        appear_form.setContentsMargins(0, 0, 0, 0)
        appear_form.setSpacing(4)

        # Colour button
        color_row = QHBoxLayout()
        self._colourBtn = QPushButton()
        self._colourBtn.setFixedSize(28, 28)
        self._colourBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._colourBtn.setToolTip('Click to change colour')
        self._colourBtn.clicked.connect(self._onColourPick)
        color_row.addWidget(self._colourBtn)
        self._colourLabel = _info_label()
        color_row.addWidget(self._colourLabel)
        color_row.addStretch()
        appear_form.addRow('Colour', color_row)

        # Opacity slider
        opacity_row = QHBoxLayout()
        self._opacitySlider = QSlider(Qt.Orientation.Horizontal)
        self._opacitySlider.setRange(0, 100)
        self._opacitySlider.setValue(100)
        self._opacitySlider.setFixedWidth(120)
        self._opacitySlider.valueChanged.connect(self._onOpacityChanged)
        opacity_row.addWidget(self._opacitySlider)
        self._opacityLabel = _info_label('100%')
        opacity_row.addWidget(self._opacityLabel)
        opacity_row.addStretch()
        appear_form.addRow('Opacity', opacity_row)

        # Visibility
        self._visibleCheck = QCheckBox('Visible')
        self._visibleCheck.setChecked(True)
        appear_form.addRow('', self._visibleCheck)

        self._contentLayout.addLayout(appear_form)
        self._contentLayout.addWidget(_h_line())

        # --- Geometry section ---
        self._contentLayout.addWidget(_section_label('GEOMETRY'))
        geo_form = QFormLayout()
        geo_form.setContentsMargins(0, 0, 0, 0)
        geo_form.setSpacing(4)

        self._triCountLabel = _info_label()
        geo_form.addRow('Triangles', self._triCountLabel)

        self._vertCountLabel = _info_label()
        geo_form.addRow('Vertices', self._vertCountLabel)

        self._bboxMinLabel = _info_label()
        geo_form.addRow('BB Min', self._bboxMinLabel)

        self._bboxMaxLabel = _info_label()
        geo_form.addRow('BB Max', self._bboxMaxLabel)

        self._bboxSizeLabel = _info_label()
        geo_form.addRow('BB Size', self._bboxSizeLabel)

        self._contentLayout.addLayout(geo_form)
        self._contentLayout.addWidget(_h_line())

        # --- Transform section ---
        self._contentLayout.addWidget(_section_label('TRANSFORM'))
        tf_form = QFormLayout()
        tf_form.setContentsMargins(0, 0, 0, 0)
        tf_form.setSpacing(4)

        self._posLabels = []
        for axis in ('X', 'Y', 'Z'):
            lbl = _info_label('0.0000')
            tf_form.addRow(f'Pos {axis}', lbl)
            self._posLabels.append(lbl)

        self._contentLayout.addLayout(tf_form)

        # Spacer at the bottom
        self._contentLayout.addStretch()

    # ════════════════════════════════════════════════════════════════
    #  Public API
    # ════════════════════════════════════════════════════════════════

    def set_component(self, comp: Optional[Component]):
        """Show properties for the given component, or clear."""
        self._component = comp
        if comp is None:
            self._content.setVisible(False)
            self._placeholder.setVisible(True)
            return

        self._placeholder.setVisible(False)
        self._content.setVisible(True)

        # --- Identity ---
        self._nameEdit.blockSignals(True)
        self._nameEdit.setText(comp.name)
        self._nameEdit.blockSignals(False)

        self._tagLabel.setText(str(comp.tag))
        self._dimLabel.setText(f'{comp.dim}D' if comp.dim else '—')

        # --- Appearance ---
        r, g, b, a = comp.colour
        self._updateColourSwatch(r, g, b)
        self._colourLabel.setText(
            f'({r:.2f}, {g:.2f}, {b:.2f})'
        )

        self._opacitySlider.blockSignals(True)
        self._opacitySlider.setValue(int(a * 100))
        self._opacitySlider.blockSignals(False)
        self._opacityLabel.setText(f'{int(a * 100)}%')

        self._visibleCheck.blockSignals(True)
        self._visibleCheck.setChecked(comp.visible and not comp.deleted)
        self._visibleCheck.blockSignals(False)

        # --- Geometry ---
        if comp.mesh:
            ntri = comp.mesh.triangle_count()
            nvert = comp.mesh.vertices.shape[0]
            self._triCountLabel.setText(f'{ntri:,}')
            self._vertCountLabel.setText(f'{nvert:,}')

            bb = comp.bounding_box()
            if bb:
                vmin, vmax = bb
                size = vmax - vmin
                self._bboxMinLabel.setText(
                    f'({vmin[0]:.3f}, {vmin[1]:.3f}, {vmin[2]:.3f})'
                )
                self._bboxMaxLabel.setText(
                    f'({vmax[0]:.3f}, {vmax[1]:.3f}, {vmax[2]:.3f})'
                )
                self._bboxSizeLabel.setText(
                    f'({size[0]:.3f}, {size[1]:.3f}, {size[2]:.3f})'
                )
            else:
                for lbl in (self._bboxMinLabel, self._bboxMaxLabel, self._bboxSizeLabel):
                    lbl.setText('—')
        else:
            for lbl in (self._triCountLabel, self._vertCountLabel,
                        self._bboxMinLabel, self._bboxMaxLabel, self._bboxSizeLabel):
                lbl.setText('—')

        # --- Transform ---
        if comp.mesh and comp.mesh.vertices.shape[0] > 0:
            centroid = comp.mesh.vertices.mean(axis=0)
            for i, lbl in enumerate(self._posLabels):
                lbl.setText(f'{centroid[i]:.4f}')
        else:
            for lbl in self._posLabels:
                lbl.setText('—')

    def clear(self):
        self.set_component(None)

    # ════════════════════════════════════════════════════════════════
    #  Private slots
    # ════════════════════════════════════════════════════════════════

    def _updateColourSwatch(self, r: float, g: float, b: float):
        ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
        self._colourBtn.setStyleSheet(
            f'background-color: rgb({ri},{gi},{bi}); '
            f'border: 2px solid #555; border-radius: 4px;'
        )

    def _onNameChanged(self):
        if self._component is None:
            return
        new_name = self._nameEdit.text().strip()
        if new_name and new_name != self._component.name:
            self.renameRequested.emit(self._component.tag, new_name)

    def _onColourPick(self):
        if self._component is None:
            return
        r, g, b, a = self._component.colour
        initial = QColor.fromRgbF(r, g, b, a)
        colour = QColorDialog.getColor(
            initial, self, 'Component Colour',
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if colour.isValid():
            self.colourRequested.emit(
                self._component.tag,
                (colour.redF(), colour.greenF(), colour.blueF(), colour.alphaF()),
            )

    def _onOpacityChanged(self, value: int):
        if self._component is None:
            return
        alpha = value / 100.0
        self._opacityLabel.setText(f'{value}%')
        self.opacityChanged.emit(self._component.tag, alpha)
