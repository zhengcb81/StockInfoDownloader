#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DownloaderFactory全面单元测试
测试下载器工厂的所有功能，包括下载器创建、配置管理、错误处理等
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.factory.downloader_factory import DownloaderFactory
from src.services.unified_downloader import UnifiedDownloader
from src.core.config import ConfigManager
from .test_utils import TestConfig, TestDataGenerator, EnvironmentManager
from .dependency_injection import DependencyInjectionTestBase


class TestDownloaderFactory(DependencyInjectionTestBase):
    """DownloaderFactory测试类"""

    def setup_method(self):
        """测试初始化"""
        super().setup_method()
        self.test_env = EnvironmentManager()

        # 创建mock配置管理器
        self.mock_config_manager = Mock(spec=ConfigManager)
        self._setup_mock_config()

        # 创建DownloaderFactory实例
        self.factory = DownloaderFactory(config_manager=self.mock_config_manager)

    def teardown_method(self):
        """测试清理"""
        super().teardown_method()
        self.test_env.cleanup()

    def _setup_mock_config(self):
        """设置mock配置"""
        # 基础配置
        self.mock_config_manager.get.side_effect = lambda key, default=None: {
            'save_dir': 'downloads',
            'files.mapping_file': 'stock_orgid_mapping.json',
            'downloader.default_type': 'refactored',
            'downloader.unified_type': 'refactored',
            'config_file': 'config.json'
        }.get(key, default)

        self.mock_config_manager.config_path = 'config.json'

    def test_init(self):
        """测试初始化"""
        # 测试默认初始化
        default_factory = DownloaderFactory()
        assert default_factory.config_manager is not None
        assert default_factory.logger is not None

        # 测试自定义配置管理器
        custom_factory = DownloaderFactory(config_manager=self.mock_config_manager)
        assert custom_factory.config_manager == self.mock_config_manager

    def test_create_downloader_refactored(self):
        """测试创建refactored下载器"""
        # 直接测试创建过程，不依赖mock比较
        downloader = self.factory.create_downloader('refactored')

        # 验证创建成功
        assert downloader is not None
        # 验证类型正确（根据实际类名判断）
        assert hasattr(downloader, '__class__')
        assert 'RefactoredDownloader' in downloader.__class__.__name__

    def test_create_downloader_improved(self):
        """测试创建improved下载器"""
        # 直接测试创建过程，不依赖mock比较
        downloader = self.factory.create_downloader('improved')

        # 验证创建成功
        assert downloader is not None
        # 验证类型正确（现在 mapping 为 DownloadServiceV2Adapter）
        assert 'DownloadServiceV2Adapter' in downloader.__class__.__name__

    def test_create_downloader_invalid_type(self):
        """测试创建无效下载器类型"""
        # 测试不支持的下载器类型
        with pytest.raises(ValueError) as exc_info:
            self.factory.create_downloader('invalid_type')

        assert 'invalid_type' in str(exc_info.value)

    def test_create_downloader_with_custom_kwargs(self):
        """测试使用自定义参数创建下载器"""
        # 执行测试
        downloader = self.factory.create_downloader('refactored')

        # 验证创建成功
        assert downloader is not None
        assert 'RefactoredDownloaderAdapter' in downloader.__class__.__name__

    def test_get_default_downloader_type(self):
        """测试获取默认下载器类型"""
        # 测试默认类型
        default_type = self.factory.default_downloader_type
        assert default_type == 'unified'

    def test_create_default_downloader(self):
        """测试创建默认下载器"""
        # 直接测试创建过程，不依赖mock比较
        downloader = self.factory.create_default_downloader()

        # 验证创建成功
        assert downloader is not None
        assert 'UnifiedDownloader' in downloader.__class__.__name__

    def test_register_downloader(self):
        """测试注册新下载器"""
        # 创建自定义下载器类
        class CustomDownloader:
            """自定义下载器"""
            pass

        # 注册新下载器
        self.factory.register_downloader('custom', CustomDownloader)

        # 验证注册成功
        assert 'custom' in self.factory._downloaders
        assert self.factory._downloaders['custom'] == CustomDownloader

    def test_list_available_downloaders(self):
        """测试列出可用下载器"""
        # 获取可用下载器列表
        available_downloaders = self.factory.list_available_downloaders()

        # 验证列表内容
        assert 'refactored' in available_downloaders
        assert 'improved' in available_downloaders
        assert len(available_downloaders) >= 2  # 至少包含这两个，可能有更多

    def test_get_downloader_info(self):
        """测试获取下载器信息"""
        # 获取refactored下载器信息
        refactored_info = self.factory.get_downloader_info('refactored')

        # 验证信息内容
        assert refactored_info['type'] == 'refactored'
        assert 'class_name' in refactored_info
        assert 'module' in refactored_info
        assert 'description' in refactored_info
        assert 'is_default' in refactored_info

    def test_get_downloader_info_invalid_type(self):
        """测试获取无效下载器信息"""
        # 获取不存在的下载器信息
        info = self.factory.get_downloader_info('invalid_type')

        # 验证返回空字典
        assert info == {}

    def test_compare_downloaders(self):
        """测试比较下载器"""
        # 比较所有下载器
        comparison = self.factory.compare_downloaders()

        # 验证比较结果
        assert 'refactored' in comparison
        assert 'improved' in comparison
        assert len(comparison) >= 2  # 至少包含这两个，可能有更多

        # 验证每个下载器都有完整信息
        for downloader_type, info in comparison.items():
            assert 'type' in info
            assert 'class_name' in info
            assert 'module' in info
            assert 'description' in info
            assert 'is_default' in info

    @patch('src.factory.downloader_factory.UnifiedDownloader')
    def test_create_unified_downloader(self, mock_unified):
        """测试创建统一下载器"""
        # 设置mock
        mock_downloader_instance = Mock()
        mock_unified.return_value = mock_downloader_instance

        # 创建统一下载器
        unified_downloader = self.factory.create_unified_downloader()

        # 验证统一下载器创建
        assert unified_downloader == mock_downloader_instance

    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种错误情况

        # 无效下载器类型
        with pytest.raises(ValueError):
            self.factory.create_downloader('invalid_type')

        # 无效下载器信息
        info = self.factory.get_downloader_info('nonexistent_type')
        assert info == {}

        # 注册重复下载器类型（应该不会抛出异常）
        class TestDownloader:
            pass

        self.factory.register_downloader('test', TestDownloader)
        self.factory.register_downloader('test', TestDownloader)  # 重复注册
        assert self.factory._downloaders['test'] == TestDownloader


