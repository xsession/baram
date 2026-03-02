#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
from pathlib import Path

import yaml
from PySide6.QtCore import QLocale, QRect


FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100


class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    SCALE = 'display_scale'
    DARK_MODE = 'dark_mode'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_IMPORT_DIRECTORY = 'recent_import_directory'
    LAST_START_WINDOW_GEOMETRY = 'LAST_START_WINDOW_GEOMETRY'
    LAST_MAIN_WINDOW_GEOMETRY = 'LAST_MAIN_WINDOW_GEOMETRY'


class AppSettings:
    def __init__(self):
        self._settings = None
        self._settingsFile = None

    def load(self, name):
        path = Path.home() / f'.{name}'
        self._settingsFile = path / 'baram.cfg.yaml'

        if self._settingsFile.is_file():
            with open(self._settingsFile) as file:
                self._settings = yaml.load(file, Loader=yaml.FullLoader)
        else:
            path.mkdir(exist_ok=True)
            self._settings = {SettingKey.FORMAT_VERSION.value: FORMAT_VERSION}

    def getRecentLocation(self):
        return self._get(SettingKey.RECENT_DIRECTORY, str(Path.home()))

    def getRecentProjects(self):
        return self._get(SettingKey.RECENT_CASES, [])

    def updateRecents(self, path, new=False):
        if new:
            self._settings[SettingKey.RECENT_DIRECTORY.value] = str(path.parent)
        p = str(path)
        recentCases = self._settings.get(SettingKey.RECENT_CASES.value, [])
        if p in recentCases:
            recentCases.remove(p)
        recentCases.insert(0, p)
        self._settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_PROJECTS_NUMBER]
        self._save()

    def getRecentImportDirectory(self):
        return self._get(SettingKey.RECENT_IMPORT_DIRECTORY, str(Path.home()))

    def updateRecentImportDirectory(self, path):
        self._set(SettingKey.RECENT_IMPORT_DIRECTORY, str(path))

    def getLastStartWindowGeometry(self) -> QRect:
        x, y, width, height = self._get(SettingKey.LAST_START_WINDOW_GEOMETRY, [200, 100, 400, 300])
        return QRect(x, y, width, height)

    def updateLastStartWindowGeometry(self, geometry: QRect):
        self._set(SettingKey.LAST_START_WINDOW_GEOMETRY,
                  [geometry.x(), geometry.y(), geometry.width(), geometry.height()])

    def getLastMainWindowGeometry(self) -> QRect:
        x, y, width, height = self._get(SettingKey.LAST_MAIN_WINDOW_GEOMETRY, [200, 100, 1280, 770])
        return QRect(x, y, width, height)

    def updateLastMainWindowGeometry(self, geometry: QRect):
        self._set(SettingKey.LAST_MAIN_WINDOW_GEOMETRY,
                  [geometry.x(), geometry.y(), geometry.width(), geometry.height()])

    def getScale(self):
        return self._get(SettingKey.SCALE, '1.0')

    def setScale(self, scale):
        return self._set(SettingKey.SCALE, scale)

    def isDarkModeEnabled(self) -> bool:
        return bool(self._get(SettingKey.DARK_MODE, False))

    def setDarkModeEnabled(self, enabled: bool) -> bool:
        return self._set(SettingKey.DARK_MODE, bool(enabled))

    def getLanguage(self):
        return self._get(SettingKey.LOCALE, 'en')

    def setLanguage(self, language):
        return self._set(SettingKey.LOCALE, language)

    def _save(self):
        with open(self._settingsFile, 'w') as file:
            yaml.dump(self._settings, file)

    def _get(self, key, default=None):
        return self._settings.get(key.value, default)

    def _set(self, key, value):
        if self._settings.get(key.value) == value:
            return False
        self._settings[key.value] = value
        self._save()
        return True

    def removeProject(self, num):
        projects = self.getRecentProjects()
        recentCases = self._settings.get(SettingKey.RECENT_CASES.value, [])
        if num < len(projects) and projects[num] in recentCases:
            recentCases.remove(projects[num])
        self._save()


appSettings = AppSettings()
