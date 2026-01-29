"""
智能缓存策略模块
提供多级缓存、智能预热、自适应淘汰等功能
"""

import asyncio
import functools
import hashlib
import json
import pickle
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.core.config import ConfigManager
from src.core.logger import get_logger


class CacheLevel(Enum):
    """缓存级别"""

    L1_MEMORY = 1  # 内存缓存
    L2_DISK = 2  # 磁盘缓存
    L3_REMOTE = 3  # 远程缓存


class EvictionPolicy(Enum):
    """淘汰策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出
    ARC = "arc"  # 自适应替换缓存
    TTL_BASED = "ttl"  # 基于时间的淘汰


@dataclass
class CacheConfig:
    """缓存配置"""

    # 容量配置
    l1_max_size: int = 1000  # L1缓存最大条目数
    l1_max_memory: int = 100 * 1024 * 1024  # L1缓存最大内存(100MB)
    l2_max_size: int = 10000  # L2缓存最大条目数
    l2_max_disk: int = 1024 * 1024 * 1024  # L2缓存最大磁盘空间(1GB)

    # 生存时间配置
    default_ttl: float = 3600.0  # 默认TTL(1小时)
    l1_ttl: float = 1800.0  # L1缓存TTL(30分钟)
    l2_ttl: float = 7200.0  # L2缓存TTL(2小时)

    # 淘汰策略配置
    l1_eviction_policy: EvictionPolicy = EvictionPolicy.ARC
    l2_eviction_policy: EvictionPolicy = EvictionPolicy.LRU

    # 性能配置
    compression_enabled: bool = True  # 启用压缩
    serialization: str = "pickle"  # 序列化方式 (pickle/json)
    background_cleanup: bool = True  # 后台清理
    cleanup_interval: float = 300.0  # 清理间隔(5分钟)

    # 智能配置
    preload_enabled: bool = True  # 启用预热
    adaptive_ttl: bool = True  # 启用自适应TTL
    hit_rate_threshold: float = 0.8  # 命中率阈值


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size: int = 0
    compression_ratio: float = 1.0
    level: CacheLevel = CacheLevel.L1_MEMORY


class AdaptiveTTL:
    """自适应TTL管理器"""

    def __init__(self, base_ttl: float = 3600.0):
        self.base_ttl = base_ttl
        self.access_patterns = defaultdict(list)
        self.hit_rates = defaultdict(float)
        self.logger = get_logger(__name__)

    def record_access(self, key: str, is_hit: bool):
        """记录访问模式"""
        current_time = time.time()
        self.access_patterns[key].append((current_time, is_hit))

        # 保持最近100次访问记录
        if len(self.access_patterns[key]) > 100:
            self.access_patterns[key] = self.access_patterns[key][-100:]

        # 计算命中率
        recent_accesses = self.access_patterns[key][-20:]  # 最近20次访问
        if recent_accesses:
            hits = sum(1 for _, hit in recent_accesses if hit)
            self.hit_rates[key] = hits / len(recent_accesses)

    def calculate_optimal_ttl(self, key: str) -> float:
        """计算最优TTL"""
        hit_rate = self.hit_rates[key]
        access_count = len(self.access_patterns[key])

        if access_count < 5:  # 数据不足，使用默认值
            return self.base_ttl

        # 基于命中率调整TTL
        if hit_rate > 0.8:  # 高命中率，延长TTL
            return self.base_ttl * 2.0
        elif hit_rate > 0.5:  # 中等命中率，保持默认TTL
            return self.base_ttl
        else:  # 低命中率，缩短TTL
            return self.base_ttl * 0.5

    def get_access_frequency(self, key: str) -> float:
        """获取访问频率"""
        accesses = self.access_patterns[key]
        if not accesses:
            return 0.0

        # 计算最近一小时的访问频率
        current_time = time.time()
        recent_accesses = [t for t, _ in accesses if current_time - t < 3600]
        return len(recent_accesses) / 3600.0


class IntelligentCache:
    """智能缓存系统"""

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化智能缓存

        Args:
            config: 缓存配置
        """
        self.config = config or CacheConfig()
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()

        # 多级缓存
        self.l1_cache = OrderedDict()  # L1内存缓存
        self.l2_cache_path = Path("cache") / "l2_cache"
        self.l2_cache_path.mkdir(parents=True, exist_ok=True)

        # 统计信息
        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "l1_evictions": 0,
            "l2_evictions": 0,
            "total_requests": 0,
            "compression_savings": 0,
            "adaptive_ttl_adjustments": 0,
        }

        # 自适应TTL
        self.adaptive_ttl = AdaptiveTTL(self.config.default_ttl)

        # ARC算法状态
        self.arc_p = 0  # ARC算法中的p参数
        self.arc_t1 = OrderedDict()  # T1: 最近只使用一次
        self.arc_t2 = OrderedDict()  # T2: 最近使用两次或更多
        self.arc_b1 = OrderedDict()  # B1: 最近淘汰的只使用一次项
        self.arc_b2 = OrderedDict()  # B2: 最近淘汰的使用多次项

        # 后台任务
        self.cleanup_task = None
        self.preload_task = None
        self.running = False

        # 事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 启动后台任务
        self._start_background_tasks()

        self.logger.info(
            f"智能缓存初始化完成: L1={self.config.l1_max_size}, "
            f"L2={self.config.l2_max_size}, 策略={self.config.l1_eviction_policy.value}"
        )

    def _start_background_tasks(self):
        """启动后台任务"""
        self.running = True

        # 启动清理任务
        if self.config.background_cleanup:
            self.cleanup_task = threading.Thread(
                target=self._cleanup_worker, daemon=True
            )
            self.cleanup_task.start()

        # 启动预热任务
        if self.config.preload_enabled:
            self.preload_task = threading.Thread(
                target=self._preload_worker, daemon=True
            )
            self.preload_task.start()

    def _cleanup_worker(self):
        """后台清理工作线程"""
        while self.running:
            try:
                self._cleanup_expired_entries()
                self._optimize_cache_size()
                time.sleep(self.config.cleanup_interval)
            except Exception as e:
                self.logger.error(f"缓存清理异常: {e}")
                time.sleep(60)  # 错误后等待1分钟

    def _preload_worker(self):
        """后台预热工作线程"""
        while self.running:
            try:
                self._preload_hot_data()
                time.sleep(600)  # 每10分钟检查一次
            except Exception as e:
                self.logger.error(f"缓存预热异常: {e}")
                time.sleep(300)  # 错误后等待5分钟

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            Any: 缓存值或默认值
        """
        self.stats["total_requests"] += 1

        # 记录访问模式
        is_hit = False
        result = default

        # 尝试L1缓存
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not self._is_entry_expired(entry):
                self._update_access_info(entry, CacheLevel.L1_MEMORY)
                self.stats["l1_hits"] += 1
                is_hit = True
                result = entry.value
                self.adaptive_ttl.record_access(key, True)
            else:
                self._remove_from_l1(key)

        # 尝试L2缓存
        if result is default:
            l2_entry = self._get_from_l2(key)
            if l2_entry and not self._is_entry_expired(l2_entry):
                # 提升到L1缓存
                self._promote_to_l1(l2_entry)
                self.stats["l2_hits"] += 1
                is_hit = True
                result = l2_entry.value
                self.adaptive_ttl.record_access(key, True)
            else:
                self.stats["l2_misses"] += 1
                self.adaptive_ttl.record_access(key, False)

        return result

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间

        Returns:
            bool: 是否成功设置
        """
        try:
            # 自适应TTL
            if ttl is None and self.config.adaptive_ttl:
                ttl = self.adaptive_ttl.calculate_optimal_ttl(key)
            elif ttl is None:
                ttl = self.config.default_ttl

            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                level=CacheLevel.L1_MEMORY,
            )

            # 计算大小
            entry.size = self._calculate_entry_size(entry)

            # 尝试放入L1缓存
            if self._can_fit_in_l1(entry):
                self._add_to_l1(entry)
                return True
            else:
                # L1缓存已满，放入L2缓存
                self._add_to_l2(entry)
                return True

        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存项

        Args:
            key: 缓存键

        Returns:
            bool: 是否成功删除
        """
        deleted = False

        if key in self.l1_cache:
            del self.l1_cache[key]
            deleted = True

        if self._exists_in_l2(key):
            self._remove_from_l2(key)
            deleted = True

        return deleted

    def clear(self):
        """清空所有缓存"""
        self.l1_cache.clear()
        self._clear_l2_cache()
        self.stats = {k: 0 for k in self.stats.keys()}

    def _is_entry_expired(self, entry: CacheEntry) -> bool:
        """检查条目是否过期"""
        return (time.time() - entry.created_at) > entry.ttl

    def _calculate_entry_size(self, entry: CacheEntry) -> int:
        """计算条目大小"""
        try:
            if self.config.serialization == "pickle":
                size = len(pickle.dumps(entry.value))
            else:
                size = len(json.dumps(entry.value, default=str).encode("utf-8"))

            if self.config.compression_enabled:
                # 估算压缩后的大小
                entry.compression_ratio = 0.3  # 假设压缩比为70%
                return int(size * entry.compression_ratio)
            return size

        except Exception:
            return 1024  # 默认1KB

    def _can_fit_in_l1(self, entry: CacheEntry) -> bool:
        """检查是否可以放入L1缓存"""
        if len(self.l1_cache) >= self.config.l1_max_size:
            return False

        current_memory = sum(e.size for e in self.l1_cache.values())
        return (current_memory + entry.size) <= self.config.l1_max_memory

    def _add_to_l1(self, entry: CacheEntry):
        """添加到L1缓存"""
        # 应用淘汰策略
        if self.config.l1_eviction_policy == EvictionPolicy.ARC:
            self._arc_replace(key=entry.key, in_cache=True)
        elif self.config.l1_eviction_policy == EvictionPolicy.LRU:
            if len(self.l1_cache) >= self.config.l1_max_size:
                self.l1_cache.popitem(last=False)
        elif self.config.l1_eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu_from_l1()

        self.l1_cache[entry.key] = entry

    def _add_to_l2(self, entry: CacheEntry):
        """添加到L2缓存"""
        if self.config.l2_eviction_policy == EvictionPolicy.LRU:
            self._evict_lru_from_l2()
        elif self.config.l2_eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu_from_l2()

        entry.level = CacheLevel.L2_DISK
        self._save_to_l2(entry)

    def _promote_to_l1(self, entry: CacheEntry):
        """提升到L1缓存"""
        entry.level = CacheLevel.L1_MEMORY
        if self._can_fit_in_l1(entry):
            self._add_to_l1(entry)
            # 应用ARC算法
            if self.config.l1_eviction_policy == EvictionPolicy.ARC:
                self._arc_replace(key=entry.key, in_cache=True)

    def _update_access_info(self, entry: CacheEntry, level: CacheLevel):
        """更新访问信息"""
        entry.access_count += 1
        entry.last_accessed = time.time()

        if level == CacheLevel.L1_MEMORY:
            # LRU: 移动到末尾
            if self.config.l1_eviction_policy == EvictionPolicy.LRU:
                self.l1_cache.move_to_end(entry.key)
            # ARC: 记录访问
            elif self.config.l1_eviction_policy == EvictionPolicy.ARC:
                self._arc_replace(key=entry.key, in_cache=True)

    def _arc_replace(self, key: str, in_cache: bool):
        """ARC替换算法"""
        if in_cache:
            if key in self.arc_t1:
                # 从T1移动到T2
                self.arc_t2[key] = self.arc_t1.pop(key)
                if key in self.arc_b1:
                    self.arc_b1.pop(key)
            elif key in self.arc_t2:
                # 已在T2，更新访问时间
                self.arc_t2.move_to_end(key)
        else:
            # 缓存未命中，调整p参数
            if key in self.arc_b1:
                self.arc_p = min(self.arc_p + 1, len(self.l1_cache))
            elif key in self.arc_b2:
                self.arc_p = max(self.arc_p - 1, 0)

        # 执行实际的替换
        if len(self.arc_t1) + len(self.arc_t2) > self.config.l1_max_size:
            if len(self.arc_t1) > 0 and (
                len(self.arc_t1) > self.arc_p
                or (key in self.arc_b2 and len(self.arc_t2) == 0)
            ):
                # 从T1淘汰
                evicted_key = next(iter(self.arc_t1))
                self.arc_b1[evicted_key] = self.arc_t1.pop(evicted_key)
                self.stats["l1_evictions"] += 1
            elif len(self.arc_t2) > 0:
                # 从T2淘汰
                evicted_key = next(iter(self.arc_t2))
                self.arc_b2[evicted_key] = self.arc_t2.pop(evicted_key)
                self.stats["l1_evictions"] += 1

    def _evict_lfu_from_l1(self):
        """从L1缓存淘汰最不常用的项"""
        if not self.l1_cache:
            return

        # 找到访问次数最少的项
        min_access = min(e.access_count for e in self.l1_cache.values())
        candidates = [
            k for k, e in self.l1_cache.items() if e.access_count == min_access
        ]

        if candidates:
            evicted_key = candidates[0]
            self.l1_cache.pop(evicted_key)
            self.stats["l1_evictions"] += 1

    def _evict_lru_from_l2(self):
        """从L2缓存淘汰最近最少使用的项"""
        l2_files = list(self.l2_cache_path.glob("*.cache"))
        if len(l2_files) > self.config.l2_max_size:
            # 按修改时间排序，删除最旧的文件
            l2_files.sort(key=lambda f: f.stat().st_mtime)
            for file in l2_files[: len(l2_files) - self.config.l2_max_size]:
                file.unlink()
                self.stats["l2_evictions"] += 1

    def _evict_lfu_from_l2(self):
        """从L2缓存淘汰最不常用的项"""
        # 这个实现较复杂，需要维护L2缓存的访问计数
        self._evict_lru_from_l2()  # 简化实现，使用LRU

    def _get_from_l2(self, key: str) -> Optional[CacheEntry]:
        """从L2缓存获取"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        )

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)

            entry = CacheEntry(**data)
            if not self._is_entry_expired(entry):
                return entry
            else:
                cache_file.unlink()
                return None

        except Exception as e:
            self.logger.warning(f"从L2缓存读取失败: {e}")
            if cache_file.exists():
                cache_file.unlink()
            return None

    def _save_to_l2(self, entry: CacheEntry):
        """保存到L2缓存"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(entry.key.encode()).hexdigest()}.cache"
        )

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(entry.__dict__, f)
        except Exception as e:
            self.logger.error(f"保存到L2缓存失败: {e}")

    def _exists_in_l2(self, key: str) -> bool:
        """检查L2缓存中是否存在"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        )
        return cache_file.exists()

    def _remove_from_l2(self, key: str):
        """从L2缓存删除"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        )
        if cache_file.exists():
            cache_file.unlink()

    def _remove_from_l1(self, key: str):
        """从L1缓存删除"""
        if key in self.l1_cache:
            del self.l1_cache[key]

    def _clear_l2_cache(self):
        """清空L2缓存"""
        for cache_file in self.l2_cache_path.glob("*.cache"):
            cache_file.unlink()

    def _cleanup_expired_entries(self):
        """清理过期条目"""
        # 清理L1缓存
        expired_keys = []
        for key, entry in self.l1_cache.items():
            if self._is_entry_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_from_l1(key)

        # 清理L2缓存
        for cache_file in self.l2_cache_path.glob("*.cache"):
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                entry = CacheEntry(**data)
                if self._is_entry_expired(entry):
                    cache_file.unlink()
            except Exception:
                cache_file.unlink()

    def _optimize_cache_size(self):
        """优化缓存大小"""
        # 基于命中率调整缓存大小
        l1_hit_rate = self.stats["l1_hits"] / max(self.stats["total_requests"], 1)

        if l1_hit_rate < 0.5:  # L1命中率低，考虑增加L1大小
            # 这里可以动态调整配置，但需要谨慎
            pass

    def _preload_hot_data(self):
        """预热热门数据"""
        # 基于访问模式预热数据
        hot_keys = []
        for key, accesses in self.adaptive_ttl.access_patterns.items():
            frequency = self.adaptive_ttl.get_access_frequency(key)
            if frequency > 0.1:  # 每小时访问超过0.1次的数据
                hot_keys.append((key, frequency))

        # 按频率排序，预热最热的数据
        hot_keys.sort(key=lambda x: x[1], reverse=True)
        for key, frequency in hot_keys[:10]:  # 预热前10个最热的数据
            if key not in self.l1_cache:
                # 这里需要实现数据的实际预热逻辑
                pass

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        l1_size = len(self.l1_cache)
        l1_memory = sum(e.size for e in self.l1_cache.values())
        l2_files = len(list(self.l2_cache_path.glob("*.cache")))

        l1_hit_rate = self.stats["l1_hits"] / max(self.stats["total_requests"], 1)
        l2_hit_rate = self.stats["l2_hits"] / max(self.stats["total_requests"], 1)
        overall_hit_rate = (self.stats["l1_hits"] + self.stats["l2_hits"]) / max(
            self.stats["total_requests"], 1
        )

        return {
            "cache_sizes": {
                "l1_entries": l1_size,
                "l1_memory_bytes": l1_memory,
                "l2_files": l2_files,
            },
            "hit_rates": {
                "l1_hit_rate": l1_hit_rate,
                "l2_hit_rate": l2_hit_rate,
                "overall_hit_rate": overall_hit_rate,
            },
            "performance": {
                "total_requests": self.stats["total_requests"],
                "l1_hits": self.stats["l1_hits"],
                "l1_misses": self.stats["l1_misses"],
                "l2_hits": self.stats["l2_hits"],
                "l2_misses": self.stats["l2_misses"],
                "l1_evictions": self.stats["l1_evictions"],
                "l2_evictions": self.stats["l2_evictions"],
            },
            "adaptive_metrics": {
                "adaptive_ttl_adjustments": self.stats["adaptive_ttl_adjustments"],
                "compression_savings": self.stats["compression_savings"],
                "arc_p_parameter": self.arc_p,
            },
        }

    def get_detailed_status(self) -> Dict[str, Any]:
        """获取详细状态信息"""
        stats = self.get_stats()

        # 获取热点数据
        hot_keys = []
        for key, accesses in self.adaptive_ttl.access_patterns.items():
            frequency = self.adaptive_ttl.get_access_frequency(key)
            hit_rate = self.adaptive_ttl.hit_rates[key]
            hot_keys.append(
                {
                    "key": key,
                    "frequency": frequency,
                    "hit_rate": hit_rate,
                    "access_count": len(accesses),
                }
            )

        hot_keys.sort(key=lambda x: x["frequency"], reverse=True)

        return {
            **stats,
            "hot_data": hot_keys[:20],  # 前20个最热的数据
            "cache_config": {
                "l1_max_size": self.config.l1_max_size,
                "l1_max_memory": self.config.l1_max_memory,
                "l2_max_size": self.config.l2_max_size,
                "default_ttl": self.config.default_ttl,
                "eviction_policies": {
                    "l1": self.config.l1_eviction_policy.value,
                    "l2": self.config.l2_eviction_policy.value,
                },
            },
        }

    def cleanup(self):
        """清理资源"""
        self.running = False
        self.clear()


# 装饰器模式
def cached(
    cache: IntelligentCache,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None,
):
    """
    缓存装饰器

    Args:
        cache: 缓存实例
        ttl: 生存时间
        key_func: 自定义键生成函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# 全局缓存实例
_global_cache: Optional[IntelligentCache] = None
_cache_lock = threading.Lock()


def get_global_cache() -> IntelligentCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = IntelligentCache()
    return _global_cache


# 便捷函数
def get_cached(key: str, default: Any = None) -> Any:
    """便捷函数：获取缓存值"""
    return get_global_cache().get(key, default)


def set_cached(key: str, value: Any, ttl: Optional[float] = None) -> bool:
    """便捷函数：设置缓存值"""
    return get_global_cache().set(key, value, ttl)


def delete_cached(key: str) -> bool:
    """便捷函数：删除缓存值"""
    return get_global_cache().delete(key)