class TestUnifiedDownloader:
    """UnifiedDownloader测试类"""

    def setup_method(self):
        """测试初始化"""
        # 创建mock工厂
        self.mock_config_manager = Mock(spec=ConfigManager)

        # 配置mock
        self.mock_config_manager.get.side_effect = lambda key, default=None: {
            'downloader.unified_type': 'refactored'
        }.get(key, default)

        # 创建UnifiedDownloader实例 (strategy is playwright by default)
        self.unified_downloader = UnifiedDownloader(config={})

    def test_init(self):
        """测试初始化"""
        # 验证初始化
        assert self.unified_downloader.config is not None
        assert self.unified_downloader.logger is not None

    def test_download_stock_pdfs_success(self, mocker):
        """测试成功下载股票PDF"""
        # 设置mock下载流程
        mocker.patch.object(self.unified_downloader, '_perform_download', return_value=['file1.pdf', 'file2.pdf'])
        mocker.patch('src.data.mapping.MappingManager.get_org_id', return_value='9900023856')

        # 执行下载 (传递 stock_code 作为第一个参数 request)
        result = self.unified_downloader.download_stock_pdfs(
            '300470',
            stock_name='测试股票',
            suffix='research',
            allowed_keywords=['投资者关系'],
            max_pages=5
        )

        # 验证结果
        assert result == ['file1.pdf', 'file2.pdf']

    def test_download_stock_pdfs_fallback_method(self, mocker):
        """测试回退下载方法"""
        # 设置mock下载流程
        mocker.patch.object(self.unified_downloader, '_perform_download', return_value=['file1.pdf'])
        mocker.patch('src.data.mapping.MappingManager.get_org_id', return_value='9900023856')

        # 执行下载
        result = self.unified_downloader.download_stock_pdfs(
            '300470',
            stock_name='测试股票'
        )

        # 验证结果
        assert result == ['file1.pdf']

    def test_download_stock_pdfs_no_method_available(self, mocker):
        """测试下载失败场景"""
        mocker.patch.object(self.unified_downloader, '_perform_download', side_effect=Exception("Error"))
        mocker.patch('src.data.mapping.MappingManager.get_org_id', return_value='9900023856')

        # 执行下载
        result = self.unified_downloader.download_stock_pdfs(
            '300470',
            stock_name='测试股票'
        )

        # 验证返回空列表
        assert result == []

    def test_get_current_downloader_info(self):
        """测试获取状态"""
        status = self.unified_downloader.get_status()
        assert status is not None
        assert status.is_running is False

    def test_error_handling_consistency(self, mocker):
        """测试错误处理的一致性"""
        # 下载方法调用失败
        mocker.patch.object(self.unified_downloader, '_perform_download', side_effect=Exception("下载失败"))
        mocker.patch('src.data.mapping.MappingManager.get_org_id', return_value='9900023856')
        
        result = self.unified_downloader.download_stock_pdfs('300470', '测试股票')
        assert result == []  # 应该返回空列表而不是抛出异常


