"""
DownloadService的单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.services.downloader import DownloadService
from src.data.models import StockInfo, DownloadRecord, DownloadStatus


class TestDownloadService:
    """测试DownloadService"""
    
    def test_init(self):
        """测试初始化"""
        service = DownloadService(save_dir="test_downloads")
        assert service.save_dir == Path("test_downloads")
    
    def test_get_page_config_found(self):
        """测试找到页面配置"""
        with patch('src.services.downloader.ConfigManager') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = [
                {"suffix": "research", "max_pages": 3},
                {"suffix": "reports", "max_pages": 5}
            ]
            mock_config.return_value = mock_config_instance
            
            service = DownloadService()
            config = service._get_page_config("research")
            assert config["max_pages"] == 3
    
    def test_get_page_config_not_found(self):
        """测试未找到页面配置"""
        with patch('src.services.downloader.ConfigManager') as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = []
            mock_config.return_value = mock_config_instance
            
            service = DownloadService()
            config = service._get_page_config("unknown")
            assert config == {}
    
    def test_create_keyword_matcher(self):
        """测试创建关键词匹配器"""
        page_config = {
            "allowed_keywords": ["调研"],
            "exclude_keywords": ["更正"],
            "allowed_keywords_mode": "any"
        }
        
        service = DownloadService()
        matcher = service._create_keyword_matcher(page_config)
        
        assert matcher is not None
    
    def test_filter_links_by_keywords(self):
        """测试关键词过滤"""
        from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
        
        config = KeywordConfig(
            allowed_keywords=["调研"],
            mode="any"
        )
        matcher = KeywordMatcher(config)
        
        service = DownloadService()
        
        pdf_links = [
            {"title": "投资者关系调研活动记录表"},
            {"title": "年度报告"},
            {"title": "调研报告"}
        ]
        
        filtered = service._filter_links_by_keywords(pdf_links, matcher)
        
        assert len(filtered) == 2
        titles = [link["title"] for link in filtered]
        assert "投资者关系调研活动记录表" in titles
        assert "调研报告" in titles
        assert "年度报告" not in titles
    
    def test_empty_filter_links(self):
        """测试空链接列表过滤"""
        from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
        
        config = KeywordConfig(allowed_keywords=["调研"])
        matcher = KeywordMatcher(config)
        
        service = DownloadService()
        filtered = service._filter_links_by_keywords([], matcher)
        
        assert filtered == []
    
    def test_keyword_matcher_exception_handling(self):
        """测试关键词匹配异常处理"""
        mock_matcher = Mock()
        mock_matcher.matches.side_effect = Exception("Test error")
        
        service = DownloadService()
        
        pdf_links = [{"title": "测试文档"}]
        filtered = service._filter_links_by_keywords(pdf_links, mock_matcher)
        
        # 异常时应该包含所有链接
        assert len(filtered) == 1
    
    def test_get_stock_info_with_preset_name(self):
        """测试使用预设股票名称"""
        with patch('src.services.downloader.StockService') as mock_stock_service, \
             patch('src.services.downloader.ConfigManager') as mock_config:
            
            mock_stock_instance = Mock()
            mock_stock_instance.get_stock_name.return_value = None
            mock_stock_service.return_value = mock_stock_instance
            
            mock_config_instance = Mock()
            mock_config_instance.get.side_effect = lambda key, default=None: {
                'preset_stock_names': {'000001': '平安银行'}
            }.get(key, default)
            mock_config.return_value = mock_config_instance
            
            mock_mapping = Mock()
            mock_mapping.get_org_id.return_value = "gssz0000001"
            
            service = DownloadService()
            service.mapping_manager = mock_mapping
            
            stock_info = service._get_stock_info("000001")
            assert stock_info is not None
            assert stock_info.stock_name == "平安银行"
    
    def test_get_stock_info_failed(self):
        """测试获取股票信息失败"""
        with patch('src.services.downloader.StockService') as mock_stock_service, \
             patch('src.services.downloader.ConfigManager') as mock_config:
            
            mock_stock_instance = Mock()
            mock_stock_instance.get_stock_name.return_value = None
            mock_stock_service.return_value = mock_stock_instance
            
            mock_config_instance = Mock()
            mock_config_instance.get.return_value = {}
            mock_config.return_value = mock_config_instance
            
            mock_mapping = Mock()
            mock_mapping.get_org_id.return_value = None
            
            service = DownloadService()
            service.mapping_manager = mock_mapping
            
            stock_info = service._get_stock_info("invalid")
            assert stock_info is None
    
    def test_cleanup_downloads(self):
        """测试清理下载文件"""
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            # 创建模拟文件
            mock_file1 = Mock()
            mock_file1.stat.return_value.st_mtime = 1234567890  # 旧文件
            mock_file2 = Mock()
            mock_file2.stat.return_value.st_mtime = 9999999999  # 新文件
            
            mock_glob.return_value = [mock_file1, mock_file2]
            
            service = DownloadService()
            cleaned = service.cleanup_downloads(days=30)
            
            # 应该清理1个旧文件
            assert cleaned == 1
            mock_unlink.assert_called_once_with(mock_file1)
    
    def test_cleanup_downloads_exception(self):
        """测试清理下载文件异常处理"""
        with patch('pathlib.Path.glob') as mock_glob:
            mock_glob.side_effect = Exception("Test error")
            
            service = DownloadService()
            cleaned = service.cleanup_downloads(days=30)
            
            assert cleaned == 0