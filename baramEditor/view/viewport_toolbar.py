#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Floating viewport toolbar — overlays the 3D viewer with view controls
like Fusion 360's navigation cube neighbours (fit, perspective/ortho,
wireframe, axis-aligned views, grid toggle).
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QFrame,
    QSizePolicy, QButtonGroup,
)

logger = logging.getLogger(__name__)


def _tool_btn(
    text: str,
    tooltip: str,
    checkable: bool = False,
    icon_name: str = '',
    size: int = 28,
) -> QToolButton:
    """Create a compact tool button for the viewport bar."""
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        'QToolButton {'
        '  background: rgba(50, 50, 50, 200);'
        '  border: 1px solid rgba(80, 80, 80, 180);'
        '  border-radius: 4px;'
        '  color: #ddd;'
        '  font-size: 11px;'
        '  font-weight: bold;'
        '}'
        'QToolButton:hover {'
        '  background: rgba(70, 70, 70, 220);'
        '  border-color: #0696D7;'
        '}'
        'QToolButton:checked {'
        '  background: rgba(6, 150, 215, 200);'
        '  color: white;'
        '}'
    )
    return btn


class ViewportToolbar(QWidget):
    """Floating semi-transparent toolbar that overlays the 3D viewport.

    Signals emitted for each action — the viewer or main window
    connects to them.
    """

    fitAllClicked = Signal()
    perspectiveToggled = Signal(bool)    # True = perspective, False = ortho
    wireframeToggled = Signal(bool)      # True = wireframe, False = solid
    gridToggled = Signal(bool)
    axesToggled = Signal(bool)
    cubeAxesToggled = Signal(bool)

    # Predefined camera positions
    viewFront = Signal()
    viewBack = Signal()
    viewTop = Signal()
    viewBottom = Signal()
    viewLeft = Signal()
    viewRight = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet('background: transparent;')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # ── Top row: View controls ──
        top_row = QHBoxLayout()
        top_row.setSpacing(3)

        self._fitBtn = _tool_btn('⊞', 'Fit All (F)')
        self._fitBtn.clicked.connect(self.fitAllClicked)
        top_row.addWidget(self._fitBtn)

        self._perspBtn = _tool_btn('P', 'Perspective / Orthographic', checkable=True)
        self._perspBtn.setChecked(True)
        self._perspBtn.toggled.connect(lambda c: self.perspectiveToggled.emit(c))
        top_row.addWidget(self._perspBtn)

        self._wireBtn = _tool_btn('W', 'Wireframe / Solid', checkable=True)
        self._wireBtn.toggled.connect(lambda c: self.wireframeToggled.emit(c))
        top_row.addWidget(self._wireBtn)

        self._gridBtn = _tool_btn('G', 'Toggle Grid', checkable=True)
        self._gridBtn.setChecked(True)
        self._gridBtn.toggled.connect(lambda c: self.gridToggled.emit(c))
        top_row.addWidget(self._gridBtn)

        self._axesBtn = _tool_btn('A', 'Toggle Axes', checkable=True)
        self._axesBtn.setChecked(True)
        self._axesBtn.toggled.connect(lambda c: self.axesToggled.emit(c))
        top_row.addWidget(self._axesBtn)

        self._cubeBtn = _tool_btn('C', 'Cube Axes', checkable=True)
        self._cubeBtn.toggled.connect(lambda c: self.cubeAxesToggled.emit(c))
        top_row.addWidget(self._cubeBtn)

        top_row.addStretch()
        main_layout.addLayout(top_row)

        # ── Bottom row: Preset camera views ──
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(3)

        views = [
            ('F', 'Front', self.viewFront),
            ('B', 'Back', self.viewBack),
            ('T', 'Top', self.viewTop),
            ('Bo', 'Bottom', self.viewBottom),
            ('L', 'Left', self.viewLeft),
            ('R', 'Right', self.viewRight),
        ]
        for text, tooltip, signal in views:
            btn = _tool_btn(text, f'{tooltip} View', size=24)
            btn.clicked.connect(signal)
            bottom_row.addWidget(btn)

        bottom_row.addStretch()
        main_layout.addLayout(bottom_row)

        main_layout.addStretch()

        # Compact size
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.adjustSize()
