"""
Intelligent Cache Strategy Module
Provides multi-level caching, smart preloading, and adaptive eviction features
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
    """Cache level enumeration"""

    L1_MEMORY = 1  # In-memory cache
    L2_DISK = 2  # Disk cache
    L3_REMOTE = 3  # Remote cache


class EvictionPolicy(Enum):
    """Cache eviction policy enumeration"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    ARC = "arc"  # Adaptive Replacement Cache
    TTL_BASED = "ttl"  # Time-based eviction


@dataclass
class CacheConfig:
    """Cache configuration"""

    # Capacity settings
    l1_max_size: int = 1000  # L1 max entries
    l1_max_memory: int = 100 * 1024 * 1024  # L1 max memory (100MB)
    l2_max_size: int = 10000  # L2 max entries
    l2_max_disk: int = 1024 * 1024 * 1024  # L2 max disk space (1GB)

    # TTL settings
    default_ttl: float = 3600.0  # Default TTL (1 hour)
    l1_ttl: float = 1800.0  # L1 TTL (30 minutes)
    l2_ttl: float = 7200.0  # L2 TTL (2 hours)

    # Eviction policy settings
    l1_eviction_policy: EvictionPolicy = EvictionPolicy.ARC
    l2_eviction_policy: EvictionPolicy = EvictionPolicy.LRU

    # Performance settings
    compression_enabled: bool = True  # Enable compression
    serialization: str = "pickle"  # Serialization method (pickle/json)
    background_cleanup: bool = True  # Background cleanup
    cleanup_interval: float = 300.0  # Cleanup interval (5 minutes)

    # Smart settings
    preload_enabled: bool = True  # Enable preloading
    adaptive_ttl: bool = True  # Enable adaptive TTL
    hit_rate_threshold: float = 0.8  # Hit rate threshold


@dataclass
class CacheEntry:
    """Cache entry data class"""

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
    """Adaptive TTL manager"""

    def __init__(self, base_ttl: float = 3600.0) -> None:
        self.base_ttl = base_ttl
        self.access_patterns: Dict[str, List[tuple]] = defaultdict(list)
        self.hit_rates: Dict[str, float] = defaultdict(float)
        self.logger = get_logger(__name__)

    def record_access(self, key: str, is_hit: bool) -> None:
        """Record access pattern"""
        current_time = time.time()
        self.access_patterns[key].append((current_time, is_hit))

        # Keep last 100 access records
        if len(self.access_patterns[key]) > 100:
            self.access_patterns[key] = self.access_patterns[key][-100:]

        # Calculate hit rate
        recent_accesses = self.access_patterns[key][-20:]  # Last 20 accesses
        if recent_accesses:
            hits = sum(1 for _, hit in recent_accesses if hit)
            self.hit_rates[key] = hits / len(recent_accesses)

    def calculate_optimal_ttl(self, key: str) -> float:
        """Calculate optimal TTL based on access patterns"""
        hit_rate = self.hit_rates[key]
        access_count = len(self.access_patterns[key])

        if access_count < 5:  # Insufficient data, use default
            return self.base_ttl

        # Adjust TTL based on hit rate
        if hit_rate > 0.8:  # High hit rate, extend TTL
            return self.base_ttl * 2.0
        elif hit_rate > 0.5:  # Medium hit rate, keep default TTL
            return self.base_ttl
        else:  # Low hit rate, shorten TTL
            return self.base_ttl * 0.5

    def get_access_frequency(self, key: str) -> float:
        """Get access frequency per hour"""
        accesses = self.access_patterns[key]
        if not accesses:
            return 0.0

        # Calculate access frequency in last hour
        current_time = time.time()
        recent_accesses = [t for t, _ in accesses if current_time - t < 3600]
        return len(recent_accesses) / 3600.0


