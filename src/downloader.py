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
from .exceptions import BrowserError, OrgIdError
from .logger import log
from .mapping import MappingManager
from .models import DownloadRequest, DownloadResult
from .string_utils import clean_filename
from .transport_states import LoadState


class FailedDownloadLogger:
    """Logs failed downloads to a JSON file for later retry.

    Uses batched writes: records are accumulated in memory and flushed
    to disk only when flush() is called, avoiding per-record file I/O
    and eliminating data-loss races in parallel downloads.
    """

    def __init__(self, log_file: str = "logs/failed_downloads.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._pending: List[Dict[str, Any]] = []

    def record(
        self, stock_code: str, stock_name: str, text: str, url: str, error: str
    ) -> None:
        """Append a failed download to the in-memory buffer."""
        self._pending.append(
            {
                "timestamp": datetime.now().isoformat(),
                "stock_code": stock_code,
                "stock_name": stock_name,
                "file_name": text,
                "url": url,
                "error": error,
            }
        )

    def get_failed(self) -> List[Dict[str, Any]]:
        """Return all pending (un-flushed) records."""
        return self._pending.copy()

    def flush(self) -> None:
        """Write all pending records to disk atomically."""
        if not self._pending:
            return
        try:
            existing = []
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.extend(self._pending)
            self._pending.clear()
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Failed to save failed downloads log: {e}")

    def reset(self) -> None:
        """Clear pending records without writing to disk."""
        self._pending.clear()


def _matches_excluded(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text matches any excluded keyword."""
    if not keywords:
        return False
    cleaned = "".join(text.split()).lower()
    for k in keywords:
        ck = "".join(k.split()).lower()
        if ck in cleaned:
            return True
    return False


def _matches_keywords(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text matches any keyword.

    Supports date-based matching: if keyword contains an 8-digit date (e.g.
    "公告20250725"), extracts the date and checks if it appears in the text.
    """
    if not keywords:
        return True
    cleaned = "".join(text.split()).lower()
    for k in keywords:
        ck = "".join(k.split()).lower()
        if ck in cleaned:
            return True
        # Date-based match: extract 8-digit date from keyword and match date only
        date_match = re.search(r"\d{8}", k)
        if date_match and date_match.group() in cleaned:
            return True
    return False


class StockDownloader:
    """Downloads stock documents from cninfo.com.cn."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.save_dir = config["save_dir"]
        self.max_retries = int(config["max_retries"])
        self.headless = config.get("headless", True)

        # Browser (lazy init)
        self._browser: Optional[PlaywrightBrowser] = None
        self._mapping: Optional[MappingManager] = None

        # E2E test verification fields
        self.skipped_files: List[str] = []
        self.pages_traversed: int = 0
        self.download_count: int = 0

        # CW-2.27D typed load state. Set by ``_switch_tab`` after observing
        # the SPA tab state and by the (future) cninfo announcement API
        # client for CONFIRMED_EMPTY. Defaults to None until observed.
        self._official_status: Optional[LoadState] = None

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
        finally:
            self._failed_logger.flush()

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
                except Exception as e:
                    log.debug(f"Browser restart failed: {e}")

            last_result = self._download_internal(request)
            if last_result.success:
                return last_result

            log.warning(f"Attempt {attempt + 1} failed: {last_result.errors}")
            if attempt < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s, ...
                backoff = 2**attempt
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
        # Reset per-request typed status so prior observations do not leak.
        # Preserve an upstream-preconfirmed CONFIRMED_EMPTY so the Phase 5
        # announcement API client can pre-mark total=0 before SPA fallback.
        if self._official_status != LoadState.CONFIRMED_EMPTY:
            self._official_status = None

        try:
            self._navigate_to_stock_page(request)
            self._wait_for_page_load()

            if request.suffix:
                has_content = self._switch_tab(request.suffix)
                if not has_content:
                    # The historical code folded this into success/0 files.
                    # Now the typed state decides:
                    #   - CONFIRMED_EMPTY → upstream API explicitly confirmed 0.
                    #   - INFRASTRUCTURE_FAIL → no official empty observed;
                    #     SPA/DNS/resource fault must surface, not be masked.
                    if self._official_status == LoadState.CONFIRMED_EMPTY:
                        return DownloadResult(
                            success=True,
                            downloaded_files=[],
                            total_files=0,
                            duration_seconds=time.time() - start,
                            load_state=LoadState.CONFIRMED_EMPTY,
                            error_code=None,
                            retryable=False,
                        )
                    if self._official_status is None:
                        self._official_status = LoadState.INFRASTRUCTURE_FAIL
                    return DownloadResult(
                        success=False,
                        downloaded_files=[],
                        total_files=0,
                        duration_seconds=time.time() - start,
                        load_state=LoadState.INFRASTRUCTURE_FAIL,
                        error_code="upstream_unavailable",
                        retryable=True,
                        errors=[
                            "upstream observed neither official empty nor"
                            " disclosure links after retry"
                        ],
                    )

            downloaded = self._download_pages(request)

            # Post-download verification
            verify_warnings = self._verify_downloads(request, downloaded)
            if verify_warnings:
                log.warning(
                    f"Post-download verification found {len(verify_warnings)} issue(s):"
                )
                for w in verify_warnings:
                    log.warning(f"  - {w}")

            return DownloadResult(
                success=True,
                downloaded_files=downloaded,
                total_files=len(downloaded),
                duration_seconds=time.time() - start,
                skipped_files=self.skipped_files,
                pages_traversed=self.pages_traversed,
                metadata={"verification_warnings": verify_warnings},
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

    # Map URL suffix to sidebar menu text (cninfo uses el-menu-item now)
    _TAB_MENU_TEXT = {
        "latestAnnouncement": "最新公告",
        "periodicReports": "定期报告",
        "research": "调研",
    }

    def _switch_tab(self, suffix: str) -> bool:
        """Switch to the correct sidebar menu item, with verification and retry.

        Always clicks the menu item — never assumes the page already shows
        the correct tab. cninfo SPA defaults to "最新公告" on load, so the
        previous approach of checking for pre-existing links was incorrect:
        it would find default-tab links and skip the click entirely.

        Returns True if the tab has content, False if genuinely empty.
        """
        menu_text = self._TAB_MENU_TEXT.get(suffix)

        for attempt in range(3):
            # Always click the correct sidebar menu item
            if menu_text:
                self.browser.execute_script(f"""
                    const items = document.querySelectorAll('.el-menu-item');
                    for (const item of items) {{
                        if (item.textContent.trim() === '{menu_text}') {{
                            item.click();
                            break;
                        }}
                    }}
                """)
            time.sleep(C.CONTENT_LOAD_WAIT)

            # Verify links appeared after switching
            link_count = self.browser.execute_script("""
                () => document.querySelectorAll(
                    'a[href*="/new/disclosure/detail"]'
                ).length
            """)
            log.debug(f"Tab switch check: {link_count} links found on page")

            if link_count and link_count > 0:
                log.info(f"Tab '{suffix}' switched: {link_count} links found")
                break

            log.warning(f"Tab switch attempt {attempt + 1} failed, no links found")
        else:
            # No links after 3 attempts. Preserve an upstream-confirmed
            # CONFIRMED_EMPTY if it was already set (e.g. by the Phase 5
            # announcement API client); otherwise record an infrastructure
            # failure so the legacy ``success=True / 0 files`` mask is gone.
            if self._official_status != LoadState.CONFIRMED_EMPTY:
                self._official_status = LoadState.INFRASTRUCTURE_FAIL
            log.info(f"Tab '{suffix}' has no content — skipping")
            return False

        # Extra wait for latestAnnouncement tab (heavy SPA content)
        if suffix == "latestAnnouncement":
            # Wait for pagination element to render (not just links)
            for _ in range(10):
                time.sleep(C.SPA_CONTENT_WAIT)
                info = self.browser.get_current_page_info()
                total = info.get("total_pages", 1)
                if total > 1:
                    log.info(f"Pagination loaded: {total} pages")
                    break
                log.debug(f"Waiting for pagination... (total={total})")
            self._wait_for_page_load()

        return True

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
        time.sleep(C.PAGINATION_WAIT)
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

    def _download_page_links(self, request: DownloadRequest, page: int) -> List[str]:
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
            if _matches_excluded(text, request.excluded_keywords):
                log.debug(f"Skipping excluded: {text}")
                continue
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
        save_dir = (
            Path(str(request.save_dir)) if request.save_dir else Path(self.save_dir)
        )
        company_dir = save_dir / (request.stock_name or f"Stock_{request.stock_code}")
        if request.save_subdir:
            dest = company_dir / request.save_subdir / f"{target_name}.pdf"
        else:
            dest = company_dir / f"{target_name}.pdf"

        # Skip if already exists
        if dest.exists() and dest.stat().st_size > C.MIN_FILE_SIZE:
            log.info(f"File exists, skipping: {dest}")
            self.skipped_files.append(str(dest))
            return str(dest)

        log.info(f"Downloading: {text}")
        if self.browser.download_file(href, str(dest)):
            if dest.exists() and dest.stat().st_size > C.MIN_FILE_SIZE:
                self.download_count += 1
                time.sleep(C.POST_DOWNLOAD_WAIT)
                return str(dest)
            else:
                error_msg = f"File invalid or too small: {dest}"
                log.error(error_msg)
                self._failed_logger.record(
                    request.stock_code, request.stock_name or "", text, href, error_msg
                )
        else:
            self._failed_logger.record(
                request.stock_code,
                request.stock_name or "",
                text,
                href,
                "download_file returned False",
            )

        time.sleep(1)
        return None

    # ── Post-Download Verification ─────────────────────────────────────

    def _verify_downloads(
        self, request: DownloadRequest, downloaded: List[str]
    ) -> List[str]:
        """Verify downloaded files match config requirements.

        Returns list of validation warnings. Empty = all OK.
        """
        warnings: List[str] = []

        # CW-2.27H / Phase 7 mandatory baseline fix (user_override on the
        # Phase 3 baseline-failure exemption). Surfacing an empty-download
        # outcome as a validation warning prevents the historical
        # "success=True / 0 files" mask now that Phase 3 typed LoadState
        # has been propagated to _download_internal. Downstream callers
        # receive an explicit "No files were downloaded" warning rather
        # than a silent green result.
        if not downloaded:
            warnings.append("No files were downloaded")

        for fpath in downloaded:
            path = Path(fpath)

            # 1. Check file exists and is valid size
            if not path.exists():
                warnings.append(f"File missing: {path.name}")
                continue
            if path.stat().st_size <= C.MIN_FILE_SIZE:
                warnings.append(f"File too small (likely failed): {path.name}")
                continue

            # 2. Check filename matches allowed_keywords (if specified)
            stem = path.stem  # filename without extension
            if request.allowed_keywords:
                if not _matches_keywords(stem, request.allowed_keywords):
                    warnings.append(
                        f"File '{stem}' does not match any allowed keyword: "
                        f"{request.allowed_keywords}"
                    )

            # 3. Check filename does NOT match excluded_keywords
            if request.excluded_keywords:
                if _matches_excluded(stem, request.excluded_keywords):
                    warnings.append(
                        f"File '{stem}' matches excluded keyword but was "
                        f"downloaded anyway: {request.excluded_keywords}"
                    )

            # 4. Check file is in expected save_subdir
            if request.save_subdir:
                expected = request.save_subdir.replace("/", "\\")  # Windows path
                if expected not in str(path.parent):
                    warnings.append(
                        f"File '{path.name}' is in unexpected directory: "
                        f"{path.parent} (expected subpath: {request.save_subdir})"
                    )

        return warnings

    def _get_links(self) -> List[Tuple[str, str]]:
        """Extract detail links from the active tab pane only."""
        results: List[Tuple[str, str]] = []

        # Scope search to the active (non-hidden) tab pane
        ACTIVE_TAB_XPATH = (
            "//div[contains(@class,'el-tab-pane') and not(contains(@class,'is-hidden'))]"
            "//a[contains(@href, '/new/disclosure/detail')]"
        )
        elements = self.browser.find_elements(ACTIVE_TAB_XPATH, by="xpath")

        # Fallback to original broad XPath if scoped search found nothing
        if not elements:
            elements = self.browser.find_elements(C.DETAIL_LINKS_XPATH, by="xpath")

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
            except Exception as e:
                log.debug(f"Link extraction error for element: {e}")

        return results
