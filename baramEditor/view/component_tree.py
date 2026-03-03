#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Component browser panel — Fusion 360 / Plasticity-style sidebar with:
- Search/filter bar
- Eye icons for visibility
- Colour swatch per component
- Right-click context menu
- Summary footer
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QColor, QIcon, QBrush, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QInputDialog, QColorDialog, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QHeaderView, QFrame, QToolButton,
    QSizePolicy, QAbstractItemView, QStyledItemDelegate,
)

from baramEditor.cad_document import CADDocument, Component

logger = logging.getLogger(__name__)

# Column indices
COL_VIS = 0     # visibility checkbox
COL_COLOR = 1   # colour swatch
COL_NAME = 2    # component name
COL_TRIS = 3    # triangle count


def _colour_swatch_icon(r: float, g: float, b: float, size: int = 16) -> QIcon:
    """Create a small coloured circle icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(100, 100, 100), 1))
    painter.setBrush(QBrush(QColor.fromRgbF(r, g, b)))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pix)


def _h_line() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet('color: #484848;')
    line.setFixedHeight(1)
    return line


class ComponentTree(QWidget):
    """Left-side component browser panel."""

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
        self.setObjectName('cadPanel')
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

        self._document: Optional[CADDocument] = None
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ═══ Header ═══
        header = QHBoxLayout()
        header.setContentsMargins(10, 8, 10, 8)
        title = QLabel('Components')
        title.setObjectName('panelTitle')
        title.setStyleSheet(
            'color: white; font-size: 12px; font-weight: bold; padding: 0;'
        )
        header.addWidget(title)

        header.addStretch()

        self._showAllBtn = QToolButton()
        self._showAllBtn.setText('\U0001F441')   # eye icon
        self._showAllBtn.setToolTip('Show All')
        self._showAllBtn.setFixedSize(24, 24)
        self._showAllBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._showAllBtn.setStyleSheet(
            'QToolButton { background: transparent; border: none; font-size: 14px; }'
            'QToolButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }'
        )
        self._showAllBtn.clicked.connect(self.showAllRequested)
        header.addWidget(self._showAllBtn)

        layout.addLayout(header)

        # ═══ Search bar ═══
        search_container = QHBoxLayout()
        search_container.setContentsMargins(10, 0, 10, 8)
        self._searchEdit = QLineEdit()
        self._searchEdit.setPlaceholderText('\U0001F50D  Search components...')
        self._searchEdit.setClearButtonEnabled(True)
        self._searchEdit.textChanged.connect(self._filterTree)
        search_container.addWidget(self._searchEdit)
        layout.addLayout(search_container)

        layout.addWidget(_h_line())

        # ═══ Tree widget ═══
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['', '', 'Component', 'Tris'])
        self._tree.setColumnCount(4)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(COL_VIS, QHeaderView.ResizeMode.Fixed)
        self._tree.header().setSectionResizeMode(COL_COLOR, QHeaderView.ResizeMode.Fixed)
        self._tree.header().setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(COL_TRIS, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setColumnWidth(COL_VIS, 32)
        self._tree.setColumnWidth(COL_COLOR, 28)
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.setAlternatingRowColors(False)
        self._tree.setIndentation(0)
        self._tree.setAnimated(True)
        self._tree.itemChanged.connect(self._onItemChanged)
        self._tree.currentItemChanged.connect(self._onCurrentChanged)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._onContextMenu)
        layout.addWidget(self._tree, 1)

        layout.addWidget(_h_line())

        # ═══ Summary footer ═══
        footer = QHBoxLayout()
        footer.setContentsMargins(10, 6, 10, 6)
        self._summaryLabel = QLabel()
        self._summaryLabel.setStyleSheet('color: #888; font-size: 10px;')
        footer.addWidget(self._summaryLabel)
        footer.addStretch()
        layout.addLayout(footer)

    # ── Document binding ───────────────────────────────────────────

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

            # Visibility checkbox
            item.setCheckState(COL_VIS,
                               Qt.CheckState.Checked if (comp.visible and not comp.deleted)
                               else Qt.CheckState.Unchecked)

            # Colour swatch
            r, g, b, a = comp.colour
            item.setIcon(COL_COLOR, _colour_swatch_icon(r, g, b))

            # Name
            item.setText(COL_NAME, comp.name)

            # Triangle count
            tri_count = comp.mesh.triangle_count() if comp.mesh else 0
            total_tris += tri_count
            item.setText(COL_TRIS, f'{tri_count:,}')

            # Deleted style
            if comp.deleted:
                font = item.font(COL_NAME)
                font.setStrikeOut(True)
                item.setFont(COL_NAME, font)
                item.setForeground(COL_NAME, QBrush(QColor('#666')))
                item.setForeground(COL_TRIS, QBrush(QColor('#666')))

            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            self._tree.addTopLevelItem(item)

        visible = sum(1 for c in self._document.components if c.visible and not c.deleted)
        total = len(self._document.components)
        self._summaryLabel.setText(
            f'{visible}/{total} visible  \u00B7  {total_tris:,} \u25B3'
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
                    COL_VIS,
                    Qt.CheckState.Checked if (comp.visible and not comp.deleted)
                    else Qt.CheckState.Unchecked,
                )

                r, g, b, a = comp.colour
                item.setIcon(COL_COLOR, _colour_swatch_icon(r, g, b))

                tri_count = comp.mesh.triangle_count() if comp.mesh else 0
                item.setText(COL_TRIS, f'{tri_count:,}')

                font = item.font(COL_NAME)
                font.setStrikeOut(comp.deleted)
                item.setFont(COL_NAME, font)
                if comp.deleted:
                    item.setForeground(COL_NAME, QBrush(QColor('#666')))
                    item.setForeground(COL_TRIS, QBrush(QColor('#666')))
                else:
                    item.setForeground(COL_NAME, QBrush(QColor('#E0E0E0')))
                    item.setForeground(COL_TRIS, QBrush(QColor('#888')))

                self._updating = False
                break

        # Update summary
        if self._document:
            visible = sum(1 for c in self._document.components if c.visible and not c.deleted)
            total = len(self._document.components)
            total_tris = sum(c.mesh.triangle_count() for c in self._document.components if c.mesh)
            self._summaryLabel.setText(
                f'{visible}/{total} visible  \u00B7  {total_tris:,} \u25B3'
            )

    # ── Slots ──────────────────────────────────────────────────────

    def _onItemChanged(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != COL_VIS:
            return
        tag = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
        checked = item.checkState(COL_VIS) == Qt.CheckState.Checked
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
        menu.setStyleSheet(
            'QMenu { background: #3C3C3C; border: 1px solid #555; }'
            'QMenu::item { padding: 6px 24px 6px 16px; }'
            'QMenu::item:selected { background: #0696D7; }'
            'QMenu::separator { height: 1px; background: #555; margin: 4px 8px; }'
        )

        # ── Rename ──
        rename_action = menu.addAction('\u270F\uFE0F  Rename...')
        rename_action.triggered.connect(lambda: self._doRename(tag, comp.name))

        menu.addSeparator()

        # ── Visibility ──
        if comp.visible and not comp.deleted:
            hide = menu.addAction('\U0001F441  Hide')
            hide.triggered.connect(lambda: self.visibilityChanged.emit(tag, False))
        else:
            show = menu.addAction('\U0001F441  Show')
            show.triggered.connect(lambda: self.visibilityChanged.emit(tag, True))

        isolate = menu.addAction('\U0001F50D  Isolate')
        isolate.triggered.connect(lambda: self.isolateRequested.emit(tag))

        show_all = menu.addAction('\U0001F441  Show All')
        show_all.triggered.connect(self.showAllRequested.emit)

        menu.addSeparator()

        # ── Appearance ──
        colour_action = menu.addAction('\U0001F3A8  Change Colour...')
        colour_action.triggered.connect(lambda: self._doColourPick(tag, comp.colour))

        menu.addSeparator()

        # ── Transform operations ──
        if not comp.deleted:
            dup_action = menu.addAction('\U0001F4CB  Duplicate')
            dup_action.triggered.connect(lambda: self.duplicateRequested.emit(tag))

            move_action = menu.addAction('\u2194\uFE0F  Move...')
            move_action.triggered.connect(lambda: self.moveRequested.emit(tag))

            rot_action = menu.addAction('\U0001F504  Rotate...')
            rot_action.triggered.connect(lambda: self.rotateRequested.emit(tag))

            scale_action = menu.addAction('\U0001F4D0  Scale...')
            scale_action.triggered.connect(lambda: self.scaleRequested.emit(tag))

            mirror_action = menu.addAction('\U0001FA9E  Mirror...')
            mirror_action.triggered.connect(lambda: self.mirrorRequested.emit(tag))

        menu.addSeparator()

        # ── Delete / Restore ──
        if comp.deleted:
            restore = menu.addAction('\u267B\uFE0F  Restore')
            restore.triggered.connect(lambda: self.restoreRequested.emit(tag))
        else:
            delete = menu.addAction('\U0001F5D1\uFE0F  Delete')
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
