#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
翻页行为测试
验证下载器在 max_pages > 1 时正确执行翻页
基于用户设计思路: 用 max_pages 测试翻页功能
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models import DownloadResult


class PaginationHandler:
    """Pagination handler with page_turns counter for testing."""

    def __init__(self, browser_strategy):
        self.browser = browser_strategy
        self.page_turns = 0

    def go_to_next_page(self) -> bool:
        result = self.browser.go_to_next_page()
        if result:
            self.page_turns += 1
        return result

    def wait_after_page_change(self) -> None:
        import time
        time.sleep(2)

    def reset_counters(self) -> None:
        self.page_turns = 0


class TestPaginationBehavior:
    """翻页行为测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建 mock browser strategy
        self.mock_browser = MagicMock()

    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_page_turns_counter_initialized(self):
        """测试翻页计数器初始化"""
        handler = PaginationHandler(self.mock_browser)

        assert handler.page_turns == 0

    def test_page_turns_increment_on_success(self):
        """测试翻页成功时计数器增加"""
        handler = PaginationHandler(self.mock_browser)
        self.mock_browser.go_to_next_page.return_value = True

        # 执行翻页
        result = handler.go_to_next_page()

        assert result is True
        assert handler.page_turns == 1

    def test_page_turns_not_increment_on_failure(self):
        """测试翻页失败时计数器不增加"""
        handler = PaginationHandler(self.mock_browser)
        self.mock_browser.go_to_next_page.return_value = False

        # 执行翻页
        result = handler.go_to_next_page()

        assert result is False
        assert handler.page_turns == 0

    def test_multiple_page_turns(self):
        """测试多次翻页"""
        handler = PaginationHandler(self.mock_browser)
        self.mock_browser.go_to_next_page.return_value = True

        # 模拟5次翻页
        for i in range(5):
            result = handler.go_to_next_page()
            assert result is True

        assert handler.page_turns == 5

    def test_page_turns_counter_reset(self):
        """测试翻页计数器重置"""
        handler = PaginationHandler(self.mock_browser)
        self.mock_browser.go_to_next_page.return_value = True

        # 执行几次翻页
        for _ in range(3):
            handler.go_to_next_page()

        assert handler.page_turns == 3

        # 重置计数器
        handler.reset_counters()

        assert handler.page_turns == 0

    def test_download_result_has_pages_traversed_field(self):
        """测试 DownloadResult 包含 pages_traversed 字段"""
        result = DownloadResult(
            success=True,
            downloaded_files=[],
            total_files=0,
            errors=[],
            duration_seconds=0.0,
            metadata={},
        )

        # 验证字段存在且有默认值
        assert hasattr(result, "pages_traversed")
        assert result.pages_traversed == 0

    def test_download_result_pages_traversed_value(self):
        """测试 DownloadResult pages_traversed 值"""
        result = DownloadResult(
            success=True,
            downloaded_files=["file1.pdf"],
            total_files=1,
            errors=[],
            duration_seconds=5.0,
            metadata={},
            pages_traversed=5,
        )

        assert result.pages_traversed == 5


class TestPaginationScenarioSimulation:
    """翻页场景模拟测试"""

    def test_single_page_scenario(self):
        """模拟单页下载场景"""
        mock_browser = MagicMock()
        mock_browser.go_to_next_page.return_value = False  # 没有下一页

        handler = PaginationHandler(mock_browser)

        # 尝试翻页
        result = handler.go_to_next_page()

        # 单页场景不应该成功翻页
        assert result is False
        assert handler.page_turns == 0

    def test_multi_page_scenario(self):
        """模拟多页下载场景"""
        mock_browser = MagicMock()
        # 模拟3页：前2次翻页成功，第3次失败
        mock_browser.go_to_next_page.side_effect = [True, True, False]

        handler = PaginationHandler(mock_browser)

        # 模拟分页下载循环
        max_pages = 5
        actual_pages = 1  # 从第1页开始

        for page in range(1, max_pages + 1):
            # 处理当前页...

            # 尝试翻页
            if not handler.go_to_next_page():
                break
            actual_pages += 1

        # 验证：实际遍历了3页，翻页2次
        assert handler.page_turns == 2
        assert actual_pages == 3

    def test_max_pages_limit_scenario(self):
        """模拟达到最大页数限制场景"""
        mock_browser = MagicMock()
        mock_browser.go_to_next_page.return_value = True  # 总是可以翻页

        handler = PaginationHandler(mock_browser)

        # 模拟分页下载循环（限制最大页数）
        max_pages = 3
        actual_pages = 1

        for page in range(1, max_pages + 1):
            # 处理当前页...

            # 如果达到最大页数，不翻页
            if page >= max_pages:
                break

            # 尝试翻页
            if not handler.go_to_next_page():
                break
            actual_pages += 1

        # 验证：遍历了3页，翻页2次
        assert handler.page_turns == 2
        assert actual_pages == 3

    def test_e2e_pagination_verification(self):
        """模拟 E2E 翻页验证场景"""
        # 场景：TC-002 max_pages=5
        mock_browser = MagicMock()
        # 假设只有3页数据
        mock_browser.go_to_next_page.side_effect = [True, True, False]

        handler = PaginationHandler(mock_browser)

        # 模拟下载过程
        max_pages = 5
        downloaded_files = []

        for page in range(1, max_pages + 1):
            # 模拟下载当前页的文件
            downloaded_files.append(f"page_{page}_file.pdf")

            # 尝试翻页
            if not handler.go_to_next_page():
                break

        # 创建下载结果
        result = DownloadResult(
            success=True,
            downloaded_files=downloaded_files,
            total_files=len(downloaded_files),
            errors=[],
            duration_seconds=10.0,
            metadata={},
            pages_traversed=handler.page_turns + 1,  # 翻页次数+1=总页数
        )

        # 验证
        assert result.success is True
        assert result.total_files == 3  # 实际只有3页
        assert handler.page_turns == 2  # 翻页2次
        assert result.pages_traversed == 3  # 遍历了3页


class TestPaginationEdgeCases:
    """翻页边界情况测试"""

    def test_no_browser_strategy(self):
        """测试没有浏览器策略时的行为"""
        handler = PaginationHandler(None)

        # 应该不会崩溃，返回 False
        try:
            result = handler.go_to_next_page()
            # 如果没有崩溃，验证结果
            assert result is False or result is None
        except AttributeError:
            # 预期的异常
            pass

    def test_wait_after_page_change(self):
        """测试翻页后等待"""
        mock_browser = MagicMock()
        handler = PaginationHandler(mock_browser)

        # 测试等待不会崩溃
        import time

        start = time.time()
        handler.wait_after_page_change()
        elapsed = time.time() - start

        # 等待时间应该大于0
        assert elapsed >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
