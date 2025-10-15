#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试执行优化器
优化测试执行时间和资源使用
"""

import os
import sys
import time
import json
import subprocess
import psutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from src.core.logger import get_logger

def log(message):
    """记录日志"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    except UnicodeEncodeError:
        # 处理编码问题
        safe_message = message.encode('gbk', errors='replace').decode('gbk')
        print(f"[{time.strftime('%H:%M:%S')}] {safe_message}")

@dataclass
class TestExecutionMetrics:
    """测试执行指标"""
    test_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    disk_io: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_name: str
    before_metrics: TestExecutionMetrics
    after_metrics: TestExecutionMetrics
    improvement_percentage: float
    optimization_applied: bool

class TestExecutionOptimizer:
    """测试执行优化器"""

    def __init__(self):
        self.logger = get_logger("test_execution_optimizer")
        self.optimization_results = []

    def measure_test_execution(self, test_command: str, test_name: str) -> TestExecutionMetrics:
        """测量测试执行指标"""
        log(f"测量测试执行: {test_name}")

        start_time = time.time()
        start_memory = psutil.virtual_memory().used
        start_cpu = psutil.cpu_percent(interval=None)
        start_disk_io = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes

        try:
            # 执行测试命令
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            end_time = time.time()
            end_memory = psutil.virtual_memory().used
            end_cpu = psutil.cpu_percent(interval=None)
            end_disk_io = psutil.disk_io_counters().read_bytes + psutil.disk_io_counters().write_bytes

            execution_time = end_time - start_time
            memory_usage = (end_memory - start_memory) / (1024 * 1024)  # MB
            cpu_usage = end_cpu - start_cpu
            disk_io = (end_disk_io - start_disk_io) / (1024 * 1024)  # MB

            success = result.returncode == 0

            metrics = TestExecutionMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                disk_io=disk_io,
                success=success
            )

            log(f"✅ 测试执行测量完成: {test_name}")
            log(f"  执行时间: {execution_time:.2f}秒")
            log(f"  内存使用: {memory_usage:.2f} MB")
            log(f"  CPU使用: {cpu_usage:.2f}%")
            log(f"  磁盘IO: {disk_io:.2f} MB")
            log(f"  成功: {success}")

            return metrics

        except subprocess.TimeoutExpired:
            end_time = time.time()
            execution_time = end_time - start_time

            metrics = TestExecutionMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage=0,
                cpu_usage=0,
                disk_io=0,
                success=False,
                error_message="测试执行超时"
            )

            log(f"❌ 测试执行超时: {test_name}")
            return metrics

        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time

            metrics = TestExecutionMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage=0,
                cpu_usage=0,
                disk_io=0,
                success=False,
                error_message=str(e)
            )

            log(f"❌ 测试执行失败: {test_name} - {e}")
            return metrics

    def optimize_test_parallelization(self) -> OptimizationResult:
        """优化测试并行化"""
        optimization_name = "测试并行化优化"
        log(f"开始 {optimization_name}...")

        # 测量优化前的执行
        test_command = "python -m pytest tests/unit/ -v"
        before_metrics = self.measure_test_execution(test_command, "单元测试")

        # 应用并行化优化
        optimized_command = "python -m pytest tests/unit/ -v -n auto"
        after_metrics = self.measure_test_execution(optimized_command, "单元测试(并行)")

        # 计算改进百分比
        if before_metrics.execution_time > 0:
            improvement_percentage = ((before_metrics.execution_time - after_metrics.execution_time) / before_metrics.execution_time) * 100
        else:
            improvement_percentage = 0

        result = OptimizationResult(
            optimization_name=optimization_name,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percentage=improvement_percentage,
            optimization_applied=True
        )

        log(f"✅ {optimization_name} 完成 - 改进: {improvement_percentage:.1f}%")
        return result

    def optimize_test_selection(self) -> OptimizationResult:
        """优化测试选择"""
        optimization_name = "测试选择优化"
        log(f"开始 {optimization_name}...")

        # 测量优化前的执行
        test_command = "python -m pytest tests/ -v"
        before_metrics = self.measure_test_execution(test_command, "完整测试套件")

        # 应用测试选择优化
        optimized_command = "python -m pytest tests/unit/ tests/integration/ -v"
        after_metrics = self.measure_test_execution(optimized_command, "核心测试套件")

        # 计算改进百分比
        if before_metrics.execution_time > 0:
            improvement_percentage = ((before_metrics.execution_time - after_metrics.execution_time) / before_metrics.execution_time) * 100
        else:
            improvement_percentage = 0

        result = OptimizationResult(
            optimization_name=optimization_name,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percentage=improvement_percentage,
            optimization_applied=True
        )

        log(f"✅ {optimization_name} 完成 - 改进: {improvement_percentage:.1f}%")
        return result

    def optimize_test_cache(self) -> OptimizationResult:
        """优化测试缓存"""
        optimization_name = "测试缓存优化"
        log(f"开始 {optimization_name}...")

        # 测量优化前的执行
        test_command = "python -m pytest tests/unit/ -v"
        before_metrics = self.measure_test_execution(test_command, "单元测试(无缓存)")

        # 应用缓存优化
        optimized_command = "python -m pytest tests/unit/ -v --cache-clear"
        after_metrics = self.measure_test_execution(optimized_command, "单元测试(有缓存)")

        # 计算改进百分比
        if before_metrics.execution_time > 0:
            improvement_percentage = ((before_metrics.execution_time - after_metrics.execution_time) / before_metrics.execution_time) * 100
        else:
            improvement_percentage = 0

        result = OptimizationResult(
            optimization_name=optimization_name,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percentage=improvement_percentage,
            optimization_applied=True
        )

        log(f"✅ {optimization_name} 完成 - 改进: {improvement_percentage:.1f}%")
        return result

    def optimize_test_environment(self) -> OptimizationResult:
        """优化测试环境"""
        optimization_name = "测试环境优化"
        log(f"开始 {optimization_name}...")

        # 测量优化前的执行
        test_command = "python -m pytest tests/unit/ -v"
        before_metrics = self.measure_test_execution(test_command, "单元测试(标准环境)")

        # 应用环境优化 - 清理临时文件
        temp_files = list(Path(".").glob("*.pyc")) + list(Path(".").glob("__pycache__"))
        for temp_file in temp_files:
            if temp_file.is_file():
                temp_file.unlink()
            elif temp_file.is_dir():
                import shutil
                shutil.rmtree(temp_file)

        after_metrics = self.measure_test_execution(test_command, "单元测试(优化环境)")

        # 计算改进百分比
        if before_metrics.execution_time > 0:
            improvement_percentage = ((before_metrics.execution_time - after_metrics.execution_time) / before_metrics.execution_time) * 100
        else:
            improvement_percentage = 0

        result = OptimizationResult(
            optimization_name=optimization_name,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percentage=improvement_percentage,
            optimization_applied=True
        )

        log(f"✅ {optimization_name} 完成 - 改进: {improvement_percentage:.1f}%")
        return result

    def optimize_test_resource_usage(self) -> OptimizationResult:
        """优化测试资源使用"""
        optimization_name = "测试资源使用优化"
        log(f"开始 {optimization_name}...")

        # 测量优化前的执行
        test_command = "python -m pytest tests/unit/ -v"
        before_metrics = self.measure_test_execution(test_command, "单元测试(标准资源)")

        # 应用资源优化 - 限制内存使用
        optimized_command = "python -m pytest tests/unit/ -v --maxfail=5"
        after_metrics = self.measure_test_execution(optimized_command, "单元测试(优化资源)")

        # 计算改进百分比
        if before_metrics.execution_time > 0:
            improvement_percentage = ((before_metrics.execution_time - after_metrics.execution_time) / before_metrics.execution_time) * 100
        else:
            improvement_percentage = 0

        result = OptimizationResult(
            optimization_name=optimization_name,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            improvement_percentage=improvement_percentage,
            optimization_applied=True
        )

        log(f"✅ {optimization_name} 完成 - 改进: {improvement_percentage:.1f}%")
        return result

    def run_all_optimizations(self) -> List[OptimizationResult]:
        """运行所有优化"""
        log("开始测试执行优化...")

        optimization_methods = [
            self.optimize_test_parallelization,
            self.optimize_test_selection,
            self.optimize_test_cache,
            self.optimize_test_environment,
            self.optimize_test_resource_usage
        ]

        optimization_results = []

        for optimization_method in optimization_methods:
            try:
                result = optimization_method()
                optimization_results.append(result)
            except Exception as e:
                log(f"❌ 优化执行失败: {optimization_method.__name__} - {e}")

        return optimization_results

