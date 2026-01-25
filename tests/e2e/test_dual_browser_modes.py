#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
双浏览器模式组件集成测试（使用mock对象）
测试Selenium和Playwright两种浏览器策略的模拟下载工作流程
注意：这不是真正的端到端测试，真正的端到端测试是 e2e_test.py
"""

import pytest
import tempfile
import os
import shutil
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.adapters.legacy_downloader_adapter import DownloadServiceV2Adapter as DownloadServiceV2
from tests.test_config_manager import ConfigManagerTool


# 测试股票数据
test_stock = {
    "code": "300470",
    "name": "中密控股",
    "org_id": "gssz0000470"
}


class TestSeleniumModeE2E:
    """Selenium模式组件集成测试类（使用mock对象）"""

    def setup_method(self):
        """测试设置"""
        self.browser_strategy = "selenium"
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, 'downloads')
        self.test_config = ConfigManagerTool()

        # 创建测试映射文件（使用测试配置）
        self.mapping_file = os.path.join(self.temp_dir, 'test_mapping.json')
        test_stocks = self.test_config.get_test_stocks()
        test_mapping = {
            stock.get('code'): {
                "orgId": stock.get('org_id'),
                "name": stock.get('name')
            }
            for stock in test_stocks
        }
        # 添加额外的测试数据
        test_mapping["000001"] = {
            "orgId": "9900000001",
            "name": "平安银行"
        }

        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

        # 创建测试配置文件
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "stock_code": test_stock.get('code', '300470'),
                "save_dir": self.save_dir,
                "headless": True,
                "max_retries": 2,
                "browser": {
                    "strategy": self.browser_strategy,
                    "headless": True
                },
                "pages": [
                    {
                        "name": "投资者关系活动",
                        "suffix": "research",
                        "allowed_keywords": ["投资者关系", "调研"],
                        "max_pages": 2
                    }
                ]
            }, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_browser_strategy_initialization(self, mock_create_strategy):
        """测试浏览器策略初始化"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 验证策略创建（允许有额外的config参数）
        mock_create_strategy.assert_called_once()
        call_args = mock_create_strategy.call_args
        assert call_args[1]['strategy_type'] == self.browser_strategy
        assert call_args[1]['headless'] is True
        assert call_args[1]['download_dir'] == self.save_dir

        # 验证下载器属性
        assert downloader.browser_strategy == mock_strategy

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_strategy_specific_configuration(self, mock_create_strategy):
        """测试策略特定配置"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # 测试Selenium特定配置
        if self.browser_strategy == "selenium":
            downloader = DownloadServiceV2(
                save_dir=self.save_dir,
                mapping_file=self.mapping_file,
                browser_strategy="selenium"
            )
            # 验证Selenium特定的配置参数传递
            call_args = mock_create_strategy.call_args
            assert call_args[1]['strategy_type'] == "selenium"

        # 测试Playwright特定配置
        elif self.browser_strategy == "playwright":
            downloader = DownloadServiceV2(
                save_dir=self.save_dir,
                mapping_file=self.mapping_file,
                browser_strategy="playwright"
            )
            # 验证Playwright特定的配置参数传递
            call_args = mock_create_strategy.call_args
            assert call_args[1]['strategy_type'] == "playwright"

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    @patch('src.data.mapping.MappingManager.get_org_id')
    def test_download_workflow_consistency(self, mock_get_org_id, mock_create_strategy):
        """测试不同策略下的下载工作流程一致性"""
        # 设置mock对象
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # Mock组织ID获取
        mock_get_org_id.return_value = test_stock.get('org_id', '9900023856')

        # 模拟成功的下载流程
        mock_strategy.navigate.return_value = True
        mock_strategy.find_elements.return_value = []
        mock_strategy.get_current_url.return_value = "https://example.com"

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行下载
        download_records = downloader.download_stock_pdfs(
            stock_code=test_stock.get('code', '300470'),
            target_pages=[{
                "suffix": "research",
                "allowed_keywords": ["投资者关系", "调研"]
            }],
            max_retries=1
        )

        # 验证下载结果一致性
        assert isinstance(download_records, list)

        # 验证策略方法调用一致性
        mock_strategy.navigate.assert_called()
        mock_strategy.find_elements.assert_called()

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    @patch('src.data.mapping.MappingManager.get_org_id')
    def test_error_handling_consistency(self, mock_get_org_id, mock_create_strategy):
        """测试不同策略下的错误处理一致性"""
        # 设置mock策略来模拟错误
        mock_strategy = MagicMock()
        mock_strategy.navigate.side_effect = Exception("Navigation failed")
        mock_create_strategy.return_value = mock_strategy

        # Mock组织ID获取
        mock_get_org_id.return_value = test_stock.get('org_id', '9900023856')

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行下载 - 由于装饰器的重试机制，这会抛出异常
        # 我们测试的是异常被正确抛出，而不是静默失败
        with pytest.raises(Exception) as exc_info:
            downloader.download_stock_pdfs(
                stock_code=test_stock.get('code', '300470'),
                target_pages=[{
                    "suffix": "research",
                    "allowed_keywords": ["投资者关系", "调研"]
                }],
                max_retries=1
            )

        # 验证异常信息包含导航失败信息
        assert "Navigation failed" in str(exc_info.value) or "导航" in str(exc_info.value)

        # 验证策略方法被调用了多次（由于重试机制）
        assert mock_strategy.navigate.call_count > 1

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    @patch('src.data.mapping.MappingManager.get_org_id')
    def test_performance_monitoring_integration(self, mock_get_org_id, mock_create_strategy):
        """测试性能监控集成"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_strategy.navigate.return_value = True
        mock_strategy.find_elements.return_value = []
        mock_create_strategy.return_value = mock_strategy

        # Mock组织ID获取
        mock_get_org_id.return_value = test_stock.get('org_id', '9900023856')

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行下载
        download_records = downloader.download_stock_pdfs(
            stock_code=test_stock.get('code', '300470'),
            target_pages=[{
                "suffix": "research",
                "allowed_keywords": ["投资者关系", "调研"]
            }],
            max_retries=1
        )

        # 验证性能监控数据（使用get_status方法）
        status_data = downloader.get_status()
        assert isinstance(status_data, dict)

        # 验证包含必要的状态信息
        assert 'download_count' in status_data or 'retry_count' in status_data

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_resource_cleanup(self, mock_create_strategy):
        """测试资源清理"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行清理
        downloader.cleanup()

        # 验证策略清理方法被调用
        mock_strategy.close.assert_called_once()

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_config_loading_integration(self, mock_create_strategy):
        """测试配置加载集成"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # 从配置文件创建下载器
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        downloader = DownloadServiceV2(
            save_dir=config['save_dir'],
            mapping_file=self.mapping_file,
            browser_strategy=config['browser']['strategy']
        )

        # 验证配置参数正确传递
        call_args = mock_create_strategy.call_args
        assert call_args[1]['strategy_type'] == self.browser_strategy
        assert call_args[1]['headless'] == config['browser']['headless']


