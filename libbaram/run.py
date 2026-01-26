#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import subprocess

import psutil
from pathlib import Path
import asyncio

from typing import Mapping, Optional, Sequence, Tuple

from libbaram.mpi import ParallelEnvironment

from libbaram.app_path import APP_PATH
from libbaram.process import RunSubprocess

# Solver Directory Structure
#
# solvers/
#     mingw64/ : mingw64 library, only on Windows
#         bin/
#         lib/
#     openfoam/
#         bin/ : solvers reside here
#         lib/
#         lib/sys-openmpi
#         lib/dummy
#         etc/ : OpenFOAM system 'etc'
#         tlib/ : Third-Party Library, only for Linux and macOS



# MPICMD = 'mpirun'

def _openfoam_root() -> Path:
    """Return OpenFOAM root directory.

    Dev checkouts often don't include the packaged solver tree under
    <APP_PATH>/solvers/openfoam. Allow pointing to an external install.

    Supported env vars:
    - BARAM_OPENFOAM_DIR: OpenFOAM root directory containing bin/lib/etc
    - BARAM_OPENFOAM_BIN: directory containing solver executables (bin). If set,
      the root is inferred as its parent.
    """
    of_dir = os.environ.get('BARAM_OPENFOAM_DIR', '').strip().strip('"')
    if of_dir:
        return Path(of_dir)

    of_bin = os.environ.get('BARAM_OPENFOAM_BIN', '').strip().strip('"')
    if of_bin:
        return Path(of_bin).parent

    return APP_PATH / 'solvers' / 'openfoam'


OPENFOAM = _openfoam_root()


def _openfoam_bin() -> Path:
    of_bin = os.environ.get('BARAM_OPENFOAM_BIN', '').strip().strip('"')
    return Path(of_bin) if of_bin else (OPENFOAM / 'bin')


OPENFOAM_BIN = _openfoam_bin()

creationflags = 0
startupinfo = None

STDOUT_FILE_NAME = 'stdout.log'
STDERR_FILE_NAME = 'stderr.log'

WM_PROJECT_DIR = str(OPENFOAM)

if platform.system() == 'Windows':
    # MPICMD = 'mpiexec'
    MINGW = APP_PATH / 'solvers' / 'mingw64'
    library = str(OPENFOAM/'lib') + os.pathsep \
              + str(OPENFOAM/'lib'/'msmpi') + os.pathsep \
              + str(MINGW/'bin') + os.pathsep \
              + str(MINGW/'lib')
    creationflags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
            | subprocess.CREATE_NEW_PROCESS_GROUP
    )
    startupinfo = subprocess.STARTUPINFO(
        dwFlags=subprocess.STARTF_USESHOWWINDOW,
        wShowWindow=subprocess.SW_HIDE
    )

    PATH = library + os.pathsep + os.environ['PATH']

    ENV = os.environ.copy()
    ENV.update({
        'WM_PROJECT_DIR': WM_PROJECT_DIR,
        'PATH': PATH
    })

    MPI_OPTIONS = ['-env', 'WM_PROJECT_DIR', WM_PROJECT_DIR, '-env', 'PATH', PATH]
else:
    library = str(OPENFOAM/'lib') + os.pathsep \
              + str(OPENFOAM/'lib'/'sys-openmpi') + os.pathsep \
              + str(OPENFOAM/'lib'/'dummy') + os.pathsep \
              + str(OPENFOAM/'tlib')

    if platform.system() == 'Darwin':
        library += os.pathsep + '/opt/homebrew/lib'
        library = str(APP_PATH) + os.pathsep + library  # APP_PATH should be at the front to get priority

    if platform.system() == 'Darwin':
        LIBRARY_PATH_NAME = 'DYLD_LIBRARY_PATH'
    else:
        LIBRARY_PATH_NAME = 'LD_LIBRARY_PATH'

    if LIBRARY_PATH_NAME not in os.environ:
        os.environ[LIBRARY_PATH_NAME] = ''

    LIBRARY_PATH = library + os.pathsep + os.environ[LIBRARY_PATH_NAME]

    ENV = os.environ.copy()
    ENV.update({
        'WM_PROJECT_DIR': WM_PROJECT_DIR,
        LIBRARY_PATH_NAME: LIBRARY_PATH
    })

    if platform.system() == 'Darwin':
        PATH = '/opt/homebrew/bin' + os.pathsep + os.environ['PATH']
        ENV.update({
            'PATH': PATH,
            'DYLD_FALLBACK_LIBRARY_PATH': LIBRARY_PATH,  # To find libraries for function objects
            'FOAM_LD_LIBRARY_PATH': library
        })

    MPI_OPTIONS = ['-x', 'WM_PROJECT_DIR', '-x', LIBRARY_PATH_NAME]


