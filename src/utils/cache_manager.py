"""
缓存管理器模块
提供智能缓存功能，减少重复的文件系统操作和网络请求
"""

import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.core.logger import get_logger


class CacheManager:
    """智能缓存管理器"""

    def __init__(self, max_cache_size: int = 1000, cache_ttl: int = 300):
        """
        初始化缓存管理器

        Args:
            max_cache_size: 最大缓存条目数
            cache_ttl: 缓存生存时间（秒）
        """
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl
        self.logger = get_logger(__name__)

        # 文件存在性缓存
        self._file_exists_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._file_exists_lock = threading.RLock()

        # 股票信息缓存
        self._stock_info_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._stock_info_lock = threading.RLock()

        # 页面内容缓存
        self._page_content_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._page_content_lock = threading.RLock()

        # 配置缓存
        self._config_cache: Dict[str, Any] = {}
        self._config_lock = threading.RLock()

        self.logger.info(
            f"缓存管理器初始化完成，最大缓存: {max_cache_size}, TTL: {cache_ttl}s"
        )

    def _cleanup_expired_cache(self, cache_dict: OrderedDict, lock: threading.RLock):
        """清理过期的缓存条目"""
        current_time = time.time()
        keys_to_remove = []

        with lock:
            for key, cache_data in cache_dict.items():
                if current_time - cache_data["timestamp"] > cache_data["ttl"]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del cache_dict[key]
                self.logger.debug(f"清理过期缓存: {key}")

    def _evict_cache_if_needed(self, cache_dict: OrderedDict, lock: threading.RLock):
        """如果缓存超过大小限制，移除最旧的条目"""
        with lock:
            while len(cache_dict) > self.max_cache_size:
                oldest_key = next(iter(cache_dict))
                del cache_dict[oldest_key]
                self.logger.debug(f"移除最旧缓存条目: {oldest_key}")

    def cached_file_exists(
        self,
        file_path: Union[str, Path],
        min_size: int = 1024,
        custom_ttl: Optional[int] = None,
    ) -> bool:
        """
        缓存的文件存在性检查

        Args:
            file_path: 文件路径
            min_size: 最小文件大小（字节）
            custom_ttl: 自定义TTL

        Returns:
            bool: 文件是否存在且大小足够
        """
        file_path = str(file_path)
        ttl = custom_ttl or self.cache_ttl

        # 生成缓存键（包含文件修改时间）
        try:
            mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            cache_key = f"{file_path}:{mtime}"
        except OSError:
            cache_key = f"{file_path}:0"

        # 检查缓存
        with self._file_exists_lock:
            if cache_key in self._file_exists_cache:
                cache_data = self._file_exists_cache[cache_key]
                if time.time() - cache_data["timestamp"] < ttl:
                    self.logger.debug(f"缓存命中: {file_path}")
                    return cache_data["exists"]
                else:
                    # 缓存过期，移除
                    del self._file_exists_cache[cache_key]

        # 执行实际的文件检查
        exists = os.path.exists(file_path)
        size_ok = False
        if exists:
            try:
                size = os.path.getsize(file_path)
                size_ok = size >= min_size
                self.logger.debug(f"文件检查: {file_path}, 大小: {size} bytes")
            except OSError:
                size_ok = False

        result = exists and size_ok

        # 更新缓存
        with self._file_exists_lock:
            self._file_exists_cache[cache_key] = {
                "exists": result,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            # 清理过期缓存
            self._cleanup_expired_cache(self._file_exists_cache, self._file_exists_lock)

            # 如果缓存过大，移除最旧的条目
            self._evict_cache_if_needed(self._file_exists_cache, self._file_exists_lock)

        self.logger.debug(f"文件检查结果: {file_path} -> {result}")
        return result

    def cached_stock_info(
        self, stock_code: str, info_fetcher_func, custom_ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        缓存的股票信息获取

        Args:
            stock_code: 股票代码
            info_fetcher_func: 获取股票信息的函数
            custom_ttl: 自定义TTL

        Returns:
            Dict[str, Any]: 股票信息或None
        """
        ttl = custom_ttl or self.cache_ttl

        # 检查缓存
        with self._stock_info_lock:
            if stock_code in self._stock_info_cache:
                cache_data = self._stock_info_cache[stock_code]
                if time.time() - cache_data["timestamp"] < ttl:
                    self.logger.debug(f"股票信息缓存命中: {stock_code}")
                    return cache_data["info"]
                else:
                    # 缓存过期，移除
                    del self._stock_info_cache[stock_code]

        # 执行实际的信息获取
        try:
            stock_info = info_fetcher_func(stock_code)
            if stock_info:
                self.logger.debug(f"获取股票信息: {stock_code}")

                # 更新缓存
                with self._stock_info_lock:
                    self._stock_info_cache[stock_code] = {
                        "info": stock_info,
                        "timestamp": time.time(),
                        "ttl": ttl,
                    }

                    # 清理过期缓存
                    self._cleanup_expired_cache(
                        self._stock_info_cache, self._stock_info_lock
                    )

                    # 如果缓存过大，移除最旧的条目
                    self._evict_cache_if_needed(
                        self._stock_info_cache, self._stock_info_lock
                    )
            else:
                self.logger.warning(f"无法获取股票信息: {stock_code}")

            return stock_info

        except Exception as e:
            self.logger.error(f"获取股票信息失败 {stock_code}: {e}")
            return None

    def cached_page_content(
        self, url: str, content_fetcher_func, custom_ttl: Optional[int] = None
    ) -> Optional[str]:
        """
        缓存的页面内容获取

        Args:
            url: 页面URL
            content_fetcher_func: 获取页面内容的函数
            custom_ttl: 自定义TTL

        Returns:
            str: 页面内容或None
        """
        ttl = custom_ttl or self.cache_ttl

        # 检查缓存
        with self._page_content_lock:
            if url in self._page_content_cache:
                cache_data = self._page_content_cache[url]
                if time.time() - cache_data["timestamp"] < ttl:
                    self.logger.debug(f"页面内容缓存命中: {url}")
                    return cache_data["content"]
                else:
                    # 缓存过期，移除
                    del self._page_content_cache[url]

        # 执行实际的内容获取
        try:
            content = content_fetcher_func(url)
            if content:
                self.logger.debug(f"获取页面内容: {url[:50]}...")

                # 更新缓存
                with self._page_content_lock:
                    self._page_content_cache[url] = {
                        "content": content,
                        "timestamp": time.time(),
                        "ttl": ttl,
                    }

                    # 清理过期缓存
                    self._cleanup_expired_cache(
                        self._page_content_cache, self._page_content_lock
                    )

                    # 如果缓存过大，移除最旧的条目
                    self._evict_cache_if_needed(
                        self._page_content_cache, self._page_content_lock
                    )
            else:
                self.logger.warning(f"无法获取页面内容: {url}")

            return content

        except Exception as e:
            self.logger.error(f"获取页面内容失败 {url}: {e}")
            return None

    def get_config_value(self, key: str, default_value: Any = None) -> Any:
        """
        获取缓存的配置值

        Args:
            key: 配置键
            default_value: 默认值

        Returns:
            Any: 配置值
        """
        with self._config_lock:
            return self._config_cache.get(key, default_value)

    def set_config_value(self, key: str, value: Any):
        """
        设置缓存的配置值

        Args:
            key: 配置键
            value: 配置值
        """
        with self._config_lock:
            self._config_cache[key] = value

    def clear_cache(self, cache_type: Optional[str] = None):
        """
        清理缓存

        Args:
            cache_type: 缓存类型 ('file_exists', 'stock_info', 'page_content', 'config', None)
                        None表示清理所有缓存
        """
        if cache_type is None or cache_type == "all":
            with self._file_exists_lock:
                self._file_exists_cache.clear()
            with self._stock_info_lock:
                self._stock_info_cache.clear()
            with self._page_content_lock:
                self._page_content_cache.clear()
            with self._config_lock:
                self._config_cache.clear()
            self.logger.info("清理所有缓存")
        elif cache_type == "file_exists":
            with self._file_exists_lock:
                self._file_exists_cache.clear()
            self.logger.info("清理文件存在性缓存")
        elif cache_type == "stock_info":
            with self._stock_info_lock:
                self._stock_info_cache.clear()
            self.logger.info("清理股票信息缓存")
        elif cache_type == "page_content":
            with self._page_content_lock:
                self._page_content_cache.clear()
            self.logger.info("清理页面内容缓存")
        elif cache_type == "config":
            with self._config_lock:
                self._config_cache.clear()
            self.logger.info("清理配置缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计
        """
        with self._file_exists_lock:
            file_exists_count = len(self._file_exists_cache)
        with self._stock_info_lock:
            stock_info_count = len(self._stock_info_cache)
        with self._page_content_lock:
            page_content_count = len(self._page_content_cache)
        with self._config_lock:
            config_count = len(self._config_cache)

        return {
            "file_exists_cache_size": file_exists_count,
            "stock_info_cache_size": stock_info_count,
            "page_content_cache_size": page_content_count,
            "config_cache_size": config_count,
            "max_cache_size": self.max_cache_size,
            "cache_ttl": self.cache_ttl,
        }

    def optimize_cache(self):
        """优化缓存，清理过期条目"""
        self.logger.info("开始缓存优化")

        # 清理各种缓存
        self._cleanup_expired_cache(self._file_exists_cache, self._file_exists_lock)
        self._cleanup_expired_cache(self._stock_info_cache, self._stock_info_lock)
        self._cleanup_expired_cache(self._page_content_cache, self._page_content_lock)

        # 确保不超过大小限制
        self._evict_cache_if_needed(self._file_exists_cache, self._file_exists_lock)
        self._evict_cache_if_needed(self._stock_info_cache, self._stock_info_lock)
        self._evict_cache_if_needed(self._page_content_cache, self._page_content_lock)

        stats = self.get_cache_stats()
        self.logger.info(f"缓存优化完成: {stats}")


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                _cache_manager = CacheManager()
    return _cache_manager


def cached_file_exists(file_path: Union[str, Path], min_size: int = 1024) -> bool:
    """便捷函数：缓存的文件存在性检查"""
    return get_cache_manager().cached_file_exists(file_path, min_size)


def cached_stock_info(stock_code: str, info_fetcher_func) -> Optional[Dict[str, Any]]:
    """便捷函数：缓存的股票信息获取"""
    return get_cache_manager().cached_stock_info(stock_code, info_fetcher_func)


def clear_all_cache():
    """便捷函数：清理所有缓存"""
    get_cache_manager().clear_cache()


def get_cache_stats() -> Dict[str, Any]:
    """便捷函数：获取缓存统计"""
    return get_cache_manager().get_cache_stats()
