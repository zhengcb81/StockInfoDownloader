#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
并行下载管理器测试
测试并行下载管理器的功能
"""

# 添加项目根目录到Python路径
import sys
import time
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.parallel_downloader import (
    ParallelDownloadManager,
    TaskPriority,
)


class TestParallelDownloadManager:
    """测试并行下载管理器"""

    @pytest.fixture
    def download_manager(self):
        """下载管理器fixture"""
        config = {
            "task_timeout": 60,
            "retry_policy": {"max_retries": 2, "retry_delay": 1, "backoff_factor": 1.5},
        }
        return ParallelDownloadManager(max_workers=3, config=config)

    def test_add_task(self, download_manager):
        """测试添加任务"""
        task_id = download_manager.add_task(
            stock_code="300470",
            company_name="测试公司",
            target_pages=[{"suffix": "research", "allowed_keywords": None}],
        )

        assert task_id is not None
        assert isinstance(task_id, str)

        # 检查任务是否添加成功
        task = download_manager.task_queue.get_task(task_id)
        assert task is not None
        assert task.stock_code == "300470"
        assert task.company_name == "测试公司"

    def test_task_priority(self, download_manager):
        """测试任务优先级"""
        # 添加不同优先级的任务
        task1_id = download_manager.add_task(
            "300470", "公司1", [{"suffix": "research"}], TaskPriority.LOW
        )
        task2_id = download_manager.add_task(
            "301611", "公司2", [{"suffix": "research"}], TaskPriority.HIGH
        )

        # 高优先级任务应该先执行
        task1 = download_manager.task_queue.get_task(task1_id)
        task2 = download_manager.task_queue.get_task(task2_id)

        assert task1.priority == TaskPriority.LOW
        assert task2.priority == TaskPriority.HIGH

    def test_start_stop_manager(self, download_manager):
        """测试启动和停止管理器"""
        # 添加任务
        download_manager.add_task("300470", "测试公司", [{"suffix": "research"}])

        # 启动管理器
        download_manager.start()
        assert download_manager._running is True

        # 等待一段时间让任务处理
        time.sleep(2)

        # 停止管理器
        download_manager.stop()
        assert download_manager._running is False

    def test_task_status_tracking(self, download_manager):
        """测试任务状态跟踪"""
        task_id = download_manager.add_task(
            "300470", "测试公司", [{"suffix": "research"}]
        )

        # 获取任务状态
        status = download_manager.get_task_status(task_id)
        assert status is not None
        assert status["stock_code"] == "300470"
        assert status["status"] == "pending"

        # 获取所有任务状态
        all_status = download_manager.get_all_tasks_status()
        assert len(all_status) >= 1

    def test_manager_stats(self, download_manager):
        """测试管理器统计信息"""
        # 添加一些任务
        download_manager.add_task("300470", "公司1", [{"suffix": "research"}])
        download_manager.add_task("301611", "公司2", [{"suffix": "research"}])

        stats = download_manager.get_stats()
        assert "manager_stats" in stats
        assert "resource_usage" in stats
        assert "queue_size" in stats
        assert stats["queue_size"] >= 2
        assert stats["max_workers"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
