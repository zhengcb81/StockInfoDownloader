# Utils API Reference

This document provides a comprehensive reference for all utility modules in `src/utils/`.

## Overview

The utils package contains 11 modules with 71 exported items, providing:
- Browser configuration utilities
- Cleanup and file management
- Security and validation
- Caching and error handling

## Module Index

| Module | Description | Key Classes/Functions |
|--------|-------------|----------------------|
| `browser_utils` | Browser configuration | `BrowserConfig`, `TimeoutConfig`, `DownloadConfig` |
| `cleanup_utils` | File/directory cleanup | `safe_cleanup()`, `cleanup_directory()`, `cleanup_file()` |
| `directory_manager` | Directory operations | `DirectoryManager`, `create_directory_manager()` |
| `keyword_matcher` | Keyword matching | `KeywordMatcher`, `KeywordConfig` |
| `string_optimizer` | String processing | `StringOptimizer`, `sanitize_filename()`, `standardize_stock_code()` |
| `security` | Security utilities | `SecurityValidator`, `safe_join_path()`, `sanitize_url()` |
| `cache_manager` | Simple caching | `CacheManager`, `get_cache_manager()`, `cached_file_exists()` |
| `validation` | Data validation | `DataValidator`, `validate_data()`, `validate_batch_data()` |
| `debug_marker` | Debug tracing | `DebugMarker` |
| `enhanced_error_handler` | Error handling | `EnhancedErrorHandler`, `error_protected()`, `RetryConfig` |
| `intelligent_cache` | Advanced caching | `IntelligentCache`, `cached()`, `CacheConfig` |

---

## browser_utils

Browser configuration classes and utilities.

### Classes

#### BrowserConfig
Configuration for browser instances.

```python
from src.utils import BrowserConfig

config = BrowserConfig(
    headless=True,
    user_agent="Mozilla/5.0...",
    window_size=(1920, 1080)
)
```

**Attributes:**
- `headless` (bool): Run browser in headless mode
- `user_agent` (str): Custom user agent string
- `window_size` (Tuple[int, int]): Browser window dimensions

#### TimeoutConfig
Timeout settings for browser operations.

```python
from src.utils import TimeoutConfig

config = TimeoutConfig(
    page_load=30.0,
    implicit_wait=10.0,
    download=60.0
)
```

**Attributes:**
- `page_load` (float): Page load timeout in seconds
- `implicit_wait` (float): Implicit wait timeout
- `download` (float): Download timeout

#### DownloadConfig
Configuration for file downloads.

```python
from src.utils import DownloadConfig

config = DownloadConfig(
    download_dir="/path/to/downloads",
    max_file_size=100 * 1024 * 1024  # 100MB
)
```

**Attributes:**
- `download_dir` (str): Directory for downloaded files
- `max_file_size` (int): Maximum file size in bytes

### Functions

#### get_default_user_agents
Returns a list of common user agent strings.

```python
from src.utils import get_default_user_agents

user_agents = get_default_user_agents()
```

#### get_common_chrome_args
Returns common Chrome browser arguments.

```python
from src.utils import get_common_chrome_args

args = get_common_chrome_args()
```

#### validate_and_normalize_timeout
Validates and normalizes timeout values.

```python
from src.utils import validate_and_normalize_timeout

timeout = validate_and_normalize_timeout(30, min_value=1, max_value=300)
```

---

## cleanup_utils

File and directory cleanup utilities.

### Functions

#### safe_cleanup
Safely cleans up files and directories with error handling.

```python
from src.utils import safe_cleanup

success = safe_cleanup("/path/to/cleanup", max_age_days=7)
```

**Parameters:**
- `path` (str): Path to clean up
- `max_age_days` (int): Maximum age of files to keep
- `exclude_patterns` (List[str]): Patterns to exclude from cleanup

**Returns:** `bool` - True if cleanup succeeded

#### cleanup_directory
Cleans up a directory with options.

```python
from src.utils import cleanup_directory

cleanup_directory("/path/to/dir", remove_empty=True)
```

#### cleanup_file
Safely removes a single file.

```python
from src.utils import cleanup_file

cleanup_file("/path/to/file.txt")
```

#### cleanup_multiple_paths
Cleans up multiple paths at once.

```python
from src.utils import cleanup_multiple_paths

cleanup_multiple_paths(["/path/1", "/path/2"])
```

#### get_directory_size
Calculates the total size of a directory.

```python
from src.utils import get_directory_size

size = get_directory_size("/path/to/dir")  # Returns size in bytes
```

---

## directory_manager

Directory management utilities.

### Classes

#### DirectoryManager
Manages directory operations with safety checks.

