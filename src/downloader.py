"""Core downloader — handles the full download workflow.

This is the heart of the project. ~350 lines doing what the old project needed
29,000 lines for.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any, Dict, List, Optional, Tuple

from . import constants as C
from .browser import PlaywrightBrowser
from .exceptions import BrowserError, DownloadError, OrgIdError
from .logger import log
from .mapping import MappingManager
from .models import (
    DownloadRequest,
    DownloadResult,
    VerificationIssue,
    VerificationResult,
)
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


def _subdir_components(save_subdir: str) -> Tuple[str, ...]:
    """Split a declared relative sub-directory into path components.

    Both POSIX ``/`` and Windows ``\\`` separators are accepted so a config
    written on either platform keeps working.  Parent references and absolute
    paths are rejected: the downloader may only ever write *below* the company
    directory, and silently normalising ``..`` away would hide a configuration
    error.
    """
    if not isinstance(save_subdir, str) or not save_subdir.strip():
        raise ValueError("save_subdir must be non-empty text")
    raw = save_subdir.strip()
    if raw.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw):
        raise ValueError(f"save_subdir must be relative: {save_subdir!r}")
    parts = tuple(part for part in re.split(r"[\\/]+", raw) if part not in ("", "."))
    if not parts:
        raise ValueError(f"save_subdir has no usable component: {save_subdir!r}")
    if any(part == ".." for part in parts):
        raise ValueError(f"save_subdir must not contain '..': {save_subdir!r}")
    return parts


def _path_is_within_subdir(
    path: Any,
    save_subdir: str,
    *,
    case_sensitive: Optional[bool] = None,
) -> bool:
    """True when ``path``'s parent chain ends with ``save_subdir``.

    Matching is by whole components, never by substring: ``raw/prospectus``
    and ``raw/prospectus-extra`` are different scopes.  ``path`` may be a
    ``PurePosixPath``/``PureWindowsPath`` so both platform semantics stay
    testable on one machine; the default case sensitivity follows the path
    flavour (Windows is case-insensitive, POSIX is not).
    """
    candidate = path if isinstance(path, PurePath) else Path(path)
    expected = _subdir_components(save_subdir)
    actual = tuple(str(part) for part in candidate.parent.parts)
    if len(actual) < len(expected):
        return False
    tail = actual[-len(expected) :]
    if case_sensitive is None:
        case_sensitive = not isinstance(candidate, PureWindowsPath)
    if case_sensitive:
        return tail == expected
    return tuple(part.casefold() for part in tail) == tuple(
        part.casefold() for part in expected
    )


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
        # Failures observed while serving the *current* request.  The owner
        # must not report success while it already knows a candidate failed.
        self._request_failures: List[Tuple[str, str]] = []

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
        self._request_failures = []

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
            # A typed non-retryable outcome (for example a verification
            # failure) must not re-download the whole company three times.
            if last_result.retryable is False:
                break
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
        """Core download logic.

        The typed load state is derived per request.  ``request.confirmed_empty``
        is the only way an upstream announcement API can pre-confirm zero
        documents for *this* company and period; nothing is cached on the
        instance, so the next request always re-observes.
        """
        start = time.time()
        downloaded: List[str] = []
        upstream_confirmed_empty = bool(request.confirmed_empty)

        try:
            self._navigate_to_stock_page(request)
            self._wait_for_page_load()

            if request.suffix:
                has_content = self._switch_tab(request.suffix)
                if not has_content:
                    # The historical code folded this into success/0 files.
                    # Now the typed state decides:
                    #   - CONFIRMED_EMPTY → the announcement API explicitly
                    #     confirmed zero documents for this request.
                    #   - INFRASTRUCTURE_FAIL → no official empty was observed;
                    #     SPA/DNS/resource fault must surface, not be masked.
                    if upstream_confirmed_empty:
                        return DownloadResult(
                            success=True,
                            downloaded_files=[],
                            total_files=0,
                            duration_seconds=time.time() - start,
                            load_state=LoadState.CONFIRMED_EMPTY,
                            error_code=None,
                            retryable=False,
                        )
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

            # Post-download verification.  The owner decides the outcome here;
            # callers read ``success`` and never re-judge diagnostics.
            verification = self._verify_downloads(
                request, downloaded, self._request_failures
            )
            if not verification.ok:
                log.warning(
                    f"Post-download verification found {len(verification.issues)}"
                    " blocking issue(s):"
                )
                for issue in verification.issues:
                    log.warning(f"  - [{issue.code}] {issue.message}")

            return DownloadResult(
                success=verification.ok,
                downloaded_files=downloaded,
                total_files=len(downloaded),
                duration_seconds=time.time() - start,
                skipped_files=self.skipped_files,
                pages_traversed=self.pages_traversed,
                verification=verification,
                error_code=None if verification.ok else "verification_failed",
                retryable=False if not verification.ok else None,
                errors=[] if verification.ok else ["verification_failed"],
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

    def _wait_for_page_load(self, *, tab_scoped: bool = False) -> None:
        """Poll until data links appear on the page (or in the active pane)."""
        for _ in range(C.PAGE_LOAD_MAX_ATTEMPTS):
            time.sleep(C.PAGE_LOAD_CHECK_INTERVAL)
            links = self._get_links(tab_scoped=tab_scoped)
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
        """Switch to the requested sidebar menu item and prove the scope.

        The requested tab must be *reachable and selected* before any link is
        read.  Two failure modes are refused instead of being papered over:

        * an unknown suffix has no menu mapping, so the caller's intended scope
          cannot be proven at all — that is a configuration error;
        * a mapped suffix whose menu item is missing means the page markup
          drifted; reading whichever tab is active would download another
          type/period.

        Verification uses the active pane's links and, when the page exposes a
        selection marker, the selected menu item's label.  A page-level link
        count would report the default tab's documents.

        Returns True if the selected tab has content, False if it is empty or
        unreachable.
        """
        menu_text = self._TAB_MENU_TEXT.get(suffix)
        if menu_text is None:
            raise DownloadError(
                f"unsupported tab suffix {suffix!r}; known tabs: "
                f"{', '.join(sorted(self._TAB_MENU_TEXT))}"
            )

        for attempt in range(3):
            if not self.browser.click_menu_item(menu_text):
                log.warning(
                    f"Tab switch attempt {attempt + 1}: menu item"
                    f" {menu_text!r} not found on this page"
                )
                time.sleep(C.CONTENT_LOAD_WAIT)
                continue

            time.sleep(C.CONTENT_LOAD_WAIT)

            label = self.browser.active_tab_label()
            if label is not None and label != menu_text:
                log.warning(
                    f"Tab switch attempt {attempt + 1}: selected tab is"
                    f" {label!r}, expected {menu_text!r}"
                )
                continue

            link_count = len(self.browser.find_active_tab_links())
            log.debug(f"Tab switch check: {link_count} links in the active pane")
            if link_count > 0:
                log.info(f"Tab '{suffix}' switched: {link_count} links found")
                break

            log.warning(f"Tab switch attempt {attempt + 1} failed, no links found")
        else:
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
            self._wait_for_page_load(tab_scoped=True)

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
        self._wait_for_page_load(tab_scoped=bool(request.suffix))

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
                self._wait_for_page_load(tab_scoped=bool(request.suffix))

        return all_downloaded

    # ── Link Processing ───────────────────────────────────────────────

    def _download_page_links(self, request: DownloadRequest, page: int) -> List[str]:
        """Match and download links on the current page."""
        links = self._get_links(tab_scoped=bool(request.suffix))
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
            # Build the destination from validated components so a
            # platform-specific separator never becomes part of a filename.
            dest = company_dir.joinpath(
                *_subdir_components(request.save_subdir), f"{target_name}.pdf"
            )
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
                self._request_failures.append((text, error_msg))
                self._failed_logger.record(
                    request.stock_code, request.stock_name or "", text, href, error_msg
                )
        else:
            self._request_failures.append((text, "download_file returned False"))
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
        self,
        request: DownloadRequest,
        downloaded: List[str],
        failures: Optional[List[Tuple[str, str]]] = None,
    ) -> VerificationResult:
        """Verify downloaded files match the request's declared scope.

        Returns a machine-readable outcome.  ``ok=False`` means the caller must
        not report success: a missing/too-small file, a keyword that does not
        match, an excluded keyword that was downloaded anyway, a file outside
        the declared sub-directory, or simply zero files.
        """
        issues: List[VerificationIssue] = []

        # A candidate the owner already failed to fetch is not a success, even
        # when the other candidates downloaded fine.  Without this the result
        # could be green while logs/failed_downloads.json recorded a real gap.
        for title, reason in failures or ():
            issues.append(
                VerificationIssue(
                    "download_failed", f"Candidate failed: {title} ({reason})"
                )
            )

        # An empty result is only positive when the announcement API confirmed
        # it (that path returns before verification).  Anything else is a
        # silent-green risk the historical code used to hide.
        if not downloaded:
            issues.append(VerificationIssue("no_files", "No files were downloaded"))

        for fpath in downloaded:
            path = Path(fpath)

            # 1. Check file exists and is valid size
            if not path.exists():
                issues.append(
                    VerificationIssue("file_missing", f"File missing: {path.name}")
                )
                continue
            if path.stat().st_size <= C.MIN_FILE_SIZE:
                issues.append(
                    VerificationIssue(
                        "file_too_small",
                        f"File too small (likely failed): {path.name}",
                    )
                )
                continue

            # 2. Check filename matches allowed_keywords (if specified)
            stem = path.stem  # filename without extension
            if request.allowed_keywords and not _matches_keywords(
                stem, request.allowed_keywords
            ):
                issues.append(
                    VerificationIssue(
                        "keyword_mismatch",
                        f"File '{stem}' does not match any allowed keyword: "
                        f"{request.allowed_keywords}",
                    )
                )

            # 3. Check filename does NOT match excluded_keywords
            if request.excluded_keywords and _matches_excluded(
                stem, request.excluded_keywords
            ):
                issues.append(
                    VerificationIssue(
                        "excluded_keyword_present",
                        f"File '{stem}' matches excluded keyword but was "
                        f"downloaded anyway: {request.excluded_keywords}",
                    )
                )

            # 4. Check the file sits inside the declared relative sub-directory
            if request.save_subdir and not _path_is_within_subdir(
                path, request.save_subdir
            ):
                issues.append(
                    VerificationIssue(
                        "unexpected_directory",
                        f"File '{path.name}' is in unexpected directory: "
                        f"{path.parent} (expected subpath: {request.save_subdir})",
                    )
                )

        return VerificationResult(ok=not issues, issues=tuple(issues))

    def _get_links(self, *, tab_scoped: bool = False) -> List[Tuple[str, str]]:
        """Extract detail links, optionally scoped to the active tab pane.

        When a tab is selected the extraction stays inside that pane.  Falling
        back to the whole page would silently download another type/period
        from a tab the caller never asked for.
        """
        results: List[Tuple[str, str]] = []

        if tab_scoped:
            pairs = self.browser.find_active_tab_links()
        else:
            elements = self.browser.find_elements(C.DETAIL_LINKS_XPATH, by="xpath")
            # Fallback to all <a> tags (unscoped navigation only)
            if not elements:
                elements = self.browser.find_elements("a")
            pairs = []
            for el in elements:
                try:
                    pairs.append(
                        (
                            self.browser.get_attribute(el, "href") or "",
                            self.browser.get_text(el).strip(),
                        )
                    )
                except Exception as e:
                    log.debug(f"Link extraction error for element: {e}")

        for href, text in pairs:
            if "/detail" not in href or not text:
                continue
            abs_url = href if href.startswith("http") else C.BASE_URL + href
            results.append((text, abs_url))

        return results
