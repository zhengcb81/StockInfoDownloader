#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
并行下载管理器
支持多公司并行下载，具备任务调度、资源管理和监控功能
"""

import asyncio
import concurrent.futures
import time
import threading
import queue
import uuid
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from pathlib import Path

from src.core.logger import get_logger
from src.core.performance_monitor import PerformanceMonitor


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class DownloadTask:
    """下载任务数据类"""
    task_id: str
    stock_code: str
    company_name: str
    target_pages: List[Dict[str, Any]]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    proxy_info: Optional[Dict[str, Any]] = None

    @property
    def execution_time(self) -> float:
        """执行时间"""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or time.time()
        return end_time - self.started_at

    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    def mark_started(self):
        """标记任务开始"""
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self, result: Dict[str, Any]):
        """标记任务完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result
        self.progress = 100.0

    def mark_failed(self, error: str):
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED

    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error = None


class TaskQueue:
    """任务队列（支持优先级）"""

    def __init__(self):
        self._queue = queue.PriorityQueue()
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.RLock()

    def put(self, task: DownloadTask):
        """添加任务到队列"""
        with self._lock:
            # 使用负优先级，因为PriorityQueue是最小堆
            priority = -task.priority.value
            self._queue.put((priority, task.created_at, task.task_id, task))
            self._tasks[task.task_id] = task

    def get(self, timeout: Optional[float] = None) -> Optional[DownloadTask]:
        """从队列获取任务"""
        try:
            _, _, task_id, task = self._queue.get(timeout=timeout)
            with self._lock:
                if task_id in self._tasks:
                    return task
            return None
        except queue.Empty:
            return None

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """根据ID获取任务"""
        with self._lock:
            return self._tasks.get(task_id)

    def remove_task(self, task_id: str):
        """移除任务"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]

    def size(self) -> int:
        """队列大小"""
        with self._lock:
            return len(self._tasks)

    def empty(self) -> bool:
        """队列是否为空"""
        return self.size() == 0

    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())

    def get_pending_tasks(self) -> List[DownloadTask]:
        """获取待处理任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.status == TaskStatus.PENDING]

    def get_running_tasks(self) -> List[DownloadTask]:
        """获取运行中任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.status == TaskStatus.RUNNING]

    def get_completed_tasks(self) -> List[DownloadTask]:
        """获取已完成任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.is_completed]


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self.logger = get_logger("ResourceMonitor")
        self._cpu_usage = 0.0
        self._memory_usage = 0.0
        self._network_io = 0.0
        self._disk_usage = 0.0
        self._lock = threading.Lock()

    def update_usage(self):
        """更新资源使用情况"""
        try:
            import psutil
            process = psutil.Process()

            with self._lock:
                self._cpu_usage = process.cpu_percent()
                self._memory_usage = process.memory_percent()
                self._network_io = sum(process.io_counters()[:2])
                disk_info = psutil.disk_usage('/')
                self._disk_usage = disk_info.percent

        except ImportError:
            self.logger.warning("psutil not available, resource monitoring disabled")
        except Exception as e:
            self.logger.error(f"资源监控更新失败: {e}")

    def get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        with self._lock:
            return self._cpu_usage

    def get_memory_usage(self) -> float:
        """获取内存使用率"""
        with self._lock:
            return self._memory_usage

    def get_network_io(self) -> float:
        """获取网络IO"""
        with self._lock:
            return self._network_io

    def get_disk_usage(self) -> float:
        """获取磁盘使用率"""
        with self._lock:
            return self._disk_usage

    def is_resource_available(self, max_cpu: float = 80.0, max_memory: float = 80.0) -> bool:
        """检查资源是否可用"""
        self.update_usage()
        return (self.get_cpu_usage() < max_cpu and
                self.get_memory_usage() < max_memory)


