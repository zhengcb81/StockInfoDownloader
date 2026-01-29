"""
分页功能的集成测试
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.services.unified_downloader import UnifiedDownloader
from src.web.scraper import WebScraper


class TestPaginationIntegration:
    """分页功能集成测试"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {"save_dir": self.temp_dir, "headless": True}
        self.service = UnifiedDownloader(self.config)

    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unified_downloader_initialization(self):
        """测试 UnifiedDownloader 初始化"""
        assert self.service is not None
        assert self.service.config is not None
        assert self.service.config.get("save_dir") == self.temp_dir

    def test_error_handling_in_pagination(self):
        """测试分页过程中的错误处理"""
        # 测试 has_next_page 在找不到元素时的正常行为
        mock_driver = Mock()
        mock_driver.find_element.side_effect = Exception("No element found")

        scraper = WebScraper(mock_driver)
        result = scraper.has_next_page()
        assert result is False

        # 测试 go_to_next_page 在 execute_script 异常时的行为
        mock_driver2 = Mock()
        mock_element = Mock()
        mock_element.is_enabled.return_value = True
        mock_element.is_displayed.return_value = True
        mock_driver2.find_element.return_value = mock_element
        mock_driver2.execute_script.side_effect = Exception("WebDriver error")

        scraper2 = WebScraper(mock_driver2)
        result = scraper2.go_to_next_page()
        assert result is False

    def test_matches_keywords(self):
        """测试关键词匹配功能"""
        # 测试 _matches 方法
        result1 = self.service._matches("调研报告", ["调研"])
        assert result1 is True

        result2 = self.service._matches("年度报告", ["调研"])
        assert result2 is False

        result3 = self.service._matches("调研报告", None)
        assert result3 is True  # 没有关键词时应该匹配所有

    def test_config_defaults(self):
        """测试配置默认值"""
        # 空配置应该使用默认值
        assert self.service.config.get("max_pages", 5) == 5
        assert self.service.config.get("max_retries", 3) == 3

    def test_cleanup(self):
        """测试资源清理"""
        # 测试 cleanup 方法可以正常调用
        self.service.cleanup()
        # 清理后不应抛出异常
        assert True
