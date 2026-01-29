#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
监控系统集成测试
验证测试执行监控、覆盖率监控和性能监控的集成功能
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.monitoring.test_execution_monitor import (
        TestExecutionMonitor,
        TestStatus,
        get_global_monitor,
    )
except ImportError:
    # 回退方案
    TestExecutionMonitor = None
    TestStatus = None
    get_global_monitor = None

try:
    from tests.monitoring.coverage_monitor import (
        CoverageMetrics,
        CoverageMonitor,
        CoverageStatus,
        get_global_coverage_monitor,
    )
except ImportError:
    CoverageMonitor = None
    CoverageStatus = None
    CoverageMetrics = None
    get_global_coverage_monitor = None

try:
    from tests.monitoring.performance_monitor import (
        PerformanceMonitor,
        PerformanceStatus,
        get_global_performance_monitor,
    )
except ImportError:
    PerformanceMonitor = None
    PerformanceStatus = None
    get_global_performance_monitor = None


class TestMonitoringIntegration:
    """监控系统集成测试"""

    def setup_method(self):
        """测试初始化"""
        self.test_output_dir = "test_monitoring_output"
        Path(self.test_output_dir).mkdir(exist_ok=True)

    def teardown_method(self):
        """测试清理"""
        import shutil

        if Path(self.test_output_dir).exists():
            shutil.rmtree(self.test_output_dir)

    def test_execution_monitor_basic_functionality(self):
        """测试执行监控器基本功能"""
        monitor = TestExecutionMonitor(output_dir=self.test_output_dir)

        # 开始监控测试
        test_id = monitor.start_test(
            "test_example_1", "test_basic_functionality", "tests/unit/test_example.py"
        )

        # 模拟测试执行
        time.sleep(0.1)

        # 结束监控测试
        monitor.end_test(test_id, TestStatus.PASSED)

        # 验证测试状态
        status = monitor.get_test_status(test_id)
        assert status is not None
        assert status["status"] == TestStatus.PASSED.value
        assert status["execution_time"] > 0

        # 验证统计信息
        stats = monitor.get_stats()
        assert stats["total_tests"] == 1
        assert stats["passed_tests"] == 1

    def test_execution_monitor_error_handling(self):
        """测试执行监控器错误处理"""
        monitor = TestExecutionMonitor(output_dir=self.test_output_dir)

        # 开始监控测试
        test_id = monitor.start_test(
            "test_example_2", "test_error_handling", "tests/unit/test_example.py"
        )

        # 模拟测试执行
        time.sleep(0.1)

        # 结束监控测试（失败）
        error_message = "Assertion error: expected True but got False"
        monitor.end_test(test_id, TestStatus.FAILED, error_message)

        # 验证错误信息
        status = monitor.get_test_status(test_id)
        assert status["status"] == TestStatus.FAILED.value
        assert status["error_message"] == error_message

    def test_execution_monitor_report_generation(self):
        """测试执行监控器报告生成"""
        monitor = TestExecutionMonitor(output_dir=self.test_output_dir)

        # 记录多个测试
        test_ids = []
        for i in range(3):
            test_id = monitor.start_test(
                f"test_{i}", f"test_report_generation_{i}", "tests/unit/test_example.py"
            )
            time.sleep(0.05)
            monitor.end_test(test_id, TestStatus.PASSED)
            test_ids.append(test_id)

        # 生成报告
        report_path = monitor.save_report()
        assert report_path is not None
        assert Path(report_path).exists()

        # 验证报告内容
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert "test_statistics" in report
        assert report["test_statistics"]["total_tests"] == 3
        assert report["test_statistics"]["passed_tests"] == 3

    @patch("subprocess.run")
    def test_coverage_monitor_basic_functionality(self, mock_subprocess):
        """测试覆盖率监控器基本功能"""
        # 模拟subprocess.run返回成功
        mock_subprocess.return_value = Mock(returncode=0)

        monitor = CoverageMonitor(source_dir="src", output_dir=self.test_output_dir)

        # 直接测试覆盖率计算逻辑，不依赖复杂的mock
        with patch.object(monitor, "_calculate_coverage_metrics") as mock_calculate:
            # 模拟覆盖率计算结果
            mock_calculate.return_value = CoverageMetrics(
                timestamp=time.time(),
                overall_coverage=85.0,
                line_coverage=85.0,
                branch_coverage=68.0,
                function_coverage=76.5,
                total_lines=100,
                covered_lines=85,
                total_branches=50,
                covered_branches=34,
                total_functions=10,
                covered_functions=8,
            )

            # 测量覆盖率
            metrics = monitor.measure_coverage()

            # 验证覆盖率指标
            assert metrics.overall_coverage == 85.0
            assert metrics.status == CoverageStatus.GOOD

    def test_coverage_monitor_quality_check(self):
        """测试覆盖率监控器质量检查"""
        monitor = CoverageMonitor(output_dir=self.test_output_dir)

        # 模拟覆盖率数据
        with patch.object(monitor, "_coverage_data", new=[]):
            # 添加模拟的覆盖率指标
            from tests.monitoring.coverage_monitor import CoverageMetrics

            # 添加高覆盖率数据
            high_coverage = CoverageMetrics(
                timestamp=time.time(),
                overall_coverage=85.0,
                line_coverage=85.0,
                branch_coverage=68.0,
                function_coverage=76.5,
                total_lines=100,
                covered_lines=85,
                total_branches=50,
                covered_branches=34,
                total_functions=10,
                covered_functions=8,
            )
            monitor._coverage_data.append(high_coverage)

            # 检查质量
            quality = monitor.check_coverage_quality()
            assert quality["current_coverage"] == 85.0
            assert quality["meets_target"] == True  # 85% >= 80%
            assert quality["status"] == "good"

    def test_performance_monitor_basic_functionality(self):
        """测试性能监控器基本功能"""
        monitor = PerformanceMonitor(output_dir=self.test_output_dir)

        # 记录性能指标
        metrics = monitor.record_performance(
            "test_performance_1", execution_time=2.5, memory_usage=50.2, cpu_usage=15.3
        )

        # 验证性能指标
        assert metrics.test_name == "test_performance_1"
        assert metrics.execution_time == 2.5
        assert metrics.memory_usage == 50.2
        assert metrics.cpu_usage == 15.3
        assert metrics.is_valid

    def test_performance_monitor_baseline_creation(self):
        """测试性能监控器基准创建"""
        monitor = PerformanceMonitor(output_dir=self.test_output_dir)

        # 记录多个性能指标（达到基准样本大小）
        for i in range(10):
            monitor.record_performance(
                "test_baseline",
                execution_time=2.0 + (i * 0.1),  # 轻微变化
                memory_usage=50.0,
                cpu_usage=15.0,
            )

        # 验证基准已创建
        baseline = monitor.get_baseline("test_baseline")
        assert baseline is not None
        assert baseline.test_name == "test_baseline"
        assert baseline.sample_count == 10

    def test_performance_monitor_regression_detection(self):
        """测试性能监控器回归检测"""
        monitor = PerformanceMonitor(output_dir=self.test_output_dir)

        # 手动设置基准
        monitor.set_baseline_manually(
            "test_regression", execution_time=2.0, memory_usage=50.0, cpu_usage=15.0
        )

        # 记录性能回归（执行时间增加100%）
        metrics = monitor.record_performance(
            "test_regression",
            execution_time=4.0,  # 100%增加
            memory_usage=50.0,
            cpu_usage=15.0,
        )

        # 检查性能
        check = monitor.check_performance("test_regression", metrics)
        assert check["status"] == PerformanceStatus.DEGRADED.value
        assert not check["within_thresholds"]["execution_time"]

    def test_global_monitors_integration(self):
        """测试全局监控器集成"""
        # 获取全局监控器实例
        execution_monitor = get_global_monitor()
        coverage_monitor = get_global_coverage_monitor()
        performance_monitor = get_global_performance_monitor()

        # 验证实例创建
        assert execution_monitor is not None
        assert coverage_monitor is not None
        assert performance_monitor is not None

        # 验证实例单例模式
        execution_monitor2 = get_global_monitor()
        assert execution_monitor is execution_monitor2

    def test_monitoring_system_end_to_end(self):
        """测试监控系统端到端功能"""
        # 创建临时监控器
        execution_monitor = TestExecutionMonitor(output_dir=self.test_output_dir)
        performance_monitor = PerformanceMonitor(output_dir=self.test_output_dir)

        # 模拟完整的测试执行流程
        test_name = "test_end_to_end"
        file_path = "tests/integration/test_monitoring.py"

        # 1. 开始监控测试执行
        test_id = execution_monitor.start_test(
            f"{file_path}::{test_name}", test_name, file_path
        )

        # 2. 记录性能指标
        start_time = time.time()

        # 模拟测试执行
        time.sleep(0.2)

        execution_time = time.time() - start_time
        performance_metrics = performance_monitor.record_performance(
            test_name, execution_time=execution_time, memory_usage=45.5, cpu_usage=12.3
        )

        # 3. 结束监控测试执行
        execution_monitor.end_test(test_id, TestStatus.PASSED)

        # 4. 验证监控数据
        execution_status = execution_monitor.get_test_status(test_id)
        assert execution_status["status"] == TestStatus.PASSED.value
        assert execution_status["execution_time"] > 0

        performance_check = performance_monitor.check_performance(
            test_name, performance_metrics
        )
        assert performance_check is not None

        # 5. 生成报告
        execution_report_path = execution_monitor.save_report(
            "test_execution_report.json"
        )
        performance_report_path = performance_monitor.save_report(
            "test_performance_report.json"
        )

        assert Path(execution_report_path).exists()
        assert Path(performance_report_path).exists()

    def test_monitoring_error_resilience(self):
        """测试监控系统错误恢复能力"""
        monitor = TestExecutionMonitor(output_dir=self.test_output_dir)

        # 测试无效操作
        monitor.end_test("nonexistent_test", TestStatus.PASSED)  # 应该不会崩溃

        # 测试无效状态获取
        status = monitor.get_test_status("nonexistent_test")
        assert status is None

        # 测试空统计信息
        stats = monitor.get_stats()
        assert stats["total_tests"] == 0

    def test_monitoring_configuration_validation(self):
        """测试监控系统配置验证"""
        # 测试执行监控器配置
        execution_monitor = TestExecutionMonitor(output_dir=self.test_output_dir)
        assert "max_execution_time" in execution_monitor.config
        assert execution_monitor.config["max_execution_time"] == 60.0

        # 测试覆盖率监控器配置
        coverage_monitor = CoverageMonitor(output_dir=self.test_output_dir)
        assert "target_coverage" in coverage_monitor.config
        assert coverage_monitor.config["target_coverage"] == 80.0

        # 测试性能监控器配置
        performance_monitor = PerformanceMonitor(output_dir=self.test_output_dir)
        assert "baseline_sample_size" in performance_monitor.config
        assert performance_monitor.config["baseline_sample_size"] == 10

    def test_monitoring_data_persistence(self):
        """测试监控数据持久化"""
        performance_monitor = PerformanceMonitor(output_dir=self.test_output_dir)

        # 记录一些性能数据
        for i in range(5):
            performance_monitor.record_performance(
                f"test_persistence_{i}",
                execution_time=1.0 + i * 0.1,
                memory_usage=40.0 + i * 2,
                cpu_usage=10.0 + i * 1,
            )

        # 手动设置一个基准
        performance_monitor.set_baseline_manually(
            "test_manual_baseline",
            execution_time=2.0,
            memory_usage=50.0,
            cpu_usage=15.0,
        )

        # 验证基准已保存
        baseline_file = Path(self.test_output_dir) / "performance_baselines.json"
        assert baseline_file.exists()

        # 重新创建监控器（模拟重启）
        performance_monitor2 = PerformanceMonitor(output_dir=self.test_output_dir)

        # 验证基准已加载
        baseline = performance_monitor2.get_baseline("test_manual_baseline")
        assert baseline is not None
        assert baseline.execution_time == 2.0


if __name__ == "__main__":
    # 运行集成测试
    pytest.main([__file__, "-v"])
