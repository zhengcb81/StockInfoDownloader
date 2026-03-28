#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试映射获取能力
验证从本地和网络获取 org_id 和 stock_name 的功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_get_stock_name_from_tencent():
    """测试从腾讯财经接口获取股票名称"""
    from src.services.stock_service import StockService

    service = StockService()

    # 测试多个股票代码
    test_cases = [
        ("300470", "中密控股"),
        ("301611", "珂玛科技"),
        ("000001", "平安银行"),
    ]

    for stock_code, expected_name in test_cases:
        name = service._get_name_from_tencent(stock_code)
        print(f"[TEST] {stock_code}: {name}")
        assert name is not None, f"Failed to get stock name for {stock_code}"
        # 腾讯接口返回的是中文，需要确保能正确解析
        assert len(name) > 0, f"Stock name is empty for {stock_code}"

    print("[PASS] Tencent stock name retrieval works!")


def test_get_org_id_from_web():
    """测试从网络爬取 org_id"""
    from src.services.orgid_service import OrgIdService

    service = OrgIdService()

    # 测试从网络获取 org_id
    org_id = service.get_org_id("300470", headless=True)
    print(f"[TEST] Org_id for 300470: {org_id}")

    assert org_id is not None, "Failed to get org_id from web"
    assert len(org_id) > 0, "Org_id is empty"
    print("[PASS] Web org_id crawling works!")


def test_mapping_manager_with_force_crawl():
    """测试 MappingManager 强制从网络获取"""
    from src.data.mapping import MappingManager

    mm = MappingManager()

    # 测试强制刷新（从网络获取）
    org_id = mm.get_org_id("300470", force_refresh=True)
    print(f"[TEST] MappingManager org_id (force_refresh): {org_id}")

    assert org_id is not None, "Failed to get org_id with force refresh"
    print("[PASS] MappingManager force refresh works!")


def test_mapping_manager_stock_name_crawl():
    """测试 MappingManager 从网络获取股票名称"""
    from src.data.mapping import MappingManager

    mm = MappingManager()

    # 测试自动爬取股票名称
    stock_name = mm.get_stock_name("300470", auto_crawl=True)
    print(f"[TEST] MappingManager stock_name: {stock_name}")

    assert stock_name is not None, "Failed to get stock name"
    assert len(stock_name) > 0, "Stock name is empty"
    print("[PASS] MappingManager stock name crawling works!")


if __name__ == "__main__":
    print("=== Testing Real-time Mapping Retrieval ===\n")

    try:
        print("1. Testing Tencent stock name API...")
        test_get_stock_name_from_tencent()
        print()

        print("2. Testing web org_id crawling...")
        test_get_org_id_from_web()
        print()

        print("3. Testing MappingManager force refresh...")
        test_mapping_manager_with_force_crawl()
        print()

        print("4. Testing MappingManager stock name crawling...")
        test_mapping_manager_stock_name_crawl()
        print()

        print("=== All tests passed! ===")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
