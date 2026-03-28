#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""System Constants Configuration

Provides unified constant management, eliminates hardcoding, improves maintainability and extensibility
"""


# =============================================================================
# Timeout Configuration (seconds)
# =============================================================================
class TimeoutConfig:
    """Timeout configuration"""

    PAGE_LOAD = 30  # Page load timeout
    ELEMENT_WAIT = 10  # Element wait timeout
    DOWNLOAD = 300  # Download timeout (5 minutes)
    SCRIPT = 30  # Script execution timeout
    VALIDATION = 10  # Validation timeout
    NAVIGATION = 10  # Navigation timeout
    BUTTON_CLICK = 5  # Button click timeout
    INITIALIZATION = 180  # Browser initialization timeout
    RETRY_DELAY = 2  # Retry delay (seconds)
    BROWSER_CLOSE = 0.5  # Browser close wait time (seconds)
    PAGE_STABILITY = 1.0  # Page stability wait time (seconds)
    DOM_READY = 2.0  # DOM ready wait time (seconds)
    SHORT_WAIT = 0.5  # Short wait time (seconds)
    MEDIUM_WAIT = 1.0  # Medium wait time (seconds)
    LONG_WAIT = 3.0  # Long wait time (seconds)
    SCROLL_DELAY = 0.5  # Post-scroll wait time (seconds)
    CLICK_STABILIZATION = 2.0  # Post-click page stability time (seconds)
    SELECTOR_RETRY = 0.2  # Selector retry interval (seconds)


# =============================================================================
# File Size Thresholds (bytes)
# =============================================================================
class FileSizeThreshold:
    """File size threshold configuration"""

    MIN_VALID_PDF = 10 * 1024  # Minimum valid PDF file size: 10KB
    DOWNLOAD_CHECK_INTERVAL = 0.5  # Download check interval (seconds)
    DOWNLOAD_STABILITY_WAIT = 1  # File stability wait time (seconds)
    TEMP_FILE_MIN_SIZE = 10 * 1024  # Temp file minimum size: 10KB


# =============================================================================
# Retry Configuration
# =============================================================================
class RetryConfig:
    """Retry strategy configuration"""

    MAX_RETRIES = 3  # Maximum retry attempts
    BASE_DELAY = 1.0  # Base delay time (seconds)
    BACKOFF_FACTOR = 2.0  # Exponential backoff factor
    MAX_DELAY = 30  # Maximum delay time (seconds)


# =============================================================================
# Browser Configuration
# =============================================================================
class BrowserConfig:
    """Browser-related configuration"""

    DEFAULT_WINDOW_SIZE = "1920,1080"  # String format
    DEFAULT_WINDOW_SIZE_DICT = {"width": 1920, "height": 1080}  # Dict format
    MAX_DOWNLOADS_PER_SESSION = 10  # Maximum downloads per session
    IMPLICIT_WAIT = 3  # Implicit wait time (seconds)
    PAGE_LOAD_TIMEOUT = 30  # Page load timeout (seconds)


# =============================================================================
# Anti-Crawler Configuration
# =============================================================================
class AntiCrawlerConfig:
    """Anti-crawler strategy configuration"""

    MIN_DELAY = 2.0  # Minimum delay (seconds)
    MAX_DELAY = 8.0  # Maximum delay (seconds)
    MAX_DOWNLOADS = 5  # Maximum download count
    SCROLL_RANGE = [200, 600]  # Scroll range (pixels)
    BEHAVIOR_DELAY = [0.5, 1.5]  # Behavior delay range (seconds)


# =============================================================================
# Pagination Configuration
# =============================================================================
class PaginationConfig:
    """Pagination operation configuration"""

    MAX_PAGES = 3  # Maximum page count
    PAGINATION_WAIT = 2  # Pagination wait time (seconds)
    HUMAN_BEHAVIOR_DELAY = 3  # Simulated human behavior delay (seconds)
    DOM_STABILITY_WAIT = 1  # DOM stability wait time (seconds)
    CLICK_DELAY = 0.5  # Post-click wait time (seconds)
    SELECTOR_RETRY_DELAY = 0.2  # Selector retry delay (seconds)


# =============================================================================
# File Configuration
# =============================================================================
class FileConfig:
    """File-related configuration"""

    MIN_FILE_SIZE = 10 * 1024  # Minimum file size: 10KB
    TEMP_EXTENSIONS = [".tmp", ".crdownload", ".partial", ".download"]  # Temp file extensions
    PDF_EXTENSION = ".pdf"  # PDF file extension
    MAX_FILE_AGE = 300  # Maximum file age (seconds)
    DOWNLOAD_CHECK_INTERVAL = 0.5  # Download check interval (seconds)
    DOWNLOAD_STABILITY_WAIT = 1  # File stability wait time (seconds)


# =============================================================================
# Selector Configuration (CSS/XPath)
# =============================================================================
class SelectorConfig:
    """Browser element selector configuration"""

    # Detail page links
    DETAIL_LINKS = "//a[contains(@href, '/new/disclosure/detail')]"

    # Download button
    DOWNLOAD_BUTTON = "//button[contains(., '公告下载')]"

    # Next page button
    NEXT_PAGE_BUTTON = "//button[contains(@class, 'el-pagination__next')]"

    # Table element
    TABLE_ELEMENT = "//table[contains(@class, 'el-table__body')]"

    # Alternative download button selectors (sorted by priority)
    DOWNLOAD_BUTTON_ALTERNATIVES = [
        "//button[contains(., '公告下载')]",
        "//button[contains(., '下载')]",
        "//a[contains(., '公告下载')]",
        "//a[contains(., '下载')]",
        "//span[contains(., '公告下载')]/..",  # Element UI button with span
        "//span[contains(., '下载')]/..",
        "//button[contains(., 'PDF')]",
        "//a[contains(., 'PDF')]",
        "button i.el-icon-download",  # Element UI download icon
        ".download-btn",
        ".pdf-download",
        "button.download",
        "a.download",
    ]

    # Next page selectors (sorted by priority)
    NEXT_PAGE_SELECTORS = [
        ".el-pager li.number.active + li.number",  # Element UI primary selector
        "button.el-pagination__next:not(.is-disabled)",  # Element UI next page button
        ".el-pager li.active + li.number",  # Element UI alternative selector
        ".el-pager li.number.active + li",  # Element UI another pattern
        "button.el-pagination__next:not([disabled])",  # Generic next page button
        ".pagination .next:not(.disabled)",  # Generic pagination style
        "a[aria-label='下一页']:not(.disabled)",  # ARIA label
        "button[aria-label='Next page']:not([disabled])",  # English label
    ]

    # Page input and jump
    PAGE_INPUT_SELECTORS = [
        "input.el-pagination__editor",
        "input.page-input",
        "input[type='number']",
        "input.pagination-input",
    ]

    GO_BUTTON_SELECTORS = [
        "button.el-pagination__jump",
        "button.page-go",
        "button:contains('跳转')",
        "button:contains('Go')",
    ]

    # Page number buttons
    PAGE_BUTTON_SELECTORS = [
        ".el-pager li.number:not(.active)",
        ".pagination li:not(.active)",
        "a:not(.active)",
        "button:not([disabled])",
    ]


# =============================================================================
# 用户代理列表
# =============================================================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


# =============================================================================
# Chrome Launch Arguments
# =============================================================================
CHROME_LAUNCH_ARGS = [
    # Sandbox and shared memory
    "--no-sandbox",
    "--disable-dev-shm-usage",
    # Hardware acceleration
    "--disable-gpu",
    # Extensions and automation detection
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
    # Debug and port
    "--remote-debugging-port=0",
    # First run check
    "--no-first-run",
    "--no-default-browser-check",
    # Performance optimization
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    # Feature disable
    "--disable-sync",
    "--disable-translate",
    "--disable-default-apps",
    "--disable-notifications",
    "--disable-popup-blocking",
    # Log level
    "--log-level=3",
    # Feature switches
    "--disable-features=TranslateUI",
    "--disable-component-extensions-with-background-pages",
    "--disable-domain-reliability",
    "--disable-setuid-sandbox",
    "--disable-features=VizDisplayCompositor",
    "--disable-ipc-flooding-protection",
]


# =============================================================================
# Playwright-Specific Configuration
# =============================================================================
class PlaywrightConfig:
    """Playwright browser configuration"""

    # Context options
    CONTEXT_OPTIONS = {
        "viewport": {"width": 1920, "height": 1080},
        "java_script_enabled": True,
        "ignore_https_errors": False,
        "accept_downloads": True,
    }

    # Anti-detection script
    ANTI_DETECTION_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
    """

    # Wait state
    WAIT_STATE = "domcontentloaded"

    # Download event timeout (milliseconds)
    DOWNLOAD_TIMEOUT = 30000


