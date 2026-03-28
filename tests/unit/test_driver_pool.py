"""
Driver Pool Module Unit Tests
测试WebDriver连接池功能
"""

import pytest
import queue
import threading
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from src.web.driver_pool import WebDriverPool, EnhancedWebDriverManager


class TestWebDriverPool:
    """测试WebDriver连接池"""

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_driver_pool_initialization(self, mock_chrome, mock_config):
        """测试连接池初始化"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=2, max_session_downloads=10)

        assert pool.pool_size == 2
        assert pool.max_session_downloads == 10

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_get_driver(self, mock_chrome, mock_config):
        """测试从池中获取driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=2, max_session_downloads=10)

        # 获取driver
        driver = pool.get_driver()
        assert driver is not None

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_return_driver(self, mock_chrome, mock_config):
        """测试归还driver回池"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=2, max_session_downloads=10)

        # 获取并归还driver
        driver = pool.get_driver()
        pool.return_driver(driver)

        # Driver应该回到池中
        assert pool.pool.qsize() >= 1

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_get_pool_status(self, mock_chrome, mock_config):
        """测试获取连接池状态"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=3, max_session_downloads=10)

        status = pool.get_pool_status()
        assert 'pool_size' in status
        assert 'max_pool_size' in status
        assert 'active_drivers' in status

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_cleanup_all(self, mock_chrome, mock_config):
        """测试清理所有driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=2, max_session_downloads=10)
        pool.cleanup_all()

        # 池应该被清空
        assert pool.pool.qsize() == 0
        assert len(pool.active_drivers) == 0

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_context_manager(self, mock_chrome, mock_config):
        """测试上下文管理器"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        with WebDriverPool(pool_size=2, max_session_downloads=10) as pool:
            assert pool is not None

    @patch('src.web.driver_pool.ConfigManager')
    @patch('src.web.driver_pool.webdriver.Chrome')
    def test_concurrent_get_return(self, mock_chrome, mock_config):
        """测试并发获取和归还driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        pool = WebDriverPool(pool_size=3, max_session_downloads=10)

        results = []

        def get_return():
            driver = pool.get_driver()
            time.sleep(0.1)
            pool.return_driver(driver)
            results.append(True)

        # 并发获取和归还
        threads = []
        for _ in range(5):
            t = threading.Thread(target=get_return)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 所有操作应该成功
        assert len(results) == 5


class TestEnhancedWebDriverManager:
    """测试增强的WebDriver管理器"""

    @patch('src.web.driver_pool.WebDriverPool')
    def test_manager_initialization(self, mock_pool):
        """测试管理器初始化"""
        manager = EnhancedWebDriverManager(pool_size=3, max_session_downloads=20)

        assert manager.driver_pool is not None
        assert manager.current_driver is None

    @patch('src.web.driver_pool.WebDriverPool')
    def test_get_driver(self, mock_pool):
        """测试获取driver"""
        mock_driver = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.get_driver.return_value = mock_driver
        mock_pool.return_value = mock_pool_instance

        manager = EnhancedWebDriverManager()
        driver = manager.get_driver()

        assert driver == mock_driver
        assert manager.current_driver == mock_driver

    @patch('src.web.driver_pool.WebDriverPool')
    def test_release_driver(self, mock_pool):
        """测试释放driver"""
        mock_driver = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.get_driver.return_value = mock_driver
        mock_pool.return_value = mock_pool_instance

        manager = EnhancedWebDriverManager()
        manager.get_driver()
        manager.release_driver()

        assert manager.current_driver is None

    @patch('src.web.driver_pool.WebDriverPool')
    def test_get_pool_status(self, mock_pool):
        """测试获取池状态"""
        mock_pool_instance = Mock()
        mock_pool_instance.get_pool_status.return_value = {'pool_size': 3}
        mock_pool.return_value = mock_pool_instance

        manager = EnhancedWebDriverManager()
        status = manager.get_pool_status()

        assert status == {'pool_size': 3}
