"""
测试数据管理模块
提供统一的测试数据加载和管理功能
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataManagerTool:
    """测试数据管理器工具"""

    def __init__(self, config_file: str = "tests/test_config.json"):
        """
        初始化测试数据管理器

        Args:
            config_file: 测试配置文件路径
        """
        self.config_file = Path(config_file)
        self._config_data = None

    def load_config(self) -> Dict[str, Any]:
        """
        加载测试配置

        Returns:
            Dict[str, Any]: 配置数据
        """
        if self._config_data is None:
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config_data = json.load(f)
            except FileNotFoundError:
                # 如果配置文件不存在，返回默认配置
                self._config_data = {
                    "test_companies": [
                        {
                            "stock_code": "000001",
                            "stock_name": "测试公司",
                            "expected_org_id": "9900000001",
                        }
                    ],
                    "test_settings": {
                        "headless": True,
                        "max_retries": 2,
                        "timeout": 10,
                    },
                }
        return self._config_data

    def get_test_companies(self) -> List[Dict[str, Any]]:
        """
        获取测试公司列表

        Returns:
            List[Dict[str, Any]]: 测试公司列表
        """
        config = self.load_config()
        return config.get("test_companies", [])

    def get_test_company(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """
        获取指定索引的测试公司

        Args:
            index: 公司索引

        Returns:
            Optional[Dict[str, Any]]: 测试公司数据
        """
        companies = self.get_test_companies()
        if 0 <= index < len(companies):
            return companies[index]
        return None

    def get_test_settings(self) -> Dict[str, Any]:
        """
        获取测试设置

        Returns:
            Dict[str, Any]: 测试设置
        """
        config = self.load_config()
        return config.get("test_settings", {})

    def get_valid_stock_code(self, index: int = 0) -> str:
        """
        获取有效的股票代码

        Args:
            index: 公司索引

        Returns:
            str: 股票代码
        """
        company = self.get_test_company(index)
        return company["stock_code"] if company else "000001"

    def get_valid_stock_name(self, index: int = 0) -> str:
        """
        获取有效的股票名称

        Args:
            index: 公司索引

        Returns:
            str: 股票名称
        """
        company = self.get_test_company(index)
        return company["stock_name"] if company else "测试公司"

    def get_expected_org_id(self, index: int = 0) -> str:
        """
        获取期望的组织ID

        Args:
            index: 公司索引

        Returns:
            str: 组织ID
        """
        company = self.get_test_company(index)
        return company["expected_org_id"] if company else "9900000001"


# 全局测试数据管理器实例
test_data_manager = DataManagerTool()


def get_test_stock_code(index: int = 0) -> str:
    """
    获取测试股票代码的便捷函数

    Args:
        index: 公司索引

    Returns:
        str: 股票代码
    """
    return test_data_manager.get_valid_stock_code(index)


def get_test_stock_name(index: int = 0) -> str:
    """
    获取测试股票名称的便捷函数

    Args:
        index: 公司索引

    Returns:
        str: 股票名称
    """
    return test_data_manager.get_valid_stock_name(index)


def get_test_org_id(index: int = 0) -> str:
    """
    获取测试组织ID的便捷函数

    Args:
        index: 公司索引

    Returns:
        str: 组织ID
    """
    return test_data_manager.get_expected_org_id(index)
