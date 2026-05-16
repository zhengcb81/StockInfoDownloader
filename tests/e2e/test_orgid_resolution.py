"""E2E tests for org_id resolution via real cninfo API.

These tests make actual HTTP requests to cninfo.com.cn.
Requires network access. Marked with pytest.mark.e2e.
"""
import re

import pytest

from src.orgid import OrgIdCrawler


# Known stock_code → org_id pairs (verified against real API)
KNOWN_PAIRS = {
    "000651": "gssz0000651",   # 格力电器 (深市主板, column=szse)
    "002415": "9900012688",    # 海康威视 (中小板, column=szse)
    "300750": "GD165627",      # 宁德时代 (创业板, column=szse)
    "601318": "9900002221",    # 中国平安 (上交所, column=sse)
    "688981": "gshk0000981",   # 中芯国际 (科创板, column=sse)
    "603360": "9900030005",    # 百傲化学 (上交所, column=sse)
    "000026": "gssz0000026",   # 飞亚达   (深市主板, column=szse)
}


def _make_crawler() -> OrgIdCrawler:
    """Create an OrgIdCrawler with browser disabled (API-only testing)."""
    return OrgIdCrawler(browser_strategy=None, config={})


@pytest.mark.e2e
class TestOrgIdApiResolution:
    """Tests for _query_api method using real HTTP requests."""

    def test_resolve_szse_main_board(self):
        """深市主板 — 000651 格力电器"""
        crawler = _make_crawler()
        result = crawler._query_api("000651")
        assert result == KNOWN_PAIRS["000651"]

    def test_resolve_szse_small_board(self):
        """中小板 — 002415 海康威视"""
        crawler = _make_crawler()
        result = crawler._query_api("002415")
        assert result == KNOWN_PAIRS["002415"]

    def test_resolve_szse_chinext(self):
        """创业板 — 300750 宁德时代"""
        crawler = _make_crawler()
        result = crawler._query_api("300750")
        assert result == KNOWN_PAIRS["300750"]

    def test_resolve_sh_main_board(self):
        """上交所 — 601318 中国平安"""
        crawler = _make_crawler()
        result = crawler._query_api("601318")
        assert result == KNOWN_PAIRS["601318"]

    def test_resolve_sse_tech(self):
        """科创板 — 688981 中芯国际"""
        crawler = _make_crawler()
        result = crawler._query_api("688981")
        assert result == KNOWN_PAIRS["688981"]

    def test_resolve_bse(self):
        """北交所 — 872808 曙光数创, API 通常无法搜索到"""
        crawler = _make_crawler()
        result = crawler._query_api("872808")
        # BSE stocks are not indexed by this API; expect None
        assert result is None

    def test_invalid_code_returns_none(self):
        """无效代码应返回 None"""
        crawler = _make_crawler()
        assert crawler._query_api("000000") is None

    def test_org_id_format_valid(self):
        """验证返回的 org_id 格式：纯数字 / gssz 前缀 / gshk 前缀 / GD 前缀"""
        valid_pattern = re.compile(r"^(gssz|gshk)\d+$|^\d+$|^GD\d+$")
        crawler = _make_crawler()
        for code, expected_org_id in KNOWN_PAIRS.items():
            result = crawler._query_api(code)
            assert result is not None, f"API returned None for {code}"
            assert valid_pattern.match(result), (
                f"org_id '{result}' for {code} doesn't match expected format"
            )


@pytest.mark.e2e
class TestOrgIdCrawlerIntegration:
    """Tests for OrgIdCrawler full get_org_id flow (API path, no browser)."""

    def test_get_org_id_api_path(self):
        """验证 get_org_id 通过 API 通路正确返回"""
        crawler = _make_crawler()
        result = crawler.get_org_id("000651")
        assert result == KNOWN_PAIRS["000651"]

    def test_get_org_id_caches_result(self):
        """同一代码多次调用结果一致（API 幂等性）"""
        crawler = _make_crawler()
        first = crawler.get_org_id("002415")
        second = crawler.get_org_id("002415")
        assert first == second
        assert first == KNOWN_PAIRS["002415"]

    def test_multiple_stocks_sequential(self):
        """连续解析多只不同股票"""
        crawler = _make_crawler()
        test_codes = ["000651", "601318", "300750", "688981", "000026"]
        for code in test_codes:
            result = crawler.get_org_id(code)
            assert result is not None, f"Failed to resolve {code}"
            assert result == KNOWN_PAIRS[code], (
                f"Mismatch for {code}: got {result}, expected {KNOWN_PAIRS[code]}"
            )
