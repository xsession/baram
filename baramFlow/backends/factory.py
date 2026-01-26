#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from baramFlow.coredb.app_settings import AppSettings

from .external_backend import ExternalCommandBackend
from .openfoam_backend import OpenFOAMBackend


def get_backend():
    backend = AppSettings.getCalculationBackend()
    if backend == 'external':
        return ExternalCommandBackend(AppSettings.getExternalSolverCommand())

    return OpenFOAMBackend()
