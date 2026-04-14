#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrgIdService 真实网络测试
测试从网络获取 org_id 的能力（不使用 Mock）

注意：测试用例中的股票代码分为两类：
1. 映射表中已有的（300470, 301611 等）- 验证基本功能
2. 映射表中没有的（600519, 300750, 601398 等）- 验证真实爬取能力
   这些股票的 orgId 格式多样（gssh/GD/jjxt 前缀等），确保覆盖各种格式
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 映射表中预设的股票
PRESET_STOCKS = {"000001", "000002", "000858", "002415", "002853", "300470", "301589", "301611"}

# 不在映射表中的股票，用于验证真实爬取（覆盖各种 orgId 格式）
CRAWL_ONLY_STOCKS = {
    "600519": "gssh0600519",   # 贵州茅台 - gssh 前缀
    "300750": "GD165627",      # 宁德时代 - GD 前缀
    "601398": "jjxt0000019",   # 工商银行 - jjxt 前缀
}


@pytest.mark.network
class TestOrgIdServiceRealNetwork:
    """OrgIdService 真实网络测试 (Selenium)"""

    def test_get_org_id_from_web(self):
        """测试从网络真实获取 org_id（默认 Selenium 策略）"""
        from src.services.orgid_service import OrgIdService

        service = OrgIdService()
        org_id = service.get_org_id("300470", headless=True)

        print(f"Org_id for 300470: {org_id}")
        assert org_id is not None, "Failed to get org_id from web"
        assert org_id == "9900023856", f"Unexpected org_id: {org_id}"

    def test_get_org_id_multiple_stocks(self):
        """测试从网络获取多个股票的 org_id（默认 Selenium 策略）"""
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


@pytest.mark.network
class TestOrgIdServicePlaywrightRealNetwork:
    """OrgIdService 真实网络测试 (Playwright)"""

    def test_get_org_id_playwright_single(self):
        """测试 Playwright 策略获取 org_id"""
        from src.services.orgid_service import OrgIdService

        service = OrgIdService(strategy_type="playwright")
        org_id = service.get_org_id("300470", headless=True)

        print(f"[Playwright] Org_id for 300470: {org_id}")
        assert org_id is not None, "Failed to get org_id with Playwright"
        assert org_id == "9900023856", f"Unexpected org_id: {org_id}"

    def test_get_org_id_playwright_multiple_stocks(self):
        """测试 Playwright 策略获取多个股票的 org_id（含各种 orgId 格式）"""
        from src.services.orgid_service import OrgIdService

        test_cases = [
            ("300470", "9900023856"),   # 中密控股 - 纯数字
            ("301611", "9900056250"),   # 珂玛科技 - 纯数字
            ("000001", "gssz0000001"),  # 平安银行 - gssz 前缀
        ]

        for stock_code, expected_org_id in test_cases:
            service = OrgIdService(strategy_type="playwright")
            org_id = service.get_org_id(stock_code, headless=True)
            print(f"[Playwright] {stock_code}: {org_id}")
            assert org_id is not None, (
                f"Failed to get org_id for {stock_code} with Playwright"
            )
            assert org_id == expected_org_id, (
                f"Unexpected org_id for {stock_code}: {org_id}"
            )

    def test_get_org_id_playwright_crawl_only_stocks(self):
        """测试 Playwright 爬取映射表中不存在的股票（真实爬取验证）"""
        from src.services.orgid_service import OrgIdService

        for stock_code, expected_org_id in CRAWL_ONLY_STOCKS.items():
            service = OrgIdService(strategy_type="playwright")
            org_id = service.get_org_id(stock_code, headless=True)
            print(f"[Playwright] {stock_code} (crawl-only): {org_id}")
            assert org_id is not None, (
                f"Failed to crawl org_id for {stock_code} with Playwright"
            )
            assert org_id == expected_org_id, (
                f"Unexpected org_id for {stock_code}: {org_id} (expected {expected_org_id})"
            )


@pytest.mark.network
class TestOrgIdServicePlaywrightViaMappingManager:
    """通过 MappingManager 端到端测试 Playwright 爬取（验证真实爬取链路）"""

    def test_mapping_manager_crawl_missing_stock(self):
        """测试 MappingManager 对映射表中不存在的股票自动爬取"""
        from src.data.mapping import MappingManager
        import tempfile
        import os

        # 使用临时映射文件（空的），确保不会命中缓存
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{}")
            temp_path = f.name

        try:
            mm = MappingManager(
                mapping_file=temp_path,
                browser_strategy_type="playwright",
            )

            # 600519 不在空映射表中，必须通过 Playwright 爬取
            org_id = mm.get_org_id("600519")
            print(f"[MappingManager→Playwright] 600519: {org_id}")
            assert org_id is not None, "MappingManager failed to crawl org_id"
            assert org_id == "gssh0600519", f"Unexpected org_id: {org_id}"
        finally:
            os.unlink(temp_path)

    def test_mapping_manager_crawl_various_formats(self):
        """测试 MappingManager 爬取各种 orgId 格式的股票"""
        from src.data.mapping import MappingManager
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{}")
            temp_path = f.name

        try:
            mm = MappingManager(
                mapping_file=temp_path,
                browser_strategy_type="playwright",
            )

            for stock_code, expected_org_id in CRAWL_ONLY_STOCKS.items():
                org_id = mm.get_org_id(stock_code)
                print(
                    f"[MappingManager→Playwright] {stock_code}: "
                    f"{org_id} (expected {expected_org_id})"
                )
                assert org_id is not None, (
                    f"Failed for {stock_code}"
                )
                assert org_id == expected_org_id, (
                    f"Wrong org_id for {stock_code}: {org_id}"
                )
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
