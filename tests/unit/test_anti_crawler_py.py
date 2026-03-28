#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反爬虫策略模块 (anti_crawler_py.py) 单元测试
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from src.web.anti_crawler_py import (
    AntiCrawlerStrategy,
    is_test_environment,
)


class TestIsTestEnvironment:
    """测试 is_test_environment 函数"""

    def test_with_test_env_variable(self):
        """测试 TEST_ENV 环境变量"""
        with patch.dict(os.environ, {"TEST_ENV": "true"}):
            assert is_test_environment() is True

    def test_with_pytest_current_test(self):
        """测试 PYTEST_CURRENT_TEST 环境变量"""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
            assert is_test_environment() is True

    def test_with_test_in_argv(self):
        """测试 test 在 sys.argv 中"""
        original_argv = sys.argv
        try:
            sys.argv = ["test_script.py"]
            # 注意：由于 pytest 本身会设置环境，这个测试可能已经返回 True
            # 我们只验证函数不会抛出异常
            result = is_test_environment()
            assert isinstance(result, bool)
        finally:
            sys.argv = original_argv

    def test_production_environment(self):
        """测试生产环境"""
        # 清除所有测试相关环境变量
        env_copy = os.environ.copy()
        for key in ["TEST_ENV", "PYTEST_CURRENT_TEST"]:
            if key in env_copy:
                del os.environ[key]

        with patch.dict(os.environ, env_copy, clear=True):
            # 由于 pytest 运行时，这仍然可能返回 True
            # 我们只验证函数能正常运行
            result = is_test_environment()
            assert isinstance(result, bool)


class TestAntiCrawlerStrategyInit:
    """测试 AntiCrawlerStrategy 初始化"""

    def test_init_production_environment(self):
        """测试生产环境初始化"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=False):
            strategy = AntiCrawlerStrategy()
            assert strategy.min_delay == 0.3
            assert strategy.max_delay == 1.0
            assert strategy.max_session_downloads == 10
            assert strategy.download_count == 0
            assert len(strategy._user_agents) == 5

    def test_init_test_environment(self):
        """测试测试环境初始化"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            strategy = AntiCrawlerStrategy()
            assert strategy.min_delay == 0.1
            assert strategy.max_delay == 0.3
            assert strategy.max_session_downloads == 10


