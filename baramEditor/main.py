#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Entry point for BaramEditor — a Fusion 360-style CAD component
viewer / editor with modification history.

Usage:
    python -m baramEditor.main
"""

import asyncio
import logging
import os
import sys

import qasync
from PySide6.QtWidgets import QApplication

# Side-effect imports for PySide6 SVG support and Qt resource file
# noinspection PyUnresolvedReferences
import PySide6.QtSvg
# noinspection PyUnresolvedReferences
import resource_rc

from vtkmodules.vtkCommonCore import vtkSMPTools

from libbaram.process import getAvailablePhysicalCores
from libbaram.logging_config import setup_logging
from libbaram.qt_utils import apply_dark_mode_stylesheet

from baramEditor.app import app
from baramEditor.app_properties import AppProperties
from baramEditor.view.main_window import MainWindow

logger = logging.getLogger(__name__)

setup_logging(app_name='baramEditor')


def handle_exception(eType, eValue, eTraceback):
    if issubclass(eType, KeyboardInterrupt):
        sys.__excepthook__(eType, eValue, eTraceback)
        return
    logger.critical('Uncaught exception', exc_info=(eType, eValue, eTraceback))


sys.excepthook = handle_exception


def loop_exception(loop, context):
    print('exception handling: ', context['exception'])
    loop.stop()


def main():
    application = QApplication(sys.argv)

    # No MPI check needed for the editor — CAD only.

    app.setupApplication(AppProperties(
        name='BaramEditor',
        fullName=QApplication.translate('Main', 'BaramEditor'),
        iconResource='baramMesh.ico',   # reuse existing icon for now
        logoResource='baramMesh.ico',
        projectSuffix='.bep',
    ))

    os.environ['LC_NUMERIC'] = 'C'
    os.environ['QT_SCALE_FACTOR'] = app.settings.getScale()

    # VTK threading — leave one core free
    numCores = max(1, getAvailablePhysicalCores() - 1)
    smp = vtkSMPTools()
    smp.Initialize(numCores)
    smp.SetBackend('STDThread')

    app.qApplication = application

    loop = qasync.QEventLoop(application)
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(loop_exception)

    app.applyLanguage()

    apply_dark_mode_stylesheet(application, app.settings.isDarkModeEnabled())

    app.window = MainWindow()

    background_tasks = set()
    task = loop.create_task(app.window.start())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    with loop:
        loop.run_forever()

    loop.close()


if __name__ == '__main__':
    main()
