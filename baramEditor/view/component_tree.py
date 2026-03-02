#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Component tree panel — Fusion 360-style sidebar with eye icons to
toggle visibility, right-click context menu for rename/delete/colour,
and drag selection.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QInputDialog, QColorDialog, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QHeaderView,
)

from baramEditor.cad_document import CADDocument, Component

logger = logging.getLogger(__name__)

# Column indices
COL_NAME = 0
COL_TRIS = 1


class ComponentTree(QWidget):
    """Sidebar tree listing all CAD components with visibility toggles."""

    visibilityChanged = Signal(int, bool)    # tag, visible
    selectionChanged = Signal(int)           # tag
    renameRequested = Signal(int, str)       # tag, new_name
    deleteRequested = Signal(int)            # tag
    restoreRequested = Signal(int)           # tag
    colourRequested = Signal(int, tuple)     # tag, (r, g, b, a) floats 0-1
    isolateRequested = Signal(int)           # tag — show only this
    showAllRequested = Signal()
    duplicateRequested = Signal(int)         # tag
    moveRequested = Signal(int)              # tag
    rotateRequested = Signal(int)            # tag
    scaleRequested = Signal(int)             # tag
    mirrorRequested = Signal(int)            # tag

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._document: Optional[CADDocument] = None
        self._updating = False   # guard against signal loops

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)

        # Search bar
        search_layout = QHBoxLayout()
        self._searchEdit = QLineEdit()
        self._searchEdit.setPlaceholderText('Filter components…')
        self._searchEdit.setClearButtonEnabled(True)
        self._searchEdit.textChanged.connect(self._filterTree)
        search_layout.addWidget(self._searchEdit)

        self._showAllBtn = QPushButton('Show All')
        self._showAllBtn.setFixedWidth(70)
        self._showAllBtn.clicked.connect(self.showAllRequested)
        search_layout.addWidget(self._showAllBtn)
        layout.addLayout(search_layout)

        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['Component', 'Triangles'])
        self._tree.setColumnCount(2)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(COL_TRIS, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.itemChanged.connect(self._onItemChanged)
        self._tree.currentItemChanged.connect(self._onCurrentChanged)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._onContextMenu)
        layout.addWidget(self._tree)

        # Summary
        self._summaryLabel = QLabel()
        layout.addWidget(self._summaryLabel)

    # -- Document binding ----------------------------------------------------

    def set_document(self, doc: CADDocument):
        self._document = doc
        self.rebuild()

    def rebuild(self):
        """Rebuild the tree from the document."""
        self._updating = True
        self._tree.clear()

        if self._document is None:
            self._summaryLabel.clear()
            self._updating = False
            return

        total_tris = 0
        for comp in self._document.components:
            item = QTreeWidgetItem()
            item.setData(COL_NAME, Qt.ItemDataRole.UserRole, comp.tag)
            item.setText(COL_NAME, comp.name)
            item.setCheckState(COL_NAME,
                               Qt.CheckState.Checked if (comp.visible and not comp.deleted)
                               else Qt.CheckState.Unchecked)

            tri_count = comp.mesh.triangle_count() if comp.mesh else 0
            total_tris += tri_count
            item.setText(COL_TRIS, f'{tri_count:,}')

            # Colour swatch via background
            r, g, b, a = comp.colour
            item.setBackground(COL_NAME, QBrush(QColor.fromRgbF(r, g, b, 0.25)))

            if comp.deleted:
                font = item.font(COL_NAME)
                font.setStrikeOut(True)
                item.setFont(COL_NAME, font)

            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            self._tree.addTopLevelItem(item)

        visible = sum(1 for c in self._document.components if c.visible and not c.deleted)
        total = len(self._document.components)
        self._summaryLabel.setText(
            f'{visible}/{total} visible  ·  {total_tris:,} triangles'
        )
        self._updating = False

    def update_component(self, comp: Component):
        """Update a single row without rebuilding the entire tree."""
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item.data(COL_NAME, Qt.ItemDataRole.UserRole) == comp.tag:
                self._updating = True
                item.setText(COL_NAME, comp.name)
                item.setCheckState(
                    COL_NAME,
                    Qt.CheckState.Checked if (comp.visible and not comp.deleted)
                    else Qt.CheckState.Unchecked,
                )
                r, g, b, a = comp.colour
                item.setBackground(COL_NAME, QBrush(QColor.fromRgbF(r, g, b, 0.25)))
                font = item.font(COL_NAME)
                font.setStrikeOut(comp.deleted)
                item.setFont(COL_NAME, font)
                self._updating = False
                break

        # Update summary
        if self._document:
            visible = sum(1 for c in self._document.components if c.visible and not c.deleted)
            total = len(self._document.components)
            total_tris = sum(c.mesh.triangle_count() for c in self._document.components if c.mesh)
            self._summaryLabel.setText(
                f'{visible}/{total} visible  ·  {total_tris:,} triangles'
            )

    # -- Slots ---------------------------------------------------------------

    def _onItemChanged(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != COL_NAME:
            return
        tag = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        checked = item.checkState(COL_NAME) == Qt.CheckState.Checked
        self.visibilityChanged.emit(tag, checked)

    def _onCurrentChanged(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if current is None:
            return
        tag = current.data(COL_NAME, Qt.ItemDataRole.UserRole)
        self.selectionChanged.emit(tag)

    def _onContextMenu(self, pos):
        item = self._tree.itemAt(pos)
        if item is None:
            return
        tag = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        comp = self._document.component_by_tag(tag) if self._document else None
        if comp is None:
            return

        menu = QMenu(self)

        # Rename
        rename_action = menu.addAction('Rename…')
        rename_action.triggered.connect(lambda: self._doRename(tag, comp.name))

        menu.addSeparator()

        # Visibility
        if comp.visible and not comp.deleted:
            hide = menu.addAction('Hide')
            hide.triggered.connect(lambda: self.visibilityChanged.emit(tag, False))
        else:
            show = menu.addAction('Show')
            show.triggered.connect(lambda: self.visibilityChanged.emit(tag, True))

        isolate = menu.addAction('Isolate (show only this)')
        isolate.triggered.connect(lambda: self.isolateRequested.emit(tag))

        show_all = menu.addAction('Show All')
        show_all.triggered.connect(self.showAllRequested.emit)

        menu.addSeparator()

        # Colour
        colour_action = menu.addAction('Change Colour…')
        colour_action.triggered.connect(lambda: self._doColourPick(tag, comp.colour))

        menu.addSeparator()

        # Transform operations
        if not comp.deleted:
            dup_action = menu.addAction('Duplicate')
            dup_action.triggered.connect(lambda: self.duplicateRequested.emit(tag))

            move_action = menu.addAction('Move…')
            move_action.triggered.connect(lambda: self.moveRequested.emit(tag))

            rot_action = menu.addAction('Rotate…')
            rot_action.triggered.connect(lambda: self.rotateRequested.emit(tag))

            scale_action = menu.addAction('Scale…')
            scale_action.triggered.connect(lambda: self.scaleRequested.emit(tag))

            mirror_action = menu.addAction('Mirror…')
            mirror_action.triggered.connect(lambda: self.mirrorRequested.emit(tag))

        menu.addSeparator()

        # Delete / Restore
        if comp.deleted:
            restore = menu.addAction('Restore')
            restore.triggered.connect(lambda: self.restoreRequested.emit(tag))
        else:
            delete = menu.addAction('Delete')
            delete.triggered.connect(lambda: self.deleteRequested.emit(tag))

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _doRename(self, tag: int, current_name: str):
        name, ok = QInputDialog.getText(
            self, 'Rename Component', 'New name:', text=current_name,
        )
        if ok and name and name != current_name:
            self.renameRequested.emit(tag, name)

    def _doColourPick(self, tag: int, current: tuple):
        r, g, b, a = current
        initial = QColor.fromRgbF(r, g, b, a)
        colour = QColorDialog.getColor(
            initial, self, 'Component Colour',
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if colour.isValid():
            self.colourRequested.emit(
                tag, (colour.redF(), colour.greenF(), colour.blueF(), colour.alphaF())
            )

    def _filterTree(self, text: str):
        text_lower = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            item.setHidden(text_lower not in item.text(COL_NAME).lower())

    def selected_tag(self) -> Optional[int]:
        """Return the tag of the currently selected component, or ``None``."""
        item = self._tree.currentItem()
        if item is None:
            return None
        return item.data(COL_NAME, Qt.ItemDataRole.UserRole)
