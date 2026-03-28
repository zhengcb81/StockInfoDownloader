"""
Enhanced Driver Pool Module Unit Tests
测试增强版WebDriver连接池功能
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from src.web.enhanced_driver_pool import (
    EnhancedWebDriverPool,
    PoolConfig,
    DriverHealth,
    DriverPriority,
    DriverMetrics,
    create_enhanced_driver_pool,
    EnhancedWebDriverManager
)


class TestPoolConfig:
    """测试连接池配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = PoolConfig()

        assert config.min_pool_size == 3
        assert config.max_pool_size == 10
        assert config.max_session_downloads == 20
        assert config.health_check_interval == 60
        assert config.memory_threshold == 80.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = PoolConfig(
            min_pool_size=5,
            max_pool_size=15,
            max_session_downloads=30,
            health_check_interval=30
        )

        assert config.min_pool_size == 5
        assert config.max_pool_size == 15
        assert config.max_session_downloads == 30


class TestDriverMetrics:
    """测试驱动指标"""

    def test_driver_metrics_creation(self):
        """测试创建驱动指标"""
        metrics = DriverMetrics(
            response_time=1.5,
            memory_usage=50.0,
            success_rate=0.95,
            error_count=2,
            total_requests=40,
            last_health_check=time.time(),
            consecutive_failures=0
        )

        assert metrics.response_time == 1.5
        assert metrics.memory_usage == 50.0
        assert metrics.success_rate == 0.95
        assert metrics.total_requests == 40
        assert metrics.consecutive_failures == 0


class TestDriverHealth:
    """测试驱动健康状态枚举"""

    def test_driver_health_enum(self):
        """测试健康状态枚举"""
        assert DriverHealth.HEALTHY.value == "healthy"
        assert DriverHealth.DEGRADED.value == "degraded"
        assert DriverHealth.UNHEALTHY.value == "unhealthy"
        assert DriverHealth.DEAD.value == "dead"


class TestDriverPriority:
    """测试驱动优先级枚举"""

    def test_driver_priority_enum(self):
        """测试优先级枚举"""
        assert DriverPriority.HIGH.value == 1
        assert DriverPriority.NORMAL.value == 2
        assert DriverPriority.LOW.value == 3


class TestEnhancedWebDriverPool:
    """测试增强版WebDriver连接池"""

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_pool_initialization(self, mock_chrome, mock_config):
        """测试连接池初始化"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig(min_pool_size=2, max_pool_size=5)
        pool = EnhancedWebDriverPool(config)

        assert pool.config.min_pool_size == 2
        assert pool.config.max_pool_size == 5

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_get_driver_by_priority(self, mock_chrome, mock_config):
        """测试按优先级获取driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig(min_pool_size=2, max_pool_size=5)
        pool = EnhancedWebDriverPool(config)

        # 按高优先级获取
        driver = pool.get_driver(priority=DriverPriority.HIGH)
        assert driver is not None

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_return_driver(self, mock_chrome, mock_config):
        """测试归还driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig(min_pool_size=2, max_pool_size=5)
        pool = EnhancedWebDriverPool(config)

        # 获取driver
        driver = pool.get_driver()

        # 归还driver
        pool.return_driver(driver, success=True)

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_get_pool_status(self, mock_chrome, mock_config):
        """测试获取连接池状态"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig()
        pool = EnhancedWebDriverPool(config)

        status = pool.get_pool_status()
        assert 'pool_size' in status
        assert 'active_drivers' in status
        assert 'min_pool_size' in status
        assert 'max_pool_size' in status

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_get_detailed_metrics(self, mock_chrome, mock_config):
        """测试获取详细指标"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig()
        pool = EnhancedWebDriverPool(config)

        metrics = pool.get_detailed_metrics()
        assert 'pool_status' in metrics
        assert 'driver_metrics' in metrics
        assert 'system_resources' in metrics

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_cleanup_all(self, mock_chrome, mock_config):
        """测试清理所有driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig()
        pool = EnhancedWebDriverPool(config)
        pool.cleanup_all()

        # 所有driver应该被清理
        assert len(pool.active_drivers) == 0

    @patch('src.web.enhanced_driver_pool.ConfigManager')
    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_context_manager(self, mock_chrome, mock_config):
        """测试上下文管理器"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_config.return_value.get = Mock(side_effect=lambda x, y=None: y)

        config = PoolConfig()
        with EnhancedWebDriverPool(config) as pool:
            assert pool is not None


class TestEnhancedDriverPoolFactory:
    """测试增强连接池工厂函数"""

    @patch('src.web.enhanced_driver_pool.webdriver.Chrome')
    def test_create_enhanced_driver_pool(self, mock_chrome):
        """测试创建增强连接池"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        config = PoolConfig()
        pool = create_enhanced_driver_pool(config)

        assert pool is not None
        assert isinstance(pool, EnhancedWebDriverPool)


class TestEnhancedWebDriverManager:
    """测试增强WebDriver管理器"""

    @patch('src.web.enhanced_driver_pool.create_enhanced_driver_pool')
    def test_manager_initialization(self, mock_create_pool):
        """测试管理器初始化"""
        mock_pool = Mock()
        mock_create_pool.return_value = mock_pool

        manager = EnhancedWebDriverManager()

        assert manager.driver_pool is not None
        assert manager.current_driver is None

    @patch('src.web.enhanced_driver_pool.create_enhanced_driver_pool')
    def test_manager_get_driver(self, mock_create_pool):
        """测试管理器获取driver"""
        mock_pool = Mock()
        mock_driver = Mock()
        mock_pool.get_driver.return_value = mock_driver
        mock_create_pool.return_value = mock_pool

        manager = EnhancedWebDriverManager()
        driver = manager.get_driver()

        assert driver == mock_driver

    @patch('src.web.enhanced_driver_pool.create_enhanced_driver_pool')
    def test_manager_release_driver(self, mock_create_pool):
        """测试管理器释放driver"""
        mock_pool = Mock()
        mock_driver = Mock()
        mock_pool.get_driver.return_value = mock_driver
        mock_create_pool.return_value = mock_pool

        manager = EnhancedWebDriverManager()
        manager.get_driver()
        manager.release_driver(success=True)

        mock_pool.return_driver.assert_called_once()

    @patch('src.web.enhanced_driver_pool.create_enhanced_driver_pool')
    def test_manager_get_pool_status(self, mock_create_pool):
        """测试管理器获取池状态"""
        mock_pool = Mock()
        mock_pool.get_pool_status.return_value = {'pool_size': 3}
        mock_create_pool.return_value = mock_pool

        manager = EnhancedWebDriverManager()
        status = manager.get_pool_status()

        assert status == {'pool_size': 3}
