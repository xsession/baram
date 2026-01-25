#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
import subprocess
import shutil
from typing import Optional

FOLDERS = ['baramFlow/view', 'baramMesh/view', 'widgets']


def _find_tool(exe: str) -> Optional[str]:
    path = shutil.which(exe)
    if path:
        return path

    scripts_dir = Path(sys.executable).resolve().parent
    candidates = [scripts_dir / exe]
    if sys.platform.startswith('win') and not exe.lower().endswith('.exe'):
        candidates.append(scripts_dir / f'{exe}.exe')

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def _require_tool(exe: str) -> str:
    path = _find_tool(exe)
    if path is None:
        raise FileNotFoundError(
            f"Required tool not found: {exe}. "
            f"Install PySide6 (not Essentials) in your active environment so it provides pyside6-uic/pyside6-rcc, "
            f"or ensure the tool is on PATH."
        )
    return path


def _optional_tool(exe: str) -> Optional[str]:
    return _find_tool(exe)

force_update = False
if len(sys.argv) > 1 and sys.argv[1] == '-f':
    force_update = True

# Convert Translation Files
print('>> Convert Translation Files')
lrelease = _optional_tool('pyside6-lrelease')
if not lrelease:
    print('  Skipping translation compilation (pyside6-lrelease not found)')
for ts in Path('resources', 'locale').glob('baram_*.ts'):
    qm = ts.with_suffix('.qm')
    if not force_update and qm.is_file() and qm.stat().st_mtime >= ts.stat().st_mtime:
        print(f'  Skipping...   {ts} -> {qm}, Already Up-to-date')
    else:
        if not lrelease:
            continue
        print(f'  Converting... {ts} -> {qm}')
        subprocess.run([lrelease, ts, '-qm', qm], check=False)


# Convert QResource File
target = Path('resource_rc.py')
source = Path('resource.qrc')
print('>> Convert QResource File')
rcc = _require_tool('pyside6-rcc')
if not force_update and target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
    print(f'  Skipping...   {source} -> {target}, Already Up-to-date')
else:
    print(f'  Converting... {source} -> {target}')
    subprocess.run([rcc, source, '-o', target], check=True)


# Convert QT Designer Files
print('\n>> Convert QT Designer Files')
uic = _require_tool('pyside6-uic')
paths = []
for folder in FOLDERS:
    paths += list(Path(folder).glob('**/*.ui'))  # Convert to 'list' to get the length of it

totalNum = len(paths)

for i, source in enumerate(paths):
    target = source.parent / (source.stem + '_ui.py')
    if not force_update and target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        print(f'  [{i+1}/{totalNum}] Skipping...   {source.name} -> {source.stem}_ui.py, Already Up-to-date')
    else:
        print(f'  [{i+1}/{totalNum}] Converting... {source.name} -> {source.stem}_ui.py')
        subprocess.run([uic, source, '-o', target], check=True)
