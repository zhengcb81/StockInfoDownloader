#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MonitoringService 模块测试
提升 src/services/monitoring_service.py 模块的测试覆盖率
"""

import time
from unittest.mock import patch

import pytest

from src.services.monitoring_service import MonitoringService


class TestMonitoringService:
    """测试 MonitoringService 类"""

    def test_init_default(self):
        """测试默认初始化"""
        service = MonitoringService()
        assert service.config == {}
        assert service.start_time > 0
        assert service.metrics == {
            "total_attempts": 0,
            "success_count": 0,
            "fail_count": 0
        }

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"key": "value", "threshold": 100}
        service = MonitoringService(config)
        assert service.config == config
        assert service.start_time > 0
        assert service.metrics == {
            "total_attempts": 0,
            "success_count": 0,
            "fail_count": 0
        }

    def test_init_with_none_config(self):
        """测试传入 None 配置"""
        service = MonitoringService(None)
        assert service.config == {}

    def test_record_success(self):
        """测试记录成功"""
        service = MonitoringService()
        service.record_success()

        assert service.metrics["success_count"] == 1
        assert service.metrics["total_attempts"] == 1
        assert service.metrics["fail_count"] == 0

    def test_record_success_multiple(self):
        """测试记录多次成功"""
        service = MonitoringService()
        for _ in range(5):
            service.record_success()

        assert service.metrics["success_count"] == 5
        assert service.metrics["total_attempts"] == 5
        assert service.metrics["fail_count"] == 0

    def test_record_failure(self):
        """测试记录失败"""
        service = MonitoringService()
        service.record_failure()

        assert service.metrics["fail_count"] == 1
        assert service.metrics["total_attempts"] == 1
        assert service.metrics["success_count"] == 0

    def test_record_failure_multiple(self):
        """测试记录多次失败"""
        service = MonitoringService()
        for _ in range(3):
            service.record_failure()

        assert service.metrics["fail_count"] == 3
        assert service.metrics["total_attempts"] == 3
        assert service.metrics["success_count"] == 0

    def test_record_mixed(self):
        """测试记录混合的成功和失败"""
        service = MonitoringService()
        service.record_success()
        service.record_failure()
        service.record_success()
        service.record_failure()
        service.record_success()

        assert service.metrics["success_count"] == 3
        assert service.metrics["fail_count"] == 2
        assert service.metrics["total_attempts"] == 5

    def test_get_summary(self):
        """测试获取摘要"""
        service = MonitoringService()
        service.record_success()
        service.record_failure()

        summary = service.get_summary()

        assert "duration_seconds" in summary
        assert summary["total_attempts"] == 2
        assert summary["success_count"] == 1
        assert summary["fail_count"] == 1
        assert summary["duration_seconds"] >= 0

    def test_get_summary_duration_increases(self):
        """测试摘要中的持续时间递增"""
        service = MonitoringService()

        summary1 = service.get_summary()
        duration1 = summary1["duration_seconds"]
        assert duration1 >= 0

        time.sleep(0.1)

        summary2 = service.get_summary()
        duration2 = summary2["duration_seconds"]
        assert duration2 > duration1

    def test_get_summary_initial(self):
        """测试初始摘要（无操作）"""
        service = MonitoringService()
        summary = service.get_summary()

        assert summary["total_attempts"] == 0
        assert summary["success_count"] == 0
        assert summary["fail_count"] == 0
        assert summary["duration_seconds"] >= 0


class TestMonitoringServiceIntegration:
    """集成测试"""

    def test_complete_monitoring_workflow(self):
        """测试完整的监控工作流"""
        service = MonitoringService({"operation": "download"})

        # 模拟一些操作
        service.record_success()
        service.record_success()
        service.record_failure()
        service.record_success()
        service.record_failure()
        service.record_failure()

        # 获取摘要
        summary = service.get_summary()

        # 验证结果
        assert summary["total_attempts"] == 6
        assert summary["success_count"] == 3
        assert summary["fail_count"] == 3
        assert summary["duration_seconds"] >= 0

    def test_metrics_modification(self):
        """测试指标修改会影响摘要"""
        service = MonitoringService()
        original_metrics = service.metrics.copy()

        # 直接修改 metrics 会影响 get_summary() 的结果
        # 因为 get_summary() 使用 **self.metrics
        service.metrics["custom_metric"] = "custom_value"
        summary = service.get_summary()
        assert "custom_metric" in summary
        assert summary["custom_metric"] == "custom_value"

        # 使用 record 方法仍然正常工作
        service.record_success()
        assert service.metrics["success_count"] == 1

    def test_config_usage(self):
        """测试配置的使用"""
        config = {"timeout": 30, "retries": 3}
        service = MonitoringService(config)

        assert service.config["timeout"] == 30
        assert service.config["retries"] == 3
