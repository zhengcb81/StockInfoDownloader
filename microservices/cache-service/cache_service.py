#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
缓存服务微服务
提供智能缓存功能，优化性能和减少重复请求
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
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
class CacheRequest(BaseModel):
    """缓存请求"""
    key: str = Field(..., description="缓存键")
    value: Any = Field(..., description="缓存值")
    ttl: Optional[int] = Field(3600, description="过期时间（秒）")
    tags: Optional[List[str]] = Field([], description="标签")


class CacheResponse(BaseModel):
    """缓存响应"""
    success: bool
    message: str
    key: str
    expires_at: Optional[datetime] = None


class CacheStats(BaseModel):
    """缓存统计"""
    total_keys: int
    hit_count: int
    miss_count: int
    hit_rate: float
    memory_usage: Dict[str, Any]
    top_keys: List[Dict[str, Any]]


class CacheInvalidationRequest(BaseModel):
    """缓存失效请求"""
    keys: Optional[List[str]] = Field(None, description="要失效的键")
    tags: Optional[List[str]] = Field(None, description="要失效的标签")
    pattern: Optional[str] = Field(None, description="键模式")


class CacheService(MicroserviceBase):
    """缓存服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.redis_client = None
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0
        }

        # 自定义指标
        self.cache_hits = self.add_metric(
            "cache_hits_total", "counter", "Total cache hits"
        )
        self.cache_misses = self.add_metric(
            "cache_misses_total", "counter", "Total cache misses"
        )
        self.cache_operations = self.add_metric(
            "cache_operations_total", "counter", "Total cache operations", ["operation"]
        )
        self.cache_size = self.add_metric(
            "cache_size_bytes", "gauge", "Current cache size in bytes"
        )

    async def _setup_service(self):
        """设置缓存服务"""
        self.logger.info("Setting up cache service")

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
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

        # 注册API路由
        self._register_cache_routes()

        # 启动缓存清理任务
        asyncio.create_task(self._cache_cleanup_task())

    def _register_cache_routes(self):
        """注册缓存相关路由"""

        @self.app.post("/api/v1/cache", response_model=CacheResponse)
        async def set_cache(request: CacheRequest):
            """设置缓存"""
            try:
                # 序列化值
                serialized_value = json.dumps(request.value, default=str)

                # 设置缓存
                await self.redis_client.setex(
                    request.key,
                    request.ttl,
                    serialized_value
                )

                # 添加标签索引
                if request.tags:
                    for tag in request.tags:
                        await self.redis_client.sadd(f"tag:{tag}", request.key)

                # 记录指标
                self.cache_operations.labels(operation="set").inc()

                # 计算过期时间
                expires_at = datetime.now() + timedelta(seconds=request.ttl)

                self.logger.info(f"Cache set for key: {request.key}")

                return CacheResponse(
                    success=True,
                    message="Cache set successfully",
                    key=request.key,
                    expires_at=expires_at
                )

            except Exception as e:
                self.logger.error(f"Failed to set cache: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/cache/{key}")
        async def get_cache(key: str):
            """获取缓存"""
            try:
                # 获取缓存值
                cached_value = await self.redis_client.get(key)

                if cached_value is None:
                    # 缓存未命中
                    self.cache_misses.inc()
                    self.cache_operations.labels(operation="miss").inc()
                    self.cache_stats["misses"] += 1
                    self.cache_stats["total_requests"] += 1

                    return {"found": False, "value": None}

                # 缓存命中
                self.cache_hits.inc()
                self.cache_operations.labels(operation="hit").inc()
                self.cache_stats["hits"] += 1
                self.cache_stats["total_requests"] += 1

                # 反序列化值
                value = json.loads(cached_value)

                # 获取剩余TTL
                ttl = await self.redis_client.ttl(key)

                self.logger.debug(f"Cache hit for key: {key}")

                return {
                    "found": True,
                    "value": value,
                    "ttl": ttl
                }

            except Exception as e:
                self.logger.error(f"Failed to get cache: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/v1/cache/{key}")
        async def delete_cache(key: str):
            """删除缓存"""
            try:
                # 删除缓存
                deleted = await self.redis_client.delete(key)

                if deleted:
                    self.cache_operations.labels(operation="delete").inc()
                    self.logger.info(f"Cache deleted for key: {key}")
                    return {"deleted": True, "message": "Cache deleted successfully"}
                else:
                    return {"deleted": False, "message": "Key not found"}

            except Exception as e:
                self.logger.error(f"Failed to delete cache: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/cache/invalidate")
        async def invalidate_cache(request: CacheInvalidationRequest):
            """批量失效缓存"""
            try:
                invalidated_count = 0

                if request.keys:
                    # 按键失效
                    for key in request.keys:
                        deleted = await self.redis_client.delete(key)
                        if deleted:
                            invalidated_count += 1

                if request.tags:
                    # 按标签失效
                    for tag in request.tags:
                        tag_keys = await self.redis_client.smembers(f"tag:{tag}")
                        if tag_keys:
                            deleted = await self.redis_client.delete(*tag_keys)
                            invalidated_count += deleted
                        # 删除标签索引
                        await self.redis_client.delete(f"tag:{tag}")

                if request.pattern:
                    # 按模式失效
                    keys = []
                    async for key in self.redis_client.scan_iter(match=request.pattern):
                        keys.append(key)
                    if keys:
                        deleted = await self.redis_client.delete(*keys)
                        invalidated_count += deleted

                self.cache_operations.labels(operation="invalidate").inc()
                self.logger.info(f"Cache invalidation completed: {invalidated_count} keys")

                return {
                    "invalidated": True,
                    "count": invalidated_count,
                    "message": f"Invalidated {invalidated_count} cache entries"
                }

            except Exception as e:
                self.logger.error(f"Failed to invalidate cache: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/cache/stats", response_model=CacheStats)
        async def get_cache_stats():
            """获取缓存统计"""
            try:
                # 获取Redis信息
                info = await self.redis_client.info("memory")

                # 计算命中率
                total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
                hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

                # 获取最常用的键
                top_keys = []
                try:
                    # 使用Redis的slowlog或其他方式获取常用键
                    keys = await self.redis_client.keys("*")
                    for key in keys[:10]:  # 限制返回数量
                        ttl = await self.redis_client.ttl(key)
                        size = await self.redis_client.memory_usage(key) if hasattr(self.redis_client, 'memory_usage') else 0
                        top_keys.append({
                            "key": key,
                            "ttl": ttl,
                            "size": size
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to get top keys: {e}")

                return CacheStats(
                    total_keys=len(await self.redis_client.keys("*")),
                    hit_count=self.cache_stats["hits"],
                    miss_count=self.cache_stats["misses"],
                    hit_rate=hit_rate,
                    memory_usage={
                        "used_memory": info.get("used_memory", 0),
                        "used_memory_peak": info.get("used_memory_peak", 0),
                        "used_memory_human": info.get("used_memory_human", "0B")
                    },
                    top_keys=top_keys
                )

            except Exception as e:
                self.logger.error(f"Failed to get cache stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/cache/health")
        async def cache_health():
            """缓存健康检查"""
            try:
                # 测试Redis连接
                await self.redis_client.ping()

                # 获取基本统计
                key_count = len(await self.redis_client.keys("*"))

                return {
                    "status": "healthy",
                    "redis_connected": True,
                    "total_keys": key_count,
                    "hit_rate": f"{self.cache_stats['hits'] / max(1, self.cache_stats['total_requests']) * 100:.2f}%"
                }

            except Exception as e:
                self.logger.error(f"Cache health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "redis_connected": False,
                    "error": str(e)
                }

        @self.app.post("/api/v1/cache/cleanup")
        async def cleanup_cache():
            """清理过期缓存"""
            try:
                # Redis会自动清理过期键，这里主要是清理标签索引
                tags = await self.redis_client.keys("tag:*")
                cleaned_tags = 0

                for tag_key in tags:
                    tag_name = tag_key.replace("tag:", "")
                    keys = await self.redis_client.smembers(tag_key)

                    # 检查标签下的键是否还存在
                    valid_keys = []
                    for key in keys:
                        if await self.redis_client.exists(key):
                            valid_keys.append(key)

                    # 更新标签索引
                    if valid_keys:
                        await self.redis_client.delete(tag_key)
                        await self.redis_client.sadd(tag_key, *valid_keys)
                    else:
                        await self.redis_client.delete(tag_key)
                        cleaned_tags += 1

                self.logger.info(f"Cache cleanup completed: {cleaned_tags} empty tags removed")

                return {
                    "cleaned": True,
                    "cleaned_tags": cleaned_tags,
                    "message": f"Cleaned up {cleaned_tags} empty tag indexes"
                }

            except Exception as e:
                self.logger.error(f"Failed to cleanup cache: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _cache_cleanup_task(self):
        """定期缓存清理任务"""
        self.logger.info("Cache cleanup task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._perform_cleanup()
            except Exception as e:
                self.logger.error(f"Cache cleanup task error: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟

    async def _perform_cleanup(self):
        """执行缓存清理"""
        try:
            # 清理过期的标签索引
            tags = await self.redis_client.keys("tag:*")

            for tag_key in tags:
                tag_name = tag_key.replace("tag:", "")
                keys = await self.redis_client.smembers(tag_key)

                # 检查并清理无效的标签
                valid_keys = []
                for key in keys:
                    if await self.redis_client.exists(key):
                        valid_keys.append(key)

                if not valid_keys:
                    await self.redis_client.delete(tag_key)
                    self.logger.debug(f"Cleaned up empty tag: {tag_name}")

        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")

    async def _cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()


def create_cache_service():
    """创建缓存服务实例"""
    # 创建服务配置
    config_dict = ServiceConfig(
        service_name="cache-service",
        service_port=8002,
        service_host="0.0.0.0",
        enable_metrics=True,
        enable_health_check=True,
        log_level="INFO",
        cors_origins=["*"]
    )

    return CacheService(config_dict)


if __name__ == "__main__":
    service = create_cache_service()
    service.run()