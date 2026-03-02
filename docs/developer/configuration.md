# Configuration Management

## Overview

BARAM provides centralised configuration via `libbaram.configuration`
with a layered resolution strategy:

```
Defaults  →  Config file (~/.baram/config.yaml)  →  Environment variables
     (each layer overrides the previous)
```

## Quick Start

```python
from libbaram.configuration import config

# Read a setting
deflection = config.cad.default_deflection  # 0.001

# Override via environment
#   BARAM_CAD_DEFLECTION=0.0005

# Override via config file
config.load(Path('~/.baram/config.yaml'))
config.save(Path('~/.baram/config.yaml'))
```

## Configuration Sections

### `cad` — CAD Import Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_deflection` | float | 0.001 | Chord tolerance for tessellation |
| `default_angle` | float | 30.0 | Angular tolerance (degrees) |
| `curvature_elements` | int | 12 | Elements per 2π curvature |
| `mesh_algorithm` | int | 6 | Gmsh 2-D algorithm ID |
| `auto_identify_volumes` | bool | true | Auto-detect closed volumes |
| `max_file_size_mb` | float | 500.0 | Warn threshold for large files |

### `logging` — Logging Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `level` | str | INFO | Root log level |
| `log_dir` | str | (platform) | Log file directory |
| `log_format` | str | text | `text` or `json` |
| `max_bytes` | int | 10485760 | Max log file size |
| `backup_count` | int | 5 | Rotated backups |
| `enable_console` | bool | true | Console output |

### `mesh` — Mesh Generation Defaults

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_num_cells_x` | int | 10 | Base grid X cells |
| `default_num_cells_y` | int | 10 | Base grid Y cells |
| `default_num_cells_z` | int | 10 | Base grid Z cells |
| `default_resolve_feature_angle` | float | 30.0 | Feature angle |
| `max_global_cells` | int | 100000000 | Global cell limit |
| `max_local_cells` | int | 10000000 | Local cell limit |

### `ui` — User Interface

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme` | str | ElegantDark | UI theme name |
| `language` | str | en | Interface language |
| `recent_import_dirs_max` | int | 10 | Recent directories |
| `confirm_geometry_removal` | bool | true | Confirm before remove |
| `show_import_statistics` | bool | true | Show import stats |

### `performance` — Performance Tuning

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vtk_smp_backend` | str | Sequential | VTK SMP backend |
| `max_render_triangles` | int | 5000000 | Render triangle limit |
| `background_save` | bool | true | Background file saves |
| `parallel_import` | bool | false | Parallel file import |

## Environment Variables

All settings can be overridden with environment variables:

| Variable | Config Path |
|----------|------------|
| `BARAM_LOG_LEVEL` | `logging.level` |
| `BARAM_LOG_DIR` | `logging.log_dir` |
| `BARAM_LOG_FORMAT` | `logging.log_format` |
| `BARAM_LOG_MAX_BYTES` | `logging.max_bytes` |
| `BARAM_LOG_BACKUP_COUNT` | `logging.backup_count` |
| `BARAM_LOG_CONSOLE` | `logging.enable_console` |
| `BARAM_CAD_DEFLECTION` | `cad.default_deflection` |
| `BARAM_CAD_ANGLE` | `cad.default_angle` |
| `BARAM_CAD_MAX_FILE_MB` | `cad.max_file_size_mb` |
| `BARAM_VTK_SMP_BACKEND` | `performance.vtk_smp_backend` |
| `BARAM_UI_THEME` | `ui.theme` |
| `BARAM_UI_LANGUAGE` | `ui.language` |

## Config File Format

```yaml
# ~/.baram/config.yaml
cad:
  default_deflection: 0.001
  default_angle: 30.0
  curvature_elements: 12
  auto_identify_volumes: true
  max_file_size_mb: 500.0

logging:
  level: INFO
  log_format: text
  max_bytes: 10485760
  backup_count: 5

mesh:
  default_num_cells_x: 10
  default_num_cells_y: 10
  default_num_cells_z: 10

ui:
  theme: ElegantDark
  language: en
  show_import_statistics: true

performance:
  vtk_smp_backend: Sequential
  max_render_triangles: 5000000
```

## Validation

- Settings are type-checked on assignment (float, int, bool, str)
- Invalid environment values produce a warning and fall back to defaults
- Unknown config file keys produce a warning but don't cause errors

## Thread Safety

The `config` singleton is a plain dataclass — reads are thread-safe.
Writes (e.g., from a settings dialog) should be serialised by the
application's main thread.
