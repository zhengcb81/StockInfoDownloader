#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CacheManager 模块测试
提升 src/utils/cache_manager.py 模块的测试覆盖率
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.utils.cache_manager import (
    CacheManager,
    get_cache_manager,
    cached_file_exists,
    cached_stock_info,
    clear_all_cache,
    get_cache_stats,
)


class TestCacheManager:
    """测试 CacheManager 类"""

    def setup_method(self):
        """设置测试环境"""
        self.cache_manager = CacheManager(max_cache_size=10, cache_ttl=1)

    def test_init_default(self):
        """测试默认初始化"""
        cm = CacheManager()
        assert cm.max_cache_size == 1000
        assert cm.cache_ttl == 300
        assert isinstance(cm._file_exists_cache, dict)
        assert isinstance(cm._stock_info_cache, dict)
        assert isinstance(cm._page_content_cache, dict)
        assert isinstance(cm._config_cache, dict)

    def test_init_custom(self):
        """测试自定义参数初始化"""
        cm = CacheManager(max_cache_size=5, cache_ttl=10)
        assert cm.max_cache_size == 5
        assert cm.cache_ttl == 10

    def test_cached_file_exists_file_not_found(self):
        """测试文件不存在的情况"""
        result = self.cache_manager.cached_file_exists("/nonexistent/file.txt")
        assert result is False

    def test_cached_file_exists_with_temp_file(self):
        """测试临时文件存在性检查"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content that is long enough")
            temp_path = f.name

        try:
            result = self.cache_manager.cached_file_exists(temp_path, min_size=10)
            assert result is True

            # 第二次调用应该使用缓存
            result2 = self.cache_manager.cached_file_exists(temp_path, min_size=10)
            assert result2 is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_file_exists_too_small(self):
        """测试文件太小的情况"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x")  # 太小
            temp_path = f.name

        try:
            result = self.cache_manager.cached_file_exists(temp_path, min_size=100)
            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_file_exists_cache_hit(self):
        """测试缓存命中"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)  # 足够大
            temp_path = f.name

        try:
            # 第一次调用 - 缓存未命中
            result1 = self.cache_manager.cached_file_exists(temp_path, min_size=100)
            assert result1 is True

            # 第二次调用 - 缓存命中
            result2 = self.cache_manager.cached_file_exists(temp_path, min_size=100)
            assert result2 is True

            # 验证缓存中有数据
            assert len(self.cache_manager._file_exists_cache) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_file_exists_cache_expiry(self):
        """测试缓存过期"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            cm = CacheManager(max_cache_size=10, cache_ttl=1)

            # 第一次调用 - 使用真实 time.time()
            result1 = cm.cached_file_exists(temp_path, min_size=100)
            assert result1 is True

            # 确认缓存有数据
            assert len(cm._file_exists_cache) > 0

            # 直接修改缓存时间戳模拟过期
            for key in cm._file_exists_cache:
                cm._file_exists_cache[key]["timestamp"] = time.time() - 10  # 10秒前

            # 缓存应该已过期，重新检查文件
            result2 = cm.cached_file_exists(temp_path, min_size=100)
            assert result2 is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_file_exists_custom_ttl(self):
        """测试自定义 TTL"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            # 使用较短的 TTL
            result = self.cache_manager.cached_file_exists(
                temp_path, min_size=100, custom_ttl=0
            )
            assert result is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_stock_info_cache_hit(self):
        """测试股票信息缓存命中"""
        stock_code = "000001"
        mock_info = {"name": "Test Stock", "price": 100.0}

        def mock_fetcher(code):
            return mock_info

        # 第一次调用 - 缓存未命中
        result1 = self.cache_manager.cached_stock_info(stock_code, mock_fetcher)
        assert result1 == mock_info

        # 第二次调用 - 缓存命中
        result2 = self.cache_manager.cached_stock_info(stock_code, mock_fetcher)
        assert result2 == mock_info

        # 验证缓存中有数据
        assert len(self.cache_manager._stock_info_cache) > 0

    def test_cached_stock_info_none_result(self):
        """测试股票信息获取返回 None"""
        stock_code = "000002"

        def mock_fetcher(code):
            return None

        result = self.cache_manager.cached_stock_info(stock_code, mock_fetcher)
        assert result is None

        # None 结果不应该被缓存
        assert stock_code not in self.cache_manager._stock_info_cache

    def test_cached_stock_info_exception_handling(self):
        """测试股票信息获取异常处理"""
        stock_code = "000003"

        def mock_fetcher(code):
            raise ValueError("Network error")

        result = self.cache_manager.cached_stock_info(stock_code, mock_fetcher)
        assert result is None

    def test_cached_stock_info_cache_expiry(self):
        """测试股票信息缓存过期"""
        stock_code = "000004"
        mock_info = {"name": "Test Stock"}

        def mock_fetcher(code):
            return mock_info.copy()

        cm = CacheManager(max_cache_size=10, cache_ttl=1)

        # 第一次调用
        result1 = cm.cached_stock_info(stock_code, mock_fetcher)
        assert result1 == mock_info

        # 直接修改缓存时间戳模拟过期
        for key in cm._stock_info_cache:
            cm._stock_info_cache[key]["timestamp"] = time.time() - 10

        # 缓存应该已过期，重新获取
        result2 = cm.cached_stock_info(stock_code, mock_fetcher)
        assert result2 == mock_info

    def test_cached_page_content_cache_hit(self):
        """测试页面内容缓存命中"""
        url = "https://example.com"
        mock_content = "<html>Test Page</html>"

        def mock_fetcher(u):
            return mock_content

        # 第一次调用 - 缓存未命中
        result1 = self.cache_manager.cached_page_content(url, mock_fetcher)
        assert result1 == mock_content

        # 第二次调用 - 缓存命中
        result2 = self.cache_manager.cached_page_content(url, mock_fetcher)
        assert result2 == mock_content

        # 验证缓存中有数据
        assert len(self.cache_manager._page_content_cache) > 0

    def test_cached_page_content_none_result(self):
        """测试页面内容获取返回 None"""
        url = "https://example.com/empty"

        def mock_fetcher(u):
            return None

        result = self.cache_manager.cached_page_content(url, mock_fetcher)
        assert result is None

        # None 结果不应该被缓存
        assert url not in self.cache_manager._page_content_cache

    def test_cached_page_content_exception_handling(self):
        """测试页面内容获取异常处理"""
        url = "https://example.com/error"

        def mock_fetcher(u):
            raise ConnectionError("Connection failed")

        result = self.cache_manager.cached_page_content(url, mock_fetcher)
        assert result is None

    def test_cached_page_content_cache_expiry(self):
        """测试页面内容缓存过期"""
        url = "https://example.com/expiry"
        mock_content = "<html>Content</html>"

        def mock_fetcher(u):
            return mock_content

        cm = CacheManager(max_cache_size=10, cache_ttl=1)

        # 第一次调用
        result1 = cm.cached_page_content(url, mock_fetcher)
        assert result1 == mock_content

        # 直接修改缓存时间戳模拟过期
        for key in cm._page_content_cache:
            cm._page_content_cache[key]["timestamp"] = time.time() - 10

        # 缓存应该已过期，重新获取
        result2 = cm.cached_page_content(url, mock_fetcher)
        assert result2 == mock_content

    def test_config_value_operations(self):
        """测试配置值的读写操作"""
        # 设置配置值
        self.cache_manager.set_config_value("key1", "value1")
        self.cache_manager.set_config_value("key2", 123)

        # 获取配置值
        assert self.cache_manager.get_config_value("key1") == "value1"
        assert self.cache_manager.get_config_value("key2") == 123

        # 获取不存在的配置值
        assert self.cache_manager.get_config_value("key3") is None
        assert self.cache_manager.get_config_value("key3", "default") == "default"

    def test_clear_cache_all(self):
        """测试清理所有缓存"""
        # 添加一些缓存数据
        self.cache_manager.set_config_value("key", "value")
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            self.cache_manager.cached_file_exists(temp_path, min_size=100)
            assert len(self.cache_manager._file_exists_cache) > 0

            # 清理所有缓存
            self.cache_manager.clear_cache()

            assert len(self.cache_manager._file_exists_cache) == 0
            assert len(self.cache_manager._stock_info_cache) == 0
            assert len(self.cache_manager._page_content_cache) == 0
            assert len(self.cache_manager._config_cache) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_clear_cache_by_type(self):
        """测试按类型清理缓存"""
        # 添加数据到各种缓存
        self.cache_manager.set_config_value("key", "value")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            self.cache_manager.cached_file_exists(temp_path, min_size=100)
            assert len(self.cache_manager._file_exists_cache) > 0

            # 只清理配置缓存
            self.cache_manager.clear_cache("config")
            assert len(self.cache_manager._config_cache) == 0
            assert len(self.cache_manager._file_exists_cache) > 0

            # 只清理文件存在性缓存
            self.cache_manager.clear_cache("file_exists")
            assert len(self.cache_manager._file_exists_cache) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_clear_cache_stock_info(self):
        """测试清理股票信息缓存"""
        stock_code = "000001"

        def mock_fetcher(code):
            return {"name": "Test"}

        self.cache_manager.cached_stock_info(stock_code, mock_fetcher)
        assert len(self.cache_manager._stock_info_cache) > 0

        self.cache_manager.clear_cache("stock_info")
        assert len(self.cache_manager._stock_info_cache) == 0

    def test_clear_cache_page_content(self):
        """测试清理页面内容缓存"""
        url = "https://example.com"

        def mock_fetcher(u):
            return "content"

        self.cache_manager.cached_page_content(url, mock_fetcher)
        assert len(self.cache_manager._page_content_cache) > 0

        self.cache_manager.clear_cache("page_content")
        assert len(self.cache_manager._page_content_cache) == 0

    def test_get_cache_stats(self):
        """测试获取缓存统计"""
        stats = self.cache_manager.get_cache_stats()
        assert isinstance(stats, dict)
        assert "file_exists_cache_size" in stats
        assert "stock_info_cache_size" in stats
        assert "page_content_cache_size" in stats
        assert "config_cache_size" in stats
        assert "max_cache_size" in stats
        assert "cache_ttl" in stats
        assert stats["max_cache_size"] == 10
        assert stats["cache_ttl"] == 1

    def test_evict_cache_if_needed(self):
        """测试缓存驱逐机制"""
        cm = CacheManager(max_cache_size=3, cache_ttl=300)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            # 添加4个文件，超过最大缓存大小3
            for i in range(4):
                cm.cached_file_exists(f"{temp_path}_{i}", min_size=100)

            # 缓存大小应该不超过最大值
            assert len(cm._file_exists_cache) <= 3
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_optimize_cache(self):
        """测试缓存优化"""
        cm = CacheManager(max_cache_size=10, cache_ttl=0)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            # 添加缓存条目
            cm.cached_file_exists(temp_path, min_size=100)

            # TTL=0 means cache is immediately expired
            # 优化缓存应该清理过期条目
            cm.optimize_cache()

            # Cache should be empty after optimization with TTL=0
            assert len(cm._file_exists_cache) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestGlobalFunctions:
    """测试全局便捷函数"""

    def test_get_cache_manager_singleton(self):
        """测试全局缓存管理器单例"""
        cm1 = get_cache_manager()
        cm2 = get_cache_manager()
        assert cm1 is cm2

    def test_cached_file_exists_convenience(self):
        """测试便捷函数 - 文件存在性检查"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            result = cached_file_exists(temp_path, min_size=100)
            assert result is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_cached_stock_info_convenience(self):
        """测试便捷函数 - 股票信息"""
        stock_code = "000001"

        def mock_fetcher(code):
            return {"name": "Test"}

        result = cached_stock_info(stock_code, mock_fetcher)
        assert result == {"name": "Test"}

    def test_clear_all_cache_convenience(self):
        """测试便捷函数 - 清理所有缓存"""
        # 添加一些缓存
        cm = get_cache_manager()
        cm.set_config_value("test", "value")

        clear_all_cache()

        assert cm.get_config_value("test") is None

    def test_get_cache_stats_convenience(self):
        """测试便捷函数 - 获取缓存统计"""
        stats = get_cache_stats()
        assert isinstance(stats, dict)
        assert "max_cache_size" in stats


