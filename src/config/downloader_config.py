#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器配置管理 (已废弃)
请使用 src.core.config.ConfigManager

此模块现作为 ConfigManager 的适配层，以保持向后兼容性。
"""

import warnings
from dataclasses import asdict
from typing import Any, Dict, Optional, Union
from pathlib import Path

from src.core.config import ConfigManager
# Re-export dataclasses for compatibility
from src.core.config_definitions import (
    BrowserConfig,
    AntiCrawlerConfig,
    DownloadConfig,
    LoggingConfig
)
from src.core.logger import get_logger

logger = get_logger(__name__)

class DownloaderConfigManager:
    """
    下载器配置管理器 (已废弃)
    
    .. deprecated:: 2.0.0
       使用 `src.core.config.ConfigManager` 替代。
    """

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        warnings.warn(
            "DownloaderConfigManager is deprecated. Use src.core.config.ConfigManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.logger = logger
        # Delegate to the singleton ConfigManager
        # Convert Path to str for ConfigManager compatibility
        config_file_str = str(config_file) if config_file is not None else None
        self._manager = ConfigManager(config_file_str)
        
        # Expose properties for compatibility
        self.browser = self._manager.browser_config
        self.anti_crawler = self._manager.anti_crawler_config
        self.download = self._manager.download_config
        # logging config is in manager but logging attribute name conflicts with logging module commonly
        # mapping it manually
        # self.logging = self._manager.logging_config  (ConfigManager needs this accessor)

    @property
    def logging(self):
        # Access internal global config directly or add accessor to ConfigManager
        # Using internal property for now to avoid modifying ConfigManager interface too much
        return self._manager._global_config.logging

    @logging.setter
    def logging(self, value):
        self._manager._global_config.logging = value

    def load_config(self) -> None:
        """从文件加载配置"""
        self._manager.load_config()

    def save_config(self) -> None:
        """保存配置到文件"""
        self._manager.save_config()

    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return asdict(self.browser)

    def get_anti_crawler_config(self) -> Dict[str, Any]:
        """获取反爬虫配置"""
        return asdict(self.anti_crawler)

    def get_download_config(self) -> Dict[str, Any]:
        """获取下载配置"""
        return asdict(self.download)

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return asdict(self.logging)

    # Update methods
    def update_browser_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.browser, key):
                setattr(self.browser, key, value)
        self.save_config()

    def update_anti_crawler_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.anti_crawler, key):
                setattr(self.anti_crawler, key, value)
        self.save_config()

    def update_download_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.download, key):
                setattr(self.download, key, value)
        self.save_config()

    def get_all_config(self) -> Dict[str, Any]:
        return {
            "browser": asdict(self.browser),
            "anti_crawler": asdict(self.anti_crawler),
            "download": asdict(self.download),
            "logging": asdict(self.logging),
        }

    def reset_to_defaults(self) -> None:
        self._manager.reset_config()
        # Refresh references
        self.browser = self._manager.browser_config
        self.anti_crawler = self._manager.anti_crawler_config
        self.download = self._manager.download_config

    def validate_config(self) -> bool:
        # Simple validation logic migration
        try:
            if self.browser.strategy not in ["playwright", "selenium"]:
                return False
            if self.browser.timeout <= 0:
                return False
            if self.download.max_pages <= 0:
                return False
            return True
        except (AttributeError, TypeError):
            # Config object may not have expected attributes
            return False

    def get_environment_overrides(self) -> Dict[str, Any]:
        """获取环境变量覆盖的配置"""
        return self._manager.get_environment_overrides()

# Global instance for compatibility
config_manager = DownloaderConfigManager()