def merged_env(extra_env: Optional[Mapping[str, object]]) -> dict:
    if not extra_env:
        return ENV

    merged = ENV.copy()
    for key, value in extra_env.items():
        if key is None:
            continue
        merged[str(key)] = '' if value is None else str(value)

    return merged


def openSolverProcess(cmd, casePath, extra_env: Optional[Mapping[str, object]] = None):
    stdout = open(casePath / STDOUT_FILE_NAME, 'w')
    stderr = open(casePath / STDERR_FILE_NAME, 'w')

    p = subprocess.Popen(
        cmd,
        env=merged_env(extra_env),
        cwd=casePath,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )

    stdout.close()
    stderr.close()

    return p


def openExternalProcess(cmd, casePath: Path, extra_env: Optional[Mapping[str, object]] = None):
    stdout = open(casePath / STDOUT_FILE_NAME, 'w')
    stderr = open(casePath / STDERR_FILE_NAME, 'w')

    p = subprocess.Popen(
        cmd,
        env=merged_env(extra_env),
        cwd=casePath,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )

    stdout.close()
    stderr.close()

    return p


async def runExternalCommand(
    cmd: Sequence[str],
    casePath: Path,
    extra_env: Optional[Mapping[str, object]] = None,
):
    stdout = open(casePath / STDOUT_FILE_NAME, 'w')
    stderr = open(casePath / STDERR_FILE_NAME, 'w')

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=merged_env(extra_env),
            cwd=casePath,
            creationflags=creationflags,
            startupinfo=startupinfo,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        stdout.close()
        stderr.close()

    return proc


def launchSolverOnWindow(
    solver: str,
    casePath: Path,
    parallel: ParallelEnvironment,
    extra_env: Optional[Mapping[str, object]] = None,
) -> Tuple[int, float]:
    process = openSolverProcess(
        parallel.makeCommand(OPENFOAM / 'bin' / solver, cwd=casePath, options=MPI_OPTIONS), casePath, extra_env=extra_env)

    ps = psutil.Process(pid=process.pid)
    return ps.pid, ps.create_time()


def launchSolverOnLinux(
    solver: str,
    casePath: Path,
    uuid,
    parallel: ParallelEnvironment,
    extra_env: Optional[Mapping[str, object]] = None,
) -> Tuple[int, float]:
    args = [OPENFOAM/'bin'/'baramd', '-project', uuid, '-cmdline']
    args.extend(parallel.makeCommand(OPENFOAM / 'bin' / solver, cwd=casePath, options=MPI_OPTIONS))

    process = openSolverProcess(args, casePath, extra_env=extra_env)
    process.wait()

    processes = [p for p in psutil.process_iter(['pid', 'cmdline', 'create_time'])
                 if (p.info['cmdline'] is not None) and (uuid in p.info['cmdline'])]
    if processes:
        ps = max(processes, key=lambda p: p.create_time())
        return ps.pid, ps.create_time()

    return None


def launchSolver(
    solver: str,
    casePath: Path,
    uuid,
    parallel: ParallelEnvironment,
    extra_env: Optional[Mapping[str, object]] = None,
) -> Tuple[int, float]:
    """Launch solver

    Launch solver in case folder
    Solver runs by mpirun/mpiexec by default

    Solver standard output file
        casePath/stdout.log
    Solver standard error file
        casePath/stderr.log

    Args:
        solver: solver name
        casePath: case folder absolute path
        uuid: UUID for the process
        parallel: Parallel Environment

    Returns:
        pid: process id of mpirun/mpiexec
        create_time: process creation time
    """
    if not isinstance(casePath, Path) or not casePath.is_absolute():
        raise AssertionError

    if platform.system() == 'Windows':
        return launchSolverOnWindow(solver, casePath, parallel, extra_env=extra_env)
    else:
        return launchSolverOnLinux(solver, casePath, uuid, parallel, extra_env=extra_env)


async def runUtility(program: str, *args, cwd=None, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL):
    global creationflags
    global startupinfo

    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW,
            wShowWindow=subprocess.SW_HIDE
        )

    exe = OPENFOAM_BIN / program
    if platform.system() == 'Windows' and exe.suffix.lower() != '.exe':
        exe = exe.with_suffix('.exe')
    if not exe.is_file():
        raise FileNotFoundError(
            f"OpenFOAM executable not found: {exe}. "
            f"Set BARAM_OPENFOAM_BIN to your OpenFOAM bin directory (or BARAM_OPENFOAM_DIR to the root)."
        )

    proc = await asyncio.create_subprocess_exec(exe, *args,
                                                env=ENV, cwd=cwd,
                                                creationflags=creationflags,
                                                startupinfo=startupinfo,
                                                stdout=stdout,
                                                stderr=stderr)

    return proc


