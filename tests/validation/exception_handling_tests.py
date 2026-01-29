#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异常处理测试模块
测试期待数据验证框架在各种异常情况下的行为
包括文件不存在、权限错误、格式错误等场景
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch


from tests.validation.expected_data_validator import (
    ExpectedDataValidator,
    ValidationResult,
)


class ExceptionHandlingTester:
    """异常处理测试器"""

    def __init__(self):
        """初始化异常处理测试器"""
        self.validator = ExpectedDataValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_nonexistent_expected_directory(self) -> ValidationResult:
        """测试期待目录不存在的情况"""
        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 期待目录不存在
        expected_dir = self.temp_dir / "nonexistent_expected"

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_nonexistent_actual_directory(self) -> ValidationResult:
        """测试实际目录不存在的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 实际目录不存在
        actual_dir = self.temp_dir / "nonexistent_actual"

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_both_directories_nonexistent(self) -> ValidationResult:
        """测试两个目录都不存在的情况"""
        # 两个目录都不存在
        expected_dir = self.temp_dir / "nonexistent_expected"
        actual_dir = self.temp_dir / "nonexistent_actual"

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_empty_expected_directory_with_files_in_actual(self) -> ValidationResult:
        """测试空期待目录但实际目录有文件的情况"""
        # 创建空期待目录
        expected_dir = self.temp_dir / "empty_expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建有文件的实际目录
        actual_dir = self.temp_dir / "actual_with_files"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 在实际目录中创建文件
        content = b"%PDF-1.4\nActual file content\n%%EOF"
        actual_file = company_actual_dir / "test.pdf"

        with open(actual_file, "wb") as f:
            f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_missing_files_in_actual(self) -> ValidationResult:
        """测试实际目录中缺少文件的情况"""
        # 创建期待目录（有文件）
        expected_dir = self.temp_dir / "expected_with_files"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 在期待目录中创建文件
        content = b"%PDF-1.4\nExpected file content\n%%EOF"
        expected_file = company_expected_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)

        # 创建实际目录（有公司目录但无文件）
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_corrupted_file_content(self) -> ValidationResult:
        """测试文件内容损坏的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建相同文件但内容不同
        expected_content = b"%PDF-1.4\nExpected file content\n%%EOF"
        actual_content = b"%PDF-1.4\nCorrupted file content\n%%EOF"

        expected_file = company_expected_dir / "test.pdf"
        actual_file = company_actual_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(expected_content)
        with open(actual_file, "wb") as f:
            f.write(actual_content)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_different_file_sizes(self) -> ValidationResult:
        """测试文件大小不同的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建相同内容但大小不同的文件
        expected_content = b"%PDF-1.4\nExpected file content\n%%EOF"
        actual_content = b"%PDF-1.4\nActual file content with extra padding\n%%EOF"

        expected_file = company_expected_dir / "test.pdf"
        actual_file = company_actual_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(expected_content)
        with open(actual_file, "wb") as f:
            f.write(actual_content)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_extra_files_in_actual(self) -> ValidationResult:
        """测试实际目录中有额外文件的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 在期待目录中创建文件
        content = b"%PDF-1.4\nFile content\n%%EOF"
        expected_file = company_expected_dir / "expected.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)

        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 在实际目录中创建额外文件（包括期待文件）
        actual_file1 = company_actual_dir / "expected.pdf"
        actual_file2 = company_actual_dir / "extra.pdf"

        with open(actual_file1, "wb") as f:
            f.write(content)
        with open(actual_file2, "wb") as f:
            f.write(b"%PDF-1.4\nExtra file content\n%%EOF")

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_different_directory_structures(self) -> ValidationResult:
        """测试目录结构不同的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 在期待目录中创建文件
        content = b"%PDF-1.4\nFile content\n%%EOF"
        expected_file = company_expected_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)

        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建不同的公司目录
        company_actual_dir = actual_dir / "different_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 在实际目录中创建相同内容的文件
        actual_file = company_actual_dir / "test.pdf"

        with open(actual_file, "wb") as f:
            f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_file_permission_errors(self) -> Dict[str, Any]:
        """测试文件权限错误的情况"""
        # 创建测试目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建文件
        content = b"%PDF-1.4\nFile content\n%%EOF"

        expected_file = company_expected_dir / "test.pdf"
        actual_file = company_actual_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)
        with open(actual_file, "wb") as f:
            f.write(content)

        results = {}

        # 测试正常情况
        normal_result = self.validator.validate_expected_data(expected_dir, actual_dir)
        results["normal"] = normal_result.overall_success

        # 测试文件读取错误（模拟权限问题）
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            try:
                permission_result = self.validator.validate_expected_data(
                    expected_dir, actual_dir
                )
                results["permission_error"] = permission_result.overall_success
            except Exception as e:
                results["permission_error"] = f"Exception: {str(e)}"

        return results

    def test_invalid_file_formats(self) -> ValidationResult:
        """测试无效文件格式的情况"""
        # 创建期待目录
        expected_dir = self.temp_dir / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_expected_dir.mkdir(parents=True, exist_ok=True)

        # 创建实际目录
        actual_dir = self.temp_dir / "actual"
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_actual_dir = actual_dir / "test_company"
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建PDF文件（期待）
        pdf_content = b"%PDF-1.4\nValid PDF content\n%%EOF"
        expected_file = company_expected_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(pdf_content)

        # 创建无效文件（实际）
        invalid_content = b"This is not a valid PDF file"
        actual_file = company_actual_dir / "test.pdf"

        with open(actual_file, "wb") as f:
            f.write(invalid_content)

        # 执行验证
        return self.validator.validate_expected_data(expected_dir, actual_dir)

    def test_symlink_handling(self) -> Dict[str, Any]:
        """测试符号链接处理（如果支持）"""
        results = {}

        try:
            # 创建测试目录
            expected_dir = self.temp_dir / "expected"
            expected_dir.mkdir(parents=True, exist_ok=True)

            actual_dir = self.temp_dir / "actual"
            actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建公司目录
            company_expected_dir = expected_dir / "test_company"
            company_expected_dir.mkdir(parents=True, exist_ok=True)

            company_actual_dir = actual_dir / "test_company"
            company_actual_dir.mkdir(parents=True, exist_ok=True)

            # 创建源文件
            source_file = self.temp_dir / "source.pdf"
            content = b"%PDF-1.4\nSource file content\n%%EOF"

            with open(source_file, "wb") as f:
                f.write(content)

            # 创建符号链接（期待）
            expected_link = company_expected_dir / "test.pdf"
            expected_link.symlink_to(source_file)

            # 创建实际文件
            actual_file = company_actual_dir / "test.pdf"

            with open(actual_file, "wb") as f:
                f.write(content)

            # 执行验证
            result = self.validator.validate_expected_data(expected_dir, actual_dir)
            results["symlink_test"] = result.overall_success

        except (OSError, NotImplementedError) as e:
            # 符号链接可能在某些系统上不可用
            results["symlink_test"] = f"Symlink not supported: {str(e)}"

        return results

    def run_all_exception_tests(self) -> Dict[str, Any]:
        """运行所有异常处理测试"""
        test_results = {}

        try:
            # 期待目录不存在测试
            nonexistent_expected_result = self.test_nonexistent_expected_directory()
            test_results["nonexistent_expected_directory"] = {
                "success": nonexistent_expected_result.overall_success,
                "error_messages": nonexistent_expected_result.error_messages,
            }

            # 实际目录不存在测试
            nonexistent_actual_result = self.test_nonexistent_actual_directory()
            test_results["nonexistent_actual_directory"] = {
                "success": nonexistent_actual_result.overall_success,
                "error_messages": nonexistent_actual_result.error_messages,
            }

            # 两个目录都不存在测试
            both_nonexistent_result = self.test_both_directories_nonexistent()
            test_results["both_directories_nonexistent"] = {
                "success": both_nonexistent_result.overall_success,
                "error_messages": both_nonexistent_result.error_messages,
            }

            # 空期待目录测试
            empty_expected_result = (
                self.test_empty_expected_directory_with_files_in_actual()
            )
            test_results["empty_expected_directory"] = {
                "success": empty_expected_result.overall_success,
                "files_compared": empty_expected_result.total_files_compared,
                "files_missing": empty_expected_result.files_missing,
                "files_extra": empty_expected_result.files_extra,
            }

            # 缺少文件测试
            missing_files_result = self.test_missing_files_in_actual()
            test_results["missing_files_in_actual"] = {
                "success": missing_files_result.overall_success,
                "files_compared": missing_files_result.total_files_compared,
                "files_missing": missing_files_result.files_missing,
            }

            # 文件内容损坏测试
            corrupted_content_result = self.test_corrupted_file_content()
            test_results["corrupted_file_content"] = {
                "success": corrupted_content_result.overall_success,
                "files_compared": corrupted_content_result.total_files_compared,
                "files_mismatched": corrupted_content_result.files_mismatched,
            }

            # 文件大小不同测试
            different_sizes_result = self.test_different_file_sizes()
            test_results["different_file_sizes"] = {
                "success": different_sizes_result.overall_success,
                "files_compared": different_sizes_result.total_files_compared,
                "files_mismatched": different_sizes_result.files_mismatched,
            }

            # 额外文件测试
            extra_files_result = self.test_extra_files_in_actual()
            test_results["extra_files_in_actual"] = {
                "success": extra_files_result.overall_success,
                "files_compared": extra_files_result.total_files_compared,
                "files_extra": extra_files_result.files_extra,
            }

            # 目录结构不同测试
            different_structure_result = self.test_different_directory_structures()
            test_results["different_directory_structures"] = {
                "success": different_structure_result.overall_success,
                "files_compared": different_structure_result.total_files_compared,
                "files_missing": different_structure_result.files_missing,
            }

            # 文件权限测试
            permission_results = self.test_file_permission_errors()
            test_results["file_permission_errors"] = permission_results

            # 无效文件格式测试
            invalid_format_result = self.test_invalid_file_formats()
            test_results["invalid_file_formats"] = {
                "success": invalid_format_result.overall_success,
                "files_compared": invalid_format_result.total_files_compared,
                "files_mismatched": invalid_format_result.files_mismatched,
            }

            # 符号链接测试
            symlink_results = self.test_symlink_handling()
            test_results["symlink_handling"] = symlink_results

        except Exception as e:
            test_results["error"] = str(e)

        return test_results


# 异常处理测试运行器
exception_handling_tester = ExceptionHandlingTester()
