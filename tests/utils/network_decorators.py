#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络环境感知测试装饰器
提供检测网络连接状态并相应处理测试的装饰器
"""

import functools
import socket
import urllib.request
import urllib.error
import time
import logging
from typing import Callable, Optional, Any
import pytest

logger = logging.getLogger(__name__)


def check_network_connection(
    host: str = "8.8.8.8",
    port: int = 53,
    timeout: float = 3.0
) -> bool:
    """
    检查网络连接状态

    Args:
        host: 要连接的主机（默认Google DNS）
        port: 端口号（默认DNS端口53）
        timeout: 连接超时时间（秒）

    Returns:
        bool: 网络是否可用
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        logger.debug(f"网络连接检查成功: {host}:{port}")
        return True
    except (socket.error, OSError, TimeoutError) as e:
        logger.debug(f"网络连接检查失败: {host}:{port}, 错误: {e}")
        return False


def check_website_availability(
    url: str = "https://www.baidu.com",
    timeout: float = 5.0
) -> bool:
    """
    检查网站可访问性

    Args:
        url: 要检查的URL
        timeout: 请求超时时间（秒）

    Returns:
        bool: 网站是否可访问
    """
    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        status = response.getcode()
        logger.debug(f"网站可访问性检查: {url}, 状态码: {status}")
        return 200 <= status < 400
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        logger.debug(f"网站可访问性检查失败: {url}, 错误: {e}")
        return False


class NetworkStatus:
    """网络状态检测器"""

    def __init__(
        self,
        check_dns: bool = True,
        check_website: bool = True,
        dns_host: str = "8.8.8.8",
        dns_port: int = 53,
        website_url: str = "https://www.baidu.com",
        timeout: float = 3.0
    ):
        """
        初始化网络状态检测器

        Args:
            check_dns: 是否检查DNS连接
            check_website: 是否检查网站可访问性
            dns_host: DNS主机
            dns_port: DNS端口
            website_url: 检查网站URL
            timeout: 超时时间
        """
        self.check_dns = check_dns
        self.check_website = check_website
        self.dns_host = dns_host
        self.dns_port = dns_port
        self.website_url = website_url
        self.timeout = timeout
        self._last_check_time = 0
        self._last_result = None
        self._cache_duration = 30  # 缓存结果30秒

    def is_network_available(self, force_check: bool = False) -> bool:
        """
        检查网络是否可用

        Args:
            force_check: 是否强制检查（忽略缓存）

        Returns:
            bool: 网络是否可用
        """
        current_time = time.time()

        # 使用缓存结果（如果没过期）
        if (not force_check and
            self._last_result is not None and
            current_time - self._last_check_time < self._cache_duration):
            logger.debug(f"使用缓存的网络状态: {'可用' if self._last_result else '不可用'}")
            return self._last_result

        result = self._perform_network_check()

        # 更新缓存
        self._last_check_time = current_time
        self._last_result = result

        return result

    def _perform_network_check(self) -> bool:
        """执行网络检查"""
        if self.check_dns:
            dns_available = check_network_connection(
                host=self.dns_host,
                port=self.dns_port,
                timeout=self.timeout
            )
            if not dns_available:
                logger.warning("DNS连接检查失败，网络可能不可用")
                return False

        if self.check_website:
            website_available = check_website_availability(
                url=self.website_url,
                timeout=self.timeout
            )
            if not website_available:
                logger.warning(f"网站 {self.website_url} 不可访问，网络可能有问题")
                # 如果只检查网站，返回False；如果同时检查DNS且DNS通过，可能只是网站问题
                # 这里我们保守一点，认为网络有问题
                return False

        return True

    def get_network_status_report(self) -> dict:
        """获取网络状态报告"""
        dns_status = None
        website_status = None

        if self.check_dns:
            dns_status = check_network_connection(
                host=self.dns_host,
                port=self.dns_port,
                timeout=self.timeout
            )

        if self.check_website:
            website_status = check_website_availability(
                url=self.website_url,
                timeout=self.timeout
            )

        return {
            "timestamp": time.time(),
            "dns_check_enabled": self.check_dns,
            "dns_status": dns_status,
            "website_check_enabled": self.check_website,
            "website_status": website_status,
            "overall_available": self.is_network_available(force_check=True)
        }


# 全局网络状态检测器实例
_default_network_checker = NetworkStatus()


def requires_network(
    func: Optional[Callable] = None,
    *,
    skip_on_failure: bool = True,
    checker: Optional[NetworkStatus] = None,
    message: Optional[str] = None
):
    """
    网络需求装饰器

    用法1（作为函数装饰器）:
        @requires_network
        def test_something():
            pass

    用法2（作为pytest标记）:
        @requires_network(skip_on_failure=True)
        def test_something():
            pass

    Args:
        func: 要装饰的函数
        skip_on_failure: 网络不可用时是否跳过测试（True）还是失败（False）
        checker: 网络状态检测器实例
        message: 跳过或失败时的自定义消息

    Returns:
        Callable: 装饰器函数
    """
    if checker is None:
        checker = _default_network_checker

    def decorator(test_func: Callable) -> Callable:
        @functools.wraps(test_func)
        def wrapper(*args, **kwargs):
            if checker.is_network_available():
                return test_func(*args, **kwargs)
            else:
                network_report = checker.get_network_status_report()
                error_msg = message or f"网络不可用，无法运行测试 {test_func.__name__}"
                error_msg += f"\n网络状态报告: {network_report}"

                if skip_on_failure:
                    logger.warning(f"跳过测试 {test_func.__name__}: {error_msg}")
                    pytest.skip(error_msg)
                else:
                    logger.error(f"测试失败 {test_func.__name__}: {error_msg}")
                    pytest.fail(error_msg)

        # 添加pytest标记
        wrapper.pytestmark = getattr(wrapper, 'pytestmark', []) + [pytest.mark.network]

        return wrapper

    # 支持带参数和不带参数的调用
    if func is None:
        return decorator
    else:
        return decorator(func)


