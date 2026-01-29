"""
浏览器崩溃恢复测试

测试 UnifiedDownloader 在浏览器崩溃时的恢复能力
"""

import pytest
from unittest.mock import Mock, patch

from src.services.unified_downloader import UnifiedDownloader


class TestBrowserRecovery:
    """浏览器崩溃恢复测试"""

    def test_normal_operation_with_mock(self):
        """测试正常操作"""
        mock_strategy = Mock()
        mock_strategy.navigate.return_value = True
        mock_strategy.is_healthy.return_value = True

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        # 替换为 mock 策略
        downloader.browser_strategy = mock_strategy

        # 正常操作不应抛出异常
        assert downloader.browser_strategy is not None
        mock_strategy.navigate.assert_not_called()

    def test_browser_crash_recovery(self):
        """测试浏览器崩溃恢复"""
        mock_strategy = Mock()
        mock_strategy.is_healthy.return_value = False

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 清理不应抛出异常
        downloader.cleanup()
        mock_strategy.close.assert_called_once()

    def test_navigation_failure_handling(self):
        """测试导航失败处理"""
        mock_strategy = Mock()
        mock_strategy.navigate.return_value = False

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 导航失败应该返回 False
        result = downloader.browser_strategy.navigate("http://example.com")
        assert result is False

    def test_download_failure_handling(self):
        """测试下载失败处理"""
        mock_strategy = Mock()
        mock_strategy.download_file.return_value = None

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 下载失败应该返回 None
        result = downloader.browser_strategy.download_file("http://example.com/test.pdf", "test.pdf")
        assert result is None

    def test_element_not_found(self):
        """测试元素未找到"""
        mock_strategy = Mock()
        mock_strategy.find_element.return_value = None
        mock_strategy.find_elements.return_value = []

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 元素未找到应该返回 None
        result = downloader.browser_strategy.find_element("//div[@class='nonexistent']")
        assert result is None

        # find_elements 应该返回空列表
        results = downloader.browser_strategy.find_elements("//div[@class='nonexistent']")
        assert results == []

    def test_element_interaction(self):
        """测试元素交互"""
        mock_strategy = Mock()
        mock_element = {"id": "download", "text": "Download", "clicked": False}
        mock_strategy.find_element.return_value = mock_element
        mock_strategy.click.return_value = True

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 点击元素
        result = downloader.browser_strategy.click("//button[@id='download']")
        assert result is True

    def test_cleanup_on_error(self):
        """测试错误时的资源清理"""
        mock_strategy = Mock()

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 模拟操作
        downloader.browser_strategy.navigate("http://example.com")

        # 清理资源
        downloader.cleanup()

        # 验证浏览器已关闭
        mock_strategy.close.assert_called_once()

    def test_multiple_operations(self):
        """测试多次操作"""
        mock_strategy = Mock()
        mock_strategy.navigate.return_value = True
        mock_strategy.find_elements.return_value = [
            {"text": "PDF 1", "href": "http://example.com/1.pdf"},
            {"text": "PDF 2", "href": "http://example.com/2.pdf"},
        ]
        mock_strategy.download_file.side_effect = [
            "/tmp/downloads/1.pdf",
            "/tmp/downloads/2.pdf",
        ]

        config = {
            "save_dir": "/tmp/downloads",
            "browser_strategy": "playwright",
            "headless": True,
        }
        downloader = UnifiedDownloader(config)
        downloader.browser_strategy = mock_strategy

        # 执行多次操作
        assert downloader.browser_strategy.navigate("http://example.com") is True
        elements = downloader.browser_strategy.find_elements("//a[@class='pdf']")
        assert len(elements) == 2

        for elem in elements:
            result = downloader.browser_strategy.download_file(elem["href"], elem["text"] + ".pdf")
            assert result is not None

        assert downloader.browser_strategy.download_file.call_count == 2
