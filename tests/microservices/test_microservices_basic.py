#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微服务基础功能测试
测试微服务架构的核心组件
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime
from typing import Dict, Any

# 导入微服务模块
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from microservices.common.service_client import ServiceEvent, ServiceEventType
from microservices.common.task_queue import Task, TaskStatus, TaskPriority, TaskQueue


class TestServiceEvent:
    """服务事件测试"""

    def test_event_creation(self):
        """测试事件创建"""
        event = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service="test-service",
            data={"message": "Service started"}
        )

        assert event.event_type == ServiceEventType.SERVICE_UP
        assert event.source_service == "test-service"
        assert event.data["message"] == "Service started"
        assert event.timestamp is not None
        assert event.event_id is not None

    def test_event_serialization(self):
        """测试事件序列化"""
        event = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service="test-service",
            data={"message": "Service started"}
        )

        # 转换为字典
        event_dict = {
            "event_type": event.event_type.value,
            "source_service": event.source_service,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id
        }

        assert "event_type" in event_dict
        assert "source_service" in event_dict
        assert event_dict["event_type"] == "service_up"


class TestTask:
    """任务测试"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id="test-task-1",
            name="Test Task",
            func_name="test_function",
            args=[1, 2, 3],
            kwargs={"param": "value"}
        )

        assert task.id == "test-task-1"
        assert task.name == "Test Task"
        assert task.func_name == "test_function"
        assert task.args == [1, 2, 3]
        assert task.kwargs == {"param": "value"}
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.created_at is not None

    def test_task_defaults(self):
        """测试任务默认值"""
        task = Task(
            id="test-task-2",
            name="Simple Task",
            func_name="simple_function"
        )

        assert task.args == []
        assert task.kwargs == {}
        assert task.dependencies == []
        assert task.tags == []
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.timeout == 300

    def test_task_status_enum(self):
        """测试任务状态枚举"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.RETRYING.value == "retrying"

    def test_task_priority_enum(self):
        """测试任务优先级枚举"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4


class TestTaskResult:
    """任务结果测试"""

    def test_task_result_creation(self):
        """测试任务结果创建"""
        from microservices.common.task_queue import TaskResult

        result = TaskResult(
            task_id="test-task-1",
            status=TaskStatus.COMPLETED,
            result={"data": "success"},
            execution_time=1.5,
            worker_id="worker-1"
        )

        assert result.task_id == "test-task-1"
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"data": "success"}
        assert result.execution_time == 1.5
        assert result.worker_id == "worker-1"


@pytest.mark.asyncio
class TestMicroservicesComponents:
    """微服务组件异步测试"""

    async def test_service_event_timestamp(self):
        """测试服务事件时间戳"""
        before_create = datetime.now()

        event = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service="test-service"
        )

        after_create = datetime.now()

        # 验证时间戳在合理范围内
        assert before_create <= event.timestamp <= after_create

    async def test_service_event_id_generation(self):
        """测试服务事件ID生成"""
        event1 = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service="test-service"
        )

        event2 = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service="test-service"
        )

        # 不同时间创建的事件应该有不同的ID
        assert event1.event_id != event2.event_id

    async def test_task_progress_tracking(self):
        """测试任务进度跟踪"""
        task = Task(
            id="progress-task",
            name="Progress Task",
            func_name="progress_function"
        )

        # 初始进度为0
        assert task.progress == 0.0

        # 模拟进度更新
        task.progress = 0.5
        assert task.progress == 0.5

        # 完成时进度为1.0
        task.progress = 1.0
        assert task.progress == 1.0