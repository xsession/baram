#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Editor dialogs — TinkerCAD-style property panels for transform
operations, primitive insertion, boolean operations, and STL export.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QComboBox, QDialogButtonBox, QLabel,
    QPushButton, QLineEdit, QCheckBox, QWidget,
)

from baramEditor.primitives import PrimitiveType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Translate dialog
# ---------------------------------------------------------------------------

class TranslateDialog(QDialog):
    """Move a component by (dx, dy, dz)."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Move — {name}' if name else 'Move')
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        self._dx = QDoubleSpinBox()
        self._dy = QDoubleSpinBox()
        self._dz = QDoubleSpinBox()
        for sb in (self._dx, self._dy, self._dz):
            sb.setRange(-1e6, 1e6)
            sb.setDecimals(4)
            sb.setSingleStep(0.1)
            sb.setValue(0.0)

        layout.addRow('ΔX:', self._dx)
        layout.addRow('ΔY:', self._dy)
        layout.addRow('ΔZ:', self._dz)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> Tuple[float, float, float]:
        return self._dx.value(), self._dy.value(), self._dz.value()


# ---------------------------------------------------------------------------
# Rotate dialog
# ---------------------------------------------------------------------------

class RotateDialog(QDialog):
    """Rotate a component around an axis."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Rotate — {name}' if name else 'Rotate')
        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        self._angle = QDoubleSpinBox()
        self._angle.setRange(-360, 360)
        self._angle.setDecimals(2)
        self._angle.setSingleStep(15)
        self._angle.setValue(0.0)
        self._angle.setSuffix(' °')
        layout.addRow('Angle:', self._angle)

        self._axis = QComboBox()
        self._axis.addItems(['X', 'Y', 'Z'])
        self._axis.setCurrentIndex(2)
        layout.addRow('Axis:', self._axis)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> Tuple[float, str]:
        return self._angle.value(), self._axis.currentText().lower()


# ---------------------------------------------------------------------------
# Scale dialog
# ---------------------------------------------------------------------------

class ScaleDialog(QDialog):
    """Scale a component (uniform or per-axis)."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Scale — {name}' if name else 'Scale')
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        self._uniform = QCheckBox('Uniform scale')
        self._uniform.setChecked(True)
        self._uniform.toggled.connect(self._onUniformToggled)
        layout.addWidget(self._uniform)

        form = QFormLayout()

        self._sx = QDoubleSpinBox()
        self._sy = QDoubleSpinBox()
        self._sz = QDoubleSpinBox()
        for sb in (self._sx, self._sy, self._sz):
            sb.setRange(0.001, 1000)
            sb.setDecimals(4)
            sb.setSingleStep(0.1)
            sb.setValue(1.0)

        self._sx.valueChanged.connect(self._syncUniform)

        form.addRow('X:', self._sx)
        form.addRow('Y:', self._sy)
        form.addRow('Z:', self._sz)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._onUniformToggled(True)

    def _onUniformToggled(self, checked: bool):
        self._sy.setEnabled(not checked)
        self._sz.setEnabled(not checked)
        if checked:
            self._syncUniform(self._sx.value())

    def _syncUniform(self, val: float):
        if self._uniform.isChecked():
            self._sy.setValue(val)
            self._sz.setValue(val)

    def values(self) -> Tuple[float, float, float]:
        return self._sx.value(), self._sy.value(), self._sz.value()


# ---------------------------------------------------------------------------
# Mirror dialog
# ---------------------------------------------------------------------------

class MirrorDialog(QDialog):
    """Mirror across a plane."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Mirror — {name}' if name else 'Mirror')
        self.setMinimumWidth(260)

        layout = QFormLayout(self)

        self._plane = QComboBox()
        self._plane.addItems(['XY (flip Z)', 'XZ (flip Y)', 'YZ (flip X)'])
        self._plane.setCurrentIndex(0)
        layout.addRow('Mirror plane:', self._plane)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def plane(self) -> str:
        text = self._plane.currentText()
        if 'XY' in text:
            return 'xy'
        elif 'XZ' in text:
            return 'xz'
        return 'yz'


# ---------------------------------------------------------------------------
# Add Primitive dialog
# ---------------------------------------------------------------------------

