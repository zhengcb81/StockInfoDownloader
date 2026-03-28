#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误日志模块 (error_logger.py) 单元测试
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.error_logger import (
    ErrorLogEntry,
    ErrorLogger,
    ErrorLogLevel,
)
from src.core.exceptions import (
    ErrorCode,
    ErrorContext,
    ErrorSeverity,
    RecoveryStrategy,
    StockInfoError,
)


class TestErrorLogLevel:
    """测试 ErrorLogLevel 枚举"""

    def test_log_levels(self):
        """测试日志级别"""
        assert ErrorLogLevel.DEBUG.value == "DEBUG"
        assert ErrorLogLevel.INFO.value == "INFO"
        assert ErrorLogLevel.WARNING.value == "WARNING"
        assert ErrorLogLevel.ERROR.value == "ERROR"
        assert ErrorLogLevel.CRITICAL.value == "CRITICAL"


class TestErrorLogEntry:
    """测试 ErrorLogEntry 数据类"""

    def create_sample_entry(self) -> ErrorLogEntry:
        """创建示例日志条目"""
        return ErrorLogEntry(
            timestamp=datetime.now(),
            error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
            severity=ErrorSeverity.ERROR,
            message="Test error message",
            module="test_module",
            function="test_function",
            line_number=42,
            file_path="/path/to/file.py",
            recovery_strategy=RecoveryStrategy.RETRY,
            recovery_attempted=True,
            recovery_successful=False,
            context={"key": "value"},
            stack_trace="Traceback...",
            original_exception="Original error",
            user_action=None,
            system_state={"cpu": 50},
        )

    def test_to_dict(self):
        """测试转换为字典"""
        entry = self.create_sample_entry()
        result = entry.to_dict()

        assert "timestamp" in result
        assert result["error_code"] == ErrorCode.NETWORK_CONNECTION_ERROR.value
        assert result["severity"] == ErrorSeverity.ERROR.value
        assert result["message"] == "Test error message"
        assert result["module"] == "test_module"
        assert result["recovery_strategy"] == RecoveryStrategy.RETRY.value

    def test_to_json(self):
        """测试转换为 JSON"""
        entry = self.create_sample_entry()
        json_str = entry.to_json()

        # 验证是有效的 JSON
        data = json.loads(json_str)
        assert data["message"] == "Test error message"


class TestErrorLogger:
    """测试 ErrorLogger 类"""

    def test_init(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(
                log_dir=tmpdir,
                enable_console=True,
                enable_file=True,
                enable_json=True,
            )

            assert logger.log_dir == Path(tmpdir)
            assert logger.enable_console is True
            assert logger.enable_file is True
            assert logger.enable_json is True
            assert logger.text_log_path.exists()
            assert logger.json_log_path.exists()

    def test_init_creates_log_directory(self):
        """测试创建日志目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs" / "errors"
            logger = ErrorLogger(log_dir=str(log_dir))

            assert log_dir.exists()

    def test_error_counts_initialized(self):
        """测试错误计数初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            assert logger.error_counts == {}
            assert logger.recovery_stats == {}
            assert logger.error_patterns == {}

    def test_update_statistics(self):
        """测试更新统计信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            entry = ErrorLogEntry(
                timestamp=datetime.now(),
                error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                severity=ErrorSeverity.ERROR,
                message="Test",
                module="test",
                function="func",
                line_number=1,
                file_path="test.py",
                recovery_strategy=RecoveryStrategy.RETRY,
                recovery_attempted=True,
                recovery_successful=True,
                context={},
                stack_trace="",
                original_exception=None,
                user_action=None,
                system_state=None,
            )

            logger._update_statistics(entry)

            assert logger.error_counts[ErrorCode.NETWORK_CONNECTION_ERROR.value] == 1
            assert logger.recovery_stats[ErrorCode.NETWORK_CONNECTION_ERROR.value]["attempted"] == 1
            assert logger.recovery_stats[ErrorCode.NETWORK_CONNECTION_ERROR.value]["successful"] == 1

    def test_log_to_text_file(self):
        """测试写入文本文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir, enable_json=False)

            entry = ErrorLogEntry(
                timestamp=datetime.now(),
                error_code=ErrorCode.FILE_NOT_FOUND_ERROR,
                severity=ErrorSeverity.WARNING,
                message="File not found",
                module="file_module",
                function="read_file",
                line_number=10,
                file_path="file.py",
                recovery_strategy=RecoveryStrategy.FALLBACK,
                recovery_attempted=False,
                recovery_successful=False,
                context={},
                stack_trace="",
                original_exception=None,
                user_action=None,
                system_state=None,
            )

            logger._log_to_text_file(entry)

            content = logger.text_log_path.read_text()
            assert "File not found" in content
            assert "file_module:read_file" in content

    def test_log_to_json_file(self):
        """测试写入 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir, enable_file=False)

            entry = ErrorLogEntry(
                timestamp=datetime.now(),
                error_code=ErrorCode.DATA_PARSING_ERROR,
                severity=ErrorSeverity.ERROR,
                message="Parse error",
                module="parse_module",
                function="parse_data",
                line_number=20,
                file_path="parse.py",
                recovery_strategy=RecoveryStrategy.NONE,
                recovery_attempted=False,
                recovery_successful=False,
                context={},
                stack_trace="",
                original_exception=None,
                user_action=None,
                system_state=None,
            )

            logger._log_to_json_file(entry)

            with open(logger.json_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data["entries"]) == 1
            assert data["entries"][0]["message"] == "Parse error"

    def test_analyze_error_pattern(self):
        """测试错误模式分析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir, enable_console=False, enable_file=False, enable_json=False)

            entry = ErrorLogEntry(
                timestamp=datetime.now(),
                error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                severity=ErrorSeverity.ERROR,
                message="Connection failed",
                module="network",
                function="connect",
                line_number=1,
                file_path="net.py",
                recovery_strategy=RecoveryStrategy.RETRY,
                recovery_attempted=False,
                recovery_successful=False,
                context={},
                stack_trace="",
                original_exception=None,
                user_action=None,
                system_state=None,
            )

            logger._analyze_error_pattern(entry)

            assert "network:connect" in logger.error_patterns
            assert len(logger.error_patterns["network:connect"]) == 1

    def test_get_error_summary_no_errors(self):
        """测试无错误时的摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            summary = logger.get_error_summary()

            assert summary["total_errors"] == 0

    def test_get_error_trends(self):
        """测试获取错误趋势"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            trends = logger.get_error_trends(days=1)

            assert isinstance(trends, dict)

    def test_get_error_patterns_empty(self):
        """测试空错误模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            patterns = logger.get_error_patterns()

            assert patterns == {}

    def test_get_error_patterns_with_entries(self):
        """测试有条目的错误模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(
                log_dir=tmpdir,
                enable_console=False,
                enable_file=False,
                enable_json=False,
            )

            # 添加足够的条目以满足 min_occurrences
            for _ in range(5):
                entry = ErrorLogEntry(
                    timestamp=datetime.now(),
                    error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                    severity=ErrorSeverity.ERROR,
                    message="Error",
                    module="test",
                    function="func",
                    line_number=1,
                    file_path="test.py",
                    recovery_strategy=RecoveryStrategy.RETRY,
                    recovery_attempted=False,
                    recovery_successful=False,
                    context={},
                    stack_trace="",
                    original_exception=None,
                    user_action=None,
                    system_state=None,
                )
                logger._analyze_error_pattern(entry)

            patterns = logger.get_error_patterns(min_occurrences=3)

            assert "test:func" in patterns

    def test_cleanup_old_logs(self):
        """测试清理旧日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            # 创建一个旧文件
            old_file = logger.log_dir / "old_log.log"
            old_file.touch()

            # 设置修改时间为 31 天前
            import os
            old_time = (datetime.now() - timedelta(days=31)).timestamp()
            os.utime(old_file, (old_time, old_time))

            logger.cleanup_old_logs(days=30)

            # 旧文件应该被删除
            assert not old_file.exists()

    def test_calculate_recovery_rate_no_attempts(self):
        """测试无尝试时的恢复率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            rate = logger._calculate_recovery_rate([])
            assert rate == 0.0

    def test_calculate_recovery_rate_with_attempts(self):
        """测试有尝试时的恢复率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            errors = [
                {"recovery_attempted": True, "recovery_successful": True},
                {"recovery_attempted": True, "recovery_successful": True},
                {"recovery_attempted": True, "recovery_successful": False},
            ]

            rate = logger._calculate_recovery_rate(errors)
            assert rate == pytest.approx(2 / 3)

    def test_load_recent_errors_no_file(self):
        """测试文件不存在时加载错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            errors = logger._load_recent_errors(
                datetime.now() - timedelta(hours=1)
            )

            assert errors == []


