#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API网关微服务
提供统一的API入口，路由和负载均衡
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import aiohttp
import redis.asyncio as redis

# 导入微服务基础类
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from microservices.common.service_base import MicroserviceBase, ServiceConfig
from microservices.common.service_config import create_service_config
from src.core.logger import get_logger


# 请求和响应模型
class ServiceInfo(BaseModel):
    """服务信息"""

    name: str
    url: str
    health_check_url: str
    weight: int = 1
    healthy: bool = True
    last_health_check: Optional[datetime] = None


class RouteConfig(BaseModel):
    """路由配置"""

    path: str
    target_service: str
    methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    strip_path: bool = True
    timeout: int = 30


class GatewayStats(BaseModel):
    """网关统计"""

    total_requests: int
    active_connections: int
    requests_by_service: Dict[str, int]
    response_times: Dict[str, float]
    error_rates: Dict[str, float]


class APIGateway(MicroserviceBase):
    """API网关"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.redis_client = None
        self.services: Dict[str, ServiceInfo] = {}
        self.routes: Dict[str, RouteConfig] = {}
        self.request_stats = {
            "total_requests": 0,
            "active_connections": 0,
            "requests_by_service": {},
            "response_times": {},
            "errors": {},
        }

        # 自定义指标
        self.gateway_requests = self.add_metric(
            "gateway_requests_total",
            "counter",
            "Total gateway requests",
            ["service", "method", "status"],
        )
        self.gateway_response_time = self.add_metric(
            "gateway_response_time_seconds",
            "histogram",
            "Gateway response time",
            ["service"],
        )
        self.active_connections = self.add_metric(
            "gateway_active_connections", "gauge", "Active connections"
        )

    async def _setup_service(self):
        """设置API网关"""
        self.logger.info("Setting up API Gateway")

        # 初始化Redis连接
        try:
            redis_config = self.config.redis
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=redis_config.decode_responses,
                max_connections=redis_config.max_connections,
            )
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {e}")

        # 注册服务
        await self._register_services()

        # 注册路由
        await self._register_routes()

        # 注册网关路由
        self._register_gateway_routes()

        # 启动健康检查任务
        asyncio.create_task(self._health_check_task())

    async def _register_services(self):
        """注册微服务"""
        # 从环境变量获取服务地址，默认值为 localhost
        download_host = os.getenv("DOWNLOAD_SERVICE_HOST", "localhost")
        download_port = os.getenv("DOWNLOAD_SERVICE_PORT", "8001")

        cache_host = os.getenv("CACHE_SERVICE_HOST", "localhost")
        cache_port = os.getenv("CACHE_SERVICE_PORT", "8002")

        error_host = os.getenv("ERROR_SERVICE_HOST", "localhost")
        error_port = os.getenv("ERROR_SERVICE_PORT", "8003")

        config_host = os.getenv("CONFIG_SERVICE_HOST", "localhost")
        config_port = os.getenv("CONFIG_SERVICE_PORT", "8004")

        services_config = {
            "download-service": ServiceInfo(
                name="download-service",
                url=f"http://{download_host}:{download_port}",
                health_check_url=f"http://{download_host}:{download_port}/health",
                weight=1,
            ),
            "cache-service": ServiceInfo(
                name="cache-service",
                url=f"http://{cache_host}:{cache_port}",
                health_check_url=f"http://{cache_host}:{cache_port}/health",
                weight=1,
            ),
            "error-service": ServiceInfo(
                name="error-service",
                url=f"http://{error_host}:{error_port}",
                health_check_url=f"http://{error_host}:{error_port}/health",
                weight=1,
            ),
            "config-service": ServiceInfo(
                name="config-service",
                url=f"http://{config_host}:{config_port}",
                health_check_url=f"http://{config_host}:{config_port}/health",
                weight=1,
            ),
        }

        self.services = services_config
        self.logger.info(f"Registered {len(services_config)} services")

    async def _register_routes(self):
        """注册路由配置"""
        routes_config = {
            "/api/v1/download": RouteConfig(
                path="/api/v1/download",
                target_service="download-service",
                methods=["GET", "POST", "PUT", "DELETE"],
            ),
            "/api/v1/cache": RouteConfig(
                path="/api/v1/cache",
                target_service="cache-service",
                methods=["GET", "POST", "PUT", "DELETE"],
            ),
            "/api/v1/errors": RouteConfig(
                path="/api/v1/errors",
                target_service="error-service",
                methods=["GET", "POST"],
            ),
            "/api/v1/config": RouteConfig(
                path="/api/v1/config",
                target_service="config-service",
                methods=["GET", "POST", "PUT", "DELETE"],
            ),
        }

        self.routes = routes_config
        self.logger.info(f"Registered {len(routes_config)} routes")

    def _register_gateway_routes(self):
        """注册网关管理路由"""

        @self.app.get("/gateway/services")
        async def get_services():
            """获取服务列表"""
            return {
                "services": [
                    {
                        "name": service.name,
                        "url": service.url,
                        "healthy": service.healthy,
                        "last_health_check": service.last_health_check,
                        "weight": service.weight,
                    }
                    for service in self.services.values()
                ]
            }

        @self.app.get("/gateway/routes")
        async def get_routes():
            """获取路由配置"""
            return {
                "routes": [
                    {
                        "path": route.path,
                        "target_service": route.target_service,
                        "methods": route.methods,
                        "strip_path": route.strip_path,
                        "timeout": route.timeout,
                    }
                    for route in self.routes.values()
                ]
            }

        @self.app.get("/gateway/stats")
        async def get_stats():
            """获取网关统计"""
            return GatewayStats(
                total_requests=self.request_stats["total_requests"],
                active_connections=self.request_stats["active_connections"],
                requests_by_service=self.request_stats["requests_by_service"],
                response_times=self.request_stats["response_times"],
                error_rates=self._calculate_error_rates(),
            )

        @self.app.post("/gateway/services/{service_name}/health")
        async def check_service_health(service_name: str):
            """手动检查服务健康状态"""
            if service_name not in self.services:
                raise HTTPException(status_code=404, detail="Service not found")

            service = self.services[service_name]
            is_healthy = await self._check_single_service_health(service)

            return {
                "service_name": service_name,
                "healthy": is_healthy,
                "last_check": datetime.now(),
            }

        @self.app.post("/gateway/routes")
        async def add_route(route_config: RouteConfig):
            """添加路由"""
            self.routes[route_config.path] = route_config
            self.logger.info(
                f"Added route: {route_config.path} -> {route_config.target_service}"
            )
            return {"status": "added", "route": route_config.dict()}

        @self.app.delete("/gateway/routes/{path}")
        async def remove_route(path: str):
            """删除路由"""
            if path in self.routes:
                del self.routes[path]
                self.logger.info(f"Removed route: {path}")
                return {"status": "removed"}
            else:
                raise HTTPException(status_code=404, detail="Route not found")

        @self.app.get("/gateway/health")
        async def gateway_health():
            """网关健康检查"""
            healthy_services = sum(
                1 for service in self.services.values() if service.healthy
            )
            total_services = len(self.services)

            return {
                "status": "healthy" if healthy_services > 0 else "degraded",
                "healthy_services": healthy_services,
                "total_services": total_services,
                "active_routes": len(self.routes),
                "timestamp": datetime.now(),
            }

        # 请求中间件
        @self.app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            start_time = datetime.now()

            # 更新活跃连接数
            self.request_stats["active_connections"] += 1
            self.active_connections.inc()

            try:
                # 检查是否是网关管理路由
                if request.url.path.startswith("/gateway/"):
                    response = await call_next(request)
                else:
                    # 代理到目标服务
                    response = await self._proxy_request(request)

                # 记录统计
                self._record_request_stats(request, response, start_time)

                return response

            except Exception as e:
                self.logger.error(f"Gateway middleware error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal Gateway Error", "message": str(e)},
                )
            finally:
                # 减少活跃连接数
                self.request_stats["active_connections"] -= 1
                self.active_connections.dec()

    async def _proxy_request(self, request: Request) -> Response:
        """代理请求到目标服务"""
        try:
            # 查找匹配的路由
            route_config = self._find_matching_route(request)
            if not route_config:
                return JSONResponse(
                    status_code=404, content={"error": "Route not found"}
                )

            # 获取目标服务
            target_service = self.services.get(route_config.target_service)
            if not target_service or not target_service.healthy:
                return JSONResponse(
                    status_code=503, content={"error": "Service unavailable"}
                )

            # 构建目标URL
            target_url = self._build_target_url(request, route_config, target_service)

            # 转发请求
            return await self._forward_request(
                request, target_url, route_config, target_service
            )

        except Exception as e:
            self.logger.error(f"Proxy request error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Gateway proxy error", "message": str(e)},
            )

    def _find_matching_route(self, request: Request) -> Optional[RouteConfig]:
        """查找匹配的路由"""
        for route_path, route_config in self.routes.items():
            if request.url.path.startswith(route_path):
                # 检查HTTP方法
                if request.method in route_config.methods:
                    return route_config

        return None

    def _build_target_url(
        self, request: Request, route_config: RouteConfig, target_service: ServiceInfo
    ) -> str:
        """构建目标URL"""
        target_path = request.url.path
        if route_config.strip_path:
            target_path = target_path[len(route_config.path) :] or "/"

        target_url = f"{target_service.url}{target_path}"
        if request.url.query:
            target_url += f"?{request.url.query}"

        return target_url

    async def _forward_request(
        self,
        request: Request,
        target_url: str,
        route_config: RouteConfig,
        target_service: ServiceInfo,
    ) -> Response:
        """转发请求"""
        try:
            # 准备请求头
            headers = dict(request.headers)
            headers.pop("host", None)  # 移除host头，让aiohttp自动设置
            headers["X-Forwarded-For"] = request.client.host
            headers["X-Forwarded-Proto"] = request.url.scheme
            headers["X-Gateway-Service"] = target_service.name

            # 获取请求体
            body = await request.body()

            # 转发请求
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=route_config.timeout)
            ) as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body if body else None,
                ) as response:
                    # 读取响应体
                    response_body = await response.read()

                    # 构建响应
                    return Response(
                        content=response_body,
                        status_code=response.status,
                        headers=dict(response.headers),
                        media_type=response.content_type,
                    )

        except asyncio.TimeoutError:
            self.logger.warning(
                f"Request timeout to {target_service.name}: {target_url}"
            )
            return JSONResponse(status_code=504, content={"error": "Gateway timeout"})
        except aiohttp.ClientError as e:
            self.logger.error(f"Client error forwarding to {target_service.name}: {e}")
            return JSONResponse(status_code=502, content={"error": "Bad gateway"})

    def _record_request_stats(
        self, request: Request, response: Response, start_time: datetime
    ):
        """记录请求统计"""
        # 更新总请求数
        self.request_stats["total_requests"] += 1

        # 获取目标服务
        route_config = self._find_matching_route(request)
        if route_config:
            service_name = route_config.target_service

            # 按服务统计请求数
            self.request_stats["requests_by_service"][service_name] = (
                self.request_stats["requests_by_service"].get(service_name, 0) + 1
            )

            # 记录响应时间
            response_time = (datetime.now() - start_time).total_seconds()
            if service_name not in self.request_stats["response_times"]:
                self.request_stats["response_times"][service_name] = []
            self.request_stats["response_times"][service_name].append(response_time)

            # 记录错误
            if response.status_code >= 400:
                if service_name not in self.request_stats["errors"]:
                    self.request_stats["errors"][service_name] = 0
                self.request_stats["errors"][service_name] += 1

            # 记录Prometheus指标
            self.gateway_requests.labels(
                service=service_name, method=request.method, status=response.status_code
            ).inc()
            self.gateway_response_time.labels(service=service_name).observe(
                response_time
            )

    def _calculate_error_rates(self) -> Dict[str, float]:
        """计算错误率"""
        error_rates = {}
        for service_name, requests_count in self.request_stats[
            "requests_by_service"
        ].items():
            errors_count = self.request_stats["errors"].get(service_name, 0)
            error_rate = (
                (errors_count / requests_count * 100) if requests_count > 0 else 0
            )
            error_rates[service_name] = round(error_rate, 2)
        return error_rates

    async def _health_check_task(self):
        """健康检查任务"""
        self.logger.info("Health check task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._check_all_services_health()
            except Exception as e:
                self.logger.error(f"Health check task error: {e}")
                await asyncio.sleep(60)

    async def _check_all_services_health(self):
        """检查所有服务健康状态"""
        for service in self.services.values():
            try:
                is_healthy = await self._check_single_service_health(service)
                service.healthy = is_healthy
                service.last_health_check = datetime.now()

                if not is_healthy:
                    self.logger.warning(f"Service {service.name} is unhealthy")
                else:
                    self.logger.debug(f"Service {service.name} is healthy")

            except Exception as e:
                self.logger.error(f"Health check failed for {service.name}: {e}")
                service.healthy = False

    async def _check_single_service_health(self, service: ServiceInfo) -> bool:
        """检查单个服务健康状态"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(service.health_check_url) as response:
                    if response.status == 200:
                        try:
                            health_data = await response.json()
                            return health_data.get("status") == "healthy"
                        except Exception:
                            return True
                    return False
        except Exception:
            return False

    async def _cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()


def create_api_gateway():
    """创建API网关实例"""
    # 创建服务配置
    config_dict = ServiceConfig(
        service_name="api-gateway",
        service_port=8000,
        service_host="0.0.0.0",
        enable_metrics=True,
        enable_health_check=True,
        log_level="INFO",
        cors_origins=["*"],
    )

    return APIGateway(config_dict)


if __name__ == "__main__":
    gateway = create_api_gateway()
    gateway.run()
