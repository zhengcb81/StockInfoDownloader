#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能基准测试模块的单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from tests.validation.performance_benchmark_tests import (
    PerformanceBenchmarkTester, 
    BenchmarkResult
)


class TestPerformanceBenchmarkTester:
    """性能基准测试器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.tester = PerformanceBenchmarkTester()
    
    def teardown_method(self):
        """测试清理"""
        self.tester.cleanup()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.tester.validator is not None
        assert self.tester.temp_dir.exists()
    
    def test_create_test_data(self):
        """测试创建测试数据"""
        expected_dir, actual_dir = self.tester.create_test_data(
            file_count=5, 
            file_size_kb=1, 
            company_count=1, 
            depth=1
        )
        
        assert expected_dir.exists()
        assert actual_dir.exists()
        
        # 检查文件是否创建
        expected_files = list(expected_dir.rglob("*.pdf"))
        actual_files = list(actual_dir.rglob("*.pdf"))
        
        assert len(expected_files) == 5
        assert len(actual_files) == 5
    
    def test_create_test_data_multiple_companies(self):
        """测试创建多公司测试数据"""
        expected_dir, actual_dir = self.tester.create_test_data(
            file_count=10, 
            file_size_kb=1, 
            company_count=2, 
            depth=1
        )
        
        # 检查公司目录
        expected_companies = [d for d in expected_dir.iterdir() if d.is_dir()]
        actual_companies = [d for d in actual_dir.iterdir() if d.is_dir()]
        
        assert len(expected_companies) == 2
        assert len(actual_companies) == 2
        
        # 检查每个公司的文件数量
        for company_dir in expected_companies:
            company_files = list(company_dir.rglob("*.pdf"))
            assert len(company_files) == 5  # 10个文件 / 2个公司 = 5个文件每个公司
    
    def test_create_test_data_deep_directories(self):
        """测试创建深层目录测试数据"""
        expected_dir, actual_dir = self.tester.create_test_data(
            file_count=3, 
            file_size_kb=1, 
            company_count=1, 
            depth=3
        )
        
        # 检查深层目录结构
        expected_files = list(expected_dir.rglob("*.pdf"))
        
        assert len(expected_files) == 3
        
        # 检查文件路径深度
        for file_path in expected_files:
            relative_path = file_path.relative_to(expected_dir)
            path_parts = relative_path.parts
            assert len(path_parts) >= 4  # company/level_0/level_1/level_2/file.pdf
    
    def test_benchmark_small_files(self):
        """测试小文件基准测试"""
        result = self.tester.benchmark_small_files(file_count=5)
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "small_files"
        assert result.file_count == 5
        assert result.execution_time_seconds > 0
        assert result.success_rate == 100.0  # 所有文件应该匹配
        assert result.error_count == 0
    
    def test_benchmark_medium_files(self):
        """测试中等文件基准测试"""
        result = self.tester.benchmark_medium_files(file_count=3)
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "medium_files"
        assert result.file_count == 3
        assert result.execution_time_seconds > 0
        assert result.success_rate == 100.0
        assert result.error_count == 0
    
    def test_benchmark_large_files(self):
        """测试大文件基准测试"""
        result = self.tester.benchmark_large_files(file_count=2)
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "large_files"
        assert result.file_count == 2
        assert result.execution_time_seconds > 0
        assert result.success_rate == 100.0
        assert result.error_count == 0
    
    def test_benchmark_many_companies(self):
        """测试多公司基准测试"""
        result = self.tester.benchmark_many_companies(company_count=3, files_per_company=2)
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "many_companies"
        assert result.file_count == 6  # 3个公司 * 2个文件
        assert result.execution_time_seconds > 0
        assert result.success_rate == 100.0
        assert result.error_count == 0
    
    def test_benchmark_deep_directories(self):
        """测试深层目录基准测试"""
        result = self.tester.benchmark_deep_directories(depth=2, file_count=3)
        
        assert isinstance(result, BenchmarkResult)
        assert result.test_name == "deep_directories"
        assert result.file_count == 3
        assert result.execution_time_seconds > 0
        assert result.success_rate == 100.0
        assert result.error_count == 0
    
    def test_benchmark_comparison_modes(self):
        """测试比较模式基准测试"""
        results = self.tester.benchmark_comparison_modes(file_count=5)
        
        assert isinstance(results, dict)
        assert len(results) >= 3  # 至少应该有strict, lenient, content_only模式
        
        for mode, result in results.items():
            assert isinstance(result, BenchmarkResult)
            assert result.file_count == 5
            assert result.execution_time_seconds > 0
            assert result.success_rate == 100.0
            assert result.error_count == 0
    
    def test_run_scalability_test(self):
        """测试可扩展性测试"""
        results = self.tester.run_scalability_test(scale_factors=[1, 2])
        
        assert isinstance(results, dict)
        assert "file_count_scalability" in results
        assert "file_size_scalability" in results
        
        # 文件数量可扩展性
        file_count_results = results["file_count_scalability"]
        assert len(file_count_results) == 2
        
        for result in file_count_results:
            assert isinstance(result, BenchmarkResult)
            assert result.execution_time_seconds > 0
        
        # 文件大小可扩展性
        file_size_results = results["file_size_scalability"]
        assert len(file_size_results) >= 2
        
        for result in file_size_results:
            assert isinstance(result, BenchmarkResult)
            assert result.execution_time_seconds > 0
    
    def test_run_stress_test(self):
        """测试压力测试"""
        results = self.tester.run_stress_test(iterations=2)
        
        assert isinstance(results, dict)
        assert "iterations" in results
        assert results["iterations"] == 2
        assert "avg_execution_time" in results
        assert results["avg_execution_time"] > 0
        assert "avg_success_rate" in results
        assert results["avg_success_rate"] == 100.0
    
    def test_run_all_benchmarks(self):
        """测试运行所有基准测试"""
        results = self.tester.run_all_benchmarks()
        
        assert isinstance(results, dict)
        
        # 验证所有基准测试都包含在结果中
        expected_tests = [
            "small_files",
            "medium_files", 
            "large_files",
            "many_companies",
            "deep_directories",
            "comparison_modes",
            "scalability",
            "stress_test"
        ]
        
        for test_name in expected_tests:
            assert test_name in results
    
    def test_generate_report(self):
        """测试生成报告"""
        # 运行一些基准测试
        benchmark_results = {
            "small_files": BenchmarkResult(
                test_name="small_files",
                file_count=10,
                total_size_bytes=102400,  # 100KB
                execution_time_seconds=0.123,
                memory_usage_mb=5.0,
                success_rate=100.0,
                error_count=0
            ),
            "medium_files": BenchmarkResult(
                test_name="medium_files",
                file_count=5,
                total_size_bytes=512000,  # 500KB
                execution_time_seconds=0.456,
                memory_usage_mb=10.0,
                success_rate=100.0,
                error_count=0
            )
        }
        
        report = self.tester.generate_report(benchmark_results)
        
        assert isinstance(report, str)
        assert "# 性能基准测试报告" in report
        assert "small_files" in report
        assert "medium_files" in report
    
    def test_cleanup(self):
        """测试清理功能"""
        # 确保临时目录存在
        assert self.tester.temp_dir.exists()
        
        # 执行清理
        self.tester.cleanup()
        
        # 验证临时目录被清理
        assert not self.tester.temp_dir.exists()


class TestPerformanceBenchmarkTesterEdgeCases:
    """性能基准测试器边缘情况测试"""
    
    def test_zero_files(self):
        """测试零文件的情况"""
        tester = PerformanceBenchmarkTester()
        
        try:
            expected_dir, actual_dir = tester.create_test_data(file_count=0)
            
            # 执行验证
            result = tester.validator.validate_expected_data(expected_dir, actual_dir)
            
            # 应该成功，因为没有文件需要比较
            assert result.overall_success is True
            assert result.total_files_compared == 0
            
        finally:
            tester.cleanup()
    
    def test_very_large_file_count(self):
        """测试非常大的文件数量（谨慎使用）"""
        tester = PerformanceBenchmarkTester()
        
        try:
            # 使用较小的文件数量以避免性能问题
            result = tester.benchmark_small_files(file_count=20)
            
            assert result.execution_time_seconds > 0
            assert result.success_rate == 100.0
            
        finally:
            tester.cleanup()
    
    def test_very_large_file_size(self):
        """测试非常大的文件大小（谨慎使用）"""
        tester = PerformanceBenchmarkTester()
        
        try:
            # 使用较小的文件大小以避免内存问题
            expected_dir, actual_dir = tester.create_test_data(file_count=2, file_size_kb=10)
            result = tester._run_validation_benchmark("test", expected_dir, actual_dir, 2)
            
            assert result.execution_time_seconds > 0
            assert result.success_rate == 100.0
            
        finally:
            tester.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])