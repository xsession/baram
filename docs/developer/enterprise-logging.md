# Enterprise Logging

## Overview

BARAM includes a production-grade logging subsystem in
`libbaram/logging_config.py` suitable for enterprise deployments:

- **Rotating file logs** with configurable size and retention
- **Structured JSON output** for log aggregation (ELK, Splunk, etc.)
- **Console output** for interactive development
- **Correlation IDs** for tracing operations across components
- **Performance timing** decorators and context managers
- **Audit logging** for compliance and traceability

## Quick Start

```python
from libbaram.logging_config import setup_logging

# In your application entry point:
log_dir = setup_logging(level='INFO', app_name='baramMesh')
```

All subsequent `logging.getLogger(__name__)` calls will automatically
route to the configured handlers.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BARAM_LOG_LEVEL` | `INFO` | Root log level |
| `BARAM_LOG_DIR` | Platform-specific | Directory for log files |
| `BARAM_LOG_FORMAT` | `text` | `text` or `json` |
| `BARAM_LOG_MAX_BYTES` | `10485760` | Max file size before rotation |
| `BARAM_LOG_BACKUP_COUNT` | `5` | Number of backup files |
| `BARAM_LOG_CONSOLE` | `1` | Enable console output |

### Platform-Specific Log Directories

| Platform | Default directory |
|----------|------------------|
| Windows | `%LOCALAPPDATA%\BARAM\logs` |
| macOS | `~/Library/Logs/BARAM/logs` |
| Linux | `~/.local/state/BARAM/logs` |

### Programmatic Configuration

```python
from libbaram.logging_config import setup_logging

setup_logging(
    level='DEBUG',
    log_dir='/var/log/baram',
    log_format='json',       # Machine-parseable
    max_bytes=50_000_000,    # 50 MB per file
    backup_count=10,         # Keep 10 rotated files
    app_name='baramFlow',
)
```

## Features

### Structured JSON Logging

Set `BARAM_LOG_FORMAT=json` for machine-parseable output:

```json
{
  "timestamp": "2026-03-02T10:15:30.123456+00:00",
  "level": "INFO",
  "logger": "baramMesh.view.geometry.cad_utility",
  "message": "CAD Import: housing.step ...",
  "module": "cad_utility",
  "function": "_import_cad_file",
  "line": 245,
  "correlation_id": "a1b2c3d4e5f6",
  "process": 12345,
  "thread": 67890
}
```

### Correlation IDs

Track related operations across log entries:

```python
from libbaram.logging_config import set_correlation_id, clear_correlation_id

cid = set_correlation_id()  # Generates UUID
logger.info("Starting import")  # All logs now tagged with cid
# ... do work ...
clear_correlation_id()
```

### Performance Timing

#### Context manager

```python
from libbaram.logging_config import PerfTimer

with PerfTimer("STEP tessellation"):
    importer.load(files)
# Logs: "STEP tessellation completed in 3.21s"
```

#### Decorator

```python
from libbaram.logging_config import timed

@timed("mesh generation")
async def generate_mesh():
    ...
```

### Audit Logging

For compliance and traceability:

```python
from libbaram.logging_config import audit

audit('geometry.import', {
    'file': 'housing.step',
    'format': 'STEP',
    'triangles': 125430,
    'user': 'operator1',
})
```

Audit entries go to the `baram.audit` logger and can be routed to
a separate file or external system.

## Integration with Application Config

The `libbaram.configuration.config.logging` section mirrors the
environment variables:

```yaml
# ~/.baram/config.yaml
logging:
  level: INFO
  log_dir: /var/log/baram
  log_format: json
  max_bytes: 10485760
  backup_count: 5
  enable_console: true
```

## Best Practices

1. **Use module-level loggers**: `logger = logging.getLogger(__name__)`
2. **Log at appropriate levels**:
   - `DEBUG`: Detailed diagnostic (mesh sizes, VTK operations)
   - `INFO`: Normal operations (import complete, mesh generated)
   - `WARNING`: Recoverable issues (tessellation warnings, fallbacks)
   - `ERROR`: Failed operations (import error, solver crash)
   - `CRITICAL`: Application-level failures
3. **Include context**: File paths, counts, elapsed times
4. **Use correlation IDs** for multi-step operations (import → mesh → solve)
5. **Never log credentials** or sensitive file system paths in production
