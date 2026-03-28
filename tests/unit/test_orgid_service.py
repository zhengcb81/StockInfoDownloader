#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrgIdService 单元测试
"""

import pytest
from typing import cast
from unittest.mock import MagicMock, patch, PropertyMock
from selenium.common.exceptions import TimeoutException
from src.services.orgid_service import OrgIdService


class TestOrgIdService:
    """测试 OrgIdService 类"""

    def setup_method(self):
        """设置测试环境"""
        self.service = OrgIdService()

    @patch("src.services.orgid_service.WebDriverManager")
    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_success(self, mock_standardize, mock_driver_manager):
        """测试成功获取组织ID"""
        # 创建服务实例（在 patch 之后）
        service = OrgIdService()

        # Mock 股票代码标准化
        mock_standardize.return_value = "000001"

        # Mock WebDriverManager
        mock_driver = MagicMock()
        mock_driver.page_source = (
            '<html><a href="/companyProfile?orgId=9900000001">公司介绍</a></html>'
        )
        mock_driver.find_elements.return_value = []

        # Mock 公司介绍链接
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = (
            "https://www.cninfo.com.cn/companyProfile?orgId=9900000001"
        )

        # 设置 context manager 行为
        mock_dm_instance = mock_driver_manager.return_value
        mock_dm_instance.__enter__.return_value = mock_driver

        # Mock WebDriverWait 返回链接
        with patch("src.services.orgid_service.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = [mock_link]

            # 执行获取
            org_id = service.get_org_id("000001")

        # 验证
        assert org_id == "9900000001"
        mock_standardize.assert_called_with("000001")

    @patch("src.services.orgid_service.WebDriverWait")
    @patch("src.services.orgid_service.WebDriverManager")
    @patch("src.services.orgid_service.standardize_stock_code")
    def test_crawl_org_id_success(
        self, mock_standardize, mock_driver_manager, mock_wait
    ):
        """测试爬取组织ID成功"""
        mock_driver = MagicMock()
        mock_driver.page_source = (
            '<html><a href="/companyProfile?orgId=9900000001">公司介绍</a></html>'
        )

        # Mock 公司介绍链接
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = (
            "https://www.cninfo.com.cn/companyProfile?orgId=9900000001"
        )
        mock_wait.return_value.until.return_value = [mock_link]

        result = self.service._crawl_org_id(mock_driver, "000001")
        assert result == "9900000001"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_invalid_code(self, mock_standardize):
        """测试无效股票代码"""
        mock_standardize.return_value = None

        org_id = self.service.get_org_id("invalid")

        assert org_id is None

    @patch("src.services.orgid_service.WebDriverManager")
    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_exception(self, mock_standardize, mock_driver_manager):
        """测试获取过程中的异常"""
        service = OrgIdService()
        mock_standardize.return_value = "000001"
        mock_driver_manager.side_effect = Exception("Test error")

        org_id = service.get_org_id("000001")

        assert org_id is None

    def test_extract_org_id_from_url_success(self):
        """测试从URL提取组织ID"""
        url = "https://example.com?orgId=123456"
        result = self.service._extract_org_id_from_url(url)
        assert result == "123456"

    def test_extract_org_id_from_url_missing(self):
        """测试从URL提取组织ID - 缺失"""
        url = "https://example.com?noOrgId=123"
        result = self.service._extract_org_id_from_url(url)
        assert result is None

    def test_extract_org_id_from_page_script(self):
        """测试从页面脚本提取组织ID"""
        mock_driver = MagicMock()
        mock_script = MagicMock()
        mock_script.get_attribute.return_value = 'var config = {"orgId": "654321"};'
        mock_driver.find_elements.return_value = [mock_script]

        result = self.service._extract_org_id_from_page(mock_driver)
        assert result == "654321"

    def test_extract_org_id_from_page_hidden_input(self):
        """测试从隐藏表单提取组织ID"""
        mock_driver = MagicMock()
        # 第一次调用返回脚本（空），第二次调用返回隐藏字段
        mock_script = MagicMock()
        mock_script.get_attribute.return_value = ""

        mock_hidden = MagicMock()
        mock_hidden.get_attribute.side_effect = (
            lambda attr: "orgId" if attr == "name" else "112233"
        )

        def find_elements_side_effect(by, value):
            if by == "tag name" and value == "script":
                return [mock_script]
            return [mock_hidden]

        mock_driver.find_elements.side_effect = find_elements_side_effect

        result = self.service._extract_org_id_from_page(mock_driver)
        assert result == "112233"

    @patch("src.services.orgid_service.WebDriverWait")
    def test_crawl_org_id_timeout(self, mock_wait):
        """测试爬取超时"""
        mock_driver = MagicMock()
        mock_wait.side_effect = TimeoutException("Timeout")

        result = self.service._crawl_org_id(mock_driver, "000001")
        assert result is None