```python
from src.utils import DirectoryManager

manager = DirectoryManager(base_path="/base/dir")
manager.ensure_exists("subdir")
```

**Methods:**
- `ensure_exists(path)`: Creates directory if it doesn't exist
- `get_full_path(relative_path)`: Returns absolute path
- `is_within_base(path)`: Checks if path is within base directory

### Functions

#### create_directory_manager
Factory function to create a DirectoryManager.

```python
from src.utils import create_directory_manager

manager = create_directory_manager("/base/dir")
```

---

## keyword_matcher

Keyword matching and filtering utilities.

### Classes

#### KeywordConfig
Configuration for keyword matching.

```python
from src.utils import KeywordConfig

config = KeywordConfig(
    keywords=["annual", "report"],
    case_sensitive=False,
    match_all=False
)
```

#### KeywordMatcher
Matches text against keywords.

```python
from src.utils import KeywordMatcher

matcher = KeywordMatcher(config)
matches = matcher.match("2024 Annual Report")
```

**Methods:**
- `match(text)`: Returns matching keywords
- `is_match(text)`: Returns True if any keyword matches

---

## string_optimizer

String processing and optimization utilities.

### Classes

#### StringOptimizer
Optimizes string operations with caching.

```python
from src.utils import StringOptimizer

optimizer = StringOptimizer()
result = optimizer.optimize("  Some  Text  ")
```

### Functions

#### sanitize_filename
Sanitizes a string for use as a filename.

```python
from src.utils import sanitize_filename

safe_name = sanitize_filename("file:name?.txt")  # Returns "file_name_.txt"
```

#### standardize_stock_code
Standardizes stock code format.

```python
from src.utils import standardize_stock_code

code = standardize_stock_code("000001")  # Returns "000001.SZ"
```

#### normalize_whitespace
Normalizes whitespace in text.

```python
from src.utils import normalize_whitespace

text = normalize_whitespace("  Multiple   spaces  ")  # Returns "Multiple spaces"
```

#### validate_stock_code
Validates stock code format.

```python
from src.utils import validate_stock_code

is_valid = validate_stock_code("000001")  # Returns True
```

---

## security

Security and validation utilities.

### Classes

#### SecurityValidator
Validates security-related inputs.

```python
from src.utils import SecurityValidator

validator = SecurityValidator()
validator.validate_path("/safe/path")
```

### Functions

#### safe_join_path
Safely joins path components.

```python
from src.utils import safe_join_path

path = safe_join_path("/base", "subdir", "file.txt")
```

#### sanitize_url
Sanitizes URL strings.

```python
from src.utils import sanitize_url

safe_url = sanitize_url("https://example.com/path?param=value")
```

#### is_safe_file_content
Checks if file content is safe.

```python
from src.utils import is_safe_file_content

is_safe = is_safe_file_content(b"file content bytes")
```

#### validate_directory_path
Validates directory path safety.

```python
from src.utils import validate_directory_path

is_valid = validate_directory_path("/path/to/dir")
```

---

## cache_manager

Simple caching utilities.

### Classes

#### CacheManager
Manages cached data with TTL support.

```python
from src.utils import CacheManager

cache = CacheManager(max_cache_size=1000, cache_ttl=300)
cache.set_config_value("key", value)
```

### Functions

#### get_cache_manager
Returns the global cache manager instance.

```python
from src.utils import get_cache_manager

cache = get_cache_manager()
```

#### cached_file_exists
Cached file existence check.

```python
from src.utils import cached_file_exists

exists = cached_file_exists("/path/to/file", min_size=1024)
```

#### clear_all_cache
Clears all caches.

```python
from src.utils import clear_all_cache

clear_all_cache()
```

---

## validation

Data validation utilities.

### Classes

#### DataValidator
Validates data structures.

```python
from src.utils import DataValidator

validator = DataValidator()
result = validator.validate(data, schema)
```

### Functions

#### validate_data
Validates data against a schema.

```python
from src.utils import validate_data

is_valid = validate_data(data, schema)
```

#### validate_batch_data
Validates multiple data items.

```python
from src.utils import validate_batch_data

results = validate_batch_data([data1, data2], schema)
```

---

## debug_marker

Debug tracing and logging utilities.

### Classes

#### DebugMarker
Records execution steps for debugging.

```python
from src.utils import DebugMarker

marker = DebugMarker("download_process")
marker.add_step("step1", "Starting download", {"url": "http://example.com"})
marker.save()
```

**Methods:**
- `add_step(step_id, description, details)`: Adds a step record
- `save(log_dir)`: Saves marker data to file

---

## enhanced_error_handler

Advanced error handling with retry and circuit breaker patterns.

### Classes

#### ErrorSeverity
Enumeration of error severity levels.

