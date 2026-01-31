# Web API Reference

This document provides API reference for web modules in `src/web/`.

## Overview

The web package provides browser automation:
- Browser strategy abstraction
- Playwright implementation
- Selenium implementation
- Driver pool management

## Module Index

| Module | Description | Key Classes |
|--------|-------------|-------------|
| `browser_strategy` | Strategy interface | `BrowserStrategy` |
| `playwright_strategy` | Playwright implementation | `PlaywrightStrategy` |
| `selenium_strategy` | Selenium implementation | `SeleniumStrategy` |

---

## browser_strategy

Browser strategy interface defining the contract for browser implementations.

### Classes

#### BrowserStrategy
Abstract base class for browser strategies.

```python
from src.web.browser_strategy import BrowserStrategy

class CustomStrategy(BrowserStrategy):
    def navigate(self, url):
        pass

    def find_element(self, selector):
        pass

    def close(self):
        pass
```

**Abstract Methods:**
- `navigate(url)`: Navigates to a URL
- `find_element(selector)`: Finds an element by selector
- `click(selector)`: Clicks an element
- `input_text(selector, text)`: Inputs text into an element
- `get_page_source()`: Returns current page source
- `close()`: Closes the browser

---

## playwright_strategy

Playwright-based browser implementation.

### Classes

#### PlaywrightStrategy
Browser strategy using Playwright.

```python
from src.web.playwright_strategy import PlaywrightStrategy
from src.utils import BrowserConfig

config = BrowserConfig(headless=True)
strategy = PlaywrightStrategy(config)
```

**Constructor Parameters:**
- `config` (BrowserConfig): Browser configuration

**Methods:**

##### navigate
Navigates to a URL.

```python
strategy.navigate("https://www.cninfo.com.cn")
```

##### find_element
Finds an element by CSS selector.

```python
element = strategy.find_element("#search-input")
```

##### click
Clicks an element.

```python
strategy.click("#download-button")
```

##### input_text
Inputs text into an element.

```python
strategy.input_text("#stock-code", "000001")
```

##### wait_for_download
Waits for a file download to complete.

```python
download_path = strategy.wait_for_download(timeout=60)
```

**Returns:** `str` - Path to downloaded file

##### close
Closes the browser.

```python
strategy.close()
```

### Usage Example

```python
from src.web.playwright_strategy import PlaywrightStrategy
from src.utils import BrowserConfig, TimeoutConfig

# Create configuration
config = BrowserConfig(
    headless=True,
    window_size=(1920, 1080)
)

# Create strategy
strategy = PlaywrightStrategy(config)

try:
    # Navigate to page
    strategy.navigate("https://www.cninfo.com.cn")

    # Input stock code
    strategy.input_text("#stock-code-input", "000001")

    # Click search
    strategy.click("#search-button")

    # Wait for and click download
    strategy.click("#download-link")
    download_path = strategy.wait_for_download(timeout=60)

    print(f"Downloaded to: {download_path}")

finally:
    strategy.close()
```

---

## selenium_strategy

Selenium-based browser implementation.

### Classes

#### SeleniumStrategy
Browser strategy using Selenium WebDriver.

```python
from src.web.selenium_strategy import SeleniumStrategy
from src.utils import BrowserConfig

config = BrowserConfig(headless=True)
strategy = SeleniumStrategy(config)
```

**Constructor Parameters:**
- `config` (BrowserConfig): Browser configuration

**Methods:**

##### navigate
Navigates to a URL.

```python
strategy.navigate("https://www.cninfo.com.cn")
```

##### find_element
Finds an element by CSS selector or XPath.

```python
element = strategy.find_element("#search-input")
element = strategy.find_element("//input[@id='search']", by="xpath")
```

##### click
Clicks an element.

```python
strategy.click("#download-button")
```

##### input_text
Inputs text into an element.

```python
strategy.input_text("#stock-code", "000001")
```

##### wait_for_element
Waits for an element to be present.

```python
element = strategy.wait_for_element("#results", timeout=10)
```

##### close
Closes the browser.

```python
strategy.close()
```

### Usage Example

```python
from src.web.selenium_strategy import SeleniumStrategy
from src.utils import BrowserConfig

# Create configuration
config = BrowserConfig(headless=False)

# Create strategy
strategy = SeleniumStrategy(config)

try:
    # Navigate to page
    strategy.navigate("https://www.cninfo.com.cn")

    # Wait for and interact with elements
    strategy.wait_for_element("#stock-code-input", timeout=10)
    strategy.input_text("#stock-code-input", "000001")
    strategy.click("#search-button")

    # Wait for results and download
    strategy.wait_for_element(".download-link", timeout=10)
    strategy.click(".download-link")

finally:
    strategy.close()
```

---

## Strategy Selection

Choose the appropriate strategy based on your needs:

| Feature | Playwright | Selenium |
|---------|------------|----------|
| Speed | Faster | Slower |
| Stability | Higher | Good |
| Memory Usage | Lower | Higher |
| Modern Web | Excellent | Good |
| Headless | Native | Requires config |

### Factory Usage

Use the factory to create the appropriate strategy:

```python
from src.factory.downloader_factory import DownloaderFactory

# Create with Playwright (default)
downloader = DownloaderFactory.create_unified_downloader(
    config,
    browser_strategy="playwright"
)

# Create with Selenium
downloader = DownloaderFactory.create_unified_downloader(
    config,
    browser_strategy="selenium"
)
```

---

## See Also

- [Core API](core_api.md) - Core module API reference
- [Utils API](utils_api.md) - Utility modules API reference
- [Services API](services_api.md) - Service layer API reference
