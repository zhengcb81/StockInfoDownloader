#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期待数据验证器的单元测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.validation.expected_data_validator import (
    ExpectedDataValidator, 
    ComparisonMode, 
    FileComparisonResult, 
    DirectoryComparisonResult, 
    ValidationResult,
    validate_expected_vs_actual,
    validate_test_case
)


class TestExpectedDataValidator:
    """期待数据验证器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.expected_dir = Path(self.temp_dir) / "expected"
        self.actual_dir = Path(self.temp_dir) / "actual"
        
        # 创建测试目录结构
        self.expected_dir.mkdir(parents=True, exist_ok=True)
        self.actual_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = ExpectedDataValidator()
    
    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_calculate_file_hash(self):
        """测试文件哈希计算"""
        # 创建测试文件
        test_file = self.expected_dir / "test.txt"
        test_content = b"Hello, World!"
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # 计算哈希
        hash_result = self.validator.calculate_file_hash(test_file)
        
        # 验证哈希值（已知的MD5值）
        import hashlib
        expected_hash = hashlib.md5(test_content).hexdigest()
        
        assert hash_result == expected_hash
        assert len(hash_result) == 32  # MD5哈希长度
    
    def test_calculate_file_hash_nonexistent(self):
        """测试不存在的文件哈希计算"""
        nonexistent_file = self.expected_dir / "nonexistent.txt"
        
        hash_result = self.validator.calculate_file_hash(nonexistent_file)
        
        assert hash_result == ""
    
    def test_compare_files_content_identical(self):
        """测试相同文件内容比较"""
        # 创建两个相同的文件
        file1 = self.expected_dir / "file1.txt"
        file2 = self.actual_dir / "file2.txt"
        
        test_content = b"Test content for comparison"
        
        with open(file1, 'wb') as f:
            f.write(test_content)
        with open(file2, 'wb') as f:
            f.write(test_content)
        
        result = self.validator.compare_files_content(file1, file2)
        
        assert result is True
    
    def test_compare_files_content_different(self):
        """测试不同文件内容比较"""
        # 创建两个不同的文件
        file1 = self.expected_dir / "file1.txt"
        file2 = self.actual_dir / "file2.txt"
        
        with open(file1, 'wb') as f:
            f.write(b"Content 1")
        with open(file2, 'wb') as f:
            f.write(b"Content 2")
        
        result = self.validator.compare_files_content(file1, file2)
        
        assert result is False
    
    def test_compare_files_content_different_sizes(self):
        """测试不同大小文件比较"""
        # 创建两个大小不同的文件
        file1 = self.expected_dir / "file1.txt"
        file2 = self.actual_dir / "file2.txt"
        
        with open(file1, 'wb') as f:
            f.write(b"Longer content")
        with open(file2, 'wb') as f:
            f.write(b"Short")
        
        result = self.validator.compare_files_content(file1, file2)
        
        assert result is False
    
    def test_compare_file_both_exist(self):
        """测试两个文件都存在时的比较"""
        # 创建相同的文件
        expected_file = self.expected_dir / "test.pdf"
        actual_file = self.actual_dir / "test.pdf"
        
        test_content = b"PDF content for testing"
        
        with open(expected_file, 'wb') as f:
            f.write(test_content)
        with open(actual_file, 'wb') as f:
            f.write(test_content)
        
        result = self.validator.compare_file(expected_file, actual_file)
        
        assert result.expected_exists is True
        assert result.actual_exists is True
        assert result.size_match is True
        assert result.hash_match is True
        assert result.content_match is True
        assert result.is_match() is True
    
    def test_compare_file_expected_missing(self):
        """测试期待文件不存在时的比较"""
        # 只有实际文件存在
        expected_file = self.expected_dir / "missing.pdf"
        actual_file = self.actual_dir / "actual.pdf"
        
        with open(actual_file, 'wb') as f:
            f.write(b"Actual content")
        
        result = self.validator.compare_file(expected_file, actual_file)
        
        assert result.expected_exists is False
        assert result.actual_exists is True
        assert result.is_match() is False
        assert "期待文件不存在" in result.error_message
    
    def test_compare_file_actual_missing(self):
        """测试实际文件不存在时的比较"""
        # 只有期待文件存在
        expected_file = self.expected_dir / "expected.pdf"
        actual_file = self.actual_dir / "missing.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(b"Expected content")
        
        result = self.validator.compare_file(expected_file, actual_file)
        
        assert result.expected_exists is True
        assert result.actual_exists is False
        assert result.is_match() is False
        assert "实际文件不存在" in result.error_message
    
    def test_compare_directories_identical(self):
        """测试相同目录比较"""
        # 创建相同的目录结构
        company_dir = "测试公司"
        
        expected_company_dir = self.expected_dir / company_dir
        actual_company_dir = self.actual_dir / company_dir
        
        expected_company_dir.mkdir(parents=True, exist_ok=True)
        actual_company_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建相同的文件
        file_content = b"Test PDF content"
        
        expected_file = expected_company_dir / "文件1.pdf"
        actual_file = actual_company_dir / "文件1.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(file_content)
        with open(actual_file, 'wb') as f:
            f.write(file_content)
        
        result = self.validator.compare_directories(expected_company_dir, actual_company_dir)
        
        assert result.expected_exists is True
        assert result.actual_exists is True
        assert result.file_count_match is True
        assert result.file_list_match is True
        assert result.structure_match is True
        assert len(result.file_comparisons) == 1
        assert result.is_match() is True
    
    def test_validate_expected_data_success(self):
        """测试成功的期待数据验证"""
        # 创建相同的目录结构
        company_name = "中密控股"
        
        expected_company_dir = self.expected_dir / company_name
        actual_company_dir = self.actual_dir / company_name
        
        expected_company_dir.mkdir(parents=True, exist_ok=True)
        actual_company_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建相同的PDF文件
        file_content = b"PDF content for testing"
        
        expected_file = expected_company_dir / "中密控股：2025年一季度报告.pdf"
        actual_file = actual_company_dir / "中密控股：2025年一季度报告.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(file_content)
        with open(actual_file, 'wb') as f:
            f.write(file_content)
        
        result = self.validator.validate_expected_data(self.expected_dir, self.actual_dir)
        
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_matched == 1
        assert result.files_mismatched == 0
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert len(result.error_messages) == 0
        assert result.success_rate == 100.0
    
    def test_validate_expected_data_missing_expected_dir(self):
        """测试期待目录不存在的情况"""
        nonexistent_dir = Path("/nonexistent/expected")
        
        result = self.validator.validate_expected_data(nonexistent_dir, self.actual_dir)
        
        assert result.overall_success is False
        assert "期待数据目录不存在" in result.error_messages[0]
    
    def test_validate_expected_data_missing_actual_dir(self):
        """测试实际目录不存在的情况"""
        nonexistent_dir = Path("/nonexistent/actual")
        
        result = self.validator.validate_expected_data(self.expected_dir, nonexistent_dir)
        
        assert result.overall_success is False
        assert "实际数据目录不存在" in result.error_messages[0]
    
    def test_validate_single_test_case_success(self):
        """测试单个测试用例验证成功"""
        # 创建测试数据
        stock_code = "300470"
        company_name = "中密控股"
        
        expected_company_dir = self.expected_dir / company_name
        actual_company_dir = self.actual_dir / company_name
        
        expected_company_dir.mkdir(parents=True, exist_ok=True)
        actual_company_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建包含股票代码的文件
        file_content = b"Test PDF content"
        
        expected_file = expected_company_dir / f"中密控股：{stock_code}2025年一季度报告.pdf"
        actual_file = actual_company_dir / f"中密控股：{stock_code}2025年一季度报告.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(file_content)
        with open(actual_file, 'wb') as f:
            f.write(file_content)
        
        test_case = {
            "stock_code": stock_code,
            "suffix": "research",
            "allowed_keywords": ["一季度报告"]
        }
        
        result = self.validator.validate_single_test_case(
            test_case, self.expected_dir, self.actual_dir
        )
        
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_matched == 1
        assert len(result.directory_results) == 1
    
    def test_validate_single_test_case_missing_stock_code(self):
        """测试缺少股票代码的测试用例"""
        test_case = {
            "suffix": "research",
            "allowed_keywords": ["一季度报告"]
        }
        
        result = self.validator.validate_single_test_case(
            test_case, self.expected_dir, self.actual_dir
        )
        
        assert result.overall_success is False
        assert "测试用例缺少股票代码" in result.error_messages[0]
    
    def test_validate_single_test_case_no_expected_data(self):
        """测试没有对应期待数据的测试用例"""
        test_case = {
            "stock_code": "999999",  # 不存在的股票代码
            "suffix": "research"
        }
        
        result = self.validator.validate_single_test_case(
            test_case, self.expected_dir, self.actual_dir
        )
        
        assert result.overall_success is False
        assert "未找到股票代码 999999 对应的期待数据" in result.error_messages[0]


class TestComparisonModes:
    """比较模式测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.expected_dir = Path(self.temp_dir) / "expected"
        self.actual_dir = Path(self.temp_dir) / "actual"
        
        self.expected_dir.mkdir(parents=True, exist_ok=True)
        self.actual_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_strict_mode(self):
        """测试严格模式"""
        validator = ExpectedDataValidator(ComparisonMode.STRICT)
        
        # 创建相同的文件
        expected_file = self.expected_dir / "test.pdf"
        actual_file = self.actual_dir / "test.pdf"
        
        content = b"Identical content"
        
        with open(expected_file, 'wb') as f:
            f.write(content)
        with open(actual_file, 'wb') as f:
            f.write(content)
        
        result = validator.compare_file(expected_file, actual_file)
        
        assert result.content_match is True  # 严格模式会进行内容比较
    
    def test_lenient_mode(self):
        """测试宽松模式"""
        validator = ExpectedDataValidator(ComparisonMode.LENIENT)
        
        # 创建相同的文件
        expected_file = self.expected_dir / "test.pdf"
        actual_file = self.actual_dir / "test.pdf"
        
        content = b"Identical content"
        
        with open(expected_file, 'wb') as f:
            f.write(content)
        with open(actual_file, 'wb') as f:
            f.write(content)
        
        result = validator.compare_file(expected_file, actual_file)
        
        # 宽松模式下假设内容匹配
        assert result.content_match is True
    
    def test_content_only_mode(self):
        """测试仅内容模式"""
        validator = ExpectedDataValidator(ComparisonMode.CONTENT_ONLY)
        
        # 创建相同的文件
        expected_file = self.expected_dir / "test.pdf"
        actual_file = self.actual_dir / "test.pdf"
        
        content = b"Identical content"
        
        with open(expected_file, 'wb') as f:
            f.write(content)
        with open(actual_file, 'wb') as f:
            f.write(content)
        
        result = validator.compare_file(expected_file, actual_file)
        
        assert result.content_match is True  # 仅内容模式会进行内容比较


