#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Geometry import dialog supporting STL, STEP, IGES, and BREP formats.

This dialog allows users to select one or more geometry files for import
into the BaramMesh geometry pipeline.  When CAD files (STEP/IGES/BREP) are
selected, additional tessellation quality controls are displayed.

File format detection is automatic based on the file extension.  Mixed
selection of STL and CAD files is supported — each file is routed to the
appropriate import backend.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidgetItem,
)

from baramMesh.app import app
from .cad_utility import (
    CAD_EXTENSIONS,
    TessellationParams,
    check_gmsh_available,
    get_supported_formats_filter,
    is_cad_file,
)
from .geometry_import_dialog_ui import Ui_ImportDialog

logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """Geometry file import dialog with CAD tessellation controls.

    Attributes
    ----------
    QUALITY_PRESETS : dict
        Mapping of human-readable preset names to ``TessellationParams``
        factory methods.
    """

    QUALITY_PRESETS = {
        'Coarse (fast preview)': TessellationParams.coarse,
        'Medium (balanced)': TessellationParams.medium,
        'Fine (production)': TessellationParams.fine,
    }

    def __init__(self, parent):
        super().__init__(parent)
        self._ui = Ui_ImportDialog()
        self._ui.setupUi(self)

        self._dialog: Optional[QFileDialog] = None
        self._hasCADFiles = False

        # --- CAD tessellation quality controls ---
        self._cadGroup = QGroupBox(self.tr('CAD Tessellation Quality'))
        self._cadGroup.setVisible(False)
        cadLayout = QFormLayout(self._cadGroup)

        self._qualityCombo = QComboBox()
        for name in self.QUALITY_PRESETS:
            self._qualityCombo.addItem(name)
        self._qualityCombo.setCurrentIndex(1)  # Medium
        cadLayout.addRow(self.tr('Quality Preset:'), self._qualityCombo)

        if not check_gmsh_available():
            notice = QLabel(self.tr(
                '<span style="color: #cc6600;">'
                'Note: Install <b>gmsh</b> package for STEP/IGES/BREP support.'
                '</span>'
            ))
            notice.setTextFormat(Qt.TextFormat.RichText)
            notice.setWordWrap(True)
            cadLayout.addRow(notice)

        # Insert CAD group before the button box
        layout = self._ui.verticalLayout
        layout.insertWidget(layout.count() - 1, self._cadGroup)

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        # Update dialog title
        self.setWindowTitle(self.tr('Import Geometry'))

        self._connectSignalsSlots()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def files(self) -> List[Path]:
        """Return the list of selected file paths."""
        return [Path(self._ui.files.item(i).text()) for i in range(self._ui.files.count())]

    def stlFiles(self) -> List[Path]:
        """Return only the STL files from the selection."""
        return [f for f in self.files() if f.suffix.lower() in ('.stl',)]

    def cadFiles(self) -> List[Path]:
        """Return only the CAD files (STEP/IGES/BREP) from the selection."""
        return [f for f in self.files() if is_cad_file(f)]

    def hasCADFiles(self) -> bool:
        """Return True if any CAD files are in the selection."""
        return self._hasCADFiles

    def tessellationParams(self) -> TessellationParams:
        """Return the selected tessellation parameters for CAD import."""
        preset_name = self._qualityCombo.currentText()
        factory = self.QUALITY_PRESETS.get(preset_name, TessellationParams.medium)
        return factory()

    def featureAngle(self) -> Optional[str]:
        """Return splitting feature angle text, or None if disabled."""
        return self._ui.featureAngle.text() if self._ui.splitSurface.isChecked() else None

    # ------------------------------------------------------------------
    # Signals / slots
    # ------------------------------------------------------------------

    def _connectSignalsSlots(self):
        self._ui.select.clicked.connect(self._openFileDialog)

    def _openFileDialog(self):
        file_filter = get_supported_formats_filter()

        self._dialog = QFileDialog(
            self,
            self.tr('Select Geometry Files'),
            app.settings.getRecentImportDirectory(),
            file_filter,
        )
        self._dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        self._dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self._dialog.filesSelected.connect(self._filesSelected)
        self._dialog.open()

    def _filesSelected(self, files):
        self._ui.files.clear()
        self._hasCADFiles = False

        for f in files:
            self._ui.files.addItem(QListWidgetItem(f))
            if is_cad_file(Path(f)):
                self._hasCADFiles = True

        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

        # Show/hide CAD tessellation controls
        self._cadGroup.setVisible(self._hasCADFiles)

        # Log file selection
        cad_count = len([f for f in files if is_cad_file(Path(f))])
        stl_count = len(files) - cad_count
        logger.info(
            "Files selected: %d STL, %d CAD (STEP/IGES/BREP)",
            stl_count, cad_count,
        )

        app.settings.updateRecentImportDirectory(Path(files[0]).parent)