class AddPrimitiveDialog(QDialog):
    """Pick a primitive shape and its dimensions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Shape')
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)

        # Shape selector
        form = QFormLayout()

        self._shapeCombo = QComboBox()
        for pt in PrimitiveType:
            self._shapeCombo.addItem(pt.name.capitalize(), userData=pt)
        self._shapeCombo.currentIndexChanged.connect(self._onShapeChanged)
        form.addRow('Shape:', self._shapeCombo)

        self._nameEdit = QLineEdit()
        self._nameEdit.setPlaceholderText('Auto')
        form.addRow('Name:', self._nameEdit)

        layout.addLayout(form)

        # Parameter group
        self._paramGroup = QGroupBox('Parameters')
        self._paramLayout = QFormLayout(self._paramGroup)
        layout.addWidget(self._paramGroup)

        # Common parameter spinboxes
        self._xLen = self._addSpin('Width (X):', 1.0)
        self._yLen = self._addSpin('Height (Y):', 1.0)
        self._zLen = self._addSpin('Depth (Z):', 1.0)
        self._radius = self._addSpin('Radius:', 0.5)
        self._height = self._addSpin('Height:', 1.0)
        self._ringRadius = self._addSpin('Ring radius:', 0.5)
        self._tubeRadius = self._addSpin('Tube radius:', 0.15)

        # Position
        posGroup = QGroupBox('Position')
        posLayout = QFormLayout(posGroup)
        self._cx = self._makeSpin(0.0, -1e6, 1e6)
        self._cy = self._makeSpin(0.0, -1e6, 1e6)
        self._cz = self._makeSpin(0.0, -1e6, 1e6)
        posLayout.addRow('X:', self._cx)
        posLayout.addRow('Y:', self._cy)
        posLayout.addRow('Z:', self._cz)
        layout.addWidget(posGroup)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._onShapeChanged(0)

    def _makeSpin(self, val: float, lo: float = 0.001, hi: float = 1e6) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setDecimals(4)
        sb.setSingleStep(0.1)
        sb.setValue(val)
        return sb

    def _addSpin(self, label: str, val: float) -> QDoubleSpinBox:
        sb = self._makeSpin(val)
        self._paramLayout.addRow(label, sb)
        return sb

    def _onShapeChanged(self, idx: int):
        shape = self._shapeCombo.currentData()
        # Hide all params first
        for sb in (self._xLen, self._yLen, self._zLen, self._radius,
                   self._height, self._ringRadius, self._tubeRadius):
            sb.setVisible(False)
            label = self._paramLayout.labelForField(sb)
            if label:
                label.setVisible(False)

        # Show relevant params
        if shape == PrimitiveType.BOX:
            self._show(self._xLen, self._yLen, self._zLen)
        elif shape == PrimitiveType.CYLINDER:
            self._show(self._radius, self._height)
        elif shape == PrimitiveType.SPHERE:
            self._show(self._radius)
        elif shape == PrimitiveType.CONE:
            self._show(self._radius, self._height)
        elif shape == PrimitiveType.TORUS:
            self._show(self._ringRadius, self._tubeRadius)
        elif shape == PrimitiveType.WEDGE:
            self._show(self._xLen, self._yLen, self._zLen)

    def _show(self, *spinboxes):
        for sb in spinboxes:
            sb.setVisible(True)
            label = self._paramLayout.labelForField(sb)
            if label:
                label.setVisible(True)

    def primitive_type(self) -> PrimitiveType:
        return self._shapeCombo.currentData()

    def name(self) -> str:
        txt = self._nameEdit.text().strip()
        if txt:
            return txt
        return self._shapeCombo.currentText()

    def center(self) -> Tuple[float, float, float]:
        return self._cx.value(), self._cy.value(), self._cz.value()

    def params(self) -> dict:
        """Return keyword arguments suitable for the primitive factory."""
        shape = self.primitive_type()
        c = self.center()
        if shape == PrimitiveType.BOX:
            return dict(x_len=self._xLen.value(), y_len=self._yLen.value(),
                        z_len=self._zLen.value(), center=c)
        elif shape == PrimitiveType.CYLINDER:
            return dict(radius=self._radius.value(), height=self._height.value(), center=c)
        elif shape == PrimitiveType.SPHERE:
            return dict(radius=self._radius.value(), center=c)
        elif shape == PrimitiveType.CONE:
            return dict(radius=self._radius.value(), height=self._height.value(), center=c)
        elif shape == PrimitiveType.TORUS:
            return dict(ring_radius=self._ringRadius.value(),
                        cross_section_radius=self._tubeRadius.value(), center=c)
        elif shape == PrimitiveType.WEDGE:
            return dict(x_len=self._xLen.value(), y_len=self._yLen.value(),
                        z_len=self._zLen.value(), center=c)
        return dict(center=c)


# ---------------------------------------------------------------------------
# Boolean operation dialog
# ---------------------------------------------------------------------------

class BooleanDialog(QDialog):
    """Pick two components and an operation."""

    def __init__(self, parent=None, component_names: list[tuple[int, str]] = None):
        super().__init__(parent)
        self.setWindowTitle('Boolean Operation')
        self.setMinimumWidth(340)
        component_names = component_names or []

        layout = QFormLayout(self)

        self._opCombo = QComboBox()
        self._opCombo.addItems(['Union (A + B)', 'Subtract (A − B)', 'Intersect (A ∩ B)'])
        layout.addRow('Operation:', self._opCombo)

        self._comboA = QComboBox()
        self._comboB = QComboBox()
        for tag, name in component_names:
            self._comboA.addItem(name, userData=tag)
            self._comboB.addItem(name, userData=tag)
        if len(component_names) > 1:
            self._comboB.setCurrentIndex(1)
        layout.addRow('Component A:', self._comboA)
        layout.addRow('Component B:', self._comboB)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def operation_index(self) -> int:
        """0=union, 1=subtract, 2=intersect."""
        return self._opCombo.currentIndex()

    def tag_a(self) -> int:
        return self._comboA.currentData()

    def tag_b(self) -> int:
        return self._comboB.currentData()
