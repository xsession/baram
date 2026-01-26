#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Smoke-test that an OpenFOAM solver executable can be launched.

This is meant to validate your environment + solver binary wiring (including
GPU/OpenCL-enabled OpenFOAM forks) without needing a full BaramFlow project.

It runs the solver with a help/version-like argument list (default: -help), optionally via MPI.

Usage examples (PowerShell):
    python .\tools\smoke_openfoam_load.py --solver buoyantSimpleNFoam
    python .\tools\smoke_openfoam_load.py --solver buoyantSimpleNFoamOpenCL
    python .\tools\smoke_openfoam_load.py --solver buoyantSimpleNFoam --args -help
    python .\tools\smoke_openfoam_load.py --solver buoyantSimpleNFoam --args -help -case .
  $env:BARAM_OPENFOAM_BIN = "C:\\OpenFOAM\\bin"; python .\tools\smoke_openfoam_load.py --solver buoyantSimpleNFoam

Notes:
- If you are using the packaged Baram distribution, solvers are usually under
  <APP_PATH>\solvers\openfoam\bin. This repo checkout may not include them.
- For external OpenFOAM installs, point `BARAM_OPENFOAM_BIN` to the folder
  containing solver executables, or ensure the solver is on PATH.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def _find_solver(solver: str) -> Optional[Path]:
    # 1) Explicit bin folder
    of_bin = os.environ.get("BARAM_OPENFOAM_BIN", "").strip().strip('"')
    if of_bin:
        p = Path(of_bin) / solver
        if platform.system() == "Windows":
            if p.with_suffix(".exe").is_file():
                return p.with_suffix(".exe")
        if p.is_file():
            return p

    # 2) Packaged layout (if present)
    try:
        repo_root = Path(__file__).resolve().parents[1]
        packaged = repo_root / "solvers" / "openfoam" / "bin" / solver
        if platform.system() == "Windows":
            if packaged.with_suffix(".exe").is_file():
                return packaged.with_suffix(".exe")
        if packaged.is_file():
            return packaged
    except Exception:
        pass

    # 3) PATH lookup
    found = shutil.which(solver)
    if found:
        return Path(found)

    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", required=True, help="Solver executable name (e.g. buoyantSimpleNFoam)")
    ap.add_argument(
        "--args",
        nargs=argparse.REMAINDER,
        default=None,
        help="Arguments to pass to the solver (default: -help). Use this for args starting with '-' (e.g. --args -help)",
    )
    ap.add_argument("--mpi", action="store_true", help="Run via mpiexec/mpirun -np 1")
    ap.add_argument("--timeout", type=float, default=20.0)

    ns = ap.parse_args()

    solver_path = _find_solver(ns.solver)
    if not solver_path:
        print(f"ERROR: Could not find solver '{ns.solver}'.")
        print("- Put it on PATH, or")
        print("- Set BARAM_OPENFOAM_BIN to the directory containing the solver executable.")
        print("  PowerShell example:")
        print('    $env:BARAM_OPENFOAM_BIN = "C:\\Path\\To\\OpenFOAM\\bin"')
        return 2

    with tempfile.TemporaryDirectory(prefix="baram_of_smoke_") as tmp:
        cwd = Path(tmp)

        solver_args = ns.args if ns.args else ["-help"]

        if ns.mpi:
            mpicmd = "mpiexec" if platform.system() == "Windows" else "mpirun"
            cmd = [mpicmd, "-np", "1", str(solver_path), *solver_args]
        else:
            cmd = [str(solver_path), *solver_args]

        print("Running:")
        print("  " + " ".join(cmd))
        print(f"cwd={cwd}")

        try:
            cp = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=os.environ.copy(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=ns.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"ERROR: timed out after {ns.timeout}s")
            return 3
        except FileNotFoundError as e:
            print(f"ERROR: {e}")
            return 4

        out = cp.stdout or ""
        if len(out) > 8000:
            out = out[:8000] + "\n... (trimmed)"

        print("\n--- output (trimmed) ---")
        print(out)
        print("\nreturncode=", cp.returncode)

        return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
