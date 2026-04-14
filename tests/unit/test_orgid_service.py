#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrgIdService 单元测试
测试 OrgIdService 通过 BrowserStrategy 抽象接口获取组织ID
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.services.orgid_service import OrgIdService


class TestOrgIdService:
    """测试 OrgIdService 类"""

    def _create_mock_strategy(self):
        """创建 mock BrowserStrategy"""
        mock_strategy = MagicMock()
        mock_strategy.initialize.return_value = True
        mock_strategy.navigate.return_value = True
        mock_strategy.wait_for_element.return_value = True
        mock_strategy.cleanup.return_value = None
        return mock_strategy

    def setup_method(self):
        """设置测试环境"""
        self.mock_strategy = self._create_mock_strategy()
        self.service = OrgIdService(browser_strategy=self.mock_strategy)

    def test_init_with_strategy(self):
        """测试使用 BrowserStrategy 实例初始化"""
        mock_strategy = self._create_mock_strategy()
        service = OrgIdService(browser_strategy=mock_strategy)
        assert service._strategy is mock_strategy

    @patch("src.services.orgid_service.BrowserStrategyFactory")
    def test_init_with_strategy_type(self, mock_factory):
        """测试使用 strategy_type 字符串初始化"""
        mock_strategy = self._create_mock_strategy()
        mock_factory.create_strategy.return_value = mock_strategy

        service = OrgIdService(strategy_type="playwright")

        mock_factory.create_strategy.assert_called_once_with(
            "playwright", headless=True, config={}
        )
        assert service._strategy is mock_strategy

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_success(self, mock_standardize):
        """测试成功获取组织ID"""
        mock_standardize.return_value = "000001"

        # Mock 公司介绍链接
        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "https://www.cninfo.com.cn/companyProfile?orgId=9900000001"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        org_id = self.service.get_org_id("000001")

        assert org_id == "9900000001"
        mock_standardize.assert_called_with("000001")
        self.mock_strategy.initialize.assert_called_once()
        self.mock_strategy.cleanup.assert_called_once()

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_from_page_source(self, mock_standardize):
        """测试从页面源代码中提取组织ID"""
        mock_standardize.return_value = "000001"

        # 模拟找不到公司介绍链接
        self.mock_strategy.find_elements.return_value = []
        self.mock_strategy.get_page_source.return_value = (
            '<html><script>var orgId = "9900001234";</script></html>'
        )

        org_id = self.service.get_org_id("000001")

        assert org_id == "9900001234"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_crawl_org_id_success(self, mock_standardize):
        """测试爬取组织ID成功"""
        mock_standardize.return_value = "000001"

        # Mock 公司介绍链接
        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "https://www.cninfo.com.cn/companyProfile?orgId=9900000001"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        # 直接调用 _crawl_org_id（不经过 get_org_id 的 initialize/cleanup）
        result = self.service._crawl_org_id("000001")
        assert result == "9900000001"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_invalid_code(self, mock_standardize):
        """测试无效股票代码"""
        mock_standardize.return_value = None

        org_id = self.service.get_org_id("invalid")

        assert org_id is None

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_exception(self, mock_standardize):
        """测试获取过程中的异常"""
        mock_standardize.return_value = "000001"
        self.mock_strategy.initialize.side_effect = Exception("Test error")

        org_id = self.service.get_org_id("000001")

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

    def test_crawl_org_id_navigate_failure(self):
        """测试导航失败"""
        self.mock_strategy.navigate.return_value = False

        result = self.service._crawl_org_id("000001")
        assert result is None

    def test_crawl_org_id_wait_timeout(self):
        """测试等待元素超时"""
        self.mock_strategy.wait_for_element.return_value = False
        self.mock_strategy.find_elements.return_value = []
        self.mock_strategy.get_page_source.return_value = ""

        result = self.service._crawl_org_id("000001")
        assert result is None

    def test_crawl_org_id_no_org_id_in_page(self):
        """测试页面中没有组织ID"""
        self.mock_strategy.find_elements.return_value = []
        self.mock_strategy.get_page_source.return_value = "<html><body>No orgId here</body></html>"

        result = self.service._crawl_org_id("000001")
        assert result is None

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_cleanup_called_on_error(self, mock_standardize):
        """测试异常时 cleanup 仍然被调用"""
        mock_standardize.return_value = "000001"
        self.mock_strategy.navigate.side_effect = Exception("Navigation failed")

        self.service.get_org_id("000001")

        # cleanup 应该在 finally 中被调用
        self.mock_strategy.cleanup.assert_called_once()

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_gssz_prefix(self, mock_standardize):
        """测试提取 gssz 前缀的组织ID"""
        mock_standardize.return_value = "000001"

        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "https://www.cninfo.com.cn/companyProfile?orgId=gssz12345"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        org_id = self.service.get_org_id("000001")

        assert org_id == "gssz12345"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_gssh_prefix(self, mock_standardize):
        """测试提取 gssh 前缀的组织ID（沪市股票）"""
        mock_standardize.return_value = "600519"

        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "/new/disclosure/stock?orgId=gssh0600519&stockCode=600519#companyProfile"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        org_id = self.service.get_org_id("600519")

        assert org_id == "gssh0600519"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_gd_prefix(self, mock_standardize):
        """测试提取 GD 前缀的组织ID（创业板）"""
        mock_standardize.return_value = "300750"

        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "/new/disclosure/stock?orgId=GD165627&stockCode=300750#companyProfile"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        org_id = self.service.get_org_id("300750")

        assert org_id == "GD165627"

    @patch("src.services.orgid_service.standardize_stock_code")
    def test_get_org_id_jjxt_prefix(self, mock_standardize):
        """测试提取 jjxt 前缀的组织ID（银行等金融股）"""
        mock_standardize.return_value = "601398"

        mock_link = MagicMock()
        self.mock_strategy.get_attribute.return_value = (
            "/new/disclosure/stock?orgId=jjxt0000019&stockCode=601398#companyProfile"
        )
        self.mock_strategy.find_elements.return_value = [mock_link]
        self.mock_strategy.get_page_source.return_value = ""

        org_id = self.service.get_org_id("601398")

        assert org_id == "jjxt0000019"

    def test_is_valid_org_id_various_formats(self):
        """测试 _is_valid_org_id 校验各种 orgId 格式"""
        # 有效格式
        assert OrgIdService._is_valid_org_id("9900023856") is True  # 纯数字
        assert OrgIdService._is_valid_org_id("gssz0000001") is True  # gssz 前缀
        assert OrgIdService._is_valid_org_id("gssh0600519") is True  # gssh 前缀
        assert OrgIdService._is_valid_org_id("GD165627") is True  # GD 前缀
        assert OrgIdService._is_valid_org_id("jjxt0000019") is True  # jjxt 前缀

        # 无效格式
        assert OrgIdService._is_valid_org_id("") is False  # 空字符串
        assert OrgIdService._is_valid_org_id("ab") is False  # 太短
        assert OrgIdService._is_valid_org_id("a" * 21) is False  # 太长
        assert OrgIdService._is_valid_org_id("abc!@#") is False  # 特殊字符

    def test_extract_org_id_from_url_alphanumeric(self):
        """测试从URL提取字母数字混合的 orgId"""
        url = "https://cninfo.com.cn/stock?orgId=gssh0600519&stockCode=600519"
        result = self.service._extract_org_id_from_url(url)
        assert result == "gssh0600519"

    def test_extract_org_id_from_url_gd_prefix(self):
        """测试从URL提取 GD 前缀的 orgId"""
        url = "https://cninfo.com.cn/stock?orgId=GD165627&stockCode=300750"
        result = self.service._extract_org_id_from_url(url)
        assert result == "GD165627"
