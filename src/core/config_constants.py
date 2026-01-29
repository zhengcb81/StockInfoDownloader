"""
配置常量模块
提供所有硬编码值的常量定义，实现配置驱动
"""

import json
from pathlib import Path
from typing import Dict


class ConfigConstants:
    """配置常量类，集中管理所有硬编码值"""

    # URL常量
    BASE_URL = "https://www.cninfo.com.cn"
    DETAIL_URL_PATTERN = "/new/disclosure/detail"
    STOCK_PAGE_URL_TEMPLATE = "https://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}"

    # 超时时间常量（秒）
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

    # 浏览器配置常量
    DEFAULT_BROWSER_CONFIG = {
        "headless": True,
        "window_size": "1920,1080",
        "page_load_strategy": "eager",
    }

    BROWSER_LAUNCH_ARGS = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-blink-features=AutomationControlled",
        "--remote-debugging-port=0",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-sync",
        "--disable-translate",
        "--disable-default-apps",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--log-level=3",
        "--disable-features=TranslateUI",
        "--disable-component-extensions-with-background-pages",
        "--disable-domain-reliability",
        "--disable-setuid-sandbox",
        "--disable-features=VizDisplayCompositor",
        "--disable-ipc-flooding-protection",
    ]

    ANTI_DETECTION_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']})
    """

    BLANK_PAGE_URL = "about:blank"

    # 文件配置常量
    FILE_CONFIG = {
        "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
        "mapping_file": "stock_orgid_mapping.json",
        "log_dir": "logs",
        "download_dir": "downloads",
    }

    # 选择器常量
    SELECTORS = {
        "detail_links": "//a[contains(@href, '/new/disclosure/detail')]",
        "download_button": "//button[contains(., '公告下载')]",
        "next_page_button": "//button[contains(@class, 'el-pagination__next')]",
        "table_element": "//table[contains(@class, 'el-table__body')]",
    }

    # 下载配置常量
    DOWNLOAD_CONFIG = {
        "max_downloads_per_session": 5,
        "pagination_wait": 2,
        "human_behavior_delay": 3,
    }

    # 测试数据常量
    TEST_DATA = {
        "stocks": [
            {"code": "300470", "name": "中密控股", "org_id": "9900023856"},
            {"code": "301611", "name": "珂玛科技", "org_id": "9900047115"},
        ],
        "test_keywords": ["投资者关系", "2023年", "活动记录表", "招股说明书"],
    }

    # 页面类型常量
    PAGE_TYPES = {
        "research": {"name": "调研", "suffix": "research"},
        "periodicReports": {"name": "定期公告", "suffix": "periodicReports"},
        "latestAnnouncement": {"name": "最新公告", "suffix": "latestAnnouncement"},
    }

    # 目录路径常量
    PATHS = {
        "configs": "configs",
        "logs": "logs",
        "downloads": "downloads",
        "tests": "tests",
        "tools": "tools",
        "docs": "docs",
    }

    # 用户代理常量
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # 文件名非法字符
    INVALID_FILENAME_CHARS = r'[\\/:*?"<>|]'

    # 日志配置
    LOGGING_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "encoding": "utf-8",
    }

    # 反爬虫配置
    ANTI_CRAWLER_CONFIG = {
        "min_delay": 2.0,
        "max_delay": 8.0,
        "max_downloads": 5,
        "scroll_range": (200, 600),
        "behavior_delay": (0.5, 1.5),
        "max_retries": 3,
    }

    @classmethod
    def get_base_url(cls) -> str:
        """获取基础URL"""
        return cls.BASE_URL

    @classmethod
    def get_timeout(cls, timeout_type: str) -> int:
        """获取指定类型的超时时间"""
        return cls.DEFAULT_TIMEOUTS.get(timeout_type, 30)

    @classmethod
    def get_selector(cls, selector_name: str) -> str:
        """获取指定选择器"""
        return cls.SELECTORS.get(selector_name, "")

    @classmethod
    def get_test_stock(cls, stock_code: str) -> Dict[str, str]:
        """获取测试股票信息"""
        for stock in cls.TEST_DATA["stocks"]:
            if stock["code"] == stock_code:
                return stock
        return {}

    @classmethod
    def get_page_type_config(cls, page_type: str) -> Dict[str, str]:
        """获取页面类型配置"""
        return cls.PAGE_TYPES.get(page_type, {})

    @classmethod
    def get_path(cls, path_name: str) -> str:
        """获取指定路径"""
        return cls.PATHS.get(path_name, "")

    @classmethod
    def load_external_config(cls):
        """从外部JSON文件加载配置"""
        try:
            # 计算项目根目录: src/core/config_constants.py -> ../../..
            project_root = Path(__file__).resolve().parent.parent.parent
            config_path = project_root / "configs" / "business_rules.json"
            
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if "urls" in data:
                        urls = data["urls"]
                        if "base_url" in urls:
                            cls.BASE_URL = urls["base_url"]
                        if "detail_url_pattern" in urls:
                            cls.DETAIL_URL_PATTERN = urls["detail_url_pattern"]
                        if "stock_page_url_template" in urls:
                            cls.STOCK_PAGE_URL_TEMPLATE = urls["stock_page_url_template"]
                            
                    if "selectors" in data:
                        cls.SELECTORS.update(data["selectors"])
                        
                    if "anti_crawler" in data:
                        cls.ANTI_CRAWLER_CONFIG.update(data["anti_crawler"])

                    if "timeouts" in data:
                        cls.DEFAULT_TIMEOUTS.update(data["timeouts"])
                        
        except Exception as e:
            print(f"Warning: Failed to load external business rules: {e}")


# Load external config on module import
ConfigConstants.load_external_config()