class IntelligentCache:
    """Intelligent caching system"""

    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        """
        Initialize intelligent cache

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager()

        # Multi-level cache
        self.l1_cache: OrderedDict = OrderedDict()  # L1 in-memory cache
        self.l2_cache_path = Path("cache") / "l2_cache"
        self.l2_cache_path.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats: Dict[str, int] = {
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

        # Adaptive TTL
        self.adaptive_ttl = AdaptiveTTL(self.config.default_ttl)

        # ARC algorithm state
        self.arc_p = 0  # ARC p parameter
        self.arc_t1: OrderedDict = OrderedDict()  # T1: recently used once
        self.arc_t2: OrderedDict = OrderedDict()  # T2: recently used twice or more
        self.arc_b1: OrderedDict = OrderedDict()  # B1: recently evicted once-used items
        self.arc_b2: OrderedDict = OrderedDict()  # B2: recently evicted multi-used items

        # Background tasks
        self.cleanup_task: Optional[threading.Thread] = None
        self.preload_task: Optional[threading.Thread] = None
        self.running = False

        # Event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Start background tasks
        self._start_background_tasks()

        self.logger.info(
            f"Intelligent cache initialized: L1={self.config.l1_max_size}, "
            f"L2={self.config.l2_max_size}, policy={self.config.l1_eviction_policy.value}"
        )

    def _start_background_tasks(self) -> None:
        """Start background tasks"""
        self.running = True

        # Start cleanup task
        if self.config.background_cleanup:
            self.cleanup_task = threading.Thread(
                target=self._cleanup_worker, daemon=True
            )
            self.cleanup_task.start()

        # Start preload task
        if self.config.preload_enabled:
            self.preload_task = threading.Thread(
                target=self._preload_worker, daemon=True
            )
            self.preload_task.start()

    def _cleanup_worker(self) -> None:
        """Background cleanup worker thread"""
        while self.running:
            try:
                self._cleanup_expired_entries()
                self._optimize_cache_size()
                time.sleep(self.config.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
                time.sleep(60)  # Wait 1 minute after error

    def _preload_worker(self) -> None:
        """Background preload worker thread"""
        while self.running:
            try:
                self._preload_hot_data()
                time.sleep(600)  # Check every 10 minutes
            except Exception as e:
                self.logger.error(f"Cache preload error: {e}")
                time.sleep(300)  # Wait 5 minutes after error

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get cached value

        Args:
            key: Cache key
            default: Default value

        Returns:
            Any: Cached value or default
        """
        self.stats["total_requests"] += 1

        # Record access pattern
        is_hit = False
        result = default

        # Try L1 cache
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

        # Try L2 cache
        if result is default:
            l2_entry = self._get_from_l2(key)
            if l2_entry and not self._is_entry_expired(l2_entry):
                # Promote to L1 cache
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
        Set cache value

        Args:
            key: Cache key
            value: Cache value
            ttl: Time to live

        Returns:
            bool: Whether successfully set
        """
        try:
            # Adaptive TTL
            if ttl is None and self.config.adaptive_ttl:
                ttl = self.adaptive_ttl.calculate_optimal_ttl(key)
            elif ttl is None:
                ttl = self.config.default_ttl

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                level=CacheLevel.L1_MEMORY,
            )

            # Calculate size
            entry.size = self._calculate_entry_size(entry)

            # Try to put in L1 cache
            if self._can_fit_in_l1(entry):
                self._add_to_l1(entry)
                return True
            else:
                # L1 cache full, put in L2 cache
                self._add_to_l2(entry)
                return True

        except Exception as e:
            self.logger.error(f"Failed to set cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete cache entry

        Args:
            key: Cache key

        Returns:
            bool: Whether successfully deleted
        """
        deleted = False

        if key in self.l1_cache:
            del self.l1_cache[key]
            deleted = True

        if self._exists_in_l2(key):
            self._remove_from_l2(key)
            deleted = True

        return deleted

    def clear(self) -> None:
        """Clear all cache"""
        self.l1_cache.clear()
        self._clear_l2_cache()
        self.stats = {k: 0 for k in self.stats.keys()}

    def _is_entry_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired"""
        return (time.time() - entry.created_at) > entry.ttl

    def _calculate_entry_size(self, entry: CacheEntry) -> int:
        """Calculate entry size"""
        try:
            if self.config.serialization == "pickle":
                size = len(pickle.dumps(entry.value))
            else:
                size = len(json.dumps(entry.value, default=str).encode("utf-8"))

            if self.config.compression_enabled:
                # Estimate compressed size
                entry.compression_ratio = 0.3  # Assume 70% compression ratio
                return int(size * entry.compression_ratio)
            return size

        except Exception:
            return 1024  # Default 1KB

    def _can_fit_in_l1(self, entry: CacheEntry) -> bool:
        """Check if can fit in L1 cache"""
        if len(self.l1_cache) >= self.config.l1_max_size:
            return False

        current_memory = sum(e.size for e in self.l1_cache.values())
        return (current_memory + entry.size) <= self.config.l1_max_memory

    def _add_to_l1(self, entry: CacheEntry) -> None:
        """Add to L1 cache"""
        # Apply eviction policy
        if self.config.l1_eviction_policy == EvictionPolicy.ARC:
            self._arc_replace(key=entry.key, in_cache=True)
        elif self.config.l1_eviction_policy == EvictionPolicy.LRU:
            if len(self.l1_cache) >= self.config.l1_max_size:
                self.l1_cache.popitem(last=False)
        elif self.config.l1_eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu_from_l1()

        self.l1_cache[entry.key] = entry

    def _add_to_l2(self, entry: CacheEntry) -> None:
        """Add to L2 cache"""
        if self.config.l2_eviction_policy == EvictionPolicy.LRU:
            self._evict_lru_from_l2()
        elif self.config.l2_eviction_policy == EvictionPolicy.LFU:
            self._evict_lfu_from_l2()

        entry.level = CacheLevel.L2_DISK
        self._save_to_l2(entry)

    def _promote_to_l1(self, entry: CacheEntry) -> None:
        """Promote to L1 cache"""
        entry.level = CacheLevel.L1_MEMORY
        if self._can_fit_in_l1(entry):
            self._add_to_l1(entry)
            # Apply ARC algorithm
            if self.config.l1_eviction_policy == EvictionPolicy.ARC:
                self._arc_replace(key=entry.key, in_cache=True)

    def _update_access_info(self, entry: CacheEntry, level: CacheLevel) -> None:
        """Update access information"""
        entry.access_count += 1
        entry.last_accessed = time.time()

        if level == CacheLevel.L1_MEMORY:
            # LRU: Move to end
            if self.config.l1_eviction_policy == EvictionPolicy.LRU:
                self.l1_cache.move_to_end(entry.key)
            # ARC: Record access
            elif self.config.l1_eviction_policy == EvictionPolicy.ARC:
                self._arc_replace(key=entry.key, in_cache=True)

    def _arc_replace(self, key: str, in_cache: bool) -> None:
        """ARC replacement algorithm"""
        if in_cache:
            if key in self.arc_t1:
                # Move from T1 to T2
                self.arc_t2[key] = self.arc_t1.pop(key)
                if key in self.arc_b1:
                    self.arc_b1.pop(key)
            elif key in self.arc_t2:
                # Already in T2, update access time
                self.arc_t2.move_to_end(key)
        else:
            # Cache miss, adjust p parameter
            if key in self.arc_b1:
                self.arc_p = min(self.arc_p + 1, len(self.l1_cache))
            elif key in self.arc_b2:
                self.arc_p = max(self.arc_p - 1, 0)

        # Execute actual replacement
        if len(self.arc_t1) + len(self.arc_t2) > self.config.l1_max_size:
            if len(self.arc_t1) > 0 and (
                len(self.arc_t1) > self.arc_p
                or (key in self.arc_b2 and len(self.arc_t2) == 0)
            ):
                # Evict from T1
                evicted_key = next(iter(self.arc_t1))
                self.arc_b1[evicted_key] = self.arc_t1.pop(evicted_key)
                self.stats["l1_evictions"] += 1
            elif len(self.arc_t2) > 0:
                # Evict from T2
                evicted_key = next(iter(self.arc_t2))
                self.arc_b2[evicted_key] = self.arc_t2.pop(evicted_key)
                self.stats["l1_evictions"] += 1

    def _evict_lfu_from_l1(self) -> None:
        """Evict least frequently used item from L1 cache"""
        if not self.l1_cache:
            return

        # Find item with minimum access count
        min_access = min(e.access_count for e in self.l1_cache.values())
        candidates = [
            k for k, e in self.l1_cache.items() if e.access_count == min_access
        ]

        if candidates:
            evicted_key = candidates[0]
            self.l1_cache.pop(evicted_key)
            self.stats["l1_evictions"] += 1

    def _evict_lru_from_l2(self) -> None:
        """Evict least recently used item from L2 cache"""
        l2_files = list(self.l2_cache_path.glob("*.cache"))
        if len(l2_files) > self.config.l2_max_size:
            # Sort by modification time, delete oldest files
            l2_files.sort(key=lambda f: f.stat().st_mtime)
            for file in l2_files[: len(l2_files) - self.config.l2_max_size]:
                file.unlink()
                self.stats["l2_evictions"] += 1

    def _evict_lfu_from_l2(self) -> None:
        """Evict least frequently used item from L2 cache"""
        # This implementation is complex, requires maintaining L2 access counts
        self._evict_lru_from_l2()  # Simplified implementation using LRU

    def _get_from_l2(self, key: str) -> Optional[CacheEntry]:
        """Get from L2 cache"""
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
            self.logger.warning(f"Failed to read from L2 cache: {e}")
            if cache_file.exists():
                cache_file.unlink()
            return None

    def _save_to_l2(self, entry: CacheEntry) -> None:
        """Save to L2 cache"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(entry.key.encode()).hexdigest()}.cache"
        )

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(entry.__dict__, f)
        except Exception as e:
            self.logger.error(f"Failed to save to L2 cache: {e}")

    def _exists_in_l2(self, key: str) -> bool:
        """Check if exists in L2 cache"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        )
        return cache_file.exists()

    def _remove_from_l2(self, key: str) -> None:
        """Remove from L2 cache"""
        cache_file = (
            self.l2_cache_path / f"{hashlib.md5(key.encode()).hexdigest()}.cache"
        )
        if cache_file.exists():
            cache_file.unlink()

    def _remove_from_l1(self, key: str) -> None:
        """Remove from L1 cache"""
        if key in self.l1_cache:
            del self.l1_cache[key]

    def _clear_l2_cache(self) -> None:
        """Clear L2 cache"""
        for cache_file in self.l2_cache_path.glob("*.cache"):
            cache_file.unlink()

    def _cleanup_expired_entries(self) -> None:
        """Clean up expired entries"""
        # Clean up L1 cache
        expired_keys = []
        for key, entry in self.l1_cache.items():
            if self._is_entry_expired(entry):
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_from_l1(key)

        # Clean up L2 cache
        for cache_file in self.l2_cache_path.glob("*.cache"):
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                entry = CacheEntry(**data)
                if self._is_entry_expired(entry):
                    cache_file.unlink()
            except Exception:
                cache_file.unlink()

    def _optimize_cache_size(self) -> None:
        """Optimize cache size"""
        # Adjust cache size based on hit rate
        l1_hit_rate = self.stats["l1_hits"] / max(self.stats["total_requests"], 1)

        if l1_hit_rate < 0.5:  # Low L1 hit rate, consider increasing L1 size
            # Dynamic config adjustment can be done here, but needs caution
            pass

    def _preload_hot_data(self) -> None:
        """Preload hot data"""
        # Preload data based on access patterns
        hot_keys = []
        for key, accesses in self.adaptive_ttl.access_patterns.items():
            frequency = self.adaptive_ttl.get_access_frequency(key)
            if frequency > 0.1:  # Data accessed more than 0.1 times per hour
                hot_keys.append((key, frequency))

        # Sort by frequency, preload hottest data
        hot_keys.sort(key=lambda x: x[1], reverse=True)
        for key, frequency in hot_keys[:10]:  # Preload top 10 hottest data
            if key not in self.l1_cache:
                # Actual data preload logic needs to be implemented here
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
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
        """Get detailed status information"""
        stats = self.get_stats()

        # Get hot data
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
            "hot_data": hot_keys[:20],  # Top 20 hottest data
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

    def cleanup(self) -> None:
        """Clean up resources"""
        self.running = False
        self.clear()


# Decorator pattern
def cached(
    cache: IntelligentCache,
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None,
):
    """
    Cache decorator

    Args:
        cache: Cache instance
        ttl: Time to live
        key_func: Custom key generation function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# Global cache instance
_global_cache: Optional[IntelligentCache] = None
_cache_lock = threading.Lock()


def get_global_cache() -> IntelligentCache:
    """Get global cache instance"""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = IntelligentCache()
    return _global_cache


# Convenience functions
def get_cached(key: str, default: Any = None) -> Any:
    """Convenience function: get cached value"""
    return get_global_cache().get(key, default)


def set_cached(key: str, value: Any, ttl: Optional[float] = None) -> bool:
    """Convenience function: set cached value"""
    return get_global_cache().set(key, value, ttl)


def delete_cached(key: str) -> bool:
    """Convenience function: delete cached value"""
    return get_global_cache().delete(key)
