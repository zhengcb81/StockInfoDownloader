"Selenium Browser Automation Strategy Implementation"

import os
import platform
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants
from ..core.constants import (
    USER_AGENTS,
    BrowserConfig,
    FileSizeThreshold,
    SelectorConfig,
    TimeoutConfig,
)
from ..core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    WebDriverCrashError,
    WebDriverInitError,
    WebDriverTimeoutError,
    with_error_handling,
)
from ..core.logger import get_logger
from ..utils.browser_utils import (
    get_common_chrome_args,
    is_test_environment,
)
from ..utils.cleanup_utils import safe_cleanup
from .browser_strategy import BrowserAutomationStrategy

logger = get_logger(__name__)


class SeleniumStrategy(BrowserAutomationStrategy):
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
        self.driver: Optional[webdriver.Chrome] = None
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

        # Use constant user agents
        self._user_agents = self.config.get("user_agents", USER_AGENTS)

    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3,
    )
    def create_driver(self) -> Any:
        """Create WebDriver instance"""
        # Ensure previous driver is completely closed
        if self.driver:
            self.close()

        logger.info("Initializing Selenium WebDriver...")

        # Only cleanup processes in non-test environment
        if not is_test_environment():
            self._cleanup_chrome_processes()

        try:
            chrome_options = self._build_chrome_options()

            # Create driver
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as create_error:
                logger.error(f"Failed to create ChromeDriver: {create_error}")
                # Try to cleanup and recreate
                self._cleanup_chrome_processes()
                time.sleep(TimeoutConfig.RETRY_DELAY)
                self.driver = webdriver.Chrome(options=chrome_options)

            # Configure driver
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(self.implicit_wait)

            # Execute anti-detection script
            self.driver.execute_script(ConfigConstants.ANTI_DETECTION_SCRIPT)

            # Test if driver is working
            self.driver.get(ConfigConstants.BLANK_PAGE_URL)

            logger.info("Selenium WebDriver initialized successfully")
            return self.driver

        except Exception as e:
            error_msg = f"Failed to create WebDriver: {e}"
            logger.error(error_msg)

            # Cleanup failed driver
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

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

    def initialize(self) -> bool:
        """
        Initialize browser (compatible with IBrowserStrategy interface)

        Returns:
            bool: Whether initialization was successful
        """
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

    def get_driver(self) -> Any:
        """Get current driver instance"""
        return self.driver

    def cleanup(self) -> None:
        """
        Cleanup browser resources (implement interface)
        """
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
        """
        Navigate to specified page (compatible with IBrowserStrategy interface)

        Args:
            url: Target URL

        Returns:
            bool: Whether navigation was successful
        """
        return self.navigate(url)

    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """Find elements"""
        if not self.driver:
            return []

        try:
            by_method = getattr(By, by.upper(), By.CSS_SELECTOR)
            return self.driver.find_elements(by_method, selector)
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
            return element.text
        except Exception as e:
            logger.error(f"Failed to get element text: {e}")
            return ""

    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """Get element attribute"""
        if not element:
            return None

        try:
            return element.get_attribute(attribute)
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
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return ""

    def get_current_url(self) -> str:
        """Get current URL"""
        if not self.driver:
            return ""

        try:
            return self.driver.current_url
        except Exception as e:
            logger.error(f"Failed to get current URL: {e}")
            return ""

    def get_page_title(self) -> str:
        """Get page title"""
        if not self.driver:
            return ""

        try:
            return self.driver.title
        except Exception as e:
            logger.error(f"Failed to get page title: {e}")
            return ""

    def close(self) -> None:
        """Close browser (optimized version)"""
        if self.driver:
            safe_cleanup(self.driver.quit, "Failed to close WebDriver")

        # Enhanced cleanup logic: clean up residual files in download root directory
        try:
            if self.download_dir and os.path.exists(self.download_dir):
                logger.info(
                    f"Cleaning up residual files in download root directory: {self.download_dir}"
                )
                for item in os.listdir(self.download_dir):
                    item_path = os.path.join(self.download_dir, item)
                    # Only clean files, not subdirectories
                    if os.path.isfile(item_path):
                        # Clean temp files and pdf.txt (do not clean PDF files to prevent accidental deletion)
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

        # Enhanced retry mechanism
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
            screenshot_data = self.driver.get_screenshot_as_png()

            if save_path:
                with open(save_path, "wb") as f:
                    f.write(screenshot_data)

            return screenshot_data
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    def download_file(self, url: str, save_path: str, timeout: int = 10) -> bool:
        """
        Download file to specified path (refactored version)

        Args:
            url: URL to download
            save_path: File save path
            timeout: Timeout in seconds

        Returns:
            bool: Whether download was successful
        """
        if not self.driver:
            logger.error("Browser not initialized, cannot download file")
            return False

        try:
            # 1. Prepare download
            if not self._prepare_download():
                return False

            # 2. Navigate to detail page and wait
            if not self._navigate_to_detail_page(url):
                return False

            # 3. Click download button
            if not self._click_download_button():
                return False

            # 4. Wait and move file
            return self._wait_and_move_file(save_path, timeout)

        except Exception as e:
            logger.error(f"File download failed: {e}")
            return False

    def _prepare_download(self) -> bool:
        """
        Prepare download: clean root PDFs and record status

        Returns:
            bool: Whether preparation was successful
        """
        if not self.download_dir or not os.path.exists(self.download_dir):
            return True

        # Aggressively clean up ANY PDF files in the download root directory
        # to prevent orphans from previous attempts being detected as new
        download_root = Path(self.download_dir)
        try:
            for f in download_root.glob("*.pdf"):
                try:
                    f.unlink()
                    logger.info(f"Cleaned pre-existing orphan PDF in root: {f}")
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error during pre-download cleanup: {e}")

        # Record file list before download - ONLY in subdirectories
        # (root should be empty now)
        self._before_files = set()
        for root, dirs, files in os.walk(self.download_dir):
            # Skip root directory itself
            if Path(root).resolve() == download_root.resolve():
                continue
            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = Path(os.path.join(root, file))
                    self._before_files.add(file_path)

        logger.debug(f"before_files (subdirectories): {len(self._before_files)} items")
        return True

    def _navigate_to_detail_page(self, url: str) -> bool:
        """
        Navigate to detail page and wait for page ready

        Args:
            url: Target URL

        Returns:
            bool: Whether navigation was successful
        """
        # Navigate to detail page
        logger.info(f"Navigating to detail page: {url}")
        if not self.navigate(url):
            return False

        # Handle SPA: sometimes URL changes but page doesn't reload,
        # or URL is still the list page URL.
        # Force a direct GET if we suspect we are stuck.
        time.sleep(2)  # Initial SPA wait
        current_url = self.get_current_url()

        # If still on list page or URL mismatch for detail, force reload
        if "/new/disclosure/stock" in current_url and "/new/disclosure/detail" in url:
            logger.info("SPA detected: forcing direct GET for detail page")
            self.driver.get(url)
            time.sleep(3)

        # Wait for page load indicators
        if not self._wait_for_page_ready():
            # Second attempt if indicators missing
            logger.info("Retrying navigation for detail page...")
            self.driver.get(url)
            if not self._wait_for_page_ready():
                return False

        return True

    def _wait_for_page_ready(self) -> bool:
        """
        Wait for page to be ready

        Returns:
            bool: Whether page is ready
        """
        # 1. 优先等待下载按钮出现（最可靠的就绪标志）
        if self.wait_for_element(
            "//button[contains(., '公告下载')]",
            timeout=ConfigConstants.get_timeout("element_wait"),
            by="xpath",
            condition="visible",
        ):
            logger.info("Download button detected, page ready")
            return True

        # 2. 如果按钮没出现，等待页面标题包含特定内容（表示基本导航完成）
        logger.info(
            "Download button not appeared immediately, waiting for page indicators"
        )
        start_time = time.time()
        max_wait = ConfigConstants.get_timeout("page_load_max_attempts") * ConfigConstants.get_timeout("page_load_check_interval")
        while time.time() - start_time < max_wait:
            title = self.get_page_title()
            if "巨潮资讯网" in title:
                # 即使标题对，也可能内容没加载完，给一点额外时间
                time.sleep(ConfigConstants.get_timeout("page_load_check_interval"))
                return True
            time.sleep(TimeoutConfig.SHORT_WAIT)

        # 3. 检查是否有常见的 SPA 加载指示器（可选，目前通过 sleep 简化）
        time.sleep(3)

        logger.warning("Page load wait finished, but indicators might be missing")
        return True  # 继续执行，让后续重试逻辑处理

    def _click_download_button(self) -> bool:
        """
        Find and click download button

        Returns:
            bool: Whether click was successful
        """
        try:
            # 1. Wait for button to be present
            main_selector = "//button[contains(., '公告下载') or contains(., '下载')]"
            if not self.wait_for_element(
                main_selector, timeout=30, by="xpath", condition="presence"
            ):
                logger.error(
                    "Wait for download button timeout (30s), trying alternative selectors"
                )
                # Fallback to _find_download_button directly which tries alternatives

            # 2. Find the actual button element
            download_btn = self._find_download_button()
            if not download_btn:
                logger.error("No clickable download button found with any selector")
                return False

            # 3. Ensure element is in view and visible
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", download_btn
            )
            time.sleep(1)

            # 4. Click download button
            if not self.click(download_btn):
                logger.info("Normal click failed, trying JavaScript click")
                try:
                    self.driver.execute_script("arguments[0].click();", download_btn)
                except Exception as je:
                    logger.error(f"JavaScript click also failed: {je}")
                    return False

            logger.info("Clicked download button, waiting for file download...")
            return True

        except Exception as e:
            logger.error(f"Error in _click_download_button: {e}")
            return False

    def _wait_and_move_file(self, save_path: str, timeout: int) -> bool:
        """
        Wait for file download to complete and move to target location

        Args:
            save_path: Target save path
            timeout: Timeout in seconds

        Returns:
            bool: Whether download and move were successful
        """
        start_time = time.time()
        check_interval = 0.5

        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            check_interval = min(check_interval * 1.2, 2.0)

            # Check for new file
            downloaded_file = self._check_for_new_file()
            if downloaded_file:
                if self._handle_downloaded_file(downloaded_file, save_path):
                    return True

            # Check if target file already exists (might have been moved by another process)
            if self._check_target_file_exists(save_path):
                return True

            # Output progress info
            self._log_download_progress(start_time)

        # Handle timeout
        return self._handle_timeout(save_path, start_time)

    def _check_for_new_file(self):
        """
        Check for newly downloaded file

        Returns:
            Path or None: Path to newly downloaded file
        """
        if not self.download_dir or not os.path.exists(self.download_dir):
            return None

        after_files = set()
        # Recursively check all directories, including subdirectories
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                # Check PDF files and temp files (.tmp or .crdownload)
                if (
                    file.lower().endswith(".pdf")
                    or file.lower().endswith(".tmp")
                    or file.lower().endswith(".crdownload")
                ):
                    file_path = Path(os.path.join(root, file))
                    after_files.add(file_path)

        logger.debug(f"after_files count: {len(after_files)}")

        new_files = after_files - self._before_files
        logger.debug(f"new_files found: {[str(f) for f in new_files]}")

        if not new_files:
            return None

        # Find largest new file (usually the latest download)
        downloaded_file = None
        max_size = 0
        for f in new_files:
            if f.exists():
                try:
                    size = f.stat().st_size
                    if size > max_size:
                        max_size = size
                        downloaded_file = f
                except:
                    pass

        return downloaded_file

    def _handle_downloaded_file(self, downloaded_file: Path, save_path: str) -> bool:
        """
        Handle downloaded file

        Args:
            downloaded_file: Path to downloaded file
            save_path: Target save path

        Returns:
            bool: Whether handling was successful
        """
        if not downloaded_file or not downloaded_file.exists():
            return False

        # Handle temp files (.tmp or .crdownload)
        actual_file = downloaded_file
        if downloaded_file.suffix in (".tmp", ".crdownload"):
            # This method renames the file to .pdf internally
            if self._wait_for_temp_file_completion(downloaded_file):
                actual_file = downloaded_file.with_suffix(".pdf")
                if not actual_file.exists():
                    logger.error(f"Renamed PDF file not found: {actual_file}")
                    return False
            else:
                return False

        file_size = actual_file.stat().st_size
        if file_size <= FileSizeThreshold.MIN_VALID_PDF:
            logger.debug(f"File size too small: {file_size} bytes")
            return False

        # Move file to target location
        success = self._move_file_to_target(actual_file, save_path)

        # If move successful, clean up potentially residual source file in root directory
        if success:
            self._cleanup_downloaded_file(actual_file, save_path)

        return success

    def _cleanup_downloaded_file(self, downloaded_file: Path, save_path: str):
        """
        Cleanup potentially residual source file after download.
        Delete all files in root and subdirectories with same content or name as target file.
        """
        try:
            download_root = Path(self.download_dir)
            target_path = Path(save_path)

            if not target_path.exists():
                return

            target_size = target_path.stat().st_size
            target_name = target_path.name

            # Use rglob to find all PDFs recursively for cleanup
            all_pdfs = list(download_root.rglob("*.pdf"))
            logger.debug(
                f"[CLEANUP] Scanning for residual files: {len(all_pdfs)} PDFs found"
            )

            for f in all_pdfs:
                try:
                    # NEVER delete target file itself!
                    if f.resolve() == target_path.resolve():
                        continue

                    # If filename is same, or file size same (high probability of same content)
                    if f.name == target_name or (
                        f.stat().st_size == target_size
                        and target_size > FileSizeThreshold.MIN_VALID_PDF
                    ):
                        f.unlink()
                        logger.info(f"[CLEANUP] Cleaned residual file: {f}")
                except Exception as e:
                    logger.debug(f"Failed to clean file {f}: {e}")
        except Exception as e:
            logger.debug(f"Error in _cleanup_downloaded_file: {e}")

    def _find_download_button(self):
        """Find download button"""
        # Main selector
        download_button = self.find_element(
            "//button[contains(., '公告下载')]", by="xpath"
        )
        if download_button:
            return download_button

        # Alternative selectors
        for selector in SelectorConfig.DOWNLOAD_BUTTON_ALTERNATIVES:
            download_button = self.find_element(
                selector, by="xpath" if "//" in selector else "css"
            )
            if download_button:
                logger.info(
                    f"Found download button using alternative selector: {selector}"
                )
                return download_button

        return None

    def _get_pdf_files_in_download_dir(self) -> set:
        """Get set of PDF files in download directory"""
        if not self.download_dir or not os.path.exists(self.download_dir):
            return set()

        files = set()
        # Recursively check all directories, including subdirectories
        for root, dirs, file_list in os.walk(self.download_dir):
            for file in file_list:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and file.lower().endswith(".pdf"):
                    files.add(file_path)
        return files

    def _wait_for_temp_file_completion(self, temp_file: Path) -> bool:
        """
        Wait for temporary file download to complete

        Args:
            temp_file: Path to temp file

        Returns:
            bool: Whether completed
        """
        logger.info(f"Waiting for temp file download to complete: {temp_file}")

        max_wait = ConfigConstants.get_timeout("temp_file_stabilize_timeout")
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < max_wait:
            if not temp_file.exists():
                # Might have been renamed by browser automatically
                pdf_file = temp_file.with_suffix(".pdf")
                if pdf_file.exists():
                    logger.info(
                        "Temp file vanished but PDF found (auto-renamed by browser)"
                    )
                    return True
                return False

            try:
                current_size = temp_file.stat().st_size
                if (
                    current_size == last_size
                    and current_size > FileSizeThreshold.MIN_VALID_PDF
                ):
                    # Stability reached
                    pdf_file = temp_file.with_suffix(".pdf")
                    try:
                        # If target PDF already exists, remove it first
                        if pdf_file.exists():
                            pdf_file.unlink()
                        temp_file.rename(pdf_file)
                        logger.info(
                            f"Temp file stabilized and renamed to PDF: {pdf_file}"
                        )
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to rename temp file: {e}")
                        # If rename failed because PDF now exists (concurrency), check it
                        if pdf_file.exists():
                            return True
                        return False

                last_size = current_size
            except Exception as e:
                logger.debug(f"Error checking temp file status: {e}")

            time.sleep(ConfigConstants.get_timeout("temp_file_check_interval"))

        logger.error(f"Temp file did not stabilize after {max_wait}s")
        return False

    def _move_file_to_target(self, source_file: Path, save_path: str) -> bool:
        """
        Move file to target location

        Args:
            source_file: Source file path
            save_path: Target save path

        Returns:
            bool: Whether move was successful
        """
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        logger.debug(f"downloaded_file: {source_file}")

        # Ensure target directory exists
        target_dir = Path(save_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Check if source and target files are the same
        target_path = Path(save_path)
        if source_file.resolve() == target_path.resolve():
            logger.debug(
                f"Source and target files are the same, no need to move: {source_file}"
            )
            # Still need to verify file size
            if source_file.stat().st_size > FileSizeThreshold.MIN_VALID_PDF:
                logger.info(f"File in place: {save_path}")
                return True
            else:
                logger.debug(f"Invalid file size: {source_file.stat().st_size}")
                return False

        try:
            # Check if source file exists and is accessible
            if (
                not source_file.exists()
                or source_file.stat().st_size <= FileSizeThreshold.MIN_VALID_PDF
            ):
                logger.debug(f"Invalid source file: does not exist or size too small")
                return False

            logger.debug(f"Preparing to move file: {source_file} -> {save_path}")

            # Try to move file
            shutil.move(str(source_file), save_path)

            # Verify if move was successful
            if (
                target_path.exists()
                and target_path.stat().st_size > FileSizeThreshold.MIN_VALID_PDF
            ):
                logger.debug(f"File moved successfully: {save_path}")
                logger.info(f"File download successful: {save_path}")

                # Clean up potentially residual source file (if shutil.move created a copy)
                if source_file.exists():
                    try:
                        source_file.unlink()
                        logger.debug(f"Cleaned residual source file: {source_file}")
                    except:
                        pass

                return True
            else:
                logger.debug(
                    f"File move failed: target file does not exist or size abnormal"
                )
                return False

        except Exception as move_error:
            logger.debug(f"File move exception: {move_error}")
            return False

    def _check_target_file_exists(self, save_path: str) -> bool:
        """
        Check if target file already exists

        Args:
            save_path: Target path

        Returns:
            bool: Whether file exists
        """
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        if (
            os.path.exists(save_path)
            and os.path.getsize(save_path) > FileSizeThreshold.MIN_VALID_PDF
        ):
            logger.info(f"File already downloaded: {save_path}")
            return True
        return False

    def _log_download_progress(self, start_time: float):
        """
        Log download progress info

        Args:
            start_time: Start time
        """
        # Check temp files (recursively check all directories)
        temp_files = []
        if self.download_dir and os.path.exists(self.download_dir):
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    if file.endswith(".crdownload") or file.endswith(".tmp"):
                        temp_files.append(os.path.join(root, file))

        # Output progress info
        elapsed = time.time() - start_time
        if elapsed > 10 and elapsed % 10 < 1:  # Output status every 10 seconds
            logger.info(
                f"Download status: Waited {elapsed:.1f}s, Temp files: {len(temp_files)}"
            )
            if self.download_dir and os.path.exists(self.download_dir):
                current_files = list(Path(self.download_dir).rglob(r"*\*"))
                logger.info(f"Current files in download dir: {len(current_files)}")

    def _handle_timeout(self, save_path: str, start_time: float) -> bool:
        """
        Handle download timeout

        Args:
            save_path: Target save path
            start_time: Start time

        Returns:
            bool: Always returns False
        """
        elapsed = time.time() - start_time
        logger.error(f"File download timeout ({elapsed:.1f}s): {save_path}")

        # Check if partial file exists at target
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.error(f"Partial file exists but timed out: {file_size} bytes")
            try:
                os.remove(save_path)
                logger.info(f"Removed partial file: {save_path}")
            except:
                pass

        # Check download root for potentially orphan files
        if self.download_dir and os.path.exists(self.download_dir):
            try:
                download_root = Path(self.download_dir)
                orphan_pdfs = list(download_root.glob("*.pdf"))
                # If we find PDFs in root during a timeout, they are likely orphans from this failed attempt
                for orphan in orphan_pdfs:
                    try:
                        orphan.unlink()
                        logger.info(f"Cleaned orphan PDF during timeout: {orphan}")
                    except:
                        pass
            except:
                pass

        return False

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        Go to next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether successfully went to next page
        """
        if not self.driver:
            logger.error("Browser not initialized, cannot go to next page")
            return False

        try:
            from selenium.common.exceptions import (
                NoSuchElementException,
                TimeoutException,
            )
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            from ..utils.debug_marker import DebugMarker

            # DEBUG MARKER: Start pagination attempt
            marker = DebugMarker("pagination")
            marker.add_step(
                "pagination_start",
                "Start pagination operation",
                {
                    "current_url": (
                        self.driver.current_url if self.driver else "no_driver"
                    )
                },
            )

            next_selectors = [
                # Primary selector - verified by diagnostic results
                ".el-pager li.number.active + li.number",
                # Element UI pagination buttons
                "button.el-pagination__next:not(.is-disabled)",
                # Alternative Element UI patterns
                ".el-pager li.active + li.number",
                ".el-pager li.number.active + li",
                # Backup selectors
                "button.el-pagination__next:not([disabled])",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
            ]

            marker.add_step(
                "selectors_defined",
                "Selector list defined",
                {"selectors_count": len(next_selectors)},
            )

            for idx, selector in enumerate(next_selectors):
                try:
                    marker.add_step(
                        f"try_selector_{idx}",
                        f"Try selector {idx}",
                        {"selector": selector},
                    )

                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    marker.add_step(
                        f"found_element_{idx}",
                        f"Found element {idx}",
                        {
                            "selector": selector,
                            "enabled": (
                                next_button.is_enabled() if next_button else None
                            ),
                            "displayed": (
                                next_button.is_displayed() if next_button else None
                            ),
                            "text": next_button.text if next_button else None,
                        },
                    )

                    if (
                        next_button
                        and next_button.is_enabled()
                        and next_button.is_displayed()
                    ):
                        # Scroll to element
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView();", next_button
                        )
                        time.sleep(TimeoutConfig.SCROLL_DELAY)

                        marker.add_step(
                            f"clicking_{idx}",
                            f"Clicking next page button {idx}",
                            {"selector": selector, "button_text": next_button.text},
                        )

                        # Click next page
                        next_button.click()

                        marker.add_step(
                            f"clicked_{idx}",
                            f"Clicked {idx}",
                            {
                                "selector": selector,
                                "url_before_click": self.driver.current_url,
                            },
                        )

                        # Wait for page load (independent try-catch, does not affect overall success)
                        try:
                            WebDriverWait(self.driver, timeout).until(
                                EC.staleness_of(next_button)
                            )
                            marker.add_step(
                                f"page_loaded_{idx}",
                                f"Page loaded {idx}",
                                {"selector": selector},
                            )
                        except TimeoutException:
                            marker.add_step(
                                f"page_load_timeout_{idx}",
                                f"Page load timeout {idx} (but click successful)",
                                {"selector": selector},
                            )
                            # Click successful, return True even if wait timeout

                        # CRITICAL: Add extra wait and URL verification
                        time.sleep(
                            TimeoutConfig.CLICK_STABILIZATION
                        )  # Additional wait for page stabilization
                        url_after_click = self.driver.current_url
                        marker.add_step(
                            f"url_after_click_{idx}",
                            f"URL status after click",
                            {
                                "selector": selector,
                                "url_after_click": url_after_click,
                                "url_changed": (
                                    url_after_click != self.driver.current_url
                                    if hasattr(self, "_last_url")
                                    else "unknown"
                                ),
                            },
                        )

                        # Store current URL for next comparison
                        self._last_url = url_after_click

                        marker.add_step(
                            "pagination_success",
                            "Pagination successful",
                            {"selector_used": selector, "final_url": url_after_click},
                        )
                        marker.save()
                        return True

                except (NoSuchElementException, TimeoutException) as e:
                    marker.add_step(
                        f"selector_failed_{idx}",
                        f"Selector {idx} failed",
                        {"selector": selector, "error": str(e)},
                    )
                    continue
                except Exception as e:
                    marker.add_step(
                        f"unexpected_error_{idx}",
                        f"Selector {idx} exception",
                        {"selector": selector, "error": str(e)},
                    )
                    continue

            marker.add_step(
                "pagination_failed",
                "Next page button not found or reached last page",
                {},
            )
            marker.save()
            logger.info("Next page button not found or reached last page")
            return False

        except Exception as e:
            marker.add_step(
                "pagination_exception",
                "Pagination operation exception",
                {"error": str(e)},
            )
            marker.save()
            logger.error(f"Failed to go to next page: {e}")
            return False

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        Go to specified page number

        Args:
            page_number: Target page number
            timeout: Timeout in seconds

        Returns:
            bool: Whether successfully jumped to page
        """
        if not self.driver:
            logger.error("Browser not initialized, cannot go to page")
            return False

        try:
            from selenium.common.exceptions import (
                NoSuchElementException,
                TimeoutException,
            )
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            # Method 1: Find page input box and go button
            page_input_selectors = [
                "input.el-pagination__editor",
                "input.page-input",
                "input[type='number']",
                "input.pagination-input",
            ]

            go_button_selectors = [
                "button.el-pagination__jump",
                "button.page-go",
                "button:contains('跳转')",
                "button:contains('Go')",
            ]

            for input_selector, button_selector in zip(
                page_input_selectors, go_button_selectors
            ):
                try:
                    # Find page input box
                    page_input = self.driver.find_element(
                        By.CSS_SELECTOR, input_selector
                    )
                    if not page_input.is_enabled() or not page_input.is_displayed():
                        continue

                    # Find go button
                    go_button = self.driver.find_element(
                        By.CSS_SELECTOR, button_selector
                    )
                    if not go_button.is_enabled() or not go_button.is_displayed():
                        continue

                    # Clear input box and enter page number
                    page_input.clear()
                    page_input.send_keys(str(page_number))

                    # Click go button
                    go_button.click()

                    # Wait for page load
                    WebDriverWait(self.driver, timeout).until(
                        EC.staleness_of(page_input)
                    )

                    logger.info(f"Successfully jumped to page {page_number}")
                    return True

                except (NoSuchElementException, TimeoutException):
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
                    page_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for page_button in page_buttons:
                        if page_button.is_enabled() and page_button.is_displayed():
                            button_text = page_button.text.strip()
                            if button_text == str(page_number):
                                # Scroll to element
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView();", page_button
                                )
                                time.sleep(TimeoutConfig.SCROLL_DELAY)

                                # Click page button
                                page_button.click()

                                # Wait for page load
                                time.sleep(TimeoutConfig.LONG_WAIT)
                                logger.info(
                                    f"Successfully jumped to page {page_number}"
                                )
                                return True

                except (NoSuchElementException, TimeoutException):
                    continue

            logger.warning(f"Failed to jump to page {page_number}")
            return False

        except Exception as e:
            logger.error(f"Failed to jump to specified page: {e}")
            return False

    def has_next_page(self, timeout: int = 5) -> bool:
        """
        Check if there is a next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether there is a next page
        """
        if not self.driver:
            logger.error("Browser not initialized, cannot check for next page")
            return False

        try:
            import time

            from selenium.common.exceptions import (
                NoSuchElementException,
                TimeoutException,
            )
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait

            from ..utils.debug_marker import DebugMarker

            # DEBUG MARKER: Start has_next_page check
            marker = DebugMarker("has_next_page")
            current_url = self.driver.current_url if self.driver else "no_driver"
            marker.add_step(
                "check_start",
                "Start checking next page",
                {"current_url": current_url, "timestamp": time.time()},
            )

            # CRITICAL FIX: Add wait mechanism to ensure DOM is ready after previous pagination
            # This is the key difference from go_to_next_page() that was causing validation failures
            marker.add_step("wait_for_stability", "Wait for page stability", {})
            time.sleep(TimeoutConfig.MEDIUM_WAIT)  # Wait for DOM to stabilize

            # Also wait for any pending network requests or DOM updates
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )
                marker.add_step(
                    "dom_ready",
                    "DOM ready",
                    {
                        "current_url_after_wait": (
                            self.driver.current_url if self.driver else "no_driver"
                        )
                    },
                )
            except TimeoutException:
                marker.add_step(
                    "dom_wait_timeout",
                    "DOM wait timeout, continuing anyway",
                    {
                        "current_url_after_timeout": (
                            self.driver.current_url if self.driver else "no_driver"
                        )
                    },
                )

            # DEBUG: Check page content before selector search
            try:
                page_source_preview = (
                    self.driver.page_source[:500] if self.driver else ""
                )
                marker.add_step(
                    "page_source_check",
                    "Page source preview",
                    {
                        "length": len(page_source_preview),
                        "has_pagination": "el-pager" in page_source_preview
                        or "pagination" in page_source_preview,
                        "current_url_final": (
                            self.driver.current_url if self.driver else "no_driver"
                        ),
                    },
                )
            except:
                pass

            next_selectors = [
                # Primary selector - verified by diagnostic results
                ".el-pager li.number.active + li.number",
                # Element UI pagination buttons
                "button.el-pagination__next:not(.is-disabled)",
                # Alternative Element UI patterns
                ".el-pager li.active + li.number",
                ".el-pager li.number.active + li",
                # Backup selectors
                "button.el-pagination__next:not([disabled])",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
            ]

            marker.add_step(
                "selectors_defined",
                "Selector list defined",
                {"selectors_count": len(next_selectors)},
            )

            for idx, selector in enumerate(next_selectors):
                try:
                    # Add small wait between selector attempts
                    if idx > 0:
                        time.sleep(TimeoutConfig.SELECTOR_RETRY)

                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    marker.add_step(
                        f"check_selector_{idx}",
                        f"Check selector {idx}",
                        {
                            "selector": selector,
                            "found": next_button is not None,
                            "enabled": (
                                next_button.is_enabled() if next_button else None
                            ),
                            "displayed": (
                                next_button.is_displayed() if next_button else None
                            ),
                        },
                    )

                    if (
                        next_button
                        and next_button.is_enabled()
                        and next_button.is_displayed()
                    ):
                        marker.add_step(
                            "has_next_page_true",
                            "Detected next page button",
                            {"selector": selector},
                        )
                        marker.save()
                        return True
                except (NoSuchElementException, TimeoutException):
                    marker.add_step(
                        f"selector_not_found_{idx}",
                        f"Selector {idx} not found",
                        {"selector": selector},
                    )
                    continue
                except Exception as e:
                    marker.add_step(
                        f"selector_error_{idx}",
                        f"Selector {idx} error",
                        {"selector": selector, "error": str(e)},
                    )
                    continue

            marker.add_step("has_next_page_false", "Next page button not found", {})
            marker.save()
            return False

        except Exception as e:
            marker.add_step(
                "check_exception", "Exception checking next page", {"error": str(e)}
            )
            marker.save()
            logger.warning(f"Failed to check next page: {e}")
            return False
