#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一日志配置模块
提供结构化的日志记录功能
"""

import os
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Optional


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, log_file: Optional[str] = None, level: int = logging.INFO):
        """
        初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: Optional[str]):
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 使用RotatingFileHandler避免日志文件过大
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # 强制创建文件并写入一条测试日志来确保文件存在
            # 临时降低日志级别以确保初始化消息被记录
            original_level = self.logger.level
            self.logger.setLevel(logging.INFO)
            self.logger.info("Logger initialized")
            self.logger.handlers[-1].flush()  # 强制刷新
            self.logger.setLevel(original_level)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        if kwargs:
            message = f"{message} | Context: {json.dumps(kwargs, ensure_ascii=False)}"
        self.logger.debug(message)
        # 强制刷新所有处理器
        for handler in self.logger.handlers:
            handler.flush()
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        if kwargs:
            message = f"{message} | Context: {json.dumps(kwargs, ensure_ascii=False)}"
        self.logger.info(message)
        # 强制刷新所有处理器
        for handler in self.logger.handlers:
            handler.flush()
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        if kwargs:
            message = f"{message} | Context: {json.dumps(kwargs, ensure_ascii=False)}"
        self.logger.warning(message)
        # 强制刷新所有处理器
        for handler in self.logger.handlers:
            handler.flush()
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        if kwargs:
            message = f"{message} | Context: {json.dumps(kwargs, ensure_ascii=False)}"
        self.logger.error(message)
        # 强制刷新所有处理器
        for handler in self.logger.handlers:
            handler.flush()
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        if kwargs:
            message = f"{message} | Context: {json.dumps(kwargs, ensure_ascii=False)}"
        self.logger.critical(message)
        # 强制刷新所有处理器
        for handler in self.logger.handlers:
            handler.flush()


def get_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> StructuredLogger:
    """
    获取结构化日志记录器
    
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        level: 日志级别
        
    Returns:
        StructuredLogger: 结构化日志记录器实例
    """
    return StructuredLogger(name, log_file, level)


def setup_global_logging(log_dir: str = "logs", level: int = logging.INFO):
    """
    设置全局日志配置
    
    Args:
        log_dir: 日志目录
        level: 日志级别
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                os.path.join(log_dir, "application.log"),
                maxBytes=10*1024*1024,
                backupCount=5
            )
        ]
    )