```python
from src.utils import ErrorSeverity

severity = ErrorSeverity.HIGH
```

**Values:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

#### ErrorCategory
Enumeration of error categories.

```python
from src.utils import ErrorCategory

category = ErrorCategory.NETWORK
```

**Values:** `NETWORK`, `TIMEOUT`, `AUTHENTICATION`, `PERMISSION`, `VALIDATION`, `BUSINESS`, `SYSTEM`, `EXTERNAL`, `CRITICAL`, `UNKNOWN`

#### RetryConfig
Configuration for retry behavior.

```python
from src.utils import RetryConfig, RetryStrategy

config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL
)
```

#### CircuitBreakerConfig
Configuration for circuit breaker pattern.

```python
from src.utils import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60.0
)
```

#### EnhancedErrorHandler
Main error handler with retry and circuit breaker support.

```python
from src.utils import EnhancedErrorHandler

handler = EnhancedErrorHandler()
result = handler.execute_with_protection(risky_function)
```

### Decorators

#### error_protected
Decorator for automatic error protection.

```python
from src.utils import error_protected, RetryConfig

@error_protected(retry_config=RetryConfig(max_retries=3))
def my_function():
    # Function that might fail
    pass
```

### Functions

#### handle_error
Convenience function to handle errors.

```python
from src.utils import handle_error

error_info = handle_error(exception, context={"key": "value"})
```

---

## intelligent_cache

Advanced multi-level caching with intelligent eviction.

### Classes

#### CacheLevel
Enumeration of cache levels.

```python
from src.utils import CacheLevel

level = CacheLevel.L1_MEMORY
```

**Values:** `L1_MEMORY`, `L2_DISK`, `L3_REMOTE`

#### EvictionPolicy
Enumeration of cache eviction policies.

```python
from src.utils import EvictionPolicy

policy = EvictionPolicy.ARC
```

**Values:** `LRU`, `LFU`, `FIFO`, `ARC`, `TTL_BASED`

#### CacheConfig
Configuration for intelligent cache.

```python
from src.utils import CacheConfig, EvictionPolicy

config = CacheConfig(
    l1_max_size=1000,
    l2_max_size=10000,
    l1_eviction_policy=EvictionPolicy.ARC
)
```

#### IntelligentCache
Multi-level cache with L1 (memory) and L2 (disk) storage.

```python
from src.utils import IntelligentCache, CacheConfig

cache = IntelligentCache(CacheConfig())
cache.set("key", value, ttl=300)
result = cache.get("key")
```

**Methods:**
- `get(key, default)`: Retrieves value from cache
- `set(key, value, ttl)`: Stores value in cache
- `delete(key)`: Removes value from cache
- `clear()`: Clears all cache levels
- `get_stats()`: Returns cache statistics

### Decorators

#### cached
Decorator for function result caching.

```python
from src.utils import cached, get_global_cache

@cached(cache=get_global_cache(), ttl=300)
def expensive_function():
    # Expensive computation
    return result
```

### Functions

#### get_global_cache
Returns the global cache instance.

```python
from src.utils import get_global_cache

cache = get_global_cache()
```

#### get_cached
Convenience function to get cached values.

```python
from src.utils import get_cached

value = get_cached("key", default=None)
```

#### set_cached
Convenience function to set cached values.

```python
from src.utils import set_cached

set_cached("key", value, ttl=300)
```

---

## Usage Examples

### Complete Download Workflow

```python
from src.utils import (
    BrowserConfig, TimeoutConfig, DownloadConfig,
    DirectoryManager, sanitize_filename,
    error_protected, RetryConfig,
    IntelligentCache, CacheConfig
)

# Setup configurations
browser_config = BrowserConfig(headless=True)
timeout_config = TimeoutConfig(page_load=30.0)
download_config = DownloadConfig(download_dir="/downloads")

# Setup directory manager
dir_manager = DirectoryManager(base_path="/downloads")
dir_manager.ensure_exists("reports")

# Setup cache
cache = IntelligentCache(CacheConfig())

# Protected download function
@error_protected(retry_config=RetryConfig(max_retries=3))
def download_file(url, filename):
    safe_name = sanitize_filename(filename)
    # Download logic here
    return f"/downloads/{safe_name}"

# Use cache for stock info
def get_stock_info(stock_code):
    cached = cache.get(f"stock:{stock_code}")
    if cached:
        return cached

    # Fetch from API
    info = fetch_stock_info(stock_code)
    cache.set(f"stock:{stock_code}", info, ttl=3600)
    return info
```

---

## See Also

- [Core API](core_api.md) - Core module API reference
- [Services API](services_api.md) - Service layer API reference
- [Configuration Reference](../guides/CONFIGURATION_REFERENCE.md) - Configuration options
