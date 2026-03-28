"""
Selenium Browser Automation Strategy Implementation

Refactored version using modular architecture with driver_factory and download_manager.
"""

import os
import random
import time
from typing import Any, Dict, List, Optional, cast

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...core.config import ConfigManager
from ...core.constants import USER_AGENTS, BrowserConfig, TimeoutConfig
from ...core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    with_error_handling,
)
from ...core.logger import get_logger
from ...utils.cleanup_utils import safe_cleanup
from ..browser_strategy import BrowserStrategy
from .driver_factory import ChromeDriverFactory
from .download_manager import DownloadManager

logger = get_logger(__name__)


class SeleniumStrategy(BrowserStrategy):
    """Selenium Browser Automation Strategy"""

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Selenium Strategy"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}
        self.driver: Optional[Any] = None
        self.download_count = 0

        # Initialize config manager
        self.config_manager = ConfigManager()

        # Use constant config
        self.window_size = self.config.get(
            "window_size", BrowserConfig.DEFAULT_WINDOW_SIZE
        )

        # BaseDownloader timeout is in seconds, convert to seconds (Selenium uses seconds)
        timeout_seconds = self.config.get("timeout", TimeoutConfig.PAGE_LOAD)
        self.page_load_timeout = self.config.get("page_load_timeout", timeout_seconds)
        self.implicit_wait = self.config.get(
            "implicit_wait", BrowserConfig.IMPLICIT_WAIT
        )
        self.max_downloads_per_session = self.config.get(
            "max_downloads_per_session", BrowserConfig.MAX_DOWNLOADS_PER_SESSION
        )

        # Use constant user agents (for backward compatibility)
        self._user_agents = self.config.get("user_agents", USER_AGENTS)

        # Initialize driver factory
        self._driver_factory = ChromeDriverFactory(
            headless=headless,
            download_dir=download_dir,
            config=self.config,
        )

        # Download manager (initialized when driver is created)
        self._download_manager: Optional[DownloadManager] = None

    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3,
    )
    def create_driver(self) -> Any:
        """Create WebDriver instance using factory"""
        # Ensure previous driver is completely closed
        if self.driver:
            self.close()

        self.driver = self._driver_factory.create_driver()

        # Initialize download manager
        self._download_manager = DownloadManager(
            driver=self.driver,
            download_dir=self.download_dir,
        )

        return self.driver

    def initialize(self) -> bool:
        """Initialize browser"""
        try:
            if not self.driver:
                self.create_driver()
            return self.driver is not None
        except Exception as e:
            logger.error(f"Initialization failed: {e}")

            # Cleanup failed driver
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

            return False

    def get_driver(self) -> Any:
        """Get current driver instance"""
        return self.driver

    def cleanup(self) -> None:
        """Cleanup browser resources"""
        try:
            self.close()
        except Exception as e:
            logger.error(f"Selenium cleanup failed: {e}")

    def navigate(self, url: str) -> bool:
        """Navigate to specified URL"""
        if not self.driver:
            return False

        try:
            self.driver.get(url)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False

    def navigate_to_page(self, url: str) -> bool:
        """Navigate to specified page (compatible with IBrowserStrategy interface)"""
        return self.navigate(url)

    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """Find elements"""
        if not self.driver:
            return []

        try:
            by_method = getattr(By, by.upper(), By.CSS_SELECTOR)
            return cast(List[Any], self.driver.find_elements(by_method, selector))
        except Exception as e:
            logger.error(f"Failed to find elements: {e}")
            return []

    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """Find single element"""
        elements = self.find_elements(selector, by)
        return elements[0] if elements else None

    def click(self, element: Any) -> bool:
        """Click element"""
        if not element:
            return False

        try:
            element.click()
            return True
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return False

    def get_text(self, element: Any) -> str:
        """Get element text"""
        if not element:
            return ""

        try:
            return cast(str, element.text)
        except Exception as e:
            logger.error(f"Failed to get element text: {e}")
            return ""

    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """Get element attribute"""
        if not element:
            return None

        try:
            return cast(Optional[str], element.get_attribute(attribute))
        except Exception as e:
            logger.error(f"Failed to get element attribute: {e}")
            return None

    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript script"""
        if not self.driver:
            return None

        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            return None

    def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        by: str = "css",
        condition: str = "visible",
    ) -> bool:
        """Wait for element to appear"""
        if not self.driver:
            return False

        try:
            by_method = getattr(By, by.upper(), By.CSS_SELECTOR)
            wait = WebDriverWait(self.driver, timeout)

            if condition == "presence":
                wait.until(EC.presence_of_element_located((by_method, selector)))
            elif condition == "visible":
                wait.until(EC.visibility_of_element_located((by_method, selector)))
            elif condition == "clickable":
                wait.until(EC.element_to_be_clickable((by_method, selector)))

            return True

        except Exception:
            return False

    def get_page_source(self) -> str:
        """Get page source code"""
        if not self.driver:
            return ""

        try:
            return cast(str, self.driver.page_source)
        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return ""

    def get_current_url(self) -> str:
        """Get current URL"""
        if not self.driver:
            return ""

        try:
            return cast(str, self.driver.current_url)
        except Exception as e:
            logger.error(f"Failed to get current URL: {e}")
            return ""
            return ""

    def get_page_title(self) -> str:
        """Get page title"""
        if not self.driver:
            return ""

        try:
            return cast(str, self.driver.title)
        except Exception as e:
            logger.error(f"Failed to get page title: {e}")
            return ""

    def close(self) -> None:
        """Close browser"""
        if self.driver:
            safe_cleanup(self.driver.quit, "Failed to close WebDriver")

        # Enhanced cleanup logic
        try:
            if self.download_dir and os.path.exists(self.download_dir):
                logger.info(
                    f"Cleaning up residual files in download directory: {self.download_dir}"
                )
                for item in os.listdir(self.download_dir):
                    item_path = os.path.join(self.download_dir, item)
                    if os.path.isfile(item_path):
                        if (
                            item.lower() == "pdf.txt"
                            or item.endswith(".tmp")
                            or item.endswith(".crdownload")
                        ):
                            try:
                                os.remove(item_path)
                                logger.info(f"Cleaned residual file: {item}")
                            except Exception as e:
                                logger.warning(f"Failed to clean file {item}: {e}")
        except Exception as e:
            logger.error(f"Error while cleaning residual files: {e}")

        # Reset state
        self.driver = None
        self._download_manager = None
        self.download_count = 0

        logger.info("Selenium WebDriver closed")

    def is_healthy(self) -> bool:
        """Check if browser is healthy"""
        if not self.driver:
            return False

        try:
            self.driver.current_url
            return True
        except Exception:
            return False

    def restart(self) -> bool:
        """Restart browser"""
        logger.info("Restarting Selenium WebDriver...")

        self.close()

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(
                    f"Attempting to restart WebDriver ({attempt + 1}/{max_attempts})..."
                )
                self.create_driver()
                logger.info("WebDriver restarted successfully")
                return True

            except Exception as e:
                logger.error(f"WebDriver restart attempt {attempt + 1} failed: {e}")

                if attempt < max_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"Waiting {retry_wait:.2f} seconds before retry...")
                    time.sleep(retry_wait)

        logger.error("WebDriver restart failed after all attempts")
        return False

    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """Take screenshot"""
        if not self.driver:
            return None

        try:
            screenshot_data = cast(bytes, self.driver.get_screenshot_as_png())

            if save_path:
                with open(save_path, "wb") as f:
                    f.write(screenshot_data)

            return screenshot_data
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    def download_file(self, url: str, save_path: str, timeout: int = 60) -> bool:
        """Download file to specified path"""
        if not self._download_manager:
            logger.error("Download manager not initialized")
            return False

        success = self._download_manager.download_file(url, save_path, timeout)
        if success:
            self.download_count = self._download_manager.download_count
        return success

    def go_to_page(self, page_number: int, timeout: int = 30) -> bool:  # type: ignore[override]
        """Navigate to specific page number"""
        if not self.driver:
            return False

        try:
            # Find page input and navigate
            page_input = self.find_element("//input[@class='el-pagination__editor']", by="xpath")
            if page_input:
                from selenium.webdriver.common.keys import Keys

                page_input.clear()
                page_input.send_keys(str(page_number))
                page_input.send_keys(Keys.RETURN)
                time.sleep(2)  # Fixed wait time instead of TimeoutConfig.PAGINATION_WAIT
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to go to page {page_number}: {e}")
            return False

    def go_to_next_page(self, timeout: int = 30) -> bool:  # type: ignore[override]
        """Navigate to next page"""
        if not self.driver:
            return False

        try:
            next_button = self.find_element(
                "//button[contains(@class, 'el-pagination__next') and not(contains(@class, 'is-disabled'))]",
                by="xpath"
            )
            if next_button:
                self.click(next_button)
                time.sleep(2)  # Fixed wait time instead of TimeoutConfig.PAGINATION_WAIT
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to go to next page: {e}")
            return False

    def has_next_page(self, timeout: int = 30) -> bool:  # type: ignore[override]
        """Check if there is a next page"""
        if not self.driver:
            return False

        try:
            next_button = self.find_element(
                "//button[contains(@class, 'el-pagination__next') and contains(@class, 'is-disabled')]",
                by="xpath"
            )
            # If disabled button found, no next page
            return next_button is None
        except Exception:
            # If no disabled button found, assume there is a next page
            return True

    def get_current_page_info(self) -> Dict[str, Any]:
        """Get current page info including current page and total pages"""
        if not self.driver:
            return {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            }

        try:
            current_page = self.driver.execute_script(
                "const active = document.querySelector('.el-pager li.number.active');"
                "return active ? parseInt(active.textContent.trim()) : 1;"
            )
            total_pages = self.driver.execute_script(
                "const pages = document.querySelectorAll('.el-pager li.number');"
                "return pages.length > 0 ? parseInt(pages[pages.length - 1].textContent.trim()) : 1;"
            )
            return {
                "current_page": current_page or 1,
                "total_pages": total_pages or 1,
                "has_next": self.has_next_page(),
                "has_previous": (current_page or 1) > 1,
            }
        except Exception as e:
            logger.error(f"Failed to get page info: {e}")
            return {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            }


# Backward compatibility - keep the same export name
__all__ = ["SeleniumStrategy"]
