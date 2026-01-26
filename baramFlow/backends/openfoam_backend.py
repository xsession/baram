#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Tuple

from baramFlow.openfoam.solver import findSolverExecutable
from libbaram.run import launchSolver, runParallelUtility

from .base import BackendContext


class OpenFOAMBackend:
    name = 'openfoam'

    def launch_live(self, ctx: BackendContext) -> Tuple[int, float]:
        return launchSolver(
            findSolverExecutable(),
            ctx.case_path,
            ctx.project_uuid,
            ctx.parallel,
            extra_env=ctx.extra_env,
        )

    async def run_batch(self, ctx: BackendContext) -> int:
        proc = await runParallelUtility(
            findSolverExecutable(),
            parallel=ctx.parallel,
            cwd=ctx.case_path,
            extra_env=ctx.extra_env,
        )
        return await proc.wait()
