"""
Rate Limiter Module
Prevents too frequent requests to avoid being blocked by target websites.
"""

import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.core.config import ConfigManager
from src.core.logger import get_logger


@dataclass
class RateLimitInfo:
    """Rate limit information"""

    max_requests: int
    time_window: float
    current_count: int
    window_start: float
    wait_time: float


class RateLimiter:
    """Rate limiter"""

    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: deque[float] = deque()
        self.lock = threading.RLock()
        self.logger = get_logger(__name__)

        # Statistics
        self.total_requests = 0
        self.blocked_requests = 0
        self.total_wait_time = 0.0

        self.logger.info(f"Rate limiter initialized: {max_requests} requests / {time_window}s")

    def _cleanup_old_requests(self):
        """Clean up requests outside the time window."""
        current_time = time.time()
        cutoff_time = current_time - self.time_window

        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()

    def wait_if_needed(self, reason: str = "") -> float:
        """
        Wait if needed.

        Args:
            reason: Request reason (for logging)

        Returns:
            float: Actual wait time
        """
        with self.lock:
            self._cleanup_old_requests()
            self.total_requests += 1

            if len(self.requests) >= self.max_requests:
                # Calculate wait time needed
                oldest_request = self.requests[0]
                current_time = time.time()
                wait_time = self.time_window - (current_time - oldest_request)

                if wait_time > 0:
                    self.blocked_requests += 1
                    self.total_wait_time += wait_time

                    log_msg = f"Rate limit: waiting {wait_time:.2f}s"
                    if reason:
                        log_msg += f" ({reason})"
                    self.logger.warning(log_msg)

                    time.sleep(wait_time)
                    return wait_time

            # Record new request
            self.requests.append(time.time())

            if reason:
                self.logger.debug(f"Request allowed: {reason}")

            return 0.0

    def get_rate_limit_info(self) -> RateLimitInfo:
        """
        Get rate limit information.

        Returns:
            RateLimitInfo: Rate limit information
        """
        with self.lock:
            self._cleanup_old_requests()
            current_time = time.time()

            # Calculate requests in current window
            window_requests = len(self.requests)
            window_start = self.requests[0] if self.requests else current_time

            # Calculate wait time
            if window_requests >= self.max_requests:
                wait_time = self.time_window - (current_time - window_start)
            else:
                wait_time = 0.0

            return RateLimitInfo(
                max_requests=self.max_requests,
                time_window=self.time_window,
                current_count=window_requests,
                window_start=window_start,
                wait_time=max(0.0, wait_time),
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics.

        Returns:
            Dict[str, Any]: Statistics
        """
        with self.lock:
            self._cleanup_old_requests()
            current_time = time.time()

            # Calculate request rate
            total_time = current_time - (
                self.requests[0] if self.requests else current_time
            )
            request_rate = len(self.requests) / max(total_time, 1.0)

            # Calculate block rate
            block_rate = self.blocked_requests / max(self.total_requests, 1) * 100

            # Calculate average wait time
            avg_wait_time = self.total_wait_time / max(self.blocked_requests, 1)

            return {
                "max_requests": self.max_requests,
                "time_window": self.time_window,
                "current_requests": len(self.requests),
                "request_rate": request_rate,
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "block_rate": block_rate,
                "total_wait_time": self.total_wait_time,
                "avg_wait_time": avg_wait_time,
            }

    def reset_stats(self):
        """Reset statistics."""
        with self.lock:
            self.total_requests = 0
            self.blocked_requests = 0
            self.total_wait_time = 0.0
        self.logger.info("Rate limit statistics reset")

    def adjust_limits(
        self, max_requests: Optional[int] = None, time_window: Optional[float] = None
    ):
        """
        Adjust rate limit parameters.

        Args:
            max_requests: Maximum requests
            time_window: Time window
        """
        with self.lock:
            old_max = self.max_requests
            old_window = self.time_window

            if max_requests is not None:
                self.max_requests = max_requests
            if time_window is not None:
                self.time_window = time_window

            if old_max != self.max_requests or old_window != self.time_window:
                self.logger.info(
                    f"Rate limit adjusted: {old_max}/{old_window}s -> {self.max_requests}/{self.time_window}s"
                )


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts limits dynamically based on responses."""

    def __init__(
        self, initial_max_requests: int = 10, initial_time_window: float = 60.0
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_max_requests: Initial maximum requests
            initial_time_window: Initial time window
        """
        self.base_limiter = RateLimiter(initial_max_requests, initial_time_window)
        self.logger = get_logger(__name__)

        # Adaptive parameters
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment_time = time.time()
        self.adjustment_interval = 300.0  # Adjust every 5 minutes

        # Configuration parameters
        self.min_requests = 1
        self.max_requests = 50
        self.min_window = 10.0
        self.max_window = 300.0

        self.logger.info("Adaptive rate limiter initialized")

    def wait_if_needed(self, reason: str = "") -> float:
        """
        Wait if needed.

        Args:
            reason: Request reason

        Returns:
            float: Actual wait time
        """
        # Check if adjustment is needed
        self._check_adjustment()

        return self.base_limiter.wait_if_needed(reason)

    def record_success(self):
        """Record successful request."""
        self.success_count += 1

    def record_failure(self, error_type: str = "unknown"):
        """
        Record failed request.

        Args:
            error_type: Error type
        """
        self.failure_count += 1
        self.logger.debug(f"Recorded failure request: {error_type}")

    def _check_adjustment(self):
        """Check and adjust rate limit parameters."""
        current_time = time.time()
        if current_time - self.last_adjustment_time < self.adjustment_interval:
            return

        total_requests = self.success_count + self.failure_count
        if total_requests < 10:  # Not enough requests to adjust
            return

        success_rate = self.success_count / total_requests

        # Adjust limits based on success rate
        if success_rate > 0.9:  # High success rate, can increase limits
            self._increase_limits()
        elif success_rate < 0.7:  # Low success rate, need to decrease limits
            self._decrease_limits()

        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment_time = current_time

        self.logger.info(f"Adaptive adjustment complete, success rate: {success_rate:.2%}")

    def _increase_limits(self):
        """Increase rate limits."""
        stats = self.base_limiter.get_stats()
        current_max = stats["max_requests"]
        current_window = stats["time_window"]

        # Increase by 20%, but not exceeding maximum
        new_max = min(int(current_max * 1.2), self.max_requests)
        new_window = min(current_window * 1.1, self.max_window)

        self.base_limiter.adjust_limits(new_max, new_window)
        self.logger.info(
            f"Increased rate limits: {current_max}/{current_window}s -> {new_max}/{new_window}s"
        )

    def _decrease_limits(self):
        """Decrease rate limits."""
        stats = self.base_limiter.get_stats()
        current_max = stats["max_requests"]
        current_window = stats["time_window"]

        # Decrease by 20%, but not below minimum
        new_max = max(int(current_max * 0.8), self.min_requests)
        new_window = max(current_window * 0.9, self.min_window)

        self.base_limiter.adjust_limits(new_max, new_window)
        self.logger.info(
            f"Decreased rate limits: {current_max}/{current_window}s -> {new_max}/{new_window}s"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        base_stats = self.base_limiter.get_stats()
        total_requests = self.success_count + self.failure_count
        success_rate = self.success_count / max(total_requests, 1)

        return {
            **base_stats,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "adaptive": True,
        }


class DomainRateLimiter:
    """Rate limiter grouped by domain."""

    def __init__(
        self, default_max_requests: int = 10, default_time_window: float = 60.0
    ):
        """
        Initialize domain rate limiter.

        Args:
            default_max_requests: Default maximum requests
            default_time_window: Default time window
        """
        self.limiters: Dict[str, RateLimiter] = {}
        self.default_max_requests = default_max_requests
        self.default_time_window = default_time_window
        self.lock = threading.RLock()
        self.logger = get_logger(__name__)

    def get_limiter(self, domain: str) -> RateLimiter:
        """
        Get rate limiter for specified domain.

        Args:
            domain: Domain name

        Returns:
            RateLimiter: Rate limiter
        """
        with self.lock:
            if domain not in self.limiters:
                self.limiters[domain] = RateLimiter(
                    self.default_max_requests, self.default_time_window
                )
                self.logger.debug(f"Created domain rate limiter: {domain}")
            return self.limiters[domain]

    def wait_if_needed(self, url: str, reason: str = "") -> float:
        """
        Wait if needed.

        Args:
            url: Request URL
            reason: Request reason

        Returns:
            float: Actual wait time
        """
        # Extract domain
        domain = self._extract_domain(url)
        limiter = self.get_limiter(domain)
        return limiter.wait_if_needed(f"{domain} - {reason}")

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all domains."""
        with self.lock:
            return {
                domain: limiter.get_stats() for domain, limiter in self.limiters.items()
            }

    def cleanup_inactive_limiters(self, max_age: float = 3600.0):
        """
        Clean up inactive rate limiters.

        Args:
            max_age: Maximum inactive time in seconds
        """
        current_time = time.time()
        domains_to_remove = []

        with self.lock:
            for domain, limiter in self.limiters.items():
                stats = limiter.get_stats()
                if (
                    stats["current_requests"] == 0
                    and current_time - stats.get("last_request_time", 0) > max_age
                ):
                    domains_to_remove.append(domain)

            for domain in domains_to_remove:
                del self.limiters[domain]
                self.logger.debug(f"Cleaned up inactive domain rate limiter: {domain}")


# Global rate limiter instance
_global_rate_limiter: Optional[DomainRateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_global_rate_limiter() -> DomainRateLimiter:
    """Get global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        with _rate_limiter_lock:
            if _global_rate_limiter is None:
                config_manager = ConfigManager()
                max_requests = config_manager.get("anti_crawler.max_requests", 10)
                time_window = config_manager.get("anti_crawler.time_window", 60.0)
                _global_rate_limiter = DomainRateLimiter(max_requests, time_window)
    return _global_rate_limiter


@contextmanager
def rate_limit(url: str, reason: str = ""):
    """
    Rate limit context manager.

    Args:
        url: Request URL
        reason: Request reason

    Usage:
        with rate_limit("https://example.com", "data_fetch"):
            # Execute request
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
    Convenience function: wait if needed.

    Args:
        url: Request URL
        reason: Request reason

    Returns:
        float: Actual wait time
    """
    return get_global_rate_limiter().wait_if_needed(url, reason)
