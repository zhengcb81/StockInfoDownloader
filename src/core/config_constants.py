"""
Configuration Constants Module
Provides constant definitions for all hardcoded values, enables configuration-driven approach.
Shared constants (USER_AGENTS, CHROME_LAUNCH_ARGS) are imported from constants.py to avoid duplication.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from .constants import CHROME_LAUNCH_ARGS, USER_AGENTS as _SHARED_USER_AGENTS

logger = logging.getLogger(__name__)


class ConfigConstants:
    """Configuration constants class, centralized management of all hardcoded values"""

    # URL constants
    BASE_URL = "https://www.cninfo.com.cn"
    DETAIL_URL_PATTERN = "/new/disclosure/detail"
    STOCK_PAGE_URL_TEMPLATE = "https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}"

    # Timeout constants (seconds)
    DEFAULT_TIMEOUTS = {
        "page_load": 30,
        "element_wait": 10,
        "download": 60,
        "script": 30,
        "validation": 10,
        "page_load_check_interval": 2,
        "page_load_max_attempts": 5,
        "spa_tab_switch_wait": 2,
        "content_load_wait": 3,
        "pagination_wait": 3,
        "process_cleanup": 5,
        "temp_file_stabilize_timeout": 60,
        "temp_file_check_interval": 2,
    }

    # Browser configuration constants
    DEFAULT_BROWSER_CONFIG = {
        "headless": True,
        "window_size": "1920,1080",
        "page_load_strategy": "eager",
    }

    # Browser launch args - imported from constants.py to avoid duplication
    BROWSER_LAUNCH_ARGS = CHROME_LAUNCH_ARGS

    ANTI_DETECTION_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']})
    """

    BLANK_PAGE_URL = "about:blank"

    # File configuration constants
    FILE_CONFIG = {
        "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
        "mapping_file": "stock_orgid_mapping.json",
        "log_dir": "logs",
        "download_dir": "downloads",
    }
    # Selector constants
    SELECTORS = {
        "detail_links": "//a[contains(@href, '/new/disclosure/detail')]",
        "download_button": "//button[contains(., '公告下载')]",
        "next_page_button": "//button[contains(@class, 'el-pagination__next')]",
        "table_element": "//table[contains(@class, 'el-table__body')]",
    }
    # Download configuration constants
    DOWNLOAD_CONFIG = {
        "max_downloads_per_session": 5,
        "pagination_wait": 2,
        "human_behavior_delay": 3,
    }
    # Test data constants
    TEST_DATA = {
        "stocks": [
            {"code": "300470", "name": "中密控股", "org_id": "9900023856"},
            {"code": "301611", "name": "珂玛科技", "org_id": "9900047115"},
        ],
        "test_keywords": ["投资者关系", "2023年", "活动记录表", "招股说明书"],
    }
    # Page type constants
    PAGE_TYPES = {
        "research": {"name": "调研", "suffix": "research"},
        "periodicReports": {"name": "定期公告", "suffix": "periodicReports"},
        "latestAnnouncement": {"name": "最新公告", "suffix": "latestAnnouncement"},
    }
    # Directory path constants
    PATHS = {
        "configs": "configs",
        "logs": "logs",
        "downloads": "downloads",
        "tests": "tests",
        "tools": "tools",
        "docs": "docs",
    }
    # User agent constants - imported from constants.py to avoid duplication
    USER_AGENTS = _SHARED_USER_AGENTS
    # Invalid filename characters
    INVALID_FILENAME_CHARS = r'[\\/:*?"<>|]'
    # Logging configuration
    LOGGING_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "encoding": "utf-8",
    }
    # Anti-crawler configuration
    ANTI_CRAWLER_CONFIG = {
        "min_delay": 2.0,
        "max_delay": 8.0,
        "max_downloads": 5,
        "scroll_range": (200, 600),
        "behavior_delay": (0.5, 1.5),
        "max_retries": 3,
    }

    # Lazy loading guard
    _external_config_loaded: bool = False

    @classmethod
    def external_config_loaded(cls) -> bool:
        """Whether external config has been loaded"""
        return cls._external_config_loaded

    @classmethod
    def load_external_config(cls) -> None:
        """Load external configuration from file (placeholder)."""
        # TODO: Implement external config loading if needed
        pass

    @classmethod
    def ensure_loaded(cls) -> None:
        """Load external config on first access if not already loaded."""
        if not cls._external_config_loaded:
            cls.load_external_config()
            cls._external_config_loaded = True

    @classmethod
    def get_base_url(cls) -> str:
        """Get base URL"""
        return cls.BASE_URL

    @classmethod
    def get_timeout(cls, timeout_type: str) -> int:
        """Get timeout for specified type"""
        return cls.DEFAULT_TIMEOUTS.get(timeout_type, 30)
