#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版下载器工厂模块
提供统一的下载器创建和管理接口，支持新的统一下载器架构
"""

from typing import Any, Dict, List, Optional, Type, Union, cast

from src.adapters.legacy_downloader_adapter import (
    DownloadServiceV2Adapter,
    RefactoredDownloaderAdapter,
)
from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.interfaces.downloader_interface import IDownloader
from src.services.unified_downloader import UnifiedDownloader


class EnhancedDownloaderFactory:
    """增强版下载器工厂类"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化下载器工厂

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)

        # 下载器注册表
        self._downloaders: Dict[str, Type[IDownloader]] = {
            "unified": UnifiedDownloader,
        }

        # 遗留适配器注册表（向后兼容）
        self._legacy_adapters: Dict[str, Type] = {
            "download_service_v2": DownloadServiceV2Adapter,
            "refactored": RefactoredDownloaderAdapter,
            "improved": DownloadServiceV2Adapter,
        }

        # 默认配置
        self.default_downloader_type = "unified"
        self.legacy_mode = False

        self.logger.info("增强版下载器工厂初始化完成")

    def create_downloader(
        self,
        downloader_type: str = "unified",
        use_legacy_adapter: bool = False,
        **kwargs,
    ) -> IDownloader:
        """
        创建下载器实例

        Args:
            downloader_type: 下载器类型
            use_legacy_adapter: 是否使用遗留适配器
            **kwargs: 下载器初始化参数

        Returns:
            IDownloader: 下载器实例

        Raises:
            ValueError: 不支持的下载器类型
        """
        try:
            # 自动检测是否需要使用遗留适配器
            if (
                downloader_type in self._legacy_adapters
                and downloader_type != "unified"
            ):
                use_legacy_adapter = True

            # 决定使用哪种实现
            if self.legacy_mode or use_legacy_adapter:
                # 使用适配器
                return self._create_legacy_adapter(downloader_type, **kwargs)
            else:
                # 使用统一下载器
                return self._create_unified_downloader(downloader_type, **kwargs)

        except Exception as e:
            self.logger.error(f"创建下载器失败: {e}")
            raise

    def _create_unified_downloader(self, downloader_type: str, **kwargs) -> IDownloader:
        """创建统一下载器"""
        # 允许明确的 'unified' 类型
        if downloader_type == "unified":
            pass
        # 允许已知的遗留类型（如果在非遗留模式下被请求，我们映射到 unified）
        elif downloader_type in ["cninfo", "download_service"]:
            self.logger.info(f"将遗留类型 '{downloader_type}' 映射到 'unified'")
        else:
            # 对于完全未知的类型，抛出异常
            raise ValueError(f"不支持的下载器类型: {downloader_type}")

        # 合并配置
        config = self._merge_config(**kwargs)

        # 创建统一下载器
        return UnifiedDownloader(config)

    def _create_legacy_adapter(self, downloader_type: str, **kwargs) -> IDownloader:
        """创建遗留适配器"""
        if downloader_type not in self._legacy_adapters:
            # Fallback for removed adapters: map to UnifiedDownloader directly
            if downloader_type in ["cninfo", "download_service"]:
                self.logger.warning(f"Adapter '{downloader_type}' is removed. Using UnifiedDownloader instead.")
                config = self._merge_config(**kwargs)
                return UnifiedDownloader(config)

            available_types = list(self._legacy_adapters.keys())
            raise ValueError(
                f"不支持的适配器类型: {downloader_type}. "
                f"可用类型: {available_types}"
            )

        adapter_class = self._legacy_adapters[downloader_type]
        return cast(IDownloader, adapter_class(**kwargs))

    def _merge_config(self, **kwargs) -> Dict[str, Any]:
        """合并配置参数"""
        # 从配置管理器获取基础配置
        base_config = self.config_manager.get_all_config()  # type: ignore[no-any-call]

        # 合并环境变量覆盖
        env_overrides = self.config_manager.get_environment_overrides()  # type: ignore[attr-defined]

        # 合并所有配置
        final_config = {}

        # 1. 基础配置
        if "config" in kwargs:
            final_config.update(kwargs["config"])
        else:
            final_config.update(base_config.get("config", {}))

        # 2. 其他配置类别
        for category in ["browser", "anti_crawler", "download", "logging"]:
            if category in kwargs:
                final_config.update(kwargs[category])
            else:
                final_config.update(base_config.get(category, {}))

        # 3. 环境变量覆盖
        final_config.update(env_overrides)

        # 4. 直接参数覆盖 (kwargs other than config)
        for k, v in kwargs.items():
            if k not in ["config"] and k not in final_config:
                final_config[k] = v

        return final_config

    def create_default_downloader(self, **kwargs) -> IDownloader:
        """
        创建默认下载器

        Args:
            **kwargs: 下载器初始化参数

        Returns:
            IDownloader: 默认下载器实例
        """
        return self.create_downloader(
            self.default_downloader_type, use_legacy_adapter=self.legacy_mode, **kwargs
        )

    def register_downloader(
        self,
        downloader_type: str,
        downloader_class: Type[IDownloader],
        is_legacy: bool = False,
    ) -> None:
        """
        注册新的下载器类型

        Args:
            downloader_type: 下载器类型名称
            downloader_class: 下载器类
            is_legacy: 是否为遗留适配器
        """
        if is_legacy:
            self._legacy_adapters[downloader_type] = downloader_class
        else:
            self._downloaders[downloader_type] = downloader_class

        self.logger.info(f"注册下载器类型: {downloader_type} (遗留适配器: {is_legacy})")

    def list_available_downloaders(self) -> Union[List[str], Dict[str, Dict[str, Any]]]:
        """
        列出所有可用的下载器类型
        为保持兼容性，返回一个包含所有可用类型名称的列表
        """
        return list(self._downloaders.keys()) + list(self._legacy_adapters.keys())

    def get_downloader_info(self, downloader_type: str) -> Dict[str, Any]:
        """
        获取下载器详细信息

        Args:
            downloader_type: 下载器类型

        Returns:
            Dict[str, Any]: 下载器信息
        """
        # 检查统一下载器
        if downloader_type in self._downloaders:
            downloader_class = self._downloaders[downloader_type]
            return {
                "type": downloader_type,
                "class_name": downloader_class.__name__,
                "module": downloader_class.__module__,
                "description": "统一下载器",
                "is_legacy": False,
                "is_default": downloader_type == self.default_downloader_type,
            }

        # 检查遗留适配器
        if downloader_type in self._legacy_adapters:
            adapter_class = self._legacy_adapters[downloader_type]
            return {
                "type": downloader_type,
                "class_name": adapter_class.__name__,
                "module": adapter_class.__module__,
                "description": "遗留适配器",
                "is_legacy": True,
                "is_default": downloader_type == self.default_downloader_type,
            }

        return {}

    def create_legacy_adapter(self, downloader_type: str, **kwargs) -> IDownloader:
        """
        创建遗留适配器

        Args:
            downloader_type: 适配器类型
            **kwargs: 适配器初始化参数

        Returns:
            IDownloader: 适配器实例
        """
        return self.create_downloader(
            downloader_type, use_legacy_adapter=True, **kwargs
        )

    def compare_downloaders(self) -> Dict[str, Any]:
        """
        比较不同下载器的特性

        Returns:
            Dict[str, Any]: 下载器比较信息
        """
        comparison = {}
        available_types = list(self._downloaders.keys()) + list(
            self._legacy_adapters.keys()
        )
        for downloader_type in available_types:
            info = self.get_downloader_info(downloader_type)
            comparison[downloader_type] = info

        return comparison

    def create_unified_downloader(self, **kwargs) -> IDownloader:
        """
        创建统一下载器（向后兼容接口）
        """
        return self._create_unified_downloader("unified", **kwargs)

    def enable_legacy_mode(self, enabled: bool = True) -> None:
        """
        启用或禁用遗留模式

        Args:
            enabled: 是否启用遗留模式
        """
        self.legacy_mode = enabled
        self.logger.info(f"遗留模式已{'启用' if enabled else '禁用'}")


# For backward compatibility, keep the old factory class
class DownloaderFactory(EnhancedDownloaderFactory):
    """
    下载器工厂类（向后兼容）
    """

    pass  # 所有功能都在 EnhancedDownloaderFactory 中实现


# 全局工厂实例
downloader_factory = EnhancedDownloaderFactory()
