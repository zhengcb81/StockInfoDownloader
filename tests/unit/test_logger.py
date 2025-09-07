#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志系统单元测试
测试Logger类的功能
"""

import pytest
import tempfile
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.logger import Logger


class TestLogger:
    """日志系统测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'test.log')
        self.logger = Logger("test_logger", self.log_file)
    
    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        logger = Logger("test")
        assert logger.name == "test"
        assert logger.level == logging.INFO
        assert logger.logger is not None
        assert isinstance(logger.logger, logging.Logger)
    
    def test_init_with_file(self):
        """测试带文件初始化"""
        logger = Logger("test", self.log_file)
        assert logger.log_file == self.log_file
        
        # 检查文件处理器是否添加
        file_handlers = [h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
    
    def test_init_with_level(self):
        """测试带日志级别初始化"""
        logger = Logger("test", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
        assert logger.logger.level == logging.DEBUG
    
    def test_get_logger(self):
        """测试获取logger实例"""
        logger_instance = self.logger.get_logger()
        assert logger_instance is not None
        assert isinstance(logger_instance, logging.Logger)
        assert logger_instance.name == "test_logger"
    
    def test_log_levels(self):
        """测试不同日志级别"""
        # 测试DEBUG级别
        self.logger.set_level(logging.DEBUG)
        assert self.logger.level == logging.DEBUG
        
        # 测试INFO级别
        self.logger.set_level(logging.INFO)
        assert self.logger.level == logging.INFO
        
        # 测试WARNING级别
        self.logger.set_level(logging.WARNING)
        assert self.logger.level == logging.WARNING
        
        # 测试ERROR级别
        self.logger.set_level(logging.ERROR)
        assert self.logger.level == logging.ERROR
    
    def test_debug_logging(self):
        """测试DEBUG日志记录"""
        self.logger.set_level(logging.DEBUG)
        
        # Mock日志方法
        with patch.object(self.logger.logger, 'debug') as mock_debug:
            self.logger.debug("Debug message")
            mock_debug.assert_called_once_with("Debug message")
    
    def test_info_logging(self):
        """测试INFO日志记录"""
        with patch.object(self.logger.logger, 'info') as mock_info:
            self.logger.info("Info message")
            mock_info.assert_called_once_with("Info message")
    
    def test_warning_logging(self):
        """测试WARNING日志记录"""
        with patch.object(self.logger.logger, 'warning') as mock_warning:
            self.logger.warning("Warning message")
            mock_warning.assert_called_once_with("Warning message")
    
    def test_error_logging(self):
        """测试ERROR日志记录"""
        with patch.object(self.logger.logger, 'error') as mock_error:
            self.logger.error("Error message")
            mock_error.assert_called_once_with("Error message")
    
    def test_critical_logging(self):
        """测试CRITICAL日志记录"""
        with patch.object(self.logger.logger, 'critical') as mock_critical:
            self.logger.critical("Critical message")
            mock_critical.assert_called_once_with("Critical message")
    
    def test_log_with_exception(self):
        """测试带异常的日志记录"""
        exception = ValueError("Test exception")
        
        with patch.object(self.logger.logger, 'error') as mock_error:
            self.logger.error("Error occurred", exc_info=exception)
            mock_error.assert_called_once()
            
            # 检查调用参数
            args, kwargs = mock_error.call_args
            assert args[0] == "Error occurred"
            assert 'exc_info' in kwargs
    
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
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert test_message in content
    
    def test_multiple_handlers(self):
        """测试多个处理器"""
        # 创建另一个日志文件
        log_file2 = os.path.join(self.temp_dir, 'test2.log')
        
        # 添加文件处理器
        self.logger.add_file_handler(log_file2)
        
        # 检查处理器数量
        file_handlers = [h for h in self.logger.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 2
    
    def test_console_handler(self):
        """测试控制台处理器"""
        # 添加控制台处理器
        self.logger.add_console_handler()
        
        # 检查处理器
        console_handlers = [h for h in self.logger.logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1
    
    def test_remove_handler(self):
        """测试移除处理器"""
        # 添加一个额外的处理器
        extra_file = os.path.join(self.temp_dir, 'extra.log')
        handler = logging.FileHandler(extra_file)
        self.logger.logger.addHandler(handler)
        
        # 移除处理器
        self.logger.remove_handler(handler)
        
        # 检查是否移除
        assert handler not in self.logger.logger.handlers
    
    def test_log_format(self):
        """测试日志格式"""
        # 测试默认格式
        formatter = self.logger.logger.handlers[0].formatter
        assert formatter is not None
        
        # 测试自定义格式
        custom_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.logger.set_format(custom_format)
        
        # 检查格式是否应用
        formatter = self.logger.logger.handlers[0].formatter
        assert custom_format in formatter._fmt
    
    def test_log_rotation(self):
        """测试日志轮转"""
        # 创建大日志文件测试轮转
        rotation_file = os.path.join(self.temp_dir, 'rotation.log')
        
        # 设置小尺寸进行测试
        self.logger.add_file_handler(rotation_file, max_bytes=1024, backup_count=3)
        
        # 写入大量数据
        for i in range(100):
            self.logger.info(f"Large log message {i}" * 100)
        
        # 检查是否创建轮转文件
        rotation_files = [f for f in os.listdir(self.temp_dir) if f.startswith('rotation.log')]
        assert len(rotation_files) > 1  # 应该有轮转文件
    
    def test_log_filtering(self):
        """测试日志过滤"""
        # 创建过滤器
        class TestFilter(logging.Filter):
            def filter(self, record):
                return "important" in record.getMessage().lower()
        
        filter_obj = TestFilter()
        self.logger.add_filter(filter_obj)
        
        # Mock日志方法
        with patch.object(self.logger.logger, 'info') as mock_info:
            # 应该被记录
            self.logger.info("This is an important message")
            # 不应该被记录
            self.logger.info("This is a normal message")
            
            # 只应该调用一次（important消息）
            assert mock_info.call_count == 1
    
    def test_logger_singleton(self):
        """测试Logger单例模式"""
        # 创建同名的logger
        logger1 = Logger("test_singleton")
        logger2 = Logger("test_singleton")
        
        # 应该是同一个实例
        assert logger1 is logger2
    
    def test_different_loggers(self):
        """测试不同的logger实例"""
        logger1 = Logger("logger1")
        logger2 = Logger("logger2")
        
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
        import time
        
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
    
    def test_cleanup(self):
        """测试清理资源"""
        # 添加一些处理器
        self.logger.add_console_handler()
        extra_file = os.path.join(self.temp_dir, 'cleanup.log')
        self.logger.add_file_handler(extra_file)
        
        # 清理
        self.logger.cleanup()
        
        # 检查处理器是否被移除
        assert len(self.logger.logger.handlers) == 0
    
    def test_invalid_log_level(self):
        """测试无效日志级别"""
        # 测试无效级别
        with pytest.raises(ValueError):
            self.logger.set_level("invalid")
        
        # 测试None级别
        with pytest.raises(ValueError):
            self.logger.set_level(None)
    
    def test_log_with_context(self):
        """测试带上下文的日志"""
        context = {"user": "test", "action": "login"}
        
        with patch.object(self.logger.logger, 'info') as mock_info:
            self.logger.info("User action", extra=context)
            mock_info.assert_called_once()
            
            # 检查上下文
            args, kwargs = mock_info.call_args
            assert "extra" in kwargs
            assert kwargs["extra"] == context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])