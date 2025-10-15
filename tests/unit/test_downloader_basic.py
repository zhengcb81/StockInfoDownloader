#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
下载器基础功能测试
测试核心下载器的基本功能
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.downloader import DownloadService
from src.core.config import ConfigManager
from src.data.mapping import MappingManager


class TestDownloaderBasic:
    """下载器基础功能测试"""

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
            },
            "000001": {
                "orgId": "9900000001",
                "name": "平安银行"
            }
        }

        import json
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_downloader_initialization(self, mock_anti_crawler, mock_driver_manager):
        """测试下载器初始化"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证下载器属性
        assert str(downloader.save_dir) == self.save_dir
        assert downloader.mapping_file == self.mapping_file
        assert downloader.driver_manager is not None
        assert downloader.anti_crawler is not None

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_downloader_with_config_file(self, mock_anti_crawler, mock_driver_manager):
        """测试带配置文件的下载器初始化"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        # 创建配置文件路径
        config_file = os.path.join(self.temp_dir, 'test_config.json')

        # 创建测试配置文件
        import json
        test_config = {
            "browser": {
                "type": "selenium",
                "headless": True
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        # 创建下载器
        downloader = DownloadService(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            config_file=config_file
        )

        # 验证下载器属性
        assert str(downloader.save_dir) == self.save_dir
        assert downloader.mapping_file == self.mapping_file

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_downloader_methods_exist(self, mock_anti_crawler, mock_driver_manager):
        """测试下载器方法存在性"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 验证方法存在
        assert hasattr(downloader, 'download_stock_pdfs')
        assert hasattr(downloader, 'clean_filename')
        assert hasattr(downloader, 'get_org_id')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])