#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OrgIdService 真实网络测试
测试从网络获取 org_id 的能力（不使用 Mock）
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.network
class TestOrgIdServiceRealNetwork:
    """OrgIdService 真实网络测试"""

    def test_get_org_id_from_web(self):
        """测试从网络真实获取 org_id"""
        from src.services.orgid_service import OrgIdService

        service = OrgIdService()
        org_id = service.get_org_id("300470", headless=True)

        print(f"Org_id for 300470: {org_id}")
        assert org_id is not None, "Failed to get org_id from web"
        assert org_id == "9900023856", f"Unexpected org_id: {org_id}"

    def test_get_org_id_multiple_stocks(self):
        """测试从网络获取多个股票的 org_id"""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
