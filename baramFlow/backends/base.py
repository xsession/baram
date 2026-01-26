#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Protocol, Tuple

from libbaram.mpi import ParallelEnvironment


@dataclass(frozen=True)
class BackendContext:
    case_path: Path
    project_uuid: str
    parallel: ParallelEnvironment
    extra_env: Mapping[str, object]


class SolverBackend(Protocol):
    name: str

    def launch_live(self, ctx: BackendContext) -> Tuple[int, float]:
        """Launch a long-running solve and return (pid, create_time)."""

    async def run_batch(self, ctx: BackendContext) -> int:
        """Run to completion and return process returncode."""
