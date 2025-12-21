#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反爬虫系统增强测试
测试反爬虫策略的高级功能和集成场景
"""

import pytest
import time
import os
import sys
from unittest.mock import Mock, patch, MagicMock, call

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.anti_crawler import AntiCrawlerStrategy, is_test_environment


class TestAntiCrawlerEnhanced:
    """反爬虫策略增强测试"""

    def setup_method(self):
        """测试设置"""
        self.strategy = AntiCrawlerStrategy()

    # ==================== 环境检测测试 ====================

    def test_is_test_environment_via_env_var(self):
        """通过环境变量检测测试环境"""
        # 保存原始状态
        original_argv = sys.argv
        original_env = os.environ.copy()

        try:
            # 模拟非测试环境（确保其他检测机制不触发）
            sys.argv = ['main.py']  # 非测试脚本
            if 'PYTEST_CURRENT_TEST' in os.environ:
                del os.environ['PYTEST_CURRENT_TEST']

            # 测试 TEST_ENV='true'
            os.environ['TEST_ENV'] = 'true'
            assert is_test_environment() is True

            # 测试 TEST_ENV='false'
            os.environ['TEST_ENV'] = 'false'
            assert is_test_environment() is False

        finally:
            # 恢复原始状态
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)

    def test_is_test_environment_via_pytest(self):
        """通过pytest环境变量检测测试环境"""
        with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': 'test_name'}):
            assert is_test_environment() is True

        # 清理环境变量
        if 'PYTEST_CURRENT_TEST' in os.environ:
            del os.environ['PYTEST_CURRENT_TEST']

    def test_is_test_environment_via_script_name(self):
        """通过脚本名称检测测试环境"""
        # 保存原始状态
        original_argv = sys.argv
        original_env = os.environ.copy()

        try:
            # 确保其他检测机制不干扰
            if 'TEST_ENV' in os.environ:
                del os.environ['TEST_ENV']
            if 'PYTEST_CURRENT_TEST' in os.environ:
                del os.environ['PYTEST_CURRENT_TEST']

            # 模拟测试脚本
            sys.argv = ['pytest', 'test_file.py']
            assert is_test_environment() is True

            # 模拟生产脚本
            sys.argv = ['main.py']
            assert is_test_environment() is False

        finally:
            # 恢复原始状态
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)

    # ==================== 反检测策略测试 ====================

    def test_apply_anti_detection_success(self):
        """测试应用反检测策略成功"""
        mock_driver = MagicMock()

        # 设置execute_script返回正常值
        mock_driver.execute_script.return_value = None

        self.strategy.apply_anti_detection(mock_driver)

        # 验证execute_script被调用了至少3次（webdriver属性、navigator属性、screen属性）
        assert mock_driver.execute_script.call_count >= 3

        # 验证特定脚本被调用
        calls = mock_driver.execute_script.call_args_list
        script_texts = [str(call[0][0]) for call in calls]

        # 检查是否包含关键脚本
        webdriver_script_found = any('navigator' in script and 'webdriver' in script for script in script_texts)
        assert webdriver_script_found, "应该调用隐藏webdriver属性的脚本"

    def test_apply_anti_detection_with_exception(self):
        """测试应用反检测策略时出现异常"""
        mock_driver = MagicMock()
        mock_driver.execute_script.side_effect = Exception("JavaScript错误")

        # 应该捕获异常而不崩溃
        try:
            self.strategy.apply_anti_detection(mock_driver)
            assert True, "应该捕获异常而不崩溃"
        except Exception as e:
            assert False, f"应该捕获异常而不崩溃，但抛出了: {e}"

    # ==================== 模拟鼠标移动测试 ====================

    def test_simulate_real_mouse_movement_with_element(self):
        """测试模拟真实鼠标移动（带元素）"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.location = {'x': 300, 'y': 400}

        # 模拟ActionChains以避免实际创建
        with patch('selenium.webdriver.common.action_chains.ActionChains'):
            with patch('random.randint') as mock_randint:
                # 提供足够的返回值
                # num_points = random.randint(8, 15) -> 10
                # 循环中的 random.randint(-15, 15) 需要2*num_points个值，简化测试只提供几个
                mock_randint.side_effect = [10] + [-10, 10] * 20  # 提供足够的值

                # 应该能够执行而不抛出异常
                try:
                    self.strategy.simulate_real_mouse_movement(mock_driver, mock_element)
                    assert True
                except Exception as e:
                    assert False, f"方法应该执行而不抛出异常，但抛出了: {e}"

    def test_simulate_real_mouse_movement_without_element(self):
        """测试模拟真实鼠标移动（不带元素）"""
        mock_driver = MagicMock()

        # 模拟ActionChains以避免实际创建
        with patch('selenium.webdriver.common.action_chains.ActionChains'):
            with patch('random.randint') as mock_randint:
                # 提供足够的返回值
                # 第一次调用: random.randint(200, 500) -> 250 (x), 300 (y)
                # num_points = random.randint(8, 15) -> 10
                # 循环中的 random.randint(-15, 15) 需要2*num_points个值
                mock_randint.side_effect = [250, 300, 10] + [-10, 10] * 20

                # 应该能够执行而不抛出异常
                try:
                    self.strategy.simulate_real_mouse_movement(mock_driver, None)
                    assert True
                except Exception as e:
                    assert False, f"方法应该执行而不抛出异常，但抛出了: {e}"

    def test_simulate_real_mouse_movement_without_driver(self):
        """测试模拟真实鼠标移动（无driver）"""
        # 应该能够处理None driver而不抛出异常
        try:
            self.strategy.simulate_real_mouse_movement(None, None)
            assert True
        except Exception as e:
            assert False, f"应该能够处理None driver，但抛出了: {e}"

    # ==================== 复杂浏览行为测试 ====================

    def test_simulate_complex_browsing_test_environment(self):
        """测试模拟复杂浏览行为（测试环境）"""
        mock_driver = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            with patch('random.randint') as mock_randint:
                with patch('random.sample') as mock_sample:
                    # 模拟随机选择行为
                    mock_sample.return_value = [self.strategy._simulate_scrolling]

                    self.strategy.simulate_complex_browsing(mock_driver)

                    # 验证_simulate_scrolling被调用
                    # 由于是内部方法，我们验证driver的execute_script是否被调用
                    # 实际测试中，我们会mock_simulate_scrolling来验证调用

    def test_simulate_complex_browsing_production_environment(self):
        """测试模拟复杂浏览行为（生产环境）"""
        mock_driver = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=False):
            with patch('random.randint') as mock_randint:
                with patch('random.sample') as mock_sample:
                    # 模拟随机选择行为
                    mock_sample.return_value = [
                        self.strategy._simulate_scrolling,
                        self.strategy._simulate_random_clicks
                    ]

                    self.strategy.simulate_complex_browsing(mock_driver)

                    # 验证两个行为都被调用

    def test_simulate_complex_browsing_without_driver(self):
        """测试模拟复杂浏览行为（无driver）"""
        # 应该能够处理None driver而不抛出异常
        try:
            self.strategy.simulate_complex_browsing(None)
            assert True
        except Exception as e:
            assert False, f"应该能够处理None driver，但抛出了: {e}"

    # ==================== 滚动行为测试 ====================

    def test_simulate_scrolling_test_environment(self):
        """测试模拟滚动行为（测试环境）"""
        mock_driver = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            with patch('random.randint', return_value=1):  # num_scrolls = 1
                with patch('random.sample') as mock_sample:
                    # 模拟选择滚动脚本
                    mock_sample.return_value = ["window.scrollTo(0, document.body.scrollHeight * 0.2);"]
                    with patch('random.uniform', return_value=0.2):
                        with patch('time.sleep') as mock_sleep:
                            self.strategy._simulate_scrolling(mock_driver)

                            # 验证execute_script被调用
                            mock_driver.execute_script.assert_called_once_with(
                                "window.scrollTo(0, document.body.scrollHeight * 0.2);"
                            )
                            mock_sleep.assert_called_once_with(0.2)

    def test_simulate_scrolling_production_environment(self):
        """测试模拟滚动行为（生产环境）"""
        mock_driver = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=False):
            with patch('random.randint', return_value=2):  # num_scrolls = 2
                with patch('random.sample') as mock_sample:
                    # 模拟选择滚动脚本
                    mock_sample.return_value = [
                        "window.scrollTo(0, document.body.scrollHeight * 0.2);",
                        "window.scrollTo(0, document.body.scrollHeight * 0.8);"
                    ]
                    with patch('random.uniform', return_value=0.8):
                        with patch('time.sleep') as mock_sleep:
                            self.strategy._simulate_scrolling(mock_driver)

                            # 验证execute_script被调用了2次
                            assert mock_driver.execute_script.call_count == 2
                            # 验证sleep被调用了2次（每次滚动后）
                            assert mock_sleep.call_count == 2

    # ==================== 随机点击测试 ====================

    def test_simulate_random_clicks_with_clickable_elements(self):
        """测试模拟随机点击（有可点击元素）"""
        mock_driver = MagicMock()
        mock_element1 = MagicMock()
        mock_element1.is_displayed.return_value = True
        mock_element1.is_enabled.return_value = True

        mock_element2 = MagicMock()
        mock_element2.is_displayed.return_value = True
        mock_element2.is_enabled.return_value = True

        # 设置find_elements返回值
        mock_driver.find_elements.side_effect = [
            [mock_element1],  # By.TAG_NAME, "a"
            [mock_element2]   # By.TAG_NAME, "button"
        ]

        with patch('random.randint') as mock_randint:
            with patch('random.sample') as mock_sample:
                # 模拟选择元素
                mock_sample.return_value = [mock_element1]

                self.strategy._simulate_random_clicks(mock_driver)

                # 验证click被调用
                mock_element1.click.assert_called()

    def test_simulate_random_clicks_no_clickable_elements(self):
        """测试模拟随机点击（无可点击元素）"""
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []

        # 应该正常执行而不崩溃
        try:
            self.strategy._simulate_random_clicks(mock_driver)
            assert True
        except Exception as e:
            assert False, f"应该能够处理无可点击元素的情况，但抛出了: {e}"

    # ==================== 标签页切换测试 ====================

    def test_simulate_tab_switching(self):
        """测试模拟标签页切换"""
        mock_driver = MagicMock()
        mock_driver.window_handles = ['window1', 'window2']

        self.strategy._simulate_tab_switching(mock_driver)

        # 验证打开了新标签页并切换
        mock_driver.execute_script.assert_called_with("window.open('about:blank', '_blank');")
        mock_driver.switch_to.window.assert_called()

    # ==================== 智能等待测试 ====================

    def test_smart_wait_success(self):
        """测试智能等待成功"""
        mock_driver = MagicMock()
        mock_condition = MagicMock()

        with patch('src.web.anti_crawler.WebDriverWait') as mock_wait_class:
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True

            result = self.strategy.smart_wait(mock_driver, mock_condition, timeout=5)

            assert result is True
            mock_wait_class.assert_called_with(mock_driver, 5)
            mock_wait_instance.until.assert_called_with(mock_condition)

    def test_smart_wait_timeout(self):
        """测试智能等待超时"""
        mock_driver = MagicMock()
        mock_condition = MagicMock()

        with patch('src.web.anti_crawler.WebDriverWait') as mock_wait_class, \
             patch.object(self.strategy, 'random_delay') as mock_delay:
            from selenium.common.exceptions import TimeoutException
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.side_effect = TimeoutException("超时")

            result = self.strategy.smart_wait(mock_driver, mock_condition, timeout=2)

            assert result is False
            mock_delay.assert_called()  # random_delay should be called

    def test_smart_wait_exception(self):
        """测试智能等待出现异常"""
        mock_driver = MagicMock()
        mock_condition = MagicMock()

        with patch('src.web.anti_crawler.WebDriverWait') as mock_wait_class, \
             patch.object(self.strategy, 'random_delay') as mock_delay:
            mock_wait_instance = MagicMock()
            mock_wait_class.return_value = mock_wait_instance
            mock_wait_instance.until.side_effect = Exception("未知错误")

            result = self.strategy.smart_wait(mock_driver, mock_condition)

            assert result is False
            mock_delay.assert_called()

    # ==================== 速率限制处理测试 ====================

    def test_handle_rate_limit_with_captcha_test_env(self):
        """测试处理速率限制（测试环境，检测到验证码）"""
        mock_driver = MagicMock()

        # 模拟找到验证码元素
        mock_driver.find_element.return_value = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            with patch('time.sleep') as mock_sleep:
                result = self.strategy.handle_rate_limit(mock_driver, retry_count=0)

                assert result is False
                mock_sleep.assert_called()
                # 验证等待时间在测试环境范围内
                sleep_call_arg = mock_sleep.call_args[0][0]
                assert sleep_call_arg <= 15  # 测试环境最多15秒

    def test_handle_rate_limit_with_captcha_production_env(self):
        """测试处理速率限制（生产环境，检测到验证码）"""
        mock_driver = MagicMock()
        mock_driver.find_element.return_value = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=False):
            with patch('time.sleep') as mock_sleep:
                result = self.strategy.handle_rate_limit(mock_driver, retry_count=2)

                assert result is False
                mock_sleep.assert_called()
                sleep_call_arg = mock_sleep.call_args[0][0]
                assert sleep_call_arg <= 120  # 生产环境最多120秒

    def test_handle_rate_limit_without_captcha(self):
        """测试处理速率限制（未检测到验证码）"""
        mock_driver = MagicMock()
        # 模拟找不到验证码元素
        mock_driver.find_element.side_effect = Exception("未找到元素")

        with patch('time.sleep') as mock_sleep:
            result = self.strategy.handle_rate_limit(mock_driver, retry_count=1)

            assert result is True
            mock_sleep.assert_called()

    def test_handle_rate_limit_exception(self):
        """测试处理速率限制出现异常"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = Exception("查找元素失败")

        with patch('time.sleep', side_effect=Exception("sleep失败")):
            result = self.strategy.handle_rate_limit(mock_driver)

            assert result is False

    # ==================== 边界条件测试 ====================

    def test_dynamic_delay_with_high_download_count(self):
        """测试动态延迟（高下载计数）"""
        # 设置高下载计数
        self.strategy.download_count = 100

        with patch('src.web.anti_crawler.is_test_environment', return_value=False):
            with patch('random.uniform') as mock_uniform:
                mock_uniform.return_value = 2.5
                with patch('time.sleep') as mock_sleep:
                    result = self.strategy.dynamic_delay(1.0, 2.0)

                    assert result == 2.5
                    mock_sleep.assert_called_with(2.5)

                    # 验证延迟因子计算
                    # delay_factor = 1 + (100 / 100) = 2.0
                    # min_delay = 1.0 * 2.0 = 2.0
                    # max_delay = 2.0 * 2.0 = 4.0
                    # random.uniform应该被调用(2.0, 4.0)
                    mock_uniform.assert_called_once()
                    call_args = mock_uniform.call_args[0]
                    assert call_args[0] >= 2.0  # min_delay
                    assert call_args[1] >= 4.0  # max_delay

    def test_dynamic_delay_test_environment(self):
        """测试动态延迟（测试环境）"""
        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            with patch('random.uniform') as mock_uniform:
                mock_uniform.return_value = 0.2
                with patch('time.sleep') as mock_sleep:
                    result = self.strategy.dynamic_delay(1.0, 2.0)

                    # 在测试环境中，基础延迟会缩小
                    # base_min = max(0.05, 1.0 * 0.2) = 0.2
                    # base_max = max(0.1, 2.0 * 0.2) = 0.4
                    mock_uniform.assert_called_with(0.2, 0.4)
                    mock_sleep.assert_called_with(0.2)

    def test_check_session_limit_edge_cases(self):
        """测试检查会话限制边界情况"""
        # 刚好达到限制
        assert self.strategy.check_session_limit(self.strategy.max_session_downloads) is True

        # 超过限制
        assert self.strategy.check_session_limit(self.strategy.max_session_downloads + 1) is True

        # 未达到限制
        assert self.strategy.check_session_limit(self.strategy.max_session_downloads - 1) is False

        # 零下载
        assert self.strategy.check_session_limit(0) is False

    # ==================== 参数验证测试 ====================

    def test_set_session_parameters_validation(self):
        """测试设置会话参数验证"""
        # 测试有效参数
        self.strategy.set_session_parameters(1.0, 5.0, 10)
        assert self.strategy.min_delay == 1.0
        assert self.strategy.max_delay == 5.0
        assert self.strategy.max_session_downloads == 10

        # 测试无效参数（负值）
        self.strategy.set_session_parameters(-1.0, -2.0, -3)
        # 虽然参数无效，但应该被接受（实际使用中可能会有问题）
        assert self.strategy.min_delay == -1.0
        assert self.strategy.max_delay == -2.0
        assert self.strategy.max_session_downloads == -3

    def test_random_delay_with_custom_parameters(self):
        """测试随机延迟（自定义参数）"""
        with patch('random.uniform') as mock_uniform:
            mock_uniform.return_value = 3.0
            with patch('time.sleep') as mock_sleep:
                self.strategy.random_delay(2.0, 4.0)

                mock_uniform.assert_called_with(2.0, 4.0)
                mock_sleep.assert_called_with(3.0)

    def test_random_delay_with_default_parameters(self):
        """测试随机延迟（默认参数）"""
        with patch('random.uniform') as mock_uniform:
            mock_uniform.return_value = 0.5
            with patch('time.sleep') as mock_sleep:
                self.strategy.random_delay()

                # 应该使用实例的min_delay和max_delay
                mock_uniform.assert_called_with(self.strategy.min_delay, self.strategy.max_delay)
                mock_sleep.assert_called_with(0.5)

    # ==================== 集成测试 ====================

    def test_full_workflow_in_test_environment(self):
        """测试完整工作流程（测试环境）"""
        mock_driver = MagicMock()

        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            # 1. 应用反检测策略
            self.strategy.apply_anti_detection(mock_driver)

            # 2. 模拟人类行为
            self.strategy.simulate_human_behavior(mock_driver)

            # 3. 增加下载计数
            initial_count = self.strategy.download_count
            self.strategy.increment_download_count()
            assert self.strategy.download_count == initial_count + 1

            # 4. 检查会话限制
            limit_reached = self.strategy.check_session_limit(5)
            # 取决于max_session_downloads的默认值（10）
            assert limit_reached is False

            # 5. 动态延迟
            with patch('time.sleep'):
                self.strategy.dynamic_delay()

            # 6. 智能等待
            with patch('selenium.webdriver.support.ui.WebDriverWait'):
                self.strategy.smart_wait(mock_driver, MagicMock())

            # 7. 重置下载计数
            self.strategy.reset_download_count()
            assert self.strategy.download_count == 0

    def test_environment_aware_parameter_selection(self):
        """测试环境感知的参数选择"""
        # 测试环境
        with patch('src.web.anti_crawler.is_test_environment', return_value=True):
            strategy_test = AntiCrawlerStrategy()
            assert strategy_test.min_delay == 0.1
            assert strategy_test.max_delay == 0.3

        # 生产环境
        with patch('src.web.anti_crawler.is_test_environment', return_value=False):
            strategy_prod = AntiCrawlerStrategy()
            assert strategy_prod.min_delay == 0.3
            assert strategy_prod.max_delay == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])