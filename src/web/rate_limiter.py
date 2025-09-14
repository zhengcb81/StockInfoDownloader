"""
速率限制器模块
防止过度频繁的请求，避免被目标网站封禁
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass
from contextlib import contextmanager

from src.core.logger import get_logger
from src.core.config import ConfigManager


@dataclass
class RateLimitInfo:
    """速率限制信息"""
    max_requests: int
    time_window: float
    current_count: int
    window_start: float
    wait_time: float


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.RLock()
        self.logger = get_logger(__name__)

        # 统计信息
        self.total_requests = 0
        self.blocked_requests = 0
        self.total_wait_time = 0.0

        self.logger.info(f"速率限制器初始化: {max_requests} requests / {time_window}s")

    def _cleanup_old_requests(self):
        """清理时间窗口外的旧请求"""
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()

    def wait_if_needed(self, reason: str = "") -> float:
        """
        如果需要则等待

        Args:
            reason: 请求原因（用于日志）

        Returns:
            float: 实际等待时间
        """
        with self.lock:
            self._cleanup_old_requests()
            self.total_requests += 1

            if len(self.requests) >= self.max_requests:
                # 计算需要等待的时间
                oldest_request = self.requests[0]
                current_time = time.time()
                wait_time = self.time_window - (current_time - oldest_request)

                if wait_time > 0:
                    self.blocked_requests += 1
                    self.total_wait_time += wait_time

                    log_msg = f"速率限制: 等待 {wait_time:.2f}s"
                    if reason:
                        log_msg += f" ({reason})"
                    self.logger.warning(log_msg)

                    time.sleep(wait_time)
                    return wait_time

            # 记录新请求
            self.requests.append(time.time())

            if reason:
                self.logger.debug(f"请求允许: {reason}")

            return 0.0

    def get_rate_limit_info(self) -> RateLimitInfo:
        """
        获取速率限制信息

        Returns:
            RateLimitInfo: 速率限制信息
        """
        with self.lock:
            self._cleanup_old_requests()
            current_time = time.time()

            # 计算当前窗口中的请求数
            window_requests = len(self.requests)
            window_start = self.requests[0] if self.requests else current_time

            # 计算等待时间
            if window_requests >= self.max_requests:
                wait_time = self.time_window - (current_time - window_start)
            else:
                wait_time = 0.0

            return RateLimitInfo(
                max_requests=self.max_requests,
                time_window=self.time_window,
                current_count=window_requests,
                window_start=window_start,
                wait_time=max(0.0, wait_time)
            )

    def get_stats(self) -> Dict[str, any]:
        """
        获取统计信息

        Returns:
            Dict[str, any]: 统计信息
        """
        with self.lock:
            self._cleanup_old_requests()
            current_time = time.time()

            # 计算请求速率
            total_time = current_time - (self.requests[0] if self.requests else current_time)
            request_rate = len(self.requests) / max(total_time, 1.0)

            # 计算阻止率
            block_rate = self.blocked_requests / max(self.total_requests, 1) * 100

            # 计算平均等待时间
            avg_wait_time = self.total_wait_time / max(self.blocked_requests, 1)

            return {
                'max_requests': self.max_requests,
                'time_window': self.time_window,
                'current_requests': len(self.requests),
                'request_rate': request_rate,
                'total_requests': self.total_requests,
                'blocked_requests': self.blocked_requests,
                'block_rate': block_rate,
                'total_wait_time': self.total_wait_time,
                'avg_wait_time': avg_wait_time
            }

    def reset_stats(self):
        """重置统计信息"""
        with self.lock:
            self.total_requests = 0
            self.blocked_requests = 0
            self.total_wait_time = 0.0
        self.logger.info("速率限制统计信息已重置")

    def adjust_limits(self, max_requests: Optional[int] = None, time_window: Optional[float] = None):
        """
        调整速率限制参数

        Args:
            max_requests: 最大请求数
            time_window: 时间窗口
        """
        with self.lock:
            old_max = self.max_requests
            old_window = self.time_window

            if max_requests is not None:
                self.max_requests = max_requests
            if time_window is not None:
                self.time_window = time_window

            if old_max != self.max_requests or old_window != self.time_window:
                self.logger.info(f"速率限制调整: {old_max}/{old_window}s -> {self.max_requests}/{self.time_window}s")


class AdaptiveRateLimiter:
    """自适应速率限制器，根据响应动态调整限制"""

    def __init__(self, initial_max_requests: int = 10, initial_time_window: float = 60.0):
        """
        初始化自适应速率限制器

        Args:
            initial_max_requests: 初始最大请求数
            initial_time_window: 初始时间窗口
        """
        self.base_limiter = RateLimiter(initial_max_requests, initial_time_window)
        self.logger = get_logger(__name__)

        # 自适应参数
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment_time = time.time()
        self.adjustment_interval = 300.0  # 5分钟调整一次

        # 配置参数
        self.min_requests = 1
        self.max_requests = 50
        self.min_window = 10.0
        self.max_window = 300.0

        self.logger.info("自适应速率限制器初始化完成")

    def wait_if_needed(self, reason: str = "") -> float:
        """
        如果需要则等待

        Args:
            reason: 请求原因

        Returns:
            float: 实际等待时间
        """
        # 检查是否需要调整参数
        self._check_adjustment()

        return self.base_limiter.wait_if_needed(reason)

    def record_success(self):
        """记录成功请求"""
        self.success_count += 1

    def record_failure(self, error_type: str = "unknown"):
        """
        记录失败请求

        Args:
            error_type: 错误类型
        """
        self.failure_count += 1
        self.logger.debug(f"记录失败请求: {error_type}")

    def _check_adjustment(self):
        """检查并调整速率限制参数"""
        current_time = time.time()
        if current_time - self.last_adjustment_time < self.adjustment_interval:
            return

        total_requests = self.success_count + self.failure_count
        if total_requests < 10:  # 请求数太少，不调整
            return

        success_rate = self.success_count / total_requests

        # 根据成功率调整限制
        if success_rate > 0.9:  # 成功率很高，可以增加限制
            self._increase_limits()
        elif success_rate < 0.7:  # 成功率较低，需要降低限制
            self._decrease_limits()

        # 重置计数器
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment_time = current_time

        self.logger.info(f"自适应调整完成，成功率: {success_rate:.2%}")

    def _increase_limits(self):
        """增加速率限制"""
        stats = self.base_limiter.get_stats()
        current_max = stats['max_requests']
        current_window = stats['time_window']

        # 增加20%，但不超过最大值
        new_max = min(int(current_max * 1.2), self.max_requests)
        new_window = min(current_window * 1.1, self.max_window)

        self.base_limiter.adjust_limits(new_max, new_window)
        self.logger.info(f"增加速率限制: {current_max}/{current_window}s -> {new_max}/{new_window}s")

    def _decrease_limits(self):
        """降低速率限制"""
        stats = self.base_limiter.get_stats()
        current_max = stats['max_requests']
        current_window = stats['time_window']

        # 减少20%，但不低于最小值
        new_max = max(int(current_max * 0.8), self.min_requests)
        new_window = max(current_window * 0.9, self.min_window)

        self.base_limiter.adjust_limits(new_max, new_window)
        self.logger.info(f"降低速率限制: {current_max}/{current_window}s -> {new_max}/{new_window}s")

    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        base_stats = self.base_limiter.get_stats()
        total_requests = self.success_count + self.failure_count
        success_rate = self.success_count / max(total_requests, 1)

        return {
            **base_stats,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': success_rate,
            'adaptive': True
        }


class DomainRateLimiter:
    """按域名分组的速率限制器"""

    def __init__(self, default_max_requests: int = 10, default_time_window: float = 60.0):
        """
        初始化域名速率限制器

        Args:
            default_max_requests: 默认最大请求数
            default_time_window: 默认时间窗口
        """
        self.limiters = {}
        self.default_max_requests = default_max_requests
        self.default_time_window = default_time_window
        self.lock = threading.RLock()
        self.logger = get_logger(__name__)

    def get_limiter(self, domain: str) -> RateLimiter:
        """
        获取指定域名的速率限制器

        Args:
            domain: 域名

        Returns:
            RateLimiter: 速率限制器
        """
        with self.lock:
            if domain not in self.limiters:
                self.limiters[domain] = RateLimiter(
                    self.default_max_requests,
                    self.default_time_window
                )
                self.logger.debug(f"创建域名速率限制器: {domain}")
            return self.limiters[domain]

    def wait_if_needed(self, url: str, reason: str = "") -> float:
        """
        如果需要则等待

        Args:
            url: 请求URL
            reason: 请求原因

        Returns:
            float: 实际等待时间
        """
        # 提取域名
        domain = self._extract_domain(url)
        limiter = self.get_limiter(domain)
        return limiter.wait_if_needed(f"{domain} - {reason}")

    def _extract_domain(self, url: str) -> str:
        """从URL中提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"

    def get_all_stats(self) -> Dict[str, Dict[str, any]]:
        """获取所有域名的统计信息"""
        with self.lock:
            return {domain: limiter.get_stats() for domain, limiter in self.limiters.items()}

    def cleanup_inactive_limiters(self, max_age: float = 3600.0):
        """
        清理不活跃的速率限制器

        Args:
            max_age: 最大不活跃时间（秒）
        """
        current_time = time.time()
        domains_to_remove = []

        with self.lock:
            for domain, limiter in self.limiters.items():
                stats = limiter.get_stats()
                if stats['current_requests'] == 0 and current_time - stats.get('last_request_time', 0) > max_age:
                    domains_to_remove.append(domain)

            for domain in domains_to_remove:
                del self.limiters[domain]
                self.logger.debug(f"清理不活跃域名速率限制器: {domain}")


# 全局速率限制器实例
_global_rate_limiter: Optional[DomainRateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_global_rate_limiter() -> DomainRateLimiter:
    """获取全局速率限制器实例"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        with _rate_limiter_lock:
            if _global_rate_limiter is None:
                config_manager = ConfigManager()
                max_requests = config_manager.get('anti_crawler.max_requests', 10)
                time_window = config_manager.get('anti_crawler.time_window', 60.0)
                _global_rate_limiter = DomainRateLimiter(max_requests, time_window)
    return _global_rate_limiter


@contextmanager
def rate_limit(url: str, reason: str = ""):
    """
    速率限制上下文管理器

    Args:
        url: 请求URL
        reason: 请求原因

    Usage:
        with rate_limit("https://example.com", "data_fetch"):
            # 执行请求
            pass
    """
    limiter = get_global_rate_limiter()
    wait_time = limiter.wait_if_needed(url, reason)
    try:
        yield wait_time
    finally:
        pass


def wait_if_needed(url: str, reason: str = "") -> float:
    """
    便捷函数：如果需要则等待

    Args:
        url: 请求URL
        reason: 请求原因

    Returns:
        float: 实际等待时间
    """
    return get_global_rate_limiter().wait_if_needed(url, reason)