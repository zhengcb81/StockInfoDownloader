"""
浏览器服务模块
负责浏览器的初始化、配置和生命周期管理
"""

import random
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..core.config import ConfigManager
from ..core.logger import get_logger
from ..web.anti_crawler_py import AntiCrawlerStrategy
from ..web.browser_config import BrowserConfig


class BrowserService:
    """浏览器服务类，负责浏览器管理和操作"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化浏览器服务

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.browser_config = BrowserConfig(self.config_manager)
        self.anti_crawler = AntiCrawlerStrategy()
        self.driver = None
        self.download_count = 0

        # 初始化反爬虫策略
        self._init_anti_crawler()

        self.logger = get_logger(__name__)

    def _init_anti_crawler(self) -> None:
        """初始化反爬虫策略"""
        anti_crawler_config = self.config_manager.get("anti_crawler", {})
        self.anti_crawler.set_session_parameters(
            min_delay=anti_crawler_config.get("min_delay", 2.0),
            max_delay=anti_crawler_config.get("max_delay", 8.0),
            max_downloads=anti_crawler_config.get("max_downloads", 5),
        )

    def setup_driver(self, headless: Optional[bool] = None) -> webdriver.Chrome:
        """
        设置并初始化Chrome驱动

        Args:
            headless: 是否使用无头模式，None则使用配置文件设置

        Returns:
            webdriver.Chrome: Chrome驱动实例
        """
        if headless is None:
            headless = self.browser_config.is_headless()

        try:
            chrome_options = self._get_chrome_options(headless)

            # 创建驱动
            self.driver = webdriver.Chrome(options=chrome_options)

            # 设置超时
            timeouts = self.browser_config.get_all_timeouts()
            self.driver.set_page_load_timeout(timeouts["page_load"])

            # 设置窗口大小
            window_size = self.browser_config.get_window_size()
            width, height = map(int, window_size.split(","))
            self.driver.set_window_size(width, height)

            self.logger.info(
                f"浏览器初始化成功 - 无头模式: {headless}, 窗口大小: {window_size}"
            )
            return self.driver

        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {e}")
            raise

    def _get_chrome_options(self, headless: bool) -> Options:
        """
        获取Chrome选项配置

        Args:
            headless: 是否使用无头模式

        Returns:
            Options: Chrome选项配置
        """
        options = Options()

        # 基础配置
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        # 下载配置
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": self._get_download_directory(),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )

        # 无头模式配置
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-software-rasterizer")

        # 用户代理
        user_agent = self.browser_config.get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")

        # 页面加载策略
        page_load_strategy = self.browser_config.get_page_load_strategy()
        options.page_load_strategy = page_load_strategy

        return options

    def _get_download_directory(self) -> str:
        """获取下载目录"""
        import os

        download_dir = self.config_manager.get("save_dir", "downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        return os.path.abspath(download_dir)

    def simulate_human_behavior(self) -> None:
        """模拟人类行为"""
        try:
            if not self.driver:
                return

            # 随机滚动
            scroll_range = self.config_manager.get(
                "anti_crawler.scroll_range", [200, 600]
            )
            scroll_amount = random.randint(*scroll_range)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")

            # 随机延迟
            behavior_delay = self.config_manager.get(
                "anti_crawler.behavior_delay", [0.5, 1.5]
            )
            time.sleep(random.uniform(*behavior_delay))

            self.logger.debug("模拟人类行为完成")

        except Exception as e:
            self.logger.debug(f"模拟人类行为失败: {e}")

    def dynamic_delay(self) -> None:
        """动态延迟"""
        min_delay = self.config_manager.get("anti_crawler.min_delay", 2.0)
        max_delay = self.config_manager.get("anti_crawler.max_delay", 8.0)

        # 随着下载次数增加，延迟时间也会增加
        delay_factor = 1 + (self.download_count / 20)
        actual_min = min_delay * delay_factor
        actual_max = max_delay * delay_factor

        delay = random.uniform(actual_min, actual_max)
        self.logger.debug(f"动态延迟 {delay:.2f} 秒 (因子: {delay_factor:.2f})")
        time.sleep(delay)

    def wait_for_element(self, locator: tuple, timeout: Optional[int] = None) -> bool:
        """
        等待元素出现

        Args:
            locator: 元素定位器 (By.XPATH, xpath)
            timeout: 超时时间

        Returns:
            bool: 是否找到元素
        """
        if timeout is None:
            timeout = self.browser_config.get_timeout("element_wait")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except TimeoutException:
            self.logger.warning(f"等待元素超时: {locator}")
            return False

    def restart_driver(self, headless: Optional[bool] = None) -> None:
        """
        重启浏览器驱动

        Args:
            headless: 是否使用无头模式
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"关闭浏览器失败: {e}")

        # 重置下载计数
        self.download_count = 0

        # 重新初始化
        self.setup_driver(headless)
        self.logger.info("浏览器驱动重启完成")

    def close(self) -> None:
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.info("浏览器已关闭")
            except Exception as e:
                self.logger.error(f"关闭浏览器失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
