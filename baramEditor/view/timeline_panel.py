#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Horizontal timeline panel — Fusion 360-style history timeline that sits
at the bottom of the viewport.  Each modification is a clickable node on
a left-to-right strip; the cursor shows the current position.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen, QBrush,
    QMouseEvent, QPaintEvent, QResizeEvent,
)
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QSizePolicy, QToolTip,
)

from baramEditor.cad_document import (
    CADDocument, Modification, ModificationHistory, ModificationType,
)

logger = logging.getLogger(__name__)

# Colour palette
_ACCENT = QColor('#0696D7')
_BG = QColor('#333333')
_NODE_DEFAULT = QColor('#555555')
_NODE_ACTIVE = QColor('#0696D7')
_NODE_FUTURE = QColor('#444444')
_TEXT = QColor('#E0E0E0')
_TEXT_DIM = QColor('#777777')
_BORDER = QColor('#484848')
_CURSOR_COLOR = QColor('#0696D7')

# Node appearance
_NODE_RADIUS = 8
_NODE_SPACING = 48
_RAIL_HEIGHT = 3
_TIMELINE_HEIGHT = 64

# Icons per modification type
_TYPE_ICONS = {
    ModificationType.RENAME:           '\u270F',    # pencil
    ModificationType.SET_VISIBLE:      '\U0001F441', # eye
    ModificationType.SET_COLOUR:       '\U0001F3A8', # palette
    ModificationType.DELETE:           '\U0001F5D1', # waste basket
    ModificationType.RESTORE:          '\u267B',     # recycle
    ModificationType.TRANSFORM:        '\u2194',     # left-right arrow
    ModificationType.GROUP:            '\U0001F4E6', # package
    ModificationType.ADD_COMPONENT:    '\u2795',     # plus
    ModificationType.REMOVE_COMPONENT: '\u274C',     # cross mark
    ModificationType.DUPLICATE:        '\U0001F4CB', # clipboard
    ModificationType.SCALE:            '\U0001F4D0', # triangular ruler
    ModificationType.ROTATE:           '\U0001F504', # arrows circle
    ModificationType.MIRROR:           '\U0001FA9E', # mirror
    ModificationType.BOOLEAN:          '\U0001F517', # link
}

_TYPE_LABELS = {
    ModificationType.RENAME:           'Rename',
    ModificationType.SET_VISIBLE:      'Visibility',
    ModificationType.SET_COLOUR:       'Colour',
    ModificationType.DELETE:           'Delete',
    ModificationType.RESTORE:          'Restore',
    ModificationType.TRANSFORM:        'Transform',
    ModificationType.GROUP:            'Group',
    ModificationType.ADD_COMPONENT:    'Add',
    ModificationType.REMOVE_COMPONENT: 'Remove',
    ModificationType.DUPLICATE:        'Duplicate',
    ModificationType.SCALE:            'Scale',
    ModificationType.ROTATE:           'Rotate',
    ModificationType.MIRROR:           'Mirror',
    ModificationType.BOOLEAN:          'Boolean',
}


