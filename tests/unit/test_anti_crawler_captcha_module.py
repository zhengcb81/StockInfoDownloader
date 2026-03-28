"""
Anti-Crawler Captcha Module Tests
Tests for CAPTCHA detection and handling functionality
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.anti_crawler.captcha import CaptchaHandler


class TestCaptchaHandler:
    """CaptchaHandler class tests"""

    def test_init_default(self):
        """Test initialization with default config"""
        config = {}
        handler = CaptchaHandler(config)

        assert handler.strategies == ["delay_retry", "proxy_rotation", "user_agent_change"]
        assert handler.max_wait_time == 120
        assert handler.solve_timeout == 30
        assert len(handler.captcha_indicators) > 0

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "strategies": ["delay_retry"],
            "max_wait_time": 60,
            "solve_timeout": 15
        }
        handler = CaptchaHandler(config)

        assert handler.strategies == ["delay_retry"]
        assert handler.max_wait_time == 60
        assert handler.solve_timeout == 15

    def test_captcha_indicators(self):
        """Test captcha indicators are defined"""
        config = {}
        handler = CaptchaHandler(config)

        expected_indicators = [
            "captcha",
            "验证码",
            "请输入验证码",
            "请完成验证",
            "security check",
            "human verification",
            "robot check",
        ]
        assert handler.captcha_indicators == expected_indicators

    def test_detect_captcha_in_content(self):
        """Test detecting captcha in page content"""
        config = {}
        handler = CaptchaHandler(config)

        # Test with captcha keyword
        result = handler.detect_captcha("Please complete the captcha to continue")
        assert result is True

    def test_detect_captcha_chinese(self):
        """Test detecting captcha with Chinese text"""
        config = {}
        handler = CaptchaHandler(config)

        # Test with Chinese captcha text
        result = handler.detect_captcha("请输入验证码")
        assert result is True

    def test_detect_captcha_in_headers(self):
        """Test detecting captcha in response headers"""
        config = {}
        handler = CaptchaHandler(config)

        # Test with exact indicator in headers value
        headers = {"X-Verification": "Please enter the captcha to continue"}
        result = handler.detect_captcha("No content here", headers)
        assert result is True

    def test_detect_captcha_no_captcha(self):
        """Test when no captcha is present"""
        config = {}
        handler = CaptchaHandler(config)

        # Test with no captcha
        result = handler.detect_captcha("Welcome to our website", {})
        assert result is False

    def test_detect_captcha_case_insensitive(self):
        """Test captcha detection is case insensitive"""
        config = {}
        handler = CaptchaHandler(config)

        # Test case insensitive
        result = handler.detect_captcha("CAPTCHA challenge required")
        assert result is True

    def test_execute_strategy_delay_retry(self):
        """Test executing delay retry strategy"""
        config = {}
        handler = CaptchaHandler(config)

        with patch("src.web.anti_crawler.captcha.time.sleep"):
            result = handler._execute_strategy("delay_retry", {})
            assert result["strategy"] == "delay_retry"

    def test_execute_strategy_proxy_rotation_no_manager(self):
        """Test proxy rotation strategy without proxy manager"""
        config = {}
        handler = CaptchaHandler(config)

        result = handler._execute_strategy("proxy_rotation", {})
        assert result["success"] is False
        assert "Proxy manager not available" in result["error"]

    def test_execute_strategy_proxy_rotation_with_manager(self):
        """Test proxy rotation strategy with proxy manager"""
        config = {}
        handler = CaptchaHandler(config)

        mock_manager = MagicMock()
        context = {"proxy_manager": mock_manager}

        result = handler._execute_strategy("proxy_rotation", context)
        assert result["success"] is True
        mock_manager.rotate_all_proxies.assert_called_once()

    def test_execute_strategy_user_agent_change_no_agents(self):
        """Test user agent change strategy without user agents"""
        config = {}
        handler = CaptchaHandler(config)

        result = handler._execute_strategy("user_agent_change", {})
        assert result["success"] is False
        assert "User agent list not available" in result["error"]

    def test_execute_strategy_user_agent_change_with_agents(self):
        """Test user agent change strategy with user agents"""
        config = {}
        handler = CaptchaHandler(config)

        user_agents = ["Agent1", "Agent2", "Agent3"]
        context = {"user_agents": user_agents}

        with patch("random.choice", return_value="Agent2"):
            result = handler._execute_strategy("user_agent_change", context)
            assert result["success"] is True
            assert result["new_user_agent"] == "Agent2"

    def test_execute_strategy_ip_change(self):
        """Test IP change strategy"""
        config = {}
        handler = CaptchaHandler(config)

        with patch("src.web.anti_crawler.captcha.time.sleep"):
            result = handler._execute_strategy("ip_change", {})
            assert result["strategy"] == "ip_change"
            assert result["action"] == "ip_changed"

    def test_execute_strategy_unknown(self):
        """Test executing unknown strategy"""
        config = {}
        handler = CaptchaHandler(config)

        result = handler._execute_strategy("unknown_strategy", {})
        assert result["success"] is False
        assert "Unknown strategy" in result["error"]

    def test_handle_captcha_first_strategy_succeeds(self):
        """Test handling captcha when first strategy succeeds"""
        config = {"strategies": ["delay_retry"]}
        handler = CaptchaHandler(config)

        with patch.object(handler, "_execute_strategy", return_value={"success": True}):
            result = handler.handle_captcha({})
            assert result["success"] is True

    def test_handle_captcha_all_strategies_fail(self):
        """Test handling captcha when all strategies fail"""
        config = {"strategies": ["delay_retry", "proxy_rotation"]}
        handler = CaptchaHandler(config)

        with patch.object(handler, "_execute_strategy", return_value={"success": False}):
            result = handler.handle_captcha({})
            assert result["success"] is False
            assert result["strategy"] == "all"

    def test_handle_captcha_exception_handling(self):
        """Test exception handling in captcha handling"""
        config = {"strategies": ["delay_retry"]}
        handler = CaptchaHandler(config)

        with patch.object(handler, "_execute_strategy", side_effect=Exception("Strategy error")):
            result = handler.handle_captcha({})
            assert result["success"] is False
            assert "results" in result

    def test_strategy_delay_retry_returns_delay(self):
        """Test delay retry strategy returns delay value"""
        config = {}
        handler = CaptchaHandler(config)

        with patch("random.uniform", return_value=45.0), \
             patch("src.web.anti_crawler.captcha.time.sleep"):
            result = handler._strategy_delay_retry({})
            assert result["delay"] == 45.0

    def test_strategy_user_agent_change_returns_new_agent(self):
        """Test user agent change returns new user agent"""
        config = {}
        handler = CaptchaHandler(config)

        user_agents = ["Agent1", "Agent2"]
        context = {"user_agents": user_agents}

        with patch("random.choice", return_value="Agent2"):
            result = handler._strategy_user_agent_change(context)
            assert result["new_user_agent"] == "Agent2"

    def test_strategy_user_agent_change_action(self):
        """Test user agent change action"""
        config = {}
        handler = CaptchaHandler(config)

        user_agents = ["Agent1", "Agent2"]
        context = {"user_agents": user_agents}

        with patch("random.choice", return_value="Agent2"):
            result = handler._strategy_user_agent_change(context)
            assert result["action"] == "user_agent_changed"

    def test_handle_captcha_multiple_strategies(self):
        """Test handling captcha with multiple strategies"""
        config = {
            "strategies": ["delay_retry", "user_agent_change"]
        }
        handler = CaptchaHandler(config)

        # First strategy fails, second succeeds
        call_count = [0]

        def side_effect(strategy, context):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"success": False, "strategy": strategy}
            else:
                return {"success": True, "strategy": strategy}

        with patch.object(handler, "_execute_strategy", side_effect=side_effect):
            result = handler.handle_captcha({})
            assert result["success"] is True

    def test_detect_captcha_empty_content(self):
        """Test captcha detection with empty content"""
        config = {}
        handler = CaptchaHandler(config)

        result = handler.detect_captcha("", {})
        assert result is False

    def test_detect_captcha_null_headers(self):
        """Test captcha detection with null headers"""
        config = {}
        handler = CaptchaHandler(config)

        result = handler.detect_captcha("Some content", None)
        assert result is False

    def test_strategy_proxy_rotation_action(self):
        """Test proxy rotation strategy action"""
        config = {}
        handler = CaptchaHandler(config)

        mock_manager = MagicMock()
        context = {"proxy_manager": mock_manager}

        result = handler._strategy_proxy_rotation(context)
        assert result["action"] == "proxy_rotated"

    def test_max_wait_time_from_config(self):
        """Test max wait time from config"""
        config = {"max_wait_time": 180}
        handler = CaptchaHandler(config)
        assert handler.max_wait_time == 180

    def test_solve_timeout_from_config(self):
        """Test solve timeout from config"""
        config = {"solve_timeout": 45}
        handler = CaptchaHandler(config)
        assert handler.solve_timeout == 45
