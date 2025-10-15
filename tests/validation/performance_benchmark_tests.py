#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能基准测试模块
测试期待数据验证框架在不同规模数据下的性能表现
包括文件数量、文件大小、目录深度等性能指标
"""

import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple
import statistics
from dataclasses import dataclass

from tests.validation.expected_data_validator import ExpectedDataValidator, ComparisonMode


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    file_count: int
    total_size_bytes: int
    execution_time_seconds: float
    memory_usage_mb: float
    success_rate: float
    error_count: int


class PerformanceBenchmarkTester:
    """性能基准测试器"""
    
    def __init__(self):
        """初始化性能基准测试器"""
        self.validator = ExpectedDataValidator()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_data(self, file_count: int, file_size_kb: int = 10, 
                        company_count: int = 1, depth: int = 1) -> Tuple[Path, Path]:
        """创建测试数据"""
        expected_dir = self.temp_dir / f"expected_{file_count}_{file_size_kb}kb"
        actual_dir = self.temp_dir / f"actual_{file_count}_{file_size_kb}kb"
        
        expected_dir.mkdir(parents=True, exist_ok=True)
        actual_dir.mkdir(parents=True, exist_ok=True)
        
        files_per_company = file_count // company_count if company_count > 0 else file_count
        
        for company_idx in range(company_count):
            company_name = f"company_{company_idx:04d}"
            
            # 创建公司目录
            company_expected_dir = expected_dir / company_name
            company_actual_dir = actual_dir / company_name
            
            # 创建深层目录结构
            current_expected = company_expected_dir
            current_actual = company_actual_dir
            
            for level in range(depth):
                current_expected = current_expected / f"level_{level}"
                current_actual = current_actual / f"level_{level}"
            
            current_expected.mkdir(parents=True, exist_ok=True)
            current_actual.mkdir(parents=True, exist_ok=True)
            
            # 创建文件
            for file_idx in range(files_per_company):
                if file_idx >= files_per_company:
                    break
                
                content = self._generate_file_content(file_size_kb * 1024)
                
                expected_file = current_expected / f"file_{file_idx:06d}.pdf"
                actual_file = current_actual / f"file_{file_idx:06d}.pdf"
                
                with open(expected_file, 'wb') as f:
                    f.write(content)
                with open(actual_file, 'wb') as f:
                    f.write(content)
        
        return expected_dir, actual_dir
    
    def _generate_file_content(self, size_bytes: int) -> bytes:
        """生成文件内容"""
        pdf_header = b"%PDF-1.4\n"
        pdf_footer = b"%%EOF\n"
        
        # 基础内容
        base_content = b"Performance benchmark test content\n"
        
        # 计算需要填充的大小
        padding_size = size_bytes - len(pdf_header) - len(base_content) - len(pdf_footer)
        if padding_size > 0:
            padding = b"x" * padding_size
        else:
            padding = b""
        
        return pdf_header + base_content + padding + pdf_footer
    
    def benchmark_small_files(self, file_count: int = 100) -> BenchmarkResult:
        """基准测试：小文件（10KB）"""
        return self._run_benchmark("small_files", file_count, file_size_kb=10)
    
    def benchmark_medium_files(self, file_count: int = 50) -> BenchmarkResult:
        """基准测试：中等文件（100KB）"""
        return self._run_benchmark("medium_files", file_count, file_size_kb=100)
    
    def benchmark_large_files(self, file_count: int = 10) -> BenchmarkResult:
        """基准测试：大文件（1MB）"""
        return self._run_benchmark("large_files", file_count, file_size_kb=1024)
    
    def benchmark_many_companies(self, company_count: int = 10, files_per_company: int = 10) -> BenchmarkResult:
        """基准测试：多公司目录"""
        file_count = company_count * files_per_company
        expected_dir, actual_dir = self.create_test_data(
            file_count=file_count, 
            file_size_kb=10, 
            company_count=company_count
        )
        
        return self._run_validation_benchmark("many_companies", expected_dir, actual_dir, file_count)
    
    def benchmark_deep_directories(self, depth: int = 5, file_count: int = 10) -> BenchmarkResult:
        """基准测试：深层目录结构"""
        expected_dir, actual_dir = self.create_test_data(
            file_count=file_count, 
            file_size_kb=10, 
            company_count=1, 
            depth=depth
        )
        
        return self._run_validation_benchmark("deep_directories", expected_dir, actual_dir, file_count)
    
    def benchmark_comparison_modes(self, file_count: int = 50) -> Dict[str, BenchmarkResult]:
        """基准测试：不同比较模式的性能"""
        expected_dir, actual_dir = self.create_test_data(file_count=file_count, file_size_kb=10)
        
        results = {}
        
        for mode in ComparisonMode:
            validator = ExpectedDataValidator(mode)
            
            start_time = time.time()
            result = validator.validate_expected_data(expected_dir, actual_dir)
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            benchmark_result = BenchmarkResult(
                test_name=f"comparison_mode_{mode.value}",
                file_count=file_count,
                total_size_bytes=file_count * 10 * 1024,  # 10KB per file
                execution_time_seconds=execution_time,
                memory_usage_mb=0.0,  # 简化版本，不测量内存
                success_rate=100.0 if result.overall_success else 0.0,
                error_count=len(result.error_messages)
            )
            
            results[mode.value] = benchmark_result
        
        return results
    
    def _run_benchmark(self, test_name: str, file_count: int, file_size_kb: int) -> BenchmarkResult:
        """运行基准测试"""
        expected_dir, actual_dir = self.create_test_data(file_count=file_count, file_size_kb=file_size_kb)
        return self._run_validation_benchmark(test_name, expected_dir, actual_dir, file_count)
    
    def _run_validation_benchmark(self, test_name: str, expected_dir: Path, 
                                 actual_dir: Path, file_count: int) -> BenchmarkResult:
        """运行验证基准测试"""
        # 测量执行时间
        start_time = time.time()
        result = self.validator.validate_expected_data(expected_dir, actual_dir)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 计算总文件大小
        total_size = 0
        for pdf_file in expected_dir.rglob("*.pdf"):
            total_size += pdf_file.stat().st_size
        
        # 计算成功率
        success_rate = (result.files_matched / result.total_files_compared * 100) if result.total_files_compared > 0 else 0.0
        
        return BenchmarkResult(
            test_name=test_name,
            file_count=file_count,
            total_size_bytes=total_size,
            execution_time_seconds=execution_time,
            memory_usage_mb=0.0,  # 简化版本，不测量内存
            success_rate=success_rate,
            error_count=len(result.error_messages)
        )
    
    def run_scalability_test(self, scale_factors: List[int] = None) -> Dict[str, List[BenchmarkResult]]:
        """运行可扩展性测试"""
        if scale_factors is None:
            scale_factors = [1, 10, 50, 100, 500]
        
        results = {}
        
        # 测试不同文件数量
        file_count_results = []
        for scale in scale_factors:
            file_count = scale * 10  # 每个比例因子对应10个文件
            result = self.benchmark_small_files(file_count)
            file_count_results.append(result)
        results["file_count_scalability"] = file_count_results
        
        # 测试不同文件大小
        file_size_results = []
        size_factors = [1, 10, 100, 500]  # KB
        for size_kb in size_factors:
            expected_dir, actual_dir = self.create_test_data(file_count=10, file_size_kb=size_kb)
            result = self._run_validation_benchmark(f"file_size_{size_kb}kb", expected_dir, actual_dir, 10)
            file_size_results.append(result)
        results["file_size_scalability"] = file_size_results
        
        return results
    
    def run_stress_test(self, iterations: int = 10) -> Dict[str, Any]:
        """运行压力测试"""
        execution_times = []
        success_rates = []
        
        for i in range(iterations):
            expected_dir, actual_dir = self.create_test_data(file_count=100, file_size_kb=10)
            
            start_time = time.time()
            result = self.validator.validate_expected_data(expected_dir, actual_dir)
            end_time = time.time()
            
            execution_time = end_time - start_time
            success_rate = (result.files_matched / result.total_files_compared * 100) if result.total_files_compared > 0 else 0.0
            
            execution_times.append(execution_time)
            success_rates.append(success_rate)
        
        return {
            "iterations": iterations,
            "avg_execution_time": statistics.mean(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "std_execution_time": statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0,
            "avg_success_rate": statistics.mean(success_rates),
            "min_success_rate": min(success_rates),
            "max_success_rate": max(success_rates)
        }
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        benchmark_results = {}
        
        try:
            # 小文件基准测试
            small_files_result = self.benchmark_small_files(100)
            benchmark_results["small_files"] = small_files_result
            
            # 中等文件基准测试
            medium_files_result = self.benchmark_medium_files(50)
            benchmark_results["medium_files"] = medium_files_result
            
            # 大文件基准测试
            large_files_result = self.benchmark_large_files(10)
            benchmark_results["large_files"] = large_files_result
            
            # 多公司基准测试
            many_companies_result = self.benchmark_many_companies(10, 10)
            benchmark_results["many_companies"] = many_companies_result
            
            # 深层目录基准测试
            deep_directories_result = self.benchmark_deep_directories(5, 10)
            benchmark_results["deep_directories"] = deep_directories_result
            
            # 比较模式基准测试
            comparison_modes_result = self.benchmark_comparison_modes(50)
            benchmark_results["comparison_modes"] = comparison_modes_result
            
            # 可扩展性测试
            scalability_results = self.run_scalability_test()
            benchmark_results["scalability"] = scalability_results
            
            # 压力测试
            stress_test_results = self.run_stress_test(5)
            benchmark_results["stress_test"] = stress_test_results
            
        except Exception as e:
            benchmark_results["error"] = str(e)
        
        return benchmark_results
    
    def generate_report(self, benchmark_results: Dict[str, Any]) -> str:
        """生成基准测试报告"""
        report_lines = ["# 性能基准测试报告\n"]
        
        # 基本基准测试结果
        basic_tests = ["small_files", "medium_files", "large_files", "many_companies", "deep_directories"]
        
        report_lines.append("## 基本基准测试结果\n")
        report_lines.append("| 测试名称 | 文件数量 | 总大小 (MB) | 执行时间 (秒) | 成功率 (%) |")
        report_lines.append("|---------|---------|------------|--------------|-----------|")
        
        for test_name in basic_tests:
            if test_name in benchmark_results:
                result = benchmark_results[test_name]
                size_mb = result.total_size_bytes / (1024 * 1024)
                report_lines.append(
                    f"| {result.test_name} | {result.file_count} | {size_mb:.2f} | {result.execution_time_seconds:.4f} | {result.success_rate:.1f} |"
                )
        
        # 比较模式性能
        if "comparison_modes" in benchmark_results:
            report_lines.append("\n## 比较模式性能\n")
            report_lines.append("| 比较模式 | 执行时间 (秒) | 成功率 (%) |")
            report_lines.append("|---------|--------------|-----------|")
            
            for mode, result in benchmark_results["comparison_modes"].items():
                report_lines.append(f"| {mode} | {result.execution_time_seconds:.4f} | {result.success_rate:.1f} |")
        
        # 可扩展性测试结果
        if "scalability" in benchmark_results:
            report_lines.append("\n## 可扩展性测试结果\n")
            
            # 文件数量可扩展性
            file_count_results = benchmark_results["scalability"].get("file_count_scalability", [])
            if file_count_results:
                report_lines.append("### 文件数量可扩展性\n")
                report_lines.append("| 文件数量 | 执行时间 (秒) |")
                report_lines.append("|---------|--------------|")
                
                for result in file_count_results:
                    report_lines.append(f"| {result.file_count} | {result.execution_time_seconds:.4f} |")
            
            # 文件大小可扩展性
            file_size_results = benchmark_results["scalability"].get("file_size_scalability", [])
            if file_size_results:
                report_lines.append("\n### 文件大小可扩展性\n")
                report_lines.append("| 文件大小 (KB) | 执行时间 (秒) |")
                report_lines.append("|--------------|--------------|")
                
                for result in file_size_results:
                    size_kb = result.total_size_bytes / (1024 * result.file_count) if result.file_count > 0 else 0
                    report_lines.append(f"| {size_kb:.0f} | {result.execution_time_seconds:.4f} |")
        
        # 压力测试结果
        if "stress_test" in benchmark_results:
            stress_results = benchmark_results["stress_test"]
            report_lines.append("\n## 压力测试结果\n")
            report_lines.append(f"- 迭代次数: {stress_results['iterations']}")
            report_lines.append(f"- 平均执行时间: {stress_results['avg_execution_time']:.4f} 秒")
            report_lines.append(f"- 最小执行时间: {stress_results['min_execution_time']:.4f} 秒")
            report_lines.append(f"- 最大执行时间: {stress_results['max_execution_time']:.4f} 秒")
            report_lines.append(f"- 执行时间标准差: {stress_results['std_execution_time']:.4f} 秒")
            report_lines.append(f"- 平均成功率: {stress_results['avg_success_rate']:.1f}%")
        
        return "\n".join(report_lines)


# 性能基准测试运行器
performance_benchmark_tester = PerformanceBenchmarkTester()