#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StockService增强测试模块
测试src.services.stock_service.StockService类的全面功能
使用统一的测试基类提高代码复用性
"""

import pytest
import tempfile
import csv
import os
from unittest.mock import Mock, patch, MagicMock

from src.services.stock_service import StockService
from src.data.models import StockInfo
from .test_base import StockServiceTestBase, assert_stock_info_equal, assert_stock_code_valid


class TestStockServiceEnhanced(StockServiceTestBase):
    """StockService增强测试类"""

    def setup_method(self):
        """测试初始化"""
        super().setup_method()
        self.service = StockService()

    def test_init(self):
        """测试初始化"""
        service = StockService()
        assert service is not None
        assert hasattr(service, 'session')
        assert hasattr(service, 'base_url')
        assert service.base_url == "https://www.cninfo.com.cn"

    @patch('src.services.stock_service.standardize_stock_code')
    @patch('src.services.stock_service.requests.Session.get')
    def test_get_stock_name_success(self, mock_get, mock_standardize):
        """测试成功获取股票名称"""
        # 设置mock
        mock_standardize.return_value = "300470"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {'code': '300470', 'value': '日机密封-测试股票'},
            {'code': '000001', 'value': '平安银行'}
        ]
        mock_get.return_value = mock_response

        # 执行测试
        result = self.service.get_stock_name("300470")

        # 验证结果
        assert result == "日机密封"
        mock_get.assert_called_once()
        mock_standardize.assert_called_once_with("300470")

    @patch('src.services.stock_service.standardize_stock_code')
    def test_get_stock_name_invalid_code(self, mock_standardize):
        """测试无效股票代码"""
        mock_standardize.return_value = None

        result = self.service.get_stock_name("invalid")

        assert result is None
        mock_standardize.assert_called_once_with("invalid")

    @patch('src.services.stock_service.standardize_stock_code')
    @patch('src.services.stock_service.requests.Session.get')
    def test_get_stock_name_not_found(self, mock_get, mock_standardize):
        """测试股票代码未找到"""
        mock_standardize.return_value = "999999"

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {'code': '000001', 'value': '平安银行'}
        ]
        mock_get.return_value = mock_response

        result = self.service.get_stock_name("999999")

        assert result is None

    @patch('src.services.stock_service.standardize_stock_code')
    @patch('src.services.stock_service.requests.Session.get')
    def test_get_stock_name_network_error(self, mock_get, mock_standardize):
        """测试网络错误"""
        mock_standardize.return_value = "300470"
        mock_get.side_effect = Exception("Network error")

        result = self.service.get_stock_name("300470")

        assert result is None

    @patch('src.services.stock_service.StockService.get_stock_name')
    def test_get_stock_info_success(self, mock_get_stock_name):
        """测试成功获取股票信息"""
        mock_get_stock_name.return_value = "测试股票"

        with patch.object(self.service, '_get_market_info') as mock_market:
            mock_market.return_value = "SZ"

            result = self.service.get_stock_info("300470")

            assert isinstance(result, StockInfo)
            assert result.stock_code == "300470"
            assert result.stock_name == "测试股票"
            assert result.market == "SZ"

    @patch('src.services.stock_service.StockService.get_stock_name')
    def test_get_stock_info_no_name(self, mock_get_stock_name):
        """测试获取股票信息但名称为空"""
        mock_get_stock_name.return_value = None

        result = self.service.get_stock_info("300470")

        assert result is None

    def test_get_market_info_sh(self):
        """测试获取上海市场信息"""
        result = self.service._get_market_info("600519")
        assert result == "SH"

    def test_get_market_info_sz(self):
        """测试获取深圳市场信息"""
        result = self.service._get_market_info("000001")
        assert result == "SZ"

        result = self.service._get_market_info("300470")
        assert result == "SZ"

    def test_get_market_info_bj(self):
        """测试获取北京市场信息"""
        result = self.service._get_market_info("430001")
        assert result == "BJ"

        result = self.service._get_market_info("830001")
        assert result == "BJ"

    def test_get_market_info_invalid(self):
        """测试无效市场信息"""
        result = self.service._get_market_info("999999")
        assert result is None

    def test_validate_stock_code_valid(self):
        """测试有效股票代码验证"""
        valid_codes = ["000001", "300470", "600519", "430001"]

        for code in valid_codes:
            result = self.service.validate_stock_code(code)
            assert result is True, f"Code {code} should be valid"

    def test_validate_stock_code_invalid(self):
        """测试无效股票代码验证"""
        invalid_cases = [
            "abc123",     # 包含字母
            "12345",      # 长度不足
            "1234567",    # 长度过长
            "",           # 空字符串
            "300470A",    # 带后缀
        ]

        for code in invalid_cases:
            result = self.service.validate_stock_code(code)
            assert result is False, f"Code {code} should be invalid"

    def test_validate_stock_code_with_spaces(self):
        """测试带空格的股票代码验证（会被trim）"""
        # 带空格的代码会被trim，所以应该有效
        result = self.service.validate_stock_code(" 300470 ")
        assert result is True, "Code with spaces should be valid after trimming"

    def test_get_stock_list_from_file_success(self):
        """测试从CSV文件成功读取股票列表"""
        # 创建临时CSV文件（使用英文表头避免编码问题）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['stock_code', 'stock_name'])  # 英文表头
            writer.writerow(['000001', 'PingAn Bank'])
            writer.writerow(['300470', 'Riji Mifeng'])
            writer.writerow(['600519', 'Guizhou Maotai'])
            temp_file = f.name

        try:
            result = self.service.get_stock_list_from_file(temp_file)

            assert len(result) == 3
            assert "000001" in result
            assert "300470" in result
            assert "600519" in result
        finally:
            # 清理临时文件
            os.unlink(temp_file)

    def test_get_stock_list_from_file_not_exists(self):
        """测试文件不存在的情况"""
        result = self.service.get_stock_list_from_file("/path/to/nonexistent/file.csv")

        assert result == []

    def test_get_stock_list_from_file_empty(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['股票代码', '股票名称'])  # 只有表头
            temp_file = f.name

        try:
            result = self.service.get_stock_list_from_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    @patch('src.services.stock_service.StockService.get_stock_name')
    def test_batch_get_stock_names(self, mock_get_stock_name):
        """测试批量获取股票名称"""
        # 设置mock返回值
        mock_get_stock_name.side_effect = lambda code: {
            '000001': '平安银行',
            '300470': '日机密封',
            '600519': '贵州茅台'
        }.get(code)

        stock_codes = ['000001', '300470', '600519']

        result = self.service.batch_get_stock_names(stock_codes)

        assert len(result) == 3
        assert result['000001'] == '平安银行'
        assert result['300470'] == '日机密封'
        assert result['600519'] == '贵州茅台'

        # 验证每个股票代码都被调用了一次
        assert mock_get_stock_name.call_count == 3

    @patch('src.services.stock_service.StockService.get_stock_name')
    def test_batch_get_stock_names_with_failures(self, mock_get_stock_name):
        """测试批量获取股票名称包含失败情况"""
        mock_get_stock_name.side_effect = lambda code: {
            '000001': '平安银行',
            '300470': None,  # 获取失败
            '600519': '贵州茅台'
        }.get(code)

        stock_codes = ['000001', '300470', '600519']

        result = self.service.batch_get_stock_names(stock_codes)

        assert len(result) == 3
        assert result['000001'] == '平安银行'
        assert result['300470'] is None
        assert result['600519'] == '贵州茅台'

    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种边界情况下的错误处理

        # 空股票代码
        with patch('src.services.stock_service.standardize_stock_code') as mock_standardize:
            mock_standardize.return_value = None
            result = self.service.get_stock_name("")
            assert result is None

        # 无效股票代码格式
        result = self.service.validate_stock_code("abc123")
        assert result is False

        # 不存在的文件
        result = self.service.get_stock_list_from_file("/nonexistent/file.csv")
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])