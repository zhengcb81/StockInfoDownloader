"""
Download Helper Classes
Provides extracted responsibilities from UnifiedDownloader for better separation of concerns.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.config_constants import ConfigConstants
from src.core.logger import get_logger
from src.interfaces.downloader_interface import IBrowserStrategy
from src.web.browser_strategy import BrowserStrategy

logger = get_logger(__name__)


class KeywordMatcher:
    """Handles keyword matching for filtering download items."""

    def matches(self, text: str, keywords: Optional[List[str]]) -> bool:
        """
        Check if text matches any of the given keywords.

        Args:
            text: Text to check
            keywords: List of keywords to match against

        Returns:
            bool: True if text matches any keyword or keywords is empty/None
        """
        if not keywords:
            return True
        cleaned_text = "".join(text.split()).lower()
        for k in keywords:
            ck = "".join(k.split()).lower()
            # 1. Try partial match
            if ck in cleaned_text:
                return True

            # 2. Try date match (for truncated titles)
            # Extract 8-digit date like 20250725
            date_match = re.search(r"\d{8}", k)
            if date_match:
                date_str = date_match.group()
                if date_str in cleaned_text:
                    return True
        return False


class LinkExtractor:
    """Handles extraction of links from web pages."""

    def __init__(self, browser_strategy: BrowserStrategy):
        self.browser_strategy = browser_strategy
        self.base_url = ConfigConstants.BASE_URL

    def get_links_safe(self) -> List[Tuple[str, str]]:
        """
        Fetch link data using the most robust selector.

        Returns:
            List[Tuple[str, str]]: List of (text, url) tuples for detail links
        """
        from selenium.common.exceptions import WebDriverException
        from src.core.constants import SelectorConfig

        if not self.browser_strategy:
            return []

        results = []

        # Try using configured XPath selector (more precise)
        elements = self.browser_strategy.find_elements(
            SelectorConfig.DETAIL_LINKS, by="xpath"
        )

        # Fallback to basic a tags if XPath finds nothing
        if not elements:
            elements = self.browser_strategy.find_elements("a")

        for el in elements:
            try:
                h = self.browser_strategy.get_attribute(el, "href")
                if h and "/detail" in h:
                    t = self.browser_strategy.get_text(el).strip()
                    if t:
                        abs_url = h if h.startswith("http") else self.base_url + h
                        results.append((t, abs_url))
            except (WebDriverException, AttributeError, ValueError):
                # Element may be stale or not accessible
                continue
        return results


class PaginationHandler:
    """Handles pagination navigation."""

    def __init__(self, browser_strategy: BrowserStrategy):
        self.browser_strategy = browser_strategy
        # 翻页行为计数器 (E2E 测试用)
        self.page_turns: int = 0  # 翻页次数

    def go_to_next_page(self) -> bool:
        """
        Navigate to the next page.

        Returns:
            bool: True if successfully navigated to next page, False if no more pages
        """
        result = self.browser_strategy.go_to_next_page()
        if result:
            self.page_turns += 1
            logger.info(f"Page turn successful, total turns: {self.page_turns}")
        return result

    def wait_after_page_change(self) -> None:
        """Wait for pagination interval."""
        time.sleep(ConfigConstants.get_timeout("pagination_wait"))

    def reset_counters(self) -> None:
        """重置翻页计数器"""
        self.page_turns = 0


class DownloadHistoryTracker:
    """Tracks download history."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def add_record(
        self,
        stock_code: str,
        stock_name: Optional[str],
        file_name: str,
        file_path: str,
        status: str = "success",
    ) -> None:
        """Add a download record to history."""
        self.history.append(
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "file_name": file_name,
                "file_path": file_path,
                "timestamp": datetime.now().isoformat(),
                "status": status,
            }
        )

    def get_history(self) -> List[Dict[str, Any]]:
        """Get download history."""
        return self.history

    def clear(self) -> None:
        """Clear download history."""
        self.history.clear()
