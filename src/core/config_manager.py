"""
Configuration Manager Module
Provides unified configuration loading and management functionality
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .config_constants import ConfigConstants
from .config_definitions import (
    GlobalConfig,
    BrowserConfig,
    AntiCrawlerConfig,
    DownloadConfig,
    LoggingConfig
)
from .exceptions import (
    ConfigError,
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    with_error_handling,
)
from .logger import get_logger


class BaseConfigManager:
    """Base configuration manager with core functionality"""

    _instance = None
    _config: Dict[str, Any] = {}
    _global_config: GlobalConfig = GlobalConfig()

    def __new__(cls, config_file=None):
        # Create different instances for different config file paths
        # This allows using different configs in tests without interference
        if config_file:
            instance = super().__new__(cls)
            instance._is_test_instance = True
            return instance
        else:
            # Use singleton for default config
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._is_test_instance = False
            return cls._instance

    def __init__(self, config_file=None, environment="production"):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._config_path: Optional[str] = None
            self._environment = environment
            self._test_config = None
            self.logger = get_logger(self.__class__.__name__)

            # Initialize default global config
            self._global_config = GlobalConfig()

            if config_file:
                self.load_config(config_file)

    @with_error_handling(
        error_code=ErrorCode.CONFIG_FILE_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.TERMINATE,
    )
    def load_config(self, config_path: str = "config.json") -> Dict[str, Any]:
        """
        Load configuration file

        Args:
            config_path: Configuration file path

        Returns:
            Dict[str, Any]: Configuration dictionary

        Raises:
            ConfigError: Failed to load configuration file
        """
        try:
            config_path_obj = Path(config_path)
            if not config_path_obj.exists():
                # Try fallback locations
                if not config_path_obj.is_absolute():
                     # Try config/ folder
                     fallback = Path("config") / config_path_obj
                     if fallback.exists():
                         config_path_obj = fallback

            if not config_path_obj.exists():
                # If still not found, create default if it's the main config
                if config_path == "config.json":
                    self.logger.warning(f"Config file not found: {config_path}, creating default.")
                    self._config = self.get_default_config()
                    self._config_path = str(config_path_obj)
                    self._sync_to_dataclass()
                    self.save_config()
                    return self._config

                raise ConfigError(
                    f"Configuration file does not exist: {config_path}",
                    error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.TERMINATE,
                    context={"config_path": str(config_path_obj)},
                )

            with open(config_path_obj, "r", encoding="utf-8") as f:
                self._config = json.load(f)
                self._config_path = str(config_path_obj)

            # Sync to dataclass
            self._sync_to_dataclass()

            return self._config

        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Configuration file format error: {e}",
                error_code=ErrorCode.CONFIG_FORMAT_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"config_path": str(config_path), "parse_error": str(e)},
                original_exception=e,
            )
        except Exception as e:
            raise ConfigError(
                f"Failed to load configuration file: {e}",
                error_code=ErrorCode.CONFIG_LOAD_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"config_path": str(config_path)},
                original_exception=e,
            )

    def _sync_to_dataclass(self) -> None:
        """Sync dictionary config to GlobalConfig dataclass"""
        try:
            data = self._config.copy()

            # Helper to update dataclass from dict
            def update_dc(dc, dc_data):
                if not dc_data:
                    return
                for k, v in dc_data.items():
                    if hasattr(dc, k):
                        setattr(dc, k, v)

            # Update subsections
            if "browser" in data:
                update_dc(self._global_config.browser, data.pop("browser"))
            if "anti_crawler" in data:
                update_dc(self._global_config.anti_crawler, data.pop("anti_crawler"))
            if "download" in data:
                update_dc(self._global_config.download, data.pop("download"))
            if "logging" in data:
                update_dc(self._global_config.logging, data.pop("logging"))

            if "companies" in data:
                self._global_config.companies = data.pop("companies")

            # Put remainder in extra
            self._global_config.extra = data

        except Exception as e:
            self.logger.error(f"Failed to sync config to dataclass: {e}")

    # Typed Accessors (for transition)
    @property
    def browser_config(self) -> BrowserConfig:
        return self._global_config.browser

    @property
    def anti_crawler_config(self) -> AntiCrawlerConfig:
        return self._global_config.anti_crawler

    @property
    def download_config(self) -> DownloadConfig:
        return self._global_config.download

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key, supports dot notation like 'pages.0.name'
            default: Default value

        Returns:
            Any: Configuration value
        """
        if self._config_path is None and not self._config:
            self.load_config()

        # Simplified dot notation access
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            elif isinstance(value, list) and k.isdigit() and int(k) < len(value):
                value = value[int(k)]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        if self._config_path is None and not self._config:
            self.load_config()

        keys = key.split(".")
        target = self._config

        # Simplified nested dict creation
        for k in keys[:-1]:
            target = target.setdefault(k, {})

        target[keys[-1]] = value

        # Sync back to dataclass
        self._sync_to_dataclass()

    @with_error_handling(
        error_code=ErrorCode.CONFIG_SAVE_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.FALLBACK,
    )
    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        Save configuration to file

        Args:
            config_path: Configuration file path, if None use original path
        """
        if config_path is None:
            config_path = self._config_path

        if config_path is None:
            raise ConfigError(
                "Configuration file path not specified",
                error_code=ErrorCode.CONFIG_PATH_NOT_SET,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"operation": "save_config"},
            )

        try:
            config_path_obj = Path(config_path)
            config_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path_obj, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

        except Exception as e:
            raise ConfigError(
                f"Failed to save configuration file: {e}",
                error_code=ErrorCode.CONFIG_SAVE_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                context={"config_path": str(config_path)},
                original_exception=e,
            )

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration framework (no specific stock codes)"""
        # Create default GlobalConfig and convert to dict
        default_global = GlobalConfig()
        base_dict = asdict(default_global)

        # Add legacy fields needed for compatibility
        legacy_defaults = {
            "save_dir": "downloads",
            "headless": True,
            "max_retries": 3,
            "use_dynamic_delay": True,
            "base_url": "https://www.cninfo.com.cn",
            "page_load_strategy": "eager",
            "timeout": {
                "page_load": 30,
                "element_wait": 30,
                "download": 180,
                "script": 30,
            },
            "selectors": {
                "detail_links": "//a[contains(@href, '/new/disclosure/detail')]",
                "download_button": "//button[contains(., '公告下载')]",
                "next_page_button": "//button[contains(@class, 'el-pagination__next')]",
                "table_element": "//table[contains(@class, 'el-table__body')]",
            },
            "files": {
                "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
                "mapping_file": "stock_orgid_mapping.json",
                "log_dir": "logs",
            },
            # Map browser config
            "browser": base_dict["browser"],
            "anti_crawler": base_dict["anti_crawler"],
            "download": base_dict["download"],
            "logging": base_dict["logging"],
            "pages": [
                {"name": "Research", "suffix": "research", "allowed_keywords": None},
                {
                    "name": "Periodic Reports",
                    "suffix": "periodicReports",
                    "allowed_keywords": None,
                },
                {
                    "name": "Latest Announcements",
                    "suffix": "latestAnnouncement",
                    "allowed_keywords": ["招股说明书"],
                },
            ],
        }
        return legacy_defaults

    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration

        Returns:
            Dict[str, Any]: Complete configuration dictionary
        """
        if self._config_path is None and not self._config:
            self.load_config()

        # Return deep copy to prevent external modification
        import copy
        return copy.deepcopy(self._config)

    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get environment variable overrides"""
        import os
        overrides = {}

        # Browser strategy override
        browser_strategy = os.getenv("DOWNLOADER_BROWSER_STRATEGY")
        if browser_strategy:
            overrides["browser_strategy"] = browser_strategy

        # Timeout override
        timeout = os.getenv("DOWNLOADER_TIMEOUT")
        if timeout:
            try:
                overrides["timeout"] = int(timeout)
            except ValueError:
                pass

        # Max pages override
        max_pages = os.getenv("DOWNLOADER_MAX_PAGES")
        if max_pages:
            try:
                overrides["max_pages"] = int(max_pages)
            except ValueError:
                pass

        # Anti-crawler switch
        anti_crawler = os.getenv("DOWNLOADER_ANTI_CRAWLER")
        if anti_crawler:
            overrides["anti_crawler_enabled"] = anti_crawler.lower() in (
                "true",
                "1",
                "yes",
            )

        return overrides

    def reset_config(self) -> None:
        """Reset to default configuration"""
        self._config = self.get_default_config()
        if self._config_path:
            self.save_config()

    @property
    def config(self) -> Dict[str, Any]:
        """Get complete configuration"""
        if not self._config:
            self.load_config()
        return self._config.copy()

    @property
    def config_path(self) -> Optional[str]:
        """Get configuration file path"""
        return self._config_path

    def get_base_url(self) -> str:
        """Get base URL"""
        return self.get("base_url", "https://www.cninfo.com.cn")

    def get_timeout(self, timeout_type: str = "page_load") -> int:
        """Get timeout value"""
        return self.get(f"timeout.{timeout_type}", 60)

    def get_selector(self, selector_name: str) -> str:
        """Get selector"""
        return self.get(f"selectors.{selector_name}", "")

    def get_user_agents(self) -> list:
        """Get user agent list"""
        return self.get(
            "webdriver.user_agents",
            [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ],
        )

    def get_max_retries(self) -> int:
        """Get max retry count"""
        return self.get("retries.max_attempts", 3)

    def is_headless(self) -> bool:
        """Whether to use headless mode"""
        return self.get("webdriver.headless", True)

    def get_window_size(self) -> str:
        """Get window size"""
        return self.get("webdriver.window_size", "1920,1080")

    def get_page_load_strategy(self) -> str:
        """Get page load strategy"""
        return self.get("page_load_strategy", "eager")

    def get_parallel_download_config(self) -> Dict[str, Any]:
        """Get parallel download configuration"""
        return self.get(
            "parallel_download",
            {"enabled": False, "max_workers": 3, "batch_size": 50, "task_timeout": 300},
        )

    def get_proxy_config(self) -> Dict[str, Any]:
        """Get proxy configuration"""
        return self.get("proxy_management", {"enabled": False, "pools": {}})

    def get_anti_crawler_config(self) -> Dict[str, Any]:
        """Get anti-crawler configuration"""
        return self.get("enhanced_anti_crawler", {"enabled": True, "level": "high"})

    def is_parallel_download_enabled(self) -> bool:
        """Check if parallel download is enabled"""
        config = self.get_parallel_download_config()
        return config.get("enabled", False)

    def is_proxy_enabled(self) -> bool:
        """Check if proxy is enabled"""
        config = self.get_proxy_config()
        return config.get("enabled", False)

    def get_max_workers(self) -> int:
        """Get max worker threads"""
        config = self.get_parallel_download_config()
        return config.get("max_workers", 3)

    def use_constants(self, key: str) -> Any:
        """Use configuration constants"""
        constant_map = {
            "base_url": ConfigConstants.get_base_url(),
            "timeouts": ConfigConstants.DEFAULT_TIMEOUTS,
            "selectors": ConfigConstants.SELECTORS,
            "test_data": ConfigConstants.TEST_DATA,
            "user_agents": ConfigConstants.USER_AGENTS,
            "INVALID_FILENAME_CHARS": ConfigConstants.INVALID_FILENAME_CHARS,
        }

        if "." in key:
            parent, child = key.split(".", 1)
            parent_val = constant_map.get(parent)
            if isinstance(parent_val, dict):
                return parent_val.get(child)
            return None
        else:
            return constant_map.get(key)