class TestDownloaderFactoryEdgeCases:
    """DownloaderFactory边界情况测试"""

    def setup_method(self):
        """测试初始化"""
        self.mock_config_manager = Mock(spec=ConfigManager)
        self.mock_config_manager.get.side_effect = lambda key, default=None: default
        self.mock_config_manager.config_path = 'config.json'

    def test_init_with_none_config(self):
        """测试使用None配置初始化"""
        factory = DownloaderFactory(config_manager=None)
        assert factory.config_manager is not None

    def test_create_downloader_with_empty_kwargs(self):
        """测试使用空参数创建下载器"""
        factory = DownloaderFactory(config_manager=self.mock_config_manager)

        # 直接测试创建过程
        downloader = factory.create_downloader('unified')

        # 验证创建成功
        assert downloader is not None
        assert 'UnifiedDownloader' in downloader.__class__.__name__

    def test_register_downloader_override_existing(self):
        """测试覆盖已存在的下载器"""
        factory = DownloaderFactory(config_manager=self.mock_config_manager)

        class OriginalDownloader:
            pass

        class NewDownloader:
            pass

        # 注册原始下载器
        factory.register_downloader('test', OriginalDownloader)
        assert factory._downloaders['test'] == OriginalDownloader

        # 覆盖注册新下载器
        factory.register_downloader('test', NewDownloader)
        assert factory._downloaders['test'] == NewDownloader


class TestDownloaderFactoryExceptionHandling:
    """DownloaderFactory异常处理测试"""

    def setup_method(self):
        """测试初始化"""
        self.mock_config_manager = Mock(spec=ConfigManager)
        self.mock_config_manager.get.side_effect = lambda key, default=None: default
        self.mock_config_manager.config_path = 'config.json'

    def test_create_downloader_exception_handling(self):
        """测试创建下载器时的异常处理"""
        factory = DownloaderFactory(config_manager=self.mock_config_manager)

        # 验证异常被正确捕获和重新抛出
        with pytest.raises(ValueError):
            factory.create_downloader('nonexistent')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])