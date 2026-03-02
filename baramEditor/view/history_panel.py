#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""History panel — shows the linear modification history with a cursor
indicator, supports click-to-jump (mass undo/redo), and optional icons.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QLabel,
)

from baramEditor.cad_document import (
    CADDocument, ModificationHistory, Modification, ModificationType,
)

logger = logging.getLogger(__name__)

# Icons per modification type (emoji fallback; swap for QIcons later)
_TYPE_ICONS = {
    ModificationType.RENAME:           '✏️',
    ModificationType.SET_VISIBLE:      '👁️',
    ModificationType.SET_COLOUR:       '🎨',
    ModificationType.DELETE:           '🗑️',
    ModificationType.RESTORE:          '♻️',
    ModificationType.TRANSFORM:        '↔️',
    ModificationType.GROUP:            '📦',
    ModificationType.ADD_COMPONENT:    '➕',
    ModificationType.REMOVE_COMPONENT: '❌',
    ModificationType.DUPLICATE:        '📋',
    ModificationType.SCALE:            '📐',
    ModificationType.ROTATE:           '🔄',
    ModificationType.MIRROR:           '🪞',
    ModificationType.BOOLEAN:          '🔗',
}


class HistoryPanel(QWidget):
    """Displays the modification history and allows click-to-jump."""

    undoRequested = Signal()
    redoRequested = Signal()
    jumpRequested = Signal(int)   # target cursor position (0 = initial state)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._document: Optional[CADDocument] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)

        # Title
        title = QLabel('<b>History</b>')
        layout.addWidget(title)

        # Undo / Redo buttons
        btn_row = QHBoxLayout()
        self._undoBtn = QPushButton('Undo')
        self._undoBtn.setEnabled(False)
        self._undoBtn.clicked.connect(self.undoRequested)
        btn_row.addWidget(self._undoBtn)

        self._redoBtn = QPushButton('Redo')
        self._redoBtn.setEnabled(False)
        self._redoBtn.clicked.connect(self.redoRequested)
        btn_row.addWidget(self._redoBtn)
        layout.addLayout(btn_row)

        # List widget
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._onRowChanged)
        layout.addWidget(self._list)

        # Cursor label
        self._cursorLabel = QLabel()
        layout.addWidget(self._cursorLabel)

    # -- Document binding ----------------------------------------------------

    def set_document(self, doc: CADDocument):
        self._document = doc
        self.rebuild()

    def rebuild(self):
        """Rebuild the list from the document history."""
        self._list.blockSignals(True)
        self._list.clear()

        if self._document is None:
            self._undoBtn.setEnabled(False)
            self._redoBtn.setEnabled(False)
            self._cursorLabel.clear()
            self._list.blockSignals(False)
            return

        history = self._document.history

        # Row 0 = initial state (before any modifications)
        initial = QListWidgetItem('● Initial state')
        initial.setData(Qt.ItemDataRole.UserRole, 0)
        self._list.addItem(initial)

        for idx, mod in enumerate(history.items, start=1):
            icon = _TYPE_ICONS.get(mod.type, '•')
            text = f'{icon}  {mod.description}'
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setToolTip(f'{mod.timestamp}')
            self._list.addItem(item)

        self._highlightCursor(history.cursor)
        self._undoBtn.setEnabled(history.can_undo)
        self._redoBtn.setEnabled(history.can_redo)
        self._cursorLabel.setText(
            f'Step {history.cursor} / {len(history.items)}'
        )

        self._list.blockSignals(False)

    def refresh_buttons(self):
        """Update undo/redo button states without full rebuild."""
        if self._document is None:
            return
        history = self._document.history
        self._undoBtn.setEnabled(history.can_undo)
        self._redoBtn.setEnabled(history.can_redo)
        self._cursorLabel.setText(
            f'Step {history.cursor} / {len(history.items)}'
        )
        self._highlightCursor(history.cursor)

    def append_modification(self, mod: Modification):
        """Append a new modification (fast path — no full rebuild)."""
        if self._document is None:
            return
        history = self._document.history

        # Remove any items after current cursor (they were truncated by push)
        while self._list.count() > history.cursor:
            self._list.takeItem(self._list.count() - 1)

        # Add the new item
        idx = history.cursor
        icon = _TYPE_ICONS.get(mod.type, '•')
        text = f'{icon}  {mod.description}'
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, idx)
        item.setToolTip(f'{mod.timestamp}')
        self._list.addItem(item)

        self._highlightCursor(idx)
        self._undoBtn.setEnabled(history.can_undo)
        self._redoBtn.setEnabled(history.can_redo)
        self._cursorLabel.setText(
            f'Step {history.cursor} / {len(history.items)}'
        )

    # -- Internal ------------------------------------------------------------

    def _highlightCursor(self, cursor: int):
        """Bold the row at `cursor`, dim rows after cursor."""
        bold = QFont()
        bold.setBold(True)
        normal = QFont()
        dim_brush = QBrush(QColor(128, 128, 128))
        default_brush = QBrush()

        for i in range(self._list.count()):
            item = self._list.item(i)
            row_idx = item.data(Qt.ItemDataRole.UserRole)
            if row_idx == cursor:
                item.setFont(bold)
                item.setForeground(default_brush)
            elif row_idx > cursor:
                item.setFont(normal)
                item.setForeground(dim_brush)
            else:
                item.setFont(normal)
                item.setForeground(default_brush)

        # Scroll to cursor row
        if 0 <= cursor < self._list.count():
            self._list.setCurrentRow(cursor)

    def _onRowChanged(self, row: int):
        if row < 0 or self._document is None:
            return
        item = self._list.item(row)
        if item is None:
            return
        target = item.data(Qt.ItemDataRole.UserRole)
        current = self._document.history.cursor
        if target != current:
            self.jumpRequested.emit(target)
