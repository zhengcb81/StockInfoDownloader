#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通用浏览器操作模块单元测试
"""

import pytest
from src.web.common_browser_ops import (
    CommonBrowserConfig,
    CommonBrowserOperations,
    BrowserConfigNormalizer,
    normalize_config_for_engine
)


class TestCommonBrowserConfig:
    """测试通用浏览器配置"""

    def test_get_base_args(self):
        """测试获取基础参数"""
        args = CommonBrowserConfig.get_base_args()
        assert isinstance(args, list)
        assert len(args) > 0
        assert '--no-sandbox' in args
        assert '--disable-dev-shm-usage' in args

    def test_get_default_user_agents(self):
        """测试获取默认User-Agent"""
        agents = CommonBrowserConfig.get_default_user_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert all('Mozilla' in agent for agent in agents)

    def test_get_random_user_agent(self):
        """测试获取随机User-Agent"""
        agent = CommonBrowserConfig.get_random_user_agent()
        assert isinstance(agent, str)
        assert 'Mozilla' in agent

        # 测试自定义User-Agent列表
        custom_agents = ['Agent1', 'Agent2']
        agent = CommonBrowserConfig.get_random_user_agent(custom_agents)
        assert agent in custom_agents

    def test_normalize_window_size(self):
        """测试窗口大小标准化"""
        # 字符串格式
        result = CommonBrowserConfig.normalize_window_size("1920,1080")
        assert result == {'width': 1920, 'height': 1080}

        # 字典格式
        result = CommonBrowserConfig.normalize_window_size({'width': 1280, 'height': 720})
        assert result == {'width': 1280, 'height': 720}

        # None格式
        result = CommonBrowserConfig.normalize_window_size(None)
        assert result == {'width': 1920, 'height': 1080}

        # 列表格式
        result = CommonBrowserConfig.normalize_window_size([1024, 768])
        assert result == {'width': 1024, 'height': 768}

    def test_normalize_timeout(self):
        """测试超时标准化"""
        # 秒数
        assert CommonBrowserConfig.normalize_timeout(60) == 60
        assert CommonBrowserConfig.normalize_timeout(180) == 180

        # 毫秒数（应该转换为秒）
        assert CommonBrowserConfig.normalize_timeout(30000) == 30
        assert CommonBrowserConfig.normalize_timeout(60000) == 60

        # None
        assert CommonBrowserConfig.normalize_timeout(None) == 180

    def test_build_selenium_preferences(self):
        """测试Selenium偏好设置"""
        prefs = CommonBrowserConfig.build_selenium_preferences("/tmp/downloads")
        assert 'download.default_directory' in prefs
        assert prefs['download.prompt_for_download'] is False
        assert prefs['plugins.always_open_pdf_externally'] is True

        # 无下载目录
        prefs = CommonBrowserConfig.build_selenium_preferences(None)
        assert prefs == {}

    def test_build_playwright_context_options(self):
        """测试Playwright上下文选项"""
        options = CommonBrowserConfig.build_playwright_context_options("/tmp/downloads")
        assert 'java_script_enabled' in options
        assert options['accept_downloads'] is True

        # 无下载目录
        options = CommonBrowserConfig.build_playwright_context_options(None)
        assert 'accept_downloads' not in options


class TestCommonBrowserOperations:
    """测试通用浏览器操作"""

    def setup_method(self):
        """设置测试环境"""
        # 创建mock策略
        self.mock_strategy = MockBrowserStrategy()
        self.common_ops = CommonBrowserOperations(self.mock_strategy)

    def test_find_and_click(self):
        """测试查找并点击"""
        result = self.common_ops.find_and_click("button", timeout=5)
        assert result is True

        # 测试失败情况
        self.mock_strategy.should_fail = True
        result = self.common_ops.find_and_click("button", timeout=5)
        assert result is False

    def test_get_element_text(self):
        """测试获取元素文本"""
        text = self.common_ops.get_element_text("div", timeout=5)
        assert text == "测试文本"

        # 测试失败情况
        self.mock_strategy.should_fail = True
        text = self.common_ops.get_element_text("div", timeout=5)
        assert text == ""

    def test_navigate_and_wait(self):
        """测试导航并等待"""
        result = self.common_ops.navigate_and_wait("https://example.com", timeout=5)
        assert result is True

        # 测试失败情况
        self.mock_strategy.should_fail = True
        result = self.common_ops.navigate_and_wait("https://example.com", timeout=5)
        assert result is False

    def test_get_elements_by_text(self):
        """测试根据文本获取元素"""
        elements = self.common_ops.get_elements_by_text("测试")
        assert len(elements) == 1

    def test_click_element_by_text(self):
        """测试根据文本点击元素"""
        result = self.common_ops.click_element_by_text("点击")
        assert result is True

    def test_wait_for_url_contains(self):
        """测试等待URL包含"""
        result = self.common_ops.wait_for_url_contains("example", timeout=2)
        assert result is True

    def test_is_element_visible(self):
        """测试元素是否可见"""
        result = self.common_ops.is_element_visible("div", timeout=5)
        assert result is True


class TestBrowserConfigNormalizer:
    """测试配置标准化器"""

    def test_normalize_for_selenium(self):
        """测试Selenium配置标准化"""
        config = {
            'window_size': '1280,720',
            'timeout': 60,
            'download_dir': '/tmp/downloads',
            'max_downloads_per_session': 5
        }

        result = BrowserConfigNormalizer.normalize_for_selenium(config)

        assert result['window_size'] == '1280,720'
        assert result['timeout'] == 60
        assert result['page_load_timeout'] == 60
        assert result['implicit_wait'] == 3  # 默认值
        assert result['download_dir'] == '/tmp/downloads'
        assert result['max_downloads_per_session'] == 5

    def test_normalize_for_playwright(self):
        """测试Playwright配置标准化"""
        config = {
            'window_size': {'width': 1280, 'height': 720},
            'timeout': 60,
            'download_dir': '/tmp/downloads',
            'max_downloads_per_session': 5
        }

        result = BrowserConfigNormalizer.normalize_for_playwright(config)

        assert result['window_size'] == {'width': 1280, 'height': 720}
        assert result['timeout'] == 60000  # 转换为毫秒
        assert result['download_dir'] == '/tmp/downloads'
        assert result['max_downloads_per_session'] == 5


class TestNormalizeConfigForEngine:
    """测试引擎配置标准化函数"""

    def test_selenium_engine(self):
        """测试Selenium引擎"""
        config = {'timeout': 90}
        result = normalize_config_for_engine('selenium', config)
        assert result['timeout'] == 90

    def test_playwright_engine(self):
        """测试Playwright引擎"""
        config = {'timeout': 90}
        result = normalize_config_for_engine('playwright', config)
        assert result['timeout'] == 90000  # 毫秒

    def test_invalid_engine(self):
        """测试无效引擎"""
        with pytest.raises(ValueError, match="不支持的引擎"):
            normalize_config_for_engine('invalid', {})


# Mock类用于测试
class MockBrowserStrategy:
    """模拟浏览器策略"""

    def __init__(self):
        self.should_fail = False

    def wait_for_element(self, selector, timeout, by="css"):
        if self.should_fail:
            return None
        return "mock_element"

    def click(self, element):
        if self.should_fail:
            return False
        return True

    def get_text(self, element):
        if self.should_fail:
            return ""
        return "测试文本"

    def navigate_to_page(self, url):
        if self.should_fail:
            return False
        return True

    def find_elements(self, selector, by="css"):
        return ["mock_element"]

    def get_current_url(self):
        return "https://example.com/test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])