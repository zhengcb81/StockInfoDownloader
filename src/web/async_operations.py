"""
异步操作优化模块
提供异步下载、并发处理和任务调度功能
"""

import asyncio
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import aiofiles
import aiohttp

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.utils.string_optimizer import get_string_optimizer
from src.web.rate_limiter import get_global_rate_limiter


class TaskPriority(Enum):
    """任务优先级"""

    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadTask:
    """下载任务"""

    url: str
    save_path: str
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 300.0
    retry_count: int = 3
    metadata: Optional[Dict[str, Any]] = None
    callback: Optional[Callable[[bool, str], None]] = None
    on_progress: Optional[Callable[[float], None]] = None


@dataclass
class TaskResult:
    """任务结果"""

    task_id: str
    status: TaskStatus
    success: bool
    file_path: str
    error_message: str = ""
    duration: float = 0.0
    bytes_downloaded: int = 0


class AsyncTaskManager:
    """异步任务管理器"""

    def __init__(self, max_concurrent_tasks: int = 10, max_workers: int = 5):
        """
        初始化异步任务管理器

        Args:
            max_concurrent_tasks: 最大并发任务数
            max_workers: 最大工作线程数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_workers = max_workers
        self.task_queue = asyncio.PriorityQueue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.session_pool = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()
        self.rate_limiter = get_global_rate_limiter()
        self.string_optimizer = get_string_optimizer()

        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "total_bytes_downloaded": 0,
            "average_download_speed": 0.0,
            "concurrent_tasks_peak": 0,
        }

        # 事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.logger.info(
            f"异步任务管理器初始化完成: "
            f"最大并发任务={max_concurrent_tasks}, "
            f"最大工作线程={max_workers}"
        )

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()

    async def start(self):
        """启动任务管理器"""
        if self.session_pool is None:
            # 创建HTTP会话池
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_tasks,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            self.session_pool = aiohttp.ClientSession(
                connector=connector, timeout=timeout, headers=headers
            )

        # 启动任务处理器
        self.task_processor = asyncio.create_task(self._process_tasks())
        self.logger.info("异步任务管理器已启动")

    async def stop(self):
        """停止任务管理器"""
        # 取消所有任务
        for task_id, task_info in self.active_tasks.items():
            if not task_info["task"].done():
                task_info["task"].cancel()

        # 停止任务处理器
        if hasattr(self, "task_processor"):
            self.task_processor.cancel()
            try:
                await self.task_processor
            except asyncio.CancelledError:
                pass

        # 关闭HTTP会话池
        if self.session_pool:
            await self.session_pool.close()

        # 关闭线程池
        self.executor.shutdown(wait=True)

        self.logger.info("异步任务管理器已停止")

    def add_download_task(self, task: DownloadTask) -> str:
        """
        添加下载任务

        Args:
            task: 下载任务

        Returns:
            str: 任务ID
        """
        task_id = hashlib.md5(f"{task.url}{time.time()}".encode()).hexdigest()
        priority_value = task.priority.value

        # 添加到队列
        self.task_queue.put_nowait((priority_value, time.time(), task_id, task))

        # 更新统计
        self.stats["total_tasks"] += 1

        self.logger.debug(f"添加下载任务: {task_id} -> {Path(task.save_path).name}")
        return task_id

    async def _process_tasks(self):
        """处理任务队列"""
        while True:
            try:
                # 获取任务
                priority, enqueue_time, task_id, task = await self.task_queue.get()

                # 检查并发限制
                while len(self.active_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)

                # 创建任务
                task_future = asyncio.create_task(self._execute_task(task_id, task))
                self.active_tasks[task_id] = {
                    "task": task_future,
                    "start_time": time.time(),
                    "task_obj": task,
                }

                # 更新并发峰值
                current_concurrent = len(self.active_tasks)
                if current_concurrent > self.stats["concurrent_tasks_peak"]:
                    self.stats["concurrent_tasks_peak"] = current_concurrent

                self.task_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"任务处理异常: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task_id: str, task: DownloadTask) -> TaskResult:
        """执行单个任务"""
        start_time = time.time()
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            success=False,
            file_path=task.save_path,
        )

        try:
            self.logger.debug(f"开始执行任务: {task_id}")

            # 应用速率限制
            await self.rate_limiter.wait_if_needed_async(
                task.url, f"download_{task_id}"
            )

            # 创建保存目录
            save_dir = Path(task.save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)

            # 下载文件
            success = await self._download_file(task, result)

            result.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            result.success = success
            result.duration = time.time() - start_time

            # 更新统计
            if success:
                self.stats["completed_tasks"] += 1
                self.stats["total_bytes_downloaded"] += result.bytes_downloaded

                # 计算平均下载速度
                if result.duration > 0:
                    speed = result.bytes_downloaded / result.duration
                    total_completed = self.stats["completed_tasks"]
                    current_avg = self.stats["average_download_speed"]
                    self.stats["average_download_speed"] = (
                        current_avg * (total_completed - 1) + speed
                    ) / total_completed
            else:
                self.stats["failed_tasks"] += 1

            # 调用回调
            if task.callback:
                try:
                    await self._run_callback(task.callback, success, task.save_path)
                except Exception as e:
                    self.logger.error(f"任务回调异常: {e}")

        except asyncio.CancelledError:
            result.status = TaskStatus.CANCELLED
            result.duration = time.time() - start_time
            self.stats["cancelled_tasks"] += 1
            self.logger.info(f"任务已取消: {task_id}")

        except Exception as e:
            result.status = TaskStatus.FAILED
            result.success = False
            result.error_message = str(e)
            result.duration = time.time() - start_time
            self.stats["failed_tasks"] += 1
            self.logger.error(f"任务执行失败: {task_id} - {e}")

        finally:
            # 移动到完成列表
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            self.completed_tasks[task_id] = result

            # 限制完成列表大小
            if len(self.completed_tasks) > 1000:
                oldest_keys = sorted(self.completed_tasks.keys())[:100]
                for key in oldest_keys:
                    del self.completed_tasks[key]

        return result

    async def _download_file(self, task: DownloadTask, result: TaskResult) -> bool:
        """下载文件"""
        for attempt in range(task.retry_count + 1):
            try:
                async with self.session_pool.get(task.url) as response:
                    response.raise_for_status()

                    # 获取文件大小
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded_size = 0

                    # 下载文件
                    async with aiofiles.open(task.save_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded_size += len(chunk)

                            # 更新进度
                            if task.on_progress and total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                await self._run_callback(task.on_progress, progress)

                    result.bytes_downloaded = downloaded_size

                    # 验证下载完整性
                    if total_size > 0 and downloaded_size != total_size:
                        raise Exception(f"下载不完整: {downloaded_size}/{total_size}")

                    self.logger.info(
                        f"文件下载成功: {Path(task.save_path).name} "
                        f"({downloaded_size} bytes, {result.duration:.1f}s)"
                    )
                    return True

            except Exception as e:
                self.logger.warning(
                    f"下载失败 (尝试 {attempt + 1}/{task.retry_count + 1}): {e}"
                )
                if attempt < task.retry_count:
                    await asyncio.sleep(2**attempt)  # 指数退避
                else:
                    result.error_message = str(e)
                    return False

        return False

    async def _run_callback(self, callback: Callable, *args):
        """运行回调函数"""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            # 在线程池中运行同步回调
            await self.loop.run_in_executor(self.executor, callback, *args)

    async def wait_for_task(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[TaskResult]:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            timeout: 超时时间

        Returns:
            Optional[TaskResult]: 任务结果
        """
        start_time = time.time()

        while True:
            # 检查是否已完成
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]

            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                return None

            # 检查是否在运行
            if task_id not in self.active_tasks:
                return None

            await asyncio.sleep(0.1)

    async def wait_for_all_tasks(
        self, timeout: Optional[float] = None
    ) -> Dict[str, TaskResult]:
        """
        等待所有任务完成

        Args:
            timeout: 超时时间

        Returns:
            Dict[str, TaskResult]: 所有任务结果
        """
        start_time = time.time()

        while self.active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                break

            await asyncio.sleep(0.1)

        return self.completed_tasks.copy()

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id]
            if not task_info["task"].done():
                task_info["task"].cancel()
                self.stats["cancelled_tasks"] += 1
                self.logger.info(f"任务已取消: {task_id}")
                return True
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[TaskStatus]: 任务状态
        """
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].status
        elif task_id in self.active_tasks:
            return TaskStatus.RUNNING
        else:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "queue_size": self.task_queue.qsize(),
            "success_rate": (
                self.stats["completed_tasks"] / max(self.stats["total_tasks"], 1) * 100
            ),
        }

    def get_active_tasks_info(self) -> List[Dict[str, Any]]:
        """
        获取活动任务信息

        Returns:
            List[Dict[str, Any]]: 活动任务信息列表
        """
        active_info = []
        for task_id, task_info in self.active_tasks.items():
            runtime = time.time() - task_info["start_time"]
            task_obj = task_info["task_obj"]

            active_info.append(
                {
                    "task_id": task_id,
                    "url": task_obj.url,
                    "save_path": task_obj.save_path,
                    "priority": task_obj.priority.name,
                    "runtime": runtime,
                    "timeout": task_obj.timeout,
                }
            )

        return active_info


class AsyncBatchDownloader:
    """异步批量下载器"""

    def __init__(self, task_manager: Optional[AsyncTaskManager] = None):
        """
        初始化批量下载器

        Args:
            task_manager: 任务管理器实例
        """
        self.task_manager = task_manager or AsyncTaskManager()
        self.logger = get_logger(__name__)

    async def download_batch(
        self, download_tasks: List[DownloadTask]
    ) -> Dict[str, TaskResult]:
        """
        批量下载

        Args:
            download_tasks: 下载任务列表

        Returns:
            Dict[str, TaskResult]: 任务结果字典
        """
        # 添加所有任务
        task_ids = []
        for task in download_tasks:
            task_id = self.task_manager.add_download_task(task)
            task_ids.append(task_id)

        self.logger.info(f"开始批量下载 {len(download_tasks)} 个文件")

        # 等待所有任务完成
        results = await self.task_manager.wait_for_all_tasks()

        # 输出统计
        stats = self.task_manager.get_stats()
        self.logger.info(
            f"批量下载完成: 成功={stats['completed_tasks']}, "
            f"失败={stats['failed_tasks']}, "
            f"取消={stats['cancelled_tasks']}, "
            f"总大小={stats['total_bytes_downloaded']} bytes"
        )

        return results

    async def download_with_progress(
        self, download_tasks: List[DownloadTask]
    ) -> Dict[str, TaskResult]:
        """
        带进度显示的批量下载

        Args:
            download_tasks: 下载任务列表

        Returns:
            Dict[str, TaskResult]: 任务结果字典
        """
        # 创建进度回调
        progress_info = {}

        def progress_callback(task_id: str, progress: float):
            progress_info[task_id] = progress

        # 添加进度回调到任务
        enhanced_tasks = []
        for task in download_tasks:
            task_id = hashlib.md5(f"{task.url}{time.time()}".encode()).hexdigest()
            enhanced_task = DownloadTask(
                url=task.url,
                save_path=task.save_path,
                priority=task.priority,
                timeout=task.timeout,
                retry_count=task.retry_count,
                metadata=task.metadata,
                on_progress=lambda p: progress_callback(task_id, p),
            )
            enhanced_tasks.append(enhanced_task)

        # 执行下载
        results = await self.download_batch(enhanced_tasks)

        # 输出最终进度
        completed_count = sum(
            1 for r in results.values() if r.status == TaskStatus.COMPLETED
        )
        self.logger.info(f"下载进度: {completed_count}/{len(download_tasks)} 完成")

        return results


# 便捷函数
async def download_file_async(url: str, save_path: str, **kwargs) -> bool:
    """
    异步下载单个文件

    Args:
        url: 下载URL
        save_path: 保存路径
        **kwargs: 其他参数

    Returns:
        bool: 是否成功
    """
    task = DownloadTask(url=url, save_path=save_path, **kwargs)

    async with AsyncTaskManager() as manager:
        task_id = manager.add_download_task(task)
        result = await manager.wait_for_task(task_id)
        return result.success if result else False


async def download_batch_async(
    download_tasks: List[DownloadTask],
) -> Dict[str, TaskResult]:
    """
    异步批量下载

    Args:
        download_tasks: 下载任务列表

    Returns:
        Dict[str, TaskResult]: 任务结果字典
    """
    async with AsyncTaskManager() as manager:
        downloader = AsyncBatchDownloader(manager)
        return await downloader.download_batch(download_tasks)
