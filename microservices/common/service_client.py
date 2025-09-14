#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务间通信客户端
提供微服务间的通信功能
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import aiohttp
import redis.asyncio as redis
from src.core.logger import get_logger


class ServiceEventType(Enum):
    """服务事件类型"""
    SERVICE_UP = "service_up"
    SERVICE_DOWN = "service_down"
    CONFIG_CHANGE = "config_change"
    ERROR_REPORT = "error_report"
    CACHE_INVALIDATE = "cache_invalidate"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


@dataclass
class ServiceEvent:
    """服务事件"""
    event_type: ServiceEventType
    source_service: str
    target_service: Optional[str] = None
    data: Dict[str, Any] = None
    timestamp: datetime = None
    event_id: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}
        if self.event_id is None:
            import hashlib
            content = f"{self.event_type.value}:{self.source_service}:{self.timestamp.isoformat()}"
            self.event_id = hashlib.md5(content.encode()).hexdigest()


class ServiceDiscovery:
    """服务发现"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = get_logger(__name__)
        self.service_registry = {}

    async def register_service(self, service_name: str, service_url: str, health_check_url: str):
        """注册服务"""
        service_info = {
            "name": service_name,
            "url": service_url,
            "health_check_url": health_check_url,
            "registered_at": datetime.now().isoformat(),
            "status": "healthy"
        }

        self.service_registry[service_name] = service_info

        if self.redis_client:
            try:
                await self.redis_client.hset(
                    f"service:{service_name}",
                    mapping=json.dumps(service_info, default=str)
                )
                await self.redis_client.expire(f"service:{service_name}", 300)  # 5分钟过期
            except Exception as e:
                self.logger.error(f"Failed to register service in Redis: {e}")

        self.logger.info(f"Service registered: {service_name} at {service_url}")

    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """发现服务"""
        # 先从本地缓存查找
        if service_name in self.service_registry:
            return self.service_registry[service_name]

        # 从Redis查找
        if self.redis_client:
            try:
                service_data = await self.redis_client.hgetall(f"service:{service_name}")
                if service_data:
                    service_info = json.loads(list(service_data.values())[0])
                    self.service_registry[service_name] = service_info
                    return service_info
            except Exception as e:
                self.logger.error(f"Failed to discover service from Redis: {e}")

        return None

    async def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务"""
        services = {}

        # 从本地缓存获取
        services.update(self.service_registry)

        # 从Redis获取
        if self.redis_client:
            try:
                service_keys = await self.redis_client.keys("service:*")
                for key in service_keys:
                    service_data = await self.redis_client.hgetall(key)
                    if service_data:
                        service_name = key.replace("service:", "")
                        service_info = json.loads(list(service_data.values())[0])
                        services[service_name] = service_info
                        self.service_registry[service_name] = service_info
            except Exception as e:
                self.logger.error(f"Failed to get services from Redis: {e}")

        return services

    async def unregister_service(self, service_name: str):
        """注销服务"""
        if service_name in self.service_registry:
            del self.service_registry[service_name]

        if self.redis_client:
            try:
                await self.redis_client.delete(f"service:{service_name}")
            except Exception as e:
                self.logger.error(f"Failed to unregister service from Redis: {e}")

        self.logger.info(f"Service unregistered: {service_name}")


class ServiceBus:
    """服务总线"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = get_logger(__name__)
        self.subscribers = {}

    async def publish_event(self, event: ServiceEvent):
        """发布事件"""
        if self.redis_client:
            try:
                event_data = {
                    "event_type": event.event_type.value,
                    "source_service": event.source_service,
                    "target_service": event.target_service,
                    "data": event.data,
                    "timestamp": event.timestamp.isoformat(),
                    "event_id": event.event_id
                }

                # 发布到Redis频道
                await self.redis_client.publish("service_events", json.dumps(event_data))

                # 存储事件历史
                await self.redis_client.lpush(
                    f"service_events:{event.source_service}",
                    json.dumps(event_data, default=str)
                )
                await self.redis_client.ltrim(f"service_events:{event.source_service}", 0, 999)  # 保留最近1000条

                self.logger.debug(f"Event published: {event.event_type.value} from {event.source_service}")

            except Exception as e:
                self.logger.error(f"Failed to publish event: {e}")
        else:
            # 本地事件处理
            await self._handle_local_event(event)

    async def subscribe_to_events(self, event_type: ServiceEventType, callback):
        """订阅事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

        self.logger.info(f"Subscribed to event: {event_type.value}")

    async def _handle_local_event(self, event: ServiceEvent):
        """处理本地事件"""
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.error(f"Event callback error: {e}")

    async def start_event_listener(self):
        """启动事件监听器"""
        if not self.redis_client:
            return

        self.logger.info("Starting event listener")

        try:
            # 创建Redis订阅者
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("service_events")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = ServiceEvent(
                            event_type=ServiceEventType(event_data["event_type"]),
                            source_service=event_data["source_service"],
                            target_service=event_data.get("target_service"),
                            data=event_data["data"],
                            timestamp=datetime.fromisoformat(event_data["timestamp"]),
                            event_id=event_data["event_id"]
                        )
                        await self._handle_local_event(event)
                    except Exception as e:
                        self.logger.error(f"Event processing error: {e}")

        except Exception as e:
            self.logger.error(f"Event listener error: {e}")


