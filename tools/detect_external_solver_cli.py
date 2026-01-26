#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Heuristically detect an external solver's CLI for OpenCL device selection.

This runs the provided command with common help flags and scans stdout/stderr for
known option names.

Usage:
  python tools/detect_external_solver_cli.py -- "C:\\path\\solver.exe" --help

If you only have the executable path:
  python tools/detect_external_solver_cli.py -- "C:\\path\\solver.exe"

Notes:
- This tool only inspects help output. It does not start a simulation.
- For safety, it uses a short timeout.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence


HELP_FLAGS: Sequence[str] = ("--help", "-h", "-help", "/?", "help")

DEVICE_TOKENS = (
    "--device",
    "--devices",
    "--opencl-device",
    "--opencl-devices",
    "--cl-device",
    "--cl-devices",
    "--gpu",
    "--gpus",
    "--platform",
    "--opencl-platform",
    "--cl-platform",
)


@dataclass
class ProbeResult:
    argv: List[str]
    returncode: Optional[int]
    output: str
    timed_out: bool


def _run(argv: Sequence[str], timeout_s: float) -> ProbeResult:
    try:
        cp = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return ProbeResult(list(argv), cp.returncode, cp.stdout or "", timed_out=False)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        return ProbeResult(list(argv), None, out, timed_out=True)
    except Exception as e:
        return ProbeResult(list(argv), None, f"{type(e).__name__}: {e}", timed_out=False)


def _find_tokens(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    for tok in DEVICE_TOKENS:
        if tok.lower() in lowered:
            found.append(tok)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--", dest="_dashdash", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)

    ns = parser.parse_args()

    cmd = ns.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("Provide a command after --")
        print("Example: python tools/detect_external_solver_cli.py -- C:\\path\\solver.exe")
        return 2

    tried: List[ProbeResult] = []

    # If user already included a help flag, probe as-is first.
    if any(flag in cmd for flag in HELP_FLAGS):
        tried.append(_run(cmd, ns.timeout))
    else:
        # Try common help flags.
        for flag in HELP_FLAGS:
            tried.append(_run([*cmd, flag], ns.timeout))

    # Pick the best output (longest non-empty).
    best = max(tried, key=lambda r: len(r.output or ""))

    print("Probed:")
    for r in tried:
        suffix = " (timeout)" if r.timed_out else ""
        rc = "?" if r.returncode is None else str(r.returncode)
        print(f"  rc={rc}{suffix}: {shlex.join(r.argv)}")

    print("\n--- Captured output (trimmed) ---")
    text = best.output or ""
    if len(text) > 8000:
        print(text[:8000])
        print("... (trimmed)")
    else:
        print(text)

    tokens = _find_tokens(text)
    print("\nDetected option tokens:")
    if tokens:
        print("  " + ", ".join(tokens))
    else:
        print("  (none found)")

    print("\nNext steps:")
    print("- If your solver uses CLI args, put them into `external_solver_command`. You can use placeholders:")
    print("    {BARAM_CASE_PATH}, {BARAM_PROJECT_UUID}, {BARAM_RUN_MODE}, {BARAM_OPENCL_DEVICES}")
    print("- If your solver uses env vars, set them in `solver_env`.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
