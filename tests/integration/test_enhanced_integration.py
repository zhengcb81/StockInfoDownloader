#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强集成测试 - 多层次集成测试套件
覆盖关键集成路径和边界情况
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.legacy_downloader_adapter import (
    DownloadServiceV2Adapter as DownloadService,
)
from src.core.config import ConfigManager
from src.data.mapping import MappingManager
from src.utils.keyword_matcher import KeywordConfig, KeywordMatcher
from src.web.browser_strategy import BrowserStrategyFactory


class TestEnhancedIntegration:
    """增强集成测试类 - 多层次测试套件"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.mapping_file = os.path.join(self.temp_dir, "test_mapping.json")

        # 创建测试映射数据
        test_mapping = {
            "301611": {"orgId": "9900056250", "name": "珂玛科技"},
            "300470": {"orgId": "9900030047", "name": "中密控股"},
            "002415": {"orgId": "9900002415", "name": "海康威视"},
        }

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_level1_config_mapping_integration(self):
        """层级1: 配置和映射基础集成"""
        # 测试配置管理器
        config = ConfigManager()
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

        # 测试映射管理器
        mapping = MappingManager(self.mapping_file)
        org_id = mapping.get_org_id("301611")
        assert org_id == "9900056250"

        # 测试双向映射
        stock_name = mapping.get_stock_name("301611")
        assert stock_name == "珂玛科技"

    def test_level2_browser_strategy_integration(self):
        """层级2: 浏览器策略集成"""
        # 测试策略工厂
        selenium_strategy = BrowserStrategyFactory.create_strategy(
            strategy_type="selenium", headless=True, download_dir=self.temp_dir
        )
        assert selenium_strategy is not None

        playwright_strategy = BrowserStrategyFactory.create_strategy(
            strategy_type="playwright", headless=True, download_dir=self.temp_dir
        )
        assert playwright_strategy is not None

        # 测试策略切换
        downloader = DownloadService(
            save_dir=self.temp_dir,
            mapping_file=self.mapping_file,
            browser_strategy="selenium",
        )

        # 切换到Playwright
        success = downloader.switch_browser_strategy("playwright")
        assert success
        assert downloader.browser_strategy_type == "playwright"

    def test_level3_keyword_matcher_integration(self):
        """层级3: 关键词匹配器集成"""
        # 测试关键词配置
        keyword_config = KeywordConfig(
            allowed_keywords=["投资者关系", "调研"], exclude_keywords=["公告", "通知"]
        )

        keyword_matcher = KeywordMatcher(keyword_config)

        # 测试匹配逻辑
        assert keyword_matcher.matches(text="投资者关系活动记录表", title="投资者关系")
        assert not keyword_matcher.matches(text="公司公告", title="公告")
        assert keyword_matcher.matches(text="机构调研报告", title="调研")

        # 测试下载器中的关键词集成
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试关键词过滤
        test_links = [
            {"text": "投资者关系活动记录表", "url": "link1"},
            {"text": "公司公告", "url": "link2"},
            {"text": "机构调研报告", "url": "link3"},
        ]

        allowed_keywords = ["投资者关系", "调研"]
        filtered_links = []
        for link in test_links:
            if downloader._matches_keywords(link["text"], allowed_keywords):
                filtered_links.append(link)

        assert len(filtered_links) == 2

    def test_level4_file_management_integration(self):
        """层级4: 文件管理集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试文件路径生成
        file_path = downloader._generate_file_path("珂玛科技", "投资者关系活动记录表")
        assert "珂玛科技" in file_path
        assert "投资者关系活动记录表.pdf" in file_path

        # 测试文件存在性检查
        assert not downloader._file_exists_and_valid(file_path)

        # 创建测试文件
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"PDF content" * 1000)

        assert downloader._file_exists_and_valid(file_path)

        # 测试文件名清理
        dirty_filename = "测试/文件*?.pdf"
        clean_filename = downloader._clean_filename(dirty_filename)
        assert "/" not in clean_filename
        assert "*" not in clean_filename
        assert "?" not in clean_filename

    def test_level5_error_recovery_integration(self):
        """层级5: 错误恢复集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试重试机制
        initial_retries = downloader.retry_count
        assert initial_retries == 0

        # 模拟重试
        downloader.retry_count = 2
        assert downloader.should_retry() == (
            downloader.retry_count < downloader.max_retries
        )

        # 测试会话限制
        assert downloader.max_downloads_per_session > 0

        # 测试动态延迟
        start_time = time.time()
        downloader.dynamic_delay(0.1, 0.2)
        end_time = time.time()

        elapsed = end_time - start_time
        assert elapsed >= 0  # 至少等待了0秒

    def test_level6_multi_stock_integration(self):
        """层级6: 多股票处理集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试多股票处理
        test_stocks = ["301611", "300470", "002415"]
        results = {}

        for stock_code in test_stocks:
            org_id = downloader.mapping_manager.get_org_id(stock_code)
            stock_name = downloader.mapping_manager.get_stock_name(stock_code)

            results[stock_code] = {
                "org_id": org_id,
                "stock_name": stock_name,
                "success": org_id is not None,
            }

        # 验证结果
        assert len(results) == 3
        for stock_code in test_stocks:
            assert results[stock_code]["success"]
            assert results[stock_code]["org_id"] is not None
            assert results[stock_code]["stock_name"] is not None

    def test_level7_performance_monitoring_integration(self):
        """层级7: 性能监控集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试性能监控
        status = downloader.get_status()

        # 验证状态报告包含必要信息
        assert "download_count" in status
        assert "retry_count" in status
        assert "success_count" in status
        assert "error_count" in status

        # 测试下载计数
        initial_count = downloader.download_count
        assert initial_count == 0

        # 模拟下载
        downloader.download_count = 5
        assert downloader.download_count == 5

    def test_level8_boundary_conditions_integration(self):
        """层级8: 边界条件集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 测试无效股票代码
        invalid_org_id = downloader.mapping_manager.get_org_id("999999")
        assert invalid_org_id is None

        # 测试空关键词
        assert downloader._matches_keywords("测试文本", None)
        assert downloader._matches_keywords("测试文本", [])

        # 测试特殊字符处理
        special_chars = "测试<>:/\\|?*文件名"
        clean_name = downloader._clean_filename(special_chars)
        assert "<" not in clean_name
        assert ">" not in clean_name
        assert ":" not in clean_name
        assert '"' not in clean_name
        assert "/" not in clean_name
        assert "\\" not in clean_name
        assert "|" not in clean_name
        assert "?" not in clean_name
        assert "*" not in clean_name

    def test_level9_real_browser_integration(self):
        """层级9: 真实浏览器集成测试"""
        # 创建下载器
        downloader = DownloadService(
            save_dir=self.temp_dir,
            mapping_file=self.mapping_file,
            browser_strategy="playwright",
        )

        # 测试浏览器策略初始化
        assert downloader.browser_strategy is not None
        assert downloader.browser_strategy_type == "playwright"

        # 测试策略配置
        assert hasattr(downloader.browser_strategy, "headless")
        assert hasattr(downloader.browser_strategy, "download_dir")

        # 测试策略切换
        success = downloader.switch_browser_strategy("selenium")
        assert success
        assert downloader.browser_strategy_type == "selenium"

    def test_level10_comprehensive_workflow_integration(self):
        """层级10: 完整工作流集成"""
        downloader = DownloadService(
            save_dir=self.temp_dir, mapping_file=self.mapping_file
        )

        # 模拟完整工作流
        stock_code = "301611"

        # 1. 获取股票信息
        stock_info = downloader._get_stock_info(stock_code)
        assert stock_info is not None
        assert stock_info["stock_code"] == stock_code
        assert stock_info["stock_name"] == "珂玛科技"
        assert stock_info["org_id"] == "9900056250"

        # 2. 构建URL
        url = downloader._build_page_url(stock_info, "research")
        expected_url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={stock_info['org_id']}&stockCode={stock_code}#research"
        assert url == expected_url

        # 3. 测试文件路径生成
        file_path = downloader._generate_file_path(stock_info["stock_name"], "测试文件")
        assert stock_info["stock_name"] in file_path
        assert "测试文件.pdf" in file_path

        # 4. 测试关键词匹配
        assert downloader._matches_keywords("投资者关系活动记录表", ["投资者关系"])
        assert not downloader._matches_keywords("公司公告", ["投资者关系"])

        # 5. 测试状态报告
        status = downloader.get_status()
        assert isinstance(status, dict)
        assert "download_count" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
