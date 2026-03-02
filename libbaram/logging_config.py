#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Enterprise-grade logging configuration for BARAM applications.

This module provides centralised, production-ready logging with:

* **Rotating file logs** — automatic size-based rotation with configurable
  retention to prevent disk exhaustion.
* **Structured JSON output** — machine-parseable log records for log
  aggregation pipelines (ELK, Splunk, CloudWatch, etc.).
* **Console output** — human-readable coloured output for interactive use.
* **Correlation IDs** — optional per-operation trace IDs for distributed
  tracing and support diagnostics.
* **Performance timing** — decorator and context manager for measuring
  operation durations.
* **Environment-based configuration** — all settings overridable via
  ``BARAM_LOG_*`` environment variables for containerised deployments.

Quick start
-----------
Call :func:`setup_logging` once during application startup:

>>> from libbaram.logging_config import setup_logging
>>> setup_logging()              # sensible defaults
>>> setup_logging(level='DEBUG') # override log level

Environment variables
---------------------
``BARAM_LOG_LEVEL``
    Root log level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``).
    Default: ``INFO``.
``BARAM_LOG_DIR``
    Directory for log files.  Default: ``<user data dir>/logs``.
``BARAM_LOG_FORMAT``
    ``text`` (default) or ``json``.
``BARAM_LOG_MAX_BYTES``
    Maximum size per log file in bytes.  Default: ``10485760`` (10 MB).
``BARAM_LOG_BACKUP_COUNT``
    Number of rotated log files to keep.  Default: ``5``.
``BARAM_LOG_CONSOLE``
    ``1`` (default) to enable console logging, ``0`` to disable.
"""

from __future__ import annotations

import contextlib
import functools
import json
import logging
import logging.handlers
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import local as _thread_local
from typing import Any, Callable, Dict, Optional, Union

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_LOG_LEVEL = 'INFO'
_DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
_DEFAULT_LOG_BACKUP_COUNT = 5
_DEFAULT_CONSOLE_FORMAT = (
    '%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s'
)
_DEFAULT_FILE_FORMAT = (
    '%(asctime)s  %(levelname)-8s  [%(name)s:%(lineno)d]  %(message)s'
)

# Thread-local storage for correlation IDs
_context = _thread_local()


# ---------------------------------------------------------------------------
# Correlation ID support
# ---------------------------------------------------------------------------

def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set a correlation ID for the current thread/task.

    Parameters
    ----------
    cid : str, optional
        Explicit correlation ID.  If *None*, a new UUID4 is generated.

    Returns
    -------
    str
        The active correlation ID.
    """
    if cid is None:
        cid = uuid.uuid4().hex[:12]
    _context.correlation_id = cid
    return cid


def get_correlation_id() -> str:
    """Return the current correlation ID, or ``'-'`` if none is set."""
    return getattr(_context, 'correlation_id', '-')


def clear_correlation_id() -> None:
    """Clear the current correlation ID."""
    _context.correlation_id = '-'


# ---------------------------------------------------------------------------
# Custom log record factory (injects correlation ID)
# ---------------------------------------------------------------------------