class TestPlaywrightModeE2E:
    """Playwright模式组件集成测试类（使用mock对象）"""

    def setup_method(self):
        """测试设置"""
        self.browser_strategy = "playwright"
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, 'downloads')

        # 创建测试映射文件（使用真实股票代码）
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

        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

        # 创建测试配置文件
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "stock_code": test_stock.get('code', '300470'),
                "save_dir": self.save_dir,
                "headless": True,
                "max_retries": 2,
                "browser": {
                    "strategy": "playwright",
                    "headless": True
                },
                "pages": [
                    {
                        "name": "投资者关系活动",
                        "suffix": "research",
                        "allowed_keywords": ["投资者关系", "调研"],
                        "max_pages": 2
                    }
                ]
            }, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_browser_strategy_initialization(self, mock_create_strategy):
        """测试浏览器策略初始化"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 验证策略创建（允许有额外的config参数）
        mock_create_strategy.assert_called_once()
        call_args = mock_create_strategy.call_args
        assert call_args[1]['strategy_type'] == "playwright"
        assert call_args[1]['headless'] is True
        assert call_args[1]['download_dir'] == self.save_dir

        # 验证下载器属性
        assert downloader.browser_strategy == mock_strategy

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    @patch('src.data.mapping.MappingManager.get_org_id')
    def test_download_workflow_consistency(self, mock_get_org_id, mock_create_strategy):
        """测试下载工作流程一致性"""
        # 设置mock策略
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        # Mock组织ID获取
        mock_get_org_id.return_value = test_stock.get('org_id', '9900023856')

        # 模拟成功的下载流程
        mock_strategy.navigate.return_value = True
        mock_strategy.find_elements.return_value = []
        mock_strategy.get_current_url.return_value = "https://example.com"

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行下载
        download_records = downloader.download_stock_pdfs(
            stock_code=test_stock.get('code', '300470'),
            target_pages=[{
                "suffix": "research",
                "allowed_keywords": ["投资者关系", "调研"]
            }],
            max_retries=1
        )

        # 验证下载结果一致性
        assert isinstance(download_records, list)

        # 验证策略方法调用一致性
        mock_strategy.navigate.assert_called()
        mock_strategy.find_elements.assert_called()

    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    @patch('src.data.mapping.MappingManager.get_org_id')
    def test_error_handling_consistency(self, mock_get_org_id, mock_create_strategy):
        """测试错误处理一致性"""
        # 设置mock策略来模拟错误
        mock_strategy = MagicMock()
        mock_strategy.navigate.side_effect = Exception("Navigation failed")
        mock_create_strategy.return_value = mock_strategy

        # Mock组织ID获取
        mock_get_org_id.return_value = test_stock.get('org_id', '9900023856')

        # 创建下载器
        downloader = DownloadServiceV2(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file,
            browser_strategy=self.browser_strategy
        )

        # 执行下载 - 由于装饰器的重试机制，这会抛出异常
        # 我们测试的是异常被正确抛出，而不是静默失败
        with pytest.raises(Exception) as exc_info:
            downloader.download_stock_pdfs(
                stock_code=test_stock.get('code', '300470'),
                target_pages=[{
                    "suffix": "research",
                    "allowed_keywords": ["投资者关系", "调研"]
                }],
                max_retries=1
            )

        # 验证异常信息包含导航失败信息
        assert "Navigation failed" in str(exc_info.value) or "导航" in str(exc_info.value)

        # 验证策略方法被调用了多次（由于重试机制）
        assert mock_strategy.navigate.call_count > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])