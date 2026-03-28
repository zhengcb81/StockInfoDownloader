#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DownloadHelper 单元测试
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.services.download_helper import PlaywrightDownloadHelper, SeleniumDownloadHelper


class TestPlaywrightDownloadHelper:
    """测试 PlaywrightDownloadHelper 类"""

    def test_download_from_detail_page_success(self):
        """测试成功下载"""
        mock_strategy = MagicMock()
        mock_strategy.download_file.return_value = True
        
        helper = PlaywrightDownloadHelper(mock_strategy)
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is True
        mock_strategy.download_file.assert_called_once()

    def test_download_from_detail_page_failure(self):
        """测试下载失败"""
        mock_strategy = MagicMock()
        mock_strategy.download_file.return_value = False
        
        helper = PlaywrightDownloadHelper(mock_strategy)
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is False

    def test_download_from_detail_page_no_method(self):
        """测试策略不支持 download_file 方法"""
        mock_strategy = object()  # 没有 download_file 方法
        
        helper = PlaywrightDownloadHelper(mock_strategy)
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is False

    def test_download_from_detail_page_exception(self):
        """测试下载过程中的异常"""
        mock_strategy = MagicMock()
        mock_strategy.download_file.side_effect = Exception("Test error")
        
        helper = PlaywrightDownloadHelper(mock_strategy)
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is False


class TestSeleniumDownloadHelper:
    """测试 SeleniumDownloadHelper 类"""

    def test_init(self):
        """测试初始化"""
        mock_strategy = MagicMock()
        helper = SeleniumDownloadHelper(mock_strategy, "/tmp/downloads")
        assert helper.download_dir == "/tmp/downloads"

    def test_download_from_detail_page_success(self):
        """测试成功下载"""
        mock_strategy = MagicMock()
        mock_strategy.download_file.return_value = True
        
        helper = SeleniumDownloadHelper(mock_strategy, "/tmp/downloads")
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is True
        mock_strategy.download_file.assert_called_once()

    def test_download_from_detail_page_exception(self):
        """测试下载过程中的异常"""
        mock_strategy = MagicMock()
        mock_strategy.download_file.side_effect = Exception("Test error")
        
        helper = SeleniumDownloadHelper(mock_strategy, "/tmp/downloads")
        result = helper.download_from_detail_page("http://example.com/file.pdf", "/tmp/file.pdf")
        
        assert result is False
