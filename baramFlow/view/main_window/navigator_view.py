#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, auto

from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont, QColor

from baramFlow.coredb import coredb
from baramFlow.case_manager import CaseManager


# Unicode icons for each navigator section (visually cleaner than loading image files)
_ICONS = {
    'SETUP':                '\u2699',     # ⚙  gear
    'SOLUTION':             '\u25b6',     # ▶  play
    'RESULTS':              '\U0001f4ca', # 📊 chart
    'GENERAL':              '\u2630',     # ☰  hamburger
    'MODELS':               '\U0001f9e9', # 🧩 puzzle
    'MATERIALS':            '\U0001f9ea', # 🧪 test tube
    'CELL_ZONE_CONDITIONS': '\u25a6',     # ▦  grid
    'BOUNDARY_CONDITIONS':  '\U0001f536', # 🔶 diamond
    'REFERENCE_VALUES':     '\U0001f4cf', # 📏 ruler
    'NUMERICAL_CONDITIONS': '\u2211',     # ∑  sigma
    'MONITORS':             '\U0001f4c8', # 📈 chart up
    'INITIALIZATION':       '\u2316',     # ⌖  crosshairs
    'RUN_CONDITIONS':       '\u23f1',     # ⏱  stopwatch
    'RUN':                  '\u25b6',     # ▶  play
    'PODROM':               '\U0001f300', # 🌀 cyclone
    'SCAFFOLDS':            '\U0001f4d0', # 📐 triangular ruler
    'GRAPHICS':             '\U0001f5bc', # 🖼  frame
    'REPORTS':              '\U0001f4cb', # 📋 clipboard
}


class MenuItem(Enum):
    MENU_SETUP = QTreeWidgetItem.UserType
    MENU_SOLUTION = auto()
    MENU_RESULTS = auto()

    # Setup
    MENU_SETUP_GENERAL = auto()
    MENU_SETUP_MODELS = auto()
    MENU_SETUP_MATERIALS = auto()
    MENU_SETUP_CELL_ZONE_CONDITIONS = auto()
    MENU_SETUP_BOUNDARY_CONDITIONS = auto()
    MENU_SETUP_REFERENCE_VALUES = auto()

    # Solution
    MENU_SOLUTION_NUMERICAL_CONDITIONS = auto()
    MENU_SOLUTION_MONITORS = auto()
    MENU_SOLUTION_INITIALIZATION = auto()
    MENU_SOLUTION_RUN_CONDITIONS = auto()
    MENU_SOLUTION_RUN = auto()
    MENU_SOLUTION_PODROM = auto()

    # Results
    MENU_RESULTS_SCAFFOLDS = auto()
    MENU_RESULTS_GRAPHICS = auto()
    MENU_RESULTS_REPORTS = auto()


