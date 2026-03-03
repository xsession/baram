#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Main window for BaramEditor — Fusion 360 / Plasticity-style layout.

Layout:
  ┌──────────────────── Toolbar Ribbon ────────────────────────┐
  │  File  │  Create  │  Modify  │  Boolean │  View  │  Help  │
  ├────────┬──────────────────────────────────────┬────────────┤
  │  Left  │                                      │   Right    │
  │ Panel  │          3D Viewport                  │  Panel     │
  │(Comps) │  (floating viewport toolbar overlay)  │(Properties)│
  ├────────┴──────────────────────────────────────┴────────────┤
  │              Timeline (horizontal history strip)            │
  ├────────────────────── Status Bar ──────────────────────────┤
  └────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import Optional

import qasync
from PySide6.QtCore import Qt, QEvent, QObject, Signal as QtSignal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox,
    QDockWidget, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QToolBar, QLabel, QToolButton, QFrame,
)

from widgets.async_message_box import AsyncMessageBox
from widgets.progress_dialog import ProgressDialog

from baramEditor.app import app
from baramEditor.cad_document import CADDocument, Component, ComponentMesh, Modification
from baramEditor.view.cad_style import CAD_STYLESHEET
from baramEditor.view.cad_viewer import CADViewer
from baramEditor.view.component_tree import ComponentTree
from baramEditor.view.properties_panel import PropertiesPanel
from baramEditor.view.timeline_panel import TimelinePanel

logger = logging.getLogger(__name__)


class _ProgressBridge(QObject):
    """Thread-safe bridge: emit signals from worker thread,
    connect to ProgressDialog slots on the GUI thread."""
    percentChanged = QtSignal(int)
    messageChanged = QtSignal(str)

    def callback(self, pct: int, msg: str):
        self.percentChanged.emit(pct)
        self.messageChanged.emit(msg)


def _toolbar_separator_label(text: str) -> QLabel:
    """Small dim group label for toolbar sections."""
    lbl = QLabel(text)
    lbl.setStyleSheet('color: #666; font-size: 9px; padding: 0 2px;')
    return lbl


