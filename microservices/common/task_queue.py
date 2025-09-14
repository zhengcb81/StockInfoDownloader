#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分布式任务队列
提供异步任务处理功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis
from src.core.logger import get_logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """任务"""
    id: str
    name: str
    func_name: str
    args: List[Any] = None
    kwargs: Dict[str, Any] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 5分钟超时
    dependencies: List[str] = None
    tags: List[str] = None
    progress: float = 0.0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.args is None:
            self.args = []
        if self.kwargs is None:
            self.kwargs = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    worker_id: Optional[str] = None
    completed_at: Optional[datetime] = None


class TaskQueue:
    """任务队列"""

    def __init__(self, redis_client: redis.Redis, queue_name: str = "default"):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.logger = get_logger(__name__)
        self.task_handlers = {}
        self.workers = {}
        self.active_tasks = {}

    async def enqueue_task(self, task: Task) -> str:
        """将任务加入队列"""
        try:
            # 序列化任务
            task_data = asdict(task)
            task_data["status"] = task.status.value
            task_data["priority"] = task.priority.value
            task_data["created_at"] = task.created_at.isoformat()
            if task.started_at:
                task_data["started_at"] = task.started_at.isoformat()
            if task.completed_at:
                task_data["completed_at"] = task.completed_at.isoformat()

            # 根据优先级选择队列
            queue_key = f"task_queue:{self.queue_name}:{task.priority.name}"
            priority_score = task.priority.value * 1000000 + int(task.created_at.timestamp())

            # 添加任务到队列
            await self.redis_client.zadd(queue_key, {json.dumps(task_data): priority_score})

            # 存储任务详情
            await self.redis_client.hset(
                f"task:{task.id}",
                mapping=json.dumps(task_data, default=str)
            )

            # 设置任务过期时间（7天）
            await self.redis_client.expire(f"task:{task.id}", 7 * 24 * 3600)

            self.logger.info(f"Task enqueued: {task.id} - {task.name}")
            return task.id

        except Exception as e:
            self.logger.error(f"Failed to enqueue task: {e}")
            raise

    async def dequeue_task(self, worker_id: str) -> Optional[Task]:
        """从队列中取出任务"""
        try:
            # 按优先级顺序检查队列
            for priority in ["CRITICAL", "HIGH", "NORMAL", "LOW"]:
                queue_key = f"task_queue:{self.queue_name}:{priority}"

                # 使用原子操作获取任务
                result = await self.redis_client.bzpopmax(queue_key, timeout=1)
                if result:
                    queue_name, task_json, score = result
                    task_data = json.loads(task_json)

                    # 创建任务对象
                    task = Task(
                        id=task_data["id"],
                        name=task_data["name"],
                        func_name=task_data["func_name"],
                        args=task_data.get("args", []),
                        kwargs=task_data.get("kwargs", {}),
                        status=TaskStatus(task_data["status"]),
                        priority=TaskPriority(task_data["priority"]),
                        created_at=datetime.fromisoformat(task_data["created_at"]),
                        started_at=datetime.fromisoformat(task_data["started_at"]) if task_data.get("started_at") else None,
                        completed_at=datetime.fromisoformat(task_data["completed_at"]) if task_data.get("completed_at") else None,
                        result=task_data.get("result"),
                        error=task_data.get("error"),
                        retry_count=task_data.get("retry_count", 0),
                        max_retries=task_data.get("max_retries", 3),
                        timeout=task_data.get("timeout", 300),
                        dependencies=task_data.get("dependencies", []),
                        tags=task_data.get("tags", []),
                        progress=task_data.get("progress", 0.0)
                    )

                    # 更新任务状态
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    await self._update_task(task)

                    # 记录活跃任务
                    self.active_tasks[task.id] = worker_id

                    self.logger.info(f"Task dequeued: {task.id} by worker {worker_id}")
                    return task

            return None

        except Exception as e:
            self.logger.error(f"Failed to dequeue task: {e}")
            return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        try:
            task_data = await self.redis_client.hgetall(f"task:{task_id}")
            if task_data:
                task_json = list(task_data.values())[0]
                task_data_dict = json.loads(task_json)

                return Task(
                    id=task_data_dict["id"],
                    name=task_data_dict["name"],
                    func_name=task_data_dict["func_name"],
                    args=task_data_dict.get("args", []),
                    kwargs=task_data_dict.get("kwargs", {}),
                    status=TaskStatus(task_data_dict["status"]),
                    priority=TaskPriority(task_data_dict["priority"]),
                    created_at=datetime.fromisoformat(task_data_dict["created_at"]),
                    started_at=datetime.fromisoformat(task_data_dict["started_at"]) if task_data_dict.get("started_at") else None,
                    completed_at=datetime.fromisoformat(task_data_dict["completed_at"]) if task_data_dict.get("completed_at") else None,
                    result=task_data_dict.get("result"),
                    error=task_data_dict.get("error"),
                    retry_count=task_data_dict.get("retry_count", 0),
                    max_retries=task_data_dict.get("max_retries", 3),
                    timeout=task_data_dict.get("timeout", 300),
                    dependencies=task_data_dict.get("dependencies", []),
                    tags=task_data_dict.get("tags", []),
                    progress=task_data_dict.get("progress", 0.0)
                )

            return None

        except Exception as e:
            self.logger.error(f"Failed to get task: {e}")
            return None

    async def update_task_status(self, task_id: str, status: TaskStatus, result: Any = None, error: str = None):
        """更新任务状态"""
        try:
            task = await self.get_task(task_id)
            if not task:
                raise Exception(f"Task {task_id} not found")

            task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()

            await self._update_task(task)

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                # 从活跃任务中移除
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

            self.logger.info(f"Task status updated: {task_id} - {status.value}")

        except Exception as e:
            self.logger.error(f"Failed to update task status: {e}")
            raise

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False

            # 如果任务正在运行，需要通知工作器停止
            if task.status == TaskStatus.RUNNING:
                # 这里可以实现更复杂的取消逻辑
                pass

            await self.update_task_status(task_id, TaskStatus.CANCELLED)
            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel task: {e}")
            return False

    async def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        try:
            task = await self.get_task(task_id)
            if not task:
                return False

            if task.status != TaskStatus.FAILED:
                return False

            if task.retry_count >= task.max_retries:
                return False

            # 重置任务状态
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            task.error = None

            # 重新加入队列
            await self.enqueue_task(task)

            self.logger.info(f"Task retried: {task_id} (attempt {task.retry_count})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to retry task: {e}")
            return False

    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        try:
            stats = {
                "queue_name": self.queue_name,
                "pending_tasks": 0,
                "running_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "active_workers": len(self.workers),
                "tasks_by_priority": {}
            }

            # 统计各优先级的待处理任务
            for priority in ["CRITICAL", "HIGH", "NORMAL", "LOW"]:
                queue_key = f"task_queue:{self.queue_name}:{priority}"
                count = await self.redis_client.zcard(queue_key)
                stats["tasks_by_priority"][priority] = count
                stats["pending_tasks"] += count

            # 统计活跃任务
            stats["running_tasks"] = len(self.active_tasks)

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {e}")
            return {}

    async def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            task_keys = await self.redis_client.keys("task:*")

            cleaned_count = 0
            for key in task_keys:
                task_data = await self.redis_client.hgetall(key)
                if task_data:
                    task_json = list(task_data.values())[0]
                    task_data_dict = json.loads(task_json)

                    created_at = datetime.fromisoformat(task_data_dict["created_at"])
                    if created_at < cutoff_date:
                        await self.redis_client.delete(key)
                        cleaned_count += 1

            self.logger.info(f"Cleaned up {cleaned_count} old tasks")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

    async def register_task_handler(self, func_name: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[func_name] = handler
        self.logger.info(f"Task handler registered: {func_name}")

    async def register_worker(self, worker_id: str, worker_info: Dict[str, Any]):
        """注册工作器"""
        self.workers[worker_id] = {
            "info": worker_info,
            "registered_at": datetime.now(),
            "last_heartbeat": datetime.now()
        }

        # 存储工作器信息
        await self.redis_client.hset(
            f"worker:{worker_id}",
            mapping=json.dumps({
                "worker_id": worker_id,
                "info": worker_info,
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat()
            }, default=str)
        )

        self.logger.info(f"Worker registered: {worker_id}")

    async def unregister_worker(self, worker_id: str):
        """注销工作器"""
        if worker_id in self.workers:
            del self.workers[worker_id]

        await self.redis_client.delete(f"worker:{worker_id}")
        self.logger.info(f"Worker unregistered: {worker_id}")

    async def worker_heartbeat(self, worker_id: str):
        """工作器心跳"""
        if worker_id in self.workers:
            self.workers[worker_id]["last_heartbeat"] = datetime.now()

        await self.redis_client.hset(
            f"worker:{worker_id}",
            mapping=json.dumps({
                "worker_id": worker_id,
                "info": self.workers.get(worker_id, {}).get("info", {}),
                "registered_at": self.workers.get(worker_id, {}).get("registered_at", datetime.now()).isoformat(),
                "last_heartbeat": datetime.now().isoformat()
            }, default=str)
        )

    async def _update_task(self, task: Task):
        """更新任务信息"""
        task_data = asdict(task)
        task_data["status"] = task.status.value
        task_data["priority"] = task.priority.value
        task_data["created_at"] = task.created_at.isoformat()
        if task.started_at:
            task_data["started_at"] = task.started_at.isoformat()
        if task.completed_at:
            task_data["completed_at"] = task.completed_at.isoformat()

        await self.redis_client.hset(
            f"task:{task.id}",
            mapping=json.dumps(task_data, default=str)
        )


class TaskWorker:
    """任务工作器"""

    def __init__(self, worker_id: str, task_queue: TaskQueue):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.logger = get_logger(__name__)
        self.running = False
        self.current_task = None

    async def start(self):
        """启动工作器"""
        self.running = True

        # 注册工作器
        await self.task_queue.register_worker(self.worker_id, {
            "worker_id": self.worker_id,
            "started_at": datetime.now().isoformat(),
            "status": "running"
        })

        self.logger.info(f"Worker started: {self.worker_id}")

        # 开始处理任务
        while self.running:
            try:
                await self._process_next_task()
                await asyncio.sleep(0.1)  # 短暂休眠避免CPU占用过高
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)  # 错误时等待更长时间

    async def stop(self):
        """停止工作器"""
        self.running = False
        await self.task_queue.unregister_worker(self.worker_id)
        self.logger.info(f"Worker stopped: {self.worker_id}")

    async def _process_next_task(self):
        """处理下一个任务"""
        try:
            # 获取任务
            task = await self.task_queue.dequeue_task(self.worker_id)
            if not task:
                return

            self.current_task = task

            # 发送心跳
            await self.task_queue.worker_heartbeat(self.worker_id)

            # 执行任务
            await self._execute_task(task)

        except Exception as e:
            self.logger.error(f"Task processing error: {e}")

    async def _execute_task(self, task: Task):
        """执行任务"""
        try:
            # 查找任务处理器
            handler = self.task_queue.task_handlers.get(task.func_name)
            if not handler:
                raise Exception(f"No handler found for function: {task.func_name}")

            self.logger.info(f"Executing task: {task.id} - {task.name}")

            # 执行任务
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = handler(*task.args, **task.kwargs)

            # 更新任务状态
            await self.task_queue.update_task_status(
                task.id,
                TaskStatus.COMPLETED,
                result=result
            )

            self.logger.info(f"Task completed: {task.id}")

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Task failed: {task.id} - {error_msg}")

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                await self.task_queue.update_task_status(
                    task.id,
                    TaskStatus.RETRYING,
                    error=error_msg
                )
                # 延迟后重试
                await asyncio.sleep(2 ** task.retry_count)  # 指数退避
                await self.task_queue.retry_task(task.id)
            else:
                await self.task_queue.update_task_status(
                    task.id,
                    TaskStatus.FAILED,
                    error=error_msg
                )

        finally:
            self.current_task = None


# 创建全局任务队列实例
_task_queues = {}

async def get_task_queue(queue_name: str = "default", redis_client: redis.Redis = None) -> TaskQueue:
    """获取任务队列实例"""
    if queue_name not in _task_queues:
        _task_queues[queue_name] = TaskQueue(redis_client, queue_name)
    return _task_queues[queue_name]