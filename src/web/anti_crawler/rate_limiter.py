#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adaptive rate limiter module.
Adjusts request rates based on success/error rates.
"""

import time
from typing import Any, Dict, List, Tuple

from src.core.logger import get_logger


class AdaptiveRateLimiter:
    """Adaptive rate limiter"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("AdaptiveRateLimiter")

        # Rate limiting parameters
        self.initial_requests_per_minute = config.get("initial_requests_per_minute", 30)
        self.max_requests_per_minute = config.get("max_requests_per_minute", 100)
        self.adjustment_factor = config.get("adjustment_factor", 1.2)
        self.success_rate_threshold = config.get("success_rate_threshold", 0.8)
        self.error_rate_threshold = config.get("error_rate_threshold", 0.2)

        # Dynamic parameters
        self.current_rate_limit = self.initial_requests_per_minute
        self.request_history = []
        self.success_history = []
        self.error_history = []

        # Statistics window
        self.window_size = 60  # 60-second window
        self.last_adjustment = time.time()

        # Protection mechanism
        self.protection_mode = False
        self.protection_start_time = None
        self.protection_duration = 300  # 5-minute protection mode

        self.logger.info(
            f"Adaptive rate limiter initialized, initial rate: {self.initial_requests_per_minute}/minute"
        )

    def record_request(self, success: bool = True):
        """Record request result"""
        current_time = time.time()

        # Record request
        self.request_history.append(current_time)
        if success:
            self.success_history.append(current_time)
        else:
            self.error_history.append(current_time)

        # Clean up history
        self._cleanup_history()

        # Adjust rate periodically
        if current_time - self.last_adjustment > 30:  # Adjust every 30 seconds
            self._adjust_rate_limit()

    def _cleanup_history(self):
        """Clean up expired history records"""
        cutoff_time = time.time() - self.window_size

        self.request_history = [t for t in self.request_history if t > cutoff_time]
        self.success_history = [t for t in self.success_history if t > cutoff_time]
        self.error_history = [t for t in self.error_history if t > cutoff_time]

    def _adjust_rate_limit(self):
        """Adjust rate limit"""
        current_time = time.time()
        self.last_adjustment = current_time

        # Check if should exit protection mode
        if (
            self.protection_mode
            and (current_time - self.protection_start_time) > self.protection_duration
        ):
            self.protection_mode = False
            self.logger.info("Exiting protection mode")

        # Calculate statistics
        total_requests = len(self.request_history)
        successful_requests = len(self.success_history)
        error_requests = len(self.error_history)

        if total_requests == 0:
            return

        success_rate = successful_requests / total_requests
        error_rate = error_requests / total_requests

        # Adjust rate based on success rate
        if success_rate >= self.success_rate_threshold and not self.protection_mode:
            # High success rate, increase rate appropriately
            new_rate = min(
                self.current_rate_limit * self.adjustment_factor,
                self.max_requests_per_minute,
            )
            if new_rate > self.current_rate_limit:
                self.current_rate_limit = new_rate
                self.logger.info(
                    f"Increased rate limit to {self.current_rate_limit:.1f}/minute (success rate: {success_rate:.2%})"
                )

        elif (
            success_rate < self.success_rate_threshold
            or error_rate > self.error_rate_threshold
        ):
            # Low success rate or high error rate, decrease rate
            new_rate = self.current_rate_limit / self.adjustment_factor
            self.current_rate_limit = max(1, new_rate)

            # If error rate is too high, enter protection mode
            if error_rate > 0.5 or success_rate < 0.5:
                self.protection_mode = True
                self.protection_start_time = current_time
                self.current_rate_limit = max(5, self.current_rate_limit / 2)
                self.logger.warning(
                    f"Entering protection mode, reduced rate limit to {self.current_rate_limit:.1f}/minute"
                )

            self.logger.warning(
                f"Reduced rate limit to {self.current_rate_limit:.1f}/minute (success rate: {success_rate:.2%}, error rate: {error_rate:.2%})"
            )

    def can_make_request(self) -> Tuple[bool, float]:
        """Check if request can be made"""
        if self.protection_mode:
            # More conservative in protection mode
            recent_requests = len(
                [t for t in self.request_history if time.time() - t < 10]
            )
            if recent_requests >= 2:
                wait_time = (
                    10 - (time.time() - self.request_history[-1])
                    if self.request_history
                    else 0
                )
                return False, max(0, wait_time)

        # Check rate limit
        recent_requests = len([t for t in self.request_history if time.time() - t < 60])
        if recent_requests >= self.current_rate_limit:
            wait_time = (
                60 - (time.time() - self.request_history[-1])
                if self.request_history
                else 0
            )
            return False, max(0, wait_time)

        return True, 0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        self._cleanup_history()

        total_requests = len(self.request_history)
        successful_requests = len(self.success_history)
        error_requests = len(self.error_history)

        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        error_rate = error_requests / total_requests if total_requests > 0 else 0

        current_requests_per_minute = len(
            [t for t in self.request_history if time.time() - t < 60]
        )

        return {
            "current_rate_limit": self.current_rate_limit,
            "current_requests_per_minute": current_requests_per_minute,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "protection_mode": self.protection_mode,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "error_requests": error_requests,
        }