class TestThreadSafety:
    """测试线程安全性"""

    def test_concurrent_file_exists_checks(self):
        """测试并发文件存在性检查"""
        cm = CacheManager(max_cache_size=100, cache_ttl=300)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("x" * 2000)
            temp_path = f.name

        try:
            results = []
            threads = []

            def check_file():
                result = cm.cached_file_exists(temp_path, min_size=100)
                results.append(result)

            # 创建多个线程
            for _ in range(10):
                t = threading.Thread(target=check_file)
                threads.append(t)
                t.start()

            # 等待所有线程完成
            for t in threads:
                t.join()

            # 所有结果应该相同
            assert all(results)
            assert len(results) == 10

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_concurrent_config_operations(self):
        """测试并发配置操作"""
        cm = CacheManager()

        results = []
        threads = []

        def set_config(i):
            cm.set_config_value(f"key{i}", f"value{i}")
            results.append(cm.get_config_value(f"key{i}"))

        # 创建多个线程
        for i in range(10):
            t = threading.Thread(target=set_config, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证所有操作都成功
        assert len(results) == 10

    def test_concurrent_cache_clear(self):
        """测试并发缓存清理"""
        cm = CacheManager()

        # 添加数据
        for i in range(10):
            cm.set_config_value(f"key{i}", f"value{i}")

        threads = []

        def clear_cache():
            cm.clear_cache()

        # 创建多个清理线程
        for _ in range(5):
            t = threading.Thread(target=clear_cache)
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 缓存应该被清理
        assert len(cm._config_cache) == 0