class MainWindow(QMainWindow):
    """Fusion 360-style main window with ribbon toolbar, side panels,
    central viewport, and bottom timeline."""

    def __init__(self):
        super().__init__()

        self._document: Optional[CADDocument] = None
        self._projectPath: Optional[Path] = None

        self.setWindowTitle(app.properties.fullName)
        self.setWindowIcon(app.properties.icon())
        self.resize(1600, 950)

        # ═══ Apply stylesheet ═══
        self.setStyleSheet(CAD_STYLESHEET)

        # ═══ Central area: splitter with 3 panels ═══
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Horizontal splitter: [left panel | viewport | right panel]
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(2)

        # Left panel: Component browser
        self._componentTree = ComponentTree()
        self._splitter.addWidget(self._componentTree)

        # Centre: 3D Viewer
        self._viewer = CADViewer()
        self._splitter.addWidget(self._viewer)

        # Right panel: Properties inspector
        self._propertiesPanel = PropertiesPanel()
        self._splitter.addWidget(self._propertiesPanel)

        # Splitter proportions: left=280, center=stretch, right=280
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setSizes([280, 900, 280])

        central_layout.addWidget(self._splitter, 1)

        # Bottom: Timeline
        self._timeline = TimelinePanel()
        central_layout.addWidget(self._timeline)

        self.setCentralWidget(central)

        # ═══ Status bar ═══
        self._statusLabel = QLabel('  Ready — Import a CAD or STL file to begin')
        self.statusBar().addWidget(self._statusLabel, 1)

        self._triLabel = QLabel()
        self.statusBar().addPermanentWidget(self._triLabel)

        self._coordLabel = QLabel()
        self.statusBar().addPermanentWidget(self._coordLabel)

        # ═══ Menus & toolbar ═══
        self._buildMenus()
        self._buildToolbar()

        # ═══ Wire signals ═══
        self._connectSignals()

    # ====================================================================
    # Toolbar ribbon (Fusion 360 style with grouped sections)
    # ====================================================================

    def _buildToolbar(self):
        tb = self.addToolBar('Main')
        tb.setMovable(False)
        tb.setIconSize(self.fontMetrics().size(0, 'WW') * 1.2)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        # ── File group ──
        tb.addWidget(_toolbar_separator_label('FILE'))
        tb.addAction(self._actImport)
        tb.addAction(self._actExportSTL)
        tb.addAction(self._actSaveProject)
        tb.addSeparator()

        # ── Edit group ──
        tb.addWidget(_toolbar_separator_label('EDIT'))
        tb.addAction(self._actUndo)
        tb.addAction(self._actRedo)
        tb.addSeparator()

        # ── Create group ──
        tb.addWidget(_toolbar_separator_label('CREATE'))
        tb.addAction(self._actAddShape)
        tb.addAction(self._actDuplicate)
        tb.addSeparator()

        # ── Modify group ──
        tb.addWidget(_toolbar_separator_label('MODIFY'))
        tb.addAction(self._actMove)
        tb.addAction(self._actRotate)
        tb.addAction(self._actScale)
        tb.addAction(self._actMirror)
        tb.addSeparator()

        # ── Boolean group ──
        tb.addWidget(_toolbar_separator_label('BOOLEAN'))
        tb.addAction(self._actBoolean)
        tb.addSeparator()

        # ── View group ──
        tb.addWidget(_toolbar_separator_label('VIEW'))
        tb.addAction(self._actFitAll)

    # ====================================================================
    # Menus
    # ====================================================================

    def _buildMenus(self):
        menubar = self.menuBar()

        # ── File ──
        file_menu = menubar.addMenu('&File')
        self._actImport = file_menu.addAction('&Import...')
        self._actImport.setShortcut(QKeySequence('Ctrl+I'))
        self._actImport.setToolTip('Import CAD / STL file')

        self._actExportSTL = file_menu.addAction('&Export STL...')
        self._actExportSTL.setShortcut(QKeySequence('Ctrl+E'))
        self._actExportSTL.setEnabled(False)

        file_menu.addSeparator()

        self._actSaveProject = file_menu.addAction('&Save Project')
        self._actSaveProject.setShortcut(QKeySequence.StandardKey.Save)
        self._actSaveProject.setEnabled(False)

        self._actOpenProject = file_menu.addAction('&Open Project...')
        self._actOpenProject.setShortcut(QKeySequence.StandardKey.Open)

        file_menu.addSeparator()
        self._actExit = file_menu.addAction('E&xit')
        self._actExit.setShortcut(QKeySequence('Ctrl+Q'))

        # ── Edit ──
        edit_menu = menubar.addMenu('&Edit')
        self._actUndo = edit_menu.addAction('&Undo')
        self._actUndo.setShortcut(QKeySequence.StandardKey.Undo)
        self._actUndo.setEnabled(False)

        self._actRedo = edit_menu.addAction('&Redo')
        self._actRedo.setShortcut(QKeySequence.StandardKey.Redo)
        self._actRedo.setEnabled(False)
        edit_menu.addSeparator()

        self._actAddShape = edit_menu.addAction('Add &Shape...')
        self._actAddShape.setShortcut(QKeySequence('Ctrl+Shift+A'))

        self._actDuplicate = edit_menu.addAction('&Duplicate')
        self._actDuplicate.setShortcut(QKeySequence('Ctrl+D'))
        edit_menu.addSeparator()

        self._actMove = edit_menu.addAction('&Move...')
        self._actMove.setShortcut(QKeySequence('G'))

        self._actRotate = edit_menu.addAction('&Rotate...')
        self._actRotate.setShortcut(QKeySequence('R'))

        self._actScale = edit_menu.addAction('Sca&le...')
        self._actScale.setShortcut(QKeySequence('S'))

        self._actMirror = edit_menu.addAction('M&irror...')
        edit_menu.addSeparator()

        self._actBoolean = edit_menu.addAction('&Boolean...')
        self._actBoolean.setShortcut(QKeySequence('Ctrl+B'))

        for act in (self._actDuplicate, self._actMove,
                     self._actRotate, self._actScale, self._actMirror,
                     self._actBoolean):
            act.setEnabled(False)

        # ── View ──
        view_menu = menubar.addMenu('&View')
        self._actFitAll = view_menu.addAction('&Fit All')
        self._actFitAll.setShortcut(QKeySequence('F'))

        # ── Settings ──
        settings_menu = menubar.addMenu('&Settings')

        self._themeGroup = QActionGroup(self)
        self._themeGroup.setExclusive(True)

        self._actLightMode = QAction('&Light Mode', self)
        self._actLightMode.setCheckable(True)
        self._actLightMode.setActionGroup(self._themeGroup)
        settings_menu.addAction(self._actLightMode)

        self._actDarkMode = QAction('&Dark Mode', self)
        self._actDarkMode.setCheckable(True)
        self._actDarkMode.setActionGroup(self._themeGroup)
        settings_menu.addAction(self._actDarkMode)

        if app.settings.isDarkModeEnabled():
            self._actDarkMode.setChecked(True)
        else:
            self._actLightMode.setChecked(True)

        # ── Help ──
        help_menu = menubar.addMenu('&Help')
        self._actAbout = help_menu.addAction('&About')

    # ====================================================================
    # Signals wiring
    # ====================================================================

    def _connectSignals(self):
        # File
        self._actImport.triggered.connect(self._onImport)
        self._actExportSTL.triggered.connect(self._onExportSTL)
        self._actSaveProject.triggered.connect(self._onSaveProject)
        self._actOpenProject.triggered.connect(self._onOpenProject)
        self._actExit.triggered.connect(self.close)

        # Edit
        self._actUndo.triggered.connect(self._onUndo)
        self._actRedo.triggered.connect(self._onRedo)
        self._actAddShape.triggered.connect(self._onAddShape)
        self._actDuplicate.triggered.connect(self._onDuplicate)
        self._actMove.triggered.connect(self._onMove)
        self._actRotate.triggered.connect(self._onRotate)
        self._actScale.triggered.connect(self._onScale)
        self._actMirror.triggered.connect(self._onMirror)
        self._actBoolean.triggered.connect(self._onBoolean)

        # View
        self._actFitAll.triggered.connect(lambda: self._viewer.fit_camera())

        # Settings
        self._actLightMode.triggered.connect(lambda checked: self._setTheme(False) if checked else None)
        self._actDarkMode.triggered.connect(lambda checked: self._setTheme(True) if checked else None)

        # About
        self._actAbout.triggered.connect(self._onAbout)

        # Component tree
        self._componentTree.visibilityChanged.connect(self._onVisibilityChanged)
        self._componentTree.renameRequested.connect(self._onRename)
        self._componentTree.deleteRequested.connect(self._onDelete)
        self._componentTree.restoreRequested.connect(self._onRestore)
        self._componentTree.colourRequested.connect(self._onColourChanged)
        self._componentTree.isolateRequested.connect(self._onIsolate)
        self._componentTree.showAllRequested.connect(self._onShowAll)
        self._componentTree.selectionChanged.connect(self._onSelectionChanged)
        self._componentTree.duplicateRequested.connect(self._onDuplicateTag)
        self._componentTree.moveRequested.connect(self._onMoveTag)
        self._componentTree.rotateRequested.connect(self._onRotateTag)
        self._componentTree.scaleRequested.connect(self._onScaleTag)
        self._componentTree.mirrorRequested.connect(self._onMirrorTag)

        # Properties panel
        self._propertiesPanel.renameRequested.connect(self._onRename)
        self._propertiesPanel.colourRequested.connect(self._onColourChanged)
        self._propertiesPanel.opacityChanged.connect(self._onOpacityChanged)

        # Timeline
        self._timeline.undoRequested.connect(self._onUndo)
        self._timeline.redoRequested.connect(self._onRedo)
        self._timeline.jumpRequested.connect(self._onHistoryJump)

        # Viewer
        self._viewer.componentPicked.connect(self._onViewerPick)

    # ====================================================================
    # Theme
    # ====================================================================

    def _setTheme(self, dark: bool):
        app.settings.setDarkModeEnabled(dark)
        # Keep our custom CAD stylesheet, just update VTK bg
        self._viewer.apply_theme(dark)

    # ====================================================================
    # File actions
    # ====================================================================

    @qasync.asyncSlot()
    async def _onImport(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Import CAD / STL File', '',
            'All Supported (*.step *.stp *.iges *.igs *.brep *.stl);;'
            'STEP Files (*.step *.stp);;'
            'IGES Files (*.iges *.igs);;'
            'BREP Files (*.brep);;'
            'STL Files (*.stl);;'
            'All Files (*)',
        )
        if not path:
            return

        file_name = Path(path).name

        progressDlg = ProgressDialog(self, f'Importing {file_name}', cancelable=False)
        progressDlg.setRange(0, 100)
        progressDlg.setPercent(0)
        progressDlg.setLabelText(f'Loading {file_name}...')
        progressDlg.open()
        QApplication.processEvents()

        bridge = _ProgressBridge()
        bridge.percentChanged.connect(progressDlg.setPercent, Qt.ConnectionType.QueuedConnection)
        bridge.messageChanged.connect(progressDlg.setLabelText, Qt.ConnectionType.QueuedConnection)

        try:
            doc = CADDocument()
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: doc.load(path, progress=bridge.callback)
            )
        except Exception as e:
            logger.exception('Failed to load CAD file')
            progressDlg.close()
            await AsyncMessageBox().information(
                self, 'Import Error', f'Could not load file:\n{e}',
            )
            self._statusLabel.setText('  Import failed')
            return

        progressDlg.close()

        self._document = doc
        self._setDocument(doc)
        n = len(doc.components)
        total_tris = sum(c.mesh.triangle_count() for c in doc.components if c.mesh)
        self._statusLabel.setText(
            f'  {file_name}  \u2014  {n} component{"s" if n != 1 else ""},  {total_tris:,} triangles'
        )
        self._actSaveProject.setEnabled(True)

    def _onSaveProject(self):
        if self._document is None:
            return
        if self._projectPath is None:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Save Project', '',
                'BaramEditor Project (*.bep);;All Files (*)',
            )
            if not path:
                return
            self._projectPath = Path(path)

        try:
            self._document.save_project(self._projectPath)
            self._statusLabel.setText(f'  Saved to {self._projectPath.name}')
        except Exception as e:
            logger.exception('Failed to save project')
            QMessageBox.warning(self, 'Save Error', f'Could not save:\n{e}')

    @qasync.asyncSlot()
    async def _onOpenProject(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open Project', '',
            'BaramEditor Project (*.bep);;All Files (*)',
        )
        if not path:
            return

        try:
            doc = CADDocument()
            doc.open_project(Path(path))
        except Exception as e:
            logger.exception('Failed to open project')
            await AsyncMessageBox().information(
                self, 'Open Error', f'Could not open project:\n{e}',
            )
            return

        self._document = doc
        self._projectPath = Path(path)
        self._setDocument(doc)
        self._statusLabel.setText(f'  {Path(path).name}  \u2014  {len(doc.components)} components')
        self._actSaveProject.setEnabled(True)

    # ====================================================================
    # Document binding
    # ====================================================================

    def _setDocument(self, doc: CADDocument):
        self._viewer.set_document(doc)
        self._componentTree.set_document(doc)
        self._timeline.set_document(doc)
        self._propertiesPanel.clear()
        self._viewer.fit_camera()
        self._updateUndoRedo()
        self._updateTriangleCount()
        # Enable editing actions
        has_doc = doc is not None
        for act in (self._actAddShape, self._actDuplicate, self._actMove,
                     self._actRotate, self._actScale, self._actMirror,
                     self._actBoolean, self._actExportSTL):
            act.setEnabled(has_doc)

    def _updateUndoRedo(self):
        if self._document is None:
            self._actUndo.setEnabled(False)
            self._actRedo.setEnabled(False)
            return
        self._actUndo.setEnabled(self._document.history.can_undo)
        self._actRedo.setEnabled(self._document.history.can_redo)
        self._timeline.refresh_buttons()

    def _updateTriangleCount(self):
        if self._document is None:
            self._triLabel.clear()
            return
        total = sum(c.mesh.triangle_count() for c in self._document.components if c.mesh)
        self._triLabel.setText(f'  {total:,} \u25B3  ')

    # ====================================================================
    # Edit operations
    # ====================================================================

    def _afterEdit(self, comp: Component, mod: Modification):
        """Common update after any edit operation."""
        self._viewer.update_component(comp)
        self._componentTree.update_component(comp)
        self._timeline.append_modification(mod)
        self._updateUndoRedo()
        self._updateTriangleCount()
        # Update properties panel if this is the selected component
        if self._propertiesPanel._component and self._propertiesPanel._component.tag == comp.tag:
            self._propertiesPanel.set_component(comp)

    def _onVisibilityChanged(self, tag: int, visible: bool):
        if self._document is None:
            return
        mod = self._document.set_visible(tag, visible)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onRename(self, tag: int, new_name: str):
        if self._document is None:
            return
        mod = self._document.rename_component(tag, new_name)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onDelete(self, tag: int):
        if self._document is None:
            return
        mod = self._document.delete_component(tag)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onRestore(self, tag: int):
        if self._document is None:
            return
        mod = self._document.restore_component(tag)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onColourChanged(self, tag: int, colour: tuple):
        if self._document is None:
            return
        mod = self._document.set_colour(tag, colour)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onOpacityChanged(self, tag: int, alpha: float):
        """Handle opacity change from properties panel."""
        if self._document is None:
            return
        comp = self._document.component_by_tag(tag)
        if comp is None:
            return
        new_colour = (comp.colour[0], comp.colour[1], comp.colour[2], alpha)
        mod = self._document.set_colour(tag, new_colour)
        if mod is None:
            return
        comp = self._document.component_by_tag(tag)
        self._afterEdit(comp, mod)

    def _onIsolate(self, tag: int):
        if self._document is None:
            return
        for comp in self._document.components:
            if comp.deleted:
                continue
            should_be_visible = (comp.tag == tag)
            if comp.visible != should_be_visible:
                self._document.set_visible(comp.tag, should_be_visible)
        self._fullRefresh()

    def _onShowAll(self):
        if self._document is None:
            return
        for comp in self._document.components:
            if not comp.visible and not comp.deleted:
                self._document.set_visible(comp.tag, True)
        self._fullRefresh()

    # ====================================================================
    # Create / Modify operations
    # ====================================================================

    def _selectedTag(self) -> Optional[int]:
        return self._componentTree.selected_tag()

    def _requireSelection(self) -> Optional[int]:
        tag = self._selectedTag()
        if tag is None:
            QMessageBox.information(self, 'No Selection',
                                    'Please select a component first.')
        return tag

    def _onAddShape(self):
        if self._document is None:
            self._document = CADDocument()
            self._setDocument(self._document)

        from baramEditor.view.editor_dialogs import AddPrimitiveDialog
        from baramEditor.primitives import PRIMITIVE_FACTORIES

        dlg = AddPrimitiveDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        ptype = dlg.primitive_type()
        name = dlg.name()
        params = dlg.params()

        factory = PRIMITIVE_FACTORIES.get(ptype)
        if factory is None:
            return

        verts, faces = factory(**params)
        mesh = ComponentMesh(vertices=verts, faces=faces)
        comp, mod = self._document.add_component(name=name, dim=3, mesh=mesh)
        if comp is not None and mod is not None:
            self._afterAddComponent(comp, mod)

    def _onDuplicate(self):
        tag = self._requireSelection()
        if tag is None or self._document is None:
            return
        new_comp, mod = self._document.duplicate_component(tag)
        if new_comp is not None and mod is not None:
            self._afterAddComponent(new_comp, mod)

    def _onMove(self):
        tag = self._requireSelection()
        if tag is None or self._document is None:
            return
        from baramEditor.view.editor_dialogs import TranslateDialog
        dlg = TranslateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        dx, dy, dz = dlg.values()
        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            return
        mod = self._document.move_component_mesh(tag, dx, dy, dz)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onRotate(self):
        tag = self._requireSelection()
        if tag is None or self._document is None:
            return
        from baramEditor.view.editor_dialogs import RotateDialog
        dlg = RotateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        angle, axis = dlg.values()
        if angle == 0.0:
            return
        mod = self._document.rotate_component(tag, angle, axis)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onScale(self):
        tag = self._requireSelection()
        if tag is None or self._document is None:
            return
        from baramEditor.view.editor_dialogs import ScaleDialog
        dlg = ScaleDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        sx, sy, sz = dlg.values()
        if sx == 1.0 and sy == 1.0 and sz == 1.0:
            return
        mod = self._document.scale_component(tag, sx, sy, sz)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onMirror(self):
        tag = self._requireSelection()
        if tag is None or self._document is None:
            return
        from baramEditor.view.editor_dialogs import MirrorDialog
        dlg = MirrorDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        plane = dlg.plane()
        new_comp, mod = self._document.mirror_component(tag, plane)
        if new_comp is not None and mod is not None:
            self._afterAddComponent(new_comp, mod)

    def _onBoolean(self):
        if self._document is None:
            return
        from baramEditor.view.editor_dialogs import BooleanDialog
        comps = [c for c in self._document.components if not c.deleted]
        if len(comps) < 2:
            QMessageBox.information(
                self, 'Boolean', 'At least two components are required.')
            return
        comp_names = [(c.tag, c.name) for c in comps]
        dlg = BooleanDialog(self, comp_names)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        tag_a = dlg.tag_a()
        tag_b = dlg.tag_b()
        op_idx = dlg.operation_index()
        if tag_a == tag_b:
            QMessageBox.warning(
                self, 'Boolean', 'Please select two different components.')
            return

        try:
            new_comp, mod = self._document.boolean_operation(tag_a, tag_b, op_idx)
        except Exception as e:
            logger.exception('Boolean operation failed')
            QMessageBox.warning(
                self, 'Boolean Error',
                f'Boolean operation failed:\n{e}')
            return

        if new_comp is not None and mod is not None:
            self._afterAddComponent(new_comp, mod)

    def _onExportSTL(self):
        if self._document is None:
            return
        tag = self._selectedTag()
        if tag is None:
            comps = [c for c in self._document.components
                     if not c.deleted and c.visible and c.mesh]
        else:
            comp = self._document.component_by_tag(tag)
            comps = [comp] if comp and comp.mesh else []
        if not comps:
            QMessageBox.information(
                self, 'Export STL', 'No visible components to export.')
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Export STL', '', 'STL Files (*.stl);;All Files (*)')
        if not path:
            return

        try:
            from baramEditor.primitives import export_stl, numpy_to_polydata
            import vtk
            appender = vtk.vtkAppendPolyData()
            for c in comps:
                pd = numpy_to_polydata(c.mesh.vertices, c.mesh.faces)
                appender.AddInputData(pd)
            appender.Update()
            writer = vtk.vtkSTLWriter()
            writer.SetFileName(path)
            writer.SetInputData(appender.GetOutput())
            writer.Write()
            self._statusLabel.setText(f'  Exported to {Path(path).name}')
        except Exception as e:
            logger.exception('STL export failed')
            QMessageBox.warning(self, 'Export Error', f'Export failed:\n{e}')

    def _afterAddComponent(self, comp: Component, mod: Modification):
        """Refresh after a new component is added."""
        self._viewer.add_new_component(comp)
        self._componentTree.rebuild()
        self._timeline.append_modification(mod)
        self._updateUndoRedo()
        self._updateTriangleCount()

    # ── Context-menu handlers (tag provided by tree signals) ────────

    def _onDuplicateTag(self, tag: int):
        if self._document is None:
            return
        new_comp, mod = self._document.duplicate_component(tag)
        if new_comp is not None and mod is not None:
            self._afterAddComponent(new_comp, mod)

    def _onMoveTag(self, tag: int):
        if self._document is None:
            return
        from baramEditor.view.editor_dialogs import TranslateDialog
        dlg = TranslateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        dx, dy, dz = dlg.values()
        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            return
        mod = self._document.move_component_mesh(tag, dx, dy, dz)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onRotateTag(self, tag: int):
        if self._document is None:
            return
        from baramEditor.view.editor_dialogs import RotateDialog
        dlg = RotateDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        angle, axis = dlg.values()
        if angle == 0.0:
            return
        mod = self._document.rotate_component(tag, angle, axis)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onScaleTag(self, tag: int):
        if self._document is None:
            return
        from baramEditor.view.editor_dialogs import ScaleDialog
        dlg = ScaleDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        sx, sy, sz = dlg.values()
        if sx == 1.0 and sy == 1.0 and sz == 1.0:
            return
        mod = self._document.scale_component(tag, sx, sy, sz)
        if mod:
            comp = self._document.component_by_tag(tag)
            self._afterEdit(comp, mod)

    def _onMirrorTag(self, tag: int):
        if self._document is None:
            return
        from baramEditor.view.editor_dialogs import MirrorDialog
        dlg = MirrorDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        plane = dlg.plane()
        new_comp, mod = self._document.mirror_component(tag, plane)
        if new_comp is not None and mod is not None:
            self._afterAddComponent(new_comp, mod)

    # ====================================================================
    # Undo / Redo
    # ====================================================================

    def _onUndo(self):
        if self._document is None or not self._document.history.can_undo:
            return
        self._document.undo()
        self._fullRefresh()

    def _onRedo(self):
        if self._document is None or not self._document.history.can_redo:
            return
        self._document.redo()
        self._fullRefresh()

    def _onHistoryJump(self, target: int):
        if self._document is None:
            return
        current = self._document.history.cursor
        while current > target and self._document.history.can_undo:
            self._document.undo()
            current = self._document.history.cursor
        while current < target and self._document.history.can_redo:
            self._document.redo()
            current = self._document.history.cursor
        self._fullRefresh()

    def _fullRefresh(self):
        self._viewer.refresh_all()
        self._componentTree.rebuild()
        self._timeline.rebuild()
        self._updateUndoRedo()
        self._updateTriangleCount()
        # Update properties panel for current selection
        tag = self._selectedTag()
        if tag is not None and self._document:
            comp = self._document.component_by_tag(tag)
            self._propertiesPanel.set_component(comp)
        else:
            self._propertiesPanel.clear()

    # ====================================================================
    # Selection / picking
    # ====================================================================

    def _onSelectionChanged(self, tag: int):
        """Tree selection changed — highlight in viewer and update properties."""
        self._viewer.select_component(tag)
        if self._document:
            comp = self._document.component_by_tag(tag)
            self._propertiesPanel.set_component(comp)

    def _onViewerPick(self, tag: int):
        """3D viewer pick — select in tree and update properties."""
        # TODO: map picked actor back to tag
        pass

    # ====================================================================
    # About
    # ====================================================================

    def _onAbout(self):
        QMessageBox.about(
            self, 'About BaramEditor',
            '<h3>BaramEditor</h3>'
            '<p>A professional CAD component viewer and editor.</p>'
            '<p>Load STEP / IGES / BREP / STL files, add primitives, '
            'perform boolean operations, transform components, '
            'and track all changes with full undo/redo history.</p>'
            '<p style="color: #888;">Fusion 360-style interface</p>',
        )

    # ====================================================================
    # Lifecycle
    # ====================================================================

    async def start(self):
        """Called from main() after the event loop is running."""
        self.show()
        self._viewer.apply_theme(True)  # Default to dark mode for CAD

    def closeEvent(self, event):
        if self._document is not None and self._document.history.cursor > 0:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'You have unsaved changes. Exit anyway?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        self._viewer.clear()
        super().closeEvent(event)
        QApplication.instance().quit()
