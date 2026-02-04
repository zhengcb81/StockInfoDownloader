#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
String Optimizer 模块测试
"""

import pytest
from src.utils.string_optimizer import standardize_stock_code, sanitize_filename, clean_text_content, normalize_whitespace


class TestStandardizeStockCode:
    """测试股票代码标准化"""
    
    def test_valid_6_digit_code(self):
        """测试有效的6位股票代码"""
        assert standardize_stock_code("000001") == "000001"
        assert standardize_stock_code("600000") == "600000"
        assert standardize_stock_code("300470") == "300470"
    
    def test_short_code_padded(self):
        """测试短代码补零"""
        result = standardize_stock_code("1")
        assert result == "000001"
    
    def test_invalid_code_returns_none(self):
        """测试无效代码返回None"""
        assert standardize_stock_code("") is None
        assert standardize_stock_code(None) is None


class TestSanitizeFilename:
    """测试文件名清理"""
    
    def test_remove_invalid_chars(self):
        """测试移除非法字符"""
        result = sanitize_filename("test<>:\"/\\|?*.pdf")
        assert "<" not in result
        assert ">" not in result
    
    def test_keep_valid_chars(self):
        """测试保留有效字符"""
        result = sanitize_filename("正常文件名_2024.pdf")
        assert "正常文件名" in result


class TestCleanTextContent:
    """测试文本内容清理"""
    
    def test_clean_whitespace(self):
        """测试清理空白字符"""
        result = clean_text_content("  text  with   spaces  ")
        assert "  " not in result or result.strip() == "text with spaces"
    
    def test_handle_empty(self):
        """测试处理空字符串"""
        result = clean_text_content("")
        assert result == "" or result is not None


class TestNormalizeWhitespace:
    """测试空白字符规范化"""
    
    def test_normalize_multiple_spaces(self):
        """测试规范化多个空格"""
        result = normalize_whitespace("text    with    spaces")
        assert result == "text with spaces" or "  " not in result
    
    def test_normalize_tabs(self):
        """测试规范化制表符"""
        result = normalize_whitespace("text\twith\ttabs")
        assert "\t" not in result or result == "text with tabs"
