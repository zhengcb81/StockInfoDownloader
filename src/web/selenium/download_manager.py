"""
Selenium Download Manager Module

Provides file download management and handling functionality.
"""

import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Set

from ...core.config_constants import ConfigConstants
from ...core.constants import FileSizeThreshold, SelectorConfig, TimeoutConfig
from ...core.logger import get_logger

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

logger = get_logger(__name__)


class DownloadManager:
    """Manages file downloads for Selenium browser"""

    def __init__(self, driver: "WebDriver", download_dir: Optional[str] = None):
        """Initialize download manager"""
        self.driver = driver
        self.download_dir = download_dir
        self._before_files: Set[Path] = set()
        self.download_count = 0

    def download_file(self, url: str, save_path: str, timeout: int = 60) -> bool:
        """
        Download file to specified path

        Args:
            url: URL to download
            save_path: File save path
            timeout: Timeout in seconds (default: 60)

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
        """Prepare download: clean root PDFs and record status"""
        if not self.download_dir or not os.path.exists(self.download_dir):
            return True

        download_root = Path(self.download_dir)
        try:
            # Clean up ANY PDF files in the download root directory
            for f in download_root.glob("*.pdf"):
                try:
                    f.unlink()
                    logger.info(f"Cleaned pre-existing orphan PDF in root: {f}")
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error during pre-download cleanup: {e}")

        # Record file list before download - ONLY in subdirectories
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
        """Navigate to detail page and wait for page ready"""
        from selenium.webdriver.common.by import By

        # Navigate to detail page
        logger.info(f"Navigating to detail page: {url}")
        try:
            self.driver.get(url)
        except Exception as e:
            logger.error(f"Failed to navigate: {e}")
            return False

        # Handle SPA: sometimes URL changes but page doesn't reload
        time.sleep(2)  # Initial SPA wait
        current_url = self.driver.current_url

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
        """Wait for page to be ready"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        # 1. Wait for download button
        try:
            wait = WebDriverWait(
                self.driver, ConfigConstants.get_timeout("element_wait")
            )
            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//button[contains(., '公告下载')]")
                )
            )
            logger.info("Download button detected, page ready")
            return True
        except:
            pass

        # 2. Wait for page title
        logger.info(
            "Download button not appeared immediately, waiting for page indicators"
        )
        start_time = time.time()
        max_wait = (
            ConfigConstants.get_timeout("page_load_max_attempts")
            * ConfigConstants.get_timeout("page_load_check_interval")
        )
        while time.time() - start_time < max_wait:
            try:
                title = self.driver.title
                if "巨潮资讯网" in title:
                    time.sleep(ConfigConstants.get_timeout("page_load_check_interval"))
                    return True
            except:
                pass
            time.sleep(TimeoutConfig.SHORT_WAIT)

        # 3. Give it more time
        time.sleep(3)
        logger.warning("Page load wait finished, but indicators might be missing")
        return True

    def _click_download_button(self) -> bool:
        """Find and click download button"""
        from selenium.webdriver.common.by import By

        try:
            # 1. Wait for button to be present
            main_selector = "//button[contains(., '公告下载') or contains(., '下载')]"
            try:
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                wait = WebDriverWait(self.driver, 30)
                wait.until(
                    EC.presence_of_element_located((By.XPATH, main_selector))
                )
            except:
                logger.error(
                    "Wait for download button timeout (30s), trying alternative selectors"
                )

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
            try:
                download_btn.click()
            except Exception:
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

    def _find_download_button(self):
        """Find download button"""
        from selenium.webdriver.common.by import By

        # Main selector
        try:
            download_button = self.driver.find_element(
                By.XPATH, "//button[contains(., '公告下载')]"
            )
            if download_button:
                return download_button
        except:
            pass

        # Alternative selectors
        for selector in SelectorConfig.DOWNLOAD_BUTTON_ALTERNATIVES:
            try:
                by_type = By.XPATH if "//" in selector else By.CSS_SELECTOR
                download_button = self.driver.find_element(by_type, selector)
                if download_button:
                    logger.info(
                        f"Found download button using alternative selector: {selector}"
                    )
                    return download_button
            except:
                continue

        return None

    def _wait_and_move_file(self, save_path: str, timeout: int) -> bool:
        """Wait for file download to complete and move to target location"""
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

            # Check if target file already exists
            if self._check_target_file_exists(save_path):
                return True

            # Output progress info
            self._log_download_progress(start_time)

        # Handle timeout
        return self._handle_timeout(save_path, start_time)

    def _check_for_new_file(self) -> Optional[Path]:
        """Check for newly downloaded file"""
        if not self.download_dir or not os.path.exists(self.download_dir):
            return None

        after_files = set()
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
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

        # Find largest new file
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
        """Handle downloaded file"""
        if not downloaded_file or not downloaded_file.exists():
            return False

        # Handle temp files
        actual_file = downloaded_file
        if downloaded_file.suffix in (".tmp", ".crdownload"):
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

        if success:
            self._cleanup_downloaded_file(actual_file, save_path)
            self.download_count += 1

        return success

    def _wait_for_temp_file_completion(self, temp_file: Path) -> bool:
        """Wait for temporary file download to complete"""
        logger.info(f"Waiting for temp file download to complete: {temp_file}")

        max_wait = ConfigConstants.get_timeout("temp_file_stabilize_timeout")
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < max_wait:
            if not temp_file.exists():
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
                    pdf_file = temp_file.with_suffix(".pdf")
                    try:
                        if pdf_file.exists():
                            pdf_file.unlink()
                        temp_file.rename(pdf_file)
                        logger.info(
                            f"Temp file stabilized and renamed to PDF: {pdf_file}"
                        )
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to rename temp file: {e}")
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
        """Move file to target location"""
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        logger.debug(f"downloaded_file: {source_file}")

        target_dir = Path(save_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = Path(save_path)
        if source_file.resolve() == target_path.resolve():
            logger.debug(
                f"Source and target files are the same, no need to move: {source_file}"
            )
            if source_file.stat().st_size > FileSizeThreshold.MIN_VALID_PDF:
                logger.info(f"File in place: {save_path}")
                return True
            else:
                logger.debug(f"Invalid file size: {source_file.stat().st_size}")
                return False

        try:
            if (
                not source_file.exists()
                or source_file.stat().st_size <= FileSizeThreshold.MIN_VALID_PDF
            ):
                logger.debug(f"Invalid source file: does not exist or size too small")
                return False

            logger.debug(f"Preparing to move file: {source_file} -> {save_path}")

            shutil.move(str(source_file), save_path)

            if (
                target_path.exists()
                and target_path.stat().st_size > FileSizeThreshold.MIN_VALID_PDF
            ):
                logger.debug(f"File moved successfully: {save_path}")
                logger.info(f"File download successful: {save_path}")

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

    def _cleanup_downloaded_file(self, downloaded_file: Path, save_path: str):
        """Cleanup potentially residual source file after download"""
        try:
            download_root = Path(self.download_dir) if self.download_dir else None
            target_path = Path(save_path)

            if not download_root or not target_path.exists():
                return

            target_size = target_path.stat().st_size
            target_name = target_path.name

            all_pdfs = list(download_root.rglob("*.pdf"))
            logger.debug(
                f"[CLEANUP] Scanning for residual files: {len(all_pdfs)} PDFs found"
            )

            for f in all_pdfs:
                try:
                    if f.resolve() == target_path.resolve():
                        continue

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

    def _check_target_file_exists(self, save_path: str) -> bool:
        """Check if target file already exists"""
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        if (
            os.path.exists(save_path)
            and os.path.getsize(save_path) > FileSizeThreshold.MIN_VALID_PDF
        ):
            logger.info(f"File already downloaded: {save_path}")
            return True
        return False

    def _log_download_progress(self, start_time: float):
        """Log download progress info"""
        temp_files = []
        if self.download_dir and os.path.exists(self.download_dir):
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    if file.endswith(".crdownload") or file.endswith(".tmp"):
                        temp_files.append(os.path.join(root, file))

        elapsed = time.time() - start_time
        if elapsed > 10 and elapsed % 10 < 1:
            logger.info(
                f"Download status: Waited {elapsed:.1f}s, Temp files: {len(temp_files)}"
            )
            if self.download_dir and os.path.exists(self.download_dir):
                current_files = list(Path(self.download_dir).rglob(r"*\*"))
                logger.info(f"Current files in download dir: {len(current_files)}")

    def _handle_timeout(self, save_path: str, start_time: float) -> bool:
        """Handle download timeout"""
        elapsed = time.time() - start_time
        logger.error(f"File download timeout ({elapsed:.1f}s): {save_path}")

        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.error(f"Partial file exists but timed out: {file_size} bytes")
            try:
                os.remove(save_path)
                logger.info(f"Removed partial file: {save_path}")
            except:
                pass

        return False


# Module exports
__all__ = ["DownloadManager"]
