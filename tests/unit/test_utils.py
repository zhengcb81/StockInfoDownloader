#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试专用工具和配置系统
提供测试专用的配置、数据和工具函数，提高测试隔离性
"""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional


class TestConfig:
    """测试专用配置类"""

    # 基础配置
    BASE_URL = "https://test.cninfo.com.cn"
    TEST_TIMEOUT = 10  # 测试超时时间（秒）
    MAX_RETRIES = 3  # 最大重试次数

    # 测试数据配置
    TEST_STOCK_CODES = {
        "300470": "中密控股",
        "301611": "珂玛科技",
        "000001": "平安银行",
        "600519": "贵州茅台",
        "430001": "北交所测试",
    }

    TEST_ORG_IDS = {
        "300470": "9900023856",
        "301611": "9900041611",
        "000001": "9900000001",
        "600519": "9900010519",
    }

    # Mock配置
    MOCK_RESPONSES = {
        "stock_name": {
            "300470": "日机密封",
            "000001": "平安银行",
            "600519": "贵州茅台",
        },
        "org_id": {
            "300470": "9900023856",
            "000001": "9900000001",
            "600519": "9900010519",
        },
    }

    # 文件路径配置
    @classmethod
    def get_test_temp_dir(cls) -> str:
        """获取测试临时目录"""
        return tempfile.mkdtemp(prefix="stock_test_")

    @classmethod
    def get_test_mapping_file(cls, temp_dir: str) -> str:
        """创建测试映射文件"""
        mapping_data = {}
        for code, name in cls.TEST_STOCK_CODES.items():
            if code in cls.TEST_ORG_IDS:
                mapping_data[code] = {"org_id": cls.TEST_ORG_IDS[code], "name": name}

        file_path = os.path.join(temp_dir, "test_mapping.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)

        return file_path

    @classmethod
    def get_test_csv_file(cls, temp_dir: str) -> str:
        """创建测试CSV文件"""
        import csv

        file_path = os.path.join(temp_dir, "test_stocks.csv")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["stock_code", "stock_name"])
            for code, name in cls.TEST_STOCK_CODES.items():
                writer.writerow([code, name])

        return file_path


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_stock_info(
        stock_code: str,
        stock_name: Optional[str] = None,
        org_id: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成股票信息测试数据"""
        if stock_name is None:
            stock_name = TestConfig.TEST_STOCK_CODES.get(
                stock_code, f"测试股票{stock_code}"
            )

        if org_id is None:
            org_id = TestConfig.TEST_ORG_IDS.get(stock_code, "9900000000")

        if market is None:
            if stock_code.startswith("6"):
                market = "SH"
            elif stock_code.startswith("0") or stock_code.startswith("3"):
                market = "SZ"
            elif stock_code.startswith("4") or stock_code.startswith("8"):
                market = "BJ"
            else:
                market = "UNKNOWN"

        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "org_id": org_id,
            "market": market,
        }

    @staticmethod
    def generate_mock_response(data_type: str, key: str) -> Any:
        """生成mock响应数据"""
        return TestConfig.MOCK_RESPONSES.get(data_type, {}).get(key)

    @staticmethod
    def generate_error_response(
        error_type: str, message: str = "测试错误"
    ) -> Dict[str, Any]:
        """生成错误响应数据"""
        error_responses = {
            "network": {"error": "NetworkError", "message": message, "code": 500},
            "timeout": {"error": "TimeoutError", "message": message, "code": 408},
            "validation": {"error": "ValidationError", "message": message, "code": 400},
        }

        return error_responses.get(
            error_type, {"error": "UnknownError", "message": message, "code": 500}
        )


class EnvironmentManager:
    """测试环境管理器"""

    def __init__(self):
        self.temp_dirs = []
        self.temp_files = []

    def create_temp_dir(self, prefix: str = "test_") -> str:
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir

    def create_temp_file(
        self, content: str = "", suffix: str = ".txt", prefix: str = "test_"
    ) -> str:
        """创建临时文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, prefix=prefix, delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_file = f.name

        self.temp_files.append(temp_file)
        return temp_file

    def cleanup(self):
        """清理测试环境"""
        import shutil

        # 删除临时文件
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass

        # 删除临时目录
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception:
                pass

        self.temp_dirs.clear()
        self.temp_files.clear()


# 全局测试配置实例
test_config = TestConfig()
test_data_generator = TestDataGenerator()


# 测试数据常量
def get_test_stock_codes() -> List[str]:
    """获取测试股票代码列表"""
    return list(TestConfig.TEST_STOCK_CODES.keys())


def get_test_org_ids() -> List[str]:
    """获取测试组织ID列表"""
    return list(TestConfig.TEST_ORG_IDS.values())


def get_test_market_codes() -> Dict[str, List[str]]:
    """获取按市场分类的测试股票代码"""
    market_codes = {"SH": [], "SZ": [], "BJ": []}

    for code in TestConfig.TEST_STOCK_CODES.keys():
        if code.startswith("6"):
            market_codes["SH"].append(code)
        elif code.startswith("0") or code.startswith("3"):
            market_codes["SZ"].append(code)
        elif code.startswith("4") or code.startswith("8"):
            market_codes["BJ"].append(code)

    return market_codes
