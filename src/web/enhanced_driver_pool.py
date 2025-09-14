"""
增强版WebDriver连接池模块
提供智能调度、健康监控、动态扩容等高级功能
"""

import threading
import time
import queue
import asyncio
import psutil
import statistics
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass
from contextlib import asynccontextmanager
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.core.logger import get_logger
from src.core.config import ConfigManager
from src.web.driver_pool import WebDriverPool


class DriverHealth(Enum):
    """驱动健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"


class DriverPriority(Enum):
    """驱动优先级"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class DriverMetrics:
    """驱动性能指标"""
    response_time: float
    memory_usage: float
    success_rate: float
    error_count: int
    total_requests: int
    last_health_check: float
    consecutive_failures: int


@dataclass
class PoolConfig:
    """连接池配置"""
    min_pool_size: int = 3
    max_pool_size: int = 10
    max_session_downloads: int = 20
    health_check_interval: int = 60
    response_timeout: float = 30.0
    memory_threshold: float = 80.0  # 内存使用阈值(%)
    max_consecutive_failures: int = 3
    scaling_enabled: bool = True
    scaling_threshold: float = 0.8  # 扩容阈值
    shrink_threshold: float = 0.3  # 缩容阈值


class EnhancedWebDriverPool:
    """增强版WebDriver连接池"""

    def __init__(self, config: Optional[PoolConfig] = None):
        """
        初始化增强版连接池

        Args:
            config: 连接池配置
        """
        self.config = config or PoolConfig()
        self.pool = queue.PriorityQueue(maxsize=self.config.max_pool_size)
        self.active_drivers = {}  # {driver: DriverMetrics}
        self.priority_queue = {priority: queue.Queue() for priority in DriverPriority}
        self.lock = threading.RLock()
        self.config_manager = ConfigManager()
        self.logger = get_logger(__name__)

        # 性能监控
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'pool_hits': 0,
            'pool_misses': 0,
            'scaling_events': 0
        }

        # 健康监控
        self.health_monitor_thread = None
        self.health_monitor_running = False
        self.last_health_check = {}

        # 异步事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 初始化连接池
        self._initialize_pool()
        self._start_health_monitor()

        self.logger.info(f"增强版WebDriver连接池初始化完成: "
                       f"最小池大小={self.config.min_pool_size}, "
                       f"最大池大小={self.config.max_pool_size}")

    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.config.min_pool_size):
            driver = self._create_driver()
            self._add_driver_to_pool(driver, DriverPriority.NORMAL)

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

            # 性能优化选项
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # 禁用图片加载
            chrome_options.add_argument('--disable-javascript-har-promises')  # 禁用某些JS特性

            # 添加反检测设置
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # 创建WebDriver实例
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(page_load_timeout)

            # 设置隐式等待
            driver.implicitly_wait(element_wait_timeout)

            self.logger.debug(f"创建新的WebDriver实例，当前池大小: {len(self.active_drivers) + 1}")
            return driver

        except Exception as e:
            self.logger.error(f"创建WebDriver失败: {e}")
            raise

    def _add_driver_to_pool(self, driver: webdriver.Chrome, priority: DriverPriority = DriverPriority.NORMAL):
        """添加驱动到连接池"""
        with self.lock:
            metrics = DriverMetrics(
                response_time=0.0,
                memory_usage=0.0,
                success_rate=1.0,
                error_count=0,
                total_requests=0,
                last_health_check=time.time(),
                consecutive_failures=0
            )
            self.active_drivers[driver] = metrics
            self.priority_queue[priority].put((time.time(), driver))
            self.pool.put((priority.value, time.time(), driver))

    def get_driver(self, priority: DriverPriority = DriverPriority.NORMAL) -> webdriver.Chrome:
        """
        获取可用的WebDriver实例

        Args:
            priority: 请求优先级

        Returns:
            webdriver.Chrome: 可用的WebDriver实例
        """
        start_time = time.time()
        self.performance_stats['total_requests'] += 1

        try:
            # 尝试从优先级队列获取
            if not self.priority_queue[priority].empty():
                _, driver = self.priority_queue[priority].get_nowait()
                self.performance_stats['pool_hits'] += 1
                self.logger.debug(f"从优先级队列获取WebDriver: {priority.name}")
                return self._validate_and_return_driver(driver)

            # 尝试从普通池获取
            try:
                priority_val, _, driver = self.pool.get_nowait()
                self.performance_stats['pool_hits'] += 1
                self.logger.debug(f"从连接池获取WebDriver，剩余: {self.pool.qsize()}")
                return self._validate_and_return_driver(driver)
            except queue.Empty:
                self.performance_stats['pool_misses'] += 1
                pass

            # 池为空，尝试扩容
            if self.config.scaling_enabled and len(self.active_drivers) < self.config.max_pool_size:
                driver = self._scale_up()
                self.performance_stats['scaling_events'] += 1
                return driver

            # 等待可用驱动
            self.logger.debug("连接池已满，等待可用WebDriver...")
            priority_val, _, driver = self.pool.get(timeout=self.config.response_timeout)
            return self._validate_and_return_driver(driver)

        except Exception as e:
            self.logger.error(f"获取WebDriver失败: {e}")
            self.performance_stats['failed_requests'] += 1
            raise

    def _validate_and_return_driver(self, driver: webdriver.Chrome) -> webdriver.Chrome:
        """验证并返回驱动"""
        if self._is_driver_healthy(driver):
            self.performance_stats['successful_requests'] += 1
            return driver
        else:
            # 驱动不健康，创建新的
            self._cleanup_driver(driver)
            new_driver = self._create_driver()
            self._add_driver_to_pool(new_driver)
            return new_driver

    def _is_driver_healthy(self, driver: webdriver.Chrome) -> bool:
        """检查驱动健康状态"""
        try:
            # 检查driver是否仍然有效
            start_time = time.time()
            driver.current_url
            driver.title
            response_time = time.time() - start_time

            # 更新性能指标
            if driver in self.active_drivers:
                metrics = self.active_drivers[driver]
                metrics.response_time = response_time
                metrics.last_health_check = time.time()

                # 检查内存使用
                try:
                    process = psutil.Process()
                    metrics.memory_usage = process.memory_percent()
                except:
                    pass

                # 检查响应时间
                if response_time > self.config.response_timeout:
                    metrics.consecutive_failures += 1
                    return False

                # 检查内存使用
                if metrics.memory_usage > self.config.memory_threshold:
                    metrics.consecutive_failures += 1
                    return False

                # 检查连续失败次数
                if metrics.consecutive_failures >= self.config.max_consecutive_failures:
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"Driver健康检查失败: {e}")
            if driver in self.active_drivers:
                self.active_drivers[driver].consecutive_failures += 1
            return False

    def return_driver(self, driver: webdriver.Chrome, success: bool = True):
        """
        归还WebDriver到连接池

        Args:
            driver: WebDriver实例
            success: 操作是否成功
        """
        try:
            with self.lock:
                if driver not in self.active_drivers:
                    self.logger.warning("尝试归还未知的WebDriver实例")
                    return

                metrics = self.active_drivers[driver]
                metrics.total_requests += 1

                if success:
                    metrics.success_rate = (metrics.total_requests - metrics.error_count) / metrics.total_requests
                    metrics.consecutive_failures = 0
                else:
                    metrics.error_count += 1
                    metrics.success_rate = (metrics.total_requests - metrics.error_count) / metrics.total_requests
                    metrics.consecutive_failures += 1

                # 检查是否需要重启
                runtime = time.time() - (metrics.last_health_check - metrics.response_time)
                if (metrics.total_requests >= self.config.max_session_downloads or
                    runtime > 1800 or  # 30分钟
                    metrics.success_rate < 0.5 or  # 成功率低于50%
                    metrics.consecutive_failures > 0):

                    self.logger.info(f"WebDriver达到重启条件，重新创建: "
                                   f"请求次数={metrics.total_requests}, "
                                   f"成功率={metrics.success_rate:.2%}, "
                                   f"连续失败={metrics.consecutive_failures}")
                    self._cleanup_driver(driver)
                    new_driver = self._create_driver()
                    self._add_driver_to_pool(new_driver)
                else:
                    # 归还到池中
                    if self._is_driver_healthy(driver):
                        priority = self._calculate_driver_priority(metrics)
                        self.priority_queue[priority].put((time.time(), driver))
                        self.pool.put((priority.value, time.time(), driver))
                        self.logger.debug(f"WebDriver归还到池中，剩余: {self.pool.qsize()}")
                    else:
                        self._cleanup_driver(driver)
                        new_driver = self._create_driver()
                        self._add_driver_to_pool(new_driver)

        except Exception as e:
            self.logger.error(f"归还WebDriver失败: {e}")
            self._cleanup_driver(driver)

    def _calculate_driver_priority(self, metrics: DriverMetrics) -> DriverPriority:
        """计算驱动优先级"""
        if metrics.success_rate >= 0.9 and metrics.response_time < 5.0:
            return DriverPriority.HIGH
        elif metrics.success_rate >= 0.7 and metrics.response_time < 10.0:
            return DriverPriority.NORMAL
        else:
            return DriverPriority.LOW

    def _scale_up(self) -> webdriver.Chrome:
        """扩容连接池"""
        if len(self.active_drivers) >= self.config.max_pool_size:
            raise RuntimeError("连接池已达到最大大小")

        driver = self._create_driver()
        self._add_driver_to_pool(driver, DriverPriority.NORMAL)
        self.logger.info(f"连接池扩容: 当前大小={len(self.active_drivers)}/{self.config.max_pool_size}")
        return driver

    def _scale_down(self):
        """缩容连接池"""
        if len(self.active_drivers) <= self.config.min_pool_size:
            return

        # 找到性能最差的驱动进行清理
        worst_driver = None
        worst_metrics = None

        for driver, metrics in self.active_drivers.items():
            if worst_metrics is None or metrics.success_rate < worst_metrics.success_rate:
                worst_driver = driver
                worst_metrics = metrics

        if worst_driver:
            self._cleanup_driver(worst_driver)
            self.logger.info(f"连接池缩容: 当前大小={len(self.active_drivers)}/{self.config.max_pool_size}")

    def _cleanup_driver(self, driver: webdriver.Chrome):
        """清理WebDriver实例"""
        try:
            if driver in self.active_drivers:
                del self.active_drivers[driver]

            try:
                driver.quit()
            except Exception:
                pass

            self.logger.debug("清理WebDriver实例")
        except Exception as e:
            self.logger.error(f"清理WebDriver失败: {e}")

    def _start_health_monitor(self):
        """启动健康监控线程"""
        def health_monitor():
            while self.health_monitor_running:
                try:
                    self._perform_health_check()
                    time.sleep(self.config.health_check_interval)
                except Exception as e:
                    self.logger.error(f"健康监控异常: {e}")
                    time.sleep(10)  # 错误后等待10秒再重试

        self.health_monitor_running = True
        self.health_monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        self.health_monitor_thread.start()
        self.logger.info("健康监控线程已启动")

    def _perform_health_check(self):
        """执行健康检查"""
        try:
            with self.lock:
                current_time = time.time()
                drivers_to_remove = []

                # 检查所有驱动的健康状态
                for driver, metrics in self.active_drivers.items():
                    if current_time - metrics.last_health_check > self.config.health_check_interval:
                        if not self._is_driver_healthy(driver):
                            drivers_to_remove.append(driver)

                # 清理不健康的驱动
                for driver in drivers_to_remove:
                    self._cleanup_driver(driver)
                    self.logger.warning(f"清理不健康的WebDriver实例")

                # 动态扩缩容
                if self.config.scaling_enabled:
                    utilization_rate = self.performance_stats['pool_hits'] / max(self.performance_stats['total_requests'], 1)

                    if utilization_rate > self.config.scaling_threshold and len(self.active_drivers) < self.config.max_pool_size:
                        self._scale_up()
                    elif utilization_rate < self.config.shrink_threshold and len(self.active_drivers) > self.config.min_pool_size:
                        self._scale_down()

                # 更新性能统计
                self._update_performance_stats()

        except Exception as e:
            self.logger.error(f"健康检查执行失败: {e}")

    def _update_performance_stats(self):
        """更新性能统计"""
        if self.active_drivers:
            response_times = [m.response_time for m in self.active_drivers.values() if m.response_time > 0]
            if response_times:
                self.performance_stats['average_response_time'] = statistics.mean(response_times)

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        with self.lock:
            health_distribution = {}
            for driver, metrics in self.active_drivers.items():
                if metrics.success_rate >= 0.9:
                    health_distribution['healthy'] = health_distribution.get('healthy', 0) + 1
                elif metrics.success_rate >= 0.7:
                    health_distribution['degraded'] = health_distribution.get('degraded', 0) + 1
                else:
                    health_distribution['unhealthy'] = health_distribution.get('unhealthy', 0) + 1

            return {
                'pool_size': self.pool.qsize(),
                'active_drivers': len(self.active_drivers),
                'min_pool_size': self.config.min_pool_size,
                'max_pool_size': self.config.max_pool_size,
                'health_distribution': health_distribution,
                'performance_stats': self.performance_stats.copy(),
                'priority_queues': {
                    priority.name: queue.qsize()
                    for priority, queue in self.priority_queue.items()
                }
            }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """获取详细性能指标"""
        with self.lock:
            driver_metrics = []
            for driver, metrics in self.active_drivers.items():
                driver_metrics.append({
                    'driver_id': id(driver),
                    'response_time': metrics.response_time,
                    'memory_usage': metrics.memory_usage,
                    'success_rate': metrics.success_rate,
                    'error_count': metrics.error_count,
                    'total_requests': metrics.total_requests,
                    'consecutive_failures': metrics.consecutive_failures,
                    'last_health_check': metrics.last_health_check
                })

            return {
                'pool_status': self.get_pool_status(),
                'driver_metrics': driver_metrics,
                'system_resources': {
                    'memory_percent': psutil.virtual_memory().percent,
                    'cpu_percent': psutil.cpu_percent(),
                    'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                }
            }

    def optimize_pool(self):
        """优化连接池配置"""
        with self.lock:
            # 基于历史性能数据调整配置
            hit_rate = self.performance_stats['pool_hits'] / max(self.performance_stats['total_requests'], 1)

            if hit_rate < 0.5 and self.config.min_pool_size < self.config.max_pool_size:
                # 提高最小池大小
                old_min = self.config.min_pool_size
                self.config.min_pool_size = min(self.config.min_pool_size + 1, self.config.max_pool_size)
                self.logger.info(f"优化连接池: 最小池大小 {old_min} -> {self.config.min_pool_size}")

                # 扩容到新的最小大小
                while len(self.active_drivers) < self.config.min_pool_size:
                    driver = self._create_driver()
                    self._add_driver_to_pool(driver)

    def cleanup_all(self):
        """清理所有WebDriver实例"""
        self.logger.info("清理所有WebDriver实例")

        # 停止健康监控
        self.health_monitor_running = False
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=5)

        with self.lock:
            # 清理池中的driver
            while not self.pool.empty():
                try:
                    _, _, driver = self.pool.get_nowait()
                    self._cleanup_driver(driver)
                except queue.Empty:
                    break

            # 清理所有active driver
            drivers_to_cleanup = list(self.active_drivers.keys())
            for driver in drivers_to_cleanup:
                self._cleanup_driver(driver)

    @asynccontextmanager
    async def get_driver_async(self, priority: DriverPriority = DriverPriority.NORMAL):
        """异步获取WebDriver上下文管理器"""
        driver = await self.loop.run_in_executor(None, self.get_driver, priority)
        try:
            yield driver
        finally:
            await self.loop.run_in_executor(None, self.return_driver, driver)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup_all()

    def __del__(self):
        """析构函数"""
        try:
            self.cleanup_all()
        except:
            pass


