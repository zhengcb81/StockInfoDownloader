#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代理管理器
支持多种代理类型，智能轮换和健康检查
"""

import random
import time
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import hashlib
from pathlib import Path

from src.core.logger import get_logger


class ProxyType(Enum):
    """代理类型枚举"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"
    RESIDENTIAL = "residential"
    DATA_CENTER = "data_center"
    ELITE = "elite"


class ProxyStatus(Enum):
    """代理状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    BANNED = "banned"
    EXPIRED = "expired"


@dataclass
class ProxyInfo:
    """代理信息数据类"""
    ip: str
    port: int
    proxy_type: ProxyType
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    provider: Optional[str] = None
    response_time: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[float] = None
    last_checked: Optional[float] = None
    status: ProxyStatus = ProxyStatus.ACTIVE
    score: float = 100.0
    max_requests: int = 100
    current_requests: int = 0
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.last_checked is None:
            self.last_checked = time.time()
        if self.score is None:
            self.score = 100.0

    @property
    def proxy_url(self) -> str:
        """获取代理URL"""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.ip}:{self.port}"
        else:
            return f"{self.proxy_type.value}://{self.ip}:{self.port}"

    @property
    def is_expired(self) -> bool:
        """检查代理是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def is_banned(self) -> bool:
        """检查代理是否被封禁"""
        return self.status == ProxyStatus.BANNED

    @property
    def is_active(self) -> bool:
        """检查代理是否活跃"""
        return self.status == ProxyStatus.ACTIVE and not self.is_expired

    def record_request(self, success: bool, response_time: float):
        """记录请求结果"""
        self.total_requests += 1
        self.current_requests += 1
        self.last_used = time.time()

        if success:
            self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests
        else:
            self.failed_requests += 1
            self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests

        # 更新响应时间（使用移动平均）
        if self.response_time > 0:
            self.response_time = 0.7 * self.response_time + 0.3 * response_time
        else:
            self.response_time = response_time

        # 更新评分
        self.update_score()

    def update_score(self):
        """更新代理评分"""
        # 基础分数
        score = 100.0

        # 成功率影响
        score *= self.success_rate

        # 响应时间影响（越快越好）
        if self.response_time > 0:
            time_factor = max(0.1, 1.0 - (self.response_time / 10.0))
            score *= time_factor

        # 使用频率影响（避免过度使用）
        usage_factor = 1.0 - (self.current_requests / self.max_requests)
        score *= max(0.1, usage_factor)

        # 年龄影响（新代理有初始优势）
        age = time.time() - self.created_at
        if age < 3600:  # 1小时内
            score *= 1.2
        elif age > 86400:  # 24小时以上
            score *= 0.8

        self.score = max(0.0, min(100.0, score))

    def reset_usage(self):
        """重置使用计数"""
        self.current_requests = 0

    def get_unique_id(self) -> str:
        """获取代理唯一标识"""
        unique_str = f"{self.ip}:{self.port}:{self.proxy_type.value}:{self.provider or ''}"
        return hashlib.md5(unique_str.encode()).hexdigest()


