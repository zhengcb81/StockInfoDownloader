#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微服务配置管理
提供统一的配置管理功能
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging

# 导入项目配置管理器
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import ConfigManager


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "stock_downloader"
    username: str = "postgres"
    password: str = "password"
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 50
    decode_responses: bool = True


@dataclass
class MessageQueueConfig:
    """消息队列配置"""
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    connection_timeout: int = 30


@dataclass
class ServiceDiscoveryConfig:
    """服务发现配置"""
    enabled: bool = True
    consul_host: str = "localhost"
    consul_port: int = 8500
    health_check_interval: int = 10
    deregister_after: int = 30


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    metrics_port: int = 9090
    prometheus_path: str = "/metrics"
    log_level: str = "INFO"
    tracing_enabled: bool = True
    jaeger_endpoint: Optional[str] = None


@dataclass
class MicroserviceConfig:
    """微服务配置"""
    service_name: str
    service_version: str = "1.0.0"
    service_host: str = "0.0.0.0"
    service_port: int = 8000
    debug: bool = False
    environment: str = "development"

    # 数据库配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # Redis配置
    redis: RedisConfig = field(default_factory=RedisConfig)

    # 消息队列配置
    message_queue: MessageQueueConfig = field(default_factory=MessageQueueConfig)

    # 服务发现配置
    service_discovery: ServiceDiscoveryConfig = field(default_factory=ServiceDiscoveryConfig)

    # 监控配置
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # CORS配置
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # 其他配置
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_health_check: bool = True


class ServiceConfigManager:
    """服务配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = None
        self.logger = logging.getLogger(__name__)

    def load_config(self, service_name: str, config_file: Optional[str] = None) -> MicroserviceConfig:
        """加载服务配置"""
        if config_file:
            self.config_file = config_file

        # 1. 从环境变量加载
        config = self._load_from_env(service_name)

        # 2. 从配置文件加载（如果存在）
        if self.config_file and Path(self.config_file).exists():
            file_config = self._load_from_file(self.config_file)
            config = self._merge_configs(config, file_config)

        # 3. 从项目配置管理器加载
        project_config = self._load_from_project_config()
        config = self._merge_configs(config, project_config)

        self.config = config
        self.logger.info(f"Loaded configuration for service: {service_name}")
        return config

    def _load_from_env(self, service_name: str) -> MicroserviceConfig:
        """从环境变量加载配置"""
        def get_env_var(key: str, default: Any = None) -> Any:
            return os.getenv(f"{service_name.upper()}_{key.upper()}", default)

        return MicroserviceConfig(
            service_name=service_name,
            service_version=get_env_var("version", "1.0.0"),
            service_host=get_env_var("host", "0.0.0.0"),
            service_port=int(get_env_var("port", "8000")),
            debug=get_env_var("debug", "false").lower() == "true",
            environment=get_env_var("environment", "development"),
            log_level=get_env_var("log_level", "INFO"),
            enable_metrics=get_env_var("enable_metrics", "true").lower() == "true",
            enable_health_check=get_env_var("enable_health_check", "true").lower() == "true",
            cors_origins=get_env_var("cors_origins", "*").split(","),
            database=DatabaseConfig(
                host=get_env_var("db_host", "localhost"),
                port=int(get_env_var("db_port", "5432")),
                database=get_env_var("db_database", "stock_downloader"),
                username=get_env_var("db_username", "postgres"),
                password=get_env_var("db_password", "password"),
                pool_size=int(get_env_var("db_pool_size", "10")),
                max_overflow=int(get_env_var("db_max_overflow", "20"))
            ),
            redis=RedisConfig(
                host=get_env_var("redis_host", "localhost"),
                port=int(get_env_var("redis_port", "6379")),
                db=int(get_env_var("redis_db", "0")),
                password=get_env_var("redis_password"),
                max_connections=int(get_env_var("redis_max_connections", "50")),
                decode_responses=get_env_var("redis_decode_responses", "true").lower() == "true"
            ),
            message_queue=MessageQueueConfig(
                host=get_env_var("mq_host", "localhost"),
                port=int(get_env_var("mq_port", "5672")),
                username=get_env_var("mq_username", "guest"),
                password=get_env_var("mq_password", "guest"),
                virtual_host=get_env_var("mq_virtual_host", "/"),
                connection_timeout=int(get_env_var("mq_connection_timeout", "30"))
            )
        )

    def _load_from_file(self, config_file: str) -> Dict[str, Any]:
        """从配置文件加载"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load config file {config_file}: {e}")
            return {}

    def _load_from_project_config(self) -> Dict[str, Any]:
        """从项目配置管理器加载"""
        try:
            config_manager = ConfigManager()
            return {
                "browser_strategy": config_manager.get('browser_strategy', 'playwright'),
                "headless": config_manager.get('headless', True),
                "timeout": config_manager.get('timeout', {}),
                "anti_crawler": config_manager.get('anti_crawler', {})
            }
        except Exception as e:
            self.logger.warning(f"Failed to load project config: {e}")
            return {}

    def _merge_configs(self, base_config: MicroserviceConfig, override_config: Dict[str, Any]) -> MicroserviceConfig:
        """合并配置"""
        config_dict = asdict(base_config)

        def deep_merge(base: Dict, override: Dict) -> Dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        merged_dict = deep_merge(config_dict, override_config)
        return MicroserviceConfig(**merged_dict)

    def get_config(self) -> MicroserviceConfig:
        """获取当前配置"""
        if not self.config:
            raise ValueError("Configuration not loaded. Call load_config() first.")
        return self.config

    def save_config(self, config_file: str):
        """保存配置到文件"""
        if not self.config:
            raise ValueError("No configuration to save.")

        try:
            config_dict = asdict(self.config)
            with open(config_file, 'w', encoding='utf-8') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {e}")
            raise

    def create_docker_env_file(self, output_file: str = ".env"):
        """创建Docker环境变量文件"""
        if not self.config:
            raise ValueError("No configuration to export.")

        env_lines = []
        config_dict = asdict(self.config)

        def flatten_dict(d: Dict, prefix: str = "") -> Dict[str, str]:
            result = {}
            for key, value in d.items():
                full_key = f"{prefix}_{key}" if prefix else key
                if isinstance(value, dict):
                    result.update(flatten_dict(value, full_key))
                else:
                    result[full_key] = str(value)
            return result

        flat_config = flatten_dict(config_dict)

        for key, value in flat_config.items():
            env_lines.append(f"{key.upper()}={value}")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))

            self.logger.info(f"Docker env file created: {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to create env file: {e}")
            raise


def create_service_config(service_name: str, config_file: Optional[str] = None) -> MicroserviceConfig:
    """创建服务配置的便捷函数"""
    manager = ServiceConfigManager(config_file)
    return manager.load_config(service_name)