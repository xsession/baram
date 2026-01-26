#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Sequence, Tuple

import psutil

from libbaram.run import openExternalProcess, runExternalCommand

from .base import BackendContext


class ExternalCommandBackend:
    name = 'external'

    def __init__(self, command: Sequence[str]):
        self._command = list(command)

    @staticmethod
    def _expand_command(command: Sequence[str], extra_env: dict) -> list[str]:
        # Allow simple placeholders so users can adapt to different solver CLIs.
        # Example:
        #   ["solver.exe", "--case={BARAM_CASE_PATH}", "--devices={BARAM_OPENCL_DEVICES}"]
        substitutions = {
            'BARAM_CASE_PATH': str(extra_env.get('BARAM_CASE_PATH', '')),
            'BARAM_PROJECT_UUID': str(extra_env.get('BARAM_PROJECT_UUID', '')),
            'BARAM_RUN_MODE': str(extra_env.get('BARAM_RUN_MODE', '')),
            'BARAM_OPENCL_DEVICES': str(extra_env.get('BARAM_OPENCL_DEVICES', '')),
        }

        expanded: list[str] = []
        for arg in command:
            try:
                expanded.append(str(arg).format(**substitutions))
            except Exception:
                expanded.append(str(arg))

        return expanded

    def launch_live(self, ctx: BackendContext) -> Tuple[int, float]:
        if not self._command:
            raise RuntimeError('External solver command is not configured')

        cmd = self._expand_command(self._command, dict(ctx.extra_env))
        process = openExternalProcess(cmd, ctx.case_path, extra_env=ctx.extra_env)
        ps = psutil.Process(process.pid)
        return ps.pid, ps.create_time()

    async def run_batch(self, ctx: BackendContext) -> int:
        if not self._command:
            raise RuntimeError('External solver command is not configured')

        cmd = self._expand_command(self._command, dict(ctx.extra_env))
        proc = await runExternalCommand(cmd, ctx.case_path, extra_env=ctx.extra_env)
        return await proc.wait()
