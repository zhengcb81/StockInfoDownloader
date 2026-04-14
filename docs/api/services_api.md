# Services API Reference

This document provides API reference for service modules in `src/services/`.

## Overview

The services package implements the business logic layer:
- Unified download orchestration
- Organization ID fetching (supports Selenium and Playwright)
- Download result validation
- File system operations

## Module Index

| Module | Description | Key Classes |
|--------|-------------|-------------|
| `unified_downloader` | Main download orchestration | `UnifiedDownloader` |
| `orgid_service` | Organization ID fetching | `OrgIdService` |
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

## orgid_service

Organization ID fetching service. Supports both Selenium and Playwright through the `BrowserStrategy` abstraction.

### Classes

#### OrgIdService
Fetches organization IDs from CNINFO (巨潮资讯网) based on stock codes.

```python
from src.services.orgid_service import OrgIdService

# Use Playwright (recommended)
service = OrgIdService(strategy_type="playwright")

# Or use Selenium (default)
service = OrgIdService(strategy_type="selenium")

# Or inject a pre-configured BrowserStrategy
from src.web.browser_strategy import BrowserStrategyFactory
strategy = BrowserStrategyFactory.create_strategy("playwright", headless=True)
service = OrgIdService(browser_strategy=strategy)
```

**Constructor Parameters:**
- `browser_strategy` (BrowserStrategy, optional): Pre-configured browser strategy instance. Takes priority over `strategy_type`.
- `strategy_type` (str): Browser strategy type, `"selenium"` (default) or `"playwright"`. Only used when `browser_strategy` is `None`.
- `config` (Dict, optional): Additional configuration passed to BrowserStrategy.

**Methods:**

##### get_org_id
Fetches the organization ID for a given stock code.

```python
org_id = service.get_org_id("300470", headless=True)
# Returns: "9900023856"
```

**Parameters:**
- `stock_code` (str): Stock code (e.g., "300470", "000001")
- `headless` (bool): Whether to use headless browser mode (default: True)

**Returns:** `Optional[str]` - The org ID string, or `None` on failure. Org IDs are typically numeric (e.g., `"9900023856"`) or have a `gssz` prefix (e.g., `"gssz0000001"`).

**Extraction Strategy:**
1. Navigate to CNINFO search page for the stock code
2. Primary: Extract from "公司介绍" (Company Profile) link's `href` attribute
3. Fallback: Extract from page source code using regex patterns

### Usage Example

```python
from src.services.orgid_service import OrgIdService

# Using Playwright (recommended for stability)
service = OrgIdService(strategy_type="playwright")

try:
    org_id = service.get_org_id("300470")
    if org_id:
        print(f"Organization ID: {org_id}")
    else:
        print("Failed to fetch org ID")
finally:
    pass  # cleanup is handled internally

# Batch processing with Playwright
test_cases = [
    ("300470", "9900023856"),   # 中密控股
    ("301611", "9900056250"),   # 珂玛科技
    ("000001", "gssz0000001"),  # 平安银行
]

for code, expected in test_cases:
    service = OrgIdService(strategy_type="playwright")
    org_id = service.get_org_id(code)
    print(f"{code}: {org_id} {'OK' if org_id == expected else 'MISMATCH'}")
```

### Integration with MappingManager

When using `UnifiedDownloader`, the browser strategy is automatically propagated to `OrgIdService` via `MappingManager`:

```python
# In config.json
{
    "browser_strategy": "playwright"
}

# OrgIdService will automatically use Playwright when the downloader does
downloader = UnifiedDownloader(config)
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
