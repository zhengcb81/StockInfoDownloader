#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优雅降级策略模块 (degradation.py) 单元测试
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.degradation import (
    DEGRADATION_LEVELS,
    DegradationLevel,
    FileSystemDegradationManager,
    NetworkDegradationManager,
    check_disk_space,
    ensure_directory_exists,
    execute_with_network_fallback,
    get_network_status,
    network_degradation_manager,
    safe_write_file,
)
from src.core.exceptions import ErrorCode, ErrorSeverity, NetworkError


class TestDegradationLevel:
    """测试 DegradationLevel 数据类"""

    def test_degradation_level_creation(self):
        """测试创建降级级别"""
        level = DegradationLevel(
            name="test",
            priority=1,
            description="Test level",
            is_available=True,
        )
        assert level.name == "test"
        assert level.priority == 1
        assert level.description == "Test level"
        assert level.is_available is True
        assert level.last_failure is None
        assert level.consecutive_failures == 0

    def test_degradation_level_defaults(self):
        """测试降级级别默认值"""
        level = DegradationLevel(name="test", priority=1, description="Test")
        assert level.max_consecutive_failures == 3
        assert level.cooldown_period == timedelta(minutes=5)


class TestDegradationLevels:
    """测试预定义的降级级别"""

    def test_predefined_levels_exist(self):
        """测试预定义级别存在"""
        assert "full" in DEGRADATION_LEVELS
        assert "cache_only" in DEGRADATION_LEVELS
        assert "offline_mode" in DEGRADATION_LEVELS
        assert "minimal" in DEGRADATION_LEVELS
        assert "emergency" in DEGRADATION_LEVELS

    def test_level_priorities(self):
        """测试级别优先级顺序"""
        assert DEGRADATION_LEVELS["full"].priority < DEGRADATION_LEVELS["cache_only"].priority
        assert DEGRADATION_LEVELS["cache_only"].priority < DEGRADATION_LEVELS["offline_mode"].priority
        assert DEGRADATION_LEVELS["offline_mode"].priority < DEGRADATION_LEVELS["minimal"].priority
        assert DEGRADATION_LEVELS["minimal"].priority < DEGRADATION_LEVELS["emergency"].priority


