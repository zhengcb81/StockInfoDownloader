#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误处理服务微服务
提供统一的错误处理、日志聚合和告警功能
"""

import asyncio
import json
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr
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
class ErrorReport(BaseModel):
    """错误报告"""
    service_name: str = Field(..., description="服务名称")
    error_type: str = Field(..., description="错误类型")
    error_message: str = Field(..., description="错误消息")
    stack_trace: Optional[str] = Field(None, description="堆栈跟踪")
    context: Optional[Dict[str, Any]] = Field(None, description="错误上下文")
    severity: str = Field("error", description="严重程度: debug, info, warning, error, critical")
    timestamp: Optional[datetime] = Field(None, description="错误时间")


class ErrorAlert(BaseModel):
    """错误告警"""
    id: str
    service_name: str
    error_type: str
    error_message: str
    severity: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class ErrorQuery(BaseModel):
    """错误查询"""
    service_name: Optional[str] = Field(None, description="服务名称")
    error_type: Optional[str] = Field(None, description="错误类型")
    severity: Optional[str] = Field(None, description="严重程度")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(100, description="限制数量")


class NotificationConfig(BaseModel):
    """通知配置"""
    email_enabled: bool = Field(False, description="启用邮件通知")
    email_recipients: List[EmailStr] = Field([], description="邮件接收者")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    slack_webhook: Optional[str] = Field(None, description="Slack Webhook")


class ErrorService(MicroserviceBase):
    """错误处理服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.redis_client = None
        self.notification_config = NotificationConfig()
        self.error_counts = {}  # 内存中的错误计数
        self.active_alerts = {}  # 活跃的告警

        # 自定义指标
        self.errors_received = self.add_metric(
            "errors_received_total", "counter", "Total errors received"
        )
        self.alerts_created = self.add_metric(
            "alerts_created_total", "counter", "Total alerts created"
        )
        self.errors_by_service = self.add_metric(
            "errors_by_service_total", "counter", "Errors by service", ["service"]
        )
        self.errors_by_severity = self.add_metric(
            "errors_by_severity_total", "counter", "Errors by severity", ["severity"]
        )

    async def _setup_service(self):
        """设置错误处理服务"""
        self.logger.info("Setting up error service")

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

        # 加载通知配置
        self._load_notification_config()

        # 注册API路由
        self._register_error_routes()

        # 启动后台任务
        asyncio.create_task(self._error_analysis_task())
        asyncio.create_task(self._alert_monitor_task())
        asyncio.create_task(self._cleanup_task())

    def _load_notification_config(self):
        """加载通知配置"""
        try:
            # 从环境变量加载配置
            self.notification_config = NotificationConfig(
                email_enabled=self._get_env_bool("ERROR_EMAIL_ENABLED", False),
                email_recipients=self._get_env_list("ERROR_EMAIL_RECIPIENTS", []),
                webhook_url=self._get_env("ERROR_WEBHOOK_URL"),
                slack_webhook=self._get_env("ERROR_SLACK_WEBHOOK")
            )
        except Exception as e:
            self.logger.warning(f"Failed to load notification config: {e}")

    def _get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        import os
        return os.getenv(key, default)

    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔环境变量"""
        value = self._get_env(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def _get_env_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """获取列表环境变量"""
        value = self._get_env(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _register_error_routes(self):
        """注册错误处理相关路由"""

        @self.app.post("/api/v1/errors")
        async def report_error(error_report: ErrorReport):
            """报告错误"""
            try:
                # 设置默认时间戳
                if not error_report.timestamp:
                    error_report.timestamp = datetime.now()

                # 生成错误ID
                error_id = self._generate_error_id(error_report)

                # 存储错误
                await self._store_error(error_id, error_report)

                # 更新错误计数
                self._update_error_count(error_report)

                # 记录指标
                self.errors_received.inc()
                self.errors_by_service.labels(service=error_report.service_name).inc()
                self.errors_by_severity.labels(severity=error_report.severity).inc()

                # 检查是否需要创建告警
                await self._check_alert_conditions(error_report)

                self.logger.info(f"Error reported from {error_report.service_name}: {error_report.error_type}")

                return {
                    "id": error_id,
                    "status": "received",
                    "message": "Error report received successfully"
                }

            except Exception as e:
                self.logger.error(f"Failed to report error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/errors")
        async def query_errors(query: ErrorQuery):
            """查询错误"""
            try:
                errors = await self._query_errors(query)

                return {
                    "errors": errors,
                    "total": len(errors),
                    "query": query.dict()
                }

            except Exception as e:
                self.logger.error(f"Failed to query errors: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/errors/{error_id}")
        async def get_error(error_id: str):
            """获取错误详情"""
            try:
                error = await self._get_error(error_id)
                if not error:
                    raise HTTPException(status_code=404, detail="Error not found")

                return error

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/alerts")
        async def get_alerts(
            service_name: Optional[str] = None,
            severity: Optional[str] = None,
            resolved: Optional[bool] = None,
            limit: int = 100
        ):
            """获取告警列表"""
            try:
                alerts = await self._get_alerts(service_name, severity, resolved, limit)

                return {
                    "alerts": alerts,
                    "total": len(alerts)
                }

            except Exception as e:
                self.logger.error(f"Failed to get alerts: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/alerts/{alert_id}/resolve")
        async def resolve_alert(alert_id: str, notes: Optional[str] = None):
            """解决告警"""
            try:
                result = await self._resolve_alert(alert_id, notes)

                return result

            except Exception as e:
                self.logger.error(f"Failed to resolve alert: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/errors/stats")
        async def get_error_stats():
            """获取错误统计"""
            try:
                stats = await self._get_error_stats()

                return stats

            except Exception as e:
                self.logger.error(f"Failed to get error stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/v1/notifications/config")
        async def update_notification_config(config: NotificationConfig):
            """更新通知配置"""
            try:
                self.notification_config = config

                return {
                    "status": "updated",
                    "message": "Notification configuration updated successfully"
                }

            except Exception as e:
                self.logger.error(f"Failed to update notification config: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/v1/notifications/config")
        async def get_notification_config():
            """获取通知配置"""
            return self.notification_config

    def _generate_error_id(self, error_report: ErrorReport) -> str:
        """生成错误ID"""
        # 基于服务名称、错误类型和错误消息生成唯一ID
        import hashlib
        content = f"{error_report.service_name}:{error_report.error_type}:{error_report.error_message}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _store_error(self, error_id: str, error_report: ErrorReport):
        """存储错误"""
        if not self.redis_client:
            self.logger.warning("Redis not available, skipping error storage")
            return

        try:
            error_data = error_report.dict()
            error_data["id"] = error_id

            # 存储错误数据
            await self.redis_client.hset(
                f"error:{error_id}",
                mapping=json.dumps(error_data, default=str)
            )

            # 设置过期时间（30天）
            await self.redis_client.expire(f"error:{error_id}", 30 * 24 * 3600)

            # 添加到错误列表
            await self.redis_client.lpush(
                "errors:recent",
                error_id
            )

            # 限制最近错误列表大小
            await self.redis_client.ltrim("errors:recent", 0, 999)

        except Exception as e:
            self.logger.error(f"Failed to store error: {e}")

    def _update_error_count(self, error_report: ErrorReport):
        """更新错误计数"""
        key = f"{error_report.service_name}:{error_report.error_type}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    async def _check_alert_conditions(self, error_report: ErrorReport):
        """检查告警条件"""
        key = f"{error_report.service_name}:{error_report.error_type}"
        count = self.error_counts.get(key, 0)

        # 如果错误次数达到阈值，创建告警
        if count >= 5:  # 5次错误触发告警
            alert_key = f"alert:{key}"
            if alert_key not in self.active_alerts:
                alert = ErrorAlert(
                    id=alert_key,
                    service_name=error_report.service_name,
                    error_type=error_report.error_type,
                    error_message=error_report.error_message,
                    severity=error_report.severity,
                    count=count,
                    first_occurrence=error_report.timestamp,
                    last_occurrence=error_report.timestamp
                )

                self.active_alerts[alert_key] = alert
                self.alerts_created.inc()

                # 发送通知
                await self._send_alert_notification(alert)

                self.logger.warning(f"Alert created for {key}: {count} occurrences")

    async def _send_alert_notification(self, alert: ErrorAlert):
        """发送告警通知"""
        try:
            message = f"🚨 Alert: {alert.service_name} - {alert.error_type}\n"
            message += f"Count: {alert.count}\n"
            message += f"Severity: {alert.severity}\n"
            message += f"Message: {alert.error_message}\n"
            message += f"First occurrence: {alert.first_occurrence}\n"
            message += f"Last occurrence: {alert.last_occurrence}"

            # 发送邮件通知
            if self.notification_config.email_enabled and self.notification_config.email_recipients:
                await self._send_email_alert(alert, message)

            # 发送Webhook通知
            if self.notification_config.webhook_url:
                await self._send_webhook_alert(alert, message)

            # 发送Slack通知
            if self.notification_config.slack_webhook:
                await self._send_slack_alert(alert, message)

        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {e}")

    async def _send_email_alert(self, alert: ErrorAlert, message: str):
        """发送邮件告警"""
        # 这里应该集成邮件服务，示例实现
        self.logger.info(f"Email alert would be sent to {self.notification_config.email_recipients}")

    async def _send_webhook_alert(self, alert: ErrorAlert, message: str):
        """发送Webhook告警"""
        try:
            import aiohttp

            payload = {
                "alert_id": alert.id,
                "service_name": alert.service_name,
                "error_type": alert.error_type,
                "error_message": alert.error_message,
                "severity": alert.severity,
                "count": alert.count,
                "timestamp": alert.last_occurrence.isoformat(),
                "message": message
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.notification_config.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Webhook alert sent successfully")
                    else:
                        self.logger.warning(f"Webhook alert failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    async def _send_slack_alert(self, alert: ErrorAlert, message: str):
        """发送Slack告警"""
        try:
            import aiohttp

            payload = {
                "text": message,
                "attachments": [
                    {
                        "color": "danger" if alert.severity in ["error", "critical"] else "warning",
                        "fields": [
                            {
                                "title": "Service",
                                "value": alert.service_name,
                                "short": True
                            },
                            {
                                "title": "Error Type",
                                "value": alert.error_type,
                                "short": True
                            },
                            {
                                "title": "Count",
                                "value": str(alert.count),
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity,
                                "short": True
                            }
                        ]
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.notification_config.slack_webhook, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Slack alert sent successfully")
                    else:
                        self.logger.warning(f"Slack alert failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    async def _query_errors(self, query: ErrorQuery) -> List[Dict[str, Any]]:
        """查询错误"""
        errors = []

        if not self.redis_client:
            return errors

        try:
            # 获取最近的错误ID列表
            error_ids = await self.redis_client.lrange("errors:recent", 0, query.limit - 1)

            for error_id in error_ids:
                error_data = await self.redis_client.hgetall(f"error:{error_id}")
                if error_data:
                    error = json.loads(list(error_data.values())[0])

                    # 应用过滤条件
                    if query.service_name and error.get("service_name") != query.service_name:
                        continue
                    if query.error_type and error.get("error_type") != query.error_type:
                        continue
                    if query.severity and error.get("severity") != query.severity:
                        continue
                    if query.start_time and error.get("timestamp"):
                        error_time = datetime.fromisoformat(error["timestamp"])
                        if error_time < query.start_time:
                            continue
                    if query.end_time and error.get("timestamp"):
                        error_time = datetime.fromisoformat(error["timestamp"])
                        if error_time > query.end_time:
                            continue

                    errors.append(error)

                    if len(errors) >= query.limit:
                        break

        except Exception as e:
            self.logger.error(f"Failed to query errors: {e}")

        return errors

    async def _get_error(self, error_id: str) -> Optional[Dict[str, Any]]:
        """获取错误详情"""
        if not self.redis_client:
            return None

        try:
            error_data = await self.redis_client.hgetall(f"error:{error_id}")
            if error_data:
                return json.loads(list(error_data.values())[0])
        except Exception as e:
            self.logger.error(f"Failed to get error: {e}")

        return None

    async def _get_alerts(self, service_name: Optional[str], severity: Optional[str],
                        resolved: Optional[bool], limit: int) -> List[Dict[str, Any]]:
        """获取告警列表"""
        alerts = []

        for alert in self.active_alerts.values():
            # 应用过滤条件
            if service_name and alert.service_name != service_name:
                continue
            if severity and alert.severity != severity:
                continue
            if resolved is not None and alert.resolved != resolved:
                continue

            alerts.append(alert.dict())

            if len(alerts) >= limit:
                break

        return alerts

    async def _resolve_alert(self, alert_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            if notes:
                alert.resolution_notes = notes

            self.logger.info(f"Alert resolved: {alert_id}")
            return {
                "status": "resolved",
                "alert_id": alert_id,
                "resolved_at": alert.resolved_at
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")

    async def _get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        stats = {
            "total_errors": sum(self.error_counts.values()),
            "unique_errors": len(self.error_counts),
            "active_alerts": len([a for a in self.active_alerts.values() if not a.resolved]),
            "errors_by_service": {},
            "errors_by_severity": {},
            "top_errors": []
        }

        # 按服务统计
        for key, count in self.error_counts.items():
            service_name = key.split(":")[0]
            stats["errors_by_service"][service_name] = stats["errors_by_service"].get(service_name, 0) + count

        # 获取Top错误
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        stats["top_errors"] = [{"error_type": key, "count": count} for key, count in sorted_errors[:10]]

        return stats

    async def _error_analysis_task(self):
        """错误分析任务"""
        self.logger.info("Error analysis task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(300)  # 每5分钟分析一次
                await self._analyze_errors()
            except Exception as e:
                self.logger.error(f"Error analysis task error: {e}")
                await asyncio.sleep(60)

    async def _analyze_errors(self):
        """分析错误模式"""
        try:
            # 这里可以实现错误模式分析、趋势分析等
            pass
        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")

    async def _alert_monitor_task(self):
        """告警监控任务"""
        self.logger.info("Alert monitor task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._monitor_alerts()
            except Exception as e:
                self.logger.error(f"Alert monitor task error: {e}")
                await asyncio.sleep(60)

    async def _monitor_alerts(self):
        """监控告警状态"""
        try:
            # 检查是否需要升级告警或自动解决
            for alert_id, alert in self.active_alerts.items():
                if not alert.resolved:
                    # 检查告警是否长时间未解决
                    if datetime.now() - alert.last_occurrence > timedelta(hours=1):
                        # 可以在这里实现告警升级逻辑
                        pass
        except Exception as e:
            self.logger.error(f"Alert monitoring failed: {e}")

    async def _cleanup_task(self):
        """清理任务"""
        self.logger.info("Cleanup task started")

        while self.status.value == "running":
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                await self._cleanup_old_data()
            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(300)

    async def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            # 清理已解决的告警
            resolved_alerts = [
                alert_id for alert_id, alert in self.active_alerts.items()
                if alert.resolved and (datetime.now() - alert.resolved_at > timedelta(days=7))
            ]

            for alert_id in resolved_alerts:
                del self.active_alerts[alert_id]
                self.logger.debug(f"Cleaned up resolved alert: {alert_id}")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

    async def _cleanup(self):
        """清理资源"""
        if self.redis_client:
            await self.redis_client.close()


def create_error_service():
    """创建错误服务实例"""
    # 创建服务配置
    config_dict = ServiceConfig(
        service_name="error-service",
        service_port=8003,
        service_host="0.0.0.0",
        enable_metrics=True,
        enable_health_check=True,
        log_level="INFO",
        cors_origins=["*"]
    )

    return ErrorService(config_dict)


if __name__ == "__main__":
    service = create_error_service()
    service.run()