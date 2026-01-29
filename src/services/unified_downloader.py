#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器实现 - 生产级稳定版
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.abstracts.base_downloader import BaseDownloader
from src.core.config_constants import ConfigConstants
from src.core.debug_tracker import (
    DebugMarker,
    DebugStep,
    get_debug_marker_manager,
)
from src.core.logger import get_logger
from src.interfaces.downloader_interface import (
    DownloadRequest,
    DownloadResult,
    DownloadStatus,
    IBrowserStrategy,
    IDownloader,
)

logger = get_logger(__name__)


# ==================== 核心组件 ====================


class UnifiedDownloader(BaseDownloader, IDownloader):
    browser_strategy: Optional[IBrowserStrategy]

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
        self.max_retries = int(self.config.get("retry_count", ConfigConstants.ANTI_CRAWLER_CONFIG["max_retries"]))
        self.max_downloads_per_session = ConfigConstants.DOWNLOAD_CONFIG["max_downloads_per_session"]

        self.logger.info(
            f"Unified Downloader initialized, core driver: {self.config.get('browser_strategy')}"
        )
        self.history: List[Dict[str, Any]] = []

    def get_download_history(self) -> List[Dict[str, Any]]:
        """Get download history"""
        return self.history

    def _init_services(self):
        from src.services.file_service import FileService
        from src.services.validation_service import ValidationService

        self.file_service = FileService(self.config)
        self.validation_service = ValidationService(self.config)

    def _init_browser_strategy(self, force: bool = False):
        if self.config.get("skip_browser_init", False) and not force:
            self.logger.info("跳过浏览器策略初始化")
            return

        from src.web.browser_strategy import BrowserStrategyFactory

        strategy_type = self.config.get("browser_strategy") or self.config.get(
            "browser", {}
        ).get("strategy", "playwright")
        download_dir = self.config.get("save_dir", "downloads")
        headless = self.config.get("headless", True)
        if isinstance(self.config.get("browser"), dict):
            headless = self.config.get("browser").get("headless", headless)

        self.browser_strategy = BrowserStrategyFactory.create_strategy(
            strategy_type=strategy_type,
            headless=headless,
            download_dir=download_dir,
            config=self.config,
        )
        self.browser_strategy.initialize()

    def _log_debug_marker(
        self,
        step: DebugStep,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        self.marker_manager.add_marker(step, success, details, error)

    def _debug_step(self, step: DebugStep, func, *args, **kwargs):
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

    def download_stock_pdfs(  # type: ignore[override]
        self,
        request: Union[DownloadRequest, str],
        stock_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[DownloadResult, List[str]]:
        if isinstance(request, str):
            # Legacy call format
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
            res = self._download_with_retry(request)
            return res.downloaded_files

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
                except:
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

        try:
            # 1. Mapping injection
            from src.data.mapping import MappingManager

            mm = MappingManager()
            if not request.org_id:
                request.org_id = mm.get_org_id(request.stock_code)
                if not request.org_id:
                    raise Exception(f"OrgID NotFound: {request.stock_code}")
                self._log_debug_marker(
                    DebugStep.ORG_ID_MAPPING, True, {"org_id": request.org_id}
                )

            if not request.stock_name:
                request.stock_name = (
                    mm.get_stock_name(request.stock_code)
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
            )
        except Exception as e:
            self.logger.error(f"Pipeline crashed: {e}")
            return DownloadResult(False, [], 0, [str(e)], time.time() - start_time, {})

    def download_activity_records(self, **kwargs) -> List[str]:
        """Best compatibility entry point"""
        stock_code = kwargs.get("stock_code")
        request = DownloadRequest(
            stock_code=stock_code,
            stock_name=kwargs.get("stock_name"),
            suffix=kwargs.get("suffix", "research"),
            allowed_keywords=kwargs.get("allowed_keywords"),
            max_pages=kwargs.get("max_pages", 5),
            save_dir=kwargs.get("save_dir", self.config.get("save_dir", "downloads")),
        )
        res = self._download_internal(request)
        return res.downloaded_files

    def _perform_download(self, request: DownloadRequest) -> List[str]:
        if not self.browser_strategy:
            raise RuntimeError("Browser strategy not initialized")

        # URL 路由
        url = ConfigConstants.STOCK_PAGE_URL_TEMPLATE.format(
            stock_code=request.stock_code, org_id=request.org_id
        )
        if request.suffix:
            url += f"#{request.suffix}"

        DebugMarker(DebugStep.URL_GENERATION, True, {"url": url}).log()
        self.logger.info(f"Navigating to stock page: {url}")
        if not self.browser_strategy.navigate(url):
            raise Exception("Failed to navigate to list page")

        # Wait for page load (especially AJAX data)
        # We wait for the table or list container to appear
        max_attempts = ConfigConstants.get_timeout("page_load_max_attempts")
        check_interval = ConfigConstants.get_timeout("page_load_check_interval")

        for _ in range(max_attempts):
            time.sleep(check_interval)
            links = self._get_links_safe()
            if len(links) > 0:
                break
            self.logger.debug("Waiting for data links to load...")

        # Handle SPA tab switching
        if request.suffix:
            time.sleep(ConfigConstants.get_timeout("spa_tab_switch_wait"))
            # Safely inject script
            tab_script = (
                f"document.querySelector('a[href*=\"{request.suffix}\"]')?.click()"
            )
            self.browser_strategy.execute_script(tab_script)
            # Wait for tab content
            time.sleep(ConfigConstants.get_timeout("content_load_wait"))

        all_downloaded = []
        for page in range(1, request.max_pages + 1):
            self.logger.info(f"Processing page {page}...")

            # Batch fetch to avoid stale references
            links = self._get_links_safe()
            DebugMarker(
                DebugStep.PDF_VISIBILITY, True, {"page": page, "count": len(links)}
            ).log()

            if len(links) == 0:
                self.logger.warning(
                    f"No links found on page {page}, saving debug screenshot..."
                )
                self.browser_strategy.take_screenshot(
                    f"logs/debug_page_{request.stock_code}_p{page}.png"
                )

            for text, href in links:
                if self._matches(text, request.allowed_keywords):
                    target_name = self.file_service.clean_filename(text)
                    save_dir = (
                        Path(str(request.save_dir))
                        if request.save_dir
                        else Path("downloads")
                    )
                    dest = (
                        save_dir
                        / (request.stock_name or f"Stock_{request.stock_code}")
                        / f"{target_name}.pdf"
                    )

                    if dest.exists() and dest.stat().st_size > 100:
                        self.logger.debug(f"File already exists: {dest}")
                        all_downloaded.append(str(dest))
                        continue

                    self.logger.info(f"Downloading: {text}")
                    if self.browser_strategy.download_file(href, str(dest)):
                        if dest.exists() and dest.stat().st_size > 100:
                            all_downloaded.append(str(dest))
                            self.history.append(
                                {
                                    "stock_code": request.stock_code,
                                    "stock_name": request.stock_name,
                                    "file_name": text,
                                    "file_path": str(dest),
                                    "timestamp": datetime.now().isoformat(),
                                    "status": "success",
                                }
                            )
                            DebugMarker(
                                DebugStep.DOWNLOAD_SUCCESS, True, {"file": text}
                            ).log()
                        else:
                            self.logger.error(
                                f"Download reported success but file missing or invalid: {dest}"
                            )
                        time.sleep(1)

            if not self.browser_strategy.go_to_next_page():
                break
            time.sleep(ConfigConstants.get_timeout("pagination_wait"))

        return all_downloaded

    def _get_links_safe(self) -> List[tuple]:
        """Fetch link data using the most robust selector"""
        if not self.browser_strategy:
            return []

        results = []
        base = ConfigConstants.BASE_URL

        # Try using configured XPath selector (more precise)
        from src.core.constants import SelectorConfig

        elements = self.browser_strategy.find_elements(
            SelectorConfig.DETAIL_LINKS, by="xpath"
        )

        # Fallback to basic a tags if XPath finds nothing
        if not elements:
            elements = self.browser_strategy.find_elements("a")

        for el in elements:
            try:
                h = self.browser_strategy.get_attribute(el, "href")
                if h and "/detail" in h:
                    t = self.browser_strategy.get_text(el).strip()
                    if t:
                        abs_url = h if h.startswith("http") else base + h
                        results.append((t, abs_url))
            except:
                continue
        return results

    def _matches(self, text: str, keywords: Optional[List[str]]) -> bool:
        if not keywords:
            return True
        ct = "".join(text.split()).lower()
        for k in keywords:
            ck = "".join(k.split()).lower()
            # 1. Try partial match
            if ck in ct:
                return True

            # 2. Try date match (for truncated titles)
            # Extract 8-digit date like 20250725
            import re

            date_match = re.search(r"\d{8}", k)
            if date_match:
                date_str = date_match.group()
                if date_str in ct:
                    return True
        return False

    def cleanup(self):
        if hasattr(self, "browser_strategy"):
            self.browser_strategy.close()

    @property
    def user_agents(self) -> List[str]:
        """Get user agents from config or constants."""
        from src.core.constants import USER_AGENTS

        return self.config.get("user_agents", USER_AGENTS)

    def configure(self, config: Dict):
        self.config.update(config)

    def get_supported_browsers(self):
        return ["playwright"]
