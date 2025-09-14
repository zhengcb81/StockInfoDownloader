#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微服务基础类
提供所有微服务的通用功能
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import prometheus_client as prom
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge

# 导入项目模块
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.core.config import ConfigManager


class ServiceStatus(Enum):
    """服务状态"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    version: str
    status: ServiceStatus
    host: str
    port: int
    start_time: float
    health_check_url: str
    metrics_url: str


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    enable_metrics: bool = True
    enable_health_check: bool = True
    log_level: str = "INFO"
    cors_origins: List[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    timestamp: float
    uptime: float
    dependencies: Dict[str, str] = {}


class MetricsResponse(BaseModel):
    """指标响应"""
    service: str
    timestamp: float
    metrics: Dict[str, Any]


class MicroserviceBase(ABC):
    """微服务基类"""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.name = config.name
        self.version = config.version
        self.host = config.host
        self.port = config.port

        # 初始化日志
        self.logger = get_logger(self.name)
        self.logger.setLevel(getattr(logging, config.log_level))

        # 服务状态
        self.status = ServiceStatus.STOPPED
        self.start_time = time.time()

        # FastAPI应用
        self.app = FastAPI(
            title=f"{self.name} Service",
            version=self.version,
            description=f"{self.name} Microservice"
        )

        # 添加CORS中间件
        if config.cors_origins is None:
            config.cors_origins = ["*"]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 初始化指标
        if config.enable_metrics:
            self._init_metrics()

        # 初始化健康检查
        if config.enable_health_check:
            self._init_health_check()

        # 依赖服务
        self.dependencies = {}

        # 注册路由
        self._register_routes()

        # 子类特定的初始化
        self._setup_service()

    def _init_metrics(self):
        """初始化指标收集"""
        # 创建自定义注册表
        self.registry = CollectorRegistry()

        # 基础指标
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )

        self.active_connections = Gauge(
            'active_connections',
            'Active connections',
            registry=self.registry
        )

        # 业务指标
        self.service_metrics = {}

        # 添加指标端点
        @self.app.get("/metrics")
        async def metrics():
            from fastapi.responses import Response
            return Response(
                media_type="text/plain",
                content=prom.generate_latest(self.registry)
            )

        # 添加业务指标端点
        @self.app.get("/api/v1/metrics")
        async def api_metrics():
            metrics_data = {
                "service": self.name,
                "timestamp": time.time(),
                "metrics": {
                    "uptime": time.time() - self.start_time,
                    "status": self.status.value,
                    "dependencies": self.dependencies,
                    "custom_metrics": {k: v._value.get() if hasattr(v, '_value') else v
                                     for k, v in self.service_metrics.items()}
                }
            }
            return MetricsResponse(**metrics_data)

    def _init_health_check(self):
        """初始化健康检查"""

        @self.app.get("/health")
        async def health_check():
            try:
                # 检查依赖服务
                dependency_status = await self._check_dependencies()

                # 如果所有依赖都正常，服务状态为健康
                if all(status == "healthy" for status in dependency_status.values()):
                    service_status = "healthy"
                else:
                    service_status = "degraded"

                return HealthResponse(
                    status=service_status,
                    service=self.name,
                    version=self.version,
                    timestamp=time.time(),
                    uptime=time.time() - self.start_time,
                    dependencies=dependency_status
                )
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return HealthResponse(
                    status="unhealthy",
                    service=self.name,
                    version=self.version,
                    timestamp=time.time(),
                    uptime=time.time() - self.start_time,
                    dependencies={}
                )

    def _register_routes(self):
        """注册基础路由"""

        @self.app.get("/")
        async def root():
            return {
                "service": self.name,
                "version": self.version,
                "status": self.status.value,
                "timestamp": time.time()
            }

        @self.app.get("/api/v1/info")
        async def info():
            return ServiceInfo(
                name=self.name,
                version=self.version,
                status=self.status,
                host=self.host,
                port=self.port,
                start_time=self.start_time,
                health_check_url=f"http://{self.host}:{self.port}/health",
                metrics_url=f"http://{self.host}:{self.port}/metrics"
            ).__dict__

        # 添加请求中间件
        @self.app.middleware("http")
        async def log_requests(request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time

            self.logger.info(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} - {process_time:.3f}s"
            )

            # 记录指标
            if hasattr(self, 'request_counter'):
                self.request_counter.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code
                ).inc()

            if hasattr(self, 'request_duration'):
                self.request_duration.labels(
                    method=request.method,
                    endpoint=request.url.path
                ).observe(process_time)

            return response

    async def _check_dependencies(self) -> Dict[str, str]:
        """检查依赖服务状态"""
        dependency_status = {}

        for name, check_func in self.dependencies.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    status = await check_func()
                else:
                    status = check_func()
                dependency_status[name] = "healthy" if status else "unhealthy"
            except Exception as e:
                self.logger.warning(f"Dependency {name} check failed: {e}")
                dependency_status[name] = "unhealthy"

        return dependency_status

    def add_dependency(self, name: str, check_func):
        """添加依赖服务检查"""
        self.dependencies[name] = check_func

    def add_metric(self, name: str, metric_type: str = "counter", **kwargs):
        """添加自定义指标"""
        if metric_type == "counter":
            metric = Counter(name, kwargs.get('description', ''), registry=self.registry)
        elif metric_type == "gauge":
            metric = Gauge(name, kwargs.get('description', ''), registry=self.registry)
        elif metric_type == "histogram":
            metric = Histogram(name, kwargs.get('description', ''), registry=self.registry)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        self.service_metrics[name] = metric
        return metric

    @abstractmethod
    def _setup_service(self):
        """子类服务特定的设置"""
        pass

    async def start(self):
        """启动服务"""
        try:
            self.status = ServiceStatus.STARTING
            self.logger.info(f"Starting {self.name} service on {self.host}:{self.port}")

            # 启动前检查
            await self._pre_start_check()

            # 启动服务
            self.status = ServiceStatus.RUNNING
            self.start_time = time.time()

            self.logger.info(f"{self.name} service started successfully")

        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.logger.error(f"Failed to start {self.name} service: {e}")
            raise

    async def stop(self):
        """停止服务"""
        try:
            self.status = ServiceStatus.STOPPING
            self.logger.info(f"Stopping {self.name} service")

            # 清理资源
            await self._cleanup()

            self.status = ServiceStatus.STOPPED
            self.logger.info(f"{self.name} service stopped successfully")

        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.logger.error(f"Failed to stop {self.name} service: {e}")
            raise

    async def _pre_start_check(self):
        """启动前检查"""
        pass

    async def _cleanup(self):
        """清理资源"""
        pass

    def run(self):
        """运行服务"""
        try:
            # 启动事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 启动服务
            loop.run_until_complete(self.start())

            # 运行FastAPI应用
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level=self.config.log_level.lower(),
                lifespan=False
            )

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Service error: {e}")
        finally:
            loop.run_until_complete(self.stop())
            loop.close()

    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app

    def get_service_info(self) -> ServiceInfo:
        """获取服务信息"""
        return ServiceInfo(
            name=self.name,
            version=self.version,
            status=self.status,
            host=self.host,
            port=self.port,
            start_time=self.start_time,
            health_check_url=f"http://{self.host}:{self.port}/health",
            metrics_url=f"http://{self.host}:{self.port}/metrics"
        )