class TimelineStrip(QWidget):
    """Custom-painted timeline strip showing modification nodes."""

    jumpRequested = Signal(int)  # target cursor position

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._modifications: list[Modification] = []
        self._cursor: int = 0
        self._hover_idx: int = -1
        self.setMouseTracking(True)
        self.setMinimumHeight(_TIMELINE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, modifications: list[Modification], cursor: int):
        self._modifications = modifications
        self._cursor = cursor
        self._recalc_size()
        self.update()

    def _recalc_size(self):
        n = max(1, len(self._modifications) + 1)  # +1 for initial state
        width = n * _NODE_SPACING + 40
        self.setMinimumWidth(width)

    def _node_center(self, idx: int) -> QPoint:
        """Centre point of node `idx` (0 = initial state)."""
        x = 20 + idx * _NODE_SPACING
        y = self.height() // 2
        return QPoint(x, y)

    def _hit_test(self, pos: QPoint) -> int:
        """Return the node index at `pos`, or -1."""
        n = len(self._modifications) + 1
        for i in range(n):
            centre = self._node_center(i)
            dx = pos.x() - centre.x()
            dy = pos.y() - centre.y()
            if dx * dx + dy * dy <= (_NODE_RADIUS + 4) ** 2:
                return i
        return -1

    # ── Paint ──────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        n = len(self._modifications) + 1  # +1 for initial node

        if n < 1:
            painter.end()
            return

        # ── Draw the rail line ──
        y_mid = self.height() // 2
        first_x = self._node_center(0).x()
        last_x = self._node_center(n - 1).x()

        # Past rail (solid)
        if self._cursor > 0:
            cursor_x = self._node_center(self._cursor).x()
            painter.setPen(QPen(_ACCENT, _RAIL_HEIGHT, Qt.PenStyle.SolidLine))
            painter.drawLine(first_x, y_mid, cursor_x, y_mid)

        # Future rail (dimmed)
        if self._cursor < n - 1:
            start_x = self._node_center(self._cursor).x()
            painter.setPen(QPen(_NODE_FUTURE, _RAIL_HEIGHT, Qt.PenStyle.SolidLine))
            painter.drawLine(start_x, y_mid, last_x, y_mid)

        # ── Draw nodes ──
        font = QFont()
        font.setPixelSize(9)
        painter.setFont(font)

        for i in range(n):
            centre = self._node_center(i)

            # Determine colour
            if i == self._cursor:
                colour = _NODE_ACTIVE
                ring = _ACCENT
            elif i < self._cursor:
                colour = _ACCENT.darker(140)
                ring = _ACCENT.darker(160)
            else:
                colour = _NODE_FUTURE
                ring = _BORDER

            # Node circle
            is_hovered = (i == self._hover_idx)
            r = _NODE_RADIUS + (2 if is_hovered else 0)
            painter.setPen(QPen(ring, 2))
            painter.setBrush(QBrush(colour))
            painter.drawEllipse(centre, r, r)

            # Cursor indicator (larger ring)
            if i == self._cursor:
                painter.setPen(QPen(_CURSOR_COLOR, 2, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(centre, r + 4, r + 4)

            # Label below
            if i == 0:
                label = 'Start'
            else:
                mod = self._modifications[i - 1]
                label = _TYPE_LABELS.get(mod.type, '?')

            text_color = _TEXT if i <= self._cursor else _TEXT_DIM
            painter.setPen(text_color)
            text_rect = QRect(centre.x() - 30, centre.y() + r + 4, 60, 16)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

        painter.end()

    # ── Mouse interaction ──────────────────────────────────────────

    def mouseMoveEvent(self, event: QMouseEvent):
        idx = self._hit_test(event.position().toPoint())
        if idx != self._hover_idx:
            self._hover_idx = idx
            self.setCursor(
                Qt.CursorShape.PointingHandCursor if idx >= 0
                else Qt.CursorShape.ArrowCursor
            )
            self.update()

        # Tooltip
        if idx > 0 and idx <= len(self._modifications):
            mod = self._modifications[idx - 1]
            QToolTip.showText(event.globalPosition().toPoint(), mod.description)
        elif idx == 0:
            QToolTip.showText(event.globalPosition().toPoint(), 'Initial state')
        else:
            QToolTip.hideText()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._hit_test(event.position().toPoint())
            if idx >= 0 and idx != self._cursor:
                self.jumpRequested.emit(idx)

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.update()


class TimelinePanel(QWidget):
    """Fusion 360-style horizontal timeline at the bottom of the window."""

    undoRequested = Signal()
    redoRequested = Signal()
    jumpRequested = Signal(int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName('cadPanel')
        self.setFixedHeight(_TIMELINE_HEIGHT + 30)

        self._document: Optional[CADDocument] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top border line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet('color: #484848;')
        layout.addWidget(line)

        # Content row
        content = QHBoxLayout()
        content.setContentsMargins(8, 4, 8, 4)
        content.setSpacing(8)

        # Undo / Redo buttons
        self._undoBtn = QPushButton('\u25C0')   # left arrow
        self._undoBtn.setToolTip('Undo')
        self._undoBtn.setFixedSize(28, 28)
        self._undoBtn.setEnabled(False)
        self._undoBtn.clicked.connect(self.undoRequested)
        content.addWidget(self._undoBtn)

        self._redoBtn = QPushButton('\u25B6')   # right arrow
        self._redoBtn.setToolTip('Redo')
        self._redoBtn.setFixedSize(28, 28)
        self._redoBtn.setEnabled(False)
        self._redoBtn.clicked.connect(self.redoRequested)
        content.addWidget(self._redoBtn)

        # Scrollable strip
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(False)

        self._strip = TimelineStrip()
        self._strip.jumpRequested.connect(self.jumpRequested)
        self._scroll.setWidget(self._strip)
        content.addWidget(self._scroll, 1)

        # Step counter
        self._stepLabel = QLabel('0 / 0')
        self._stepLabel.setStyleSheet('color: #888; font-size: 10px; padding: 0 4px;')
        content.addWidget(self._stepLabel)

        layout.addLayout(content)

    # ── Document binding ───────────────────────────────────────────

    def set_document(self, doc: CADDocument):
        self._document = doc
        self.rebuild()

    def rebuild(self):
        if self._document is None:
            self._strip.set_data([], 0)
            self._undoBtn.setEnabled(False)
            self._redoBtn.setEnabled(False)
            self._stepLabel.setText('0 / 0')
            return

        h = self._document.history
        self._strip.set_data(list(h.items), h.cursor)
        self._undoBtn.setEnabled(h.can_undo)
        self._redoBtn.setEnabled(h.can_redo)
        self._stepLabel.setText(f'{h.cursor} / {len(h.items)}')

        # Scroll to cursor
        self._scroll_to_cursor()

    def refresh_buttons(self):
        if self._document is None:
            return
        h = self._document.history
        self._undoBtn.setEnabled(h.can_undo)
        self._redoBtn.setEnabled(h.can_redo)
        self._stepLabel.setText(f'{h.cursor} / {len(h.items)}')
        self._strip.set_data(list(h.items), h.cursor)
        self._scroll_to_cursor()

    def append_modification(self, mod: Modification):
        if self._document is None:
            return
        self.rebuild()

    def _scroll_to_cursor(self):
        if self._document is None:
            return
        cursor = self._document.history.cursor
        x = 20 + cursor * _NODE_SPACING - self._scroll.width() // 2
        self._scroll.horizontalScrollBar().setValue(max(0, x))
