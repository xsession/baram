#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from PySide6.QtCore import QObject, QTranslator, QCoreApplication, QLocale, Signal
from PySide6.QtWidgets import QApplication

from resources import resource
from baramEditor.app_settings import appSettings


class App(QObject):
    """Application singleton for BaramEditor."""

    projectOpened = Signal(str)   # path
    projectClosed = Signal()

    def __init__(self):
        super().__init__()

        self._properties = None
        self._settings = None
        self._window = None
        self._translator = None
        self._qApplication: Optional[QApplication] = None

    @property
    def properties(self):
        return self._properties

    @property
    def settings(self):
        return self._settings

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, window):
        self._window = window

    @property
    def qApplication(self):
        return self._qApplication

    @qApplication.setter
    def qApplication(self, application):
        self._qApplication = application

    def setupApplication(self, properties):
        self._properties = properties
        appSettings.load(properties.name)
        self._settings = appSettings

    def applyLanguage(self):
        QCoreApplication.removeTranslator(self._translator)
        self._translator = QTranslator()
        self._translator.load(
            QLocale(QLocale.languageToCode(QLocale(self._settings.getLanguage()).language())),
            'baram', '_', str(resource.file('locale')),
        )
        QCoreApplication.installTranslator(self._translator)


app = App()
