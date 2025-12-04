#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TestExecutionMonitor单元测试
测试测试执行监控系统的核心功能
"""

import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from src.core.monitoring.test_execution_monitor import (
    TestExecutionMonitor,
    TestExecutionRecord,
    TestStatus,
    get_global_monitor,
    start_monitoring_test,
    end_monitoring_test
)


class TestTestExecutionRecord:
    """TestExecutionRecord类测试"""

    def test_record_initialization(self):
        """测试记录初始化"""
        record = TestExecutionRecord(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py",
            start_time=time.time()
        )

        assert record.test_id == "test_1"
        assert record.test_name == "test_example"
        assert record.file_path == "test_example.py"
        assert record.status == TestStatus.PENDING
        assert record.end_time is None
        assert record.execution_time == 0.0
        assert record.error_message is None

    def test_is_completed_property(self):
        """测试is_completed属性"""
        record = TestExecutionRecord(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py",
            start_time=time.time()
        )

        # 初始状态为PENDING，未完成
        assert not record.is_completed

        # 设置为PASSED状态，应标记为完成
        record.status = TestStatus.PASSED
        assert record.is_completed

        # 设置为FAILED状态，应标记为完成
        record.status = TestStatus.FAILED
        assert record.is_completed

        # 设置为SKIPPED状态，应标记为完成
        record.status = TestStatus.SKIPPED
        assert record.is_completed

        # 设置为ERROR状态，应标记为完成
        record.status = TestStatus.ERROR
        assert record.is_completed

        # 设置为RUNNING状态，不应标记为完成
        record.status = TestStatus.RUNNING
        assert not record.is_completed

    def test_mark_started(self):
        """测试标记开始"""
        start_time = time.time()
        record = TestExecutionRecord(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py",
            start_time=start_time
        )

        # 标记开始
        record.mark_started()

        # 应该更新状态为RUNNING
        assert record.status == TestStatus.RUNNING
        # 开始时间应该更新（可能略有不同）
        assert record.start_time >= start_time

    def test_mark_completed(self):
        """测试标记完成"""
        start_time = time.time()
        record = TestExecutionRecord(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py",
            start_time=start_time
        )

        # 标记开始
        record.mark_started()

        # 等待一小段时间
        time.sleep(0.01)

        # 标记完成
        error_message = "测试失败"
        record.mark_completed(TestStatus.FAILED, error_message)

        # 验证状态和属性
        assert record.status == TestStatus.FAILED
        assert record.end_time is not None
        assert record.end_time > start_time
        assert record.execution_time > 0
        assert record.error_message == error_message
        # 内存和CPU使用率应该有值（可能为0）
        assert isinstance(record.memory_usage, float)
        assert isinstance(record.cpu_usage, float)


class TestTestExecutionMonitor:
    """TestExecutionMonitor类测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建临时目录用于输出
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_monitor_"))
        self.monitor = TestExecutionMonitor(output_dir=str(self.temp_dir))

    def teardown_method(self):
        """每个测试方法后的清理"""
        # 清理临时目录
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_monitor_initialization(self):
        """测试监控器初始化"""
        assert self.monitor.output_dir == self.temp_dir
        assert self.temp_dir.exists()
        assert len(self.monitor._records) == 0
        assert self.monitor.stats['total_tests'] == 0
        assert self.monitor.stats['passed_tests'] == 0
        assert self.monitor.stats['failed_tests'] == 0

    def test_start_test(self):
        """测试开始监控测试"""
        test_id = self.monitor.start_test(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py"
        )

        # 应该返回test_id
        assert test_id == "test_1"

        # 应该有记录
        assert "test_1" in self.monitor._records
        record = self.monitor._records["test_1"]

        # 验证记录内容
        assert record.test_id == "test_1"
        assert record.test_name == "test_example"
        assert record.file_path == "test_example.py"
        assert record.status == TestStatus.RUNNING
        assert record.start_time > 0

        # 统计信息应该更新
        assert self.monitor.stats['total_tests'] == 1

    def test_end_test(self):
        """测试结束监控测试"""
        # 先开始测试
        test_id = self.monitor.start_test(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py"
        )

        # 等待一小段时间
        time.sleep(0.01)

        # 结束测试
        error_message = "断言错误"
        self.monitor.end_test(
            test_id=test_id,
            status=TestStatus.FAILED,
            error_message=error_message
        )

        # 获取记录
        record = self.monitor._records[test_id]

        # 验证记录
        assert record.status == TestStatus.FAILED
        assert record.end_time is not None
        assert record.execution_time > 0
        assert record.error_message == error_message

        # 验证统计信息
        assert self.monitor.stats['total_tests'] == 1
        assert self.monitor.stats['failed_tests'] == 1
        assert self.monitor.stats['passed_tests'] == 0

    def test_end_test_nonexistent(self):
        """测试结束不存在的测试"""
        # 应该不会抛出异常，但会记录警告
        with patch.object(self.monitor.logger, 'warning') as mock_warning:
            self.monitor.end_test(
                test_id="nonexistent",
                status=TestStatus.PASSED
            )

            # 应该记录警告
            mock_warning.assert_called()

    def test_get_test_status(self):
        """测试获取测试状态"""
        # 开始并结束测试
        test_id = self.monitor.start_test(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py"
        )

        time.sleep(0.01)
        self.monitor.end_test(test_id, TestStatus.PASSED)

        # 获取状态
        status = self.monitor.get_test_status(test_id)

        # 验证状态信息
        assert status is not None
        assert status['test_id'] == test_id
        assert status['test_name'] == "test_example"
        assert status['file_path'] == "test_example.py"
        assert status['status'] == TestStatus.PASSED.value
        assert status['execution_time'] > 0

    def test_get_test_status_nonexistent(self):
        """测试获取不存在的测试状态"""
        status = self.monitor.get_test_status("nonexistent")
        assert status is None

    def test_get_all_test_status(self):
        """测试获取所有测试状态"""
        # 创建多个测试
        test_ids = []
        for i in range(3):
            test_id = f"test_{i}"
            self.monitor.start_test(
                test_id=test_id,
                test_name=f"test_example_{i}",
                file_path="test_example.py"
            )
            self.monitor.end_test(test_id, TestStatus.PASSED)
            test_ids.append(test_id)

        # 获取所有状态
        all_status = self.monitor.get_all_test_status()

        # 应该有3个状态
        assert len(all_status) == 3

        # 验证每个状态
        for status in all_status:
            assert status['test_id'] in test_ids

    def test_get_stats(self):
        """测试获取统计信息"""
        # 创建多个测试，混合状态
        for i in range(5):
            test_id = f"test_{i}"
            self.monitor.start_test(
                test_id=test_id,
                test_name=f"test_example_{i}",
                file_path="test_example.py"
            )

            # 分配不同的状态
            if i % 3 == 0:
                status = TestStatus.PASSED
            elif i % 3 == 1:
                status = TestStatus.FAILED
            else:
                status = TestStatus.SKIPPED

            time.sleep(0.001)  # 确保执行时间>0
            self.monitor.end_test(test_id, status)

        # 获取统计信息
        stats = self.monitor.get_stats()

        # 验证统计信息
        assert stats['total_tests'] == 5
        # 成功率计算
        completed = stats['passed_tests'] + stats['failed_tests']
        if completed > 0:
            assert stats['success_rate'] == stats['passed_tests'] / completed
        else:
            assert stats['success_rate'] == 0.0

    def test_generate_report(self):
        """测试生成报告"""
        # 创建测试数据
        test_id = self.monitor.start_test(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py"
        )
        self.monitor.end_test(test_id, TestStatus.PASSED)

        # 生成报告
        report = self.monitor.generate_report()

        # 验证报告结构
        assert 'timestamp' in report
        assert 'monitor_config' in report
        assert 'test_statistics' in report
        assert 'test_records' in report
        assert 'performance_issues' in report
        assert 'summary' in report

        # 验证统计数据
        stats = report['test_statistics']
        assert stats['total_tests'] == 1
        assert stats['passed_tests'] == 1

    def test_save_report(self):
        """测试保存报告"""
        # 创建测试数据
        test_id = self.monitor.start_test(
            test_id="test_1",
            test_name="test_example",
            file_path="test_example.py"
        )
        self.monitor.end_test(test_id, TestStatus.PASSED)

        # 保存报告
        report_path = self.monitor.save_report()

        # 验证文件存在
        report_file = Path(report_path)
        assert report_file.exists()

        # 验证文件内容
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert '"total_tests"' in content  # 检查JSON内容

    def test_clear_records(self):
        """测试清除记录"""
        # 创建测试数据
        for i in range(3):
            test_id = f"test_{i}"
            self.monitor.start_test(
                test_id=test_id,
                test_name=f"test_example_{i}",
                file_path="test_example.py"
            )
            self.monitor.end_test(test_id, TestStatus.PASSED)

        # 验证有记录
        assert len(self.monitor._records) == 3
        assert self.monitor.stats['total_tests'] == 3

        # 清除记录
        self.monitor.clear_records()

        # 验证记录已清除
        assert len(self.monitor._records) == 0
        assert self.monitor.stats['total_tests'] == 0
        assert self.monitor.stats['passed_tests'] == 0


