#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
下载服务微服务
提供股票PDF文件下载功能
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field
import redis.asyncio as redis

# 导入微服务基础类
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from microservices.common.service_base import MicroserviceBase, ServiceConfig
from microservices.common.service_config import create_service_config
from src.factory.downloader_factory import downloader_factory
from src.core.logger import get_logger


# 请求和响应模型
class DownloadTaskRequest(BaseModel):
    """下载任务请求 - 微服务API层的数据模型"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    page_types: List[str] = Field(["research", "periodicReports"], description="页面类型")
    keywords: List[str] = Field([], description="关键词过滤")
    max_pages: int = Field(5, description="最大页数")
    priority: str = Field("normal", description="任务优先级")
    callback_url: Optional[str] = Field(None, description="回调URL")


class DownloadTask(BaseModel):
    """下载任务"""
    task_id: str
    request: DownloadTaskRequest
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DownloadResponse(BaseModel):
    """下载响应"""
    task_id: str
    status: str
    message: str
    estimated_duration: Optional[int] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskStatusResponse]
    total: int
    page: int
    page_size: int


class DownloadService(MicroserviceBase):
    """下载服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.tasks: Dict[str, DownloadTask] = {}
        self.redis_client = None
        self.download_service = None
        self.active_downloads = 0
        self.max_concurrent_downloads = 3

        # 自定义指标
        self.tasks_created = self.add_metric(
            "download_tasks_created_total", "counter", "Total download tasks created"
        )
        self.tasks_completed = self.add_metric(
            "download_tasks_completed_total", "counter", "Total download tasks completed"
        )
        self.tasks_failed = self.add_metric(
            "download_tasks_failed_total", "counter", "Total download tasks failed"
        )
        self.download_duration = self.add_metric(
            "download_duration_seconds", "histogram", "Download duration in seconds"
        )

    async def _setup_service(self):
        """设置下载服务"""
        self.logger.info("Setting up download service")

        # 初始化Redis连接
        try:
            redis_config = self.config.redis
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=redis_config.decode_responses,
                max_connections=redis_config.max_connections
            )
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {e}")

        # 初始化下载服务
        self.download_service = downloader_factory.create_downloader('unified')

        # 注册API路由
        self._register_download_routes()

        # 启动后台任务处理器
        asyncio.create_task(self._task_processor())

    def _register_download_routes(self):
        """注册下载相关路由"""

        @self.app.post("/api/v1/download", response_model=DownloadResponse)
        async def create_download_task(request: DownloadTaskRequest, background_tasks: BackgroundTasks):
            """创建下载任务"""
            try:
                task_id = str(uuid.uuid4())
                task = DownloadTask(
                    task_id=task_id,
                    request=request,
                    status="pending",
                    created_at=datetime.now()
                )

                # 存储任务
                self.tasks[task_id] = task

                # 如果连接了Redis，也存储到Redis
                if self.redis_client:
                    await self.redis_client.hset(
                        f"download_task:{task_id}",
                        mapping=json.dumps(task.dict(), default=str)
                    )
                    await self.redis_client.expire(f"download_task:{task_id}", 3600)  # 1小时过期

                # 增加任务创建指标
                self.tasks_created.inc()

                # 估算下载时间
                estimated_duration = self._estimate_download_time(request)

                self.logger.info(f"Created download task {task_id} for stock {request.stock_code}")

                return DownloadResponse(
                    task_id=task_id,
                    status="pending",
                    message="Download task created successfully",
                    estimated_duration=estimated_duration
                )

            except Exception as e:
                self.logger.error(f"Failed to create download task: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/download/{task_id}", response_model=TaskStatusResponse)
        async def get_task_status(task_id: str):
            """获取任务状态"""
            try:
                # 先从内存获取
                task = self.tasks.get(task_id)

                # 如果内存中没有，尝试从Redis获取
                if not task and self.redis_client:
                    task_data = await self.redis_client.hgetall(f"download_task:{task_id}")
                    if task_data:
                        task = DownloadTask(**json.loads(list(task_data.values())[0]))

                if not task:
                    raise HTTPException(status_code=404, detail="Task not found")

                return TaskStatusResponse(**task.dict())

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get task status: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/download", response_model=TaskListResponse)
        async def list_tasks(
            page: int = 1,
            page_size: int = 20,
            status: Optional[str] = None,
            stock_code: Optional[str] = None
        ):
            """获取任务列表"""
            try:
                # 过滤任务
                filtered_tasks = []
                for task in self.tasks.values():
                    if status and task.status != status:
                        continue
                    if stock_code and task.request.stock_code != stock_code:
                        continue
                    filtered_tasks.append(task)

                # 分页
                total = len(filtered_tasks)
                start = (page - 1) * page_size
                end = start + page_size
                paginated_tasks = filtered_tasks[start:end]

                # 转换为响应格式
                task_responses = [
                    TaskStatusResponse(**task.dict()) for task in paginated_tasks
                ]

                return TaskListResponse(
                    tasks=task_responses,
                    total=total,
                    page=page,
                    page_size=page_size
                )

            except Exception as e:
                self.logger.error(f"Failed to list tasks: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/v1/download/{task_id}")
        async def cancel_task(task_id: str):
            """取消任务"""
            try:
                task = self.tasks.get(task_id)
                if not task:
                    raise HTTPException(status_code=404, detail="Task not found")

                if task.status in ["completed", "failed"]:
                    raise HTTPException(status_code=400, detail="Task already completed")

                task.status = "cancelled"
                task.completed_at = datetime.now()

                # 更新Redis
                if self.redis_client:
                    await self.redis_client.hset(
                        f"download_task:{task_id}",
                        mapping=json.dumps(task.dict(), default=str)
                    )

                self.logger.info(f"Cancelled task {task_id}")
                return {"message": "Task cancelled successfully"}

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to cancel task: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/download/batch")
        async def create_batch_tasks(requests: List[DownloadTaskRequest], background_tasks: BackgroundTasks):
            """批量创建下载任务"""
            try:
                task_ids = []
                for request in requests:
                    response = await create_download_task(request, background_tasks)
                    task_ids.append(response.task_id)

                return {
                    "task_ids": task_ids,
                    "total": len(task_ids),
                    "message": f"Created {len(task_ids)} download tasks"
                }

            except Exception as e:
                self.logger.error(f"Failed to create batch tasks: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/download/stats")
        async def get_download_stats():
            """获取下载统计信息"""
            try:
                stats = {
                    "total_tasks": len(self.tasks),
                    "pending_tasks": sum(1 for t in self.tasks.values() if t.status == "pending"),
                    "running_tasks": sum(1 for t in self.tasks.values() if t.status == "running"),
                    "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
                    "failed_tasks": sum(1 for t in self.tasks.values() if t.status == "failed"),
                    "active_downloads": self.active_downloads,
                    "max_concurrent_downloads": self.max_concurrent_downloads
                }

                return stats

            except Exception as e:
                self.logger.error(f"Failed to get download stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _task_processor(self):
        """后台任务处理器"""
        self.logger.info("Task processor started")

        while self.status.value == "running":
            try:
                # 查找待处理任务
                pending_tasks = [
                    task for task in self.tasks.values()
                    if task.status == "pending" and self.active_downloads < self.max_concurrent_downloads
                ]

                if pending_tasks:
                    # 按优先级排序
                    pending_tasks.sort(key=lambda t: self._get_priority_value(t.request.priority))

                    # 处理任务
                    for task in pending_tasks[:self.max_concurrent_downloads - self.active_downloads]:
                        asyncio.create_task(self._execute_task(task))

                await asyncio.sleep(1)  # 每秒检查一次

            except Exception as e:
                self.logger.error(f"Error in task processor: {e}")
                await asyncio.sleep(5)  # 错误时等待更长时间

    async def _execute_task(self, task: DownloadTask):
        """执行下载任务"""
        try:
            self.active_downloads += 1
            task.status = "running"
            task.started_at = datetime.now()

            # 更新任务状态
            self.tasks[task.task_id] = task
            if self.redis_client:
                await self.redis_client.hset(
                    f"download_task:{task.task_id}",
                    mapping=json.dumps(task.dict(), default=str)
                )

            self.logger.info(f"Started executing task {task.task_id}")

            # 执行下载
            start_time = asyncio.get_event_loop().time()
            result = await self._perform_download(task.request)
            duration = asyncio.get_event_loop().time() - start_time

            # 更新任务状态
            task.status = "completed"
            task.completed_at = datetime.now()
            task.progress = 100.0
            task.result = result

            # 记录指标
            self.tasks_completed.inc()
            self.download_duration.observe(duration)

            self.logger.info(f"Task {task.task_id} completed in {duration:.2f}s")

        except Exception as e:
            # 任务失败
            task.status = "failed"
            task.completed_at = datetime.now()
            task.error = str(e)

            # 记录指标
            self.tasks_failed.inc()

            self.logger.error(f"Task {task.task_id} failed: {e}")

        finally:
            self.active_downloads -= 1

            # 更新最终状态
            self.tasks[task.task_id] = task
            if self.redis_client:
                await self.redis_client.hset(
                    f"download_task:{task.task_id}",
                    mapping=json.dumps(task.dict(), default=str)
                )

            # 发送回调（如果有）
            if task.request.callback_url:
                asyncio.create_task(self._send_callback(task))

    async def _perform_download(self, request: DownloadTaskRequest) -> Dict[str, Any]:
        """执行实际的下载操作"""
        try:
            # 设置浏览器策略
            from src.core.config import ConfigManager
            config = ConfigManager()
            config.set('browser_strategy', 'playwright')

            # 聚合结果
            all_downloaded_files = []
            total_execution_time = 0

            # 遍历页面类型进行下载
            for page_type in request.page_types:
                # 使用 UnifiedDownloader 的 download_activity_records 或 download_stock_pdfs
                # 这里使用 download_activity_records 作为兼容入口，它底层调用 download_stock_pdfs
                files = self.download_service.download_activity_records(
                    stock_code=request.stock_code,
                    suffix=page_type,
                    allowed_keywords=request.keywords if request.keywords else None,
                    max_pages=request.max_pages
                )
                
                if files:
                    all_downloaded_files.extend(files)

            return {
                "success": len(all_downloaded_files) > 0,
                "downloaded_files": all_downloaded_files,
                "total_files": len(all_downloaded_files),
                "execution_time": total_execution_time # Currently not tracked precisely per call in this simplified version
            }

        except Exception as e:
            raise Exception(f"Download failed: {e}")

    async def _send_callback(self, task: DownloadTask):
        """发送回调通知"""
        try:
            import aiohttp

            callback_data = {
                "task_id": task.task_id,
                "status": task.status,
                "result": task.result,
                "error": task.error,
                "timestamp": task.completed_at.isoformat() if task.completed_at else None
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(task.request.callback_url, json=callback_data) as response:
                    if response.status == 200:
                        self.logger.info(f"Callback sent successfully for task {task.task_id}")
                    else:
                        self.logger.warning(f"Callback failed for task {task.task_id}: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send callback for task {task.task_id}: {e}")

    def _estimate_download_time(self, request: DownloadTaskRequest) -> int:
        """估算下载时间（秒）"""
        # 基于经验估算：每个页面类型约30秒
        base_time = len(request.page_types) * 30
        # 每个关键词增加10秒
        keyword_time = len(request.keywords) * 10
        # 页数影响
        page_time = request.max_pages * 5

        return base_time + keyword_time + page_time

    def _get_priority_value(self, priority: str) -> int:
        """获取优先级数值"""
        priority_map = {
            "high": 1,
            "normal": 2,
            "low": 3
        }
        return priority_map.get(priority, 2)

    async def _cleanup(self):
        """清理资源"""
        # 关闭Redis连接
        if self.redis_client:
            await self.redis_client.close()

        # 取消所有运行中的任务
        for task in self.tasks.values():
            if task.status == "running":
                task.status = "cancelled"
                task.completed_at = datetime.now()


def create_download_service():
    """创建下载服务实例"""
    # 创建服务配置
    config_dict = ServiceConfig(
        service_name="download-service",
        service_port=8001,
        service_host="0.0.0.0",
        enable_metrics=True,
        enable_health_check=True,
        log_level="INFO",
        cors_origins=["*"]
    )

    return DownloadService(config_dict)


if __name__ == "__main__":
    service = create_download_service()
    service.run()