class NavigatorView(QObject):
    currentMenuChanged = Signal(int, int)

    def __init__(self, tree):
        super().__init__()

        self._view = tree

        self._menuTexts = {
            MenuItem.MENU_SETUP.value: lambda: _ICONS['SETUP'] + '  ' + self.tr('Setup'),
            MenuItem.MENU_SOLUTION.value: lambda: _ICONS['SOLUTION'] + '  ' + self.tr('Solution'),
            MenuItem.MENU_RESULTS.value: lambda: _ICONS['RESULTS'] + '  ' + self.tr('Results'),

            # Setup
            MenuItem.MENU_SETUP_GENERAL.value: lambda: _ICONS['GENERAL'] + '  ' + self.tr('General'),
            MenuItem.MENU_SETUP_MODELS.value: lambda: _ICONS['MODELS'] + '  ' + self.tr('Models'),
            MenuItem.MENU_SETUP_MATERIALS.value: lambda: _ICONS['MATERIALS'] + '  ' + self.tr('Materials'),
            MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value: lambda: _ICONS['CELL_ZONE_CONDITIONS'] + '  ' + self.tr('Cell Zone Conditions'),
            MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value: lambda: _ICONS['BOUNDARY_CONDITIONS'] + '  ' + self.tr('Boundary Conditions'),
            MenuItem.MENU_SETUP_REFERENCE_VALUES.value: lambda: _ICONS['REFERENCE_VALUES'] + '  ' + self.tr('Reference Values'),

            # Solution
            MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS.value: lambda: _ICONS['NUMERICAL_CONDITIONS'] + '  ' + self.tr('Numerical Conditions'),
            MenuItem.MENU_SOLUTION_MONITORS.value: lambda: _ICONS['MONITORS'] + '  ' + self.tr('Monitors'),
            MenuItem.MENU_SOLUTION_INITIALIZATION.value: lambda: _ICONS['INITIALIZATION'] + '  ' + self.tr('Initialization'),
            MenuItem.MENU_SOLUTION_RUN_CONDITIONS.value: lambda: _ICONS['RUN_CONDITIONS'] + '  ' + self.tr('Run Conditions'),
            MenuItem.MENU_SOLUTION_RUN.value: lambda: _ICONS['RUN'] + '  ' + self.tr('Run'),
            MenuItem.MENU_SOLUTION_PODROM.value: lambda: _ICONS['PODROM'] + '  ' + self.tr('Reduced Order Model'),

            # Results
            MenuItem.MENU_RESULTS_SCAFFOLDS.value: lambda: _ICONS['SCAFFOLDS'] + '  ' + self.tr('Scaffolds'),
            MenuItem.MENU_RESULTS_GRAPHICS.value: lambda: _ICONS['GRAPHICS'] + '  ' + self.tr('Graphics'),
            MenuItem.MENU_RESULTS_REPORTS.value: lambda: _ICONS['REPORTS'] + '  ' + self.tr('Reports'),
        }

        self._menu = {}

        setupMenu = self._addTopMenu(MenuItem.MENU_SETUP)
        self._addMenu(MenuItem.MENU_SETUP_GENERAL, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_MODELS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_MATERIALS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS, setupMenu)
        self._addMenu(MenuItem.MENU_SETUP_REFERENCE_VALUES, setupMenu)

        solutionMenu = self._addTopMenu(MenuItem.MENU_SOLUTION)
        self._addMenu(MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_MONITORS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_INITIALIZATION, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_RUN_CONDITIONS, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_RUN, solutionMenu)
        self._addMenu(MenuItem.MENU_SOLUTION_PODROM, solutionMenu)

        resultsMenu = self._addTopMenu(MenuItem.MENU_RESULTS)
        self._addMenu(MenuItem.MENU_RESULTS_SCAFFOLDS, resultsMenu)
        self._addMenu(MenuItem.MENU_RESULTS_GRAPHICS, resultsMenu)
        self._addMenu(MenuItem.MENU_RESULTS_REPORTS, resultsMenu)

        self._connectSignalsSlots()

        # self._menu[MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value].setDisabled(True)
        # self._menu[MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value].setDisabled(True)
        # self.updateMenu()

    def currentMenu(self):
        return self._view.currentItem().type()

    def setCurrentMenu(self, value):
        self._view.setCurrentItem(self._menu[value])

    def updateEnabled(self):
        noMesh = not coredb.CoreDB().hasMesh()
        solverActivated = CaseManager().isActive()
        #
        # self._menu[MenuItem.MENU_SETUP_GENERAL.value].setDisabled(solverActivated)
        # self._menu[MenuItem.MENU_SETUP_MODELS.value].setDisabled(solverActivated)
        # self._menu[MenuItem.MENU_SETUP_MATERIALS.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SETUP_CELL_ZONE_CONDITIONS.value].setDisabled(noMesh)
        self._menu[MenuItem.MENU_SETUP_BOUNDARY_CONDITIONS.value].setDisabled(noMesh)
        # self._menu[MenuItem.MENU_SETUP_REFERENCE_VALUES.value].setDisabled(solverActivated)

        # self._menu[MenuItem.MENU_SOLUTION_INITIALIZATION.value].setDisabled(solverActivated)
        self._menu[MenuItem.MENU_SOLUTION_RUN.value].setDisabled(noMesh)

        # self._menu[MenuItem.MENU_SOLUTION_NUMERICAL_CONDITIONS.value].setDisabled(CaseManager().isBatchRunning())
        # self._menu[MenuItem.MENU_SOLUTION_MONITORS.value].setDisabled(CaseManager().isBatchRunning())
        # self._menu[MenuItem.MENU_SOLUTION_RUN_CONDITIONS.value].setDisabled(CaseManager().isBatchRunning())
        self._menu[MenuItem.MENU_SOLUTION_PODROM.value].setDisabled(noMesh)

        self._menu[MenuItem.MENU_RESULTS_SCAFFOLDS.value].setDisabled(noMesh)
        self._menu[MenuItem.MENU_RESULTS_GRAPHICS.value].setDisabled(noMesh)
        self._menu[MenuItem.MENU_RESULTS_REPORTS.value].setDisabled(solverActivated)

    def translate(self):
        for key, menu in self._menu.items():
            menu.setText(0, self._menuTexts[key]())

    def _connectSignalsSlots(self):
        self._view.currentItemChanged.connect(self._currentMenuChanged)

    def _addTopMenu(self, menuItem):
        self._menu[menuItem.value] = QTreeWidgetItem(self._view, [self._menuTexts[menuItem.value]()], menuItem.value)
        item = self._menu[menuItem.value]
        item.setExpanded(True)

        # Bold font for top-level groups
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

        # Slightly brighter color to distinguish category headers
        item.setForeground(0, QColor(180, 200, 230))

        return item

    def _addMenu(self, menuItem, parent):
        self._menu[menuItem.value] = QTreeWidgetItem(parent, [self._menuTexts[menuItem.value]()], menuItem.value)

    def _currentMenuChanged(self, current, previous):
        self.currentMenuChanged.emit(current.type(), previous.type() if previous else -1)