# =============================================================================
# Selenium-Specific Configuration
# =============================================================================
class SeleniumConfig:
    """Selenium browser configuration"""

    # Anti-detection script
    ANTI_DETECTION_SCRIPT = (
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    # Experimental options
    EXPERIMENTAL_OPTIONS = {
        "excludeSwitches": ["enable-automation"],
        "useAutomationExtension": False,
    }

    # Download preferences
    DOWNLOAD_PREFERENCES = {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        "download_restrictions": 0,
        "credentials_enable_service": False,
        "password_manager_enabled": False,
    }


# =============================================================================
# Environment Configuration
# =============================================================================
class EnvironmentConfig:
    """Environment-related configuration"""

    # Test environment detection
    TEST_ENVIRONMENT_INDICATORS = ["TEST_ENV", "PYTEST_CURRENT_TEST", "pytest", "test"]

    # Log levels
    LOG_LEVEL_DEBUG = "DEBUG"
    LOG_LEVEL_INFO = "INFO"
    LOG_LEVEL_WARNING = "WARNING"
    LOG_LEVEL_ERROR = "ERROR"
    LOG_LEVEL_CRITICAL = "CRITICAL"


# =============================================================================
# Error Configuration
# =============================================================================
class ErrorConfig:
    """Error handling configuration"""

    # Maximum error history records
    MAX_ERROR_HISTORY = 1000

    # Error recovery strategies
    RECOVERY_STRATEGIES = {
        "NONE": "No recovery",
        "RETRY": "Retry",
        "FALLBACK": "Degrade",
        "SKIP": "Skip",
        "TERMINATE": "Terminate",
        "MANUAL": "Manual handling",
    }

    # Severity levels
    SEVERITY_LEVELS = {
        "DEBUG": "Debug",
        "INFO": "Info",
        "WARNING": "Warning",
        "ERROR": "Error",
        "CRITICAL": "Critical",
        "FATAL": "Fatal",
    }


# =============================================================================
# Performance Monitoring Configuration
# =============================================================================
class PerformanceConfig:
    """Performance monitoring configuration"""

    # Benchmark timeout
    BENCHMARK_TIMEOUT = 60

    # Performance thresholds
    THRESHOLDS = {
        "initialization_time": 2.0,  # seconds
        "config_loading_time": 0.5,  # seconds
        "constant_access_time": 0.1,  # 1000 access seconds
        "method_execution_time": 5.0,  # seconds
    }

    # Monitor interval
    MONITOR_INTERVAL = 10  # seconds


# =============================================================================
# Configuration Validation Rules
# =============================================================================
class ValidationRules:
    """Configuration validation rules"""

    # Timeout validation
    TIMEOUT_MIN = 1
    TIMEOUT_MAX = 3600

    # File size validation
    FILE_SIZE_MIN = 1024  # 1KB
    FILE_SIZE_MAX = 1024 * 1024 * 1024  # 1GB

    # Retry count validation
    RETRY_MIN = 0
    RETRY_MAX = 10

    # Window size validation
    WINDOW_WIDTH_MIN = 800
    WINDOW_HEIGHT_MIN = 600
    WINDOW_WIDTH_MAX = 7680
    WINDOW_HEIGHT_MAX = 4320

    # String length validation
    MAX_STRING_LENGTH = 1000
    MAX_PATH_LENGTH = 4096


# =============================================================================
# Global Constants
# =============================================================================
class GlobalConstants:
    """Global constants configuration"""

    # Project name
    PROJECT_NAME = "StockInfoDownloader"

    # Version information
    VERSION = "2.0.0"

    # Encoding
    ENCODING = "utf-8"

    # File paths
    DEFAULT_CONFIG_PATH = "config.json"
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_DOWNLOAD_DIR = "downloads"

    # Date time format
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    FILENAME_DATETIME_FORMAT = "%Y%m%d_%H%M%S"

    # Maximum values
    MAX_CONCURRENT_DOWNLOADS = 5
    MAX_RETRIES_PER_DOWNLOAD = 3

    # Validation thresholds
    VALIDATION_RETRY_COUNT = 3
    VALIDATION_RETRY_DELAY = 2  # seconds


# =============================================================================
# Business-Related Constants
# =============================================================================
class BusinessConfig:
    """Business-related configuration"""

    # CNINFO (cninfo.com.cn) related
    CNINFO_BASE_URL = "http://www.cninfo.com.cn"
    CNINFO_NEW_DISCLOSURE = "/new/disclosure"
    CNINFO_DETAIL_PATH = "/new/disclosure/detail"

    # File naming pattern
    FILENAME_PATTERN = "{stock_code}_{company_name}_{date}_{doc_type}.pdf"

    # Supported document types
    SUPPORTED_DOC_TYPES = ["公告", "报告", "摘要"]

    # Default query parameters
    DEFAULT_SEARCH_PARAMS = {"pageNum": 1, "pageSize": 30, "category": "announcement"}
