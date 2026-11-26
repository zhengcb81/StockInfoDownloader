"""Playwright browser wrapper — clean, focused interface for browser automation.

No abstract base class, no factory pattern, no adapter layer. Just Playwright.
"""

import os
import random
import time
from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional, Tuple

try:
    from playwright.sync_api import (
        sync_playwright, Browser, Page, BrowserContext,
        TimeoutError as PlaywrightTimeoutError,
    )
except ImportError:
    sync_playwright = None  # type: ignore
    PlaywrightTimeoutError = TimeoutError

from . import constants as C
from .exceptions import BrowserDownloadError, BrowserError, PaginationError
from .feedback_files import native_path
from .logger import log
from .runtime_steps import checkpoint, exception_types


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
            import socket as _socket

            self._pw = sync_playwright().start()
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
            # Resolve every critical cninfo host independently via system DNS.
            # Hardcoded fallback IPs are intentionally forbidden: when system
            # DNS fails the browser must fail fast so callers observe a typed
            # INFRASTRUCTURE_FAIL — never silently alias www's IP to static's,
            # because that has been confirmed to keep SPA assets unreachable.
            #
            # CW-2.27H / Phase 8 hardening: only www and static are CRITICAL
            # for the SPA navigation + PDF transport pipeline. The bare host
            # ``cninfo.com.cn`` is not used by any actual request and often
            # fails to resolve (Akamai CDN routing quirk); treat it as
            # best-effort and warn rather than kill browser initialisation.
            _CRITICAL_HOSTS = ("www.cninfo.com.cn", "static.cninfo.com.cn")
            _OPTIONAL_HOSTS = ("cninfo.com.cn",)
            resolver_rules = []
            for host in _CRITICAL_HOSTS:
                try:
                    ip = _socket.getaddrinfo(host, 443)[0][4][0]
                except OSError as exc:
                    raise BrowserError(
                        f"critical cninfo host unresolved: {host} ({exc})"
                    ) from exc
                resolver_rules.append(f"MAP {host} {ip}")
            for host in _OPTIONAL_HOSTS:
                try:
                    ip = _socket.getaddrinfo(host, 443)[0][4][0]
                    resolver_rules.append(f"MAP {host} {ip}")
                except OSError:
                    log.debug(f"optional cninfo host unresolved (continuing): {host}")
            launch_args.append(f"--host-resolver-rules={', '.join(resolver_rules)}")
            self._browser = self._pw.chromium.launch(
                headless=self.headless,
                args=launch_args,
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
            raise BrowserError(f"Failed to initialize browser: {e}") from e

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
            self.page.goto(
                url, wait_until=wait_until, timeout=C.PAGE_LOAD_TIMEOUT * 1000
            )
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

    # ── SPA tab scope ─────────────────────────────────────────────────
    #
    # cninfo renders every tab into the DOM and hides the inactive panes.  A
    # page-wide ``a[href*=detail]`` query therefore returns documents from tabs
    # the caller never selected.  These accessors are the only place that knows
    # the pane markup; callers ask for "the active tab" instead of re-deriving
    # a selector.

    _PANE_SELECTOR = '.el-tab-pane, .tab-pane, [role="tabpanel"]'
    _MENU_SELECTOR = '.el-menu-item, .el-tabs__item, [role="tab"]'

    #: ``select_menu_item`` outcomes.
    TAB_ACTIVE = "active"
    TAB_INACTIVE = "inactive"
    TAB_UNKNOWN = "unknown"
    TAB_MISSING = "missing"

    def select_menu_item(self, text: str) -> str:
        """Click a menu item and wait briefly for an asynchronous selection.

        Returns one of ``TAB_ACTIVE`` / ``TAB_INACTIVE`` / ``TAB_UNKNOWN`` /
        ``TAB_MISSING``. The wait uses the existing SPA tab-switch timeout; it
        does not infer success from the click itself. A state without a
        recognised selection marker remains ``unknown`` for the caller's
        existing active-pane link check.
        """
        args = [self._MENU_SELECTOR, text]
        click_script = """
        ([menuSelector, label]) => {
            const items = Array.from(document.querySelectorAll(menuSelector));
            const target = items.find(
                (item) => (item.textContent || '').trim() === label
            );
            if (!target) return 'missing';
            target.click();
            return 'clicked';
        }
        """
        state_script = """
        ([menuSelector, label]) => {
            const items = Array.from(document.querySelectorAll(menuSelector));
            const target = items.find(
                (item) => (item.textContent || '').trim() === label
            );
            if (!target) return 'missing';
            const isSelected = (item) =>
                item.classList.contains('is-active')
                || item.getAttribute('aria-selected') === 'true';
            const selected = items.filter(isSelected);
            if (selected.length === 0) return 'unknown';
            return selected.includes(target) ? 'active' : 'inactive';
        }
        """
        wait_for_active_script = """
        ([menuSelector, label]) => {
            const items = Array.from(document.querySelectorAll(menuSelector));
            const target = items.find(
                (item) => (item.textContent || '').trim() === label
            );
            if (!target) return true;
            return target.classList.contains('is-active')
                || target.getAttribute('aria-selected') === 'true';
        }
        """
        try:
            clicked = self.page.evaluate(click_script, args)
            if clicked == self.TAB_MISSING:
                return self.TAB_MISSING

            value = self.page.evaluate(state_script, args)
            if value == self.TAB_INACTIVE:
                try:
                    timeout_ms = max(1, int(C.SPA_TAB_SWITCH_WAIT * 1000))
                    self.page.wait_for_function(
                        wait_for_active_script, args, timeout=timeout_ms
                    )
                except PlaywrightTimeoutError:
                    # Re-read below: selection may have completed at the edge
                    # of the timeout, or may remain genuinely inactive.
                    pass
                value = self.page.evaluate(state_script, args)
        except Exception as e:
            log.debug(f"select_menu_item failed ({text!r}): {e}")
            return self.TAB_MISSING

        if value in (
            self.TAB_ACTIVE,
            self.TAB_INACTIVE,
            self.TAB_UNKNOWN,
            self.TAB_MISSING,
        ):
            return value
        return self.TAB_UNKNOWN

    def find_active_tab_links(self) -> List[Tuple[str, str]]:
        """Return ``(href, text)`` for disclosure links in the visible pane.

        Visibility uses ``offsetParent``, which is false for any element hidden
        by ``display:none`` — whether that comes from an ``is-hidden`` class, an
        inline style or a framework ``v-show``.  A class-only predicate would
        miss the inline-style case and keep returning another tab's documents.

        When the page has no recognised pane container at all, the whole
        document is the active scope (there is nothing to switch away from).
        When pane containers exist but none is visible, the result is empty:
        the caller must not widen to the whole page.
        """
        script = """
        (paneSelector) => {
            const panes = Array.from(document.querySelectorAll(paneSelector));
            const visible = panes.filter((pane) => pane.offsetParent !== null);
            const roots = panes.length === 0 ? [document] : visible;
            const out = [];
            for (const root of roots) {
                const links = root.querySelectorAll(
                    'a[href*="/new/disclosure/detail"]'
                );
                for (const link of links) {
                    out.push([
                        link.getAttribute('href') || '',
                        (link.textContent || '').trim(),
                    ]);
                }
            }
            return out;
        }
        """
        try:
            raw = self.page.evaluate(script, self._PANE_SELECTOR)
        except Exception as e:
            log.debug(f"find_active_tab_links failed: {e}")
            return []
        pairs: List[Tuple[str, str]] = []
        for item in raw or []:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            href, text = item
            if isinstance(href, str) and href and isinstance(text, str) and text:
                pairs.append((href, text))
        return pairs

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

    @staticmethod
    def _save_download(download: Any, target: Path) -> None:
        temporary = None
        try:
            with NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as stream:
                temporary = Path(stream.name)
            download.save_as(temporary)
            if temporary.stat().st_size <= C.MIN_FILE_SIZE:
                raise OSError("Downloaded data is incomplete")
            os.replace(temporary, target)
        except Exception as error:
            raise BrowserDownloadError("staging", "sent") from error
        finally:
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

    def _direct_download(self, detail: Page, url: str) -> Any:
        try:
            with detail.expect_download(timeout=10000) as received:
                detail.goto(url, wait_until="domcontentloaded", timeout=C.PAGE_LOAD_TIMEOUT * 1000)
            return received.value
        except Exception as error:
            if "Download is starting" not in str(error):
                raise BrowserDownloadError("direct", "unknown") from error
            try:
                return detail.wait_for_event("download", timeout=5000)
            except Exception as unfinished:
                raise BrowserDownloadError("direct", "sent") from unfinished

    @staticmethod
    def _button_download(detail: Page, timeout: int) -> Any:
        selectors = (
            "button:has-text('公告下载')", "a:has-text('下载')", ".download-link",
            "button:has-text('下载')", "a:has-text('公告下载')",
        )
        try:
            button = next(
                (node for selector in selectors
                 if (node := detail.query_selector(selector)) and node.is_visible()),
                None,
            )
            if button is None:
                for selector in selectors:
                    try:
                        button = detail.wait_for_selector(selector, timeout=3000, state="visible")
                    except PlaywrightTimeoutError:
                        continue
                    if button:
                        break
            if button is None:
                raise LookupError("No download button was exposed")
            with detail.expect_download(timeout=timeout * 1000) as received:
                button.click()
            return received.value
        except Exception as cause:
            raise BrowserDownloadError("button", "unknown") from cause

    def download_file(self, url: str, save_path: str, timeout: int = 60) -> bool:
        """Fetch into an independent detail page and commit only complete bytes."""
        target = native_path(Path(save_path))
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            detail = self._context.new_page()
        except Exception as cause:
            raise BrowserDownloadError("setup", "not_sent") from cause
        try:
            try:
                download = self._direct_download(detail, url)
            except BrowserDownloadError as error:
                checkpoint("direct-download", "failed", sent=error.sent, cause_types=exception_types(error))
                if error.sent == "sent":
                    raise
                download = self._button_download(detail, timeout)
            self._save_download(download, target)
            return True
        finally:
            try:
                detail.close()
            except Exception as error:
                log.warning("Could not close document page exception_type=%s", type(error).__name__)

    # ── Pagination ────────────────────────────────────────────────────

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """Advance to the next page. False means the last page was observed."""
        position = self.get_current_page_info()
        current = position["current_page"]
        return self._turn_page(
            current, current + 1, "next", C.NEXT_PAGE_CSS, timeout,
            boundary=current == position["total_pages"],
        )

    def go_to_previous_page(self, timeout: int = 10) -> bool:
        """Go to the previous page. False means the first page was observed."""
        current = self.get_current_page_info()["current_page"]
        if current == 1:
            return False
        return self._turn_page(current, current - 1, "previous", C.PREV_PAGE_CSS, timeout)

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """Navigate to a specific page number."""
        position = self.get_current_page_info()
        current = position["current_page"]
        if page_number == current or not 1 <= page_number <= position["total_pages"]:
            return False
        return self._turn_page(current, page_number, "numbered", None, timeout)

    def go_to_last_page(self, timeout: int = 10) -> bool:
        """Jump to the observed last page using a dedicated or numbered button."""
        position = self.get_current_page_info()
        current, total = position["current_page"], position["total_pages"]
        if current == total:
            return False
        return self._turn_page(current, total, "last", C.LAST_PAGE_CSS, timeout)

    def _turn_page(self, current: int, destination: int, operation: str,
                   selector: Optional[str], timeout: int, *, boundary: bool = False) -> bool:
        """Verify arrival before any caller may process the target page."""
        try:
            button = self.page.query_selector(selector) if selector else None
            if operation in ("last", "numbered") and (button is None or button.is_disabled()):
                button = next(
                    (item for item in self.page.query_selector_all(".el-pager li.number")
                     if (item.text_content() or "").strip() == str(destination)),
                    None,
                )
            if button is None or button.is_disabled():
                if boundary:
                    return False
                raise RuntimeError("Expected pagination control is unavailable")
            button.click()
            self.page.wait_for_function(
                "(destination) => Number(document.querySelector('.el-pager .active')?.textContent) === destination",
                arg=destination, timeout=timeout * 1000,
            )
            time.sleep(C.PAGINATION_WAIT)
        except Exception as exc:
            raise PaginationError(operation, current, destination) from exc
        return True

    def has_next_page(self, timeout: int = 5) -> bool:
        """Check if there is a next page available."""
        position = self.get_current_page_info()
        return position["current_page"] < position["total_pages"]

    def get_current_page_info(self) -> Dict[str, Any]:
        """Get current page number and total pages.

        The cninfo site uses Element UI pagination. The pager component
        (.el-pager) contains <li> elements for page numbers. The last <li>
        always shows the final page number, even when the full list is
        ellipsis-truncated (e.g. 1 2 3 4 ... 38).

        The total-record label is not a page count.
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

                    return {
                        current_page: active ? parseInt(active.textContent) : 1,
                        total_pages: totalFromPager,
                    };
                }
            """)
            current, total = info["current_page"], info["total_pages"]
            if type(current) is not int or type(total) is not int or not 1 <= current <= total:
                raise ValueError("Pagination returned inconsistent page numbers")
            return info
        except Exception as exc:
            log.error("Failed to read pagination info: %s", exc, exc_info=True)
            raise BrowserError(f"Failed to read pagination info: {exc}") from exc

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