_original_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _original_factory(*args, **kwargs)
    record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
    return record


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects.

    Suitable for ingestion by centralised log management systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        doc: Dict[str, Any] = {
            'timestamp': datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'correlation_id': getattr(record, 'correlation_id', '-'),
            'process': record.process,
            'thread': record.thread,
        }
        if record.exc_info and record.exc_info[1]:
            doc['exception'] = self.formatException(record.exc_info)
        return json.dumps(doc, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Log directory resolution
# ---------------------------------------------------------------------------

def _default_log_dir() -> Path:
    """Return the platform-appropriate default log directory."""
    env_dir = os.environ.get('BARAM_LOG_DIR', '').strip()
    if env_dir:
        return Path(env_dir)

    if platform.system() == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif platform.system() == 'Darwin':
        base = Path.home() / 'Library' / 'Logs'
    else:
        base = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local' / 'state'))

    return base / 'BARAM' / 'logs'


# ---------------------------------------------------------------------------
# Main setup function
# ---------------------------------------------------------------------------

def setup_logging(
    level: Optional[str] = None,
    log_dir: Optional[Union[str, Path]] = None,
    log_format: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
    enable_console: Optional[bool] = None,
    app_name: str = 'baram',
) -> Path:
    """Configure the root logger for production use.

    All parameters fall back to the corresponding ``BARAM_LOG_*`` environment
    variable, then to a sensible default.

    Parameters
    ----------
    level : str, optional
        Root log level.
    log_dir : str or Path, optional
        Directory for rotating log files.
    log_format : str, optional
        ``'text'`` or ``'json'``.
    max_bytes : int, optional
        Maximum log file size before rotation.
    backup_count : int, optional
        Number of rotated backups to retain.
    enable_console : bool, optional
        Whether to attach a console (stderr) handler.
    app_name : str
        Used as the log file prefix (e.g. ``baram.log``).

    Returns
    -------
    Path
        The directory containing log files.
    """
    # Resolve parameters with env-var fallback
    level = (level or os.environ.get('BARAM_LOG_LEVEL', _DEFAULT_LOG_LEVEL)).upper()
    log_dir = Path(log_dir) if log_dir else _default_log_dir()
    log_format = log_format or os.environ.get('BARAM_LOG_FORMAT', 'text')
    max_bytes = max_bytes or int(os.environ.get('BARAM_LOG_MAX_BYTES', _DEFAULT_LOG_MAX_BYTES))
    backup_count = backup_count or int(os.environ.get('BARAM_LOG_BACKUP_COUNT', _DEFAULT_LOG_BACKUP_COUNT))
    if enable_console is None:
        enable_console = os.environ.get('BARAM_LOG_CONSOLE', '1') != '0'

    # Install custom record factory for correlation IDs
    logging.setLogRecordFactory(_record_factory)

    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers (idempotent re-configuration)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    # ── File handler (rotating) ───────────────────────────────────────
    log_file = log_dir / f'{app_name}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
    )
    file_handler.setLevel(level)
    if log_format == 'json':
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(_DEFAULT_FILE_FORMAT))
    root.addHandler(file_handler)

    # ── Console handler ───────────────────────────────────────────────
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(_DEFAULT_CONSOLE_FORMAT))
        root.addHandler(console_handler)

    # Quieten noisy third-party loggers
    for noisy in ('PIL', 'matplotlib', 'h5py', 'urllib3', 'gmsh'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.info(
        "Logging initialised: level=%s, dir=%s, format=%s, max_bytes=%s, backups=%s",
        level, log_dir, log_format, max_bytes, backup_count,
    )

    return log_dir


# ---------------------------------------------------------------------------
# Performance timing utilities
# ---------------------------------------------------------------------------

class PerfTimer:
    """Context manager that logs the elapsed time of a code block.

    Example
    -------
    >>> with PerfTimer("mesh generation"):
    ...     generate_mesh()
    INFO  [perf]  mesh generation completed in 3.21s
    """

    _logger = logging.getLogger('baram.perf')

    def __init__(self, operation: str, log_level: int = logging.INFO):
        self.operation = operation
        self.log_level = log_level
        self.elapsed: float = 0.0
        self._t0: float = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self._t0
        if exc_type is None:
            self._logger.log(
                self.log_level,
                "%s completed in %.2fs",
                self.operation, self.elapsed,
            )
        else:
            self._logger.warning(
                "%s failed after %.2fs: %s",
                self.operation, self.elapsed, exc_val,
            )
        return False  # Do not suppress exceptions


def timed(operation: Optional[str] = None, level: int = logging.INFO):
    """Decorator that logs the execution time of a function.

    Parameters
    ----------
    operation : str, optional
        Label for log messages.  Defaults to the function's qualified name.
    level : int
        Logging level.
    """
    def decorator(fn: Callable) -> Callable:
        label = operation or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with PerfTimer(label, level):
                return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            with PerfTimer(label, level):
                return await fn(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

_audit_logger = logging.getLogger('baram.audit')


def audit(action: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Write an audit log entry.

    Audit entries are always logged at ``INFO`` level to the ``baram.audit``
    logger, regardless of the root log level.

    Parameters
    ----------
    action : str
        Short description of the auditable action (e.g. ``'geometry.import'``).
    details : dict, optional
        Additional structured data.
    """
    msg = f"AUDIT  action={action}"
    if details:
        extras = '  '.join(f'{k}={v}' for k, v in details.items())
        msg = f"{msg}  {extras}"
    _audit_logger.info(msg)
