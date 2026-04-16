"""Org ID crawler — fetches org_id from cninfo.com.cn for a given stock code."""
import re
import time
from typing import Any, Optional

from .constants import BASE_URL, SEARCH_URL_TEMPLATE
from .logger import log
from .string_utils import standardize_stock_code


class OrgIdCrawler:
    """Crawls org_id from cninfo.com.cn search page."""

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
        """Get org_id by crawling cninfo.com.cn."""
        code = standardize_stock_code(stock_code)
        if not code:
            log.warning(f"Invalid stock code: {stock_code}")
            return None

        try:
            if self._owns_browser:
                from .browser import PlaywrightBrowser

                self._browser = PlaywrightBrowser(headless=True, config=self._config)
                self._browser.initialize()

            try:
                return self._crawl(code)
            finally:
                if self._owns_browser and self._browser:
                    self._browser.close()
        except Exception as e:
            log.error(f"OrgId crawl failed: {e}")
            return None

    def _crawl(self, stock_code: str) -> Optional[str]:
        """Core crawl logic — search → find company link → extract org_id."""
        search_url = SEARCH_URL_TEMPLATE.format(stock_code=stock_code)
        log.info(f"Searching for org_id: {search_url}")

        if not self._browser.navigate(search_url):
            log.error("Failed to navigate to search page")
            return None

        time.sleep(3)  # Wait for SPA content

        # Find company introduction link
        elements = self._browser.find_elements("a")
        for el in elements:
            try:
                href = self._browser.get_attribute(el, "href") or ""
                text = self._browser.get_text(el).strip()

                if "/new/disclosure" in href and stock_code in href:
                    # Extract orgId from URL
                    match = re.search(r"orgId=([^&]+)", href)
                    if match:
                        org_id = match.group(1)
                        log.info(f"Found org_id: {stock_code} → {org_id}")
                        return org_id

                    # Try alternate URL pattern
                    match = re.search(r"stock[/?].*?orgId=([^&]+)", href)
                    if match:
                        org_id = match.group(1)
                        log.info(f"Found org_id (alt): {stock_code} → {org_id}")
                        return org_id
            except Exception:
                continue

        # Fallback: try to extract from page source
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
