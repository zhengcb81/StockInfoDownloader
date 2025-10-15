#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反爬虫系统基础测试
测试反爬虫策略的基本功能
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.anti_crawler import AntiCrawlerStrategy


class TestAntiCrawlerStrategy:
    """反爬虫策略测试"""

    def setup_method(self):
        """测试设置"""
        self.strategy = AntiCrawlerStrategy()

    def test_anti_crawler_initialization(self):
        """测试反爬虫策略初始化"""
        assert self.strategy is not None
        assert hasattr(self.strategy, '_user_agents')
        assert hasattr(self.strategy, 'min_delay')
        assert hasattr(self.strategy, 'max_delay')
        assert hasattr(self.strategy, 'download_count')

    def test_user_agents_exist(self):
        """测试用户代理列表存在"""
        assert hasattr(self.strategy, '_user_agents')
        assert isinstance(self.strategy._user_agents, list)
        assert len(self.strategy._user_agents) > 0
        assert all(isinstance(agent, str) for agent in self.strategy._user_agents)

    def test_delay_parameters(self):
        """测试延迟参数"""
        # 验证延迟参数在合理范围内
        assert self.strategy.min_delay > 0
        assert self.strategy.max_delay > 0
        assert self.strategy.min_delay <= self.strategy.max_delay

    def test_simulate_human_behavior_with_driver(self):
        """测试模拟人类行为（带driver）"""
        mock_driver = MagicMock()

        # 测试模拟行为
        self.strategy.simulate_human_behavior(mock_driver)

        # 验证driver方法被调用
        mock_driver.execute_script.assert_called()

    def test_simulate_human_behavior_without_driver(self):
        """测试模拟人类行为（不带driver）"""
        # 测试不带driver的情况 - 应该能够处理None driver而不抛出异常
        try:
            self.strategy.simulate_human_behavior(None)
            # 如果没有抛出异常，测试通过
            assert True
        except Exception as e:
            # 如果抛出异常，测试失败
            assert False, f"模拟人类行为应该能够处理None driver，但抛出了异常: {e}"

    def test_increment_download_count(self):
        """测试增加下载计数"""
        initial_count = self.strategy.download_count

        self.strategy.increment_download_count()

        # 验证计数增加
        assert self.strategy.download_count == initial_count + 1

    def test_reset_download_count(self):
        """测试重置下载计数"""
        # 先增加一些计数
        self.strategy.increment_download_count()
        self.strategy.increment_download_count()

        # 重置计数
        self.strategy.reset_download_count()

        # 验证计数被重置
        assert self.strategy.download_count == 0

    def test_check_session_limit(self):
        """测试检查会话限制"""
        # 测试不同下载计数下的限制判断
        self.strategy.reset_download_count()

        # 初始状态不应该达到限制
        assert not self.strategy.check_session_limit(0)
        assert not self.strategy.check_session_limit(self.strategy.max_session_downloads - 1)

        # 达到限制时应该返回True
        assert self.strategy.check_session_limit(self.strategy.max_session_downloads)
        assert self.strategy.check_session_limit(self.strategy.max_session_downloads + 1)

    def test_random_delay_method(self):
        """测试随机延迟方法"""
        start_time = time.time()
        self.strategy.random_delay(0.01, 0.02)  # 使用很小的延迟进行测试
        end_time = time.time()

        # 验证有延迟发生
        assert end_time - start_time > 0

    def test_dynamic_delay_method(self):
        """测试动态延迟方法"""
        start_time = time.time()
        self.strategy.dynamic_delay(0.01, 0.02)  # 使用很小的延迟进行测试
        end_time = time.time()

        # 验证有延迟发生
        assert end_time - start_time > 0

    def test_set_session_parameters(self):
        """测试设置会话参数"""
        # 设置新的参数
        new_min_delay = 2.0
        new_max_delay = 6.0
        new_max_downloads = 8

        self.strategy.set_session_parameters(new_min_delay, new_max_delay, new_max_downloads)

        # 验证参数已更新
        assert self.strategy.min_delay == new_min_delay
        assert self.strategy.max_delay == new_max_delay
        assert self.strategy.max_session_downloads == new_max_downloads

    def test_error_handling_in_simulation(self):
        """测试模拟行为中的错误处理"""
        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = Exception("JavaScript错误")

        # 应该能够处理JavaScript错误而不崩溃
        try:
            self.strategy.simulate_human_behavior(mock_driver)
            # 如果没有异常抛出，测试通过
            assert True
        except Exception:
            # 如果有异常，测试失败
            assert False, "模拟行为应该能够处理JavaScript错误"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])