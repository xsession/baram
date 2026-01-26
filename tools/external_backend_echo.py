#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Example external backend command.

Use this to validate BaramFlow's `calculation_backend: external` wiring.
It prints key env vars and writes a small marker file in the case folder.

Expected env vars:
- BARAM_CASE_PATH
- BARAM_PROJECT_UUID
- BARAM_RUN_MODE
- BARAM_OPENCL_DEVICES (optional)

It exits with code 0.
"""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    case_path = os.environ.get('BARAM_CASE_PATH', '')
    project_uuid = os.environ.get('BARAM_PROJECT_UUID', '')
    run_mode = os.environ.get('BARAM_RUN_MODE', '')
    devices = os.environ.get('BARAM_OPENCL_DEVICES', '')

    print('External backend echo')
    print('BARAM_CASE_PATH=', case_path)
    print('BARAM_PROJECT_UUID=', project_uuid)
    print('BARAM_RUN_MODE=', run_mode)
    print('BARAM_OPENCL_DEVICES=', devices)

    if case_path:
        path = Path(case_path)
        try:
            (path / 'external_backend_ok.txt').write_text(
                f'uuid={project_uuid}\nmode={run_mode}\ndevices={devices}\n',
                encoding='utf-8',
            )
        except Exception as e:
            print('Failed to write marker file:', e)
            return 2

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
