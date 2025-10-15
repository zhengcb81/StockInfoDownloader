#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
下载器简化测试
测试核心下载器的基本功能，与实际代码结构匹配
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.downloader import DownloadService


class TestDownloaderSimplified:
    """下载器简化测试"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, 'downloads')

        # 创建临时映射文件
        self.mapping_file = os.path.join(self.temp_dir, 'test_mapping.json')
        test_mapping = {
            "300470": {
                "orgId": "9900023856",
                "name": "中密控股"
            }
        }

        import json
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.MappingManager')
    def test_downloader_initialization(self, mock_mapping_manager, mock_browser_manager):
        """测试下载器初始化"""
        # 设置mock
        mock_mapping_instance = MagicMock()
        mock_mapping_manager.return_value = mock_mapping_instance

        mock_browser_instance = MagicMock()
        mock_browser_manager.return_value = mock_browser_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证下载器属性
        assert downloader.save_dir == Path(self.save_dir)
        assert downloader.mapping_file == self.mapping_file
        assert downloader.mapping_manager == mock_mapping_instance
        assert downloader.browser_strategy_manager == mock_browser_instance

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.MappingManager')
    def test_downloader_with_default_config(self, mock_mapping_manager, mock_browser_manager):
        """测试下载器默认配置"""
        # 设置mock
        mock_mapping_instance = MagicMock()
        mock_mapping_manager.return_value = mock_mapping_instance

        mock_browser_instance = MagicMock()
        mock_browser_manager.return_value = mock_browser_instance

        # 使用默认配置创建下载器
        downloader = DownloadService()

        # 验证默认配置
        assert downloader.save_dir == Path("downloads")
        assert downloader.mapping_file == "stock_orgid_mapping.json"

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.MappingManager')
    def test_downloader_directory_creation(self, mock_mapping_manager, mock_browser_manager):
        """测试下载器目录创建"""
        # 设置mock
        mock_mapping_instance = MagicMock()
        mock_mapping_manager.return_value = mock_mapping_instance

        mock_browser_instance = MagicMock()
        mock_browser_manager.return_value = mock_browser_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证目录已创建
        assert downloader.save_dir.exists()
        assert downloader.save_dir.is_dir()

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.MappingManager')
    def test_downloader_mapping_manager_integration(self, mock_mapping_manager, mock_browser_manager):
        """测试下载器与映射管理器集成"""
        # 设置mock
        mock_mapping_instance = MagicMock()
        mock_mapping_manager.return_value = mock_mapping_instance

        mock_browser_instance = MagicMock()
        mock_browser_manager.return_value = mock_browser_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证映射管理器被正确初始化
        mock_mapping_manager.assert_called_once_with(self.mapping_file)

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.MappingManager')
    def test_downloader_browser_manager_integration(self, mock_mapping_manager, mock_browser_manager):
        """测试下载器与浏览器管理器集成"""
        # 设置mock
        mock_mapping_instance = MagicMock()
        mock_mapping_manager.return_value = mock_mapping_instance

        mock_browser_instance = MagicMock()
        mock_browser_manager.return_value = mock_browser_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证浏览器管理器被正确初始化
        mock_browser_manager.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])