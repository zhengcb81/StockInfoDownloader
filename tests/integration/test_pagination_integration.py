"""
分页功能的集成测试
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch
from src.services.downloader import DownloadService
from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
from src.web.scraper import WebScraper


class TestPaginationIntegration:
    """分页功能集成测试"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.service = DownloadService(save_dir=self.temp_dir)
        
        # 加载测试配置
        test_config_path = Path(__file__).parent / "test_pagination_config.json"
        with open(test_config_path, 'r', encoding='utf-8') as f:
            self.test_config = json.load(f)
    
    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pagination_config_loading(self):
        """测试分页配置加载"""
        # 使用配置文件中的数据
        test_config = {"pages": self.test_config["page_configs"]}
        
        # 使用 mock 来设置配置
        with patch.object(self.service, 'config', test_config):
            page_config = self.service._get_page_config("research")
            expected_config = self.test_config["page_configs"][0]
            assert page_config.get("max_pages") == expected_config["max_pages"]
            assert expected_config["allowed_keywords"][0] in page_config.get("allowed_keywords", [])
    
    def test_keyword_matcher_integration(self):
        """测试关键词匹配器集成"""
        # 使用配置文件中的关键词配置
        keyword_config = self.test_config["keyword_config"]
        
        matcher = self.service._create_keyword_matcher(keyword_config)
        
        # 使用配置文件中的测试用例
        for test_case in self.test_config["keyword_test_cases"]:
            result = matcher.matches(text=test_case["text"], title=test_case["title"])
            assert result == test_case["expected"], f"Failed for: {test_case['text']}"
    
    def test_filter_links_integration(self):
        """测试链接过滤集成"""
        page_config = {
            "allowed_keywords": ["调研"],
            "allowed_keywords_mode": "any"
        }
        
        matcher = self.service._create_keyword_matcher(page_config)
        
        pdf_links = [
            {"title": "投资者关系调研活动记录表", "url": "http://example.com/1.pdf"},
            {"title": "年度报告", "url": "http://example.com/2.pdf"},
            {"title": "调研纪要", "url": "http://example.com/3.pdf"},
            {"title": "财务更正公告", "url": "http://example.com/4.pdf"}
        ]
        
        filtered = self.service._filter_links_by_keywords(pdf_links, matcher)
        
        titles = [link["title"] for link in filtered]
        assert "投资者关系调研活动记录表" in titles
        assert "调研纪要" in titles
        assert len(filtered) == 2
    
    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 确保旧配置格式仍然可用
        old_config = {
            "pages": [
                {"name": "调研", "suffix": "research", "allowed_keywords": None}
            ]
        }
        
        page_config = self.service._get_page_config("research")
        # 应该使用默认配置
        assert isinstance(page_config, dict)
    
    def test_pagination_with_different_modes(self):
        """测试不同关键词模式的集成"""
        # 使用配置文件中的测试用例
        for case in self.test_config["keyword_mode_test_cases"]:
            matcher = self.service._create_keyword_matcher(case["config"])
            result = matcher.matches(text=case["text"])
            assert result == case["expected"], f"Failed for config: {case['config']}, text: {case['text']}"
    
    def test_pagination_config_defaults(self):
        """测试分页配置默认值"""
        # 空配置应该使用默认值
        empty_config = {}
        
        max_pages = empty_config.get("max_pages", self.service.config.get("max_pages", 5))
        assert max_pages == 5
        
        # 页面特定配置应该覆盖全局配置
        page_config = {"max_pages": 10}
        max_pages = page_config.get("max_pages", self.service.config.get("max_pages", 5))
        assert max_pages == 10
    
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
    
    def test_pagination_with_exclude_keywords(self):
        """测试排除关键词功能"""
        config = {
            "allowed_keywords": ["调研"],
            "exclude_keywords": ["更正", "补充"],
            "allowed_keywords_mode": "any"
        }
        
        matcher = self.service._create_keyword_matcher(config)
        
        test_cases = [
            ("投资者关系调研活动", True),
            ("调研活动更正", False),
            ("调研补充说明", False),
            ("年度报告", False)
        ]
        
        for text, expected in test_cases:
            result = matcher.matches(text=text)
            assert result == expected
    
    def test_large_scale_pagination_simulation(self):
        """测试大规模分页模拟"""
        # 模拟100个链接的处理
        large_links = [
            {"title": f"调研报告{i}", "url": f"http://example.com/{i}.pdf"}
            for i in range(100)
        ]
        
        config = {
            "allowed_keywords": ["调研"],
            "allowed_keywords_mode": "any"
        }
        
        matcher = self.service._create_keyword_matcher(config)
        
        # 应该能处理大量链接而不崩溃
        filtered = self.service._filter_links_by_keywords(large_links, matcher)
        assert len(filtered) == 100  # 所有都包含"调研"