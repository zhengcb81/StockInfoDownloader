# Configuration Reference

This document provides a comprehensive reference for all configuration options in StockInfoDownloader.

## Overview

Configuration is managed through JSON files and the `ConfigManager` class. The main configuration file is `config.json` in the project root.

## Configuration File Structure

```json
{
  "download": {
    "directory": "./downloads",
    "timeout": 60,
    "retry_count": 3,
    "concurrent_downloads": 5
  },
  "browser": {
    "strategy": "playwright",
    "headless": true,
    "window_size": [1920, 1080],
    "user_agent": "Mozilla/5.0..."
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "max_size": 10485760,
    "backup_count": 5
  },
  "mapping": {
    "cache_enabled": true,
    "cache_ttl": 3600
  }
}
```

## Configuration Sections

### Download Configuration

Controls file download behavior.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `download.directory` | string | `"./downloads"` | Base directory for downloaded files |
| `download.timeout` | integer | `60` | Download timeout in seconds |
| `download.retry_count` | integer | `3` | Number of retry attempts on failure |
| `download.concurrent_downloads` | integer | `5` | Maximum concurrent downloads |
| `download.min_file_size` | integer | `1024` | Minimum valid file size in bytes |
| `download.max_file_size` | integer | `104857600` | Maximum file size in bytes (100MB) |

**Example:**
```json
{
  "download": {
    "directory": "/data/downloads",
    "timeout": 120,
    "retry_count": 5,
    "concurrent_downloads": 3,
    "min_file_size": 2048,
    "max_file_size": 524288000
  }
}
```

### Browser Configuration

Controls browser automation settings.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `browser.strategy` | string | `"playwright"` | Browser strategy: `"playwright"` or `"selenium"` |
| `browser.headless` | boolean | `true` | Run browser in headless mode |
| `browser.window_size` | array | `[1920, 1080]` | Browser window size `[width, height]` |
| `browser.user_agent` | string | `null` | Custom user agent string |
| `browser.page_load_timeout` | integer | `30` | Page load timeout in seconds |
| `browser.implicit_wait` | integer | `10` | Implicit wait timeout in seconds |
| `browser.download_timeout` | integer | `60` | Download wait timeout in seconds |

**Example:**
```json
{
  "browser": {
    "strategy": "selenium",
    "headless": false,
    "window_size": [1920, 1080],
    "page_load_timeout": 45,
    "implicit_wait": 15
  }
}
```

### Logging Configuration

Controls logging behavior.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `logging.level` | string | `"INFO"` | Log level: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"` |
| `logging.file` | string | `"logs/app.log"` | Log file path |
| `logging.max_size` | integer | `10485760` | Maximum log file size in bytes (10MB) |
| `logging.backup_count` | integer | `5` | Number of backup log files to keep |
| `logging.console_output` | boolean | `true` | Enable console output |
| `logging.file_output` | boolean | `true` | Enable file output |

**Example:**
```json
{
  "logging": {
    "level": "DEBUG",
    "file": "logs/downloader.log",
    "max_size": 20971520,
    "backup_count": 10,
    "console_output": true,
    "file_output": true
  }
}
```

### Mapping Configuration

Controls stock code mapping behavior.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mapping.cache_enabled` | boolean | `true` | Enable mapping cache |
| `mapping.cache_ttl` | integer | `3600` | Cache time-to-live in seconds |
| `mapping.auto_update` | boolean | `true` | Auto-update mapping data |
| `mapping.fallback_enabled` | boolean | `true` | Enable fallback mappings |

**Example:**
```json
{
  "mapping": {
    "cache_enabled": true,
    "cache_ttl": 7200,
    "auto_update": true,
    "fallback_enabled": true
  }
}
```

### Cache Configuration

Controls caching behavior.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cache.enabled` | boolean | `true` | Enable caching |
| `cache.l1_max_size` | integer | `1000` | L1 (memory) cache max entries |
| `cache.l2_max_size` | integer | `10000` | L2 (disk) cache max entries |
| `cache.default_ttl` | integer | `3600` | Default cache TTL in seconds |
| `cache.compression_enabled` | boolean | `true` | Enable cache compression |

**Example:**
```json
{
  "cache": {
    "enabled": true,
    "l1_max_size": 2000,
    "l2_max_size": 20000,
    "default_ttl": 7200,
    "compression_enabled": true
  }
}
```

