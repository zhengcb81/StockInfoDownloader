#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""系统常量配置

提供统一的常量管理，消除硬编码，提高配置的可维护性和可扩展性
"""


# =============================================================================
# 超时时间配置（秒）
# =============================================================================
class TimeoutConfig:
    """超时时间配置"""

    PAGE_LOAD = 30  # 页面加载超时
    ELEMENT_WAIT = 10  # 元素等待超时
    DOWNLOAD = 300  # 下载超时（5分钟）
    SCRIPT = 30  # 脚本执行超时
    VALIDATION = 10  # 验证超时
    NAVIGATION = 10  # 导航超时
    BUTTON_CLICK = 5  # 按钮点击超时
    INITIALIZATION = 180  # 浏览器初始化超时
    RETRY_DELAY = 2  # 重试延迟时间（秒）
    BROWSER_CLOSE = 0.5  # 浏览器关闭等待时间（秒）
    PAGE_STABILITY = 1.0  # 页面稳定等待时间（秒）
    DOM_READY = 2.0  # DOM就绪等待时间（秒）
    SHORT_WAIT = 0.5  # 短等待时间（秒）
    MEDIUM_WAIT = 1.0  # 中等等待时间（秒）
    LONG_WAIT = 3.0  # 长等待时间（秒）
    SCROLL_DELAY = 0.5  # 滚动后等待时间（秒）
    CLICK_STABILIZATION = 2.0  # 点击后页面稳定时间（秒）
    SELECTOR_RETRY = 0.2  # 选择器重试间隔（秒）


# =============================================================================
# 文件大小阈值（字节）
# =============================================================================
class FileSizeThreshold:
    """文件大小阈值配置"""

    MIN_VALID_PDF = 10 * 1024  # 最小有效PDF文件大小：10KB
    DOWNLOAD_CHECK_INTERVAL = 0.5  # 下载检查间隔（秒）
    DOWNLOAD_STABILITY_WAIT = 1  # 文件稳定性等待时间（秒）
    TEMP_FILE_MIN_SIZE = 10 * 1024  # 临时文件最小大小：10KB


# =============================================================================
# 重试配置
# =============================================================================
class RetryConfig:
    """重试策略配置"""

    MAX_RETRIES = 3  # 最大重试次数
    BASE_DELAY = 1.0  # 基础延迟时间（秒）
    BACKOFF_FACTOR = 2.0  # 指数退避因子
    MAX_DELAY = 30  # 最大延迟时间（秒）


# =============================================================================
# 浏览器配置
# =============================================================================
class BrowserConfig:
    """浏览器相关配置"""

    DEFAULT_WINDOW_SIZE = "1920,1080"  # 字符串格式
    DEFAULT_WINDOW_SIZE_DICT = {"width": 1920, "height": 1080}  # 字典格式
    MAX_DOWNLOADS_PER_SESSION = 10  # 每个会话最大下载数
    IMPLICIT_WAIT = 3  # 隐式等待时间（秒）
    PAGE_LOAD_TIMEOUT = 30  # 页面加载超时（秒）


# =============================================================================
# 反爬虫配置
# =============================================================================
class AntiCrawlerConfig:
    """反爬虫策略配置"""

    MIN_DELAY = 2.0  # 最小延迟（秒）
    MAX_DELAY = 8.0  # 最大延迟（秒）
    MAX_DOWNLOADS = 5  # 最大下载次数
    SCROLL_RANGE = [200, 600]  # 滚动范围（像素）
    BEHAVIOR_DELAY = [0.5, 1.5]  # 行为延迟范围（秒）


# =============================================================================
# 分页配置
# =============================================================================
class PaginationConfig:
    """分页操作配置"""

    MAX_PAGES = 3  # 最大页数
    PAGINATION_WAIT = 2  # 分页等待时间（秒）
    HUMAN_BEHAVIOR_DELAY = 3  # 模拟人类行为延迟（秒）
    DOM_STABILITY_WAIT = 1  # DOM稳定等待时间（秒）
    CLICK_DELAY = 0.5  # 点击后等待时间（秒）
    SELECTOR_RETRY_DELAY = 0.2  # 选择器重试延迟（秒）


# =============================================================================
# 文件配置
# =============================================================================
class FileConfig:
    """文件相关配置"""

    MIN_FILE_SIZE = 10 * 1024  # 最小文件大小：10KB
    TEMP_EXTENSIONS = [".tmp", ".crdownload", ".partial", ".download"]  # 临时文件扩展名
    PDF_EXTENSION = ".pdf"  # PDF文件扩展名
    MAX_FILE_AGE = 300  # 最大文件年龄（秒）
    DOWNLOAD_CHECK_INTERVAL = 0.5  # 下载检查间隔（秒）
    DOWNLOAD_STABILITY_WAIT = 1  # 文件稳定性等待时间（秒）


# =============================================================================
# 选择器配置（CSS/XPath）
# =============================================================================
class SelectorConfig:
    """浏览器元素选择器配置"""

    # 详情页链接
    DETAIL_LINKS = "//a[contains(@href, '/new/disclosure/detail')]"

    # 下载按钮
    DOWNLOAD_BUTTON = "//button[contains(., '公告下载')]"

    # 下一页按钮
    NEXT_PAGE_BUTTON = "//button[contains(@class, 'el-pagination__next')]"

    # 表格元素
    TABLE_ELEMENT = "//table[contains(@class, 'el-table__body')]"

    # 备选下载按钮选择器（按优先级排序）
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

    # 下一页选择器（按优先级排序）
    NEXT_PAGE_SELECTORS = [
        ".el-pager li.number.active + li.number",  # Element UI 主要选择器
        "button.el-pagination__next:not(.is-disabled)",  # Element UI 下一页按钮
        ".el-pager li.active + li.number",  # Element UI 备用选择器
        ".el-pager li.number.active + li",  # Element UI 另一种模式
        "button.el-pagination__next:not([disabled])",  # 通用下一页按钮
        ".pagination .next:not(.disabled)",  # 通用分页样式
        "a[aria-label='下一页']:not(.disabled)",  # ARIA标签
        "button[aria-label='Next page']:not([disabled])",  # 英文标签
    ]

    # 页码输入和跳转
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

    # 页码按钮
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
# Chrome启动参数
# =============================================================================
CHROME_LAUNCH_ARGS = [
    # 沙箱和共享内存
    "--no-sandbox",
    "--disable-dev-shm-usage",
    # 硬件加速
    "--disable-gpu",
    # 扩展和自动化检测
    "--disable-extensions",
    "--disable-blink-features=AutomationControlled",
    # 调试和端口
    "--remote-debugging-port=0",
    # 首次运行检查
    "--no-first-run",
    "--no-default-browser-check",
    # 性能优化
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    # 功能禁用
    "--disable-sync",
    "--disable-translate",
    "--disable-default-apps",
    "--disable-notifications",
    "--disable-popup-blocking",
    # 日志级别
    "--log-level=3",
    # 特性开关
    "--disable-features=TranslateUI",
    "--disable-component-extensions-with-background-pages",
    "--disable-domain-reliability",
    "--disable-setuid-sandbox",
    "--disable-features=VizDisplayCompositor",
    "--disable-ipc-flooding-protection",
]


# =============================================================================
# Playwright特定配置
# =============================================================================
class PlaywrightConfig:
    """Playwright浏览器配置"""

    # 上下文选项
    CONTEXT_OPTIONS = {
        "viewport": {"width": 1920, "height": 1080},
        "java_script_enabled": True,
        "ignore_https_errors": False,
        "accept_downloads": True,
    }

    # 反检测脚本
    ANTI_DETECTION_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
    """

    # 等待状态
    WAIT_STATE = "domcontentloaded"

    # 下载事件超时（毫秒）
    DOWNLOAD_TIMEOUT = 30000