class ProxyPool:
    """代理池"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = get_logger(f"ProxyPool.{name}")

        self.proxies: Dict[str, ProxyInfo] = {}
        self.lock = threading.RLock()

        self.max_size = config.get('max_size', 100)
        self.rotation_interval = config.get('rotation_interval', 100)
        self.health_check_interval = config.get('health_check_interval', 60)
        self.max_usage_time = config.get('max_usage_time', 1800)

        # 启动健康检查线程
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()

        self.logger.info(f"代理池 {name} 初始化完成，最大容量: {self.max_size}")

    def add_proxy(self, proxy_info: ProxyInfo):
        """添加代理到池中"""
        with self.lock:
            proxy_id = proxy_info.get_unique_id()

            # 检查是否已存在
            if proxy_id in self.proxies:
                self.logger.warning(f"代理 {proxy_info.ip}:{proxy_info.port} 已存在")
                return

            # 检查池是否已满
            if len(self.proxies) >= self.max_size:
                # 移除评分最低的代理
                self._remove_worst_proxy()

            self.proxies[proxy_id] = proxy_info
            self.logger.info(f"添加代理: {proxy_info.ip}:{proxy_info.port} ({proxy_info.proxy_type.value})")

    def remove_proxy(self, proxy_id: str):
        """从池中移除代理"""
        with self.lock:
            if proxy_id in self.proxies:
                proxy = self.proxies.pop(proxy_id)
                self.logger.info(f"移除代理: {proxy.ip}:{proxy.port}")

    def _remove_worst_proxy(self):
        """移除评分最低的代理"""
        if not self.proxies:
            return

        worst_proxy_id = min(
            self.proxies.keys(),
            key=lambda pid: self.proxies[pid].score
        )

        self.remove_proxy(worst_proxy_id)

    def get_proxy(self, requirements: Optional[Dict[str, Any]] = None) -> Optional[ProxyInfo]:
        """获取代理"""
        with self.lock:
            # 过滤活跃代理
            active_proxies = [
                proxy for proxy in self.proxies.values()
                if proxy.is_active
            ]

            if not active_proxies:
                self.logger.warning(f"代理池 {self.name} 中没有可用的代理")
                return None

            # 根据要求过滤
            if requirements:
                filtered_proxies = self._filter_proxies(active_proxies, requirements)
            else:
                filtered_proxies = active_proxies

            if not filtered_proxies:
                self.logger.warning(f"没有符合要求的代理")
                return None

            # 根据评分选择代理（权重随机选择）
            return self._select_proxy_by_score(filtered_proxies)

    def _filter_proxies(self, proxies: List[ProxyInfo], requirements: Dict[str, Any]) -> List[ProxyInfo]:
        """根据要求过滤代理"""
        filtered = proxies

        # 按代理类型过滤
        if 'proxy_type' in requirements:
            req_type = requirements['proxy_type']
            if isinstance(req_type, str):
                req_type = ProxyType(req_type)
            filtered = [p for p in filtered if p.proxy_type == req_type]

        # 按国家过滤
        if 'country' in requirements:
            country = requirements['country']
            filtered = [p for p in filtered if p.country == country]

        # 按最小评分过滤
        if 'min_score' in requirements:
            min_score = requirements['min_score']
            filtered = [p for p in filtered if p.score >= min_score]

        # 按最大响应时间过滤
        if 'max_response_time' in requirements:
            max_time = requirements['max_response_time']
            filtered = [p for p in filtered if p.response_time <= max_time]

        return filtered

    def _select_proxy_by_score(self, proxies: List[ProxyInfo]) -> ProxyInfo:
        """根据评分选择代理（权重随机）"""
        # 计算总权重
        total_weight = sum(proxy.score for proxy in proxies)

        if total_weight == 0:
            return random.choice(proxies)

        # 权重随机选择
        rand_value = random.uniform(0, total_weight)
        current_weight = 0

        for proxy in proxies:
            current_weight += proxy.score
            if current_weight >= rand_value:
                return proxy

        # 如果随机选择失败，返回评分最高的代理
        return max(proxies, key=lambda p: p.score)

    def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"健康检查失败: {e}")
                time.sleep(self.health_check_interval)

    def _perform_health_checks(self):
        """执行健康检查"""
        with self.lock:
            proxy_list = list(self.proxies.values())

        # 使用线程池并行检查
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for proxy in proxy_list:
                if proxy.is_active:
                    future = executor.submit(self._check_proxy_health, proxy)
                    futures.append(future)

            # 等待检查完成
            for future in futures:
                try:
                    future.result(timeout=10)
                except Exception as e:
                    self.logger.error(f"代理健康检查异常: {e}")

    def _check_proxy_health(self, proxy: ProxyInfo):
        """检查单个代理的健康状况"""
        try:
            # 测试代理连接
            test_url = "http://httpbin.org/ip"

            start_time = time.time()
            response = requests.get(
                test_url,
                proxies={'http': proxy.proxy_url, 'https': proxy.proxy_url},
                timeout=10
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                proxy.record_request(True, response_time)
                proxy.status = ProxyStatus.ACTIVE
                proxy.last_checked = time.time()
                self.logger.debug(f"代理 {proxy.ip}:{proxy.port} 健康检查通过，响应时间: {response_time:.2f}s")
            else:
                proxy.record_request(False, response_time)
                proxy.status = ProxyStatus.INACTIVE
                self.logger.warning(f"代理 {proxy.ip}:{proxy.port} 健康检查失败: HTTP {response.status_code}")

        except Exception as e:
            proxy.record_request(False, 0)
            proxy.status = ProxyStatus.INACTIVE
            self.logger.debug(f"代理 {proxy.ip}:{proxy.port} 健康检查异常: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取代理池统计信息"""
        with self.lock:
            total_proxies = len(self.proxies)
            active_proxies = sum(1 for p in self.proxies.values() if p.is_active)

            if total_proxies > 0:
                avg_score = sum(p.score for p in self.proxies.values()) / total_proxies
                avg_response_time = sum(p.response_time for p in self.proxies.values()) / total_proxies
                avg_success_rate = sum(p.success_rate for p in self.proxies.values()) / total_proxies
            else:
                avg_score = 0
                avg_response_time = 0
                avg_success_rate = 0

            return {
                'name': self.name,
                'total_proxies': total_proxies,
                'active_proxies': active_proxies,
                'avg_score': avg_score,
                'avg_response_time': avg_response_time,
                'avg_success_rate': avg_success_rate,
                'max_size': self.max_size,
                'health_check_interval': self.health_check_interval
            }


