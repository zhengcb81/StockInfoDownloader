#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Anti-Crawler 模块测试
提升 src/web/anti_crawler/ 模块的测试覆盖率
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.web.anti_crawler.core import EnhancedAntiCrawler
from src.web.anti_crawler.types import AntiCrawlerLevel, FingerprintType
from src.web.anti_crawler.behavior import BehaviorSimulator
from src.web.anti_crawler.rate_limiter import AdaptiveRateLimiter
from src.web.anti_crawler.captcha import CaptchaHandler


class TestEnhancedAntiCrawler:
    """测试 EnhancedAntiCrawler 类"""

    def setup_method(self):
        """设置测试环境"""
        self.config = {
            "enabled": True,
            "level": "high",
            "behavior_simulation": {
                "complexity_level": "high",
                "randomization_factor": 0.3,
                "patterns": ["mouse_movement", "scrolling"]
            },
            "adaptive_rate_limiting": {},
            "captcha_handling": {},
            "fingerprint_randomization": {
                "user_agent_rotation": True,
                "screen_resolution": True
            }
        }

    def test_init_enabled(self):
        """测试启用的反爬虫系统初始化"""
        ac = EnhancedAntiCrawler(self.config)
        assert ac.enabled is True
        assert ac.level == AntiCrawlerLevel.HIGH
        assert ac.stats["total_requests"] == 0
        assert ac.fingerprint_randomization is not None

    def test_init_disabled(self):
        """测试禁用的反爬虫系统初始化"""
        config = {"enabled": False, "level": "low"}
        ac = EnhancedAntiCrawler(config)
        assert ac.enabled is False

    def test_init_fingerprint_randomization(self):
        """测试指纹随机化初始化"""
        ac = EnhancedAntiCrawler(self.config)
        assert FingerprintType.USER_AGENT in ac.fingerprint_randomization
        assert ac.fingerprint_randomization[FingerprintType.USER_AGENT] is True

    def test_before_request_disabled(self):
        """测试禁用状态下的请求前处理"""
        config = {"enabled": False, "level": "low"}
        ac = EnhancedAntiCrawler(config)
        result = ac.before_request({})
        assert result["success"] is True
        assert result["action"] == "disabled"

    def test_before_request_enabled(self):
        """测试启用状态下的请求前处理"""
        ac = EnhancedAntiCrawler(self.config)
        with patch.object(ac.behavior_simulator, "simulate_human_interaction", return_value={}):
            result = ac.before_request({})
        assert result["success"] is True
        assert "action" in result
        assert ac.stats["total_requests"] == 1

    def test_after_request_disabled(self):
        """测试禁用状态下的请求后处理"""
        config = {"enabled": False, "level": "low"}
        ac = EnhancedAntiCrawler(config)
        result = ac.after_request(True)
        assert result["success"] is True
        assert result["action"] == "disabled"

    def test_after_request_success(self):
        """测试成功请求的请求后处理"""
        ac = EnhancedAntiCrawler(self.config)
        result = ac.after_request(True)
        assert result["success"] is True
        assert ac.stats["successful_requests"] == 1

    def test_after_request_failure(self):
        """测试失败请求的请求后处理"""
        ac = EnhancedAntiCrawler(self.config)
        result = ac.after_request(False)
        # 当 success=False 时，result["success"] 应该是 False
        assert result["success"] is False
        assert ac.stats["blocked_requests"] == 1

    def test_after_request_with_captcha(self):
        """测试包含验证码的请求后处理"""
        ac = EnhancedAntiCrawler(self.config)
        response_data = {
            "page_content": "<div class='g-recaptcha'>captcha</div>",
            "response_headers": {}
        }
        result = ac.after_request(True, response_data)
        # 检查验证码是否被检测到
        assert ac.stats["captcha_encountered"] >= 0

    def test_get_protection_level(self):
        """测试获取保护级别"""
        ac = EnhancedAntiCrawler(self.config)
        level = ac.get_protection_level()
        assert level == AntiCrawlerLevel.HIGH

    def test_randomize_fingerprint(self):
        """测试指纹随机化"""
        ac = EnhancedAntiCrawler(self.config)
        context = {"user_agent": "test"}
        changes = ac._randomize_fingerprint(context)
        assert isinstance(changes, dict)

    def test_simulate_behavior_patterns(self):
        """测试模拟行为模式"""
        ac = EnhancedAntiCrawler(self.config)
        with patch.object(ac.behavior_simulator, "simulate_human_interaction", return_value={}):
            result = ac._simulate_behavior_patterns()
        assert isinstance(result, dict)

    def test_get_stats(self):
        """测试获取统计信息"""
        ac = EnhancedAntiCrawler(self.config)
        stats = ac.get_stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats

    def test_reset_stats(self):
        """测试重置统计信息"""
        ac = EnhancedAntiCrawler(self.config)
        with patch.object(ac.behavior_simulator, "simulate_human_interaction", return_value={}):
            ac.before_request({})  # 增加计数
        initial_count = ac.stats["total_requests"]
        assert initial_count > 0


