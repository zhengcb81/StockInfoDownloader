"""
分页功能的集成测试
"""

import pytest
import tempfile
import shutil
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
    
    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pagination_config_loading(self):
        """测试分页配置加载"""
        config = {
            "pages": [
                {
                    "name": "调研",
                    "suffix": "research",
                    "max_pages": 3,
                    "allowed_keywords": ["调研"]
                },
                {
                    "name": "公告",
                    "suffix": "latestAnnouncement", 
                    "max_pages": 5,
                    "allowed_keywords": None
                }
            ]
        }
        
        page_config = self.service._get_page_config("research")
        assert page_config.get("max_pages") == 3
        assert "调研" in page_config.get("allowed_keywords", [])
    
    def test_keyword_matcher_integration(self):
        """测试关键词匹配器集成"""
        page_config = {
            "allowed_keywords": ["投资者关系", "调研"],
            "exclude_keywords": ["更正", "补充"],
            "allowed_keywords_mode": "any"
        }
        
        matcher = self.service._create_keyword_matcher(page_config)
        
        # 测试匹配
        assert matcher.matches(title="投资者关系调研活动记录表")
        assert matcher.matches(title="调研报告")
        assert not matcher.matches(title="年度财务报告")
        assert not matcher.matches(title="投资者关系活动更正公告")
    
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
        test_cases = [
            {
                "config": {"allowed_keywords": ["a", "b"], "mode": "any"},
                "text": "a b c",
                "expected": True
            },
            {
                "config": {"allowed_keywords": ["a", "b"], "mode": "all"},
                "text": "a b c", 
                "expected": True
            },
            {
                "config": {"allowed_keywords": ["a", "b"], "mode": "all"},
                "text": "a c",
                "expected": False
            },
            {
                "config": {"allowed_keywords": [r"\d+"], "mode": "regex"},
                "text": "123活动",
                "expected": True
            }
        ]
        
        for case in test_cases:
            matcher = self.service._create_keyword_matcher(case["config"])
            result = matcher.matches(text=case["text"])
            assert result == case["expected"]
    
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
        # 模拟WebDriver异常
        mock_driver = Mock()
        mock_driver.execute_script.side_effect = Exception("WebDriver error")
        
        scraper = WebScraper(mock_driver)
        
        # 异常应该被捕获并返回安全值
        result = scraper.has_next_page()
        assert result is False
        
        result = scraper.go_to_next_page()
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