class ServiceClient:
    """服务客户端"""

    def __init__(self, service_name: str, discovery: ServiceDiscovery, timeout: int = 30):
        self.service_name = service_name
        self.discovery = discovery
        self.timeout = timeout
        self.logger = get_logger(__name__)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def call_service(self, method: str, endpoint: str, data: Optional[Dict] = None,
                          params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """调用服务"""
        try:
            # 发现服务
            service_info = await self.discovery.discover_service(self.service_name)
            if not service_info:
                raise Exception(f"Service {self.service_name} not found")

            # 构建请求URL
            url = f"{service_info['url']}{endpoint}"

            # 准备请求头
            request_headers = {
                "Content-Type": "application/json",
                "X-Source-Service": "service_client",
                "X-Request-ID": f"req_{datetime.now().timestamp()}"
            }
            if headers:
                request_headers.update(headers)

            # 发送请求
            if method.upper() == "GET":
                async with self.session.get(url, params=params, headers=request_headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "POST":
                async with self.session.post(url, json=data, params=params, headers=request_headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data, params=params, headers=request_headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "DELETE":
                async with self.session.delete(url, params=params, headers=request_headers) as response:
                    return await self._handle_response(response)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")

        except Exception as e:
            self.logger.error(f"Service call failed: {e}")
            raise

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """处理响应"""
        try:
            response_data = await response.json()

            if response.status >= 400:
                raise Exception(f"Service returned error {response.status}: {response_data}")

            return response_data

        except Exception as e:
            self.logger.error(f"Response handling error: {e}")
            raise


class ServiceRegistry:
    """服务注册中心"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = get_logger(__name__)
        self.discovery = ServiceDiscovery(redis_client)
        self.service_bus = ServiceBus(redis_client)

    async def register(self, service_name: str, service_url: str, health_check_url: str):
        """注册服务"""
        await self.discovery.register_service(service_name, service_url, health_check_url)

        # 发布服务上线事件
        event = ServiceEvent(
            event_type=ServiceEventType.SERVICE_UP,
            source_service=service_name,
            data={
                "service_url": service_url,
                "health_check_url": health_check_url
            }
        )
        await self.service_bus.publish_event(event)

    async def unregister(self, service_name: str):
        """注销服务"""
        await self.discovery.unregister_service(service_name)

        # 发布服务下线事件
        event = ServiceEvent(
            event_type=ServiceEventType.SERVICE_DOWN,
            source_service=service_name
        )
        await self.service_bus.publish_event(event)

    async def get_client(self, service_name: str) -> ServiceClient:
        """获取服务客户端"""
        return ServiceClient(service_name, self.discovery)

    async def publish_event(self, event: ServiceEvent):
        """发布事件"""
        await self.service_bus.publish_event(event)

    async def subscribe_to_event(self, event_type: ServiceEventType, callback):
        """订阅事件"""
        await self.service_bus.subscribe_to_events(event_type, callback)

    async def start_event_listener(self):
        """启动事件监听器"""
        await self.service_bus.start_event_listener()


# 创建全局服务注册中心实例
_service_registry = None

async def get_service_registry(redis_client: Optional[redis.Redis] = None) -> ServiceRegistry:
    """获取服务注册中心实例"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry(redis_client)
    return _service_registry


# 便捷函数
async def call_service(service_name: str, method: str, endpoint: str,
                      data: Optional[Dict] = None, params: Optional[Dict] = None,
                      headers: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷的服务调用函数"""
    registry = await get_service_registry()
    async with registry.get_client(service_name) as client:
        return await client.call_service(method, endpoint, data, params, headers)


async def publish_event(event_type: ServiceEventType, source_service: str,
                       target_service: Optional[str] = None, data: Optional[Dict] = None):
    """便捷的事件发布函数"""
    registry = await get_service_registry()
    event = ServiceEvent(
        event_type=event_type,
        source_service=source_service,
        target_service=target_service,
        data=data or {}
    )
    await registry.publish_event(event)


async def subscribe_to_event(event_type: ServiceEventType, callback):
    """便捷的事件订阅函数"""
    registry = await get_service_registry()
    await registry.subscribe_to_event(event_type, callback)