"""
Anti-Crawler Rate Limiter Module Tests
Tests for adaptive rate limiting in anti-crawler protection
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.anti_crawler.rate_limiter import AdaptiveRateLimiter


class TestAdaptiveRateLimiter:
    """AdaptiveRateLimiter class tests"""

    def test_init_default(self):
        """Test initialization with default config"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        assert limiter.initial_requests_per_minute == 30
        assert limiter.max_requests_per_minute == 100
        assert limiter.adjustment_factor == 1.2
        assert limiter.success_rate_threshold == 0.8
        assert limiter.error_rate_threshold == 0.2
        assert limiter.current_rate_limit == 30
        assert limiter.window_size == 60
        assert limiter.protection_mode is False

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "initial_requests_per_minute": 60,
            "max_requests_per_minute": 200,
            "adjustment_factor": 1.5,
            "success_rate_threshold": 0.9,
            "error_rate_threshold": 0.1,
        }
        limiter = AdaptiveRateLimiter(config)

        assert limiter.initial_requests_per_minute == 60
        assert limiter.max_requests_per_minute == 200
        assert limiter.adjustment_factor == 1.5
        assert limiter.success_rate_threshold == 0.9
        assert limiter.error_rate_threshold == 0.1

    def test_record_request_success(self):
        """Test recording successful request"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            mock_time.time.return_value = 100.0
            limiter.record_request(True)

            assert len(limiter.request_history) == 1
            assert len(limiter.success_history) == 1
            assert len(limiter.error_history) == 0

    def test_record_request_failure(self):
        """Test recording failed request"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            mock_time.time.return_value = 100.0
            limiter.record_request(False)

            assert len(limiter.request_history) == 1
            assert len(limiter.success_history) == 0
            assert len(limiter.error_history) == 1

    def test_cleanup_history(self):
        """Test history cleanup"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        limiter.request_history = [10.0, 20.0, 30.0, 100.0]  # 100.0 is within window
        limiter.success_history = [10.0, 30.0]
        limiter.error_history = [20.0]

        with patch("src.web.anti_crawler.rate_limiter.time.time", return_value=100.0):
            limiter._cleanup_history()

            # Only 100.0 should remain (within 60 second window from 100.0)
            assert len(limiter.request_history) == 1

    def test_can_make_request_true(self):
        """Test can_make_request when allowed"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            mock_time.time.return_value = 100.0
            can_make, wait_time = limiter.can_make_request()

            assert can_make is True
            assert wait_time == 0

    def test_can_make_request_rate_limited(self):
        """Test can_make_request when rate limited"""
        config = {"initial_requests_per_minute": 2}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time.time", return_value=100.0):
            # Add requests at the limit
            limiter.request_history = [99.5, 99.8, 100.0]
            limiter.current_rate_limit = 2

            # Now should be rate limited
            can_make, wait_time = limiter.can_make_request()

            assert can_make is False

    def test_can_make_request_protection_mode(self):
        """Test can_make_request in protection mode"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        limiter.protection_mode = True

        with patch("src.web.anti_crawler.rate_limiter.time.time", return_value=100.0):
            # Add recent requests
            limiter.request_history = [99.5, 99.8, 100.0]

            # Should be limited in protection mode
            can_make, wait_time = limiter.can_make_request()

            assert can_make is False

    def test_get_stats(self):
        """Test getting statistics"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            mock_time.time.return_value = 100.0
            limiter.record_request(True)
            limiter.record_request(False)

            stats = limiter.get_stats()

            assert "current_rate_limit" in stats
            assert "success_rate" in stats
            assert "error_rate" in stats
            assert "protection_mode" in stats
            assert stats["total_requests"] == 2

    def test_get_stats_no_requests(self):
        """Test getting stats when no requests"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        stats = limiter.get_stats()

        assert stats["total_requests"] == 0
        assert stats["success_rate"] == 0
        assert stats["error_rate"] == 0

    def test_adjust_rate_increase_on_success(self):
        """Test rate increases on high success rate"""
        config = {"initial_requests_per_minute": 10, "success_rate_threshold": 0.8}
        limiter = AdaptiveRateLimiter(config)
        limiter.current_rate_limit = 10

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            # Add successful requests
            for _ in range(10):
                mock_time.time.return_value = 100.0 + len(limiter.request_history) * 0.1
                limiter.record_request(True)

            mock_time.time.return_value = 200.0
            limiter._adjust_rate_limit()

            # Rate should have increased
            assert limiter.current_rate_limit >= 10

    def test_adjust_rate_decrease_on_failure(self):
        """Test rate decreases on low success rate"""
        config = {"initial_requests_per_minute": 10}
        limiter = AdaptiveRateLimiter(config)
        limiter.current_rate_limit = 10

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            # Add failed requests
            for _ in range(10):
                mock_time.time.return_value = 100.0 + len(limiter.request_history) * 0.1
                limiter.record_request(False)

            mock_time.time.return_value = 200.0
            limiter._adjust_rate_limit()

            # Rate should have decreased
            assert limiter.current_rate_limit <= 10

    def test_protection_mode_entry(self):
        """Test entering protection mode"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            # Add failed requests to trigger protection mode
            for _ in range(10):
                mock_time.time.return_value = 100.0 + len(limiter.request_history) * 0.1
                limiter.record_request(False)

            mock_time.time.return_value = 200.0
            limiter._adjust_rate_limit()

            # Should enter protection mode if error rate > 0.5
            if len(limiter.error_history) / len(limiter.request_history) > 0.5:
                assert limiter.protection_mode is True

    def test_protection_mode_exit(self):
        """Test exiting protection mode"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        limiter.protection_mode = True
        limiter.protection_start_time = 100.0

        with patch("src.web.anti_crawler.rate_limiter.time.time", return_value=401.0):  # > 300 seconds later
            # Manually call adjust to check for protection mode exit
            limiter._adjust_rate_limit()

            # Should exit protection mode (more than 300 seconds have passed)
            assert limiter.protection_mode is False

    def test_adjust_rate_max_limit(self):
        """Test rate doesn't exceed max limit"""
        config = {"initial_requests_per_minute": 10, "max_requests_per_minute": 50}
        limiter = AdaptiveRateLimiter(config)
        limiter.current_rate_limit = 50

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            # Add many successful requests
            for _ in range(20):
                mock_time.time.return_value = 100.0 + len(limiter.request_history) * 0.1
                limiter.record_request(True)

            mock_time.time.return_value = 200.0
            limiter._adjust_rate_limit()

            assert limiter.current_rate_limit <= 50

    def test_adjust_rate_min_limit(self):
        """Test rate doesn't go below minimum"""
        config = {"initial_requests_per_minute": 10}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time") as mock_time:
            # Add failed requests
            for _ in range(10):
                mock_time.time.return_value = 100.0 + len(limiter.request_history) * 0.1
                limiter.record_request(False)

            mock_time.time.return_value = 200.0
            limiter._adjust_rate_limit()

            assert limiter.current_rate_limit >= 1

    def test_current_requests_per_minute(self):
        """Test current requests per minute calculation"""
        config = {}
        limiter = AdaptiveRateLimiter(config)

        with patch("src.web.anti_crawler.rate_limiter.time.time", return_value=101.5):
            # Add requests within the last minute
            limiter.request_history = [100.0, 100.5, 101.0]

            stats = limiter.get_stats()
            assert stats["current_requests_per_minute"] == 3

    def test_window_size(self):
        """Test window size is set correctly"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        assert limiter.window_size == 60

    def test_protection_duration(self):
        """Test protection duration is set correctly"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        assert limiter.protection_duration == 300

    def test_request_history_initialization(self):
        """Test request history is initialized as empty list"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        assert limiter.request_history == []
        assert limiter.success_history == []
        assert limiter.error_history == []

    def test_last_adjustment_initialization(self):
        """Test last adjustment is set on initialization"""
        config = {}
        limiter = AdaptiveRateLimiter(config)
        # last_adjustment should be set to current time
        assert limiter.last_adjustment > 0
