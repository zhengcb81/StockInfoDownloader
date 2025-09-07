#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志配置模块单元测试
"""

import unittest
import tempfile
import os
import sys
import json
from unittest.mock import patch, MagicMock
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger_config import StructuredLogger, get_logger, setup_global_logging
from tests.test_config import TestEnvironment


class TestStructuredLogger(unittest.TestCase):
    """结构化日志记录器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_log_dir = self.test_env.create_temp_dir("test_logs_")
        self.test_log_file = os.path.join(self.test_log_dir, "test.log")
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_logger_initialization(self):
        """测试日志记录器初始化"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        self.assertIsNotNone(logger)
        self.assertIsNotNone(logger.logger)
        self.assertEqual(logger.logger.name, "test_logger")
        self.assertEqual(logger.logger.level, logging.INFO)
        self.assertGreater(len(logger.logger.handlers), 0)
    
    def test_logger_without_file(self):
        """测试不使用文件的日志记录器"""
        logger = StructuredLogger("test_logger")
        
        self.assertIsNotNone(logger)
        self.assertEqual(logger.logger.name, "test_logger")
        # 应该至少有一个处理器（控制台处理器）
        self.assertGreaterEqual(len(logger.logger.handlers), 1)
    
    def test_info_logging(self):
        """测试信息日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录一条信息日志
        logger.info("测试信息日志")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_info_logging_with_context(self):
        """测试带上下文的信息日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录带上下文的信息日志
        logger.info("测试信息日志", user_id=123, action="test_action")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_error_logging(self):
        """测试错误日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录一条错误日志
        logger.error("测试错误日志")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_error_logging_with_context(self):
        """测试带上下文的错误日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录带上下文的错误日志
        logger.error("测试错误日志", error_code=500, error_message="内部服务器错误")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_warning_logging(self):
        """测试警告日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录一条警告日志
        logger.warning("测试警告日志")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_debug_logging(self):
        """测试调试日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file, logging.DEBUG)
        
        # 记录一条调试日志
        logger.debug("测试调试日志")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_critical_logging(self):
        """测试严重错误日志记录"""
        logger = StructuredLogger("test_logger", self.test_log_file)
        
        # 记录一条严重错误日志
        logger.critical("测试严重错误日志")
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(self.test_log_file))
    
    def test_log_file_rotation(self):
        """测试日志文件轮转"""
        # 创建一个小容量的日志记录器来测试轮转
        small_log_file = os.path.join(self.test_log_dir, "small.log")
        logger = StructuredLogger("test_logger", small_log_file)
        
        # 记录大量日志来触发轮转
        for i in range(100):
            logger.info(f"测试日志消息 {i}" * 100)
        
        # 验证日志文件存在
        self.assertTrue(os.path.exists(small_log_file))


class TestGetLoggerFunction(unittest.TestCase):
    """get_logger函数测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_log_dir = self.test_env.create_temp_dir("test_logs_")
        self.test_log_file = os.path.join(self.test_log_dir, "test.log")
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_get_logger_with_file(self):
        """测试获取带文件的日志记录器"""
        logger = get_logger("test_logger", self.test_log_file)
        
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.logger.name, "test_logger")
    
    def test_get_logger_without_file(self):
        """测试获取不带文件的日志记录器"""
        logger = get_logger("test_logger")
        
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.logger.name, "test_logger")
    
    def test_get_logger_with_custom_level(self):
        """测试获取自定义级别的日志记录器"""
        logger = get_logger("test_logger", self.test_log_file, logging.DEBUG)
        
        self.assertIsInstance(logger, StructuredLogger)
        self.assertEqual(logger.logger.level, logging.DEBUG)


class TestGlobalLoggingSetup(unittest.TestCase):
    """全局日志设置测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_log_dir = self.test_env.create_temp_dir("test_global_logs_")
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_setup_global_logging(self):
        """测试全局日志设置"""
        # 设置全局日志
        setup_global_logging(self.test_log_dir, logging.INFO)
        
        # 验证日志目录存在
        self.assertTrue(os.path.exists(self.test_log_dir))
        
        # 验证应用日志文件存在
        app_log_file = os.path.join(self.test_log_dir, "application.log")
        self.assertTrue(os.path.exists(app_log_file))
    
    def test_setup_global_logging_creates_directory(self):
        """测试全局日志设置创建目录"""
        new_log_dir = os.path.join(self.test_log_dir, "new_logs")
        
        # 目录应该不存在
        self.assertFalse(os.path.exists(new_log_dir))
        
        # 设置全局日志应该创建目录
        setup_global_logging(new_log_dir, logging.INFO)
        
        # 验证目录已创建
        self.assertTrue(os.path.exists(new_log_dir))


class TestLoggerIntegration(unittest.TestCase):
    """日志集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_log_dir = self.test_env.create_temp_dir("test_integration_logs_")
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_logger_integration_with_downloader(self):
        """测试日志记录器与下载器集成"""
        # 这个测试需要确保日志模块能与现有代码正确集成
        from cninfo_activity_downloader import CninfoDownloader
        
        # 创建下载器实例
        test_dir = self.test_env.create_temp_dir("test_downloader_")
        downloader = CninfoDownloader(save_dir=test_dir)
        
        # 验证下载器能正常工作
        self.assertIsNotNone(downloader)
        self.assertTrue(os.path.exists(test_dir))
    
    def test_multiple_loggers_same_name(self):
        """测试多个同名日志记录器"""
        logger1 = StructuredLogger("same_name", os.path.join(self.test_log_dir, "log1.log"))
        logger2 = StructuredLogger("same_name", os.path.join(self.test_log_dir, "log2.log"))
        
        # 应该是同一个日志记录器实例（避免重复添加处理器）
        self.assertEqual(logger1.logger, logger2.logger)


if __name__ == "__main__":
    unittest.main()