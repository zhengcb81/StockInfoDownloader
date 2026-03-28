#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Downloader Implementation - Production Stable Version
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from selenium.common.exceptions import WebDriverException

from src.abstracts.base_downloader import BaseDownloader
from src.core.config_constants import ConfigConstants
from src.core.debug_tracker import (
    DebugMarker,
    DebugStep,
    get_debug_marker_manager,
)
from src.core.exceptions import OrgIdError
from src.core.logger import get_logger
from src.interfaces.downloader_interface import (
    DownloadRequest,
    DownloadResult,
    DownloadStatus,
    IBrowserStrategy,
    IDownloader,
)
from src.web.browser_strategy import BrowserStrategy
from src.services.download_helpers import (
    DownloadHistoryTracker,
    KeywordMatcher,
    LinkExtractor,
    PaginationHandler,
)

logger = get_logger(__name__)


# ==================== 核心组件 ====================


class UnifiedDownloader(BaseDownloader, IDownloader):
    browser_strategy: Optional[BrowserStrategy]

    def __init__(
        self,
        strategy: Union[str, Dict[str, Any]] = "playwright",
        config: Optional[Dict[str, Any]] = None,
    ):
        if isinstance(strategy, dict) and config is None:
            config = strategy
            strategy = config.get("browser_strategy") or config.get("browser", {}).get(
                "strategy", "playwright"
            )

        self.config = config or {}
        # 默认使用 Playwright 以确保 E2E 100% 成功率，但允许通过配置覆盖
        if "browser_strategy" not in self.config:
            self.config["browser_strategy"] = (
                strategy if isinstance(strategy, str) else "playwright"
            )

        self.logger = logger
        self._init_services()
        # Initialize browser_strategy to None first
        self.browser_strategy = None
        self._init_browser_strategy()
        self.marker_manager = get_debug_marker_manager()

        # 兼容性字段
        self.download_count = 0
        self.retry_count = 0
        # 行为验证字段 (E2E 测试用)
        self.skipped_files: List[str] = []  # 跳过的已存在文件
        self.pages_traversed: int = 0  # 实际遍历的页数
        self.max_retries = int(
            self.config.get(
                "retry_count", ConfigConstants.ANTI_CRAWLER_CONFIG["max_retries"]
            )
        )
        self.max_downloads_per_session = ConfigConstants.DOWNLOAD_CONFIG[
            "max_downloads_per_session"
        ]

        self.logger.info(
            f"Unified Downloader initialized, core driver: {self.config.get('browser_strategy')}"
        )
        # Initialize helper classes
        self.history_tracker = DownloadHistoryTracker()
        self.keyword_matcher = KeywordMatcher()
        # LinkExtractor and PaginationHandler are initialized with browser_strategy
        self._link_extractor: Optional[LinkExtractor] = None
        self._pagination_handler: Optional[PaginationHandler] = None

    def get_download_history(self) -> List[Dict[str, Any]]:
        """Get download history"""
        return self.history_tracker.get_history()

    @property
    def link_extractor(self) -> Optional[LinkExtractor]:
        """Get link extractor (lazily initialized with browser_strategy)."""
        if self._link_extractor is None and self.browser_strategy:
            self._link_extractor = LinkExtractor(self.browser_strategy)
        return self._link_extractor

    @property
    def pagination_handler(self) -> Optional[PaginationHandler]:
        """Get pagination handler (lazily initialized with browser_strategy)."""
        if self._pagination_handler is None and self.browser_strategy:
            self._pagination_handler = PaginationHandler(self.browser_strategy)
        return self._pagination_handler

    def _init_services(self) -> None:
        from src.services.file_service import FileService
        from src.services.validation_service import ValidationService

        self.file_service = FileService(None)
        self.validation_service = ValidationService(None)

    def _init_browser_strategy(self, force: bool = False) -> None:
        if self.config.get("skip_browser_init", False) and not force:
            self.logger.info("跳过浏览器策略初始化")
            return

        from src.web.browser_strategy import BrowserStrategyFactory

        strategy_type = self.config.get("browser_strategy") or self.config.get(
            "browser", {}
        ).get("strategy", "playwright")
        download_dir = self.config.get("save_dir", "downloads")
        headless = self.config.get("headless", True)
        browser_config = self.config.get("browser")
        if isinstance(browser_config, dict):
            headless = browser_config.get("headless", headless)

        self.browser_strategy = BrowserStrategyFactory.create_strategy(
            strategy_type=strategy_type,
            headless=headless,
            download_dir=download_dir,
            config=self.config,
        )
        if self.browser_strategy:
            self.browser_strategy.initialize()

    def _log_debug_marker(
        self,
        step: DebugStep,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.marker_manager.add_marker(step, success, details, error)

    def _debug_step(self, step: DebugStep, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
            self._log_debug_marker(
                step, True, {"args": str(args), "kwargs": str(kwargs)}
            )
            return result
        except Exception as e:
            self._log_debug_marker(
                step, False, {"args": str(args), "kwargs": str(kwargs)}, str(e)
            )
            raise

    def get_debug_markers(self) -> List[Dict]:
        return self.marker_manager.get_markers_for_e2e_test()

    def get_debug_summary(self) -> Dict:
        return self.marker_manager.get_summary()

    def get_status(self) -> DownloadStatus:
        # Mock status for compatibility
        return DownloadStatus(
            is_running=False,
            current_page=0,
            total_pages=0,
            downloaded_count=0,
            error_count=0,
            last_error=None,
        )

    def download_stock_pdfs(
        self,
        request: Union[DownloadRequest, str],
        stock_name: Optional[str] = None,
        **kwargs: Any,
    ) -> DownloadResult:
        if isinstance(request, str):
            # Legacy call format - convert str to DownloadRequest
            stock_code = request
            request = DownloadRequest(
                stock_code=stock_code,
                stock_name=stock_name,
                suffix=kwargs.get("suffix", "research"),
                allowed_keywords=kwargs.get("allowed_keywords"),
                max_pages=kwargs.get("max_pages", 5),
                save_dir=kwargs.get(
                    "save_dir", self.config.get("save_dir", "downloads")
                ),
            )

        return self._download_with_retry(request)

    def _download_with_retry(self, request: DownloadRequest) -> DownloadResult:
        max_retries = int(self.config.get("retry_count", 3))
        last_res = DownloadResult(False, [], 0, [], 0.0, {})

        if not self.browser_strategy:
            return DownloadResult(
                False, [], 0, ["Browser strategy not initialized"], 0.0, {}
            )

        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.info(f"Retrying download (attempt {attempt})...")
                try:
                    self.browser_strategy.restart()
                except (WebDriverException, RuntimeError, AttributeError):
                    # Browser restart failed, will try again
                    pass

            last_res = self._download_internal(request)
            if last_res.success:
                return last_res

            self.logger.warning(
                f"Download attempt {attempt + 1} failed: {last_res.errors}"
            )
            if attempt < max_retries:
                time.sleep(1)

        return last_res

    def _download_internal(self, request: DownloadRequest) -> DownloadResult:
        self.logger.info(f"Starting download pipeline for: {request.stock_code}")
        start_time = time.time()
        # 重置行为验证字段
        self.skipped_files = []
        self.pages_traversed = 0

        try:
            # 1. Mapping injection
            from src.data.mapping import MappingManager

            # 是否强制从网络获取（用于测试实时爬取能力）
            force_crawl = self.config.get("force_crawl_mapping", False)

            mm = MappingManager()
            if not request.org_id:
                request.org_id = mm.get_org_id(
                    request.stock_code, force_refresh=force_crawl
                )
                if not request.org_id:
                    raise OrgIdError(f"OrgID NotFound: {request.stock_code}")
                self._log_debug_marker(
                    DebugStep.ORG_ID_MAPPING, True, {"org_id": request.org_id}
                )

            if not request.stock_name:
                request.stock_name = (
                    mm.get_stock_name(request.stock_code, auto_crawl=force_crawl)
                    or f"Stock_{request.stock_code}"
                )

            # 2. Core pipeline
            downloaded = self._perform_download(request)

            return DownloadResult(
                success=True,
                downloaded_files=downloaded,
                total_files=len(downloaded),
                errors=[],
                duration_seconds=time.time() - start_time,
                metadata={},
                skipped_files=self.skipped_files,
                pages_traversed=self.pages_traversed,
            )
        except Exception as e:
            self.logger.error(f"Pipeline crashed: {e}")
            return DownloadResult(False, [], 0, [str(e)], time.time() - start_time, {})

    def download_activity_records(self, **kwargs: Any) -> List[str]:
        """Best compatibility entry point"""
        stock_code = kwargs.get("stock_code")
        request = DownloadRequest(
            stock_code=stock_code or "",
            stock_name=kwargs.get("stock_name"),
            suffix=kwargs.get("suffix", "research"),
            allowed_keywords=kwargs.get("allowed_keywords"),
            max_pages=kwargs.get("max_pages", 5),
            save_dir=kwargs.get("save_dir", self.config.get("save_dir", "downloads")),
        )
        res = self._download_internal(request)
        return res.downloaded_files

    def _perform_download(self, request: DownloadRequest) -> List[str]:  # type: ignore[override]
        if not self.browser_strategy:
            raise RuntimeError("Browser strategy not initialized")

        self._navigate_to_stock_page(request)
        self._wait_for_page_load()

        if request.suffix:
            self._handle_spa_tab_switch(request.suffix)

        all_downloaded: List[str] = []

        # 支持从最后一页开始（用于 latestAnnouncement 等经常更新的页面）
        if request.reverse_order:
            # 获取总页数
            page_info = self.browser_strategy.get_current_page_info()
            total_pages = page_info.get("total_pages", 1)
            self.logger.info(f"Reverse order: total_pages={total_pages}")

            # 跳转到最后一页（点击最后一页按钮）
            self.browser_strategy.execute_script("""
                (() => {
                    const pages = document.querySelectorAll('.el-pager li.number');
                    if (pages.length > 0) {
                        pages[pages.length - 1].click();
                    }
                })()
            """)
            time.sleep(3)
            self._wait_for_page_load()

            # 获取当前页码
            current_info = self.browser_strategy.get_current_page_info()
            current_page = current_info.get("current_page", total_pages)
            self.logger.info(f"Jumped to last page: {current_page}")

            # 从最后一页开始往前遍历
            pages_to_check = min(request.max_pages, current_page)
            for i in range(pages_to_check):
                page = current_page - i
                self.logger.info(f"Processing page {page}/{total_pages}...")
                self.pages_traversed = i + 1
                downloaded = self._download_page_links(request, page)
                all_downloaded.extend(downloaded)

                # 如果找到目标文件，可以提前结束
                if len(downloaded) > 0 and request.allowed_keywords:
                    self.logger.info(f"Found target files on page {page}, stopping")
                    break

                # 往前翻一页
                if i < pages_to_check - 1 and page > 1:
                    # 点击上一页按钮
                    self.browser_strategy.execute_script("""
                        (() => {
                            const prev = document.querySelector('.btn-prev');
                            if (prev && !prev.disabled) prev.click();
                        })()
                    """)
                    assert self.pagination_handler is not None
                    self.pagination_handler.wait_after_page_change()  # type: ignore[union-attr]
                    self._wait_for_page_load()
        else:
            # 正常顺序：从第1页开始
            for page in range(1, request.max_pages + 1):
                self.logger.info(f"Processing page {page}...")
                self.pages_traversed = page
                downloaded = self._download_page_links(request, page)
                all_downloaded.extend(downloaded)

                if not self.pagination_handler.go_to_next_page():  # type: ignore[union-attr]
                    break
                self.pagination_handler.wait_after_page_change()  # type: ignore[union-attr]

        return all_downloaded

    def _navigate_to_stock_page(self, request: DownloadRequest) -> None:
        """Navigate to the stock page URL."""
        url = ConfigConstants.STOCK_PAGE_URL_TEMPLATE.format(
            stock_code=request.stock_code, org_id=request.org_id
        )
        if request.suffix:
            url += f"#{request.suffix}"

        DebugMarker(DebugStep.URL_GENERATION, True, {"url": url}).log()
        self.logger.info(f"Navigating to stock page: {url}")
        if not self.browser_strategy.navigate(url):  # type: ignore[union-attr]
            raise Exception("Failed to navigate to list page")

    def _wait_for_page_load(self) -> None:
        """Wait for page data links to appear via polling."""
        max_attempts = ConfigConstants.get_timeout("page_load_max_attempts")
        check_interval = ConfigConstants.get_timeout("page_load_check_interval")

        for _ in range(max_attempts):
            time.sleep(check_interval)
            links = self._get_links_safe()
            if len(links) > 0:
                break
            self.logger.debug("Waiting for data links to load...")

    def _handle_spa_tab_switch(self, suffix: str) -> None:
        """Handle SPA tab switching for suffix-based navigation."""
        time.sleep(ConfigConstants.get_timeout("spa_tab_switch_wait"))
        tab_script = f"document.querySelector('a[href*=\"{suffix}\"]')?.click()"
        self.browser_strategy.execute_script(tab_script)  # type: ignore[union-attr]
        time.sleep(ConfigConstants.get_timeout("content_load_wait"))

    def _download_page_links(self, request: DownloadRequest, page: int) -> List[str]:
        """Match and download links on the current page."""
        links = self._get_links_safe()
        DebugMarker(
            DebugStep.PDF_VISIBILITY, True, {"page": page, "count": len(links)}
        ).log()

        if len(links) == 0:
            self.logger.warning(
                f"No links found on page {page}, saving debug screenshot..."
            )
            self.browser_strategy.take_screenshot(  # type: ignore[union-attr]
                f"logs/debug_page_{request.stock_code}_p{page}.png"
            )

        downloaded: List[str] = []
        for text, href in links:
            if self._matches(text, request.allowed_keywords):
                result = self._download_single_link(request, text, href)
                if result:
                    downloaded.append(result)
        return downloaded

    def _download_single_link(
        self, request: DownloadRequest, text: str, href: str
    ) -> Optional[str]:
        """Download a single matched link and return the file path on success."""
        target_name = self.file_service.clean_filename(text)
        save_dir = (
            Path(str(request.save_dir)) if request.save_dir else Path("downloads")
        )
        dest = (
            save_dir
            / (request.stock_name or f"Stock_{request.stock_code}")
            / f"{target_name}.pdf"
        )

        if dest.exists() and dest.stat().st_size > 100:
            self.logger.info(f"File already exists, skipping: {dest}")
            self.skipped_files.append(str(dest))
            return str(dest)

        self.logger.info(f"Downloading: {text}")
        if self.browser_strategy.download_file(href, str(dest)):  # type: ignore[union-attr]
            if dest.exists() and dest.stat().st_size > 100:
                self.history_tracker.add_record(
                    stock_code=request.stock_code,
                    stock_name=request.stock_name,
                    file_name=text,
                    file_path=str(dest),
                    status="success",
                )
                DebugMarker(DebugStep.DOWNLOAD_SUCCESS, True, {"file": text}).log()
                time.sleep(1)
                return str(dest)
            else:
                self.logger.error(
                    f"Download reported success but file missing or invalid: {dest}"
                )
            time.sleep(1)
        return None

    def _get_links_safe(self) -> List[tuple]:
        """Fetch link data using the most robust selector"""
        if not self.link_extractor:
            return []
        return self.link_extractor.get_links_safe()

    def _matches(self, text: str, keywords: Optional[List[str]]) -> bool:
        """Check if text matches any of the given keywords."""
        return self.keyword_matcher.matches(text, keywords)

    def cleanup(self) -> None:
        if hasattr(self, "browser_strategy") and self.browser_strategy:
            self.browser_strategy.close()

    @property
    def user_agents(self) -> List[str]:
        """Get user agents from config or constants."""
        from src.core.constants import USER_AGENTS

        return self.config.get("user_agents", USER_AGENTS)  # type: ignore[no-any-return]

    def configure(self, config: Dict[str, Any]) -> None:
        self.config.update(config)

    def get_supported_browsers(self) -> List[str]:
        return ["playwright"]
