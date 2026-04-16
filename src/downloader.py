"""Core downloader — handles the full download workflow.

This is the heart of the project. ~350 lines doing what the old project needed
29,000 lines for.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import constants as C
from .browser import PlaywrightBrowser
from .exceptions import BrowserError, DownloadError, OrgIdError
from .logger import log
from .mapping import MappingManager
from .models import DownloadRequest, DownloadResult
from .string_utils import clean_filename


class FailedDownloadLogger:
    """Logs failed downloads to a JSON file for later retry."""

    def __init__(self, log_file: str = "logs/failed_downloads.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._failed: List[Dict[str, Any]] = []

    def record(self, stock_code: str, stock_name: str, text: str, url: str, error: str) -> None:
        """Record a failed download."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stock_code": stock_code,
            "stock_name": stock_name,
            "file_name": text,
            "url": url,
            "error": error,
        }
        self._failed.append(entry)
        self._save()

    def get_failed(self) -> List[Dict[str, Any]]:
        """Get all recorded failed downloads."""
        return self._failed.copy()

    def _save(self) -> None:
        """Persist failed downloads to file."""
        try:
            existing = []
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.extend(self._failed)
            self._failed = []  # Clear after saving
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Failed to save failed downloads log: {e}")


def _matches_keywords(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text matches any keyword. Supports date-based matching."""
    if not keywords:
        return True
    cleaned = "".join(text.split()).lower()
    for k in keywords:
        ck = "".join(k.split()).lower()
        if ck in cleaned:
            return True
        # Date-based match (e.g., "20250725")
        date_match = re.search(r"\d{8}", k)
        if date_match and date_match.group() in cleaned:
            return True
    return False


class StockDownloader:
    """Downloads stock documents from cninfo.com.cn."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.save_dir = config.get("save_dir", C.DEFAULT_SAVE_DIR)
        self.max_retries = int(config.get("max_retries", 3))
        self.headless = config.get("headless", True)

        # Browser (lazy init)
        self._browser: Optional[PlaywrightBrowser] = None
        self._mapping: Optional[MappingManager] = None

        # E2E test verification fields
        self.skipped_files: List[str] = []
        self.pages_traversed: int = 0
        self.download_count: int = 0

        # Failed download logger
        self._failed_logger = FailedDownloadLogger()

    @property
    def browser(self) -> PlaywrightBrowser:
        if not self._browser:
            self._browser = PlaywrightBrowser(
                headless=self.headless,
                download_dir=self.save_dir,
                config=self.config,
            )
            self._browser.initialize()
        return self._browser

    @property
    def mapping(self) -> MappingManager:
        if not self._mapping:
            self._mapping = MappingManager(
                browser_strategy=self.browser,
                browser_strategy_type="playwright",
            )
        return self._mapping

    # ── Public API ────────────────────────────────────────────────────

    def download(self, request: DownloadRequest) -> DownloadResult:
        """Download documents for a stock. Main entry point."""
        log.info(f"Starting download for {request.stock_code}")
        start = time.time()

        # Reset state
        self.skipped_files = []
        self.pages_traversed = 0

        try:
            # Resolve org_id
            if not request.org_id:
                force_crawl = self.config.get("force_crawl_mapping", False)
                request.org_id = self.mapping.get_org_id(
                    request.stock_code, force_refresh=force_crawl
                )
                if not request.org_id:
                    raise OrgIdError(
                        f"Cannot resolve org_id for {request.stock_code}",
                        stock_code=request.stock_code,
                    )

            # Resolve stock name
            if not request.stock_name:
                request.stock_name = (
                    self.mapping.get_stock_name(request.stock_code)
                    or f"Stock_{request.stock_code}"
                )

            # Download with retry
            return self._download_with_retry(request, start)

        except Exception as e:
            log.error(f"Download failed for {request.stock_code}: {e}")
            return DownloadResult(
                success=False,
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )

    def download_activity_records(self, **kwargs: Any) -> List[str]:
        """Compatibility entry point matching old UnifiedDownloader API.

        Resolves org_id and stock name, then delegates to download().
        """
        request = DownloadRequest(
            stock_code=kwargs.get("stock_code", ""),
            stock_name=kwargs.get("stock_name"),
            suffix=kwargs.get("suffix", "research"),
            allowed_keywords=kwargs.get("allowed_keywords"),
            max_pages=kwargs.get("max_pages", 5),
            save_dir=kwargs.get("save_dir", self.save_dir),
            reverse_order=kwargs.get("reverse_order", False),
        )
        result = self.download(request)
        return result.downloaded_files

    def cleanup(self) -> None:
        """Shut down browser."""
        if self._browser:
            self._browser.close()
            self._browser = None

    # ── Download Pipeline ─────────────────────────────────────────────

    def _download_with_retry(
        self, request: DownloadRequest, start_time: float
    ) -> DownloadResult:
        """Retry wrapper around the core download logic."""
        last_result = DownloadResult(success=False)

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                log.info(f"Retry attempt {attempt}/{self.max_retries}")
                try:
                    self.browser.restart()
                except Exception:
                    pass

            last_result = self._download_internal(request)
            if last_result.success:
                return last_result

            log.warning(f"Attempt {attempt + 1} failed: {last_result.errors}")
            if attempt < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s, ...
                backoff = 2 ** attempt
                log.info(f"Waiting {backoff}s before retry...")
                time.sleep(backoff)
                # Clear cookies for fresh session
                self.browser.clear_cookies()

        last_result.duration_seconds = time.time() - start_time
        return last_result

    def _download_internal(self, request: DownloadRequest) -> DownloadResult:
        """Core download logic."""
        start = time.time()
        downloaded: List[str] = []

        try:
            self._navigate_to_stock_page(request)
            self._wait_for_page_load()

            if request.suffix:
                self._switch_tab(request.suffix)

            downloaded = self._download_pages(request)

            return DownloadResult(
                success=True,
                downloaded_files=downloaded,
                total_files=len(downloaded),
                duration_seconds=time.time() - start,
                skipped_files=self.skipped_files,
                pages_traversed=self.pages_traversed,
            )
        except Exception as e:
            log.error(f"Download pipeline failed: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=downloaded,
                errors=[str(e)],
                duration_seconds=time.time() - start,
            )

    def _navigate_to_stock_page(self, request: DownloadRequest) -> None:
        """Navigate to the stock detail page."""
        url = C.STOCK_PAGE_URL_TEMPLATE.format(
            stock_code=request.stock_code, org_id=request.org_id
        )
        if request.suffix:
            url += f"#{request.suffix}"

        log.info(f"Navigating to: {url}")
        if not self.browser.navigate(url):
            raise BrowserError(f"Failed to navigate to {url}")

    def _wait_for_page_load(self) -> None:
        """Poll until data links appear on the page."""
        for _ in range(C.PAGE_LOAD_MAX_ATTEMPTS):
            time.sleep(C.PAGE_LOAD_CHECK_INTERVAL)
            links = self._get_links()
            if links:
                return
            log.debug("Waiting for data links to load...")

    def _switch_tab(self, suffix: str) -> None:
        """Switch to the correct SPA tab."""
        time.sleep(C.SPA_TAB_SWITCH_WAIT)
        self.browser.execute_script(
            f'document.querySelector(\'a[href*="{suffix}"]\')?.click()'
        )
        time.sleep(C.CONTENT_LOAD_WAIT)
        # Extra wait for latestAnnouncement tab (heavy SPA content)
        if suffix == "latestAnnouncement":
            # Wait for pagination element to render (not just links)
            for _ in range(10):
                time.sleep(2)
                info = self.browser.get_current_page_info()
                total = info.get("total_pages", 1)
                if total > 1:
                    log.info(f"Pagination loaded: {total} pages")
                    break
                log.debug(f"Waiting for pagination... (total={total})")
            self._wait_for_page_load()

    # ── Page Traversal ────────────────────────────────────────────────

    def _download_pages(self, request: DownloadRequest) -> List[str]:
        """Download files across multiple pages."""
        all_downloaded: List[str] = []

        if request.reverse_order:
            all_downloaded = self._download_reverse(request)
        else:
            all_downloaded = self._download_forward(request)

        return all_downloaded

    def _download_forward(self, request: DownloadRequest) -> List[str]:
        """Download from page 1 forward."""
        all_downloaded: List[str] = []

        for page in range(1, request.max_pages + 1):
            log.info(f"Processing page {page}...")
            self.pages_traversed = page
            downloaded = self._download_page_links(request, page)
            all_downloaded.extend(downloaded)

            if not self.browser.go_to_next_page():
                break
            time.sleep(C.PAGINATION_WAIT)

        return all_downloaded

    def _download_reverse(self, request: DownloadRequest) -> List[str]:
        """Download from last page backward."""
        page_info = self.browser.get_current_page_info()
        total_pages = page_info.get("total_pages", 1)
        log.info(f"Reverse order: total_pages={total_pages}")

        # Jump to last page
        self.browser.go_to_last_page()
        time.sleep(3)
        self._wait_for_page_load()

        current_info = self.browser.get_current_page_info()
        current_page = current_info.get("current_page", total_pages)
        log.info(f"Jumped to last page: {current_page}")

        all_downloaded: List[str] = []
        pages_to_check = min(request.max_pages, current_page)

        for i in range(pages_to_check):
            page = current_page - i
            log.info(f"Processing page {page}/{total_pages}...")
            self.pages_traversed = i + 1

            downloaded = self._download_page_links(request, page)
            all_downloaded.extend(downloaded)

            # Early exit if we found files
            if downloaded and request.allowed_keywords:
                log.info(f"Found target files on page {page}, stopping")
                break

            # Go to previous page
            if i < pages_to_check - 1 and page > 1:
                self.browser.execute_script("""
                    (() => {
                        const prev = document.querySelector('.btn-prev');
                        if (prev && !prev.disabled) prev.click();
                    })()
                """)
                time.sleep(C.PAGINATION_WAIT)
                self._wait_for_page_load()

        return all_downloaded

    # ── Link Processing ───────────────────────────────────────────────

    def _download_page_links(
        self, request: DownloadRequest, page: int
    ) -> List[str]:
        """Match and download links on the current page."""
        links = self._get_links()
        log.info(f"Page {page}: found {len(links)} links")

        if not links:
            log.warning(f"No links on page {page}, saving debug screenshot")
            self.browser.take_screenshot(
                f"logs/debug_page_{request.stock_code}_p{page}.png"
            )

        downloaded: List[str] = []
        for text, href in links:
            if _matches_keywords(text, request.allowed_keywords):
                result = self._download_single_link(request, text, href)
                if result:
                    downloaded.append(result)
        return downloaded

    def _download_single_link(
        self, request: DownloadRequest, text: str, href: str
    ) -> Optional[str]:
        """Download a single file."""
        target_name = clean_filename(text)
        save_dir = Path(str(request.save_dir)) if request.save_dir else Path(self.save_dir)
        dest = save_dir / (request.stock_name or f"Stock_{request.stock_code}") / f"{target_name}.pdf"

        # Skip if already exists
        if dest.exists() and dest.stat().st_size > C.MIN_FILE_SIZE:
            log.info(f"File exists, skipping: {dest}")
            self.skipped_files.append(str(dest))
            return str(dest)

        log.info(f"Downloading: {text}")
        if self.browser.download_file(href, str(dest)):
            if dest.exists() and dest.stat().st_size > C.MIN_FILE_SIZE:
                self.download_count += 1
                time.sleep(1)
                return str(dest)
            else:
                error_msg = f"File invalid or too small: {dest}"
                log.error(error_msg)
                self._failed_logger.record(
                    request.stock_code, request.stock_name or "", text, href, error_msg
                )
        else:
            self._failed_logger.record(
                request.stock_code, request.stock_name or "", text, href, "download_file returned False"
            )

        time.sleep(1)
        return None

    def _get_links(self) -> List[Tuple[str, str]]:
        """Extract detail links from the current page."""
        results: List[Tuple[str, str]] = []

        # Try XPath selector first (more precise)
        elements = self.browser.find_elements(C.DETAIL_LINKS_XPATH, by="xpath")

        # Fallback to all <a> tags
        if not elements:
            elements = self.browser.find_elements("a")

        for el in elements:
            try:
                href = self.browser.get_attribute(el, "href") or ""
                if "/detail" not in href:
                    continue
                text = self.browser.get_text(el).strip()
                if not text:
                    continue
                abs_url = href if href.startswith("http") else C.BASE_URL + href
                results.append((text, abs_url))
            except Exception:
                continue

        return results