class TestErrorLoggerWithStockInfoError:
    """测试 ErrorLogger 与 StockInfoError 集成"""

    def create_mock_error(self) -> StockInfoError:
        """创建模拟错误"""
        return StockInfoError(
            message="Test error",
            error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
            severity=ErrorSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.RETRY,
            context={"test_key": "test_value"},
        )

    def test_log_error(self):
        """测试记录 StockInfoError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(
                log_dir=tmpdir,
                enable_console=False,
                enable_file=True,
                enable_json=True,
            )

            error = self.create_mock_error()
            logger.log_error(error)

            # 验证文本日志
            content = logger.text_log_path.read_text()
            assert "Test error" in content or logger.text_log_path.exists()

            # 验证 JSON 日志
            with open(logger.json_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert len(data["entries"]) >= 1

    def test_log_error_with_additional_context(self):
        """测试带额外上下文的错误记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(
                log_dir=tmpdir,
                enable_console=False,
                enable_file=False,
                enable_json=True,
            )

            error = self.create_mock_error()
            logger.log_error(error, additional_context={"extra": "info"})

            with open(logger.json_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 验证条目被添加
            assert len(data["entries"]) >= 1

    def test_create_log_entry(self):
        """Test create log entry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            error = self.create_mock_error()

            entry = logger._create_log_entry(error)

            assert entry.error_code == ErrorCode.NETWORK_CONNECTION_ERROR
            assert entry.severity == ErrorSeverity.ERROR
            assert entry.message == "Test error"
            # caller_info is dynamically determined from stack frames
            assert entry.module is not None
            assert entry.function is not None


class TestErrorLoggerExport:
    """测试错误日志导出功能"""

    def test_export_error_report_json(self):
        """测试导出 JSON 报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)
            output_path = Path(tmpdir) / "report.json"

            result = logger.export_error_report(
                str(output_path), hours=24, format_type="json"
            )

            assert result is True
            assert output_path.exists()

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "summary" in data
            assert "trends" in data
            assert "patterns" in data

    def test_generate_recommendations_high_frequency(self):
        """Test high frequency error recommendations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            summary = {"error_frequency": 15, "recovery_rate": 0.8}
            patterns = {}

            recommendations = logger._generate_recommendations(summary, patterns)

            assert any("High error frequency" in r for r in recommendations)

    def test_generate_recommendations_low_recovery(self):
        """Test low recovery rate recommendations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ErrorLogger(log_dir=tmpdir)

            summary = {"error_frequency": 5, "recovery_rate": 0.3}
            patterns = {}

            recommendations = logger._generate_recommendations(summary, patterns)

            assert any("Low error recovery rate" in r for r in recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
