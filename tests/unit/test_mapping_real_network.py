#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
映射模块真实网络测试
测试从网络获取 org_id 和 stock_name 的能力（不使用 Mock）
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.network
class TestMappingRealNetwork:
    """映射模块真实网络测试"""

    def test_get_stock_name_from_tencent(self):
        """测试从腾讯财经接口获取股票名称"""
        from src.services.stock_service import StockService

        service = StockService()

        test_cases = [
            ("300470", "中密控股"),
            ("301611", "珂玛科技"),
            ("000001", "平安银行"),
        ]

        for stock_code, expected_name in test_cases:
            name = service._get_name_from_tencent(stock_code)
            print(f"{stock_code}: {name}")
            assert name is not None, f"Failed to get stock name for {stock_code}"
            assert name == expected_name, f"Unexpected name for {stock_code}: {name}"

    def test_get_org_id_from_web(self):
        """测试从网络获取 org_id"""
        from src.services.orgid_service import OrgIdService

        service = OrgIdService()

        test_cases = [
            ("300470", "9900023856"),  # 中密控股
            ("301611", "9900056250"),  # 珂玛科技
        ]

        for stock_code, expected_org_id in test_cases:
            org_id = service.get_org_id(stock_code, headless=True)
            print(f"{stock_code}: {org_id}")
            assert org_id is not None, f"Failed to get org_id for {stock_code}"
            assert org_id == expected_org_id, (
                f"Unexpected org_id for {stock_code}: {org_id}"
            )

    def test_mapping_manager_get_org_id_with_force_refresh(self):
        """测试 MappingManager 强制从网络获取 org_id"""
        from src.data.mapping import MappingManager

        mm = MappingManager()
        org_id = mm.get_org_id("300470", force_refresh=True)
        print(f"MappingManager org_id: {org_id}")

        assert org_id is not None, "Failed to get org_id"
        assert org_id == "9900023856", f"Unexpected org_id: {org_id}"

    def test_mapping_manager_get_stock_name_with_crawl(self):
        """测试 MappingManager 从网络获取股票名称"""
        from src.data.mapping import MappingManager

        mm = MappingManager()
        stock_name = mm.get_stock_name("300470", auto_crawl=True)
        print(f"MappingManager stock_name: {stock_name}")

        assert stock_name is not None, "Failed to get stock_name"
        assert stock_name == "中密控股", f"Unexpected stock_name: {stock_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
