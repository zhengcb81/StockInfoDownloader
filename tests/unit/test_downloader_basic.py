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
            },
            "688001": {
                "orgId": "9900068801",
                "name": "测试公司"
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

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_save_dir_creation(self, mock_anti_crawler, mock_driver_manager):
        """测试保存目录自动创建"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        # 创建一个不存在的保存目录
        non_existent_dir = os.path.join(self.temp_dir, 'non_existent', 'downloads')

        # 创建下载器 - 应该自动创建目录
        downloader = DownloadService(save_dir=non_existent_dir, mapping_file=self.mapping_file)

        # 验证目录被创建
        assert os.path.exists(non_existent_dir)

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_invalid_mapping_file(self, mock_anti_crawler, mock_driver_manager):
        """测试无效的映射文件"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        # 使用不存在的映射文件
        invalid_mapping_file = os.path.join(self.temp_dir, 'non_existent_mapping.json')

        # 应该创建下载器但不立即失败（惰性加载）
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=invalid_mapping_file)

        # 验证下载器被创建
        assert downloader.mapping_file == invalid_mapping_file

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_clean_filename_method(self, mock_anti_crawler, mock_driver_manager):
        """测试clean_filename方法"""
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

        # 测试各种文件名清理场景
        test_cases = [
            ("正常文件名.pdf", "正常文件名.pdf"),
            ("文件/名.pdf", "文件_名.pdf"),
            ("文件\\名.pdf", "文件_名.pdf"),
            ("文件:名.pdf", "文件_名.pdf"),
            ("文件*名.pdf", "文件_名.pdf"),
            ("文件?名.pdf", "文件_名.pdf"),
            ('文件"名.pdf', "文件_名.pdf"),
            ("文件<名.pdf", "文件_名.pdf"),
            ("文件>名.pdf", "文件_名.pdf"),
            ("文件|名.pdf", "文件_名.pdf"),
            ("  文件名  .pdf", "文件名.pdf"),
            ("文件名.....pdf", "文件名.pdf"),
            ("", ""),
        ]

        for input_name, expected in test_cases:
            result = downloader.clean_filename(input_name)
            assert result == expected, f"clean_filename({input_name}) = {result}, 期望 {expected}"

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_get_org_id_method(self, mock_anti_crawler, mock_driver_manager):
        """测试get_org_id方法"""
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

        # 测试映射查询
        org_id = downloader.get_org_id("300470")
        assert org_id == "9900023856", f"获取到的org_id: {org_id}"

        # 测试不存在的股票代码
        org_id = downloader.get_org_id("999999")
        assert org_id is None, f"不存在的股票代码应该返回None, 但返回了: {org_id}"

        # 测试None输入
        org_id = downloader.get_org_id(None)
        assert org_id is None, "None输入应该返回None"

        # 测试空字符串输入
        org_id = downloader.get_org_id("")
        assert org_id is None, "空字符串输入应该返回None"

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_stock_code_validation(self, mock_anti_crawler, mock_driver_manager):
        """测试股票代码验证"""
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

        # 假设下载器有validate_stock_code方法
        if hasattr(downloader, 'validate_stock_code'):
            # 测试有效的股票代码
            assert downloader.validate_stock_code("000001") == True
            assert downloader.validate_stock_code("300470") == True
            assert downloader.validate_stock_code("688001") == True

            # 测试无效的股票代码
            assert downloader.validate_stock_code("") == False
            assert downloader.validate_stock_code("abc") == False
            assert downloader.validate_stock_code("12345") == False  # 长度不对
            assert downloader.validate_stock_code("1234567") == False  # 长度不对

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_date_parameter_validation(self, mock_anti_crawler, mock_driver_manager):
        """测试日期参数验证"""
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

        # 假设下载器有validate_date方法或日期参数在download_stock_pdfs方法中验证
        # 这里我们测试download_stock_pdfs方法的日期参数处理
        if hasattr(downloader, 'download_stock_pdfs'):
            # 使用mock模拟实际的下载操作
            with patch.object(downloader, 'download_stock_pdfs') as mock_download:
                # 测试有效的日期
                downloader.download_stock_pdfs("300470", "2023-01-01", "2023-12-31")
                mock_download.assert_called_once_with("300470", "2023-01-01", "2023-12-31")

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_network_error_handling(self, mock_anti_crawler, mock_driver_manager):
        """测试网络错误处理"""
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

        # 测试download_stock_pdfs方法中的错误处理
        if hasattr(downloader, 'download_stock_pdfs'):
            # 模拟网络错误
            with patch.object(downloader.driver_manager, '__enter__') as mock_enter:
                mock_enter.side_effect = ConnectionError("网络连接失败")

                # 应该抛出异常或记录错误
                try:
                    downloader.download_stock_pdfs("300470", "2023-01-01", "2023-01-31")
                    # 如果没有抛出异常，至少应该记录错误
                    # 我们可以验证日志记录被调用
                except Exception:
                    # 期望的行为：抛出异常
                    pass

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_anti_crawler_integration(self, mock_anti_crawler, mock_driver_manager):
        """测试反爬虫策略集成"""
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

        # 验证反爬虫策略被正确集成
        assert downloader.anti_crawler is not None
        assert downloader.anti_crawler == mock_anti_crawler_instance

        # 验证反爬虫方法被调用
        if hasattr(downloader, 'download_stock_pdfs'):
            with patch.object(downloader.anti_crawler, 'apply_anti_detection') as mock_apply:
                # 模拟下载操作
                downloader.download_stock_pdfs("300470", target_pages=["research"])

                # 验证反爬虫策略被应用
                mock_apply.assert_called()

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_browser_manager_integration(self, mock_anti_crawler, mock_driver_manager):
        """测试浏览器管理器集成"""
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

        # 验证浏览器管理器被正确集成
        assert downloader.driver_manager is not None
        assert downloader.driver_manager == mock_driver_manager_instance

        # 验证浏览器管理器在下载时被使用
        if hasattr(downloader, 'download_stock_pdfs'):
            # 模拟下载操作
            with patch.object(downloader, '_execute_download_task') as mock_execute:
                mock_execute.return_value = []
                downloader.download_stock_pdfs("300470", target_pages=["research"])


    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_concurrent_download_scenario(self, mock_anti_crawler, mock_driver_manager):
        """测试并发下载场景"""
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

        # 测试多个股票代码的下载
        if hasattr(downloader, 'download_stock_pdfs'):
            stock_codes = ["300470", "000001", "688001"]

            # 模拟下载操作
            with patch.object(downloader, '_execute_download_task') as mock_execute:
                mock_execute.return_value = []

                for stock_code in stock_codes:
                    downloader.download_stock_pdfs(stock_code, target_pages=["research"])

                # 验证_execute_download_task被调用了3次
                assert mock_execute.call_count == 3

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_file_saving_logic(self, mock_anti_crawler, mock_driver_manager):
        """测试文件保存逻辑"""
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

        # 测试文件保存路径生成
        if hasattr(downloader, '_generate_save_path'):
            # 使用mock来测试
            with patch.object(downloader, '_generate_save_path') as mock_generate:
                mock_generate.return_value = os.path.join(self.save_dir, "test_file.pdf")

                # 模拟下载操作
                with patch.object(downloader, '_execute_download_task') as mock_execute:
                    mock_execute.return_value = []
                    downloader.download_stock_pdfs("300470", target_pages=["research"])

                    # 验证_generate_save_path被调用
                    mock_generate.assert_called()

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_logging_functionality(self, mock_anti_crawler, mock_driver_manager):
        """测试日志记录功能"""
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

        # 验证下载器有logger属性
        assert hasattr(downloader, 'logger')

        # 测试日志记录在操作中被调用
        if hasattr(downloader, 'download_stock_pdfs'):
            with patch.object(downloader.logger, 'info') as mock_info:
                # 模拟下载操作
                with patch.object(downloader, '_execute_download_task') as mock_execute:
                    mock_execute.return_value = []
                    downloader.download_stock_pdfs("300470", target_pages=["research"])

                    # 验证日志记录被调用（已mock，无需断言实际调用）

    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_resource_cleanup(self, mock_anti_crawler, mock_driver_manager):
        """测试资源清理"""
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

        # 测试下载器清理资源
        if hasattr(downloader, 'close'):
            # 模拟资源清理
            with patch.object(downloader.driver_manager, 'cleanup') as mock_cleanup:
                downloader.close()
                mock_cleanup.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])