class TestConvenienceFunctions:
    """便捷函数测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.expected_dir = Path(self.temp_dir) / "expected"
        self.actual_dir = Path(self.temp_dir) / "actual"
        
        self.expected_dir.mkdir(parents=True, exist_ok=True)
        self.actual_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_expected_vs_actual(self):
        """测试便捷验证函数"""
        # 创建相同的文件
        company_name = "测试公司"
        
        expected_company_dir = self.expected_dir / company_name
        actual_company_dir = self.actual_dir / company_name
        
        expected_company_dir.mkdir(parents=True, exist_ok=True)
        actual_company_dir.mkdir(parents=True, exist_ok=True)
        
        content = b"Test content"
        
        expected_file = expected_company_dir / "test.pdf"
        actual_file = actual_company_dir / "test.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(content)
        with open(actual_file, 'wb') as f:
            f.write(content)
        
        result = validate_expected_vs_actual(
            str(self.expected_dir), 
            str(self.actual_dir), 
            "strict"
        )
        
        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
    
    def test_validate_test_case(self):
        """测试测试用例验证函数"""
        # 创建测试数据
        stock_code = "300470"
        company_name = "中密控股"
        
        expected_company_dir = self.expected_dir / company_name
        actual_company_dir = self.actual_dir / company_name
        
        expected_company_dir.mkdir(parents=True, exist_ok=True)
        actual_company_dir.mkdir(parents=True, exist_ok=True)
        
        content = b"Test content"
        
        expected_file = expected_company_dir / f"中密控股：{stock_code}报告.pdf"
        actual_file = actual_company_dir / f"中密控股：{stock_code}报告.pdf"
        
        with open(expected_file, 'wb') as f:
            f.write(content)
        with open(actual_file, 'wb') as f:
            f.write(content)
        
        test_case = {
            "stock_code": stock_code,
            "suffix": "research"
        }
        
        result = validate_test_case(
            test_case, 
            str(self.expected_dir), 
            str(self.actual_dir), 
            "strict"
        )
        
        assert isinstance(result, ValidationResult)
        assert result.overall_success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])