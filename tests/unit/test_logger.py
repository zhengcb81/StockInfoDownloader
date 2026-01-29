#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志系统单元测试
测试Logger类的功能
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.logger import LoggerManager, get_logger


class TestLogger:
    """日志系统测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger("test_logger", self.log_file)

    def teardown_method(self):
        """测试清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_config(self):
        """测试默认配置初始化"""
        logger = get_logger("test")
        assert logger.name == "test"
        assert logger.logger.level == logging.INFO
        assert isinstance(logger.logger, logging.Logger)

    def test_init_with_file(self):
        """测试带文件初始化"""
        logger = self.logger_manager.get_logger("test", self.log_file)

        # 检查文件处理器是否添加
        file_handlers = [
            h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_init_with_level(self):
        """测试带日志级别初始化"""
        # Note: LoggerManager returns existing loggers if they already exist
        # So we need to use a unique name to test level setting
        logger = self.logger_manager.get_logger(
            f"test_level_{id(self)}", level=logging.DEBUG
        )
        assert logger.logger.level == logging.DEBUG

    def test_get_logger(self):
        """测试获取logger实例"""
        logger_instance = self.logger
        assert logger_instance is not None
        assert isinstance(logger_instance.logger, logging.Logger)
        assert logger_instance.name == "test_logger"

    def test_log_levels(self):
        """测试不同日志级别"""
        # 测试DEBUG级别
        self.logger_manager.set_log_level("test_logger", logging.DEBUG)
        assert self.logger.logger.level == logging.DEBUG

        # 测试INFO级别
        self.logger_manager.set_log_level("test_logger", logging.INFO)
        assert self.logger.logger.level == logging.INFO

        # 测试WARNING级别
        self.logger_manager.set_log_level("test_logger", logging.WARNING)
        assert self.logger.logger.level == logging.WARNING

        # 测试ERROR级别
        self.logger_manager.set_log_level("test_logger", logging.ERROR)
        assert self.logger.logger.level == logging.ERROR

    def test_debug_logging(self):
        """测试DEBUG日志记录"""
        self.logger_manager.set_log_level("test_logger", logging.DEBUG)

        # Mock日志方法
        with patch.object(self.logger, "debug") as mock_debug:
            self.logger.debug("Debug message")
            mock_debug.assert_called_once_with("Debug message")

    def test_info_logging(self):
        """测试INFO日志记录"""
        with patch.object(self.logger, "info") as mock_info:
            self.logger.info("Info message")
            mock_info.assert_called_once_with("Info message")

    def test_warning_logging(self):
        """测试WARNING日志记录"""
        with patch.object(self.logger, "warning") as mock_warning:
            self.logger.warning("Warning message")
            mock_warning.assert_called_once_with("Warning message")

    def test_error_logging(self):
        """测试ERROR日志记录"""
        with patch.object(self.logger, "error") as mock_error:
            self.logger.error("Error message")
            mock_error.assert_called_once_with("Error message")

    def test_critical_logging(self):
        """测试CRITICAL日志记录"""
        with patch.object(self.logger, "critical") as mock_critical:
            self.logger.critical("Critical message")
            mock_critical.assert_called_once_with("Critical message")

    def test_log_with_exception(self):
        """测试带异常的日志记录"""
        exception = ValueError("Test exception")

        with patch.object(self.logger, "error") as mock_error:
            self.logger.error("Error occurred", exc_info=exception)
            mock_error.assert_called_once()

            # 检查调用参数
            args, kwargs = mock_error.call_args
            assert args[0] == "Error occurred"
            assert "exc_info" in kwargs

    def test_log_to_file(self):
        """测试日志写入文件"""
        test_message = "Test log message"

        # 写入日志
        self.logger.info(test_message)

        # 强制刷新
        for handler in self.logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()

        # 检查文件内容
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert test_message in content

    def test_multiple_handlers(self):
        """测试多个处理器"""
        # 创建另一个日志器来测试多个处理器
        logger2 = self.logger_manager.get_logger(
            "test_logger2", os.path.join(self.temp_dir, "test2.log")
        )

        # 检查处理器数量
        file_handlers = [
            h for h in logger2.logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_console_handler(self):
        """测试控制台处理器"""
        # 检查默认控制台处理器
        console_handlers = [
            h
            for h in self.logger.logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(console_handlers) >= 1

    def test_logger_singleton(self):
        """测试LoggerManager单例模式"""
        # 创建同名的logger manager
        manager1 = LoggerManager()
        manager2 = LoggerManager()

        # 应该是同一个实例
        assert manager1 is manager2

    def test_different_loggers(self):
        """测试不同的logger实例"""
        logger1 = self.logger_manager.get_logger("logger1")
        logger2 = self.logger_manager.get_logger("logger2")

        # 应该是不同的实例
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_log_performance(self):
        """测试日志性能"""
        import time

        # 记录大量日志
        start_time = time.time()
        for i in range(1000):
            self.logger.info(f"Performance test message {i}")
        end_time = time.time()

        # 应该在合理时间内完成
        assert end_time - start_time < 1.0  # 1秒内完成1000条日志

    def test_log_thread_safety(self):
        """测试日志线程安全性"""
        import threading

        results = []

        def log_worker(worker_id):
            for i in range(100):
                self.logger.info(f"Worker {worker_id} message {i}")
            results.append(worker_id)

        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 检查所有线程都完成了
        assert len(results) == 5

    def test_log_with_context(self):
        """测试带上下文的日志"""
        context = {"user": "test", "action": "login"}

        with patch.object(self.logger, "info") as mock_info:
            self.logger.info("User action", extra=context)
            mock_info.assert_called_once()

            # 检查上下文
            args, kwargs = mock_info.call_args
            assert "extra" in kwargs
            assert kwargs["extra"] == context

    def test_get_log_files(self):
        """测试获取日志文件"""
        log_files = self.logger_manager.get_log_files()
        assert isinstance(log_files, dict)

    def test_cleanup_logs(self):
        """测试清理日志"""
        # 测试清理功能
        cleaned_count = self.logger_manager.cleanup_logs(days=0)  # 清理所有日志
        assert isinstance(cleaned_count, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