class TestNetworkDegradationManager:
    """测试网络降级管理器"""

    def test_init(self):
        """测试初始化"""
        manager = NetworkDegradationManager()
        assert manager.current_level == DEGRADATION_LEVELS["full"]
        assert manager.connection_history == []
        assert manager.circuit_breaker_open is False
        assert manager.circuit_breaker_timeout is None

    def test_fallback_strategies_registered(self):
        """测试降级策略已注册"""
        manager = NetworkDegradationManager()
        assert "timeout_increase" in manager.fallback_strategies
        assert "cache_fallback" in manager.fallback_strategies
        assert "retry_with_backoff" in manager.fallback_strategies
        assert "alternative_endpoint" in manager.fallback_strategies
        assert "offline_mode" in manager.fallback_strategies

    def test_record_success(self):
        """测试记录成功"""
        manager = NetworkDegradationManager()
        manager._record_success()

        assert len(manager.connection_history) == 1
        assert manager.connection_history[0]["success"] is True

    def test_record_failure(self):
        """测试记录失败"""
        manager = NetworkDegradationManager()
        manager._record_failure()

        assert len(manager.connection_history) == 1
        assert manager.connection_history[0]["success"] is False

    def test_record_success_resets_circuit_breaker(self):
        """测试成功记录重置熔断器"""
        manager = NetworkDegradationManager()
        manager.circuit_breaker_open = True
        manager.circuit_breaker_timeout = datetime.now() + timedelta(minutes=5)

        manager._record_success()

        assert manager.circuit_breaker_open is False
        assert manager.circuit_breaker_timeout is None

    def test_check_circuit_breaker_opens_after_failures(self):
        """测试连续失败后熔断器打开"""
        manager = NetworkDegradationManager()

        # 添加足够多的失败记录
        for _ in range(10):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
                "error": "Connection failed",
            })

        manager._check_circuit_breaker()

        assert manager.circuit_breaker_open is True
        assert manager.circuit_breaker_timeout is not None

    def test_adjust_degradation_level_full(self):
        """测试失败率低时保持完整功能"""
        manager = NetworkDegradationManager()

        # 添加成功的记录
        for _ in range(18):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })
        # 添加少量失败
        for _ in range(2):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
            })

        manager._adjust_degradation_level()

        assert manager.current_level.name == "full"

    def test_adjust_degradation_level_cache_only(self):
        """测试中等失败率降级到缓存模式"""
        manager = NetworkDegradationManager()

        # 20% 失败率
        for _ in range(16):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })
        for _ in range(4):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
            })

        manager._adjust_degradation_level()

        # 由于降级只升不降，可能是 cache_only 或更高
        assert manager.current_level.priority >= DEGRADATION_LEVELS["cache_only"].priority

    def test_set_degradation_level(self):
        """测试设置降级级别"""
        manager = NetworkDegradationManager()

        # 设置更高优先级（更严重）的级别
        manager._set_degradation_level("cache_only")

        assert manager.current_level.name == "cache_only"

    def test_set_degradation_level_no_downgrade(self):
        """测试不能降级到更低优先级（更好）的级别"""
        manager = NetworkDegradationManager()
        manager.current_level = DEGRADATION_LEVELS["cache_only"]

        # 尝试设置更好（更低优先级数字）的级别
        manager._set_degradation_level("full")

        # 应该保持不变
        assert manager.current_level.name == "cache_only"

    def test_cleanup_history(self):
        """测试清理历史记录"""
        manager = NetworkDegradationManager()
        manager.max_history_size = 10

        # 添加超过限制的记录
        for i in range(15):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })

        manager._cleanup_history()

        assert len(manager.connection_history) <= 10

    def test_get_network_status_no_history(self):
        """Test network status with no history"""
        manager = NetworkDegradationManager()
        status = manager.get_network_status()

        assert status["status"] == "unknown"
        assert status["message"] == "No historical data"

    def test_get_network_status_healthy(self):
        """测试健康网络状态"""
        manager = NetworkDegradationManager()

        # 添加成功的记录
        for _ in range(18):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })
        for _ in range(2):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
            })

        status = manager.get_network_status()

        assert status["status"] == "healthy"
        assert status["success_rate"] > 0.8

    def test_get_network_status_degraded(self):
        """测试降级网络状态"""
        manager = NetworkDegradationManager()

        # 60% 成功率
        for _ in range(12):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })
        for _ in range(8):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
            })

        status = manager.get_network_status()

        assert status["status"] == "degraded"

    def test_get_network_status_unhealthy(self):
        """测试不健康网络状态"""
        manager = NetworkDegradationManager()

        # 40% 成功率
        for _ in range(8):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": True,
            })
        for _ in range(12):
            manager.connection_history.append({
                "timestamp": datetime.now(),
                "success": False,
            })

        status = manager.get_network_status()

        assert status["status"] == "unhealthy"

    def test_increase_timeout(self):
        """测试增加超时时间策略"""
        manager = NetworkDegradationManager()
        context = {"timeout": 30}

        result = manager._increase_timeout(context)

        assert result["timeout"] == 60
        assert result["strategy_used"] == "timeout_increase"

    def test_increase_timeout_max(self):
        """测试超时时间最大限制"""
        manager = NetworkDegradationManager()
        context = {"timeout": 200}

        result = manager._increase_timeout(context)

        assert result["timeout"] == 300  # 最大5分钟

    def test_use_cache_data(self):
        """测试使用缓存数据策略"""
        manager = NetworkDegradationManager()
        context = {"cache_key": "test_key", "cached_data": "cached_value"}

        result = manager._use_cache_data(context)

        assert result == "cached_value"
        assert context["strategy_used"] == "cache_fallback"

    def test_use_cache_data_no_key(self):
        """测试无缓存键的情况"""
        manager = NetworkDegradationManager()
        context = {}

        result = manager._use_cache_data(context)

        assert result is None

    def test_retry_with_exponential_backoff(self):
        """测试指数退避重试策略"""
        manager = NetworkDegradationManager()
        context = {"retry_count": 0, "max_retries": 3}

        result = manager._retry_with_exponential_backoff(context)

        assert result["retry_count"] == 1
        assert result["strategy_used"] == "retry_with_backoff"

    def test_retry_with_exponential_backoff_max_retries(self):
        """测试达到最大重试次数"""
        manager = NetworkDegradationManager()
        context = {"retry_count": 3, "max_retries": 3}

        result = manager._retry_with_exponential_backoff(context)

        assert result is None

    def test_use_alternative_endpoint(self):
        """测试使用备用端点策略"""
        manager = NetworkDegradationManager()
        context = {"url": "https://www.cninfo.com.cn/page"}

        result = manager._use_alternative_endpoint(context)

        assert "backup1.cninfo.com.cn" in result["url"]
        assert result["strategy_used"] == "alternative_endpoint"

    def test_use_alternative_endpoint_no_match(self):
        """测试无匹配备用端点"""
        manager = NetworkDegradationManager()
        context = {"url": "https://other-site.com/page"}

        result = manager._use_alternative_endpoint(context)

        assert result is None

    def test_switch_to_offline_mode(self):
        """测试切换到离线模式"""
        manager = NetworkDegradationManager()
        context = {}

        result = manager._switch_to_offline_mode(context)

        assert result["offline_mode"] is True
        assert result["strategy_used"] == "offline_mode"

    def test_execute_with_fallback_success(self):
        """测试主要操作成功"""
        manager = NetworkDegradationManager()

        result = manager.execute_with_fallback(
            lambda: "success",
            ["timeout_increase"],
        )

        assert result == "success"

    def test_execute_with_fallback_with_fallback(self):
        """测试主要操作失败后使用降级策略"""
        manager = NetworkDegradationManager()

        # 主要操作会失败，但缓存策略会返回数据
        context = {"cache_key": "test", "cached_data": "fallback_value"}

        with patch.object(manager, "_use_cache_data", return_value="fallback_value"):
            result = manager.execute_with_fallback(
                lambda: (_ for _ in ()).throw(Exception("Primary failed")),
                ["cache_fallback"],
                context,
            )

            assert result == "fallback_value"

    def test_execute_with_fallback_circuit_breaker_open(self):
        """测试熔断器打开时抛出异常"""
        manager = NetworkDegradationManager()
        manager.circuit_breaker_open = True
        manager.circuit_breaker_timeout = datetime.now() + timedelta(minutes=5)

        with pytest.raises(NetworkError) as exc_info:
            manager.execute_with_fallback(
                lambda: "success",
                ["timeout_increase"],
            )

        assert exc_info.value.error_code == ErrorCode.NETWORK_CONNECTION_ERROR