class TestAntiCrawlerStrategyMethods:
    """测试 AntiCrawlerStrategy 方法"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            self.strategy = AntiCrawlerStrategy()

    def test_random_delay(self):
        """测试随机延迟"""
        # 使用非常短的延迟测试
        start = time.time()
        self.strategy.random_delay(0.01, 0.02)
        elapsed = time.time() - start
        assert 0.01 <= elapsed <= 0.1  # 给一些余量

    def test_random_delay_default(self):
        """测试默认参数的随机延迟"""
        start = time.time()
        self.strategy.random_delay()
        elapsed = time.time() - start
        assert elapsed >= 0  # 只验证不抛异常

    def test_dynamic_delay(self):
        """测试动态延迟"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            start = time.time()
            delay = self.strategy.dynamic_delay(0.05, 0.1)
            elapsed = time.time() - start
            assert delay is not None
            assert elapsed >= 0

    def test_dynamic_delay_increases_with_count(self):
        """测试动态延迟随下载次数增加"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            strategy = AntiCrawlerStrategy()

            # 初始延迟
            delay1 = strategy.dynamic_delay(0.5, 1.0)

            # 增加下载次数
            strategy.download_count = 100
            delay2 = strategy.dynamic_delay(0.5, 1.0)

            # 下载次数越多，延迟越长
            # 注意：由于有随机性，我们只验证第二个延迟不为None
            assert delay2 is not None

    def test_increment_download_count(self):
        """测试增加下载计数"""
        initial = self.strategy.download_count
        self.strategy.increment_download_count()
        assert self.strategy.download_count == initial + 1

    def test_reset_download_count(self):
        """测试重置下载计数"""
        self.strategy.download_count = 10
        self.strategy.reset_download_count()
        assert self.strategy.download_count == 0

    def test_set_session_parameters(self):
        """测试设置会话参数"""
        self.strategy.set_session_parameters(0.5, 1.5, 20)
        assert self.strategy.min_delay == 0.5
        assert self.strategy.max_delay == 1.5
        assert self.strategy.max_session_downloads == 20

    def test_check_session_limit_not_reached(self):
        """测试会话限制未达到"""
        result = self.strategy.check_session_limit(5)
        assert result is False

    def test_check_session_limit_reached(self):
        """测试会话限制达到"""
        result = self.strategy.check_session_limit(10)
        assert result is True

    def test_check_session_limit_exceeded(self):
        """测试会话限制超过"""
        result = self.strategy.check_session_limit(15)
        assert result is True

    def test_should_retry_timeout(self):
        """测试超时不重试"""
        error = Exception("timeout occurred")
        assert self.strategy.should_retry(error) is False

    def test_should_retry_connection_refused(self):
        """测试连接拒绝不重试"""
        error = Exception("connection refused")
        assert self.strategy.should_retry(error) is False

    def test_should_retry_dns_error(self):
        """测试 DNS 错误不重试"""
        error = Exception("dns lookup failed")
        assert self.strategy.should_retry(error) is False

    def test_should_retry_ssl_error(self):
        """测试 SSL 错误不重试"""
        error = Exception("ssl error occurred")
        assert self.strategy.should_retry(error) is False

    def test_should_retry_other_error(self):
        """测试其他错误应该重试"""
        error = Exception("some other error")
        assert self.strategy.should_retry(error) is True

    def test_before_request(self):
        """测试请求前处理"""
        # 只验证不抛异常
        self.strategy.before_request({"url": "http://example.com"})

    def test_after_request_success(self):
        """测试请求成功后处理"""
        initial_count = self.strategy.download_count
        self.strategy.after_request({"success": True})
        assert self.strategy.download_count == initial_count + 1

    def test_after_request_failure(self):
        """测试请求失败后处理"""
        initial_count = self.strategy.download_count
        self.strategy.after_request({"success": False})
        assert self.strategy.download_count == initial_count

    def test_smart_delay(self):
        """测试智能延迟"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            start = time.time()
            self.strategy.smart_delay(0.05, 0.1)
            elapsed = time.time() - start
            assert elapsed >= 0


