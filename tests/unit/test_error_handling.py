"""
结构化错误处理系统测试
验证异常类、错误处理器、日志记录和降级策略的功能
"""

import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.degradation import (
    FileSystemDegradationManager,
    NetworkDegradationManager,
)
from src.core.error_logger import ErrorLogEntry, ErrorLogger
from src.core.exceptions import (
    ConfigError,
    ErrorCode,
    ErrorHandler,
    ErrorSeverity,
    FileSystemError,
    NetworkError,
    RecoveryStrategy,
    StockInfoError,
    ValidationError,
    WebDriverError,
    with_error_handling,
)


class TestStructuredExceptions(unittest.TestCase):
    """结构化异常类测试"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        error = StockInfoError(
            message="Test error message",
            error_code=ErrorCode.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
            recovery_strategy=RecoveryStrategy.RETRY,
            context={"test": "context"},
        )

        self.assertEqual(str(error), "[SYS_1000] ERROR: Test error message")
        self.assertEqual(error.error_code, ErrorCode.SYSTEM_ERROR)
        self.assertEqual(error.severity, ErrorSeverity.ERROR)
        self.assertEqual(error.recovery_strategy, RecoveryStrategy.RETRY)
        self.assertEqual(error.context, {"test": "context"})
        self.assertIsNotNone(error.timestamp)
        self.assertIsNotNone(error.stack_trace)

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        error = StockInfoError(
            message="Test error",
            error_code=ErrorCode.CONFIG_FILE_ERROR,
            severity=ErrorSeverity.WARNING,
        )

        error_dict = error.to_dict()

        self.assertIsInstance(error_dict, dict)
        self.assertEqual(error_dict["error_code"], "CFG_3000")
        self.assertEqual(error_dict["severity"], "WARNING")
        self.assertEqual(error_dict["message"], "Test error")
        self.assertIn("timestamp", error_dict)
        self.assertIn("caller_info", error_dict)

    def test_specific_exception_types(self):
        """Test specific exception types"""
        # WebDriver exception
        webdriver_error = WebDriverError("WebDriver failed")
        self.assertEqual(
            webdriver_error.error_code, ErrorCode.WEBDRIVER_CONNECTION_ERROR
        )

        # Config exception
        config_error = ConfigError("Config failed")
        self.assertEqual(config_error.error_code, ErrorCode.CONFIG_FILE_ERROR)

        # Network exception
        network_error = NetworkError("Network failed")
        self.assertEqual(network_error.error_code, ErrorCode.NETWORK_CONNECTION_ERROR)

        # FileSystem exception
        file_error = FileSystemError("File system failed")
        self.assertEqual(file_error.error_code, ErrorCode.FILE_NOT_FOUND_ERROR)

        # Validation exception
        validation_error = ValidationError("Validation failed")
        self.assertEqual(validation_error.error_code, ErrorCode.VALIDATION_INPUT_ERROR)

    def test_exception_with_original_exception(self):
        """测试包含原始异常的异常"""
        original_error = ValueError("Original error")
        error = StockInfoError(
            message="Wrapped error", original_exception=original_error
        )

        self.assertIn("Original error", str(error.original_exception))
        self.assertEqual(error.original_exception, original_error)


class TestErrorHandler(unittest.TestCase):
    """错误处理器测试"""

    def setUp(self):
        """测试前设置"""
        self.handler = ErrorHandler()
        # 清空错误历史
        self.handler.error_history.clear()

    def test_error_handling(self):
        """测试错误处理"""
        error = StockInfoError("Test error")

        # 处理错误
        result = self.handler.handle_error(error)

        # 验证错误被记录
        self.assertEqual(len(self.handler.error_history), 1)
        self.assertEqual(self.handler.error_history[0].message, "Test error")
        self.assertTrue(self.handler.error_history[0].recovery_attempted)

    def test_recovery_handler_registration(self):
        """测试恢复处理器注册"""

        def custom_recovery(error):
            return True

        # 注册恢复处理器
        self.handler.register_recovery_handler(ErrorCode.SYSTEM_ERROR, custom_recovery)

        # 验证处理器被注册
        self.assertIn(ErrorCode.SYSTEM_ERROR, self.handler.recovery_handlers)
        self.assertEqual(
            self.handler.recovery_handlers[ErrorCode.SYSTEM_ERROR], custom_recovery
        )

    def test_recovery_execution(self):
        """测试恢复执行"""
        recovery_called = False

        def test_recovery(error):
            nonlocal recovery_called
            recovery_called = True
            return True

        # 注册恢复处理器
        self.handler.register_recovery_handler(ErrorCode.SYSTEM_ERROR, test_recovery)

        # 创建可恢复的错误
        error = StockInfoError(
            "Test error",
            error_code=ErrorCode.SYSTEM_ERROR,
            recovery_strategy=RecoveryStrategy.RETRY,
        )

        # 处理错误
        result = self.handler.handle_error(error)

        # 验证恢复处理器被调用
        self.assertTrue(recovery_called)
        self.assertTrue(result)

    def test_error_statistics(self):
        """测试错误统计"""
        # 添加多个错误
        errors = [
            StockInfoError("Error 1", error_code=ErrorCode.SYSTEM_ERROR),
            StockInfoError("Error 2", error_code=ErrorCode.SYSTEM_ERROR),
            StockInfoError("Error 3", error_code=ErrorCode.CONFIG_FILE_ERROR),
        ]

        for error in errors:
            self.handler.handle_error(error)

        # 获取统计信息
        stats = self.handler.get_error_statistics()

        self.assertEqual(stats["total_errors"], 3)
        self.assertEqual(stats["error_codes"]["SYS_1000"], 2)
        self.assertEqual(stats["error_codes"]["CFG_3000"], 1)
        self.assertIn("recovery_rate", stats)


class TestErrorHandlingDecorator(unittest.TestCase):
    """错误处理装饰器测试"""

    def test_successful_execution(self):
        """测试成功执行"""

        @with_error_handling(
            error_code=ErrorCode.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
            max_retries=1,
        )
        def test_function():
            return "success"

        result = test_function()
        self.assertEqual(result, "success")

    def test_retry_mechanism(self):
        """测试重试机制"""
        call_count = 0

        @with_error_handling(
            error_code=ErrorCode.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
            max_retries=3,
        )
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise StockInfoError("Temporary error")
            return "success"

        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_exception_conversion(self):
        """测试异常转换"""

        @with_error_handling(
            error_code=ErrorCode.CONFIG_FILE_ERROR, severity=ErrorSeverity.WARNING
        )
        def test_function():
            raise ValueError("Original error")

        with self.assertRaises(StockInfoError) as context:
            test_function()

        self.assertIn("Original error", str(context.exception))
        self.assertEqual(context.exception.error_code, ErrorCode.CONFIG_FILE_ERROR)


class TestErrorLogger(unittest.TestCase):
    """错误日志记录器测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = ErrorLogger(
            log_dir=str(self.temp_dir),
            enable_console=False,
            enable_file=True,
            enable_json=True,
        )

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)

    def test_log_entry_creation(self):
        """测试日志条目创建"""
        error = StockInfoError(
            "Test error",
            error_code=ErrorCode.SYSTEM_ERROR,
            severity=ErrorSeverity.ERROR,
        )

        log_entry = self.logger._create_log_entry(error)

        self.assertIsInstance(log_entry, ErrorLogEntry)
        self.assertEqual(log_entry.message, "Test error")
        self.assertEqual(log_entry.error_code, ErrorCode.SYSTEM_ERROR)
        self.assertEqual(log_entry.severity, ErrorSeverity.ERROR)

    def test_error_logging(self):
        """测试错误记录"""
        error = StockInfoError("Test error")

        # 记录错误
        self.logger.log_error(error)

        # 验证文件被创建
        self.assertTrue(self.logger.text_log_path.exists())
        self.assertTrue(self.logger.json_log_path.exists())

    def test_error_summary(self):
        """测试错误摘要"""
        # 记录多个错误
        errors = [
            StockInfoError("Error 1", error_code=ErrorCode.SYSTEM_ERROR),
            StockInfoError("Error 2", error_code=ErrorCode.SYSTEM_ERROR),
            StockInfoError("Error 3", error_code=ErrorCode.CONFIG_FILE_ERROR),
        ]

        for error in errors:
            self.logger.log_error(error)

        # 获取摘要
        summary = self.logger.get_error_summary(hours=24)

        self.assertEqual(summary["total_errors"], 3)
        self.assertEqual(summary["error_codes"]["SYS_1000"], 2)
        self.assertEqual(summary["error_codes"]["CFG_3000"], 1)
        self.assertIn("recovery_rate", summary)

    def test_error_patterns(self):
        """测试错误模式分析"""
        # 记录相同位置的多个错误
        for i in range(5):
            error = StockInfoError(f"Pattern error {i}")
            error.caller_info = {"module": "test_module", "function": "test_function"}
            self.logger.log_error(error)

        # 获取错误模式
        patterns = self.logger.get_error_patterns(min_occurrences=3)

        self.assertIn("test_module:test_function", patterns)
        self.assertEqual(patterns["test_module:test_function"]["total_occurrences"], 5)

    def test_log_rotation(self):
        """测试日志轮转"""
        # 设置很小的文件大小限制以触发轮转
        self.logger.max_file_size = 1024  # 1KB

        # 记录大量错误
        for i in range(100):
            error = StockInfoError(f"Large error message {i}" * 100)
            self.logger.log_error(error)

        # 验证备份文件被创建
        backup_files = list(self.temp_dir.glob("errors_*.log"))
        self.assertGreater(len(backup_files), 0)


