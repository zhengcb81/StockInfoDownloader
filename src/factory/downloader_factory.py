#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版下载器工厂模块
提供统一的下载器创建和管理接口，支持新的统一下载器架构
"""

from typing import Dict, Any, Optional, Type, List, Union
from pathlib import Path
import json

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.config.downloader_config import config_manager
from src.interfaces.downloader_interface import IDownloader
from src.services.unified_downloader import UnifiedDownloader
from src.adapters.legacy_downloader_adapter import (
    CninfoDownloaderAdapter,
    DownloadServiceV1Adapter,
    DownloadServiceV2Adapter,
    RefactoredDownloaderAdapter,
    create_legacy_adapter,
    UniversalDownloaderWrapper
)


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
            'unified': UnifiedDownloader,
        }

        # 遗留适配器注册表（向后兼容）
        self._legacy_adapters: Dict[str, Type] = {
            'cninfo': CninfoDownloaderAdapter,
            'download_service': DownloadServiceV1Adapter,
            'download_service_v2': DownloadServiceV2Adapter,
            'refactored': RefactoredDownloaderAdapter,
            'improved': DownloadServiceV2Adapter,
        }

        # 默认配置
        self.default_downloader_type = 'unified'
        self.legacy_mode = False

        self.logger.info("增强版下载器工厂初始化完成")

    def create_downloader(
        self,
        downloader_type: str = 'unified',
        use_legacy_adapter: bool = False,
        **kwargs
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
            if downloader_type in self._legacy_adapters and downloader_type != 'unified':
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
        if downloader_type != 'unified':
            raise ValueError(f"统一下载器只支持 'unified' 类型，收到: {downloader_type}")

        # 合并配置
        config = self._merge_config(**kwargs)

        # 创建统一下载器
        return UnifiedDownloader(config)

    def _create_legacy_adapter(self, downloader_type: str, **kwargs) -> IDownloader:
        """创建遗留适配器"""
        if downloader_type not in self._legacy_adapters:
            available_types = list(self._legacy_adapters.keys())
            raise ValueError(f"不支持的适配器类型: {downloader_type}. "
                           f"可用类型: {available_types}")

        adapter_class = self._legacy_adapters[downloader_type]
        return adapter_class(**kwargs)

    def _merge_config(self, **kwargs) -> Dict[str, Any]:
        """合并配置参数"""
        # 从配置管理器获取基础配置
        base_config = config_manager.get_all_config()

        # 合并环境变量覆盖
        env_overrides = config_manager.get_environment_overrides()

        # 合并所有配置
        final_config = {}

        # 1. 基础配置
        if 'config' in kwargs:
            final_config.update(kwargs['config'])
        else:
            final_config.update(base_config.get('config', {}))

        # 2. 其他配置类别
        for category in ['browser', 'anti_crawler', 'download', 'logging']:
            if category in kwargs:
                final_config.update(kwargs[category])
            else:
                final_config.update(base_config.get(category, {}))

        # 3. 环境变量覆盖
        final_config.update(env_overrides)

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
            self.default_downloader_type,
            use_legacy_adapter=self.legacy_mode,
            **kwargs
        )

    def register_downloader(
        self,
        downloader_type: str,
        downloader_class: Type[IDownloader],
        is_legacy: bool = False
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
                'type': downloader_type,
                'class_name': downloader_class.__name__,
                'module': downloader_class.__module__,
                'description': '统一下载器',
                'is_legacy': False,
                'is_recommended': True,
                'is_default': downloader_type == self.default_downloader_type,
                'features': self._get_downloader_features(downloader_class)
            }

        # 检查遗留适配器
        if downloader_type in self._legacy_adapters:
            adapter_class = self._legacy_adapters[downloader_type]
            return {
                'type': downloader_type,
                'class_name': adapter_class.__name__,
                'module': adapter_class.__module__,
                'description': '遗留适配器',
                'is_legacy': True,
                'is_recommended': False,
                'is_default': downloader_type == self.default_downloader_type,
                'original_class': adapter_class.__name__.replace('Adapter', '')
            }

        return {}

    def _get_downloader_features(self, downloader_class: Type) -> List[str]:
        """获取下载器特性列表"""
        features = []

        # 通过类名和模块推断特性
        class_name = downloader_class.__name__.lower()
        module_path = downloader_class.__module__

        if 'unified' in class_name:
            features.extend([
                '统一下载器接口',
                '策略模式支持',
                '服务分离架构',
                '配置管理集成',
                '监控和日志'
            ])

        if 'v2' in class_name or 'download_service_v2' in module_path:
            features.extend([
                '策略模式',
                'Playwright支持',
                '性能优化',
                '增强错误处理'
            ])

        return features

    def get_recommended_downloader(self) -> str:
        """
        获取推荐的下载器类型

        Returns:
            str: 推荐的下载器类型
        """
        return 'unified'

    def create_legacy_adapter(
        self,
        downloader_type: str,
        **kwargs
    ) -> IDownloader:
        """
        创建遗留适配器

        Args:
            downloader_type: 适配器类型
            **kwargs: 适配器初始化参数

        Returns:
            IDownloader: 适配器实例
        """
        return self.create_downloader(
            downloader_type,
            use_legacy_adapter=True,
            **kwargs
        )

    def compare_downloaders(self) -> Dict[str, Any]:
        """
        比较不同下载器的特性

        Returns:
            Dict[str, Any]: 下载器比较信息
        """
        comparison = {}
        available_types = list(self._downloaders.keys()) + list(self._legacy_adapters.keys())
        for downloader_type in available_types:
            info = self.get_downloader_info(downloader_type)
            comparison[downloader_type] = info

        return comparison

    def create_recommended_downloader(self, **kwargs) -> IDownloader:
        """
        创建推荐的下载器

        Args:
            **kwargs: 下载器初始化参数

        Returns:
            IDownloader: 推荐的下载器实例
        """
        recommended_type = self.get_recommended_downloader()
        return self.create_downloader(recommended_type, **kwargs)

    def create_unified_downloader(self, **kwargs) -> IDownloader:
        """
        创建统一下载器（向后兼容接口）
        """
        return self._create_unified_downloader('unified', **kwargs)

    def create_downloader_for_scenario(
        self,
        scenario: str,
        **kwargs
    ) -> IDownloader:
        """
        根据场景创建最适合的下载器

        Args:
            scenario: 使用场景
            **kwargs: 下载器初始化参数

        Returns:
            IDownloader: 适合场景的下载器实例
        """
        scenario_mappings = {
            'performance': 'unified',
            'compatibility': 'legacy:download_service',
            'testing': 'unified',
            'legacy': 'legacy:cninfo',
            'default': 'unified'
        }

        downloader_type = scenario_mappings.get(scenario, 'unified')

        # 解析适配器类型
        use_legacy = downloader_type.startswith('legacy:')
        actual_type = downloader_type.replace('legacy:', '') if use_legacy else downloader_type

        return self.create_downloader(
            actual_type,
            use_legacy_adapter=use_legacy,
            **kwargs
        )

    def enable_legacy_mode(self, enabled: bool = True) -> None:
        """
        启用或禁用遗留模式

        Args:
            enabled: 是否启用遗留模式
        """
        self.legacy_mode = enabled
        self.logger.info(f"遗留模式已{'启用' if enabled else '禁用'}")

    def get_factory_info(self) -> Dict[str, Any]:
        """
        获取工厂信息

        Returns:
            Dict[str, Any]: 工厂信息
        """
        return {
            'version': '2.0',
            'default_downloader': self.default_downloader_type,
            'legacy_mode': self.legacy_mode,
            'total_downloaders': len(self._downloaders) + len(self._legacy_adapters),
            'unified_downloaders': len(self._downloaders),
            'legacy_adapters': len(self._legacy_adapters),
            'config_manager_type': type(self.config_manager).__name__,
            'supported_browsers': ['playwright', 'selenium']
        }

    def export_factory_config(self, export_file: Union[str, Path]) -> None:
        """
        导出工厂配置

        Args:
            export_file: 导出文件路径
        """
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            config_data = {
                'factory_info': self.get_factory_info(),
                'downloaders': self.list_available_downloaders(),
                'config_manager_config': config_manager.get_all_config(),
                'export_timestamp': self._get_timestamp()
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"工厂配置已导出到: {export_path}")

        except Exception as e:
            self.logger.error(f"导出工厂配置失败: {e}")

    def import_factory_config(self, import_file: Union[str, Path]) -> None:
        """
        导入工厂配置

        Args:
            import_file: 导入文件路径
        """
        try:
            import_path = Path(import_file)
            if not import_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {import_path}")

            with open(import_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 验证配置
            self._validate_factory_config(config_data)

            # 应用配置
            if 'default_downloader' in config_data.get('factory_info', {}):
                self.default_downloader_type = config_data['factory_info']['default_downloader']

            # 注册自定义下载器
            if 'downloaders' in config_data:
                import importlib
                for downloader_type, info in config_data['downloaders'].items():
                    if isinstance(info, dict) and 'module' in info and 'class_name' in info:
                        try:
                            module = importlib.import_module(info['module'])
                            cls = getattr(module, info['class_name'])
                            self.register_downloader(downloader_type, cls, info.get('is_legacy', False))
                        except Exception as reg_err:
                            self.logger.warning(f"无法注册动态下载器 {downloader_type}: {reg_err}")

            self.logger.info(f"工厂配置已从 {import_path} 导入")

        except Exception as e:
            self.logger.error(f"导入工厂配置失败: {e}")
            raise

    def _validate_factory_config(self, config_data: Dict[str, Any]) -> None:
        """验证工厂配置"""
        required_keys = ['factory_info']
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"配置文件缺少必要字段: {key}")

        factory_info = config_data['factory_info']
        required_info_keys = ['version', 'default_downloader']
        for key in required_info_keys:
            if key not in factory_info:
                raise ValueError(f"工厂信息缺少必要字段: {key}")

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 为了向后兼容，保留旧的工厂类
class DownloaderFactory(EnhancedDownloaderFactory):
    """
    下载器工厂类（向后兼容）
    """
    pass  # 所有功能都在 EnhancedDownloaderFactory 中实现


# 全局工厂实例
downloader_factory = EnhancedDownloaderFactory()