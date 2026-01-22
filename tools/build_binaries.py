#!/usr/bin/env python
"""Build installable binaries (per-OS) using PyInstaller.

Creates:
- dist-binaries/<platform>/baramFlow/*
- dist-binaries/<platform>/baramMesh/*

This is intended for local builds and CI.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import platform
import shutil
import subprocess
import sys


def run(cmd: list[str], *, cwd: pathlib.Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def platform_id() -> str:
    system = platform.system().lower()
    if system.startswith("msys") or system.startswith("mingw"):
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return system


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Clean PyInstaller build caches")
    parser.add_argument(
        "--out",
        default="dist-binaries",
        help="Output directory (default: dist-binaries)",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    out_root = (repo_root / args.out / platform_id()).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    if args.clean:
        shutil.rmtree(repo_root / "build", ignore_errors=True)
        shutil.rmtree(repo_root / "dist", ignore_errors=True)

    # Generate Qt resources/UI python files (resource_rc.py, *_ui.py, translations)
    run([sys.executable, "convertUi.py"], cwd=repo_root)

    # Ensure pyinstaller exists
    try:
        run([sys.executable, "-m", "PyInstaller", "--version"], cwd=repo_root)
    except subprocess.CalledProcessError:
        print("error: PyInstaller not installed. Install with: pip install pyinstaller", file=sys.stderr)
        return 2

    # Build both apps
    specs = [
        repo_root / "packaging" / "pyinstaller" / "baramFlow.spec",
        repo_root / "packaging" / "pyinstaller" / "baramMesh.spec",
    ]

    for spec in specs:
        run([
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean" if args.clean else "--log-level=INFO",
            str(spec),
        ], cwd=repo_root)

    # Collect outputs into dist-binaries/<platform>/...
    # PyInstaller writes to ./dist/<name>/ (onedir) by default.
    for name in ("baramFlow", "baramMesh"):
        src = repo_root / "dist" / name
        if not src.exists():
            print(f"error: expected PyInstaller output missing: {src}", file=sys.stderr)
            return 3
        dest = out_root / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"Wrote: {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
