#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform

from libbaram.run import OPENFOAM

_basePath = OPENFOAM.joinpath('lib')
if platform.system() == 'Windows':
    _libExt = '.dll'
elif platform.system() == 'Darwin':
    _libExt = '.dylib'
else:
    _libExt = '.so'


def openfoamLibraryPath(baseName: str) -> str:
    return f'"{str(_basePath.joinpath(baseName).with_suffix(_libExt))}"'
