"""
Selenium WebDriver Factory Module

Provides Chrome driver creation and configuration functionality.
"""

import os
import platform
import random
import subprocess
import time
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from ...core.config_constants import ConfigConstants
from ...core.constants import USER_AGENTS, BrowserConfig, TimeoutConfig
from ...core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    WebDriverCrashError,
    WebDriverInitError,
    WebDriverTimeoutError,
    with_error_handling,
)
from ...core.logger import get_logger
from ...utils.browser_utils import get_common_chrome_args, is_test_environment

logger = get_logger(__name__)


class ChromeDriverFactory:
    """Chrome WebDriver Factory"""

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize factory"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}

        # Use constant config
        self.window_size = self.config.get(
            "window_size", BrowserConfig.DEFAULT_WINDOW_SIZE
        )

        # Timeout configuration
        timeout_seconds = self.config.get("timeout", TimeoutConfig.PAGE_LOAD)
        self.page_load_timeout = self.config.get("page_load_timeout", timeout_seconds)
        self.implicit_wait = self.config.get(
            "implicit_wait", BrowserConfig.IMPLICIT_WAIT
        )

        # Use constant user agents
        self._user_agents = self.config.get("user_agents", USER_AGENTS)

    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3,
    )
    def create_driver(self) -> webdriver.Chrome:
        """Create WebDriver instance"""
        logger.info("Initializing Selenium WebDriver...")

        # Only cleanup processes in non-test environment
        if not is_test_environment():
            self._cleanup_chrome_processes()

        try:
            chrome_options = self._build_chrome_options()

            # Create driver
            try:
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as create_error:
                logger.error(f"Failed to create ChromeDriver: {create_error}")
                # Try to cleanup and recreate
                self._cleanup_chrome_processes()
                time.sleep(TimeoutConfig.RETRY_DELAY)
                driver = webdriver.Chrome(options=chrome_options)

            # Configure driver
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.implicitly_wait(self.implicit_wait)

            # Execute anti-detection script
            driver.execute_script(ConfigConstants.ANTI_DETECTION_SCRIPT)

            # Test if driver is working
            driver.get(ConfigConstants.BLANK_PAGE_URL)

            logger.info("Selenium WebDriver initialized successfully")
            return driver

        except Exception as e:
            error_msg = f"Failed to create WebDriver: {e}"
            logger.error(error_msg)

            # Raise different exceptions based on error type
            if "tab crashed" in str(e).lower():
                raise WebDriverCrashError(
                    error_msg,
                    context={"phase": "initialization", "crash_type": "tab_crashed"},
                    original_exception=e,
                )
            elif "timeout" in str(e).lower():
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

    def _build_chrome_options(self) -> Options:
        """Build Chrome options"""
        chrome_options = Options()

        # Basic settings
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f"--window-size={self.window_size}")

        # Use common tools to get generic Chrome args
        for arg in get_common_chrome_args():
            chrome_options.add_argument(arg)

        # Anti-automation detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Set download directory
        if self.download_dir:
            abs_download_dir = os.path.abspath(self.download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)

            if platform.system() == "Windows":
                abs_download_dir = abs_download_dir.replace("/", "\\")

            prefs = {
                "download.default_directory": abs_download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "safebrowsing.enabled": True,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
                "download_restrictions": 0,  # Allow all downloads
                "credentials_enable_service": False,
                "password_manager_enabled": False,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            logger.info(f"Set download directory: {abs_download_dir}")

        # Random User-Agent
        user_agent = random.choice(self._user_agents)
        chrome_options.add_argument(f"--user-agent={user_agent}")

        return chrome_options

    def _cleanup_chrome_processes(self):
        """Cleanup Chrome processes"""
        try:
            if is_test_environment():
                return

            timeout_value = ConfigConstants.get_timeout("process_cleanup")

            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/f", "/im", "chromedriver.exe"],
                    capture_output=True,
                    timeout=timeout_value,
                    check=False,
                )
            else:
                subprocess.run(
                    ["pkill", "-f", "chromedriver"],
                    capture_output=True,
                    timeout=timeout_value,
                    check=False,
                )

            time.sleep(TimeoutConfig.BROWSER_CLOSE)

        except Exception as e:
            logger.debug(f"Error cleaning up Chrome processes: {e}")


# Module exports
__all__ = ["ChromeDriverFactory"]
