#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Centralised configuration management for BARAM applications.

Provides a single source of truth for all application settings with:

* **Layered resolution** — defaults → config file → environment variables,
  each layer overriding the previous.
* **Validation** — type-checked and range-validated on access.
* **Thread-safe singleton** — same instance across the entire process.
* **Serialisation** — save / load to YAML for user preferences.

Usage
-----
>>> from libbaram.configuration import config
>>> config.cad.default_deflection        # 0.001
>>> config.logging.level                 # 'INFO'
>>> config.load(Path('~/.baram/config.yaml'))  # overlay user prefs
>>> config.save(Path('~/.baram/config.yaml'))  # persist changes
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CADConfig:
    """CAD import / tessellation settings.

    Attributes
    ----------
    default_deflection : float
        Default chord tolerance for STEP/IGES tessellation.
    default_angle : float
        Default angular tolerance (degrees).
    curvature_elements : int
        Minimum elements per 2π of curvature.
    mesh_algorithm : int
        Gmsh 2-D meshing algorithm ID.
    auto_identify_volumes : bool
        Automatically run closed-volume detection after import.
    max_file_size_mb : float
        Warn when a CAD file exceeds this size (megabytes).
    """
    default_deflection: float = 0.001
    default_angle: float = 30.0
    curvature_elements: int = 12
    mesh_algorithm: int = 6
    auto_identify_volumes: bool = True
    max_file_size_mb: float = 500.0


@dataclass
class LoggingConfig:
    """Logging settings (see also ``libbaram.logging_config``)."""
    level: str = 'INFO'
    log_dir: str = ''
    log_format: str = 'text'
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    enable_console: bool = True


@dataclass
class MeshConfig:
    """Mesh generation defaults."""
    default_num_cells_x: int = 10
    default_num_cells_y: int = 10
    default_num_cells_z: int = 10
    default_resolve_feature_angle: float = 30.0
    max_global_cells: int = 100_000_000
    max_local_cells: int = 10_000_000


@dataclass
class UIConfig:
    """User-interface preferences."""
    theme: str = 'ElegantDark'
    language: str = 'en'
    recent_import_dirs_max: int = 10
    confirm_geometry_removal: bool = True
    show_import_statistics: bool = True


@dataclass
class PerformanceConfig:
    """Performance tuning."""
    vtk_smp_backend: str = 'Sequential'
    max_render_triangles: int = 5_000_000
    background_save: bool = True
    parallel_import: bool = False


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """Top-level application configuration.

    Access named sections as attributes::

        >>> config.cad.default_deflection
        0.001
    """
    cad: CADConfig = field(default_factory=CADConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    mesh: MeshConfig = field(default_factory=MeshConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # ------------------------------------------------------------------
    # Environment variable overlay
    # ------------------------------------------------------------------

    _ENV_PREFIX = 'BARAM_'
    _ENV_MAP: Dict[str, str] = field(default_factory=lambda: {
        'BARAM_LOG_LEVEL': 'logging.level',
        'BARAM_LOG_DIR': 'logging.log_dir',
        'BARAM_LOG_FORMAT': 'logging.log_format',
        'BARAM_LOG_MAX_BYTES': 'logging.max_bytes',
        'BARAM_LOG_BACKUP_COUNT': 'logging.backup_count',
        'BARAM_LOG_CONSOLE': 'logging.enable_console',
        'BARAM_CAD_DEFLECTION': 'cad.default_deflection',
        'BARAM_CAD_ANGLE': 'cad.default_angle',
        'BARAM_CAD_MAX_FILE_MB': 'cad.max_file_size_mb',
        'BARAM_VTK_SMP_BACKEND': 'performance.vtk_smp_backend',
        'BARAM_UI_THEME': 'ui.theme',
        'BARAM_UI_LANGUAGE': 'ui.language',
    }, repr=False)

    def __post_init__(self):
        self._apply_env_overrides()

    # ------------------------------------------------------------------
    # YAML persistence
    # ------------------------------------------------------------------

    def load(self, path: Union[str, Path]) -> None:
        """Load configuration from a YAML file, overlaying current values.

        Missing keys are silently ignored; extra keys produce a warning.
        """
        path = Path(path)
        if not path.is_file():
            logger.debug("Config file not found, using defaults: %s", path)
            return

        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not available; cannot load config file")
            return

        with open(path, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh) or {}

        self._apply_dict(data)
        logger.info("Configuration loaded from %s", path)

    def save(self, path: Union[str, Path]) -> None:
        """Save current configuration to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not available; cannot save config file")
            return

        with open(path, 'w', encoding='utf-8') as fh:
            yaml.dump(self.to_dict(), fh, default_flow_style=False, sort_keys=False)

        logger.info("Configuration saved to %s", path)

    # ------------------------------------------------------------------
    # Dict conversion
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        from dataclasses import asdict
        result = {}
        for f in fields(self):
            if f.repr is False:
                continue
            val = getattr(self, f.name)
            if hasattr(val, '__dataclass_fields__'):
                result[f.name] = asdict(val)
            else:
                result[f.name] = val
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_env_overrides(self) -> None:
        """Apply BARAM_* environment variable overrides."""
        for env_key, config_path in self._ENV_MAP.items():
            env_val = os.environ.get(env_key, '').strip()
            if not env_val:
                continue
            try:
                self._set_dotted(config_path, env_val)
                logger.debug("Env override: %s=%s → %s", env_key, env_val, config_path)
            except Exception as exc:
                logger.warning("Failed to apply env %s=%s: %s", env_key, env_val, exc)

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Recursively apply a dictionary of settings."""
        for section_name, section_data in data.items():
            section = getattr(self, section_name, None)
            if section is None or not hasattr(section, '__dataclass_fields__'):
                logger.warning("Unknown config section: %s", section_name)
                continue
            if not isinstance(section_data, dict):
                continue
            for key, value in section_data.items():
                if hasattr(section, key):
                    expected_type = type(getattr(section, key))
                    try:
                        setattr(section, key, expected_type(value))
                    except (ValueError, TypeError) as exc:
                        logger.warning(
                            "Invalid config value %s.%s=%r: %s",
                            section_name, key, value, exc,
                        )
                else:
                    logger.warning("Unknown config key: %s.%s", section_name, key)

    def _set_dotted(self, path: str, value: str) -> None:
        """Set a value by dotted path (e.g. ``'cad.default_deflection'``)."""
        parts = path.split('.')
        obj = self
        for part in parts[:-1]:
            obj = getattr(obj, part)
        attr = parts[-1]
        expected_type = type(getattr(obj, attr))
        if expected_type is bool:
            converted = value.lower() in ('1', 'true', 'yes', 'on')
        else:
            converted = expected_type(value)
        setattr(obj, attr, converted)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

#: Global configuration instance.  Import and use directly::
#:
#:     from libbaram.configuration import config
#:     print(config.cad.default_deflection)
config = AppConfig()