class TestGlobalMonitorFunctions:
    """全局监控函数测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置全局监控器
        from src.core.monitoring.test_execution_monitor import _global_monitor
        _global_monitor = None

    def test_get_global_monitor(self):
        """测试获取全局监控器"""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()

        # 应该是同一个实例
        assert monitor1 is monitor2

    def test_start_monitoring_test(self):
        """测试开始监控测试便捷函数"""
        test_id = start_monitoring_test("test_example", "test_example.py")

        # 应该返回test_id
        assert test_id == "test_example.py::test_example"

        # 应该创建了全局监控器
        monitor = get_global_monitor()
        assert test_id in monitor._records

    def test_end_monitoring_test(self):
        """测试结束监控测试便捷函数"""
        test_id = start_monitoring_test("test_example", "test_example.py")
        end_monitoring_test(test_id, TestStatus.PASSED)

        # 验证状态更新
        monitor = get_global_monitor()
        record = monitor._records[test_id]
        assert record.status == TestStatus.PASSED

    def test_save_monitoring_report(self):
        """测试保存监控报告便捷函数"""
        # 创建测试数据
        test_id = start_monitoring_test("test_example", "test_example.py")
        end_monitoring_test(test_id, TestStatus.PASSED)

        # 保存报告
        report_path = get_global_monitor().save_report()

        # 应该返回路径
        assert report_path is not None
        assert Path(report_path).exists()

    def test_get_monitoring_stats(self):
        """测试获取监控统计信息便捷函数"""
        # 创建测试数据
        test_id = start_monitoring_test("test_example", "test_example.py")
        end_monitoring_test(test_id, TestStatus.PASSED)

        # 获取统计信息
        stats = get_global_monitor().get_stats()

        # 验证统计信息
        assert stats['total_tests'] == 1
        assert stats['passed_tests'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])