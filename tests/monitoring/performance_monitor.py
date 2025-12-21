#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能基准监控系统
监控测试执行性能，建立性能基准，检测性能回归
"""

import time
import psutil
import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.logger import get_logger
except ImportError:
    import logging
    get_logger = logging.getLogger

logger = get_logger(__name__)


class PerformanceStatus(Enum):
    """性能状态枚举"""
    EXCELLENT = "excellent"    # 性能优于基准
    GOOD = "good"             # 性能接近基准
    ACCEPTABLE = "acceptable"  # 性能在容忍范围内
    DEGRADED = "degraded"     # 性能明显下降
    CRITICAL = "critical"     # 性能严重下降


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    test_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    throughput: float
    error_rate: float

    @property
    def is_valid(self) -> bool:
        """指标是否有效"""
        return (
            self.execution_time > 0 and
            self.memory_usage >= 0 and
            self.cpu_usage >= 0 and
            self.throughput >= 0 and
            0 <= self.error_rate <= 1
        )


@dataclass
class PerformanceBaseline:
    """性能基准"""
    test_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    throughput: float
    error_rate: float
    sample_count: int
    standard_deviation: float
    created_at: float
    updated_at: float

    @property
    def execution_time_threshold(self) -> float:
        """执行时间阈值"""
        return self.execution_time * 1.5  # 允许50%的性能下降

    @property
    def memory_usage_threshold(self) -> float:
        """内存使用阈值"""
        return self.memory_usage * 1.3  # 允许30%的内存增加


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, output_dir: str = "performance_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.logger = get_logger("PerformanceMonitor")
        self._performance_data: Dict[str, List[PerformanceMetrics]] = {}
        self._baselines: Dict[str, PerformanceBaseline] = {}

        # 监控配置
        self.config = {
            'baseline_sample_size': 10,
            'performance_threshold_factor': 1.5,
            'memory_threshold_factor': 1.3,
            'cpu_threshold_factor': 1.5,
            'enable_auto_baseline': True,
            'trend_analysis_window': 20
        }

        # 统计信息
        self.stats = {
            'total_tests_monitored': 0,
            'tests_with_baseline': 0,
            'performance_regressions': [],
            'performance_improvements': [],
            'average_execution_time': 0.0,
            'worst_performing_tests': []
        }

        # 加载现有基准
        self._load_baselines()

        self.logger.info("性能监控器初始化完成")

    def record_performance(self, test_name: str, execution_time: float,
                          memory_usage: Optional[float] = None,
                          cpu_usage: Optional[float] = None,
                          throughput: float = 0.0,
                          error_rate: float = 0.0) -> PerformanceMetrics:
        """记录性能指标"""
        # 自动测量资源使用（如果未提供）
        if memory_usage is None or cpu_usage is None:
            memory_usage, cpu_usage = self._measure_resource_usage()

        metrics = PerformanceMetrics(
            timestamp=time.time(),
            test_name=test_name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            throughput=throughput,
            error_rate=error_rate
        )

        # 存储性能数据
        if test_name not in self._performance_data:
            self._performance_data[test_name] = []
        self._performance_data[test_name].append(metrics)

        # 更新统计信息
        self._update_stats()

        # 自动更新基准（如果启用）
        if self.config['enable_auto_baseline']:
            self._update_baseline(test_name)

        self.logger.debug(f"记录性能指标: {test_name} - {execution_time:.2f}s")
        return metrics

    def _measure_resource_usage(self) -> Tuple[float, float]:
        """测量资源使用情况"""
        try:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
            return memory_usage, cpu_usage
        except Exception as e:
            self.logger.warning(f"资源测量失败: {e}")
            return 0.0, 0.0

    def _update_baseline(self, test_name: str):
        """更新性能基准"""
        if test_name not in self._performance_data:
            return

        metrics_list = self._performance_data[test_name]
        if len(metrics_list) < self.config['baseline_sample_size']:
            return

        # 获取最近的样本
        recent_metrics = metrics_list[-self.config['baseline_sample_size']:]

        # 计算平均值和标准差
        execution_times = [m.execution_time for m in recent_metrics]
        memory_usages = [m.memory_usage for m in recent_metrics]
        cpu_usages = [m.cpu_usage for m in recent_metrics]
        throughputs = [m.throughput for m in recent_metrics]
        error_rates = [m.error_rate for m in recent_metrics]

        baseline = PerformanceBaseline(
            test_name=test_name,
            execution_time=statistics.mean(execution_times),
            memory_usage=statistics.mean(memory_usages),
            cpu_usage=statistics.mean(cpu_usages),
            throughput=statistics.mean(throughputs),
            error_rate=statistics.mean(error_rates),
            sample_count=len(recent_metrics),
            standard_deviation=statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            created_at=time.time() if test_name not in self._baselines else self._baselines[test_name].created_at,
            updated_at=time.time()
        )

        self._baselines[test_name] = baseline
        self._save_baselines()

        self.logger.info(f"更新性能基准: {test_name}")

    def check_performance(self, test_name: str, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """检查性能是否符合基准"""
        if test_name not in self._baselines:
            return {
                'status': 'no_baseline',
                'message': '没有性能基准数据',
                'metrics': asdict(metrics)
            }

        baseline = self._baselines[test_name]

        # 计算性能偏差
        execution_time_deviation = metrics.execution_time / baseline.execution_time
        memory_usage_deviation = metrics.memory_usage / baseline.memory_usage
        cpu_usage_deviation = metrics.cpu_usage / baseline.cpu_usage

        # 确定性能状态
        status = self._determine_performance_status(
            execution_time_deviation,
            memory_usage_deviation,
            cpu_usage_deviation
        )

        performance_check = {
            'status': status.value,
            'test_name': test_name,
            'current_metrics': asdict(metrics),
            'baseline_metrics': {
                'execution_time': baseline.execution_time,
                'memory_usage': baseline.memory_usage,
                'cpu_usage': baseline.cpu_usage,
                'throughput': baseline.throughput,
                'error_rate': baseline.error_rate
            },
            'deviations': {
                'execution_time': execution_time_deviation,
                'memory_usage': memory_usage_deviation,
                'cpu_usage': cpu_usage_deviation
            },
            'within_thresholds': {
                'execution_time': metrics.execution_time <= baseline.execution_time_threshold,
                'memory_usage': metrics.memory_usage <= baseline.memory_usage_threshold,
                'cpu_usage': metrics.cpu_usage <= (baseline.cpu_usage * self.config['cpu_threshold_factor'])
            }
        }

        return performance_check

    def _determine_performance_status(self, time_deviation: float,
                                     memory_deviation: float,
                                     cpu_deviation: float) -> PerformanceStatus:
        """确定性能状态"""
        # 检查是否所有指标都在优秀范围内
        if (time_deviation <= 1.1 and memory_deviation <= 1.1 and cpu_deviation <= 1.1):
            return PerformanceStatus.EXCELLENT

        # 检查是否在可接受范围内
        elif (time_deviation <= self.config['performance_threshold_factor'] and
              memory_deviation <= self.config['memory_threshold_factor'] and
              cpu_deviation <= self.config['cpu_threshold_factor']):
            return PerformanceStatus.ACCEPTABLE

        # 检查是否性能下降
        elif (time_deviation > self.config['performance_threshold_factor'] or
              memory_deviation > self.config['memory_threshold_factor'] or
              cpu_deviation > self.config['cpu_threshold_factor']):
            return PerformanceStatus.DEGRADED

        # 严重性能问题
        elif (time_deviation > 2.0 or memory_deviation > 2.0 or cpu_deviation > 2.0):
            return PerformanceStatus.CRITICAL

        else:
            return PerformanceStatus.GOOD

    def _update_stats(self):
        """更新统计信息"""
        self.stats['total_tests_monitored'] = len(self._performance_data)
        self.stats['tests_with_baseline'] = len(self._baselines)

        # 找出性能回归的测试
        self.stats['performance_regressions'] = []
        self.stats['performance_improvements'] = []
        self.stats['worst_performing_tests'] = []

        for test_name, metrics_list in self._performance_data.items():
            if not metrics_list:
                continue

            # 计算平均执行时间
            avg_time = statistics.mean([m.execution_time for m in metrics_list])

            # 找出最差的测试
            if len(self.stats['worst_performing_tests']) < 5:
                self.stats['worst_performing_tests'].append({
                    'test_name': test_name,
                    'average_time': avg_time
                })
            else:
                # 替换最差的测试
                worst_tests = sorted(self.stats['worst_performing_tests'],
                                   key=lambda x: x['average_time'], reverse=True)
                if avg_time > worst_tests[-1]['average_time']:
                    worst_tests[-1] = {'test_name': test_name, 'average_time': avg_time}
                    self.stats['worst_performing_tests'] = worst_tests

        # 按执行时间排序
        self.stats['worst_performing_tests'].sort(key=lambda x: x['average_time'], reverse=True)

        # 计算总体平均执行时间
        all_times = []
        for metrics_list in self._performance_data.values():
            all_times.extend([m.execution_time for m in metrics_list])

        if all_times:
            self.stats['average_execution_time'] = statistics.mean(all_times)

    def get_performance_history(self, test_name: str, days: int = 7) -> List[PerformanceMetrics]:
        """获取性能历史"""
        if test_name not in self._performance_data:
            return []

        cutoff_time = time.time() - (days * 24 * 60 * 60)
        return [m for m in self._performance_data[test_name] if m.timestamp >= cutoff_time]

    def get_baseline(self, test_name: str) -> Optional[PerformanceBaseline]:
        """获取性能基准"""
        return self._baselines.get(test_name)

    def set_baseline_manually(self, test_name: str, execution_time: float,
                             memory_usage: float, cpu_usage: float,
                             throughput: float = 0.0, error_rate: float = 0.0):
        """手动设置性能基准"""
        baseline = PerformanceBaseline(
            test_name=test_name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            throughput=throughput,
            error_rate=error_rate,
            sample_count=1,
            standard_deviation=0.0,
            created_at=time.time(),
            updated_at=time.time()
        )

        self._baselines[test_name] = baseline
        self._save_baselines()

        self.logger.info(f"手动设置性能基准: {test_name}")

    def _load_baselines(self):
        """加载性能基准"""
        baseline_file = self.output_dir / "performance_baselines.json"
        if not baseline_file.exists():
            return

        try:
            with open(baseline_file, 'r', encoding='utf-8') as f:
                baseline_data = json.load(f)

            for test_name, data in baseline_data.items():
                self._baselines[test_name] = PerformanceBaseline(**data)

            self.logger.info(f"加载了 {len(self._baselines)} 个性能基准")

        except Exception as e:
            self.logger.error(f"加载性能基准失败: {e}")

    def _save_baselines(self):
        """保存性能基准"""
        baseline_file = self.output_dir / "performance_baselines.json"

        try:
            baseline_data = {}
            for test_name, baseline in self._baselines.items():
                baseline_data[test_name] = asdict(baseline)

            with open(baseline_file, 'w', encoding='utf-8') as f:
                json.dump(baseline_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"保存性能基准失败: {e}")

    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'monitor_config': self.config,
            'statistics': self.stats,
            'baselines_summary': {
                'total_baselines': len(self._baselines),
                'recently_updated': [
                    baseline.test_name for baseline in self._baselines.values()
                    if time.time() - baseline.updated_at < 24 * 60 * 60  # 24小时内更新的
                ]
            },
            'performance_analysis': {
                'tests_with_regression': len(self.stats['performance_regressions']),
                'tests_with_improvement': len(self.stats['performance_improvements']),
                'worst_performing_tests': self.stats['worst_performing_tests'][:5]
            }
        }

        return report

    def save_report(self, filename: Optional[str] = None) -> Optional[str]:
        """保存性能报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"

        report_path = self.output_dir / filename

        try:
            report = self.generate_report()

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"性能报告已保存到: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"保存性能报告失败: {e}")
            return None