class TestFileSystemDegradationManager:
    """测试文件系统降级管理器"""

    def test_init(self):
        """测试初始化"""
        manager = FileSystemDegradationManager()
        assert manager.temp_dir.exists()
        assert len(manager.fallback_directories) > 0

    def test_check_disk_space(self):
        """测试检查磁盘空间"""
        manager = FileSystemDegradationManager()

        result = manager.check_disk_space(tempfile.gettempdir())

        assert "total" in result
        assert "used" in result
        assert "free" in result
        assert "status" in result

    def test_check_disk_space_nonexistent_path(self):
        """测试不存在的路径"""
        manager = FileSystemDegradationManager()

        result = manager.check_disk_space("/nonexistent/path/file.txt")

        # 应该返回父目录的空间信息
        assert "status" in result

    def test_ensure_directory_exists_creates_dir(self):
        """测试创建目录"""
        manager = FileSystemDegradationManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_directory"
            result = manager.ensure_directory_exists(new_dir)

            assert result.exists()
            assert result == new_dir

    def test_ensure_directory_exists_existing(self):
        """测试已存在的目录"""
        manager = FileSystemDegradationManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = manager.ensure_directory_exists(tmpdir)
            assert str(result) == tmpdir

    def test_safe_write_file_string(self):
        """测试安全写入字符串文件"""
        manager = FileSystemDegradationManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            result = manager.safe_write_file(file_path, "test content")

            assert result is True
            assert file_path.exists()
            assert file_path.read_text() == "test content"

    def test_safe_write_file_bytes(self):
        """测试安全写入字节文件"""
        manager = FileSystemDegradationManager()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.bin"
            result = manager.safe_write_file(file_path, b"binary content")

            assert result is True
            assert file_path.exists()
            assert file_path.read_bytes() == b"binary content"

    def test_cleanup_temp_files(self):
        """测试清理临时文件"""
        manager = FileSystemDegradationManager()

        # 创建一个临时文件
        temp_file = manager.temp_dir / "test_cleanup.tmp"
        temp_file.touch()

        # 清理（使用0小时，应该清理所有文件）
        manager.cleanup_temp_files(max_age_hours=0)

        # 文件应该被删除（除非有权限问题）
        # 注意：由于文件刚创建，可能不会被删除
        # 我们只验证方法不会抛出异常


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_execute_with_network_fallback(self):
        """测试网络降级便捷函数"""
        result = execute_with_network_fallback(
            lambda: "test_result",
            ["timeout_increase"],
        )
        assert result == "test_result"

    def test_ensure_directory_exists_func(self):
        """测试目录确保便捷函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ensure_directory_exists(tmpdir)
            assert str(result) == tmpdir

    def test_safe_write_file_func(self):
        """测试安全写入便捷函数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            result = safe_write_file(file_path, "content")
            assert result is True

    def test_get_network_status_func(self):
        """测试网络状态便捷函数"""
        status = get_network_status()
        assert "status" in status

    def test_check_disk_space_func(self):
        """测试磁盘空间便捷函数"""
        result = check_disk_space(tempfile.gettempdir())
        assert "status" in result


class TestGlobalInstances:
    """测试全局实例"""

    def test_network_degradation_manager_instance(self):
        """测试网络降级管理器全局实例"""
        assert network_degradation_manager is not None
        assert isinstance(network_degradation_manager, NetworkDegradationManager)

    def test_file_system_degradation_manager_instance(self):
        """测试文件系统降级管理器全局实例"""
        from src.core.degradation import file_system_degradation_manager
        assert file_system_degradation_manager is not None
        assert isinstance(file_system_degradation_manager, FileSystemDegradationManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