# =============================================================================
# Selenium特定配置
# =============================================================================
class SeleniumConfig:
    """Selenium浏览器配置"""

    # 反检测脚本
    ANTI_DETECTION_SCRIPT = (
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    # 实验选项
    EXPERIMENTAL_OPTIONS = {
        "excludeSwitches": ["enable-automation"],
        "useAutomationExtension": False,
    }

    # 下载偏好设置
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
# 环境配置
# =============================================================================
class EnvironmentConfig:
    """环境相关配置"""

    # 测试环境检测
    TEST_ENVIRONMENT_INDICATORS = ["TEST_ENV", "PYTEST_CURRENT_TEST", "pytest", "test"]

    # 日志级别
    LOG_LEVEL_DEBUG = "DEBUG"
    LOG_LEVEL_INFO = "INFO"
    LOG_LEVEL_WARNING = "WARNING"
    LOG_LEVEL_ERROR = "ERROR"
    LOG_LEVEL_CRITICAL = "CRITICAL"


# =============================================================================
# 错误配置
# =============================================================================
class ErrorConfig:
    """错误处理配置"""

    # 错误历史最大记录数
    MAX_ERROR_HISTORY = 1000

    # 错误恢复策略
    RECOVERY_STRATEGIES = {
        "NONE": "无恢复",
        "RETRY": "重试",
        "FALLBACK": "降级",
        "SKIP": "跳过",
        "TERMINATE": "终止",
        "MANUAL": "手动处理",
    }

    # 严重级别
    SEVERITY_LEVELS = {
        "DEBUG": "调试",
        "INFO": "信息",
        "WARNING": "警告",
        "ERROR": "错误",
        "CRITICAL": "严重",
        "FATAL": "致命",
    }


# =============================================================================
# 性能监控配置
# =============================================================================
class PerformanceConfig:
    """性能监控配置"""

    # 基准测试超时
    BENCHMARK_TIMEOUT = 60

    # 性能阈值
    THRESHOLDS = {
        "initialization_time": 2.0,  # 秒
        "config_loading_time": 0.5,  # 秒
        "constant_access_time": 0.1,  # 1000次访问秒
        "method_execution_time": 5.0,  # 秒
    }

    # 监控间隔
    MONITOR_INTERVAL = 10  # 秒


# =============================================================================
# 配置验证规则
# =============================================================================
class ValidationRules:
    """配置验证规则"""

    # 超时验证
    TIMEOUT_MIN = 1
    TIMEOUT_MAX = 3600

    # 文件大小验证
    FILE_SIZE_MIN = 1024  # 1KB
    FILE_SIZE_MAX = 1024 * 1024 * 1024  # 1GB

    # 重试次数验证
    RETRY_MIN = 0
    RETRY_MAX = 10

    # 窗口大小验证
    WINDOW_WIDTH_MIN = 800
    WINDOW_HEIGHT_MIN = 600
    WINDOW_WIDTH_MAX = 7680
    WINDOW_HEIGHT_MAX = 4320

    # 字符串长度验证
    MAX_STRING_LENGTH = 1000
    MAX_PATH_LENGTH = 4096


# =============================================================================
# 全局常量
# =============================================================================
class GlobalConstants:
    """全局常量配置"""

    # 项目名称
    PROJECT_NAME = "StockInfoDownloader"

    # 版本信息
    VERSION = "2.0.0"

    # 编码
    ENCODING = "utf-8"

    # 文件路径
    DEFAULT_CONFIG_PATH = "config.json"
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_DOWNLOAD_DIR = "downloads"

    # 时间格式
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    FILENAME_DATETIME_FORMAT = "%Y%m%d_%H%M%S"

    # 最大值
    MAX_CONCURRENT_DOWNLOADS = 5
    MAX_RETRIES_PER_DOWNLOAD = 3

    # 验证阈值
    VALIDATION_RETRY_COUNT = 3
    VALIDATION_RETRY_DELAY = 2  # 秒


# =============================================================================
# 业务相关常量
# =============================================================================
class BusinessConfig:
    """业务相关配置"""

    # 巨潮资讯网相关
    CNINFO_BASE_URL = "http://www.cninfo.com.cn"
    CNINFO_NEW_DISCLOSURE = "/new/disclosure"
    CNINFO_DETAIL_PATH = "/new/disclosure/detail"

    # 文件命名模式
    FILENAME_PATTERN = "{stock_code}_{company_name}_{date}_{doc_type}.pdf"

    # 支持的文档类型
    SUPPORTED_DOC_TYPES = ["公告", "报告", "摘要"]

    # 默认查询参数
    DEFAULT_SEARCH_PARAMS = {"pageNum": 1, "pageSize": 30, "category": "announcement"}
