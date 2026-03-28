"""
Async Operations Tests
Tests for async operations module functionality
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.web.async_operations import (
    AsyncBatchDownloader,
    AsyncTaskManager,
    DownloadTask,
    TaskPriority,
    TaskResult,
    TaskStatus,
    download_batch_async,
    download_file_async,
)


class TestTaskPriority:
    """TaskPriority enum tests"""

    def test_task_priority_values(self):
        """Test task priority enum values"""
        assert TaskPriority.HIGH.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.LOW.value == 3


class TestTaskStatus:
    """TaskStatus enum tests"""

    def test_task_status_values(self):
        """Test task status enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestDownloadTask:
    """DownloadTask dataclass tests"""

    def test_init_basic(self):
        """Test basic initialization"""
        task = DownloadTask(
            url="https://example.com/file.pdf",
            save_path="/tmp/file.pdf"
        )
        assert task.url == "https://example.com/file.pdf"
        assert task.save_path == "/tmp/file.pdf"
        assert task.priority == TaskPriority.NORMAL
        assert task.timeout == 300.0
        assert task.retry_count == 3

    def test_init_with_all_params(self):
        """Test initialization with all parameters"""
        callback = Mock()
        progress = Mock()
        task = DownloadTask(
            url="https://example.com/file.pdf",
            save_path="/tmp/file.pdf",
            priority=TaskPriority.HIGH,
            timeout=600.0,
            retry_count=5,
            metadata={"test": "data"},
            callback=callback,
            on_progress=progress
        )
        assert task.priority == TaskPriority.HIGH
        assert task.timeout == 600.0
        assert task.retry_count == 5
        assert task.metadata == {"test": "data"}
        assert task.callback is callback
        assert task.on_progress is progress


class TestTaskResult:
    """TaskResult dataclass tests"""

    def test_init(self):
        """Test initialization"""
        result = TaskResult(
            task_id="test_id",
            status=TaskStatus.COMPLETED,
            success=True,
            file_path="/tmp/file.pdf"
        )
        assert result.task_id == "test_id"
        assert result.status == TaskStatus.COMPLETED
        assert result.success is True
        assert result.file_path == "/tmp/file.pdf"
        assert result.error_message == ""
        assert result.duration == 0.0
        assert result.bytes_downloaded == 0


class TestAsyncTaskManager:
    """AsyncTaskManager class tests"""

    def test_init(self):
        """Test initialization"""
        manager = AsyncTaskManager(max_concurrent_tasks=5, max_workers=2)
        assert manager.max_concurrent_tasks == 5
        assert manager.max_workers == 2
        assert manager.stats["total_tasks"] == 0
        assert len(manager.active_tasks) == 0
        assert len(manager.completed_tasks) == 0

    def test_init_defaults(self):
        """Test initialization with defaults"""
        manager = AsyncTaskManager()
        assert manager.max_concurrent_tasks == 10
        assert manager.max_workers == 5

    def test_add_download_task(self):
        """Test adding download task"""
        manager = AsyncTaskManager()
        task = DownloadTask(
            url="https://example.com/file.pdf",
            save_path="/tmp/file.pdf"
        )
        task_id = manager.add_download_task(task)
        assert isinstance(task_id, str)
        assert len(task_id) == 32  # MD5 hex digest length
        assert manager.stats["total_tasks"] == 1

    def test_add_task_with_priority(self):
        """Test adding task with priority"""
        manager = AsyncTaskManager()
        task = DownloadTask(
            url="https://example.com/file.pdf",
            save_path="/tmp/file.pdf",
            priority=TaskPriority.HIGH
        )
        manager.add_download_task(task)
        assert manager.stats["total_tasks"] == 1

    def test_get_stats(self):
        """Test getting statistics"""
        manager = AsyncTaskManager()
        stats = manager.get_stats()

        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "failed_tasks" in stats
        assert "cancelled_tasks" in stats
        assert "active_tasks" in stats
        assert "completed_tasks" in stats
        assert "queue_size" in stats
        assert "success_rate" in stats

    def test_get_task_status_not_found(self):
        """Test get task status for non-existent task"""
        manager = AsyncTaskManager()
        status = manager.get_task_status("non_existent")
        assert status is None

    def test_cancel_task_not_found(self):
        """Test cancel non-existent task"""
        manager = AsyncTaskManager()
        result = manager.cancel_task("non_existent")
        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with AsyncTaskManager(max_concurrent_tasks=2) as manager:
            assert manager is not None
            assert manager.max_concurrent_tasks == 2

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop methods"""
        manager = AsyncTaskManager()
        await manager.start()
        assert manager.session_pool is not None
        await manager.stop()

    @pytest.mark.asyncio
    async def test_wait_for_task_timeout(self):
        """Test wait for task with timeout"""
        manager = AsyncTaskManager()
        result = await manager.wait_for_task("non_existent", timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_all_tasks_empty(self):
        """Test wait for all tasks when none are active"""
        manager = AsyncTaskManager()
        results = await manager.wait_for_all_tasks(timeout=0.1)
        assert isinstance(results, dict)

    def test_get_active_tasks_info(self):
        """Test getting active tasks info"""
        manager = AsyncTaskManager()
        info = manager.get_active_tasks_info()
        assert isinstance(info, list)


class TestAsyncBatchDownloader:
    """AsyncBatchDownloader class tests"""

    def test_init(self):
        """Test initialization"""
        task_manager = AsyncTaskManager()
        downloader = AsyncBatchDownloader(task_manager)
        assert downloader.task_manager is task_manager

    def test_init_default_manager(self):
        """Test initialization with default task manager"""
        downloader = AsyncBatchDownloader()
        assert downloader.task_manager is not None


class TestConvenienceFunctions:
    """Convenience function tests"""

    @pytest.mark.asyncio
    async def test_download_file_async(self):
        """Test download file async function"""
        with patch("src.web.async_operations.AsyncTaskManager") as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value.__aenter__.return_value = mock_manager

            mock_result = MagicMock()
            mock_result.success = True
            mock_manager.add_download_task.return_value = "test_id"
            mock_manager.wait_for_task = AsyncMock(return_value=mock_result)

            result = await download_file_async("https://example.com/file.pdf", "/tmp/file.pdf")
            assert result is True

    @pytest.mark.asyncio
    async def test_download_batch_async(self):
        """Test download batch async function"""
        with patch("src.web.async_operations.AsyncTaskManager") as mock_manager_class:
            # Setup proper mocks
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager_instance = MagicMock()
            mock_manager_instance.wait_for_all_tasks = AsyncMock(return_value={})
            mock_manager_instance.get_stats = MagicMock(return_value={
                "completed_tasks": 0,
                "failed_tasks": 0,
                "cancelled_tasks": 0,
                "total_bytes_downloaded": 0,
            })
            mock_manager_instance.add_download_task = MagicMock(return_value="task_id")

            # Make __aenter__ and __aexit__ return the mock instance
            mock_manager.__aenter__ = AsyncMock(return_value=mock_manager_instance)
            mock_manager.__aexit__ = AsyncMock(return_value=None)

            tasks = [
                DownloadTask(url="https://example.com/file1.pdf", save_path="/tmp/file1.pdf"),
                DownloadTask(url="https://example.com/file2.pdf", save_path="/tmp/file2.pdf"),
            ]

            result = await download_batch_async(tasks)
            assert isinstance(result, dict)
