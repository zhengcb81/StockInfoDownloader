#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置服务微服务
提供分布式配置管理功能
"""

import asyncio
import json
from datetime import datetime
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
class ConfigItem(BaseModel):
    """配置项"""
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值")
    type: str = Field("string", description="配置类型")
    description: Optional[str] = Field(None, description="配置描述")
    is_sensitive: bool = Field(False, description="是否敏感信息")
    environment: str = Field("default", description="环境")
    version: int = Field(1, description="版本号")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")
    is_sensitive: Optional[bool] = Field(None, description="是否敏感信息")


class ConfigQuery(BaseModel):
    """配置查询"""
    environment: Optional[str] = Field(None, description="环境")
    prefix: Optional[str] = Field(None, description="键前缀")
    type: Optional[str] = Field(None, description="配置类型")
    version: Optional[int] = Field(None, description="版本号")


class ConfigHistory(BaseModel):
    """配置历史"""
    key: str
    value: Any
    old_value: Any
    changed_by: str
    changed_at: datetime
    change_reason: Optional[str] = None


class ConfigService(MicroserviceBase):
    """配置服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.redis_client = None
        self.config_cache = {}  # 内存缓存
        self.config_subscribers = {}  # 配置订阅者

        # 自定义指标
        self.config_updates = self.add_metric(
            "config_updates_total", "counter", "Total configuration updates"
        )
        self.config_reads = self.add_metric(
            "config_reads_total", "counter", "Total configuration reads"
        )
        self.configs_by_environment = self.add_metric(
            "configs_by_environment_total", "gauge", "Configs by environment", ["environment"]
        )

    async def _setup_service(self):
        """设置配置服务"""
        self.logger.info("Setting up config service")

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

        # 注册API路由
        self._register_config_routes()

        # 启动配置同步任务
        asyncio.create_task(self._config_sync_task())

    def _register_config_routes(self):
        """注册配置相关路由"""

        @self.app.post("/api/v1/config", response_model=ConfigItem)
        async def create_config(config_item: ConfigItem):
            """创建配置"""
            try:
                # 检查配置是否已存在
                existing = await self._get_config(config_item.key, config_item.environment)
                if existing:
                    raise HTTPException(status_code=409, detail="Configuration already exists")

                # 保存配置
                await self._save_config(config_item)

                # 记录指标
                self.config_updates.inc()

                self.logger.info(f"Configuration created: {config_item.key}")

                return config_item

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to create config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/api/v1/config/{key}", response_model=ConfigItem)
        async def update_config(key: str, request: ConfigUpdateRequest, environment: str = "default"):
            """更新配置"""
            try:
                # 获取现有配置
                existing = await self._get_config(key, environment)
                if not existing:
                    raise HTTPException(status_code=404, detail="Configuration not found")

                # 更新配置
                updated_config = ConfigItem(
                    key=key,
                    value=request.value,
                    type=existing.type,
                    description=request.description or existing.description,
                    is_sensitive=request.is_sensitive if request.is_sensitive is not None else existing.is_sensitive,
                    environment=environment,
                    version=existing.version + 1
                )

                # 保存配置
                await self._save_config(updated_config)

                # 记录历史
                await self._record_config_change(key, existing.value, request.value, "system", "Configuration update")

                # 记录指标
                self.config_updates.inc()

                # 通知订阅者
                await self._notify_config_change(key, environment, request.value)

                self.logger.info(f"Configuration updated: {key}")

                return updated_config

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to update config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/config/{key}")
        async def get_config(key: str, environment: str = "default", version: Optional[int] = None):
            """获取配置"""
            try:
                config = await self._get_config(key, environment, version)
                if not config:
                    raise HTTPException(status_code=404, detail="Configuration not found")

                # 记录指标
                self.config_reads.inc()

                return config

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/v1/config/{key}")
        async def delete_config(key: str, environment: str = "default"):
            """删除配置"""
            try:
                # 获取现有配置
                existing = await self._get_config(key, environment)
                if not existing:
                    raise HTTPException(status_code=404, detail="Configuration not found")

                # 删除配置
                await self._delete_config(key, environment)

                self.logger.info(f"Configuration deleted: {key}")

                return {"deleted": True, "message": "Configuration deleted successfully"}

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to delete config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/config")
        async def list_configs(query: ConfigQuery):
            """列出配置"""
            try:
                configs = await self._list_configs(query)

                return {
                    "configs": configs,
                    "total": len(configs),
                    "query": query.dict()
                }

            except Exception as e:
                self.logger.error(f"Failed to list configs: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/config/{key}/history")
        async def get_config_history(key: str, environment: str = "default", limit: int = 50):
            """获取配置历史"""
            try:
                history = await self._get_config_history(key, environment, limit)

                return {
                    "key": key,
                    "environment": environment,
                    "history": history
                }

            except Exception as e:
                self.logger.error(f"Failed to get config history: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/config/batch")
        async def batch_update_configs(configs: List[ConfigItem]):
            """批量更新配置"""
            try:
                results = []
                for config_item in configs:
                    try:
                        existing = await self._get_config(config_item.key, config_item.environment)
                        if existing:
                            # 更新配置
                            config_item.version = existing.version + 1
                            await self._record_config_change(
                                config_item.key, existing.value, config_item.value, "system", "Batch update"
                            )
                        await self._save_config(config_item)
                        results.append({"key": config_item.key, "status": "success"})
                    except Exception as e:
                        results.append({"key": config_item.key, "status": "error", "error": str(e)})

                self.logger.info(f"Batch config update completed: {len([r for r in results if r['status'] == 'success'])} success")

                return {"results": results}

            except Exception as e:
                self.logger.error(f"Failed to batch update configs: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/config/environments")
        async def get_environments():
            """获取环境列表"""
            try:
                environments = await self._get_environments()

                return {"environments": environments}

            except Exception as e:
                self.logger.error(f"Failed to get environments: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/config/subscribe")
        async def subscribe_config(key: str, environment: str = "default", webhook_url: Optional[str] = None):
            """订阅配置变更"""
            try:
                subscription_id = f"{environment}:{key}"
                self.config_subscribers[subscription_id] = {
                    "webhook_url": webhook_url,
                    "subscribed_at": datetime.now()
                }

                self.logger.info(f"Configuration subscription created: {subscription_id}")

                return {"subscription_id": subscription_id, "status": "subscribed"}

            except Exception as e:
                self.logger.error(f"Failed to subscribe to config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/v1/config/subscribe/{subscription_id}")
        async def unsubscribe_config(subscription_id: str):
            """取消订阅配置变更"""
            try:
                if subscription_id in self.config_subscribers:
                    del self.config_subscribers[subscription_id]
                    return {"unsubscribed": True}
                else:
                    return {"unsubscribed": False, "message": "Subscription not found"}

            except Exception as e:
                self.logger.error(f"Failed to unsubscribe from config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/config/stats")
        async def get_config_stats():
            """获取配置统计"""
            try:
                stats = await self._get_config_stats()

                return stats

            except Exception as e:
                self.logger.error(f"Failed to get config stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/config/export")
        async def export_configs(environment: str = "default"):
            """导出配置"""
            try:
                configs = await self._list_configs(ConfigQuery(environment=environment))

                export_data = {
                    "environment": environment,
                    "exported_at": datetime.now().isoformat(),
                    "configs": configs
                }

                return export_data

            except Exception as e:
                self.logger.error(f"Failed to export configs: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/config/import")
        async def import_configs(export_data: Dict[str, Any]):
            """导入配置"""
            try:
                environment = export_data.get("environment", "default")
                configs = export_data.get("configs", [])

                results = []
                for config_data in configs:
                    try:
                        config_item = ConfigItem(**config_data)
                        existing = await self._get_config(config_item.key, environment)
                        if existing:
                            config_item.version = existing.version + 1
                            await self._record_config_change(
                                config_item.key, existing.value, config_item.value, "system", "Import"
                            )
                        await self._save_config(config_item)
                        results.append({"key": config_item.key, "status": "success"})
                    except Exception as e:
                        results.append({"key": config_item.get("key", "unknown"), "status": "error", "error": str(e)})

                self.logger.info(f"Config import completed: {len([r for r in results if r['status'] == 'success'])} success")

                return {"results": results}

            except Exception as e:
                self.logger.error(f"Failed to import configs: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _save_config(self, config_item: ConfigItem):
        """保存配置"""
        if not self.redis_client:
            # 仅内存存储
            cache_key = f"{config_item.environment}:{config_item.key}"
            self.config_cache[cache_key] = config_item.dict()
            return

        try:
            # 序列化配置
            config_data = config_item.dict()

            # 保存到Redis
            redis_key = f"config:{config_item.environment}:{config_item.key}"
            await self.redis_client.hset(
                redis_key,
                mapping=json.dumps(config_data, default=str)
            )

            # 添加到环境索引
            await self.redis_client.sadd(f"env:{config_item.environment}", config_item.key)

            # 更新内存缓存
            cache_key = f"{config_item.environment}:{config_item.key}"
            self.config_cache[cache_key] = config_data

        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    async def _get_config(self, key: str, environment: str = "default", version: Optional[int] = None) -> Optional[ConfigItem]:
        """获取配置"""
        cache_key = f"{environment}:{key}"

        # 检查内存缓存
        if cache_key in self.config_cache:
            config_data = self.config_cache[cache_key]
            if version is None or config_data.get("version") == version:
                return ConfigItem(**config_data)

        if not self.redis_client:
            return None

        try:
            # 从Redis获取
            redis_key = f"config:{environment}:{key}"
            config_data = await self.redis_client.hgetall(redis_key)

            if config_data:
                config = ConfigItem(**json.loads(list(config_data.values())[0]))

                # 更新内存缓存
                self.config_cache[cache_key] = config.dict()

                if version is None or config.version == version:
                    return config

        except Exception as e:
            self.logger.error(f"Failed to get config: {e}")

        return None

    async def _delete_config(self, key: str, environment: str):
        """删除配置"""
        if not self.redis_client:
            # 仅内存删除
            cache_key = f"{environment}:{key}"
            if cache_key in self.config_cache:
                del self.config_cache[cache_key]
            return

        try:
            # 从Redis删除
            redis_key = f"config:{environment}:{key}"
            await self.redis_client.delete(redis_key)

            # 从环境索引删除
            await self.redis_client.srem(f"env:{environment}", key)

            # 从内存缓存删除
            cache_key = f"{environment}:{key}"
            if cache_key in self.config_cache:
                del self.config_cache[cache_key]

        except Exception as e:
            self.logger.error(f"Failed to delete config: {e}")

    async def _list_configs(self, query: ConfigQuery) -> List[ConfigItem]:
        """列出配置"""
        configs = []

        if not self.redis_client:
            # 从内存缓存获取
            for cache_key, config_data in self.config_cache.items():
                env, key = cache_key.split(":", 1)
                if query.environment and env != query.environment:
                    continue
                if query.prefix and not key.startswith(query.prefix):
                    continue

                config = ConfigItem(**config_data)
                if query.type and config.type != query.type:
                    continue
                if query.version and config.version != query.version:
                    continue

                configs.append(config)
        else:
            try:
                # 从Redis获取
                environment = query.environment or "default"
                keys = await self.redis_client.smembers(f"env:{environment}")

                for key in keys:
                    if query.prefix and not key.startswith(query.prefix):
                        continue

                    config = await self._get_config(key, environment)
                    if config:
                        if query.type and config.type != query.type:
                            continue
                        if query.version and config.version != query.version:
                            continue
                        configs.append(config)

            except Exception as e:
                self.logger.error(f"Failed to list configs: {e}")

        return configs

    async def _get_config_history(self, key: str, environment: str, limit: int) -> List[ConfigHistory]:
        """获取配置历史"""
        # 这里应该实现配置历史记录功能
        # 简化的实现，实际应该存储在Redis中
        return []

    async def _record_config_change(self, key: str, old_value: Any, new_value: Any, changed_by: str, reason: str):
        """记录配置变更"""
        try:
            # 这里应该实现配置变更记录功能
            pass
        except Exception as e:
            self.logger.error(f"Failed to record config change: {e}")

    async def _get_environments(self) -> List[str]:
        """获取环境列表"""
        environments = []

        if not self.redis_client:
            # 从内存缓存获取
            envs = set()
            for cache_key in self.config_cache.keys():
                env = cache_key.split(":", 1)[0]
                envs.add(env)
            return list(envs)

        try:
            # 从Redis获取
            env_keys = await self.redis_client.keys("env:*")
            for env_key in env_keys:
                env = env_key.replace("env:", "")
                environments.append(env)
        except Exception as e:
            self.logger.error(f"Failed to get environments: {e}")

        return environments

    async def _get_config_stats(self) -> Dict[str, Any]:
        """获取配置统计"""
        stats = {
            "total_configs": len(self.config_cache),
            "environments": len(set(key.split(":", 1)[0] for key in self.config_cache.keys())),
            "subscriptions": len(self.config_subscribers),
            "configs_by_environment": {}
        }

        # 按环境统计
        for cache_key in self.config_cache.keys():
            env = cache_key.split(":", 1)[0]
            stats["configs_by_environment"][env] = stats["configs_by_environment"].get(env, 0) + 1

        return stats

    async def _notify_config_change(self, key: str, environment: str, value: Any):
        """通知配置变更"""
        try:
            subscription_id = f"{environment}:{key}"
            if subscription_id in self.config_subscribers:
                subscriber = self.config_subscribers[subscription_id]
                if subscriber.get("webhook_url"):
                    await self._send_webhook_notification(
                        subscriber["webhook_url"],
                        key, environment, value
                    )
        except Exception as e:
            self.logger.error(f"Failed to notify config change: {e}")

    async def _send_webhook_notification(self, webhook_url: str, key: str, environment: str, value: Any):
        """发送Webhook通知"""
        try:
            import aiohttp

            payload = {
                "event": "config_changed",
                "key": key,
                "environment": environment,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook notification sent for {key}")
                    else:
                        self.logger.warning(f"Webhook notification failed for {key}: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")

    async def _config_sync_task(self):
        """配置同步任务"""
        self.logger.info("Config sync task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(60)  # 每分钟同步一次
                await self._sync_configs()
            except Exception as e:
                self.logger.error(f"Config sync task error: {e}")
                await asyncio.sleep(30)

    async def _sync_configs(self):
        """同步配置"""
        try:
            # 这里可以实现与其他配置源的同步
            pass
        except Exception as e:
            self.logger.error(f"Config sync failed: {e}")

    async def _cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()


def create_config_service():
    """创建配置服务实例"""
    # 创建服务配置
    config_dict = ServiceConfig(
        service_name="config-service",
        service_port=8004,
        service_host="0.0.0.0",
        enable_metrics=True,
        enable_health_check=True,
        log_level="INFO",
        cors_origins=["*"]
    )

    return ConfigService(config_dict)


if __name__ == "__main__":
    service = create_config_service()
    service.run()