# 工厂函数
def create_enhanced_driver_pool(config: Optional[PoolConfig] = None) -> EnhancedWebDriverPool:
    """
    创建增强版WebDriver连接池的工厂函数

    Args:
        config: 连接池配置

    Returns:
        EnhancedWebDriverPool: 增强版连接池实例
    """
    return EnhancedWebDriverPool(config)


# 向后兼容的包装器
class EnhancedWebDriverManager:
    """增强的WebDriver管理器，集成增强连接池"""

    def __init__(self, config: Optional[PoolConfig] = None):
        """
        初始化增强的WebDriver管理器

        Args:
            config: 连接池配置
        """
        self.driver_pool = create_enhanced_driver_pool(config)
        self.current_driver = None
        self.logger = get_logger(__name__)

    def get_driver(self, priority: DriverPriority = DriverPriority.NORMAL) -> webdriver.Chrome:
        """获取WebDriver实例"""
        if self.current_driver is None:
            self.current_driver = self.driver_pool.get_driver(priority)
        return self.current_driver

    def release_driver(self, success: bool = True):
        """释放当前WebDriver实例"""
        if self.current_driver is not None:
            self.driver_pool.return_driver(self.current_driver, success)
            self.current_driver = None

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        return self.driver_pool.get_pool_status()

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """获取详细性能指标"""
        return self.driver_pool.get_detailed_metrics()

    def optimize_pool(self):
        """优化连接池"""
        self.driver_pool.optimize_pool()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release_driver()
        self.driver_pool.cleanup_all()