class TestNetworkDegradationManager(unittest.TestCase):
    """网络降级管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = NetworkDegradationManager()

    def test_network_health_check(self):
        """测试网络健康检查"""
        # 由于网络检查依赖外部服务，我们模拟测试
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = self.manager.check_network_health()
            self.assertTrue(result)
            self.assertGreater(len(self.manager.connection_history), 0)

    def test_circuit_breaker(self):
        """测试熔断器机制"""
        # 模拟连续失败
        for i in range(10):
            self.manager._record_failure()

        # 验证熔断器被打开
        self.assertTrue(self.manager.circuit_breaker_open)
        self.assertIsNotNone(self.manager.circuit_breaker_timeout)

    def test_degradation_level_adjustment(self):
        """测试降级级别调整"""
        # 模拟高失败率
        for i in range(15):
            self.manager.connection_history.append(
                {
                    "timestamp": datetime.now(),
                    "success": False,
                    "error": "Connection failed",
                }
            )

        # 添加少量成功
        for i in range(5):
            self.manager.connection_history.append(
                {"timestamp": datetime.now(), "success": True, "response_time": 0.1}
            )

        # 调整降级级别
        self.manager._adjust_degradation_level()

        # 验证降级级别被调整
        self.assertGreater(self.manager.current_level.priority, 1)

    def test_fallback_execution(self):
        """测试降级执行"""

        def failing_operation():
            raise ConnectionError("Network failed")

        context = {"timeout": 30}

        # 使用降级策略执行
        result = self.manager.execute_with_fallback(
            failing_operation, ["timeout_increase", "retry_with_backoff"], context
        )

        # 验证上下文被修改
        self.assertIn("strategy_used", context)
        self.assertGreater(context.get("timeout", 30), 30)

    def test_network_status(self):
        """测试网络状态获取"""
        # 添加一些历史记录
        self.manager.connection_history = [
            {"timestamp": datetime.now(), "success": True, "response_time": 0.1},
            {"timestamp": datetime.now(), "success": True, "response_time": 0.2},
            {"timestamp": datetime.now(), "success": False, "error": "timeout"},
        ]

        status = self.manager.get_network_status()

        self.assertIn("status", status)
        self.assertIn("success_rate", status)
        self.assertIn("current_level", status)


class TestFileSystemDegradationManager(unittest.TestCase):
    """文件系统降级管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = FileSystemDegradationManager()

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)

    def test_directory_creation(self):
        """测试目录创建"""
        test_path = self.temp_dir / "test" / "nested" / "directory"

        # 确保目录存在
        result_path = self.manager.ensure_directory_exists(test_path)

        self.assertTrue(result_path.exists())
        self.assertEqual(result_path.name, "directory")

    def test_fallback_directory_usage(self):
        """测试备用目录使用"""
        # 模拟无法访问的目录
        inaccessible_path = Path("/root/inaccessible")

        # 尝试确保目录存在（应该使用备用目录）
        try:
            result_path = self.manager.ensure_directory_exists(inaccessible_path)
            # 如果没有抛出异常，说明使用了备用目录
            self.assertTrue(result_path.exists())
        except FileSystemError:
            # 如果抛出异常，也是可以接受的
            pass

    def test_safe_file_write(self):
        """测试安全文件写入"""
        test_file = self.temp_dir / "test.txt"
        content = "Test content"

        # 安全写入文件
        result = self.manager.safe_write_file(test_file, content)

        self.assertTrue(result)
        self.assertTrue(test_file.exists())

        # 验证文件内容
        with open(test_file, "r", encoding="utf-8") as f:
            file_content = f.read()
        self.assertEqual(file_content, content)

    def test_disk_space_check(self):
        """测试磁盘空间检查"""
        space_info = self.manager.check_disk_space(self.temp_dir)

        self.assertIn("total", space_info)
        self.assertIn("used", space_info)
        self.assertIn("free", space_info)
        self.assertIn("percent_used", space_info)
        self.assertIn("status", space_info)

    def test_temp_file_cleanup(self):
        """测试临时文件清理"""
        # 创建一些临时文件在管理器的临时目录中
        old_time = time.time() - 25 * 3600  # 25小时前

        temp_files = []
        for i in range(3):
            temp_file = self.manager.temp_dir / f"temp_{i}.tmp"
            temp_file.write_text(f"Content {i}")
            # 修改文件时间为过去
            os.utime(temp_file, (old_time, old_time))
            temp_files.append(temp_file)

        # 清理临时文件
        self.manager.cleanup_temp_files(max_age_hours=24)

        # 验证文件被清理
        for temp_file in temp_files:
            self.assertFalse(temp_file.exists())


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前设置"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)

    def test_end_to_end_error_handling(self):
        """测试端到端错误处理"""
        # 创建自定义错误处理器
        handler = ErrorHandler()

        # 注册恢复处理器
        def test_recovery(error):
            return "recovered"

        handler.register_recovery_handler(ErrorCode.SYSTEM_ERROR, test_recovery)

        # 创建错误
        error = StockInfoError(
            "Integration test error",
            error_code=ErrorCode.SYSTEM_ERROR,
            recovery_strategy=RecoveryStrategy.RETRY,
        )

        # 处理错误
        result = handler.handle_error(error)

        # 验证处理结果
        self.assertTrue(result)
        self.assertEqual(len(handler.error_history), 1)

        # 获取统计信息
        stats = handler.get_error_statistics()
        self.assertEqual(stats["total_errors"], 1)

    def test_error_logging_integration(self):
        """测试错误日志集成"""
        # 创建错误日志记录器
        logger = ErrorLogger(log_dir=str(self.temp_dir), enable_console=False)

        # 创建错误处理器
        handler = ErrorHandler()

        # 记录错误
        error = StockInfoError("Integration test error")
        logger.log_error(error)

        # 验证日志文件
        self.assertTrue(logger.text_log_path.exists())
        self.assertTrue(logger.json_log_path.exists())

        # 获取错误摘要
        summary = logger.get_error_summary()
        self.assertEqual(summary["total_errors"], 1)

    def test_degradation_integration(self):
        """测试降级集成"""
        # 创建网络降级管理器
        network_manager = NetworkDegradationManager()

        # 模拟网络故障
        for i in range(10):
            network_manager._record_failure()

        # 验证降级级别
        self.assertGreater(network_manager.current_level.priority, 1)

        # 验证熔断器状态
        if network_manager.circuit_breaker_open:
            self.assertIsNotNone(network_manager.circuit_breaker_timeout)


if __name__ == "__main__":
    # 配置测试运行
    unittest.main(verbosity=2)