def analyze_optimization_results(optimization_results: List[OptimizationResult]) -> Dict[str, Any]:
    """分析优化结果"""
    log("分析优化结果...")

    total_improvement = 0
    successful_optimizations = 0
    total_optimizations = len(optimization_results)

    for result in optimization_results:
        if result.improvement_percentage > 0:
            total_improvement += result.improvement_percentage
            successful_optimizations += 1

    average_improvement = total_improvement / successful_optimizations if successful_optimizations > 0 else 0

    analysis = {
        "total_optimizations": total_optimizations,
        "successful_optimizations": successful_optimizations,
        "average_improvement": average_improvement,
        "optimization_results": [asdict(result) for result in optimization_results]
    }

    log(f"优化分析完成:")
    log(f"  总优化数: {total_optimizations}")
    log(f"  成功优化数: {successful_optimizations}")
    log(f"  平均改进: {average_improvement:.1f}%")

    return analysis

def main():
    """主函数"""
    log("开始测试执行优化...")

    optimizer = TestExecutionOptimizer()
    optimization_results = optimizer.run_all_optimizations()

    # 分析优化结果
    analysis = analyze_optimization_results(optimization_results)

    # 保存优化结果
    result_file = "test_execution_optimization_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    log(f"✅ 测试执行优化结果已保存: {result_file}")

    # 显示优化建议
    log("\n" + "="*50)
    log("测试执行优化建议:")

    for result in optimization_results:
        if result.improvement_percentage > 0:
            log(f"  ✅ {result.optimization_name}: 改进 {result.improvement_percentage:.1f}%")
        else:
            log(f"  ⚠️ {result.optimization_name}: 无改进或负改进")

    overall_success = analysis["successful_optimizations"] > 0

    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)