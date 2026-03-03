#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Editor dialogs — Fusion 360-style modal dialogs for transform
operations, primitive insertion, boolean operations, and STL export.

All dialogs inherit the parent CAD stylesheet via Qt cascading,
with additional local styling for a cohesive dark-theme look.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDoubleSpinBox, QComboBox, QDialogButtonBox, QLabel,
    QPushButton, QLineEdit, QCheckBox, QWidget, QFrame,
)

from baramEditor.primitives import PrimitiveType
from baramEditor.view.cad_style import (
    ACCENT, ACCENT_HOVER, ACCENT_PRESSED,
    BG_DARK, BG_PANEL, BG_INPUT, BG_HOVER, BORDER, TEXT, TEXT_DIM,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Shared dialog style — applied to every dialog in this module
# ──────────────────────────────────────────────────────────────

_DIALOG_STYLE = f"""
QDialog {{
    background-color: {BG_PANEL};
    color: {TEXT};
}}
QLabel {{
    color: {TEXT};
    font-size: 12px;
}}
QGroupBox {{
    color: {TEXT};
    font-weight: bold;
    font-size: 12px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 14px;
    padding-top: 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    color: {ACCENT};
}}
QDoubleSpinBox, QLineEdit {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 4px 6px;
    min-height: 22px;
}}
QDoubleSpinBox:focus, QLineEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 22px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_DARK};
    color: {TEXT};
    selection-background-color: {ACCENT};
    border: 1px solid {BORDER};
}}
QCheckBox {{
    color: {TEXT};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
}}
QPushButton, QDialogButtonBox QPushButton {{
    background-color: {BG_INPUT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 18px;
    min-width: 72px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {ACCENT_PRESSED};
}}
/* Primary action button (OK / Accept) */
QPushButton[text="OK"], QPushButton[text="&OK"] {{
    background-color: {ACCENT};
    color: #FFF;
    border-color: {ACCENT};
}}
QPushButton[text="OK"]:hover, QPushButton[text="&OK"]:hover {{
    background-color: {ACCENT_HOVER};
}}
"""


def _section_header(text: str) -> QLabel:
    """Small accent-coloured section label."""
    lbl = QLabel(text)
    lbl.setStyleSheet(f'color: {ACCENT}; font-size: 11px; font-weight: bold; '
                      f'padding: 4px 0 2px 0;')
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet(f'color: {BORDER};')
    return line


# ─────────────────────────────────────────────────────────────
# Translate dialog
# ─────────────────────────────────────────────────────────────

class TranslateDialog(QDialog):
    """Move a component by (dx, dy, dz)."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Move — {name}' if name else 'Move')
        self.setMinimumWidth(340)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_section_header('DISPLACEMENT'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._dx = QDoubleSpinBox()
        self._dy = QDoubleSpinBox()
        self._dz = QDoubleSpinBox()
        for sb in (self._dx, self._dy, self._dz):
            sb.setRange(-1e6, 1e6)
            sb.setDecimals(4)
            sb.setSingleStep(0.1)
            sb.setValue(0.0)

        form.addRow('ΔX :', self._dx)
        form.addRow('ΔY :', self._dy)
        form.addRow('ΔZ :', self._dz)
        layout.addLayout(form)

        layout.addWidget(_separator())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> Tuple[float, float, float]:
        return self._dx.value(), self._dy.value(), self._dz.value()


# ─────────────────────────────────────────────────────────────
# Rotate dialog
# ─────────────────────────────────────────────────────────────

class RotateDialog(QDialog):
    """Rotate a component around an axis."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Rotate — {name}' if name else 'Rotate')
        self.setMinimumWidth(340)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_section_header('ROTATION'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._angle = QDoubleSpinBox()
        self._angle.setRange(-360, 360)
        self._angle.setDecimals(2)
        self._angle.setSingleStep(15)
        self._angle.setValue(0.0)
        self._angle.setSuffix(' °')
        form.addRow('Angle :', self._angle)

        self._axis = QComboBox()
        self._axis.addItems(['X', 'Y', 'Z'])
        self._axis.setCurrentIndex(2)
        form.addRow('Axis :', self._axis)

        layout.addLayout(form)
        layout.addWidget(_separator())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> Tuple[float, str]:
        return self._angle.value(), self._axis.currentText().lower()


# ─────────────────────────────────────────────────────────────
# Scale dialog
# ─────────────────────────────────────────────────────────────

class ScaleDialog(QDialog):
    """Scale a component (uniform or per-axis)."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Scale — {name}' if name else 'Scale')
        self.setMinimumWidth(340)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_section_header('SCALE MODE'))

        self._uniform = QCheckBox('Uniform scale')
        self._uniform.setChecked(True)
        self._uniform.toggled.connect(self._onUniformToggled)
        layout.addWidget(self._uniform)

        layout.addWidget(_section_header('FACTORS'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._sx = QDoubleSpinBox()
        self._sy = QDoubleSpinBox()
        self._sz = QDoubleSpinBox()
        for sb in (self._sx, self._sy, self._sz):
            sb.setRange(0.001, 1000)
            sb.setDecimals(4)
            sb.setSingleStep(0.1)
            sb.setValue(1.0)

        self._sx.valueChanged.connect(self._syncUniform)

        form.addRow('X :', self._sx)
        form.addRow('Y :', self._sy)
        form.addRow('Z :', self._sz)
        layout.addLayout(form)

        layout.addWidget(_separator())

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


# ─────────────────────────────────────────────────────────────
# Mirror dialog
# ─────────────────────────────────────────────────────────────

class MirrorDialog(QDialog):
    """Mirror across a plane."""

    def __init__(self, parent=None, name: str = ''):
        super().__init__(parent)
        self.setWindowTitle(f'Mirror — {name}' if name else 'Mirror')
        self.setMinimumWidth(320)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_section_header('MIRROR PLANE'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._plane = QComboBox()
        self._plane.addItems(['XY  (flip Z)', 'XZ  (flip Y)', 'YZ  (flip X)'])
        self._plane.setCurrentIndex(0)
        form.addRow('Plane :', self._plane)
        layout.addLayout(form)

        layout.addWidget(_separator())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def plane(self) -> str:
        text = self._plane.currentText()
        if 'XY' in text:
            return 'xy'
        elif 'XZ' in text:
            return 'xz'
        return 'yz'


# ─────────────────────────────────────────────────────────────
# Add Primitive dialog
# ─────────────────────────────────────────────────────────────

class AddPrimitiveDialog(QDialog):
    """Pick a primitive shape and its dimensions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Shape')
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Shape selector ──
        layout.addWidget(_section_header('SHAPE'))
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._shapeCombo = QComboBox()
        for pt in PrimitiveType:
            self._shapeCombo.addItem(pt.name.capitalize(), userData=pt)
        self._shapeCombo.currentIndexChanged.connect(self._onShapeChanged)
        form.addRow('Type :', self._shapeCombo)

        self._nameEdit = QLineEdit()
        self._nameEdit.setPlaceholderText('Auto')
        form.addRow('Name :', self._nameEdit)
        layout.addLayout(form)

        # ── Parameters ──
        self._paramGroup = QGroupBox('Parameters')
        self._paramLayout = QFormLayout(self._paramGroup)
        self._paramLayout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._paramLayout.setSpacing(6)
        layout.addWidget(self._paramGroup)

        self._xLen = self._addSpin('Width (X) :', 1.0)
        self._yLen = self._addSpin('Height (Y) :', 1.0)
        self._zLen = self._addSpin('Depth (Z) :', 1.0)
        self._radius = self._addSpin('Radius :', 0.5)
        self._height = self._addSpin('Height :', 1.0)
        self._ringRadius = self._addSpin('Ring radius :', 0.5)
        self._tubeRadius = self._addSpin('Tube radius :', 0.15)

        # ── Position ──
        posGroup = QGroupBox('Position')
        posLayout = QFormLayout(posGroup)
        posLayout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        posLayout.setSpacing(6)
        self._cx = self._makeSpin(0.0, -1e6, 1e6)
        self._cy = self._makeSpin(0.0, -1e6, 1e6)
        self._cz = self._makeSpin(0.0, -1e6, 1e6)
        posLayout.addRow('X :', self._cx)
        posLayout.addRow('Y :', self._cy)
        posLayout.addRow('Z :', self._cz)
        layout.addWidget(posGroup)

        layout.addWidget(_separator())

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
        for sb in (self._xLen, self._yLen, self._zLen, self._radius,
                   self._height, self._ringRadius, self._tubeRadius):
            sb.setVisible(False)
            label = self._paramLayout.labelForField(sb)
            if label:
                label.setVisible(False)

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


# ─────────────────────────────────────────────────────────────
# Boolean operation dialog
# ─────────────────────────────────────────────────────────────

class BooleanDialog(QDialog):
    """Pick two components and an operation."""

    def __init__(self, parent=None, component_names: list[tuple[int, str]] = None):
        super().__init__(parent)
        self.setWindowTitle('Boolean Operation')
        self.setMinimumWidth(380)
        self.setStyleSheet(_DIALOG_STYLE)
        component_names = component_names or []

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(_section_header('BOOLEAN'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        self._opCombo = QComboBox()
        self._opCombo.addItems(['Union  (A + B)', 'Subtract  (A \u2212 B)', 'Intersect  (A \u2229 B)'])
        form.addRow('Operation :', self._opCombo)

        self._comboA = QComboBox()
        self._comboB = QComboBox()
        for tag, name in component_names:
            self._comboA.addItem(name, userData=tag)
            self._comboB.addItem(name, userData=tag)
        if len(component_names) > 1:
            self._comboB.setCurrentIndex(1)
        form.addRow('Component A :', self._comboA)
        form.addRow('Component B :', self._comboB)

        layout.addLayout(form)
        layout.addWidget(_separator())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def operation_index(self) -> int:
        """0=union, 1=subtract, 2=intersect."""
        return self._opCombo.currentIndex()

    def tag_a(self) -> int:
        return self._comboA.currentData()

    def tag_b(self) -> int:
        return self._comboB.currentData()