### Error Handling Configuration

Controls error handling and retry behavior.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `error_handling.max_retries` | integer | `3` | Maximum retry attempts |
| `error_handling.retry_delay` | number | `1.0` | Initial retry delay in seconds |
| `error_handling.backoff_factor` | number | `2.0` | Exponential backoff factor |
| `error_handling.circuit_breaker.enabled` | boolean | `true` | Enable circuit breaker |
| `error_handling.circuit_breaker.failure_threshold` | integer | `5` | Circuit breaker failure threshold |
| `error_handling.circuit_breaker.recovery_timeout` | integer | `60` | Circuit breaker recovery timeout |

**Example:**
```json
{
  "error_handling": {
    "max_retries": 5,
    "retry_delay": 2.0,
    "backoff_factor": 2.0,
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 3,
      "recovery_timeout": 120
    }
  }
}
```

## Environment-Specific Configuration

### Development Configuration

```json
{
  "download": {
    "directory": "./downloads/dev",
    "timeout": 30,
    "retry_count": 1
  },
  "browser": {
    "headless": false,
    "strategy": "playwright"
  },
  "logging": {
    "level": "DEBUG"
  }
}
```

### Production Configuration

```json
{
  "download": {
    "directory": "/data/downloads",
    "timeout": 120,
    "retry_count": 5,
    "concurrent_downloads": 10
  },
  "browser": {
    "headless": true,
    "strategy": "playwright"
  },
  "logging": {
    "level": "WARNING",
    "file": "/var/log/downloader.log"
  }
}
```

## Configuration Loading

### From File

```python
from src.core.config import ConfigManager

config = ConfigManager()
config.load_from_file("config.json")
```

### Programmatic Configuration

```python
from src.core.config import ConfigManager

config = ConfigManager()
config.set("download.directory", "/custom/path")
config.set("browser.headless", True)
```

### Configuration Priority

Configuration values are resolved in this priority order (highest first):

1. Programmatic settings (set at runtime)
2. Environment variables
3. Configuration file
4. Default values

## Environment Variables

Some configuration options can be set via environment variables:

| Environment Variable | Configuration Path | Example |
|---------------------|-------------------|---------|
| `DOWNLOADER_DOWNLOAD_DIR` | `download.directory` | `/data/downloads` |
| `DOWNLOADER_LOG_LEVEL` | `logging.level` | `DEBUG` |
| `DOWNLOADER_BROWSER_STRATEGY` | `browser.strategy` | `playwright` |
| `DOWNLOADER_HEADLESS` | `browser.headless` | `true` |

## Validation

Configuration is validated on load. Invalid configurations will raise `ConfigurationError`.

```python
from src.core.config import ConfigManager
from src.core.exceptions import ConfigurationError

try:
    config = ConfigManager()
    config.load_from_file("config.json")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Complete Example

```json
{
  "download": {
    "directory": "./downloads",
    "timeout": 60,
    "retry_count": 3,
    "concurrent_downloads": 5,
    "min_file_size": 1024,
    "max_file_size": 104857600
  },
  "browser": {
    "strategy": "playwright",
    "headless": true,
    "window_size": [1920, 1080],
    "page_load_timeout": 30,
    "implicit_wait": 10,
    "download_timeout": 60
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "max_size": 10485760,
    "backup_count": 5,
    "console_output": true,
    "file_output": true
  },
  "mapping": {
    "cache_enabled": true,
    "cache_ttl": 3600,
    "auto_update": true,
    "fallback_enabled": true
  },
  "cache": {
    "enabled": true,
    "l1_max_size": 1000,
    "l2_max_size": 10000,
    "default_ttl": 3600,
    "compression_enabled": true
  },
  "error_handling": {
    "max_retries": 3,
    "retry_delay": 1.0,
    "backoff_factor": 2.0,
    "circuit_breaker": {
      "enabled": true,
      "failure_threshold": 5,
      "recovery_timeout": 60
    }
  }
}
```

## See Also

- [Core API](../api/core_api.md) - ConfigManager API reference
- [Utils API](../api/utils_api.md) - Utility configuration classes
- [Project Structure](PROJECT_STRUCTURE.md) - Project organization
