#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强反爬虫测试
测试增强反爬虫机制的功能
"""

# 添加项目根目录到Python路径
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.web.anti_crawler_enhanced import AntiCrawlerLevel, EnhancedAntiCrawler


class TestEnhancedAntiCrawler:
    """测试增强反爬虫机制"""

    @pytest.fixture
    def anti_crawler_config(self):
        """反爬虫配置fixture"""
        return {
            "enabled": True,
            "level": "high",
            "fingerprint_randomization": {
                "user_agent_rotation": True,
                "screen_resolution": True,
                "timezone": True,
                "language": True,
            },
            "behavior_simulation": {
                "complexity_level": "high",
                "randomization_factor": 0.3,
                "patterns": ["mouse_movement", "scrolling", "typing"],
            },
            "adaptive_rate_limiting": {
                "initial_requests_per_minute": 30,
                "max_requests_per_minute": 100,
                "adjustment_factor": 1.2,
            },
            "captcha_handling": {
                "strategies": ["delay_retry", "proxy_rotation"],
                "max_wait_time": 120,
            },
        }

    def test_anti_crawler_initialization(self, anti_crawler_config):
        """测试反爬虫初始化"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)
        assert anti_crawler is not None
        assert anti_crawler.enabled is True
        assert anti_crawler.level == AntiCrawlerLevel.HIGH

    def test_before_request(self, anti_crawler_config):
        """测试请求前处理"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        context = {
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            ]
        }

        result = anti_crawler.before_request(context)
        assert result["success"] is True
        assert "fingerprint_changes" in result
        assert "behavior_simulation" in result

    def test_after_request(self, anti_crawler_config):
        """测试请求后处理"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        response_data = {
            "page_content": "正常页面内容",
            "response_headers": {"content-type": "text/html"},
        }

        result = anti_crawler.after_request(True, response_data)
        assert result["success"] is True
        assert "stats" in result

    def test_captcha_detection(self, anti_crawler_config):
        """测试验证码检测"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        # 测试正常页面
        normal_content = "这是一个正常的页面"
        assert not anti_crawler.captcha_handler.detect_captcha(normal_content)

        # 测试包含验证码的页面
        captcha_content = "请输入验证码以继续"
        assert anti_crawler.captcha_handler.detect_captcha(captcha_content)

    def test_rate_limiting(self, anti_crawler_config):
        """测试速率限制"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        # 记录一些成功请求
        for i in range(10):
            anti_crawler.rate_limiter.record_request(True)

        # 检查是否可以继续请求
        can_request, wait_time = anti_crawler.rate_limiter.can_make_request()
        assert can_request is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
