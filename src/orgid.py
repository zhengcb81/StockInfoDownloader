"""Org ID resolver — fetches org_id from cninfo.com.cn for a given stock code.

Uses the cninfo announcement query API (HTTP POST) for reliable resolution,
fall back to browser-based crawling only when the API fails.
"""
import re
import time
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from . import constants as C
from .logger import log
from .string_utils import standardize_stock_code

# cninfo announcement query API — returns orgId in JSON response
_ANNOUNCEMENT_API = "https://www.cninfo.com.cn/new/hisAnnouncement/query"

_API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.cninfo.com.cn/new/fulltextSearch",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


class OrgIdCrawler:
    """Resolves org_id from cninfo.com.cn via HTTP API, with browser fallback."""

    def __init__(
        self,
        browser_strategy: Optional[Any] = None,
        strategy_type: str = "playwright",
        config: Optional[dict] = None,
    ):
        self._browser = browser_strategy
        self._owns_browser = browser_strategy is None
        self._strategy_type = strategy_type
        self._config = config or {}

    def get_org_id(self, stock_code: str) -> Optional[str]:
        """Get org_id for a stock code. Tries HTTP API first, then browser."""
        code = standardize_stock_code(stock_code)
        if not code:
            log.warning(f"Invalid stock code: {stock_code}")
            return None

        # Strategy 1: HTTP API (fast, reliable, no browser needed)
        org_id = self._query_api(code)
        if org_id:
            return org_id

        # Strategy 2: Browser-based crawl (fallback)
        log.info(f"API lookup failed for {code}, falling back to browser crawl")
        return self._crawl_via_browser(code)

    def _query_api(self, stock_code: str) -> Optional[str]:
        """Query cninfo announcement API to resolve org_id."""
        if requests is None:
            log.warning("requests library not installed, skipping API lookup")
            return None

        try:
            # Select exchange column based on stock code prefix
            column = "sse" if stock_code.startswith("6") else "szse"
            data = {
                "pageNum": "1",
                "pageSize": "5",
                "tabName": "fulltext",
                "stock": f"{stock_code},",
                "searchkey": stock_code,
                "column": column,
                "category": "category_ndbg_szsh;",
                "seDate": "",
                "sortName": "",
                "sortType": "",
                "isHL": "true",
            }
            resp = requests.post(
                _ANNOUNCEMENT_API,
                headers=_API_HEADERS,
                data=data,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()

            announcements = result.get("announcements") or []
            for ann in announcements:
                sec_code = ann.get("secCode", "")
                if sec_code == stock_code:
                    org_id = ann.get("orgId")
                    if org_id:
                        log.info(f"API resolved org_id: {stock_code} → {org_id}")
                        return org_id

            # No exact match — try first announcement if code prefix matches
            if announcements:
                first = announcements[0]
                org_id = first.get("orgId")
                sec_code = first.get("secCode", "")
                if org_id and sec_code == stock_code:
                    log.info(f"API resolved org_id (first match): {stock_code} → {org_id}")
                    return org_id

            log.debug(f"API returned no matching announcement for {stock_code}")
        except Exception as e:
            log.warning(f"API lookup failed for {stock_code}: {e}")
        return None

    def _crawl_via_browser(self, stock_code: str) -> Optional[str]:
        """Fallback: crawl org_id using browser automation."""
        try:
            if self._owns_browser:
                from .browser import PlaywrightBrowser

                self._browser = PlaywrightBrowser(headless=True, config=self._config)
                self._browser.initialize()

            try:
                return self._crawl(stock_code)
            finally:
                if self._owns_browser and self._browser:
                    self._browser.close()
        except Exception as e:
            log.error(f"Browser crawl failed: {e}")
        return None

    def _crawl(self, stock_code: str) -> Optional[str]:
        """Core crawl logic — search → find company link → extract org_id."""
        search_url = C.SEARCH_URL_TEMPLATE.format(stock_code=stock_code)
        log.info(f"Searching for org_id: {search_url}")

        if not self._browser.navigate(search_url):
            log.error("Failed to navigate to search page")
            return None

        time.sleep(C.SPA_CONTENT_WAIT)

        # Find company link using XPath selector
        elements = self._browser.find_elements(
            f"xpath=//a[contains(@href, 'new/disclosure') and contains(@href, '{stock_code}')]"
        )
        for el in elements:
            try:
                href = self._browser.get_attribute(el, "href") or ""
                if not href:
                    continue

                match = re.search(r"orgId=([^&]+)", href)
                if match:
                    org_id = match.group(1)
                    log.info(f"Found org_id: {stock_code} → {org_id}")
                    return org_id
            except Exception:
                continue

        # Fallback: extract from page source
        try:
            page_source = self._browser.get_page_source()
            match = re.search(r"orgId['\"]?\s*[:=]\s*['\"]([^'\"]+)", page_source)
            if match:
                org_id = match.group(1)
                log.info(f"Found org_id from page source: {stock_code} → {org_id}")
                return org_id
        except Exception:
            pass

        log.warning(f"Could not find org_id for {stock_code}")
        return None
