#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""FlowEFD-style boundary-condition quick-assign panel.

Provides a compact floating panel that appears near the mouse when a
boundary face is picked in the 3D viewport.  The panel shows:
  - Current boundary name and type
  - Color swatch (from BC type color)
  - One-click type-change buttons for common BC types
  - Edit button to open the full dialog
  - Info tooltip with face count / area

This mirrors the workflow of Siemens FloEFD, STAR-CCM+, and Ansys Fluent
where users click faces directly and assign boundary conditions visually.
"""

from __future__ import annotations

import logging
from functools import partial

from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QToolButton, QSizePolicy, QApplication,
)

from baramFlow.coredb.boundary_db import BoundaryType, BoundaryDB
from baramFlow.mesh.bc_colors import get_bc_color, BC_CATEGORY_COLORS

logger = logging.getLogger(__name__)


# ── Quick-assign button definitions ──────────────────────────
# These are the most common BC types users want fast access to.
_QUICK_TYPES = [
    ('Vel. Inlet',     BoundaryType.VELOCITY_INLET,  '#3380E6'),
    ('Press. Inlet',   BoundaryType.PRESSURE_INLET,   '#4D99FF'),
    ('Press. Outlet',  BoundaryType.PRESSURE_OUTLET,   '#E64D33'),
    ('Wall',           BoundaryType.WALL,              '#B3B3B3'),
    ('Symmetry',       BoundaryType.SYMMETRY,          '#4DCC66'),
    ('Interface',      BoundaryType.INTERFACE,          '#B366E6'),
]


class BCQuickPanel(QWidget):
    """Floating panel for quick BC type assignment — FlowEFD style.

    Signals:
        typeChangeRequested(int, BoundaryType) — emitted when user picks a new type.
        editRequested(int) — emitted when user clicks the Edit button.
    """

    typeChangeRequested = Signal(int, object)  # (bcid, BoundaryType)
    editRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(self._style())

        self._bcid = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # ── Header: color swatch + name + type ──
        header = QHBoxLayout()
        header.setSpacing(6)

        self._colorSwatch = QLabel()
        self._colorSwatch.setFixedSize(18, 18)
        header.addWidget(self._colorSwatch)

        self._nameLabel = QLabel()
        self._nameLabel.setObjectName('bc_name')
        self._nameLabel.setStyleSheet('font-weight: bold; font-size: 12px;')
        header.addWidget(self._nameLabel, 1)

        layout.addLayout(header)

        self._typeLabel = QLabel()
        self._typeLabel.setObjectName('bc_type')
        self._typeLabel.setStyleSheet('color: #AAA; font-size: 11px; padding-left: 24px;')
        layout.addWidget(self._typeLabel)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet('color: #555;')
        layout.addWidget(sep)

        # ── Quick-assign section label ──
        quick_label = QLabel('Quick Assign:')
        quick_label.setStyleSheet('color: #888; font-size: 10px; font-weight: bold;')
        layout.addWidget(quick_label)

        # ── Quick-assign buttons (2 rows of 3) ──
        row1 = QHBoxLayout()
        row1.setSpacing(3)
        row2 = QHBoxLayout()
        row2.setSpacing(3)

        self._quickButtons = []
        for i, (label, bctype, color) in enumerate(_QUICK_TYPES):
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                f'QPushButton {{ background: {color}; color: #FFF; border: none; '
                f'border-radius: 3px; font-size: 10px; font-weight: bold; padding: 2px 6px; }}'
                f'QPushButton:hover {{ background: {color}; opacity: 0.8; border: 1px solid #FFF; }}'
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._onQuickAssign, bctype))
            self._quickButtons.append(btn)
            if i < 3:
                row1.addWidget(btn)
            else:
                row2.addWidget(btn)

        layout.addLayout(row1)
        layout.addLayout(row2)

        # ── Separator ──
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet('color: #555;')
        layout.addWidget(sep2)

        # ── Edit button ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._editBtn = QPushButton('Edit Boundary...')
        self._editBtn.setFixedHeight(28)
        self._editBtn.setStyleSheet(
            'QPushButton { background: #0696D7; color: #FFF; border: none; '
            'border-radius: 4px; font-weight: bold; padding: 4px 12px; }'
            'QPushButton:hover { background: #0AA8ED; }'
        )
        self._editBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._editBtn.clicked.connect(self._onEdit)
        btn_row.addWidget(self._editBtn, 1)

        self._closeBtn = QPushButton('✕')
        self._closeBtn.setFixedSize(28, 28)
        self._closeBtn.setStyleSheet(
            'QPushButton { background: #555; color: #FFF; border: none; '
            'border-radius: 4px; font-weight: bold; }'
            'QPushButton:hover { background: #E04040; }'
        )
        self._closeBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._closeBtn.clicked.connect(self.hide)
        btn_row.addWidget(self._closeBtn)

        layout.addLayout(btn_row)

    def showForBoundary(self, bcid: int, bcname: str, bctype: BoundaryType,
                        global_pos: QPoint):
        """Display the panel near the given screen position."""
        self._bcid = bcid

        # Update labels
        self._nameLabel.setText(bcname)
        self._typeLabel.setText(BoundaryDB.dbBoundaryTypeToText(bctype))

        # Color swatch
        color = get_bc_color(bctype)
        r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
        self._colorSwatch.setStyleSheet(
            f'background: rgb({r},{g},{b}); border-radius: 9px; border: 1px solid #666;'
        )

        # Highlight current type in quick buttons
        for btn, (_, bt, _) in zip(self._quickButtons, _QUICK_TYPES):
            if bt == bctype:
                btn.setProperty('current', True)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            else:
                btn.setProperty('current', False)

        self.adjustSize()

        # Position near cursor but keep on screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = min(global_pos.x() + 15, screen.right() - self.width() - 10)
        y = min(global_pos.y() + 15, screen.bottom() - self.height() - 10)
        self.move(x, y)
        self.show()

    def _onQuickAssign(self, bctype: BoundaryType):
        if self._bcid is not None:
            self.typeChangeRequested.emit(self._bcid, bctype)
            # Update display immediately
            self._typeLabel.setText(BoundaryDB.dbBoundaryTypeToText(bctype))
            color = get_bc_color(bctype)
            r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
            self._colorSwatch.setStyleSheet(
                f'background: rgb({r},{g},{b}); border-radius: 9px; border: 1px solid #666;'
            )

    def _onEdit(self):
        if self._bcid is not None:
            self.editRequested.emit(self._bcid)
            self.hide()

    @staticmethod
    def _style() -> str:
        return """
            BCQuickPanel {
                background: #2D2D2D;
                border: 1px solid #555;
                border-radius: 6px;
            }
            QLabel {
                color: #E0E0E0;
            }
        """


class BCLegendWidget(QWidget):
    """Small legend overlay showing BC-type → color mapping.

    Designed to float in a corner of the 3D viewport when
    BC color mode is active.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(140)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(
            'BCLegendWidget { background: rgba(40,40,40,220); '
            'border: 1px solid #555; border-radius: 4px; }'
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        title = QLabel('Boundary Types')
        title.setStyleSheet('color: #CCC; font-size: 10px; font-weight: bold;')
        layout.addWidget(title)

        for name, color in BC_CATEGORY_COLORS:
            row = QHBoxLayout()
            row.setSpacing(6)

            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
            swatch.setStyleSheet(
                f'background: rgb({r},{g},{b}); border-radius: 2px; border: 1px solid #666;'
            )
            row.addWidget(swatch)

            lbl = QLabel(name)
            lbl.setStyleSheet('color: #BBB; font-size: 9px;')
            row.addWidget(lbl, 1)

            layout.addLayout(row)

        self.adjustSize()
