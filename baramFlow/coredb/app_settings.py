#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from filelock import FileLock
from PySide6.QtCore import QLocale, QRect

from baramFlow.base.material.database import materialsBase
from libbaram.mpi import ParallelEnvironment, ParallelType
from resources import resource

FORMAT_VERSION = 1
RECENT_PROJECTS_NUMBER = 100

MATERIALS_FILE_NAME = 'materials.yaml'
THERMOS_FILE_NAME = 'thermos.csv'

class SettingKey(Enum):
    FORMAT_VERSION = 'format_version'
    UI_SCALING = 'ui_scaling'
    DARK_MODE = 'dark_mode'
    SOLVER_ENV = 'solver_env'
    CALCULATION_BACKEND = 'calculation_backend'
    EXTERNAL_SOLVER_COMMAND = 'external_solver_command'
    OPENCL_DEVICES = 'opencl_devices'
    OPENFOAM_SOLVER_OVERRIDES = 'openfoam_solver_overrides'
    LOCALE = 'default_language'
    RECENT_DIRECTORY = 'recent_directory'
    RECENT_CASES = 'recent_cases'
    RECENT_MESH_DIRECTORY = 'recent_mesh_directory'
    LAST_START_WINDOW_GEOMETRY = 'last_start_window_position'
    LAST_MAIN_WINDOW_GEOMETRY = 'last_main_window_position'
    PARAVIEW_INSTALLED_PATH = 'paraview_installed_path'
    PARALLEL_NP = 'parallel_np'
    PARALLEL_TYPE = 'parallel_type'
    PARALLEL_HOSTFILE = 'parallel_hostfile'