class RunUtility(RunSubprocess):
    def __init__(self, program: str, *args, cwd: Path = None, useVenv=True, parallel: ParallelEnvironment = None):
        super().__init__(program, *args, cwd=cwd, useVenv=useVenv)

        self._parallel = parallel

    async def start(self):
        global creationflags
        global startupinfo

        if platform.system() == 'Windows':
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO(
                dwFlags=subprocess.STARTF_USESHOWWINDOW,
                wShowWindow=subprocess.SW_HIDE
            )

        exe = OPENFOAM_BIN / self._program
        if platform.system() == 'Windows' and exe.suffix.lower() != '.exe':
            exe = exe.with_suffix('.exe')
        if not exe.is_file():
            raise FileNotFoundError(
                f"OpenFOAM executable not found: {exe}. "
                f"Set BARAM_OPENFOAM_BIN to your OpenFOAM bin directory (or BARAM_OPENFOAM_DIR to the root)."
            )

        if self._parallel is None:
            self._proc = await asyncio.create_subprocess_exec(exe, *self._args,
                                                              env=ENV, cwd=self._cwd,
                                                              creationflags=creationflags,
                                                              startupinfo=startupinfo,
                                                              stdout=asyncio.subprocess.PIPE,
                                                              stderr=asyncio.subprocess.PIPE)
        else:
            self._proc = await asyncio.create_subprocess_exec(
                *self._parallel.makeCommand(exe, *self._args, cwd=self._cwd, options=MPI_OPTIONS),
                env=ENV, cwd=self._cwd, creationflags=creationflags, startupinfo=startupinfo, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


async def runParallelUtility(program: str, *args, parallel: ParallelEnvironment, cwd: Path = None,
                             stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                             extra_env: Optional[Mapping[str, object]] = None):
    global creationflags
    global startupinfo

    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW,
            wShowWindow=subprocess.SW_HIDE
        )

    proc = await asyncio.create_subprocess_exec(
        *parallel.makeCommand(OPENFOAM / 'bin' / program, *args, cwd=cwd, options=MPI_OPTIONS),
        env=merged_env(extra_env), cwd=cwd, creationflags=creationflags, startupinfo=startupinfo, stdout=stdout, stderr=stderr)

    return proc


def hasUtility(program: str):
    exe = OPENFOAM_BIN / program
    if platform.system() == 'Windows' and exe.suffix.lower() != '.exe':
        exe = exe.with_suffix('.exe')
    return exe.is_file()


class OpenFOAMError(Exception):
    def __init__(self, returncode, message):
        super().__init__(returncode, message)


class RunParallelUtility(RunUtility):
    pass


async def openTerminal(cwd: Path):
    env = ENV.copy()
    paths = env['PATH'].split(os.pathsep)
    paths.append(str(OPENFOAM_BIN))

    if 'VIRTUAL_ENV' in env:
        vpath = env['VIRTUAL_ENV']
        env['PATH'] = os.pathsep.join([p for p in paths if not p.startswith(vpath)])

    vvars = ['VIRTUAL_ENV', 'PYTHONHOME', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV']
    for var in vvars:
        env.pop(var, None)

    system = platform.system()

    if system == "Windows":
        env.pop('PROMPT', None)

        try:
            # Windows Terminal
            process = await asyncio.create_subprocess_exec("wt.exe", "--inheritEnvironment", "-d", str(cwd), env=env, cwd=cwd)
        except FileNotFoundError:
            # Fallback to PowerShell
            process = await asyncio.create_subprocess_exec("powershell.exe", env=env, cwd=cwd)
            
        await process.wait()

    elif system == "Darwin":  # macOS
        env.pop('PS1', None)

        process = await asyncio.create_subprocess_exec("open", "-a", "Terminal", env=env, cwd=cwd)
        await process.wait()

    elif system == "Linux":
        env.pop('PS1', None)

        process = None
        terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
        for terminal in terminals:
            try:
                process = await asyncio.create_subprocess_exec(terminal, env=env, cwd=cwd)
                await process.wait()
                break
            except FileNotFoundError:
                continue

        if process is None:
            raise RuntimeError("No suitable terminal emulator found")

    else:
        raise OSError(f"Unsupported operating system: {system}")

