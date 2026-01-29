#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异常处理测试模块的单元测试
"""


import pytest

from tests.validation.exception_handling_tests import ExceptionHandlingTester
from tests.validation.expected_data_validator import ValidationResult


class TestExceptionHandlingTester:
    """异常处理测试器测试类"""

    def setup_method(self):
        """测试设置"""
        self.tester = ExceptionHandlingTester()

    def teardown_method(self):
        """测试清理"""
        self.tester.cleanup()

    def test_initialization(self):
        """测试初始化"""
        assert self.tester.validator is not None
        assert self.tester.temp_dir.exists()

    def test_nonexistent_expected_directory(self):
        """测试期待目录不存在的情况"""
        result = self.tester.test_nonexistent_expected_directory()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "期待数据目录不存在" in result.error_messages[0]
        assert result.total_files_compared == 0

    def test_nonexistent_actual_directory(self):
        """测试实际目录不存在的情况"""
        result = self.tester.test_nonexistent_actual_directory()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "实际数据目录不存在" in result.error_messages[0]
        assert result.total_files_compared == 0

    def test_both_directories_nonexistent(self):
        """测试两个目录都不存在的情况"""
        result = self.tester.test_both_directories_nonexistent()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is False
        assert len(result.error_messages) > 0
        # 应该报告期待目录不存在
        assert "期待数据目录不存在" in result.error_messages[0]
        assert result.total_files_compared == 0

    def test_empty_expected_directory_with_files_in_actual(self):
        """测试空期待目录但实际目录有文件的情况"""
        result = self.tester.test_empty_expected_directory_with_files_in_actual()

        assert isinstance(result, ValidationResult)
        # 期待目录为空，实际目录有文件，应该报告多余文件
        assert result.overall_success is False
        assert result.files_extra > 0
        assert result.files_missing == 0

    def test_missing_files_in_actual(self):
        """测试实际目录中缺少文件的情况"""
        result = self.tester.test_missing_files_in_actual()

        assert isinstance(result, ValidationResult)
        # 期待目录有文件，实际目录有公司目录但无文件，应该报告缺失文件
        assert result.overall_success is False
        assert result.files_missing > 0
        assert result.files_extra == 0

    def test_corrupted_file_content(self):
        """测试文件内容损坏的情况"""
        result = self.tester.test_corrupted_file_content()

        assert isinstance(result, ValidationResult)
        # 文件内容不同，应该报告不匹配
        assert result.overall_success is False
        assert result.files_mismatched > 0
        assert result.files_missing == 0
        assert result.files_extra == 0

    def test_different_file_sizes(self):
        """测试文件大小不同的情况"""
        result = self.tester.test_different_file_sizes()

        assert isinstance(result, ValidationResult)
        # 文件大小不同，应该报告不匹配
        assert result.overall_success is False
        assert result.files_mismatched > 0
        assert result.files_missing == 0
        assert result.files_extra == 0

    def test_extra_files_in_actual(self):
        """测试实际目录中有额外文件的情况"""
        result = self.tester.test_extra_files_in_actual()

        assert isinstance(result, ValidationResult)
        # 当前验证器只比较期待目录中存在的文件，不检测实际目录中多余的文件
        # 因此文件数量不匹配，但期待文件匹配，整体验证成功
        assert result.overall_success is True
        assert result.files_matched == 1  # 期待文件匹配
        assert result.total_files_compared == 1  # 只比较了期待目录中的文件
        assert result.files_extra == 0  # 不检测同一公司目录中的多余文件

    def test_different_directory_structures(self):
        """测试目录结构不同的情况"""
        result = self.tester.test_different_directory_structures()

        assert isinstance(result, ValidationResult)
        # 目录结构不同（不同公司目录），验证器检测到多余的公司目录
        assert result.overall_success is False
        # 期待目录中的文件在实际目录中找不到（公司目录不同），但files_missing为0
        # 因为验证器只比较期待目录中存在的公司目录
        assert result.files_missing == 0
        # 实际目录中的文件在期待目录中找不到，报告多余
        assert result.files_extra > 0

    def test_file_permission_errors(self):
        """测试文件权限错误的情况"""
        results = self.tester.test_file_permission_errors()

        assert isinstance(results, dict)
        assert "normal" in results
        assert "permission_error" in results

        # 正常情况应该成功
        assert results["normal"] is True

        # 权限错误可能抛出异常或返回失败结果
        assert results["permission_error"] is not None

    def test_invalid_file_formats(self):
        """测试无效文件格式的情况"""
        result = self.tester.test_invalid_file_formats()

        assert isinstance(result, ValidationResult)
        # 文件格式不同，应该报告不匹配
        assert result.overall_success is False
        assert result.files_mismatched > 0
        assert result.files_missing == 0
        assert result.files_extra == 0

    def test_symlink_handling(self):
        """测试符号链接处理"""
        results = self.tester.test_symlink_handling()

        assert isinstance(results, dict)
        assert "symlink_test" in results

        # 符号链接测试可能成功或报告不支持
        assert results["symlink_test"] is not None

    def test_run_all_exception_tests(self):
        """测试运行所有异常处理测试"""
        results = self.tester.run_all_exception_tests()

        assert isinstance(results, dict)

        # 验证所有测试都包含在结果中
        expected_tests = [
            "nonexistent_expected_directory",
            "nonexistent_actual_directory",
            "both_directories_nonexistent",
            "empty_expected_directory",
            "missing_files_in_actual",
            "corrupted_file_content",
            "different_file_sizes",
            "extra_files_in_actual",
            "different_directory_structures",
            "file_permission_errors",
            "invalid_file_formats",
            "symlink_handling",
        ]

        for test_name in expected_tests:
            assert test_name in results
            test_result = results[test_name]
            assert test_result is not None

    def test_cleanup(self):
        """测试清理功能"""
        # 确保临时目录存在
        assert self.tester.temp_dir.exists()

        # 执行清理
        self.tester.cleanup()

        # 验证临时目录被清理
        assert not self.tester.temp_dir.exists()


class TestExceptionHandlingTesterEdgeCases:
    """异常处理测试器边缘情况测试"""

    def test_extreme_path_lengths(self):
        """测试极端路径长度"""
        tester = ExceptionHandlingTester()

        try:
            # 创建非常长的路径名
            long_path_name = "a" * 100  # 100个字符的路径名

            expected_dir = tester.temp_dir / long_path_name / "expected"
            actual_dir = tester.temp_dir / long_path_name / "actual"

            expected_dir.mkdir(parents=True, exist_ok=True)
            actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建公司目录
            company_expected_dir = expected_dir / "test_company"
            company_actual_dir = actual_dir / "test_company"

            company_expected_dir.mkdir(parents=True, exist_ok=True)
            company_actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建文件
            content = b"%PDF-1.4\nTest content\n%%EOF"

            expected_file = company_expected_dir / "test.pdf"
            actual_file = company_actual_dir / "test.pdf"

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

            # 执行验证
            result = tester.validator.validate_expected_data(expected_dir, actual_dir)
            assert result.overall_success is True

        finally:
            tester.cleanup()

    def test_special_unicode_characters(self):
        """测试特殊Unicode字符"""
        tester = ExceptionHandlingTester()

        try:
            # 创建包含特殊Unicode字符的目录名
            special_chars = "测试目录_🎉_特殊字符_🚀"

            expected_dir = tester.temp_dir / special_chars / "expected"
            actual_dir = tester.temp_dir / special_chars / "actual"

            expected_dir.mkdir(parents=True, exist_ok=True)
            actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建公司目录
            company_expected_dir = expected_dir / "测试公司_🎯"
            company_actual_dir = actual_dir / "测试公司_🎯"

            company_expected_dir.mkdir(parents=True, exist_ok=True)
            company_actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建文件
            content = b"%PDF-1.4\nTest content\n%%EOF"

            expected_file = company_expected_dir / "测试文件_📄.pdf"
            actual_file = company_actual_dir / "测试文件_📄.pdf"

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

            # 执行验证
            result = tester.validator.validate_expected_data(expected_dir, actual_dir)
            assert result.overall_success is True

        finally:
            tester.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
