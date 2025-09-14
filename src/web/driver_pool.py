"""
WebDriver连接池模块
提供高效的WebDriver实例管理和复用，减少初始化开销
"""

import threading
import time
import queue
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.core.logger import get_logger
from src.core.config import ConfigManager


class WebDriverPool:
    """WebDriver连接池"""

    def __init__(self, pool_size: int = 3, max_session_downloads: int = 20):
        """
        初始化WebDriver连接池

        Args:
            pool_size: 连接池大小
            max_session_downloads: 每个会话最大下载次数
        """
        self.pool_size = pool_size
        self.max_session_downloads = max_session_downloads
        self.pool = queue.Queue(maxsize=pool_size)
        self.active_drivers = {}  # {driver: {'downloads': 0, 'created_at': time}}
        self.lock = threading.RLock()
        self.config_manager = ConfigManager()
        self.logger = get_logger(__name__)

        # 初始化连接池
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            driver = self._create_driver()
            self.pool.put(driver)
            self.active_drivers[driver] = {
                'downloads': 0,
                'created_at': time.time()
            }

    def _create_driver(self) -> webdriver.Chrome:
        """创建新的WebDriver实例"""
        try:
            # 获取配置
            headless = self.config_manager.get('headless', True)
            window_size = self.config_manager.get('browser.window_size', '1920,1080')
            page_load_timeout = self.config_manager.get('timeout.page_load', 30)
            element_wait_timeout = self.config_manager.get('timeout.element_wait', 10)

            # 配置Chrome选项
            chrome_options = Options()

            if headless:
                chrome_options.add_argument('--headless')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--window-size=' + window_size)

            # 添加反检测设置
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 创建WebDriver实例
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(page_load_timeout)

            # 设置隐式等待
            driver.implicitly_wait(element_wait_timeout)

            self.logger.info(f"创建新的WebDriver实例，池大小: {self.pool.qsize() + 1}")
            return driver

        except Exception as e:
            self.logger.error(f"创建WebDriver失败: {e}")
            raise

    def _is_driver_healthy(self, driver: webdriver.Chrome) -> bool:
        """检查WebDriver是否健康"""
        try:
            # 检查driver是否仍然有效
            driver.current_url
            driver.title
            return True
        except Exception:
            return False

    def _cleanup_driver(self, driver: webdriver.Chrome):
        """清理WebDriver实例"""
        try:
            if driver in self.active_drivers:
                del self.active_drivers[driver]

            try:
                driver.quit()
            except Exception:
                pass  # 忽略关闭时的异常

            self.logger.debug("清理WebDriver实例")
        except Exception as e:
            self.logger.error(f"清理WebDriver失败: {e}")

    def get_driver(self) -> webdriver.Chrome:
        """获取一个可用的WebDriver实例"""
        try:
            # 尝试从池中获取
            driver = self.pool.get_nowait()

            # 检查driver是否健康
            if self._is_driver_healthy(driver):
                self.logger.debug(f"从池中获取WebDriver，剩余: {self.pool.qsize()}")
                return driver
            else:
                self.logger.warning("从池中获取的WebDriver不健康，重新创建")
                self._cleanup_driver(driver)

        except queue.Empty:
            self.logger.debug("连接池为空，创建新的WebDriver")

        # 创建新的driver
        return self._create_driver()

    def return_driver(self, driver: webdriver.Chrome):
        """归还WebDriver到连接池"""
        try:
            with self.lock:
                if driver not in self.active_drivers:
                    self.logger.warning("尝试归还未知的WebDriver实例")
                    return

                # 更新下载计数
                self.active_drivers[driver]['downloads'] += 1
                downloads = self.active_drivers[driver]['downloads']

                # 检查是否需要重启（超过最大下载次数或运行时间过长）
                created_at = self.active_drivers[driver]['created_at']
                runtime = time.time() - created_at

                if downloads >= self.max_session_downloads or runtime > 1800:  # 30分钟
                    self.logger.info(f"WebDriver达到使用限制（下载次数: {downloads}, 运行时间: {runtime:.1f}s），重新创建")
                    self._cleanup_driver(driver)
                    new_driver = self._create_driver()
                    self.pool.put(new_driver)
                else:
                    # 检查健康状态
                    if self._is_driver_healthy(driver):
                        self.pool.put(driver)
                        self.logger.debug(f"WebDriver归还到池中，剩余: {self.pool.qsize()}")
                    else:
                        self.logger.warning("WebDriver不健康，重新创建")
                        self._cleanup_driver(driver)
                        new_driver = self._create_driver()
                        self.pool.put(new_driver)

        except Exception as e:
            self.logger.error(f"归还WebDriver失败: {e}")
            # 确保清理异常的driver
            self._cleanup_driver(driver)

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        with self.lock:
            return {
                'pool_size': self.pool.qsize(),
                'max_pool_size': self.pool_size,
                'active_drivers': len(self.active_drivers),
                'driver_stats': [
                    {
                        'downloads': info['downloads'],
                        'runtime': time.time() - info['created_at']
                    }
                    for info in self.active_drivers.values()
                ]
            }

    def cleanup_all(self):
        """清理所有WebDriver实例"""
        self.logger.info("清理所有WebDriver实例")

        with self.lock:
            # 清理池中的driver
            while not self.pool.empty():
                try:
                    driver = self.pool.get_nowait()
                    self._cleanup_driver(driver)
                except queue.Empty:
                    break

            # 清理所有active driver
            drivers_to_cleanup = list(self.active_drivers.keys())
            for driver in drivers_to_cleanup:
                self._cleanup_driver(driver)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup_all()


class EnhancedWebDriverManager:
    """增强的WebDriver管理器，集成连接池"""

    def __init__(self, pool_size: int = 3, max_session_downloads: int = 20):
        """
        初始化增强的WebDriver管理器

        Args:
            pool_size: 连接池大小
            max_session_downloads: 每个会话最大下载次数
        """
        self.driver_pool = WebDriverPool(pool_size, max_session_downloads)
        self.current_driver = None
        self.logger = get_logger(__name__)

    def get_driver(self) -> webdriver.Chrome:
        """获取WebDriver实例"""
        if self.current_driver is None:
            self.current_driver = self.driver_pool.get_driver()
        return self.current_driver

    def release_driver(self):
        """释放当前WebDriver实例"""
        if self.current_driver is not None:
            self.driver_pool.return_driver(self.current_driver)
            self.current_driver = None

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        return self.driver_pool.get_pool_status()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release_driver()
        self.driver_pool.cleanup_all()


# 为向后兼容性保留原有类名
WebDriverManager = EnhancedWebDriverManager


def create_webdriver_manager(pool_size: int = 3, max_session_downloads: int = 20) -> EnhancedWebDriverManager:
    """
    创建WebDriver管理器的工厂函数

    Args:
        pool_size: 连接池大小
        max_session_downloads: 每个会话最大下载次数

    Returns:
        EnhancedWebDriverManager: WebDriver管理器实例
    """
    return EnhancedWebDriverManager(pool_size, max_session_downloads)