# 全局监控器实例
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_global_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def record_test_performance(test_name: str, execution_time: float, **kwargs) -> PerformanceMetrics:
    """记录测试性能（便捷函数）"""
    monitor = get_global_performance_monitor()
    return monitor.record_performance(test_name, execution_time, **kwargs)


def check_test_performance(test_name: str, metrics: PerformanceMetrics) -> Dict[str, Any]:
    """检查测试性能（便捷函数）"""
    monitor = get_global_performance_monitor()
    return monitor.check_performance(test_name, metrics)


def save_performance_report() -> Optional[str]:
    """保存性能报告（便捷函数）"""
    monitor = get_global_performance_monitor()
    return monitor.save_report()


if __name__ == "__main__":
    # 示例用法
    monitor = PerformanceMonitor()

    # 记录性能指标
    metrics1 = monitor.record_performance(
        "test_example_1",
        execution_time=2.5,
        memory_usage=50.2,
        cpu_usage=15.3
    )

    metrics2 = monitor.record_performance(
        "test_example_2",
        execution_time=1.8,
        memory_usage=45.1,
        cpu_usage=12.7
    )

    # 检查性能
    check1 = monitor.check_performance("test_example_1", metrics1)
    print(f"性能检查1: {json.dumps(check1, indent=2)}")

    # 生成报告
    report_path = monitor.save_report()
    print(f"报告已保存到: {report_path}")

    # 打印统计信息
    stats = monitor.stats
    print(f"统计信息: {json.dumps(stats, indent=2)}")