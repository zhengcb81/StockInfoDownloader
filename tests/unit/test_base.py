#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试基础模块
提供统一的测试基类、工具函数和测试数据
"""

import json
import os
import tempfile
from unittest.mock import Mock


class TestBase:
    """测试基类，提供通用的测试工具和配置"""

    def setup_method(self):
        """通用测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data = self._get_test_data()

    def teardown_method(self):
        """通用测试清理"""
        import shutil

        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _get_test_data(self):
        """获取标准测试数据"""
        return {
            "stock_codes": {
                "300470": "中密控股",
                "301611": "珂玛科技",
                "000001": "平安银行",
                "600519": "贵州茅台",
                "430001": "北交所测试",
            },
            "org_ids": {
                "300470": "9900023856",
                "301611": "9900041611",
                "000001": "9900000001",
                "600519": "9900010519",
            },
            "market_info": {
                "SH": ["600519", "601318"],  # 上海
                "SZ": ["000001", "300470"],  # 深圳
                "BJ": ["430001", "830001"],  # 北京
            },
        }

    def create_test_mapping_file(self, filename="test_mapping.json"):
        """创建测试映射文件"""
        mapping_data = {}
        for code, name in self.test_data["stock_codes"].items():
            if code in self.test_data["org_ids"]:
                mapping_data[code] = {
                    "org_id": self.test_data["org_ids"][code],
                    "name": name,
                }

        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)

        return file_path

    def create_test_csv_file(self, filename="test_stocks.csv"):
        """创建测试CSV文件"""
        import csv

        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["stock_code", "stock_name"])
            for code, name in self.test_data["stock_codes"].items():
                writer.writerow([code, name])

        return file_path

    def mock_requests_session(self, mock_get=None, mock_post=None):
        """创建mock的requests session"""
        mock_session = Mock()

        if mock_get:
            mock_session.get = mock_get
        else:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = []
            mock_session.get.return_value = mock_response

        if mock_post:
            mock_session.post = mock_post

        return mock_session

    def mock_web_driver(self):
        """创建mock的web driver"""
        mock_driver = Mock()
        mock_driver.current_url = "https://www.cninfo.com.cn/new/investor/investor?stockCode=300470&orgId=9900023856"
        mock_driver.find_elements.return_value = []
        return mock_driver

    def mock_anti_crawler(self):
        """创建mock的反爬虫策略"""
        mock_anti_crawler = Mock()
        mock_anti_crawler.apply_anti_detection.return_value = None
        mock_anti_crawler.random_delay.return_value = None
        mock_anti_crawler.simulate_human_behavior.return_value = None
        return mock_anti_crawler


class StockServiceTestBase(TestBase):
    """StockService测试基类"""

    def setup_method(self):
        """StockService测试设置"""
        super().setup_method()
        self.stock_service = None  # 子类需要初始化具体的service

    def mock_stock_api_response(self, stock_code, stock_name):
        """mock股票API响应"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {"code": stock_code, "value": f"{stock_name}-测试股票"}
        ]
        return mock_response


class DownloadServiceTestBase(TestBase):
    """DownloadService测试基类"""

    def setup_method(self):
        """DownloadService测试设置"""
        super().setup_method()
        self.save_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(self.save_dir, exist_ok=True)
        self.download_service = None  # 子类需要初始化具体的service

    def create_test_pdf_file(self, filename="test.pdf"):
        """创建测试PDF文件"""
        file_path = os.path.join(self.save_dir, filename)
        # 创建空的PDF文件（实际测试中可能需要真实内容）
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\n%fake pdf content")
        return file_path


class OrgIdServiceTestBase(TestBase):
    """OrgIdService测试基类"""

    def setup_method(self):
        """OrgIdService测试设置"""
        super().setup_method()
        self.orgid_service = None  # 子类需要初始化具体的service

    def mock_web_driver_with_org_id(self, org_id="9900023856"):
        """创建包含orgId的mock web driver"""
        mock_driver = self.mock_web_driver()
        mock_driver.current_url = f"https://www.cninfo.com.cn/new/investor/investor?stockCode=300470&orgId={org_id}"

        # 创建包含orgId的script元素
        mock_script = Mock()
        mock_script.get_attribute.return_value = "innerHTML"
        mock_script.get_attribute.side_effect = lambda attr: {
            "innerHTML": f'var config = {{"orgId": "{org_id}"}};'
        }.get(attr)

        mock_driver.find_elements.return_value = [mock_script]
        return mock_driver


def assert_stock_info_equal(actual, expected, msg=""):
    """断言股票信息相等"""
    assert actual.stock_code == expected.stock_code, f"{msg}: stock_code mismatch"
    assert actual.stock_name == expected.stock_name, f"{msg}: stock_name mismatch"
    assert actual.market == expected.market, f"{msg}: market mismatch"


def assert_org_id_valid(org_id, msg=""):
    """断言组织ID格式有效"""
    assert org_id is not None, f"{msg}: org_id should not be None"
    assert isinstance(org_id, str), f"{msg}: org_id should be string"
    assert len(org_id) == 10, f"{msg}: org_id should be 10 digits"
    assert org_id.startswith("99"), f"{msg}: org_id should start with 99"
    assert org_id.isdigit(), f"{msg}: org_id should contain only digits"


def assert_stock_code_valid(stock_code, msg=""):
    """断言股票代码格式有效"""
    assert stock_code is not None, f"{msg}: stock_code should not be None"
    assert isinstance(stock_code, str), f"{msg}: stock_code should be string"
    assert len(stock_code) == 6, f"{msg}: stock_code should be 6 digits"
    assert stock_code.isdigit(), f"{msg}: stock_code should contain only digits"


# 测试数据常量
TEST_STOCK_CODES = {
    "VALID": ["300470", "000001", "600519", "430001"],
    "INVALID": ["abc123", "12345", "1234567", "", "300470A"],
    "WITH_SPACES": [" 300470 ", " 000001 "],
}

TEST_ORG_IDS = {
    "VALID": ["9900023856", "9900000001", "9900010519"],
    "INVALID": ["1234567890", "990002385", "99000238567", "abc1234567"],
}

TEST_URLS = {
    "WITH_ORG_ID": [
        "https://www.cninfo.com.cn/new/investor/investor?stockCode=300470&orgId=9900023856",
        "https://www.cninfo.com.cn/new/disclosure/stock?orgId=9900010519&stockCode=600519",
    ],
    "WITHOUT_ORG_ID": [
        "https://www.cninfo.com.cn/new/investor/investor?stockCode=300470",
        "https://example.com",
    ],
}
