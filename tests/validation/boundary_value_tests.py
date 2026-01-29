#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
边界值测试增强模块
测试期待数据验证框架在各种边界条件下的行为
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict


from tests.validation.expected_data_samples import ExpectedDataSampleLibrary
from tests.validation.expected_data_validator import (
    ComparisonMode,
    ExpectedDataValidator,
    ValidationResult,
)


class BoundaryValueTester:
    """边界值测试器"""

    def __init__(self):
        """初始化边界值测试器"""
        self.validator = ExpectedDataValidator()
        self.sample_library = ExpectedDataSampleLibrary()
        self.temp_dir = Path(tempfile.mkdtemp())

    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.sample_library.cleanup()

    def test_empty_directories(self) -> ValidationResult:
        """测试空目录边界条件"""
        # 创建空目录
        empty_expected_dir = self.temp_dir / "empty_expected"
        empty_actual_dir = self.temp_dir / "empty_actual"

        empty_expected_dir.mkdir(parents=True, exist_ok=True)
        empty_actual_dir.mkdir(parents=True, exist_ok=True)

        # 执行验证
        return self.validator.validate_expected_data(
            empty_expected_dir, empty_actual_dir
        )

    def test_single_file_scenario(self) -> ValidationResult:
        """测试单文件边界条件"""
        # 创建单文件场景（符合验证器期望的目录结构）
        single_expected_dir = self.temp_dir / "single_expected"
        single_actual_dir = self.temp_dir / "single_actual"

        single_expected_dir.mkdir(parents=True, exist_ok=True)
        single_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = single_expected_dir / "test_company"
        company_actual_dir = single_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建单个文件（PDF格式）
        test_content = b"%PDF-1.4\nSingle file test content\n%%EOF"

        expected_file = company_expected_dir / "single_file.pdf"
        actual_file = company_actual_dir / "single_file.pdf"

        with open(expected_file, "wb") as f:
            f.write(test_content)
        with open(actual_file, "wb") as f:
            f.write(test_content)

        # 执行验证
        return self.validator.validate_expected_data(
            single_expected_dir, single_actual_dir
        )

    def test_large_file_scenario(self, file_size_mb: float = 10.0) -> ValidationResult:
        """测试大文件边界条件"""
        # 创建大文件场景（符合验证器期望的目录结构）
        large_expected_dir = self.temp_dir / "large_expected"
        large_actual_dir = self.temp_dir / "large_actual"

        large_expected_dir.mkdir(parents=True, exist_ok=True)
        large_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = large_expected_dir / "test_company"
        company_actual_dir = large_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建大文件（PDF格式）
        pdf_header = b"%PDF-1.4\n"
        pdf_footer = b"%%EOF\n"
        large_content = (
            pdf_header
            + b"x" * int(file_size_mb * 1024 * 1024 - len(pdf_header) - len(pdf_footer))
            + pdf_footer
        )  # MB转换为字节

        expected_file = company_expected_dir / "large_file.pdf"
        actual_file = company_actual_dir / "large_file.pdf"

        with open(expected_file, "wb") as f:
            f.write(large_content)
        with open(actual_file, "wb") as f:
            f.write(large_content)

        # 执行验证
        return self.validator.validate_expected_data(
            large_expected_dir, large_actual_dir
        )

    def test_very_small_file_scenario(self) -> ValidationResult:
        """测试极小文件边界条件"""
        # 创建极小文件场景（符合验证器期望的目录结构）
        small_expected_dir = self.temp_dir / "small_expected"
        small_actual_dir = self.temp_dir / "small_actual"

        small_expected_dir.mkdir(parents=True, exist_ok=True)
        small_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = small_expected_dir / "test_company"
        company_actual_dir = small_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建极小文件（PDF格式）
        tiny_content = b"%PDF-1.4\n%%EOF"

        expected_file = company_expected_dir / "tiny_file.pdf"
        actual_file = company_actual_dir / "tiny_file.pdf"

        with open(expected_file, "wb") as f:
            f.write(tiny_content)
        with open(actual_file, "wb") as f:
            f.write(tiny_content)

        # 执行验证
        return self.validator.validate_expected_data(
            small_expected_dir, small_actual_dir
        )

    def test_many_files_scenario(self, file_count: int = 100) -> ValidationResult:
        """测试多文件边界条件"""
        # 创建多文件场景（符合验证器期望的目录结构）
        many_expected_dir = self.temp_dir / "many_expected"
        many_actual_dir = self.temp_dir / "many_actual"

        many_expected_dir.mkdir(parents=True, exist_ok=True)
        many_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = many_expected_dir / "test_company"
        company_actual_dir = many_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建多个文件（PDF格式）
        for i in range(file_count):
            content = f"%PDF-1.4\nFile {i} content\n%%EOF".encode("utf-8")

            expected_file = company_expected_dir / f"file_{i:04d}.pdf"
            actual_file = company_actual_dir / f"file_{i:04d}.pdf"

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(many_expected_dir, many_actual_dir)

    def test_deep_directory_structure(self, depth: int = 5) -> ValidationResult:
        """测试深层目录结构边界条件"""
        # 创建深层目录结构（符合验证器期望的目录结构）
        deep_expected_dir = self.temp_dir / "deep_expected"
        deep_actual_dir = self.temp_dir / "deep_actual"

        deep_expected_dir.mkdir(parents=True, exist_ok=True)
        deep_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = deep_expected_dir / "test_company"
        company_actual_dir = deep_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 构建深层目录
        current_expected = company_expected_dir
        current_actual = company_actual_dir

        for i in range(depth):
            current_expected = current_expected / f"level_{i}"
            current_actual = current_actual / f"level_{i}"

        current_expected.mkdir(parents=True, exist_ok=True)
        current_actual.mkdir(parents=True, exist_ok=True)

        # 在最深层创建文件（PDF格式）
        content = b"%PDF-1.4\nDeep directory test content\n%%EOF"

        expected_file = current_expected / "deep_file.pdf"
        actual_file = current_actual / "deep_file.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)
        with open(actual_file, "wb") as f:
            f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(deep_expected_dir, deep_actual_dir)

    def test_special_characters_filenames(self) -> ValidationResult:
        """测试特殊字符文件名边界条件"""
        # 创建特殊字符文件名场景（符合验证器期望的目录结构）
        special_expected_dir = self.temp_dir / "special_expected"
        special_actual_dir = self.temp_dir / "special_actual"

        special_expected_dir.mkdir(parents=True, exist_ok=True)
        special_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = special_expected_dir / "test_company"
        company_actual_dir = special_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 特殊字符文件名（Windows兼容）
        special_filenames = [
            "文件 带 空格.pdf",
            "文件-带-连字符.pdf",
            "文件_带_下划线.pdf",
            "文件.带.点.pdf",
            "文件(带括号).pdf",
            "文件[带方括号].pdf",
            "文件{带花括号}.pdf",
            "文件@带@符号.pdf",
            "文件#带#井号.pdf",
            "文件$带$美元符号.pdf",
            "文件%带%百分号.pdf",
            "文件^带^脱字符.pdf",
            "文件&带&和号.pdf",
            "文件+带+加号.pdf",
            # 移除*号，因为Windows文件名中不允许使用*
        ]

        # 创建文件（PDF格式）
        content = b"%PDF-1.4\nSpecial characters test content\n%%EOF"

        for filename in special_filenames:
            expected_file = company_expected_dir / filename
            actual_file = company_actual_dir / filename

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(
            special_expected_dir, special_actual_dir
        )

    def test_unicode_filenames(self) -> ValidationResult:
        """测试Unicode文件名边界条件"""
        # 创建Unicode文件名场景（符合验证器期望的目录结构）
        unicode_expected_dir = self.temp_dir / "unicode_expected"
        unicode_actual_dir = self.temp_dir / "unicode_actual"

        unicode_expected_dir.mkdir(parents=True, exist_ok=True)
        unicode_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = unicode_expected_dir / "test_company"
        company_actual_dir = unicode_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # Unicode文件名
        unicode_filenames = [
            "中文文件名.pdf",
            "日本語ファイル名.pdf",
            "한국어파일이름.pdf",
            "русскийфайл.pdf",
            "العربيةملف.pdf",
            "Ελληνικόαρχείο.pdf",
            "עבריתקובץ.pdf",
            "ไทยไฟล์.pdf",
            "TiếngViệttệp.pdf",
            "Českýsoubor.pdf",
        ]

        # 创建文件（PDF格式）
        content = b"%PDF-1.4\nUnicode filenames test content\n%%EOF"

        for filename in unicode_filenames:
            expected_file = company_expected_dir / filename
            actual_file = company_actual_dir / filename

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

        # 执行验证
        return self.validator.validate_expected_data(
            unicode_expected_dir, unicode_actual_dir
        )

    def test_file_permission_scenarios(self) -> Dict[str, Any]:
        """测试文件权限边界条件"""
        # 创建文件权限测试场景（符合验证器期望的目录结构）
        perm_expected_dir = self.temp_dir / "perm_expected"
        perm_actual_dir = self.temp_dir / "perm_actual"

        perm_expected_dir.mkdir(parents=True, exist_ok=True)
        perm_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = perm_expected_dir / "test_company"
        company_actual_dir = perm_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建正常文件（PDF格式）
        normal_content = b"%PDF-1.4\nNormal file content\n%%EOF"
        normal_expected = company_expected_dir / "normal.pdf"
        normal_actual = company_actual_dir / "normal.pdf"

        with open(normal_expected, "wb") as f:
            f.write(normal_content)
        with open(normal_actual, "wb") as f:
            f.write(normal_content)

        # 测试只读文件（在实际环境中可能难以模拟，这里主要测试可访问性）
        # 在实际测试中，可能需要特殊权限设置

        results = {}

        # 测试正常文件验证
        normal_result = self.validator.validate_expected_data(
            perm_expected_dir, perm_actual_dir
        )
        results["normal_files"] = normal_result.overall_success

        return results

    def test_comparison_mode_boundaries(self) -> Dict[str, ValidationResult]:
        """测试比较模式边界条件"""
        # 创建测试数据（符合验证器期望的目录结构）
        mode_expected_dir = self.temp_dir / "mode_expected"
        mode_actual_dir = self.temp_dir / "mode_actual"

        mode_expected_dir.mkdir(parents=True, exist_ok=True)
        mode_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = mode_expected_dir / "test_company"
        company_actual_dir = mode_actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建相同内容的文件（PDF格式）
        content = b"%PDF-1.4\nComparison mode test content\n%%EOF"

        expected_file = company_expected_dir / "test.pdf"
        actual_file = company_actual_dir / "test.pdf"

        with open(expected_file, "wb") as f:
            f.write(content)
        with open(actual_file, "wb") as f:
            f.write(content)

        results = {}

        # 测试所有比较模式
        for mode in ComparisonMode:
            validator = ExpectedDataValidator(mode)
            result = validator.validate_expected_data(
                mode_expected_dir, mode_actual_dir
            )
            results[mode.value] = result

        return results

    def run_all_boundary_tests(self) -> Dict[str, Any]:
        """运行所有边界值测试"""
        test_results = {}

        try:
            # 空目录测试
            empty_result = self.test_empty_directories()
            test_results["empty_directories"] = {
                "success": empty_result.overall_success,
                "files_compared": empty_result.total_files_compared,
            }

            # 单文件测试
            single_result = self.test_single_file_scenario()
            test_results["single_file"] = {
                "success": single_result.overall_success,
                "files_compared": single_result.total_files_compared,
            }

            # 大文件测试（使用较小的大小以避免内存问题）
            large_result = self.test_large_file_scenario(file_size_mb=1)
            test_results["large_file"] = {
                "success": large_result.overall_success,
                "files_compared": large_result.total_files_compared,
            }

            # 极小文件测试
            small_result = self.test_very_small_file_scenario()
            test_results["small_file"] = {
                "success": small_result.overall_success,
                "files_compared": small_result.total_files_compared,
            }

            # 多文件测试（使用较小的数量以避免性能问题）
            many_result = self.test_many_files_scenario(file_count=10)
            test_results["many_files"] = {
                "success": many_result.overall_success,
                "files_compared": many_result.total_files_compared,
            }

            # 深层目录测试
            deep_result = self.test_deep_directory_structure(depth=3)
            test_results["deep_directory"] = {
                "success": deep_result.overall_success,
                "files_compared": deep_result.total_files_compared,
            }

            # 特殊字符文件名测试（跳过Windows不兼容的测试）
            try:
                special_result = self.test_special_characters_filenames()
                test_results["special_characters"] = {
                    "success": special_result.overall_success,
                    "files_compared": special_result.total_files_compared,
                }
            except OSError as e:
                test_results["special_characters"] = {"success": False, "error": str(e)}

            # Unicode文件名测试
            try:
                unicode_result = self.test_unicode_filenames()
                test_results["unicode_filenames"] = {
                    "success": unicode_result.overall_success,
                    "files_compared": unicode_result.total_files_compared,
                }
            except OSError as e:
                test_results["unicode_filenames"] = {"success": False, "error": str(e)}

            # 比较模式测试
            mode_results = self.test_comparison_mode_boundaries()
            test_results["comparison_modes"] = {
                mode: result.overall_success for mode, result in mode_results.items()
            }

        except Exception as e:
            test_results["error"] = str(e)

        return test_results


# 边界值测试运行器
boundary_value_tester = BoundaryValueTester()