class AppSettings:
    _settingsPath = None
    _casesPath = None
    _settingsFile = None
    _applicationLockFile = None
    _settings = None

    @classmethod
    def setup(cls, name):
        cls._settingsPath = Path.home() / f'.{name}'
        cls._casesPath = cls._settingsPath / 'cases'
        cls._settingsFile = cls._settingsPath / 'baram.cfg.yaml'
        cls._applicationLockFile = cls._settingsPath / 'baram.lock'
        cls._materialsDBFile = cls._settingsPath / MATERIALS_FILE_NAME

        # ToDo: For compatibility. Remove this code block after 20241201
        # Migration from previous name of "BaramFlow"
        # Begin
        if name == 'BaramFlow':
            oldPath = Path.home().joinpath('.baram')
            if not cls._settingsPath.exists() and oldPath.is_dir():
                oldPath.replace(cls._settingsPath)
        # End

        cls._settingsPath.mkdir(exist_ok=True)
        cls._casesPath.mkdir(exist_ok=True)

        if not cls._materialsDBFile.exists():
            shutil.copy(resource.file(MATERIALS_FILE_NAME), cls._materialsDBFile)
        materialsBase.load(cls._materialsDBFile)
        
        materialsBase.loadThermos(resource.file(THERMOS_FILE_NAME))

    @classmethod
    def casesPath(cls):
        return cls._casesPath

    @classmethod
    def acquireLock(cls, timeout):
        lock = FileLock(cls._applicationLockFile)
        lock.acquire(timeout=timeout)
        return lock

    @classmethod
    def getRecentLocation(cls):
        return cls._get(SettingKey.RECENT_DIRECTORY, str(Path.home()))

    @classmethod
    def getRecentProjects(cls, count):
        projects = cls._get(SettingKey.RECENT_CASES, [])
        return projects[:count]

    @classmethod
    def updateRecents(cls, project, new):
        settings = cls._load()
        if new:
            settings[SettingKey.RECENT_DIRECTORY.value] = str(project.path.parent)

        recentCases\
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project.uuid in recentCases:
            recentCases.remove(project.uuid)
        recentCases.insert(0, project.uuid)
        settings[SettingKey.RECENT_CASES.value] = recentCases[:RECENT_PROJECTS_NUMBER]
        cls._save(settings)

    @classmethod
    def getRecentMeshDirectory(cls):
        return cls._get(SettingKey.RECENT_MESH_DIRECTORY, os.path.expanduser('~'))

    @classmethod
    def updateRecentMeshDirectory(cls, path):
        settings = cls._load()
        settings[SettingKey.RECENT_MESH_DIRECTORY.value] = path
        cls._save(settings)

    @classmethod
    def getLastStartWindowGeometry(cls) -> QRect:
        x, y, width, height = cls._get(SettingKey.LAST_START_WINDOW_GEOMETRY, [200, 100, 400, 300])
        return QRect(x, y, width, height)

    @classmethod
    def updateLastStartWindowGeometry(cls, geometry: QRect):
        settings = cls._load()
        settings[SettingKey.LAST_START_WINDOW_GEOMETRY.value] = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
        cls._save(settings)

    @classmethod
    def getLastMainWindowGeometry(cls) -> QRect:
        x, y, width, height = cls._get(SettingKey.LAST_MAIN_WINDOW_GEOMETRY, [200, 100, 1280, 770])
        return QRect(x, y, width, height)

    @classmethod
    def updateLastMainWindowGeometry(cls, geometry: QRect):
        settings = cls._load()
        settings[SettingKey.LAST_MAIN_WINDOW_GEOMETRY.value] = [geometry.x(), geometry.y(), geometry.width(), geometry.height()]
        cls._save(settings)

    @classmethod
    def getUiScaling(cls):
        return cls._get(SettingKey.UI_SCALING, '1.0')

    @classmethod
    def updateUiScaling(cls, scaling):
        settings = cls._load()
        settings[SettingKey.UI_SCALING.value] = scaling
        cls._save(settings)

    @classmethod
    def isDarkModeEnabled(cls) -> bool:
        return bool(cls._get(SettingKey.DARK_MODE, False))

    @classmethod
    def setDarkModeEnabled(cls, enabled: bool):
        settings = cls._load()
        settings[SettingKey.DARK_MODE.value] = bool(enabled)
        cls._save(settings)

    @classmethod
    def getSolverEnv(cls) -> dict:
        value = cls._get(SettingKey.SOLVER_ENV, {})
        return value if isinstance(value, dict) else {}

    @classmethod
    def setSolverEnv(cls, env: dict):
        settings = cls._load()
        settings[SettingKey.SOLVER_ENV.value] = env if isinstance(env, dict) else {}
        cls._save(settings)

    @classmethod
    def getCalculationBackend(cls) -> str:
        backend = cls._get(SettingKey.CALCULATION_BACKEND, 'openfoam')
        return backend if backend in ('openfoam', 'external') else 'openfoam'

    @classmethod
    def setCalculationBackend(cls, backend: str):
        settings = cls._load()
        settings[SettingKey.CALCULATION_BACKEND.value] = backend if backend in ('openfoam', 'external') else 'openfoam'
        cls._save(settings)

    @classmethod
    def getExternalSolverCommand(cls) -> list:
        value = cls._get(SettingKey.EXTERNAL_SOLVER_COMMAND, [])
        return value if isinstance(value, list) else []

    @classmethod
    def setExternalSolverCommand(cls, cmd: list):
        settings = cls._load()
        settings[SettingKey.EXTERNAL_SOLVER_COMMAND.value] = cmd if isinstance(cmd, list) else []
        cls._save(settings)

    @classmethod
    def getOpenCLDevices(cls) -> str:
        value = cls._get(SettingKey.OPENCL_DEVICES, '')
        return str(value) if value is not None else ''

    @classmethod
    def setOpenCLDevices(cls, devices: str):
        settings = cls._load()
        settings[SettingKey.OPENCL_DEVICES.value] = str(devices) if devices is not None else ''
        cls._save(settings)

    @classmethod
    def getOpenFOAMSolverOverrides(cls) -> dict:
        value = cls._get(SettingKey.OPENFOAM_SOLVER_OVERRIDES, {})
        return value if isinstance(value, dict) else {}

    @classmethod
    def setOpenFOAMSolverOverrides(cls, overrides: dict):
        settings = cls._load()
        settings[SettingKey.OPENFOAM_SOLVER_OVERRIDES.value] = overrides if isinstance(overrides, dict) else {}
        cls._save(settings)

    @classmethod
    def resolveOpenFOAMSolver(cls, solver: str) -> str:
        """Map a canonical OpenFOAM solver name to an overridden executable name.

        This is intended for using custom OpenFOAM builds/forks where solvers are
        shipped under different names (e.g. GPU/OpenCL-enabled variants).
        """
        if not solver:
            return solver

        overrides = cls.getOpenFOAMSolverOverrides()
        mapped = overrides.get(solver)
        if mapped is None:
            return solver

        mapped = str(mapped).strip()
        return mapped if mapped else solver

    # Territory is not considered for now
    @classmethod
    def getLocale(cls) -> QLocale:
        return QLocale(QLocale.languageToCode(QLocale(cls.getLanguage()).language()))

    @classmethod
    def getLanguage(cls):
        return cls._get(SettingKey.LOCALE, 'en')

    @classmethod
    def setLanguage(cls, language):
        settings = cls._load()
        settings[SettingKey.LOCALE.value] = language
        cls._save(settings)

    @classmethod
    def updateParaviewInstalledPath(cls, path: Path):
        settings = cls._load()
        settings[SettingKey.PARAVIEW_INSTALLED_PATH.value] = str(path)
        cls._save(settings)

    @classmethod
    def findParaviewInstalledPath(cls) -> Optional[Path]:
        def validate(pathString: str, update=True):
            if pathString:
                p = Path(pathString)
                if p.is_file():
                    if update:
                        cls.updateParaviewInstalledPath(p)

                    return p

            return None

        if path := validate(cls._get(SettingKey.PARAVIEW_INSTALLED_PATH, ''), False):
            return path

        if path := validate(shutil.which('paraview')):
            return path

        if platform.system() == 'Windows':
            # Search the unique paraview executable file.
            paraviewHomes = list(Path(os.environ.get('PROGRAMFILES')).glob('paraview*'))
            if len(paraviewHomes) == 1:
                if path := validate(str(paraviewHomes[0] / 'bin/paraview.exe')):
                    return path

        return None

    @classmethod
    def getParallenEnvironment(cls):
        settings = cls._load()
        type_ = settings.get(SettingKey.PARALLEL_TYPE.value)

        return ParallelEnvironment(
            settings.get(SettingKey.PARALLEL_NP.value, 1),
            ParallelType.LOCAL_MACHINE if type_ is None else ParallelType[type_],
            settings.get(SettingKey.PARALLEL_HOSTFILE.value))

    @classmethod
    def setParallelEnvironment(cls, environment):
        settings = cls._load()
        settings[SettingKey.PARALLEL_NP.value] = environment.np()
        settings[SettingKey.PARALLEL_TYPE.value] = environment.type().name
        settings[SettingKey.PARALLEL_HOSTFILE.value] = environment.hosts()
        cls._save(settings)

    @classmethod
    def _load(cls):
        if cls._settingsFile.is_file():
            with open(cls._settingsFile) as file:
                return yaml.load(file, Loader=yaml.FullLoader)
        else:
            return {}

    @classmethod
    def _save(cls, settings):
        settings[SettingKey.FORMAT_VERSION.value] = FORMAT_VERSION

        with open(cls._settingsFile, 'w') as file:
            yaml.dump(settings, file)

    @classmethod
    def _get(cls, key, default=None):
        settings = cls._load()
        return settings[key.value] if key.value in settings else default

    @classmethod
    def removeProject(cls, num):
        project = AppSettings.getRecentProjects(RECENT_PROJECTS_NUMBER)

        settings = cls._load()
        recentCases \
            = settings[SettingKey.RECENT_CASES.value] if SettingKey.RECENT_CASES.value in settings else []
        if project[num] in recentCases:
            recentCases.remove(project[num])
        cls._save(settings)
