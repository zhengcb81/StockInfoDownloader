"""
DownloadService的单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.adapters.legacy_downloader_adapter import DownloadServiceV2Adapter as DownloadService
from src.interfaces.downloader_interface import DownloadResult as DownloadRecord, DownloadStatus


class TestDownloadService:
    """测试DownloadService"""
    
    def test_init(self):
        """测试初始化"""
        service = DownloadService(save_dir="test_downloads")
        assert service.save_dir == Path("test_downloads")
    
    def test_config_access(self):
        """测试配置访问"""
        with patch('src.core.config.ConfigManager') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = [
                {"suffix": "research", "max_pages": 3},
                {"suffix": "reports", "max_pages": 5}
            ]
            mock_config.return_value = mock_config_instance

            service = DownloadService()
            # 测试可以访问配置
            assert service.config is not None
            assert hasattr(service.config, 'get')
    
    def test_keyword_matching_integration(self):
        """测试关键词匹配集成"""
        from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig

        # 测试关键词匹配配置
        config = KeywordConfig(
            allowed_keywords=["调研"],
            exclude_keywords=["更正"]
        )

        matcher = KeywordMatcher(config)

        # 测试匹配
        result1 = matcher.matches("投资者关系调研活动记录表", "投资者关系调研活动记录表")
        result2 = matcher.matches("年度报告更正版", "年度报告更正版")

        assert result1 is True
        assert result2 is False
    
    def test_stock_info_methods(self):
        """测试股票信息相关方法"""
        with patch('src.data.mapping.MappingManager') as mock_mapping:
            mock_mapping_instance = Mock()
            mock_mapping_instance.get_org_id.return_value = "gssz0000001"
            mock_mapping_instance.get_stock_name.return_value = "测试公司"
            mock_mapping.return_value = mock_mapping_instance

            service = DownloadService()

            # 测试获取股票信息
            stock_info = service._get_stock_info("000001")
            assert stock_info is not None
            assert stock_info['stock_code'] == "000001"
            assert stock_info['stock_name'] == "测试公司"
            assert stock_info['org_id'] == "gssz0000001"

    def test_browser_strategy_initialization(self):
        """测试浏览器策略初始化"""
        service = DownloadService()

        # 验证浏览器策略已初始化
        assert service.browser_strategy is not None
        assert service.browser_strategy_type in ['selenium', 'playwright']

    def test_anti_crawler_configuration(self):
        """测试反爬虫配置"""
        service = DownloadService()

        # 验证反爬虫配置
        assert service.anti_crawler is not None
        assert service.max_downloads_per_session > 0
        assert service.max_retries > 0