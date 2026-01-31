"""
Selenium Browser Strategy Package

Provides modular Selenium WebDriver automation with separate concerns:
- driver_factory: Chrome driver creation and configuration
- download_manager: File download handling
- strategy: Main browser automation interface
"""

from .driver_factory import ChromeDriverFactory
from .download_manager import DownloadManager
from .strategy import SeleniumStrategy

# Backward compatibility - SeleniumStrategy can still be imported directly
__all__ = [
    "SeleniumStrategy",
    "ChromeDriverFactory",
    "DownloadManager",
]
