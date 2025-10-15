#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID服务单元测试
测试OrgIdService类的功能
注意：这个测试文件针对的是实时爬取的OrgIdService，不是带缓存机制的版本
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.orgid_service import OrgIdService


@pytest.fixture(autouse=True)
def mock_subprocess_calls():
    """Mock all subprocess calls and time.sleep to prevent hanging in tests"""
    with patch('src.web.driver.subprocess.run') as mock_run, \
         patch('src.web.driver.time.sleep') as mock_sleep:
        mock_run.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
        yield


class TestOrgIdService:
    """组织ID服务测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """测试初始化"""
        service = OrgIdService()
        assert service.driver_manager is not None
        assert service.anti_crawler is not None
        assert service.base_url == "https://www.cninfo.com.cn"

    @patch('src.services.orgid_service.WebDriverManager')
    @patch('src.services.orgid_service.AntiCrawlerStrategy')
    def test_get_org_id_success(self, mock_anti_crawler, mock_driver_manager):
        """测试成功获取组织ID"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver.current_url = "https://www.cninfo.com.cn/new/investor/investor?stockCode=300470&orgId=9900023856"

        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        service = OrgIdService()

        # 测试获取组织ID
        org_id = service.get_org_id("300470")
        assert org_id == "9900023856"

    @patch('src.services.orgid_service.WebDriverManager')
    @patch('src.services.orgid_service.AntiCrawlerStrategy')
    def test_get_org_id_not_found(self, mock_anti_crawler, mock_driver_manager):
        """测试获取不存在的组织ID"""
        # 设置mock
        mock_driver = MagicMock()
        mock_driver.current_url = "https://www.cninfo.com.cn/new/investor/investor?stockCode=999999"  # 没有orgId

        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        service = OrgIdService()

        org_id = service.get_org_id("999999")
        assert org_id is None

    def test_extract_org_id_from_url_success(self):
        """测试从URL成功提取组织ID"""
        service = OrgIdService()

        test_cases = [
            ("https://www.cninfo.com.cn/new/investor/investor?stockCode=300470&orgId=9900023856", "9900023856"),
            ("https://www.cninfo.com.cn/new/disclosure/stock?orgId=9900010519&stockCode=600519", "9900010519"),
            ("https://example.com?orgId=1234567890&other=param", "1234567890"),
        ]

        for url, expected in test_cases:
            result = service._extract_org_id_from_url(url)
            assert result == expected, f"Failed for URL: {url}"

    def test_extract_org_id_from_url_failure(self):
        """测试从URL提取组织ID失败"""
        service = OrgIdService()

        test_cases = [
            "https://www.cninfo.com.cn/new/investor/investor?stockCode=300470",  # 没有orgId
            "",  # 空URL
            "https://example.com",  # 没有参数
        ]

        for url in test_cases:
            result = service._extract_org_id_from_url(url)
            assert result is None, f"Should return None for URL: {url}"

    @patch('src.services.orgid_service.WebDriverManager')
    @patch('src.services.orgid_service.AntiCrawlerStrategy')
    def test_crawl_org_id_timeout_handling(self, mock_anti_crawler, mock_driver_manager):
        """测试爬取组织ID时的超时处理"""
        from selenium.common.exceptions import TimeoutException

        # 设置mock driver
        mock_driver = MagicMock()
        mock_driver.get.side_effect = TimeoutException("页面加载超时")

        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        service = OrgIdService()

        result = service._crawl_org_id(mock_driver, "300470")
        assert result is None

    @patch('src.services.orgid_service.WebDriverManager')
    @patch('src.services.orgid_service.AntiCrawlerStrategy')
    def test_crawl_org_id_general_exception_handling(self, mock_anti_crawler, mock_driver_manager):
        """测试爬取组织ID时的通用异常处理"""
        # 设置mock driver
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("通用错误")

        mock_driver_manager_instance = MagicMock()
        mock_driver_manager_instance.__enter__ = MagicMock(return_value=mock_driver)
        mock_driver_manager_instance.__exit__ = MagicMock(return_value=None)
        mock_driver_manager.return_value = mock_driver_manager_instance

        mock_anti_crawler_instance = MagicMock()
        mock_anti_crawler.return_value = mock_anti_crawler_instance

        service = OrgIdService()

        result = service._crawl_org_id(mock_driver, "300470")
        assert result is None

    def test_stock_code_standardization(self):
        """测试股票代码标准化"""
        service = OrgIdService()

        # 测试get_org_id方法中的标准化逻辑
        # 由于get_org_id需要网络请求，我们直接测试标准化函数
        from src.utils.string_optimizer import standardize_stock_code

        test_cases = [
            ("300470", "300470"),  # 标准格式
            ("000001", "000001"),  # 深市股票
            ("600519", "600519"),  # 沪市股票
            (" 300470 ", "300470"),  # 带空格
        ]

        for input_code, expected in test_cases:
            result = standardize_stock_code(input_code)
            assert result == expected, f"Failed for: {input_code} (got {result}, expected {expected})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])