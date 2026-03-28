#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StockService 单元测试
"""

import csv
import os
import pytest
from unittest.mock import MagicMock, patch
import requests
from src.services.stock_service import StockService
from src.data.models import StockInfo


class TestStockService:
    """测试 StockService 类"""

    def setup_method(self):
        """设置测试环境"""
        self.service = StockService()

    @patch("src.services.stock_service.standardize_stock_code")
    def test_get_stock_name_success(self, mock_standardize):
        """测试成功获取股票名称"""
        mock_standardize.return_value = "000001"
        
        # Mock requests.Session.get
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"code": "000001", "value": "平安银行-PA银行"},
            {"code": "000002", "value": "万科A-WK银行"}
        ]
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.service.session, "get", return_value=mock_response):
            name = self.service.get_stock_name("000001")
            assert name == "平安银行"

    @patch("src.services.stock_service.standardize_stock_code")
    def test_get_stock_name_not_found(self, mock_standardize):
        """测试未找到股票名称"""
        mock_standardize.return_value = "000001"
        
        mock_response = MagicMock()
        mock_response.json.return_value = [{"code": "999999", "value": "Unknown"}]
        mock_response.raise_for_status.return_value = None
        
        with patch.object(self.service.session, "get", return_value=mock_response):
            name = self.service.get_stock_name("000001")
            assert name is None

    @patch("src.services.stock_service.standardize_stock_code")
    def test_get_stock_name_invalid_code(self, mock_standardize):
        """测试无效股票代码"""
        mock_standardize.return_value = None
        name = self.service.get_stock_name("invalid")
        assert name is None

    @patch.object(StockService, "get_stock_name")
    def test_get_stock_info_success(self, mock_get_name):
        """测试成功获取股票详细信息"""
        mock_get_name.return_value = "平安银行"
        
        info = self.service.get_stock_info("000001")
        
        assert info is not None
        assert info.stock_code == "000001"
        assert info.stock_name == "平安银行"
        assert info.market == "SZ"

    def test_get_market_info(self):
        """测试获取市场信息"""
        assert self.service._get_market_info("600000") == "SH"
        assert self.service._get_market_info("000001") == "SZ"
        assert self.service._get_market_info("430001") == "BJ"
        assert self.service._get_market_info("999999") is None

    def test_validate_stock_code(self):
        """测试股票代码验证"""
        assert self.service.validate_stock_code("000001") is True
        assert self.service.validate_stock_code("600000") is True
        assert self.service.validate_stock_code("12345") is False
        assert self.service.validate_stock_code("ABCDEF") is False
        assert self.service.validate_stock_code("00000A") is False

    def test_get_stock_list_from_file(self, tmp_path):
        """测试从文件获取股票列表"""
        # 创建测试CSV
        csv_file = tmp_path / "stocks.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["code", "name"])
            writer.writerow(["000001", "平安银行"])
            writer.writerow(["600000", "浦发银行"])
            writer.writerow(["invalid", "Error"])
            
        with patch("src.services.stock_service.standardize_stock_code", side_effect=lambda x: x if x.isdigit() else None):
            stocks = self.service.get_stock_list_from_file(str(csv_file))
            assert len(stocks) == 2
            assert "000001" in stocks
            assert "600000" in stocks

    @patch.object(StockService, "get_stock_name")
    def test_batch_get_stock_names(self, mock_get_name):
        """测试批量获取股票名称"""
        mock_get_name.side_effect = ["Name1", "Name2"]
        
        with patch("time.sleep"):  # 跳过延迟
            results = self.service.batch_get_stock_names(["000001", "000002"])
            assert results["000001"] == "Name1"
            assert results["000002"] == "Name2"
