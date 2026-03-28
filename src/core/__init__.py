"""
Core module
Provides project's basic functionality and configuration management
"""

from .config import ConfigManager
from .config_definitions import (
    AntiCrawlerConfig,
    BrowserConfig,
    DownloadConfig,
    GlobalConfig,
    LoggingConfig,
)
from .constants import (
    AntiCrawlerConfig as AntiCrawlerConstants,
    BrowserConfig as BrowserConstants,
    PaginationConfig,
    RetryConfig,
    TimeoutConfig,
)
from .exceptions import (
    ConfigError,
    OrgIdError,
    StockInfoError,
    WebDriverError,
)
from .logger import LoggerManager

__all__ = [
    # Configuration management
    "ConfigManager",
    "GlobalConfig",
    # Configuration dataclasses (from config_definitions)
    "BrowserConfig",
    "AntiCrawlerConfig",
    "DownloadConfig",
    "LoggingConfig",
    # Configuration constants (from constants)
    "BrowserConstants",
    "AntiCrawlerConstants",
    "TimeoutConfig",
    "RetryConfig",
    "PaginationConfig",
    # Utilities
    "LoggerManager",
    # Exceptions
    "StockInfoError",
    "WebDriverError",
    "ConfigError",
    "OrgIdError",
]
