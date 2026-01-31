# Services API Reference

This document provides API reference for service modules in `src/services/`.

## Overview

The services package implements the business logic layer:
- Unified download orchestration
- Download result validation
- File system operations

## Module Index

| Module | Description | Key Classes |
|--------|-------------|-------------|
| `unified_downloader` | Main download orchestration | `UnifiedDownloader` |
| `validation_service` | Result validation | `ValidationService` |
| `file_service` | File operations | `FileService` |

---

## unified_downloader

Main download orchestration service.

### Classes

#### UnifiedDownloader
Central downloader supporting multiple browser strategies.

```python
from src.services.unified_downloader import UnifiedDownloader
from src.core.config import ConfigManager

config = ConfigManager()
downloader = UnifiedDownloader(config)
```

**Constructor Parameters:**
- `config` (ConfigManager): Configuration manager instance

**Methods:**

##### download
Downloads files for a stock code.

```python
result = downloader.download(
    stock_code="000001",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**Parameters:**
- `stock_code` (str): Stock code to download
- `start_date` (str): Start date (YYYY-MM-DD)
- `end_date` (str): End date (YYYY-MM-DD)
- `file_types` (List[str]): File types to download

**Returns:** `DownloadResult` - Download operation result

##### download_batch
Downloads files for multiple stock codes.

```python
results = downloader.download_batch(
    stock_codes=["000001", "000002"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**Parameters:**
- `stock_codes` (List[str]): List of stock codes
- `start_date` (str): Start date
- `end_date` (str): End date

**Returns:** `Dict[str, DownloadResult]` - Results by stock code

##### close
Closes the downloader and releases resources.

```python
downloader.close()
```

### Usage Example

```python
from src.services.unified_downloader import UnifiedDownloader
from src.core.config import ConfigManager

# Initialize
config = ConfigManager()
config.load_from_file("config.json")

# Create downloader
downloader = UnifiedDownloader(config)

try:
    # Single download
    result = downloader.download(
        stock_code="000001",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )

    if result.success:
        print(f"Downloaded {len(result.files)} files")
    else:
        print(f"Download failed: {result.error}")

    # Batch download
    results = downloader.download_batch(
        stock_codes=["000001", "000002", "000003"],
        start_date="2024-01-01",
        end_date="2024-12-31"
    )

    for code, result in results.items():
        print(f"{code}: {'Success' if result.success else 'Failed'}")

finally:
    downloader.close()
```

---

## validation_service

Download result validation service.

### Classes

#### ValidationService
Validates downloaded files and results.

```python
from src.services.validation_service import ValidationService

validator = ValidationService()
```

**Methods:**

##### validate_file
Validates a downloaded file.

```python
is_valid = validator.validate_file(
    file_path="/path/to/file.pdf",
    min_size=1024,
    expected_extension=".pdf"
)
```

**Parameters:**
- `file_path` (str): Path to the file
- `min_size` (int): Minimum file size in bytes
- `expected_extension` (str): Expected file extension

**Returns:** `bool` - True if file is valid

##### validate_download_result
Validates a complete download result.

```python
is_valid = validator.validate_download_result(
    result=download_result,
    expected_files=5
)
```

**Parameters:**
- `result` (DownloadResult): Download result to validate
- `expected_files` (int): Expected number of files

**Returns:** `bool` - True if result is valid

### Usage Example

```python
from src.services.validation_service import ValidationService

validator = ValidationService()

# Validate single file
if validator.validate_file("/downloads/report.pdf", min_size=1024):
    print("File is valid")
else:
    print("File validation failed")

# Validate download result
is_valid = validator.validate_download_result(
    result=download_result,
    expected_files=3
)
```

---

## file_service

File system operations service.

### Classes

#### FileService
Handles file system operations.

```python
from src.services.file_service import FileService

file_service = FileService()
```

**Methods:**

##### ensure_directory
Ensures a directory exists.

```python
file_service.ensure_directory("/path/to/directory")
```

**Parameters:**
- `path` (str): Directory path

##### move_file
Moves a file to a new location.

```python
file_service.move_file(
    source="/tmp/file.pdf",
    destination="/downloads/file.pdf"
)
```

**Parameters:**
- `source` (str): Source file path
- `destination` (str): Destination file path

##### get_file_info
Gets information about a file.

```python
info = file_service.get_file_info("/path/to/file.pdf")
```

**Parameters:**
- `file_path` (str): Path to the file

**Returns:** `FileInfo` - File information object

### Usage Example

```python
from src.services.file_service import FileService

file_service = FileService()

# Ensure directory exists
file_service.ensure_directory("/downloads/reports")

# Move file
file_service.move_file(
    source="/tmp/downloaded.pdf",
    destination="/downloads/reports/annual_report.pdf"
)

# Get file info
info = file_service.get_file_info("/downloads/reports/annual_report.pdf")
print(f"Size: {info.size}, Modified: {info.modified_time}")
```

---

## See Also

- [Core API](core_api.md) - Core module API reference
- [Utils API](utils_api.md) - Utility modules API reference
- [Web API](web_api.md) - Web layer API reference