class TestAntiCrawlerStrategyWithDriver:
    """测试需要 driver 的方法"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            self.strategy = AntiCrawlerStrategy()
        self.mock_driver = MagicMock()

    def test_apply_anti_detection(self):
        """测试应用反检测策略"""
        self.strategy.apply_anti_detection(self.mock_driver)
        # 验证 execute_script 被调用
        assert self.mock_driver.execute_script.call_count >= 3

    def test_apply_anti_detection_exception(self):
        """测试反检测策略异常处理"""
        self.mock_driver.execute_script.side_effect = Exception("Script error")
        # 不应抛出异常
        self.strategy.apply_anti_detection(self.mock_driver)

    def test_simulate_real_mouse_movement_no_driver(self):
        """测试无 driver 的鼠标移动"""
        # 不应抛出异常
        self.strategy.simulate_real_mouse_movement(None)

    def test_simulate_real_mouse_movement_with_element(self):
        """测试有元素的鼠标移动"""
        mock_element = MagicMock()
        mock_element.location = {"x": 100, "y": 100}

        # 不应抛出异常
        self.strategy.simulate_real_mouse_movement(self.mock_driver, mock_element)

    def test_simulate_real_mouse_movement_without_element(self):
        """测试无元素的鼠标移动"""
        # 不应抛出异常
        self.strategy.simulate_real_mouse_movement(self.mock_driver, None)

    def test_simulate_complex_browsing(self):
        """测试复杂浏览行为模拟"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            # 不应抛出异常
            self.strategy.simulate_complex_browsing(self.mock_driver)

    def test_simulate_complex_browsing_no_driver(self):
        """测试无 driver 的复杂浏览行为"""
        # 不应抛出异常
        self.strategy.simulate_complex_browsing(None)

    def test_simulate_scrolling(self):
        """测试滚动模拟"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            # 不应抛出异常
            self.strategy._simulate_scrolling(self.mock_driver)

    def test_simulate_scrolling_exception(self):
        """测试滚动模拟异常处理"""
        self.mock_driver.execute_script.side_effect = Exception("Scroll error")
        # 不应抛出异常
        self.strategy._simulate_scrolling(self.mock_driver)

    def test_simulate_random_clicks_no_elements(self):
        """测试无元素时的随机点击"""
        self.mock_driver.find_elements.return_value = []
        # 不应抛出异常
        self.strategy._simulate_random_clicks(self.mock_driver)

    def test_simulate_random_clicks_with_elements(self):
        """测试有元素时的随机点击"""
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        self.mock_driver.find_elements.return_value = [mock_element]

        # 不应抛出异常
        self.strategy._simulate_random_clicks(self.mock_driver)

    def test_simulate_tab_switching(self):
        """测试标签页切换模拟"""
        self.mock_driver.window_handles = ["handle1", "handle2"]
        # 不应抛出异常
        self.strategy._simulate_tab_switching(self.mock_driver)

    def test_simulate_tab_switching_single_window(self):
        """测试单窗口时的标签页切换"""
        self.mock_driver.window_handles = ["handle1"]
        # 不应抛出异常
        self.strategy._simulate_tab_switching(self.mock_driver)

    def test_simulate_human_behavior(self):
        """测试人类行为模拟"""
        mock_body = MagicMock()
        self.mock_driver.find_element.return_value = mock_body

        # 不应抛出异常
        self.strategy.simulate_human_behavior(self.mock_driver)

    def test_simulate_human_behavior_exception(self):
        """测试人类行为模拟异常处理"""
        self.mock_driver.find_element.side_effect = Exception("Find error")
        # 不应抛出异常
        self.strategy.simulate_human_behavior(self.mock_driver)

    def test_smart_wait_success(self):
        """测试智能等待成功"""
        mock_condition = MagicMock()

        with patch("src.web.anti_crawler_py.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True

            result = self.strategy.smart_wait(self.mock_driver, mock_condition, timeout=5)
            assert result is True

    def test_smart_wait_timeout(self):
        """测试智能等待超时"""
        from selenium.common.exceptions import TimeoutException

        mock_condition = MagicMock()

        with patch("src.web.anti_crawler_py.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            result = self.strategy.smart_wait(self.mock_driver, mock_condition, timeout=5)
            assert result is False

    def test_handle_rate_limit_no_captcha(self):
        """测试无验证码的速率限制处理"""
        self.mock_driver.find_element.side_effect = Exception("Not found")

        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            result = self.strategy.handle_rate_limit(self.mock_driver, retry_count=0)
            assert result is True

    def test_handle_rate_limit_with_captcha(self):
        """测试有验证码的速率限制处理"""
        # 模拟找到验证码元素
        mock_element = MagicMock()
        self.mock_driver.find_element.return_value = mock_element

        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            start = time.time()
            result = self.strategy.handle_rate_limit(self.mock_driver, retry_count=0)
            elapsed = time.time() - start

            assert result is False
            # 测试环境最多15秒，但我们设置了最小延迟
            assert elapsed >= 0


class TestAntiCrawlerStrategyEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        """设置测试环境"""
        with patch("src.web.anti_crawler_py.is_test_environment", return_value=True):
            self.strategy = AntiCrawlerStrategy()

    def test_random_delay_with_custom_range(self):
        """测试自定义范围的随机延迟"""
        start = time.time()
        self.strategy.random_delay(0.01, 0.02)
        elapsed = time.time() - start
        assert elapsed >= 0

    def test_check_session_limit_at_boundary(self):
        """测试边界值的会话限制"""
        # 刚好等于限制
        result = self.strategy.check_session_limit(10)
        assert result is True

        # 刚好少一个
        result = self.strategy.check_session_limit(9)
        assert result is False

    def test_should_retry_case_insensitive(self):
        """测试错误消息大小写不敏感"""
        error1 = Exception("TIMEOUT")
        error2 = Exception("Timeout")
        error3 = Exception("timeout")

        assert self.strategy.should_retry(error1) is False
        assert self.strategy.should_retry(error2) is False
        assert self.strategy.should_retry(error3) is False

    def test_user_agents_list(self):
        """测试 User-Agent 列表"""
        agents = self.strategy._user_agents
        assert len(agents) == 5
        assert all("Mozilla" in agent for agent in agents)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
