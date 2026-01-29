#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源使用监控测试模块
监控期待数据验证框架的资源使用情况
包括内存使用、CPU使用、文件句柄等资源指标
"""

import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psutil

from tests.validation.expected_data_validator import ExpectedDataValidator


@dataclass
class ResourceUsage:
    """资源使用情况"""

    memory_usage_mb: float
    cpu_percent: float
    file_handles: int
    execution_time_seconds: float
    peak_memory_mb: float


@dataclass
class ResourceMonitoringResult:
    """资源监控结果"""

    test_name: str
    file_count: int
    total_size_bytes: int
    resource_usage: ResourceUsage
    success_rate: float
    error_count: int


class ResourceMonitor:
    """资源监控器"""

    def __init__(self, process=None):
        """初始化资源监控器"""
        self.process = process or psutil.Process()
        self.monitoring_data = []
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self, interval: float = 0.1):
        """开始监控"""
        self.monitoring = True
        self.monitoring_data = []

        def monitor_loop():
            while self.monitoring:
                try:
                    memory_info = self.process.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)  # 转换为MB
                    cpu_percent = self.process.cpu_percent()

                    # 获取文件句柄数量（Windows上使用句柄数）
                    try:
                        file_handles = len(self.process.open_files())
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        file_handles = 0

                    self.monitoring_data.append(
                        {
                            "timestamp": time.time(),
                            "memory_mb": memory_mb,
                            "cpu_percent": cpu_percent,
                            "file_handles": file_handles,
                        }
                    )

                    time.sleep(interval)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> ResourceUsage:
        """停止监控并返回结果"""
        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        if not self.monitoring_data:
            return ResourceUsage(0.0, 0.0, 0, 0.0, 0.0)

        # 计算统计信息
        memory_values = [data["memory_mb"] for data in self.monitoring_data]
        cpu_values = [data["cpu_percent"] for data in self.monitoring_data]
        file_handles_values = [data["file_handles"] for data in self.monitoring_data]

        avg_memory = sum(memory_values) / len(memory_values)
        avg_cpu = sum(cpu_values) / len(cpu_values)
        avg_file_handles = sum(file_handles_values) / len(file_handles_values)
        peak_memory = max(memory_values)

        execution_time = (
            self.monitoring_data[-1]["timestamp"] - self.monitoring_data[0]["timestamp"]
        )

        return ResourceUsage(
            memory_usage_mb=avg_memory,
            cpu_percent=avg_cpu,
            file_handles=int(avg_file_handles),
            execution_time_seconds=execution_time,
            peak_memory_mb=peak_memory,
        )

    def get_monitoring_data(self) -> List[Dict[str, Any]]:
        """获取监控数据"""
        return self.monitoring_data.copy()


class ResourceMonitoringTester:
    """资源使用监控测试器"""

    def __init__(self):
        """初始化资源监控测试器"""
        self.validator = ExpectedDataValidator()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.monitor = ResourceMonitor()

    def cleanup(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_data(
        self, file_count: int, file_size_kb: int = 10
    ) -> Tuple[Path, Path]:
        """创建测试数据"""
        expected_dir = self.temp_dir / f"expected_{file_count}_{file_size_kb}kb"
        actual_dir = self.temp_dir / f"actual_{file_count}_{file_size_kb}kb"

        expected_dir.mkdir(parents=True, exist_ok=True)
        actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建公司目录
        company_expected_dir = expected_dir / "test_company"
        company_actual_dir = actual_dir / "test_company"

        company_expected_dir.mkdir(parents=True, exist_ok=True)
        company_actual_dir.mkdir(parents=True, exist_ok=True)

        # 创建文件
        for i in range(file_count):
            content = self._generate_file_content(file_size_kb * 1024)

            expected_file = company_expected_dir / f"file_{i:06d}.pdf"
            actual_file = company_actual_dir / f"file_{i:06d}.pdf"

            with open(expected_file, "wb") as f:
                f.write(content)
            with open(actual_file, "wb") as f:
                f.write(content)

        return expected_dir, actual_dir

    def _generate_file_content(self, size_bytes: int) -> bytes:
        """生成文件内容"""
        pdf_header = b"%PDF-1.4\n"
        pdf_footer = b"%%EOF\n"

        base_content = b"Resource monitoring test content\n"

        padding_size = (
            size_bytes - len(pdf_header) - len(base_content) - len(pdf_footer)
        )
        if padding_size > 0:
            padding = b"x" * padding_size
        else:
            padding = b""

        return pdf_header + base_content + padding + pdf_footer

    def monitor_memory_usage(self, file_count: int = 50) -> ResourceMonitoringResult:
        """监控内存使用情况"""
        return self._run_resource_monitoring("memory_usage", file_count)

    def monitor_cpu_usage(self, file_count: int = 100) -> ResourceMonitoringResult:
        """监控CPU使用情况"""
        return self._run_resource_monitoring("cpu_usage", file_count)

    def monitor_file_handles(self, file_count: int = 50) -> ResourceMonitoringResult:
        """监控文件句柄使用情况"""
        return self._run_resource_monitoring("file_handles", file_count)

    def monitor_large_dataset(self, file_count: int = 200) -> ResourceMonitoringResult:
        """监控大数据集的资源使用"""
        return self._run_resource_monitoring("large_dataset", file_count)

    def monitor_stress_scenario(self, iterations: int = 10) -> Dict[str, Any]:
        """监控压力场景的资源使用"""
        memory_usage = []
        cpu_usage = []
        execution_times = []

        for i in range(iterations):
            expected_dir, actual_dir = self.create_test_data(
                file_count=50, file_size_kb=10
            )

            # 开始监控
            self.monitor.start_monitoring()

            start_time = time.time()
            result = self.validator.validate_expected_data(expected_dir, actual_dir)
            end_time = time.time()

            # 停止监控
            resource_usage = self.monitor.stop_monitoring()

            memory_usage.append(resource_usage.memory_usage_mb)
            cpu_usage.append(resource_usage.cpu_percent)
            execution_times.append(end_time - start_time)

        return {
            "iterations": iterations,
            "avg_memory_usage_mb": sum(memory_usage) / len(memory_usage),
            "max_memory_usage_mb": max(memory_usage),
            "avg_cpu_percent": sum(cpu_usage) / len(cpu_usage),
            "max_cpu_percent": max(cpu_usage),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "memory_leak_detected": self._detect_memory_leak(memory_usage),
        }

    def _detect_memory_leak(self, memory_usage: List[float]) -> bool:
        """检测内存泄漏"""
        if len(memory_usage) < 3:
            return False

        # 简单的内存泄漏检测：检查内存使用是否持续增长
        first_half_avg = sum(memory_usage[: len(memory_usage) // 2]) / (
            len(memory_usage) // 2
        )
        second_half_avg = sum(memory_usage[len(memory_usage) // 2 :]) / (
            len(memory_usage) - len(memory_usage) // 2
        )

        # 如果后半段平均内存使用比前半段高10%，认为可能有内存泄漏
        return second_half_avg > first_half_avg * 1.1

    def _run_resource_monitoring(
        self, test_name: str, file_count: int
    ) -> ResourceMonitoringResult:
        """运行资源监控测试"""
        expected_dir, actual_dir = self.create_test_data(
            file_count=file_count, file_size_kb=10
        )

        # 开始监控
        self.monitor.start_monitoring()

        # 执行验证
        start_time = time.time()
        result = self.validator.validate_expected_data(expected_dir, actual_dir)
        end_time = time.time()

        # 停止监控
        resource_usage = self.monitor.stop_monitoring()

        # 计算总文件大小
        total_size = 0
        for pdf_file in expected_dir.rglob("*.pdf"):
            total_size += pdf_file.stat().st_size

        # 计算成功率
        success_rate = (
            (result.files_matched / result.total_files_compared * 100)
            if result.total_files_compared > 0
            else 0.0
        )

        return ResourceMonitoringResult(
            test_name=test_name,
            file_count=file_count,
            total_size_bytes=total_size,
            resource_usage=resource_usage,
            success_rate=success_rate,
            error_count=len(result.error_messages),
        )

    def run_comprehensive_monitoring(self) -> Dict[str, Any]:
        """运行全面的资源监控"""
        monitoring_results = {}

        try:
            # 内存使用监控
            memory_result = self.monitor_memory_usage(50)
            monitoring_results["memory_usage"] = memory_result

            # CPU使用监控
            cpu_result = self.monitor_cpu_usage(100)
            monitoring_results["cpu_usage"] = cpu_result

            # 文件句柄监控
            file_handles_result = self.monitor_file_handles(50)
            monitoring_results["file_handles"] = file_handles_result

            # 大数据集监控
            large_dataset_result = self.monitor_large_dataset(200)
            monitoring_results["large_dataset"] = large_dataset_result

            # 压力测试监控
            stress_results = self.monitor_stress_scenario(5)
            monitoring_results["stress_test"] = stress_results

        except Exception as e:
            monitoring_results["error"] = str(e)

        return monitoring_results

    def generate_monitoring_report(self, monitoring_results: Dict[str, Any]) -> str:
        """生成监控报告"""
        report_lines = ["# 资源使用监控报告\n"]

        # 基本监控结果
        basic_tests = ["memory_usage", "cpu_usage", "file_handles", "large_dataset"]

        report_lines.append("## 基本资源监控结果\n")
        report_lines.append(
            "| 测试名称 | 文件数量 | 内存使用 (MB) | CPU使用 (%) | 文件句柄 | 执行时间 (秒) | 峰值内存 (MB) |"
        )
        report_lines.append(
            "|---------|---------|--------------|------------|----------|--------------|--------------|"
        )

        for test_name in basic_tests:
            if test_name in monitoring_results:
                result = monitoring_results[test_name]
                resource = result.resource_usage

                report_lines.append(
                    f"| {result.test_name} | {result.file_count} | {resource.memory_usage_mb:.2f} | "
                    f"{resource.cpu_percent:.1f} | {resource.file_handles} | {resource.execution_time_seconds:.4f} | "
                    f"{resource.peak_memory_mb:.2f} |"
                )

        # 压力测试结果
        if "stress_test" in monitoring_results:
            stress_results = monitoring_results["stress_test"]
            report_lines.append("\n## 压力测试结果\n")
            report_lines.append(f"- 迭代次数: {stress_results['iterations']}")
            report_lines.append(
                f"- 平均内存使用: {stress_results['avg_memory_usage_mb']:.2f} MB"
            )
            report_lines.append(
                f"- 最大内存使用: {stress_results['max_memory_usage_mb']:.2f} MB"
            )
            report_lines.append(
                f"- 平均CPU使用: {stress_results['avg_cpu_percent']:.1f}%"
            )
            report_lines.append(
                f"- 最大CPU使用: {stress_results['max_cpu_percent']:.1f}%"
            )
            report_lines.append(
                f"- 平均执行时间: {stress_results['avg_execution_time']:.4f} 秒"
            )
            report_lines.append(
                f"- 内存泄漏检测: {'是' if stress_results['memory_leak_detected'] else '否'}"
            )

        # 资源使用建议
        report_lines.append("\n## 资源使用建议\n")

        if "memory_usage" in monitoring_results:
            memory_result = monitoring_results["memory_usage"]
            if memory_result.resource_usage.peak_memory_mb > 100:
                report_lines.append("- ⚠️ 内存使用较高，建议优化大文件处理")
            else:
                report_lines.append("- ✅ 内存使用正常")

        if "cpu_usage" in monitoring_results:
            cpu_result = monitoring_results["cpu_usage"]
            if cpu_result.resource_usage.cpu_percent > 50:
                report_lines.append("- ⚠️ CPU使用较高，建议优化计算密集型操作")
            else:
                report_lines.append("- ✅ CPU使用正常")

        if "stress_test" in monitoring_results:
            stress_results = monitoring_results["stress_test"]
            if stress_results["memory_leak_detected"]:
                report_lines.append("- ❌ 检测到可能的内存泄漏，需要进一步调查")
            else:
                report_lines.append("- ✅ 未检测到内存泄漏")

        return "\n".join(report_lines)


# 资源监控测试运行器
resource_monitoring_tester = ResourceMonitoringTester()
