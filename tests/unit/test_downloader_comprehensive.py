#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
下载器全面功能测试
测试DownloadService的所有公共方法和核心私有方法
"""

import pytest
import tempfile
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, List, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.downloader import DownloadService, StockService
from src.core.config import ConfigManager
from src.data.mapping import MappingManager
from src.data.models import StockInfo, DownloadRecord, DownloadStatus, DownloadTask
from src.core.exceptions import DownloadError


class TestDownloadServiceComprehensive:
    """DownloadService全面功能测试"""

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

        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== 初始化测试 ====================

    def test_initialization_default(self):
        """测试默认初始化"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        assert downloader.save_dir == Path(self.save_dir)
        assert downloader.save_dir.exists()
        assert downloader.mapping_file == self.mapping_file
        assert hasattr(downloader, 'mapping_manager')
        assert hasattr(downloader, 'browser_strategy_manager')
        assert hasattr(downloader, 'browser_strategy')
        assert hasattr(downloader, 'driver_manager')
        assert hasattr(downloader, 'anti_crawler')
        assert hasattr(downloader, 'config')
        assert hasattr(downloader, 'logger')
        assert downloader.download_count == 0

    def test_initialization_with_config_file(self):
        """测试带配置文件的初始化"""
        # 创建临时配置文件
        config_file = os.path.join(self.temp_dir, 'test_config.json')
        test_config = {
            "download": {
                "max_downloads_per_session": 20,
                "human_behavior_delay": 5
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        downloader = DownloadService(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            config_file=config_file
        )

        assert downloader.config is not None
        # 检查配置值是否被应用
        assert downloader.max_downloads_per_session == 20

    def test_initialization_invalid_save_dir(self):
        """测试无效保存目录的初始化"""
        # 使用包含空格和点的目录名（在Windows上有效但非常规）
        invalid_dir = os.path.join(self.temp_dir, 'test dir...')
        downloader = DownloadService(save_dir=invalid_dir, mapping_file=self.mapping_file)

        # 目录应该被创建
        assert downloader.save_dir.exists()

    # ==================== 文件名清理测试 ====================

    def test_clean_filename_basic(self):
        """测试基础文件名清理"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        test_cases = [
            ("正常文件名.pdf", "正常文件名.pdf"),
            ("file:with:colons.pdf", "file_with_colons.pdf"),
            ("file/with/slashes.pdf", "file_with_slashes.pdf"),
            ("file\\with\\backslashes.pdf", "file_with_backslashes.pdf"),
            ("file*with*asterisks.pdf", "file_with_asterisks.pdf"),
            ("file?with?question.pdf", "file_with_question.pdf"),
            ('file"with"quotes.pdf', 'file_with_quotes.pdf'),
            ("file<with>angles.pdf", "file_with_angles.pdf"),
            ("file|with|pipe.pdf", "file_with_pipe.pdf"),
            ("  file with spaces.pdf  ", "file with spaces.pdf"),
            ("file . . . with . dots.pdf", "file.with.dots.pdf"),
            ("file .. with .. multiple .. dots.pdf", "file.with.multiple.dots.pdf"),
            ("", ""),
            (None, None),
        ]

        for input_name, expected in test_cases:
            result = downloader.clean_filename(input_name)
            assert result == expected, f"Failed for input: {input_name}"

    def test_clean_filename_edge_cases(self):
        """测试边界情况文件名清理"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 超长文件名
        long_name = "a" * 300 + ".pdf"
        cleaned = downloader.clean_filename(long_name)
        assert len(cleaned) == len(long_name)  # 长度不变，只清理非法字符

        # 混合非法字符
        mixed = 'file:\\/*?"<>|.pdf'
        cleaned = downloader.clean_filename(mixed)
        assert cleaned == 'file_________.pdf'  # 9个非法字符被替换为9个下划线

    # ==================== 组织ID获取测试 ====================

    @patch('src.services.downloader.MappingManager')
    def test_get_org_id_success(self, mock_mapping_manager):
        """测试成功获取组织ID"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_org_id.return_value = "9900023856"
        mock_mapping_manager.return_value = mock_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)
        downloader.mapping_manager = mock_manager_instance

        org_id = downloader.get_org_id("300470")
        assert org_id == "9900023856"
        mock_manager_instance.get_org_id.assert_called_once_with("300470", force_refresh=False)

    @patch('src.services.downloader.MappingManager')
    def test_get_org_id_not_found(self, mock_mapping_manager):
        """测试未找到组织ID"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_org_id.return_value = None
        mock_mapping_manager.return_value = mock_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)
        downloader.mapping_manager = mock_manager_instance

        org_id = downloader.get_org_id("999999")
        assert org_id is None
        mock_manager_instance.get_org_id.assert_called_once_with("999999", force_refresh=False)

    @patch('src.services.downloader.MappingManager')
    def test_get_org_id_force_refresh(self, mock_mapping_manager):
        """测试强制刷新获取组织ID"""
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_org_id.return_value = "9900023856"
        mock_mapping_manager.return_value = mock_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)
        downloader.mapping_manager = mock_manager_instance

        org_id = downloader.get_org_id("300470", force_run=True)
        assert org_id == "9900023856"
        mock_manager_instance.get_org_id.assert_called_once_with("300470", force_refresh=True)

    # ==================== 主要下载方法测试 ====================

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_download_stock_pdfs_basic(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试基础下载功能"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        # 创建下载器
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # mock _execute_download_task方法
        mock_record = DownloadRecord(
            id="test-id",
            stock_code="300470",
            file_name="file.pdf",
            file_path="/path/to/file.pdf",
            file_size=1024,
            status=DownloadStatus.COMPLETED,
            created_at=datetime.now()
        )

        with patch.object(downloader, '_execute_download_task') as mock_execute:
            mock_execute.return_value = [mock_record]

            # 执行下载
            results = downloader.download_stock_pdfs("300470", target_pages=["research"])

            # 验证
            assert len(results) == 1
            assert results[0].stock_code == "300470"
            assert results[0].status == DownloadStatus.COMPLETED
            mock_execute.assert_called_once()

            # 验证task参数
            task = mock_execute.call_args[0][0]
            assert isinstance(task, DownloadTask)
            assert task.stock_info.stock_code == "300470"
            assert task.target_pages == ["research"]

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_download_stock_pdfs_with_dict_pages(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试使用字典格式的目标页面"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        with patch.object(downloader, '_execute_download_task') as mock_execute:
            mock_execute.return_value = []

            # 使用字典格式的target_pages
            target_pages = [
                {"suffix": "research", "allowed_keywords": ["年报", "季报"]},
                {"suffix": "announcement", "allowed_keywords": ["公告"]}
            ]

            results = downloader.download_stock_pdfs("300470", target_pages=target_pages)

            # 验证task参数
            task = mock_execute.call_args[0][0]
            assert task.target_pages == ["research", "announcement"]

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_download_stock_pdfs_no_stock_info(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试无法获取股票信息的情况"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # mock _get_stock_info返回None
        with patch.object(downloader, '_get_stock_info') as mock_get_info:
            mock_get_info.return_value = None

            results = downloader.download_stock_pdfs("999999", target_pages=["research"])

            assert results == []
            mock_get_info.assert_called_once_with("999999")

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_download_stock_pdfs_with_proxy(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试使用代理下载"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        with patch.object(downloader, '_execute_download_task') as mock_execute:
            mock_execute.return_value = []
            with patch.object(downloader, '_configure_proxy') as mock_configure_proxy:

                proxy_info = {
                    "host": "proxy.example.com",
                    "port": 8080,
                    "username": "user",
                    "password": "pass"
                }

                results = downloader.download_stock_pdfs(
                    "300470",
                    target_pages=["research"],
                    proxy_info=proxy_info
                )

                mock_configure_proxy.assert_called_once_with(proxy_info)
                mock_execute.assert_called_once()

    # ==================== 下载历史测试 ====================

    def test_get_download_history_empty(self):
        """测试获取空下载历史"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        history = downloader.get_download_history()
        assert isinstance(history, list)
        assert len(history) == 0

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_get_download_history_after_download(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试下载后的历史记录"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 创建测试PDF文件
        test_file_path = os.path.join(self.save_dir, "test.pdf")
        with open(test_file_path, 'wb') as f:
            f.write(b"PDF test content" * 100)  # 创建足够大的文件

        history = downloader.get_download_history()

        assert len(history) == 1
        assert history[0].file_name == "test.pdf"
        assert history[0].file_size > 0
        assert history[0].status == DownloadStatus.COMPLETED
        assert history[0].stock_code == "unknown"  # 根据get_download_history实现

    # ==================== 清理下载测试 ====================

    def test_cleanup_downloads(self):
        """测试清理下载文件"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 创建一些测试文件
        recent_file = os.path.join(self.save_dir, "recent.pdf")
        old_file = os.path.join(self.save_dir, "old.pdf")

        with open(recent_file, 'w') as f:
            f.write("recent content")

        with open(old_file, 'w') as f:
            f.write("old content")

        # 修改旧文件的修改时间（30天前）
        old_time = time.time() - (31 * 24 * 60 * 60)  # 31天前
        os.utime(old_file, (old_time, old_time))

        # 执行清理（保留30天内的文件）
        deleted_count = downloader.cleanup_downloads(days=30)

        # 验证
        assert deleted_count == 1
        assert os.path.exists(recent_file)
        assert not os.path.exists(old_file)

    def test_cleanup_downloads_no_files(self):
        """测试清理空目录"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        deleted_count = downloader.cleanup_downloads(days=30)
        assert deleted_count == 0

    def test_cleanup_downloads_custom_days(self):
        """测试自定义天数清理"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 创建测试文件
        file_path = os.path.join(self.save_dir, "test.pdf")
        with open(file_path, 'w') as f:
            f.write("test content")

        # 修改文件时间（15天前）
        file_time = time.time() - (15 * 24 * 60 * 60)
        os.utime(file_path, (file_time, file_time))

        # 清理10天前的文件（应该删除）
        deleted_count = downloader.cleanup_downloads(days=10)
        assert deleted_count == 1
        assert not os.path.exists(file_path)

        # 重新创建文件
        with open(file_path, 'w') as f:
            f.write("test content")
        os.utime(file_path, (file_time, file_time))

        # 清理20天前的文件（应该保留）
        deleted_count = downloader.cleanup_downloads(days=20)
        assert deleted_count == 0
        assert os.path.exists(file_path)

    # ==================== 延迟和重试测试 ====================

    def test_dynamic_delay(self):
        """测试动态延迟"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 测试多次调用，延迟应在范围内
        # 注意：在测试环境中，AntiCrawlerStrategy会减少延迟（乘以0.2）
        # base_min=1 -> 测试环境实际最小值: max(0.05, 1 * 0.2) = 0.2
        # base_max=3 -> 测试环境实际最大值: max(0.1, 3 * 0.2) = 0.6
        for _ in range(10):
            delay = downloader.dynamic_delay(base_min=1, base_max=3)
            assert 0.19 <= delay <= 0.61  # 包含一些容差

    def test_retry_count_property(self):
        """测试重试计数属性"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 初始值
        assert downloader.retry_count == 0

        # 设置值
        downloader.retry_count = 3
        assert downloader.retry_count == 3

        # 再次设置
        downloader.retry_count = 5
        assert downloader.retry_count == 5

    def test_max_retries_property(self):
        """测试最大重试次数属性"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 从配置中获取默认值
        default_max = downloader.config.get('download.max_retries', 3)
        assert downloader.max_retries == default_max

    def test_should_retry(self):
        """测试是否应该重试"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 初始状态
        assert downloader.should_retry() is True

        # 设置重试计数超过最大重试
        downloader.retry_count = downloader.max_retries + 1
        assert downloader.should_retry() is False

        # 重置重试计数
        downloader.retry_count = 0
        assert downloader.should_retry() is True

    # ==================== 日志方法测试 ====================

    @patch('src.services.downloader.logger')
    def test_log_methods(self, mock_logger):
        """测试日志方法"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 测试info日志
        downloader.log_info("测试信息")
        mock_logger.info.assert_called_once_with("测试信息")

        # 测试error日志
        downloader.log_error("测试错误")
        mock_logger.error.assert_called_once_with("测试错误")

        # 测试warning日志
        downloader.log_warning("测试警告")
        mock_logger.warning.assert_called_once_with("测试警告")

    # ==================== 状态获取测试 ====================

    def test_get_status(self):
        """测试获取状态"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        status = downloader.get_status()

        assert isinstance(status, dict)
        assert 'download_count' in status
        assert 'retry_count' in status
        assert 'success_count' in status
        assert 'error_count' in status

        assert status['download_count'] == 0
        assert status['retry_count'] == 0
        assert status['success_count'] == 0
        assert status['error_count'] == 0

    # ==================== 清理方法测试 ====================

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_cleanup(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试清理方法"""
        # 设置mock
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)
        # 确保downloader.driver_manager指向mock实例
        downloader.driver_manager = mock_driver_manager_instance

        # 执行清理
        downloader.cleanup()

        # 验证driver_manager的close_driver被调用（实际实现调用的是close_driver）
        mock_driver_manager_instance.close_driver.assert_called_once()

    # ==================== 错误处理测试 ====================

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_circuit_breaker_mechanism(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试断路器机制"""
        # 设置mock
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 初始状态
        assert downloader._consecutive_errors == 0
        assert downloader._circuit_breaker_active is False

        # 记录错误
        downloader._record_error()
        assert downloader._consecutive_errors == 1

        # 记录更多错误，触发断路器
        for _ in range(downloader._max_consecutive_errors):
            downloader._record_error()

        assert downloader._consecutive_errors == downloader._max_consecutive_errors + 1
        assert downloader._circuit_breaker_active is True

        # 检查断路器是否阻止操作（激活时应该返回False阻止操作）
        assert downloader._check_circuit_breaker() is False

        # 重置断路器
        downloader._reset_circuit_breaker()
        assert downloader._consecutive_errors == 0
        assert downloader._circuit_breaker_active is False
        assert downloader._check_circuit_breaker() is True

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_record_success_resets_errors(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试记录成功重置错误计数"""
        # 设置mock
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # 记录一些错误
        downloader._record_error()
        downloader._record_error()
        assert downloader._consecutive_errors == 2

        # 记录成功
        downloader._record_success()
        assert downloader._consecutive_errors == 0

    # ==================== 集成测试 ====================

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_full_download_workflow(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试完整下载工作流"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # mock整个执行链
        with patch.object(downloader, '_get_stock_info') as mock_get_stock_info, \
             patch.object(downloader, '_execute_download_task') as mock_execute_task:

            # 设置股票信息
            stock_info = StockInfo(
                stock_code="300470",
                stock_name="中密控股",
                org_id="9900023856"
            )
            mock_get_stock_info.return_value = stock_info

            # 设置下载结果
            mock_record = DownloadRecord(
                id="test-id",
                stock_code="300470",
                file_name="test.pdf",
                file_path=os.path.join(self.save_dir, "test.pdf"),
                file_size=1024,
                created_at=datetime.now(),
                status=DownloadStatus.COMPLETED
            )
            mock_execute_task.return_value = [mock_record]

            # 执行下载
            results = downloader.download_stock_pdfs("300470", target_pages=["research"])

            # 验证
            assert len(results) == 1
            assert results[0].status == DownloadStatus.COMPLETED

            # 验证历史记录
            history = downloader.get_download_history()
            assert len(history) == 0  # 注意：_download_history未在mock中设置

            # 验证状态
            status = downloader.get_status()
            assert status['download_count'] == 0  # download_count未增加

    # ==================== 性能测试 ====================

    def test_performance_initialization(self):
        """测试初始化性能"""
        import time

        start_time = time.time()
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)
        end_time = time.time()

        initialization_time = end_time - start_time
        # 初始化应该在合理时间内完成（例如5秒内）
        assert initialization_time < 5.0, f"初始化时间过长: {initialization_time:.2f}秒"

    def test_performance_clean_filename(self):
        """测试文件名清理性能"""
        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        import time

        test_name = "file:with/*?\"<>|illegal:chars.pdf"
        iterations = 1000

        start_time = time.time()
        for _ in range(iterations):
            downloader.clean_filename(test_name)
        end_time = time.time()

        total_time = end_time - start_time
        avg_time = total_time / iterations

        # 平均清理时间应该在1毫秒以内
        assert avg_time < 0.001, f"文件名清理性能差: {avg_time*1000:.2f}毫秒/次"

    # ==================== 异常处理测试 ====================

    @patch('src.services.downloader.BrowserStrategyManager')
    @patch('src.services.downloader.WebDriverManager')
    @patch('src.services.downloader.AntiCrawlerStrategy')
    def test_exception_handling_in_download(self, mock_anti_crawler, mock_driver_manager, mock_strategy_manager):
        """测试下载中的异常处理"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        mock_strategy_instance = MagicMock()
        mock_strategy_manager_instance = MagicMock()
        mock_strategy_manager_instance.get_strategy.return_value = mock_strategy_instance
        mock_strategy_manager.return_value = mock_strategy_manager_instance

        downloader = DownloadService(save_dir=self.save_dir, mapping_file=self.mapping_file)

        # mock _execute_download_task抛出异常
        with patch.object(downloader, '_execute_download_task') as mock_execute:
            mock_execute.side_effect = DownloadError("模拟下载错误")

            # 应该抛出异常
            with pytest.raises(DownloadError):
                downloader.download_stock_pdfs("300470", target_pages=["research"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])