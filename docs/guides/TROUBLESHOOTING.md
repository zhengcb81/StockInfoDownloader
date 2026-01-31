# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with StockInfoDownloader.

## Quick Diagnostic

If you're experiencing issues, check these first:

1. **Run tests**: `python tests/run_tests.py`
2. **Check logs**: Look at `logs/app.log` for error details
3. **Verify config**: Ensure `config.json` is valid JSON
4. **Check disk space**: Ensure sufficient space for downloads

---

## Common Issues

### Download Failures

#### Issue: Downloads timeout consistently

**Symptoms:**
- Error: `TimeoutError` or `DownloadError: Timeout`
- Downloads start but never complete

**Solutions:**

1. **Increase timeout in config:**
```json
{
  "download": {
    "timeout": 120
  },
  "browser": {
    "page_load_timeout": 60,
    "download_timeout": 120
  }
}
```

2. **Check network connection:**
```bash
ping www.cninfo.com.cn
```

3. **Try different browser strategy:**
```json
{
  "browser": {
    "strategy": "selenium"
  }
}
```

#### Issue: File downloads but is corrupted

**Symptoms:**
- File exists but cannot be opened
- File size is 0 bytes or very small

**Solutions:**

1. **Check minimum file size setting:**
```json
{
  "download": {
    "min_file_size": 1024
  }
}
```

2. **Verify disk space:**
```bash
# Windows
dir

# Linux/Mac
df -h
```

3. **Check antivirus software** - may be blocking downloads

#### Issue: "No files found" for valid stock code

**Symptoms:**
- Stock code is valid but no documents found
- Empty results for known-good companies

**Solutions:**

1. **Verify stock code format:**
```python
from src.utils import standardize_stock_code
code = standardize_stock_code("000001")  # Should return "000001.SZ"
```

2. **Check date range:**
```python
# Ensure dates are in correct format
start_date = "2024-01-01"  # YYYY-MM-DD
end_date = "2024-12-31"
```

3. **Clear mapping cache:**
```python
from src.utils import clear_all_cache
clear_all_cache()
```

### Browser Issues

#### Issue: Browser crashes immediately

**Symptoms:**
- `WebDriverException` on startup
- Browser window opens then closes

**Solutions:**

1. **Update browser drivers:**
```bash
# For Playwright
playwright install

# For Selenium - download latest ChromeDriver
# https://chromedriver.chromium.org/
```

2. **Check browser installation:**
```bash
# Verify Chrome is installed
google-chrome --version  # Linux/Mac
# or
"C:\Program Files\Google\Chrome\Application\chrome.exe" --version  # Windows
```

3. **Try headless mode:**
```json
{
  "browser": {
    "headless": true
  }
}
```

#### Issue: Element not found errors

**Symptoms:**
- `NoSuchElementException`
- Cannot find download buttons or search fields

**Solutions:**

1. **Increase wait time:**
```json
{
  "browser": {
    "implicit_wait": 20,
    "page_load_timeout": 45
  }
}
```

2. **Check website accessibility:**
```bash
curl -I https://www.cninfo.com.cn
```

3. **Website may have changed** - check for updates to the downloader

### Configuration Issues

#### Issue: Config file not found

**Symptoms:**
- `FileNotFoundError: config.json`
- Default settings being used

**Solutions:**

1. **Create config file:**
```bash
copy config.example.json config.json
# or
cp config.example.json config.json
```

2. **Specify config path:**
```python
from src.core.config import ConfigManager

config = ConfigManager()
config.load_from_file("/path/to/config.json")
```

#### Issue: Invalid configuration errors

**Symptoms:**
- `ConfigurationError` on startup
- Validation failures

**Solutions:**

1. **Validate JSON syntax:**
```bash
# Use Python
python -m json.tool config.json

# Or online JSON validators
```

2. **Check configuration values:**
```python
from src.core.config import ConfigManager

config = ConfigManager()
try:
    config.load_from_file("config.json")
except Exception as e:
    print(f"Config error: {e}")
```

### Memory Issues

#### Issue: High memory usage

**Symptoms:**
- System slows down during downloads
- `MemoryError` exceptions
- Browser consumes too much RAM

**Solutions:**

1. **Reduce concurrent downloads:**
```json
{
  "download": {
    "concurrent_downloads": 2
  }
}
```

2. **Enable browser cleanup:**
```python
# Close downloader after each batch
downloader.close()
```

3. **Clear cache:**
```python
from src.utils import clear_all_cache
clear_all_cache()
```

#### Issue: Disk space full

**Symptoms:**
- Downloads fail with disk errors
- Cannot create new files

**Solutions:**

1. **Clean up old downloads:**
```python
from src.utils import cleanup_directory

cleanup_directory("./downloads", max_age_days=7)
```

2. **Change download directory:**
```json
{
  "download": {
    "directory": "/path/with/more/space"
  }
}
```

3. **Monitor disk usage:**
```python
from src.utils import get_directory_size

size = get_directory_size("./downloads")
print(f"Download folder size: {size / 1024 / 1024:.2f} MB")
```

---

## Error Code Reference

### Download Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `DOWNLOAD_TIMEOUT` | Download took too long | Increase timeout, check network |
| `DOWNLOAD_FAILED` | General download failure | Check logs, retry |
| `FILE_TOO_SMALL` | Downloaded file too small | Check source, retry |
| `FILE_INVALID` | File is corrupted | Retry download, check disk space |
| `NETWORK_ERROR` | Network connectivity issue | Check internet connection |

### Browser Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `BROWSER_CRASH` | Browser crashed | Update drivers, check memory |
| `ELEMENT_NOT_FOUND` | Could not find UI element | Increase wait time, check website |
| `NAVIGATION_ERROR` | Failed to load page | Check URL, network, website status |
| `WEBDRIVER_ERROR` | WebDriver issue | Update browser/drivers |

### Configuration Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `CONFIG_INVALID` | Invalid configuration | Validate JSON, check values |
| `CONFIG_MISSING` | Missing required config | Add required configuration |
| `PATH_INVALID` | Invalid file path | Check path exists, permissions |

---

## Debug Mode

Enable debug mode for detailed logging:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

Or programmatically:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Using Debug Markers

Add debug markers to trace execution:

```python
from src.utils import DebugMarker

marker = DebugMarker("download_process")
marker.add_step("start", "Download started", {"stock_code": "000001"})

# ... download logic ...

marker.add_step("complete", "Download completed", {"files": 5})
marker.save()
```

Debug markers are saved to `logs/debug_markers/`.

---

## Getting Help

If issues persist:

1. **Check existing issues**: Search GitHub issues for similar problems
2. **Run diagnostics**: `python tests/run_tests.py`
3. **Collect logs**: Gather `logs/app.log` and debug markers
4. **Create minimal reproduction**: Simplify code to isolate issue

### Required Information for Bug Reports

When reporting issues, include:

1. **Error message**: Full traceback if available
2. **Configuration**: Relevant config (remove sensitive data)
3. **Environment**:
   - Python version: `python --version`
   - OS: Windows/Linux/Mac
   - Browser version
4. **Logs**: Relevant log entries
5. **Reproduction steps**: Minimal code to reproduce

---

## See Also

- [Configuration Reference](CONFIGURATION_REFERENCE.md) - Configuration options
- [Test Master](../testing/test_master.md) - Testing documentation
- [API Reference](../api/core_api.md) - API documentation
