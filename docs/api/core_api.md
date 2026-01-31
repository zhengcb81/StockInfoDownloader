# Core API Reference

This document provides API reference for core modules in `src/core/`.

## Overview

The core package provides fundamental infrastructure:
- Configuration management
- Logging infrastructure
- Exception handling
- Data mapping

## Module Index

| Module | Description | Key Classes |
|--------|-------------|-------------|
| `config` | Configuration management | `ConfigManager` |
| `logger` | Logging infrastructure | `get_logger()` |
| `exceptions` | Exception hierarchy | `DownloadError`, `ValidationError` |

---

## config

Configuration management with dataclass support.

### Classes

#### ConfigManager
Central configuration manager with file and dataclass synchronization.

```python
from src.core.config import ConfigManager

config = ConfigManager()
config.load_from_file("config.json")
```

**Methods:**
- `load_from_file(path)`: Loads configuration from JSON file
- `save_to_file(path)`: Saves configuration to JSON file
- `get(key, default)`: Gets configuration value
- `set(key, value)`: Sets configuration value
- `sync_to_dataclass()`: Synchronizes to ConfigConstants

### Usage Example

```python
from src.core.config import ConfigManager

# Initialize
config = ConfigManager()

# Load from file
config.load_from_file("config.json")

# Get values
download_dir = config.get("download.directory", "./downloads")

# Set values
config.set("download.directory", "/new/path")

# Save changes
config.save_to_file("config.json")
```

---

## logger

Structured logging infrastructure.

### Functions

#### get_logger
Returns a configured logger instance.

```python
from src.core.logger import get_logger

logger = get_logger(__name__)
logger.info("Message")
logger.error("Error occurred", exc_info=True)
```

**Parameters:**
- `name` (str): Logger name (typically `__name__`)

**Returns:** `logging.Logger` - Configured logger instance

### Usage Example

```python
from src.core.logger import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical error")

# With exception info
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True)
```

---

## exceptions

Exception hierarchy for error handling.

### Classes

#### DownloadError
Base exception for download-related errors.

```python
from src.core.exceptions import DownloadError

raise DownloadError("Download failed", url="http://example.com")
```

#### ValidationError
Exception for validation failures.

```python
from src.core.exceptions import ValidationError

raise ValidationError("Invalid stock code", field="stock_code")
```

#### ConfigurationError
Exception for configuration issues.

```python
from src.core.exceptions import ConfigurationError

raise ConfigurationError("Missing required config", key="api_key")
```

#### BrowserError
Exception for browser-related errors.

```python
from src.core.exceptions import BrowserError

raise BrowserError("Browser crashed", browser="chrome")
```

### Usage Example

```python
from src.core.exceptions import DownloadError, ValidationError

def download_stock_info(stock_code):
    if not validate_stock_code(stock_code):
        raise ValidationError(f"Invalid stock code: {stock_code}")

    try:
        # Download logic
        pass
    except NetworkError as e:
        raise DownloadError(
            "Failed to download",
            stock_code=stock_code,
            cause=e
        )
```

---

## See Also

- [Utils API](utils_api.md) - Utility modules API reference
- [Services API](services_api.md) - Service layer API reference
- [Configuration Reference](../guides/CONFIGURATION_REFERENCE.md) - Configuration options