def network_aware(
    skip_on_failure: bool = True,
    checker: Optional[NetworkStatus] = None,
    message: Optional[str] = None
):
    """
    网络感知装饰器（工厂函数）

    Args:
        skip_on_failure: 网络不可用时是否跳过测试
        checker: 网络状态检测器
        message: 自定义消息

    Returns:
        Callable: 装饰器
    """
    def decorator(func: Callable) -> Callable:
        return requires_network(
            func=func,
            skip_on_failure=skip_on_failure,
            checker=checker,
            message=message
        )
    return decorator


class NetworkAwareTest:
    """网络感知测试基类"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.network_checker = NetworkStatus()
        self._network_available = None

    def setup_method(self, method):
        """测试方法设置，检查网络"""
        super().setup_method(method) if hasattr(super(), 'setup_method') else None
        self._network_available = self.network_checker.is_network_available()

        if not self._network_available and hasattr(method, '__name__'):
            method_name = method.__name__
            if method_name.startswith('test_'):
                report = self.network_checker.get_network_status_report()
                pytest.skip(f"网络不可用，跳过测试 {method_name}\n网络报告: {report}")

    def requires_network(self, func: Callable) -> Callable:
        """类内网络需求装饰器"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self._network_available:
                report = self.network_checker.get_network_status_report()
                pytest.skip(f"网络不可用，跳过测试 {func.__name__}\n网络报告: {report}")
            return func(*args, **kwargs)
        return wrapper


# pytest fixture: 网络状态检测器
@pytest.fixture(scope="session")
def network_checker():
    """提供网络状态检测器fixture"""
    return NetworkStatus()


# pytest fixture: 网络可用性
@pytest.fixture(scope="function")
def network_available(network_checker):
    """检查网络是否可用的fixture"""
    available = network_checker.is_network_available()
    if not available:
        report = network_checker.get_network_status_report()
        pytest.skip(f"网络不可用，跳过测试\n网络报告: {report}")
    return available


# 便捷函数
def skip_if_no_network(checker: Optional[NetworkStatus] = None):
    """如果没有网络则跳过测试"""
    if checker is None:
        checker = _default_network_checker

    if not checker.is_network_available():
        report = checker.get_network_status_report()
        pytest.skip(f"网络不可用，跳过测试\n网络报告: {report}")


def fail_if_no_network(checker: Optional[NetworkStatus] = None):
    """如果没有网络则使测试失败"""
    if checker is None:
        checker = _default_network_checker

    if not checker.is_network_available():
        report = checker.get_network_status_report()
        pytest.fail(f"网络不可用，测试失败\n网络报告: {report}")


def retry_on_network_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    checker: Optional[NetworkStatus] = None
):
    """
    网络失败重试装饰器

    当网络操作失败时自动重试，特别适合网络不稳定的环境

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数（每次重试延迟乘以该系数）
        exceptions: 要捕获的异常类型
        checker: 网络状态检测器，用于检查网络状态

    Returns:
        Callable: 装饰器函数
    """
    if checker is None:
        checker = _default_network_checker

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    # 如果是重试，先检查网络状态
                    if attempt > 0:
                        logger.info(f"第 {attempt} 次重试 {func.__name__}，等待 {current_delay:.1f} 秒")
                        time.sleep(current_delay)

                        # 检查网络状态
                        if not checker.is_network_available():
                            logger.warning(f"重试 {attempt} 时网络不可用，继续等待")
                            current_delay *= backoff
                            continue

                    # 执行函数
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}")

                    # 如果是最后一次尝试，则抛出异常
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 所有 {max_retries + 1} 次尝试都失败")
                        raise

                    # 更新延迟时间
                    current_delay *= backoff

            # 理论上不会执行到这里
            raise last_exception

        return wrapper

    return decorator


def smart_network_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    skip_on_permanent_failure: bool = True
):
    """
    智能网络重试装饰器

    结合网络状态检查的智能重试，适用于端到端测试

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间
        backoff: 退避系数
        skip_on_permanent_failure: 永久性失败时是否跳过测试

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            checker = NetworkStatus()
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    # 检查网络状态
                    if not checker.is_network_available():
                        if attempt < max_retries:
                            logger.warning(f"网络不可用，等待 {current_delay:.1f} 秒后重试")
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue
                        else:
                            error_msg = f"网络不可用，{max_retries + 1} 次重试后仍然失败"
                            if skip_on_permanent_failure:
                                pytest.skip(error_msg)
                            else:
                                pytest.fail(error_msg)

                    # 执行函数
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}")

                    # 分析异常类型
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ['timeout', 'connection', 'network', 'socket']):
                        # 网络相关错误，可以重试
                        if attempt < max_retries:
                            logger.info(f"网络相关错误，等待 {current_delay:.1f} 秒后重试")
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue

                    # 非网络错误或达到最大重试次数
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 所有尝试都失败")
                        raise
                    else:
                        # 非网络错误，立即抛出
                        raise

            # 理论上不会执行到这里
            raise last_exception if last_exception else RuntimeError("未知错误")

        return wrapper

    return decorator


if __name__ == "__main__":
    # 测试网络检查功能
    checker = NetworkStatus()
    print("网络状态检查:")
    print(f"  网络可用: {checker.is_network_available()}")
    print(f"  详细报告: {checker.get_network_status_report()}")

    # 测试新装饰器
    print("\n新增装饰器:")
    print("  - retry_on_network_failure: 网络失败重试装饰器")
    print("  - smart_network_retry: 智能网络重试装饰器")