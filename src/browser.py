"""Playwright browser wrapper — clean, focused interface for browser automation.

No abstract base class, no factory pattern, no adapter layer. Just Playwright.
"""
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
except ImportError:
    sync_playwright = None  # type: ignore

from . import constants as C
from .exceptions import BrowserError
from .logger import log


class PlaywrightBrowser:
    """Thin wrapper around Playwright for the download workflow."""

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        if sync_playwright is None:
            raise BrowserError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        self.headless = headless
        self.download_dir = download_dir or C.DEFAULT_SAVE_DIR
        self.config = config or {}

        self._pw = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Start Playwright and open a browser."""
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            self._context = self._browser.new_context(
                user_agent=random.choice(C.USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                accept_downloads=True,
                extra_http_headers={
                    "Referer": C.BASE_URL,
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            # Anti-detection scripts
            self._context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true});

                // Mock PluginArray with realistic structure
                const mockPlugin = { name: 'Chrome PDF Plugin', description: '', filename: 'internal-pdf-viewer', length: 1 };
                const mockPlugin2 = { name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', length: 1 };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [mockPlugin, mockPlugin2],
                    configurable: true
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                    configurable: true
                });

                // Remove chrome.runtime detection
                if (window.chrome && window.chrome.runtime) {
                    Object.defineProperty(window.chrome.runtime, 'id', {get: () => undefined});
                }
            """)
            self._page = self._context.new_page()
            log.info("Playwright browser initialized")
            return True
        except Exception as e:
            log.error(f"Browser init failed: {e}")
            raise BrowserError(f"Failed to initialize browser: {e}")

    def close(self) -> None:
        """Shut down browser and Playwright."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception as e:
            log.debug(f"Browser close error: {e}")
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None

    def restart(self) -> bool:
        """Restart the browser."""
        self.close()
        return self.initialize()

    def cleanup(self) -> None:
        """Alias for close() — for compatibility."""
        self.close()

    @property
    def page(self) -> Page:
        if not self._page:
            raise BrowserError("Browser not initialized. Call initialize() first.")
        return self._page

    # ── Navigation ────────────────────────────────────────────────────

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """Navigate to a URL."""
        try:
            self.page.goto(url, wait_until=wait_until, timeout=C.PAGE_LOAD_TIMEOUT * 1000)
            # Random anti-crawler delay
            delay_range = self.config.get("anti_crawler", {}).get(
                "random_delay_range", list(C.DEFAULT_DELAY_RANGE)
            )
            time.sleep(random.uniform(*delay_range))
            return True
        except Exception as e:
            log.error(f"Navigation failed for {url}: {e}")
            return False

    def get_current_url(self) -> str:
        return self.page.url

    def get_page_source(self) -> str:
        return self.page.content()

    # ── Element Interaction ───────────────────────────────────────────

    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """Find elements by CSS or XPath selector."""
        try:
            if by == "xpath":
                return self.page.query_selector_all(f"xpath={selector}")
            return self.page.query_selector_all(selector)
        except Exception as e:
            log.debug(f"find_elements failed ({selector}): {e}")
            return []

    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """Find a single element."""
        try:
            if by == "xpath":
                return self.page.query_selector(f"xpath={selector}")
            return self.page.query_selector(selector)
        except Exception:
            return None

    def get_text(self, element: Any) -> str:
        """Get text content of an element."""
        try:
            return element.text_content() or ""
        except Exception:
            return ""

    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """Get an attribute value from an element."""
        try:
            return element.get_attribute(attribute)
        except Exception:
            return None

    def click(self, element: Any) -> bool:
        """Click an element."""
        try:
            element.click()
            return True
        except Exception as e:
            log.debug(f"click failed: {e}")
            return False

    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript in the page."""
        try:
            return self.page.evaluate(script, *args)
        except Exception as e:
            log.debug(f"Script execution failed: {e}")
            return None

    # ── Waiting ───────────────────────────────────────────────────────

    def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        by: str = "css",
        state: str = "visible",
    ) -> bool:
        """Wait for an element to appear."""
        try:
            if by == "xpath":
                selector = f"xpath={selector}"
            self.page.wait_for_selector(selector, timeout=timeout * 1000, state=state)
            return True
        except Exception:
            return False

    def wait_for_download_ready(self, timeout: int = 30) -> bool:
        """Wait for page to be ready for download."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    # ── Screenshot ────────────────────────────────────────────────────

    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """Take a screenshot."""
        try:
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=save_path)
            return self.page.screenshot()
        except Exception:
            return None

    # ── Download ──────────────────────────────────────────────────────

    def _try_direct_download(self, url: str, save_path: str) -> Optional[bool]:
        """Try strategy 1: navigate to detail page and capture automatic download."""
        try:
            with self.page.expect_download(timeout=10000) as dl_info:
                self.page.goto(
                    url, wait_until="domcontentloaded", timeout=C.PAGE_LOAD_TIMEOUT * 1000
                )
            download = dl_info.value
            download.save_as(save_path)
            if Path(save_path).stat().st_size > C.MIN_FILE_SIZE:
                log.info(f"Direct download successful: {save_path}")
                return True
        except Exception as e:
            error_msg = str(e)
            if "Download is starting" in error_msg:
                # Download was triggered but goto threw — try to capture it
                try:
                    download = self.page.wait_for_event("download", timeout=5000)
                    download.save_as(save_path)
                    if Path(save_path).stat().st_size > C.MIN_FILE_SIZE:
                        log.info(f"Captured started download: {save_path}")
                        return True
                except Exception:
                    pass
            log.debug(f"Direct download failed, trying button: {error_msg[:100]}")
        return None

    def _try_button_download(self, url: str, save_path: str, timeout: int) -> Optional[bool]:
        """Try strategy 2: find and click a download button on the detail page."""
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        # Wait for download button to appear (SPA may not have rendered it yet)
        btn_selectors = [
            "button:has-text('公告下载')",
            "a:has-text('下载')",
            ".download-link",
            "button:has-text('下载')",
            "a:has-text('公告下载')",
        ]
        btn = None
        for selector in btn_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=8000, state="visible")
                btn = self.page.query_selector(selector)
                if btn:
                    break
            except Exception:
                continue

        if not btn:
            log.error("Download button not found")
            return False

        try:
            with self.page.expect_download(timeout=timeout * 1000) as dl_info:
                btn.click()
                log.info("Clicked download button, waiting for file...")
            download = dl_info.value
            download.save_as(save_path)
            if Path(save_path).stat().st_size > C.MIN_FILE_SIZE:
                log.info(f"Button download successful: {save_path}")
                return True
            else:
                log.warning(f"Downloaded file too small: {save_path}")
                return False
        except Exception as e:
            log.debug(f"Button download failed: {e}")
        return None

    def download_file(self, url: str, save_path: str, timeout: int = 60) -> bool:
        """Download a file from a detail page URL.

        cninfo has two download modes:
        1. Direct download — navigation triggers immediate PDF download
        2. Button download — detail page has a "公告下载" button
        We try both.
        """
        try:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            log.info(f"Attempting download: {url}")

            # Strategy 1: direct download
            result = self._try_direct_download(url, save_path)
            if result is True:
                return True

            # Strategy 2: button click
            result = self._try_button_download(url, save_path, timeout)
            if result is True:
                return True

            return False
        except Exception as e:
            log.error(f"Download failed for {url}: {e}")
            return False

    # ── Pagination ────────────────────────────────────────────────────

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """Click the 'next page' button."""
        try:
            btn = self.page.query_selector(C.NEXT_PAGE_CSS)
            if btn and not btn.is_disabled():
                btn.click()
                time.sleep(C.PAGINATION_WAIT)
                return True
            return False
        except Exception:
            return False

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """Navigate to a specific page number."""
        try:
            pages = self.page.query_selector_all(".el-pager li.number")
            for pg in pages:
                if pg.text_content() == str(page_number):
                    pg.click()
                    time.sleep(C.PAGINATION_WAIT)
                    return True
            return False
        except Exception:
            return False

    def go_to_last_page(self) -> bool:
        """Navigate to the last page using the .btn-last button.

        Falls back to clicking the last visible page number if .btn-last
        is not available.
        """
        try:
            # Primary: click the dedicated "last page" button
            btn = self.page.query_selector(C.LAST_PAGE_CSS)
            if btn and not btn.is_disabled():
                btn.click()
                time.sleep(C.PAGINATION_WAIT)
                return True

            # Fallback: get total pages from page info and navigate directly
            info = self.get_current_page_info()
            total = info.get("total_pages", 1)
            if total > 1:
                return self.go_to_page(total)
            return False
        except Exception:
            return False

    def has_next_page(self, timeout: int = 5) -> bool:
        """Check if there is a next page available."""
        try:
            btn = self.page.query_selector(C.NEXT_PAGE_CSS)
            return btn is not None and not btn.is_disabled()
        except Exception:
            return False

    def get_current_page_info(self) -> Dict[str, Any]:
        """Get current page number and total pages.

        The cninfo site uses Element UI pagination. The pager component
        (.el-pager) contains <li> elements for page numbers. The last <li>
        always shows the final page number, even when the full list is
        ellipsis-truncated (e.g. 1 2 3 4 ... 38).

        We also check .el-pagination__total as a fallback.
        """
        try:
            info = self.page.evaluate("""
                () => {
                    const pager = document.querySelector('.el-pager');
                    const active = pager ? pager.querySelector('.active') : null;

                    // Strategy 1: last <li> in .el-pager gives the final page number
                    let totalFromPager = 1;
                    if (pager) {
                        const lis = pager.querySelectorAll('li.number');
                        if (lis.length > 0) {
                            const lastLi = parseInt(lis[lis.length - 1].textContent);
                            if (!isNaN(lastLi)) totalFromPager = lastLi;
                        }
                    }

                    // Strategy 2: .el-pagination__total fallback
                    const el = document.querySelector('.el-pagination__total');
                    const totalText = el ? el.textContent : '';
                    const totalMatch = totalText.match(/\\d+/);
                    const totalFromText = totalMatch ? parseInt(totalMatch[0]) : 0;

                    // Use pager result (more reliable), fall back to text
                    const total_pages = totalFromPager > 1 ? totalFromPager
                                      : totalFromText > 0 ? totalFromText
                                      : 1;

                    return {
                        current_page: active ? parseInt(active.textContent) : 1,
                        total_pages: total_pages,
                    };
                }
            """)
            return info if info else {"current_page": 1, "total_pages": 1}
        except Exception:
            return {"current_page": 1, "total_pages": 1}

    def is_healthy(self) -> bool:
        """Check if the browser is still responsive."""
        try:
            if not self._page or not self._browser:
                return False
            self.page.evaluate("1+1")
            return True
        except Exception:
            return False

    def clear_cookies(self) -> None:
        """Clear all cookies for anti-crawler rotation."""
        try:
            if self._context:
                self._context.clear_cookies()
                log.debug("Cookies cleared")
        except Exception:
            pass

    def random_delay(self, min_seconds: float = 0.5, max_seconds: float = 3.0) -> None:
        """Sleep for a random duration to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
