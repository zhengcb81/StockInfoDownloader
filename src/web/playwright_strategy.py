"""
Playwright Browser Automation Strategy Implementation
"""

import os
import random
import time
from typing import Any, Dict, List, Optional

# Playwright import (for testing mock)
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants
from ..core.constants import (
    USER_AGENTS,
    BrowserConfig,
    PaginationConfig,
    SelectorConfig,
    TimeoutConfig,
)
from ..core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    WebDriverInitError,
    WebDriverTimeoutError,
    with_error_handling,
)
from ..core.logger import get_logger
from ..utils.browser_utils import (
    validate_and_normalize_timeout,
)
from ..utils.cleanup_utils import cleanup_directory, safe_cleanup
from .browser_strategy import BrowserAutomationStrategy

logger = get_logger(__name__)


class PlaywrightStrategy(BrowserAutomationStrategy):
    """Playwright Browser Automation Strategy"""

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Playwright strategy"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}
        self.browser: Optional[Any] = None
        self.page: Optional[Any] = None
        self.user_data_dir: Optional[str] = None  # Temp user data directory path
        self.context: Optional[Any] = None
        self.playwright: Optional[Any] = None
        self.download_count = 0

        # Initialize config manager
        self.config_manager = ConfigManager()

        # Use constant config
        self.window_size = self.config.get(
            "window_size", BrowserConfig.DEFAULT_WINDOW_SIZE_DICT
        )

        # Use standardized timeout handling
        timeout_value = self.config.get("timeout", TimeoutConfig.INITIALIZATION)
        self.timeout = validate_and_normalize_timeout(timeout_value)

        self.max_downloads_per_session = self.config.get(
            "max_downloads_per_session", BrowserConfig.MAX_DOWNLOADS_PER_SESSION
        )

        self._user_agents = self.config.get("user_agents", USER_AGENTS)

    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3,
    )
    def create_driver(self) -> Any:
        """Create Playwright browser instance"""
        # Ensure previous instances are completely closed
        if self.browser:
            self.close()
            time.sleep(1)  # Wait for browser to fully close

        logger.info("Initializing Playwright browser...")

        try:
            # Check if Playwright is available
            if sync_playwright is None:
                raise ImportError("Playwright not available")

            # Force cleanup of asyncio event loop to prevent Sync API conflicts
            import asyncio

            try:
                # If current thread has an event loop, try to clear it
                # Note: this only works if the loop is not running
                asyncio.set_event_loop(None)
            except Exception:
                pass

            # Create Playwright instance
            self.playwright = sync_playwright().start()

            # Build launch options
            launch_options = self._build_launch_options()

            # If download directory is specified, use persistent context
            # Note: Do not set downloads_path, let download.save_as() control locations
            if self.download_dir:
                abs_download_dir = os.path.abspath(self.download_dir)
                os.makedirs(abs_download_dir, exist_ok=True)

                # Create temporary user data directory
                import tempfile

                self.user_data_dir = tempfile.mkdtemp(prefix="playwright_user_")

                # Launch with persistent context
                context_options = self._build_context_options()
                # Do not set downloads_path to avoid double saving

                self.context = self.playwright.chromium.launch_persistent_context(
                    self.user_data_dir, **launch_options, **context_options
                )
                self.page = (
                    self.context.pages[0]
                    if self.context.pages
                    else self.context.new_page()
                )
                logger.info(
                    f"Started with persistent context, downloads controlled via save_as"
                )
            else:
                # Launch browser
                self.browser = self.playwright.chromium.launch(**launch_options)

                # Create browser context
                context_options = self._build_context_options()
                self.context = self.browser.new_context(**context_options)

                # Create page
                self.page = self.context.new_page()

            # Set timeout
            self.page.set_default_timeout(self.timeout)

            # Execute anti-detection scripts
            self.page.add_init_script(ConfigConstants.ANTI_DETECTION_SCRIPT)

            # Test page
            self.page.goto(ConfigConstants.BLANK_PAGE_URL, wait_until="domcontentloaded")

            logger.info("Playwright browser initialized successfully")
            # Return browser or persistent context (as browser handle)
            return self.browser if self.browser else self.context

        except ImportError:
            raise WebDriverInitError(
                "Playwright not installed, please run: pip install playwright && playwright install chromium",
                context={"phase": "initialization", "error_type": "missing_dependency"},
            )
        except Exception as e:
            error_msg = f"Failed to create Playwright browser: {e}"
            logger.error(error_msg)

            # Cleanup failed instances
            self.close()

            if "timeout" in str(e).lower():
                raise WebDriverTimeoutError(
                    error_msg,
                    context={
                        "phase": "initialization",
                        "timeout_type": "creation_timeout",
                    },
                    original_exception=e,
                )
            else:
                raise WebDriverInitError(
                    error_msg,
                    context={"phase": "initialization", "error_details": str(e)},
                    original_exception=e,
                )

    def _build_launch_options(self) -> Dict[str, Any]:
        """Build browser launch options"""
        launch_options = {
            "headless": self.headless,
            "args": ConfigConstants.BROWSER_LAUNCH_ARGS.copy(),
        }

        # Add window size
        if isinstance(self.window_size, dict):
            launch_options["args"].append(
                f'--window-size={self.window_size["width"]},{self.window_size["height"]}'
            )

        # Random User-Agent
        user_agent = random.choice(self._user_agents)
        launch_options["args"].append(f"--user-agent={user_agent}")

        return launch_options

    def _build_context_options(self) -> Dict[str, Any]:
        """Build browser context options"""
        context_options = {
            "viewport": (
                self.window_size
                if isinstance(self.window_size, dict)
                else {"width": 1920, "height": 1080}
            ),
            "user_agent": random.choice(self._user_agents),
            "java_script_enabled": True,
            "ignore_https_errors": False,
        }

        # Set download directory
        if self.download_dir:
            abs_download_dir = os.path.abspath(self.download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)

            context_options["accept_downloads"] = True
            logger.info(f"Set download directory: {abs_download_dir}")

        return context_options

    def get_driver(self) -> Any:
        """Get current browser instance"""
        return self.browser

    def cleanup(self) -> None:
        """
        Cleanup browser resources (implement interface)
        """
        try:
            self.close()
        except Exception as e:
            logger.error(f"Playwright cleanup failed: {e}")

    def initialize(self) -> bool:
        """
        Initialize browser (implement interface)

        Returns:
            bool: Whether initialization was successful
        """
        try:
            self.create_driver()
            return True
        except Exception as e:
            logger.error(f"Playwright initialization failed: {e}")
            return False

    def navigate_to_page(self, url: str) -> bool:
        """
        Navigate to specified page (implement interface)

        Args:
            url: Target URL

        Returns:
            bool: Whether navigation was successful
        """
        return self.navigate(url)

    def navigate(self, url: str) -> bool:
        """Navigate to specified URL"""
        if not self.page:
            return False

        try:
            # Use configured timeout (ms)
            timeout_ms = self.timeout
            self.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return True
        except Exception as e:
            logger.error(f"Navigate to {url} failed: {e}")
            return False

    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """Find elements"""
        if not self.page:
            return []

        try:
            # Playwright mainly uses CSS selectors, also supports XPath
            if by.lower() == "xpath":
                return self.page.query_selector_all(f"xpath={selector}")
            else:
                return self.page.query_selector_all(selector)
        except Exception as e:
            logger.error(f"Find elements failed: {e}")
            return []

    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """Find single element"""
        if not self.page:
            return None

        try:
            if by.lower() == "xpath":
                return self.page.query_selector(f"xpath={selector}")
            else:
                return self.page.query_selector(selector)
        except Exception as e:
            logger.error(f"Find element failed: {e}")
            return None

    def click(self, element: Any) -> bool:
        """Click element"""
        if not element:
            return False

        try:
            element.click()
            return True
        except Exception as e:
            logger.error(f"Click element failed: {e}")
            return False

    def get_text(self, element: Any) -> str:
        """Get element text"""
        if not element:
            return ""

        try:
            # Use JavaScript to get text, ensuring dynamic content is captured
            if hasattr(element, "evaluate"):
                text = element.evaluate('element => element.textContent?.trim() || ""')
                return text or ""
            else:
                return element.text_content() or ""
        except Exception as e:
            logger.error(f"Get element text failed: {e}")
            return ""

    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """Get element attribute"""
        if not element:
            return None

        try:
            return element.get_attribute(attribute)
        except Exception as e:
            logger.error(f"Get element attribute failed: {e}")
            return None

    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript script"""
        if not self.page:
            return None

        try:
            return self.page.evaluate(script, *args)
        except Exception as e:
            logger.error(f"Execute script failed: {e}")
            return None

    def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        by: str = "css",
        condition: str = "visible",
    ) -> bool:
        """Wait for element to appear"""
        if not self.page:
            return False

        try:
            timeout_ms = timeout * 1000  # Convert to milliseconds

            if condition == "visible":
                self.page.wait_for_selector(
                    selector, state="visible", timeout=timeout_ms
                )
            elif condition == "hidden":
                self.page.wait_for_selector(
                    selector, state="hidden", timeout=timeout_ms
                )
            else:
                self.page.wait_for_selector(selector, timeout=timeout_ms)

            return True

        except Exception:
            return False

    def get_page_source(self) -> str:
        """Get page source code"""
        if not self.page:
            return ""

        try:
            return self.page.content()
        except Exception as e:
            logger.error(f"Get page source failed: {e}")
            return ""

    def get_current_url(self) -> str:
        """Get current URL"""
        if not self.page:
            return ""

        try:
            return self.page.url
        except Exception as e:
            logger.error(f"Get current URL failed: {e}")
            return ""

    def get_page_title(self) -> str:
        """Get page title"""
        if not self.page:
            return ""

        try:
            return self.page.title()
        except Exception as e:
            logger.error(f"Get page title failed: {e}")
            return ""

    def close(self) -> None:
        """Close browser (optimized version)"""
        # Orderly resource cleanup
        if self.page:
            safe_cleanup(self.page.close, "Failed to close page")

        if self.context:
            safe_cleanup(self.context.close, "Failed to close context")

        if self.browser:
            safe_cleanup(self.browser.close, "Failed to close browser")

        if hasattr(self, "playwright") and self.playwright:

            def _stop():
                self.playwright.stop()
                time.sleep(0.5)

            safe_cleanup(_stop, "Failed to stop Playwright")

        # Cleanup temporary directory
        cleanup_directory(self.user_data_dir)

        # Reset state
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.user_data_dir = None
        self.download_count = 0

        time.sleep(0.5)
        logger.info("Playwright browser closed")

    def is_healthy(self) -> bool:
        """Check if browser is healthy"""
        if not self.page:
            return False

        try:
            # Try to get page URL to test responsiveness
            _ = self.page.url
            return True
        except Exception:
            return False

    def restart(self) -> bool:
        """Restart browser"""
        logger.info("Restarting Playwright browser...")

        self.close()

        # Enhanced retry mechanism
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(
                    f"Attempting to restart browser (attempt {attempt + 1}/{max_attempts})..."
                )
                self.create_driver()
                logger.info("Browser restarted successfully")
                return True

            except Exception as e:
                logger.error(f"Browser restart attempt {attempt + 1} failed: {e}")

                if attempt < max_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"Waiting {retry_wait:.2f} seconds before retry...")
                    time.sleep(retry_wait)

        logger.error("Browser restart failed after all attempts")
        return False

    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """Take screenshot"""
        if not self.page:
            return None

        try:
            screenshot_data = self.page.screenshot()

            if save_path:
                with open(save_path, "wb") as f:
                    f.write(screenshot_data)

            return screenshot_data
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    # Playwright specific methods
    def wait_for_download(self, timeout: int = 30) -> Optional[Any]:
        """Wait for download to complete (Playwright specific)"""
        if not self.page:
            return None

        try:
            download = self.page.wait_for_event("download", timeout=timeout * 1000)
            return download
        except Exception as e:
            logger.error(f"Wait for download failed: {e}")
            return None

    def wait_for_navigation(self, timeout: int = 30) -> bool:
        """Wait for navigation to complete (Playwright specific)"""
        if not self.page:
            return False

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
            return True
        except Exception as e:
            logger.error(f"Wait for navigation failed: {e}")
            return False

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        Jump to next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether successfully jumped
        """
        if not self.page:
            logger.error("Page not initialized, cannot jump")
            return False

        try:
            # Use constant config selectors
            next_selectors = SelectorConfig.NEXT_PAGE_SELECTORS

            for selector in next_selectors:
                try:
                    next_button = self.page.query_selector(selector)
                    if next_button and next_button.is_enabled():
                        # Click next page
                        next_button.click()

                        # Wait for page load
                        self.page.wait_for_load_state(
                            "domcontentloaded", timeout=timeout * 1000
                        )
                        time.sleep(
                            PaginationConfig.DOM_STABILITY_WAIT
                        )  # Extra wait for content stability

                        logger.info("Successfully jumped to next page")
                        return True

                except Exception:
                    continue

            logger.info("No next page button found or reached last page")
            return False

        except Exception as e:
            logger.error(f"Jump to next page failed: {e}")
            return False

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        Jump to specified page number

        Args:
            page_number: Target page number
            timeout: Timeout in seconds

        Returns:
            bool: Whether successfully jumped
        """
        if not self.page:
            logger.error("Page not initialized, cannot jump")
            return False

        try:
            # Method 1: Find page input and jump button
            page_input_selectors = [
                "input.el-pagination__editor",
                "input.page-input",
                "input[type='number']",
                "input.pagination-input",
            ]

            go_button_selectors = [
                "button.el-pagination__jump",
                "button.page-go",
                "button:has-text('跳转')",
                "button:has-text('Go')",
            ]

            for input_selector, button_selector in zip(
                page_input_selectors, go_button_selectors
            ):
                try:
                    # Find page input
                    page_input = self.page.query_selector(input_selector)
                    if not page_input or not page_input.is_enabled():
                        continue

                    # Find go button
                    go_button = self.page.query_selector(button_selector)
                    if not go_button or not go_button.is_enabled():
                        continue

                    # Clear and type page number
                    page_input.fill("")
                    page_input.type(str(page_number))

                    # Click go button
                    go_button.click()

                    # Wait for page load
                    self.page.wait_for_load_state(
                        "domcontentloaded", timeout=timeout * 1000
                    )
                    time.sleep(1)

                    logger.info(f"Successfully jumped to page {page_number}")
                    return True

                except Exception:
                    continue

            # Method 2: Click page number button directly
            page_button_selectors = [
                f".el-pager li.number:not(.active)",
                f".pagination li:not(.active)",
                f"a:not(.active)",
                f"button:not([disabled])",
            ]

            for selector in page_button_selectors:
                try:
                    page_buttons = self.page.query_selector_all(selector)
                    for page_button in page_buttons:
                        if page_button and page_button.is_enabled():
                            button_text = page_button.text_content().strip()
                            if button_text == str(page_number):
                                # Click page button
                                page_button.click()

                                # Wait for page load
                                self.page.wait_for_load_state(
                                    "domcontentloaded", timeout=timeout * 1000
                                )
                                time.sleep(1)

                                logger.info(
                                    f"Successfully jumped to page {page_number}"
                                )
                                return True

                except Exception:
                    continue

            logger.warning(f"Failed to jump to page {page_number}")
            return False

        except Exception as e:
            logger.error(f"Jump to specified page failed: {e}")
            return False

    def has_next_page(self, timeout: int = 5) -> bool:
        """
        Check if next page exists

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether next page exists
        """
        if not self.page:
            logger.error("Page not initialized, cannot check pagination")
            return False

        try:
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])",
            ]

            for selector in next_selectors:
                try:
                    next_button = self.page.query_selector(selector)
                    if next_button and next_button.is_enabled():
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"Check next page failed: {e}")
            return False

    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        Download file to specified path

        Args:
            url: URL to download
            save_path: File save path
            timeout: Timeout in seconds

        Returns:
            bool: Whether download was successful
        """
        if not self.page:
            logger.error("Page not initialized, cannot download file")
            return False

        try:
            # 1. Attempt navigation to detail page, prepare for potential direct download
            # Some URLs trigger direct download, causing page.goto to throw "Download is starting"
            logger.info(f"Attempting download: {url}")

            try:
                with self.page.expect_download(timeout=10000) as download_info:
                    # Do not use self.navigate(url) directly to avoid error logging on goto throw
                    self.page.goto(
                        url, wait_until="domcontentloaded", timeout=self.timeout
                    )

                # If code reaches here and success, direct download triggered
                download = download_info.value
                download.save_as(save_path)
                logger.info(f"Direct download successful: {save_path}")
                return True
            except Exception as e:
                error_msg = str(e)
                if "Download is starting" in error_msg:
                    # Expect download should have caught this, but if not, try waiting for event
                    try:
                        download = self.page.wait_for_event("download", timeout=5000)
                        download.save_as(save_path)
                        logger.info(f"Captured started download: {save_path}")
                        return True
                    except:
                        pass

                # Continue to button search if no direct download
                logger.debug(
                    f"Direct download not triggered, searching for button: {error_msg}"
                )

            # 2. Search for download button if direct download failed
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass

            time.sleep(2)

            # Find download button
            download_button = self.find_element(
                "button:has-text('公告下载'), a:has-text('下载'), .download-link"
            )
            if not download_button:
                logger.error(
                    "Download button not found, and direct download not triggered"
                )
                logger.debug(f"Current page title: {self.get_page_title()}")
                return False

            # Setup download event listener
            with self.page.expect_download(timeout=timeout * 1000) as download_info:
                # Click download button
                if not self.click(download_button):
                    logger.error("Click download button failed")
                    return False

                logger.info("Clicked download button, waiting for file...")

            # Get download object
            download = download_info.value

            # Save file
            download.save_as(save_path)
            logger.info(f"Download via button successful: {save_path}")
            return True

        except Exception as e:
            logger.error(f"File download ultimately failed: {e}")
            return False