class ParallelDownloadManager:
    """并行下载管理器"""

    def __init__(self, max_workers: int = 5, config: Optional[Dict[str, Any]] = None):
        self.max_workers = max_workers
        self.config = config or {}
        self.logger = get_logger("ParallelDownloadManager")

        # 任务队列
        self.task_queue = TaskQueue()

        # 线程池
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        # 资源监控
        self.resource_monitor = ResourceMonitor()

        # 性能监控
        self.performance_monitor = PerformanceMonitor()

        # 控制标志
        self._running = False
        self._paused = False
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'running_tasks': 0,
            'pending_tasks': 0,
            'total_files_downloaded': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0,
            'success_rate': 0.0,
            'throughput': 0.0
        }

        # 任务超时配置
        self.task_timeout = self.config.get('task_timeout', 300)  # 5分钟

        # 重试策略
        self.retry_policy = self.config.get('retry_policy', {})
        self.max_retries = self.retry_policy.get('max_retries', 3)
        self.retry_delay = self.retry_policy.get('retry_delay', 5)
        self.backoff_factor = self.retry_policy.get('backoff_factor', 2)

        # 回调函数
        self.task_callbacks: Dict[str, List[Callable]] = {
            'on_task_start': [],
            'on_task_complete': [],
            'on_task_error': [],
            'on_task_retry': []
        }

        self.logger.info(f"并行下载管理器初始化完成，最大工作线程: {max_workers}")

    def add_task(self, stock_code: str, company_name: str, target_pages: List[Dict[str, Any]],
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_retries: int = None,
                 proxy_info: Optional[Dict[str, Any]] = None) -> str:
        """添加下载任务"""
        task_id = str(uuid.uuid4())

        task = DownloadTask(
            task_id=task_id,
            stock_code=stock_code,
            company_name=company_name,
            target_pages=target_pages,
            priority=priority,
            max_retries=max_retries or self.max_retries,
            proxy_info=proxy_info
        )

        self.task_queue.put(task)
        self._update_stats()

        self.logger.info(f"添加下载任务: {stock_code} - {company_name} (ID: {task_id})")
        return task_id

    def add_callback(self, event_type: str, callback: Callable):
        """添加回调函数"""
        if event_type in self.task_callbacks:
            self.task_callbacks[event_type].append(callback)

    def _trigger_callbacks(self, event_type: str, task: DownloadTask):
        """触发回调函数"""
        for callback in self.task_callbacks.get(event_type, []):
            try:
                callback(task)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {e}")

    def start(self):
        """启动下载管理器"""
        if self._running:
            self.logger.warning("下载管理器已在运行")
            return

        self._running = True
        self._paused = False

        # 启动工作线程
        for i in range(self.max_workers):
            worker_thread = threading.Thread(
                target=self._worker_loop,
                name=f"DownloadWorker-{i}",
                daemon=True
            )
            worker_thread.start()

        # 启动监控线程
        monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="DownloadMonitor",
            daemon=True
        )
        monitor_thread.start()

        self.logger.info(f"并行下载管理器已启动，工作线程数: {self.max_workers}")

    def stop(self):
        """停止下载管理器"""
        if not self._running:
            return

        self.logger.info("正在停止并行下载管理器...")
        self._running = False

        # 等待线程池完成
        self.executor.shutdown(wait=True)

        self.logger.info("并行下载管理器已停止")

    def pause(self):
        """暂停下载"""
        self._paused = True
        self.logger.info("并行下载管理器已暂停")

    def resume(self):
        """恢复下载"""
        self._paused = False
        self.logger.info("并行下载管理器已恢复")

    def _worker_loop(self):
        """工作线程循环"""
        while self._running:
            try:
                if self._paused:
                    time.sleep(1)
                    continue

                # 检查资源可用性
                if not self.resource_monitor.is_resource_available():
                    time.sleep(5)
                    continue

                # 获取任务
                task = self.task_queue.get(timeout=1)
                if task is None:
                    continue

                # 执行任务
                self._execute_task(task)

            except Exception as e:
                self.logger.error(f"工作线程异常: {e}")
                time.sleep(1)

    def _execute_task(self, task: DownloadTask):
        """执行下载任务"""
        try:
            task.mark_started()
            self._trigger_callbacks('on_task_start', task)
            self._update_stats()

            # 执行下载
            result = self._perform_download(task)

            if result['success']:
                task.mark_completed(result)
                self._trigger_callbacks('on_task_complete', task)
                self.logger.info(f"任务 {task.task_id} 完成: {task.stock_code} - {task.company_name}")
            else:
                task.mark_failed(result.get('error', 'Unknown error'))
                self._trigger_callbacks('on_task_error', task)

                # 检查是否需要重试
                if task.can_retry():
                    self._retry_task(task)
                else:
                    self.logger.error(f"任务 {task.task_id} 失败: {task.stock_code} - {task.company_name}")

        except Exception as e:
            error_msg = f"任务执行异常: {e}"
            task.mark_failed(error_msg)
            self._trigger_callbacks('on_task_error', task)
            self.logger.error(f"任务 {task.task_id} 执行异常: {e}")

        finally:
            self._update_stats()

    def _perform_download(self, task: DownloadTask) -> Dict[str, Any]:
        """执行实际下载操作"""
        try:
            # 这里应该调用实际的下载服务
            # 为了演示，我们模拟下载过程
            import random
            import time

            # 模拟下载时间
            download_time = random.uniform(10, 30)
            time.sleep(download_time)

            # 模拟下载结果
            success = random.random() > 0.1  # 90%成功率
            files_downloaded = random.randint(1, 10) if success else 0

            return {
                'success': success,
                'files_downloaded': files_downloaded,
                'execution_time': download_time,
                'stock_code': task.stock_code,
                'company_name': task.company_name,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': 0,
                'files_downloaded': 0
            }

    def _retry_task(self, task: DownloadTask):
        """重试任务"""
        task.increment_retry()

        # 计算重试延迟
        delay = self.retry_delay * (self.backoff_factor ** (task.retry_count - 1))
        self.logger.info(f"任务 {task.task_id} 将在 {delay} 秒后重试 (第 {task.retry_count} 次)")

        # 延迟后重新添加到队列
        def retry_later():
            time.sleep(delay)
            if self._running:
                self.task_queue.put(task)
                self._trigger_callbacks('on_task_retry', task)

        retry_thread = threading.Thread(target=retry_later, daemon=True)
        retry_thread.start()

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                time.sleep(30)  # 每30秒监控一次

                # 更新资源监控
                self.resource_monitor.update_usage()

                # 更新统计信息
                self._update_stats()

                # 清理完成的任务
                self._cleanup_completed_tasks()

                # 记录监控信息
                self._log_monitor_info()

            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")

    def _update_stats(self):
        """更新统计信息"""
        with self._lock:
            tasks = self.task_queue.get_all_tasks()

            self.stats['total_tasks'] = len(tasks)
            self.stats['pending_tasks'] = len([t for t in tasks if t.status == TaskStatus.PENDING])
            self.stats['running_tasks'] = len([t for t in tasks if t.status == TaskStatus.RUNNING])
            self.stats['completed_tasks'] = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            self.stats['failed_tasks'] = len([t for t in tasks if t.status == TaskStatus.FAILED])

            # 计算成功率
            total_completed = self.stats['completed_tasks'] + self.stats['failed_tasks']
            if total_completed > 0:
                self.stats['success_rate'] = self.stats['completed_tasks'] / total_completed

            # 计算吞吐量（暂时设为0，需要实现具体逻辑）
            self.stats['throughput'] = 0

    def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        try:
            completed_tasks = self.task_queue.get_completed_tasks()
            cutoff_time = time.time() - 3600  # 保留1小时内的已完成任务

            for task in completed_tasks:
                if task.completed_at and task.completed_at < cutoff_time:
                    self.task_queue.remove_task(task.task_id)

        except Exception as e:
            self.logger.error(f"清理任务失败: {e}")

    def _log_monitor_info(self):
        """记录监控信息"""
        if self.stats['total_tasks'] > 0:
            self.logger.info(
                f"任务状态 - 总计: {self.stats['total_tasks']}, "
                f"待处理: {self.stats['pending_tasks']}, "
                f"运行中: {self.stats['running_tasks']}, "
                f"已完成: {self.stats['completed_tasks']}, "
                f"失败: {self.stats['failed_tasks']}, "
                f"成功率: {self.stats['success_rate']:.2%}"
            )

        # 记录资源使用情况
        cpu_usage = self.resource_monitor.get_cpu_usage()
        memory_usage = self.resource_monitor.get_memory_usage()
        if cpu_usage > 0 or memory_usage > 0:
            self.logger.info(f"资源使用 - CPU: {cpu_usage:.1f}%, 内存: {memory_usage:.1f}%")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.task_queue.get_task(task_id)
        if task is None:
            return None

        return {
            'task_id': task.task_id,
            'stock_code': task.stock_code,
            'company_name': task.company_name,
            'status': task.status.value,
            'priority': task.priority.name,
            'progress': task.progress,
            'retry_count': task.retry_count,
            'execution_time': task.execution_time,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'error': task.error,
            'result': task.result
        }

    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        tasks = self.task_queue.get_all_tasks()
        return [self.get_task_status(task.task_id) for task in tasks]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'manager_stats': self.stats.copy(),
            'resource_usage': {
                'cpu_usage': self.resource_monitor.get_cpu_usage(),
                'memory_usage': self.resource_monitor.get_memory_usage(),
                'disk_usage': self.resource_monitor.get_disk_usage()
            },
            'queue_size': self.task_queue.size(),
            'is_running': self._running,
            'is_paused': self._paused,
            'max_workers': self.max_workers
        }

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.task_queue.get_task(task_id)
        if task is None:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            self._update_stats()
            self.logger.info(f"任务 {task_id} 已取消")
            return True

        return False

    def cancel_all_tasks(self):
        """取消所有任务"""
        tasks = self.task_queue.get_all_tasks()
        for task in tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED
                task.completed_at = time.time()

        self._update_stats()
        self.logger.info(f"已取消所有任务，共 {len(tasks)} 个")

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        start_time = time.time()

        while self._running:
            if self.task_queue.empty():
                return True

            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(1)

        return False

    def save_state(self, file_path: str):
        """保存状态到文件"""
        try:
            state = {
                'timestamp': time.time(),
                'stats': self.stats,
                'tasks': []
            }

            for task in self.task_queue.get_all_tasks():
                task_data = {
                    'task_id': task.task_id,
                    'stock_code': task.stock_code,
                    'company_name': task.company_name,
                    'target_pages': task.target_pages,
                    'priority': task.priority.name,
                    'max_retries': task.max_retries,
                    'retry_count': task.retry_count,
                    'created_at': task.created_at,
                    'status': task.status.value,
                    'progress': task.progress,
                    'error': task.error,
                    'result': task.result
                }
                state['tasks'].append(task_data)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            self.logger.info(f"状态已保存到 {file_path}")

        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")

    def load_state(self, file_path: str):
        """从文件加载状态"""
        try:
            if not Path(file_path).exists():
                self.logger.warning(f"状态文件 {file_path} 不存在")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.stats = state.get('stats', {})

            # 恢复任务
            for task_data in state.get('tasks', []):
                if task_data['status'] in ['pending', 'running']:
                    task = DownloadTask(
                        task_id=task_data['task_id'],
                        stock_code=task_data['stock_code'],
                        company_name=task_data['company_name'],
                        target_pages=task_data['target_pages'],
                        priority=TaskPriority[task_data['priority']],
                        max_retries=task_data['max_retries'],
                        retry_count=task_data['retry_count'],
                        created_at=task_data['created_at']
                    )
                    task.status = TaskStatus(task_data['status'])
                    task.progress = task_data.get('progress', 0.0)
                    task.error = task_data.get('error')
                    task.result = task_data.get('result')

                    self.task_queue.put(task)

            self.logger.info(f"状态已从 {file_path} 加载")

        except Exception as e:
            self.logger.error(f"加载状态失败: {e}")


# 上下文管理器支持
class ParallelDownloadContext:
    """并行下载上下文管理器"""

    def __init__(self, max_workers: int = 5, config: Optional[Dict[str, Any]] = None):
        self.manager = ParallelDownloadManager(max_workers, config)

    def __enter__(self):
        self.manager.start()
        return self.manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.stop()