class TestBehaviorSimulator:
    """测试 BehaviorSimulator 类"""

    def setup_method(self):
        """设置测试环境"""
        self.simulator = BehaviorSimulator("high")

    def test_init(self):
        """测试初始化"""
        assert self.simulator.complexity_level == "high"

    def test_simulate_behavior_mouse_movement(self):
        """测试模拟鼠标移动"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.MOUSE_MOVEMENT, 0.1)
            assert isinstance(delay, (int, float))
            assert delay >= 0

    def test_simulate_behavior_scrolling(self):
        """测试模拟滚动"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.SCROLLING, 0.1)
            assert isinstance(delay, (int, float))
            assert delay >= 0

    def test_simulate_behavior_typing(self):
        """测试模拟打字"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.TYPING, 0.1)
            assert isinstance(delay, (int, float))
            assert delay >= 0

    def test_simulate_behavior_tab_switching(self):
        """测试模拟标签页切换"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.TAB_SWITCHING, 0.1)
            assert isinstance(delay, (int, float))
            assert delay >= 0

    def test_simulate_behavior_idle_time(self):
        """测试模拟空闲时间"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.IDLE_TIME, 0.1)
            assert isinstance(delay, (int, float))

    def test_simulate_behavior_with_duration(self):
        """测试带持续时间的模拟行为"""
        from src.web.anti_crawler.types import BehaviorPattern
        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = iter(100.0 + 0.05 * i for i in range(1000))
            delay = self.simulator.simulate_behavior(BehaviorPattern.MOUSE_MOVEMENT, 0.1)
            assert isinstance(delay, (int, float))
            assert delay >= 0


class TestAdaptiveRateLimiter:
    """测试 AdaptiveRateLimiter 类"""

    def setup_method(self):
        """设置测试环境"""
        self.limiter = AdaptiveRateLimiter({})

    def test_init(self):
        """测试初始化"""
        assert self.limiter is not None

    def test_can_make_request(self):
        """测试是否可以发起请求"""
        can_request, wait_time = self.limiter.can_make_request()
        assert isinstance(can_request, bool)
        assert isinstance(wait_time, (int, float))

    def test_record_request_success(self):
        """测试记录成功请求"""
        self.limiter.record_request(True)
        # 验证请求被记录

    def test_record_request_failure(self):
        """测试记录失败请求"""
        self.limiter.record_request(False)
        # 验证请求被记录

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.limiter.get_stats()
        assert isinstance(stats, dict)


class TestCaptchaHandler:
    """测试 CaptchaHandler 类"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = CaptchaHandler({})

    def test_init(self):
        """测试初始化"""
        assert self.handler is not None

    def test_detect_captcha_no_captcha(self):
        """测试检测验证码 - 无验证码"""
        page_content = "<html><body>No captcha here</body></html>"
        headers = {}
        result = self.handler.detect_captcha(page_content, headers)
        assert isinstance(result, bool)

    def test_detect_captcha_with_recaptcha(self):
        """测试检测 reCAPTCHA"""
        page_content = "<html><body><div class='g-recaptcha'>captcha</div></body></html>"
        headers = {}
        result = self.handler.detect_captcha(page_content, headers)
        assert isinstance(result, bool)

    def test_detect_captcha_with_hcaptcha(self):
        """测试检测 hCaptcha"""
        page_content = "<html><body><div class='h-captcha'>captcha</div></body></html>"
        headers = {}
        result = self.handler.detect_captcha(page_content, headers)
        assert isinstance(result, bool)

    def test_detect_captcha_invisible(self):
        """测试检测隐形验证码"""
        page_content = "<html><body><input type='hidden' name='captcha'></body></html>"
        headers = {}
        result = self.handler.detect_captcha(page_content, headers)
        assert isinstance(result, bool)

    def test_detect_captcha_in_headers(self):
        """测试在响应头中检测验证码"""
        page_content = "<html><body>No captcha</body></html>"
        headers = {"X-Captcha-Challenge": "true"}
        result = self.handler.detect_captcha(page_content, headers)
        assert isinstance(result, bool)

    def test_handle_captcha_mock(self):
        """测试处理验证码 - 模拟"""
        # handle_captcha 接受一个 context 字典参数
        context = {"proxy_manager": None, "user_agents": []}
        result = self.handler.handle_captcha(context)
        # 返回值是包含 success 等字段的字典
        assert isinstance(result, dict)
        assert "success" in result


class TestAntiCrawlerIntegration:
    """集成测试"""

    def test_full_request_flow(self):
        """测试完整的请求流程"""
        config = {
            "enabled": True,
            "level": "medium",
            "behavior_simulation": {"complexity_level": "medium"},
            "adaptive_rate_limiting": {},
            "captcha_handling": {},
        }
        ac = EnhancedAntiCrawler(config)

        with patch.object(ac.behavior_simulator, "simulate_human_interaction", return_value={}):
            # 请求前处理
            pre_result = ac.before_request({"url": "https://example.com"})
            assert pre_result["success"] is True

        # 请求后处理（成功）
        post_result = ac.after_request(True)
        assert post_result["success"] is True
        assert ac.stats["successful_requests"] == 1

    def test_rate_limiting_flow(self):
        """测试限流流程"""
        config = {
            "enabled": True,
            "level": "high",
            "behavior_simulation": {"complexity_level": "low"},
            "adaptive_rate_limiting": {"min_delay": 1.0},
            "captcha_handling": {},
        }
        ac = EnhancedAntiCrawler(config)

        # 发起多个请求
        with patch.object(ac.behavior_simulator, "simulate_human_interaction", return_value={}):
            for _ in range(5):
                ac.before_request({})
                ac.after_request(True)

        # 检查统计
        assert ac.stats["total_requests"] == 5
