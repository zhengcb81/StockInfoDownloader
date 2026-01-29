#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
边界值测试模块的单元测试
"""


import pytest

from tests.validation.boundary_value_tests import BoundaryValueTester
from tests.validation.expected_data_validator import ComparisonMode, ValidationResult


class TestBoundaryValueTester:
    """边界值测试器测试类"""

    def setup_method(self):
        """测试设置"""
        self.tester = BoundaryValueTester()

    def teardown_method(self):
        """测试清理"""
        self.tester.cleanup()

    def test_initialization(self):
        """测试初始化"""
        assert self.tester.validator is not None
        assert self.tester.sample_library is not None
        assert self.tester.temp_dir.exists()

    def test_empty_directories(self):
        """测试空目录边界条件"""
        result = self.tester.test_empty_directories()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 0
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0
        assert len(result.directory_results) == 0

    def test_single_file_scenario(self):
        """测试单文件边界条件"""
        result = self.tester.test_single_file_scenario()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0
        assert len(result.directory_results) == 1

    def test_large_file_scenario(self):
        """测试大文件边界条件"""
        # 使用较小的文件大小以避免内存问题
        result = self.tester.test_large_file_scenario(file_size_mb=1)

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_very_small_file_scenario(self):
        """测试极小文件边界条件"""
        result = self.tester.test_very_small_file_scenario()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_many_files_scenario(self):
        """测试多文件边界条件"""
        # 使用较少的文件数量以避免性能问题
        result = self.tester.test_many_files_scenario(file_count=5)

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 5
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_deep_directory_structure(self):
        """测试深层目录结构边界条件"""
        # 使用较小的深度以避免路径过长问题
        result = self.tester.test_deep_directory_structure(depth=2)

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared == 1
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_special_characters_filenames(self):
        """测试特殊字符文件名边界条件"""
        result = self.tester.test_special_characters_filenames()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared > 0
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_unicode_filenames(self):
        """测试Unicode文件名边界条件"""
        result = self.tester.test_unicode_filenames()

        assert isinstance(result, ValidationResult)
        assert result.overall_success is True
        assert result.total_files_compared > 0
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.files_mismatched == 0

    def test_file_permission_scenarios(self):
        """测试文件权限边界条件"""
        results = self.tester.test_file_permission_scenarios()

        assert isinstance(results, dict)
        assert "normal_files" in results
        assert results["normal_files"] is True

    def test_comparison_mode_boundaries(self):
        """测试比较模式边界条件"""
        results = self.tester.test_comparison_mode_boundaries()

        assert isinstance(results, dict)
        assert len(results) == len(ComparisonMode)

        for mode in ComparisonMode:
            assert mode.value in results
            assert isinstance(results[mode.value], ValidationResult)
            assert results[mode.value].overall_success is True

    def test_run_all_boundary_tests(self):
        """测试运行所有边界值测试"""
        results = self.tester.run_all_boundary_tests()

        assert isinstance(results, dict)

        # 验证所有测试都包含在结果中
        expected_tests = [
            "empty_directories",
            "single_file",
            "large_file",
            "small_file",
            "many_files",
            "deep_directory",
            "special_characters",
            "unicode_filenames",
            "comparison_modes",
        ]

        for test_name in expected_tests:
            assert test_name in results

            if test_name != "comparison_modes":
                test_result = results[test_name]
                assert "success" in test_result
                assert "files_compared" in test_result
                assert test_result["success"] is True
            else:
                # 比较模式测试有特殊结构
                comparison_results = results[test_name]
                assert isinstance(comparison_results, dict)
                assert len(comparison_results) == len(ComparisonMode)

    def test_cleanup(self):
        """测试清理功能"""
        # 确保临时目录存在
        assert self.tester.temp_dir.exists()

        # 执行清理
        self.tester.cleanup()

        # 验证临时目录被清理
        assert not self.tester.temp_dir.exists()


class TestBoundaryValueTesterEdgeCases:
    """边界值测试器边缘情况测试"""

    def test_extreme_large_file(self):
        """测试极端大文件（谨慎使用）"""
        tester = BoundaryValueTester()

        try:
            # 使用非常小的文件大小进行测试，避免内存问题
            result = tester.test_large_file_scenario(file_size_mb=0.1)
            assert result.overall_success is True
        finally:
            tester.cleanup()

    def test_very_many_files(self):
        """测试非常多文件（谨慎使用）"""
        tester = BoundaryValueTester()

        try:
            # 使用较少的文件数量进行测试，避免性能问题
            result = tester.test_many_files_scenario(file_count=20)
            assert result.overall_success is True
        finally:
            tester.cleanup()

    def test_very_deep_directory(self):
        """测试非常深层目录（谨慎使用）"""
        tester = BoundaryValueTester()

        try:
            # 使用较小的深度进行测试，避免路径过长问题
            result = tester.test_deep_directory_structure(depth=4)
            assert result.overall_success is True
        finally:
            tester.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