class ProxyManager:
    """代理管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("ProxyManager")

        # 初始化代理池
        self.pools: Dict[str, ProxyPool] = {}

        pools_config = config.get('pools', {})
        for pool_name, pool_config in pools_config.items():
            if pool_config.get('enabled', True):
                self.pools[pool_name] = ProxyPool(pool_name, pool_config)

        # 轮换策略配置
        self.rotation_strategies = config.get('rotation_strategies', {})

        # 健康检查配置
        self.health_check_config = config.get('health_check', {})

        # 加载代理提供商
        self.providers = config.get('providers', [])

        # 初始化代理
        self._initialize_proxies()

        self.logger.info(f"代理管理器初始化完成，管理 {len(self.pools)} 个代理池")

    def _initialize_proxies(self):
        """初始化代理"""
        # 从配置中加载静态代理
        static_proxies = self.config.get('static_proxies', [])
        for proxy_config in static_proxies:
            self._add_proxy_from_config(proxy_config)

        # 从提供商加载代理
        for provider in self.providers:
            if provider.get('enabled', True):
                self._load_proxies_from_provider(provider)

    def _add_proxy_from_config(self, proxy_config: Dict[str, Any]):
        """从配置添加代理"""
        try:
            proxy_info = ProxyInfo(
                ip=proxy_config['ip'],
                port=proxy_config['port'],
                proxy_type=ProxyType(proxy_config.get('type', 'http')),
                username=proxy_config.get('username'),
                password=proxy_config.get('password'),
                country=proxy_config.get('country'),
                provider=proxy_config.get('provider'),
                max_requests=proxy_config.get('max_requests', 100)
            )

            # 添加到相应的池
            pool_name = proxy_config.get('pool', 'data_center')
            if pool_name in self.pools:
                self.pools[pool_name].add_proxy(proxy_info)
            else:
                self.logger.warning(f"代理池 {pool_name} 不存在")

        except Exception as e:
            self.logger.error(f"添加代理失败: {e}")

    def _load_proxies_from_provider(self, provider: Dict[str, Any]):
        """从提供商加载代理"""
        provider_name = provider.get('name', 'unknown')
        provider_type = provider.get('type', 'residential')

        self.logger.info(f"从提供商 {provider_name} 加载代理...")

        # 这里可以实现从各种提供商API获取代理的逻辑
        # 例如：Luminati, Oxylabs, Smartproxy等

        # 示例：添加一些测试代理
        if provider_name == 'luminati':
            # 这里应该调用Luminati API获取代理
            self.logger.info("Luminati代理加载逻辑待实现")
        elif provider_name == 'test':
            # 添加测试代理
            test_proxies = [
                {'ip': '127.0.0.1', 'port': 8080, 'type': 'http', 'pool': 'data_center'},
                {'ip': '127.0.0.1', 'port': 1080, 'type': 'socks5', 'pool': 'elite'},
            ]

            for proxy_config in test_proxies:
                proxy_config['provider'] = provider_name
                self._add_proxy_from_config(proxy_config)

    def get_proxy(self, requirements: Optional[Dict[str, Any]] = None) -> Optional[ProxyInfo]:
        """获取代理"""
        # 根据要求选择代理池
        pool_name = self._select_pool(requirements)

        if pool_name and pool_name in self.pools:
            proxy = self.pools[pool_name].get_proxy(requirements)
            if proxy:
                self.logger.debug(f"获取代理: {proxy.proxy_url}")
                return proxy

        # 如果指定池没有可用代理，尝试其他池
        for pool_name, pool in self.pools.items():
            if requirements and requirements.get('pool') != pool_name:
                continue

            proxy = pool.get_proxy(requirements)
            if proxy:
                self.logger.debug(f"从备用池 {pool_name} 获取代理: {proxy.proxy_url}")
                return proxy

        self.logger.warning("没有可用的代理")
        return None

    def _select_pool(self, requirements: Optional[Dict[str, Any]]) -> Optional[str]:
        """选择代理池"""
        if requirements and 'pool' in requirements:
            return requirements['pool']

        # 根据代理类型选择池
        if requirements and 'proxy_type' in requirements:
            proxy_type = requirements['proxy_type']
            if isinstance(proxy_type, str):
                proxy_type = ProxyType(proxy_type)

            if proxy_type in [ProxyType.ELITE, ProxyType.SOCKS5]:
                return 'elite'
            elif proxy_type == ProxyType.RESIDENTIAL:
                return 'residential'
            else:
                return 'data_center'

        # 默认返回数据中心代理池
        return 'data_center'

    def release_proxy(self, proxy_info: ProxyInfo, success: bool, response_time: float):
        """释放代理"""
        proxy_info.record_request(success, response_time)

        # 根据使用情况决定是否需要轮换
        if self._should_rotate_proxy(proxy_info):
            # 临时禁用代理
            proxy_info.status = ProxyStatus.INACTIVE
            self.logger.debug(f"代理 {proxy_info.ip}:{proxy_info.port} 已轮换")

    def _should_rotate_proxy(self, proxy_info: ProxyInfo) -> bool:
        """判断是否需要轮换代理"""
        # 检查请求次数
        max_requests = proxy_info.max_requests
        if proxy_info.current_requests >= max_requests:
            return True

        # 检查使用时间
        max_usage_time = self.config.get('max_usage_time', 1800)
        if proxy_info.last_used and (time.time() - proxy_info.last_used) > max_usage_time:
            return True

        # 检查评分
        min_score = self.config.get('min_score', 50.0)
        if proxy_info.score < min_score:
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        stats = {
            'total_pools': len(self.pools),
            'pools': {}
        }

        for pool_name, pool in self.pools.items():
            stats['pools'][pool_name] = pool.get_stats()

        return stats

    def save_state(self, file_path: str):
        """保存代理状态到文件"""
        try:
            state = {
                'timestamp': time.time(),
                'pools': {}
            }

            for pool_name, pool in self.pools.items():
                state['pools'][pool_name] = {
                    'proxies': [
                        {
                            'ip': proxy.ip,
                            'port': proxy.port,
                            'proxy_type': proxy.proxy_type.value,
                            'country': proxy.country,
                            'provider': proxy.provider,
                            'score': proxy.score,
                            'success_rate': proxy.success_rate,
                            'response_time': proxy.response_time,
                            'status': proxy.status.value,
                            'total_requests': proxy.total_requests,
                            'failed_requests': proxy.failed_requests
                        }
                        for proxy in pool.proxies.values()
                    ]
                }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            self.logger.info(f"代理状态已保存到 {file_path}")

        except Exception as e:
            self.logger.error(f"保存代理状态失败: {e}")

    def load_state(self, file_path: str):
        """从文件加载代理状态"""
        try:
            if not Path(file_path).exists():
                self.logger.warning(f"代理状态文件 {file_path} 不存在")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 恢复代理状态
            for pool_name, pool_data in state.get('pools', {}).items():
                if pool_name in self.pools:
                    pool = self.pools[pool_name]

                    # 恢复代理统计信息
                    for proxy_data in pool_data.get('proxies', []):
                        proxy_id = f"{proxy_data['ip']}:{proxy_data['port']}:{proxy_data['proxy_type']}"

                        if proxy_id in pool.proxies:
                            proxy = pool.proxies[proxy_id]
                            proxy.score = proxy_data.get('score', 100.0)
                            proxy.success_rate = proxy_data.get('success_rate', 1.0)
                            proxy.response_time = proxy_data.get('response_time', 0.0)
                            proxy.status = ProxyStatus(proxy_data.get('status', 'active'))
                            proxy.total_requests = proxy_data.get('total_requests', 0)
                            proxy.failed_requests = proxy_data.get('failed_requests', 0)

            self.logger.info(f"代理状态已从 {file_path} 加载")

        except Exception as e:
            self.logger.error(f"加载代理状态失败: {e}")

    def rotate_all_proxies(self):
        """轮换所有代理"""
        self.logger.info("开始轮换所有代理...")

        for pool_name, pool in self.pools.items():
            with pool.lock:
                for proxy in pool.proxies.values():
                    if proxy.is_active:
                        proxy.status = ProxyStatus.INACTIVE
                        proxy.current_requests = 0

        self.logger.info("所有代理已轮换")

    def cleanup_expired_proxies(self):
        """清理过期代理"""
        self.logger.info("开始清理过期代理...")

        total_removed = 0

        for pool_name, pool in self.pools.items():
            with pool.lock:
                expired_proxies = [
                    proxy_id for proxy_id, proxy in pool.proxies.items()
                    if proxy.is_expired
                ]

                for proxy_id in expired_proxies:
                    proxy = pool.proxies[proxy_id]
                    self.logger.info(f"移除过期代理: {proxy.ip}:{proxy.port}")
                    del pool.proxies[proxy_id]
                    total_removed += 1

        self.logger.info(f"清理完成，移除 {total_removed} 个过期代理")