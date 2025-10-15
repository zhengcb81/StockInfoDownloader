#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试执行监控系统
监控测试执行时间、资源使用和性能指标
"""

import time
import psutil
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from src.core.logger import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """测试状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestExecutionRecord:
    """测试执行记录"""
    test_id: str
    test_name: str
    file_path: str
    start_time: float
    end_time: Optional[float] = None
    status: TestStatus = TestStatus.PENDING
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        """测试是否完成"""
        return self.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED, TestStatus.ERROR]

    def mark_started(self):
        """标记测试开始"""
        self.start_time = time.time()
        self.status = TestStatus.RUNNING

    def mark_completed(self, status: TestStatus, error_message: Optional[str] = None):
        """标记测试完成"""
        self.end_time = time.time()
        self.status = status
        self.execution_time = self.end_time - self.start_time
        self.error_message = error_message

        # 记录资源使用情况
        self._record_resource_usage()

    def _record_resource_usage(self):
        """记录资源使用情况"""
        try:
            process = psutil.Process()
            self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.cpu_usage = process.cpu_percent()
        except Exception as e:
            logger.warning(f"记录资源使用失败: {e}")


class TestExecutionMonitor:
    """测试执行监控器"""

    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.logger = get_logger("TestExecutionMonitor")
        self._records: Dict[str, TestExecutionRecord] = {}
        self._lock = threading.RLock()

        # 监控配置
        self.config = {
            'max_execution_time': 60.0,  # 最大执行时间（秒）
            'max_memory_usage': 500.0,   # 最大内存使用（MB）
            'max_cpu_usage': 80.0,       # 最大CPU使用率（%）
            'enable_resource_monitoring': True
        }

        # 统计信息
        self.stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'error_tests': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0,
            'slow_tests': [],
            'resource_intensive_tests': []
        }

        self.logger.info("测试执行监控器初始化完成")

    def start_test(self, test_id: str, test_name: str, file_path: str) -> str:
        """开始监控测试"""
        with self._lock:
            record = TestExecutionRecord(
                test_id=test_id,
                test_name=test_name,
                file_path=file_path,
                start_time=time.time()
            )
            record.mark_started()
            self._records[test_id] = record

            self.stats['total_tests'] += 1

            self.logger.debug(f"开始监控测试: {test_name}")
            return test_id

    def end_test(self, test_id: str, status: TestStatus, error_message: Optional[str] = None):
        """结束监控测试"""
        with self._lock:
            if test_id not in self._records:
                self.logger.warning(f"未找到测试记录: {test_id}")
                return

            record = self._records[test_id]
            record.mark_completed(status, error_message)

            # 更新统计信息
            self._update_stats(record)

            # 检查性能问题
            self._check_performance_issues(record)

            self.logger.debug(f"测试完成: {record.test_name} - {status.value}")

    def _update_stats(self, record: TestExecutionRecord):
        """更新统计信息"""
        if record.status == TestStatus.PASSED:
            self.stats['passed_tests'] += 1
        elif record.status == TestStatus.FAILED:
            self.stats['failed_tests'] += 1
        elif record.status == TestStatus.SKIPPED:
            self.stats['skipped_tests'] += 1
        elif record.status == TestStatus.ERROR:
            self.stats['error_tests'] += 1

        self.stats['total_execution_time'] += record.execution_time

        # 计算平均执行时间
        completed_tests = (self.stats['passed_tests'] + self.stats['failed_tests'] +
                          self.stats['error_tests'])
        if completed_tests > 0:
            self.stats['average_execution_time'] = (
                self.stats['total_execution_time'] / completed_tests
            )

    def _check_performance_issues(self, record: TestExecutionRecord):
        """检查性能问题"""
        # 检查执行时间过长
        if record.execution_time > self.config['max_execution_time']:
            self.stats['slow_tests'].append({
                'test_name': record.test_name,
                'execution_time': record.execution_time,
                'file_path': record.file_path
            })

        # 检查资源使用过高
        if self.config['enable_resource_monitoring']:
            if record.memory_usage > self.config['max_memory_usage']:
                self.stats['resource_intensive_tests'].append({
                    'test_name': record.test_name,
                    'memory_usage': record.memory_usage,
                    'file_path': record.file_path
                })

            if record.cpu_usage > self.config['max_cpu_usage']:
                self.stats['resource_intensive_tests'].append({
                    'test_name': record.test_name,
                    'cpu_usage': record.cpu_usage,
                    'file_path': record.file_path
                })

    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """获取测试状态"""
        with self._lock:
            record = self._records.get(test_id)
            if record is None:
                return None

            return {
                'test_id': record.test_id,
                'test_name': record.test_name,
                'file_path': record.file_path,
                'status': record.status.value,
                'execution_time': record.execution_time,
                'memory_usage': record.memory_usage,
                'cpu_usage': record.cpu_usage,
                'start_time': record.start_time,
                'end_time': record.end_time,
                'error_message': record.error_message
            }

    def get_all_test_status(self) -> List[Dict[str, Any]]:
        """获取所有测试状态"""
        with self._lock:
            return [self.get_test_status(test_id) for test_id in self._records.keys()]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats_copy = self.stats.copy()

            # 计算成功率
            total_completed = (stats_copy['passed_tests'] + stats_copy['failed_tests'] +
                             stats_copy['error_tests'])
            if total_completed > 0:
                stats_copy['success_rate'] = stats_copy['passed_tests'] / total_completed
            else:
                stats_copy['success_rate'] = 0.0

            return stats_copy

    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        with self._lock:
            report = {
                'timestamp': datetime.now().isoformat(),
                'monitor_config': self.config,
                'test_statistics': self.get_stats(),
                'test_records': [asdict(record) for record in self._records.values()],
                'performance_issues': {
                    'slow_tests': self.stats['slow_tests'],
                    'resource_intensive_tests': self.stats['resource_intensive_tests']
                },
                'summary': {
                    'total_tests_monitored': len(self._records),
                    'monitoring_duration': self._calculate_monitoring_duration(),
                    'overall_status': self._calculate_overall_status()
                }
            }

            return report

    def _calculate_monitoring_duration(self) -> float:
        """计算监控持续时间"""
        if not self._records:
            return 0.0

        start_times = [record.start_time for record in self._records.values()]
        end_times = [record.end_time for record in self._records.values() if record.end_time]

        if not end_times:
            return time.time() - min(start_times)

        return max(end_times) - min(start_times)

    def _calculate_overall_status(self) -> str:
        """计算总体状态"""
        stats = self.get_stats()

        if stats['failed_tests'] > 0 or stats['error_tests'] > 0:
            return 'FAILED'
        elif stats['passed_tests'] == stats['total_tests']:
            return 'PASSED'
        else:
            return 'PARTIAL'

    def save_report(self, filename: Optional[str] = None):
        """保存监控报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_execution_report_{timestamp}.json"

        report_path = self.output_dir / filename

        try:
            report = self.generate_report()

            # 确保所有枚举值都转换为字符串
            def convert_enums(obj):
                if isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                elif isinstance(obj, Enum):
                    return obj.value
                else:
                    return obj

            report = convert_enums(report)

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"测试执行报告已保存到: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"保存测试执行报告失败: {e}")
            return None

    def clear_records(self):
        """清除所有记录"""
        with self._lock:
            self._records.clear()
            self.stats = {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'error_tests': 0,
                'total_execution_time': 0.0,
                'average_execution_time': 0.0,
                'slow_tests': [],
                'resource_intensive_tests': []
            }


# 全局监控器实例
_global_monitor: Optional[TestExecutionMonitor] = None


def get_global_monitor() -> TestExecutionMonitor:
    """获取全局监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = TestExecutionMonitor()
    return _global_monitor


def start_monitoring_test(test_name: str, file_path: str) -> str:
    """开始监控测试（便捷函数）"""
    monitor = get_global_monitor()
    test_id = f"{file_path}::{test_name}"
    return monitor.start_test(test_id, test_name, file_path)


def end_monitoring_test(test_id: str, status: TestStatus, error_message: Optional[str] = None):
    """结束监控测试（便捷函数）"""
    monitor = get_global_monitor()
    monitor.end_test(test_id, status, error_message)


def save_monitoring_report() -> Optional[str]:
    """保存监控报告（便捷函数）"""
    monitor = get_global_monitor()
    return monitor.save_report()


def get_monitoring_stats() -> Dict[str, Any]:
    """获取监控统计信息（便捷函数）"""
    monitor = get_global_monitor()
    return monitor.get_stats()


# pytest集成钩子
import pytest


@pytest.fixture(scope="function")
def test_monitor():
    """pytest测试监控fixture"""
    test_id = None

    def _start_monitoring(request):
        nonlocal test_id
        test_name = request.node.name
        file_path = request.node.fspath.strpath
        test_id = start_monitoring_test(test_name, file_path)

    def _end_monitoring(request, status: TestStatus, error_message: Optional[str] = None):
        nonlocal test_id
        if test_id:
            end_monitoring_test(test_id, status, error_message)

    return {
        'start': _start_monitoring,
        'end': _end_monitoring
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """pytest测试协议钩子"""
    # 获取监控fixture
    monitor_fixture = None
    try:
        monitor_fixture = item.funcargs.get('test_monitor')
    except Exception:
        pass

    # 开始监控
    if monitor_fixture:
        monitor_fixture['start'](item)

    # 执行测试
    result = yield

    # 结束监控
    if monitor_fixture:
        # 根据测试结果确定状态
        if hasattr(item, '_test_outcome') and item._test_outcome:
            outcome = item._test_outcome.outcome
            if outcome == 'passed':
                status = TestStatus.PASSED
            elif outcome == 'failed':
                status = TestStatus.FAILED
            elif outcome == 'skipped':
                status = TestStatus.SKIPPED
            else:
                status = TestStatus.ERROR
        else:
            status = TestStatus.ERROR

        monitor_fixture['end'](item, status)


if __name__ == "__main__":
    # 示例用法
    monitor = TestExecutionMonitor()

    # 模拟测试执行
    test_id1 = monitor.start_test("test1", "test_example_1", "test_example.py")
    time.sleep(1)
    monitor.end_test(test_id1, TestStatus.PASSED)

    test_id2 = monitor.start_test("test2", "test_example_2", "test_example.py")
    time.sleep(2)
    monitor.end_test(test_id2, TestStatus.FAILED, "Assertion error")

    # 生成报告
    report_path = monitor.save_report()
    print(f"报告已保存到: {report_path}")

    # 打印统计信息
    stats = monitor.get_stats()
    print(f"统计信息: {json.dumps(stats, indent=2)}")